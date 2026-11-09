"""Informe final: datos del servidor, exportación y pantallas."""
import os
import tempfile
import unittest
import uuid
from datetime import datetime
from pathlib import Path
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from multijugador.movimiento import PartidaMovimiento  # noqa: E402
from multijugador.protocolo import ROLES  # noqa: E402


def partida():
    return PartidaMovimiento([dict(id=str(i), nombre="J" + str(i), rol=ROLES[i]) for i in range(2)], 0)


def resolver_copa(p):
    caso = p.mision.casos[0]
    p.mision.expediente.registrar(caso[0], caso[1], dict(opcion="corregir", correcto=True, evento_id=1), [])


def resolver_nucleo(p):
    p.mision.expediente.registrar("nucleo_control", "NÚCLEO", dict(opcion="verificar", correcto=True, evento_id=2), [])


def accion(p, nombre, **datos):
    return p.actuar("0", dict(accion=nombre, id_solicitud=uuid.uuid4().hex, ronda=p.mision.ronda, **datos), p.ultima)


class Datos(unittest.TestCase):
    def test_lista_las_tres_eras_y_los_pendientes_como_sin_resolver(self):
        p = partida()
        resolver_copa(p)
        informe = p.mision.informe()
        self.assertEqual({f["era"] for f in informe["casos"]}, {"La Copa", "Distrito Conecta", "Ciudad Núcleo"})
        self.assertEqual(len(informe["casos"]), 8)
        self.assertEqual(sum(f["resuelto"] for f in informe["casos"]), 1)

    def test_ordena_de_menor_a_mayor_gravedad(self):
        p = partida()
        resolver_copa(p)
        resolver_nucleo(p)
        gravedades = [f["gravedad"] for f in p.mision.informe()["casos"]]
        self.assertEqual(gravedades, sorted(gravedades))

    def test_inorden_coincide_con_el_arbol_avl_compartido(self):
        p = partida()
        resolver_copa(p)
        informe = p.mision.informe()
        self.assertEqual(informe["inorden"], [p.mision.casos[0][0]])
        self.assertEqual(informe["total_arbol"], 1)

    def test_se_pide_por_la_misma_ruta_de_acciones(self):
        p = partida()
        acuse = accion(p, "pedir_informe")
        self.assertTrue(acuse["ok"])
        self.assertEqual(acuse["vista"], "informe")
        self.assertEqual(len(acuse["informe"]["casos"]), 8)


class Exportacion(unittest.TestCase):
    def filas(self, **extra):
        return {"casos": [dict(id="a", titulo="Caso A", era="La Copa", tipo="Rumor", gravedad=2, resuelto=True, orden=0,
                               decision="Corregir", correcto=True, norma=None, pena=None, **extra),
                          dict(id="b", titulo="Caso B", era="Ciudad Núcleo", tipo="Control", gravedad=9, resuelto=False, orden=1,
                               decision=None, correcto=False, norma=None, pena=None)]}

    def test_exporta_con_fecha_en_el_nombre_y_sin_resolver(self):
        from interfaz.informe_final import CIERRE, exportar
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = exportar(self.filas(), Path(carpeta), datetime(2026, 11, 9, 10, 30, 5))
            self.assertEqual(ruta.name, "informe_2026-11-09_103005.txt")
            texto = ruta.read_text(encoding="utf-8")
        self.assertIn("Caso A", texto)
        self.assertIn("sin resolver", texto)
        self.assertIn(CIERRE, texto)

    def test_sin_norma_ni_pena_no_deja_lineas(self):
        from interfaz.informe_final import lineas_reporte
        self.assertEqual([t for t, _ in lineas_reporte(self.filas()["casos"][0])], ["titulo", "datos"])

    def test_si_trae_norma_y_pena_las_muestra(self):
        from interfaz.informe_final import lineas_reporte
        fila = dict(self.filas()["casos"][0], norma="Art. 1", pena="Multa")
        self.assertEqual([t for t, _ in lineas_reporte(fila)], ["titulo", "datos", "ley", "sancion"])


