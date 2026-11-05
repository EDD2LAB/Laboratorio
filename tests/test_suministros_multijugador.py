import unittest
import uuid

import test_campana_copa as campana_pruebas


class SuministrosTests(unittest.TestCase):
    def setUp(self):
        self.h = campana_pruebas.CampanaTests()
        self.p = self.h.crear(("guardian", "habitante"))
        self.h.preparar(self.p)
        for i in self.p.jugadores:
            self.h.accion(self.p, i, "votar", opcion="corregir")

    def mover(self, i, objetivo):
        self.p.jugadores[i].update(x=objetivo["x"], y=objetivo["y"])

    def recoger(self, i, material):
        e = self.p.mision.encargo
        self.mover(i, e.fuente(material))
        return self.h.accion(self.p, i, "recoger_suministro", objetivo=e.fuente(material)["id"], material=material)

    def entregar(self, i):
        self.mover(i, self.p.mision.encargo.destino)
        return self.h.accion(self.p, i, "depositar")

    def test_dos_cargas_iguales_no_completan_y_se_puede_cambiar_carga(self):
        self.assertTrue(self.recoger("0", "tablas")["ok"])
        self.assertTrue(self.recoger("1", "tablas")["ok"])
        self.assertTrue(self.entregar("0")["ok"])
        self.assertFalse(self.entregar("1")["ok"])
        self.assertFalse(self.p.mision.encargo.completo)
        self.assertTrue(self.recoger("1", "cuerdas")["ok"])
        self.assertTrue(self.entregar("1")["ok"])
        self.h.hacer_actividad(self.p)
        self.assertTrue(self.p.mision.encargo.completo)

    def test_rechaza_material_inventado_distancia_y_segundo_aporte_de_la_misma_persona(self):
        self.assertFalse(self.h.accion(self.p, "0", "recoger_suministro", objetivo="archivo", material="oro")["ok"])
        self.assertTrue(self.recoger("0", "tablas")["ok"])
        self.assertFalse(self.h.accion(self.p, "0", "depositar")["ok"])
        self.assertTrue(self.entregar("0")["ok"])
        self.assertFalse(self.recoger("0", "cuerdas")["ok"])
        self.assertFalse(self.p.mision.encargo.completo)

    def test_carga_sobrevive_corte_y_recompensa_no_se_duplica(self):
        self.recoger("0", "tablas")
        self.p.conectados.discard("0")
        self.assertEqual(self.p.mision.privado("0")["carga"], "Tablas")
        self.p.conectados.add("0")
        self.entregar("0")
        self.recoger("1", "cuerdas")
        self.mover("1", self.p.mision.encargo.destino)
        solicitud = dict(accion="depositar", ronda=0, id_solicitud=uuid.uuid4().hex)
        antes = self.p.mision.puntos
        acuse = self.p.actuar("1", solicitud, 0)
        self.assertTrue(acuse["ok"])
        self.assertEqual(self.p.mision.puntos, antes)  # Falta la actividad.
        self.h.hacer_actividad(self.p)
        self.assertEqual(self.p.actuar("1", solicitud, 0), acuse)
        self.entregar("1")
        self.assertEqual(self.p.mision.puntos, antes + 30)
        self.assertEqual(self.p.mision.indicadores["armonia"], 62)
        for j in self.p.jugadores.values():
            j.update(x=480, y=380)
        for i in self.p.jugadores:
            self.h.accion(self.p, i, "continuar")
        self.assertEqual(self.p.mision.obras[0]["efecto"], "Pasarela preparada")
