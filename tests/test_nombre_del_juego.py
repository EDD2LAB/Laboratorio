"""El juego se llama Timeless Glitch; La Copa sigue siendo la primera dimensión."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from logica.dimensiones import DIMENSIONES  # noqa: E402
from multijugador.presentacion import ERAS, titulo_era  # noqa: E402
from nucleo import preferencias  # noqa: E402


class Eras(unittest.TestCase):
    def test_cada_dimension_tiene_su_era(self):
        self.assertEqual(set(ERAS), set(DIMENSIONES))
        self.assertEqual(titulo_era("la_copa", DIMENSIONES["la_copa"]["nombre"]), "Era I: La Copa")
        self.assertEqual(titulo_era("presente", DIMENSIONES["presente"]["nombre"]), "Era II: Distrito Conecta")
        self.assertEqual(titulo_era("futuro", DIMENSIONES["futuro"]["nombre"]), "Era III: Ciudad Núcleo")


class Menu(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        ruta = mock.patch.object(preferencias, "ARCHIVO", Path(carpeta.name) / "p.json")
        ruta.start()
        self.addCleanup(ruta.stop)

    def test_el_menu_dibuja_el_nombre_sin_desbordar_el_panel(self):
        from interfaz.inicio import MenuInicio
        menu = MenuInicio()
        self.assertEqual(pygame.display.get_caption()[0], "Timeless Glitch")
        textos = []
        original = menu.texto
        menu.texto = lambda texto, x, y, size=20, *a, **k: textos.append((texto, size)) or original(texto, x, y, size, *a, **k)
        menu.dibujar()
        self.assertIn(("TIMELESS GLITCH", 44), textos)
        panel_util = 480 - 2 * 12  # panel del menú principal menos su margen
        for texto, size in textos:
            self.assertLessEqual(menu.fuentes[size].size(texto)[0], panel_util, texto)


if __name__ == "__main__":
    unittest.main()
