"""
Alcalde Digital - La Copa
Interfaz grafica en pygame que conecta con logica_juego.EstadoJuego.

Estructura de archivos esperada en la misma carpeta:
  arboles.py
  logica_juego.py
  juego.py            <- este archivo
  assets/
    fondo_aldea.png    (opcional, si no existe se usa un color solido)
    guardian.png        (opcional, sprite del jugador)

Si las imagenes no existen todavia, el juego corre igual usando
rectangulos de color como marcador temporal (placeholder), asi que
puedes empezar a probar la jugabilidad antes de tener los sprites
finales.
"""

import os
import sys
import pygame

from logica_juego import EstadoJuego

# ---------------------------------------------------------------------------
# CONFIGURACION GENERAL
# ---------------------------------------------------------------------------

ANCHO, ALTO = 960, 680
FPS = 60

CARPETA_ASSETS = os.path.join(os.path.dirname(__file__), "assets")

COLOR_FONDO = (30, 40, 25)          # verde oscuro, placeholder si no hay imagen
COLOR_PANEL = (40, 30, 20, 230)     # panel de texto (marron oscuro semitransparente)
COLOR_BOTON = (90, 70, 40)
COLOR_BOTON_HOVER = (130, 100, 55)
COLOR_TEXTO = (240, 230, 210)
COLOR_INDICADOR_FONDO = (20, 20, 20)
COLOR_INDICADOR_BARRA = (200, 170, 60)


def cargar_imagen(nombre_archivo, tamano=None):
    """Carga una imagen desde assets/. Si no existe, devuelve None."""
    ruta = os.path.join(CARPETA_ASSETS, nombre_archivo)
    if not os.path.isfile(ruta):
        return None
    imagen = pygame.image.load(ruta).convert_alpha()
    if tamano:
        imagen = pygame.transform.smoothscale(imagen, tamano)
    return imagen


class Boton:
    """Boton rectangular simple con texto centrado."""
    
    def __init__(self, rect, texto, fuente):
        self.rect = pygame.Rect(rect)
        self.texto = texto
        self.fuente = fuente

    def dibujar(self, superficie, mouse_pos):
        hover = self.rect.collidepoint(mouse_pos)
        color = COLOR_BOTON_HOVER if hover else COLOR_BOTON
        pygame.draw.rect(superficie, color, self.rect, border_radius=8)
        pygame.draw.rect(superficie, COLOR_TEXTO, self.rect, width=2, border_radius=8)

        texto_render = self.fuente.render(self.texto, True, COLOR_TEXTO)
        texto_rect = texto_render.get_rect(center=self.rect.center)
        superficie.blit(texto_render, texto_rect)

    def clic_dentro(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)


def envolver_texto(texto, fuente, ancho_maximo):
    """Divide un texto largo en varias lineas para que quepa en el panel."""
    palabras = texto.split(" ")
    lineas = []
    linea_actual = ""

    for palabra in palabras:
        prueba = f"{linea_actual} {palabra}".strip()
        if fuente.size(prueba)[0] <= ancho_maximo:
            linea_actual = prueba
        else:
            lineas.append(linea_actual)
            linea_actual = palabra
    if linea_actual:
        lineas.append(linea_actual)
    return lineas


def dibujar_indicadores(superficie, fuente, indicadores, x, y, ancho_barra=180):
    """Dibuja una barra por cada indicador de la aldea."""
    alto_fila = 26
    for i, (nombre, valor) in enumerate(indicadores.items()):
        fila_y = y + i * alto_fila

        etiqueta = fuente.render(nombre.replace("_", " ").capitalize(), True, COLOR_TEXTO)
        superficie.blit(etiqueta, (x, fila_y))

        barra_x = x + 190
        pygame.draw.rect(
            superficie, COLOR_INDICADOR_FONDO, (barra_x, fila_y, ancho_barra, 16)
        )
        ancho_lleno = int(ancho_barra * (valor / 100))
        pygame.draw.rect(
            superficie, COLOR_INDICADOR_BARRA, (barra_x, fila_y, ancho_lleno, 16)
        )


