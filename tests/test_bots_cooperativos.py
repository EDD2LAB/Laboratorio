import unittest
from unittest.mock import patch

from bots.planificador_bot import PlanificadorBot
from multijugador.partida_local import ClienteCampanaLocal
from multijugador.movimiento import ColisionesMapa, PartidaMovimiento
from test_campana_copa import tiempo_acierto


class PlanificadorBotTests(unittest.TestCase):
    def test_decide_solo_con_semantica_de_las_pruebas(self):
        casos = (
            ([{"metadatos": {"confirma_riesgo_actual": True}}] * 2, "difundir"),
            ([{"metadatos": {"indica_descontextualizacion": True}}] * 2, "descartar"),
            ([{"metadatos": {"problema_parcial": True}}] * 2, "corregir"),
        )
        for inventario, esperado in casos:
            with self.subTest(esperado=esperado):
                propuesta = PlanificadorBot.proponer_decision(inventario)
                self.assertEqual(propuesta["accion_propuesta"], esperado)

    def test_no_decide_con_evidencia_insuficiente_o_en_conflicto(self):
        propuesta = PlanificadorBot.proponer_decision([
            {"metadatos": {"confirma_riesgo_actual": True}},
            {"metadatos": {"indica_descontextualizacion": True}},
        ])
        self.assertIsNone(propuesta["accion_propuesta"])

    def test_todos_los_casos_y_variantes_se_resuelven_con_sus_metadatos(self):
        roles = ("guardian", "mensajero", "habitante", "aspirante")
        for indice_variante in (0, 1):
            with self.subTest(variante=indice_variante):
                with patch(
                    "logica.sorteo_partida.SorteoPartida.elegir",
                    side_effect=lambda opciones: opciones[indice_variante],
                ):
                    partida = PartidaMovimiento(
                        [
                            {"id": rol, "nombre": rol, "rol": rol}
                            for rol in roles
                        ],
                        0,
                        ColisionesMapa({"hitboxes": [], "decoracion": []}),
                    )

                for caso in partida.mision.casos:
                    with self.subTest(caso=caso[0], correcta=caso[3]):
                        semantica = partida.mision._metadatos(
                            caso[4] or partida.mision.pruebas
                        )
                        pruebas = [
                            {"metadatos": metadatos}
                            for metadatos in semantica.values()
                        ]
                        propuesta = PlanificadorBot.proponer_decision(pruebas)
                        self.assertEqual(propuesta["accion_propuesta"], caso[3])


