"""Anclas de interacción sobre el componente realmente accesible del mapa."""
from collections import deque, OrderedDict
import json
import math
from pathlib import Path
import tempfile

_CACHE = OrderedDict()
# El componente solo depende del mapa (su firma), el origen y el paso: se guarda en
# disco para no repetir segundos de geometría en cada carga. Un mapa editado tiene
# otra firma, así que un archivo viejo nunca se usa por error.
CARPETA_DISCO = Path(__file__).resolve().parent.parent / "cache" / "zonas_caminables"


def _archivo(clave):
    firma, origen, paso = clave
    return f"{firma}_{origen[0]!r}_{origen[1]!r}_{paso}.json"


def _leer_disco(clave):
    for carpeta in (CARPETA_DISCO, Path(tempfile.gettempdir()) / "TimelessGlitch" / "zonas_caminables"):
        try:
            puntos = json.loads((carpeta / _archivo(clave)).read_text(encoding="utf-8"))
            return tuple(tuple(p) for p in puntos)
        except (OSError, ValueError, TypeError):
            continue
    return None


def _guardar_disco(clave, puntos):
    for carpeta in (CARPETA_DISCO, Path(tempfile.gettempdir()) / "TimelessGlitch" / "zonas_caminables"):
        try:
            carpeta.mkdir(parents=True, exist_ok=True)
            (carpeta / _archivo(clave)).write_text(json.dumps(puntos, separators=(",", ":")), encoding="utf-8")
            return
        except OSError:
            continue


def componente(colisiones, origen, paso=8):
    clave = (colisiones.firma, tuple(origen), paso)
    if clave in _CACHE:
        return _CACHE[clave]
    guardado = _leer_disco(clave)
    if guardado:
        _CACHE[clave] = guardado
        if len(_CACHE) > 32:
            _CACHE.popitem(last=False)
        return guardado
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
    _guardar_disco(clave, puntos)
    # Exterior del Futuro y diez interiores activos: ocho entradas expulsaban
    # mapas que la siguiente sala volvía a calcular inmediatamente.
    if len(_CACHE) > 32:
        _CACHE.popitem(last=False)
    return puntos


_CALENTADOS = set()  # (firma, origen, paso) ya recorridos en este proceso


def calentar(colisiones, origen, paso=8):
    """Generador que llena la memoria fija de colisiones del área caminable.

    Recorre las mismas aristas que el A* de los bots (cuadrícula de ``paso`` px)
    sin los bloqueos dinámicos (el puente roto), así que no deja zonas en frío
    al otro lado. Cede el control tras cada nodo para repartir el trabajo entre
    cuadros; la memoria es compartida por mapa, así que basta una vez por proceso.
    """
    from logica.movimiento_suave import segmento_libre
    clave = (colisiones.firma, tuple(map(tuple, colisiones.bloqueos)), tuple(map(round, origen)), paso)
    if clave in _CALENTADOS:
        return
    fijo = colisiones._fijo
    # Aristas del A* de los bots (NavegadorBot) para los bloqueos actuales: mismos valores
    # que calcularía el bot (``trayecto_libre``), guardados con su misma clave de celdas.
    memoria = getattr(colisiones, "memoria_aristas", None)
    aristas = memoria() if memoria is not None and paso == 8 else {}

    def puede(_origen, destino):
        return not fijo(*destino)

    def arista(a, b, desde, hasta):
        if colisiones.bloqueado(*hasta):
            return segmento_libre(desde, hasta, puede) and not fijo(*hasta)
        libre = aristas.get((a, b))
        if libre is None:
            libre = aristas[(a, b)] = colisiones.trayecto_libre(desde, hasta)
        # Solo el bloqueo dinámico (el puente roto) corta un tramo libre de paredes:
        # se sigue recorriendo para no dejar en frío el otro lado.
        return libre or (colisiones.bloqueos and segmento_libre(desde, hasta, puede))

    x0, y0, ancho, alto = colisiones.datos.get("rect_mapa", (0, 0, 960, 720))
    celda = round(origen[0] / paso), round(origen[1] / paso)
    inicios = [(celda[0] + dx, celda[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    inicios = [p for p in inicios if not fijo(p[0] * paso, p[1] * paso)]
    vistos, cola = set(inicios), deque(inicios)
    while cola:
        x, y = cola.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
            n = x + dx, y + dy
            px, py = n[0] * paso, n[1] * paso
            if not (x0 <= px <= x0 + ancho and y0 <= py <= y0 + alto):
                continue
            # El A* comprueba las ocho aristas de cada nodo, también hacia nodos ya vistos.
            if fijo(px, py) or not arista((x, y), n, (x * paso, y * paso), (px, py)):
                continue
            if dx and dy:  # las esquinas que el A* consulta en diagonal
                fijo(px, y * paso)
                fijo(x * paso, py)
            if n not in vistos:
                vistos.add(n)
                cola.append(n)
        yield
    _CALENTADOS.add(clave)


def calentar_todo(colisiones, origen, paso=8):
    """Versión de una sola vez de :func:`calentar` (carga, servidor al arrancar)."""
    for _ in calentar(colisiones, origen, paso):
        pass


def ancla(puntos, deseado, ocupados=(), separacion=18):
    candidatos = (p for p in puntos if all(math.dist(p, o) >= separacion for o in ocupados))
    return min(candidatos, key=lambda p: (math.dist(p, deseado), p))
