"""Interfaz de La Copa: tablilla y decisiones del Guardián.

Ejecuta este archivo para jugar la demostración gráfica:
    python Botones.py
"""

import os
import sys

import pygame

from logica_juego import EstadoJuego


ANCHO, ALTO = 960, 720
FPS = 60
RUTA_ASSETS = os.path.join(os.path.dirname(__file__), "Imagenes")

CREMA = (255, 243, 210)
TINTA = (61, 37, 25)
VERDE_NOCHE = (19, 45, 35)
VERDE_BOSQUE = (38, 82, 55)
ORO = (237, 185, 87)


def cargar_imagen(nombre, tamano=None):
    """Carga recursos con escalado pixelado para conservar el estilo."""
    ruta = os.path.join(RUTA_ASSETS, nombre)
    try:
        imagen = pygame.image.load(ruta).convert_alpha()
    except (pygame.error, FileNotFoundError) as error:
        raise RuntimeError(f"No se pudo cargar el recurso: {ruta}") from error
    return pygame.transform.scale(imagen, tamano) if tamano else imagen


def crear_fondo():
    """Fondo de bosque discreto para que la tablilla sea protagonista."""
    fondo = pygame.Surface((ANCHO, ALTO))
    for y in range(ALTO):
        progreso = y / ALTO
        color = tuple(int(VERDE_NOCHE[i] + (VERDE_BOSQUE[i] - VERDE_NOCHE[i]) * progreso) for i in range(3))
        pygame.draw.line(fondo, color, (0, y), (ANCHO, y))

    for x, alto_arbol in ((55, 250), (140, 180), (825, 220), (905, 310)):
        base = ALTO - 35
        pygame.draw.rect(fondo, (25, 57, 37), (x - 8, base - alto_arbol // 3, 16, alto_arbol // 3))
        for nivel in range(3):
            y = base - alto_arbol // 3 - nivel * 55
            ancho = 105 - nivel * 18
            pygame.draw.polygon(fondo, (21, 65, 39), [(x, y - 85), (x - ancho // 2, y + 20), (x + ancho // 2, y + 20)])

    for x, y in ((180, 116), (742, 132), (90, 410), (865, 440), (225, 610), (728, 600)):
        pygame.draw.circle(fondo, (242, 205, 105), (x, y), 2)
        pygame.draw.circle(fondo, (242, 205, 105), (x, y), 6, 1)
    return fondo


def envolver_texto(texto, fuente, ancho_maximo):
    palabras, lineas, actual = texto.split(), [], ""
    for palabra in palabras:
        prueba = f"{actual} {palabra}".strip()
        if fuente.size(prueba)[0] <= ancho_maximo:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


class Boton:
    """Botón ilustrado para las acciones principales o placa para las demás."""

    def __init__(self, texto, imagen, centro, fuente):
        self.texto = texto
        self.imagen = imagen
        self.centro = centro
        self.fuente = fuente
        self.rect = imagen.get_rect(center=centro) if imagen else pygame.Rect(centro[0] - 79, centro[1] - 26, 158, 52)

    def dibujar(self, superficie, mouse_pos):
        hover = self.rect.collidepoint(mouse_pos)
        if self.imagen:
            # Los PNG ya incluyen texto e icono: no se repite el rótulo encima.
            if hover:
                brillo = self.imagen.copy()
                brillo.fill((255, 238, 178, 52), special_flags=pygame.BLEND_RGBA_ADD)
                superficie.blit(brillo, brillo.get_rect(center=self.centro))
            superficie.blit(self.imagen, self.rect)
        else:
            color = (126, 81, 45) if not hover else (166, 110, 58)
            pygame.draw.rect(superficie, (42, 25, 17), self.rect.inflate(6, 6), border_radius=12)
            pygame.draw.rect(superficie, color, self.rect, border_radius=9)
            pygame.draw.rect(superficie, ORO, self.rect, width=2, border_radius=9)
            etiqueta = self.fuente.render(self.texto, True, CREMA)
            superficie.blit(etiqueta, etiqueta.get_rect(center=self.rect.center))

    def fue_clickeado(self, posicion):
        return self.rect.collidepoint(posicion)


def buscar_imagen_para_opcion(texto, imagenes):
    texto = texto.lower()
    if "colgar" in texto:
        return imagenes["colgar"]
    if "consultar" in texto:
        return imagenes["consultar"]
    if "quemar" in texto:
        return imagenes["quemar"]
    return None


def construir_botones(opciones, imagenes, fuente):
    """Centra dos, tres o cuatro acciones sin perder la separación visual."""
    if not opciones:
        return []
    separacion = 205 if len(opciones) <= 3 else 195
    inicio = ANCHO // 2 - separacion * (len(opciones) - 1) // 2
    return [Boton(opcion, buscar_imagen_para_opcion(opcion, imagenes), (inicio + i * separacion, 612), fuente) for i, opcion in enumerate(opciones)]


def dibujar_indicadores(superficie, indicadores, fuente):
    panel = pygame.Rect(22, 20, 252, 150)
    pygame.draw.rect(superficie, (20, 39, 28), panel, border_radius=14)
    pygame.draw.rect(superficie, (183, 133, 68), panel, width=2, border_radius=14)
    titulo = fuente.render("LA COPA", True, ORO)
    superficie.blit(titulo, (panel.x + 16, panel.y + 10))

    for indice, (nombre, valor) in enumerate(indicadores.items()):
        y = panel.y + 43 + indice * 20
        etiqueta = fuente.render(nombre.replace("_", " ").capitalize(), True, CREMA)
        superficie.blit(etiqueta, (panel.x + 14, y))
        barra = pygame.Rect(panel.right - 84, y + 5, 62, 8)
        pygame.draw.rect(superficie, (9, 24, 17), barra, border_radius=4)
        color = (196, 90, 54) if "susurros" in nombre or "grietas" in nombre else (104, 184, 104)
        pygame.draw.rect(superficie, color, (barra.x, barra.y, int(barra.width * valor / 100), barra.height), border_radius=4)


def dibujar_tablilla(superficie, tablilla, estado, fuente_texto, fuente_categoria):
    rect = tablilla.get_rect(center=(ANCHO // 2, 330))
    superficie.blit(tablilla, rect)

    categoria = estado.categoria_actual()
    if categoria:
        cat = fuente_categoria.render(categoria.upper(), True, (116, 81, 47))
        superficie.blit(cat, cat.get_rect(center=(rect.centerx, rect.y + 178)))

    # Área interior del pergamino: deja libres el título y el icono decorativo.
    lineas = envolver_texto(estado.texto_actual(), fuente_texto, 365)
    y = rect.y + 265 - len(lineas) * 31 // 2
    for linea in lineas:
        texto = fuente_texto.render(linea, True, TINTA)
        superficie.blit(texto, texto.get_rect(center=(rect.centerx, y)))
        y += 31


def main():
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("La Copa — Tablilla del Guardián")
    reloj = pygame.time.Clock()

    fuente_texto = pygame.font.SysFont("georgia", 22, bold=True)
    fuente_categoria = pygame.font.SysFont("arial", 13, bold=True)
    fuente_boton = pygame.font.SysFont("georgia", 19, bold=True)
    fuente_indicador = pygame.font.SysFont("arial", 14, bold=True)
    tablilla = cargar_imagen("Tablilla.png", (460, 460))
    imagenes = {
        "colgar": cargar_imagen("Colgar.png", (190, 127)),
        "consultar": cargar_imagen("Consultar.png", (190, 127)),
        "quemar": cargar_imagen("Quemar.png", (190, 127)),
    }

    fondo = crear_fondo()
    estado = EstadoJuego()
    botones = construir_botones(estado.opciones_actuales(), imagenes, fuente_boton)
    corriendo = True
    while corriendo:
        mouse_pos = pygame.mouse.get_pos()
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                corriendo = False
            elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                corriendo = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                for boton in botones:
                    if boton.fue_clickeado(evento.pos):
                        estado.elegir_opcion(boton.texto)
                        botones = construir_botones(estado.opciones_actuales(), imagenes, fuente_boton)
                        break

        pantalla.blit(fondo, (0, 0))
        dibujar_indicadores(pantalla, estado.indicadores, fuente_indicador)
        dibujar_tablilla(pantalla, tablilla, estado, fuente_texto, fuente_categoria)
        if estado.juego_terminado():
            aviso = fuente_boton.render("Ronda terminada · Presiona ESC para salir", True, CREMA)
            pantalla.blit(aviso, aviso.get_rect(center=(ANCHO // 2, 620)))
        else:
            for boton in botones:
                boton.dibujar(pantalla, mouse_pos)

        pygame.display.flip()
        reloj.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
