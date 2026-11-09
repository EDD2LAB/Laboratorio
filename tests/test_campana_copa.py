import itertools
import unittest
import uuid

from multijugador.campana import CASOS
from multijugador.movimiento import ColisionesMapa, PartidaMovimiento
from multijugador.reparacion import angulo_aguja, dentro_de_zona


def tiempo_acierto(puente):
    """Primer instante de la aguja (posterior al último intento) en zona verde."""
    inicio = int(max(0, puente.ultimo_tiempo_aguja)) + 1
    return next(t for t in range(inicio, inicio + 1200) if dentro_de_zona(angulo_aguja(t), puente.progreso))


class CampanaTests(unittest.TestCase):
    def crear(self, roles):
        return PartidaMovimiento([dict(id=str(i), nombre=str(i), rol=r) for i, r in enumerate(roles)], 0,
                                 ColisionesMapa({"hitboxes": [], "decoracion": []}))

    def accion(self, p, i, accion, **datos):
        return p.actuar(i, dict(accion=accion, ronda=p.mision.ronda, id_solicitud=uuid.uuid4().hex, **datos), 0)

    def fuente(self, p, i):
        o = p.mision.privado(i)["objetivo"]
        p.jugadores[i].update(x=o["x"], y=o["y"])
        return o

    def preparar(self, p):
        for i in p.jugadores:
            o = self.fuente(p, i)
            self.assertTrue(self.accion(p, i, "interactuar", objetivo=o["id"])["ok"])
        for j in p.jugadores.values():
            j.update(x=480, y=380)
        for i in p.jugadores:
            otro = next(j for j in p.jugadores if j != i)
            self.assertTrue(self.accion(p, otro, "entregar", pista="pista_" + p.jugadores[otro]["rol"], destinatario=i, medio="directo")["ok"])

    def hacer_actividad(self, p):
        ids = list(p.jugadores)[:2]
        d = p.mision.encargo.destino
        for i in ids:
            p.jugadores[i].update(x=d["x"], y=d["y"])
        self.assertTrue(self.accion(p, ids[0], "sujetar")["ok"])
        for _ in range(3):
            p.actualizar(p.ultima + 1)
            self.assertTrue(self.accion(p, ids[1], "trabajar")["ok"])
        self.reparar_puente(p)

    def completar_materiales(self, p):
        """Caso 1: la canasta de herramientas es el tercer objeto obligatorio."""
        e = p.mision.encargo
        i = list(p.jugadores)[0]
        while not e.materiales_listos:
            o = e.objetivo(i, p.jugadores)
            p.jugadores[i].update(x=o["x"], y=o["y"])
            self.assertTrue(self.accion(p, i, "recoger_suministro", objetivo=o["id"])["ok"])
            p.jugadores[i].update(x=e.destino["x"], y=e.destino["y"])
            self.assertTrue(self.accion(p, i, "depositar")["ok"])

    def reparar_puente(self, p, i=None):
        if p.mision.puente.reparado or not p.mision.encargo.config.get("requiere_puente"):
            return
        i = i or list(p.jugadores)[0]
        o = p.mision.objetivo_puente
        p.jugadores[i].update(x=o["x"], y=o["y"])
        self.assertTrue(self.accion(p, i, "interactuar", objetivo="puente_1")["ok"])
        while p.mision.puente.estado == "REPAIR_MINIGAME":
            p.actualizar(p.ultima + 1)
            self.assertTrue(self.accion(p, i, "intento_reparacion", tiempo_aguja_ms=tiempo_acierto(p.mision.puente))["ok"])
        p.actualizar(p.ultima + 1)
        self.assertTrue(p.mision.puente.reparado)

    def avanzar(self, p):
        for i in list(p.jugadores)[:2]:
            if i not in p.mision.materiales:
                self.fuente(p, i)
                self.assertTrue(self.accion(p, i, "recoger_suministro")["ok"])
            d = p.mision.encargo.destino
            p.jugadores[i].update(x=d["x"], y=d["y"])
            self.assertTrue(self.accion(p, i, "depositar")["ok"])
        self.completar_materiales(p)
        self.hacer_actividad(p)
        for j in p.jugadores.values():
            j.update(x=480, y=380)
        for i in p.jugadores:
            self.assertTrue(self.accion(p, i, "continuar")["ok"])

    def test_campana_completa_con_todas_las_parejas_y_cuatro_jugadores(self):
        roles = ("guardian", "mensajero", "habitante", "aspirante")
        for equipo in list(itertools.combinations(roles, 2)) + [roles]:
            with self.subTest(equipo=equipo):
                p = self.crear(equipo)
                for ronda, caso in enumerate(p.mision.casos):
                    self.preparar(p)
                    for i in p.jugadores:
                        self.assertTrue(self.accion(p, i, "votar", opcion=caso[3])["ok"])
                    self.assertTrue(p.mision.resultado["correcto"])
                    self.assertIn(caso[5] if ronda else "rumor", p.mision.resultado["texto"])
                    if ronda < len(CASOS) - 1:
                        self.avanzar(p)
                        self.assertFalse(p.mision.conocidas["0"])
                self.assertEqual(p.mision.fase, "final")
                self.assertEqual(len(p.mision.publico(p.conectados)["balance"]), 4)
                self.assertEqual(p.mision.publico(p.conectados)["estrellas"], 11)

    def test_suministros_distancia_dos_aportes_y_acuses_antiguos(self):
        p = self.crear(("guardian", "habitante"))
        self.assertFalse(self.accion(p, "0", "recoger_suministro")["ok"])
        self.preparar(p)
        for i in p.jugadores:
            self.accion(p, i, "votar", opcion="corregir")
        self.assertFalse(self.accion(p, "0", "continuar")["ok"])
        self.assertFalse(self.accion(p, "0", "recoger_suministro")["ok"])
        self.avanzar(p)
        viejo = dict(accion="interactuar", objetivo="archivo", ronda=0, id_solicitud=uuid.uuid4().hex)
        self.assertFalse(p.actuar("0", viejo, 0)["ok"])
        self.assertFalse(p.mision.conocidas["0"])

    def test_habilidades_no_se_pueden_repetir_y_correo_es_privado(self):
        p = self.crear(("guardian", "mensajero", "habitante", "aspirante"))
        for i in p.jugadores:
            self.assertFalse(self.accion(p, i, "habilidad")["ok"])
        self.preparar(p)
        for i in ("0", "2"):
            self.fuente(p, i)
        p.jugadores["1"].update(x=p.jugadores["2"]["x"], y=p.jugadores["2"]["y"])
        for i in p.jugadores:
            if i == "3":
                p.jugadores[i].update(x=480, y=380)
            self.assertTrue(self.accion(p, i, "habilidad")["ok"])
            self.assertFalse(self.accion(p, i, "habilidad")["ok"])
        self.assertNotIn("inventario", p.mision.publico(p.conectados))
        for i in p.jugadores:
            self.assertIn("pista_mensajero", p.mision.conocidas[i])

    def test_presion_se_pausa_sin_equipo_y_bono_no_se_repite(self):
        p = self.crear(("guardian", "habitante"))
        p.conectados = {"0"}
        for segundo in range(1, 65):
            p.actualizar(segundo)
        self.assertEqual(p.mision.oleadas, 0)
        p.conectados.add("1")
        for segundo in range(65, 126):
            p.actualizar(segundo)
        self.assertEqual(p.mision.oleadas, 0)  # El primer caso no tiene presión.
        self.assertEqual(p.mision.indicadores["desinformacion"], 0)
        self.preparar(p)
        p.mision.actualizar(0, p.conectados)
        confianza = p.mision.indicadores["confianza"]
        p.mision.actualizar(0, p.conectados)
        self.assertEqual(p.mision.indicadores["confianza"], confianza)

    def test_variantes_tienen_soluciones_distintas_y_no_se_publican_pruebas(self):
        from unittest.mock import patch
        for ultimo in (False, True):
            with patch("logica.sorteo_partida.SorteoPartida.elegir", side_effect=lambda opciones: opciones[-1 if ultimo else 0]):
                p = self.crear(("guardian", "habitante"))
            self.assertEqual(p.mision.casos[1][3], "difundir" if ultimo else "descartar")
            self.assertEqual(p.mision.casos[2][3], "descartar" if ultimo else "difundir")
            self.assertNotIn("correcta", p.mision.publico(p.conectados))

    def test_rectificar_no_duplica_puntuacion_ni_reprocesa_solicitudes(self):
        p = self.crear(("guardian", "habitante"))
        self.preparar(p)
        for i in p.jugadores:
            self.accion(p, i, "votar", opcion="difundir")
        self.accion(p, "0", "rectificar")
        for i in p.jugadores:
            self.accion(p, i, "votar", opcion="corregir")
        self.assertEqual(p.mision.puntos, 100)  # 80 por rectificar + 20 por informar al equipo.
        solicitud = dict(accion="recoger_suministro", ronda=0, id_solicitud=uuid.uuid4().hex)
        self.fuente(p, "0")
        acuse = p.actuar("0", solicitud, 0)
        self.avanzar(p)
        self.assertEqual(p.actuar("0", solicitud, 0), acuse)
        self.assertFalse(p.mision.materiales)


    def test_ausencia_no_bloquea_a_dos_jugadores_ya_preparados(self):
        p = self.crear(("guardian", "habitante", "mensajero"))
        self.preparar(p)
        for i in p.jugadores:
            self.accion(p, i, "votar", opcion="corregir")
        for i in ("0", "1"):
            self.fuente(p, i)
            self.accion(p, i, "recoger_suministro")
            d = p.mision.encargo.destino
            p.jugadores[i].update(x=d["x"], y=d["y"])
            self.accion(p, i, "depositar")
        self.completar_materiales(p)
        self.hacer_actividad(p)
        for i in ("0", "1"):
            p.jugadores[i].update(x=480, y=380)
            self.accion(p, i, "continuar")
        self.assertEqual(p.mision.ronda, 0)
        p.conectados.discard("2")
        p.actualizar(0)
        self.assertEqual(p.mision.ronda, 1)


