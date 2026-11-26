"""Revisión para la feria: la primera ruta de cada bot ya no congela la partida.

La memoria fija de colisiones y la de aristas del A* se comparten entre
instancias del mismo mapa, y el precalentado las llena con los mismos valores
que calcularía el bot.
"""
import time
import unittest

from bots.navegador_bot import NavegadorBot
from logica import zonas_caminables
from multijugador import movimiento
from multijugador.dimensiones_red import PRESENTE, cargar_datos, spawn_presente
from multijugador.movimiento import ColisionesMapa


def _olvidar():
    movimiento._MEMORIAS_FIJAS.clear()
    movimiento._MEMORIAS_ARISTAS.clear()
    zonas_caminables._CALENTADOS.clear()


class MemoriaCompartidaTests(unittest.TestCase):
    def setUp(self):
        _olvidar()

    def test_instancias_del_mismo_mapa_comparten_memoria(self):
        a, b = ColisionesMapa(), ColisionesMapa()
        a.bloqueado(500, 400)
        self.assertIs(a._memoria, b._memoria)
        self.assertIn((500, 400), b._memoria)
        otro = ColisionesMapa(cargar_datos(PRESENTE))
        self.assertIsNot(otro._memoria, a._memoria)

    def test_aristas_separadas_por_estado_de_bloqueos(self):
        mapa = ColisionesMapa()
        sin_puente = mapa.memoria_aristas()
        mapa.bloqueos = [(237, 224, 170, 161)]
        con_puente = mapa.memoria_aristas()
        self.assertIsNot(sin_puente, con_puente)
        mapa.bloqueos = []
        self.assertIs(mapa.memoria_aristas(), sin_puente)


class CalentadoTests(unittest.TestCase):
    ORIGEN, DESTINO = (482, 232), (416, 584)

    def setUp(self):
        _olvidar()

    def tearDown(self):
        _olvidar()

    def _mapa(self):
        return ColisionesMapa(cargar_datos(PRESENTE))

    def test_la_ruta_es_identica_en_frio_y_precalentada(self):
        fria = NavegadorBot(self._mapa()).buscar_ruta(self.ORIGEN, self.DESTINO, 10)
        _olvidar()
        mapa = self._mapa()
        zonas_caminables.calentar_todo(mapa, mapa.inicio_libre(*spawn_presente(mapa.datos)))
        caliente = NavegadorBot(mapa).buscar_ruta(self.ORIGEN, self.DESTINO, 10)
        self.assertTrue(fria)
        self.assertEqual(fria, caliente)

    def test_precalentado_cubre_lo_que_consulta_el_bot(self):
        mapa = self._mapa()
        zonas_caminables.calentar_todo(mapa, mapa.inicio_libre(*spawn_presente(mapa.datos)))
        puntos, aristas = len(mapa._memoria), len(mapa.memoria_aristas())
        inicio = time.perf_counter()
        self.assertTrue(NavegadorBot(mapa).buscar_ruta(self.ORIGEN, self.DESTINO, 10))
        self.assertLess(time.perf_counter() - inicio, .25)  # en frío tardaba 0,6–1,4 s
        self.assertLessEqual(len(mapa._memoria) - puntos, 50)
        self.assertLessEqual(len(mapa.memoria_aristas()) - aristas, 50)

    def test_aristas_guardadas_coinciden_con_el_calculo_del_bot(self):
        mapa = ColisionesMapa()
        mapa.bloqueos = [(237, 224, 170, 161)]  # La Copa con el Puente 1 roto
        zonas_caminables.calentar_todo(mapa, mapa.inicio_libre(415, 390))
        guardadas = list(mapa.memoria_aristas().items())
        self.assertGreater(len(guardadas), 1000)
        for (a, b), libre in guardadas[::97]:
            self.assertEqual(libre, mapa.trayecto_libre((a[0] * 8, a[1] * 8), (b[0] * 8, b[1] * 8)), (a, b))

    def test_calentar_es_repartible_y_una_vez_por_proceso(self):
        mapa = self._mapa()
        origen = mapa.inicio_libre(*spawn_presente(mapa.datos))
        pasos = sum(1 for _ in zonas_caminables.calentar(mapa, origen))
        self.assertGreater(pasos, 100)  # cede el control nodo a nodo
        self.assertEqual(sum(1 for _ in zonas_caminables.calentar(mapa, origen)), 0)


class CampanaLocalCalentadaTests(unittest.TestCase):
    def test_la_campana_calienta_su_era_y_reparte_las_demas(self):
        _olvidar()
        from multijugador.partida_local import ClienteCampanaLocal
        cliente = ClienteCampanaLocal("Visitante", "guardian", semilla=3)
        copa = cliente._partida.colisiones
        self.assertTrue(any(c[0] == copa.firma for c in zonas_caminables._CALENTADOS))
        self.assertIsNotNone(cliente._calentado)
        inicio = time.perf_counter()
        cliente.calentar(.002)
        self.assertLess(time.perf_counter() - inicio, .05)
        while cliente._calentado is not None:
            cliente.calentar(.5)
        self.assertEqual(len(zonas_caminables._CALENTADOS), 3)


if __name__ == "__main__":
    unittest.main()
