"""Creación del estado del mundo (jugador, cámara, grafo, reparación del puente)."""

from logica.dimensiones import DIMENSION_LA_COPA
from logica.dimensiones import DIMENSION_PRESENTE
from logica.grafo_fisico import GrafoFisico
from logica.habilidades_jugador import HabilidadJugador
from mundo.reparacion_puentes import SistemaReparacionPuente
from mundo.camara import actualizar_camara_mundo
from mundo.grafo_aldea import crear_grafo_fisico
from mundo.jugador import ajustar_inicio_jugador
from mundo.personajes import crear_jugador_local
from nucleo.config import DISTANCIA_INTERACCION, ZOOM_MAPA_PRESENTE


def crear_mundo(recursos):
    jugador = crear_jugador_local(recursos)
    personajes = [
        {
            "id": f"personaje_{indice}_{objeto['personaje'].lower()}",
            "tipo": "personaje",
            "accion": "npc",
            "personaje": objeto["personaje"],
            "rect": objeto["hitbox"].copy(),
            "objeto": objeto,
            "activo": True,
            "distancia": DISTANCIA_INTERACCION,
        }
        for indice, objeto in enumerate(recursos["decoraciones"])
        if objeto["personaje"] and objeto["personaje"] != "Guardián"
    ]
    for interaccion in recursos["interacciones"]:
        if interaccion.get("accion") != "npc" or not interaccion.get("personaje"):
            continue
        if any(actor["personaje"] == interaccion["personaje"] for actor in personajes):
            continue
        personajes.append({
            "id": interaccion["id"],
            "tipo": "personaje",
            "accion": "npc",
            "personaje": interaccion["personaje"],
            "rect": interaccion["rect"],
            "activo": interaccion.get("activo", True),
            "distancia": DISTANCIA_INTERACCION,
        })
    mundo = {
        "decoraciones": recursos["decoraciones"],
        "interacciones": recursos["interacciones"],
        "hitboxes": recursos.get("hitboxes", []),
        "rect_mapa": (
            recursos.get("rect_mapa")
            if recursos.get("dimension") == DIMENSION_PRESENTE
            else None
        ),
        "personajes": personajes,
        "jugador": jugador,
        "habilidad": HabilidadJugador(jugador["id"]),
        "grafo_fisico": (
            GrafoFisico(
                recursos.get("grafo", {}).get("nodos", []),
                recursos.get("grafo", {}).get("conexiones", []),
            )
            if recursos.get("dimension") == DIMENSION_PRESENTE
            else crear_grafo_fisico(recursos["decoraciones"])
        ),
        "propagaciones_visuales": [],
        "dimension": recursos.get("dimension", DIMENSION_LA_COPA),
        "camara": (
            {
                "zoom": (
                    1.0
                    if recursos.get("edificio_interior")
                    else ZOOM_MAPA_PRESENTE
                ),
                "x": 0.0,
                "y": 0.0,
                "x_render": 0,
                "y_render": 0,
            }
            if recursos.get("dimension") == DIMENSION_PRESENTE
            else None
        ),
    }
    if mundo["dimension"] == DIMENSION_LA_COPA:
        reparacion = recursos.get("sistema_reparacion_puentes")
        if reparacion is None and recursos.get("assets_reparacion_puentes"):
            puente = next(
                (
                    objeto for objeto in recursos["decoraciones"]
                    if objeto.get("id") == "puente_1"
                ),
                None,
            )
            if puente is not None:
                reparacion = SistemaReparacionPuente(
                    puente,
                    mundo["grafo_fisico"],
                    recursos["assets_reparacion_puentes"],
                    recursos.get("estado_reparacion_guardado"),
                )
                recursos["sistema_reparacion_puentes"] = reparacion
        if reparacion:
            mundo["reparacion_puentes"] = reparacion
            mundo["interacciones"].extend(reparacion.interacciones)
    ajustar_inicio_jugador(mundo["jugador"], mundo)
    actualizar_camara_mundo(mundo, inmediata=True)
    mundo["posicion_casa"] = mundo["jugador"]["pies"].copy()
    mundo["interacciones_cercanas"] = []
    mundo["interaccion_seleccionada"] = None
    return mundo
