"""Ambiente de La Copa: decoraciones nuevas del editor."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from multijugador.movimiento import ColisionesMapa  # noqa: E402
from nucleo.rutas import RAIZ  # noqa: E402

NUEVAS = ("Animaciones/HojitasAn2.png", "Animaciones/HojitasAn5.png", "Animaciones/Vegetación_animacion.png",
          "Animales/Pajaro.png", "Animales/Lagarto.png", "Animales/Sapo.png", "Vegetación/Flor1.png",
          "Vegetación/Presente/vegetacionextrapresente_1.png")


class Decoraciones(unittest.TestCase):
    def test_el_arte_del_catalogo_existe(self):
        for nombre in NUEVAS:
            self.assertTrue((RAIZ / "Imagenes" / nombre).is_file(), nombre)

    def test_ninguna_decoracion_nueva_tiene_colision(self):
        datos = {"decoracion": [{"name": n, "x": .5, "y": .5, "w": .1, "h": .1} for n in NUEVAS], "hitboxes": []}
        self.assertEqual(ColisionesMapa(datos).npcs, [])


if __name__ == "__main__":
    unittest.main()
