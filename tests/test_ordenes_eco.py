"""Ecos con destinatario, bots que obedecen los mensajes y juego a pantalla completa."""
import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

from bots.planificador_bot import ESPERA_ALIADO, PlanificadorBot  # noqa: E402
from multijugador.mision import MENSAJES, TODOS  # noqa: E402
from multijugador.partida_local import ClienteCampanaLocal  # noqa: E402
from nucleo import preferencias  # noqa: E402

TAREK = "bot_habitante"
MATEO = "bot_mensajero"
VEN_AL_CALDERO, AYUDAME, TENGO_PISTA, NO_DIFUNDIR = 1, 0, 2, 3


def tecla(codigo):
    return pygame.event.Event(pygame.KEYDOWN, key=codigo, mod=0, unicode="", scancode=0)


class Base(unittest.TestCase):
    def setUp(self):
        self.cliente = ClienteCampanaLocal("Prueba", "guardian")
        self.partida = self.cliente._partida
        self.mision = self.partida.mision
        self.caldero = next(o for o in self.mision.objetivos if o["id"] == "caldero")
        self.eco = next(o for o in self.mision.objetivos if o["tipo"] == "eco")
        self.yo = self.partida.jugadores["local"]
        self.yo.update(x=self.eco["x"], y=self.eco["y"])

    def bot(self, identificador):
        return self.cliente._bots.bots[identificador]

    def eco_a(self, mensaje, destinatario=TODOS):
        self.yo.update(x=self.eco["x"], y=self.eco["y"])
        self.cliente._ahora += 3  # fuera de la espera de dos segundos entre ecos
        self.cliente.actuar("eco", mensaje=mensaje, destinatario=destinatario)

    def avanzar_hasta(self, condicion, descripcion, limite=500):
        for _ in range(limite):
            if condicion():
                return
            self.cliente.actualizar(0.15)
        self.fail("No ocurrió: " + descripcion)

    def en_caldero(self, identificador):
        j = self.partida.jugadores[identificador]
        return math.hypot(j["x"] - self.caldero["x"], j["y"] - self.caldero["y"]) <= 68

    def dar_pistas(self, identificador):
        """Deja al bot con dos pistas y al equipo listo para elegir."""
        rol = self.partida.jugadores[identificador]["rol"]
        for pista, origen in (("pista_" + rol, identificador), ("pista_guardian", "local")):
            self.mision.conocidas[identificador].add(pista)
            self.mision.halladas[pista] = origen
        self.mision.entregas.append({"emisor": "local", "receptor": identificador,
                                     "pista": "pista_guardian", "medio": "directo"})


class EcoServidorTests(Base):
    def avisos(self, identificador):
        return [a for a in self.mision.privado(identificador)["avisos"] if a["tipo"] == "eco"]

    def test_mensaje_a_una_persona_solo_llega_a_ella(self):
        self.eco_a(0, TAREK)
        self.assertEqual(len(self.avisos(TAREK)), 1)
        self.assertEqual(self.avisos(MATEO), [])

    def test_mensaje_a_todos_llega_a_todos(self):
        self.eco_a(1)
        self.assertEqual(len(self.avisos(TAREK)), 1)
        self.assertEqual(len(self.avisos(MATEO)), 1)

    def test_destinatario_invalido_se_rechaza(self):
        self.eco_a(1, "nadie")
        self.cliente._ahora += 3
        self.assertEqual(self.avisos(TAREK), [])

    def test_pista_por_tronco_a_todos(self):
        self.mision.conocidas["local"].add("pista_guardian")
        self.mision.halladas["pista_guardian"] = "local"
        self.cliente.actuar("entregar", pista="pista_guardian", destinatario=TODOS, medio="eco")
        for bot in self.cliente._bots.bots:
            self.assertIn("pista_guardian", self.mision.conocidas[bot])

    def test_a_todos_solo_es_posible_por_tronco(self):
        self.mision.conocidas["local"].add("pista_guardian")
        self.mision.halladas["pista_guardian"] = "local"
        self.cliente.actuar("entregar", pista="pista_guardian", destinatario=TODOS, medio="directo")
        self.assertNotIn("pista_guardian", self.mision.conocidas[TAREK])


