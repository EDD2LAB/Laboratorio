"""Genera UNA vez el arte provisional de Ciudad Núcleo a partir del Presente.

Ejecutar desde la raíz:  .venv\\Scripts\\python.exe herramientas/generar_futuro.py

Usa pygame-ce porque el entorno del proyecto no incluye Pillow. La salida queda
en Imagenes/Futuro/generado/; qué reemplazar con arte definitivo: docs/futuro.md.
"""
import colorsys
import os
import random
import shutil
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

from nucleo.rutas import RAIZ  # noqa: E402

IMAGENES = RAIZ / "Imagenes"
SALIDA = IMAGENES / "Futuro" / "generado"
MAPA_ORIGEN = IMAGENES / "Fondos" / "Mapas" / "Presente" / "MapaPresente.png"
HITBOXES_ORIGEN = RAIZ / "Hitboxes" / "Mapas" / "Presente" / "MapaPresente_hitboxes.json"
HITBOXES_DESTINO = RAIZ / "Hitboxes" / "Mapas" / "Futuro" / "MapaFuturo_hitboxes.json"
# Oscuridad -> luz: noche morada, teal y cian.
PALETA_MAPA = ((10, 8, 34), (42, 22, 92), (18, 92, 112), (38, 184, 190), (176, 246, 240))
SEMILLA_CIRCUITOS = 3000
CIRCUITOS = ((90, 240, 235), (190, 120, 255))
# Personaje del futuro -> (carpeta del Presente, tono de destino de 0 a 1).
PERSONAJES = {"Archivista": ("Agente de verificación", .52), "Corredor de Datos": ("Mensajero urbano", .78),
              "Ciudadano Conectado": ("Habitante Conectada", .5), "Representante Humano": ("Aspirante Contempóraneo", .76)}


def color_de_paleta(luz):
    """Interpola la paleta según la luminosidad (0 a 1)."""
    posicion = min(.9999, luz) * (len(PALETA_MAPA) - 1)
    indice = int(posicion)
    mezcla = posicion - indice
    return tuple(round(a + (b - a) * mezcla) for a, b in zip(PALETA_MAPA[indice], PALETA_MAPA[indice + 1]))


def recolorear_mapa(imagen):
    # Una tabla por nivel de luz evita calcular el color de cada píxel.
    tabla = [color_de_paleta(i / 255) for i in range(256)]
    for x in range(imagen.get_width()):
        for y in range(imagen.get_height()):
            r, g, b, a = imagen.get_at((x, y))
            imagen.set_at((x, y), (*tabla[(r * 77 + g * 151 + b * 28) >> 8], a))


def dibujar_circuitos(imagen):
    """Líneas en ángulo recto con nodos luminosos: decoración, no afecta colisiones."""
    azar = random.Random(SEMILLA_CIRCUITOS)
    ancho, alto = imagen.get_size()
    capa = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    celda = max(8, ancho // 60)
    for _ in range(70):
        x, y = azar.randrange(0, ancho, celda), azar.randrange(0, alto, celda)
        color = azar.choice(CIRCUITOS)
        horizontal = azar.random() < .5
        for _ in range(azar.randint(2, 5)):
            largo = azar.randint(2, 8) * celda * azar.choice((-1, 1))
            nx, ny = (x + largo, y) if horizontal else (x, y + largo)
            pygame.draw.line(capa, (*color, 120), (x, y), (nx, ny), max(1, celda // 8))
            x, y, horizontal = nx, ny, not horizontal
        radio = max(2, celda // 4)
        pygame.draw.circle(capa, (*color, 70), (x, y), radio * 2)
        pygame.draw.circle(capa, (235, 255, 255, 230), (x, y), radio)
    imagen.blit(capa, (0, 0))


def tono_sprite(imagen, tono):
    """Variante de paleta: cambia el tono y conserva luz, alfa y forma."""
    cache = {}
    for x in range(imagen.get_width()):
        for y in range(imagen.get_height()):
            color = tuple(imagen.get_at((x, y)))
            if color[3] == 0:
                continue
            if color not in cache:
                h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in color[:3]))
                # La piel (tonos cálidos claros) se enfría poco, para que siga siendo una persona.
                nuevo = tono if not (h < .12 and v > .5) else (h + .02) % 1
                r, g, b = colorsys.hsv_to_rgb(nuevo, min(1, s * 1.1) if nuevo == tono else s * .7, v)
                cache[color] = (round(r * 255), round(g * 255), round(b * 255), color[3])
            imagen.set_at((x, y), cache[color])


def main():
    pygame.init()
    pygame.display.set_mode((10, 10))
    SALIDA.mkdir(parents=True, exist_ok=True)
    mapa = pygame.image.load(str(MAPA_ORIGEN)).convert_alpha()
    recolorear_mapa(mapa)
    dibujar_circuitos(mapa)
    pygame.image.save(mapa, str(SALIDA / "MapaFuturo.png"))
    for nombre, (origen, tono) in PERSONAJES.items():
        destino = SALIDA / "NPCS" / nombre
        destino.mkdir(parents=True, exist_ok=True)
        for archivo in sorted((IMAGENES / "NPCS" / origen).glob("*.png")):
            hoja = pygame.image.load(str(archivo)).convert_alpha()
            tono_sprite(hoja, tono)
            pygame.image.save(hoja, str(destino / archivo.name))
    HITBOXES_DESTINO.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HITBOXES_ORIGEN, HITBOXES_DESTINO)
    print("Mapa:", mapa.get_size())
    pygame.quit()


if __name__ == "__main__":
    main()
