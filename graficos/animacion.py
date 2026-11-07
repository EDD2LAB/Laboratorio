import pygame


def extraer_frames_horizontales(imagen, cantidad):
    cantidad = max(1, int(cantidad))
    ancho_frame = max(1, imagen.get_width() // cantidad)
    return [
        imagen.subsurface(
            pygame.Rect(indice * ancho_frame, 0, ancho_frame, imagen.get_height())
        ).copy()
        for indice in range(cantidad)
    ]


def crear_frame_animado_suave(frames, tamano, tiempo_ms, duracion_frame=110, alpha=255):
    if not frames:
        return None

    fase = max(0, tiempo_ms) / max(1, duracion_frame)
    indice = int(fase) % len(frames)
    siguiente = (indice + 1) % len(frames)
    mezcla = fase % 1
    mezcla = mezcla * mezcla * (3 - 2 * mezcla)

    actual = pygame.transform.smoothscale(frames[indice], tamano)
    if siguiente == indice or mezcla <= 0:
        if alpha < 255:
            actual.set_alpha(alpha)
        return actual

    proximo = pygame.transform.smoothscale(frames[siguiente], tamano)
    capa = pygame.Surface(tamano, pygame.SRCALPHA)
    actual.set_alpha(round(alpha * (1 - mezcla)))
    proximo.set_alpha(round(alpha * mezcla))
    capa.blit(actual, (0, 0))
    capa.blit(proximo, (0, 0))
    return capa
