"""Grafo físico de la aldea: plataformas y puentes de La Copa."""

from logica.grafo_fisico import GrafoFisico
from nucleo.config import ALTO, ANCHO


PLATAFORMAS_ALDEA = (
    {"id": "plataforma_central", "nombre": "Plataforma Central", "posicion": [0.50, 0.50]},
    {"id": "plataforma_noroeste", "nombre": "Plataforma Noroeste", "posicion": [0.20, 0.22]},
    {"id": "plataforma_noreste", "nombre": "Plataforma Noreste", "posicion": [0.80, 0.22]},
    {"id": "plataforma_suroeste", "nombre": "Plataforma Suroeste", "posicion": [0.20, 0.68]},
    {"id": "plataforma_sureste", "nombre": "Plataforma Sureste", "posicion": [0.80, 0.68]},
    {"id": "plataforma_borde_oeste_norte", "nombre": "Borde Oeste Norte", "posicion": [0.02, 0.45]},
    {"id": "plataforma_borde_este_norte", "nombre": "Borde Este Norte", "posicion": [0.98, 0.45]},
    {"id": "plataforma_borde_oeste_sur", "nombre": "Borde Oeste Sur", "posicion": [0.02, 0.91]},
    {"id": "plataforma_borde_este_sur", "nombre": "Borde Este Sur", "posicion": [0.98, 0.91]},
)

CONEXIONES_PUENTES_ALDEA = (
    ("puente_1", "plataforma_noroeste", "plataforma_central"),
    ("puente_2", "plataforma_noreste", "plataforma_central"),
    ("puente_3", "plataforma_noroeste", "plataforma_borde_oeste_norte"),
    ("puente_4", "plataforma_noreste", "plataforma_borde_este_norte"),
    ("puente_5", "plataforma_suroeste", "plataforma_borde_oeste_sur"),
    ("puente_6", "plataforma_suroeste", "plataforma_central"),
    ("puente_7", "plataforma_central", "plataforma_sureste"),
    ("puente_8", "plataforma_sureste", "plataforma_borde_este_sur"),
)


def crear_grafo_fisico(decoraciones):
    """Asocia plataformas (posiciones normalizadas 0..1) y puentes del mapa."""
    puentes_visuales = {
        objeto["id"]: objeto
        for objeto in decoraciones
        if objeto.get("puente") and objeto.get("id")
    }
    puentes = []
    for puente_id, origen, destino in CONEXIONES_PUENTES_ALDEA:
        if puente_id not in puentes_visuales:
            raise RuntimeError(f"No se encontro la decoracion del {puente_id}.")
        puentes.append({
            "id": puente_id,
            "origen": origen,
            "destino": destino,
            "estado": "normal",
        })
    return GrafoFisico(PLATAFORMAS_ALDEA, puentes)


def buscar_ruta_transmision(grafo, origen_id, destino_id):
    ruta = grafo.buscar_camino(origen_id, destino_id)
    if ruta is None:
        print(
            f"[Grafo] No existe ruta transitable entre {origen_id} y "
            f"{destino_id}; se omite la propagación visual."
        )
        return None

    puente_ids = [
        grafo.obtener_puente(origen, destino)
        for origen, destino in zip(ruta, ruta[1:])
    ]
    if any(puente_id is None for puente_id in puente_ids):
        print(
            f"[Grafo] La ruta entre {origen_id} y {destino_id} contiene "
            "un puente no transitable; se omite la propagación visual."
        )
        return None
    return ruta, puente_ids


def _posicion_en_mapa(plataforma, ancho=ANCHO, alto=ALTO):
    x, y = plataforma["posicion"]
    return round(x * ancho), round(y * alto)
