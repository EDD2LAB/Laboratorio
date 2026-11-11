"""Objetivos sin spoilers, votación legible y recursos visuales de respaldo."""
import os
from types import SimpleNamespace
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from interfaz.orientacion import (tarea_actual, objetivo_nucleo, aviso_analisis,
                                 datos_votacion, ArteOrientacion, OrientacionMapa)
from multijugador.presentacion import estado_votacion
from multijugador.movimiento import PartidaMovimiento


class VotacionClara(unittest.TestCase):
    def test_empate_y_pendientes_sin_publicar_elecciones(self):
        parcial = estado_votacion({"a": "verificar"}, {"a", "b"})
        self.assertEqual(parcial, {"empate": False, "faltan_votar": ["b"]})
        self.assertTrue(estado_votacion({"a": "verificar", "b": "reportar"}, {"a", "b"})["empate"])
        self.assertFalse(estado_votacion({"a": "verificar", "b": "verificar"}, {"a", "b"})["empate"])
        self.assertFalse(estado_votacion({}, set())["empate"])

    def test_las_tres_eras_exponen_estado_de_votos(self):
        p = PartidaMovimiento([dict(id="a", nombre="Ana", rol="guardian"), dict(id="b", nombre="Leo", rol="mensajero")], 0)
        for m in (p.mision, p.mision.presente, p.mision.futuro):
            m.votos = {"a": "verificar", "b": "reportar"}
            estado = m.publico({"a", "b"})
            self.assertTrue(estado["empate"])
            self.assertEqual(estado["faltan_votar"], [])
            del m.votos["b"]
            self.assertEqual(m.publico({"a", "b"})["faltan_votar"], ["b"])

    def test_muestra_el_nombre_de_quien_falta_y_como_salir_del_empate(self):
        jugadores = [dict(id="a", nombre="Ana"), dict(id="b", nombre="Leo")]
        self.assertIn("Leo", datos_votacion({"faltan_votar": ["b"]}, jugadores, "a"))
        self.assertIn("Te toca", datos_votacion({"faltan_votar": ["b"]}, jugadores, "b"))
        self.assertIn("cambien un voto", datos_votacion({"empate": True}, jugadores, "a"))


class SiguienteAccion(unittest.TestCase):
    def vista(self, contexto, dimension="presente", objetivo=None):
        return SimpleNamespace(dimension=dimension, interior=None,
                               estado={"mundo": {"caso": {}, "privado": {}}},
                               contexto=lambda: contexto, _objetivo_presente=lambda: objetivo,
                               _textos_objetivo=lambda *a: ("Sigue tu tarea", "Detalle"),
                               dimension_completa=lambda: bool(contexto.get("fin")),
                               rect_portal=lambda: pygame.Rect(400, 100, 60, 80))

    def test_analisis_pendiente_no_envia_a_la_pantalla_a_votar(self):
        contexto = {"pistas": 3, "total_pistas": 3, "analisis": {"minimo": 2, "halladas": [], "concluido": False}}
        vista = self.vista(contexto, objetivo={"id": "presente:pantalla"})
        tarea = tarea_actual(vista)
        self.assertIsNone(tarea["objetivo"])
        self.assertEqual(tarea["tecla"], "C")
        self.assertIn("2 marcas", tarea["titulo"])
        self.assertIn("2 marcas", aviso_analisis(contexto))
        from interfaz.partida_multijugador import VistaPartida
        self.assertIsNone(VistaPartida._destino_flecha(vista, pygame.Rect(0, 0, 960, 720)))
        contexto["analisis"].update(concluido=True)
        self.assertEqual(aviso_analisis(contexto), "")
        self.assertIsNotNone(tarea_actual(vista)["objetivo"])

    def test_puerta_y_persona_tienen_instrucciones_distintas(self):
        contexto = {"pistas": 0, "total_pistas": 3}
        puerta = {"id": "cafe", "nombre": "Café Digital", "puerta": True, "pista": "documento"}
        vista = self.vista(contexto, objetivo=puerta)
        self.assertEqual(tarea_actual(vista)["titulo"], "Entra a Café Digital")
        npc = {"id": "elias", "nombre": "Elías Vega", "pista": "documento", "interior": "cafe"}
        vista.interior = "cafe"
        vista._objetivo_presente = lambda: npc
        self.assertEqual(tarea_actual(vista)["titulo"], "Habla con Elías Vega")

    def test_futuro_guia_primero_conexiones_y_despues_la_llave_y_firma(self):
        objetivos = [dict(id="futuro:" + t, tarea=t, pista=t) for t in ("conexiones", "archivos", "llave", "cuentas")]
        objetivos.append({"id": "futuro:pantalla"})
        npcs = [dict(id=p, dimension="futuro", pista=p) for p in ("guia_de_firmas", "llave_supervision", "firma_representante")]
        contexto = {"objetivos": objetivos, "tareas": []}
        self.assertEqual(objetivo_nucleo(contexto, set(), npcs)["tarea"], "conexiones")
        contexto["tareas"] = ["conexiones", "archivos"]
        self.assertEqual(objetivo_nucleo(contexto, set(), npcs)["id"], "llave_supervision")
        self.assertEqual(objetivo_nucleo(contexto, {"llave_supervision"}, npcs)["tarea"], "llave")
        contexto["tareas"] += ["llave", "cuentas"]
        self.assertEqual(objetivo_nucleo(contexto, set(), npcs)["id"], "firma_representante")
        self.assertEqual(objetivo_nucleo(contexto, {"firma_representante"}, npcs)["id"], "futuro:pantalla")


class Indicadores(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)

    def test_respaldo_sin_imagenes_y_teclas_cargadas_una_vez(self):
        with mock.patch("interfaz.orientacion.cargar_imagen", return_value=None) as cargar:
            arte = ArteOrientacion()
            lienzo = pygame.Surface((960, 720))
            arte.tecla(lienzo, "E", (200, 200))
            numero = cargar.call_count
            arte.tecla(lienzo, "E", (200, 200))
            self.assertEqual(cargar.call_count, numero)
            for n in ("check", "exclamacion", "interrogacion"):
                arte.indicador(lienzo, n, (300, 300))

    def test_check_solo_tras_conseguir_la_pista_del_objetivo(self):
        vista = SimpleNamespace(panel=SimpleNamespace(activo=False), mostrar_hud=True,
                                dimension="presente", interior=None, estado={"mundo": {"caso": {"npcs": []}}},
                                contexto=lambda: {"evento": {"id": "caso1"}},
                                a_pantalla=lambda x,y: (x,y), candidatos=lambda: [])
        objetivo = {"id": "persona", "x": 400, "y": 300}
        tarea = {"logro": "pista", "objetivo": objetivo, "tecla": "E"}
        lienzo = pygame.Surface((960, 720))
        with mock.patch("interfaz.orientacion.tarea_actual", return_value=tarea), mock.patch("interfaz.orientacion.logros_actuales", return_value=set()) as logros:
            mapa = OrientacionMapa()
            mapa.dibujar(vista, lienzo)
            self.assertIsNone(mapa.celebracion)
            logros.return_value = {"pista"}
            mapa.dibujar(vista, lienzo)
            self.assertIsNotNone(mapa.celebracion)
            vista.dimension = "futuro"
            mapa.dibujar(vista, lienzo)
            self.assertIsNone(mapa.celebracion)
