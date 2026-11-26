"""Prueba de humo de toda la campaña y propiedades del árbol AVL del expediente."""
import random
import unittest

from logica.expediente_avl import Caso, ExpedienteAVL


def _altura(nodo):
    return 0 if nodo is None else 1 + max(_altura(nodo.izquierda), _altura(nodo.derecha))


def _revisar(nodo, prueba):
    """Comprueba en cada nodo el balance AVL y la altura guardada (si la hay)."""
    if nodo is None:
        return
    izquierda, derecha = _altura(nodo.izquierda), _altura(nodo.derecha)
    prueba.assertLessEqual(abs(izquierda - derecha), 1)
    if hasattr(nodo, "altura"):
        prueba.assertEqual(nodo.altura, 1 + max(izquierda, derecha))
    _revisar(nodo.izquierda, prueba)
    _revisar(nodo.derecha, prueba)


class PropiedadesAVLTests(unittest.TestCase):
    def test_muchas_inserciones_quedan_balanceadas_y_en_orden(self):
        for semilla in range(3):
            azar = random.Random(semilla)
            arbol = ExpedienteAVL()
            claves = []
            for orden in range(300):
                gravedad = azar.randint(1, 5)
                arbol.insertar(Caso(f"c{semilla}_{orden}", "Caso", gravedad, orden, {}))
                claves.append((gravedad, orden))
            _revisar(arbol.raiz, self)
            self.assertEqual([(c.gravedad, c.orden) for c in arbol.inorden()], sorted(claves))
            # Cota de altura de un AVL: 1,44·log2(n + 2).
            self.assertLessEqual(_altura(arbol.raiz), 1.44 * (len(claves) + 2).bit_length())

    def test_claves_crecientes_y_decrecientes(self):
        for gravedades in (range(1, 6), range(5, 0, -1)):
            arbol = ExpedienteAVL()
            for orden in range(120):
                arbol.insertar(Caso(f"c{orden}", "Caso", list(gravedades)[orden % 5], orden, {}))
            _revisar(arbol.raiz, self)
            claves = [(c.gravedad, c.orden) for c in arbol.inorden()]
            self.assertEqual(claves, sorted(claves))


class CampanaCompletaConBotsTests(unittest.TestCase):
    def test_cuatro_bots_llegan_al_informe_final_con_el_arbol_completo(self):
        from herramientas.partida_bots import jugar
        resultado = jugar(semilla=1)
        self.assertTrue(resultado["completa"], resultado)
        for hito in ("la_copa", "distrito_conecta", "ciudad_nucleo", "victoria", "informe"):
            self.assertIn(hito, resultado["hitos_s_simulados"])
        self.assertEqual((resultado["arbol_avl"], resultado["pendientes_avl"]), (6, 0))


if __name__ == "__main__":
    unittest.main()
