"""Cuadro de diálogo reutilizable con escritura progresiva y respuestas."""

import pygame

from interfaz.boton import Boton, GrupoBotones


class ControladorDialogo:
    """Mantiene un diálogo activo y bloquea otras interacciones mientras exista."""

    def __init__(self, fuente_texto, fuente_nombre, fuente_boton, velocidad=45):
        self.fuente_texto = fuente_texto
        self.fuente_nombre = fuente_nombre
        self.fuente_boton = fuente_boton
        self.velocidad = velocidad
        self.dialogo = None
        self.retratos = {}
        self.caracteres_visibles = 0.0
        self.botones = []
        self.grupo = GrupoBotones()
        self.resultado = None

    @property
    def activo(self):
        return self.dialogo is not None

    @property
    def texto_completo(self):
        return self.dialogo["texto"] if self.dialogo else ""

    @property
    def escribiendo(self):
        return self.activo and self.caracteres_visibles < len(self.texto_completo)

    def iniciar(self, dialogo, retratos=None):
        """Recibe {personaje, texto, respuestas?}; no revela todo el texto aún."""
        self.dialogo = {
            "personaje": dialogo.get("personaje", "Habitante"),
            "texto": dialogo.get("texto", ""),
            "respuestas": list(dialogo.get("respuestas", [])),
        }
        self.retratos = retratos or {}
        self.caracteres_visibles = 0.0
        self.resultado = None
        self.botones = []
        self.grupo.reemplazar([])

    def actualizar(self, delta_segundos):
        if self.escribiendo:
            self.caracteres_visibles = min(
                len(self.texto_completo), self.caracteres_visibles + self.velocidad * delta_segundos
            )
        if not self.escribiendo and not self.botones:
            self._crear_botones()

    def manejar_evento(self, evento, posicion):
        """Devuelve ('respuesta', texto) o ('cerrar', None) al terminar."""
        if not self.activo:
            return None
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_ESCAPE:
                return self._cerrar(None)
            if self.escribiendo and evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.caracteres_visibles = len(self.texto_completo)
                return None
            eleccion = self.grupo.manejar_teclado(evento)
            if eleccion:
                return self._elegir(eleccion)
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.escribiendo:
                self.caracteres_visibles = len(self.texto_completo)
                return None
            for boton in self.botones:
                if boton.fue_clickeado(posicion):
                    return self._elegir(boton.identificador)
            if not self.dialogo["respuestas"]:
                return self._cerrar(None)
        return None

    def dibujar(self, superficie, posicion_mouse, ancho, alto):
        if not self.activo:
            return
        panel = pygame.Rect(36, alto - 210, ancho - 72, 174)
        sombra = pygame.Surface(panel.size, pygame.SRCALPHA)
        sombra.fill((11, 23, 18, 235))
        superficie.blit(sombra, panel.topleft)
        pygame.draw.rect(superficie, (237, 185, 87), panel, width=3, border_radius=14)

        retrato = self.retratos.get(self.dialogo["personaje"])
        zona_texto_x = panel.x + 28
        if retrato:
            retrato_rect = retrato.get_rect(midbottom=(panel.x + 105, panel.bottom - 14))
            superficie.blit(retrato, retrato_rect)
            pygame.draw.rect(superficie, (237, 185, 87), retrato_rect.inflate(8, 8), 2, border_radius=8)
            zona_texto_x = panel.x + 205

        nombre = self.fuente_nombre.render(self.dialogo["personaje"].upper(), True, (237, 185, 87))
        superficie.blit(nombre, (zona_texto_x, panel.y + 18))
        texto = self.texto_completo[: int(self.caracteres_visibles)]
        for i, linea in enumerate(_envolver(texto, self.fuente_texto, panel.right - zona_texto_x - 30)):
            render = self.fuente_texto.render(linea, True, (255, 243, 210))
            superficie.blit(render, (zona_texto_x, panel.y + 52 + i * 24))

        if not self.escribiendo:
            for boton in self.botones:
                boton.dibujar(superficie, posicion_mouse)
            if not self.botones:
                aviso = self.fuente_boton.render("Clic para continuar", True, (237, 185, 87))
                superficie.blit(aviso, aviso.get_rect(bottomright=(panel.right - 22, panel.bottom - 18)))

    def _crear_botones(self):
        respuestas = self.dialogo["respuestas"]
        if not respuestas:
            return
        separacion = 190
        inicio = 480 - separacion * (len(respuestas) - 1) // 2
        self.botones = [
            Boton(texto, centro=(inicio + i * separacion, 640), fuente=self.fuente_boton, identificador=texto)
            for i, texto in enumerate(respuestas[:3])
        ]
        self.grupo.reemplazar(self.botones)

    def _elegir(self, respuesta):
        return self._cerrar(respuesta)

    def _cerrar(self, respuesta):
        self.resultado = respuesta
        self.dialogo = None
        self.botones = []
        self.grupo.reemplazar([])
        return ("respuesta" if respuesta is not None else "cerrar", respuesta)


def _envolver(texto, fuente, ancho_maximo):
    palabras, lineas, actual = texto.split(), [], ""
    for palabra in palabras:
        prueba = f"{actual} {palabra}".strip()
        if fuente.size(prueba)[0] <= ancho_maximo:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas
