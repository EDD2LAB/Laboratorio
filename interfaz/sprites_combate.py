"""Sprites en pixel art del combate final, dibujados píxel a píxel.

Son diminutos a propósito: se pintan en la capa del mundo, que la cámara del
Futuro amplía con ``transform.scale`` (vecino más cercano), así que en pantalla
quedan con el mismo grosor de píxel que el mapa. El HUD los amplía igual.
Nada se crea al importar: cada sprite se genera la primera vez que se pide,
después de ``set_mode``.
"""
from functools import lru_cache

import pygame

CONTORNO = (18, 12, 32)
PALETA = {
    "k": CONTORNO,
    "m": (56, 50, 88), "M": (104, 98, 146), "L": (160, 156, 196),   # metal
    "r": (150, 24, 66), "R": (246, 70, 122), "W": (255, 226, 238),  # núcleo hostil
    "c": (26, 120, 132), "C": (104, 243, 241), "w": (226, 255, 252),  # energía aliada
    "y": (168, 128, 34), "Y": (240, 198, 72), "h": (255, 244, 186),    # oro del caído
    "g": (64, 72, 92),                                                 # apagado
}

MINI = (
    "....kkkkk....",
    "..kkMMMMMkk..",
    ".kMMLmmmLMMk.",
    ".kMmkkkkkmMk.",
    "kMmkrrrrrkmMk",
    "kLmkrRRRrkmLk",
    "kMmkrRWRrkmMk",
    "kLmkrRRRrkmLk",
    "kMmkrrrrrkmMk",
    ".kMmkkkkkmMk.",
    ".kMMLmmmLMMk.",
    "..kkMMMMMkk..",
    "....kkkkk....",
)

BLASTER = (
    ".kkkkkkkk..",
    "kMLLLLLCCwk",
    "kmmmmmkkkk.",
    ".kmmk......",
    ".kmk.......",
    "..k........",
)

CORAZON = (
    ".kk...kk.",
    "kRRk.kRWk",
    "kRWRkRRRk",
    "kRRRRRRRk",
    ".kRRRRRk.",
    "..kRRRk..",
    "...kRk...",
    "....k....",
)

CORAZON_ROTO = (
    ".kkk...kkk.",
    "kYhYk.kYYYk",
    "kYhYYkYYYyk",
    "kYYYYkYYYyk",
    "kYYYkYYYyyk",
    ".kYYYkYYyk.",
    "..kYkYYyk..",
    "...kkYyk...",
    "....kYk....",
    ".....k.....",
)

TECLA = (
    "kkkkkkkkk",
    "kLLLLLLLk",
    "kL.....Mk",
    "kL.....Mk",
    "kL.....Mk",
    "kL.....Mk",
    "kMMMMMMMk",
    "kkkkkkkkk",
)


def desde_mapa(filas, paleta=PALETA, sustituir=None):
    """Convierte filas de caracteres en una superficie; ``.`` es transparente."""
    sustituir = sustituir or {}
    superficie = pygame.Surface((len(filas[0]), len(filas)), pygame.SRCALPHA)
    for y, fila in enumerate(filas):
        for x, letra in enumerate(fila):
            if letra != ".":
                superficie.set_at((x, y), sustituir.get(letra, paleta[letra]))
    return superficie


def ampliar(superficie, factor):
    """Pixel art: siempre ``scale``, nunca ``smoothscale``."""
    return pygame.transform.scale(superficie, (superficie.get_width() * factor, superficie.get_height() * factor))


def silueta(superficie, color):
    """Misma forma en un solo color (destello al recibir un impacto)."""
    copia = superficie.copy()
    # MAX y luego MIN fijan el color sin tocar la transparencia original.
    copia.fill((*color, 0), special_flags=pygame.BLEND_RGBA_MAX)
    copia.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MIN)
    return copia


