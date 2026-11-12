"""Ataques geométricos: marca, cuenta atrás e impacto, sin cargar arte por cuadro."""
import math
import pygame


def dibujar_ataques(superficie, final, jugadores):
    if final.get("fase") != "activo":
        return
    b = final.get("batalla", {})
    color = (102, 250, 155) if b.get("fase") == 1 else (255, 98, 109)
    radio = 22 if b.get("fase") == 1 else 30
    punto = final.get("puntos", {}).get("aspirante")
    if punto and b.get("fase") == 1:
        caja = pygame.Rect(round(punto["x"] - 34), round(punto["y"] - 64), 68, 68)
        for i, rol in enumerate(("guardian", "habitante")):
            if rol not in final.get("hechos", []):
                pygame.draw.arc(superficie, color, caja, i * math.pi + .1, (i + 1) * math.pi - .1, 4)
    for x, y in b.get("blancos", []):
        centro = round(x), round(y)
        pygame.draw.circle(superficie, (15, 30, 40), centro, radio + 3)
        pygame.draw.circle(superficie, color, centro, radio, 2)
        pygame.draw.line(superficie, color, (x - 9, y), (x + 9, y), 2)
        pygame.draw.line(superficie, color, (x, y - 9), (x, y + 9), 2)
        if b.get("turno") == "rayo":
            pygame.draw.line(superficie, color, (x, y - 95), centro, 7)
            pygame.draw.line(superficie, (255, 255, 230), (x, y - 95), centro, 2)
    for j in jugadores:
        if j["id"] in b.get("derribados", []):
            x, y = round(j["x"]), round(j["y"] - 20)
            pygame.draw.circle(superficie, (255, 220, 105), (x, y), 10, 2)
            pygame.draw.line(superficie, (255, 220, 105), (x - 5, y), (x + 5, y), 3)
            pygame.draw.line(superficie, (255, 220, 105), (x, y - 5), (x, y + 5), 3)


def dibujar_aviso(superficie, final, fuente, yo=None):
    if final.get("fase") != "activo":
        return
    b = final.get("batalla", {})
    turno = b.get("turno")
    texto = {"aviso": "¡Sal de las marcas!", "rayo": "¡Rayos! Sal de las cruces.",
             "recarga": "¡Está recargando! Usa tu estación.", "terminado": "¡Reúnanse y activen juntos!"}.get(turno, "")
    if yo and yo.get("id") in b.get("derribados", []):
        texto = "Pide ayuda. Te recuperarás también en la pausa."
    elif b.get("derribados"):
        texto += " E junto a un caído para ayudar."
    municion = final.get("aventura", {}).get("municion", 0)
    ayuda = fuente.render(f"F: disparar · Cargas del equipo: {municion} · R: caja del taller", True, (255, 243, 210))
    pygame.draw.rect(superficie, (8, 29, 38), (130, 576, 700, 28), border_radius=6)
    superficie.blit(ayuda, ayuda.get_rect(center=(480, 590)))
    titulo = f"FASE {b.get('fase', 1)}/2 · Señal {final.get('integridad', 3)}/3 · {math.ceil(b.get('segundos', 0))} s · {texto}"
    while fuente.size(titulo)[0] > 890 and len(titulo) > 6:
        titulo = titulo[:-4].rstrip() + "..."
    imagen = fuente.render(titulo, True, (255, 240, 200))
    caja = pygame.Rect(20, 110, 920, 40)
    pygame.draw.rect(superficie, (8, 29, 38), caja, border_radius=8)
    superficie.blit(imagen, imagen.get_rect(center=caja.center))
