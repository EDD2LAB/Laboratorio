"""Geometría y desplazamiento comunes, independientes de Pygame y de la red."""
import math


def solapa(a, b):
    x, y, w, h = a
    bx, by, bw, bh = b
    return x < bx + bw and x + w > bx and y < by + bh and y + h > by


def permite_salir_bloqueos(origen, destino, bloqueos):
    """No permite entrar; si ya había solape, no permite profundizarlo.

    Conserva el bloqueo mientras deja salir por sus bordes a quien estaba dentro.
    La comprobación de paredes fijas corresponde al adaptador que llama.
    """
    for b in bloqueos:
        if not solapa(destino, b):
            continue
        if not solapa(origen, b):
            return False
        def profundidad(r):
            x, y, w, h = r
            bx, by, bw, bh = b
            return min(x + w - bx, bx + bw - x, y + h - by, by + bh - y)
        if profundidad(destino) > profundidad(origen):
            return False
    return True


def linea_toca_rect(rect, x1, y1, x2, y2, grosor):
    """Distancia real entre el segmento y el rectángulo de pies (cápsula)."""
    x, y, w, h = rect
    dx, dy = x2 - x1, y2 - y1
    inferior, superior = 0.0, 1.0
    cruza = True
    for inicio, delta, menor, mayor in ((x1, dx, x, x + w), (y1, dy, y, y + h)):
        if not delta:
            if not menor <= inicio <= mayor:
                cruza = False
                break
        else:
            a, b = sorted(((menor - inicio) / delta, (mayor - inicio) / delta))
            inferior, superior = max(inferior, a), min(superior, b)
            if inferior > superior:
                cruza = False
                break
    if cruza:
        return True

    def a_rect(px, py):
        return (px - max(x, min(px, x + w))) ** 2 + (py - max(y, min(py, y + h))) ** 2
    longitud = dx * dx + dy * dy
    def a_linea(px, py):
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / longitud)) if longitud else 0
        return (px - x1 - t * dx) ** 2 + (py - y1 - t * dy) ** 2
    distancia = min(a_rect(x1, y1), a_rect(x2, y2),
                    *(a_linea(px, py) for px, py in ((x, y), (x + w, y), (x, y + h), (x + w, y + h))))
    return distancia <= (grosor / 2) ** 2


def rect_en_union(rect, zonas):
    """Cobertura por unión de rectángulos/círculos absolutos, sin saltar huecos.

    Formatos: ('rect', x, y, w, h), ('circle', cx, cy, radio). Se divide en
    franjas horizontales; los círculos usan su anchura mínima en cada franja,
    de modo que un resultado positivo nunca cubre un hueco no caminable.
    """
    x, y, w, h = rect
    cortes = {y, y + h}
    for zona in zonas:
        if zona[0] == "rect":
            cortes.update(v for v in (zona[2], zona[2] + zona[4]) if y < v < y + h)
        else:
            cortes.update(v for v in (zona[2] - zona[3], zona[2], zona[2] + zona[3]) if y < v < y + h)
    cortes = sorted(cortes)
    for arriba, abajo in zip(cortes, cortes[1:]):
        intervalos = []
        for zona in zonas:
            if zona[0] == "rect":
                _, zx, zy, zw, zh = zona
                if zy <= arriba and zy + zh >= abajo:
                    intervalos.append((zx, zx + zw))
            else:
                _, cx, cy, radio = zona
                dy = max(abs(arriba - cy), abs(abajo - cy))
                if dy <= radio:
                    ancho = math.sqrt(max(0, radio * radio - dy * dy))
                    intervalos.append((cx - ancho, cx + ancho))
        cubierto = x
        for izquierda, derecha in sorted(intervalos):
            if izquierda > cubierto + 1e-9:
                break
            cubierto = max(cubierto, derecha)
            if cubierto >= x + w - 1e-9:
                break
        if cubierto < x + w - 1e-9:
            return False
    return True


def segmento_libre(origen, destino, puede):
    distancia = math.dist(origen, destino)
    pasos = max(1, math.ceil(distancia))
    anterior = origen
    for i in range(1, pasos + 1):
        siguiente = (origen[0] + (destino[0] - origen[0]) * i / pasos,
                     origen[1] + (destino[1] - origen[1]) * i / pasos)
        if not puede(anterior, siguiente):
            return False
        if (siguiente[0] != anterior[0] and siguiente[1] != anterior[1]
                and not puede(anterior, (siguiente[0], anterior[1]))
                and not puede(anterior, (anterior[0], siguiente[1]))):
            return False
        anterior = siguiente
    return True


def desplazar(x, y, dx, dy, puede, asistencia=3):
    """Subpasos de hasta 1 px, deslizamiento por ejes y ayuda lateral de <=3 px.

    La ayuda solo se aplica si existe un paso hacia delante libre tras el roce.
    Consume el mismo presupuesto de distancia; no rodea una pared larga.
    """
    distancia = math.hypot(dx, dy)
    if not distancia:
        return x, y
    pasos = max(1, math.ceil(distancia))
    sx, sy = dx / pasos, dy / pasos
    paso = distancia / pasos
    for _ in range(pasos):
        actual = x, y
        if puede(actual, (x + sx, y + sy)) and (not sx or not sy
                or puede(actual, (x + sx, y)) or puede(actual, (x, y + sy))):
            x, y = x + sx, y + sy
            continue
        if sx and puede((x, y), (x + sx, y)):
            x += sx
        if sy and puede((x, y), (x, y + sy)):
            y += sy
        if (x, y) != actual:
            continue
        lateral = (-dy / distancia, dx / distancia)
        ayuda = None
        for margen in range(1, asistencia + 1):
            for signo in (-1, 1):
                meta = (x + lateral[0] * margen * signo, y + lateral[1] * margen * signo)
                adelante = (meta[0] + dx / distancia, meta[1] + dy / distancia)
                if segmento_libre(actual, meta, puede) and puede(meta, adelante):
                    ayuda = (x + lateral[0] * min(paso, margen) * signo,
                             y + lateral[1] * min(paso, margen) * signo)
                    break
            if ayuda:
                break
        if ayuda is None or not puede(actual, ayuda):
            break
        x, y = ayuda
    return x, y
