"""Ciudad Núcleo: acceso, terminales validadas en el servidor, decisión y bots."""
import os
import unittest
import uuid
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from bots.gestor_bots import GestorBots  # noqa: E402
from multijugador.dimensiones_red import FUTURO, LA_COPA, PRESENTE, jugadores_visibles, rect_portal  # noqa: E402
from multijugador.movimiento import PartidaMovimiento  # noqa: E402
from multijugador.nucleo import ARISTAS_BLOQUEADAS, FIRMA, LLAVE, grafo_con, red_conectada  # noqa: E402
from multijugador.presente import EVENTOS  # noqa: E402
from multijugador.protocolo import ROLES  # noqa: E402
from nucleo.rutas import RAIZ  # noqa: E402
from test_presente_manipulado import accion, resolver_caso  # noqa: E402


def partida(humanos=1, bots=False):
    jugadores = [dict(id=str(i), nombre="J" + str(i), rol=ROLES[i]) for i in range(humanos)]
    if bots:
        jugadores += [dict(id="bot_" + r, nombre=r, rol=r, controlador="bot") for r in ROLES[humanos:]]
    return PartidaMovimiento(jugadores, 0)


def al_presente_resuelto(p):
    p._viajar_equipo(LA_COPA, PRESENTE)
    p.actualizar(p.ultima + .05)
    for numero in range(len(EVENTOS)):
        resolver_caso(p)
        if numero < len(EVENTOS) - 1:
            accion(p, "0", "presente_siguiente")


def a_ciudad_nucleo(p):
    p._viajar_equipo(LA_COPA, FUTURO)
    p.actualizar(p.ultima + .05)
    return p.mision.futuro


def ir(p, objetivo, i="0"):
    p.jugadores[i].update(x=objetivo["x"], y=objetivo["y"])


def objetivo(m, tarea):
    return next(o for o in m.objetivos if o.get("tarea") == tarea)


def resolver_terminales(p, m, i="0"):
    ir(p, objetivo(m, "conexiones"), i)
    assert accion(p, i, "futuro_resolver", terminal="conexiones", arista=1)["ok"]
    ir(p, objetivo(m, "archivos"), i)
    assert accion(p, i, "futuro_resolver", terminal="archivos", registro="orden")["ok"]
    m.halladas[LLAVE] = i
    ir(p, objetivo(m, "llave"), i)
    assert accion(p, i, "interactuar", objetivo="futuro:llave")["ok"]
    ir(p, objetivo(m, "cuentas"), i)
    assert accion(p, i, "futuro_resolver", terminal="cuentas", cuentas=["voz_1", "voz_2", "voz_3"])["ok"]
    m.halladas[FIRMA] = i


class Acceso(unittest.TestCase):
    def test_viaje_libre_a_todas_las_dimensiones_desde_el_principio(self):
        p = partida()
        for origen, destino in ((LA_COPA, FUTURO), (FUTURO, PRESENTE), (PRESENTE, FUTURO), (FUTURO, LA_COPA)):
            self.assertTrue(next(d for d in p.estado("0")["destinos"][origen] if d["id"] == destino)["disponible"])
            x, y, w, h = rect_portal(origen, p.colisiones_de(origen).datos)
            p.jugadores["0"].update(x=x + w / 2, y=y + h + 3)
            self.assertTrue(accion(p, "0", "usar_portal", destino=destino)["ok"], (origen, destino))
            self.assertEqual(p.jugadores["0"]["dimension"], destino)

    def test_se_entra_desde_la_pantalla_y_se_puede_volver(self):
        p = partida()
        al_presente_resuelto(p)
        ir(p, p.mision.presente.pantalla)
        self.assertEqual(accion(p, "0", "interactuar", objetivo="presente:pantalla")["vista"], "portal")
        indicadores = dict(p.mision.indicadores)
        self.assertTrue(accion(p, "0", "usar_portal", destino=FUTURO)["ok"])
        self.assertEqual(p.jugadores["0"]["dimension"], FUTURO)
        self.assertEqual(p.mision.indicadores, indicadores)
        ir(p, p.mision.futuro.pantalla)
        self.assertTrue(accion(p, "0", "usar_portal", destino=PRESENTE)["ok"])
        self.assertEqual(p.jugadores["0"]["dimension"], PRESENTE)

    def test_otras_dimensiones_no_se_ven_ni_duplican(self):
        p = partida(2)
        p.jugadores["0"]["dimension"] = FUTURO
        jugadores = p.estado("1")["jugadores"]
        self.assertEqual([j["id"] for j in jugadores_visibles(jugadores, FUTURO)], ["0"])
        self.assertEqual([j["id"] for j in jugadores_visibles(jugadores, LA_COPA)], ["1"])
        self.assertEqual(len(jugadores), 2)


