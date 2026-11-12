"""Sprites, efectos y HUD del combate final (solo cliente)."""
import os
import subprocess
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from nucleo.rutas import RAIZ


def final(turno="aviso", segundos=2.0, minis=None, disparo=None, integridad=3, derribados=()):
    return dict(fase="activo", ronda=1, integridad=integridad, hechos=["guardian"],
                puntos=dict(aspirante=dict(x=300, y=300)),
                batalla=dict(fase=1, turno=turno, segundos=segundos, blancos=[(200, 300)] if turno != "recarga" else [],
                             derribados=list(derribados)),
                aventura=dict(fabricado=True, municion=2, disparo=disparo, taller=dict(x=100, y=300), cargas={},
                              minis=[dict(id=1, x=400, y=300, vida=2, aviso=2.5)] if minis is None else minis,
                              minis_activos=turno in ("aviso", "rayo")))


class SinCargaAlImportar(unittest.TestCase):
    def test_importar_no_crea_superficies(self):
        codigo = ("import pygame, interfaz.sprites_combate, interfaz.efectos_combate, interfaz.batalla_cooperativa;"
                  "assert not pygame.display.get_init()")
        resultado = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)


class Sprites(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((960, 720))

    def test_tamanos_y_transparencia(self):
        from interfaz import sprites_combate as sp
        self.assertEqual(sp.mini_nucleo(0).get_size(), (13, 13))
        self.assertEqual(sp.mini_nucleo(0).get_at((0, 0)).a, 0)
        self.assertEqual(sp.corazon(True, 3).get_size(), (27, 24))
        self.assertEqual(sp.blaster(True).get_size(), sp.blaster(False).get_size())
        self.assertEqual(len({sp.explosion(i).get_size() for i in range(6)}), 1)

    def test_destello_conserva_la_silueta(self):
        from interfaz import sprites_combate as sp
        golpe = sp.mini_nucleo(0, "golpe")
        self.assertEqual(golpe.get_at((0, 0)).a, 0)
        self.assertEqual(tuple(golpe.get_at((6, 6)))[:3], (255, 250, 245))


class Objetivo(unittest.TestCase):
    def test_prefiere_un_mini_alcanzable_al_mas_cercano_tras_pared(self):
        from interfaz.efectos_combate import elegir_objetivo
        cerca, lejos = dict(id=1, x=40, y=0), dict(id=2, x=120, y=0)
        mini, apuntable = elegir_objetivo([cerca, lejos], (0, 0), lambda a, b: b[0] != 40)
        self.assertEqual((mini["id"], apuntable), (2, True))

    def test_fuera_de_alcance_no_es_apuntable(self):
        from interfaz.efectos_combate import elegir_objetivo
        from multijugador.aventura_final import ALCANCE_BLASTER
        mini, apuntable = elegir_objetivo([dict(id=1, x=ALCANCE_BLASTER + 5, y=0)], (0, 0), lambda a, b: True)
        self.assertEqual((mini["id"], apuntable), (1, False))
        self.assertEqual(elegir_objetivo([], (0, 0), lambda a, b: True), (None, False))


class Sucesos(unittest.TestCase):
    def setUp(self):
        from interfaz.efectos_combate import EfectosCombate
        self.e = EfectosCombate()

    def test_disparo_nuevo_lanza_proyectil_y_luego_chispas(self):
        self.e.actualizar(final(), 1000)
        self.e.actualizar(final(disparo=[0, 0, 400, 300]), 1020)
        self.assertEqual(len(self.e.proyectiles), 1)
        self.e.actualizar(final(disparo=[0, 0, 400, 300]), 1200)
        self.assertEqual(self.e.proyectiles, [])
        self.assertTrue(self.e.chispas)

    def test_golpe_y_explosion_del_mini(self):
        self.e.actualizar(final(), 1000)
        self.e.actualizar(final(minis=[dict(id=1, x=400, y=300, vida=1, aviso=2)], disparo=[0, 0, 400, 300]), 1050)
        self.assertTrue(self.e.recien_golpeado(1))
        self.e.actualizar(final(minis=[], disparo=[1, 0, 400, 300]), 1300)
        self.assertEqual(len(self.e.explosiones), 1)
        self.assertEqual(self.e.textos[0][3], "+1")

    def test_mini_que_desaparece_sin_disparo_no_explota(self):
        self.e.actualizar(final(minis=[dict(id=1, x=400, y=300, vida=1, aviso=2)]), 1000)
        self.e.actualizar(final(minis=[]), 3000)
        self.assertEqual(self.e.explosiones, [])

    def test_rayo_y_perdida_de_senal_hacen_temblar(self):
        self.e.actualizar(final("aviso", 3.0), 1000)
        self.assertEqual(self.e.aviso_total, 3.0)
        self.e.actualizar(final("rayo", .7), 1050)
        self.assertNotEqual(self.e.sacudida_hasta, 0)
        self.e.actualizar(final("rayo", .6, integridad=2), 1100)
        self.assertTrue(self.e.perdio_senal())
        self.assertEqual(self.e.desplazamiento(99999), (0, 0))

    def test_fuera_del_combate_se_reinicia(self):
        self.e.actualizar(final(), 1000)
        self.e.actualizar(dict(fase="preparacion"), 1100)
        self.assertEqual((self.e.minis, self.e.turno), ({}, None))


class Dibujo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((960, 720))

    def test_todas_las_fases_se_dibujan(self):
        from interfaz import batalla_cooperativa as b, equipo_rebelion as r
        from interfaz.efectos_combate import EfectosCombate
        from nucleo.recursos import cargar_fuente
        efectos, fuente = EfectosCombate(), cargar_fuente(16)
        jugadores = [dict(id=0, x=200, y=300, dimension="futuro", rol="guardian"),
                     dict(id=1, x=260, y=300, dimension="futuro", rol="habitante")]
        mundo, pantalla = pygame.Surface((960, 720)), pygame.Surface((960, 720))
        for t, estado in enumerate((final("aviso"), final("rayo", .5, disparo=[200, 300, 400, 300], derribados=[1]),
                                    final("recarga", 20, minis=[]), final("terminado", 0))):
            efectos.actualizar(estado, 1000 + t * 100, 0)
            r.dibujar(mundo, estado, jugadores, efectos, 1000 + t * 100, (estado["aventura"]["minis"] or [None])[0] and
                      (estado["aventura"]["minis"][0], True))
            b.dibujar_ataques(mundo, estado, jugadores, efectos, 1000 + t * 100)
            efectos.dibujar(mundo)
            b.dibujar_aviso(pantalla, estado, fuente, jugadores[0], efectos, 1000 + t * 100)

    def test_sin_efectos_sigue_funcionando(self):
        from interfaz import batalla_cooperativa as b, equipo_rebelion as r
        from nucleo.recursos import cargar_fuente
        superficie = pygame.Surface((960, 720))
        r.dibujar(superficie, final(disparo=[0, 0, 400, 300]), [])
        b.dibujar_ataques(superficie, final(), [])
        b.dibujar_aviso(superficie, final(), cargar_fuente(16))


if __name__ == "__main__":
    unittest.main()
