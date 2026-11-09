"""Ayuda (F1) y ajustes de accesibilidad guardados."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from audio.narracion import Narrador  # noqa: E402
from interfaz.hud import HUDIndicadores  # noqa: E402
from multijugador.movimiento import PartidaMovimiento  # noqa: E402
from nucleo import preferencias  # noqa: E402


class ConMenu(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        ruta = mock.patch.object(preferencias, "ARCHIVO", Path(carpeta.name) / "p.json")
        ruta.start()
        self.addCleanup(ruta.stop)
        from interfaz.inicio import MenuInicio
        self.menu = MenuInicio()


class Ayuda(ConMenu):
    def test_f1_abre_sus_dos_pestanas(self):
        self.menu.accionar("ayuda_f1")
        self.assertEqual(self.menu.pausa.vista, "ayuda_f1")
        self.menu.dibujar()
        self.assertIn("pausa:pestana:clasificacion", self.menu.botones)
        self.menu.pausa.accionar("pestana:clasificacion")
        self.menu.dibujar()
        self.assertIsNotNone(self.menu.arbol_clasificacion)
        self.menu.pausa.tecla(pygame.K_ESCAPE)
        self.assertFalse(self.menu.pausa.activo)


class Accesibilidad(ConMenu):
    def test_se_dibuja_y_guarda_los_ajustes(self):
        self.menu.pausa.abrir("accesibilidad")
        self.menu.dibujar()
        self.menu.pausa.accionar("alto_contraste")
        self.menu.pausa.accionar("apariencia:apariencia_aspirante:mujer")
        guardado = preferencias.cargar()
        self.assertTrue(guardado["alto_contraste"])
        self.assertEqual(guardado["apariencia_aspirante"], "mujer")

    def test_una_apariencia_invalida_se_ignora(self):
        preferencias.ARCHIVO.write_text('{"apariencia_aspirante": "dragon"}', encoding="utf-8")
        self.assertEqual(preferencias.cargar()["apariencia_aspirante"], "hombre")

    def test_la_variante_se_carga_y_se_dibuja(self):
        from interfaz.partida_multijugador import VistaPartida
        p = PartidaMovimiento([dict(id="0", nombre="A", rol="aspirante", apariencia="mujer"),
                               dict(id="1", nombre="B", rol="habitante", apariencia="mujer")], 0)
        vista = VistaPartida("0", {"mundo": p.estado("0")})
        vista.dibujar(pygame.Surface((960, 720)), "T")
        self.assertIn("aspirante_mujer", vista.personajes_zoom)
        self.assertIn("habitante_mujer", vista.personajes_zoom)


class Protocolo(unittest.TestCase):
    def test_la_apariencia_viaja_como_id(self):
        p = PartidaMovimiento([dict(id="0", nombre="A", rol="aspirante", apariencia="mujer"), dict(id="1", nombre="B", rol="habitante")], 0)
        jugadores = {j["id"]: j for j in p.estado("0")["jugadores"]}
        self.assertEqual(jugadores["0"]["apariencia"], "mujer")
        self.assertIsNone(jugadores["1"]["apariencia"])

    def test_el_servidor_rechaza_valores_raros(self):
        from multijugador.servidor import ServidorSala
        sala = ServidorSala(0)
        sala._sesiones["x"] = {"jugador": {"id": "x", "nombre": "A", "rol": None, "listo": False, "anfitrion": True},
                               "salida": mock.Mock(), "cerrar": mock.Mock()}
        sala._accion("x", {"tipo": "rol", "rol": "aspirante", "apariencia": "<img>"})
        self.assertNotIn("apariencia", sala._sesiones["x"]["jugador"])
        sala._accion("x", {"tipo": "rol", "rol": "aspirante", "apariencia": "mujer"})
        self.assertEqual(sala._sesiones["x"]["jugador"]["apariencia"], "mujer")


class Contraste(unittest.TestCase):
    def test_los_cambios_llevan_flecha(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        renders = []
        fuente = mock.Mock()
        fuente.render.side_effect = lambda texto, *a: renders.append(texto) or pygame.Surface((10, 10))
        hud = HUDIndicadores(fuente, negativos={"desinformacion"})
        hud.alto_contraste = True
        hud.actualizar({"desinformacion": 50}, .1)
        hud.actualizar({"desinformacion": 40}, .1)
        hud.dibujar_avisos(pygame.Surface((200, 200)), 0, 50)
        self.assertTrue(any(t.startswith("▲ ") for t in renders))


class Narracion(unittest.TestCase):
    def test_apagada_no_arranca_ningun_hilo(self):
        narrador = Narrador()
        narrador.decir("hola")
        self.assertIsNone(narrador._hilo)

    def test_sin_pyttsx3_no_falla(self):
        narrador = Narrador()
        narrador.activo = True
        with mock.patch("audio.narracion.disponible", return_value=False):
            narrador.decir("hola")
        self.assertIsNone(narrador._hilo)


if __name__ == "__main__":
    unittest.main()