class Terminales(unittest.TestCase):
    def setUp(self):
        self.p = partida()
        self.m = a_ciudad_nucleo(self.p)

    def test_bfs_solo_acepta_la_conexion_que_reconecta(self):
        self.assertFalse(red_conectada(grafo_con()))
        resultados = [red_conectada(grafo_con(i)) for i in range(len(ARISTAS_BLOQUEADAS))]
        self.assertEqual(resultados, [False, True, False])

    def test_una_conexion_inutil_no_completa_la_terminal(self):
        ir(self.p, objetivo(self.m, "conexiones"))
        accion(self.p, "0", "futuro_resolver", terminal="conexiones", arista=0)
        self.assertNotIn("conexiones", self.m.tareas)
        accion(self.p, "0", "futuro_resolver", terminal="conexiones", arista=1)
        self.assertIn("conexiones", self.m.tareas)

    def test_rechaza_datos_invalidos_y_estar_lejos(self):
        self.assertFalse(accion(self.p, "0", "futuro_resolver", terminal="conexiones", arista=1)["ok"])  # lejos
        ir(self.p, objetivo(self.m, "conexiones"))
        for arista in (99, "1", True):
            self.assertFalse(accion(self.p, "0", "futuro_resolver", terminal="conexiones", arista=arista)["ok"])

    def test_el_registro_falso_es_el_unico_valido(self):
        ir(self.p, objetivo(self.m, "archivos"))
        accion(self.p, "0", "futuro_resolver", terminal="archivos", registro="acta")
        self.assertNotIn("archivos", self.m.tareas)
        accion(self.p, "0", "futuro_resolver", terminal="archivos", registro="orden")
        self.assertIn("archivos", self.m.tareas)

    def test_la_llave_viene_del_dialogo_con_el_corredor(self):
        ir(self.p, objetivo(self.m, "llave"))
        accion(self.p, "0", "interactuar", objetivo="futuro:llave")
        self.assertNotIn("llave", self.m.tareas)
        corredor = next(n for n in self.m.npcs if n.get("pista") == LLAVE)
        ir(self.p, corredor)
        self.assertTrue(accion(self.p, "0", "hablar_npc", npc=corredor["id"])["ok"])
        self.assertIn(LLAVE, self.m.halladas)
        ir(self.p, objetivo(self.m, "llave"))
        accion(self.p, "0", "interactuar", objetivo="futuro:llave")
        self.assertIn("llave", self.m.tareas)


