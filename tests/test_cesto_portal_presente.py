"""Cesto de la aldea, regreso por el portal, nombre y eventos de Distrito Conecta."""
from collections import deque
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from multijugador.dimensiones_red import LA_COPA, PRESENTE  # noqa: E402
from multijugador.movimiento import PartidaMovimiento  # noqa: E402
from multijugador.suministros import ENCARGOS, EncargoSuministros  # noqa: E402


def partida(cantidad=4):
    roles = ("guardian", "mensajero", "habitante", "aspirante")
    return PartidaMovimiento([dict(id=str(i), nombre="J" + str(i), rol=roles[i]) for i in range(cantidad)], 0)


class CestoDeLaAldea(unittest.TestCase):
    def setUp(self):
        self.objetivos = partida().mision.objetivos

    def test_todos_los_encargos_terminan_en_el_cesto(self):
        for ronda in range(len(ENCARGOS)):
            self.assertEqual(EncargoSuministros(ronda, self.objetivos).destino["id"], "cesto")

    def test_el_cesto_ya_no_es_un_tronco_de_ecos(self):
        cesto = next(o for o in self.objetivos if o["id"] == "cesto")
        self.assertEqual(cesto["tipo"], "cesto")
        self.assertNotIn("rol", cesto)
        ecos = [o for o in self.objetivos if o["tipo"] == "eco"]
        self.assertTrue(ecos)
        self.assertFalse(any((o["x"], o["y"]) == (cesto["x"], cesto["y"]) for o in ecos))

    def test_el_mensajero_conserva_su_fuente_en_un_tronco(self):
        fuente = next(o for o in self.objetivos if o.get("rol") == "mensajero")
        self.assertEqual(fuente["tipo"], "eco")


class RegresoPorElPortal(unittest.TestCase):
    def test_el_equipo_vuelve_a_la_plataforma_y_puede_salir_caminando(self):
        p = partida()
        for jugador in p.jugadores.values():
            jugador["dimension"] = PRESENTE
        p._viajar_equipo(PRESENTE, LA_COPA)
        mapa = p.colisiones_de(LA_COPA)
        for identificador, jugador in p.jugadores.items():
            self.assertEqual(jugador["dimension"], LA_COPA)
            self.assertFalse(mapa.bloqueado(jugador["x"], jugador["y"]))
            self.assertTrue(p._junto_al_portal(identificador, LA_COPA))
        # Desde donde reaparecen se llega a pie al inicio de la partida.
        inicio_x, inicio_y = mapa.inicio_libre(415, 390)
        salida = (int(p.jugadores["0"]["x"]), int(p.jugadores["0"]["y"]))
        vistos, cola = {salida}, deque([salida])
        llega = False
        while cola and not llega:
            x, y = cola.popleft()
            llega = abs(x - inicio_x) < 4 and abs(y - inicio_y) < 4
            for vecino in ((x + 3, y), (x - 3, y), (x, y + 3), (x, y - 3)):
                if vecino not in vistos and not mapa.bloqueado(*vecino):
                    vistos.add(vecino)
                    cola.append(vecino)
        self.assertTrue(llega)


class ConPantalla(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)


class NombreDelJugador(ConPantalla):
    def setUp(self):
        super().setUp()
        from nucleo import preferencias
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        ruta = mock.patch.object(preferencias, "ARCHIVO", Path(carpeta.name) / "p.json")
        ruta.start()
        self.addCleanup(ruta.stop)
        from interfaz.inicio import MenuInicio
        self.menu = MenuInicio()
        self.menu.accionar("campana_local")

    def test_el_nombre_empieza_vacio_y_con_foco(self):
        self.assertEqual(self.menu.campos["nombre"], "")
        self.assertEqual(self.menu.foco, "nombre")

    def test_el_cursor_parpadea_en_el_campo(self):
        with mock.patch("pygame.time.get_ticks", return_value=100), mock.patch("pygame.draw.line") as linea:
            self.menu.dibujar()
        self.assertTrue(linea.called)
        with mock.patch("pygame.time.get_ticks", return_value=700), mock.patch("pygame.draw.line") as linea:
            self.menu.dibujar()
        self.assertFalse(linea.called)

    def test_sin_nombre_no_se_inicia(self):
        self.menu.accionar("iniciar_campana_solo")
        self.assertTrue(self.menu.error)
        self.assertIsNone(self.menu.partida)


class EventosDelPresente(ConPantalla):
    def setUp(self):
        super().setUp()
        from interfaz.partida_multijugador import VistaPartida
        self.p = partida(2)
        self.vista = VistaPartida("0", {"mundo": self.p.estado("0")})
        self.vista._cargar_dimension(PRESENTE)
        self.vista.dimension = PRESENTE

    def test_no_hay_animacion_de_pocion(self):
        self.vista.iniciar_pocion({"tipo_pocion": "quemar", "evento_id": 1, "correcto": True}, "noticia")
        self.assertIsNone(self.vista.animacion_pocion)

    def test_cada_opcion_tiene_tarjeta_con_icono_propio(self):
        from interfaz.escenas_multijugador import OPCIONES_PRESENTE
        from multijugador.presente import OPCIONES
        self.assertEqual(set(OPCIONES), set(OPCIONES_PRESENTE))
        for clave, texto in OPCIONES.items():
            self.assertIsNotNone(self.vista.escenas.iconos_presente[clave])
            self.assertIsNotNone(self.vista.escenas.tarjeta_presente(clave, texto))

    def test_el_fondo_de_las_escenas_es_distrito_conecta(self):
        escenas = self.vista.escenas
        self.assertIsNotNone(escenas.fondo_presente)
        self.assertIs(escenas.r["fondos_tablilla_por_dia"][1], escenas.fondo_presente)
        self.assertIsNot(escenas.fondo_presente, escenas.fondo_tablilla)


if __name__ == "__main__":
    unittest.main()
