"""Regresiones de feria: IP compartida, gracia, RTT y transportes reales."""
import asyncio
import queue
import threading
import time
import unittest
from unittest import mock

import aiohttp
from aiohttp.test_utils import TestServer

from multijugador.cliente import ClienteSala
from multijugador.cliente_internet import ClienteInternet
from multijugador.metricas_red import SondaPing
from multijugador.protocolo import VERSION
from multijugador.servicio_internet import ServicioSalas, DemasiadasSolicitudes
from multijugador.tiempo_real import crear_app


def crear(s, nombre="Host", codigo=None, ip="universidad"):
    return s.ejecutar("POST", "/v1/unirse" if codigo else "/v1/crear",
                      {"nombre": nombre, "version": VERSION, "codigo": codigo}, ip=ip)


def iniciar(s):
    host = crear(s)
    otro = crear(s, "Invitado", host["codigo"])
    for j, rol in zip((host, otro), ("guardian", "mensajero")):
        for datos in ({"tipo": "rol", "rol": rol}, {"tipo": "listo", "listo": True}):
            s.ejecutar("POST", "/v1/accion", datos, j["token"])
    s.ejecutar("POST", "/v1/accion", {"tipo": "iniciar"}, host["token"])
    return host, otro


class LimitesYGracia(unittest.TestCase):
    def setUp(self):
        self.ahora = [0.0]
        self.s = ServicioSalas(lambda: self.ahora[0])

    def test_treinta_sesiones_con_ip_compartida_a_06_segundos(self):
        jugadores = []
        for i in range(30):
            codigo = jugadores[-1]["codigo"] if i % 4 else None
            jugadores.append(crear(self.s, str(i), codigo))
        for paso in range(101):
            self.ahora[0] = paso * .6
            for j in jugadores:
                self.s.ejecutar("GET", "/v1/estado", {}, j["token"], "universidad")
        self.assertEqual(len(self.s.sesiones), 30)

    def test_abuso_de_un_token_no_bloquea_otro_ni_health(self):
        a = crear(self.s)
        b = crear(self.s, "B", a["codigo"])
        for _ in range(300):
            self.s.ejecutar("GET", "/v1/estado", {}, a["token"])
        with self.assertRaises(DemasiadasSolicitudes):
            self.s.ejecutar("GET", "/v1/estado", {}, a["token"])
        self.assertEqual(len(self.s.ejecutar("GET", "/v1/estado", {}, b["token"])["jugadores"]), 2)
        self.assertTrue(self.s.ejecutar("GET", "/health", {})["ok"])

    def test_limite_de_creacion_por_ip_y_ventana(self):
        for i in range(60):
            crear(self.s, str(i))
        with self.assertRaises(DemasiadasSolicitudes):
            crear(self.s)
        crear(self.s, ip="otra-red")
        self.ahora[0] = 60
        crear(self.s)

    def test_tokens_invalidos_no_crean_buckets(self):
        for i in range(20):
            with self.assertRaises(PermissionError):
                self.s.ejecutar("GET", "/v1/estado", {}, str(i))
        self.assertFalse(self.s.peticiones)

    def test_gracia_conserva_identidad_rol_y_partida_tras_45_segundos(self):
        host, otro = iniciar(self.s)
        p = self.s.salas[host["codigo"]].partida
        p.jugadores[host["id"]]["seq"] = 77
        self.ahora[0] = 60
        estado = self.s.ejecutar("GET", "/v1/estado", {}, host["token"])
        yo = next(j for j in estado["mundo"]["jugadores"] if j["id"] == host["id"])
        self.assertEqual((yo["rol"], yo["seq"]), ("guardian", 77))
        self.assertIn(otro["token"], self.s.sesiones)
        self.assertIs(self.s.salas[host["codigo"]].partida, p)

    def test_anfitrion_ausente_transfiere_sin_perder_progreso(self):
        host, otro = iniciar(self.s)
        sala = self.s.salas[host["codigo"]]
        p = sala.partida
        p.mision.indicadores["confianza"] = 61
        self.ahora[0] = 110
        self.s.ejecutar("GET", "/v1/estado", {}, otro["token"])
        self.ahora[0] = 121
        estado = self.s.ejecutar("GET", "/v1/estado", {}, otro["token"])
        self.assertTrue(next(j for j in estado["jugadores"] if j["id"] == otro["id"])["anfitrion"])
        self.assertNotIn(host["token"], self.s.sesiones)
        self.assertIs(sala.partida, p)
        self.assertEqual(p.mision.indicadores["confianza"], 61)

    def test_sin_humanos_activos_la_sala_caduca(self):
        host, _ = iniciar(self.s)
        self.ahora[0] = 121
        self.s.limpiar()
        self.assertNotIn(host["codigo"], self.s.salas)


