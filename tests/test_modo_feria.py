"""Modo feria: Demo rápida, salida con confirmación e inactividad (sin cambiar el modo normal)."""
import os
import threading
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

from interfaz import inicio  # noqa: E402
from nucleo import preferencias  # noqa: E402

BOTONES_NORMALES = {"campana_local", "multi", "ajustes", "ayuda_f1", "salir"}


def menu(feria):
    entorno = {k: v for k, v in os.environ.items() if k != "TG_MODO_FERIA"}
    if feria:
        entorno["TG_MODO_FERIA"] = "1"
    with mock.patch.dict(os.environ, entorno, clear=True):
        pygame.init()
        return inicio.MenuInicio()


class MenuSinFeria(unittest.TestCase):
    def test_sin_la_variable_el_menu_es_el_de_siempre(self):
        m = menu(False)
        self.assertFalse(m.feria)
        m.dibujar()
        self.assertEqual(set(m.botones), BOTONES_NORMALES)
        self.assertEqual(m.accionar("salir"), "salir")  # sale sin confirmación

    def test_sin_feria_no_hay_aviso_de_inactividad(self):
        m = menu(False)
        m.vista, m.partida = "partida", object()
        self.assertIsNone(m.revisar_inactividad(m.ultima_actividad + 10_000))


class MenuFeria(unittest.TestCase):
    def test_con_la_variable_aparece_demo_rapida(self):
        m = menu(True)
        m.dibujar()
        self.assertIn("demo_rapida", m.botones)
        self.assertIn("ver_batalla", m.botones)
        self.assertTrue(BOTONES_NORMALES <= set(m.botones))
        rects = [b.rect for b in m.botones.values()]
        for i, rect in enumerate(rects):
            self.assertEqual(rect.collidelist(rects[i + 1:]), -1)

    def test_la_preferencia_tambien_activa_el_modo(self):
        self.assertTrue(preferencias.modo_feria({"modo_feria": True}))
        with mock.patch.dict(os.environ, {"TG_MODO_FERIA": "0"}):
            self.assertFalse(preferencias.modo_feria(preferencias.PREDETERMINADAS))

    def test_salir_pide_confirmacion(self):
        m = menu(True)
        self.assertIsNone(m.accionar("salir"))
        self.assertEqual(m.vista, "confirmar_salir")
        m.accionar("cancelar_salir")
        self.assertEqual(m.vista, "principal")
        m.accionar("salir")
        self.assertEqual(m.accionar("salir"), "salir")

    def test_inactividad_avisa_y_vuelve_al_menu_sin_dejar_nada_vivo(self):
        m = menu(True)
        hilos_antes = {h.ident for h in threading.enumerate()}
        m.accionar("demo_rapida")
        self.assertEqual(m.vista, "partida")
        self.assertTrue(m.campana_local)
        cliente = m.cliente
        inicio_t = m.ultima_actividad
        self.assertIsNone(m.revisar_inactividad(inicio_t + inicio.INACTIVIDAD - 1))
        restante = m.revisar_inactividad(inicio_t + inicio.INACTIVIDAD + 3)
        self.assertAlmostEqual(restante, inicio.AVISO_INACTIVIDAD - 3, places=3)
        # Una tecla responde al aviso y la partida sigue.
        m.registrar_actividad(inicio_t + inicio.INACTIVIDAD + 4)
        self.assertIsNone(m.revisar_inactividad(inicio_t + inicio.INACTIVIDAD + 5))
        self.assertEqual(m.vista, "partida")
        # Sin respuesta, vuelve al menú y cierra la campaña local.
        tarde = m.ultima_actividad + inicio.INACTIVIDAD + inicio.AVISO_INACTIVIDAD + 1
        self.assertIsNone(m.revisar_inactividad(tarde))
        self.assertEqual(m.vista, "principal")
        self.assertIsNone(m.partida)
        self.assertIsNone(m.cliente)
        self.assertIsNone(m.servidor)
        self.assertFalse(m.campana_local)
        self.assertTrue(cliente._cerrado)
        nuevos = [h for h in threading.enumerate() if h.ident not in hilos_antes and h.is_alive()]
        self.assertEqual(nuevos, [])


if __name__ == "__main__":
    unittest.main()
