"""Ocho casos legibles y animaciones fieles a inserciones simples y dobles."""
import os
import unittest
from types import SimpleNamespace
from copy import deepcopy

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from logica.expediente_avl import Caso, ExpedienteAVL
from multijugador.expediente import ExpedientePartida
from multijugador.presente import EVENTOS
from multijugador.campana import CASOS
from multijugador.nucleo import CASO
from interfaz.arbol_expediente import AnimacionAVL, forma_publica, posiciones, etiqueta_decision
from interfaz.cooperativo import PanelCooperativo
from interfaz import expediente


def ocho_casos():
    e = ExpedientePartida()
    for evento in [c[0] for c in CASOS] + [c["id"] for c in EVENTOS] + [CASO]:
        e.registrar(evento, "Caso " + evento,
                    dict(evento_id=evento, opcion="verificar" if evento.startswith(("presente_", "nucleo_")) else "corregir"),
                    [dict(titulo="Documento completo", texto="Explicación de la prueba. " * 100 + "FIN DE LA PRUEBA")])
        while e.pendientes:
            estado = e.publico()
            ruta = e.arbol.ruta_insercion(e.pendientes[0])
            e.paso_insercion(dict(caso=e.pendientes[0].id, revision=e.revision, paso=e.paso,
                                  direccion=ruta[e.paso]["direccion"]))
    return e


class ArbolAnimado(unittest.TestCase):
    def test_cuatro_tipos_de_rotacion_terminan_en_la_forma_real(self):
        for gravedades in ((3, 2, 1), (1, 2, 3), (3, 1, 2), (1, 3, 2)):
            arbol = ExpedienteAVL()
            for indice, gravedad in enumerate(gravedades):
                arbol.insertar(Caso(str(indice), "Caso", gravedad, indice, {}))
                self.assertEqual(arbol.animacion["pasos"][-1]["forma"], arbol.forma(arbol.raiz))
            self.assertEqual(len(arbol.animacion["pasos"]), 3 if gravedades in ((3, 1, 2), (1, 3, 2)) else 2)
            self.assertEqual([c.gravedad for c in arbol.inorden()], [1, 2, 3])

    def test_ocho_nodos_caben_sin_solaparse_ni_tocar_la_leyenda(self):
        estado = ocho_casos().publico()
        puntos = posiciones(forma_publica(estado["raiz"]))
        self.assertEqual(len(puntos), 8)
        rects = [pygame.Rect(round(x) - 22, round(y) - 22, 44, 44) for x, y in puntos.values()]
        for i, rect in enumerate(rects):
            self.assertTrue(pygame.Rect(40, 130, 425, 285).contains(rect))
            self.assertEqual(rect.collidelist(rects[i + 1:]), -1)

    def test_repetir_no_cambia_el_estado_ni_reenvia_acciones(self):
        estado = ocho_casos().publico()
        original = deepcopy(estado)
        animacion = AnimacionAVL()
        self.assertFalse(animacion.actualizar(estado, 100)[3])
        self.assertTrue(animacion.actualizar(estado, 100, repetir=True)[3])
        final, puntos, texto, activa = animacion.actualizar(estado, 10000)
        self.assertFalse(activa)
        self.assertEqual(final, forma_publica(estado["raiz"]))
        self.assertEqual(estado, original)

    def test_decision_del_futuro_no_usa_el_nombre_de_verificar_del_presente(self):
        caso = dict(id=CASO, datos=dict(resultado=dict(opcion="verificar")))
        contexto = dict(presente=dict(opciones=dict(verificar="Verificar publicación")))
        self.assertIn("NÚCLEO", etiqueta_decision(caso, contexto))
        caso["id"] = EVENTOS[0]["id"]
        self.assertEqual(etiqueta_decision(caso, contexto), "Verificar publicación")


class LibroLegible(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        e = ocho_casos()
        self.vista = SimpleNamespace(dimension="la_copa", mouse=(0, 0), estado=dict(mundo=dict(caso=dict(expediente=e.publico()))))
        self.panel = PanelCooperativo(self.vista)
        self.panel.modo = "expediente"
        self.lienzo = pygame.Surface((960, 720))

    def test_ficha_larga_se_puede_leer_hasta_el_final_sin_salir_del_panel(self):
        p = self.panel
        p.expediente_ver_pruebas = True
        p.dibujar(self.lienzo)
        self.assertGreater(p.expediente_scroll_max, 0)
        rueda = pygame.event.Event(pygame.MOUSEWHEEL, y=-1000)
        self.assertTrue(p.manejar(rueda, expediente.DETALLE.center, None))
        self.assertEqual(p.expediente_scroll, p.expediente_scroll_max)
        detalle = next(iter(expediente._casos(p.caso["expediente"]["raiz"]).values()))
        lineas, _ = expediente.lineas_detalle(p, detalle)
        self.assertIn("FIN DE LA PRUEBA", " ".join(t for t, _ in lineas[p.expediente_scroll:]))
        self.assertEqual(self.lienzo.get_clip(), self.lienzo.get_rect())
        rects = [b.rect for b in p.botones.values()]
        for i, rect in enumerate(rects):
            self.assertTrue(self.lienzo.get_rect().contains(rect))
            self.assertEqual(rect.collidelist(rects[i + 1:]), -1)

    def test_ley_existente_no_se_modifica_y_hay_explicacion_infantil(self):
        caso = next(iter(expediente._casos(self.panel.caso["expediente"]["raiz"]).values()))
        antes = deepcopy(caso)
        lineas, _ = expediente.lineas_detalle(self.panel, caso)
        self.assertIn("Para recordar:", " ".join(t for t, _ in lineas))
        self.assertEqual(caso, antes)
