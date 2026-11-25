"""Arte esencial: preparación de imágenes, medidor fijo del puente, intro y finales."""
import math
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from multijugador.reparacion import CONFIGURACION, angulo_aguja, angulo_objetivo, dentro_de_zona  # noqa: E402
from nucleo.rutas import IMAGENES  # noqa: E402

try:
    import PIL  # noqa: F401
except ImportError:  # el juego no necesita Pillow; solo el script de preparación
    PIL = None

NUEVOS = ("Indicador_base.png", "Aguja_base.png")


def cargar_sin(*faltantes):
    """cargar_imagen del juego, pero como si faltaran estos archivos."""
    from nucleo.recursos import cargar_imagen

    def cargar(nombre, tamano=None, requerido=True):
        if any(nombre.endswith(f) for f in faltantes):
            return None
        return cargar_imagen(nombre, tamano, requerido)
    return cargar


def fuentes():
    from nucleo.recursos import cargar_fuente
    return {"fuente_mapa": cargar_fuente(18), "fuente_panel_titulo": cargar_fuente(16), "fuente_panel": cargar_fuente(13)}


class ConPantalla(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((960, 720))


@unittest.skipIf(PIL is None, "Pillow no está instalado")
class PreparacionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from herramientas.preparar_arte_esencial import preparar
        cls.tmp = tempfile.TemporaryDirectory()
        cls.destino = Path(cls.tmp.name)
        cls.escritos = preparar(destino=cls.destino, informar=lambda *_: None)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_produce_los_seis_archivos_con_su_tamano(self):
        from PIL import Image
        esperados = {"Indicadores Puente/Indicador_base.png": (220, 220), "Intro/vineta1.png": (960, 720),
                     "Intro/vineta2.png": (960, 536), "Finales/Final_tres_eras.png": (960, 720),
                     "Finales/Final_humo_tres_eras.png": (960, 720)}
        self.assertEqual(len(self.escritos), 6)
        for ruta, tamano in esperados.items():
            with Image.open(self.destino / ruta) as imagen:
                self.assertEqual(imagen.size, tamano, ruta)
        with Image.open(self.destino / "Indicadores Puente/Aguja_base.png") as aguja:
            self.assertEqual(aguja.width, aguja.height)
            self.assertEqual(aguja.width % 2, 1, "lado impar: el remache ocupa el píxel central")

    def test_medidor_y_aguja_con_alfa_y_sin_magenta_visible(self):
        from PIL import Image
        from herramientas.preparar_arte_esencial import pixeles_magenta_visibles
        for nombre in NUEVOS:
            with Image.open(self.destino / "Indicadores Puente" / nombre) as imagen:
                self.assertEqual(imagen.mode, "RGBA", nombre)
                alfa = imagen.getchannel("A")
                self.assertEqual(alfa.getextrema()[0], 0, f"{nombre} debe tener zonas transparentes")
                self.assertEqual(pixeles_magenta_visibles(imagen), 0, nombre)

    def test_remache_en_el_centro_de_la_aguja(self):
        from PIL import Image
        with Image.open(self.destino / "Indicadores Puente/Aguja_base.png") as aguja:
            centro = aguja.width // 2
            self.assertGreater(aguja.getpixel((centro, centro))[3], 200)
            # La punta está arriba: hay dibujo encima del centro y casi nada debajo del remache.
            alfa = aguja.getchannel("A")
            arriba = sum(1 for y in range(centro) if alfa.getpixel((centro, y)) > 128)
            abajo = sum(1 for y in range(centro + 1, aguja.height) if alfa.getpixel((centro, y)) > 128)
            self.assertGreater(arriba, 3 * abajo)

    def test_no_modifica_los_originales(self):
        originales = IMAGENES / "assets finales"
        antes = {p.name: p.stat().st_mtime_ns for p in originales.iterdir()}
        from herramientas.preparar_arte_esencial import preparar
        with tempfile.TemporaryDirectory() as otro:
            preparar(destino=otro, informar=lambda *_: None)
        self.assertEqual(antes, {p.name: p.stat().st_mtime_ns for p in originales.iterdir()})


class MedidorPuenteTests(ConPantalla):
    def crear(self):
        from interfaz.minijuego_puente import LADO_MEDIDOR, RecursosPuente
        base = pygame.Surface((LADO_MEDIDOR, LADO_MEDIDOR), pygame.SRCALPHA)

        def cargar(nombre, tamano=None, requerido=True):
            return base if nombre.endswith("Indicador_base.png") else None
        return RecursosPuente(cargar), base

    def test_zona_dibujada_coincide_con_dentro_de_zona(self):
        recursos, _ = self.crear()
        lado = recursos.medidor.get_width()
        radio = recursos.radio_cara * .7  # mitad del grosor del arco
        tolerancia = CONFIGURACION["tolerancia_angulo"]
        for progreso in (0, 1, 2):
            zona = recursos.capas("normal", progreso)[1]
            objetivo = angulo_objetivo(progreso)
            pintados = []
            for grado in range(-180, 180):
                angulo = math.radians(grado)
                borde = abs((angulo - objetivo + math.pi) % math.tau - math.pi) - tolerancia
                if abs(borde) < math.radians(3):
                    continue  # el contorno de 2 px cae justo en el límite
                punto = (round(lado / 2 + radio * math.cos(angulo)), round(lado / 2 + radio * math.sin(angulo)))
                visible = zona.get_at(punto).a > 0
                self.assertEqual(visible, dentro_de_zona(angulo, progreso), (progreso, grado))
                if visible:
                    pintados.append(angulo)
            centro = math.atan2(sum(map(math.sin, pintados)), sum(map(math.cos, pintados)))
            self.assertAlmostEqual(centro, objetivo, delta=math.radians(1.5))

    def test_el_medidor_no_se_rota(self):
        recursos, base = self.crear()
        for progreso in (0, 1, 2):
            for estado in ("normal", "acierto", "error"):
                self.assertIs(recursos.capas(estado, progreso)[0], base)
        zonas = {id(recursos.capas("normal", p)[1]) for p in (0, 1, 2)}
        self.assertEqual(len(zonas), 3, "la que se mueve es la zona, no el medidor")

    def test_zonas_y_aguja_se_precalculan(self):
        recursos, _ = self.crear()
        self.assertIs(recursos.capas("acierto", 1)[1], recursos.capas("acierto", 1)[1])
        a = recursos.aguja_rotada(angulo_aguja(100))
        self.assertIs(a, recursos.aguja_rotada(angulo_aguja(100)))

    def test_juego_usa_el_medidor_y_la_aguja_nuevos(self):
        from interfaz.minijuego_puente import RecursosPuente
        if not (IMAGENES / "Indicadores Puente" / "Indicador_base.png").is_file():
            self.skipTest("Falta correr herramientas/preparar_arte_esencial.py")
        recursos = RecursosPuente()
        self.assertIsNotNone(recursos.medidor)
        self.assertEqual(recursos.origen_aguja, "Aguja_base")
        self.assertEqual(recursos.indicadores_viejos, {}, "el medidor anterior no se carga")
        self.assertEqual(recursos.aguja.get_width(), 2 * recursos.largo_aguja + 1)

    def test_dibujo_en_todos_los_estados(self):
        from interfaz.minijuego_puente import RecursosPuente, dibujar_panel
        recursos = RecursosPuente()
        lienzo = pygame.Surface((960, 720))
        for progreso in (0, 1, 2):
            for estado, fase in (("normal", None), ("acierto", .2), ("error", .6)):
                dibujar_panel(lienzo, recursos, fuentes(), {"progreso": progreso, "total": 3},
                              angulo_aguja(300 * progreso), estado, fase)


class RespaldosPuenteTests(ConPantalla):
    def test_sin_medidor_nuevo_usa_el_anterior_rotado(self):
        from interfaz.minijuego_puente import RecursosPuente, dibujar_panel
        recursos = RecursosPuente(cargar_sin("Indicador_base.png"))
        self.assertIsNone(recursos.medidor)
        self.assertIsNotNone(recursos.indicadores_viejos.get("normal"))
        self.assertIsNot(recursos.indicador_rotado("normal", 1), recursos.indicador_rotado("normal", 0))
        dibujar_panel(pygame.Surface((960, 720)), recursos, fuentes(), {"progreso": 1}, -1.0)

    def test_sin_aguja_nueva_usa_aguja7_y_sin_ninguna_la_raya(self):
        from interfaz.minijuego_puente import RecursosPuente, dibujar_panel
        self.assertEqual(RecursosPuente(cargar_sin("Aguja_base.png")).origen_aguja, "aguja7")
        recursos = RecursosPuente(cargar_sin("Aguja_base.png", "aguja7.png"))
        self.assertEqual(recursos.origen_aguja, "raya")
        self.assertIsNone(recursos.aguja_rotada(-1.0))
        dibujar_panel(pygame.Surface((960, 720)), recursos, fuentes(), {"progreso": 2}, -1.0, "error", .5)

    def test_sin_ningun_medidor_avisa_sin_fallar(self):
        from interfaz.minijuego_puente import RecursosPuente, dibujar_panel
        recursos = RecursosPuente(cargar_sin("Indicador_base.png", "Indicador.png", "IndicadorAcierto.png",
                                             "IndicadorError.png"))
        self.assertFalse(recursos.disponible)
        dibujar_panel(pygame.Surface((960, 720)), recursos, fuentes(), {}, -1.0)

    def test_finales_sin_imagenes_nuevas_usan_las_anteriores(self):
        from interfaz import finales
        pedidas = []

        def cargar(nombre, tamano=None, requerido=True):
            pedidas.append(nombre)
            return cargar_sin("Final_tres_eras.png", "Final_humo_tres_eras.png")(nombre, tamano, requerido)
        with mock.patch.object(finales, "cargar_imagen", cargar):
            pantalla = finales.PantallaFinal({"sabiduria": 90, "confianza": 90, "armonia": 90}, {},
                                             fuentes()["fuente_mapa"], fuentes()["fuente_panel"], total=6)
        self.assertIsNotNone(pantalla.imagen)
        self.assertEqual(pedidas, ["Finales/Final_tres_eras.png", "Finales/Final_positivo.jpeg"])


class FinalesTests(ConPantalla):
    def test_cargan_las_ilustraciones_nuevas(self):
        from interfaz import finales
        from nucleo.recursos import cargar_imagen
        for indicadores, esperado in (({"sabiduria": 90, "confianza": 90, "armonia": 90}, "Final_tres_eras.png"),
                                      ({"desinformacion": 90}, "Final_humo_tres_eras.png")):
            if not (IMAGENES / "Finales" / esperado).is_file():
                self.skipTest("Falta correr herramientas/preparar_arte_esencial.py")
            pedidas = []

            def cargar(nombre, tamano=None, requerido=True):
                pedidas.append(nombre)
                return cargar_imagen(nombre, tamano, requerido)
            with mock.patch.object(finales, "cargar_imagen", cargar):
                pantalla = finales.PantallaFinal(indicadores, {}, fuentes()["fuente_mapa"], fuentes()["fuente_panel"], total=6)
            self.assertEqual(pedidas, ["Finales/" + esperado], "no debe pedir las imágenes viejas")
            self.assertEqual(pantalla.imagen.get_size(), (960, 720))
            pantalla.dibujar(pygame.Surface((960, 720)))


class IntroTests(ConPantalla):
    def crear(self, feria=False):
        from interfaz.intro import Intro, VINETAS

        def cargar(nombre, tamano=None, requerido=True):
            return pygame.Surface(next(t for r, t, _ in VINETAS if r == nombre))
        return Intro.crear(feria=feria, cargar=cargar)

    @staticmethod
    def tecla(intro, tecla):
        intro.manejar_evento(pygame.event.Event(pygame.KEYDOWN, key=tecla, unicode="", mod=0))

    def test_espacio_avanza_y_termina(self):
        intro = self.crear()
        self.assertEqual(intro.indice, 0)
        self.tecla(intro, pygame.K_SPACE)
        self.assertEqual((intro.indice, intro.terminada), (1, False))
        intro.dibujar(pygame.Surface((960, 720)))
        intro.manejar_evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10)))
        self.assertTrue(intro.terminada)

    def test_esc_salta_toda_la_intro(self):
        intro = self.crear()
        self.tecla(intro, pygame.K_ESCAPE)
        self.assertTrue(intro.terminada)

    def test_en_feria_avanza_sola_a_los_seis_segundos(self):
        intro = self.crear(feria=True)
        intro.actualizar(5.9)
        self.assertEqual(intro.indice, 0)
        intro.actualizar(.2)
        self.assertEqual(intro.indice, 1)
        for _ in range(7):
            intro.actualizar(1.0)
        self.assertTrue(intro.terminada)

    def test_fuera_de_feria_no_avanza_sola(self):
        intro = self.crear()
        intro.actualizar(60)
        self.assertEqual((intro.indice, intro.terminada), (0, False))

    def test_sin_imagenes_se_salta(self):
        from interfaz.intro import Intro
        self.assertIsNone(Intro.crear(cargar=lambda *a, **k: None))

    def test_imagenes_reales_con_su_tamano(self):
        if not (IMAGENES / "Intro" / "vineta2.png").is_file():
            self.skipTest("Falta correr herramientas/preparar_arte_esencial.py")
        from interfaz.intro import Intro
        intro = Intro.crear()
        self.assertEqual([i.get_size() for i in intro.imagenes], [(960, 720), (960, 536)])
        lienzo = pygame.Surface((960, 720))
        intro.siguiente()
        intro.dibujar(lienzo)
        self.assertEqual(tuple(lienzo.get_at((480, 40)))[:3], (9, 18, 22), "banda #091216 arriba")


