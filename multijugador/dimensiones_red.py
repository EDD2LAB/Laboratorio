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
    # Geometría propia del exterior nuevo de Ciudad Núcleo.
    FUTURO: {"nombre": "Ciudad Núcleo", "epoca": "Futuro", "disponible": True,
             "hitboxes": RAIZ / "Hitboxes" / "Mapas" / "Futuro" / "MapaFuturo_hitboxes.json"},
}
ORDEN = (LA_COPA, PRESENTE, FUTURO)

# Interiores de Distrito Conecta: edificio -> nombre del arte y de sus hitboxes.
CARPETA_INTERIORES = RAIZ / "Hitboxes" / "Fondos" / "Mapas" / "Presente"
INTERIORES = {
    "centro_verificacion": "CentrodeVerifInt", "estudio_influencer": "EstudioInfluencerInt",
    "sede_aspirante": "SededelAspiranteInt", "cafe_digital": "CaféDigitalInt",
    "estacion_mensajero": "EstacionMensajeroInt",
}
RADIO_PUERTA = 40
RADIO_SALIDA = 58

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
    if dimension in (PRESENTE, FUTURO):
        rect = rect_mapa_presente(datos)
        datos = dict(datos, hitboxes=[mapear_hitbox(h, rect) for h in datos.get("hitboxes", [])
                                      if isinstance(h, dict)],
                     decoracion=[], rect_mapa=list(rect))
    return datos


def cargar_interior(edificio, dimension=PRESENTE):
    """Hitboxes de un interior, en el lienzo 960x720 (mismo escalado que el mapa)."""
    if dimension == FUTURO:
        from logica.dimensiones import EDIFICIOS_FUTURO
        ruta = RAIZ / "Hitboxes" / EDIFICIOS_FUTURO[edificio]["interior_hitboxes"]
    else:
        ruta = CARPETA_INTERIORES / (INTERIORES[edificio] + "_hitboxes.json")
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    rect = rect_mapa_presente(datos)
    return dict(datos, hitboxes=[mapear_hitbox(h, rect) for h in datos.get("hitboxes", [])], decoracion=[], rect_mapa=list(rect))


def spawn_interior(datos):
    x, y, w, h = datos["rect_mapa"]
    spawn = datos["spawn"]["default"]
    return x + (spawn["rx"] + spawn["rw"] / 2) * w, y + (spawn["ry"] + spawn["rh"]) * h


def rect_salida(datos):
    """Rectángulo (px del lienzo) de la puerta por la que se vuelve a la calle."""
    salida = next(h for h in datos["hitboxes"] if h.get("action") == "salir_edificio")
    return (round(salida["rx"] * ANCHO), round(salida["ry"] * ALTO), round(salida["rw"] * ANCHO), round(salida["rh"] * ALTO))


def edificios_de(datos):
    """Puertas del mapa: su rectángulo y el punto de la calle justo enfrente."""
    x0, y0, ancho, alto = datos["rect_mapa"]
    edificios = {}
    for h in datos["hitboxes"]:
        if h.get("action") == "entrar_edificio" and h.get("edificio_id") in INTERIORES:
            edificios[h["edificio_id"]] = {
                "id": h["edificio_id"], "nombre": h.get("nombre_edificio", "Edificio"),
                "rect": [round(h["rx"] * ANCHO), round(h["ry"] * ALTO), round(h["rw"] * ANCHO), round(h["rh"] * ALTO)],
                "x": round(x0 + h["frente_rx"] * ancho), "y": round(y0 + h["frente_ry"] * alto),
            }
    return edificios


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
    w, h = TAMANO_PORTAL_PRESENTE
    centro = datos.get("portal_centro")
    if isinstance(centro, dict):  # el hueco de las ruinas
        return (round(centro["x"] - w / 2), round(centro["y"] - h / 2), w, h)
    x, y = spawn_presente(datos)
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


def jugadores_visibles(jugadores, dimension, interior=None):
    """Solo se dibujan los jugadores de la misma dimensión y del mismo edificio."""
    return [j for j in jugadores if j.get("dimension", LA_COPA) == dimension and j.get("interior") == interior]
