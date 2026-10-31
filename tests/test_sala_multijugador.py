"""Pruebas de integración de la sala con conexiones TCP reales en loopback."""
import queue
import time
import unittest

from multijugador.cliente import ClienteSala
from multijugador.protocolo import codificar, extraer
from multijugador.servidor import ServidorSala


def esperar(cliente, condicion, segundos=4):
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        try:
            evento = cliente.eventos.get(timeout=0.1)
        except queue.Empty:
            continue
        if condicion(evento):
            return evento
    raise AssertionError("No llegó el evento esperado del servidor.")


class PruebasSala(unittest.TestCase):
    def setUp(self):
        self.servidor = ServidorSala(0)
        self.servidor.iniciar()
        self.clientes = []

    def tearDown(self):
        for cliente in self.clientes:
            cliente.cerrar()
        self.servidor.cerrar()

    def conectar(self, nombre, anfitrion=False):
        cliente = ClienteSala("127.0.0.1", self.servidor.puerto, nombre,
                              self.servidor.clave_host if anfitrion else "")
        self.clientes.append(cliente)
        identificador = esperar(cliente, lambda e: e["tipo"] == "bienvenida")["id"]
        return cliente, identificador

    def estado(self, cliente, condicion):
        return esperar(cliente, lambda e: e["tipo"] == "estado" and condicion(e))

    def test_equipo_y_confirmacion_sincronizada(self):
        host, host_id = self.conectar("Anfitrión", True)
        otro, otro_id = self.conectar("Compañera")
        host.enviar("iniciar")
        esperar(host, lambda e: e["tipo"] == "error")
        host.enviar("rol", rol="guardian")
        otro.enviar("rol", rol="mensajero")
        self.estado(host, lambda e: all(j["rol"] for j in e["jugadores"]) and len(e["jugadores"]) == 2)
        host.enviar("listo", listo=True)
        otro.enviar("listo", listo=True)
        self.estado(host, lambda e: all(j["listo"] for j in e["jugadores"]))
        otro.enviar("iniciar")
        esperar(otro, lambda e: e["tipo"] == "error")
        host.enviar("iniciar")
        a = self.estado(host, lambda e: e["iniciada"])
        b = self.estado(otro, lambda e: e["iniciada"])
        self.assertEqual(a, b)
        self.assertEqual({j["id"] for j in a["jugadores"]}, {host_id, otro_id})
        # Una sala confirmada no acepta entradas nuevas.
        tarde = ClienteSala("127.0.0.1", self.servidor.puerto, "Tarde")
        self.clientes.append(tarde)
        esperar(tarde, lambda e: e["tipo"] == "rechazado")

    def test_roles_exclusivos_y_cambio_quita_listo(self):
        a, _ = self.conectar("A", True)
        b, _ = self.conectar("B")
        a.enviar("rol", rol="guardian")
        self.estado(a, lambda e: any(j["rol"] == "guardian" for j in e["jugadores"]))
        b.enviar("rol", rol="guardian")
        esperar(b, lambda e: e["tipo"] == "error")
        a.enviar("listo", listo=True)
        self.estado(a, lambda e: any(j["listo"] for j in e["jugadores"]))
        a.enviar("rol", rol="habitante")
        estado = self.estado(a, lambda e: any(j["rol"] == "habitante" for j in e["jugadores"]))
        self.assertFalse(any(j["listo"] for j in estado["jugadores"]))

    def test_cuatro_cupos_y_liberacion_al_salir(self):
        host, _ = self.conectar("Host", True)
        otros = [self.conectar("Jugador" + str(i))[0] for i in range(3)]
        self.estado(host, lambda e: len(e["jugadores"]) == 4)
        extra = ClienteSala("127.0.0.1", self.servidor.puerto, "Quinto")
        self.clientes.append(extra)
        esperar(extra, lambda e: e["tipo"] == "rechazado")
        otros[0].enviar("rol", rol="aspirante")
        self.estado(host, lambda e: any(j["rol"] == "aspirante" for j in e["jugadores"]))
        otros[0].cerrar()
        estado = self.estado(host, lambda e: len(e["jugadores"]) == 3)
        self.assertFalse(any(j["rol"] == "aspirante" for j in estado["jugadores"]))
        self.conectar("Nuevo")
        self.estado(host, lambda e: len(e["jugadores"]) == 4)

    def test_salida_anfitrion_cierra_sala(self):
        host, _ = self.conectar("Host", True)
        otro, _ = self.conectar("Otro")
        host.cerrar()
        esperar(otro, lambda e: e["tipo"] == "desconectado")

    def test_liberar_rol_y_reclamar_desde_otro_cliente(self):
        a, _ = self.conectar("A", True)
        b, b_id = self.conectar("B")
        a.enviar("rol", rol="guardian")
        self.estado(a, lambda e: any(j["rol"] == "guardian" for j in e["jugadores"]))
        a.enviar("listo", listo=True)
        a.enviar("rol", rol=None)
        estado = self.estado(a, lambda e: not any(j["rol"] for j in e["jugadores"]))
        self.assertFalse(any(j["listo"] for j in estado["jugadores"]))
        b.enviar("rol", rol="guardian")
        self.estado(a, lambda e: any(j["id"] == b_id and j["rol"] == "guardian" for j in e["jugadores"]))

    def test_reclamo_simultaneo_de_un_rol(self):
        a, _ = self.conectar("A", True)
        b, _ = self.conectar("B")
        a.enviar("rol", rol="mensajero")
        b.enviar("rol", rol="mensajero")
        estado = self.estado(a, lambda e: any(j["rol"] == "mensajero" for j in e["jugadores"]))
        self.assertEqual(sum(j["rol"] == "mensajero" for j in estado["jugadores"]), 1)

    def test_listo_sin_rol_y_nombre_duplicado(self):
        host, _ = self.conectar("Host", True)
        host.enviar("listo", listo=True)
        esperar(host, lambda e: e["tipo"] == "error")
        duplicado = ClienteSala("127.0.0.1", self.servidor.puerto, "HOST")
        self.clientes.append(duplicado)
        esperar(duplicado, lambda e: e["tipo"] == "rechazado")


class PruebasProtocolo(unittest.TestCase):
    def test_fragmentos_y_mensajes_juntos(self):
        datos = codificar({"tipo": "hola", "nombre": "María"}) + codificar({"tipo": "ping"})
        mensajes, resto = extraer(datos[:10])
        self.assertEqual(mensajes, [])
        mensajes, resto = extraer(resto + datos[10:])
        self.assertEqual(len(mensajes), 2)
        self.assertEqual(mensajes[0]["nombre"], "María")
        self.assertEqual(resto, b"")

    def test_limites_y_formato(self):
        for datos in (b"[]\n", b"no es json\n", b"x" * 16385):
            with self.assertRaises(ValueError):
                extraer(datos)


if __name__ == "__main__":
    unittest.main()
