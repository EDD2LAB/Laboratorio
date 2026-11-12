"""Viaje entre dimensiones: avance por el túnel, estrellas, glitch y llegada.

El arte del túnel se escala una sola vez (factor entero, pixel art) y se
guarda para los siguientes viajes; en cada cuadro solo se recorta la zona
visible, se amplía con ``scale`` y se dibujan formas simples encima.
"""
import math
import random

import pygame

from nucleo.recursos import cargar_imagen, cargar_fuente

ARCHIVO = "Fondos/Mapas/tunel.png"
DURACION = 3.2
# Centro del vórtice en la imagen del túnel (fracción de su tamaño).
VORTICE = (.53, .40)
COLORES_ERA = {"la_copa": ((150, 230, 120), (240, 200, 90)),
               "presente": ((110, 210, 255), (255, 170, 210)),
               "futuro": ((90, 245, 235), (200, 120, 255))}
CREMA, OSCURO = (255, 243, 210), (4, 10, 20)
_BASE = {}


def _base():
    """Túnel a factor entero, cacheado entre viajes (None si falta el arte)."""
    if "imagen" not in _BASE:
        imagen = cargar_imagen(ARCHIVO, requerido=False)
        if imagen is not None:
            factor = max(1, math.ceil(max(960 / imagen.get_width(), 720 / imagen.get_height())))
            imagen = pygame.transform.scale(imagen, (imagen.get_width() * factor, imagen.get_height() * factor)).convert()
        _BASE["imagen"] = imagen
        _BASE["vineta"] = _vineta()
    return _BASE["imagen"], _BASE["vineta"]


def _vineta():
    capa = pygame.Surface((960, 720), pygame.SRCALPHA)
    for i in range(36):
        alpha = round(9 * (36 - i) ** 1.1 / 36 * 6)
        pygame.draw.rect(capa, (*OSCURO, min(255, alpha)), (i * 7, i * 5, 960 - i * 14, 720 - i * 10), 7)
    return capa


