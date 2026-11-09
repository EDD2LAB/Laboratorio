import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from bots.gestor_bots import GestorBots
from bots.navegador_bot import NavegadorBot
from multijugador.movimiento import ColisionesMapa, PartidaMovimiento
from multijugador.partida_local import ClienteCampanaLocal
from multijugador.protocolo import ROLES


class EspacioBotsTests(unittest.TestCase):
    def crear(self):
        p = PartidaMovimiento([dict(id=r, nombre=r, rol=r) for r in ROLES], 0,
                             ColisionesMapa({"hitboxes": [], "decoracion": []}), semilla=72)
        gestor = GestorBots(p, "guardian")
        for j in p.jugadores.values():
            j.update(x=480., y=380., animacion="reposo")
        return p, gestor

    def test_se_separan_sin_empujar_al_jugador(self):
        p, gestor = self.crear()
        for _ in range(50):
            gestor._separar_bots(.1)
        self.assertEqual((p.jugadores["guardian"]["x"], p.jugadores["guardian"]["y"]), (480, 380))
        posiciones = [(j["x"], j["y"]) for j in p.jugadores.values()]
        for i, (x, y) in enumerate(posiciones):
            for a, b in posiciones[i + 1:]:
                self.assertGreater(math.hypot(a - x, b - y), 25)

    def test_respeta_paredes_alcance_de_interaccion_y_velocidad(self):
        p, gestor = self.crear()
        p.colisiones.bloqueos = [(492, 300, 12, 180)]
        for bot in gestor.bots.values():
            bot.objetivo_actual = dict(x=480, y=380)
            bot.radio_objetivo = 28
        for _ in range(30):
            antes = {i: (b.posicion["x"], b.posicion["y"]) for i, b in gestor.bots.items()}
            gestor._separar_bots(.15)
            for i, bot in gestor.bots.items():
                x, y = bot.posicion["x"], bot.posicion["y"]
                self.assertFalse(p.colisiones.bloqueado(x, y))
                self.assertLessEqual(math.hypot(x - 480, y - 380), 28.001)
                self.assertLessEqual(math.hypot(x - antes[i][0], y - antes[i][1]), 3.001)

    def test_no_evade_personajes_de_otra_dimension(self):
        p, gestor = self.crear()
        p.jugadores["guardian"]["dimension"] = "presente"
        for indice, bot in enumerate(gestor.bots.values()):
            bot.posicion.update(x=480 + indice * 100)
        gestor._separar_bots(.15)
        self.assertEqual(gestor.bots["mensajero"].posicion["x"], 480)

    def test_deja_de_caminar_al_llegar(self):
        navegador = NavegadorBot(ColisionesMapa({"hitboxes": [], "decoracion": []}))
        jugador = dict(x=400, y=400, animacion="caminar")
        self.assertTrue(navegador.avanzar(jugador, (400, 400), .1))
        self.assertEqual(jugador["animacion"], "reposo")

    def test_dialogo_de_fuente_renueva_el_aviso_y_kael_puede_hablar(self):
        import uuid
        p = PartidaMovimiento([dict(id="a", nombre="A", rol="guardian"), dict(id="b", nombre="B", rol="habitante")], 0, semilla=72)
        m = p.mision
        m.ronda = 1
        m.pruebas = m.casos[1][4]
        m.metadatos_pruebas = m._metadatos(m.pruebas)
        npcs = {n["nombre"]: n for n in m.dialogos.publico()}
        self.assertEqual(sum(n["nombre"] == "Kael" for n in m.dialogos.publico()), 1)
        for nombre in ("Naira", "Kael"):
            npc = npcs[nombre]
            p.jugadores["a"].update(x=npc["x"], y=npc["y"])
            acuse = p.actuar("a", dict(accion="hablar_npc", npc=npc["id"], id_solicitud=uuid.uuid4().hex), 0)
            self.assertTrue(acuse["ok"], acuse)
        self.assertIn("pista_guardian", m.avisos_recientes["a"])
        self.assertGreater(m.avisos_recientes["a"]["pista_guardian"]["vence"], m.reloj)


class ClaridadInterfazTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((960, 720))

    def setUp(self):
        from interfaz.partida_multijugador import VistaPartida
        self.cliente = ClienteCampanaLocal("Jugador de prueba", "guardian", semilla=72)
        self.addCleanup(self.cliente.cerrar)
        self.vista = VistaPartida("local", self.cliente.eventos.get_nowait())
        self.vista.panel.modo = None

    def test_nombres_juntos_no_se_solapan_y_el_personaje_fuera_de_camara_no_tiene_etiqueta(self):
        for jugador in self.vista.jugadores.values():
            jugador["posicion"].update(450, 400)
        self.vista.estado["mundo"]["caso"]["npcs"] = [
            dict(id="naira", nombre="Naira", dimension="la_copa", x=450, y=400),
            dict(id="mira", nombre="Mira", dimension="la_copa", x=450, y=400)]
        self.vista.dibujar(pygame.Surface((960, 720)), "PRUEBA")
        etiquetas = self.vista.etiquetas_jugadores
        self.assertEqual(len(etiquetas), 4)
        self.assertEqual(len(self.vista.etiquetas_npc_actuales), 2)
        todas = etiquetas + self.vista.etiquetas_npc_actuales
        for i, e in enumerate(todas):
            for otra in todas[i + 1:]:
                self.assertFalse(e["rect"].colliderect(otra["rect"]))
        for i, e in enumerate(etiquetas):
            self.assertTrue(pygame.Rect(8, 60, 944, 584).contains(e["rect"]))
            self.assertFalse(e["rect"].colliderect(self.vista.boton_expediente.rect))
            for otra in etiquetas[i + 1:]:
                self.assertFalse(e["rect"].colliderect(otra["rect"]))
        self.vista.jugadores["bot_mensajero"]["posicion"].update(-1000, -1000)
        self.vista.dibujar(pygame.Surface((960, 720)), "PRUEBA")
        self.assertNotIn("bot_mensajero", [e["id"] for e in self.vista.etiquetas_jugadores])

    def test_boton_casos_funciona_con_detalles_cerrados_y_respeta_hud_oculto(self):
        v = self.vista
        self.assertFalse(v.mostrar_detalles)
        v.dibujar(pygame.Surface((960, 720)), "PRUEBA")
        centro = v.boton_expediente.rect.center
        self.assertTrue(v.cursor_interactivo(centro))
        clic = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1)
        self.assertTrue(v.manejar_evento(clic, centro, self.cliente))
        self.assertEqual(v.panel.modo, "expediente")
        v.panel.modo = None
        v.mostrar_hud = False
        self.assertFalse(v.cursor_interactivo(centro))
        v.manejar_evento(clic, centro, self.cliente)
        self.assertIsNone(v.panel.modo)

    def test_aspirante_es_kael_por_defecto_y_ayuda_cabe_en_la_pantalla(self):
        from interfaz.menu_pausa import CONTROLES, PAGINAS_COMO_JUGAR
        from nucleo.recursos import cargar_fuente, envolver_texto
        self.assertEqual(ClienteCampanaLocal._nombre_bot("aspirante"), "Kael · Aspirante")
        from multijugador.movimiento import es_personaje_jugable
        self.assertEqual(self.vista._clave_figura(dict(rol="aspirante", apariencia=None)), "aspirante")
        self.assertEqual(self.vista._clave_figura(dict(rol="aspirante", apariencia="mujer")), "aspirante_mujer")
        self.assertEqual(self.vista._clave_figura(dict(rol="aspirante", apariencia="hombre")), "aspirante")
        self.assertTrue(es_personaje_jugable("NPCS/Aspirante mujer/MujerAspirante Fila 2.png"))
        self.assertTrue(es_personaje_jugable("NPCS/Aspirante hombre/Fila 2. Aspirante_a_cacique-Idle.png"))
        self.assertIn("T", [tecla for tecla, _ in CONTROLES])
        fuente = cargar_fuente(16)
        for _, parrafos in PAGINAS_COMO_JUGAR:
            final = 150 + sum(len(envolver_texto(p, fuente, 680)) * (fuente.get_linesize() + 2) + 8 for p in parrafos)
            self.assertLess(final, 635)
