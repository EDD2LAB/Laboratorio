"""
Alcalde Digital - La Copa
Rama: botones

Muestra la Tablilla en pantalla junto con botones dinamicos generados
a partir de las opciones que entrega EstadoJuego (logica_arboles.py).
Este archivo NO conoce el arbol por dentro: solo le pregunta a
EstadoJuego que texto mostrar y que opciones dibujar, y le avisa
cuando el jugador hace clic.

IMPORTANTE: el archivo Logica-arboles.py debe renombrarse a
logica_arboles.py (con guion bajo) porque Python no permite importar
modulos cuyo nombre tenga un guion medio.
    git mv Logica-arboles.py logica_arboles.py

Los PNG deben estar en la carpeta assets/ junto a este archivo:
    assets/Tablilla.png, assets/Colgar.png, assets/Consultar.png, assets/Quemar.png
"""

import pygame
import sys
import os

from logica_juego import EstadoJuego

pygame.init()

# ---------------------------------------------------------------------------
# CONFIGURACION DE VENTANA
# ---------------------------------------------------------------------------
ANCHO, ALTO = 900, 600
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Alcalde Digital - La Copa")
reloj = pygame.time.Clock()

# Las imagenes viven sueltas en la misma carpeta que este archivo
# (no dentro de una subcarpeta assets/ ni Imagenes/).
RUTA_ASSETS = os.path.dirname(__file__)

FUENTE = pygame.font.SysFont("arial", 22)
FUENTE_TITULO = pygame.font.SysFont("arial", 26, bold=True)
FUENTE_INDICADORES = pygame.font.SysFont("arial", 16)

BLANCO = (255, 255, 255)
NEGRO = (20, 20, 20)
VERDE_BOSQUE = (34, 68, 43)


# ---------------------------------------------------------------------------
# CARGA DE IMAGENES
# ---------------------------------------------------------------------------
def cargar_imagen(nombre, tamano=None):
    ruta = os.path.join(RUTA_ASSETS, nombre)
    try:
        img = pygame.image.load(ruta).convert_alpha()
    except (pygame.error, FileNotFoundError):
        # Reemplazo temporal si falta el PNG, para que el juego no se caiga.
        img = pygame.Surface((150, 60), pygame.SRCALPHA)
        img.fill((150, 120, 80, 255))
    if tamano:
        img = pygame.transform.smoothscale(img, tamano)
    return img


img_tablilla = cargar_imagen("Tablilla.png", (550, 280))
img_colgar = cargar_imagen("Colgar.png", (150, 60))
img_consultar = cargar_imagen("Consultar.png", (150, 60))
img_quemar = cargar_imagen("Quemar.png", (150, 60))

# Palabra clave -> imagen. Se usa coincidencia parcial (in) porque las
# opciones reales del arbol son "Colgarla", "Quemarla", "Consultar", etc.
# (no coinciden exacto con el nombre del PNG). Si una opcion no contiene
# ninguna de estas palabras (ej. "Si", "No", "Ignorarla"), se dibuja un
# boton generico gris con el texto de la opcion.
PALABRAS_CLAVE_IMAGEN = [
    ("colgar", img_colgar),
    ("quemar", img_quemar),
    ("consultar", img_consultar),
]


def buscar_imagen_para_opcion(texto_opcion):
    clave = texto_opcion.strip().lower()
    for palabra, imagen in PALABRAS_CLAVE_IMAGEN:
        if palabra in clave:
            return imagen
    return None


# ---------------------------------------------------------------------------
# CLASE Boton
# ---------------------------------------------------------------------------
class Boton:
    def __init__(self, imagen, x, y, texto_opcion):
        self.imagen = imagen
        self.rect = imagen.get_rect(topleft=(x, y))
        self.texto_opcion = texto_opcion

    def dibujar(self, superficie):
        superficie.blit(self.imagen, self.rect)
        etiqueta = FUENTE.render(self.texto_opcion, True, BLANCO)
        superficie.blit(etiqueta, etiqueta.get_rect(center=self.rect.center))

    def fue_clickeado(self, pos):
        return self.rect.collidepoint(pos)


def construir_botones(lista_opciones):
    """Genera un boton por cada opcion que entregue EstadoJuego."""
    botones = []
    cantidad = len(lista_opciones)
    if cantidad == 0:
        return botones

    ancho_boton = 150
    espacio = 30
    ancho_total = cantidad * ancho_boton + (cantidad - 1) * espacio
    x_inicial = (ANCHO - ancho_total) // 2
    y_botones = 440

    for i, texto_opcion in enumerate(lista_opciones):
        imagen = buscar_imagen_para_opcion(texto_opcion)
        if imagen is None:
            imagen = pygame.Surface((ancho_boton, 60), pygame.SRCALPHA)
            imagen.fill((90, 90, 90, 255))
        x = x_inicial + i * (ancho_boton + espacio)
        botones.append(Boton(imagen, x, y_botones, texto_opcion))
    return botones


def dibujar_texto_envuelto(superficie, texto, fuente, color, rect, y_offset=0):
    """Dibuja texto ajustandolo a varias lineas dentro del ancho de un rect."""
    palabras = texto.split(" ")
    lineas = []
    linea_actual = ""
    for palabra in palabras:
        prueba = f"{linea_actual} {palabra}".strip()
        if fuente.size(prueba)[0] <= rect.width - 60:
            linea_actual = prueba
        else:
            lineas.append(linea_actual)
            linea_actual = palabra
    lineas.append(linea_actual)

    y = rect.top + y_offset
    for linea in lineas:
        superficie_texto = fuente.render(linea, True, color)
        superficie.blit(superficie_texto, (rect.centerx - superficie_texto.get_width() // 2, y))
        y += fuente.get_height() + 6


def dibujar_indicadores(superficie, indicadores):
    """Dibuja los indicadores de la aldea en la esquina superior izquierda."""
    x, y = 20, 20
    for nombre, valor in indicadores.items():
        texto = FUENTE_INDICADORES.render(f"{nombre}: {valor}", True, BLANCO)
        superficie.blit(texto, (x, y))
        y += 22


# ---------------------------------------------------------------------------
# BUCLE PRINCIPAL
# ---------------------------------------------------------------------------
def main():
    estado = EstadoJuego()
    botones = construir_botones(estado.opciones_actuales())

    corriendo = True
    while corriendo:
        pantalla.fill(VERDE_BOSQUE)

        # --- Indicadores de la aldea ---
        dibujar_indicadores(pantalla, estado.indicadores)

        # --- Tablilla con el texto actual ---
        rect_tablilla = img_tablilla.get_rect(center=(ANCHO // 2, 240))
        pantalla.blit(img_tablilla, rect_tablilla)
        dibujar_texto_envuelto(
            pantalla, estado.texto_actual(), FUENTE_TITULO, NEGRO, rect_tablilla, y_offset=50
        )

        # --- Eventos ---
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                corriendo = False

            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if estado.juego_terminado():
                    corriendo = False
                else:
                    for boton in botones:
                        if boton.fue_clickeado(evento.pos):
                            estado.elegir_opcion(boton.texto_opcion)
                            botones = construir_botones(estado.opciones_actuales())
                            break

        # --- Botones o aviso de fin de partida ---
        if not estado.juego_terminado():
            for boton in botones:
                boton.dibujar(pantalla)
        else:
            aviso = FUENTE.render("Haz clic para salir...", True, BLANCO)
            pantalla.blit(aviso, aviso.get_rect(center=(ANCHO // 2, 500)))

        pygame.display.flip()
        reloj.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
