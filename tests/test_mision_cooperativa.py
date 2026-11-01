import asyncio
import itertools
import json
import unittest
import uuid

import aiohttp
from aiohttp.test_utils import TestServer

from multijugador.mision import PRUEBAS
from multijugador.movimiento import ColisionesMapa, PartidaMovimiento
from multijugador.protocolo import VERSION
from multijugador.tiempo_real import crear_app, SERVICIO, CONEXIONES


def partida(roles=("guardian", "habitante")):
    return PartidaMovimiento([{"id": str(i), "nombre": "Persona" + str(i), "rol": rol}
                              for i, rol in enumerate(roles)], 0, ColisionesMapa({"hitboxes": [], "decoracion": []}))


def actuar(p, identificador, accion, ahora=0, **datos):
    return p.actuar(identificador, {"accion": accion, "id_solicitud": uuid.uuid4().hex, **datos}, ahora)


def recoger(p, identificador):
    objetivo = p.mision.privado(identificador)["objetivo"]
    p.jugadores[identificador].update(x=objetivo["x"], y=objetivo["y"])
    return actuar(p, identificador, "interactuar", objetivo=objetivo["id"])


def reunir(p):
    for jugador in p.jugadores.values():
        jugador.update(x=480, y=380)


def preparar(p):
    for i in p.jugadores:
        assert recoger(p, i)["ok"]
    reunir(p)
    for i in p.jugadores:
        origen = "1" if i == "0" else "0"
        pista = "pista_" + p.jugadores[origen]["rol"]
        assert actuar(p, origen, "entregar", destinatario=i, pista=pista, medio="directo")["ok"]


