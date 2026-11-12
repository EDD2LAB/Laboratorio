"""Representación local del equipo y enemigos con respaldo de pixel art por código."""
import pygame


def dibujar(s, final, jugadores):
    if final.get("fase") in (None, "bloqueado", "victoria"):
        return
    a = final.get("aventura", {})
    if final.get("fase") == "preparacion" and not a.get("fabricado"):
        for p in a.get("materiales", []):
            x, y = round(p["x"]), round(p["y"])
            pygame.draw.polygon(s, (249, 213, 102), [(x, y-9), (x+7, y), (x, y+9), (x-7, y)])
            pygame.draw.line(s, (255, 255, 225), (x, y-6), (x, y+4), 2)
    trazo = a.get("disparo")
    if trazo:
        pygame.draw.line(s, (115, 250, 245), trazo[:2], trazo[2:], 3)
        pygame.draw.circle(s, (255, 245, 175), trazo[2:], 7, 2)
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
            pygame.draw.rect(s, (25, 47, 63), (x, y-3, 10, 6))
            pygame.draw.line(s, (104, 243, 241), (x+2, y-2), (x+9, y-2), 2)
    if len(final.get("hechos", [])) == 4:
        for rol, p in final.get("puntos", {}).items():
            listo = any(j["rol"] == rol and j["id"] in final.get("activaciones", []) for j in jugadores)
            rect = pygame.Rect(round(p["x"]-8), round(p["y"]-9), 16, 12)
            pygame.draw.rect(s, (100, 250, 150) if listo else (100, 220, 250), rect, 2)
        return
    activos = a.get("minis_activos")
    for m in a.get("minis", []):
        x, y = round(m["x"]), round(m["y"])
        if activos:
            pygame.draw.circle(s, (245, 124, 113), (x, y), 38, 1)
        color = (246, 116, 158) if activos else (96, 123, 138)
        pygame.draw.polygon(s, color, [(x, y-11), (x+9, y), (x, y+11), (x-9, y)])
        pygame.draw.rect(s, (250, 250, 220), (x-4, y-2, 8, 3))
        pygame.draw.line(s, (87, 241, 205), (x-8, y-16), (x-8+8*m["vida"], y-16), 2)
