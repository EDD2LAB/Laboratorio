"""Efectos sobre el mapa de La Copa, disparados una vez por evento y con tope.

Las tiras se dividen y escalan una sola vez, al tamaño final de la cámara.
Energia_puente.png mide 1769 de ancho (no divisible entre 8): cada cuadro usa la
parte entera, 221 px, y sobra 1 px a la derecha.
"""
import pygame

from nucleo.recursos import cargar_spritesheet_frames

# nombre -> (ruta, cuadros, tamaño en coordenadas del mundo)
TIRAS = {
    "poder": ("Animaciones/Efectos/ActivarPoderEfecto.png", 8, (88, 97)),
    "eco": ("Tronco ecos/Efecto_eco_troncos.png", 3, (84, 84)),
    "llegada_rumor": ("Animaciones/Efectos/EfectoLlegadaRumor.png", 6, (84, 84)),
    "llegada_correccion": ("Animaciones/Efectos/EfectLlegadaCorreccion.png", 6, (84, 84)),
    "destello_rumor": ("Animaciones/DestelloMorado.png", 8, (64, 64)),
    "destello_correccion": ("Animaciones/DestelloVerde.png", 8, (64, 64)),
    "propagacion": ("Animaciones/Propagacion_puente.png", 8, (72, 24)),
    "energia": ("Animaciones/Energia_puente.png", 8, (72, 55)),
}
CUADRO_MS = 70
MAX_EFECTOS = 8
MAX_RECORRIDOS = 3
DURACION_RECORRIDO_MS = 1400


class EfectosMapa:
    def __init__(self, zoom):
        self.zoom = zoom
        self.cuadros = {}
        for nombre, (ruta, cantidad, tamano) in TIRAS.items():
            final = (tamano[0] * zoom, tamano[1] * zoom)
            self.cuadros[nombre] = [pygame.transform.scale(c, final) for c in cargar_spritesheet_frames(ruta, cantidad)]
        self.activos = []
        self.recorridos = []

    def lanzar(self, nombre, x, y, retraso=0):
        if len(self.activos) < MAX_EFECTOS and self.cuadros.get(nombre):
            self.activos.append((nombre, x, y, pygame.time.get_ticks() + retraso))

    def recorrer(self, tipo, inicio, fin):
        """Una señal cruza un puente; ``tipo``: "rumor" o "correccion"."""
        if len(self.recorridos) < MAX_RECORRIDOS:
            self.recorridos.append((tipo, pygame.math.Vector2(inicio), pygame.math.Vector2(fin), pygame.time.get_ticks()))

    def _a_pantalla(self, x, y, vista):
        return round((x - vista.x) * self.zoom), round((y - vista.y) * self.zoom)

    def dibujar(self, pantalla, vista):
        ahora = pygame.time.get_ticks()
        siguen = []
        for tipo, inicio, fin, comienzo in self.recorridos:
            avance = (ahora - comienzo) / DURACION_RECORRIDO_MS
            if avance >= 1:
                self.lanzar("llegada_" + tipo, fin.x, fin.y)
                self.lanzar("destello_" + tipo, fin.x, fin.y)
                continue
            siguen.append((tipo, inicio, fin, comienzo))
            punto = inicio.lerp(fin, max(0, avance))
            centro = self._a_pantalla(punto.x, punto.y, vista)
            indice = (ahora - comienzo) // CUADRO_MS
            for nombre in ("energia", "propagacion") if tipo == "correccion" else ("propagacion",):
                cuadros = self.cuadros[nombre]
                if cuadros:
                    cuadro = cuadros[indice % len(cuadros)]
                    pantalla.blit(cuadro, cuadro.get_rect(center=centro))
        self.recorridos = siguen
        vivos = []
        for nombre, x, y, comienzo in self.activos:
            cuadros = self.cuadros[nombre]
            indice = (ahora - comienzo) // CUADRO_MS
            if indice >= len(cuadros):
                continue
            vivos.append((nombre, x, y, comienzo))
            if indice >= 0:
                pantalla.blit(cuadros[indice], cuadros[indice].get_rect(center=self._a_pantalla(x, y, vista)))
        self.activos = vivos
