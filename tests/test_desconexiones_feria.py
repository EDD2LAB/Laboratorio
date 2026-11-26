"""Revisión para la feria: una desconexión nunca deja al equipo atascado y los bots esperan
a las personas que perdieron la conexión (siguen en la partida durante su gracia)."""
import unittest

from bots.gestor_bots import GestorBots
from multijugador.dimensiones_red import FUTURO, LA_COPA
from multijugador.movimiento import PartidaMovimiento
from multijugador.nucleo import LLAVE
from multijugador.protocolo import ROLES
from multijugador.suministros import EncargoSuministros


def sala_con_bots(personas=2):
    jugadores = [dict(id="p" + str(i), nombre="Persona" + str(i), rol=ROLES[i]) for i in range(personas)]
    jugadores += [dict(id="bot_" + r, nombre=r, rol=r) for r in ROLES[personas:]]
    partida = PartidaMovimiento(jugadores, 0, semilla=1)
    bots = GestorBots(partida, {j["id"] for j in jugadores[:personas]})
    return partida, bots


class ObjetosDeQuienSeVaTests(unittest.TestCase):
    def test_el_objeto_del_encargo_se_suelta_si_su_portador_ya_no_esta(self):
        partida, _ = sala_con_bots(2)
        encargo = partida.mision.encargo
        self.assertIsInstance(encargo, EncargoSuministros)
        encargo.cargas = {"p0": "tablas", "p1": "cuerda"}
        partida.conectados.discard("p0")
        partida.actualizar(1)
        self.assertEqual(encargo.cargas, {"p1": "cuerda"})

    def test_la_llave_vuelve_al_corredor_si_su_portador_se_desconecta(self):
        partida, _ = sala_con_bots(2)
        partida._viajar_equipo(LA_COPA, FUTURO)
        futuro = partida.mision.futuro
        futuro.halladas[LLAVE] = "p1"
        partida.actualizar(1)
        self.assertEqual(futuro.portador, "p1")  # conectado: la conserva
        partida.conectados.discard("p1")
        partida.actualizar(2)
        self.assertIsNone(futuro.portador)

    def test_la_llave_vuelve_si_su_portador_sale_de_la_sala(self):
        partida, _ = sala_con_bots(2)
        partida._viajar_equipo(LA_COPA, FUTURO)
        partida.mision.futuro.halladas[LLAVE] = "p1"
        partida.quitar("p1")
        partida.actualizar(1)
        self.assertIsNone(partida.mision.futuro.portador)


class BotsEsperanALasPersonasTests(unittest.TestCase):
    def _simular(self, partida, bots, segundos, desde=0.0):
        ahora = desde
        for _ in range(int(segundos * 20)):
            ahora += .05
            partida.actualizar(ahora)
            bots.actualizar(ahora, .05)
        return ahora

    def test_si_todas_las_personas_pierden_la_conexion_los_bots_no_resuelven(self):
        partida, bots = sala_con_bots(2)
        ahora = self._simular(partida, bots, 2)
        partida.conectados -= {"p0", "p1"}  # se cae la Wi-Fi de la feria
        self._simular(partida, bots, 40, ahora)
        mision = partida.mision
        self.assertIsNone(mision.resultado)
        self.assertEqual(mision.ronda, 0)
        self.assertTrue(all(j["dimension"] == LA_COPA for j in partida.jugadores.values()))

    def test_al_terminar_la_gracia_los_bots_vuelven_a_jugar_solos(self):
        partida, _ = sala_con_bots(2)
        for persona in ("p0", "p1"):
            partida.quitar(persona)  # lo que hace el servidor al acabar los 120 s
        self.assertEqual(partida.mision.decisores(partida.conectados), set(partida.conectados))

    def test_con_personas_conectadas_deciden_ellas(self):
        partida, _ = sala_con_bots(2)
        self.assertEqual(partida.mision.decisores(partida.conectados), {"p0", "p1"})
        partida.conectados.discard("p0")
        self.assertEqual(partida.mision.decisores(partida.conectados), {"p1"})


if __name__ == "__main__":
    unittest.main()