class IntroEnMenuTests(unittest.TestCase):
    """La regla de cuándo se muestra, sin abrir el menú completo."""

    def menu(self, ver_intro=True):
        return types.SimpleNamespace(pausa=types.SimpleNamespace(preferencias={"ver_intro": ver_intro}),
                                     salas_con_intro=set(), feria=False, intro=None)

    def empezar(self, menu, sala=None):
        from interfaz.inicio import MenuInicio
        with mock.patch("interfaz.intro.Intro.crear", return_value="intro"):
            MenuInicio.empezar_intro(menu, sala)

    def test_no_se_muestra_con_la_opcion_apagada(self):
        menu = self.menu(ver_intro=False)
        self.empezar(menu)
        self.assertIsNone(menu.intro)

    def test_se_muestra_al_empezar_y_no_al_volver_a_la_misma_sala(self):
        menu = self.menu()
        self.empezar(menu, "ABC123")
        self.assertEqual(menu.intro, "intro")
        self.empezar(menu, "ABC123")
        self.assertIsNone(menu.intro)
        self.empezar(menu)  # una campaña con bots nueva sí la muestra
        self.assertEqual(menu.intro, "intro")

    def test_preferencia_activada_por_defecto(self):
        from nucleo import preferencias
        self.assertIs(preferencias.PREDETERMINADAS["ver_intro"], True)


if __name__ == "__main__":
    unittest.main()
