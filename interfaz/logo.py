"""Logo animado del menú: brillo que pulsa y un glitch breve cada pocos segundos.

Todas las superficies se calculan una sola vez al crear el logo; en cada cuadro
solo se elige cuál dibujar.
"""
import random

import pygame

from nucleo.recursos import cargar_imagen

ARCHIVO = "Iconos/Icono_juego.png"
ALTO_LOGO = 100
PASOS_BRILLO = 8
PERIODO_BRILLO_MS = 2400
BRILLO_MAXIMO = 34
VARIANTES_GLITCH = 3
DURACION_GLITCH_MS = 150
ESPERA_GLITCH_MS = (3000, 5000)
ALTO_FRANJA = 7
SEPARACION_COLOR = 3


def _con_brillo(base, cantidad):
    imagen = base.copy()
    imagen.fill((cantidad, cantidad, cantidad, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return imagen


def _canal(base, color):
    imagen = base.copy()
    imagen.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return imagen


def _con_glitch(base, azar):
    """Separación de color y filas desplazadas, sin salirse del tamaño del logo."""
    ancho, alto = base.get_size()
    color = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    color.blit(_canal(base, (255, 0, 0)), (-SEPARACION_COLOR, 0), special_flags=pygame.BLEND_RGBA_ADD)
    color.blit(_canal(base, (0, 255, 0)), (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    color.blit(_canal(base, (0, 0, 255)), (SEPARACION_COLOR, 0), special_flags=pygame.BLEND_RGBA_ADD)
    resultado = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    for y in range(0, alto, ALTO_FRANJA):
        franja = color.subsurface((0, y, ancho, min(ALTO_FRANJA, alto - y)))
        resultado.blit(franja, (azar.choice((-8, -4, 0, 0, 0, 4, 8)), y))
    return resultado


class LogoAnimado:
    def __init__(self, alto=ALTO_LOGO, semilla=None):
        original = cargar_imagen(ARCHIVO)
        recorte = original.subsurface(original.get_bounding_rect())
        tamano = (round(recorte.get_width() * alto / recorte.get_height()), alto)
        base = pygame.transform.scale(recorte, tamano)
        self.azar = random.Random(semilla)
        # El brillo sube y baja: la mitad de los pasos se reutiliza al bajar.
        subida = [_con_brillo(base, BRILLO_MAXIMO * i // (PASOS_BRILLO // 2)) for i in range(PASOS_BRILLO // 2 + 1)]
        self.brillos = subida + subida[-2:0:-1]
        self.glitches = [_con_glitch(base, self.azar) for _ in range(VARIANTES_GLITCH)]
        self.tamano = tamano
        self.proximo_glitch = self.azar.randint(*ESPERA_GLITCH_MS)
        self.fin_glitch = 0
        self.glitch_actual = self.glitches[0]

    def cuadro(self, ahora_ms):
        if ahora_ms >= self.proximo_glitch:
            self.fin_glitch = ahora_ms + DURACION_GLITCH_MS
            self.proximo_glitch = self.fin_glitch + self.azar.randint(*ESPERA_GLITCH_MS)
            self.glitch_actual = self.azar.choice(self.glitches)
        if ahora_ms < self.fin_glitch:
            return self.glitch_actual
        return self.brillos[(ahora_ms % PERIODO_BRILLO_MS) * len(self.brillos) // PERIODO_BRILLO_MS]

    def rect(self, centro):
        return pygame.Rect((0, 0), self.tamano).move(centro[0] - self.tamano[0] // 2, centro[1] - self.tamano[1] // 2)

    def dibujar(self, superficie, centro, ahora_ms):
        superficie.blit(self.cuadro(ahora_ms), self.rect(centro))
