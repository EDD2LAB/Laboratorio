"""Final completo, límites de autoridad, cooperación y repetición sin perder casos."""
import json
import math
import os
import unittest
import uuid
from copy import deepcopy

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from multijugador.movimiento import PartidaMovimiento
from multijugador.final_cooperativo import ROLES, CORRECTA


def partida():
    p = PartidaMovimiento([dict(id=r, nombre=r, rol=r) for r in ROLES], 0)
    p._viajar_equipo("la_copa", "futuro")
    p.actualizar(.05)
    p.mision.futuro.final.preparar(31)
    return p


class ReglasFinal(unittest.TestCase):
    def setUp(self):
        self.p = partida()
        self.f = self.p.mision.futuro.final

    def accion(self, rol, op, colocar=True, **datos):
        jugador = self.p.jugadores[rol]
        punto = self.f.puntos["aspirante"] if op in ("iniciar", "reintentar", "activar") else self.f.objetivo(rol)
        if colocar:
            jugador.update(x=punto["x"], y=punto["y"], interior=None)
        return self.p.actuar(rol, dict(accion="final_accion", rol=rol, operacion=op, ronda_final=self.f.ronda, id_solicitud=uuid.uuid4().hex, **datos), self.p.ultima)

    def iniciar(self):
        self.assertTrue(self.accion("guardian", "iniciar")["ok"])

    def guardian(self):
        datos = self.f.privado("guardian")
        campo = next(c for c in datos["registro"] if datos["registro"][c] != datos["orden"][c])
        self.assertTrue(self.accion("guardian", "comparar", campo=campo)["ok"])

    def habitante(self):
        for i, meta in enumerate(self.f.metas):
            while self.f.valores[i] != meta:
                self.accion("habitante", "ajustar", indice=i, delta=1 if self.f.valores[i] < meta else -1)
        for _ in range(5):
            self.accion("habitante", "mantener")
            self.p.actualizar(self.p.ultima + .5)

    def mensajero(self):
        self.assertTrue(self.accion("mensajero", "recoger")["ok"])
        for _ in range(3):
            self.assertTrue(self.accion("mensajero", "recargar")["ok"])

    def test_cuatro_roles_y_activacion_conjunta_hasta_victoria(self):
        self.iniciar()
        self.guardian()
        self.habitante()
        self.mensajero()
        for campo, valor in CORRECTA.items():
            self.assertTrue(self.accion("aspirante", "elegir", campo=campo, valor=valor)["ok"])
        self.assertTrue(self.accion("aspirante", "autorizar")["ok"])
        for rol in ROLES[:-1]:
            self.accion(rol, "activar")
            self.assertNotEqual(self.f.fase, "victoria")
        self.accion(ROLES[-1], "activar")
        self.assertEqual(self.f.fase, "victoria")
        self.assertEqual(len(self.f.hechos), 4)
        self.assertEqual(self.p.mision.informe()["final_cooperativo"]["fase"], "victoria")

    def test_sin_verificacion_no_se_recoge_y_sin_estacion_no_se_entrega(self):
        self.iniciar()
        self.assertFalse(self.accion("mensajero", "recoger")["ok"])
        self.guardian()
        self.accion("mensajero", "recoger")
        self.accion("mensajero", "recargar")
        self.accion("mensajero", "recargar")
        self.assertFalse(self.accion("mensajero", "recargar")["ok"])
        self.assertNotIn("mensajero", self.f.hechos)

    def test_no_se_puede_saltar_un_tramo_del_recorrido(self):
        self.iniciar()
        self.guardian()
        self.accion("mensajero", "recoger")
        ultimo = self.f.ruta[-1]
        self.p.jugadores["mensajero"].update(x=ultimo["x"], y=ultimo["y"])
        self.assertFalse(self.accion("mensajero", "recargar", colocar=False)["ok"])
        self.assertEqual(self.f.tramo, 0)

    def test_carga_usa_tiempo_del_servidor_y_posicion_real(self):
        self.iniciar()
        for i in range(3):
            while self.f.valores[i] != self.f.metas[i]:
                self.accion("habitante", "ajustar", indice=i, delta=1 if self.f.valores[i] < self.f.metas[i] else -1)
        for _ in range(30):
            self.accion("habitante", "mantener")
        self.assertEqual(self.f.carga, 0)
        self.p.jugadores["habitante"].update(x=0, y=0)
        self.p.actualizar(self.p.ultima + 1)
        self.assertEqual(self.f.carga, 0)
        self.habitante()
        self.assertIn("habitante", self.f.hechos)
        self.assertTrue(self.f.publico()["estacion_activa"])

    def test_role_sala_distancia_y_datos_invalidos_se_rechazan(self):
        self.iniciar()
        self.p.jugadores["guardian"].update(interior="cafe_digital")
        self.assertFalse(self.accion("guardian", "comparar", colocar=False, campo="firma")["ok"])
        r = self.p.actuar("guardian", dict(accion="final_accion", rol="habitante", operacion="ajustar", indice=0, delta=1, ronda_final=self.f.ronda, id_solicitud=uuid.uuid4().hex), self.p.ultima)
        self.assertFalse(r["ok"])
        self.assertFalse(self.accion("guardian", "comparar", campo=[])["ok"])
        self.assertFalse(self.accion("aspirante", "elegir", campo=[], valor={})["ok"])
        self.assertFalse(self.accion("habitante", "ajustar", indice=True, delta=1000)["ok"])

    def test_reintentar_conserva_casos_y_tareas_resueltas(self):
        self.iniciar()
        self.habitante()
        arbol = deepcopy(self.p.mision.expediente.publico())
        falso = next(c for c in self.f.registro if c != self.f.campo_falso)
        for _ in range(3):
            self.accion("guardian", "comparar", campo=falso)
        self.assertEqual(self.f.fase, "reintento")
        self.accion("guardian", "reintentar")
        self.assertEqual(self.f.integridad, 3)
        self.assertIn("habitante", self.f.hechos)
        self.assertEqual(self.p.mision.expediente.publico(), arbol)

    def test_pulso_recuperable_y_desconexion_no_secuestra_el_modulo(self):
        self.iniciar()
        self.guardian()
        self.accion("mensajero", "recoger")
        self.accion("mensajero", "recargar")
        j = self.p.jugadores["mensajero"]
        self.f.invulnerable_hasta = 0
        self.f.actualizar(.1, self.p.jugadores, [(j["x"], j["y"])], self.p.mision._cerca_presente, set(ROLES))
        self.assertIsNone(self.f.portador)
        self.assertEqual(self.f.tramo, 1)
        self.assertEqual(self.f.integridad, 2)
        self.accion("mensajero", "recoger")
        self.f.actualizar(.1, self.p.jugadores, [], self.p.mision._cerca_presente, {"guardian"})
        self.assertIsNone(self.f.portador)

    def test_respuesta_correcta_no_viaja_en_el_estado_publico(self):
        publico = json.dumps(self.f.publico(), ensure_ascii=False)
        self.assertNotIn("campo_falso", publico)
        self.assertNotIn("registro", publico)
        privado = self.p.mision.privado("mensajero")["final_cooperativo"]
        self.assertNotIn("guardian", privado)

    def test_repetir_una_solicitud_no_desgasta_dos_veces(self):
        self.iniciar()
        j = self.p.jugadores["guardian"]
        punto = self.f.puntos["guardian"]
        j.update(x=punto["x"], y=punto["y"])
        datos = dict(accion="final_accion", rol="guardian", operacion="comparar", ronda_final=self.f.ronda, campo=next(c for c in self.f.registro if c != self.f.campo_falso), id_solicitud=uuid.uuid4().hex)
        self.p.actuar("guardian", datos, self.p.ultima)
        self.p.actuar("guardian", datos, self.p.ultima)
        self.assertEqual(self.f.integridad, 2)

    def test_un_intento_anterior_no_se_aplica_despues_de_reintentar(self):
        self.iniciar()
        falso = next(c for c in self.f.registro if c != self.f.campo_falso)
        viejo = dict(accion="final_accion", rol="guardian", operacion="comparar", ronda_final=self.f.ronda,
                     campo=falso, id_solicitud=uuid.uuid4().hex)
        for _ in range(3):
            self.accion("guardian", "comparar", campo=falso)
        self.accion("guardian", "reintentar")
        punto = self.f.puntos["guardian"]
        self.p.jugadores["guardian"].update(x=punto["x"], y=punto["y"])
        self.assertFalse(self.p.actuar("guardian", viejo, self.p.ultima)["ok"])
        self.assertEqual(self.f.integridad, 3)

    def test_quien_cubre_un_mensajero_desconectado_puede_terminar_la_entrega(self):
        self.iniciar()
        self.guardian()
        self.p.conectados.discard("mensajero")
        punto = self.f.recogida
        self.p.jugadores["guardian"].update(x=punto["x"], y=punto["y"])
        def suplir(op):
            return self.p.actuar("guardian", dict(accion="final_accion", rol="mensajero", operacion=op,
                                ronda_final=self.f.ronda, id_solicitud=uuid.uuid4().hex), self.p.ultima)
        self.assertTrue(suplir("recoger")["ok"])
        self.p.conectados.add("mensajero")
        self.p.actualizar(self.p.ultima + .1)
        self.assertIn("mensajero", self.p.mision.privado("guardian")["final_cooperativo"])
        punto = self.f.objetivo("mensajero")
        self.p.jugadores["guardian"].update(x=punto["x"], y=punto["y"])
        self.assertTrue(suplir("recargar")["ok"])


