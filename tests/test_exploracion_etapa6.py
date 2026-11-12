"""Exploración autoritativa, entradas/salidas y separación de escenas."""
import math
import os
import unittest
import uuid
from unittest import mock
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from multijugador.movimiento import PartidaMovimiento
from multijugador.dimensiones_red import spawn_interior, rect_salida
from bots.navegador_bot import NavegadorBot


def partida():
    return PartidaMovimiento([dict(id="0", nombre="Ana", rol="guardian"),
                              dict(id="1", nombre="Leo", rol="mensajero")], 0)


def accion(p, nombre, **datos):
    return p.actuar("0", dict(accion=nombre, id_solicitud=uuid.uuid4().hex, **datos), p.ultima)


class ExploracionServidor(unittest.TestCase):
    def setUp(self):
        self.p = partida()

    def test_vecinos_accesibles_no_regalan_pistas_ni_decisiones(self):
        for nombre in ("Elia", "Arel"):
            npc = next(n for n in self.p.mision.dialogos.npcs_copa if n["nombre"] == nombre)
            self.assertFalse(self.p.colisiones.bloqueado(npc["x"], npc["y"]))
            self.p.jugadores["0"].update(x=npc["x"], y=npc["y"])
            antes = dict(self.p.mision.halladas)
            r = accion(self.p, "hablar_npc", npc=npc["id"])
            self.assertTrue(r["ok"], r)
            respuesta = r["dialogo"]["respuestas"][0]
            r = accion(self.p, "responder_npc", npc=npc["id"], respuesta=respuesta)
            self.assertTrue(r["ok"], r)
            self.assertEqual(r["vista"], "fuente")
            self.assertEqual(self.p.mision.halladas, antes)
            self.assertIsNone(self.p.mision.resultado)

    def test_entrada_futuro_cercania_y_barrera(self):
        p = self.p
        p._viajar_equipo("la_copa", "futuro")
        puerta = p.mision.futuro.edificios["cafe_digital"]
        self.assertFalse(accion(p, "entrar_edificio", edificio="cafe_digital")["ok"])
        p.jugadores["0"].update(x=puerta["x"], y=puerta["y"])
        self.assertFalse(accion(p, "entrar_edificio", edificio="cafe_digital")["ok"])
        p.mision.futuro.tareas["conexiones"] = "1"
        self.assertTrue(accion(p, "entrar_edificio", edificio="cafe_digital")["ok"])
        self.assertEqual(p.jugadores["0"]["interior"], "cafe_digital")
        self.assertIs(p.colisiones_de_jugador(p.jugadores["0"]), p.interiores_futuro["cafe_digital"])
        self.assertFalse(accion(p, "entrar_edificio", edificio=[])["ok"])

    def test_diez_mesas_y_veinte_recorridos_transitables(self):
        puntos = self.p.mision.exploracion.objetivos
        self.assertEqual(len(puntos), 10)
        for punto in puntos:
            mapas = self.p.interiores_futuro if punto["dimension"] == "futuro" else self.p.interiores
            mapa = mapas[punto["interior"]]
            origen = spawn_interior(mapa.datos)
            salida = rect_salida(mapa.datos)
            for destino, radio in (((punto["x"], punto["y"]), 40),
                                    ((salida[0] + salida[2] / 2, salida[1] + salida[3] / 2), 58)):
                ruta = NavegadorBot(mapa).buscar_ruta(origen, destino, radio=radio)
                self.assertTrue(ruta or math.dist(origen, destino) <= radio, punto)
                anterior = origen
                for posicion in ruta:
                    self.assertTrue(mapa.trayecto_libre(anterior, posicion), punto)
                    anterior = posicion

    def test_consulta_valida_era_interior_y_distancia_sin_farmear(self):
        p = self.p
        punto = next(o for o in p.mision.exploracion.objetivos if o["dimension"] == "futuro")
        self.assertFalse(accion(p, "explorar_sector", objetivo=punto["id"])["ok"])
        jugador = p.jugadores["0"]
        jugador.update(dimension="futuro", interior=punto["interior"], x=0, y=0)
        self.assertFalse(accion(p, "explorar_sector", objetivo=punto["id"])["ok"])
        jugador.update(x=punto["x"], y=punto["y"])
        indicadores = dict(p.mision.indicadores)
        for _ in range(3):
            r = accion(p, "explorar_sector", objetivo=punto["id"])
            self.assertTrue(r["ok"], r)
            self.assertEqual(r["vista"], "descubrimiento")
        self.assertEqual(len(p.mision.exploracion.visitados["0"]), 1)
        self.assertEqual(p.mision.indicadores, indicadores)
        self.assertFalse(accion(p, "futuro_resolver", terminal="conexiones", arista=1)["ok"])
        jugador["dimension"] = "presente"
        self.assertFalse(accion(p, "explorar_sector", objetivo=punto["id"])["ok"])

    def test_salidas_de_cinco_interiores_y_regreso_al_exterior_libre(self):
        p = self.p
        p.jugadores["0"]["dimension"] = "futuro"
        p.mision.futuro.tareas["conexiones"] = "1"
        for edificio, puerta in p.mision.futuro.edificios.items():
            p.jugadores["0"].update(x=puerta["x"], y=puerta["y"], interior=None)
            self.assertTrue(accion(p, "entrar_edificio", edificio=edificio)["ok"])
            mapa = p.interiores_futuro[edificio]
            salida = rect_salida(mapa.datos)
            ruta = NavegadorBot(mapa).buscar_ruta(spawn_interior(mapa.datos),
                    (salida[0] + salida[2] / 2, salida[1] + salida[3] / 2), radio=58)
            if ruta:
                p.jugadores["0"].update(x=ruta[-1][0], y=ruta[-1][1])
            self.assertTrue(accion(p, "salir_edificio")["ok"], edificio)
            self.assertIsNone(p.jugadores["0"].get("interior"))
            self.assertFalse(p.colisiones_de("futuro").bloqueado(p.jugadores["0"]["x"], p.jugadores["0"]["y"]))

    def test_personaje_controlado_no_se_puede_escuchar_desde_otra_sala(self):
        p = self.p
        p._viajar_equipo("la_copa", "futuro")
        p.jugadores["1"].update(interior="cafe_digital", x=400, y=400)
        corredor = next(n for n in p.mision.dialogos.publico() if n["nombre"] == "Corredor de Datos")
        self.assertEqual(corredor["interior"], "cafe_digital")
        p.jugadores["0"].update(x=400, y=400, interior=None)
        self.assertFalse(accion(p, "hablar_npc", npc=corredor["id"])["ok"])
        p.jugadores["0"]["interior"] = "cafe_digital"
        self.assertTrue(accion(p, "hablar_npc", npc=corredor["id"])["ok"])

    def test_bot_busca_puerta_y_salida_de_su_era(self):
        from bots.planificador_bot import PlanificadorBot
        bot = SimpleNamespace(posicion=dict(dimension="futuro", interior=None))
        estado = dict(caso=dict(futuro=self.p.mision.futuro.publico(set())), privado={})
        plan = PlanificadorBot()._hablar_con(bot, estado, dict(interior="cafe_digital", id="corredor"))
        self.assertEqual(plan["accion"], "entrar_edificio")
        bot.posicion["interior"] = "cafe_digital"
        plan = PlanificadorBot()._tareas_nucleo(bot, estado, [], None, "normal")
        self.assertEqual(plan["accion"], "salir_edificio")


