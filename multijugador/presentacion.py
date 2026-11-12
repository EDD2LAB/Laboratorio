"""Datos de presentación compartidos por servidor y cliente (sin Pygame).

Este es el ÚNICO lugar donde se define:
- el tipo de poción de cada opción de decisión del multijugador,
- la polaridad (bueno/malo) de cada indicador y el color de sus cambios,
- las etiquetas visibles de los indicadores por dimensión.

El servidor usa estos datos para publicar ``tipo_pocion`` y aplicar efectos;
el cliente solo los lee para dibujar.
"""

# Número de era de cada dimensión (el nombre sale de logica/dimensiones.py).
ERAS = {"la_copa": "Era I", "presente": "Era II", "futuro": "Era III"}


def estado_votacion(votos, participantes, resultado=None):
    """Publica quién falta, nunca la elección privada de otra persona."""
    from collections import Counter
    participantes = set(participantes)
    emitidos = participantes.intersection(votos)
    todos = bool(participantes) and emitidos == participantes
    mayor = max(Counter(votos[i] for i in emitidos).values(), default=0)
    return {"faltan_votar": sorted(participantes - emitidos),
            "empate": bool(todos and resultado is None and mayor <= len(participantes) / 2)}


def titulo_era(dimension, nombre):
    return f"{ERAS[dimension]}: {nombre}"


TIPOS_POCION = ("colgar", "consultar", "quemar", "ignorar")

# Clasificación de cada opción concreta en uno de los 4 tipos del modo de un
# jugador (Colgar / Consultar / Quemar / Ignorar). La evaluación de si la
# decisión fue correcta NO depende de este mapa: sigue siendo la del caso.
POCION_OPCION = {
    # La Copa (campaña cooperativa).
    # "Corregir las partes equivocadas": emite una corrección pública contra
    # el contenido y retira la versión falsa -> QUEMAR (desmentir/retirar).
    "corregir": "quemar",
    # "Compartirlo: las pistas lo confirman": publicar y difundir -> COLGAR.
    "difundir": "colgar",
    # "No compartirlo: es un aviso falso": no reaccionar ni difundir -> IGNORAR.
    # Ambiguo: también "descarta" el aviso, pero no lo denuncia ni lo corrige
    # públicamente; la acción principal es no compartir.
    "descartar": "ignorar",
    # Distrito Conecta (presente).
    "verificar": "consultar",
    "reportar": "quemar",
    "dejar_pendiente": "ignorar",
    "compartir": "colgar",
}

NOMBRES_POCION = {"colgar": "Colgar", "consultar": "Consultar", "quemar": "Quemar", "ignorar": "Ignorar"}

# Mismos indicadores que el modo de un jugador. El multijugador conserva sus
# claves históricas (confianza, desinformacion) para no romper el protocolo.
INDICADORES_INICIALES = {
    "sabiduria": 50,
    "confianza": 50,
    "armonia": 50,
    "susurros_falsos": 0,
    "desinformacion": 0,
}
ORDEN_INDICADORES = tuple(INDICADORES_INICIALES)

POLARIDAD = {
    "sabiduria": "bueno",
    "confianza": "bueno",
    "armonia": "bueno",
    "susurros_falsos": "malo",
    "desinformacion": "malo",
}

COLOR_VERDE = (111, 220, 126)
COLOR_ROJO = (242, 113, 90)

ETIQUETAS = {
    "la_copa": {
        "sabiduria": "Sabiduría",
        "confianza": "Confianza del Consejo",
        "armonia": "Armonía",
        "susurros_falsos": "Susurros Falsos",
        "desinformacion": "Desinformación",
    },
    "presente": {
        "sabiduria": "Alfabetización digital",
        "confianza": "Confianza pública",
        "armonia": "Convivencia digital",
        "susurros_falsos": "Contenido viral dudoso",
        "desinformacion": "Desinformación",
    },
}


def tipo_pocion(opcion):
    tipo = POCION_OPCION.get(opcion)
    if tipo not in TIPOS_POCION:
        raise ValueError(f"La opción {opcion!r} no tiene tipo de poción.")
    return tipo


def es_negativo(indicador):
    return POLARIDAD.get(indicador) == "malo"


def cambio_favorable(indicador, delta):
    """True si el cambio ayuda a la comunidad (bueno↑ o malo↓)."""
    if indicador not in POLARIDAD:
        raise ValueError(f"Indicador sin polaridad: {indicador}")
    return (delta > 0) != es_negativo(indicador)


def color_cambio(indicador, delta):
    """VERDE: bueno↑ o malo↓. ROJO: bueno↓ o malo↑."""
    return COLOR_VERDE if cambio_favorable(indicador, delta) else COLOR_ROJO


def texto_cambio(indicador, delta, dimension="la_copa"):
    etiqueta = ETIQUETAS.get(dimension, ETIQUETAS["la_copa"]).get(indicador, indicador)
    return f"{'+' if delta > 0 else ''}{delta} {etiqueta}"


def aplicar_efectos(indicadores, efectos):
    for nombre, cambio in efectos.items():
        indicadores[nombre] = max(0, min(100, indicadores.get(nombre, 0) + cambio))
