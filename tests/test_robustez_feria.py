"""Revisión para la feria: el juego nunca se cierra delante del público por un error."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

from nucleo import registro  # noqa: E402


class _RegistroTemporal:
    """Dirige los registros a una carpeta temporal durante la prueba."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.anterior = registro._carpeta
        registro._carpeta = Path(self.tmp.name)
        return Path(self.tmp.name)

    def __exit__(self, *_):
        registro._carpeta = self.anterior
        self.tmp.cleanup()


class RegistroTests(unittest.TestCase):
    def test_registra_traceback_con_contexto(self):
        with _RegistroTemporal() as carpeta:
            try:
                raise KeyError("dato")
            except KeyError as error:
                ruta = registro.registrar_error("Contexto de prueba", error)
            texto = ruta.read_text(encoding="utf-8")
            self.assertEqual(ruta.parent, carpeta)
            self.assertIn("Contexto de prueba", texto)
            self.assertIn("KeyError", texto)

    def test_salida_sin_consola_va_al_registro(self):
        with _RegistroTemporal() as carpeta:
            salida = registro._SalidaRegistro()
            salida.write("[Audio] Desactivado\n")
            self.assertIn("[Audio] Desactivado", (carpeta / registro.ARCHIVO_SALIDA).read_text(encoding="utf-8"))

    def test_rota_al_pasar_el_tamano(self):
        with _RegistroTemporal() as carpeta, mock.patch.object(registro, "TAMANO_MAXIMO", 50):
            for _ in range(5):
                registro.escribir("x" * 40)
            self.assertTrue((carpeta / (registro.ARCHIVO_ERRORES + ".1")).exists())


class MenuRecuperaTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        from interfaz.inicio import MenuInicio
        self.menu = MenuInicio()
        self.cursor = pygame.mouse.set_cursor
        pygame.mouse.set_cursor = lambda *a, **k: None

    def tearDown(self):
        pygame.mouse.set_cursor = self.cursor
        self.menu.limpiar_conexion()
        pygame.quit()

    def test_un_error_en_la_partida_vuelve_al_menu_sin_cerrar(self):
        menu = self.menu
        from multijugador.dimensiones_red import LA_COPA
        menu.iniciar_campana("Visitante", "guardian", "normal", LA_COPA, "principal")
        menu.intro = None
        self.assertEqual(menu.vista, "partida")
        llamadas = {"n": 0}

        def falla(*_a, **_k):
            llamadas["n"] += 1
            raise KeyError("fallo simulado")

        menu.partida.dibujar = falla
        cuadros = {"n": 0}
        original = pygame.event.get

        def eventos():
            cuadros["n"] += 1
            return [pygame.event.Event(pygame.QUIT)] if cuadros["n"] > 5 else []

        with _RegistroTemporal() as carpeta, mock.patch.object(pygame.event, "get", eventos):
            self.assertEqual(menu.ejecutar(), "salir")
            texto = (carpeta / registro.ARCHIVO_ERRORES).read_text(encoding="utf-8")
        pygame.event.get = original
        self.assertEqual(llamadas["n"], 1)
        self.assertEqual(menu.vista, "principal")
        self.assertIsNone(menu.partida)
        self.assertIn("volvimos al menú", menu.mensaje)
        self.assertIn("fallo simulado", texto)

    def test_fallos_repetidos_se_relanzan_para_reiniciar(self):
        menu = self.menu
        menu.dibujar = mock.Mock(side_effect=RuntimeError("siempre falla"))
        with _RegistroTemporal(), mock.patch.object(pygame.event, "get", lambda: []):
            with self.assertRaises(RuntimeError):
                menu.ejecutar()
        self.assertEqual(menu.dibujar.call_count, 4)

    def test_un_solo_dibujo_por_cuadro(self):
        menu = self.menu
        dibujos = {"n": 0}
        dibujar = menu.dibujar

        def contar():
            dibujos["n"] += 1
            dibujar()

        menu.dibujar = contar
        cuadros = {"n": 0}

        def eventos():
            cuadros["n"] += 1
            return [pygame.event.Event(pygame.QUIT)] if cuadros["n"] > 10 else []

        with mock.patch.object(pygame.event, "get", eventos):
            menu.ejecutar()
        self.assertEqual(dibujos["n"], 10)

    def test_clics_de_la_carga_no_saltan_la_intro(self):
        menu = self.menu
        from multijugador.dimensiones_red import LA_COPA

        def crear_logica():
            for _ in range(2):
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10)))
            return None

        menu._cargar_con_barra("Prueba", crear_logica, lambda _: None)
        self.assertEqual([e for e in pygame.event.get() if e.type == pygame.MOUSEBUTTONDOWN], [])
        del LA_COPA


class JuegoPrincipalTests(unittest.TestCase):
    def test_error_fatal_se_registra_y_sale_con_codigo_1(self):
        import juego
        with _RegistroTemporal() as carpeta, \
                mock.patch("interfaz.inicio.mostrar_menu_inicio", side_effect=RuntimeError("arranque roto")), \
                mock.patch.object(registro, "iniciar"):
            with self.assertRaises(SystemExit) as salida:
                juego.main()
            self.assertEqual(salida.exception.code, 1)
            self.assertIn("arranque roto", (carpeta / registro.ARCHIVO_ERRORES).read_text(encoding="utf-8"))


class InformeTests(unittest.TestCase):
    def test_exportar_sin_permiso_no_cierra_el_juego(self):
        from interfaz import informe_final
        datos = {"casos": [], "final_cooperativo": {}}
        with mock.patch.object(informe_final, "exportar", side_effect=PermissionError("solo lectura")):
            self.assertEqual(informe_final.exportar_seguro(datos), "No se pudo guardar el informe en este equipo.")
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(informe_final, "CARPETA", Path(tmp)):
            self.assertTrue(informe_final.exportar_seguro(datos).startswith("Guardado en: "))


class ServidorSalaAveriadaTests(unittest.TestCase):
    def test_una_sala_averiada_se_cierra_sola_y_las_demas_siguen(self):
        from multijugador.servicio_internet import ServicioSalas
        from multijugador.tiempo_real import SALA_AVERIADA, _cerrar_sala_averiada
        servicio = ServicioSalas()
        respuestas = [servicio.ejecutar("POST", "/v1/crear", {"nombre": n, "version": _protocolo()}, ip="1.1.1.1")
                      for n in ("Ana", "Beto")]
        codigos = [r[1]["codigo"] if isinstance(r, tuple) else r["codigo"] for r in respuestas]
        averiadas = {}
        try:
            raise RuntimeError("tick roto")
        except RuntimeError:
            _cerrar_sala_averiada(servicio, codigos[0], averiadas)
        self.assertNotIn(codigos[0], servicio.salas)
        self.assertIn(codigos[1], servicio.salas)
        self.assertEqual(list(averiadas.values()), [SALA_AVERIADA])


def _protocolo():
    from multijugador.protocolo import VERSION
    return VERSION


if __name__ == "__main__":
    unittest.main()
