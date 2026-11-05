import os
import unittest
import uuid

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

import test_campana_copa as campana_pruebas
from multijugador.movimiento import PartidaMovimiento
from interfaz.partida_multijugador import VistaPartida


class ClienteLocal:
    def __init__(self, p, i):
        self.p, self.i = p, i
        self.acciones = []

    def actuar(self, accion, **datos):
        resultado = self.p.actuar(self.i, dict(accion=accion, ronda=self.p.mision.ronda, id_solicitud=uuid.uuid4().hex, **datos), self.p.ultima)
        self.acciones.append((accion, resultado))

    def mover(self, *args):
        pass


class InterfazGuiadaTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.p = PartidaMovimiento([dict(id="0", nombre="Ana", rol="guardian"), dict(id="1", nombre="Leo", rol="habitante")], 0)
        self.h = campana_pruebas.CampanaTests()
        self.v = VistaPartida("0", {"mundo": self.p.estado("0")})
        self.c = ClienteLocal(self.p, "0")
        self.lienzo = pygame.Surface((960, 720))

    def tearDown(self):
        pygame.quit()

    def dibujar(self, modo):
        self.v.recibir({"mundo": self.p.estado(self.v.identificador)})
        self.v.panel.abrir(modo)
        self.v.dibujar(self.lienzo, "PRUEBA")
        botones = list(self.v.panel.botones.values())
        for indice, a in enumerate(botones):
            for b in botones[indice+1:]:
                self.assertFalse(a.rect.colliderect(b.rect), (a.texto, b.texto))

    def pulsar(self, clave):
        b = self.v.panel.botones[clave]
        self.assertFalse(b.desactivado, b.texto)
        self.v.manejar_evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1), b.rect.center, self.c)
        self.assertTrue(self.c.acciones[-1][1]["ok"], self.c.acciones[-1])

    def test_bienvenida_inicia_tutorial_y_cambia_la_ruta_inmediatamente(self):
        self.dibujar("introduccion")
        self.v.actualizar(.016, self.c)
        self.pulsar("iniciar_tutorial")
        self.v.recibir({"mundo": self.p.estado("0")})
        self.v.actualizar(.016, self.c)
        self.assertFalse(self.v.panel.activo)
        self.assertEqual(self.v.destino_ruta, "caldero")
        self.assertEqual(self.p.mision.acompanante.tutoriales["0"]["estado"], "activo")

    def test_caldero_explica_bloqueo_y_boton_pide_pista_real(self):
        self.h.preparar(self.p)
        self.p.mision.conocidas["0"] = {"pista_guardian"}
        self.dibujar("caldero")
        self.assertIn("Te falta una pista", self.v.panel.falta_para_elegir())
        self.assertTrue(self.v.panel.botones["votar:corregir"].desactivado)
        self.pulsar("pedir_pista")
        self.assertEqual(self.p.mision.acompanante.pedidos["0"], "1")
        self.assertEqual(len(self.p.mision.conocidas["0"]), 1)

    def test_botones_de_actividad_necesitan_dos_personas(self):
        self.h.preparar(self.p)
        for i in self.p.jugadores:
            self.h.accion(self.p, i, "votar", opcion="corregir")
        e = self.p.mision.encargo
        for i in self.p.jugadores:
            self.h.fuente(self.p, i)
            self.h.accion(self.p, i, "recoger_suministro")
            self.p.jugadores[i].update(x=e.destino["x"], y=e.destino["y"])
            self.h.accion(self.p, i, "depositar")
        self.dibujar("actividad")
        self.assertTrue(self.v.panel.botones["trabajar"].desactivado)
        self.pulsar("sujetar")
        self.dibujar("actividad")
        self.assertTrue(self.v.panel.botones["trabajar"].desactivado)
        self.v = VistaPartida("1", {"mundo": self.p.estado("1")})
        self.c = ClienteLocal(self.p, "1")
        self.dibujar("actividad")
        self.pulsar("trabajar")
        self.assertEqual(e.progreso, 1)
