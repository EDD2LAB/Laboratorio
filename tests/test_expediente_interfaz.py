import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from interfaz.cooperativo import PanelCooperativo
from multijugador.expediente import ExpedientePartida


class LibroInterfazTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((960, 720))

    def panel(self, expediente):
        caso = {"expediente": expediente.publico(), "opciones": {"corregir": "Publicar una aclaración"}}
        vista = SimpleNamespace(dimension="la_copa", mouse=(0, 0), estado={"mundo": {"caso": caso}})
        return PanelCooperativo(vista)

    def test_t_abre_y_cierra_libro_vacio_sin_bloquear_el_juego(self):
        panel = self.panel(ExpedientePartida())
        evento = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_t)
        panel.manejar(evento, (0, 0), None)
        self.assertEqual(panel.modo, "expediente")
        panel.dibujar(pygame.Surface((960, 720)))
        self.assertIn("expediente_cerrar", panel.botones)
        panel.manejar(evento, (0, 0), None)
        self.assertFalse(panel.activo)

    def test_botones_no_se_solapan_y_envian_revision_y_paso_del_servidor(self):
        e = ExpedientePartida()
        for evento in ("puente_norte", "agua"):
            e.registrar(evento, evento, {"evento_id": evento, "opcion": "corregir"}, [])
        panel = self.panel(e)
        panel.modo = "expediente"
        panel.dibujar(pygame.Surface((960, 720)))
        rects = [b.rect for b in panel.botones.values()]
        for i, rect in enumerate(rects):
            self.assertTrue(pygame.Rect(0, 0, 960, 720).contains(rect))
            self.assertEqual(rect.collidelist(rects[i + 1:]), -1)
        enviados = []
        cliente = SimpleNamespace(actuar=lambda accion, **datos: enviados.append((accion, datos)))
        clic = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1)
        panel.manejar(clic, panel.botones["expediente:derecha"].rect.center, cliente)
        self.assertEqual(enviados, [("expediente_paso", dict(caso="agua", revision=1, paso=0, direccion="derecha"))])
        panel.manejar(clic, panel.nodos_expediente["puente_norte"].center, cliente)
        self.assertEqual(panel.caso_expediente, "puente_norte")

    def test_aviso_temporal_se_muestra_sin_contar_como_segunda_prueba(self):
        panel = self.panel(ExpedientePartida())
        panel.vista.estado["mundo"]["privado"] = {"inventario": [
            {"id": "pista_guardian", "titulo": "Documento", "texto": "Prueba permanente",
             "temporal": {"texto": "Observación caducada", "segundos": 0, "vigente": False}}]}
        self.assertEqual(len(panel.inventario()), 1)  # el aviso va dentro de su pista
        self.assertEqual(panel.cantidad_pruebas(), 1)
        self.assertFalse(panel.inventario()[0]["temporal"]["vigente"])