class RTTYRecuperacion(unittest.TestCase):
    def test_rtt_promediado_y_pongs_ajenos_no_alteran_medicion(self):
        reloj = [10.0]
        metricas = {}
        sonda = SondaPing(metricas, lambda: reloj[0])
        primero = sonda.siguiente()
        self.assertIsNone(sonda.siguiente())
        reloj[0] += .02
        self.assertFalse(sonda.recibir({"t": 12345}))
        self.assertTrue(sonda.recibir(primero))
        self.assertAlmostEqual(metricas["ping_ms"], 20)
        reloj[0] = 13
        segundo = sonda.siguiente()
        reloj[0] += .06
        self.assertTrue(sonda.recibir(segundo))
        self.assertAlmostEqual(metricas["ping_ms"], 30)
        self.assertFalse(sonda.recibir(segundo))

    def test_mas_de_tres_cortes_se_reintentan_sin_perder_sesion(self):
        c = ClienteInternet.__new__(ClienteInternet)
        c._cerrado = mock.Mock()
        c._cerrado.is_set.return_value = False
        c._evento = mock.Mock()
        c._jugar = mock.AsyncMock(side_effect=[OSError(), OSError(), OSError(), OSError(), None])
        c._abrir_juego()
        self.assertEqual(c._jugar.call_count, 5)

    def test_lectura_de_sala_se_recupera_sin_reenviar_acciones(self):
        c = ClienteInternet.__new__(ClienteInternet)
        c._cerrado = mock.Mock()
        c._cerrado.is_set.return_value = False
        c._evento = mock.Mock()
        c._peticion = mock.Mock(side_effect=[ConnectionError(), {"tipo": "estado", "revision": 1}])
        self.assertEqual(c._estado_recuperable()["revision"], 1)
        self.assertEqual(c._peticion.call_args_list, [mock.call("/v1/estado")] * 2)
        self.assertEqual(c._evento.call_args[0][0]["tipo"], "conexion_recuperada")

    def test_intentos_lentos_sin_recibir_estados_no_reinician_la_gracia(self):
        c = ClienteInternet.__new__(ClienteInternet)
        reloj = [0.0]
        c._cerrado = mock.Mock()
        c._cerrado.is_set.return_value = False
        c._cerrado.wait.side_effect = lambda segundos: reloj.__setitem__(0, reloj[0] + segundos)
        c._evento = mock.Mock()

        async def fallo_lento():
            reloj[0] += 11
            if reloj[0] > 200:
                raise ValueError("Se reinició indebidamente el plazo.")
            raise ConnectionError()

        c._jugar = fallo_lento
        with mock.patch("multijugador.cliente_internet.time.monotonic", side_effect=lambda: reloj[0]):
            with self.assertRaises(ConnectionError):
                c._abrir_juego()
        self.assertLess(reloj[0], 150)

    def test_ping_lan_real(self):
        from multijugador.servidor import ServidorSala
        servidor = ServidorSala(0)
        servidor.iniciar()
        c = ClienteSala("127.0.0.1", servidor.puerto, "Prueba", servidor.clave_host)
        try:
            fin = time.monotonic() + 4
            while c.metricas["ping_ms"] is None and time.monotonic() < fin:
                time.sleep(.02)
            self.assertIsNotNone(c.metricas["ping_ms"])
            self.assertGreater(c.metricas["bytes"], 0)
        finally:
            c.cerrar()
            servidor.cerrar()