class Decision(unittest.TestCase):
    def setUp(self):
        self.p = partida()
        self.m = a_ciudad_nucleo(self.p)

    def test_no_se_decide_sin_las_tres_terminales(self):
        ir(self.p, self.m.pantalla)
        self.assertFalse(accion(self.p, "0", "presente_votar", opcion="verificar")["ok"])

    def test_la_decision_correcta_resuelve_e_inserta_el_caso(self):
        resolver_terminales(self.p, self.m)
        ir(self.p, self.m.pantalla)
        self.assertTrue(accion(self.p, "0", "presente_votar", opcion="verificar")["ok"])
        self.assertTrue(self.m.completada)
        self.assertTrue(self.m.resultado["correcto"])
        expediente = self.p.mision.expediente
        casos = {c.id: c for c in list(expediente.arbol.casos.values()) + expediente.pendientes}
        self.assertEqual(casos["nucleo_control"].gravedad, 9)
        self.assertEqual(casos["nucleo_control"].datos["tipo"], "Control autónomo sin supervisión")
        self.assertIsNone(casos["nucleo_control"].datos["ley"])

    def test_desconectarlo_a_la_fuerza_no_es_la_correcta(self):
        resolver_terminales(self.p, self.m)
        ir(self.p, self.m.pantalla)
        accion(self.p, "0", "presente_votar", opcion="reportar")
        self.assertFalse(self.m.resultado["correcto"])

    def test_dejarlo_como_esta_permite_volver_a_decidir(self):
        resolver_terminales(self.p, self.m)
        ir(self.p, self.m.pantalla)
        accion(self.p, "0", "presente_votar", opcion="dejar_pendiente")
        self.assertFalse(self.m.completada)
        self.assertTrue(accion(self.p, "0", "presente_votar", opcion="verificar")["ok"])
        self.assertTrue(self.m.completada)


class Bots(unittest.TestCase):
    def test_los_bots_resuelven_terminales_con_los_mismos_mensajes(self):
        p = partida(1, bots=True)
        m = a_ciudad_nucleo(p)
        gestor = GestorBots(p, {"0"})
        original = p.actuar
        vistas = []
        p.actuar = lambda i, s, a: vistas.append((i, s["accion"])) or original(i, s, a)
        ahora = p.ultima
        for _ in range(900):
            ahora += .15
            p.actualizar(ahora)
            gestor.actualizar(ahora, .15)
            if m.tareas:
                break
        self.assertTrue(any(i.startswith("bot_") and a == "futuro_resolver" for i, a in vistas), vistas[-5:])
        self.assertTrue(m.tareas)
        self.assertTrue(all(i.startswith("bot_") for i in m.tareas.values()))


class Arte(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)

    def test_el_mapa_generado_mide_lo_mismo_que_el_presente(self):
        futuro = pygame.image.load(str(RAIZ / "Imagenes" / "Futuro" / "generado" / "MapaFuturo.png"))
        presente = pygame.image.load(str(RAIZ / "Imagenes" / "Fondos" / "Mapas" / "Presente" / "MapaPresente.png"))
        self.assertEqual(futuro.get_size(), presente.get_size())

    def test_las_hitboxes_son_las_del_presente(self):
        origen = RAIZ / "Hitboxes" / "Mapas" / "Presente" / "MapaPresente_hitboxes.json"
        copia = RAIZ / "Hitboxes" / "Mapas" / "Futuro" / "MapaFuturo_hitboxes.json"
        self.assertEqual(origen.read_bytes(), copia.read_bytes())

    def test_la_vista_dibuja_el_mapa_y_cada_pantalla(self):
        from interfaz.partida_multijugador import VistaPartida
        p = partida()
        m = a_ciudad_nucleo(p)
        vista = VistaPartida("0", {"mundo": p.estado("0")})
        vista.recibir({"mundo": p.estado("0")})
        self.assertEqual(vista.dimension, FUTURO)
        lienzo = pygame.Surface((960, 720))
        vista.dibujar(lienzo, "LOCAL")
        vista.panel.terminal = "conexiones"
        for modo, terminal, claves in (("terminal", "conexiones", {"terminal:arista:1"}),
                                       ("terminal", "archivos", {"terminal:registro:orden"}),
                                       ("caldero", None, {"presente_votar:verificar"}), ("introduccion", None, set())):
            vista.panel.modo, vista.panel.terminal = modo, terminal
            vista.panel.dibujar(lienzo)
            self.assertLessEqual(claves, set(vista.panel.botones), modo)
        self.assertEqual(m.pantalla["dimension"], FUTURO)

    def test_los_botones_de_la_terminal_envian_la_respuesta(self):
        from interfaz.terminal_nucleo import accion as accion_ui
        cliente = mock.Mock()
        accion_ui(None, "terminal:arista:1", cliente)
        cliente.actuar.assert_called_once_with("futuro_resolver", terminal="conexiones", arista=1)


if __name__ == "__main__":
    unittest.main()
