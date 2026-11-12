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
from multijugador.final_cooperativo import ROLES, PRUEBAS, opcion_correcta


def partida():
    p = PartidaMovimiento([dict(id=r, nombre=r, rol=r) for r in ROLES], 0)
    p._viajar_equipo("la_copa", "futuro")
    p.actualizar(.05)
    p.mision.ronda = 3
    p.mision.resultado = dict(evento_id=29, opcion="corregir", correcto=True)
    p.mision.presente.indice = 2
    p.mision.presente.resultado = dict(evento_id=30, opcion="verificar", correcto=True)
    p.mision.futuro.final.preparar(31)
    p.mision.futuro.final.aventura.fabricado = True
    p.mision.futuro.final.aventura.municion = 12
    return p


def respuesta_guardian(f, correcta=True):
    """Lo que respondería el Guardián a la orden actual (o un error a propósito)."""
    orden = f.ordenes[f.paso_orden]
    buena = orden["falso"] or "aprobar"
    if correcta:
        return buena
    return "firma" if buena == "aprobar" else "aprobar"


def paso_habitante(valores, metas):
    """Una unidad del circuito que sobra al que falta (siempre son vecinos)."""
    falta = next(i for i, (v, m) in enumerate(zip(valores, metas)) if v < m)
    sobra = next(i for i, (v, m) in enumerate(zip(valores, metas)) if v > m)
    return (falta, 1) if (falta + 1) % 3 == sobra else (sobra, -1)


