"""Catálogo propio de la feria: independiente de los casos de la campaña.

Las categorías son las mismas del árbol de clasificación de La Copa
(logica/Arboles.py). Los rumores sobre Kael y Mira se desmienten siempre al
cerrar la ronda: ninguno de los dos es culpable (regla del proyecto).
"""

DECISIONES = (
    ("compartir", "Compartir"),
    ("verificar", "Verificar"),
    ("detener", "Detener"),
    ("ignorar", "Ignorar"),
)
# Cómo cuenta cada decisión para el resultado colectivo.
RESPONSABLES = {"verificar", "detener"}
RIESGOSAS = {"compartir"}

CATEGORIAS = (
    ("rumor_politico", "Rumor Político"),
    ("suceso_natural", "Suceso Natural"),
    ("acusacion_personal", "Acusación Personal"),
)

CASOS = (
    {
        "id": "puente_norte",
        "titulo": "El puente norte",
        "tablilla": "«Kael cerrará el puente norte esta noche.»",
        "fuente": "Se escuchó en el mercado. Nadie sabe quién lo dijo primero.",
        "categoria": "rumor_politico",
        "mejor": "verificar",
        "verdad": "Falso: Kael no anunció ningún cierre. El mensaje no tenía fuente directa.",
        "ensenanza": "Un rumor sin fuente sobre un aspirante es un Rumor Político: verifica antes de compartir.",
    },
    {
        "id": "mirador_alto",
        "titulo": "El Mirador Alto",
        "tablilla": "«Un rayo dañó todas las plataformas del Mirador Alto.»",
        "fuente": "Un viajero vio humo desde lejos y no subió a comprobarlo.",
        "categoria": "suceso_natural",
        "mejor": "verificar",
        "verdad": "Exagerado: el rayo rompió una baranda. Las plataformas siguen en pie.",
        "ensenanza": "Los sucesos naturales también se exageran: un testimonio incompleto no es toda la historia.",
    },
    {
        "id": "materiales",
        "titulo": "Los materiales",
        "tablilla": "«Mira ocultó los materiales de reparación.»",
        "fuente": "Nadie dice haberla visto. No hay testigos.",
        "categoria": "acusacion_personal",
        "mejor": "detener",
        "verdad": "Falso: los materiales estaban en el almacén del Consejo. Mira no ocultó nada.",
        "ensenanza": "Acusar sin testigos daña a una persona real: detén la acusación y pide pruebas.",
    },
    {
        "id": "nueva_ruta",
        "titulo": "La nueva ruta",
        "tablilla": "«El Consejo anunció una nueva ruta entre las plataformas.»",
        "fuente": "Una hoja con aspecto oficial, pero sin sello ni fecha.",
        "categoria": "rumor_politico",
        "mejor": "verificar",
        "verdad": "Sin confirmar: el Consejo no publicó esa hoja. Sus avisos llevan sello y fecha.",
        "ensenanza": "Parecer oficial no es ser oficial: busca el sello, la fecha y quién lo firma.",
    },
)

NOMBRE_DECISION = dict(DECISIONES)
NOMBRE_CATEGORIA = dict(CATEGORIAS)
POR_ID = {caso["id"]: caso for caso in CASOS}


def publico(caso):
    """Lo que ve el celular: sin la categoría correcta ni la verdad."""
    return {clave: caso[clave] for clave in ("id", "titulo", "tablilla", "fuente")}
