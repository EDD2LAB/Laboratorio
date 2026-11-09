"""Ventana del sistema y presentación del lienzo lógico 960x720."""

import pygame
from nucleo.config import ALTO, ANCHO, RELACION_ASPECTO


def tamano_ventana_inicial():
    info = pygame.display.Info()
    max_ancho = max(640, int(info.current_w * 0.92))
    max_alto = max(480, int(info.current_h * 0.86))
    if max_ancho / max_alto > RELACION_ASPECTO:
        alto = max_alto
        ancho = int(alto * RELACION_ASPECTO)
    else:
        ancho = max_ancho
        alto = int(ancho / RELACION_ASPECTO)
    return ancho, alto


def crear_ventana(pantalla_completa, maximizada=False):
    """Crea una ventana cuyo lienzo se escala hasta ocupar todo el espacio."""
    from nucleo.recursos import aplicar_icono_ventana
    aplicar_icono_ventana()
    if pantalla_completa:
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pantalla = pygame.display.set_mode(tamano_ventana_inicial(), pygame.RESIZABLE)
    if maximizada:
        from pygame._sdl2 import Window

        Window.from_display_module().maximize()
    return pantalla


def rect_lienzo_en_ventana(tamano_ventana):
    ancho_ventana, alto_ventana = tamano_ventana
    return pygame.Rect(0, 0, max(1, ancho_ventana), max(1, alto_ventana))


def convertir_mouse_a_lienzo(posicion, rect_lienzo):
    if not rect_lienzo.collidepoint(posicion):
        return (-1, -1)
    escala_x = ANCHO / rect_lienzo.width
    escala_y = ALTO / rect_lienzo.height
    x = int((posicion[0] - rect_lienzo.x) * escala_x)
    y = int((posicion[1] - rect_lienzo.y) * escala_y)
    return (x, y)


def presentar_lienzo(pantalla, lienzo):
    """Escala el lienzo para ocupar la ventana completa."""
    rect_destino = rect_lienzo_en_ventana(pantalla.get_size())
    pantalla.fill((0, 0, 0))
    escalado = pygame.transform.scale(lienzo, rect_destino.size)
    pantalla.blit(escalado, rect_destino)
    return rect_destino
