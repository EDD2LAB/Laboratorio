"""Sala en línea real: los roles libres se llenan con bots del servidor."""
import os
import queue
import time
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


class BotsEnRedTests(unittest.TestCase):
    def test_roles_libres_se_cubren_con_bots_que_acompanan(self):
        from multijugador.cliente_internet import ClienteInternet
        from multijugador.servidor_local import ServidorLocal
        servidor = ServidorLocal()
        clientes = []

        def esperar(cliente, predicado, limite=15):
            fin = time.monotonic() + limite
            ultimo = None
            while time.monotonic() < fin:
                try:
                    evento = cliente.eventos.get(timeout=.1)
                except queue.Empty:
                    continue
                self.assertNotIn(evento.get("tipo"), ("rechazado", "desconectado"), evento)
                if predicado(evento):
                    return evento
                ultimo = evento
            self.fail(f"La sala no avanzó a tiempo: {ultimo}")

        try:
            a = ClienteInternet(servidor.url, "A", crear=True)
            clientes.append(a)
            codigo = esperar(a, lambda e: e["tipo"] == "bienvenida")["codigo"]
            b = ClienteInternet(servidor.url, "B", codigo=codigo)
            clientes.append(b)
            esperar(b, lambda e: e["tipo"] == "bienvenida")
            for cliente, rol in ((a, "guardian"), (b, "habitante")):
                cliente.enviar("rol", rol=rol)
                cliente.enviar("listo", listo=True)
            esperar(a, lambda e: e["tipo"] == "estado" and len(e["jugadores"]) == 2
                    and all(j["listo"] for j in e["jugadores"]))
            a.enviar("iniciar")
            estado = esperar(a, lambda e: e["tipo"] == "estado" and e.get("fase") == "partida")
            jugadores = estado["mundo"]["jugadores"]
            self.assertEqual(len(jugadores), 4)
            bots = {j["id"]: j for j in jugadores if j.get("controlador") == "bot"}
            self.assertEqual({j["rol"] for j in bots.values()}, {"mensajero", "aspirante"})
            inicio = {i: (j["x"], j["y"]) for i, j in bots.items()}

            def bots_se_movieron(evento):
                if evento.get("tipo") != "estado" or "mundo" not in evento:
                    return False
                # Con dos personas, los bots no investigan por su cuenta.
                self.assertEqual(evento["mundo"].get("caso", {}).get("investigadores", 0), 0)
                return any((j["x"], j["y"]) != inicio[j["id"]]
                           for j in evento["mundo"]["jugadores"] if j["id"] in inicio)
            a.mover(0, 1)  # los bots acompañan a las personas y les dejan espacio
            esperar(a, bots_se_movieron, limite=10)
        finally:
            for cliente in clientes:
                cliente.cerrar()
            servidor.cerrar()


if __name__ == "__main__":
    unittest.main()
