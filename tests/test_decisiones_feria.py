"""Decisiones del 25 de noviembre para la feria: Demo rápida, F2 secreto, ajustes, inactividad,
árbol AVL completo al ganar y nota para menores."""
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

from multijugador import partida_local  # noqa: E402
from multijugador.dimensiones_red import FUTURO, LA_COPA  # noqa: E402
from multijugador.partida_local import ClienteCampanaLocal  # noqa: E402
from nucleo import preferencias  # noqa: E402


class DemoRapidaTests(unittest.TestCase):
    def _copa_resuelta(self, cliente):
        mision = cliente._partida.mision
        mision.ronda, mision.encargo = len(mision.casos) - 1, None
        mision.resultado = {"opcion": "corregir", "correcto": True, "efectos": {}, "evento_id": mision.siguiente_evento()}
        self.assertEqual(mision.fase, "final")

    def test_al_resolver_la_copa_la_demo_salta_al_final(self):
        cliente = ClienteCampanaLocal("Visitante", "guardian", semilla=2, demo=True)
        self._copa_resuelta(cliente)
        cliente.actualizar(.1)
        self.assertEqual(cliente._partida.jugadores["local"]["dimension"], LA_COPA)  # primero se ve el resultado
        for _ in range(int(partida_local.ESPERA_DEMO / .1) + 5):
            cliente.actualizar(.1)
        self.assertTrue(all(j["dimension"] == FUTURO for j in cliente._partida.jugadores.values()))
        self.assertTrue(cliente._partida.mision.futuro.completada)

    def test_la_campana_normal_no_salta(self):
        cliente = ClienteCampanaLocal("Visitante", "guardian", semilla=2)
        self._copa_resuelta(cliente)
        for _ in range(int(partida_local.ESPERA_DEMO / .1) + 5):
            cliente.actualizar(.1)
        self.assertEqual(cliente._partida.jugadores["local"]["dimension"], LA_COPA)


class AtajoSecretoTests(unittest.TestCase):
    def test_f2_solo_con_ctrl_y_shift(self):
        from interfaz.partida_multijugador import atajo_secreto
        tecla = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F2, mod=0)
        self.assertFalse(atajo_secreto(tecla))
        self.assertFalse(atajo_secreto(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F2, mod=pygame.KMOD_LSHIFT)))
        self.assertTrue(atajo_secreto(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_F2, mod=pygame.KMOD_LCTRL | pygame.KMOD_RSHIFT)))

    def test_la_ayuda_no_anuncia_el_atajo(self):
        texto = (Path(__file__).resolve().parents[1] / "interfaz" / "menu_pausa.py").read_text(encoding="utf-8")
        self.assertNotIn("F2", texto)


class AjustesEnFeriaTests(unittest.TestCase):
    def test_en_feria_no_se_guardan_los_ajustes(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(preferencias, "ARCHIVO", Path(tmp) / "p.json"):
            with mock.patch.dict(os.environ, {"TG_MODO_FERIA": "1"}):
                preferencias.guardar({"volumen_general": 0.0})
            self.assertFalse((Path(tmp) / "p.json").exists())
            with mock.patch.dict(os.environ, {"TG_MODO_FERIA": "0"}):
                preferencias.guardar({"volumen_general": 0.5})
            self.assertTrue((Path(tmp) / "p.json").exists())


class MenuFeriaTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        from interfaz.inicio import MenuInicio
        self.menu = MenuInicio()
        self.menu.feria = True

    def tearDown(self):
        self.menu.limpiar_conexion()
        pygame.quit()

    def test_inactividad_en_un_formulario_vuelve_al_menu_y_limpia(self):
        menu = self.menu
        menu.accionar("campana_local")
        menu.campos["nombre"] = "Visitante anterior"
        menu.pausa.preferencias["volumen_general"] = 0.0  # un visitante bajó el volumen
        ahora = time.monotonic()
        menu.registrar_actividad(ahora - 200)
        self.assertIsNone(menu.revisar_inactividad(ahora))
        self.assertEqual(menu.vista, "principal")
        self.assertEqual(menu.campos["nombre"], "")
        self.assertEqual(menu.pausa.preferencias["volumen_general"], preferencias.cargar()["volumen_general"])

    def test_inactividad_con_ajustes_abiertos_los_cierra(self):
        menu = self.menu
        menu.pausa.abrir("ajustes")
        ahora = time.monotonic()
        menu.registrar_actividad(ahora - 200)
        menu.revisar_inactividad(ahora)
        self.assertFalse(menu.pausa.activo)

    def test_la_demo_vuelve_al_menu_principal(self):
        menu = self.menu
        menu.accionar("demo_rapida")
        self.assertEqual(menu.vista, "partida")
        self.assertTrue(menu.cliente.demo)
        menu.accionar("volver")
        self.assertEqual(menu.vista, "principal")


class ArbolCompletoTests(unittest.TestCase):
    def test_al_ganar_los_pendientes_entran_al_arbol_en_orden(self):
        from multijugador.expediente import ExpedientePartida
        expediente = ExpedientePartida()
        for i, evento in enumerate(("puente_norte", "agua", "presente_voz", "presente_foto")):
            expediente.registrar(evento, "Caso " + str(i), {"evento_id": i, "correcto": True}, [])
        self.assertEqual(len(expediente.pendientes), 3)
        expediente.completar()
        self.assertEqual(expediente.pendientes, [])
        self.assertEqual(len(expediente.arbol.casos), 4)
        claves = [(c.gravedad, c.orden) for c in expediente.arbol.inorden()]
        self.assertEqual(claves, sorted(claves))


if __name__ == "__main__":
    unittest.main()
