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


class Sonidos(unittest.TestCase):
    def setUp(self):
        from interfaz.efectos_combate import EfectosCombate
        self.e = EfectosCombate()

    def nombres(self):
        return [n for n, _ in self.e.tomar_sonidos()]

    def test_cada_suceso_suena_una_vez(self):
        self.e.actualizar(final("recarga", 20), 1000)
        self.e.tomar_sonidos()
        self.e.actualizar(final("aviso", 3.0), 1100)
        self.assertEqual(self.nombres(), ["rayo_aviso"])
        self.e.actualizar(final("rayo", .7), 1200)
        self.assertEqual(self.nombres(), ["rayo_impacto"])
        self.e.actualizar(final("rayo", .6), 1300)
        self.assertEqual(self.nombres(), [])

    def test_disparo_propio_mas_fuerte_que_ajeno(self):
        self.e.actualizar(final(), 1000, 0, (0, 0))
        self.e.tomar_sonidos()
        self.e.actualizar(final(disparo=[0, 0, 400, 300]), 1100, 0, (0, 0))
        self.e.actualizar(final(disparo=[200, 0, 400, 300]), 1300, 0, (0, 0))
        sonidos = self.e.tomar_sonidos()
        self.assertEqual([n for n, _ in sonidos], ["blaster_disparo", "blaster_disparo"])
        self.assertGreater(sonidos[0][1], sonidos[1][1])

    def test_golpe_explosion_senal_y_caidos(self):
        self.e.actualizar(final(), 1000, 0)
        self.e.tomar_sonidos()
        self.e.actualizar(final(minis=[dict(id=1, x=400, y=300, vida=1, aviso=2)], disparo=[0, 0, 400, 300],
                                integridad=2, derribados=[0]), 1100, 0)
        self.assertTrue({"mini_golpe", "senal_perdida", "derribado"} <= set(self.nombres()))
        self.e.actualizar(final(minis=[], disparo=[1, 0, 400, 300], integridad=2), 1300, 0)
        self.assertTrue({"mini_explosion", "levantado"} <= set(self.nombres()))

    def test_repeticiones_juntas_se_funden(self):
        self.e.actualizar(final(), 1000)
        self.e.tomar_sonidos()
        self.e.sonar("mini_golpe", .5)
        self.e.sonar("mini_golpe", .5)
        self.assertEqual(self.e.tomar_sonidos(), [("mini_golpe", .65)])

    def test_cambio_de_fase_y_preparacion(self):
        def preparacion(cargas=0, fabricado=False):
            return dict(fase="preparacion", aventura=dict(cargas={i: "x" for i in range(cargas)},
                                                          entregadas=[], fabricado=fabricado))
        self.e.actualizar(preparacion(), 1000)
        self.e.actualizar(preparacion(1), 1100)
        self.assertEqual(self.nombres(), ["recoger_material"])
        self.e.actualizar(preparacion(0, True), 1200)
        self.assertEqual(self.nombres(), ["fabricar"])
        rojo = final()
        self.e.actualizar(rojo, 1300)
        self.e.tomar_sonidos()
        rojo["batalla"]["fase"] = 2
        self.e.actualizar(rojo, 1400)
        self.assertIn("cambio_fase", self.nombres())


class Sintesis(unittest.TestCase):
    def test_genera_wav_validos_sin_pisar_los_existentes(self):
        import tempfile
        import wave
        from pathlib import Path
        from herramientas.sintetizar_sonidos_batalla import generar
        from audio.audio_manager import GestorAudio
        with tempfile.TemporaryDirectory() as carpeta:
            carpeta = Path(carpeta)
            (carpeta / "rayo_aviso.wav").write_bytes(b"propio")
            creados = generar(carpeta)
            self.assertEqual(set(creados) | {"rayo_aviso"}, set(GestorAudio.SONIDOS_BATALLA))
            self.assertEqual((carpeta / "rayo_aviso.wav").read_bytes(), b"propio")
            for nombre in creados:
                with wave.open(str(carpeta / f"{nombre}.wav")) as archivo:
                    self.assertEqual((archivo.getnchannels(), archivo.getsampwidth()), (1, 2))
                    self.assertLess(archivo.getnframes() / archivo.getframerate(), 1.5)

    def test_los_sonidos_del_repositorio_estan_registrados(self):
        from audio.audio_manager import GestorAudio
        for nombre in GestorAudio.SONIDOS_BATALLA:
            self.assertTrue((RAIZ / "Audios" / "Batalla" / f"{nombre}.wav").is_file(), nombre)
        audio = GestorAudio(str(RAIZ), categorias=True)
        self.assertIn("batalla_rayo_impacto", audio.rutas_efectos)
        audio.reproducir_batalla("rayo_impacto", .5)  # sin mezclador real no debe fallar
        self.assertFalse(audio.reproducir_batalla("no_existe"))


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
