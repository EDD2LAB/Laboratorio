"""Snapshot de las tres eras completas: conserva pruebas sin duplicar leyes."""
import json
import unittest

from test_features_portadas import Ayuda, crear
from multijugador.presente import MARCAS
from multijugador.nucleo import TERMINALES, FIRMA, GUIA_FIRMAS, LLAVE
from multijugador.protocolo import codificar, MAX_MENSAJE


def ocho_resueltos():
    ayuda, p = Ayuda(), crear(4, mapa_real=True)
    for ronda, caso in enumerate(p.mision.casos):
        ayuda.preparar(p)
        for i in p.jugadores:
            ayuda.accion(p, i, "votar", opcion=caso[3])
        if ronda < 3:
            ayuda.avanzar(p)
    p._viajar_equipo("la_copa", "presente")
    m = p.mision.presente
    for numero in range(3):
        m.halladas = {pi[0]: "0" for pi in m.evento["pistas"]}
        m.marcas = {ma["id"]: "0" for ma in MARCAS[m.evento["marcas"]]["marcas"]}
        m.conclusion_id = 123
        m.votos = {i: "verificar" for i in p.jugadores}
        m.resolver(set(p.jugadores))
        if numero < 2:
            m.listos = set(p.jugadores)
            m.resolver(set(p.jugadores))
    p._viajar_equipo("presente", "futuro")
    m = p.mision.futuro
    m.tareas = {t[0]: "0" for t in TERMINALES}
    m.halladas = {FIRMA: "0", GUIA_FIRMAS: "0", LLAVE: "0"}
    m.votos = {i: "verificar" for i in p.jugadores}
    m.resolver(set(p.jugadores))
    e = p.mision.expediente
    while e.pendientes:
        ruta = e.arbol.ruta_insercion(e.pendientes[0])
        e.paso_insercion(dict(caso=e.pendientes[0].id, revision=e.revision, paso=e.paso, direccion=ruta[e.paso]["direccion"]))
    return p


class CapacidadFinal(unittest.TestCase):
    def test_ocho_fichas_y_final_caben_para_los_cuatro_roles(self):
        p = ocho_resueltos()
        self.assertEqual(len(p.mision.expediente.arbol.casos), 8)
        for caso in p.mision.expediente.arbol.casos.values():
            self.assertTrue(caso.datos["pruebas"], caso.id)
            self.assertIn("ley", caso.datos)
            self.assertNotIn("norma", caso.datos["resultado"])
        for fase in ("preparacion", "activo", "victoria"):
            final = p.mision.futuro.final
            final.fase = fase
            final.hechos.update(("guardian", "habitante", "mensajero", "aspirante"))
            final.activaciones = set(p.jugadores)
            final.batalla.fase = 2
            final.batalla.blancos = [[j["x"], j["y"]] for j in p.jugadores.values()]
            final.batalla.derribados = set(p.jugadores)
            for i in p.jugadores:
                mensaje = dict(tipo="estado", fase="partida", revision=99999, mundo=p.estado(i))
                # Identificadores LAN reales y nombres de 20 caracteres multibyte.
                mundo = json.dumps(mensaje, ensure_ascii=False)
                for numero in range(4):
                    mundo = mundo.replace('"' + str(numero) + '"', '"' + str(numero) * 16 + '"')
                    mundo = mundo.replace('"J' + str(numero) + '"', '"' + 'ñ' * 20 + '"')
                tamano = len(codificar(json.loads(mundo)))
                self.assertLess(tamano, MAX_MENSAJE - 512, (fase, i, tamano))

    def test_ficha_completa_se_lee_sin_perder_pruebas_y_sin_revelar_casos_futuros(self):
        p = ocho_resueltos()
        e = p.mision.expediente
        for caso in e.arbol.casos.values():
            acuse = p.actuar("0", dict(accion="expediente_leer", caso=caso.id,
                                     id_solicitud=__import__("uuid").uuid4().hex), p.ultima)
            self.assertTrue(acuse["ok"])
            self.assertEqual(acuse["ficha"], caso.publico())
            self.assertLess(len(codificar(acuse)), MAX_MENSAJE)
        desconocido = p.actuar("0", dict(accion="expediente_leer", caso="caso_no_resuelto",
                               id_solicitud=__import__("uuid").uuid4().hex), p.ultima)
        self.assertFalse(desconocido["ok"])

    def test_interfaz_solicita_una_ficha_y_usa_la_cache_recibida(self):
        from types import SimpleNamespace
        from interfaz.expediente import solicitar_detalle, detalle_actual
        from interfaz.cooperativo import PanelCooperativo
        import pygame
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        p = ocho_resueltos()
        v = SimpleNamespace(estado=dict(mundo=p.estado("0")))
        panel = PanelCooperativo(v)
        panel.modo = "expediente"
        enviados = []
        cliente = SimpleNamespace(actuar=lambda tipo, **datos: enviados.append((tipo, datos)))
        solicitar_detalle(panel, cliente)
        solicitar_detalle(panel, cliente)
        self.assertEqual(len(enviados), 1)
        tipo, datos = enviados[0]
        acuse = p.actuar("0", dict(accion=tipo, id_solicitud=__import__("uuid").uuid4().hex, **datos), p.ultima)
        panel.recibir(acuse)
        self.assertFalse(detalle_actual(panel, panel.caso["expediente"]).get("detalle_remoto", False))
        solicitar_detalle(panel, cliente)
        self.assertEqual(len(enviados), 1)