@lru_cache(maxsize=None)
def mini_nucleo(cuadro=0, estado="activo"):
    """Cuatro cuadros de latido; ``estado``: activo, apagado o golpe."""
    if estado == "golpe":
        return silueta(mini_nucleo(0), (255, 250, 245))
    if estado == "apagado":
        gris = {"r": PALETA["g"], "R": (96, 110, 132), "W": (150, 164, 182)}
        return desde_mapa(MINI, sustituir=gris)
    brillo = (0, 1, 2, 1)[cuadro % 4]
    nucleo = ({"R": (200, 46, 92), "W": (246, 110, 150)},
              {},
              {"r": (214, 40, 86), "R": (255, 120, 160), "W": (255, 255, 255)})[brillo]
    return desde_mapa(MINI, sustituir=nucleo)


@lru_cache(maxsize=None)
def blaster(hacia_izquierda=False):
    imagen = desde_mapa(BLASTER)
    return pygame.transform.flip(imagen, True, False) if hacia_izquierda else imagen


@lru_cache(maxsize=None)
def corazon(lleno=True, factor=1):
    vacio = {"R": (52, 40, 68), "W": (78, 64, 96)}
    return ampliar(desde_mapa(CORAZON, sustituir=None if lleno else vacio), factor)


@lru_cache(maxsize=None)
def corazon_roto(factor=1):
    return ampliar(desde_mapa(CORAZON_ROTO), factor)


@lru_cache(maxsize=None)
def tecla(factor=3):
    return ampliar(desde_mapa(TECLA), factor)


@lru_cache(maxsize=None)
def celda_bateria(llena=True, factor=3):
    """Una carga de munición: 2 x 5 píxeles de energía con brillo arriba."""
    superficie = pygame.Surface((2, 5), pygame.SRCALPHA)
    if llena:
        superficie.fill(PALETA["C"])
        superficie.fill(PALETA["w"], (0, 0, 2, 1))
        superficie.fill(PALETA["c"], (0, 4, 2, 1))
    else:
        superficie.fill((34, 46, 60))
    return ampliar(superficie, factor)


@lru_cache(maxsize=None)
def explosion(cuadro):
    """Seis cuadros: destello, anillo que se abre y chispas que se apagan."""
    lado = 29
    superficie = pygame.Surface((lado, lado), pygame.SRCALPHA)
    centro = lado // 2
    colores = ((255, 255, 255), (255, 226, 238), (246, 70, 122), (190, 40, 96), (110, 30, 70), (60, 20, 48))
    radio = 3 + cuadro * 2
    if cuadro < 2:
        pygame.draw.circle(superficie, colores[0], (centro, centro), radio + 1)
        pygame.draw.circle(superficie, PALETA["R"], (centro, centro), radio + 1, 1)
    else:
        pygame.draw.circle(superficie, colores[cuadro], (centro, centro), radio, 2 if cuadro < 4 else 1)
    for i in range(8):
        # Esquirlas en las ocho direcciones, a una distancia que crece.
        dx, dy = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))[i]
        distancia = radio + 2 + (i % 2)
        if cuadro >= 1 and distancia < centro:
            superficie.set_at((centro + dx * distancia, centro + dy * distancia), colores[min(5, cuadro)])
    return superficie


@lru_cache(maxsize=None)
def reticula(apuntable=True, cuadro=0):
    """Mira de cuatro esquinas; se cierra un píxel en cuadros alternos."""
    lado = 21
    superficie = pygame.Surface((lado, lado), pygame.SRCALPHA)
    color = (120, 255, 170) if apuntable else (150, 160, 176)
    sombra = (16, 52, 40) if apuntable else CONTORNO
    margen = 1 + (cuadro % 2)
    largo = 5
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        x0 = margen if sx > 0 else lado - 1 - margen
        y0 = margen if sy > 0 else lado - 1 - margen
        for capa, tinta in ((1, sombra), (0, color)):
            for i in range(largo):
                superficie.set_at((x0 + sx * i, y0 + capa), tinta)
                superficie.set_at((x0 + capa, y0 + sy * i), tinta)
    if apuntable:
        superficie.set_at((lado // 2, lado // 2), color)
    return superficie
