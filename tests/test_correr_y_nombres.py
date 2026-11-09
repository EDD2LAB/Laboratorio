"""Shift para correr (servidor autoritativo), animaciones de correr/caminar y tecla L."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

from multijugador.movimiento import (  # noqa: E402
    MULTIPLICADOR_CORRER, ColisionesMapa, PartidaMovimiento,
)

ROLES = ("guardian", "mensajero", "habitante", "aspirante")


def partida_sin_paredes():
    return PartidaMovimiento([{"id": r, "nombre": r, "rol": r} for r in ROLES], 0,
                             ColisionesMapa({"hitboxes": [], "decoracion": []}))


class CorrerServidorTests(unittest.TestCase):
    def distancia(self, correr):
        partida = partida_sin_paredes()
        jugador = partida.jugadores["guardian"]
        x0 = jugador["x"]
        datos = {"dx": 1, "dy": 0, "seq": 1}
        if correr is not None:
            datos["correr"] = correr
        partida.recibir("guardian", datos, 0.0)
        partida.actualizar(0.1)
        return jugador["x"] - x0, jugador

    def test_correr_es_mas_rapido(self):
        caminando, _ = self.distancia(False)
        corriendo, jugador = self.distancia(True)
        self.assertGreater(caminando, 0)
        self.assertAlmostEqual(corriendo, caminando * MULTIPLICADOR_CORRER, delta=1)
        self.assertTrue(jugador["corriendo"])

    def test_cliente_antiguo_sin_campo_correr_camina(self):
        caminando, _ = self.distancia(False)
        sin_campo, jugador = self.distancia(None)
        self.assertAlmostEqual(sin_campo, caminando, delta=.01)
        self.assertFalse(jugador["corriendo"])

    def test_correr_debe_ser_booleano(self):
        partida = partida_sin_paredes()
        with self.assertRaises(ValueError):
            partida.recibir("guardian", {"dx": 1, "dy": 0, "seq": 1, "correr": "si"}, 0.0)

    def test_campana_local_transmite_correr(self):
        from multijugador.partida_local import ClienteCampanaLocal
        cliente = ClienteCampanaLocal("Prueba", "guardian")
        cliente.mover(0, 1, True)
        cliente.actualizar(.05)
        self.assertEqual(cliente._partida.controles["local"][3], True)
        cliente.cerrar()


class VistaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((960, 720))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_sprites_de_correr_y_caminar(self):
        from interfaz.partida_multijugador import DIRECCIONES, cargar_personajes
        personajes = cargar_personajes()
        for rol in ROLES:
            for direccion in DIRECCIONES:
                self.assertTrue(personajes[rol][("correr", direccion)])
                self.assertTrue(personajes[rol][("caminar", direccion)])
        # El Mensajero tiene hojas propias; Mira usa sus caminatas al correr.
        for rol in ("mensajero",):
            self.assertIsNot(personajes[rol][("correr", "abajo")], personajes[rol][("caminar", "abajo")])

    def test_l_oculta_y_muestra_nombres(self):
        from multijugador.partida_local import ClienteCampanaLocal
        from interfaz.partida_multijugador import VistaPartida
        cliente = ClienteCampanaLocal("Prueba", "guardian")
        vista = VistaPartida(cliente.identificador, cliente.eventos.get_nowait())
        vista.panel.modo = None
        tecla = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_l, mod=0, unicode="l", scancode=0)
        self.assertTrue(vista.mostrar_nombres)
        vista.manejar_evento(tecla, (0, 0), cliente)
        self.assertFalse(vista.mostrar_nombres)
        vista.dibujar(pygame.Surface((960, 720)), "LOCAL")
        vista.manejar_evento(tecla, (0, 0), cliente)
        self.assertTrue(vista.mostrar_nombres)
        cliente.cerrar()


if __name__ == "__main__":
    unittest.main()
