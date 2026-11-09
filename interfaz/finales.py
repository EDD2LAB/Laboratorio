"""Final del equipo: la misma regla e ilustraciones que el modo de un jugador."""
import pygame

from nucleo.recursos import cargar_imagen

CREMA = (255, 243, 210)
ORO = (237, 185, 87)
TEXTOS = {"victoria": ("LA COPA FLORECE", "Mira será la nueva Cacique"),
          "game_over": ("LA COPA SE CUBRE DE HUMO", "El Consejo deberá recomponer la confianza")}
IMAGENES = {"victoria": "Finales/Final_positivo.jpeg", "game_over": "Finales/Game_over.jpeg"}


def determinar_final(indicadores):
    """Regla de un_jugador.tablilla.determinar_resultado_final con las claves del servidor."""
    positivos = sum(indicadores.get(nombre, 0) for nombre in ("sabiduria", "confianza", "armonia")) / 3
    negativo = indicadores.get("susurros_falsos", 0) + indicadores.get("desinformacion", 0)
    return "victoria" if positivos >= 55 and negativo < 100 else "game_over"


class PantallaFinal:
    def __init__(self, indicadores, etiquetas, fuente_titulo, fuente):
        self.resultado = determinar_final(indicadores)
        self.indicadores = dict(indicadores)
        self.etiquetas = etiquetas
        self.fuente_titulo, self.fuente = fuente_titulo, fuente
        self.imagen = cargar_imagen(IMAGENES[self.resultado], (960, 720), requerido=False)
        if self.imagen is None:
            print("[Arte] Falta la imagen:", IMAGENES[self.resultado])

    def dibujar(self, superficie):
        if self.imagen is not None:
            superficie.blit(self.imagen, (0, 0))
        else:
            superficie.fill((10, 24, 17))
        titulo, detalle = TEXTOS[self.resultado]
        self._centrado(superficie, self.fuente_titulo, titulo, 88, CREMA)
        self._centrado(superficie, self.fuente, detalle, 124, CREMA)
        resumen = pygame.Rect(300, 496, 360, 132)
        capa = pygame.Surface(resumen.size, pygame.SRCALPHA)
        capa.fill((10, 24, 17, 220))
        superficie.blit(capa, resumen)
        pygame.draw.rect(superficie, ORO, resumen, 2, border_radius=10)
        filas = ("sabiduria", "confianza", "armonia", "desinformacion")
        for indice, nombre in enumerate(filas):
            self._centrado(superficie, self.fuente, f"{self.etiquetas.get(nombre, nombre)}: {self.indicadores.get(nombre, 0)}",
                           514 + indice * 26, CREMA)
        self._centrado(superficie, self.fuente, "Haz clic para continuar", 655, ORO)

    @staticmethod
    def _centrado(superficie, fuente, texto, y, color):
        render = fuente.render(texto, True, color)
        superficie.blit(render, render.get_rect(center=(480, y)))
