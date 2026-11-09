"""Ambiente de La Copa: niebla y decoraciones nuevas del editor."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from multijugador.movimiento import ColisionesMapa  # noqa: E402
from multijugador.partida_local import ClienteCampanaLocal  # noqa: E402
from nucleo import preferencias  # noqa: E402
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


class Niebla(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)

    def test_se_carga_por_cuadros_y_se_dibuja(self):
        from interfaz.partida_multijugador import VistaPartida
        cliente = ClienteCampanaLocal("Prueba", "guardian")
        vista = VistaPartida("local", cliente.eventos.get_nowait())
        self.assertEqual(len(vista.cuadros_niebla), 8)
        pantalla = pygame.Surface((960, 720))
        vista._dibujar_niebla(pantalla, 1234)

    def test_la_preferencia_se_guarda(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "p.json"
            with mock.patch.object(preferencias, "ARCHIVO", ruta):
                datos = preferencias.cargar()
                self.assertTrue(datos["niebla"])
                datos["niebla"] = False
                preferencias.guardar(datos)
                self.assertFalse(preferencias.cargar()["niebla"])
                self.assertFalse(json.loads(ruta.read_text(encoding="utf-8"))["niebla"])


if __name__ == "__main__":
    unittest.main()
