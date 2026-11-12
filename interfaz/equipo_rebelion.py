"""Representación local del equipo y enemigos con respaldo de pixel art por código."""
import math

import pygame

from interfaz import sprites_combate as sprites


def _dibujar_mini(s, m, activos, efectos, ahora_ms):
    x, y = round(m["x"]), round(m["y"])
    if activos:
        # Zona del pulso: se oscurece a medida que el mini-núcleo carga.
        carga = max(0.0, min(1.0, 1 - m.get("aviso", 4) / 4))
        radio = 38
        zona = pygame.Surface((radio * 2 + 2, radio * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(zona, (246, 70, 122, round(18 + 52 * carga)), (radio + 1, radio + 1), radio)
        s.blit(zona, (x - radio - 1, y - radio - 1))
        segmentos = 16
        for i in range(segmentos):
            if (i + ahora_ms // 120) % 2:
                continue
            inicio = i * math.tau / segmentos
            pygame.draw.arc(s, (246, 70, 122), (x - radio, y - radio, radio * 2, radio * 2), inicio, inicio + .3, 1)
        if carga > 0:
            pygame.draw.arc(s, (255, 226, 238), (x - 10, y - 10, 20, 20), math.pi / 2, math.pi / 2 + math.tau * carga, 1)
    if efectos is not None and efectos.recien_golpeado(m["id"]):
        estado, cuadro = "golpe", 0
    else:
        estado, cuadro = ("activo" if activos else "apagado"), ahora_ms // 150
    imagen = sprites.mini_nucleo(cuadro % 4 if estado == "activo" else 0, estado)
    flote = 1 if activos and (ahora_ms // 300) % 2 else 0
    s.blit(imagen, imagen.get_rect(center=(x, y - flote)))
    for i in range(2):  # vida: dos puntos sobre el sprite
        color = (246, 70, 122) if i < m.get("vida", 0) else (52, 40, 68)
        s.fill(sprites.CONTORNO, (x - 4 + i * 5, y - 12 - flote, 4, 3))
        s.fill(color, (x - 3 + i * 5, y - 11 - flote, 2, 1))


def dibujar(s, final, jugadores, efectos=None, ahora_ms=0, objetivo=None):
    """``objetivo`` es ``(mini, apuntable)`` de ``efectos_combate.elegir_objetivo``."""
    if final.get("fase") in (None, "bloqueado", "victoria"):
        return
    a = final.get("aventura", {})
    if final.get("fase") == "preparacion" and not a.get("fabricado"):
        for p in a.get("materiales", []):
            x, y = round(p["x"]), round(p["y"])
            pygame.draw.polygon(s, (249, 213, 102), [(x, y-9), (x+7, y), (x, y+9), (x-7, y)])
            pygame.draw.line(s, (255, 255, 225), (x, y-6), (x, y+4), 2)
    trazo = a.get("disparo")
    if trazo and efectos is None:  # sin efectos animados, al menos se ve el tiro
        pygame.draw.line(s, (115, 250, 245), trazo[:2], trazo[2:], 3)
    taller = a.get("taller")
    if taller:
        x, y = round(taller["x"] + 18), round(taller["y"])
        pygame.draw.rect(s, (35, 71, 81), (x-7, y-10, 14, 13))
        pygame.draw.rect(s, (248, 212, 102), (x-7, y-10, 14, 13), 2)
        pygame.draw.line(s, (248, 212, 102), (x, y-7), (x, y), 2)
    for j in jugadores:
        if j.get("dimension") != "futuro" or j.get("interior"):
            continue
        x, y = round(j["x"] + 11), round(j["y"] - 8)
        if j["id"] in a.get("cargas", {}):
            pygame.draw.rect(s, (245, 211, 101), (x, y-4, 7, 8))
        elif a.get("fabricado") and final.get("fase") == "activo":
            mini = objetivo[0] if objetivo else None
            izquierda = bool(mini) and mini["x"] < j["x"]
            imagen = sprites.blaster(izquierda)
            ancla = (round(j["x"] - 6), y + 2) if izquierda else (x - 4, y + 2)
            s.blit(imagen, imagen.get_rect(midright=ancla) if izquierda else imagen.get_rect(midleft=ancla))
    if len(final.get("hechos", [])) == 4:
        for rol, p in final.get("puntos", {}).items():
            listo = any(j["rol"] == rol and j["id"] in final.get("activaciones", []) for j in jugadores)
            rect = pygame.Rect(round(p["x"]-8), round(p["y"]-9), 16, 12)
            pygame.draw.rect(s, (100, 250, 150) if listo else (100, 220, 250), rect, 2)
        return
    activos = a.get("minis_activos")
    for m in a.get("minis", []):
        _dibujar_mini(s, m, activos, efectos, ahora_ms)
    if objetivo and objetivo[0] and final.get("fase") == "activo" and a.get("fabricado"):
        mini, apuntable = objetivo
        imagen = sprites.reticula(apuntable and bool(activos), ahora_ms // 250)
        s.blit(imagen, imagen.get_rect(center=(round(mini["x"]), round(mini["y"]))))
