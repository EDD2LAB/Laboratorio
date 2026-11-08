"""Presenta el lienzo 960x720 ocupando toda la ventana, sin bandas ni relleno.

El propio juego llega hasta los bordes: el lienzo se estira en cada eje al
tamaño de la ventana (pixel art: ``scale``, nunca ``smoothscale``).
"""
import pygame

ANCHO_LIENZO, ALTO_LIENZO = 960, 720


def a_lienzo(posicion, tamano):
    """Convierte una posición de la ventana a coordenadas del lienzo."""
    return (posicion[0] * ANCHO_LIENZO / max(1, tamano[0]),
            posicion[1] * ALTO_LIENZO / max(1, tamano[1]))


def presentar(pantalla, lienzo):
    tamano = pantalla.get_size()
    if tamano == lienzo.get_size():
        pantalla.blit(lienzo, (0, 0))
        return
    try:
        # Directo sobre la ventana: sin crear una superficie enorme en cada cuadro.
        pygame.transform.scale(lienzo, tamano, pantalla)
    except ValueError:  # formatos de píxel distintos
        pantalla.blit(pygame.transform.scale(lienzo, tamano), (0, 0))
