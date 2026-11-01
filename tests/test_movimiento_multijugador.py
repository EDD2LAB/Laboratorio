import asyncio
import math
import unittest

import aiohttp
from aiohttp.test_utils import TestServer

from multijugador.movimiento import ColisionesMapa, PartidaMovimiento, VELOCIDAD
from multijugador.protocolo import VERSION
from multijugador.tiempo_real import crear_app


class PruebasMovimiento(unittest.TestCase):
    def partida(self, colisiones=None):
        return PartidaMovimiento([{"id": "a", "nombre": "A", "rol": "guardian"}], 0,
                                  colisiones or ColisionesMapa({"hitboxes": [], "decoracion": []}))

    def test_velocidad_y_diagonal(self):
        for dx, dy in ((1, 0), (1, 1)):
            p = self.partida(); jugador = p.jugadores["a"]
            x, y = jugador["x"], jugador["y"]
            p.recibir("a", {"dx": dx, "dy": dy, "seq": 0}, 0)
            for i in range(1, 4):
                p.actualizar(i * .05)
            self.assertAlmostEqual(math.hypot(jugador["x"] - x, jugador["y"] - y), VELOCIDAD * .15)

    def test_sin_controles_se_detiene_y_no_acepta_teletransporte(self):
        p = self.partida(); j = p.jugadores["a"]; x = j["x"]
        p.recibir("a", {"dx": 1, "dy": 0, "seq": 1, "x": 999999}, 0)
        for i in range(1, 21):
            p.actualizar(i * .05)
        self.assertLessEqual(j["x"] - x, VELOCIDAD * .35 + .01)
        self.assertEqual(j["animacion"], "reposo")
        for dx in (100, float("nan"), True):
            with self.assertRaises(ValueError):
                p.recibir("a", {"dx": dx, "dy": 0, "seq": 2}, 1)

    def test_secuencia_antigua_y_usuario_ajeno(self):
        p = self.partida()
        inicio = p.jugadores["a"]["x"]
        p.recibir("a", {"dx": 1, "dy": 0, "seq": 4}, 0)
        p.recibir("a", {"dx": -1, "dy": 0, "seq": 3}, .1)
        p.actualizar(.1)
        self.assertGreater(p.jugadores["a"]["x"], inicio)
        with self.assertRaises(ValueError):
            p.recibir("b", {"dx": 0, "dy": 0, "seq": 0}, .1)

    def test_paredes_circulos_lineas_y_limites(self):
        c = ColisionesMapa({"hitboxes": [
            {"role": "wall", "type": "rect", "rx": .5, "ry": 0, "rw": .05, "rh": 1},
            {"role": "wall", "type": "circle", "cx": .2, "cy": .2, "r": .02},
            {"role": "wall", "type": "line", "x1": .3, "y1": 0, "x2": .3, "y2": 1},
        ]})
        self.assertTrue(c.bloqueado(480, 300))
        self.assertTrue(c.bloqueado(192, 144))
        self.assertTrue(c.bloqueado(288, 300))
        self.assertTrue(c.bloqueado(-1, 20))
        x, y = c.mover(465, 300, 1, 0, .15)
        self.assertFalse(c.bloqueado(x, y))
        self.assertLess(x, 480)

    def test_cuatro_inicios_reales_libres_y_distintos(self):
        p = PartidaMovimiento([{"id": str(i), "nombre": str(i), "rol": rol}
                               for i, rol in enumerate(("guardian", "mensajero", "habitante", "aspirante"))], 0)
        posiciones = {(j["x"], j["y"]) for j in p.jugadores.values()}
        self.assertEqual(len(posiciones), 4)
        self.assertFalse(any(p.colisiones.bloqueado(x, y) for x, y in posiciones))


class PruebasWebSocket(unittest.IsolatedAsyncioTestCase):
    async def test_cuatro_jugadores_movimiento_y_salida(self):
        async with TestServer(crear_app()) as servidor:
            async with aiohttp.ClientSession() as cliente:
                async def post(ruta, datos, token=""):
                    async with cliente.post(servidor.make_url(ruta), json=datos,
                                            headers={"Authorization": "Bearer " + token}) as r:
                        self.assertEqual(r.status, 200)
                        return await r.json()
                jugadores = []
                for i in range(4):
                    datos = {"nombre": "Jugador" + str(i), "version": VERSION}
                    if i:
                        datos["codigo"] = jugadores[0]["codigo"]
                    jugadores.append(await post("/v1/crear" if not i else "/v1/unirse", datos))
                with self.assertRaises(aiohttp.WSServerHandshakeError):
                    await cliente.ws_connect(servidor.make_url("/v1/juego"))
                for j, rol in zip(jugadores, ("guardian", "mensajero", "habitante", "aspirante")):
                    await post("/v1/accion", {"tipo": "rol", "rol": rol}, j["token"])
                    await post("/v1/accion", {"tipo": "listo", "listo": True}, j["token"])
                inicial = await post("/v1/accion", {"tipo": "iniciar"}, jugadores[0]["token"])
                sockets = [await cliente.ws_connect(servidor.make_url("/v1/juego"),
                           headers={"Authorization": "Bearer " + j["token"]}) for j in jugadores]
                async def estado(ws, condicion):
                    for _ in range(50):
                        mensaje = await asyncio.wait_for(ws.receive_json(), 2)
                        if condicion(mensaje):
                            return mensaje
                    self.fail("No llegó el estado esperado.")
                try:
                    primero = inicial["mundo"]["jugadores"][0]
                    for seq in range(8):
                        await sockets[0].send_json({"tipo": "mover", "dx": 1, "dy": 0, "seq": seq})
                        await asyncio.sleep(.05)
                    visto = await estado(sockets[1], lambda e: e.get("mundo", {}).get("jugadores", [{}])[0].get("x", 0) > primero["x"] + 5)
                    self.assertEqual(len(visto["mundo"]["jugadores"]), 4)
                    await sockets[1].close()
                    restante = await estado(sockets[0], lambda e: len(e.get("mundo", {}).get("jugadores", [])) == 3)
                    self.assertTrue(restante["iniciada"])
                    await sockets[0].close()
                    await estado(sockets[2], lambda e: e.get("tipo") == "desconectado")
                finally:
                    for ws in sockets:
                        await ws.close()


if __name__ == "__main__":
    unittest.main()