class BotsObedecenTests(Base):
    def test_ven_al_caldero_trae_y_hace_elegir_al_bot_lejano(self):
        fuente = next(o for o in self.mision.objetivos if o.get("rol") == "habitante")
        x, y = self.partida.colisiones.inicio_libre(fuente["x"], fuente["y"], [])  # junto a Luma, no sobre ella
        self.partida.jugadores[TAREK].update(x=x, y=y)
        self.dar_pistas(TAREK)
        self.eco_a(VEN_AL_CALDERO, TAREK)
        self.avanzar_hasta(lambda: self.en_caldero(TAREK), "Tarek llega al caldero")
        self.avanzar_hasta(lambda: TAREK in self.mision.votos, "Tarek elige")

    def test_la_orden_solo_la_cumple_el_destinatario(self):
        self.eco_a(VEN_AL_CALDERO, TAREK)
        self.cliente.actualizar(0.15)
        self.assertIsNotNone(self.bot(TAREK).orden)
        self.assertIsNone(self.bot(MATEO).orden)

    def test_ven_al_caldero_interrumpe_la_tarea_actual_de_inmediato(self):
        self.eco_a(VEN_AL_CALDERO, TAREK)
        self.cliente.actualizar(0.15)
        self.assertEqual(self.bot(TAREK).estado, "YENDO_AL_CALDERO")

    def test_sin_dos_pistas_las_busca_y_vuelve_a_elegir(self):
        self.eco_a(VEN_AL_CALDERO)
        self.partida.jugadores[TAREK].update(x=self.caldero["x"], y=self.caldero["y"] + 40)
        self.cliente.actualizar(0.15)
        self.assertTrue(self.bot(TAREK).convocado)
        self.assertIsNone(self.bot(TAREK).orden)

    def test_ayudame_lo_lleva_con_quien_llamo_y_le_da_su_pista(self):
        self.mision.conocidas[TAREK].add("pista_habitante")
        self.mision.halladas["pista_habitante"] = TAREK
        self.eco_a(AYUDAME, TAREK)
        self.avanzar_hasta(lambda: "pista_habitante" in self.mision.conocidas["local"], "recibe la pista de Tarek")

    def test_tengo_una_pista_lo_acerca_a_quien_llamo(self):
        self.eco_a(TENGO_PISTA, MATEO)
        cerca = lambda: math.hypot(self.partida.jugadores[MATEO]["x"] - self.yo["x"],
                                   self.partida.jugadores[MATEO]["y"] - self.yo["y"]) <= 60
        self.avanzar_hasta(cerca, "Mateo se acerca")

    def test_no_difundamos_impide_elegir_difundir(self):
        self.dar_pistas(TAREK)
        confirman = [{"metadatos": {"confirma_riesgo_actual": True}}] * 2
        self.assertEqual(PlanificadorBot.mejor_opcion(confirman), "difundir")
        self.assertNotEqual(PlanificadorBot.mejor_opcion(confirman, ("difundir",)), "difundir")
        self.eco_a(NO_DIFUNDIR, TAREK)
        self.cliente.actualizar(0.15)
        self.assertTrue(self.bot(TAREK).sin_difundir)
        self.assertFalse(self.bot(MATEO).sin_difundir)

    def test_las_ordenes_no_pasan_al_siguiente_caso(self):
        bot = self.bot(TAREK)
        self.eco_a(NO_DIFUNDIR, TAREK)
        self.cliente.actualizar(0.15)
        self.mision.ronda = 1
        self.mision.encargo = None
        self.mision.pruebas = self.mision.casos[1][4]
        self.cliente.actualizar(0.15)
        self.assertFalse(bot.sin_difundir)


class EleccionSinBloqueoTests(Base):
    def test_elige_aunque_las_pistas_no_sean_concluyentes(self):
        pistas = [{"metadatos": {"confirma_riesgo_actual": True}},
                  {"metadatos": {"indica_descontextualizacion": True}}]
        self.assertIsNone(PlanificadorBot.proponer_decision(pistas)["accion_propuesta"])
        self.assertIn(PlanificadorBot.mejor_opcion(pistas), ("difundir", "descartar"))

    def test_si_alguien_ya_eligio_el_bot_tambien_elige(self):
        self.dar_pistas(TAREK)
        self.bot(TAREK).sin_ayuda = True
        self.bot(TAREK).compartidas[0] = set(self.partida.jugadores)
        self.mision.votos["local"] = "corregir"
        self.avanzar_hasta(lambda: TAREK in self.mision.votos, "Tarek elige como el resto")

    def test_tarek_no_se_queda_esperando_compañero_para_siempre(self):
        bot = self.bot(TAREK)
        for otro in (MATEO, "bot_aspirante"):
            self.bot(otro).reemplaza_humano = True  # sin bots que acudan a ayudarlo
        self.mision.conocidas[TAREK].add("pista_habitante")
        self.mision.halladas["pista_habitante"] = TAREK
        pasos = round((ESPERA_ALIADO + 15) / 0.15)
        self.avanzar_hasta(lambda: bot.sin_ayuda, "Tarek deja de esperar", limite=pasos)
        self.assertNotIn(bot.identificador, self.cliente._bots.memoria.solicitudes_ayuda)


class DecisionHumanaTests(Base):
    def test_la_pocion_es_la_que_eligio_la_persona_aunque_los_bots_voten_otra(self):
        presentes = set(self.partida.jugadores)
        self.mision.votos.update({i: "corregir" for i in self.cliente._bots.bots})
        self.mision.votos["local"] = "descartar"
        self.mision.resolver(presentes)
        self.assertEqual(self.mision.resultado["opcion"], "descartar")
        self.assertEqual(self.mision.resultado["tipo_pocion"], "ignorar")

    def test_sin_el_voto_de_todos_no_se_resuelve(self):
        self.mision.votos["local"] = "descartar"
        self.mision.resolver(set(self.partida.jugadores))
        self.assertIsNone(self.mision.resultado)


