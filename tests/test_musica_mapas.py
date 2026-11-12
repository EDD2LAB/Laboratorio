"""Pistas reales por era, transiciones del combate y continuidad de reproducción."""
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from audio.musica_mapas import pista_actual

RAIZ = Path(__file__).resolve().parents[1]


class SeleccionMusical(unittest.TestCase):
    def test_cada_era_tiene_su_pista(self):
        for dimension, pista in (("la_copa", "ambiente"), ("presente", "musica_presente"), ("futuro", "musica_nucleo")):
            self.assertEqual(pista_actual(dimension, {}, {}), pista)

    def test_batalla_cambia_con_las_fases_y_el_reintento_vuelve_a_la_ciudad(self):
        for fase in (1, 2):
            contexto = {"desafio_final": {"fase": "activo", "batalla": {"fase": fase}}}
            self.assertEqual(pista_actual("futuro", contexto, {}), "batalla_fase" + str(fase))
        for fase in ("preparacion", "reintento", "victoria"):
            self.assertEqual(pista_actual("futuro", {"desafio_final": {"fase": fase}}, {}), "musica_nucleo")

    def test_epilogos_suenan_como_la_era_que_se_muestra(self):
        for indice, pista in enumerate(("musica_nucleo", "musica_presente", "ambiente")):
            contexto = {"desafio_final": {"fase": "victoria", "aventura": {"cierre": {"etapa": "epilogo", "indice": indice}}}}
            self.assertEqual(pista_actual("futuro", contexto, {}), pista)

    def test_creditos_conservan_la_musica_del_resultado(self):
        indicadores = dict(sabiduria=70, confianza=70, armonia=70)
        for etapa in ("pantalla", "creditos"):
            contexto = {"desafio_final": {"aventura": {"cierre": {"etapa": etapa}}}}
            self.assertEqual(pista_actual("futuro", contexto, indicadores), "victoria")
            self.assertEqual(pista_actual("futuro", contexto, {}), "game_over")

    def test_vista_usa_la_pista_de_su_estado(self):
        from interfaz.partida_multijugador import VistaPartida
        v = SimpleNamespace(audio=Mock(), dimension="presente", estado={"mundo": {"caso": {}}}, contexto=lambda: {})
        VistaPartida.sonido_musica(v)
        v.audio.reproducir_musica.assert_called_once_with("musica_presente", en_bucle=True)

    def test_llegar_un_estado_nuevo_cambia_la_pista_sin_viajar(self):
        from interfaz.partida_multijugador import VistaPartida
        from multijugador.movimiento import PartidaMovimiento
        pygame.init()
        pygame.display.set_mode((960,720))
        self.addCleanup(pygame.quit)
        p = PartidaMovimiento([dict(id="a", nombre="Ana", rol="guardian")], 0)
        p._viajar_equipo("la_copa", "futuro")
        audio = Mock()
        v = VistaPartida("a", {"mundo": p.estado("a")}, audio=audio)
        f = p.mision.futuro.final
        f.preparar(100)
        f.fase = "activo"
        for fase in (1,2):
            f.batalla.fase = fase
            v.recibir({"mundo": p.estado("a")})
            audio.reproducir_musica.assert_called_with("batalla_fase" + str(fase), en_bucle=True)
        f.fase = "reintento"
        v.recibir({"mundo": p.estado("a")})
        audio.reproducir_musica.assert_called_with("musica_nucleo", en_bucle=True)


class ArchivosYReproduccion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from audio.audio_manager import GestorAudio
        pygame.init()
        cls.audio = GestorAudio(str(RAIZ), categorias=True)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_las_cuatro_pistas_del_repo_se_decodifican(self):
        for nombre in ("musica_presente", "musica_nucleo", "batalla_fase1", "batalla_fase2"):
            self.assertEqual(Path(self.audio.rutas_musica[nombre]).name, nombre + ".mp3")
            self.assertIsNotNone(self.audio.musicas[nombre])
            self.assertGreater(self.audio.musicas[nombre].get_length(), 0)

    def test_actualizar_el_estado_no_reinicia_la_misma_cancion(self):
        self.audio.reproducir_musica("musica_presente", en_bucle=True)
        canal = self.audio._canal_musica_actual
        with patch.object(self.audio, "_canales_musica", [Mock(), Mock()]):
            self.assertTrue(self.audio.reproducir_musica("musica_presente", en_bucle=True))
        self.assertIs(self.audio._canal_musica_actual, canal)
