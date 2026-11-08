"""Movimiento del jugador local e interactuables cercanos."""

import math
import pygame
from mundo.colisiones import jugador_bloqueado
from nucleo.config import ALTO, ANCHO, DISTANCIA_INTERACCION, VELOCIDAD_GUARDIAN


def ajustar_inicio_jugador(jugador, mundo):
    origen = jugador["pies"]
    if not jugador_bloqueado(origen, mundo):
        return

    for distancia in range(1, 65):
        for desplazamiento_y in range(-distancia, distancia + 1):
            desplazamiento_x = distancia - abs(desplazamiento_y)
            desplazamientos = (
                [(0, desplazamiento_y)]
                if desplazamiento_x == 0
                else [(-desplazamiento_x, desplazamiento_y), (desplazamiento_x, desplazamiento_y)]
            )
            for dx, dy in desplazamientos:
                candidato = origen.move(dx, dy)
                if jugador_bloqueado(candidato, mundo):
                    continue
                if any(
                    jugador_bloqueado(candidato.move(paso_x, paso_y), mundo)
                    for paso in range(1, 4)
                    for paso_x, paso_y in (
                        (-paso, 0), (paso, 0), (0, -paso), (0, paso)
                    )
                ):
                    continue
                jugador["pies"] = candidato
                jugador["posicion_x"] = float(candidato.x)
                jugador["posicion_y"] = float(candidato.y)
                jugador["rect"].midbottom = candidato.midbottom
                return

    raise RuntimeError("No se encontró una posición inicial libre para el Guardián.")


def _posicion_interaccion(jugador, interactuable):
    rect = interactuable["rect"]
    x = max(rect.left, min(jugador["pies"].centerx, rect.right))
    y = max(rect.top, min(jugador["pies"].centery, rect.bottom))
    return math.hypot(jugador["pies"].centerx - x, jugador["pies"].centery - y)


def buscar_interactuable_cercano(jugador, mundo):
    candidatos = [
        *mundo["personajes"],
        *mundo["interacciones"],
    ]
    cercanos = [
        (distancia, objeto)
        for objeto in candidatos
        if objeto.get("activo", True)
        and (distancia := _posicion_interaccion(jugador, objeto)) <= objeto.get("distancia", DISTANCIA_INTERACCION)
    ]
    cercanos.sort(key=lambda elemento: elemento[0])
    if not cercanos:
        mundo["interacciones_cercanas"] = []
        mundo["interaccion_seleccionada"] = None
        return None, None
    mundo["interacciones_cercanas"] = cercanos
    ids = [objeto.get("id", objeto.get("personaje", objeto["accion"])) for _, objeto in cercanos]
    seleccionada = mundo.get("interaccion_seleccionada")
    if seleccionada not in ids:
        seleccionada = ids[0]
        mundo["interaccion_seleccionada"] = seleccionada
    indice = ids.index(seleccionada)
    distancia, interactuable = cercanos[indice]
    interactuable["alternativas_cercanas"] = len(cercanos)
    interactuable["indice_alternativa"] = indice + 1
    return interactuable, distancia


def alternar_interactuable_cercano(mundo, sentido=1):
    cercanos = mundo.get("interacciones_cercanas", [])
    if len(cercanos) < 2:
        return
    ids = [objeto.get("id", objeto.get("personaje", objeto["accion"])) for _, objeto in cercanos]
    actual = mundo.get("interaccion_seleccionada")
    indice = ids.index(actual) if actual in ids else 0
    mundo["interaccion_seleccionada"] = ids[(indice + sentido) % len(ids)]


def reiniciar_jugador_en_casa(mundo):
    jugador = mundo["jugador"]
    jugador["pies"] = mundo["posicion_casa"].copy()
    jugador["posicion_x"] = float(jugador["pies"].x)
    jugador["posicion_y"] = float(jugador["pies"].y)
    jugador["rect"].midbottom = jugador["pies"].midbottom
    jugador["direccion"] = "abajo"
    jugador["en_movimiento"] = False
    jugador["estado_visual"] = "idle"
    jugador["indice_frame"] = 0
    jugador["tiempo_animacion"] = 0.0
    mundo["interaccion_seleccionada"] = None


