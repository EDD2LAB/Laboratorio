"""Edificios de Distrito Conecta: puertas, interiores y pistas en boca de sus personajes."""
import math
import os
import unittest
import uuid
from collections import deque
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from bots.gestor_bots import GestorBots  # noqa: E402
from multijugador.dimensiones_red import (INTERIORES, LA_COPA, PRESENTE, RADIO_PUERTA, cargar_datos, cerca_de_rect,  # noqa: E402
                                          edificios_de, spawn_presente)
from multijugador.movimiento import ColisionesMapa, PartidaMovimiento  # noqa: E402
from multijugador.protocolo import ROLES  # noqa: E402


def partida(humanos=2, bots=False):
    jugadores = [dict(id=str(i), nombre="J" + str(i), rol=ROLES[i]) for i in range(humanos)]
    if bots:
        jugadores += [dict(id="bot_" + r, nombre=r, rol=r, controlador="bot") for r in ROLES[humanos:]]
    p = PartidaMovimiento(jugadores, 0)
    p._viajar_equipo(LA_COPA, PRESENTE)
    p.actualizar(.05)
    return p


def accion(p, i, nombre, **datos):
    return p.actuar(i, dict(accion=nombre, id_solicitud=uuid.uuid4().hex, ronda=p.mision.ronda, **datos), p.ultima)


def a_la_puerta(p, i, edificio):
    puerta = p.mision.presente.edificios[edificio]
    p.jugadores[i].update(x=float(puerta["x"]), y=float(puerta["y"]), interior=None)


def npc(p, nombre):
    return next(n for n in p.mision.dialogos.publico() if n["nombre"] == nombre)


class Puertas(unittest.TestCase):
    def test_cada_puerta_se_alcanza_a_pie_desde_el_inicio(self):
        datos = cargar_datos(PRESENTE)
        mapa = ColisionesMapa(datos)
        inicio = mapa.inicio_libre(*spawn_presente(datos))
        inicio = (round(inicio[0]), round(inicio[1]))
        vistos, cola = {inicio}, deque([inicio])
        while cola:
            a, b = cola.popleft()
            for vecino in ((a + 4, b), (a - 4, b), (a, b + 4), (a, b - 4)):
                if vecino not in vistos and not mapa.bloqueado(*vecino):
                    vistos.add(vecino)
                    cola.append(vecino)
        edificios = edificios_de(datos)
        self.assertEqual(set(edificios), set(INTERIORES))
        for clave, puerta in edificios.items():
            self.assertTrue(cerca_de_rect(puerta["x"], puerta["y"], puerta["rect"], RADIO_PUERTA), clave)
            self.assertLessEqual(min(math.hypot(a - puerta["x"], b - puerta["y"]) for a, b in vistos), 6, clave)

    def test_entrar_y_salir_por_cada_puerta(self):
        p = partida()
        for edificio in INTERIORES:
            a_la_puerta(p, "0", edificio)
            self.assertTrue(accion(p, "0", "entrar_edificio", edificio=edificio)["ok"], edificio)
            j = p.jugadores["0"]
            self.assertEqual(j["interior"], edificio)
            self.assertFalse(p.interiores[edificio].bloqueado(j["x"], j["y"]), edificio)
            self.assertTrue(accion(p, "0", "salir_edificio")["ok"], edificio)
            puerta = p.mision.presente.edificios[edificio]
            self.assertIsNone(j["interior"])
            self.assertEqual((j["x"], j["y"]), (puerta["x"], puerta["y"]))

    def test_lejos_de_la_puerta_no_se_entra(self):
        p = partida()
        p.jugadores["0"].update(x=480.0, y=400.0)
        self.assertFalse(accion(p, "0", "entrar_edificio", edificio="sede_aspirante")["ok"])
        self.assertIsNone(p.jugadores["0"].get("interior"))

    def test_dentro_se_camina_con_las_paredes_del_interior(self):
        p = partida()
        a_la_puerta(p, "0", "centro_verificacion")
        accion(p, "0", "entrar_edificio", edificio="centro_verificacion")
        j = p.jugadores["0"]
        for seq in range(40):
            p.recibir("0", {"dx": 0, "dy": -1, "seq": seq}, p.ultima)
            p.actualizar(p.ultima + .1)
        limite = p.interiores["centro_verificacion"].datos["rect_mapa"]
        self.assertGreater(j["y"], limite[1] + limite[3] * .3)  # no se sube a la pared del fondo

    def test_quien_esta_dentro_no_se_ve_desde_la_calle(self):
        from multijugador.dimensiones_red import jugadores_visibles
        p = partida()
        a_la_puerta(p, "0", "sede_aspirante")
        accion(p, "0", "entrar_edificio", edificio="sede_aspirante")
        jugadores = p.estado("1")["jugadores"]
        self.assertEqual([j["id"] for j in jugadores_visibles(jugadores, PRESENTE)], ["1"])
        self.assertEqual([j["id"] for j in jugadores_visibles(jugadores, PRESENTE, "sede_aspirante")], ["0"])