class CampanaLocalBotsTests(unittest.TestCase):
    def avanzar_hasta(self, cliente, condicion, descripcion, limite=500):
        for _ in range(limite):
            if condicion():
                return
            cliente.actualizar(0.15)
        self.fail(f"Los bots no completaron la tarea: {descripcion}.")

    @staticmethod
    def ir(partida, objetivo):
        partida.jugadores["local"].update(x=objetivo["x"], y=objetivo["y"])

    def investigar(self, cliente, partida):
        """La persona busca su pista; un bot pone la segunda y se la da cuando ella la pide."""
        objetivo = partida.mision.privado("local")["objetivo"]
        self.ir(partida, objetivo)
        cliente.actuar("interactuar", objetivo=objetivo["id"])
        self.avanzar_hasta(cliente, lambda: len(partida.mision.halladas) == 2, "buscar la segunda pista")
        cliente.actuar("pedir_pista")
        self.avanzar_hasta(cliente, lambda: len(partida.mision.conocidas["local"]) == 2, "entregar la pista pedida")

    def aportar(self, cliente, partida, material):
        encargo = partida.mision.encargo
        self.ir(partida, encargo.fuente(material))
        cliente.actuar("interactuar", objetivo=encargo.fuente(material)["id"], material=material)
        self.ir(partida, encargo.destino)
        cliente.actuar("interactuar", objetivo=encargo.destino["id"])
        self.assertEqual(encargo.entregados.get(material), "local")

    def trabajar(self, cliente, partida, bots):
        encargo = partida.mision.encargo
        self.avanzar_hasta(cliente, lambda: encargo.ayudante in bots, "sujetar en la actividad")
        self.ir(partida, encargo.destino)
        while not encargo.materiales_colocados:
            for _ in range(5):
                cliente.actualizar(.15)
            cliente.actuar("trabajar")

    def reparar_puente_a_mano(self, cliente, partida):
        self.avanzar_hasta(cliente, lambda: partida.mision.encargo.materiales_colocados,
                           "colocar los materiales del puente", limite=1500)
        for _ in range(120):  # con una persona en la partida, ningún bot lo toca
            cliente.actualizar(.1)
        puente = partida.mision.puente
        self.assertEqual(puente.estado, "READY_TO_REPAIR")
        self.assertIsNone(puente.reparador)
        objetivo = partida.mision.objetivo_puente
        partida.jugadores["local"].update(x=objetivo["x"], y=objetivo["y"])
        cliente.actuar("interactuar", objetivo="puente_1")
        while puente.estado == "REPAIR_MINIGAME":
            cliente.actualizar(.1)
            cliente.actuar("intento_reparacion", tiempo_aguja_ms=tiempo_acierto(puente))
        self.avanzar_hasta(cliente, lambda: puente.reparado, "terminar la reparación")

    def test_campana_completa_la_juega_la_persona_y_los_bots_solo_completan_parejas(self):
        cliente = ClienteCampanaLocal("Prueba", "guardian")
        partida = cliente._partida
        bots = set(cliente._bots.bots)
        caldero = next(o for o in partida.mision.objetivos if o["id"] == "caldero")

        self.assertEqual(len(bots), 3)
        self.assertNotIn("correcta", partida.mision.publico(partida.conectados))

        for ronda, caso in enumerate(partida.mision.casos):
            self.investigar(cliente, partida)
            buscadores = {i for i in partida.mision.halladas.values() if i in bots}
            self.assertEqual(len(buscadores), 1)  # un solo bot: el segundo investigador
            for _ in range(60):
                cliente.actualizar(.15)
            self.assertEqual(partida.mision.votos, {})  # los bots nunca eligen
            self.assertEqual(partida.mision.habilidades_usadas, set())

            self.ir(partida, caldero)
            cliente.actuar("votar", opcion=caso[3])
            self.assertTrue(partida.mision.resultado["correcto"])

            if ronda == len(partida.mision.casos) - 1:
                continue

            encargo = partida.mision.encargo
            if encargo.config.get("aportes_libres"):
                for material, *_ in encargo.config["materiales"]:
                    self.aportar(cliente, partida, material)
                self.assertEqual(set(encargo.entregados.values()), {"local"})
            else:
                self.aportar(cliente, partida, encargo.config["materiales"][0][0])
                self.avanzar_hasta(cliente, lambda: encargo.materiales_listos, "aportar el otro material",
                                   limite=1500)
                self.assertEqual(len(set(encargo.entregados.values()) & bots), 1)
            self.trabajar(cliente, partida, bots)

            if ronda == 0:
                self.reparar_puente_a_mano(cliente, partida)
            self.assertTrue(encargo.completo)
            self.assertEqual(partida.mision.preparados, set())  # los bots no confirman

            self.ir(partida, caldero)
            cliente.actuar("continuar")
            self.assertEqual(partida.mision.ronda, ronda + 1)

        self.assertEqual(partida.mision.fase, "final")
        self.assertEqual(len(partida.mision.resumen), len(partida.mision.casos) - 1)
        self.assertTrue(all(caso["correcto"] for caso in partida.mision.resumen))
        self.assertEqual(
            len(partida.mision.publico(partida.conectados)["balance"]),
            len(partida.mision.casos),
        )


if __name__ == "__main__":
    unittest.main()
