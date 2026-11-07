import time
import unittest

import test_campana_copa as campana_pruebas
from multijugador.movimiento import PartidaMovimiento
from interfaz.guia import buscar_camino


class GuiaInfantilTests(unittest.TestCase):
    def setUp(self):
        self.h = campana_pruebas.CampanaTests()
        self.p = self.h.crear(("guardian", "habitante"))

    def a(self, i, accion, **datos):
        return self.h.accion(self.p, i, accion, **datos)

    def test_tutorial_ensena_movimiento_saludo_y_entrega_sin_repetir(self):
        self.assertTrue(self.a("0", "iniciar_tutorial")["ok"])
        self.assertEqual(self.p.mision.privado("0")["guia"]["titulo"], "Camina con las flechas")
        self.a("0", "interactuar", objetivo="caldero")
        self.assertEqual(self.p.mision.acompanante.tutoriales["0"]["paso"], 0)
        self.p.jugadores["0"].update(x=480, y=380)
        self.p.actualizar(1)
        self.assertTrue(self.a("0", "interactuar", objetivo="caldero")["ok"])
        self.assertIn("0", self.p.mision.publico(self.p.conectados)["tutorial_cargas"])
        eco = next(o for o in self.p.mision.objetivos if o.get("rol") == "mensajero")
        self.p.jugadores["0"].update(x=eco["x"], y=eco["y"])
        self.assertTrue(self.a("0", "interactuar", objetivo=eco["id"])["ok"])
        self.assertEqual(self.p.mision.privado("0")["tutorial"]["estado"], "terminado")
        self.assertNotIn("0", self.p.mision.publico(self.p.conectados)["tutorial_cargas"])
        self.assertFalse(self.a("0", "iniciar_tutorial")["ok"])
        self.assertEqual(self.p.mision.privado("0")["guia"]["paso"], "buscar")

    def test_pedir_una_pista_notifica_sin_entregarla_ni_revelarla(self):
        self.h.preparar(self.p)
        self.p.mision.conocidas["0"] = {"pista_guardian"}
        antes = set(self.p.mision.conocidas["0"])
        self.assertTrue(self.a("0", "pedir_pista")["ok"])
        self.assertEqual(self.p.mision.conocidas["0"], antes)
        self.assertEqual(self.p.mision.privado("1")["pedidos"], [{"id": "0", "nombre": "0"}])
        self.assertEqual(self.p.mision.privado("1")["guia"]["paso"], "compartir")
        self.assertFalse(self.a("0", "pedir_pista")["ok"])
        self.a("1", "entregar", pista="pista_habitante", destinatario="0", medio="directo")
        self.assertFalse(self.p.mision.privado("1")["pedidos"])
        self.assertEqual(self.p.mision.privado("0")["guia"]["paso"], "decidir")

    def test_primera_mision_sin_prisa_y_estrellas_sin_duplicados(self):
        for n in range(1, 190):
            self.p.actualizar(n)
        self.assertEqual(self.p.mision.indicadores["desinformacion"], 0)
        self.h.preparar(self.p)
        for i in self.p.jugadores:
            self.a(i, "votar", opcion="corregir")
        self.assertEqual(self.p.mision.publico(self.p.conectados)["estrellas"], 2)
        self.h.avanzar(self.p)
        self.assertEqual(self.p.mision.publico(self.p.conectados)["estrellas"], 3)
        for _ in range(61):
            self.p.actualizar(self.p.ultima+1)
        self.assertEqual(self.p.mision.oleadas, 1)

    def test_actividad_necesita_ayudante_distinto_y_presente_sin_perder_avance(self):
        self.h.preparar(self.p)
        for i in self.p.jugadores:
            self.a(i, "votar", opcion="corregir")
        e = self.p.mision.encargo
        for i, material in zip(self.p.jugadores, ("tablas", "cuerdas")):
            fuente = e.fuente(material)
            self.p.jugadores[i].update(x=fuente["x"], y=fuente["y"])
            self.a(i, "recoger_suministro", objetivo=fuente["id"], material=material)
            self.p.jugadores[i].update(x=e.destino["x"], y=e.destino["y"])
            self.a(i, "depositar")
        self.assertFalse(e.materiales_listos)  # Caso 1: falta la canasta de herramientas.
        self.h.completar_materiales(self.p)
        self.assertTrue(e.materiales_listos)
        self.assertFalse(e.completo)
        self.assertFalse(self.a("1", "trabajar")["ok"])
        self.assertTrue(self.a("0", "sujetar")["ok"])
        self.assertFalse(self.a("0", "trabajar")["ok"])
        self.assertTrue(self.a("1", "trabajar")["ok"])
        self.assertFalse(self.a("1", "trabajar")["ok"])
        self.p.conectados.discard("0")
        self.p.actualizar(self.p.ultima+1)
        self.assertIsNone(e.ayudante)
        self.assertEqual(e.progreso, 1)
        self.assertFalse(self.a("1", "trabajar")["ok"])
        self.p.conectados.add("0")
        self.a("0", "sujetar")
        for _ in range(2):
            self.p.actualizar(self.p.ultima+1)
            self.assertTrue(self.a("1", "trabajar")["ok"])
        self.assertTrue(e.materiales_colocados)
        self.assertFalse(e.completo)  # El evento no se gana hasta reparar el Puente 1.
        self.h.reparar_puente(self.p)
        self.assertTrue(e.completo)
        puntos = self.p.mision.puntos
        self.assertFalse(self.a("1", "trabajar")["ok"])
        self.assertEqual(self.p.mision.puntos, puntos)

    def test_luces_siguen_suelo_transitable_hasta_todas_las_fuentes(self):
        p = PartidaMovimiento([dict(id="0", nombre="A", rol="guardian")], 0)
        j = p.jugadores["0"]
        inicio = time.perf_counter()
        for objetivo in p.mision.objetivos:
            if not objetivo.get("rol") and objetivo["id"] != "caldero":
                continue
            ruta = buscar_camino(p.colisiones, (j["x"], j["y"]), (objetivo["x"], objetivo["y"]))
            self.assertTrue(ruta, objetivo["nombre"])
            self.assertTrue(all(not p.colisiones.bloqueado(*pos) for pos in ruta))
            for a, b in zip(ruta, ruta[1:]):
                self.assertFalse(p.colisiones.bloqueado((a[0]+b[0])/2, (a[1]+b[1])/2))
        self.assertLess(time.perf_counter()-inicio, 5)
