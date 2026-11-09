"""Hablar con los NPC: autoridad del servidor, memoria por jugador y ventana."""
import os
import unittest
from unittest import mock
import uuid

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from bots.gestor_bots import GestorBots  # noqa: E402
from multijugador.dimensiones_red import LA_COPA, PRESENTE  # noqa: E402
from multijugador.movimiento import PartidaMovimiento  # noqa: E402

ROLES = ("guardian", "mensajero", "habitante", "aspirante")


def partida(cantidad=2):
    return PartidaMovimiento([dict(id=str(i), nombre="J" + str(i), rol=ROLES[i]) for i in range(cantidad)], 0)


class ConPartida(unittest.TestCase):
    def setUp(self):
        self.p = partida()
        self.m = self.p.mision

    def accion(self, jugador, accion, **datos):
        return self.p.actuar(jugador, dict(accion=accion, ronda=self.m.ronda, id_solicitud=uuid.uuid4().hex, **datos), self.p.ultima)

    def npc(self, nombre):
        return next(n for n in self.m.dialogos.publico() if n["nombre"] == nombre)

    def junto_a(self, jugador, npc):
        self.p.jugadores[jugador].update(x=npc["x"], y=npc["y"] + 10, dimension=npc["dimension"])

    def hablar(self, jugador, nombre):
        npc = self.npc(nombre)
        self.junto_a(jugador, npc)
        return self.accion(jugador, "hablar_npc", npc=npc["id"])

    def ir_al_distrito(self):
        self.p.colisiones_de(PRESENTE)
        self.p._viajar_equipo(LA_COPA, PRESENTE)


class Validacion(ConPartida):
    def test_desde_lejos_se_rechaza(self):
        npc = self.npc("Naira")
        self.p.jugadores["0"].update(x=npc["x"] + 300, y=npc["y"])
        self.assertFalse(self.accion("0", "hablar_npc", npc=npc["id"])["ok"])

    def test_desde_otra_dimension_se_rechaza(self):
        npc = self.npc("Naira")
        self.junto_a("0", npc)
        self.p.jugadores["0"]["dimension"] = PRESENTE
        self.assertFalse(self.accion("0", "hablar_npc", npc=npc["id"])["ok"])

    def test_un_npc_que_no_existe_se_rechaza(self):
        self.assertFalse(self.accion("0", "hablar_npc", npc="nadie")["ok"])

    def test_la_respuesta_solo_llega_a_quien_habla(self):
        acuse = self.hablar("0", "Darek")
        self.assertTrue(acuse["ok"])
        self.assertLessEqual({"personaje", "texto", "respuestas", "event_id"}, set(acuse["dialogo"]))
        self.assertNotIn(acuse["dialogo"]["texto"], str(self.p.estado("1")))


class Memoria(ConPartida):
    def test_la_segunda_conversacion_es_la_ampliacion(self):
        primera = self.hablar("0", "Darek")["dialogo"]
        self.accion("0", "responder_npc", npc=primera["npc"], respuesta=primera["respuestas"][-1])
        segunda = self.hablar("0", "Darek")["dialogo"]
        self.assertNotEqual(primera["texto"], segunda["texto"])

    def test_lo_visto_es_por_jugador(self):
        primera = self.hablar("0", "Darek")["dialogo"]
        self.accion("0", "responder_npc", npc=primera["npc"], respuesta=None)
        otra = self.hablar("1", "Darek")["dialogo"]
        self.assertEqual(primera["texto"], otra["texto"])


class Pistas(ConPartida):
    def test_el_testimonio_propio_se_registra_una_vez_para_el_grupo(self):
        self.hablar("0", "Naira")  # guardián: Naira es su fuente
        self.assertEqual(self.m.halladas["pista_guardian"], "0")
        self.assertIn("pista_guardian", self.m.conocidas["0"])
        cuantas = len(self.m.halladas)
        self.hablar("0", "Naira")
        self.assertEqual(len(self.m.halladas), cuantas)

    def test_en_el_distrito_la_pista_queda_para_todo_el_equipo(self):
        self.ir_al_distrito()
        self.hablar("0", "Darío Veraz")
        self.hablar("1", "Darío Veraz")
        presente = self.m.presente
        self.assertEqual(presente.halladas, {"fuente_ausente": "0"})
        self.assertEqual([p["id"] for p in presente.privado("1")["inventario"]], ["fuente_ausente"])

    def test_un_npc_que_ya_es_jugador_no_se_ofrece_salvo_si_da_pista(self):
        self.ir_al_distrito()
        nombres = {n["nombre"] for n in self.m.dialogos.publico() if n["dimension"] == "presente"}
        self.assertIn("Lía Nova", nombres)
        self.assertNotIn("Elías Vega", nombres)


class Respuestas(ConPartida):
    def test_consultar_tablilla_lejos_te_manda_al_caldero(self):
        dialogo = self.hablar("0", "Naira")["dialogo"]
        self.assertIn("Consultar tablilla", dialogo["respuestas"])
        acuse = self.accion("0", "responder_npc", npc=dialogo["npc"], respuesta="Consultar tablilla")
        self.assertTrue(acuse["ok"])
        self.assertNotIn("vista", acuse)

    def test_consultar_tablilla_cerca_abre_la_decision(self):
        dialogo = self.hablar("0", "Naira")["dialogo"]
        caldero = next(o for o in self.m.objetivos if o["id"] == "caldero")
        self.p.jugadores["0"].update(x=caldero["x"], y=caldero["y"])
        acuse = self.accion("0", "responder_npc", npc=dialogo["npc"], respuesta="Consultar tablilla")
        self.assertEqual(acuse["vista"], "caldero")

    def test_entrega_el_mensaje_abre_los_mensajes(self):
        self.m.dialogos.npcs_copa.append({"id": "mensajero", "nombre": "Mensajero", "dimension": "la_copa", "x": 300, "y": 300})
        dialogo = self.hablar("0", "Mensajero")["dialogo"]
        self.assertEqual(dialogo["respuestas"][0], "Entrega el mensaje")
        acuse = self.accion("0", "responder_npc", npc=dialogo["npc"], respuesta="Entrega el mensaje")
        self.assertEqual(acuse["vista"], "eco_mensajes")

    def test_una_respuesta_inventada_se_rechaza(self):
        dialogo = self.hablar("0", "Darek")["dialogo"]
        self.assertFalse(self.accion("0", "responder_npc", npc=dialogo["npc"], respuesta="otra cosa")["ok"])


