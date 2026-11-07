"""Red de seguridad del refactor: el juego arranca y corre frames sin errores.

- Modo un jugador: ~120 frames del bucle real de juego.main().
- Menú inicial: unos frames de MenuInicio.ejecutar().
- Multijugador: sala real en 127.0.0.1 (servidor de producción en un hilo)
  con dos clientes por WebSocket y ~120 frames de la vista de partida.
"""
import os
import queue
import time
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402


class _ContadorFrames:
    """Envuelve pygame.display.flip y pide salir tras N frames."""

    def __init__(self, limite):
        self.limite = limite
        self.frames = 0
        self.original = pygame.display.flip

    def __enter__(self):
        def flip(*args, **kwargs):
            self.frames += 1
            if self.frames >= self.limite:
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            return self.original(*args, **kwargs)
        pygame.display.flip = flip
        # Con SDL_VIDEODRIVER=dummy no existen cursores del sistema.
        self.cursor = pygame.mouse.set_cursor
        pygame.mouse.set_cursor = lambda *a, **k: None
        return self

    def __exit__(self, *_):
        pygame.display.flip = self.original
        pygame.mouse.set_cursor = self.cursor


class ArranqueTests(unittest.TestCase):
    def test_un_jugador_corre_120_frames(self):
        import juego
        pygame.init()
        with _ContadorFrames(120) as contador:
            with self.assertRaises(SystemExit):  # main() termina con sys.exit()
                juego.main()
        self.assertGreaterEqual(contador.frames, 120)

    def test_menu_inicio_corre_y_sale(self):
        from interfaz.inicio import mostrar_menu_inicio
        with _ContadorFrames(30) as contador:
            self.assertEqual(mostrar_menu_inicio(), "salir")
        self.assertGreaterEqual(contador.frames, 30)
        pygame.quit()

    def test_sala_multijugador_local_corre_120_frames(self):
        from multijugador.cliente_internet import ClienteInternet
        from multijugador.servidor_local import ServidorLocal
        pygame.init()
        pygame.display.set_mode((960, 720))
        servidor = ServidorLocal()
        clientes = []

        def esperar(cliente, predicado):
            fin = time.monotonic() + 15
            while time.monotonic() < fin:
                try:
                    evento = cliente.eventos.get(timeout=.1)
                except queue.Empty:
                    continue
                self.assertNotIn(evento.get("tipo"), ("rechazado", "desconectado"), evento)
                if predicado(evento):
                    return evento
            self.fail("La sala no avanzó a tiempo.")

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
            esperar(a, lambda e: e["tipo"] == "estado" and len(e["jugadores"]) == 2 and all(j["listo"] for j in e["jugadores"]))
            a.enviar("iniciar")
            estado = esperar(a, lambda e: e["tipo"] == "estado" and e.get("fase") == "partida")
            from interfaz.partida_multijugador import VistaPartida
            identificador = next(j["id"] for j in estado["jugadores"] if j["nombre"] == "A")
            vista = VistaPartida(identificador, estado)
            lienzo = pygame.Surface((960, 720))
            for frame in range(120):
                while True:
                    try:
                        evento = a.eventos.get_nowait()
                    except queue.Empty:
                        break
                    if evento.get("tipo") == "estado" and evento.get("fase") == "partida":
                        vista.recibir(evento)
                while True:
                    try:
                        b.eventos.get_nowait()
                    except queue.Empty:
                        break
                a.mover(1 if frame < 60 else -1, 0)
                vista.actualizar(1 / 60, a)
                vista.dibujar(lienzo, "PRUEBA")
            self.assertTrue(vista.jugadores)
        finally:
            for cliente in clientes:
                cliente.cerrar()
            servidor.cerrar()
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
