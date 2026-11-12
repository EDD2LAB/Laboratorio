"""Fondos de carga y viaje preparados una vez, sin deformar el pixel art."""
import math

import pygame

from nucleo.recursos import cargar_imagen, cargar_fuente
from interfaz.presentacion_pantalla import presentar

TRES_ERAS = "Fondos/Mapas/fondoMenuInicio.png"
ERAS = ("ERA I · LA COPA", "ERA II · DISTRITO CONECTA", "ERA III · CIUDAD NÚCLEO")
# Dónde termina cada panel del tríptico, en fracción del ancho de la imagen.
CORTES_ERAS = (0, 360 / 1064, 720 / 1064, 1)
CREMA, ORO, OSCURO = (255, 243, 210), (237, 185, 87), (5, 12, 23)
PERIODO_PANEO_MS = 70000


def _escalar(imagen, factor):
    """Pixel art: ``scale`` (vecino más cercano), nunca ``smoothscale``."""
    return pygame.transform.scale(imagen, (round(imagen.get_width() * factor), round(imagen.get_height() * factor)))


class FondoTresEras:
    """Fondo del menú: el tríptico a pantalla completa con un paneo lento,
    para que con el formato 4:3 se vean también los extremos de La Copa y
    de Ciudad Núcleo."""

    def __init__(self, ruta=TRES_ERAS):
        imagen = cargar_imagen(ruta, requerido=False)
        self.imagen = None if imagen is None else _escalar(imagen, max(960 / imagen.get_width(), 720 / imagen.get_height()))

    def dibujar(self, superficie, ahora_ms):
        if self.imagen is None:
            superficie.fill((8, 16, 27))
            return
        sobra = self.imagen.get_width() - 960
        fase = math.sin(ahora_ms * math.tau / PERIODO_PANEO_MS)
        superficie.blit(self.imagen, (round(-sobra / 2 - fase * sobra / 2), (720 - self.imagen.get_height()) // 2))


class PantallaCarga:
    """Pantalla de inicio y de carga: el tríptico completo, logo, eras y progreso.

    Se compone una sola vez; cada llamada solo cambia el mensaje y la barra.
    """

    def __init__(self, ruta=TRES_ERAS):
        self.fondo = pygame.Surface((960, 720))
        self.fondo.fill((8, 16, 27))
        self.fuente_detalle = cargar_fuente(18)
        imagen = cargar_imagen(ruta, requerido=False)
        if imagen is not None:
            # Detrás, la misma imagen a pantalla completa y oscurecida.
            detras = _escalar(imagen, max(960 / imagen.get_width(), 720 / imagen.get_height()))
            self.fondo.blit(detras, detras.get_rect(center=(480, 360)))
            velo = pygame.Surface((960, 720), pygame.SRCALPHA)
            velo.fill((*OSCURO, 205))
            self.fondo.blit(velo, (0, 0))
            # Delante, el tríptico entero, sin recortar ninguna era.
            frente = _escalar(imagen, 960 / imagen.get_width())
            self.marco = frente.get_rect(midtop=(480, 112))
            self.fondo.blit(frente, self.marco)
            self._viñeta(self.marco)
            for borde in (self.marco.top - 2, self.marco.bottom):
                pygame.draw.rect(self.fondo, ORO, (0, borde, 960, 2))
            self._eras(self.marco)
        else:
            self.marco = pygame.Rect(0, 112, 960, 520)
        self._cabecera()

    def _viñeta(self, marco):
        """Oscurece la parte baja del tríptico para que los nombres se lean."""
        sombra = pygame.Surface(marco.size, pygame.SRCALPHA)
        for y in range(marco.height):
            alpha = round(170 * max(0, (y - marco.height * .62) / (marco.height * .38)))
            pygame.draw.line(sombra, (*OSCURO, alpha), (0, y), (marco.width, y))
        self.fondo.blit(sombra, marco)

    def _eras(self, marco):
        fuente = cargar_fuente(16)
        for nombre, inicio, fin in zip(ERAS, CORTES_ERAS, CORTES_ERAS[1:]):
            centro = round(marco.x + (inicio + fin) / 2 * marco.width)
            texto = fuente.render(nombre, True, CREMA)
            caja = texto.get_rect(center=(centro, marco.bottom - 26)).inflate(22, 10)
            pygame.draw.rect(self.fondo, (*OSCURO,), caja, border_radius=4)
            pygame.draw.rect(self.fondo, ORO, caja, 2, border_radius=4)
            self.fondo.blit(texto, texto.get_rect(center=caja.center))

    def _cabecera(self):
        titulo = cargar_fuente(44).render("TIMELESS GLITCH", True, ORO)
        sombra = cargar_fuente(44).render("TIMELESS GLITCH", True, OSCURO)
        logo = None
        try:
            from interfaz.logo import ARCHIVO
            original = cargar_imagen(ARCHIVO, requerido=False)
            if original is not None:
                recorte = original.subsurface(original.get_bounding_rect())
                logo = _escalar(recorte, 84 / recorte.get_height())
        except (ImportError, ValueError, pygame.error):
            logo = None
        ancho = titulo.get_width() + (logo.get_width() + 18 if logo else 0)
        x = 480 - ancho // 2
        if logo:
            self.fondo.blit(logo, logo.get_rect(midleft=(x, 56)))
            x += logo.get_width() + 18
        self.fondo.blit(sombra, sombra.get_rect(midleft=(x + 2, 59)))
        self.fondo.blit(titulo, titulo.get_rect(midleft=(x, 56)))

    def dibujar(self, superficie, detalle, progreso=None):
        superficie.blit(self.fondo, (0, 0))
        texto = self.fuente_detalle.render(detalle, True, CREMA)
        superficie.blit(texto, texto.get_rect(midtop=(480, self.marco.bottom + 18)))
        if progreso is None:
            return
        # Barra en segmentos de píxel, como el resto del HUD.
        segmentos, ancho, alto = 16, 22, 10
        x0 = 480 - (segmentos * (ancho + 4) - 4) // 2
        y0 = self.marco.bottom + 52
        llenos = round(max(0.0, min(1.0, progreso)) * segmentos)
        pygame.draw.rect(superficie, OSCURO, (x0 - 6, y0 - 6, segmentos * (ancho + 4) + 8, alto + 12), border_radius=3)
        pygame.draw.rect(superficie, (96, 82, 54), (x0 - 6, y0 - 6, segmentos * (ancho + 4) + 8, alto + 12), 2, border_radius=3)
        for i in range(segmentos):
            color = ORO if i < llenos else (40, 48, 58)
            superficie.fill(color, (x0 + i * (ancho + 4), y0, ancho, alto))
            if i < llenos:
                superficie.fill((255, 228, 150), (x0 + i * (ancho + 4), y0, ancho, 2))

    def mostrar(self, pantalla, lienzo, detalle, progreso=None):
        self.dibujar(lienzo, detalle, progreso)
        presentar(pantalla, lienzo)
        pygame.display.flip()
        pygame.event.pump()


class PantallaViaje:
    def __init__(self, ruta):
        self.fondo = pygame.Surface((960, 720))
        self.fondo.fill((8, 16, 27))
        imagen = cargar_imagen(ruta, requerido=False)
        if imagen is not None:
            # Cubrir el lienzo conservando proporciones; recorte centrado.
            escala = max(960 / imagen.get_width(), 720 / imagen.get_height())
            imagen = pygame.transform.scale(imagen, (round(imagen.get_width() * escala),
                                                     round(imagen.get_height() * escala)))
            self.fondo.blit(imagen, imagen.get_rect(center=(480, 360)))
        sombra = pygame.Surface((960, 720), pygame.SRCALPHA)
        for y in range(720):
            alpha = round(25 + 210 * max(0, (y - 330) / 390))
            pygame.draw.line(sombra, (5, 12, 23, alpha), (0, y), (959, y))
        self.fondo.blit(sombra, (0, 0))
        self.fuente = cargar_fuente(18)
        self.etiquetas = {}

    def dibujar(self, superficie, fuente, titulo, detalle):
        superficie.blit(self.fondo, (0, 0))
        clave = (fuente, titulo, detalle)
        if clave not in self.etiquetas:
            titulo_imagen = fuente.render(titulo, True, (255, 243, 210))
            if titulo_imagen.get_width() > 840:
                factor = 840 / titulo_imagen.get_width()
                titulo_imagen = pygame.transform.scale(titulo_imagen,
                    (840, max(1, round(titulo_imagen.get_height() * factor))))
            texto = self.fuente.render(detalle, True, (220, 234, 239))
            self.etiquetas[clave] = titulo_imagen, texto
        titulo_imagen, texto = self.etiquetas[clave]
        superficie.blit(titulo_imagen, titulo_imagen.get_rect(midbottom=(480, 614)))
        superficie.blit(texto, texto.get_rect(midtop=(480, 635)))

    def mostrar_carga(self, pantalla, lienzo, fuente, detalle):
        self.dibujar(lienzo, fuente, "Preparando tu aventura", detalle)
        presentar(pantalla, lienzo)
        pygame.display.flip()
        pygame.event.pump()
