"""Menú de pausa (Esc), modos de pantalla y HUD ocultable del multijugador/bots."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

from nucleo import preferencias  # noqa: E402


def tecla(codigo):
    return pygame.event.Event(pygame.KEYDOWN, key=codigo, mod=0, unicode="", scancode=0)


class PreferenciasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.parche = mock.patch.object(preferencias, "ARCHIVO", Path(self.tmp.name) / "prefs.json")
        self.parche.start()

    def tearDown(self):
        self.parche.stop()
        self.tmp.cleanup()

    def test_por_defecto_maximizada(self):
        self.assertEqual(preferencias.cargar()["modo_pantalla"], "maximizada")

    def test_guardar_y_cargar(self):
        preferencias.guardar({"modo_pantalla": "completa"})
        self.assertEqual(preferencias.cargar()["modo_pantalla"], "completa")

    def test_valor_invalido_se_ignora(self):
        preferencias.ARCHIVO.write_text('{"modo_pantalla": "3d"}', encoding="utf-8")
        self.assertEqual(preferencias.cargar()["modo_pantalla"], "maximizada")


class MenuPausaCampanaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.parche = mock.patch.object(preferencias, "ARCHIVO", Path(self.tmp.name) / "prefs.json")
        self.parche.start()
        pygame.init()
        from interfaz.inicio import MenuInicio
        self.menu = MenuInicio()
        self.menu.mouse = (-1, -1)
        self.menu.campos["nombre"] = "Prueba"
        self.menu.accionar("campana_local")
        self.menu.accionar("iniciar_campana_solo")
        self.assertEqual(self.menu.vista, "partida")

    def tearDown(self):
        self.menu.limpiar_conexion()
        pygame.quit()
        self.parche.stop()
        self.tmp.cleanup()

    def correr(self, guion, frames):
        """Ejecuta el bucle real; guion = {frame: función} antes de cada flip."""
        original_flip, original_cursor = pygame.display.flip, pygame.mouse.set_cursor
        contador = {"frames": 0}

        def flip(*args, **kwargs):
            contador["frames"] += 1
            accion = guion.get(contador["frames"])
            if accion:
                accion()
            if contador["frames"] >= frames:
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            return original_flip(*args, **kwargs)

        pygame.display.flip = flip
        pygame.mouse.set_cursor = lambda *a, **k: None
        try:
            return self.menu.ejecutar()
        finally:
            pygame.display.flip, pygame.mouse.set_cursor = original_flip, original_cursor

    def test_escape_abre_pausa_y_detiene_la_campana(self):
        llamadas = []
        actualizar = self.menu.cliente.actualizar
        self.menu.cliente.actualizar = lambda s: (llamadas.append(s), actualizar(s))
        registro = {}

        def pulsar_escape():
            pygame.event.post(tecla(pygame.K_ESCAPE))

        def anotar():
            registro["vista"] = self.menu.pausa.vista
            registro["en_partida"] = self.menu.vista
            registro["llamadas"] = len(llamadas)
            registro["botones"] = set(self.menu.botones)

        def anotar_despues():
            registro["llamadas_despues"] = len(llamadas)

        # 1.er Esc cierra la introducción (como siempre); el 2.º abre la pausa.
        resultado = self.correr({3: pulsar_escape, 5: pulsar_escape, 8: anotar, 20: anotar_despues, 25: pulsar_escape,
                                 28: lambda: registro.update(cerrado=self.menu.pausa.vista)}, 40)
        self.assertEqual(resultado, "salir")
        self.assertEqual(registro["vista"], "principal")
        self.assertEqual(registro["en_partida"], "partida")  # Esc ya no sale de la partida
        self.assertEqual(registro["llamadas"], registro["llamadas_despues"])  # bots detenidos
        self.assertIn("pausa:confirmar_salida", registro["botones"])
        self.assertIsNone(registro["cerrado"])  # Esc de nuevo continúa

    def test_h_oculta_y_muestra_todo_el_hud(self):
        lienzo = pygame.Surface((960, 720))
        vista = self.menu.partida
        vista.panel.modo = None  # cerrar la introducción inicial
        self.assertTrue(vista.mostrar_hud)
        vista.manejar_evento(tecla(pygame.K_h), (0, 0), self.menu.cliente)
        self.assertFalse(vista.mostrar_hud)
        vista.dibujar(lienzo, "LOCAL")  # sin HUD no falla
        self.menu.dibujar()
        self.assertIn("alternar_hud", self.menu.botones)  # botón para recuperarlo
        self.menu.accionar("alternar_hud")
        self.assertTrue(vista.mostrar_hud)

    def test_salir_pide_confirmacion(self):
        self.menu.pausa.abrir()
        self.menu.accionar("pausa:confirmar_salida")
        self.menu.dibujar()
        self.assertEqual(self.menu.pausa.vista, "confirmar_salida")
        self.assertEqual(self.menu.vista, "partida")
        self.assertIn("pausa:salir_partida", self.menu.botones)
        self.assertIn("pausa:continuar", self.menu.botones)
        self.assertEqual(self.menu.accionar("pausa:cerrar_juego"), "salir")
        self.menu.accionar("pausa:salir_partida")
        self.assertFalse(self.menu.pausa.activo)
        self.assertNotEqual(self.menu.vista, "partida")

    def test_ajustes_y_ayuda_se_dibujan_y_cambian_modo(self):
        for vista in ("ajustes", "ayuda"):
            self.menu.accionar("pausa:" + vista)
            self.menu.dibujar()
            self.assertIn("pausa:volver", self.menu.botones)
        self.menu.accionar("pausa:ajustes")
        for modo in ("ventana", "completa", "maximizada"):
            self.menu.accionar("pausa:modo:" + modo)
            self.assertEqual(preferencias.cargar()["modo_pantalla"], modo)
            self.assertIsNotNone(self.menu.pantalla)
        self.menu.accionar("pausa:hud")
        self.assertFalse(self.menu.partida.mostrar_hud)


if __name__ == "__main__":
    unittest.main()
