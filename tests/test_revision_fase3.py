"""Bloque D: Ciudad Núcleo completa, viaje libre y trabajo del equipo tras la unión."""
import os
import unittest
import uuid
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from bots.gestor_bots import GestorBots  # noqa: E402
from multijugador.dimensiones_red import FUTURO, LA_COPA, PRESENTE, jugadores_visibles, rect_portal  # noqa: E402
from multijugador.movimiento import MULTIPLICADOR_CORRER, PartidaMovimiento  # noqa: E402
from multijugador.nucleo import (CUENTA_REAL, CUENTAS_AUTOMATICAS, FIRMA, GUIA_FIRMAS, LLAVE, RADIO_PULSO,  # noqa: E402
                                 REGISTRO_FALSO)
from multijugador.protocolo import ROLES  # noqa: E402


def partida(roles=ROLES):
    p = PartidaMovimiento([dict(id=str(i), nombre="J" + str(i), rol=r) for i, r in enumerate(roles)], 0)
    p._viajar_equipo(LA_COPA, FUTURO)
    p.actualizar(.05)
    return p, p.mision.futuro


def accion(p, i, nombre, **datos):
    return p.actuar(i, dict(accion=nombre, id_solicitud=uuid.uuid4().hex, ronda=p.mision.ronda, **datos), p.ultima)


def ir(p, i, punto):
    p.jugadores[i].update(x=float(punto["x"]), y=float(punto["y"]))


def objetivo(m, tarea):
    return next(o for o in m.objetivos if o.get("tarea") == tarea)


def npc(m, nombre):
    return next(n for n in m.npcs if n["nombre"] == nombre)


def lejos_de_pulsos(m):
    return {"x": 480, "y": 700}


class Personajes(unittest.TestCase):
    def test_archivista_y_representante_responden_por_dialogos(self):
        p, m = partida()
        for nombre, pista in (("Archivista", GUIA_FIRMAS), ("Representante Humano", FIRMA)):
            ir(p, "0", npc(m, nombre))
            acuse = accion(p, "0", "hablar_npc", npc=npc(m, nombre)["id"])
            self.assertEqual(acuse["vista"], "dialogo_npc")
            self.assertIn(pista, m.halladas)

    def test_sin_el_representante_no_se_vota_reconfigurar(self):
        p, m = partida(("guardian",))
        m.tareas.update({t: "0" for t in ("conexiones", "archivos", "llave", "cuentas")})
        ir(p, "0", m.pantalla)
        self.assertFalse(accion(p, "0", "presente_votar", opcion="verificar")["ok"])
        self.assertTrue(accion(p, "0", "presente_votar", opcion="dejar_pendiente")["ok"])
        ir(p, "0", npc(m, "Representante Humano"))
        accion(p, "0", "hablar_npc", npc=npc(m, "Representante Humano")["id"])
        ir(p, "0", m.pantalla)
        self.assertTrue(accion(p, "0", "presente_votar", opcion="verificar")["ok"])
        self.assertTrue(m.completada)


class Cuentas(unittest.TestCase):
    def setUp(self):
        self.p, self.m = partida()
        ir(self.p, "0", objetivo(self.m, "cuentas"))

    def enviar(self, cuentas):
        return accion(self.p, "0", "futuro_resolver", terminal="cuentas", cuentas=cuentas)

    def test_se_abre_hablando_con_el_ciudadano(self):
        dialogo = accion(self.p, "0", "hablar_npc", npc=npc(self.m, "Ciudadano Conectado")["id"])["dialogo"]
        acuse = accion(self.p, "0", "responder_npc", npc=dialogo["npc"], respuesta=dialogo["respuestas"][0])
        self.assertEqual((acuse["vista"], acuse["terminal"]), ("terminal", "cuentas"))

    def test_exige_las_tres_automaticas_exactas(self):
        for cuentas in (["voz_1", "voz_2"], [CUENTA_REAL, "voz_1", "voz_2"], sorted(CUENTAS_AUTOMATICAS | {CUENTA_REAL})):
            self.assertTrue(self.enviar(cuentas)["ok"])
            self.assertNotIn("cuentas", self.m.tareas)
        self.assertTrue(self.enviar(sorted(CUENTAS_AUTOMATICAS))["ok"])
        self.assertIn("cuentas", self.m.tareas)

    def test_rechaza_duplicados_y_datos_invalidos(self):
        for cuentas in (["voz_1", "voz_1", "voz_2"], ["nadie"], "voz_1", [1, 2, 3]):
            self.assertFalse(self.enviar(cuentas)["ok"], cuentas)

    def test_rechaza_marcar_fuera_de_la_dimension(self):
        self.p.jugadores["0"]["dimension"] = PRESENTE
        self.assertFalse(self.enviar(sorted(CUENTAS_AUTOMATICAS))["ok"])
        self.assertNotIn("cuentas", self.m.tareas)


