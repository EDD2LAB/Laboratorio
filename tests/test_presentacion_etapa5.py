"""Regresiones del arte opcional, sus proporciones y avisos de acciones."""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from interfaz.arte import ajustar_imagen, RETRATOS_NOMBRADOS
from interfaz.boton import Boton, etiqueta_ajustada
from interfaz.cooperativo import PanelCooperativo, VERDE
from interfaz.presentacion_arte import AnimacionesNucleo, tarjetas_disponibles
from nucleo.recursos import cargar_imagen


class Presentacion(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)

    def test_retratos_reales_caben_sin_deformarse(self):
        for archivo in RETRATOS_NOMBRADOS.values():
            original = cargar_imagen("Retratos/" + archivo)
            ajustada = ajustar_imagen(original, (78, 88))
            limites = original.get_bounding_rect()
            self.assertLessEqual(ajustada.get_width(), 78)
            self.assertLessEqual(ajustada.get_height(), 88)
            self.assertAlmostEqual(ajustada.get_width() / ajustada.get_height(), limites.w / limites.h, delta=.025)
        self.assertIsNone(ajustar_imagen(pygame.Surface((10, 10), pygame.SRCALPHA), (78, 88)))

    def test_tiras_reales_y_estados_no_inventan_derrota(self):
        arte = AnimacionesNucleo()
        self.assertEqual(len(arte.cuadros["reposo"]), 8)
        self.assertEqual(len(arte.cuadros["sereno"]), 9)
        self.assertEqual(len(arte.cuadros["saturado"]), 9)
        for contexto, esperado in (({}, "inquieto"), ({"pistas": 3, "total_pistas": 3}, "carga"),
                                    ({"resultado": {"opcion": "compartir"}}, "saturado"),
                                    ({"resultado": {"correcto": True}}, "sereno")):
            self.assertEqual(arte.estado(contexto), esperado)
            self.assertEqual(arte.cuadro(contexto, 180).get_size(), (32, 32))
        with mock.patch("pygame.transform.scale", side_effect=AssertionError("escalado por cuadro")):
            self.assertIs(arte.cuadro({}, 180), arte.cuadro({}, 180))

    def test_archivos_ausentes_o_tira_malformada_permiten_respaldo(self):
        with mock.patch("interfaz.presentacion_arte.cargar_imagen", return_value=None):
            self.assertIsNone(AnimacionesNucleo().cuadro({}, 0))
            self.assertEqual(tarjetas_disponibles(), {})
        with mock.patch("interfaz.presentacion_arte.cargar_imagen", return_value=pygame.Surface((181, 20))):
            self.assertIsNone(AnimacionesNucleo().cuadro({}, 0))

    def test_tarjetas_reales_conservan_area_clicable(self):
        tarjetas = tarjetas_disponibles()
        self.assertEqual(len(tarjetas), 6)
        for imagen in tarjetas.values():
            self.assertEqual(imagen.get_size(), (180, 200))
            self.assertGreater(imagen.get_bounding_rect().width, 0)

    def test_frases_largas_no_salen_del_boton_y_el_bloqueo_se_conserva(self):
        fuente = pygame.font.Font(None, 26)
        for texto in ("Gracias por la información", "Confirmar y entregar todos los suministros", "A" * 100):
            imagen = etiqueta_ajustada(fuente, texto, 160, 40, (255, 255, 255))
            self.assertLessEqual(imagen.get_width(), 160)
            self.assertLessEqual(imagen.get_height(), 40)
        boton = Boton("Confirmar", centro=(200, 200), fuente=fuente, tamano=(180, 50))
        self.assertTrue(boton.presionar((200, 200)))
        self.assertEqual(boton.estado, "presionado")
        boton.establecer_bloqueado()
        self.assertFalse(boton.soltar((200, 200)))

    def test_aviso_rechazado_se_distingue_sin_depender_del_color(self):
        panel = PanelCooperativo.__new__(PanelCooperativo)
        panel.vista = SimpleNamespace(narrador=SimpleNamespace(decir=mock.Mock()))
        panel.notificar("Necesitas otra prueba.", ok=False)
        self.assertTrue(panel.toast.startswith("Atención:"))
        self.assertNotEqual(panel.color_toast, VERDE)
        panel.notificar("Pista entregada.", ok=True)
        self.assertTrue(panel.toast.startswith("Listo:"))
        self.assertEqual(panel.color_toast, VERDE)
