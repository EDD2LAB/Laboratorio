"""Geometría y movimiento autoritativo, sin Pygame ni recursos gráficos."""
import hashlib
import json
import math
from pathlib import Path
import unicodedata

ANCHO, ALTO = 960, 720
VELOCIDAD = 155.0
MAPA = Path(__file__).resolve().parent.parent / "Hitboxes" / "Mapas" / "Pr_MañanaLumi_hitboxes.json"


def normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower().replace("\\", "/")) if not unicodedata.combining(c))


def es_personaje_jugable(nombre):
    ruta = normalizar(nombre)
    return ("guardian" in ruta or "/mensajero/" in ruta or "habitante hombre" in ruta
            or ("aspirante hombre" in ruta and "aspirante mujer" not in ruta
                and "habitante" not in ruta and "mensajero" not in ruta))


class ColisionesMapa:
    def __init__(self, datos=None):
        if datos is None:
            datos = json.loads(MAPA.read_text(encoding="utf-8"))
        self.firma = hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:16]
        self.paredes = [h for h in datos.get("hitboxes", []) if h.get("role", "wall") == "wall"]
        self.zonas = [h for h in datos.get("hitboxes", []) if h.get("role") == "walkable"]
        self.npcs = []
        for objeto in datos.get("decoracion", []):
            ruta = normalizar(objeto["name"])
            if ruta.startswith("npcs/") and not es_personaje_jugable(ruta):
                self.npcs.append((round(objeto["x"] * ANCHO), round(objeto["y"] * ALTO),
                                  max(1, round(objeto["w"] * ANCHO)), max(1, round(objeto["h"] * ALTO))))

    @staticmethod
    def rectangulo(h):
        return (round(h.get("rx", 0) * ANCHO), round(h.get("ry", 0) * ALTO),
                max(1, round(h.get("rw", 0) * ANCHO)), max(1, round(h.get("rh", 0) * ALTO)))

    @staticmethod
    def solapa(a, b):
        x, y, w, h = a
        bx, by, bw, bh = b
        return x < bx + bw and x + w > bx and y < by + bh and y + h > by

    def bloqueado(self, x, y):
        # La posición pública representa el centro inferior de la hitbox de pies.
        rect = (round(x) - 6, round(y) - 8, 12, 8)
        izquierda, arriba, w, h = rect
        derecha, abajo = izquierda + w, arriba + h
        if izquierda < 0 or arriba < 0 or derecha > ANCHO or abajo > ALTO:
            return True
        for pared in self.paredes:
            tipo = pared.get("type", "rect")
            if tipo == "rect" and self.solapa(rect, self.rectangulo(pared)):
                return True
            if tipo == "circle":
                cx, cy = pared.get("cx", 0) * ANCHO, pared.get("cy", 0) * ALTO
                px, py = max(izquierda, min(cx, derecha)), max(arriba, min(cy, abajo))
                if (cx - px) ** 2 + (cy - py) ** 2 <= max(4, pared.get("r", 0) * ANCHO) ** 2:
                    return True
            if tipo == "line":
                x1, y1 = pared.get("x1", 0) * ANCHO, pared.get("y1", 0) * ALTO
                dx, dy = (pared.get("x2", 0) * ANCHO - x1), (pared.get("y2", 0) * ALTO - y1)
                longitud = dx * dx + dy * dy
                cx, cy = izquierda + w / 2, arriba + h / 2
                t = max(0, min(1, ((cx - x1) * dx + (cy - y1) * dy) / longitud)) if longitud else 0
                radio = math.hypot(w, h) / 2 + max(2, pared.get("thickness", .008) * ANCHO) / 2
                if (cx - x1 - t * dx) ** 2 + (cy - y1 - t * dy) ** 2 <= radio ** 2:
                    return True
        if self.zonas:
            dentro = False
            for zona in self.zonas:
                if zona.get("type", "rect") == "rect":
                    zx, zy, zw, zh = self.rectangulo(zona)
                    dentro |= izquierda >= zx and arriba >= zy and derecha <= zx + zw and abajo <= zy + zh
                elif zona.get("type") == "circle":
                    cx, cy, radio = zona["cx"] * ANCHO, zona["cy"] * ALTO, zona["r"] * ANCHO
                    dentro |= all((px - cx) ** 2 + (py - cy) ** 2 <= radio ** 2
                                  for px, py in ((izquierda, arriba), (derecha, arriba), (izquierda, abajo), (derecha, abajo)))
            if not dentro:
                return True
        return any(self.solapa(rect, npc) for npc in self.npcs)

    def mover(self, x, y, dx, dy, segundos):
        norma = max(1, math.hypot(dx, dy))
        distancia = VELOCIDAD * max(0, min(segundos, .15))
        pasos = max(1, math.ceil(distancia / 3))
        paso_x, paso_y = dx / norma * distancia / pasos, dy / norma * distancia / pasos
        for _ in range(pasos):
            if not self.bloqueado(x + paso_x, y):
                x += paso_x
            if not self.bloqueado(x, y + paso_y):
                y += paso_y
        return x, y

    def inicio_libre(self, x, y, ocupadas=()):
        for radio in range(0, 161, 4):
            for dx in range(-radio, radio + 1, 4):
                for dy in ({-radio, radio} if radio else {0}):
                    px, py = x + dx, y + dy
                    libre = not any(self.bloqueado(px + ox, py + oy)
                                    for ox, oy in ((0, 0), (-8, 0), (8, 0), (0, -8), (0, 8)))
                    if libre and all(math.hypot(px - a, py - b) >= 22 for a, b in ocupadas):
                        return float(px), float(py)
        raise ValueError("No se encontró una posición inicial libre en el mapa.")


