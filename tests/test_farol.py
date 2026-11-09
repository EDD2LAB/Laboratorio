"""El farol del tutorial usa su imagen, con el icono de píxeles como respaldo."""
import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from interfaz import suministros  # noqa: E402


class Farol(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        self.madera = pygame.Surface((40, 20), pygame.SRCALPHA)
        self.madera.fill((120, 80, 40, 255))

    def test_se_escala_igual_que_los_demas_materiales(self):
        suministros.configurar_sprites({"tablas": self.madera})
        for tamano in (26, 34):
            farol, tablas = suministros._sprites[("farol", tamano)], suministros._sprites[("tablas", tamano)]
            self.assertEqual(max(farol.get_size()), tamano)
            self.assertEqual(max(tablas.get_size()), tamano)

    def test_se_recorta_a_su_contenido(self):
        suministros.configurar_sprites({})
        farol = suministros._sprites[("farol", 34)]
        limites = farol.get_bounding_rect()
        self.assertGreaterEqual(max(limites.size), 32)

    def test_sin_imagen_queda_el_dibujo_de_respaldo(self):
        with mock.patch.object(suministros, "cargar_imagen", return_value=None):
            suministros.configurar_sprites({})
        self.assertNotIn(("farol", 26), suministros._sprites)
        lienzo = pygame.Surface((100, 100), pygame.SRCALPHA)
        suministros.dibujar_carga(lienzo, "farol", (50, 50))
        self.assertGreater(lienzo.get_bounding_rect().width, 0)

    def test_el_brillo_pulsa_y_se_reutiliza(self):
        suministros.configurar_sprites({})
        lienzo = pygame.Surface((200, 200), pygame.SRCALPHA)
        suministros._brillos.clear()
        for ahora in range(0, 4000, 40):
            suministros.dibujar_farol_en_suelo(lienzo, (100, 100), ahora)
        self.assertGreater(len(suministros._brillos), 1)
        self.assertLessEqual(len(suministros._brillos), 13)  # uno por radio, no uno por cuadro

    def test_solo_espera_en_el_suelo_hasta_que_lo_entregan(self):
        from interfaz.partida_multijugador import VistaPartida
        visible = VistaPartida._farol_en_el_suelo
        self.assertTrue(visible({"estado": "pendiente", "paso": 0}))
        self.assertTrue(visible({"estado": "activo", "paso": 1}))
        self.assertFalse(visible({"estado": "activo", "paso": 2}))
        self.assertFalse(visible({"estado": "terminado", "paso": 3}))
        self.assertFalse(visible({}))


if __name__ == "__main__":
    unittest.main()
