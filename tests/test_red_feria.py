"""Revisión para la feria: arranque en frío de Render, versión distinta y mensajes raros."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import queue
import threading
import time
import unittest
from unittest import mock

from multijugador import cliente_internet
from multijugador.cliente_internet import ClienteInternet
from multijugador.protocolo import VERSION


class _ServidorFalso:
    """Responde /health con 503 las primeras ``dormido`` veces y luego con ``protocolo``."""

    def __init__(self, dormido=1, protocolo=VERSION, pagina=False):
        estado = {"pedidas": 0}

        class Manejador(BaseHTTPRequestHandler):
            def _responder(self, codigo, cuerpo, tipo="application/json"):
                datos = cuerpo.encode("utf-8")
                self.send_response(codigo)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(datos)))
                self.end_headers()
                self.wfile.write(datos)

            def do_GET(self):
                estado["pedidas"] += 1
                if estado["pedidas"] <= dormido:
                    if pagina:
                        return self._responder(200, "<html>Despertando</html>", "text/html")
                    return self._responder(503, "Service Unavailable", "text/plain")
                self._responder(200, json.dumps({"protocolo": protocolo}))

            def do_POST(self):
                self._responder(400, json.dumps({"error": "Sala de prueba"}))

            def log_message(self, *_):
                pass

        self.estado = estado
        self.http = ThreadingHTTPServer(("127.0.0.1", 0), Manejador)
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.http.server_port}"

    def cerrar(self):
        self.http.shutdown()
        self.http.server_close()


def _eventos(cliente, hasta, limite=15):
    vistos, fin = [], time.monotonic() + limite
    while time.monotonic() < fin:
        try:
            evento = cliente.eventos.get(timeout=.1)
        except queue.Empty:
            continue
        vistos.append(evento)
        if evento.get("tipo") in hasta:
            return vistos
    raise AssertionError("No llegó " + str(hasta) + ": " + str(vistos))


class ArranqueEnFrioTests(unittest.TestCase):
    def test_avisa_que_el_servidor_despierta_y_luego_sigue(self):
        servidor = _ServidorFalso(dormido=1)
        try:
            cliente = ClienteInternet(servidor.url, "Ana", crear=True)
            vistos = _eventos(cliente, ("rechazado", "desconectado"))
            cliente.cerrar()
        finally:
            servidor.cerrar()
        avisos = [e["mensaje"] for e in vistos if e["tipo"] == "aviso"]
        self.assertTrue(avisos and "Despertando el servidor" in avisos[0])
        self.assertEqual(vistos[-1]["mensaje"], "Sala de prueba")  # despertó y siguió con crear

    def test_una_pagina_html_no_muestra_un_error_tecnico(self):
        servidor = _ServidorFalso(dormido=1, pagina=True)
        try:
            cliente = ClienteInternet(servidor.url, "Ana", crear=True)
            vistos = _eventos(cliente, ("rechazado", "desconectado"))
            cliente.cerrar()
        finally:
            servidor.cerrar()
        self.assertFalse(any("Expecting value" in e.get("mensaje", "") for e in vistos))

    def test_version_distinta_lo_dice_con_las_dos_versiones(self):
        servidor = _ServidorFalso(dormido=0, protocolo=VERSION - 1)
        try:
            cliente = ClienteInternet(servidor.url, "Ana", crear=True)
            vistos = _eventos(cliente, ("rechazado", "desconectado"))
            cliente.cerrar()
        finally:
            servidor.cerrar()
        self.assertEqual(vistos[-1]["tipo"], "rechazado")
        self.assertIn(str(VERSION - 1), vistos[-1]["mensaje"])
        self.assertIn(str(VERSION), vistos[-1]["mensaje"])

    def test_si_no_despierta_lo_explica(self):
        servidor = _ServidorFalso(dormido=1000)
        try:
            with mock.patch.object(cliente_internet, "ESPERA_DESPERTAR", 2):
                cliente = ClienteInternet(servidor.url, "Ana", crear=True)
                vistos = _eventos(cliente, ("rechazado", "desconectado"))
                cliente.cerrar()
        finally:
            servidor.cerrar()
        self.assertEqual(vistos[-1]["tipo"], "desconectado")
        self.assertIn("no respondió", vistos[-1]["mensaje"])


class AccionesConTiposRarosTests(unittest.TestCase):
    def test_destino_o_categoria_que_no_son_texto_se_rechazan_sin_romper(self):
        from multijugador.clasificacion import evaluar
        from multijugador.movimiento import PartidaMovimiento
        partida = PartidaMovimiento([{"id": "a", "nombre": "A", "rol": "guardian"}], 0)
        with self.assertRaises(ValueError):
            partida.viajar("a", [])
        with self.assertRaises(ValueError):
            evaluar("puente_norte", [])


if __name__ == "__main__":
    unittest.main()
