"""Aviso breve con la norma aplicada al resolver un evento (una vez por evento_id)."""
import time

import pygame

from interfaz.arte import NUEVOS, icono

DURACION = 4.5
FONDO = (87, 45, 28)
BORDE = (237, 185, 87)
CREMA = (255, 243, 210)
FRASES = {(True, True): "Caso documentado. El responsable responde ante la ley.",
          (True, False): "El daño siguió. La conducta sigue siendo sancionable.",
          (False, True): "Verificar y avisar protege a la aldea.",
          (False, False): "La alerta era real: callarla también hace daño."}


def frase_legal(con_delito, correcto):
    return FRASES[bool(con_delito), bool(correcto)]


class AvisoLegal:
    """Arriba y al centro: no tapa la escena. El texto se renderiza una sola vez."""

    def __init__(self, fuente, narrador):
        self.fuente = fuente
        self.narrador = narrador
        self.icono = icono(NUEVOS + "icono_ley.png", (20, 20))
        self.cola = []
        self.imagen = None
        self.hasta = 0.0

    def agregar(self, resultado):
        if resultado.get("cita_corta"):
            self.cola.append((resultado["cita_corta"], frase_legal(resultado.get("con_delito"), resultado.get("correcto"))))

    def _mostrar(self, cita, frase, ahora):
        linea1, linea2 = (self.fuente.render(t, True, CREMA) for t in (cita, frase))
        sangria = 28 if self.icono else 0
        alto_linea = self.fuente.get_linesize()
        ancho = min(920, max(linea1.get_width() + sangria, linea2.get_width()) + 28)
        self.imagen = pygame.Surface((ancho, alto_linea * 2 + 18), pygame.SRCALPHA)
        marco = self.imagen.get_rect()
        pygame.draw.rect(self.imagen, (*FONDO, 235), marco, border_radius=8)
        pygame.draw.rect(self.imagen, BORDE, marco, width=2, border_radius=8)
        if self.icono:
            self.imagen.blit(self.icono, (14, 8))
        self.imagen.blit(linea1, (14 + sangria, 8))
        self.imagen.blit(linea2, (14, 10 + alto_linea))
        self.hasta = ahora + DURACION
        self.narrador.decir(cita.replace(" · ", ": ") + ". " + frase)

    def dibujar(self, superficie):
        ahora = time.monotonic()
        if self.imagen is not None and ahora >= self.hasta:
            self.imagen = None
        if self.imagen is None and self.cola:
            self._mostrar(*self.cola.pop(0), ahora)
        if self.imagen is not None:
            superficie.blit(self.imagen, self.imagen.get_rect(midtop=(superficie.get_width() // 2, 12)))