class NpcEnDialogo(ConPartida):
    def test_se_marca_al_hablar_y_se_libera_al_cerrar(self):
        dialogo = self.hablar("0", "Darek")["dialogo"]
        self.assertEqual(self.m.publico(self.p.conectados)["npcs_en_dialogo"], ["Darek"])
        self.accion("0", "responder_npc", npc=dialogo["npc"], respuesta=None)
        self.assertEqual(self.m.publico(self.p.conectados)["npcs_en_dialogo"], [])

    def test_con_dos_jugadores_sigue_ocupado_hasta_que_terminen(self):
        dialogo = self.hablar("0", "Darek")["dialogo"]
        self.hablar("1", "Darek")
        self.accion("0", "responder_npc", npc=dialogo["npc"], respuesta=None)
        self.assertEqual(self.m.publico(self.p.conectados)["npcs_en_dialogo"], ["Darek"])


class Bots(unittest.TestCase):
    def test_un_bot_obtiene_el_testimonio_por_la_misma_ruta(self):
        p = PartidaMovimiento([dict(id="0", nombre="A", rol="guardian")]
                              + [dict(id="bot_" + r, nombre=r, rol=r, controlador="bot") for r in ROLES[1:]], 0)
        gestor = GestorBots(p, {"0"})
        p.colisiones_de(PRESENTE)
        p._viajar_equipo(LA_COPA, PRESENTE)
        original = p.actuar
        vistas = []
        p.actuar = lambda i, s, a: vistas.append(s["accion"]) or original(i, s, a)
        ahora = 0
        for _ in range(500):
            ahora += .15
            p.actualizar(ahora)
            gestor.actualizar(ahora, .15)
        self.assertEqual(len(p.mision.presente.halladas), 2)
        self.assertIn("hablar_npc", vistas)
        self.assertIn("responder_npc", vistas)
        self.assertEqual(p.mision.dialogos.abiertos, {})


class Ventana(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        from interfaz.partida_multijugador import VistaPartida
        self.p = partida()
        self.vista = VistaPartida("0", {"mundo": self.p.estado("0")})
        self.panel = self.vista.panel
        self.cliente = mock.Mock()
        self.lienzo = pygame.Surface((960, 720))
        self.panel.recibir({"ok": True, "vista": "dialogo_npc", "silencioso": True, "dialogo": {
            "npc": "darek", "personaje": "Darek", "texto": "Hola, equipo.", "respuestas": ["Consultar tablilla", "Gracias"], "event_id": 1}})

    def tecla(self, codigo):
        evento = pygame.event.Event(pygame.KEYDOWN, key=codigo, mod=0, unicode="", scancode=0)
        return self.panel.manejar(evento, (0, 0), self.cliente)

    def test_se_abre_sin_tapar_con_un_panel(self):
        self.assertEqual(self.panel.modo, "dialogo_npc")
        self.panel.dibujar(self.lienzo)
        self.assertGreater(self.panel.dialogo["caja"][0].y, 360)

    def test_e_completa_el_texto_y_el_numero_responde(self):
        self.tecla(pygame.K_e)
        self.assertTrue(self.panel.dialogo["completo"])
        self.tecla(pygame.K_2)
        self.cliente.actuar.assert_called_once_with("responder_npc", npc="darek", respuesta="Gracias")
        self.assertIsNone(self.panel.modo)

    def test_esc_cierra_sin_responder(self):
        self.tecla(pygame.K_ESCAPE)
        self.cliente.actuar.assert_called_once_with("responder_npc", npc="darek", respuesta=None)

    def test_flechas_y_enter(self):
        self.tecla(pygame.K_SPACE)
        self.tecla(pygame.K_DOWN)
        self.tecla(pygame.K_RETURN)
        self.cliente.actuar.assert_called_once_with("responder_npc", npc="darek", respuesta="Gracias")

    def test_el_jugador_cerca_ve_la_opcion_de_hablar(self):
        npc = next(n for n in self.p.mision.dialogos.publico() if n["nombre"] == "Darek")
        self.p.jugadores["0"].update(x=npc["x"], y=npc["y"] + 10)
        self.vista.recibir({"mundo": self.p.estado("0")})
        self.panel.modo = None
        self.assertIn("npc:" + npc["id"], [o["id"] for o in self.vista.candidatos()])

    def test_los_npc_del_distrito_tienen_animacion_de_hablar(self):
        self.vista._cargar_dimension(PRESENTE)
        escena = self.vista.escenas_zoom[PRESENTE]
        con_animacion = {o["personaje"] for o in escena["decoraciones"] if o.get("cuadros_hablando")}
        self.assertLessEqual({"Darío Veraz", "Lía Nova", "Ronaldo Vélez", "Tomás Red", "Mateo Ríos"}, con_animacion)


if __name__ == "__main__":
    unittest.main()
