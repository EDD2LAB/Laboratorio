"""Regresiones de costuras caminables, líneas, pequeñas esquinas y puentes."""
import math
import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from multijugador.movimiento import ColisionesMapa, VELOCIDAD
from bots.navegador_bot import NavegadorBot
from mundo.colisiones import jugador_bloqueado


def rect(x, y, w, h, role="wall"):
    return dict(type="rect", role=role, rx=x / 960, ry=y / 720, rw=w / 960, rh=h / 720)


class MovimientoComodo(unittest.TestCase):
    def mapa(self, *paredes):
        return ColisionesMapa({"hitboxes": list(paredes), "decoracion": []})

    def test_cruza_union_de_dos_zonas_caminables_sin_salir_de_ellas(self):
        c = self.mapa(rect(100, 100, 200, 400, "walkable"), rect(300, 100, 200, 400, "walkable"))
        self.assertFalse(c.bloqueado(300, 300))
        x, y = c.mover(290, 300, 1, 0, .15)
        self.assertGreater(x, 310)
        self.assertFalse(c.bloqueado(x, y))

    def test_union_no_permite_cruzar_un_hueco_real(self):
        c = self.mapa(rect(100, 100, 200, 400, "walkable"), rect(301, 100, 200, 400, "walkable"))
        self.assertTrue(c.bloqueado(300, 300))
        self.assertLess(c.mover(290, 300, 1, 0, .15)[0], 300)

    def test_linea_no_infla_los_pies_como_un_circulo(self):
        c = self.mapa(dict(type="line", role="wall", x1=100/960, y1=200/720, x2=300/960, y2=200/720, thickness=2/960))
        self.assertFalse(c.bloqueado(200, 198))  # pies a dos px de la línea de 2 px
        self.assertTrue(c.bloqueado(200, 201))

    def test_roza_un_objeto_pequeno_sin_quedarse_atrapado(self):
        c = self.mapa(rect(408, 299, 1, 1))
        x, y = c.mover(402, 300, 1, 0, .1)
        self.assertGreater(x, 408)
        self.assertLessEqual(abs(y - 300), 3)
        self.assertFalse(c.bloqueado(x, y))
        self.assertLessEqual(math.hypot(x - 402, y - 300), VELOCIDAD * .1 + 1e-8)

    def test_no_rodea_automaticamente_una_pared_larga(self):
        c = self.mapa(rect(408, 0, 20, 720))
        x, y = c.mover(402, 300, 1, 0, .15)
        self.assertEqual((x, y), (402, 300))

    def test_diagonal_desliza_sin_atravesar_ni_aumentar_velocidad(self):
        c = self.mapa(rect(408, 0, 20, 720))
        x, y = c.mover(402, 300, 1, 1, .15)
        self.assertEqual(x, 402)
        self.assertGreater(y, 310)
        self.assertFalse(c.bloqueado(x, y))
        self.assertLessEqual(math.hypot(x - 402, y - 300), VELOCIDAD * .15)

    def test_no_corta_la_esquina_entre_dos_objetos(self):
        c = self.mapa(rect(406, 299, 1, 1), rect(394, 291, 1, 1))
        self.assertFalse(c.bloqueado(400, 300))
        self.assertFalse(c.bloqueado(401, 299))
        self.assertTrue(c.bloqueado(401, 300))
        self.assertTrue(c.bloqueado(400, 299))
        x, y = c.mover(400, 300, 1, -1, .1)
        self.assertNotEqual((round(x), round(y)), (401, 299))
        self.assertLess(math.dist((400, 300), (x, y)), 2)

    def test_puede_salir_del_bloqueo_activado_pero_no_entrar_desde_fuera(self):
        c = self.mapa()
        c.bloqueos = [(100, 100, 100, 100)]
        x, y = 150, 150
        for _ in range(4):
            x, y = c.mover(x, y, 0, -1, .15)
        self.assertFalse(c.bloqueado(x, y))
        self.assertLessEqual(y, 100)
        for _ in range(4):
            x, y = c.mover(x, y, 0, 1, .15)
        self.assertLessEqual(y, 100)

    def test_escape_del_puente_no_atraviesa_paredes_fijas(self):
        c = self.mapa(rect(0, 90, 960, 10))
        c.bloqueos = [(100, 100, 100, 100)]
        x, y = c.mover(150, 115, 0, -1, .15)
        self.assertGreaterEqual(y, 108)
        self.assertGreaterEqual(x, 100)

    def test_al_reparar_el_puente_vuelve_a_permitir_el_paso(self):
        c = self.mapa()
        c.bloqueos = [(100, 100, 100, 100)]
        self.assertEqual(c.mover(150, 100, 0, 1, .15), (150, 100))
        c.bloqueos = []
        self.assertGreater(c.mover(150, 100, 0, 1, .15)[1], 120)

    def test_bot_sale_de_un_bloqueo_sin_teletransportarse(self):
        c = self.mapa()
        c.bloqueos = [(100, 100, 100, 100)]
        bot = dict(x=150.0, y=150.0, animacion="reposo")
        nav = NavegadorBot(c)
        for _ in range(120):
            anterior = bot["x"], bot["y"]
            if nav.avanzar(bot, (150, 50), .05, radio=5):
                break
            self.assertLessEqual(math.dist(anterior, (bot["x"], bot["y"])), VELOCIDAD * .05 + 1e-6)
        self.assertLess(math.dist((bot["x"], bot["y"]), (150, 50)), 6)

    def test_bot_conserva_su_presupuesto_de_movimiento_entre_nodos(self):
        c = self.mapa()
        bot = dict(x=400.0, y=304.0, animacion="reposo")
        nav = NavegadorBot(c)
        nav.avanzar(bot, (800, 304), .1, radio=5)
        self.assertAlmostEqual(math.dist((400, 304), (bot["x"], bot["y"])), VELOCIDAD * .1)

    def test_bot_rodea_obstaculo_sin_saltar_los_vertices(self):
        c = self.mapa(rect(430, 260, 20, 80))
        bot = dict(x=400.0, y=300.0, animacion="reposo")
        nav = NavegadorBot(c)
        for _ in range(100):
            anterior = bot["x"], bot["y"]
            listo = nav.avanzar(bot, (480, 300), .05, radio=5)
            self.assertFalse(c.bloqueado(bot["x"], bot["y"]))
            self.assertLessEqual(math.dist(anterior, (bot["x"], bot["y"])), VELOCIDAD * .05 + 1e-6)
            if listo:
                break
        self.assertLessEqual(math.dist((bot["x"], bot["y"]), (480, 300)), 5)


