"""Constantes del juego: tamaño del lienzo, colores, escenas, tiempos y datos fijos."""

import os
from nucleo.rutas import RAIZ


ANCHO, ALTO = 960, 720
RELACION_ASPECTO = ANCHO / ALTO
FPS = 60
RUTA_ASSETS = os.path.join(str(RAIZ), "Imagenes")

CREMA = (255, 243, 210)
TINTA = (61, 37, 25)
MADERA = (111, 75, 43)
ORO = (237, 185, 87)
PANEL_OSCURO = (16, 31, 25, 218)

ESCENA_MAPA = "mapa"
ESCENA_TABLILLA = "tablilla"
ESCENA_CONSECUENCIA = "consecuencia"
ESCENA_CLASIFICACION = "clasificacion"
ESCENA_RESULTADO = "resultado"
ESCENA_DIALOGO = "dialogo"
ESCENA_MENSAJE = "mensaje_privado"
ESCENA_CELULAR = "celular"
ESCENA_CODICE = "codice"
ESCENA_TUTORIAL_DIMENSION = "tutorial_dimension"
ESCENA_MAPA_DESTINO = "mapa_destino"
ESCENA_TRANSICION_DIMENSION = "transicion_dimension"
ESCENA_ANALISIS = "analisis_publicacion"
ESCENA_FINAL = "final"
ESCENA_PAUSA = "pausa"
ESCENA_ZONA_EN_PROCESO = "zona_en_proceso"
ESCENA_VISUAL = "visual"
ESCENA_VOLUMEN = "volumen"
ESCENA_AYUDA = "ayuda"
ESCENA_ECO = "eco_tronco"
ESCENAS_CON_MAPA = (
    ESCENA_MAPA,
    ESCENA_PAUSA,
    ESCENA_VISUAL,
    ESCENA_VOLUMEN,
    ESCENA_AYUDA,
    ESCENA_DIALOGO,
    ESCENA_MENSAJE,
    ESCENA_CELULAR,
    ESCENA_CODICE,
    ESCENA_TUTORIAL_DIMENSION,
    ESCENA_ECO,
    ESCENA_ANALISIS,
    ESCENA_TRANSICION_DIMENSION,
)
CENTRO_TABLILLA = (ANCHO // 2, 330)
CENTRO_TABLILLA_CENTRADA = (ANCHO // 2, 330)
CENTRO_CALDERO = (ANCHO // 2, 380)
TAMANO_HITBOX_PIES = (12, 8)
VELOCIDAD_GUARDIAN = 155
DISTANCIA_INTERACCION = 58
ZOOM_MAPA_PRESENTE = 1.6
CAMARA_RESPUESTA = 8.0
VELOCIDAD_PATRULLA_NPC = 38.0
VARIACION_VELOCIDAD_NPC = 0.1
PAUSA_PATRULLA_NPC_MS = (500, 1500)
PROBABILIDAD_PAUSA_NPC = 0.3
RADIO_WAYPOINT_NPC = 5
DURACION_MINIMA_HISTORIA_DIMENSION_MS = 3600
DURACION_MINIMA_TUTORIAL_DIMENSION_MS = 2500
NOMBRE_JUGADOR_PRESENTE = "Elías Vega"
PAGINAS_CODICE = ("Misiones", "Información", "Continuidad")
CONTINUIDAD_PERSONAJES = (
    ("Guardián", "Elías Vega", "Periodista e investigador jugable"),
    ("Kael", "Ronaldo Vélez", "Descendiente de Kael y aspirante a alcalde"),
    ("Odran, Sabio de las Raíces", "Darío Veraz", "Agente de verificación digital"),
    ("Mensajero", "Mateo Ríos", "Mensajero urbano y comunicador"),
    ("Luma", "Lía Nova", "Influencer"),
    ("Tarek", "Tomás Red", "Habitante conectado"),
)
