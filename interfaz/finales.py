"""Final del equipo: la misma regla e ilustraciones que el modo de un jugador."""
import pygame

from nucleo.recursos import cargar_imagen

CREMA = (255, 243, 210)
ORO = (237, 185, 87)
TEXTOS = {"victoria": ("LAS TRES ERAS FLORECEN", "{lider} guía al Consejo; NÚCLEO trabaja bajo supervisión humana."),
          "game_over": ("LA CONFIANZA SE CUBRE DE HUMO", "NÚCLEO fue corregido, pero los rumores dejaron heridas.")}
IMAGENES = {"victoria": "Finales/Final_positivo.jpeg", "game_over": "Finales/Game_over.jpeg"}


def determinar_final(indicadores):
    """Regla de un_jugador.tablilla.determinar_resultado_final con las claves del servidor."""
    positivos = sum(indicadores.get(nombre, 0) for nombre in ("sabiduria", "confianza", "armonia")) / 3
    negativo = indicadores.get("susurros_falsos", 0) + indicadores.get("desinformacion", 0)
    return "victoria" if positivos >= 55 and negativo < 100 else "game_over"


class PantallaFinal:
    def __init__(self, indicadores, etiquetas, fuente_titulo, fuente, lider="Kael", casos=8):
        self.lider, self.casos = lider, casos
        self.resultado = determinar_final(indicadores)
        self.indicadores = dict(indicadores)
        self.etiquetas = etiquetas
        self.fuente_titulo, self.fuente = fuente_titulo, fuente
        nueva = "Finales/Final_tres_eras.png" if self.resultado == "victoria" else "Finales/Final_humo_tres_eras.png"
        self.imagen = cargar_imagen(nueva, (960, 720), requerido=False)
        if self.imagen is None:
            self.imagen = cargar_imagen(IMAGENES[self.resultado], (960, 720), requerido=False)
        if self.imagen is None:
            print("[Arte] Falta la imagen:", IMAGENES[self.resultado])

    def dibujar(self, superficie):
        if self.imagen is not None:
            superficie.blit(self.imagen, (0, 0))
        else:
            superficie.fill((10, 24, 17))
        banda = pygame.Surface((920, 120), pygame.SRCALPHA)
        banda.fill((5, 20, 25, 205))
        superficie.blit(banda, (20, 55))
        pygame.draw.rect(superficie, (8, 26, 30), (310, 446, 340, 38), border_radius=8)
        titulo, detalle = TEXTOS[self.resultado]
        self._centrado(superficie, self.fuente_titulo, titulo, 88, CREMA)
        from nucleo.recursos import envolver_texto
        for i, linea in enumerate(envolver_texto(detalle.format(lider=self.lider), self.fuente, 860)):
            self._centrado(superficie, self.fuente, linea, 124 + i * 25, CREMA)
        self._centrado(superficie, self.fuente, f"Casos resueltos: {self.casos} de 8", 465, CREMA)
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
