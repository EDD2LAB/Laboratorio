"""Colisiones del jugador con hitboxes y zonas caminables."""

import math
import pygame
from nucleo.config import ALTO, ANCHO


def _rect_hits_line(rect, x1, y1, x2, y2, grosor):
    dx, dy = x2 - x1, y2 - y1
    longitud_cuadrada = dx * dx + dy * dy
    if longitud_cuadrada == 0:
        px, py = x1, y1
    else:
        t = max(0, min(1, ((rect.centerx - x1) * dx + (rect.centery - y1) * dy) / longitud_cuadrada))
        px, py = x1 + t * dx, y1 + t * dy
    radio = math.hypot(rect.width, rect.height) / 2 + grosor / 2
    return (rect.centerx - px) ** 2 + (rect.centery - py) ** 2 <= radio * radio


def colision_hitbox_mapa(rect, hitbox):
    tipo = hitbox.get("type", "rect")
    if tipo == "rect":
        obstaculo = pygame.Rect(
            round(hitbox.get("rx", 0) * ANCHO),
            round(hitbox.get("ry", 0) * ALTO),
            max(1, round(hitbox.get("rw", 0) * ANCHO)),
            max(1, round(hitbox.get("rh", 0) * ALTO)),
        )
        return rect.colliderect(obstaculo)
    if tipo == "circle":
        cx, cy = hitbox.get("cx", 0) * ANCHO, hitbox.get("cy", 0) * ALTO
        radio = max(4, hitbox.get("r", 0) * ANCHO)
        nx = max(rect.left, min(cx, rect.right))
        ny = max(rect.top, min(cy, rect.bottom))
        return (cx - nx) ** 2 + (cy - ny) ** 2 <= radio * radio
    if tipo == "line":
        return _rect_hits_line(
            rect,
            hitbox.get("x1", 0) * ANCHO,
            hitbox.get("y1", 0) * ALTO,
            hitbox.get("x2", 0) * ANCHO,
            hitbox.get("y2", 0) * ALTO,
            max(2, hitbox.get("thickness", 0.008) * ANCHO),
        )
    return False


def contiene_zona_caminable(rect, hitbox):
    if hitbox.get("type", "rect") == "rect":
        zona = pygame.Rect(
            round(hitbox.get("rx", 0) * ANCHO),
            round(hitbox.get("ry", 0) * ALTO),
            max(1, round(hitbox.get("rw", 0) * ANCHO)),
            max(1, round(hitbox.get("rh", 0) * ALTO)),
        )
        return zona.contains(rect)
    if hitbox.get("type") == "circle":
        cx, cy = hitbox.get("cx", 0) * ANCHO, hitbox.get("cy", 0) * ALTO
        radio = hitbox.get("r", 0) * ANCHO
        return all((x - cx) ** 2 + (y - cy) ** 2 <= radio * radio for x, y in (
            rect.topleft, rect.topright, rect.bottomleft, rect.bottomright
        ))
    return False


def jugador_bloqueado(rect, mundo):
    if not pygame.Rect(0, 0, ANCHO, ALTO).contains(rect):
        return True
    limites_mapa = mundo.get("rect_mapa")
    if limites_mapa and not limites_mapa.contains(rect):
        return True
    reparacion = mundo.get("reparacion_puentes")
    if (
        reparacion
        and reparacion.bloquea_paso
        and rect.colliderect(reparacion.hitbox_puente)
    ):
        return True
    if any(
        hitbox.get("role", "wall") == "wall" and colision_hitbox_mapa(rect, hitbox)
        for hitbox in mundo["hitboxes"]
    ):
        return True
    zonas_caminables = [
        hitbox for hitbox in mundo["hitboxes"]
        if hitbox.get("role") == "walkable"
    ]
    if zonas_caminables and not any(
        contiene_zona_caminable(rect, zona) for zona in zonas_caminables
    ):
        return True
    return any(
        personaje["rect"].colliderect(rect) for personaje in mundo["personajes"]
    )
