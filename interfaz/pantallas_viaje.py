"""Fondos de carga y viaje preparados una vez, sin deformar el pixel art."""
import pygame

from nucleo.recursos import cargar_imagen, cargar_fuente
from interfaz.presentacion_pantalla import presentar


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