class CampanaRedTests(unittest.IsolatedAsyncioTestCase):
    async def test_dos_clientes_completan_campana_por_websocket(self):
        import asyncio
        import aiohttp
        from aiohttp.test_utils import TestServer
        from multijugador.protocolo import VERSION
        from multijugador.tiempo_real import crear_app, SERVICIO
        async with TestServer(crear_app()) as servidor:
            async with aiohttp.ClientSession() as cliente:
                async def post(ruta, datos, token=None):
                    async with cliente.post(servidor.make_url(ruta), json=datos,
                                            headers={"Authorization": "Bearer " + token} if token else {}) as respuesta:
                        self.assertEqual(respuesta.status, 200)
                        return await respuesta.json()
                a = await post("/v1/crear", {"nombre": "A", "version": VERSION})
                b = await post("/v1/unirse", {"nombre": "B", "version": VERSION, "codigo": a["codigo"]})
                sesiones = (a, b)
                for j, rol in zip(sesiones, ("guardian", "habitante")):
                    await post("/v1/accion", {"tipo": "rol", "rol": rol}, j["token"])
                    await post("/v1/accion", {"tipo": "listo", "listo": True}, j["token"])
                servidor.app[SERVICIO].salas[a["codigo"]].rellenar_con_bots = False  # solo humanos
                await post("/v1/accion", {"tipo": "iniciar"}, a["token"])
                p = servidor.app[SERVICIO].salas[a["codigo"]].partida
                sockets = [await cliente.ws_connect(servidor.make_url("/v1/juego"), headers={"Authorization": "Bearer " + j["token"]}) for j in sesiones]
                async def actuar(indice, accion, **datos):
                    clave = uuid.uuid4().hex
                    await sockets[indice].send_json(dict(tipo="accion", accion=accion, ronda=p.mision.ronda, id_solicitud=clave, **datos))
                    for _ in range(100):
                        evento = await asyncio.wait_for(sockets[indice].receive_json(), 3)
                        if evento.get("id_solicitud") == clave:
                            self.assertTrue(evento["ok"], evento)
                            return
                    self.fail("No llegó el acuse del servidor.")
                try:
                    for ronda, caso in enumerate(p.mision.casos):
                        for i, j in enumerate(sesiones):
                            o = p.mision.privado(j["id"])["objetivo"]
                            p.jugadores[j["id"]].update(x=o["x"], y=o["y"])
                            await actuar(i, "interactuar", objetivo=o["id"])
                        for j in p.jugadores.values():
                            j.update(x=480, y=380)
                        for i, j in enumerate(sesiones):
                            await actuar(i, "entregar", pista="pista_" + p.jugadores[j["id"]]["rol"], destinatario=sesiones[1-i]["id"], medio="directo")
                        for i in range(2):
                            await actuar(i, "votar", opcion=caso[3])
                        self.assertTrue(p.mision.resultado["correcto"])
                        if ronda < 3:
                            for i, j in enumerate(sesiones):
                                o = p.mision.privado(j["id"])["objetivo"]
                                p.jugadores[j["id"]].update(x=o["x"], y=o["y"])
                                await actuar(i, "recoger_suministro")
                                d = p.mision.encargo.destino
                                p.jugadores[j["id"]].update(x=d["x"], y=d["y"])
                                await actuar(i, "depositar")
                            e = p.mision.encargo
                            while not e.materiales_listos:  # caso 1: canasta de herramientas
                                o = e.objetivo(sesiones[0]["id"], p.jugadores)
                                p.jugadores[sesiones[0]["id"]].update(x=o["x"], y=o["y"])
                                await actuar(0, "recoger_suministro", objetivo=o["id"])
                                p.jugadores[sesiones[0]["id"]].update(x=d["x"], y=d["y"])
                                await actuar(0, "depositar")
                            for j in p.jugadores.values():
                                j.update(x=d["x"], y=d["y"])
                            await actuar(0, "sujetar")
                            for _ in range(3):
                                await asyncio.sleep(.7)
                                await actuar(1, "trabajar")
                            if e.config.get("requiere_puente"):
                                o = p.mision.objetivo_puente
                                p.jugadores[sesiones[0]["id"]].update(x=o["x"], y=o["y"])
                                await asyncio.sleep(.1)
                                await actuar(0, "interactuar", objetivo="puente_1")
                                while p.mision.puente.estado == "REPAIR_MINIGAME":
                                    await asyncio.sleep(.3)
                                    await actuar(0, "intento_reparacion", tiempo_aguja_ms=tiempo_acierto(p.mision.puente))
                                await asyncio.sleep(1.0)
                                self.assertTrue(p.mision.puente.reparado)
                            for j in p.jugadores.values():
                                j.update(x=480, y=380)
                            for i in range(2):
                                await actuar(i, "continuar")
                    self.assertEqual(p.mision.fase, "final")
                finally:
                    for ws in sockets:
                        await ws.close()


if __name__ == "__main__":
    unittest.main()
