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
        self._crear_botones()

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
            if evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                if self.escribiendo:
                    self.caracteres_visibles = len(self.texto_completo)
                    return None
                if not self.dialogo["respuestas"]:
                    return self._cerrar(None)
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
        # Reservar el texto completo desde el comienzo evita que el panel
        # cambie de tamaño durante la escritura y que las respuestas lo tapen.
        zona_texto_x = 36 + (205 if self.retratos.get(self.dialogo["personaje"]) else 28)
        lineas_completas = _envolver(self.texto_completo, self.fuente_texto, ancho - 36 - zona_texto_x - 30)
        paso_linea = max(24, self.fuente_texto.get_linesize())
        filas = self._filas_respuestas(ancho - 120)
        alto_respuestas = max(36, len(filas) * 62)
        alto_panel = max(174, 52 + len(lineas_completas) * paso_linea + 20 + alto_respuestas + 18)
        panel = pygame.Rect(36, alto - 36 - alto_panel, ancho - 72, alto_panel)
        y_boton = panel.bottom - 18 - alto_respuestas + 25
        for fila in filas:
            ancho_fila = sum(b.rect.width for b in fila) + 20 * (len(fila) - 1)
            x = (ancho - ancho_fila) // 2
            for boton in fila:
                boton.rect.topleft = (x, y_boton - 25)
                boton.centro = boton.rect.center
                x += boton.rect.width + 20
            y_boton += 62
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
            superficie.blit(render, (zona_texto_x, panel.y + 52 + i * paso_linea))

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
        respuestas = respuestas[:3]
        anchos = [max(170, self.fuente_boton.size(texto)[0] + 44) for texto in respuestas]
        separacion = 30
        ancho_total = sum(anchos) + separacion * (len(respuestas) - 1)
        cursor = (960 - ancho_total) // 2
        self.botones = []
        for texto, ancho in zip(respuestas, anchos):
            centro = (cursor + ancho // 2, 640)
            self.botones.append(
                Boton(texto, centro=centro, fuente=self.fuente_boton, tamano=(ancho, 50), identificador=texto)
            )
            cursor += ancho + separacion
        self.grupo.reemplazar(self.botones)

    def _filas_respuestas(self, ancho_disponible):
        filas, fila, ancho = [], [], 0
        for boton in self.botones:
            siguiente = ancho + (20 if fila else 0) + boton.rect.width
            if fila and siguiente > ancho_disponible:
                filas.append(fila)
                fila, ancho = [], 0
            fila.append(boton)
            ancho += (20 if len(fila) > 1 else 0) + boton.rect.width
        if fila:
            filas.append(fila)
        return filas

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
