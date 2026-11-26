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



class SalaEnLineaTests(unittest.TestCase):
    """Bots que cubren a quien se va, anfitrión que sale y microcortes (servidor)."""

    def _sala_iniciada(self, personas=2):
        from multijugador.protocolo import VERSION
        from multijugador.servicio_internet import ServicioSalas
        reloj = [0.0]
        servicio = ServicioSalas(lambda: reloj[0])
        sesiones = []
        for i in range(personas):
            datos = {"version": VERSION, "nombre": "Persona" + str(i)}
            if i:
                datos["codigo"] = sesiones[0]["codigo"]
            sesion = servicio.ejecutar("POST", "/v1/crear" if not i else "/v1/unirse", datos)
            sesiones.append(sesion)
            for accion in ({"tipo": "rol", "rol": ROLES[i]}, {"tipo": "listo", "listo": True}):
                servicio.ejecutar("POST", "/v1/accion", accion, sesion["token"])
        servicio.ejecutar("POST", "/v1/accion", {"tipo": "iniciar"}, sesiones[0]["token"])
        return servicio, servicio.salas[sesiones[0]["codigo"]], sesiones, reloj

    def test_quien_sale_deja_su_personaje_a_un_bot(self):
        servicio, sala, sesiones, _ = self._sala_iniciada()
        persona = sesiones[1]["id"]
        servicio.ejecutar("POST", "/v1/salir", {}, sesiones[1]["token"])
        jugador = sala.partida.jugadores[persona]
        self.assertEqual(jugador["controlador"], "bot")
        self.assertIn(persona, sala.bots.bots)
        self.assertIn(persona, sala.partida.conectados)
        self.assertEqual(len(sala.partida.jugadores), 4)

    def test_si_sale_el_anfitrion_la_sala_pasa_a_otra_persona(self):
        servicio, sala, sesiones, _ = self._sala_iniciada()
        servicio.ejecutar("POST", "/v1/salir", {}, sesiones[0]["token"])
        self.assertIn(sesiones[0]["codigo"], servicio.salas)
        self.assertTrue(sala._sesiones[sesiones[1]["id"]]["jugador"]["anfitrion"])
        self.assertEqual(sala.partida.jugadores[sesiones[0]["id"]]["controlador"], "bot")

    def test_un_microcorte_no_suelta_lo_que_se_lleva(self):
        _, sala, sesiones, reloj = self._sala_iniciada()
        persona = sesiones[1]["id"]
        sala.marcar_corte(persona, reloj[0])
        sala.revisar_cortes(reloj[0] + 3)
        self.assertIn(persona, sala.partida.conectados)  # volvió a tiempo: nada cambia
        sala.revisar_cortes(reloj[0] + 6)
        self.assertNotIn(persona, sala.partida.conectados)


class BotsEnElFinalTests(unittest.TestCase):
    def test_con_personas_el_bot_no_reintenta_la_batalla(self):
        from bots.final_cooperativo import planificar

        class Bot:
            posicion = {"dimension": "futuro", "x": 0, "y": 0}
            rol, identificador = "aspirante", "bot_aspirante"

        estado = {"caso": {"futuro": {"desafio_final": {
            "fase": "reintento", "puntos": {"aspirante": {"x": 1, "y": 1}}, "ronda": 1, "aventura": {}}}}}
        jugadores = [{"id": "p0", "controlador": "humano", "conectado": False}, {"id": "bot_aspirante", "controlador": "bot"}]
        plan = planificar(Bot(), estado, jugadores, lambda *a, **k: dict(a=a, k=k))
        self.assertTrue(plan.get("esperar"))
        plan = planificar(Bot(), estado, jugadores[1:], lambda estado, destino, accion, **k: {"accion": accion, **k})
        self.assertEqual(plan.get("operacion"), "reintentar")


if __name__ == "__main__":
    unittest.main()
