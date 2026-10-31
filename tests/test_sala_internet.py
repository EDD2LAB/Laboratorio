"""Reglas del servicio público y transporte HTTP real, sin cuenta externa."""
import threading
import time
import unittest

from multijugador.cliente_internet import ClienteInternet, validar_url
from multijugador.protocolo import VERSION
from multijugador.servicio_internet import ServicioSalas, ServidorHTTP


class PruebasServicio(unittest.TestCase):
    def setUp(self):
        self.tiempo = [0]
        self.servicio = ServicioSalas(lambda: self.tiempo[0])

    def crear(self, nombre="Host"):
        return self.servicio.ejecutar("POST", "/v1/crear", {"nombre": nombre, "version": VERSION})

    def unir(self, codigo, nombre):
        return self.servicio.ejecutar("POST", "/v1/unirse", {"nombre": nombre, "version": VERSION, "codigo": codigo})

    def accion(self, sesion, **datos):
        return self.servicio.ejecutar("POST", "/v1/accion", datos, sesion["token"])

    def test_salas_aisladas_y_sin_tokens_en_estado(self):
        a, b = self.crear("A"), self.crear("B")
        self.assertNotEqual(a["codigo"], b["codigo"])
        invitado = self.unir(a["codigo"].lower(), "Invitado")
        estado = self.servicio.ejecutar("GET", "/v1/estado", {}, invitado["token"])
        self.assertEqual(len(estado["jugadores"]), 2)
        self.assertNotIn(b["id"], [j["id"] for j in estado["jugadores"]])
        self.assertNotIn(a["token"], str(estado))
        with self.assertRaises(PermissionError):
            self.servicio.ejecutar("GET", "/v1/estado", {}, "token_incorrecto")

    def test_roles_cupos_y_host(self):
        host = self.crear()
        invitados = [self.unir(host["codigo"], str(i)) for i in range(3)]
        with self.assertRaises(ValueError):
            self.unir(host["codigo"], "Quinto")
        self.accion(host, tipo="rol", rol="guardian")
        with self.assertRaises(ValueError):
            self.accion(invitados[0], tipo="rol", rol="guardian")
        for sesion, rol in zip([host] + invitados, ("guardian", "mensajero", "habitante", "aspirante")):
            self.accion(sesion, tipo="rol", rol=rol)
            self.accion(sesion, tipo="listo", listo=True)
        with self.assertRaises(ValueError):
            self.accion(invitados[0], tipo="iniciar")
        self.assertTrue(self.accion(host, tipo="iniciar")["iniciada"])

    def test_caducidad_y_cierre_de_sala(self):
        host = self.crear()
        otro = self.unir(host["codigo"], "Otro")
        self.tiempo[0] = 30
        self.servicio.ejecutar("GET", "/v1/estado", {}, host["token"])
        self.tiempo[0] = 46
        estado = self.servicio.ejecutar("GET", "/v1/estado", {}, host["token"])
        self.assertEqual(len(estado["jugadores"]), 1)
        with self.assertRaises(PermissionError):
            self.servicio.ejecutar("GET", "/v1/estado", {}, otro["token"])
        self.servicio.ejecutar("POST", "/v1/salir", {}, host["token"])
        self.assertFalse(self.servicio.salas)

    def test_version_y_codigo_invalidos(self):
        with self.assertRaises(ValueError):
            self.servicio.ejecutar("POST", "/v1/crear", {"nombre": "Host", "version": -1})
        self.assertFalse(self.servicio.salas)
        with self.assertRaises(ValueError):
            self.unir("XXXXXX", "Invitado")

    def test_urls_seguras(self):
        self.assertEqual(validar_url(" https://salas.example.com/ "), "https://salas.example.com")
        validar_url("http://127.0.0.1:10000")
        for url in ("http://salas.example.com", "https://usuario:clave@salas.example.com", "", "https://example.com/ruta"):
            with self.assertRaises(ValueError):
                validar_url(url)


class PruebasHTTP(unittest.TestCase):
    def test_clientes_http_comparten_sala(self):
        servidor = ServidorHTTP(("127.0.0.1", 0))
        hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
        hilo.start()
        url = "http://127.0.0.1:" + str(servidor.server_port)
        clientes = []

        def esperar(cliente, condicion):
            import queue
            limite = time.monotonic() + 5
            while time.monotonic() < limite:
                try:
                    evento = cliente.eventos.get(timeout=0.1)
                except queue.Empty:
                    continue
                if condicion(evento):
                    return evento
            self.fail("No llegó el evento HTTP esperado.")

        try:
            host = ClienteInternet(url, "Host", crear=True)
            clientes.append(host)
            codigo = esperar(host, lambda e: e["tipo"] == "bienvenida")["codigo"]
            otro = ClienteInternet(url, "Invitado", codigo=codigo)
            clientes.append(otro)
            esperar(otro, lambda e: e["tipo"] == "bienvenida")
            host.enviar("rol", rol="guardian")
            otro.enviar("rol", rol="mensajero")
            esperar(host, lambda e: e["tipo"] == "estado" and len(e["jugadores"]) == 2 and all(j["rol"] for j in e["jugadores"]))
            host.enviar("listo", listo=True)
            otro.enviar("listo", listo=True)
            esperar(host, lambda e: e["tipo"] == "estado" and all(j["listo"] for j in e["jugadores"]))
            host.enviar("iniciar")
            a = esperar(host, lambda e: e["tipo"] == "estado" and e["iniciada"])
            b = esperar(otro, lambda e: e["tipo"] == "estado" and e["iniciada"])
            self.assertEqual(a, b)
            host.cerrar()
            esperar(otro, lambda e: e["tipo"] == "desconectado")
        finally:
            for cliente in clientes:
                cliente.cerrar()
            servidor.shutdown()
            servidor.server_close()


if __name__ == "__main__":
    unittest.main()