class Barreras(unittest.TestCase):
    def test_bloquean_hasta_restaurar_las_conexiones(self):
        p, m = partida()
        self.assertTrue(m.barreras_activas)
        self.assertTrue(m.barreras)
        rechazo = accion(p, "0", "entrar_edificio", edificio="estudio_lia")
        self.assertFalse(rechazo["ok"])
        self.assertIn("bloqueó", rechazo["mensaje"])
        ir(p, "0", objetivo(m, "conexiones"))
        accion(p, "0", "futuro_resolver", terminal="conexiones", arista=1)
        self.assertFalse(m.barreras_activas)
        self.assertIsNotNone(m.barreras_evento)

    def test_jugadores_de_otra_dimension_no_reciben_las_barreras_en_su_contexto(self):
        from interfaz.partida_multijugador import VistaPartida
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        p = PartidaMovimiento([dict(id="0", nombre="A", rol="guardian")], 0)
        v = VistaPartida("0", {"mundo": p.estado("0")})
        self.assertNotIn("barreras", v.contexto())


class Pulsos(unittest.TestCase):
    def test_un_pulso_devuelve_la_llave_al_corredor(self):
        p, m = partida()
        m.halladas[LLAVE] = "0"
        x, y = m.posiciones_pulsos()[0]
        p.jugadores["0"].update(x=x + RADIO_PULSO - 2, y=y)
        m.actualizar(0, p.jugadores)
        self.assertIsNone(m.portador)

    def test_lejos_de_los_pulsos_se_conserva_y_se_entrega(self):
        p, m = partida()
        m.halladas[LLAVE] = "0"
        ir(p, "0", lejos_de_pulsos(m))
        m.actualizar(.1, p.jugadores)
        self.assertEqual(m.portador, "0")
        ir(p, "0", objetivo(m, "llave"))
        accion(p, "0", "interactuar", objetivo="futuro:llave")
        self.assertIn("llave", m.tareas)

    def test_los_pulsos_se_mueven_a_velocidad_constante_por_las_rutas(self):
        _, m = partida()
        self.assertTrue(m.rutas_pulso)
        antes = m.posiciones_pulsos()
        m.actualizar(.5, {})
        self.assertNotEqual(antes, m.posiciones_pulsos())

    def test_otra_persona_no_entrega_la_llave_ajena(self):
        p, m = partida()
        m.halladas[LLAVE] = "1"
        ir(p, "0", objetivo(m, "llave"))
        accion(p, "0", "interactuar", objetivo="futuro:llave")
        self.assertNotIn("llave", m.tareas)


class Habilidades(unittest.TestCase):
    def setUp(self):
        self.p, self.m = partida()

    def usar(self, i):
        return accion(self.p, i, "habilidad")

    def test_lupa_resalta_el_registro_falso_y_respeta_la_recarga(self):
        ir(self.p, "0", objetivo(self.m, "archivos"))
        self.assertTrue(self.usar("0")["ok"])
        self.assertEqual(self.m.registro_resaltado, REGISTRO_FALSO)
        self.assertFalse(self.usar("0")["ok"])

    def test_impulso_solo_con_la_llave_y_acelera(self):
        self.assertFalse(self.usar("1")["ok"])
        self.m.halladas[LLAVE] = "1"
        ir(self.p, "1", lejos_de_pulsos(self.m))
        self.assertTrue(self.usar("1")["ok"])
        self.assertGreater(self.m.factor_impulso("1"), 1)
        self.m.actualizar(1, {})
        for _ in range(7):
            self.m.reloj += 1
        self.assertEqual(self.m.factor_impulso("1"), 1.0)
        self.assertFalse(self.usar("1")["ok"])

    def test_voz_comunitaria_descarta_la_cuenta_real(self):
        ir(self.p, "2", objetivo(self.m, "cuentas"))
        self.assertTrue(self.usar("2")["ok"])
        self.assertEqual(self.m.cuenta_descartada, CUENTA_REAL)

    def test_comunicado_despues_de_la_decision_correcta(self):
        self.assertFalse(self.usar("3")["ok"])
        self.m.resultado = dict(opcion="verificar", correcto=True, evento_id=1)
        self.assertTrue(self.usar("3")["ok"])
        self.assertIn("Muelle", self.m.comunicado["ruta"])
        self.assertFalse(self.usar("3")["ok"])


