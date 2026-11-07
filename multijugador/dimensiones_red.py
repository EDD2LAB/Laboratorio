"""Dimensiones del multijugador: mapas, spawn y portales (sin Pygame).

Reutiliza los mismos JSON de hitboxes que el modo de un jugador
(``dimensiones.DIMENSIONES``). Distrito Conecta se dibuja escalado y centrado
en 960x720, igual que ``mundo.mapas.cargar_mapa_presente``; aquí se replica esa
transformación con ``image_size`` del JSON porque el servidor no carga PNG.
"""
import json
import math
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ANCHO, ALTO = 960, 720

LA_COPA, PRESENTE, FUTURO = "la_copa", "presente", "futuro"

DIMENSIONES_RED = {
    LA_COPA: {"nombre": "La Copa", "epoca": "Pasado", "disponible": True,
              "hitboxes": RAIZ / "Hitboxes" / "Mapas" / "Pr_MañanaLumi_hitboxes.json"},
    PRESENTE: {"nombre": "Distrito Conecta", "epoca": "Presente", "disponible": True,
               "hitboxes": RAIZ / "Hitboxes" / "Mapas" / "Presente" / "MapaPresente_hitboxes.json"},
    # Ciudad Núcleo todavía no tiene mapa ni hitboxes en el repositorio
    # (dimensiones.DIMENSIONES["futuro"]["disponible"] es False). Punto de
    # integración: añadir aquí su JSON y poner disponible=True.
    FUTURO: {"nombre": "Ciudad Núcleo", "epoca": "Futuro", "disponible": False, "hitboxes": None},
}
ORDEN = (LA_COPA, PRESENTE, FUTURO)

# Portal de La Copa: decoración "Portales 4x4.png" del mapa (886,268,74,99).
# Portal de Distrito Conecta: se dibuja sobre el spawn del JSON (spawn_presente).
TAMANO_PORTAL_PRESENTE = (64, 84)


def rect_mapa_presente(datos):
    ancho, alto = datos.get("image_size") or (803, 464)
    factor = min(ANCHO / ancho, ALTO / alto)
    w, h = max(1, round(ancho * factor)), max(1, round(alto * factor))
    return ((ANCHO - w) // 2, (ALTO - h) // 2, w, h)


def mapear_hitbox(hitbox, rect):
    """Misma fórmula que mundo.mapas._mapear_hitbox_a_ventana."""
    x, y, w, h = rect
    salida = dict(hitbox)
    tipo = hitbox.get("type", "rect")
    if tipo == "rect":
        salida.update(rx=(x + hitbox.get("rx", 0) * w) / ANCHO, ry=(y + hitbox.get("ry", 0) * h) / ALTO,
                      rw=hitbox.get("rw", 0) * w / ANCHO, rh=hitbox.get("rh", 0) * h / ALTO)
    elif tipo == "circle":
        salida.update(cx=(x + hitbox.get("cx", 0) * w) / ANCHO, cy=(y + hitbox.get("cy", 0) * h) / ALTO,
                      r=hitbox.get("r", 0) * w / ANCHO)
    elif tipo == "line":
        for eje, tam, origen, lienzo in (("x", w, x, ANCHO), ("y", h, y, ALTO)):
            for extremo in ("1", "2"):
                salida[eje + extremo] = (origen + hitbox.get(eje + extremo, 0) * tam) / lienzo
        salida["thickness"] = hitbox.get("thickness", .008) * w / ANCHO
    return salida


def cargar_datos(dimension):
    config = DIMENSIONES_RED[dimension]
    if not config["disponible"]:
        raise ValueError(config["nombre"] + " todavía está en construcción.")
    datos = json.loads(Path(config["hitboxes"]).read_text(encoding="utf-8"))
    if dimension == PRESENTE:
        rect = rect_mapa_presente(datos)
        datos = dict(datos, hitboxes=[mapear_hitbox(h, rect) for h in datos.get("hitboxes", [])
                                      if isinstance(h, dict)],
                     decoracion=[], rect_mapa=list(rect))
    return datos


def spawn_presente(datos):
    spawn = datos.get("spawn_presente")
    if isinstance(spawn, dict) and "x" in spawn:
        return float(spawn["x"]), float(spawn["y"])
    return 480.0, 620.0


def rect_portal(dimension, datos):
    if dimension == LA_COPA:
        for objeto in datos.get("decoracion", []):
            if objeto.get("name", "").lower().endswith("portales 4x4.png"):
                return (round(objeto["x"] * ANCHO), round(objeto["y"] * ALTO),
                        max(1, round(objeto["w"] * ANCHO)), max(1, round(objeto["h"] * ALTO)))
        return (886, 268, 74, 99)
    x, y = spawn_presente(datos)
    w, h = TAMANO_PORTAL_PRESENTE
    return (round(x - w / 2), round(y - h + 6), w, h)


def cerca_de_rect(x, y, rect, radio):
    rx, ry, rw, rh = rect
    dx = max(rx - x, 0, x - (rx + rw))
    dy = max(ry - y, 0, y - (ry + rh))
    return math.hypot(dx, dy) <= radio


def destinos(origen):
    """Opciones del portal: todas las demás dimensiones, en orden temporal."""
    return [{"id": d, "nombre": DIMENSIONES_RED[d]["nombre"], "epoca": DIMENSIONES_RED[d]["epoca"],
             "disponible": DIMENSIONES_RED[d]["disponible"]} for d in ORDEN if d != origen]


def jugadores_visibles(jugadores, dimension):
    """Solo se dibujan los jugadores de la misma dimensión."""
    return [j for j in jugadores if j.get("dimension", LA_COPA) == dimension]
