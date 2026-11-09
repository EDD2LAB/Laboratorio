"""Ubicación de nombres sin superponer sus fondos ni los controles del mapa."""
import pygame


def colocar_etiquetas(elementos, limites, reservadas=()):
    """Prioriza al jugador local y conserva un vínculo con la cabeza del personaje."""
    colocadas = []
    for elemento in sorted(elementos, key=lambda e: (not e["local"], e["bot"], e["id"])):
        x, y = elemento["ancla"]
        ancho, alto = elemento["imagen"].get_size()
        base = pygame.Rect(0, 0, ancho + 12, alto + 8)
        base.midbottom = (x, y - 6)
        opciones = []
        paso = base.height + 6
        for fila in range(18):
            for lado in ((-1, 1) if fila else (0,)):
                rect = base.move(0, fila * paso * lado)
                rect.clamp_ip(limites)
                if any(rect.inflate(6, 6).colliderect(r) for r in reservadas):
                    continue
                if any(rect.inflate(6, 6).colliderect(e["rect"]) for e in colocadas):
                    continue
                opciones.append(rect)
            if opciones:
                break
        if opciones:
            rect = min(opciones, key=lambda r: abs(r.centerx - x) + abs(r.bottom - y))
            colocadas.append(dict(elemento, rect=rect))
    return colocadas
