"""Presenta el lienzo 960x720 en la ventana sin bandas negras.

El juego conserva su proporción 4:3 (sin deformar ni recortar). El espacio
sobrante a los lados (o arriba/abajo) se rellena con la parte del propio
lienzo que caería ahí si se ampliara hasta cubrir la ventana: reducida,
desenfocada y oscurecida, para que se lea como fondo y no como juego.
Solo se procesan las franjas, y se refrescan cada pocos cuadros.
"""
import pygame

OSCURECER = (92, 100, 96)
REFRESCO_CUADROS = 4
REDUCCION = 8


class PresentadorPantalla:
    def __init__(self):
        self._franjas = []
        self._clave = None
        self._cuadro = 0

    @staticmethod
    def rect_juego(tamano):
        ancho, alto = tamano
        escala = min(ancho / 960, alto / 720)
        destino = pygame.Rect(0, 0, round(960 * escala), round(720 * escala))
        destino.center = (ancho // 2, alto // 2)
        return destino, escala

    @staticmethod
    def _franja(lienzo, area_lienzo, tamano):
        area = area_lienzo.clip(lienzo.get_rect())
        if area.width < 1 or area.height < 1 or tamano[0] < 1 or tamano[1] < 1:
            return None
        pequena = pygame.transform.scale(lienzo.subsurface(area),
                                         (max(1, tamano[0] // REDUCCION), max(1, tamano[1] // REDUCCION)))
        try:
            pequena = pygame.transform.box_blur(pequena, 2)
        except (AttributeError, ValueError, pygame.error):
            pass
        franja = pygame.transform.scale(pequena, tamano)
        franja.fill(OSCURECER, special_flags=pygame.BLEND_MULT)
        return franja

    def _calcular(self, lienzo, tamano, destino):
        """Franjas: (superficie, posición en ventana)."""
        ancho, alto = tamano
        cubrir = max(ancho / 960, alto / 720)
        # Rect del lienzo ampliado hasta cubrir la ventana, centrado.
        ox, oy = (ancho - 960 * cubrir) / 2, (alto - 720 * cubrir) / 2
        franjas = []
        zonas = []
        if destino.left > 0:
            zonas += [pygame.Rect(0, 0, destino.left, alto),
                      pygame.Rect(destino.right, 0, ancho - destino.right, alto)]
        if destino.top > 0:
            zonas += [pygame.Rect(0, 0, ancho, destino.top),
                      pygame.Rect(0, destino.bottom, ancho, alto - destino.bottom)]
        for zona in zonas:
            if zona.width < 1 or zona.height < 1:
                continue
            area = pygame.Rect(round((zona.x - ox) / cubrir), round((zona.y - oy) / cubrir),
                               max(1, round(zona.width / cubrir)), max(1, round(zona.height / cubrir)))
            franja = self._franja(lienzo, area, zona.size)
            if franja:
                franjas.append((franja, zona.topleft))
        return franjas

    def presentar(self, pantalla, lienzo):
        """Dibuja el lienzo en la pantalla y devuelve (rect_juego, escala)."""
        tamano = pantalla.get_size()
        destino, escala = self.rect_juego(tamano)
        if destino.size != tamano:
            self._cuadro += 1
            if self._clave != tamano or self._cuadro >= REFRESCO_CUADROS:
                self._franjas = self._calcular(lienzo, tamano, destino)
                self._clave, self._cuadro = tamano, 0
            pantalla.fill((4, 12, 9))
            for franja, posicion in self._franjas:
                pantalla.blit(franja, posicion)
            # Sombra fina que separa el juego del fondo.
            pygame.draw.rect(pantalla, (2, 8, 6), destino.inflate(4, 4), 2)
        pantalla.blit(pygame.transform.scale(lienzo, destino.size), destino)
        return destino, escala
