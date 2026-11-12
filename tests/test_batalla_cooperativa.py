"""Reglas reales de las tandas, pausas y cooperación, sin alterar paredes."""
import unittest
from multijugador.batalla_cooperativa import BatallaCooperativa
import test_final_cooperativo as base


class Tandas(unittest.TestCase):
    def setUp(self):
        self.b = BatallaCooperativa()
        self.j = {"a": dict(x=100, y=100, dimension="futuro", interior=None),
                  "b": dict(x=200, y=100, dimension="futuro", interior=None)}

    def tick(self, dt=1, hechos=None):
        return self.b.actualizar(dt, self.j, set(self.j), hechos or set())

    def test_avisos_fijos_permiten_esquivar_y_no_hacen_dano_antes_del_impacto(self):
        self.assertEqual(self.tick(), [])
        self.j["a"]["y"] += 60
        self.tick()
        self.assertEqual(self.b.blancos[0], [100, 100])
        self.assertEqual(self.tick(), ["b"])
        self.assertEqual(self.b.turno, "rayo")

    def test_recarga_segura_y_recuperacion_automatica(self):
        for _ in range(3):
            self.tick()
        self.assertEqual(self.b.derribados, set(self.j))
        self.tick()
        self.assertEqual(self.b.turno, "recarga")
        self.assertFalse(self.b.derribados)
        for _ in range(25):
            self.assertFalse(self.tick())
        self.assertEqual(self.b.turno, "recarga")
        self.tick()
        self.assertEqual(self.b.turno, "aviso")

    def test_roja_tiene_dos_tandas_anunciadas_antes_de_la_pausa(self):
        hechos = {"guardian", "habitante"}
        for _ in range(3):
            self.tick(hechos=hechos)
        self.assertEqual(self.b.fase, 2)
        self.assertEqual(self.b.turno, "rayo")
        self.tick(hechos=hechos)
        self.assertEqual((self.b.turno, self.b.oleada), ("aviso", 2))
        for _ in range(3):
            self.tick(hechos=hechos)
        self.assertEqual(self.b.turno, "rayo")
        self.tick(hechos=hechos)
        self.assertEqual(self.b.turno, "recarga")

    def test_finalizar_las_tareas_detiene_los_rayos(self):
        self.tick(hechos={"guardian", "habitante", "mensajero", "aspirante"})
        self.assertEqual(self.b.turno, "terminado")
        self.assertFalse(self.b.blancos)

    def test_no_apunta_a_interiores_otros_mapas_o_desconectados(self):
        self.j["a"]["interior"] = "cafe"
        self.b.actualizar(1, self.j, {"a"}, set())
        self.assertFalse(self.b.blancos)


