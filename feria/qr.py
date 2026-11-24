"""QR de la sesión como superficie de pygame (módulos nítidos, sin suavizado)."""
import pygame

ZONA_SILENCIO = 4  # módulos blancos alrededor: los lectores la necesitan


def superficie_qr(texto, lado_max):
    """QR de ``texto`` que cabe en ``lado_max`` px, con módulos de tamaño entero."""
    import segno  # solo al dibujar: el módulo se puede importar sin la librería
    qr = segno.make(texto, error="m", micro=False)
    filas = [list(fila) for fila in qr.matrix]
    modulos = len(filas) + 2 * ZONA_SILENCIO
    tam = max(1, lado_max // modulos)
    superficie = pygame.Surface((modulos * tam, modulos * tam))
    superficie.fill((255, 255, 255))
    for y, fila in enumerate(filas):
        for x, oscuro in enumerate(fila):
            if oscuro:
                superficie.fill((0, 0, 0), ((x + ZONA_SILENCIO) * tam, (y + ZONA_SILENCIO) * tam, tam, tam))
    return superficie