class Pistas(unittest.TestCase):
    def test_las_pistas_estan_dentro_y_no_hay_puntos_en_la_calle(self):
        p = partida(1)
        m = p.mision.presente
        self.assertEqual([o["id"] for o in m.objetivos], ["presente:pantalla"])
        for grupo in m.personajes_evento:
            for n in grupo:
                self.assertIn(n["interior"], INTERIORES)
                self.assertFalse(p.interiores[n["interior"]].bloqueado(n["x"], n["y"]), n["nombre"])

    def test_desde_la_calle_no_se_le_habla_al_que_esta_dentro(self):
        p = partida(1)
        dario = npc(p, "Darío Veraz")
        p.jugadores["0"].update(x=dario["x"], y=dario["y"], interior=None)
        self.assertFalse(accion(p, "0", "hablar_npc", npc=dario["id"])["ok"])
        self.assertEqual(p.mision.presente.halladas, {})

    def test_hablando_dentro_se_obtiene_la_pista(self):
        p = partida(1)
        dario = npc(p, "Darío Veraz")
        p.jugadores["0"].update(x=dario["x"], y=dario["y"], interior=dario["interior"])
        acuse = accion(p, "0", "hablar_npc", npc=dario["id"])
        self.assertIn("video original", acuse["dialogo"]["texto"])
        self.assertIn("fuente_ausente", p.mision.presente.halladas)

    def test_si_alguien_juega_al_personaje_se_le_habla_a_ese_jugador(self):
        p = PartidaMovimiento([dict(id="0", nombre="A", rol="guardian"), dict(id="1", nombre="B", rol="aspirante")], 0)
        p._viajar_equipo(LA_COPA, PRESENTE)
        p.actualizar(.05)
        ronaldo = npc(p, "Ronaldo Vélez")
        jugador = p.jugadores["1"]
        self.assertEqual((ronaldo["jugador"], ronaldo["x"], ronaldo["interior"]), ("1", round(jugador["x"]), None))
        p.jugadores["0"].update(x=jugador["x"] + 400, y=jugador["y"])
        self.assertFalse(accion(p, "0", "hablar_npc", npc=ronaldo["id"])["ok"])
        p.jugadores["0"].update(x=jugador["x"] + 20, y=jugador["y"])
        self.assertTrue(accion(p, "0", "hablar_npc", npc=ronaldo["id"])["ok"])
        self.assertIn("respuesta_kael", p.mision.presente.halladas)

    def test_los_bots_usan_las_puertas_para_llegar_a_las_pistas(self):
        p = partida(1, bots=True)
        gestor = GestorBots(p, {"0"})
        original = p.actuar
        vistas = []
        p.actuar = lambda i, s, a: vistas.append(s["accion"]) or original(i, s, a)
        ahora = p.ultima
        for _ in range(900):
            ahora += .15
            p.actualizar(ahora)
            gestor.actualizar(ahora, .15)
        self.assertIn("entrar_edificio", vistas)
        self.assertIn("salir_edificio", vistas)
        self.assertEqual(len(p.mision.presente.halladas), 2)


class Vista(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        from interfaz.partida_multijugador import VistaPartida
        self.p = partida(1)
        self.v = VistaPartida("0", {"mundo": self.p.estado("0")})
        self.v.recibir({"mundo": self.p.estado("0")})

    def refrescar(self):
        self.v.recibir({"mundo": self.p.estado("0")})

    def test_se_ofrece_la_puerta_y_e_entra(self):
        a_la_puerta(self.p, "0", "centro_verificacion")
        self.refrescar()
        self.assertIn("entrar:centro_verificacion", [o["id"] for o in self.v.candidatos()])
        cliente = mock.Mock()
        self.v.seleccion, self.v.transicion = "entrar:centro_verificacion", None
        self.v.panel.modo = None
        self.v.manejar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e), (0, 0), cliente)
        cliente.actuar.assert_called_once_with("entrar_edificio", edificio="centro_verificacion")

    def test_cada_interior_se_dibuja_con_su_fondo_y_personajes(self):
        lienzo = pygame.Surface((960, 720))
        for edificio in INTERIORES:
            a_la_puerta(self.p, "0", edificio)
            self.assertTrue(accion(self.p, "0", "entrar_edificio", edificio=edificio)["ok"])
            self.refrescar()
            self.assertEqual(self.v.interior, edificio)
            self.assertIsNone(self.v.vista_camara())
            self.assertIn("salir", [o["id"] for o in self.v.candidatos()])
            self.v.dibujar(lienzo, "LOCAL")
            self.assertEqual(self.v.jugadores["0"]["datos"]["interior"], edificio)
            self.assertTrue(accion(self.p, "0", "salir_edificio")["ok"])
            self.refrescar()
            self.assertIsNone(self.v.interior)
            self.v.dibujar(lienzo, "LOCAL")

    def test_la_guia_lleva_a_una_puerta_y_dentro_al_personaje(self):
        objetivo = self.v._objetivo_presente()
        self.assertIn(objetivo["id"], self.p.mision.presente.edificios)
        a_la_puerta(self.p, "0", "centro_verificacion")
        accion(self.p, "0", "entrar_edificio", edificio="centro_verificacion")
        self.refrescar()
        self.assertEqual(self.v._objetivo_presente()["nombre"], "Darío Veraz")


if __name__ == "__main__":
    unittest.main()
