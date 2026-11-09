"""Finales del equipo y efectos del mapa de La Copa."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from interfaz.finales import determinar_final  # noqa: E402
from multijugador.partida_local import ClienteCampanaLocal  # noqa: E402


class ReglaDelFinal(unittest.TestCase):
    def test_victoria_exige_positivos_altos_y_poco_ruido(self):
        bien = dict(sabiduria=60, confianza=60, armonia=60, susurros_falsos=20, desinformacion=20)
        self.assertEqual(determinar_final(bien), "victoria")
        self.assertEqual(determinar_final(dict(bien, sabiduria=30, confianza=30, armonia=30)), "game_over")
        self.assertEqual(determinar_final(dict(bien, susurros_falsos=50, desinformacion=50)), "game_over")


class ConPartida(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        from interfaz.partida_multijugador import VistaPartida
        self.cliente = ClienteCampanaLocal("Prueba", "guardian")
        self.vista = VistaPartida("local", self.cliente.eventos.get_nowait())

    def caso(self):
        return self.vista.estado["mundo"]["caso"]


class FinalDelEquipo(ConPartida):
    def test_aparece_una_vez_al_completar_las_dos_dimensiones(self):
        self.caso().update(fase="final", presente={"completada": True}, indicadores=dict(sabiduria=90, confianza=90, armonia=90))
        self.vista._revisar_final()
        final = self.vista.pantalla_final
        self.assertIsNotNone(final)
        self.assertEqual(final.resultado, "victoria")
        self.assertIsNotNone(final.imagen)
        final.dibujar(pygame.Surface((960, 720)))
        self.vista.manejar_evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(1, 1)), (1, 1), self.cliente)
        self.assertIsNone(self.vista.pantalla_final)
        self.vista._revisar_final()
        self.assertIsNone(self.vista.pantalla_final)

    def test_no_aparece_sin_terminar_distrito_conecta(self):
        self.caso().update(fase="final", presente={"completada": False})
        self.vista._revisar_final()
        self.assertIsNone(self.vista.pantalla_final)


if __name__ == "__main__":
    unittest.main()
