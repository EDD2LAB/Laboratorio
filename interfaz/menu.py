"""Pantallas modales de pausa y ayuda."""

import pygame

from interfaz.boton import Boton, GrupoBotones


class MenuModal:
    """Modal reutilizable que bloquea el juego mientras está abierto."""

    def __init__(self, fuente_titulo, fuente_texto, fuente_boton):
        self.fuente_titulo = fuente_titulo
        self.fuente_texto = fuente_texto
        self.fuente_boton = fuente_boton
        self.botones = []
        self.grupo = GrupoBotones()

    def configurar(self, opciones):
        separacion = 62
        inicio = 448 - separacion * (len(opciones) - 1) // 2
        self.botones = [
            Boton(texto, centro=(480, inicio + i * separacion), fuente=self.fuente_boton, identificador=clave)
            for i, (clave, texto) in enumerate(opciones)
        ]
        self.grupo.reemplazar(self.botones)

    def manejar_evento(self, evento, posicion):
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_ESCAPE:
                return "volver"
            return self.grupo.manejar_teclado(evento)
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for boton in self.botones:
                if boton.fue_clickeado(posicion):
                    return boton.identificador
        return None

    def dibujar(self, superficie, titulo, lineas, mouse_pos):
        velo = pygame.Surface(superficie.get_size(), pygame.SRCALPHA)
        velo.fill((4, 13, 11, 190))
        superficie.blit(velo, (0, 0))
        panel = pygame.Rect(170, 85, 620, 550)
        pygame.draw.rect(superficie, (17, 43, 31), panel, border_radius=18)
        pygame.draw.rect(superficie, (237, 185, 87), panel, width=3, border_radius=18)
        texto_titulo = self.fuente_titulo.render(titulo, True, (237, 185, 87))
        superficie.blit(texto_titulo, texto_titulo.get_rect(center=(panel.centerx, panel.y + 48)))
        # Las explicaciones de ayuda pueden ser más largas que una etiqueta.
        # Se dividen aquí (en vez de depender de cada llamador) para que nunca
        # atraviesen el borde del modal.
        lineas_ajustadas = []
        ancho_util = panel.width - 70
        for linea in lineas:
            palabras = linea.split()
            actual = ""
            for palabra in palabras:
                prueba = f"{actual} {palabra}".strip()
                if not actual or self.fuente_texto.size(prueba)[0] <= ancho_util:
                    actual = prueba
                else:
                    lineas_ajustadas.append(actual)
                    actual = palabra
            if actual:
                lineas_ajustadas.append(actual)

        y = panel.y + 100
        for linea in lineas_ajustadas:
            texto = self.fuente_texto.render(linea, True, (255, 243, 210))
            superficie.blit(texto, texto.get_rect(center=(panel.centerx, y)))
            y += 25
        for boton in self.botones:
            boton.dibujar(superficie, mouse_pos)
