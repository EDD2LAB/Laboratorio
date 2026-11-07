"""Clasificación de los eventos multijugador con el árbol NodoCategoria."""
from Arboles import buscar_categoria, construir_arbol_categorias_multijugador

ARBOL = construir_arbol_categorias_multijugador()

# Ruta real (sin la raíz "Tablilla") de cada evento.
CATEGORIA_EVENTO = {
    # "Kael cerró hoy el puente por decisión propia": rumor sobre un aspirante.
    "puente_norte": ("Rumor Politico", "Sobre un Aspirante"),
    # Agua del depósito (aviso viejo o vigente): servicio comunitario.
    "agua": ("Aviso Comunitario", "Recursos y servicios"),
    # Alerta (o simulacro) de tormenta: el tema es el clima.
    "tormenta": ("Suceso Natural", "Clima"),
    # "Mira se quedó con la ayuda": acusación a una persona concreta difundida
    # por vecinos ("dicen que..."), por eso Entre Habitantes.
    "ayuda": ("Acusacion Personal", "Entre Habitantes"),
    # Publicación de Distrito Conecta con imagen generada con IA.
    "publicacion_presente": ("Contenido Digital", "Generado con IA"),
}

# Opciones de la trivia por dimensión: nombre visible -> nombre en el árbol.
OPCIONES = {
    "la_copa": {
        "Rumor Político": ("Rumor Politico",),
        "Suceso Natural": ("Suceso Natural",),
        "Acusación Personal": ("Acusacion Personal",),
        "Aviso Comunitario": ("Aviso Comunitario",),
    },
    "presente": {
        "Generado con IA": ("Contenido Digital", "Generado con IA"),
        "Contenido auténtico": ("Contenido Digital", "Contenido autentico"),
    },
}


def nodo_evento(evento_id):
    return buscar_categoria(ARBOL, *CATEGORIA_EVENTO[evento_id])


def ruta_evento(evento_id):
    """Ruta reconstruida subiendo por los padres (incluye la raíz)."""
    return [nodo.nombre for nodo in nodo_evento(evento_id).ruta_desde_raiz()]


def evaluar(evento_id, opcion, dimension="la_copa"):
    opciones = OPCIONES[dimension]
    if opcion not in opciones:
        raise ValueError("Clasificación inválida.")
    elegida = opciones[opcion]
    real = CATEGORIA_EVENTO[evento_id]
    return tuple(real[:len(elegida)]) == tuple(elegida)
