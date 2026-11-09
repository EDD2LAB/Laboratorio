"""Campos de texto: cursor, selección y portapapeles."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from interfaz.edicion_texto import EditorCampos  # noqa: E402
from nucleo import portapapeles  # noqa: E402


def tecla(codigo, mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=codigo, mod=mod, unicode="", scancode=0)


CTRL, SHIFT = pygame.KMOD_LCTRL, pygame.KMOD_LSHIFT


class Edicion(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((100, 100))
        self.addCleanup(pygame.quit)
        self.campos = {"a": "hola mundo", "codigo": "", "sala": "ABC123"}
        self.editor = EditorCampos(self.campos, {"a": 20, "codigo": 6, "sala": 40},
                                   {"codigo": lambda t: "".join(c for c in t.upper() if c.isalnum())}, ("sala",))

    def pulsar(self, clave, codigo, mod=0):
        return self.editor.manejar_tecla(tecla(codigo, mod), clave)

    def test_seleccionar_todo_copiar_y_pegar(self):
        self.pulsar("a", pygame.K_a, CTRL)
        self.pulsar("a", pygame.K_c, CTRL)
        self.assertEqual(portapapeles.pegar(), "hola mundo")
        self.pulsar("codigo", pygame.K_v, CTRL)
        self.assertEqual(self.campos["codigo"], "HOLAMU")  # filtro y límite del campo

    def test_cortar_borra_la_seleccion(self):
        self.editor.colocar("a", 0)
        for _ in range(5):
            self.pulsar("a", pygame.K_RIGHT, SHIFT)
        self.pulsar("a", pygame.K_x, CTRL)
        self.assertEqual(self.campos["a"], "mundo")
        self.assertEqual(portapapeles.pegar(), "hola ")

    def test_escribir_reemplaza_la_seleccion_y_respeta_el_cursor(self):
        self.editor.colocar("a", 4)
        self.editor.insertar("a", "!")
        self.assertEqual(self.campos["a"], "hola! mundo")
        self.editor.seleccionar_todo("a")
        self.editor.insertar("a", "x")
        self.assertEqual(self.campos["a"], "x")

    def test_borrar_y_suprimir_en_medio(self):
        self.editor.colocar("a", 4)
        self.pulsar("a", pygame.K_BACKSPACE)
        self.pulsar("a", pygame.K_DELETE)
        self.assertEqual(self.campos["a"], "holmundo")

    def test_ctrl_flecha_salta_palabras(self):
        self.editor.colocar("a", 0)
        self.pulsar("a", pygame.K_RIGHT, CTRL)
        self.assertEqual(self.editor.posiciones("a")[0], 4)
        self.pulsar("a", pygame.K_END)
        self.pulsar("a", pygame.K_LEFT, CTRL)
        self.assertEqual(self.editor.posiciones("a")[0], 5)

    def test_solo_lectura_se_copia_pero_no_se_cambia(self):
        self.editor.seleccionar_todo("sala")
        self.pulsar("sala", pygame.K_c, CTRL)
        self.assertEqual(portapapeles.pegar(), "ABC123")
        self.pulsar("sala", pygame.K_v, CTRL)
        self.pulsar("sala", pygame.K_BACKSPACE)
        self.assertEqual(self.campos["sala"], "ABC123")

    def test_el_texto_cambiado_desde_fuera_no_rompe_el_cursor(self):
        self.editor.colocar("a", 10)
        self.campos["a"] = "x"
        self.assertEqual(self.editor.posiciones("a"), (1, 1))


if __name__ == "__main__":
    unittest.main()