class IntegracionBatalla(unittest.TestCase):
    def setUp(self):
        self.reglas = base.ReglasFinal()
        self.reglas.setUp()
        self.p, self.f = self.reglas.p, self.reglas.f

    def test_empezar_abre_aviso_y_bloquea_consola_hasta_recarga(self):
        r = self.reglas
        self.assertTrue(r.accion("guardian", "iniciar")["ok"])
        self.assertFalse(r.accion("guardian", "comparar", campo=self.f.campo_falso)["ok"])
        self.f.batalla.turno, self.f.batalla.restante = "recarga", 26
        self.assertTrue(r.accion("guardian", "comparar", campo=self.f.campo_falso)["ok"])

    def test_mensajero_y_aspirante_esperan_el_escudo(self):
        r = self.reglas
        r.iniciar()
        r.guardian()
        self.assertFalse(r.accion("mensajero", "recoger")["ok"])
        self.assertFalse(r.accion("aspirante", "elegir", campo="prueba", valor="informe")["ok"])
        r.habitante()
        self.assertEqual(self.f.batalla.fase, 2)

    def test_ayudar_exige_proximidad_y_un_caido_real(self):
        r = self.reglas
        r.iniciar()
        j, otro = self.p.jugadores["guardian"], self.p.jugadores["habitante"]
        otro.update(x=200, y=200)
        j.update(x=205, y=200)
        self.f.batalla.derribados.add("habitante")
        self.assertTrue(r.accion("guardian", "auxiliar", colocar=False, aliado="habitante")["ok"])
        self.assertFalse(r.accion("guardian", "auxiliar", colocar=False, aliado="habitante")["ok"])
        self.f.batalla.derribados.add("habitante")
        j.update(x=500, y=500)
        self.assertFalse(r.accion("guardian", "auxiliar", colocar=False, aliado="habitante")["ok"])

    def test_caido_no_se_mueve_hasta_recuperarse(self):
        self.reglas.iniciar()
        j = self.p.jugadores["guardian"]
        antes = j["x"], j["y"]
        self.f.batalla.derribados.add("guardian")
        self.p.recibir("guardian", dict(dx=1, dy=0, seq=10), self.p.ultima)
        self.p.actualizar(self.p.ultima + .1)
        self.assertEqual((j["x"], j["y"]), antes)

    def test_pausa_no_recibe_dano_de_los_pulsos_antiguos(self):
        self.reglas.iniciar()
        self.f.portador = "mensajero"
        j = self.p.jugadores["mensajero"]
        self.f.actualizar(.1, self.p.jugadores, [(j["x"], j["y"])], self.p.mision._cerca_presente)
        self.assertEqual(self.f.integridad, 3)

    def test_reintentar_en_roja_conserva_fase_y_recorrido(self):
        self.reglas.iniciar()
        self.f.hechos.update(("guardian", "habitante"))
        self.f.tramo = 1
        for _ in range(3):
            self.f._fallo("Sin señal")
        self.assertTrue(self.reglas.accion("guardian", "reintentar")["ok"])
        self.assertEqual(self.f.batalla.fase, 2)
        self.assertEqual(self.f.tramo, 1)
        self.assertEqual(self.f.integridad, 3)

    def test_bot_fuera_del_peligro_ayuda_al_companero_cercano(self):
        from types import SimpleNamespace
        from bots.final_cooperativo import planificar
        from bots.planificador_bot import PlanificadorBot
        self.reglas.iniciar()
        self.f.batalla.turno = "rayo"
        self.f.batalla.blancos = [[100, 100]]
        self.f.batalla.derribados = {"habitante"}
        self.p.jugadores["guardian"].update(x=150, y=100)
        self.p.jugadores["habitante"].update(x=100, y=100)
        bot = SimpleNamespace(identificador="guardian", rol="guardian", posicion=self.p.jugadores["guardian"])
        plan = planificar(bot, self.p.estado("guardian"), list(self.p.jugadores.values()), PlanificadorBot._tarea)
        self.assertEqual(plan["datos"]["operacion"], "auxiliar")
        self.assertEqual(plan["datos"]["aliado"], "habitante")

    def test_cliente_cierra_consola_al_atacar_y_no_predice_movimiento_del_caido(self):
        import pygame
        from types import SimpleNamespace
        from unittest.mock import patch
        from interfaz.partida_multijugador import VistaPartida
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        self.reglas.iniciar()
        self.f.batalla.turno = "aviso"
        self.f.batalla.derribados.add("guardian")
        v = VistaPartida("guardian", {"mundo": self.p.estado("guardian")})
        v.cambiar_dimension("futuro")
        v.transicion = None
        v.panel.modo = "final_cooperativo"
        controles = []
        cliente = SimpleNamespace(mover=lambda *args: controles.append(args), actuar=lambda *a, **k: None)
        with patch("pygame.key.get_focused", return_value=True), patch("pygame.key.get_pressed", return_value={pygame.K_d: True}):
            v.actualizar(.016, cliente)
            self.assertIsNone(v.panel.modo)
            self.assertEqual(controles[-1][:2], (0, 0))
            self.f.batalla.derribados.clear()
            v.recibir({"mundo": self.p.estado("guardian")})
            v.transicion = None
            v.actualizar(.016, cliente)
            self.assertEqual(controles[-1][:2], (1, 0))