class ViajeLibre(unittest.TestCase):
    def test_entre_eras_se_conservan_indicadores_y_expediente(self):
        p = PartidaMovimiento([dict(id="0", nombre="A", rol="guardian")], 0)
        p.colisiones_de(PRESENTE)
        p.mision.expediente.registrar("agua", "Agua", dict(opcion="corregir", correcto=True, evento_id=1), [])
        p.mision.indicadores["confianza"] = 77
        for origen, destino in ((LA_COPA, FUTURO), (FUTURO, PRESENTE), (PRESENTE, LA_COPA)):
            x, y, w, h = rect_portal(origen, p.colisiones_de(origen).datos)
            p.jugadores["0"].update(x=x + w / 2, y=y + h + 3)
            self.assertTrue(accion(p, "0", "usar_portal", destino=destino)["ok"])
            self.assertEqual(p.mision.indicadores["confianza"], 77)
            self.assertIn("agua", p.mision.expediente.arbol.casos)


class Era(unittest.TestCase):
    def test_etiqueta_del_portal(self):
        from multijugador.presentacion import titulo_era
        self.assertEqual(titulo_era("futuro", "Ciudad Núcleo"), "Era III: Ciudad Núcleo")

    def test_otras_dimensiones_no_se_ven(self):
        p, m = partida(("guardian", "mensajero"))
        p.jugadores["1"]["dimension"] = LA_COPA
        self.assertEqual([j["id"] for j in jugadores_visibles(p.estado("0")["jugadores"], FUTURO)], ["0"])


class Equipo(unittest.TestCase):
    """El trabajo del compañero sigue en su sitio."""

    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        from interfaz.partida_multijugador import VistaPartida
        self.p = PartidaMovimiento([dict(id="0", nombre="A", rol="guardian"), dict(id="1", nombre="B", rol="habitante")], 0, semilla=5)
        self.v = VistaPartida("0", {"mundo": self.p.estado("0")})

    def test_t_abre_el_expediente(self):
        self.v.panel.modo = None
        self.v.manejar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_t), (0, 0), mock.Mock())
        self.assertEqual(self.v.panel.modo, "expediente")

    def test_el_sorteo_depende_de_la_semilla(self):
        otra = PartidaMovimiento([dict(id="0", nombre="A", rol="guardian")], 0, semilla=5)
        self.assertEqual([c[0] for c in self.p.mision.casos], [c[0] for c in otra.mision.casos])
        self.assertEqual([c[3] for c in self.p.mision.casos], [c[3] for c in otra.mision.casos])

    def test_avisos_temporales(self):
        m = self.p.mision
        m.ronda = 1
        aviso = m._renovar_aviso("0")
        self.assertGreater(aviso["vence"], m.reloj)

    def test_l_oculta_los_nombres(self):
        self.v.panel.modo = None
        antes = self.v.mostrar_nombres
        self.v.manejar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_l), (0, 0), mock.Mock())
        self.assertNotEqual(self.v.mostrar_nombres, antes)

    def test_bots_no_se_amontonan(self):
        p = PartidaMovimiento([dict(id="0", nombre="A", rol="guardian"), dict(id="bot_a", nombre="B", rol="aspirante", controlador="bot")], 0)
        gestor = GestorBots(p, {"0"})
        p.jugadores["bot_a"].update(x=p.jugadores["0"]["x"] + 2, y=p.jugadores["0"]["y"], animacion="reposo")
        separacion = lambda: abs(p.jugadores["bot_a"]["x"] - p.jugadores["0"]["x"]) + abs(p.jugadores["bot_a"]["y"] - p.jugadores["0"]["y"])
        antes = separacion()
        for _ in range(10):
            gestor._separar_bots(.1)
        self.assertGreater(separacion(), antes)


class TresEras(unittest.TestCase):
    def test_cuatro_bots_recorren_las_tres_eras_y_terminan_en_el_informe(self):
        jugadores = [dict(id="bot_" + r, nombre=r, rol=r, controlador="bot") for r in ROLES]
        p = PartidaMovimiento(jugadores, 0, semilla=11)
        gestor = GestorBots(p, set(), dificultad="facil")
        ahora, visitadas = 0.0, set()
        m = p.mision
        for _ in range(60000):
            ahora += .15
            p.actualizar(ahora)
            gestor.actualizar(ahora, .15)
            visitadas |= {j["dimension"] for j in p.jugadores.values()}
            if m.futuro.completada:
                break
        self.assertEqual(visitadas, {LA_COPA, PRESENTE, FUTURO})
        self.assertTrue(m.presente.fin)
        self.assertTrue(m.futuro.resultado["correcto"])
        informe = m.informe()
        self.assertEqual({f["era"] for f in informe["casos"] if f["resuelto"]}, {"La Copa", "Distrito Conecta", "Ciudad Núcleo"})
        self.assertTrue(all(f["resuelto"] for f in informe["casos"]), [f["id"] for f in informe["casos"] if not f["resuelto"]])


if __name__ == "__main__":
    unittest.main()
