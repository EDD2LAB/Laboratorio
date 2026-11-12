"""Preparación física, combate autoritativo y secuencia final compartida."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import unittest
import uuid
import test_final_cooperativo as base


class Aventura(unittest.TestCase):
    def setUp(self):
        self.p = base.partida()
        self.f = self.p.mision.futuro.final
        self.a = self.f.aventura

    def accion(self, op, rol="guardian", **datos):
        return self.p.actuar(rol, dict(accion="final_accion", operacion=op, ronda_final=self.f.ronda,
                             id_solicitud=uuid.uuid4().hex, **datos), self.p.ultima)

    def colocar(self, punto, rol="guardian"):
        self.p.jugadores[rol].update(x=punto["x"], y=punto["y"], interior=None)

    def fabricar(self):
        self.a.fabricado = False
        for _ in range(3):
            pieza = self.a.materiales()[0]
            self.colocar(pieza)
            self.assertTrue(self.accion("material", pieza=pieza["id"])["ok"])
            self.colocar(self.a.puntos["mensajero"])
            self.assertTrue(self.accion("depositar")["ok"])
        self.assertTrue(self.accion("fabricar")["ok"])

    def test_tres_piezas_reales_y_fabricacion_antes_de_batalla(self):
        self.a.fabricado = False
        self.colocar(self.f.puntos["aspirante"])
        self.assertFalse(self.accion("iniciar")["ok"])
        self.fabricar()
        self.assertEqual(self.a.municion, 12)
        self.colocar(self.f.puntos["aspirante"])
        self.assertTrue(self.accion("iniciar")["ok"])

    def test_eras_incompletas_impiden_preparacion_y_batalla(self):
        self.p.mision.resultado = None
        self.a.fabricado = False
        self.colocar(self.a.materiales()[0])
        self.assertFalse(self.accion("material", pieza=self.a.materiales()[0]["id"])["ok"])
        self.assertIn("La Copa", self.a.faltan)

    def test_no_se_recogen_piezas_a_distancia_ni_dos_por_persona(self):
        self.a.fabricado = False
        pieza = self.a.materiales()[0]
        self.p.jugadores["guardian"].update(x=0, y=0)
        self.assertFalse(self.accion("material", pieza=pieza["id"])["ok"])
        self.colocar(pieza)
        self.assertTrue(self.accion("material", pieza=pieza["id"])["ok"])
        otra = self.a.materiales()[0]
        self.colocar(otra)
        self.assertFalse(self.accion("material", pieza=otra["id"])["ok"])

    def test_desconexion_devuelve_pieza_al_mundo(self):
        self.a.fabricado = False
        pieza = self.a.materiales()[0]
        self.colocar(pieza)
        self.accion("material", pieza=pieza["id"])
        self.p.conectados.discard("guardian")
        self.p.actualizar(self.p.ultima + .1)
        self.assertFalse(self.a.cargas)
        self.assertIn(pieza["id"], [m["id"] for m in self.a.materiales()])

    def combate(self):
        self.colocar(self.f.puntos["aspirante"])
        self.assertTrue(self.accion("iniciar")["ok"])
        self.a.generar_en = 9999
        j = self.p.jugadores["guardian"]
        self.a.minis = [dict(id=1, x=j["x"], y=j["y"], vida=2, aviso=3)]

    def test_dos_impactos_consumen_municion_compartida_y_desactivan(self):
        self.combate()
        self.assertFalse(self.accion("disparar", mini=True)["ok"])
        self.assertTrue(self.accion("disparar", mini=1)["ok"])
        self.assertFalse(self.accion("disparar", mini=1)["ok"])
        self.f.reloj += 1
        self.assertTrue(self.accion("disparar", mini=1)["ok"])
        self.assertFalse(self.a.minis)
        self.assertEqual(self.a.municion, 11)

    def test_disparo_sin_linea_de_vision_no_consume_cargas(self):
        self.combate()
        self.p.mision.linea_final = lambda *args: False
        self.assertFalse(self.accion("disparar", mini=1)["ok"])
        self.assertEqual(self.a.municion, 12)

    def test_sin_municion_no_bloquea_minijuegos_y_caja_tiene_limite(self):
        self.combate()
        self.a.municion = 0
        self.assertFalse(self.accion("disparar", mini=1)["ok"])
        self.f.batalla.turno, self.f.batalla.restante = "recarga", 15
        self.colocar(self.f.puntos["guardian"])
        self.assertTrue(self.accion("comparar", campo=base.respuesta_guardian(self.f))["ok"])
        self.colocar(self.f.puntos["mensajero"])
        self.assertTrue(self.accion("municion")["ok"])
        self.assertFalse(self.accion("municion")["ok"])
        self.assertEqual(self.a.municion, 6)

    def test_minis_se_detienen_durante_la_pausa(self):
        self.combate()
        self.f.batalla.turno, self.f.batalla.restante = "recarga", 26
        self.a.minis[0]["aviso"] = .01
        self.p.actualizar(self.p.ultima + .2)
        self.assertEqual(self.f.integridad, 3)
        self.assertEqual(self.a.minis[0]["aviso"], .01)

    def test_ultima_tarea_abre_la_reconfiguracion_sin_confirmar(self):
        self.f.fase = "activo"
        self.f.ronda = 1
        self.f.verde.update(base.ROLES)
        self.f.batalla.reiniciar(self.f.hechos, self.f.verde)
        self.f.batalla.turno, self.f.batalla.restante = "recarga", 14
        self.f.hechos.update(("guardian", "habitante", "mensajero"))
        self.f.propuesta = {c: next(v for v in vs if base.opcion_correcta(c, v)) for c, vs in self.f.opciones.items()}
        self.colocar(self.f.puntos["aspirante"], "aspirante")
        self.assertTrue(self.accion("autorizar", "aspirante")["ok"])
        self.assertEqual(self.f.fase, "victoria")
        self.assertEqual(self.a.etapa, "reconfiguracion")

    def test_secuencia_compartida_y_rechazo_de_avance_retrasado(self):
        self.f.fase = "victoria"
        self.a.victoria()
        revision = self.a.revision
        self.assertFalse(self.accion("continuar", revision_cierre=True)["ok"])
        self.assertTrue(self.accion("continuar", revision_cierre=revision)["ok"])
        self.assertFalse(self.accion("continuar", revision_cierre=revision)["ok"])
        while self.a.etapa != "creditos":
            self.assertTrue(self.accion("continuar", revision_cierre=self.a.revision)["ok"])
        for i in self.p.jugadores:
            self.assertEqual(self.p.estado(i)["caso"]["futuro"]["desafio_final"]["aventura"]["cierre"]["etapa"], "creditos")

    def test_bots_recolectan_y_fabrican_sin_teletransporte(self):
        from bots.gestor_bots import GestorBots
        self.a.fabricado, self.a.municion = False, 0
        gestor = GestorBots(self.p, set(), "normal")
        for _ in range(2500):
            self.p.actualizar(self.p.ultima + .1)
            gestor.actualizar(self.p.ultima, .1)
            if self.a.fabricado:
                break
        self.assertTrue(self.a.fabricado, [(b.rol, b.ultimo_error) for b in gestor.bots.values()])


class Pantallas(unittest.TestCase):
    def test_cierre_completo_con_creditos_vacios_e_informe(self):
        import pygame
        from test_final_capacidad import ocho_resueltos
        from interfaz.partida_multijugador import VistaPartida
        from interfaz.desenlace import pantalla
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        p = ocho_resueltos()
        f = p.mision.futuro.final
        f.fase = "victoria"
        f.aventura.victoria()
        v = VistaPartida("0", {"mundo": p.estado("0")})
        v.cambiar_dimension("futuro")
        v.panel.informe = p.mision.informe()
        ui = pantalla(v.panel)
        for etapa in ("reconfiguracion", "epilogo", "informe", "pantalla", "creditos"):
            f.aventura.etapa, f.aventura.indice = etapa, 0
            v.recibir({"mundo": p.estado("0")})
            v.panel.modo = "desenlace"
            s = pygame.Surface((960, 720))
            v.panel.dibujar(s)
            self.assertTrue(v.panel.botones)
            for b in v.panel.botones.values():
                self.assertTrue(s.get_rect().contains(b.rect), (etapa, b.rect))
        self.assertEqual(ui.resultado.casos, 8)
        # Reconexión directamente en el resultado, sin el informe en caché.
        v.panel.informe = None
        ui.resultado = None
        p.jugadores["3"]["apariencia"] = "mujer"
        f.aventura.etapa = "pantalla"
        v.recibir({"mundo": p.estado("0")})
        v.panel.modo = "desenlace"
        v.panel.dibujar(pygame.Surface((960, 720)))
        self.assertEqual(ui.resultado.casos, 8)
        self.assertEqual(ui.resultado.lider, "Mira")