class ParidadLocal(unittest.TestCase):
    def mundo(self, paredes, puente=None):
        return {"hitboxes": paredes, "personajes": [], "reparacion_puentes": puente}

    def test_costura_caminable_y_linea_en_motor_local(self):
        pies = pygame.Rect(294, 292, 12, 8)
        mundo = self.mundo([rect(100, 100, 200, 400, "walkable"), rect(300, 100, 200, 400, "walkable")])
        self.assertFalse(jugador_bloqueado(pies, mundo))
        mundo = self.mundo([dict(type="line", role="wall", x1=100/960, y1=200/720, x2=300/960, y2=200/720, thickness=2/960)])
        self.assertFalse(jugador_bloqueado(pygame.Rect(194, 190, 12, 8), mundo))

    def test_el_motor_local_tambien_deja_salir_del_puente(self):
        from mundo.colisiones import puede_mover_pies
        puente = SimpleNamespace(bloquea_paso=True, hitbox_puente=pygame.Rect(100, 100, 100, 100))
        mundo = self.mundo([], puente)
        self.assertTrue(puede_mover_pies(pygame.Rect(144, 142, 12, 8), pygame.Rect(144, 141, 12, 8), mundo))
        self.assertFalse(puede_mover_pies(pygame.Rect(144, 92, 12, 8), pygame.Rect(144, 93, 12, 8), mundo))

    def test_lineas_degeneradas_y_distancia_diagonal(self):
        from logica.movimiento_suave import linea_toca_rect
        self.assertTrue(linea_toca_rect((10, 10, 12, 8), 15, 15, 15, 15, 2))
        self.assertFalse(linea_toca_rect((10, 10, 12, 8), 30, 30, 30, 30, 2))
        self.assertTrue(linea_toca_rect((10, 10, 12, 8), 0, 0, 30, 30, 2))