class Desplazamiento(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        from interfaz.partida_multijugador import VistaPartida
        from multijugador.expediente import ficha_resuelta
        p = partida()
        for orden, caso in enumerate(("puente_norte", "agua", "tormenta", "ayuda", "presente_video", "presente_voz", "presente_foto", "nucleo_control")):
            p.mision.expediente.registrar(caso, "Caso " + caso, dict(opcion="corregir", correcto=True, evento_id=orden), [], ficha_resuelta(caso, "descartar"))
        self.v = VistaPartida("0", {"mundo": p.estado("0")})
        self.panel = self.v.panel
        self.panel.recibir(accion(p, "pedir_informe"))
        self.lienzo = pygame.Surface((960, 720))
        self.panel.dibujar(self.lienzo)

    def evento(self, tipo, **datos):
        return self.panel.manejar(pygame.event.Event(tipo, **datos), datos.get("pos", (0, 0)), mock.Mock())

    def test_el_informe_largo_tiene_barra_y_la_rueda_llega_hasta_el_final(self):
        from interfaz.informe_final import maximo_desplazamiento, rect_pulgar
        self.assertGreater(maximo_desplazamiento(self.panel), 0)
        self.assertEqual(rect_pulgar(self.panel).y, 168)
        for _ in range(200):
            self.assertTrue(self.evento(pygame.MOUSEWHEEL, y=-1))
        self.assertEqual(self.panel.informe_scroll, maximo_desplazamiento(self.panel))
        self.assertEqual(rect_pulgar(self.panel).bottom, 554)
        self.evento(pygame.MOUSEWHEEL, y=1)
        self.assertLess(self.panel.informe_scroll, maximo_desplazamiento(self.panel))

    def test_se_arrastra_la_barrita(self):
        from interfaz.informe_final import maximo_desplazamiento, rect_pulgar
        pulgar = rect_pulgar(self.panel)
        self.assertTrue(self.evento(pygame.MOUSEBUTTONDOWN, button=1, pos=pulgar.center))
        self.assertTrue(self.evento(pygame.MOUSEMOTION, pos=(879, 700), rel=(0, 0), buttons=(1, 0, 0)))
        self.assertEqual(self.panel.informe_scroll, maximo_desplazamiento(self.panel))
        self.assertTrue(self.evento(pygame.MOUSEBUTTONUP, button=1, pos=(879, 700)))
        self.assertIsNone(self.panel.informe_arrastre)
        self.assertFalse(self.evento(pygame.MOUSEMOTION, pos=(879, 200), rel=(0, 0), buttons=(0, 0, 0)))
        self.assertEqual(self.panel.informe_scroll, maximo_desplazamiento(self.panel))

    def test_las_teclas_tambien_desplazan(self):
        self.evento(pygame.KEYDOWN, key=pygame.K_END)
        self.assertGreater(self.panel.informe_scroll, 0)
        self.evento(pygame.KEYDOWN, key=pygame.K_HOME)
        self.assertEqual(self.panel.informe_scroll, 0)

    def test_el_texto_no_se_sale_del_area_lisa_del_pergamino(self):
        from interfaz.informe_final import PERGAMINO, TEXTO_REPORTE
        limpio = pygame.Surface((960, 720))
        limpio.blit(self.panel.arte_informe.pergamino, PERGAMINO)
        for scroll in (0, 150, 10 ** 6):
            self.panel.informe_scroll = scroll
            self.panel.dibujar(self.lienzo)
            for y in (TEXTO_REPORTE.top - 1, TEXTO_REPORTE.bottom):
                for x in range(TEXTO_REPORTE.left, TEXTO_REPORTE.right, 3):
                    self.assertEqual(self.lienzo.get_at((x, y)), limpio.get_at((x, y)), (x, y, scroll))

    def test_el_texto_se_renderiza_una_sola_vez(self):
        arte = self.panel.arte_informe
        imagen = arte.reporte
        self.panel.informe_scroll = 90
        self.panel.dibujar(self.lienzo)
        self.assertIs(arte.reporte, imagen)

    def test_un_informe_nuevo_vuelve_arriba_y_cerrar_sigue_funcionando(self):
        self.evento(pygame.KEYDOWN, key=pygame.K_END)
        self.panel.recibir({"ok": True, "vista": "informe", "informe": dict(self.panel.informe)})
        self.assertEqual(self.panel.informe_scroll, 0)
        self.panel.dibujar(self.lienzo)
        centro = self.panel.botones["informe_cerrar"].rect.center
        self.evento(pygame.MOUSEBUTTONDOWN, button=1, pos=centro)
        self.assertIsNone(self.panel.modo)


class Pantalla(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)

    def test_recorrido_a_seis_decimas_por_nodo(self):
        from interfaz.informe_final import nodos_visitados
        self.assertEqual([nodos_visitados(t, 3) for t in (0, .59, .6, 1.2, 9)], [1, 1, 2, 3, 3])

    def test_se_dibuja_y_el_boton_exporta(self):
        from interfaz.partida_multijugador import VistaPartida
        p = partida()
        resolver_copa(p)
        vista = VistaPartida("0", {"mundo": p.estado("0")})
        vista.panel.recibir(accion(p, "pedir_informe"))
        self.assertEqual(vista.panel.modo, "informe")
        vista.panel.dibujar(pygame.Surface((960, 720)))
        self.assertLessEqual({"informe_exportar", "informe_cerrar"}, set(vista.panel.botones))
        with mock.patch("interfaz.informe_final.CARPETA", Path(tempfile.mkdtemp())):
            centro = vista.panel.botones["informe_exportar"].rect.center
            vista.panel.manejar(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=centro), centro, mock.Mock())
        self.assertTrue(vista.panel.informe_exportado.endswith(".txt"))

    def test_resolver_nucleo_programa_el_informe(self):
        from interfaz.partida_multijugador import VistaPartida
        p = partida()
        vista = VistaPartida("0", {"mundo": p.estado("0")})
        vista.estado["mundo"]["caso"]["futuro"] = {"fin": True, "resultado": {"evento_id": 9}}
        vista.dimension = "futuro"
        vista.panel.actualizar()
        self.assertIsNotNone(vista.panel.pedir_informe_en)
        vista.panel.pedir_informe_en = 0
        cliente = mock.Mock()
        vista.actualizar(.01, cliente)
        cliente.actuar.assert_any_call("pedir_informe")


class Ayuda(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)

    def test_pestana_del_arbol_avl(self):
        from interfaz.inicio import MenuInicio
        menu = MenuInicio()
        menu.pausa.abrir("ayuda_f1")
        menu.pausa.pestana_ayuda = "avl"
        menu.pausa.dibujar()
        self.assertIn("pausa:pestana:avl", menu.botones)


if __name__ == "__main__":
    unittest.main()