def main():
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Alcalde Digital - La Copa")
    reloj = pygame.time.Clock()

    fuente_texto = pygame.font.SysFont("arial", 22)
    fuente_boton = pygame.font.SysFont("arial", 20)
    fuente_indicador = pygame.font.SysFont("arial", 16)
    fuente_categoria = pygame.font.SysFont("arial", 16, italic=True)

    fondo = cargar_imagen("fondo_aldea.png", tamano=(ANCHO, ALTO))
    sprite_guardian = cargar_imagen("guardian.png", tamano=(64, 64))

    estado = EstadoJuego()

    # Posicion del jugador (Guardian) sobre una de las plataformas.
    # Ajusta estas coordenadas segun donde caiga su plataforma en tu
    # imagen de fondo real.
    pos_jugador = (ANCHO // 2 - 32, ALTO // 2 - 32)

    ejecutando = True
    while ejecutando:
        mouse_pos = pygame.mouse.get_pos()
        clic_realizado = False

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                ejecutando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                clic_realizado = True
            elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                ejecutando = False

        # --- DIBUJAR FONDO ---
        if fondo:
            pantalla.blit(fondo, (0, 0))
        else:
            pantalla.fill(COLOR_FONDO)

        # --- DIBUJAR PERSONAJE DEL JUGADOR ---
        if sprite_guardian:
            pantalla.blit(sprite_guardian, pos_jugador)
        else:
            pygame.draw.rect(
                pantalla, (180, 140, 90), (*pos_jugador, 64, 64), border_radius=10
            )

        # --- PANEL DE TEXTO (tablilla / resultado) ---
        panel_rect = pygame.Rect(60, ALTO - 220, ANCHO - 120, 160)
        panel_superficie = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel_superficie.fill(COLOR_PANEL)
        pantalla.blit(panel_superficie, panel_rect.topleft)

        categoria = estado.categoria_actual()
        y_texto = panel_rect.y + 12
        if categoria:
            texto_cat = fuente_categoria.render(f"Categoria: {categoria}", True, (200, 190, 160))
            pantalla.blit(texto_cat, (panel_rect.x + 16, y_texto))
            y_texto += 22

        lineas = envolver_texto(estado.texto_actual(), fuente_texto, panel_rect.width - 32)
        for linea in lineas:
            render = fuente_texto.render(linea, True, COLOR_TEXTO)
            pantalla.blit(render, (panel_rect.x + 16, y_texto))
            y_texto += 28

        # --- BOTONES DE OPCIONES ---
        opciones = estado.opciones_actuales()
        botones = []
        if opciones:
            ancho_boton = 200
            alto_boton = 44
            espacio = 20
            total_ancho = len(opciones) * ancho_boton + (len(opciones) - 1) * espacio
            x_inicial = (ANCHO - total_ancho) // 2
            y_botones = panel_rect.y - alto_boton - 20

            for i, texto_opcion in enumerate(opciones):
                x = x_inicial + i * (ancho_boton + espacio)
                boton = Boton((x, y_botones, ancho_boton, alto_boton), texto_opcion, fuente_boton)
                boton.dibujar(pantalla, mouse_pos)
                botones.append(boton)

        # --- INDICADORES DE LA ALDEA ---
        dibujar_indicadores(pantalla, fuente_indicador, estado.indicadores, 20, 20)

        # --- MANEJAR CLIC EN BOTONES ---
        if clic_realizado:
            for boton in botones:
                if boton.clic_dentro(mouse_pos):
                    estado.elegir_opcion(boton.texto)
                    break

        # --- MENSAJE SI EL JUEGO TERMINO ---
        if estado.juego_terminado():
            aviso = fuente_boton.render("Presiona ESC para salir", True, (220, 200, 160))
            pantalla.blit(aviso, (ANCHO // 2 - aviso.get_width() // 2, ALTO - 40))

        pygame.display.flip()
        reloj.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
