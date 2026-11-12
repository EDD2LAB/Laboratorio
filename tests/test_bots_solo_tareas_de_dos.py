"""Con personas en la partida, los bots no resuelven nada que una persona pueda hacer sola.

Solo ponen la segunda persona que exige el servidor: un segundo investigador,
la pista que se les pide, el aporte de otra persona en un encargo y quien
sujeta en la actividad en pareja.
"""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from multijugador.partida_local import ClienteCampanaLocal  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.cliente = ClienteCampanaLocal("Prueba", "guardian")
        self.partida = self.cliente._partida
        self.mision = self.partida.mision
        self.bots = set(self.cliente._bots.bots)

    def pasos(self, cantidad):
        for _ in range(cantidad):
            self.cliente.actualizar(0.15)

    def avanzar_hasta(self, condicion, descripcion, limite=900):
        for _ in range(limite):
            if condicion():
                return
            self.cliente.actualizar(0.15)
        self.fail("No ocurrió: " + descripcion)

    def persona_encuentra_su_pista(self):
        self.mision.conocidas["local"].add("pista_guardian")
        self.mision.halladas["pista_guardian"] = "local"

    def ir_a_preparacion(self, ronda):
        for _ in range(ronda):
            self.mision.resultado = {"opcion": "corregir", "correcto": True, "texto": ""}
            self.mision._siguiente()
        self.mision.resultado = {"opcion": "corregir", "correcto": True, "texto": ""}
        self.assertEqual(self.mision.fase, "preparacion")


class Investigacion(Base):
    def test_ningun_bot_busca_pistas_antes_que_la_persona(self):
        self.pasos(300)
        self.assertEqual(self.mision.halladas, {})

    def test_tras_la_persona_solo_un_bot_busca_su_pista(self):
        self.persona_encuentra_su_pista()
        self.avanzar_hasta(lambda: len(self.mision.halladas) == 2, "un bot encuentra su pista")
        self.pasos(200)
        bots_con_pista = {i for i in self.mision.halladas.values() if i in self.bots}
        self.assertEqual(len(bots_con_pista), 1)
        self.assertEqual(len(self.mision.halladas), 2)

    def test_el_bot_no_comparte_si_nadie_se_lo_pide(self):
        self.persona_encuentra_su_pista()
        self.avanzar_hasta(lambda: len(self.mision.halladas) == 2, "un bot encuentra su pista")
        self.pasos(200)
        self.assertEqual(self.mision.entregas, [])
        self.assertEqual(len(self.mision.conocidas["local"]), 1)

    def test_pedir_una_pista_hace_que_el_bot_la_envie(self):
        self.persona_encuentra_su_pista()
        self.avanzar_hasta(lambda: len(self.mision.halladas) == 2, "un bot encuentra su pista")
        self.cliente.actuar("pedir_pista")
        self.avanzar_hasta(lambda: len(self.mision.conocidas["local"]) == 2, "la persona recibe una pista")

    def test_los_bots_nunca_votan(self):
        self.persona_encuentra_su_pista()
        self.avanzar_hasta(lambda: len(self.mision.halladas) == 2, "un bot encuentra su pista")
        self.cliente.actuar("pedir_pista")
        self.avanzar_hasta(lambda: len(self.mision.conocidas["local"]) == 2, "la persona recibe una pista")
        self.pasos(200)
        self.assertEqual(self.mision.votos, {})
        self.assertIsNone(self.mision.resultado)


class Preparacion(Base):
    def test_primer_encargo_los_bots_no_recogen_ni_entregan(self):
        self.ir_a_preparacion(0)
        self.pasos(400)
        self.assertEqual(self.mision.encargo.cargas, {})
        self.assertEqual(self.mision.encargo.entregados, {})

    def test_en_la_actividad_el_bot_sujeta_y_la_persona_trabaja(self):
        self.ir_a_preparacion(0)
        encargo = self.mision.encargo
        for material, *_ in encargo.config["materiales"]:
            encargo.entregados[material] = "local"
        self.avanzar_hasta(lambda: encargo.ayudante in self.bots, "un bot sujeta")
        self.pasos(100)
        self.assertEqual(encargo.progreso, 0)  # el bot nunca hace la tarea

    def test_encargo_de_dos_personas_el_bot_aporta_despues_de_la_persona(self):
        self.ir_a_preparacion(1)
        encargo = self.mision.encargo
        self.pasos(300)
        self.assertEqual(encargo.entregados, {})  # primero aporta la persona
        primero = encargo.config["materiales"][0][0]
        encargo.entregados[primero] = "local"
        self.avanzar_hasta(lambda: encargo.materiales_listos, "un bot aporta el otro material")
        aportantes = set(encargo.entregados.values()) - {"local"}
        self.assertEqual(len(aportantes), 1)
        self.assertTrue(aportantes <= self.bots)

    def test_continuar_solo_lo_confirma_la_persona(self):
        self.ir_a_preparacion(0)
        encargo = self.mision.encargo
        for material, *_ in encargo.config["materiales"]:
            encargo.entregados[material] = "local"
        encargo.progreso = 3
        encargo.puente_reparado = True
        self.pasos(100)
        self.assertEqual(self.mision.preparados, set())
        self.assertEqual(self.mision.ronda, 0)
        caldero = next(o for o in self.mision.objetivos if o["id"] == "caldero")
        self.partida.jugadores["local"].update(x=caldero["x"], y=caldero["y"])
        self.cliente.actuar("continuar")
        self.assertEqual(self.mision.ronda, 1)


if __name__ == "__main__":
    unittest.main()
