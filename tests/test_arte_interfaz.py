"""Selección de personaje con retratos y arte nuevo conectado a la interfaz."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

from interfaz import arte, suministros  # noqa: E402
from multijugador.partida_local import ClienteCampanaLocal  # noqa: E402
from multijugador.protocolo import ROLES  # noqa: E402
from nucleo import preferencias  # noqa: E402
from nucleo.recursos import cargar_imagen  # noqa: E402


def setUpModule():
    pygame.init()
    pygame.display.set_mode((960, 720))


class ImagenesExisten(unittest.TestCase):
    def test_todas_las_rutas_del_arte_existen(self):
        rutas = [arte.NUEVOS + a for a in arte.EMBLEMAS.values()]
        rutas += [r for trio in arte.HABILIDADES.values() for r in trio]
        rutas += list(arte.ICONOS_PISTA.values())
        rutas += [f"Retratos/{c}/{p}_Num{n}.png" for c, p in arte.RETRATOS.values() for n in range(1, 5)]
        for ruta in rutas:
            with self.subTest(ruta=ruta):
                self.assertIsNotNone(cargar_imagen(ruta, requerido=False))

    def test_cada_personaje_tiene_cuatro_expresiones(self):
        for clave in arte.RETRATOS:
            self.assertEqual(len(arte.cargar_retratos(clave, (78, 88))), 4, clave)

    def test_el_arte_de_partida_carga_completo(self):
        partida = arte.ArtePartida()
        sueltos = (partida.retrato_agente, partida.marco, partida.flecha_izq, partida.flecha_der,
                   partida.tiempo, partida.arbol, partida.sello, partida.insignia)
        self.assertTrue(all(imagen is not None for imagen in sueltos))
        for grupo in (partida.emblemas_portal, partida.iconos_pista, partida.poder_grande, partida.poder_listo,
                      partida.poder_usado, partida.cestos):
            self.assertTrue(all(imagen is not None for imagen in grupo.values()))


class SeleccionCampana(unittest.TestCase):
    def setUp(self):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        ruta = mock.patch.object(preferencias, "ARCHIVO", Path(carpeta.name) / "p.json")
        ruta.start()
        self.addCleanup(ruta.stop)
        from interfaz.inicio import MenuInicio
        self.menu = MenuInicio()
        self.menu.accionar("campana_local")

    def test_muestra_una_tarjeta_con_retrato_por_personaje(self):
        with mock.patch.object(self.menu, "tarjeta_rol", wraps=self.menu.tarjeta_rol) as tarjeta:
            self.menu.dibujar()
        self.assertEqual(tarjeta.call_count, len(ROLES))
        self.assertEqual(set(self.menu.retratos), set(ROLES))
        for rol in ROLES:
            self.assertIn("rol_solo:" + rol, self.menu.botones)

    def test_elegir_una_tarjeta_cambia_el_personaje(self):
        self.menu.dibujar()
        self.assertEqual(self.menu.botones["rol_solo:guardian"].texto, "Elegido")
        self.menu.accionar("rol_solo:aspirante")
        self.menu.dibujar()
        self.assertEqual(self.menu.rol_solo, "aspirante")
        self.assertEqual(self.menu.botones["rol_solo:aspirante"].texto, "Elegido")
        self.assertEqual(self.menu.botones["rol_solo:guardian"].texto, "Elegir")

    def test_conserva_nombre_dificultad_e_inicio(self):
        self.menu.dibujar()
        self.assertIn("nombre", self.menu.areas_campos)
        for clave in ("dificultad_solo:facil", "dificultad_solo:dificil", "iniciar_campana_solo", "volver"):
            self.assertIn(clave, self.menu.botones)
        # Ningún control se solapa con otro.
        rects = [b.rect for b in self.menu.botones.values()]
        for i, rect in enumerate(rects):
            self.assertEqual(rect.collidelist(rects[i + 1:]), -1)


class ArteEnPartida(unittest.TestCase):
    def setUp(self):
        from interfaz.partida_multijugador import VistaPartida
        self.cliente = ClienteCampanaLocal("Prueba", "guardian")
        self.vista = VistaPartida("local", self.cliente.eventos.get_nowait())
        self.panel = self.vista.panel

    def test_retrato_segun_quien_habla(self):
        arte_v = self.vista.arte
        self.assertIn(self.panel.imagen_retrato("Testimonio de Luma"), arte_v.retratos["luma"])
        self.assertIn(self.panel.imagen_retrato("Mira · propuesta original"), arte_v.retratos["mira"])
        self.assertIs(self.panel.imagen_retrato("Darío Veraz · Fuente original"), arte_v.retrato_agente)

    def test_mirador_no_es_mira(self):
        self.assertIn(self.panel.imagen_retrato("Observación del mirador"), self.vista.arte.retratos["guardian"])

    def test_el_cesto_se_llena_con_los_materiales(self):
        lienzo = pygame.Surface((960, 720), pygame.SRCALPHA)
        fuente = pygame.font.Font(None, 16)
        encargo = {"materiales": [], "destino": {"x": 400, "y": 400, "nombre": "Puesto"}, "completo": False,
                   "cargas": {}, "actividad": {}, "materiales_listos": False}
        cestos = dict(suministros._cestos)
        self.assertEqual(set(cestos), {"vacio", "lleno"})
        with mock.patch.dict(suministros._cestos, {"lleno": None}):
            suministros.dibujar_encargos(lienzo, {"encargo": encargo}, fuente)  # usa el vacío
        with mock.patch.dict(suministros._cestos, {"vacio": None}):
            encargo["materiales_listos"] = True
            suministros.dibujar_encargos(lienzo, {"encargo": encargo}, fuente)  # usa el lleno
        self.assertGreater(lienzo.get_bounding_rect().width, 0)


class ZoomYHudDeLaCopa(unittest.TestCase):
    def setUp(self):
        from interfaz.partida_multijugador import VistaPartida
        self.cliente = ClienteCampanaLocal("Prueba", "guardian")
        self.vista = VistaPartida("local", self.cliente.eventos.get_nowait())
        self.vista.panel.modo = None
        self.lienzo = pygame.Surface((960, 720))

    def test_la_camara_solo_muestra_una_parte_y_sigue_al_personaje(self):
        from interfaz.partida_multijugador import ZOOM_COPA
        vista = self.vista.vista_camara()
        self.assertEqual(vista.size, (960 // ZOOM_COPA, 720 // ZOOM_COPA))
        posicion = self.vista.jugadores["local"]["posicion"]
        self.assertTrue(vista.collidepoint(posicion))

    def test_la_camara_no_se_sale_del_mapa_en_las_esquinas(self):
        mapa = pygame.Rect(0, 0, 960, 720)
        for esquina in ((0, 0), (960, 0), (0, 720), (960, 720)):
            self.vista.camara = pygame.Vector2(esquina)
            self.assertTrue(mapa.contains(self.vista.vista_camara()), esquina)
            self.vista.dibujar(self.lienzo, "LOCAL")

    def test_el_fondo_cubre_todo_el_mundo_ampliado(self):
        from interfaz.partida_multijugador import ZOOM_COPA
        self.assertEqual(self.vista.fondo_zoom.get_size(), (960 * ZOOM_COPA, 720 * ZOOM_COPA))
        self.assertEqual(self.vista.fondo.get_size(), (960, 720))

    def test_la_cascada_animada_ya_no_trae_rectangulo(self):
        cascada = next(o for o in self.vista.decoraciones if o.get("fondo_animado"))
        self.assertEqual(cascada["frames"][0].get_at((0, 0)).a, 0)
        self.assertGreater(cascada["frames"][0].get_bounding_rect().width, 0)

    def test_j_abre_y_cierra_los_detalles(self):
        self.assertFalse(self.vista.mostrar_detalles)
        evento = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j, mod=0, unicode="j", scancode=0)
        self.assertTrue(self.vista.manejar_evento(evento, (0, 0), self.cliente))
        self.assertTrue(self.vista.mostrar_detalles)
        self.vista.dibujar(self.lienzo, "LOCAL")

    def test_el_hud_cerrado_no_ocupa_la_zona_central(self):
        fondo = pygame.Surface((960, 720), pygame.SRCALPHA)
        with mock.patch.object(self.vista, "_pastilla", wraps=self.vista._pastilla) as pastilla:
            self.vista._dibujar_hud(fondo, "LOCAL", self.vista.estado["mundo"]["caso"],
                                    self.vista.estado["mundo"]["privado"], {"titulo": "Busca tu pista"})
        area = sum(llamada.args[1].width * llamada.args[1].height for llamada in pastilla.call_args_list)
        self.assertLess(area, 960 * 720 * .05)

    def test_menos_luciernagas(self):
        self.assertLessEqual(len(self.vista.particulas.luciernagas), 5)


class PuentesAmpliados(unittest.TestCase):
    def test_todos_los_objetivos_siguen_alcanzables(self):
        from multijugador.movimiento import ColisionesMapa, PartidaMovimiento
        colisiones = ColisionesMapa()
        partida = PartidaMovimiento([{"id": "a", "nombre": "A", "rol": "guardian"}], 0, colisiones)
        colisiones.bloqueos = []  # el Puente 1 se repara durante la partida
        inicio = (int(partida.jugadores["a"]["x"]) // 6, int(partida.jugadores["a"]["y"]) // 6)
        vistos, pila = {inicio}, [inicio]
        while pila:
            a, b = pila.pop()
            for p in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                if p not in vistos and 0 <= p[0] < 160 and 0 <= p[1] < 120 and not colisiones.bloqueado(p[0] * 6 + 3, p[1] * 6 + 3):
                    vistos.add(p)
                    pila.append(p)
        for objetivo in partida.mision.objetivos:
            libre = colisiones.inicio_libre(objetivo["x"], objetivo["y"])
            cerca = any((libre[0] // 6 + dx, libre[1] // 6 + dy) in vistos for dx in range(-3, 4) for dy in range(-3, 4))
            self.assertTrue(cerca, objetivo["id"])
        self.assertLess(len(vistos), 3000)  # sin fugas fuera de plataformas y puentes


if __name__ == "__main__":
    unittest.main()
