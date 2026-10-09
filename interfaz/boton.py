"""Botones reutilizables para todas las escenas de La Copa."""

import pygame


CREMA = (255, 243, 210)
ORO = (237, 185, 87)
MADERA = (126, 81, 45)
MADERA_HOVER = (166, 110, 58)
MADERA_PRESIONADA = (92, 56, 33)
BORDE = (42, 25, 17)
DESACTIVADO = (72, 67, 58)


class Boton:
    """Botón con imagen o texto, estados visuales y activación accesible.

    La interfaz se dibuja en el lienzo lógico de 960x720; el escalado a la
    ventana lo realiza el juego completo, por lo que el área clicable y el
    botón se escalan siempre de la misma forma.
    """

    def __init__(
        self,
        texto,
        imagen=None,
        centro=(0, 0),
        fuente=None,
        tamano=None,
        desactivado=False,
        identificador=None,
        sonido_hover=None,
        sonido_clic=None,
    ):
        self.texto = texto
        self.imagen = imagen
        self.centro = centro
        self.fuente = fuente
        self.identificador = identificador or texto
        self.desactivado = desactivado
        self.sonido_hover = sonido_hover
        self.sonido_clic = sonido_clic
        self.hover = False
        self.presionado = False
        self.enfocado = False

        if imagen:
            self.rect = imagen.get_rect(center=centro)
        else:
            ancho_texto = fuente.size(texto)[0] if fuente else 120
            ancho, alto = tamano or (max(164, ancho_texto + 28), 50)
            self.rect = pygame.Rect(0, 0, ancho, alto)
            self.rect.center = centro

    @property
    def estado(self):
        if self.desactivado:
            return "bloqueado"
        if self.presionado:
            return "presionado"
        if self.hover or self.enfocado:
            return "hover"
        return "normal"

    def establecer_bloqueado(self, bloqueado=True):
        self.desactivado = bloqueado
        if bloqueado:
            self.presionado = False

    def actualizar(self, posicion_mouse):
        estaba_hover = self.hover
        self.hover = not self.desactivado and self.rect.collidepoint(posicion_mouse)
        if self.hover and not estaba_hover:
            self._reproducir(self.sonido_hover)

    def presionar(self, posicion):
        if not self.desactivado and self.rect.collidepoint(posicion):
            self.presionado = True
            return True
        return False

    def soltar(self, posicion):
        activar = self.presionado and not self.desactivado and self.rect.collidepoint(posicion)
        self.presionado = False
        if activar:
            self._reproducir(self.sonido_clic)
        return activar

    def activar(self):
        """Activa desde teclado o desde otro sistema de interfaz."""
        if self.desactivado:
            return False
        self._reproducir(self.sonido_clic)
        return True

    def fue_clickeado(self, posicion):
        """Compatibilidad con el juego existente (clic directo)."""
        if self.desactivado or not self.rect.collidepoint(posicion):
            return False
        self._reproducir(self.sonido_clic)
        return True

    def dibujar(self, superficie, posicion_mouse=(-1, -1)):
        self.actualizar(posicion_mouse)
        if self.imagen:
            imagen = self.imagen.copy()
            if self.estado == "hover":
                imagen.fill((255, 238, 178, 50), special_flags=pygame.BLEND_RGBA_ADD)
            elif self.estado == "presionado":
                imagen.fill((0, 0, 0, 58), special_flags=pygame.BLEND_RGBA_SUB)
            elif self.estado == "bloqueado":
                imagen.fill((80, 80, 80, 150), special_flags=pygame.BLEND_RGBA_MULT)
            superficie.blit(imagen, imagen.get_rect(center=self.centro))
            if self.enfocado:
                pygame.draw.rect(superficie, ORO, self.rect.inflate(8, 8), 2, border_radius=10)
            return

        colores = {
            "normal": MADERA,
            "hover": MADERA_HOVER,
            "presionado": MADERA_PRESIONADA,
            "bloqueado": DESACTIVADO,
        }
        color = colores[self.estado]
        pygame.draw.rect(superficie, BORDE, self.rect.inflate(6, 6), border_radius=10)
        pygame.draw.rect(superficie, color, self.rect, border_radius=8)
        borde = ORO if self.estado != "bloqueado" else (120, 112, 94)
        pygame.draw.rect(superficie, borde, self.rect, width=2, border_radius=8)
        if self.fuente:
            etiqueta = self.fuente.render(self.texto, True, CREMA if not self.desactivado else (185, 177, 153))
            superficie.blit(etiqueta, etiqueta.get_rect(center=self.rect.center))

    @staticmethod
    def _reproducir(sonido):
        if sonido:
            sonido.play()


class GrupoBotones:
    """Gestiona foco y activación por teclado de una lista de botones."""

    def __init__(self, botones=None):
        self.botones = list(botones or [])
        self.indice_foco = self._primer_habilitado()
        self._actualizar_foco()

    def reemplazar(self, botones):
        self.botones = list(botones)
        self.indice_foco = self._primer_habilitado()
        self._actualizar_foco()

    def manejar_teclado(self, evento):
        if not self.botones or evento.type != pygame.KEYDOWN:
            return None
        if evento.key in (pygame.K_TAB, pygame.K_RIGHT, pygame.K_DOWN):
            self._mover(1)
            return None
        if evento.key in (pygame.K_LEFT, pygame.K_UP):
            self._mover(-1)
            return None
        if evento.key in (pygame.K_RETURN, pygame.K_SPACE):
            boton = self.boton_enfocado
            return boton.identificador if boton and boton.activar() else None
        return None

    @property
    def boton_enfocado(self):
        if self.indice_foco is None:
            return None
        return self.botones[self.indice_foco]

    def _primer_habilitado(self):
        return next((i for i, boton in enumerate(self.botones) if not boton.desactivado), None)

    def _mover(self, paso):
        if self.indice_foco is None:
            return
        for _ in range(len(self.botones)):
            self.indice_foco = (self.indice_foco + paso) % len(self.botones)
            if not self.botones[self.indice_foco].desactivado:
                break
        self._actualizar_foco()

    def _actualizar_foco(self):
        for i, boton in enumerate(self.botones):
            boton.enfocado = i == self.indice_foco
