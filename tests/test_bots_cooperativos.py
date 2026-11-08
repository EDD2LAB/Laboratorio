import unittest
from unittest.mock import patch

from bots.planificador_bot import PlanificadorBot
from multijugador.partida_local import ClienteCampanaLocal
from multijugador.movimiento import ColisionesMapa, PartidaMovimiento


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
                    "multijugador.campana.random.choice",
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
    def compartir_prueba_humana(cliente, bots):
        partida = cliente._partida
        objetivo = partida.mision.privado("local")["objetivo"]
        partida.jugadores["local"].update(x=objetivo["x"], y=objetivo["y"])
        cliente.actuar("interactuar", objetivo=objetivo["id"])
        pista = "pista_" + partida.jugadores["local"]["rol"]
        for identificador in bots:
            companero = partida.jugadores[identificador]
            partida.jugadores["local"].update(x=companero["x"], y=companero["y"])
            cliente.actuar(
                "entregar",
                destinatario=identificador,
                pista=pista,
                medio="directo",
            )

    def test_campana_completa_con_inferencia_votos_y_suministros(self):
        cliente = ClienteCampanaLocal("Prueba", "guardian")
        partida = cliente._partida
        bots = set(cliente._bots.bots)

        self.assertEqual(len(bots), 3)
        self.assertNotIn("correcta", partida.mision.publico(partida.conectados))

        for ronda, caso in enumerate(partida.mision.casos):
            self.compartir_prueba_humana(cliente, bots)
            self.avanzar_hasta(
                cliente,
                lambda: bots.issubset(partida.mision.votos),
                f"votar en el caso {ronda + 1}",
            )
            for identificador, bot in cliente._bots.bots.items():
                with self.subTest(ronda=ronda, bot=identificador):
                    self.assertIn("pista_" + bot.rol, bot.pruebas_conocidas)
                    self.assertGreaterEqual(len(bot.pruebas_conocidas), 2)
                    self.assertEqual(partida.mision.votos[identificador], caso[3])

            if ronda == 0:
                self.assertEqual(partida.mision.habilidades_usadas, bots)
            self.assertIsNone(partida.mision.resultado)
            self.assertNotIn("local", partida.mision.votos)

            partida.jugadores["local"].update(x=480, y=380)
            cliente.actuar("votar", opcion=caso[3])
            self.assertTrue(partida.mision.resultado["correcto"])

            if ronda == len(partida.mision.casos) - 1:
                continue

            self.avanzar_hasta(
                cliente,
                lambda: bots.issubset(partida.mision.preparados),
                f"preparar suministros para el caso {ronda + 2}",
                limite=1500,
            )
            # Los bots solos recogen, entregan en el puesto, hacen la actividad
            # en pareja y (caso 1) reparan el Puente 1 con el minijuego.
            self.assertTrue(partida.mision.encargo.completo)
            self.assertFalse(partida.mision.encargo.cargas)
            if ronda == 0:
                self.assertTrue(partida.mision.puente.reparado)

            partida.jugadores["local"].update(x=480, y=380)
            cliente.actuar("interactuar", objetivo="caldero")
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
