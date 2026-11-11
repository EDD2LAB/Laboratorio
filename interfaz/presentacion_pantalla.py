"""Presenta el lienzo 960x720 en la ventana conservando su proporción 4:3.

El lienzo se amplía por igual en ambos ejes hasta el mayor tamaño que cabe
y se centra; el espacio sobrante queda en bandas negras (pixel art:
``scale``, nunca ``smoothscale``).
"""
import pygame

ANCHO_LIENZO, ALTO_LIENZO = 960, 720
COLOR_BANDAS = (0, 0, 0)


def rect_destino(tamano):
    """Rectángulo centrado de la ventana donde se dibuja el lienzo sin deformarlo."""
    ancho, alto = max(1, tamano[0]), max(1, tamano[1])
    escala = min(ancho / ANCHO_LIENZO, alto / ALTO_LIENZO)
    destino_ancho = max(1, round(ANCHO_LIENZO * escala))
    destino_alto = max(1, round(ALTO_LIENZO * escala))
    return pygame.Rect((ancho - destino_ancho) // 2, (alto - destino_alto) // 2, destino_ancho, destino_alto)


def a_lienzo(posicion, tamano):
    """Convierte una posición de la ventana a coordenadas del lienzo.

    Fuera del lienzo (sobre las bandas) devuelve ``(-1, -1)``.
    """
    rect = rect_destino(tamano)
    if not rect.collidepoint(posicion):
        return (-1, -1)
    return ((posicion[0] - rect.x) * ANCHO_LIENZO / rect.width,
            (posicion[1] - rect.y) * ALTO_LIENZO / rect.height)


def presentar(pantalla, lienzo):
    tamano = pantalla.get_size()
    if tamano == lienzo.get_size():
        pantalla.blit(lienzo, (0, 0))
        return
    rect = rect_destino(tamano)
    if rect.size != tamano:
        pantalla.fill(COLOR_BANDAS)
    try:
        # Directo sobre la ventana: sin crear una superficie enorme en cada cuadro.
        pygame.transform.scale(lienzo, rect.size, pantalla.subsurface(rect))
    except ValueError:  # formatos de píxel distintos
        pantalla.blit(pygame.transform.scale(lienzo, rect.size), rect)