class PartidaMovimiento:
    def __init__(self, jugadores, ahora, colisiones=None):
        self.colisiones = colisiones or ColisionesMapa()
        self.jugadores = {}
        self.controles = {}
        self.ultima = ahora
        ocupadas = []
        for i, jugador in enumerate(jugadores):
            x, y = self.colisiones.inicio_libre(415 + (i % 2) * 130, 390 + (i // 2) * 70, ocupadas)
            ocupadas.append((x, y))
            self.jugadores[jugador["id"]] = {
                "id": jugador["id"], "nombre": jugador["nombre"], "rol": jugador["rol"],
                "x": x, "y": y, "direccion": "abajo", "animacion": "reposo", "seq": -1,
            }

    def recibir(self, identificador, datos, ahora):
        if identificador not in self.jugadores:
            raise ValueError("Jugador fuera de la partida.")
        dx, dy, seq = datos.get("dx"), datos.get("dy"), datos.get("seq")
        if (type(dx) is not int or type(dy) is not int or dx not in (-1, 0, 1) or dy not in (-1, 0, 1)
                or type(seq) is not int or not 0 <= seq <= 2 ** 53):
            raise ValueError("Controles de movimiento inválidos.")
        if seq <= self.jugadores[identificador]["seq"]:
            return
        self.actualizar(ahora)
        self.controles[identificador] = (dx, dy, ahora)
        self.jugadores[identificador]["seq"] = seq

    def actualizar(self, ahora):
        desde = self.ultima
        self.ultima = max(desde, ahora)
        for identificador, jugador in self.jugadores.items():
            dx, dy, recibido = self.controles.get(identificador, (0, 0, 0))
            # Un cliente detenido o desconectado deja de mover al personaje.
            segundos = max(0, min(ahora, recibido + .35) - desde)
            x, y = jugador["x"], jugador["y"]
            nx, ny = self.colisiones.mover(x, y, dx, dy, segundos)
            jugador["x"], jugador["y"] = nx, ny
            jugador["animacion"] = "caminar" if math.hypot(nx - x, ny - y) > .01 else "reposo"
            if dx:
                jugador["direccion"] = "derecha" if dx > 0 else "izquierda"
            elif dy:
                jugador["direccion"] = "abajo" if dy > 0 else "arriba"

    def quitar(self, identificador):
        self.jugadores.pop(identificador, None)
        self.controles.pop(identificador, None)

    def estado(self):
        return {"mapa": "la_copa", "firma_mapa": self.colisiones.firma,
                "jugadores": [dict(j) for j in self.jugadores.values()]}