class ReglasFinal(unittest.TestCase):
    def setUp(self):
        self.p = partida()
        self.f = self.p.mision.futuro.final

    def accion(self, rol, op, colocar=True, **datos):
        jugador = self.p.jugadores[rol]
        punto = self.f.puntos["aspirante"] if op in ("iniciar", "reintentar") else self.f.objetivo(rol)
        if colocar:
            jugador.update(x=punto["x"], y=punto["y"], interior=None)
        return self.p.actuar(rol, dict(accion="final_accion", rol=rol, operacion=op, ronda_final=self.f.ronda, id_solicitud=uuid.uuid4().hex, **datos), self.p.ultima)

    def recarga(self):
        self.f.batalla.turno, self.f.batalla.restante = "recarga", 99999

    def iniciar(self):
        self.assertTrue(self.accion("guardian", "iniciar")["ok"])
        self.recarga()

    def guardian(self):
        """Responde bien hasta terminar la parte de la fase actual."""
        while not self.f.parte_lista("guardian"):
            self.recarga()
            self.assertTrue(self.accion("guardian", "comparar", campo=respuesta_guardian(self.f))["ok"])

    def habitante(self):
        self.recarga()
        while self.f.valores != self.f.metas:
            indice, delta = paso_habitante(self.f.valores, self.f.metas)
            self.assertTrue(self.accion("habitante", "ajustar", indice=indice, delta=delta)["ok"])
        for _ in range(5):
            self.recarga()
            if self.f.parte_lista("habitante"):
                break
            self.accion("habitante", "mantener")
            self.p.actualizar(self.p.ultima + .5)
        self.assertTrue(self.f.parte_lista("habitante"))

    def mensajero_verde(self):
        for _ in range(3):
            self.recarga()
            self.assertTrue(self.accion("mensajero", "encender")["ok"])

    def aspirante_verde(self):
        self.recarga()
        for prueba in self.f.mazo:
            if PRUEBAS[prueba][2] != (prueba in self.f.seleccion):
                self.assertTrue(self.accion("aspirante", "marcar", prueba=prueba)["ok"])
        self.assertTrue(self.accion("aspirante", "guardar")["ok"])
        self.assertIn("aspirante", self.f.verde)

    def verde(self):
        self.guardian()
        self.habitante()
        self.mensajero_verde()
        self.aspirante_verde()
        self.assertEqual(self.f.batalla.fase, 2)
        self.recarga()

    def mensajero(self):
        self.recarga()
        self.assertTrue(self.accion("mensajero", "recoger")["ok"])
        for _ in range(3):
            self.assertTrue(self.accion("mensajero", "recargar")["ok"])

    def propuesta(self):
        self.recarga()
        for campo, valores in self.f.opciones.items():
            buena = next(v for v in valores if opcion_correcta(campo, v))
            self.assertTrue(self.accion("aspirante", "elegir", campo=campo, valor=buena)["ok"])

    def test_dos_fases_y_victoria_sin_confirmar_consolas(self):
        self.iniciar()
        self.verde()
        self.assertNotEqual(self.f.valores, self.f.metas)  # NÚCLEO descalibró la estación
        self.guardian()
        self.habitante()
        self.mensajero()
        self.propuesta()
        self.assertTrue(self.accion("aspirante", "autorizar")["ok"])
        self.assertEqual(self.f.fase, "victoria")
        self.assertEqual(len(self.f.hechos), 4)
        self.assertEqual(self.f.aventura.etapa, "reconfiguracion")
        self.assertEqual(self.p.mision.informe()["final_cooperativo"]["fase"], "victoria")

    def test_el_escudo_cae_solo_con_las_cuatro_partes_verdes(self):
        self.iniciar()
        self.guardian()
        self.habitante()
        self.mensajero_verde()
        self.assertEqual(self.f.batalla.fase, 1)
        self.aspirante_verde()
        self.assertEqual(self.f.batalla.fase, 2)

    def test_partes_de_cada_fase_no_se_adelantan(self):
        self.iniciar()
        self.assertFalse(self.accion("mensajero", "recoger")["ok"])
        self.assertFalse(self.accion("aspirante", "elegir", campo="limite", valor=self.f.opciones["limite"][0])["ok"])
        self.assertFalse(self.accion("aspirante", "autorizar")["ok"])
        self.verde()
        self.assertFalse(self.accion("mensajero", "encender")["ok"])
        self.assertFalse(self.accion("aspirante", "guardar")["ok"])

    def test_guardian_aprueba_las_legitimas_y_marca_las_alteradas(self):
        self.iniciar()
        tipos = {orden["falso"] is None for orden in self.f.ordenes[:3]}
        self.assertEqual(tipos, {True, False})
        self.assertFalse(self.accion("guardian", "comparar", campo="nada")["ok"])
        self.accion("guardian", "comparar", campo=respuesta_guardian(self.f, False))
        self.assertEqual(self.f.integridad, 2)
        self.assertEqual(self.f.paso_orden, 0)
        self.guardian()
        self.assertEqual(self.f.paso_orden, 3)
        self.assertIn("guardian", self.f.verde)
        self.assertNotIn("guardian", self.f.hechos)

    def test_circuitos_acoplados_respetan_limites(self):
        self.iniciar()
        self.f.valores, self.f.metas = [3, 3, 3], [4, 2, 3]
        self.assertTrue(self.accion("habitante", "ajustar", indice=0, delta=1)["ok"])
        self.assertEqual(self.f.valores, [4, 2, 3])
        self.f.valores = [6, 0, 3]
        self.assertFalse(self.accion("habitante", "ajustar", indice=0, delta=1)["ok"])
        self.assertEqual(self.f.valores, [6, 0, 3])
        self.assertTrue(self.accion("habitante", "ajustar", indice=2, delta=1)["ok"])  # el 3 cede al 1
        self.assertEqual(self.f.valores, [5, 0, 4])

    def test_metas_siempre_tienen_solucion(self):
        for semilla in range(200):
            from multijugador.final_cooperativo import FinalCooperativo
            f = FinalCooperativo(self.p.mision.futuro.objetivos, semilla)
            f.preparar(1)
            self.assertEqual(sum(f.valores), sum(f.metas))
            self.assertNotEqual(f.valores, f.metas)
            self.assertTrue(all(1 <= m <= 5 for m in f.metas))

    def test_pruebas_sin_fuente_cuestan_senal(self):
        self.iniciar()
        sin_fuente = next(p for p in self.f.mazo if not PRUEBAS[p][2])
        self.assertTrue(self.accion("aspirante", "marcar", prueba=sin_fuente)["ok"])
        self.accion("aspirante", "guardar")
        self.assertEqual(self.f.integridad, 2)
        self.assertNotIn("aspirante", self.f.verde)
        self.accion("aspirante", "marcar", prueba=sin_fuente)
        self.aspirante_verde()
        self.assertIn("aspirante", self.f.verde)

    def test_propuesta_cambia_entre_partidas_y_castiga_opciones_tentadoras(self):
        from multijugador.final_cooperativo import FinalCooperativo
        vistas = set()
        for semilla in range(12):
            f = FinalCooperativo(self.p.mision.futuro.objetivos, semilla)
            f.preparar(1)
            vistas.add(tuple(f.opciones["limite"]))
            for campo, valores in f.opciones.items():
                self.assertEqual(sum(opcion_correcta(campo, v) for v in valores), 1, campo)
        self.assertGreater(len(vistas), 3)
        self.iniciar()
        self.verde()
        self.guardian()
        self.habitante()
        self.mensajero()
        self.propuesta()
        mala = next(v for v in self.f.opciones["limite"] if not opcion_correcta("limite", v))
        self.accion("aspirante", "elegir", campo="limite", valor=mala)
        self.accion("aspirante", "autorizar")
        self.assertNotIn("aspirante", self.f.hechos)
        self.assertEqual(self.f.integridad, 2)

    def test_entrega_espera_la_estacion_recalibrada(self):
        self.iniciar()
        self.verde()
        self.guardian()
        self.recarga()
        self.assertTrue(self.accion("mensajero", "recoger")["ok"])
        for _ in range(2):
            self.assertTrue(self.accion("mensajero", "recargar")["ok"])
        self.assertFalse(self.accion("mensajero", "recargar")["ok"])
        self.habitante()
        self.recarga()
        self.assertTrue(self.accion("mensajero", "recargar")["ok"])
        self.assertIn("mensajero", self.f.hechos)

    def test_no_se_puede_saltar_un_tramo_del_recorrido(self):
        self.iniciar()
        self.verde()
        self.accion("mensajero", "recoger")
        ultimo = self.f.ruta[-1]
        self.p.jugadores["mensajero"].update(x=ultimo["x"], y=ultimo["y"])
        self.assertFalse(self.accion("mensajero", "recargar", colocar=False)["ok"])
        self.assertEqual(self.f.tramo, 0)

    def test_carga_usa_tiempo_del_servidor_y_posicion_real(self):
        self.iniciar()
        while self.f.valores != self.f.metas:
            indice, delta = paso_habitante(self.f.valores, self.f.metas)
            self.accion("habitante", "ajustar", indice=indice, delta=delta)
        for _ in range(30):
            self.accion("habitante", "mantener")
        self.assertEqual(self.f.carga, 0)
        self.p.jugadores["habitante"].update(x=0, y=0)
        self.p.actualizar(self.p.ultima + 1)
        self.assertEqual(self.f.carga, 0)
        self.habitante()
        self.assertIn("habitante", self.f.verde)
        self.assertIn("habitante", self.f.publico()["verde"])

    def test_role_sala_distancia_y_datos_invalidos_se_rechazan(self):
        self.iniciar()
        self.p.jugadores["guardian"].update(interior="cafe_digital")
        self.assertFalse(self.accion("guardian", "comparar", colocar=False, campo="firma")["ok"])
        r = self.p.actuar("guardian", dict(accion="final_accion", rol="habitante", operacion="ajustar", indice=0, delta=1, ronda_final=self.f.ronda, id_solicitud=uuid.uuid4().hex), self.p.ultima)
        self.assertFalse(r["ok"])
        self.assertFalse(self.accion("guardian", "comparar", campo=[])["ok"])
        self.assertFalse(self.accion("aspirante", "marcar", prueba={})["ok"])
        self.assertFalse(self.accion("aspirante", "marcar", prueba="no_existe")["ok"])
        self.assertFalse(self.accion("habitante", "ajustar", indice=True, delta=1000)["ok"])
        self.assertFalse(self.accion("guardian", "activar")["ok"])  # ya no hay confirmación de consolas

    def test_reintentar_conserva_casos_y_tareas_resueltas(self):
        self.iniciar()
        self.habitante()
        arbol = deepcopy(self.p.mision.expediente.publico())
        for _ in range(3):
            self.accion("guardian", "comparar", campo=respuesta_guardian(self.f, False))
        self.assertEqual(self.f.fase, "reintento")
        self.accion("guardian", "reintentar")
        self.assertEqual(self.f.integridad, 3)
        self.assertIn("habitante", self.f.verde)
        self.assertEqual(self.p.mision.expediente.publico(), arbol)

    def test_rayo_recuperable_y_desconexion_no_secuestra_el_modulo(self):
        self.iniciar()
        self.verde()
        self.accion("mensajero", "recoger")
        self.accion("mensajero", "recargar")
        j = self.p.jugadores["mensajero"]
        self.f.batalla.turno, self.f.batalla.restante = "aviso", .01
        self.f.batalla.blancos = [[j["x"], j["y"]]]
        self.f.actualizar(.1, self.p.jugadores, [(j["x"], j["y"])], self.p.mision._cerca_presente, set(ROLES))
        self.assertIsNone(self.f.portador)
        self.assertEqual(self.f.tramo, 1)
        self.assertEqual(self.f.integridad, 2)
        self.f.batalla.turno, self.f.batalla.restante = "recarga", 99
        self.f.batalla.derribados.clear()
        self.accion("mensajero", "recoger")
        self.f.actualizar(.1, self.p.jugadores, [], self.p.mision._cerca_presente, {"guardian"})
        self.assertIsNone(self.f.portador)

    def test_respuesta_correcta_no_viaja_en_el_estado(self):
        self.iniciar()
        publico = json.dumps(self.f.publico(), ensure_ascii=False)
        self.assertNotIn("falso", publico)
        self.assertNotIn("registro", publico)
        privado = self.p.mision.privado("mensajero")["final_cooperativo"]
        self.assertNotIn("guardian", privado)
        self.assertNotIn("falso", json.dumps(self.f.privado("guardian")))
        for prueba in self.f.privado("aspirante")["pruebas"]:
            self.assertEqual(set(prueba), {"id", "titulo", "detalle"})
        self.verde()
        for opciones in self.f.privado("aspirante")["opciones"].values():
            self.assertTrue(all(len(o) == 2 for o in opciones))

    def test_repetir_una_solicitud_no_desgasta_dos_veces(self):
        self.iniciar()
        j = self.p.jugadores["guardian"]
        punto = self.f.puntos["guardian"]
        j.update(x=punto["x"], y=punto["y"])
        datos = dict(accion="final_accion", rol="guardian", operacion="comparar", ronda_final=self.f.ronda,
                     campo=respuesta_guardian(self.f, False), id_solicitud=uuid.uuid4().hex)
        self.p.actuar("guardian", datos, self.p.ultima)
        self.p.actuar("guardian", datos, self.p.ultima)
        self.assertEqual(self.f.integridad, 2)

    def test_un_intento_anterior_no_se_aplica_despues_de_reintentar(self):
        self.iniciar()
        viejo = dict(accion="final_accion", rol="guardian", operacion="comparar", ronda_final=self.f.ronda,
                     campo=respuesta_guardian(self.f, False), id_solicitud=uuid.uuid4().hex)
        for _ in range(3):
            self.accion("guardian", "comparar", campo=respuesta_guardian(self.f, False))
        self.accion("guardian", "reintentar")
        punto = self.f.puntos["guardian"]
        self.p.jugadores["guardian"].update(x=punto["x"], y=punto["y"])
        self.assertFalse(self.p.actuar("guardian", viejo, self.p.ultima)["ok"])
        self.assertEqual(self.f.integridad, 3)

    def test_quien_cubre_un_mensajero_desconectado_puede_terminar_la_entrega(self):
        self.iniciar()
        self.verde()
        self.p.conectados.discard("mensajero")
        punto = self.f.recogida
        self.p.jugadores["guardian"].update(x=punto["x"], y=punto["y"])
        def suplir(op):
            return self.p.actuar("guardian", dict(accion="final_accion", rol="mensajero", operacion=op,
                                ronda_final=self.f.ronda, id_solicitud=uuid.uuid4().hex), self.p.ultima)
        self.assertTrue(suplir("recoger")["ok"])
        self.p.conectados.add("mensajero")
        self.p.actualizar(self.p.ultima + .1)
        self.recarga()
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
        for _ in range(9000):
            p.actualizar(p.ultima + .1)
            gestor.actualizar(p.ultima, .1)
            if f.batalla.turno == "aviso":
                p.jugadores["aspirante"].update(x=punto["x"] + 55, y=punto["y"])
            elif f.batalla.turno == "recarga":
                p.jugadores["aspirante"].update(x=punto["x"], y=punto["y"])
                # La persona hace su parte: los bots no la resuelven por ella.
                if f.batalla.fase == 1 and "aspirante" not in f.verde:
                    for prueba in f.mazo:
                        if PRUEBAS[prueba][2] and prueba not in f.seleccion:
                            enviar("marcar", prueba=prueba)
                    enviar("guardar")
                elif f.batalla.fase == 2 and {"guardian", "habitante", "mensajero"}.issubset(f.hechos):
                    for campo, valores in f.opciones.items():
                        enviar("elegir", campo=campo, valor=next(v for v in valores if opcion_correcta(campo, v)))
                    enviar("autorizar")
            if f.fase == "victoria":
                break
        self.assertEqual(f.fase, "victoria", [(b.rol, b.ultimo_error) for b in gestor.bots.values()])

    def test_bot_no_resuelve_la_parte_de_una_persona(self):
        from bots.gestor_bots import GestorBots
        p = partida()
        gestor = GestorBots(p, {"aspirante"}, "normal")
        f = p.mision.futuro.final
        punto = f.puntos["aspirante"]
        p.jugadores["aspirante"].update(x=punto["x"], y=punto["y"])
        p.actuar("aspirante", dict(accion="final_accion", rol="aspirante", ronda_final=f.ronda,
                                   operacion="iniciar", id_solicitud=uuid.uuid4().hex), p.ultima)
        for _ in range(3000):
            p.actualizar(p.ultima + .1)
            gestor.actualizar(p.ultima, .1)
        self.assertEqual(f.verde, {"guardian", "habitante", "mensajero"})
        self.assertEqual(f.batalla.fase, 1)

    def test_cuatro_bots_completan_sin_teletransportarse(self):
        from bots.gestor_bots import GestorBots
        p = partida()
        gestor = GestorBots(p, set(), "normal")
        f = p.mision.futuro.final
        for _ in range(9000):
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
                p.mision.ronda = 3
                p.mision.resultado = dict(evento_id=97, opcion="corregir", correcto=True)
                p.mision.presente.indice = 2
                p.mision.presente.resultado = dict(evento_id=98, opcion="verificar", correcto=True)
                p.mision.futuro.final.preparar(99)
                p.mision.futuro.final.aventura.fabricado = True
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
            e = esperar(a, lambda e: e.get("mundo", {}).get("caso", {}).get("futuro", {}).get("desafio_final", {}).get("batalla", {}).get("turno") == "recarga")
            tarjetas = e["mundo"]["privado"]["final_cooperativo"]["guardian"]
            campo = next((c for c in tarjetas["registro"] if tarjetas["registro"][c] != tarjetas["orden"][c]), "aprobar")
            a.actuar("final_accion", rol="guardian", operacion="comparar", campo=campo, ronda_final=1)
            self.assertTrue(esperar(a, lambda e: e.get("tipo") == "acuse")["ok"])
            compartido = esperar(b, lambda e: e.get("mundo", {}).get("caso", {}).get("futuro", {}).get("desafio_final", {}).get("aviso", "").startswith("Orden revisada"))
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
            for fase, batalla in (("preparacion", 2), ("activo", 1), ("activo", 2), ("reintento", 2), ("victoria", 2)):
                f.fase = fase
                f.batalla.turno, f.batalla.fase = "recarga", batalla
                v.recibir({"mundo": p.estado(rol)})
                v.transicion = None
                v.panel.modo = "final_cooperativo"
                ui.rol = rol
                s = pygame.Surface((960, 720))
                v.panel.dibujar(s)
                rects = [b.rect for b in v.panel.botones.values()]
                for i, rect in enumerate(rects):
                    self.assertTrue(s.get_rect().contains(rect), (rol, fase, batalla))
                    self.assertEqual(rect.collidelist(rects[i + 1:]), -1, (rol, fase, batalla))