def tecla_activa(teclas, *codigos):
    if teclas is None:
        return False
    for codigo in codigos:
        try:
            valor = teclas[codigo]
        except (KeyError, TypeError):
            valor = False
        if valor:
            return True
    return False


def mover_jugador(jugador, mundo, teclas, delta_ms):
    dx = int(tecla_activa(teclas, pygame.K_d, pygame.K_RIGHT)) - int(tecla_activa(teclas, pygame.K_a, pygame.K_LEFT))
    dy = int(tecla_activa(teclas, pygame.K_s, pygame.K_DOWN)) - int(tecla_activa(teclas, pygame.K_w, pygame.K_UP))
    velocidad = VELOCIDAD_GUARDIAN * (
        1.65 if tecla_activa(teclas, pygame.K_LSHIFT, pygame.K_RSHIFT) else 1.0
    )
    habilidad = mundo.get("habilidad")
    if habilidad:
        velocidad *= habilidad.multiplicador_movimiento
    movimiento = dx != 0 or dy != 0
    jugador["en_movimiento"] = movimiento
    if not movimiento:
        return
    direcciones_diagonales = {
        (1, 1): "abajo_derecha",
        (1, -1): "arriba_derecha",
        (-1, -1): "arriba_izquierda",
        (-1, 1): "abajo_izquierda",
    }
    direccion = direcciones_diagonales.get((dx, dy))
    if direccion is None:
        direccion = "arriba" if dy < 0 else "abajo" if dy > 0 else (
            "derecha" if dx > 0 else "izquierda"
        )
    if direccion != jugador["direccion"]:
        jugador["direccion"] = direccion
        jugador["indice_frame"] = 0
    if dx and dy:
        direccion_movimiento = "derecha" if dx > 0 else "izquierda"
    else:
        direccion_movimiento = direccion
    jugador["direccion_movimiento"] = direccion_movimiento
    if dx and dy:
        dx *= math.sqrt(0.5)
        dy *= math.sqrt(0.5)
    delta = min(max(delta_ms, 0), 100) / 1000
    pasos = max(1, math.ceil(velocidad * delta / 3))
    paso_x = dx * velocidad * delta / pasos
    paso_y = dy * velocidad * delta / pasos
    posicion_x = jugador.get("posicion_x", float(jugador["pies"].x))
    posicion_y = jugador.get("posicion_y", float(jugador["pies"].y))
    jugador["tiempo_animacion"] += delta_ms
    while jugador["tiempo_animacion"] >= 110:
        jugador["tiempo_animacion"] -= 110
        frames_direccion = jugador["frames_caminar"].get(
            jugador.get("direccion_movimiento", jugador["direccion"]), []
        )
        if frames_direccion:
            jugador["indice_frame"] = (jugador["indice_frame"] + 1) % len(frames_direccion)

    for _ in range(pasos):
        for eje, movimiento_eje in (("x", paso_x), ("y", paso_y)):
            if not movimiento_eje:
                continue
            pies = jugador["pies"].copy()
            candidato = (posicion_x if eje == "x" else posicion_y) + movimiento_eje
            setattr(pies, eje, round(candidato))
            if not pygame.Rect(0, 0, ANCHO, ALTO).contains(pies):
                continue
            if not jugador_bloqueado(pies, mundo):
                jugador["pies"] = pies
                if eje == "x":
                    posicion_x = candidato
                else:
                    posicion_y = candidato
    jugador["posicion_x"] = posicion_x
    jugador["posicion_y"] = posicion_y
    jugador["rect"].midbottom = jugador["pies"].midbottom
