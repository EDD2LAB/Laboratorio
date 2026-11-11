"""Resaltado dorado del objetivo que se elige con E y que cambia con Tab."""
import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from interfaz.resaltado import ALFA_MAX, ALFA_MIN, DORADO, Resaltado, alfa_pulso  # noqa: E402


def silueta():
    """Un personaje de prueba: rectángulo opaco de 10x20 dentro de un lienzo transparente."""
    imagen = pygame.Surface((20, 30), pygame.SRCALPHA)
    imagen.fill((40, 90, 200, 255), (5, 5, 10, 20))
    return imagen


class ConPantalla(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 720))
        self.addCleanup(pygame.quit)


class ContornoDorado(ConPantalla):
    def test_el_borde_rodea_la_silueta_sin_taparla(self):
        lienzo = pygame.Surface((60, 60), pygame.SRCALPHA)
        imagen = silueta()
        rect = imagen.get_rect(topleft=(20, 15))
        lienzo.blit(imagen, rect)
        Resaltado().contorno(lienzo, imagen, rect, 0, grosor=2)
        # Justo fuera del borde izquierdo del cuerpo: dorado.
        self.assertEqual(tuple(lienzo.get_at((rect.x + 4, rect.y + 15)))[:3], DORADO)
        # Dentro del cuerpo: el color del personaje sigue igual.
        self.assertEqual(tuple(lienzo.get_at((rect.x + 10, rect.y + 15)))[:3], (40, 90, 200))
        # Lejos de la silueta no se pinta nada.
        self.assertEqual(lienzo.get_at((1, 1)).a, 0)

    def test_el_contorno_se_calcula_una_sola_vez_por_imagen(self):
        resaltado, imagen = Resaltado(), silueta()
        lienzo = pygame.Surface((80, 80), pygame.SRCALPHA)
        for t in range(0, 2000, 100):
            resaltado.contorno(lienzo, imagen, (10, 10), t)
        self.assertEqual(resaltado.calculos, 1)
        resaltado.contorno(lienzo, silueta(), (10, 10), 0)  # otro cuadro de animación
        self.assertEqual(resaltado.calculos, 2)

    def test_el_brillo_pulsa_entre_sus_limites(self):
        valores = {alfa_pulso(t) for t in range(0, 1200, 25)}
        self.assertGreaterEqual(min(valores), ALFA_MIN)
        self.assertLessEqual(max(valores), ALFA_MAX)
        self.assertGreater(max(valores) - min(valores), 60)
        self.assertEqual(alfa_pulso(300, fijo=True), ALFA_MAX)

    def test_anillo_para_lo_pintado_en_el_mapa(self):
        lienzo = pygame.Surface((100, 60), pygame.SRCALPHA)
        Resaltado().anillo(lienzo, pygame.Rect(30, 20, 40, 16), 0)
        dorados = sum(1 for x in range(100) for y in range(60) if tuple(lienzo.get_at((x, y)))[:3] == DORADO)
        self.assertGreater(dorados, 20)
        self.assertEqual(lienzo.get_at((50, 28)).a, 0)  # el centro queda libre

    def test_tecla_e_existe_aunque_falte_la_imagen(self):
        fuente = pygame.font.Font(None, 20)
        with mock.patch("interfaz.resaltado.RUTA_TECLA_E") as ruta:
            ruta.exists.return_value = False
            tecla = Resaltado().tecla(fuente, 0)
        self.assertGreater(tecla.get_width(), 10)


class SeleccionConTab(ConPantalla):
    def setUp(self):
        super().setUp()
        from interfaz.partida_multijugador import VistaPartida
        from multijugador.movimiento import PartidaMovimiento
        roles = ("guardian", "mensajero")
        p = PartidaMovimiento([dict(id=str(i), nombre="J" + str(i), rol=roles[i]) for i in range(2)], 0)
        self.vista = VistaPartida("0", {"mundo": p.estado("0")})
        self.vista.panel.modo = None  # cierra la introducción con la que empieza la partida
        yo = self.vista.yo()
        self.opciones = [
            {"id": "npc:guardian", "nombre": "Hablar con el Guardián", "x": yo["x"] + 10, "y": yo["y"]},
            {"id": "caldero", "nombre": "Usar el caldero", "x": yo["x"] - 20, "y": yo["y"]},
        ]
        self.vista.candidatos = lambda: list(self.opciones)

    def pulsar(self, tecla):
        evento = pygame.event.Event(pygame.KEYDOWN, key=tecla, mod=0, unicode="")
        self.vista.manejar_evento(evento, (0, 0), mock.Mock())

    def test_el_primero_cercano_queda_resaltado(self):
        objetivo = self.vista._calcular_resaltado()
        self.assertEqual(objetivo["id"], "npc:guardian")
        self.assertTrue(objetivo["varios"])

    def test_tab_pasa_el_resaltado_al_caldero_y_e_usa_ese(self):
        self.vista._calcular_resaltado()
        self.pulsar(pygame.K_TAB)
        objetivo = self.vista._calcular_resaltado()
        self.assertEqual((objetivo["id"], objetivo["tipo"]), ("caldero", "caldero"))
        cliente = mock.Mock()
        self.vista.manejar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, mod=0, unicode="e"), (0, 0), cliente)
        cliente.actuar.assert_called_with("interactuar", objetivo="caldero")

    def test_lejos_de_todo_no_hay_resaltado(self):
        self.opciones.clear()
        self.assertIsNone(self.vista._calcular_resaltado())

    def test_con_un_panel_abierto_no_hay_resaltado(self):
        with mock.patch.object(type(self.vista.panel), "activo", new_callable=mock.PropertyMock, return_value=True):
            self.assertIsNone(self.vista._calcular_resaltado())

    def test_con_el_menu_de_pausa_no_hay_resaltado_y_vuelve_al_cerrarlo(self):
        self.vista.en_pausa = True
        self.assertIsNone(self.vista._calcular_resaltado())
        self.vista.en_pausa = False
        self.assertEqual(self.vista._calcular_resaltado()["id"], "npc:guardian")

    def test_sin_sprite_propio_se_resalta_alrededor_de_su_hitbox(self):
        hitbox = pygame.Rect(200, 200, 40, 60)
        self.vista.objetivo_resaltado = dict(id="entrar:x", tipo="objeto", clave="entrar:x",
                                             x=220, y=260, varios=False, hitbox=hitbox)
        self.vista._resaltado_hecho = False
        suelo = pygame.Surface((960, 720), pygame.SRCALPHA)
        self.vista._resaltar_sin_sprite(suelo)
        self.assertTrue(self.vista._resaltado_hecho)
        dorados = [(x, y) for x in range(150, 290) for y in range(150, 320)
                   if suelo.get_at((x, y)).a and tuple(suelo.get_at((x, y)))[:3] == DORADO]
        self.assertTrue(dorados)
        # El anillo rodea la hitbox: nada dorado dentro de ella.
        self.assertFalse([p for p in dorados if hitbox.collidepoint(p)])
        self.assertLess(min(x for x, _ in dorados), hitbox.left)
        self.assertGreater(max(x for x, _ in dorados), hitbox.right)

    def test_dibujar_resalta_y_no_recalcula_en_cada_cuadro(self):
        lienzo = pygame.Surface((960, 720))
        with mock.patch("pygame.time.get_ticks", return_value=1000):
            self.vista.dibujar(lienzo, "ABC")
            self.assertTrue(self.vista._resaltado_hecho)
            calculos = self.vista.resaltado.calculos
            self.vista.dibujar(lienzo, "ABC")
        self.assertEqual(self.vista.resaltado.calculos, calculos)