class TransporteWS(unittest.IsolatedAsyncioTestCase):
    async def test_ping_no_consume_los_sesenta_controles_y_se_valida(self):
        s = ServicioSalas(lambda: 2.0)
        host, _ = iniciar(s)
        async with TestServer(crear_app(s)) as servidor:
            async with aiohttp.ClientSession() as cliente:
                async with cliente.ws_connect(servidor.make_url("/v1/juego"),
                                              headers={"Authorization": "Bearer " + host["token"]}) as ws:
                    await ws.send_json({"tipo": "ping", "t": "no-numerico"})
                    # El snapshot inicial puede adelantarse al error bajo carga.
                    for _ in range(20):
                        error = await asyncio.wait_for(ws.receive_json(), 2)
                        if error.get("tipo") == "error":
                            break
                    else:
                        self.fail("No llegó el rechazo del ping inválido.")
                    # El ping inválido consume un control; los válidos tienen su propia cuota.
                    await ws.send_json({"tipo": "ping", "t": 42.25})
                    for seq in range(59):
                        await ws.send_json({"tipo": "mover", "dx": 0, "dy": 0, "seq": seq})
                    for _ in range(20):
                        mensaje = await asyncio.wait_for(ws.receive_json(), 2)
                        if mensaje.get("tipo") == "pong":
                            self.assertEqual(mensaje["t"], 42.25)
                            break
                    else:
                        self.fail("No llegó el pong.")
                    self.assertFalse(ws.closed)
                    await ws.send_json({"tipo": "mover", "dx": 0, "dy": 0, "seq": 99})
                    for _ in range(20):
                        mensaje = await asyncio.wait_for(ws.receive(), 2)
                        if mensaje.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
                            break
                    self.assertEqual(ws.close_code, 1008)

    async def test_limite_http_responde_429_y_retry_after(self):
        s = ServicioSalas()
        host = crear(s)
        for _ in range(300):
            s.ejecutar("GET", "/v1/estado", {}, host["token"])
        async with TestServer(crear_app(s)) as servidor:
            async with aiohttp.ClientSession() as c:
                async with c.get(servidor.make_url("/v1/estado"), headers={"Authorization": "Bearer " + host["token"]}) as r:
                    self.assertEqual(r.status, 429)
                    self.assertGreater(int(r.headers["Retry-After"]), 0)

    async def test_ping_internet_real_no_aparece_como_evento_de_juego(self):
        # Clientes reales en hilos, servidor en este event loop.
        s = ServicioSalas()
        host, _ = iniciar(s)
        c = ClienteInternet.__new__(ClienteInternet)
        c.url = ""
        c._token = host["token"]
        c._cerrado = threading.Event()
        c._movimiento, c._correr, c._secuencia = (0, 0), False, 0
        c._pendientes, c._lock_acciones = {}, threading.Lock()
        c._ronda = 0
        c.eventos = queue.Queue()
        c.metricas = {"mensajes": 0, "bytes": 0, "ping_ms": None}
        async with TestServer(crear_app(s)) as servidor:
            c.url = str(servidor.make_url("" )).rstrip("/")
            tarea = asyncio.create_task(c._jugar())
            try:
                async with asyncio.timeout(4):
                    while c.metricas["ping_ms"] is None:
                        await asyncio.sleep(.02)
                self.assertGreaterEqual(c.metricas["ping_ms"], 0)
                self.assertTrue(all(e["tipo"] != "pong" for e in list(c.eventos.queue)))
            finally:
                c._cerrado.set()
                await asyncio.wait_for(tarea, 3)
