"""Anclas de interacción sobre el componente realmente accesible del mapa."""
from collections import deque, OrderedDict
import math

_CACHE = OrderedDict()


def componente(colisiones, origen, paso=8):
    clave = (colisiones.firma, tuple(origen), paso)
    if clave in _CACHE:
        return _CACHE[clave]
    x0, y0, ancho, alto = colisiones.datos.get("rect_mapa", (0, 0, 960, 720))
    celda = round(origen[0] / paso), round(origen[1] / paso)
    inicios = [(celda[0]+dx, celda[1]+dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    inicios = [p for p in inicios if not colisiones.bloqueado(p[0]*paso, p[1]*paso)
               and colisiones.trayecto_libre(origen, (p[0]*paso, p[1]*paso))]
    vistos, cola = set(inicios), deque(inicios)
    while cola:
        x, y = cola.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
            n = x+dx, y+dy
            px, py = n[0]*paso, n[1]*paso
            if n in vistos or not (x0 <= px <= x0+ancho and y0 <= py <= y0+alto):
                continue
            if colisiones.bloqueado(px, py) or not colisiones.trayecto_libre((x*paso, y*paso), (px, py)):
                continue
            vistos.add(n)
            cola.append(n)
    puntos = tuple((x*paso, y*paso) for x, y in sorted(vistos))
    if not puntos:
        raise ValueError("El punto de aparición no conecta con el área caminable.")
    _CACHE[clave] = puntos
    # Exterior del Futuro y diez interiores activos: ocho entradas expulsaban
    # mapas que la siguiente sala volvía a calcular inmediatamente.
    if len(_CACHE) > 32:
        _CACHE.popitem(last=False)
    return puntos


def ancla(puntos, deseado, ocupados=(), separacion=18):
    candidatos = (p for p in puntos if all(math.dist(p, o) >= separacion for o in ocupados))
    return min(candidatos, key=lambda p: (math.dist(p, deseado), p))
