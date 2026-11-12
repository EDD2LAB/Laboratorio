"""Resaltado dorado del objetivo que se elige con E (solo visual, en el cliente).

El contorno de cada imagen se calcula una vez (máscara alfa dilatada) y queda en
caché; en cada cuadro solo cambia la transparencia del brillo, que pulsa.
Nada se carga al importar este módulo.
"""
import math

import pygame

from nucleo.rutas import RAIZ

DORADO = (255, 211, 77)
BRILLO = (255, 176, 0)
CICLO_MS = 1200
ALFA_MIN, ALFA_MAX = 140, 230
MAX_CACHE = 2048
RUTA_TECLA_E = RAIZ / "Imagenes" / "Indicadores" / "tecla_E.png"


def alfa_pulso(ahora_ms, fijo=False):
    """Transparencia del brillo: sube y baja en un ciclo de 1,2 s."""
    if fijo:
        return ALFA_MAX
    fase = (math.sin(ahora_ms * math.tau / CICLO_MS) + 1) / 2
    return round(ALFA_MIN + (ALFA_MAX - ALFA_MIN) * fase)


def _dilatar(mascara, radio):
    """Máscara agrandada ``radio`` píxeles en todas las direcciones (disco)."""
    salida = pygame.mask.Mask(mascara.get_size())
    for dx in range(-radio, radio + 1):
        for dy in range(-radio, radio + 1):
            if dx * dx + dy * dy <= radio * radio:
                salida.draw(mascara, (dx, dy))
    return salida


def construir_capas(imagen, grosor):
    """(brillo, contorno, margen): superficies con el halo y el borde dorado,
    ``margen`` píxeles más grandes por cada lado que ``imagen``."""
    margen = grosor * 3
    ancho, alto = imagen.get_size()
    base = pygame.mask.Mask((ancho + 2 * margen, alto + 2 * margen))
    base.draw(pygame.mask.from_surface(imagen), (margen, margen))
    borde = _dilatar(base, grosor)
    borde.erase(base, (0, 0))
    medio = _dilatar(base, grosor * 2)
    medio.erase(base, (0, 0))
    halo = _dilatar(base, margen)
    halo.erase(base, (0, 0))
    brillo = halo.to_surface(setcolor=(*BRILLO, 90), unsetcolor=(0, 0, 0, 0))
    brillo.blit(medio.to_surface(setcolor=(*BRILLO, 200), unsetcolor=(0, 0, 0, 0)), (0, 0))
    contorno = borde.to_surface(setcolor=(*DORADO, 255), unsetcolor=(0, 0, 0, 0))
    return brillo, contorno, margen


class Resaltado:
    def __init__(self):
        self._capas = {}    # (id(imagen), grosor) -> (imagen, brillo, contorno, margen)
        self._anillos = {}  # (ancho, alto, grosor) -> (brillo, borde)
        self._tecla = None
        self.calculos = 0   # cuántas veces se construyó un contorno (para las pruebas)

    def capas(self, imagen, grosor=2):
        clave = (id(imagen), grosor)
        guardado = self._capas.get(clave)
        if guardado is None or guardado[0] is not imagen:
            if len(self._capas) >= MAX_CACHE:
                self._capas.clear()
            guardado = (imagen, *construir_capas(imagen, grosor))
            self._capas[clave] = guardado
            self.calculos += 1
        return guardado[1:]

    def contorno(self, superficie, imagen, rect, ahora_ms, grosor=2, fijo=False):
        """Brillo y borde dorado alrededor de la silueta ya dibujada en ``rect``.
        El borde queda fuera de la silueta, así que no tapa la cara."""
        brillo, borde, margen = self.capas(imagen, grosor)
        destino = (rect[0] - margen, rect[1] - margen)
        brillo.set_alpha(alfa_pulso(ahora_ms, fijo))
        superficie.blit(brillo, destino)
        superficie.blit(borde, destino)

    def anillo(self, superficie, rect, ahora_ms, grosor=2, fijo=False):
        """Para lo que está pintado en el mapa y no tiene sprite propio: una elipse
        dorada con brillo alrededor de ``rect``."""
        rect = pygame.Rect(rect)
        clave = (rect.w, rect.h, grosor)
        if clave not in self._anillos:
            margen = grosor * 3
            caja = pygame.Rect(0, 0, rect.w + 2 * margen, rect.h + 2 * margen)
            brillo = pygame.Surface(caja.size, pygame.SRCALPHA)
            pygame.draw.ellipse(brillo, (*BRILLO, 90), caja, margen)
            pygame.draw.ellipse(brillo, (*BRILLO, 200), caja.inflate(-grosor * 2, -grosor * 2), grosor * 2)
            borde = pygame.Surface(caja.size, pygame.SRCALPHA)
            pygame.draw.ellipse(borde, (*DORADO, 255), caja.inflate(-margen * 2 + grosor * 2, -margen * 2 + grosor * 2), grosor)
            self._anillos[clave] = (brillo, borde, margen)
        brillo, borde, margen = self._anillos[clave]
        brillo.set_alpha(alfa_pulso(ahora_ms, fijo))
        superficie.blit(brillo, (rect.x - margen, rect.y - margen))
        superficie.blit(borde, (rect.x - margen, rect.y - margen))

    def tecla(self, fuente, ahora_ms):
        """Indicador de la tecla E: tecla_E.png (1 o 2 cuadros) o uno dibujado por código."""
        if self._tecla is None:
            cuadros = []
            if RUTA_TECLA_E.exists():
                try:
                    hoja = pygame.image.load(str(RUTA_TECLA_E)).convert_alpha()
                    alto = hoja.get_height()
                    n = max(1, hoja.get_width() // alto) if alto else 1
                    ancho = hoja.get_width() // n
                    cuadros = [hoja.subsurface((i * ancho, 0, ancho, alto)).copy() for i in range(n)]
                    if alto != 24:  # pixel art: escalado entero aproximado, sin suavizar
                        cuadros = [pygame.transform.scale(c, (round(c.get_width() * 24 / alto), 24)) for c in cuadros]
                except (pygame.error, OSError):
                    cuadros = []
            if not cuadros:
                cuadros = [self._tecla_por_codigo(fuente, "E", hundida) for hundida in (False, True)]
            self._tecla = cuadros
        return self._tecla[(ahora_ms // 500) % len(self._tecla)]

    @staticmethod
    def _tecla_por_codigo(fuente, letra, hundida):
        texto = fuente.render(letra, True, (40, 28, 8))
        lado = max(22, texto.get_height() + 4)
        tecla = pygame.Surface((lado, lado + 3), pygame.SRCALPHA)
        arriba = 2 if hundida else 0
        pygame.draw.rect(tecla, (150, 104, 20), (0, 3, lado, lado), border_radius=5)
        pygame.draw.rect(tecla, DORADO, (0, arriba, lado, lado), border_radius=5)
        pygame.draw.rect(tecla, (255, 240, 180), (0, arriba, lado, lado), 1, border_radius=5)
        tecla.blit(texto, texto.get_rect(center=(lado // 2, arriba + lado // 2)))
        return tecla

    def etiqueta_tab(self, fuente):
        if not hasattr(self, "_tab"):
            texto = fuente.render("Tab", True, DORADO)
            caja = pygame.Surface((texto.get_width() + 10, texto.get_height() + 4), pygame.SRCALPHA)
            pygame.draw.rect(caja, (13, 29, 23, 170), caja.get_rect(), border_radius=4)
            pygame.draw.rect(caja, DORADO, caja.get_rect(), 1, border_radius=4)
            caja.blit(texto, (5, 2))
            self._tab = caja
        return self._tab