class SelectorDestinoTests(Base):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.parche = mock.patch.object(preferencias, "ARCHIVO", Path(self.tmp.name) / "prefs.json")
        self.parche.start()
        pygame.init()
        pygame.display.set_mode((960, 720))
        from interfaz.partida_multijugador import VistaPartida
        self.vista = VistaPartida("local", self.cliente.eventos.get_nowait())
        self.lienzo = pygame.Surface((960, 720))
        self.panel = self.vista.panel

    def tearDown(self):
        pygame.quit()
        self.parche.stop()
        self.tmp.cleanup()

    def nombre_actual(self):
        destinos = self.panel.destinos_eco()
        return destinos[self.panel.indice_destino % len(destinos)]["nombre"]

    def test_flechas_recorren_todos_y_cada_companero(self):
        self.panel.abrir("eco_mensajes")
        self.panel.indice_destino = 0
        self.assertEqual(self.nombre_actual(), "Todos")
        vistos = set()
        for _ in range(4):
            vistos.add(self.nombre_actual())
            self.assertTrue(self.vista.manejar_evento(tecla(pygame.K_RIGHT), (0, 0), self.cliente))
            self.vista.dibujar(self.lienzo, "PRUEBA")
        self.assertEqual(len(vistos), 4)
        self.assertEqual(self.nombre_actual(), "Todos")  # da la vuelta
        self.vista.manejar_evento(tecla(pygame.K_LEFT), (0, 0), self.cliente)
        self.assertNotEqual(self.nombre_actual(), "Todos")

    def test_el_mensaje_sale_para_el_destinatario_elegido(self):
        self.panel.abrir("eco_mensajes")
        self.panel.indice_destino = 1
        self.vista.dibujar(self.lienzo, "PRUEBA")
        boton = self.panel.botones["eco:" + str(VEN_AL_CALDERO)]
        cliente = mock.Mock()
        clic = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=boton.rect.center)
        self.panel.manejar(clic, boton.rect.center, cliente)
        cliente.actuar.assert_called_once_with("eco", mensaje=VEN_AL_CALDERO,
                                               destinatario=self.panel.destinatarios()[0]["id"])

    def test_junto_a_un_tronco_la_pista_puede_ir_a_todos(self):
        self.cliente.actualizar(0.15)
        ultimo = None
        while not self.cliente.eventos.empty():
            evento = self.cliente.eventos.get_nowait()
            ultimo = evento if evento.get("tipo") == "estado" else ultimo
        self.vista.recibir(ultimo)
        self.panel.abrir("inventario")
        self.assertEqual(self.panel.destinos_pista()[0]["id"], TODOS)


class PantallaYMenuTests(unittest.TestCase):
    def test_el_lienzo_ocupa_toda_la_ventana(self):
        from interfaz.presentacion_pantalla import a_lienzo, presentar
        pygame.init()
        pantalla = pygame.display.set_mode((1920, 1080))
        lienzo = pygame.Surface((960, 720))
        lienzo.fill((200, 10, 10))
        presentar(pantalla, lienzo)
        for punto in ((0, 0), (1919, 0), (0, 1079), (1919, 1079), (5, 540), (1915, 540)):
            self.assertEqual(pantalla.get_at(punto)[:3], (200, 10, 10), punto)
        self.assertEqual(a_lienzo((1920, 1080), (1920, 1080)), (960, 720))
        self.assertEqual(a_lienzo((960, 540), (1920, 1080)), (480, 360))
        pygame.quit()

    def test_el_menu_ya_no_ofrece_un_jugador(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(preferencias, "ARCHIVO", Path(tmp) / "prefs.json"):
            pygame.init()
            from interfaz.inicio import MenuInicio
            menu = MenuInicio()
            menu.dibujar()
            self.assertEqual(set(menu.botones), {"campana_local", "multi", "ajustes", "ayuda_f1", "salir"})
            menu.accionar("ajustes")
            menu.dibujar()
            self.assertIn("pausa:como_jugar", menu.botones)
            menu.accionar("pausa:como_jugar")
            for pagina in range(3):
                menu.accionar(f"pausa:pagina:{pagina}")
                menu.dibujar()
                self.assertEqual(menu.pausa.pagina_ayuda, pagina)
            menu.pausa.tecla(pygame.K_ESCAPE)
            self.assertEqual(menu.pausa.vista, "ajustes")
            menu.limpiar_conexion()
            pygame.quit()


class MensajesTests(unittest.TestCase):
    def test_hay_una_orden_por_mensaje(self):
        from multijugador.mision import ORDENES_ECO
        self.assertEqual(len(ORDENES_ECO), len(MENSAJES))


if __name__ == "__main__":
    unittest.main()
