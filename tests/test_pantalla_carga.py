"""Pantalla de carga y fondo del menú con el tríptico de las tres eras."""
import os
import subprocess
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from nucleo.rutas import RAIZ


class PantallaCargaTresEras(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((960, 720))

    def test_importar_no_carga_imagenes(self):
        codigo = "import pygame, interfaz.pantallas_viaje; assert not pygame.display.get_init()"
        resultado = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)

    def test_triptico_completo_sin_recortar_y_con_progreso(self):
        from interfaz.pantallas_viaje import PantallaCarga
        carga = PantallaCarga()
        self.assertEqual(carga.marco.width, 960)  # las tres eras caben enteras
        self.assertTrue(pygame.Rect(0, 0, 960, 720).contains(carga.marco))
        superficie = pygame.Surface((960, 720))
        for progreso in (None, 0, .5, 1, 7):
            carga.dibujar(superficie, "Preparando La Copa y tus compañeros…", progreso)

    def test_el_paneo_del_menu_nunca_deja_bordes_vacios(self):
        from interfaz.pantallas_viaje import FondoTresEras, PERIODO_PANEO_MS
        fondo = FondoTresEras()
        self.assertGreaterEqual(fondo.imagen.get_height(), 720)
        superficie = pygame.Surface((960, 720))
        for paso in range(9):
            superficie.fill((255, 0, 255))
            fondo.dibujar(superficie, paso * PERIODO_PANEO_MS // 8)
            for punto in ((0, 0), (959, 0), (0, 719), (959, 719)):
                self.assertNotEqual(tuple(superficie.get_at(punto))[:3], (255, 0, 255), (paso, punto))

    def test_sin_imagen_se_usan_respaldos(self):
        from interfaz.pantallas_viaje import FondoTresEras, PantallaCarga
        superficie = pygame.Surface((960, 720))
        FondoTresEras("no/existe.png").dibujar(superficie, 0)
        PantallaCarga("no/existe.png").dibujar(superficie, "Cargando", .5)


if __name__ == "__main__":
    unittest.main()