def _suave(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class ViajeTunel:
    def __init__(self, titulo, emblema=None, dimension=None, subtitulo="Viajando entre dimensiones…", semilla=None):
        self.titulo, self.subtitulo = titulo, subtitulo
        self.emblema = emblema.copy() if emblema is not None else None
        self.color, self.acento = COLORES_ERA.get(dimension, ((140, 230, 255), (255, 214, 120)))
        self.azar = random.Random(semilla)
        self.t = 0.0
        self.capa = pygame.Surface((960, 720)).convert()
        self.estrellas = [self._estrella(self.azar.uniform(0, 1)) for _ in range(140)]
        fuente_titulo = cargar_fuente(44)
        self.texto_titulo = fuente_titulo.render(titulo, True, CREMA)
        self.sombra_titulo = fuente_titulo.render(titulo, True, OSCURO)
        if self.texto_titulo.get_width() > 860:
            factor = 860 / self.texto_titulo.get_width()
            tam = (860, max(1, round(self.texto_titulo.get_height() * factor)))
            self.texto_titulo = pygame.transform.scale(self.texto_titulo, tam)
            self.sombra_titulo = pygame.transform.scale(self.sombra_titulo, tam)
        self.texto_sub = cargar_fuente(18).render(subtitulo, True, (205, 232, 240))
        self.glitch_en = (1.15, 2.35)

    @property
    def terminada(self):
        return self.t >= DURACION

    def _estrella(self, edad):
        return [self.azar.uniform(0, math.tau), edad, self.azar.uniform(.55, 1.4), self.azar.random() < .25]

    def actualizar(self, segundos):
        self.t += segundos
        rapidez = .35 + 1.6 * _suave((self.t - .3) / 1.4)  # acelera durante el viaje
        for estrella in self.estrellas:
            estrella[1] += segundos * rapidez * estrella[2]
            if estrella[1] >= 1:
                estrella[:] = self._estrella(0.0)

    # --- Capas --------------------------------------------------------------
    def _tunel(self, superficie):
        imagen, _ = _base()
        if imagen is None:
            superficie.fill((8, 16, 27))
            return 480, 300
        # Zoom continuo hacia el vórtice: de 1.0 a 1.9.
        zoom = 1 + .9 * _suave(self.t / (DURACION * .85))
        cx, cy = VORTICE[0] * imagen.get_width(), VORTICE[1] * imagen.get_height()
        ancho, alto = 960 / zoom, 720 / zoom
        x = max(0, min(imagen.get_width() - ancho, cx - ancho / 2))
        y = max(0, min(imagen.get_height() - alto, cy - alto / 2))
        recorte = imagen.subsurface((round(x), round(y), max(1, round(ancho)), max(1, round(alto))))
        pygame.transform.scale(recorte, (960, 720), superficie)
        return (cx - x) * zoom, (cy - y) * zoom

    def _estrellas(self, superficie, centro):
        cx, cy = centro
        estiramiento = 6 + 60 * _suave((self.t - .4) / 1.2) * (1 - _suave((self.t - 2.4) / .6))
        for angulo, edad, rapidez, acento in self.estrellas:
            distancia = 20 + (edad ** 2.2) * 760
            dx, dy = math.cos(angulo), math.sin(angulo)
            largo = estiramiento * edad * rapidez
            x1, y1 = cx + dx * distancia, cy + dy * distancia * .75
            x0, y0 = cx + dx * max(0, distancia - largo), cy + dy * max(0, distancia - largo) * .75
            color = self.acento if acento else self.color
            grosor = 1 if edad < .3 else 2 if edad < .7 else 3
            pygame.draw.line(superficie, color, (x0, y0), (x1, y1), grosor)
            if edad > .45:  # cabeza brillante de la estela
                superficie.fill((255, 255, 240), (round(x1) - 1, round(y1) - 1, grosor + 1, grosor + 1))

    def _glitch(self, superficie):
        """Franjas desplazadas con separación de color, durante un instante."""
        for inicio in self.glitch_en:
            avance = (self.t - inicio) / .16
            if not 0 <= avance <= 1:
                continue
            copia = superficie.copy()
            for _ in range(6):
                y = self.azar.randrange(0, 700)
                alto = self.azar.randint(6, 26)
                desplazamiento = self.azar.choice((-24, -12, 12, 24))
                franja = copia.subsurface((0, y, 960, min(alto, 720 - y)))
                superficie.blit(franja, (desplazamiento, y))
            rojo = copia.copy()
            rojo.fill((255, 60, 90), special_flags=pygame.BLEND_RGB_MULT)
            rojo.set_alpha(70)
            superficie.blit(rojo, (6, 0))
            azul = copia.copy()
            azul.fill((60, 200, 255), special_flags=pygame.BLEND_RGB_MULT)
            azul.set_alpha(70)
            superficie.blit(azul, (-6, 0))

    def _llegada(self, superficie):
        aparicion = _suave((self.t - .95) / .5)
        if aparicion <= 0:
            return
        salida = 1 - _suave((self.t - 2.65) / .4)
        opacidad = round(255 * aparicion * salida)
        centro = (480, 300)
        # Anillo de luz que se abre y pulsa detrás del emblema.
        pulso = (math.sin(self.t * 7) + 1) / 2
        radio = round(70 + 18 * aparicion + 6 * pulso)
        halo = pygame.Surface((radio * 2 + 8, radio * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(halo, (*self.color, round(70 * aparicion * salida)), (radio + 4, radio + 4), radio)
        pygame.draw.circle(halo, (*self.acento, round(200 * aparicion * salida)), (radio + 4, radio + 4), radio, 3)
        superficie.blit(halo, halo.get_rect(center=centro))
        if self.emblema is not None:
            self.emblema.set_alpha(opacidad)
            superficie.blit(self.emblema, self.emblema.get_rect(center=centro))
        # Título que sube y se asienta.
        subida = round(26 * (1 - aparicion))
        rect = self.texto_titulo.get_rect(midtop=(480, 420 + subida))
        franja = pygame.Surface((960, 112), pygame.SRCALPHA)
        franja.fill((*OSCURO, round(165 * aparicion * salida)))
        superficie.blit(franja, (0, 404))
        pygame.draw.rect(superficie, self.acento, (480 - round(220 * aparicion), 404, round(440 * aparicion), 2))
        pygame.draw.rect(superficie, self.acento, (480 - round(220 * aparicion), 514, round(440 * aparicion), 2))
        for imagen, desplazamiento in ((self.sombra_titulo, (2, 3)), (self.texto_titulo, (0, 0))):
            imagen.set_alpha(opacidad)
            superficie.blit(imagen, rect.move(desplazamiento))
        self.texto_sub.set_alpha(opacidad)
        superficie.blit(self.texto_sub, self.texto_sub.get_rect(midtop=(480, rect.bottom + 8)))

    def _destello(self, superficie):
        """Fogonazo breve al salir del túnel."""
        brillo = max(0.0, 1 - abs(self.t - 2.7) / .2)
        if brillo > 0:
            luz = pygame.Surface((960, 720))
            luz.fill((255, 250, 235))
            luz.set_alpha(round(230 * brillo))
            superficie.blit(luz, (0, 0))

    def dibujar(self, superficie):
        capa = self.capa
        centro = self._tunel(capa)
        self._estrellas(capa, centro)
        _, vineta = _base()
        capa.blit(vineta, (0, 0))
        self._glitch(capa)
        self._llegada(capa)
        self._destello(capa)
        # Entra desde el mapa anterior y se funde hacia el nuevo.
        alpha = round(255 * max(0.0, min(1.0, self.t / .4, (DURACION - self.t) / .45)))
        capa.set_alpha(alpha)
        superficie.blit(capa, (0, 0))
