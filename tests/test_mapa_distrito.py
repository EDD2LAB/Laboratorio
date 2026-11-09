"""Distribución de Distrito Conecta en 3x3, personajes sin dobles y nota de voz."""
import os
import unittest
import uuid
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from logica.dimensiones import EDIFICIOS_PRESENTE  # noqa: E402
from multijugador.dimensiones_red import (FUTURO, INTERIORES, LA_COPA, PRESENTE, cargar_datos, edificios_de,  # noqa: E402
                                          rect_portal, spawn_presente)
from multijugador.movimiento import ColisionesMapa, PartidaMovimiento  # noqa: E402
from multijugador.presente import EVENTOS  # noqa: E402
from multijugador.protocolo import ROLES  # noqa: E402

# Columna y fila de la tabla: 0 izquierda/arriba, 1 centro, 2 derecha/abajo.
TABLA = {"centro_verificacion": (0, 0, "CentrodeVerifInt"), "estudio_influencer": (2, 0, "EstudioInfluencerInt"),
         "sede_aspirante": (0, 1, "SededelAspiranteInt"), "cafe_digital": (2, 1, "CaféDigitalInt"),
         "estacion_mensajero": (1, 2, "EstacionMensajeroInt")}


def partida(roles):
    p = PartidaMovimiento([dict(id=str(i), nombre="J" + str(i), rol=r) for i, r in enumerate(roles)], 0)
    p._viajar_equipo(LA_COPA, PRESENTE)
    p.actualizar(.05)
    return p


class Tabla(unittest.TestCase):
    def test_cada_edificio_usa_el_interior_de_su_nombre_y_su_lugar_en_la_tabla(self):
        datos = cargar_datos(PRESENTE)
        puertas = edificios_de(datos)
        self.assertEqual(set(puertas), set(TABLA))
        x0, y0, ancho, alto = datos["rect_mapa"]
        for edificio, (columna, fila, interior) in TABLA.items():
            self.assertEqual(INTERIORES[edificio], interior)
            self.assertIn(interior, EDIFICIOS_PRESENTE[edificio]["interior"])
            x, y = puertas[edificio]["x"], puertas[edificio]["y"]
            self.assertEqual((int((x - x0) * 3 / ancho), int((y - y0) * 3 / alto)), (columna, fila), edificio)

    def test_la_zona_residencial_no_tiene_interior(self):
        datos = cargar_datos(PRESENTE)
        for hitbox in datos["hitboxes"]:
            if hitbox.get("id") in ("entrada_centro_comunitario", "entrada_campana_ronaldo"):
                self.assertNotEqual(hitbox.get("action"), "entrar_edificio")

    def test_el_portal_esta_en_las_ruinas_en_el_centro_de_arriba(self):
        for dimension in (PRESENTE, FUTURO):
            datos = cargar_datos(dimension)
            x, y, w, h = rect_portal(dimension, datos)
            ruinas = next(g for g in datos["hitboxes"] if g.get("id") == "rotunda_plaza_norte")
            self.assertLess(abs(x + w / 2 - ruinas["cx"] * 960), 6)
            self.assertLess(abs(y + h / 2 - ruinas["cy"] * 720), 8)
            mapa = ColisionesMapa(datos)
            self.assertFalse(mapa.bloqueado(*spawn_presente(datos)))

    def test_las_pistas_estan_en_edificios_con_interior(self):
        for evento in EVENTOS:
            for _, _, edificio, _, _ in evento["pistas"]:
                self.assertIn(edificio, TABLA, evento["id"])


class SinDobles(unittest.TestCase):
    def test_en_el_presente_el_jugado_es_el_jugador(self):
        p = partida(ROLES)
        ronaldo = next(n for n in p.mision.dialogos.publico() if n["nombre"] == "Ronaldo Vélez")
        self.assertEqual(ronaldo["jugador"], "3")
        self.assertEqual(ronaldo["casa"]["interior"], "sede_aspirante")
        self.assertEqual(sum(n["nombre"] == "Mateo Ríos" for n in p.mision.dialogos.publico()), 0)

    def test_sin_jugador_espera_dentro_de_su_edificio(self):
        p = partida(("guardian",))
        tomas = next(n for n in p.mision.dialogos.publico() if n["nombre"] == "Tomás Red")
        self.assertEqual(tomas["interior"], "estacion_mensajero")
        self.assertNotIn("jugador", tomas)

    def test_en_el_futuro_el_personaje_jugado_no_tiene_doble(self):
        p = PartidaMovimiento([dict(id="0", nombre="A", rol="aspirante")], 0)
        p._viajar_equipo(LA_COPA, FUTURO)
        p.actualizar(.05)
        representante = next(n for n in p.mision.dialogos.publico() if n["nombre"] == "Representante Humano")
        self.assertEqual(representante["jugador"], "0")
        self.assertEqual((representante["x"], representante["y"]), (round(p.jugadores["0"]["x"]), round(p.jugadores["0"]["y"])))