class PruebasCaso(unittest.TestCase):
    def test_fuentes_alcanzables_en_el_mapa_real(self):
        from collections import deque
        p = PartidaMovimiento([{"id": "0", "nombre": "A", "rol": "guardian"}], 0)
        inicio = p.jugadores["0"]
        cola = deque([(inicio["x"], inicio["y"])])
        visitados = set(cola)
        objetivos = {o["id"]: o for o in p.mision.objetivos if o.get("rol") or o["id"] == "caldero"}
        alcanzados = set()
        while cola and len(alcanzados) < len(objetivos):
            x, y = cola.popleft()
            for clave, objetivo in objetivos.items():
                if (x - objetivo["x"]) ** 2 + (y - objetivo["y"]) ** 2 <= 66 ** 2:
                    alcanzados.add(clave)
            for dx, dy in ((4, 0), (-4, 0), (0, 4), (0, -4)):
                siguiente = x + dx, y + dy
                if siguiente not in visitados:
                    visitados.add(siguiente)
                    if not p.colisiones.bloqueado(*siguiente):
                        cola.append(siguiente)
        self.assertEqual(alcanzados, set(objetivos))

    def test_todas_las_parejas_de_roles_pueden_resolver(self):
        for roles in itertools.combinations(("guardian", "mensajero", "habitante", "aspirante"), 2):
            with self.subTest(roles=roles):
                p = partida(roles)
                preparar(p)
                self.assertTrue(actuar(p, "0", "votar", opcion="corregir")["ok"])
                self.assertIsNone(p.mision.resultado)
                self.assertTrue(actuar(p, "1", "votar", opcion="corregir")["ok"])
                self.assertTrue(p.mision.resultado["correcto"])
                self.assertEqual(p.mision.indicadores["confianza"], 62)

    def test_distancia_rol_y_prueba_fabricada(self):
        p = partida()
        self.assertFalse(actuar(p, "0", "interactuar", objetivo="archivo")["ok"])
        self.assertTrue(recoger(p, "0")["ok"])
        self.assertFalse(actuar(p, "0", "entregar", destinatario="1", pista="inventada", medio="directo")["ok"])
        self.assertFalse(actuar(p, "0", "entregar", destinatario={}, pista="pista_guardian", medio="directo")["ok"])
        fuente = p.mision.privado("1")["objetivo"]
        p.jugadores["0"].update(x=fuente["x"], y=fuente["y"])
        self.assertTrue(actuar(p, "0", "interactuar", objetivo=fuente["id"])["ok"])
        self.assertEqual(len(p.mision.privado("0")["inventario"]), 1)

    def test_privacidad_hasta_entrega_y_confirmacion(self):
        p = partida()
        recoger(p, "0")
        self.assertNotIn(PRUEBAS["guardian"][1], json.dumps(p.estado("1"), ensure_ascii=False))
        self.assertNotIn(PRUEBAS["guardian"][1], json.dumps(p.estado(), ensure_ascii=False))
        reunir(p)
        acuse = actuar(p, "0", "entregar", destinatario="1", pista="pista_guardian", medio="directo")
        self.assertTrue(acuse["ok"])
        self.assertIn(PRUEBAS["guardian"][1], json.dumps(p.estado("1"), ensure_ascii=False))
        self.assertTrue(any(a["tipo"] == "entrega" for a in p.mision.privado("1")["avisos"]))

    def test_reintentos_no_duplican_efectos(self):
        p = partida(); preparar(p)
        solicitud = {"accion": "entregar", "id_solicitud": uuid.uuid4().hex,
                     "destinatario": "1", "pista": "pista_guardian", "medio": "directo"}
        total = len(p.mision.entregas)
        a = p.actuar("0", solicitud, 0)
        b = p.actuar("0", solicitud, 0)
        self.assertEqual(a, b)
        self.assertEqual(len(p.mision.entregas), total)
        actuar(p, "0", "votar", opcion="corregir")
        voto = {"accion": "votar", "id_solicitud": uuid.uuid4().hex, "opcion": "corregir"}
        p.actuar("1", voto, 0); p.actuar("1", voto, 0)
        self.assertEqual(p.mision.indicadores["confianza"], 62)

    def test_eco_distancia_mensajes_y_recepcion(self):
        p = partida(); recoger(p, "0")
        self.assertFalse(actuar(p, "0", "eco", mensaje=0)["ok"])
        eco = next(o for o in p.mision.objetivos if o["tipo"] == "eco")
        p.jugadores["0"].update(x=eco["x"], y=eco["y"])
        p.jugadores["1"].update(x=900, y=600)
        self.assertTrue(actuar(p, "0", "entregar", destinatario="1", pista="pista_guardian", medio="eco")["ok"])
        self.assertTrue(actuar(p, "0", "eco", mensaje=0, ahora=10)["ok"])
        self.assertFalse(actuar(p, "0", "eco", mensaje=1, ahora=10)["ok"])
        self.assertTrue(any(a["tipo"] == "eco" for a in p.mision.privado("1")["avisos"]))

    def test_no_se_resuelve_solo_ni_sin_pruebas(self):
        p = partida(); reunir(p)
        self.assertFalse(actuar(p, "0", "votar", opcion="corregir")["ok"])
        preparar(p)
        p.conectados = {"0"}
        self.assertFalse(actuar(p, "0", "votar", opcion="corregir")["ok"])
        self.assertIsNone(p.mision.resultado)

    def test_empate_cambio_y_rectificacion_unica(self):
        p = partida(); preparar(p)
        actuar(p, "0", "votar", opcion="corregir")
        actuar(p, "1", "votar", opcion="difundir")
        self.assertIsNone(p.mision.resultado)
        self.assertTrue(p.mision.publico(p.conectados)["empate"])
        actuar(p, "0", "votar", opcion="difundir")
        self.assertEqual(p.mision.indicadores["desinformacion"], 20)
        self.assertTrue(actuar(p, "0", "rectificar")["ok"])
        actuar(p, "0", "votar", opcion="corregir")
        actuar(p, "1", "votar", opcion="corregir")
        self.assertTrue(p.mision.resultado["correcto"])
        self.assertEqual(p.mision.indicadores["desinformacion"], 10)
        self.assertFalse(actuar(p, "0", "rectificar")["ok"])

    def test_cuatro_votantes_y_ausencia(self):
        p = partida(("guardian", "habitante", "mensajero", "aspirante")); preparar(p)
        for i in ("0", "1", "2"):
            actuar(p, i, "votar", opcion="corregir")
        self.assertIsNone(p.mision.resultado)
        p.conectados.discard("3")
        p.actualizar(.05)
        self.assertTrue(p.mision.resultado["correcto"])


