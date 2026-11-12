"""Ataques del final: marcas, rayo, caídos y HUD del combate.

Las marcas y el rayo se pintan en la capa del mundo (la cámara los amplía con
``scale``); el HUD se pinta en la pantalla con sprites ampliados ×3. Nada carga
arte por cuadro: los sprites salen de ``interfaz.sprites_combate`` ya cacheados.
"""
import math

import pygame

from interfaz import sprites_combate as sprites
from multijugador.batalla_cooperativa import PAUSA

PANEL = (8, 22, 32)
CREMA = (255, 240, 200)
CIAN = (104, 243, 241)
RECARGA = PAUSA


def _color(fase):
    return (102, 250, 155) if fase == 1 else (255, 98, 109)


def _marca(superficie, centro, radio, color, progreso, ahora_ms):
    """Zona de peligro translúcida con anillo giratorio y un círculo que se cierra."""
    x, y = centro
    pulso = (math.sin(ahora_ms / 90) + 1) / 2
    zona = pygame.Surface((radio * 2 + 2, radio * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(zona, (*color, round(40 + 50 * progreso + 25 * pulso)), (radio + 1, radio + 1), radio)
    superficie.blit(zona, (x - radio - 1, y - radio - 1))
    caja = (x - radio, y - radio, radio * 2, radio * 2)
    giro = ahora_ms / 600
    for i in range(8):
        inicio = giro + i * math.tau / 8
        pygame.draw.arc(superficie, color, caja, inicio, inicio + .45, 2)
    interior = max(2, round(radio * (1 - progreso)))
    pygame.draw.circle(superficie, (255, 250, 230), centro, interior, 1)
    # Signo de alerta en píxeles: barra y punto.
    superficie.fill(sprites.CONTORNO, (x - 2, y - 7, 5, 12))
    superficie.fill(color, (x - 1, y - 6, 3, 6))
    superficie.fill(color, (x - 1, y + 2, 3, 2))


def _rayo(superficie, centro, radio, color, ahora_ms):
    x, y = centro
    alto = 150
    temblor = (ahora_ms // 40) % 3 - 1
    haz = pygame.Surface((radio * 2, alto), pygame.SRCALPHA)
    ancho = radio // 2 + 3
    pygame.draw.rect(haz, (*color, 110), (radio - ancho // 2 + temblor, 0, ancho, alto))
    pygame.draw.rect(haz, (*color, 220), (radio - 3 + temblor, 0, 7, alto))
    pygame.draw.rect(haz, (255, 255, 235, 255), (radio - 1 + temblor, 0, 3, alto))
    superficie.blit(haz, (x - radio, y - alto))
    impacto = pygame.Surface((radio * 2 + 2, radio * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(impacto, (*color, 150), (radio + 1, radio + 1), radio)
    pygame.draw.circle(impacto, (255, 255, 235, 230), (radio + 1, radio + 1), radio // 2)
    superficie.blit(impacto, (x - radio - 1, y - radio - 1))


def dibujar_ataques(superficie, final, jugadores, efectos=None, ahora_ms=0):
    if final.get("fase") != "activo":
        return
    b = final.get("batalla", {})
    color = _color(b.get("fase"))
    radio = 22 if b.get("fase") == 1 else 30
    punto = final.get("puntos", {}).get("aspirante")
    if punto and b.get("fase") == 1:
        caja = pygame.Rect(round(punto["x"] - 34), round(punto["y"] - 64), 68, 68)
        # Escudo: un cuarto por rol que aún no termina su parte verde.
        for i, rol in enumerate(("guardian", "mensajero", "habitante", "aspirante")):
            if rol not in final.get("verde", []):
                pygame.draw.arc(superficie, color, caja, i * math.pi / 2 + .1, (i + 1) * math.pi / 2 - .1, 4)
    total = efectos.aviso_total if efectos is not None else 3.0
    progreso = max(0.0, min(1.0, 1 - b.get("segundos", 0) / total))
    for x, y in b.get("blancos", []):
        centro = round(x), round(y)
        if b.get("turno") == "rayo":
            _rayo(superficie, centro, radio, color, ahora_ms)
        else:
            _marca(superficie, centro, radio, color, progreso, ahora_ms)
    caido = sprites.corazon_roto()
    for j in jugadores:
        if j["id"] in b.get("derribados", []):
            flote = (ahora_ms // 250) % 2
            superficie.blit(caido, caido.get_rect(midbottom=(round(j["x"]), round(j["y"] - 22 - flote))))


def _texto(superficie, fuente, texto, color, centro):
    sombra = fuente.render(texto, True, sprites.CONTORNO)
    superficie.blit(sombra, sombra.get_rect(center=(centro[0] + 1, centro[1] + 2)))
    imagen = fuente.render(texto, True, color)
    superficie.blit(imagen, imagen.get_rect(center=centro))


def _recortar(fuente, texto, ancho):
    while fuente.size(texto)[0] > ancho and len(texto) > 6:
        texto = texto[:-4].rstrip() + "..."
    return texto


def _panel(superficie, rect, borde):
    pygame.draw.rect(superficie, sprites.CONTORNO, rect.inflate(6, 6), border_radius=4)
    pygame.draw.rect(superficie, PANEL, rect, border_radius=3)
    pygame.draw.rect(superficie, borde, rect, 3, border_radius=3)
    pygame.draw.line(superficie, (34, 60, 76), (rect.x + 6, rect.y + 5), (rect.right - 7, rect.y + 5), 3)


def dibujar_aviso(superficie, final, fuente, yo=None, efectos=None, ahora_ms=0):
    if final.get("fase") != "activo":
        return
    b = final.get("batalla", {})
    turno, fase = b.get("turno"), b.get("fase", 1)
    color = _color(fase)
    peligro = turno in ("aviso", "rayo")
    texto = {"aviso": "¡Sal de las marcas!", "rayo": "¡Rayos! Sal de las zonas.",
             "recarga": "Está recargando: usa tu estación.", "terminado": "¡Lo lograron!"}.get(turno, "")
    if yo and yo.get("id") in b.get("derribados", []):
        texto = "Te derribaron: pide ayuda o espera la pausa."
    elif b.get("derribados"):
        texto += " E junto a un caído para ayudar."

    # Barra superior: fase, señal, mensaje y tiempo.
    caja = pygame.Rect(20, 110, 920, 40)
    parpadeo = peligro and (ahora_ms // 200) % 2
    _panel(superficie, caja, color if parpadeo or not peligro else tuple(c // 2 for c in color))
    insignia = pygame.Rect(caja.x + 8, caja.y + 8, 92, 24)
    pygame.draw.rect(superficie, tuple(c // 3 for c in color), insignia, border_radius=2)
    pygame.draw.rect(superficie, color, insignia, 2, border_radius=2)
    _texto(superficie, fuente, f"FASE {fase}", color, insignia.center)
    perdio = efectos is not None and efectos.perdio_senal()
    integridad = final.get("integridad", 3)
    for i in range(3):
        lleno = i < integridad
        imagen = sprites.corazon(lleno, 3)
        x = insignia.right + 12 + i * 31
        temblor = ((ahora_ms // 40) % 3 - 1) * 2 if perdio and i == integridad else 0
        if perdio and i == integridad and (ahora_ms // 80) % 2:
            imagen = sprites.corazon(True, 3)
        superficie.blit(imagen, imagen.get_rect(midleft=(x + temblor, caja.centery)))
    segundos = max(0, math.ceil(b.get("segundos", 0)))
    reloj = pygame.Rect(caja.right - 96, caja.y + 8, 88, 24)
    pygame.draw.rect(superficie, (18, 38, 50), reloj, border_radius=2)
    pygame.draw.rect(superficie, color if peligro else CIAN, reloj, 2, border_radius=2)
    _texto(superficie, fuente, f"{segundos} s", CREMA, reloj.center)
    izquierda = insignia.right + 12 + 3 * 31 + 8
    ancho = reloj.x - 10 - izquierda
    tinta = (255, 236, 120) if peligro and parpadeo else CREMA
    _texto(superficie, fuente, _recortar(fuente, texto, ancho), tinta, (izquierda + ancho // 2, caja.centery))
    # Tiempo restante del turno como barra bajo el panel.
    duracion = {"aviso": efectos.aviso_total if efectos else 3.0, "rayo": .7,
                "recarga": RECARGA.get(fase, 26.0)}.get(turno)
    if duracion:
        fraccion = max(0.0, min(1.0, b.get("segundos", 0) / duracion))
        barra = pygame.Rect(caja.x + 4, caja.bottom + 5, caja.width - 8, 6)
        pygame.draw.rect(superficie, sprites.CONTORNO, barra)
        relleno = barra.inflate(-2, -2)
        relleno.width = round(relleno.width * fraccion)
        pygame.draw.rect(superficie, color if peligro else CIAN, relleno)

    # Barra inferior: bláster sin munición, con su recarga de 0,6 s y la tecla.
    abajo = pygame.Rect(230, 572, 500, 34)
    _panel(superficie, abajo, (60, 110, 130))
    arma = sprites.blaster_hud()
    superficie.blit(arma, arma.get_rect(midleft=(abajo.x + 12, abajo.centery)))
    carga = efectos.carga_blaster() if efectos is not None else 1.0
    barra = pygame.Rect(abajo.x + 12 + arma.get_width() + 10, abajo.centery - 6, 120, 12)
    pygame.draw.rect(superficie, sprites.CONTORNO, barra)
    pygame.draw.rect(superficie, (160, 156, 196), barra, 2)
    for i in range(8):  # ocho segmentos de píxel, como el resto del HUD
        tinta = CIAN if (i + 1) / 8 <= carga + 1e-6 else (34, 46, 60)
        superficie.fill(tinta, (barra.x + 3 + i * 14, barra.y + 3, 12, barra.height - 6))
    lista = carga >= 1
    estado = "Listo" if lista else "Recargando"
    _texto(superficie, fuente, estado, CIAN if lista else (160, 156, 196), (barra.right + 52, abajo.centery))
    imagen = sprites.tecla(3)
    rect = imagen.get_rect(midleft=(barra.right + 108, abajo.centery))
    superficie.blit(imagen, rect)
    _texto(superficie, fuente, "F", CREMA, (rect.centerx, rect.centery - 1))
    etiqueta = fuente.render("Disparar a la mira", True, CREMA)
    superficie.blit(etiqueta, etiqueta.get_rect(midleft=(rect.right + 6, abajo.centery)))
