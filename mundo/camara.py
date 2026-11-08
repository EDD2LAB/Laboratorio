"""Cámara del mundo y conversión entre coordenadas de pantalla y de mundo."""

import math
import pygame
from nucleo.config import ALTO, ANCHO, CAMARA_RESPUESTA


def _limitar_camara(camara, rect_mapa, ancho_vista, alto_vista):
    if rect_mapa.width <= ancho_vista:
        min_x = max_x = rect_mapa.left - (ancho_vista - rect_mapa.width) / 2
    else:
        min_x = rect_mapa.left
        max_x = rect_mapa.right - ancho_vista
    if rect_mapa.height <= alto_vista:
        min_y = max_y = rect_mapa.top - (alto_vista - rect_mapa.height) / 2
    else:
        min_y = rect_mapa.top
        max_y = rect_mapa.bottom - alto_vista

    camara["x"] = min(max(camara["x"], min_x), max_x)
    camara["y"] = min(max(camara["y"], min_y), max_y)
    camara["x_render"] = round(camara["x"])
    camara["y_render"] = round(camara["y"])


def actualizar_camara_mundo(mundo, delta_ms=0, inmediata=False):
    camara = mundo.get("camara")
    if camara is None:
        return
    jugador = mundo["jugador"]
    rect_mapa = mundo.get("rect_mapa") or pygame.Rect(0, 0, ANCHO, ALTO)
    jugador_x, jugador_y = jugador["pies"].center
    zoom = camara["zoom"]
    ancho_vista = ANCHO / zoom
    alto_vista = ALTO / zoom
    destino_x = jugador_x - ancho_vista / 2
    destino_y = jugador_y - alto_vista / 2
    if inmediata:
        camara["x"] = destino_x
        camara["y"] = destino_y
    else:
        factor = 1 - math.exp(
            -CAMARA_RESPUESTA * max(0.0, float(delta_ms)) / 1000
        )
        camara["x"] += (destino_x - camara["x"]) * factor
        camara["y"] += (destino_y - camara["y"]) * factor
    _limitar_camara(camara, rect_mapa, ancho_vista, alto_vista)


def posicion_pantalla_a_mundo(posicion, mundo):
    camara = mundo.get("camara")
    if camara is None:
        return posicion
    zoom = camara["zoom"]
    return (
        round(camara.get("x_render", round(camara["x"])) + posicion[0] / zoom),
        round(camara.get("y_render", round(camara["y"])) + posicion[1] / zoom),
    )


def posicion_mundo_a_pantalla(posicion, mundo):
    camara = mundo.get("camara")
    if camara is None:
        return posicion
    zoom = camara["zoom"]
    return (
        round((posicion[0] - camara.get("x_render", round(camara["x"]))) * zoom),
        round((posicion[1] - camara.get("y_render", round(camara["y"]))) * zoom),
    )


def dibujar_escena_con_camara(superficie, escena, mundo):
    camara = mundo.get("camara")
    if camara is None:
        superficie.blit(escena, (0, 0))
        return
    zoom = camara["zoom"]
    ancho_vista = max(1, round(ANCHO / zoom))
    alto_vista = max(1, round(ALTO / zoom))
    vista = pygame.Surface((ancho_vista, alto_vista), pygame.SRCALPHA)
    vista.fill((18, 27, 38, 255))
    vista.blit(
        escena,
        (
            -camara.get("x_render", round(camara["x"])),
            -camara.get("y_render", round(camara["y"])),
        ),
    )
    superficie.blit(
        pygame.transform.scale(vista, (ANCHO, ALTO)),
        (0, 0),
    )