class PruebasCasoRed(unittest.IsolatedAsyncioTestCase):
    async def test_privacidad_y_acuse_repetido_tras_corte(self):
        async with TestServer(crear_app()) as servidor:
            async with aiohttp.ClientSession() as cliente:
                async def post(ruta, datos, token=""):
                    async with cliente.post(servidor.make_url(ruta), json=datos, headers={"Authorization": "Bearer " + token}) as r:
                        self.assertEqual(r.status, 200)
                        return await r.json()
                a = await post("/v1/crear", {"nombre": "A", "version": VERSION})
                b = await post("/v1/unirse", {"nombre": "B", "version": VERSION, "codigo": a["codigo"]})
                for j, rol in ((a, "guardian"), (b, "habitante")):
                    await post("/v1/accion", {"tipo": "rol", "rol": rol}, j["token"])
                    await post("/v1/accion", {"tipo": "listo", "listo": True}, j["token"])
                await post("/v1/accion", {"tipo": "iniciar"}, a["token"])
                p = servidor.app[SERVICIO].salas[a["codigo"]].partida
                fuente = p.mision.privado(a["id"])["objetivo"]
                p.jugadores[a["id"]].update(x=fuente["x"], y=fuente["y"])
                solicitud = {"tipo": "accion", "accion": "interactuar", "objetivo": fuente["id"], "id_solicitud": uuid.uuid4().hex}
                async def conectar(token):
                    return await cliente.ws_connect(servidor.make_url("/v1/juego"), headers={"Authorization": "Bearer " + token})
                async def leer(ws, tipo):
                    for _ in range(100):
                        e = await asyncio.wait_for(ws.receive_json(), 2)
                        if e["tipo"] == tipo:
                            return e
                    self.fail("No llegó la confirmación.")
                ws = await conectar(a["token"])
                otro = await conectar(b["token"])
                try:
                    await ws.send_json(solicitud)
                    acuse = await leer(ws, "acuse")
                    self.assertTrue(acuse["ok"])
                    estado_otro = await leer(otro, "estado")
                    self.assertNotIn(PRUEBAS["guardian"][1], json.dumps(estado_otro, ensure_ascii=False))
                    await ws.close()
                    ws = await conectar(a["token"])
                    await ws.send_json(solicitud)
                    self.assertEqual(await leer(ws, "acuse"), acuse)
                    self.assertEqual(len(p.mision.halladas), 1)
                finally:
                    await ws.close(); await otro.close()


class PruebasClienteConAcuses(unittest.TestCase):
    def test_accion_sin_acuse_se_reenvia_tras_reconexion(self):
        import queue
        import time
        from soporte_servidor import ServidorPrueba
        from multijugador.cliente_internet import ClienteInternet
        servidor = ServidorPrueba()
        clientes = []
        def esperar(c, predicado):
            fin = time.monotonic() + 8
            while time.monotonic() < fin:
                try:
                    e = c.eventos.get(timeout=.1)
                except queue.Empty:
                    continue
                if e["tipo"] in ("desconectado", "rechazado"):
                    self.fail(e.get("mensaje"))
                if predicado(e):
                    return e
            self.fail("No se recuperó la confirmación de la acción.")
        try:
            url = "http://127.0.0.1:" + str(servidor.server_port)
            a = ClienteInternet(url, "A", crear=True); clientes.append(a)
            codigo = esperar(a, lambda e: e["tipo"] == "bienvenida")["codigo"]
            b = ClienteInternet(url, "B", codigo=codigo); clientes.append(b)
            esperar(b, lambda e: e["tipo"] == "bienvenida")
            for c, rol in ((a, "guardian"), (b, "habitante")):
                c.enviar("rol", rol=rol); c.enviar("listo", listo=True)
            esperar(a, lambda e: e["tipo"] == "estado" and len(e["jugadores"]) == 2 and all(j["listo"] for j in e["jugadores"]))
            a.enviar("iniciar")
            esperar(a, lambda e: e["tipo"] == "estado" and e.get("fase") == "partida")
            async def preparar_corte():
                p = servidor.app[SERVICIO].salas[codigo].partida
                identificador = servidor.app[SERVICIO].sesiones[a._token]["id"]
                fuente = p.mision.privado(identificador)["objetivo"]
                p.jugadores[identificador].update(x=fuente["x"], y=fuente["y"])
                while a._token not in servidor.app[CONEXIONES]:
                    await asyncio.sleep(.01)
                ws = servidor.app[CONEXIONES][a._token]
                original = ws.send_json
                async def perder_acuse(datos, *args, **kwargs):
                    if datos.get("tipo") == "acuse":
                        await ws.close(code=1001)
                    else:
                        await original(datos, *args, **kwargs)
                ws.send_json = perder_acuse
                return fuente["id"]
            fuente = asyncio.run_coroutine_threadsafe(preparar_corte(), servidor.loop).result(timeout=4)
            a.actuar("interactuar", objetivo=fuente)
            esperar(a, lambda e: e["tipo"] == "reconectando")
            acuse = esperar(a, lambda e: e["tipo"] == "acuse")
            self.assertTrue(acuse["ok"])
            self.assertFalse(a._pendientes)
            self.assertEqual(len(servidor.app[SERVICIO].salas[codigo].partida.mision.halladas), 1)
        finally:
            for c in clientes:
                c.cerrar()
            servidor.shutdown()