class ExploracionVista(unittest.TestCase):
    def test_interiores_separados_marcador_opcional_y_panel_sin_botones_antiguos(self):
        import pygame
        from interfaz.partida_multijugador import VistaPartida
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        p = partida()
        v = VistaPartida("0", {"mundo": p.estado("0")})
        v.panel.modo = None
        fondo_presente = v._interior("cafe_digital")["fondo"]
        p._viajar_equipo("la_copa", "futuro")
        p.mision.futuro.tareas["conexiones"] = "1"
        puerta = p.mision.futuro.edificios["cafe_digital"]
        p.jugadores["0"].update(x=puerta["x"], y=puerta["y"])
        accion(p, "entrar_edificio", edificio="cafe_digital")
        punto = next(o for o in p.mision.exploracion.objetivos if o["dimension"] == "futuro" and o["interior"] == "cafe_digital")
        p.jugadores["0"].update(x=punto["x"], y=punto["y"])
        v.recibir({"mundo": p.estado("0")})
        self.assertIsNot(v._interior("cafe_digital")["fondo"], fondo_presente)
        self.assertIn(punto["id"], [o["id"] for o in v.candidatos()])
        acuse = accion(p, "explorar_sector", objetivo=punto["id"])
        v.recibir({"mundo": p.estado("0")})
        v.panel.recibir(acuse)
        v.transicion = None
        v.panel.botones["accion_antigua"] = object()
        lienzo = pygame.Surface((960, 720))
        v.dibujar(lienzo, "PRUEBA")
        self.assertEqual(set(v.panel.botones), {"cerrar"})
        v.panel.modo = None
        with mock.patch.object(v, "_dibujar_nucleo", side_effect=AssertionError("NÚCLEO dentro del café")):
            v.dibujar(lienzo, "PRUEBA")