class FinalConBots(unittest.TestCase):
    def test_persona_aspirante_y_tres_bots_completan_el_final(self):
        from bots.gestor_bots import GestorBots
        p = partida()
        gestor = GestorBots(p, {"aspirante"}, "normal")
        f = p.mision.futuro.final
        punto = f.puntos["aspirante"]
        p.jugadores["aspirante"].update(x=punto["x"], y=punto["y"])
        def enviar(op, **datos):
            return p.actuar("aspirante", dict(accion="final_accion", rol="aspirante", ronda_final=f.ronda,
                           operacion=op, id_solicitud=uuid.uuid4().hex, **datos), p.ultima)
        self.assertTrue(enviar("iniciar")["ok"])
        for campo, valor in CORRECTA.items():
            self.assertTrue(enviar("elegir", campo=campo, valor=valor)["ok"])
        for _ in range(7000):
            p.actualizar(p.ultima + .1)
            gestor.actualizar(p.ultima, .1)
            if {"guardian", "habitante", "mensajero"}.issubset(f.hechos):
                break
        self.assertTrue({"guardian", "habitante", "mensajero"}.issubset(f.hechos), [(b.rol, b.ultimo_error) for b in gestor.bots.values()])
        self.assertTrue(enviar("autorizar")["ok"])
        self.assertTrue(enviar("activar")["ok"])
        for _ in range(2000):
            p.actualizar(p.ultima + .1)
            gestor.actualizar(p.ultima, .1)
            if f.fase == "victoria":
                break
        self.assertEqual(f.fase, "victoria")

    def test_cuatro_bots_completan_sin_teletransportarse(self):
        from bots.gestor_bots import GestorBots
        p = partida()
        gestor = GestorBots(p, set(), "normal")
        f = p.mision.futuro.final
        for _ in range(7000):
            p.actualizar(p.ultima + .1)
            gestor.actualizar(p.ultima, .1)
            if f.fase == "victoria":
                break
        self.assertEqual(f.fase, "victoria", [(b.rol, b.ultimo_error, b.estado) for b in gestor.bots.values()])


class FinalPorInternet(unittest.TestCase):
    def test_dos_clientes_reales_reciben_el_mismo_avance_y_rechazan_otro_rol(self):
        import queue
        import threading
        import time
        from multijugador.servidor_local import ServidorLocal
        from multijugador.cliente_internet import ClienteInternet
        from multijugador.tiempo_real import SERVICIO
        servidor = ServidorLocal()
        clientes = []
        def esperar(cliente, predicado):
            fin = time.monotonic() + 10
            while time.monotonic() < fin:
                try:
                    e = cliente.eventos.get(timeout=.1)
                except queue.Empty:
                    continue
                self.assertNotIn(e.get("tipo"), ("rechazado", "desconectado"), e)
                if predicado(e):
                    return e
            self.fail("El cliente no recibió el avance del final.")
        try:
            a = ClienteInternet(servidor.url, "Ana", crear=True)
            clientes.append(a)
            bienvenida = esperar(a, lambda e: e.get("tipo") == "bienvenida")
            b = ClienteInternet(servidor.url, "Leo", codigo=bienvenida["codigo"])
            clientes.append(b)
            esperar(b, lambda e: e.get("tipo") == "bienvenida")
            for c, rol in ((a, "guardian"), (b, "mensajero")):
                c.enviar("rol", rol=rol)
                c.enviar("listo", listo=True)
            esperar(a, lambda e: e.get("tipo") == "estado" and all(j["listo"] for j in e.get("jugadores", [])))
            a.enviar("iniciar")
            esperar(a, lambda e: e.get("fase") == "partida")
            esperar(b, lambda e: e.get("fase") == "partida")
            listo = threading.Event()
            def preparar():
                sala = servidor.app[SERVICIO].salas[bienvenida["codigo"]]
                p = sala.partida
                p._viajar_equipo("la_copa", "futuro")
                p.mision.futuro.final.preparar(99)
                punto = p.mision.futuro.final.puntos["aspirante"]
                p.jugadores[bienvenida["id"]].update(x=punto["x"], y=punto["y"])
                listo.set()
            servidor.loop.call_soon_threadsafe(preparar)
            self.assertTrue(listo.wait(5))
            esperar(a, lambda e: (e.get("mundo", {}).get("caso", {}).get("futuro", {}).get("desafio_final") or {}).get("fase") == "preparacion")
            a.actuar("final_accion", rol="guardian", operacion="iniciar", ronda_final=0)
            self.assertTrue(esperar(a, lambda e: e.get("tipo") == "acuse")["ok"])
            def colocar():
                p = servidor.app[SERVICIO].salas[bienvenida["codigo"]].partida
                punto = p.mision.futuro.final.puntos["guardian"]
                p.jugadores[bienvenida["id"]].update(x=punto["x"], y=punto["y"])
            servidor.loop.call_soon_threadsafe(colocar)
            e = esperar(a, lambda e: e.get("mundo", {}).get("caso", {}).get("futuro", {}).get("desafio_final", {}).get("fase") == "activo")
            tarjetas = e["mundo"]["privado"]["final_cooperativo"]["guardian"]
            campo = next(c for c in tarjetas["registro"] if tarjetas["registro"][c] != tarjetas["orden"][c])
            a.actuar("final_accion", rol="guardian", operacion="comparar", campo=campo, ronda_final=1)
            self.assertTrue(esperar(a, lambda e: e.get("tipo") == "acuse")["ok"])
            compartido = esperar(b, lambda e: "guardian" in e.get("mundo", {}).get("caso", {}).get("futuro", {}).get("desafio_final", {}).get("hechos", []))
            self.assertNotIn("guardian", compartido["mundo"]["privado"]["final_cooperativo"])
            b.actuar("final_accion", rol="guardian", operacion="comparar", campo=campo, ronda_final=1)
            self.assertFalse(esperar(b, lambda e: e.get("tipo") == "acuse")["ok"])
        finally:
            for c in reversed(clientes):
                c.cerrar()
            servidor.cerrar()


class FinalPantallas(unittest.TestCase):
    def test_cuatro_minijuegos_y_estados_caben_y_no_se_enciman(self):
        import pygame
        from interfaz.partida_multijugador import VistaPartida
        from interfaz.final_cooperativo import pantalla
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        p = partida()
        for rol in ROLES:
            v = VistaPartida(rol, {"mundo": p.estado(rol)})
            v.cambiar_dimension("futuro")
            v.panel.modo = "final_cooperativo"
            ui = pantalla(v.panel)
            f = p.mision.futuro.final
            for fase in ("preparacion", "activo", "reintento", "victoria"):
                f.fase = fase
                v.recibir({"mundo": p.estado(rol)})
                v.transicion = None
                v.panel.modo = "final_cooperativo"
                ui.rol = rol
                s = pygame.Surface((960, 720))
                v.panel.dibujar(s)
                rects = [b.rect for b in v.panel.botones.values()]
                for i, rect in enumerate(rects):
                    self.assertTrue(s.get_rect().contains(rect), (rol, fase))
                    self.assertEqual(rect.collidelist(rects[i + 1:]), -1, (rol, fase))
