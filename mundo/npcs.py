"""Patrullas de los NPC de Distrito Conecta."""

import math
from logica.dimensiones import DIMENSION_PRESENTE
from mundo.colisiones import colision_hitbox_mapa, contiene_zona_caminable
from nucleo.config import (
    ESCENA_MAPA,
    PAUSA_PATRULLA_NPC_MS,
    PROBABILIDAD_PAUSA_NPC,
    RADIO_WAYPOINT_NPC,
    VARIACION_VELOCIDAD_NPC,
    VELOCIDAD_PATRULLA_NPC,
)


def _direccion_npc(dx, dy):
    if abs(dx) >= abs(dy):
        return "derecha" if dx >= 0 else "izquierda"
    return "abajo" if dy >= 0 else "arriba"


def _siguiente_waypoint_npc(objeto):
    ruta = objeto["ruta_npc"]
    indice = objeto["indice_waypoint"]
    if ruta["pattern"] == "loop":
        objeto["indice_waypoint"] = (indice + 1) % len(ruta["points"])
        return
    siguiente = indice + objeto["direccion_ruta"]
    if not 0 <= siguiente < len(ruta["points"]):
        objeto["direccion_ruta"] *= -1
        siguiente = indice + objeto["direccion_ruta"]
    objeto["indice_waypoint"] = siguiente


def actualizar_npcs_presentes(mundo, delta_ms):
    if mundo.get("dimension") != DIMENSION_PRESENTE:
        return
    delta_ms = max(0.0, float(delta_ms))
    jugador = mundo["jugador"]
    rect_mapa = mundo["rect_mapa"]
    pausados = mundo.get("npc_pausados", False)
    hitboxes_muro = [
        hitbox for hitbox in mundo["hitboxes"]
        if hitbox.get("role") == "wall"
    ]
    zonas_caminables = [
        hitbox for hitbox in mundo["hitboxes"]
        if hitbox.get("role") == "walkable"
    ]
    for actor in mundo["personajes"]:
        objeto = actor.get("objeto")
        if not objeto or not objeto.get("ruta_npc"):
            continue
        estado = objeto["estado_ruta"]
        if mundo.get("escena_actual") != ESCENA_MAPA or pausados:
            objeto["estado_ruta"] = (
                "INTERACTING"
                if mundo.get("npc_en_dialogo") == actor["personaje"]
                else "PAUSED_BY_EVENT"
            )
            continue
        if estado in ("INTERACTING", "PAUSED_BY_EVENT"):
            objeto["estado_ruta"] = "WAITING"
            objeto["tiempo_estado_ms"] = 500
            continue
        if estado in ("IDLE", "WAITING", "TURNING"):
            objeto["tiempo_estado_ms"] -= delta_ms
            if objeto["tiempo_estado_ms"] > 0:
                continue
            objeto["estado_ruta"] = "WALKING"

        ruta = objeto["ruta_npc"]
        destino = ruta["points"][objeto["indice_waypoint"]]
        x = objeto["posicion_ruta_x"]
        y = objeto["posicion_ruta_y"]
        dx = destino[0] - x
        dy = destino[1] - y
        distancia = math.hypot(dx, dy)
        paso_maximo = objeto["velocidad_ruta"] * min(delta_ms, 100) / 1000
        if distancia <= max(
            RADIO_WAYPOINT_NPC,
            paso_maximo,
        ):
            x, y = destino
            objeto["posicion_ruta_x"] = x
            objeto["posicion_ruta_y"] = y
            direccion_anterior = objeto["direccion"]
            _siguiente_waypoint_npc(objeto)
            siguiente = ruta["points"][objeto["indice_waypoint"]]
            objeto["direccion"] = _direccion_npc(
                siguiente[0] - x,
                siguiente[1] - y,
            )
            objeto["tiempo_frame_ms"] = 0.0
            objeto["indice_frame"] = 0
            if objeto["random_ruta"].random() < PROBABILIDAD_PAUSA_NPC:
                objeto["estado_ruta"] = "WAITING"
                objeto["tiempo_estado_ms"] = objeto["random_ruta"].uniform(
                    *PAUSA_PATRULLA_NPC_MS
                )
            elif objeto["direccion"] != direccion_anterior:
                objeto["estado_ruta"] = "TURNING"
                objeto["tiempo_estado_ms"] = 120
            else:
                objeto["estado_ruta"] = "WALKING"
                objeto["velocidad_ruta"] = VELOCIDAD_PATRULLA_NPC * (
                    1 + objeto["random_ruta"].uniform(
                        -VARIACION_VELOCIDAD_NPC,
                        VARIACION_VELOCIDAD_NPC,
                    )
                )
        elif distancia:
            objeto["direccion"] = _direccion_npc(dx, dy)
            paso = min(distancia, paso_maximo)
            x += dx / distancia * paso
            y += dy / distancia * paso
            hitbox = objeto["hitbox"].copy()
            hitbox.midbottom = (round(x), round(y))
            colisiona = (
                not rect_mapa.contains(hitbox)
                or any(
                    colision_hitbox_mapa(hitbox, pared)
                    for pared in hitboxes_muro
                )
                or (
                    zonas_caminables
                    and not any(
                        contiene_zona_caminable(hitbox, zona)
                        for zona in zonas_caminables
                    )
                )
                or hitbox.colliderect(jugador["pies"])
                or any(
                    otro is not actor and otro["rect"].colliderect(hitbox)
                    for otro in mundo["personajes"]
                )
            )
            if colisiona:
                objeto["estado_ruta"] = "WAITING"
                objeto["tiempo_estado_ms"] = 500
                continue
            objeto["posicion_ruta_x"] = x
            objeto["posicion_ruta_y"] = y
            objeto["tiempo_frame_ms"] += delta_ms
            while objeto["tiempo_frame_ms"] >= 140:
                objeto["tiempo_frame_ms"] -= 140
                frames = objeto["frames_caminar"].get(
                    objeto["direccion"],
                    (),
                )
                if frames:
                    objeto["indice_frame"] = (
                        objeto["indice_frame"] + 1
                    ) % len(frames)

        objeto["rect"].midbottom = (
            round(objeto["posicion_ruta_x"]),
            round(objeto["posicion_ruta_y"]),
        )
        objeto["hitbox"].midbottom = objeto["rect"].midbottom
        actor["rect"].update(objeto["hitbox"])
