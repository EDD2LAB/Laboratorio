"""Calles estrechas y una guía que rodea paredes en lugar de atravesarlas."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from interfaz.guia import buscar_camino, siguiente_paso
from multijugador.dimensiones_red import cargar_datos, cargar_interior
from multijugador.movimiento import ColisionesMapa


class CallesFuturo(unittest.TestCase):
    def setUp(self):
        self.m = ColisionesMapa(cargar_datos("futuro"))

    def punto(self, x, y):
        rx, ry, w, h = self.m.datos["rect_mapa"]
        return rx + x * w / 1048, ry + y * h / 577

    def test_recupera_margen_en_calles_y_escaleras_visibles(self):
        # Bordes de calles que antes rechazaba la caja de pies/grosor antiguo.
        for x, y in ((148, 400), (278, 510), (794, 330), (512, 205)):
            with self.subTest(x=x, y=y):
                self.assertFalse(self.m.bloqueado(*self.punto(x, y)))

    def test_escaleras_y_calles_se_recorreran_a_pie(self):
        for inicio, fin in (((157, 355), (157, 440)), ((500, 170), (500, 235)),
                            ((500, 350), (500, 425)), ((865, 375), (865, 445)),
                            ((755, 330), (790, 330))):
            with self.subTest(inicio=inicio):
                ruta = buscar_camino(self.m, self.punto(*inicio), self.punto(*fin), radio=8)
                self.assertTrue(ruta)
                self.assertTrue(all(self.m.trayecto_libre(a, b) for a, b in zip(ruta, ruta[1:])))

    def test_conserva_edificios_jardines_y_esculturas(self):
        for p in ((100, 35), (865, 490)):
            self.assertTrue(self.m.bloqueado(*self.punto(*p)), p)
        for inicio, fin in (((250, 280), (320, 250)), ((600, 440), (700, 400))):
            self.assertFalse(self.m.trayecto_libre(self.punto(*inicio), self.punto(*fin)))
        self.assertEqual(self.m.tamano_pies, (8, 5))
        self.assertEqual(ColisionesMapa(cargar_datos("presente")).tamano_pies, (12, 8))
        self.assertEqual(ColisionesMapa(cargar_interior("cafe_digital", "futuro")).tamano_pies, (12, 8))

    def test_la_guia_aprovecha_el_descansillo_central_sin_rodear_la_ciudad(self):
        ruta = buscar_camino(self.m, (450, 244), (416, 536), radio=24, paso=4, limite=40000)
        self.assertTrue(ruta)
        # Antes obligaba a recorrer más de mil píxeles por el extremo oriental.
        self.assertLess(len(ruta) * 4, 650)
        self.assertTrue(all(self.m.trayecto_libre(a, b) for a, b in zip(ruta, ruta[1:])))


class FlechaConRuta(unittest.TestCase):
    def setUp(self):
        self.m = ColisionesMapa({"hitboxes": [{"role": "wall", "type": "rect",
                "rx": 120/960, "ry": 50/720, "rw": 16/960, "rh": 120/720}]})

    def test_senala_un_desvio_transitable_y_no_el_objetivo_tras_la_pared(self):
        origen, destino = (80, 110), (200, 110)
        ruta = buscar_camino(self.m, origen, destino, radio=8)
        paso = siguiente_paso(self.m, origen, ruta)
        self.assertTrue(ruta)
        self.assertIsNotNone(paso)
        self.assertTrue(self.m.trayecto_libre(origen, paso))
        self.assertFalse(self.m.trayecto_libre(origen, destino))
        self.assertNotEqual(paso, destino)

    def test_no_retrocede_por_usar_una_ruta_de_unos_cuadros_antes(self):
        m = ColisionesMapa({"hitboxes": []})
        paso = siguiente_paso(m, (90, 100), [(x, 100) for x in range(10, 201, 8)])
        self.assertGreater(paso[0], 120)

    def test_no_inventa_direccion_si_no_hay_ruta(self):
        self.assertIsNone(siguiente_paso(self.m, (80, 110), []))

    def test_flecha_persiste_con_objetivo_en_camara_y_desaparece_al_llegar(self):
        from interfaz.partida_multijugador import VistaPartida
        m = ColisionesMapa({"hitboxes": []})
        vista = SimpleNamespace(dimension="futuro", identificador="a", colisiones=m,
                jugadores={"a": {"posicion": pygame.Vector2(100, 100)}},
                ruta_guia=[(x, 100) for x in range(100, 301, 8)])
        with patch("interfaz.orientacion.tarea_actual", return_value={"objetivo": {"id": "terminal", "x": 300, "y": 100}}):
            self.assertIsNotNone(VistaPartida._destino_flecha(vista, pygame.Rect(0, 0, 960, 720)))
            vista.jugadores["a"]["posicion"].update(280, 100)
            self.assertIsNone(VistaPartida._destino_flecha(vista, pygame.Rect(0, 0, 960, 720)))