class NotaDeVoz(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        from audio.audio_manager import GestorAudio
        from interfaz.partida_multijugador import VistaPartida
        from nucleo.rutas import RAIZ
        self.audio = GestorAudio(str(RAIZ), categorias=True)
        self.p = partida(("guardian",))
        self.p.mision.presente.indice = 1
        self.v = VistaPartida("0", {"mundo": self.p.estado("0")}, audio=self.audio)
        self.v._cargar_dimension(PRESENTE)
        self.v.dimension = PRESENTE
        self.ui = self.v.celular.ui

    def test_reproducir_ocupa_un_canal_aunque_esten_todos_llenos(self):
        sonido = self.ui.audios["original"].sonido
        for _ in range(8):
            sonido.play(-1)
        self.ui.reproducir("suplantado")
        self.assertIs(self.ui.canal_voz.get_sound(), self.ui.audios["suplantado"].sonido)

    def test_la_musica_vuelve_al_terminar(self):
        self.ui.reproducir("original")
        self.assertEqual(self.ui.sonando, "original")
        self.ui.inicio_audio -= 60000
        self.v.actualizar(.01, mock.Mock())
        self.assertIsNone(self.ui.sonando)

    def test_se_puede_escuchar_desde_la_publicacion(self):
        self.v.panel.modo = "introduccion"
        self.v.panel.dibujar(pygame.Surface((960, 720)))
        centro = self.v.panel.botones["analisis:reproducir:suplantado"].rect.center
        self.v.panel.manejar(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=centro), centro, mock.Mock())
        self.assertEqual(self.ui.sonando, "suplantado")


class Estudio(unittest.TestCase):
    def test_se_entra_por_abajo_y_lo_del_suelo_no_choca(self):
        from multijugador.dimensiones_red import cargar_interior, rect_salida, spawn_interior
        datos = cargar_interior("estudio_influencer")
        x0, y0, ancho, alto = datos["rect_mapa"]
        mapa = ColisionesMapa(datos)
        x, y = spawn_interior(datos)
        self.assertGreater((y - y0) / alto, .8)
        self.assertFalse(mapa.bloqueado(x, y))
        self.assertGreater((rect_salida(datos)[1] - y0) / alto, .8)
        self.assertFalse(mapa.bloqueado(x0 + .55 * ancho, y0 + .5 * alto))  # donde estaban la cámara y el trípode
        self.assertNotIn("tripodes_estudio", {h["id"] for h in datos["hitboxes"]})


class TarjetasDePistas(unittest.TestCase):
    def test_el_aviso_no_es_una_tarjeta_aparte_y_se_sabe_quien_la_tiene(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        from interfaz.partida_multijugador import VistaPartida
        p = PartidaMovimiento([dict(id="0", nombre="A", rol="guardian"), dict(id="1", nombre="B", rol="habitante")], 0)
        m = p.mision
        m.conocidas["0"].add("pista_guardian")
        m.conocidas["1"].add("pista_guardian")
        m.halladas["pista_guardian"] = "0"
        m.avisos_recientes["0"]["pista_guardian"] = {"texto": "Aviso de prueba", "vence": m.reloj + 90}
        v = VistaPartida("0", {"mundo": p.estado("0")})
        inventario = v.panel.inventario()
        self.assertEqual(len(inventario), 1)
        self.assertEqual(sorted(inventario[0]["la_tienen"]), ["0", "1"])
        self.assertTrue(inventario[0]["temporal"]["vigente"])
        v.panel.modo = "inventario"
        v.panel.dibujar(pygame.Surface((960, 720)))


if __name__ == "__main__":
    unittest.main()
