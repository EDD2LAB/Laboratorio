"""HUD compacto y animado de los indicadores de La Copa."""

import pygame


POSITIVOS = {"sabiduria", "confianza_consejo", "armonia"}
NEGATIVOS = {"susurros_falsos", "desinformación"}


class HUDIndicadores:
    """Suaviza barras, anuncia variaciones y señala estados críticos."""

    def __init__(self, fuente, marcos=None):
        self.fuente = fuente
        self.marcos = marcos or {}
        self.valores = {}
        self.objetivos = {}
        self.avisos = []
        self.tiempo = 0.0

    def actualizar(self, indicadores, delta_segundos):
        self.tiempo += delta_segundos
        for nombre, valor in indicadores.items():
            valor = max(0, min(100, valor))
            if nombre not in self.valores:
                self.valores[nombre] = float(valor)
                self.objetivos[nombre] = valor
                continue
            anterior = self.objetivos[nombre]
            if valor != anterior:
                self.avisos.append({
                    "nombre": nombre,
                    "cambio": valor - anterior,
                    "beneficioso": (valor - anterior > 0) != (nombre in NEGATIVOS),
                    "vida": 2.8,
                    "desfase": len(self.avisos) * 0.18,
                })
                self.objetivos[nombre] = valor
            # Easing rápido: los cambios se ven, pero no saltan bruscamente.
            self.valores[nombre] += (self.objetivos[nombre] - self.valores[nombre]) * min(1, delta_segundos * 7)
        for aviso in self.avisos:
            aviso["vida"] -= delta_segundos
        self.avisos = [aviso for aviso in self.avisos if aviso["vida"] > 0]

    def dibujar(self, superficie, x=14, y=12):
        nombres = list(self.objetivos)
        ancho_marco = max((marco.get_width() for marco in self.marcos.values()), default=170)
        alto_marco = max((marco.get_height() for marco in self.marcos.values()), default=55)
        alto_fila = alto_marco + 7
        panel = pygame.Rect(x - 6, y - 5, ancho_marco + 14, max(70, len(nombres) * alto_fila + 12))
        velo = pygame.Surface(panel.size, pygame.SRCALPHA)
        velo.fill((10, 27, 20, 182))
        superficie.blit(velo, panel.topleft)
        pygame.draw.rect(superficie, (202, 151, 77), panel, width=2, border_radius=12)

        for indice, nombre in enumerate(nombres):
            valor = self.valores[nombre]
            objetivo = self.objetivos[nombre]
            fila_y = y + indice * alto_fila
            self._dibujar_barra(superficie, nombre, valor, objetivo, x, fila_y)
        self._dibujar_avisos(superficie, panel.right + 10, y + 18)

    def _dibujar_barra(self, superficie, nombre, valor, objetivo, x, y):
        marco = self.marcos.get(nombre)
        escala_x = marco.get_width() / 280 if marco else 1
        escala_y = marco.get_height() / 55 if marco else 1
        es_negativo = nombre in NEGATIVOS
        critico = objetivo >= 75 if es_negativo else objetivo <= 25
        if critico:
            intensidad = int(80 + 50 * abs(pygame.math.Vector2(1, 0).rotate(self.tiempo * 360).x))
            pygame.draw.rect(
                superficie,
                (220, 82, 64, intensidad),
                (x + int(93 * escala_x), y + int(20 * escala_y), int(167 * escala_x), int(25 * escala_y)),
                border_radius=10,
            )

        # El marco tiene un canal negro opaco; por eso se pinta primero y el
        # relleno se coloca encima, exactamente dentro de su abertura.
        # El canal ilustrado ocupa casi todo el tramo entre el emblema y el
        # remate derecho.  Antes empezaba demasiado tarde, por lo que un 60%
        # parecía visualmente mucho menor. Conservamos el borde dorado y
        # aprovechamos toda la cavidad útil.
        canal = pygame.Rect(
            x + int(91 * escala_x),
            y + int(25 * escala_y),
            int(153 * escala_x),
            max(4, int(14 * escala_y)),
        )
        if es_negativo:
            color = (221, 82, 68) if valor >= 55 else (215, 159, 69)
        else:
            color = (102, 200, 112) if valor >= 35 else (225, 171, 69)

        if marco:
            superficie.blit(marco, (x, y))
        else:
            etiqueta = nombre.replace("_", " ").capitalize()
            texto = self.fuente.render(etiqueta, True, (255, 243, 210))
            superficie.blit(texto, (x + 6, y + 20))
            pygame.draw.rect(superficie, (237, 185, 87), canal, width=2, border_radius=7)

        interior = canal.inflate(-6, -8)
        pygame.draw.rect(superficie, (25, 22, 18), interior, border_radius=4)
        ancho = int(interior.width * valor / 100)
        if ancho:
            pygame.draw.rect(
                superficie,
                color,
                (interior.x, interior.y, ancho, interior.height),
                border_radius=4,
            )

        numero = self.fuente.render(str(round(valor)), True, (255, 243, 210))
        superficie.blit(numero, numero.get_rect(midleft=(canal.right + max(2, int(5 * escala_x)), canal.centery)))

    def _dibujar_avisos(self, superficie, x, y):
        for indice, aviso in enumerate(self.avisos[-4:]):
            progreso = aviso["vida"] / 2.8
            movimiento = int((1 - progreso) * 22) + indice * 22
            color = (111, 220, 126) if aviso["beneficioso"] else (242, 113, 90)
            texto = f"{'+' if aviso['cambio'] > 0 else ''}{aviso['cambio']} {aviso['nombre'].replace('_', ' ').capitalize()}"
            render = self.fuente.render(texto, True, color)
            superficie.blit(render, (x, y - movimiento))
