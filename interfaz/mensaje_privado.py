"""Interfaz de mensajes privados entregados por el Mensajero."""

import pygame

from interfaz.boton import Boton


class ControladorMensajePrivado:
    """Abre pergaminos, marca su lectura y conserva un historial local."""

    DURACION_APERTURA = 0.45

    def __init__(self, fuente_titulo, fuente_texto, fuente_boton, pergamino):
        self.fuente_titulo = fuente_titulo
        self.fuente_texto = fuente_texto
        self.fuente_boton = fuente_boton
        self.pergamino = pergamino
        self.mensaje_actual = None
        self.historial = []
        self.progreso_apertura = 0.0
        self.boton_cerrar = Boton("Cerrar", centro=(480, 574), fuente=fuente_boton, identificador="cerrar")

    @property
    def activo(self):
        return self.mensaje_actual is not None

    @property
    def abriendo(self):
        return self.progreso_apertura < 1.0

    def abrir(self, mensaje):
        self.mensaje_actual = {
            "remitente": mensaje.get("remitente", "Mensajero"),
            "destinatario": mensaje.get("destinatario", "Guardián"),
            "texto": mensaje.get("texto", ""),
            "leido": False,
        }
        self.progreso_apertura = 0.0

    def actualizar(self, delta_segundos):
        if self.activo and self.abriendo:
            self.progreso_apertura = min(1.0, self.progreso_apertura + delta_segundos / self.DURACION_APERTURA)
            if not self.abriendo:
                self.mensaje_actual["leido"] = True

    def manejar_evento(self, evento, posicion):
        if not self.activo or self.abriendo:
            return False
        if evento.type == pygame.KEYDOWN and evento.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
            return self.cerrar()
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and self.boton_cerrar.fue_clickeado(posicion):
            return self.cerrar()
        return False

    def cerrar(self):
        if not self.activo:
            return False
        self.historial.append(dict(self.mensaje_actual))
        self.mensaje_actual = None
        return True

    def dibujar(self, superficie, mouse_pos):
        velo = pygame.Surface(superficie.get_size(), pygame.SRCALPHA)
        velo.fill((4, 13, 11, 175))
        superficie.blit(velo, (0, 0))

        escala = 0.76 + self.progreso_apertura * 0.24
        ancho = round(self.pergamino.get_width() * escala)
        alto = round(self.pergamino.get_height() * escala)
        pergamino = pygame.transform.smoothscale(self.pergamino, (ancho, alto))
        rect = pergamino.get_rect(center=(480, 345))
        superficie.blit(pergamino, rect)

        if self.abriendo:
            texto = self.fuente_boton.render("El Mensajero entrega un pergamino...", True, (255, 243, 210))
            superficie.blit(texto, texto.get_rect(center=(480, 620)))
            return

        # El PNG conserva un margen transparente sobre el pergamino; el
        # contenido comienza más abajo, dentro de la zona clara del papel.
        titulo = self.fuente_texto.render("MENSAJE PRIVADO", True, (73, 43, 28))
        superficie.blit(titulo, titulo.get_rect(center=(480, rect.y + 132)))
        remitente = self.fuente_texto.render(f"De: {self.mensaje_actual['remitente']}", True, (91, 54, 31))
        destinatario = self.fuente_texto.render(f"Para: {self.mensaje_actual['destinatario']}", True, (91, 54, 31))
        superficie.blit(remitente, remitente.get_rect(center=(480, rect.y + 160)))
        superficie.blit(destinatario, destinatario.get_rect(center=(480, rect.y + 181)))

        # Este rectángulo coincide con la parte clara central del pergamino.
        # Además de envolver a un ancho conservador, se aplica como clip para
        # impedir que cualquier línea futura atraviese los rollos laterales.
        area_texto = pygame.Rect(rect.x + 112, rect.y + 202, rect.width - 224, 92)
        clip_anterior = superficie.get_clip()
        superficie.set_clip(area_texto)
        y = area_texto.y + 12
        for linea in _envolver(self.mensaje_actual["texto"], self.fuente_texto, area_texto.width):
            render = self.fuente_texto.render(linea, True, (69, 42, 28))
            superficie.blit(render, render.get_rect(center=(area_texto.centerx, y)))
            y += 23
        superficie.set_clip(clip_anterior)
        self.boton_cerrar.dibujar(superficie, mouse_pos)


def _envolver(texto, fuente, ancho_maximo):
    palabras, lineas, actual = texto.split(), [], ""
    for palabra in palabras:
        prueba = f"{actual} {palabra}".strip()
        if not actual or fuente.size(prueba)[0] <= ancho_maximo:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas
