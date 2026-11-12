"""Transición del túnel entre dimensiones."""
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from nucleo.rutas import RAIZ


class TunelViaje(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((960, 720))

    def test_importar_no_carga_arte(self):
        codigo = "import pygame, interfaz.tunel_viaje; assert not pygame.display.get_init()"
        resultado = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)

    def test_recorre_todo_el_viaje_y_termina(self):
        from interfaz.escenas_multijugador import Transicion
        from interfaz.tunel_viaje import DURACION
        for dimension in ("la_copa", "presente", "futuro", None):
            transicion = Transicion("Era II: Distrito Conecta", pygame.Surface((128, 128)), dimension)
            superficie = pygame.Surface((960, 720))
            pasos = 0
            while not transicion.terminada:
                transicion.actualizar(1 / 30, None)
                transicion.dibujar(superficie, None)
                pasos += 1
            self.assertAlmostEqual(pasos / 30, DURACION, delta=.1)

    def test_el_arte_se_prepara_una_sola_vez(self):
        import interfaz.tunel_viaje as tunel
        from interfaz.escenas_multijugador import Transicion
        tunel._BASE.clear()
        with patch.object(tunel, "cargar_imagen", wraps=tunel.cargar_imagen) as cargar:
            for _ in range(3):
                Transicion("Era I: La Copa", None, "la_copa").dibujar(pygame.Surface((960, 720)), None)
        self.assertEqual(cargar.call_count, 1)

    def test_sin_arte_del_tunel_sigue_funcionando(self):
        import interfaz.tunel_viaje as tunel
        from interfaz.escenas_multijugador import Transicion
        tunel._BASE.clear()
        try:
            with patch.object(tunel, "cargar_imagen", return_value=None):
                transicion = Transicion("Era III: Ciudad Núcleo", None, "futuro")
                transicion.actualizar(1.3, None)
                transicion.dibujar(pygame.Surface((960, 720)), None)
        finally:
            tunel._BASE.clear()


if __name__ == "__main__":
    unittest.main()
