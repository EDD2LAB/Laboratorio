import pygame


class Animacion:
    """Controla una animación formada por varios frames."""

    def __init__(
        self,
        frames,
        duracion_frame=120,
        repetir=True,
        siguiente_estado="idle",
    ):
        if not frames:
            raise ValueError("Una animación necesita al menos un frame.")

        self.frames = frames
        self.duracion_frame = duracion_frame
        self.repetir = repetir
        self.siguiente_estado = siguiente_estado

        self.indice = 0
        self.tiempo_acumulado = 0
        self.terminada = False

    def reiniciar(self):
        self.indice = 0
        self.tiempo_acumulado = 0
        self.terminada = False

    def actualizar(self, delta_ms):
        """
        Actualiza el frame de la animación.

        Devuelve True si una animación no repetitiva acaba de terminar.
        """
        if self.terminada or len(self.frames) == 1:
            return False

        self.tiempo_acumulado += delta_ms
        acaba_de_terminar = False

        while self.tiempo_acumulado >= self.duracion_frame:
            self.tiempo_acumulado -= self.duracion_frame
            self.indice += 1

            if self.indice >= len(self.frames):
                if self.repetir:
                    self.indice = 0
                else:
                    self.indice = len(self.frames) - 1
                    self.terminada = True
                    acaba_de_terminar = True
                    break

        return acaba_de_terminar

    def imagen_actual(self):
        return self.frames[self.indice]


class ControladorAnimaciones:
    """
    Administra los diferentes estados visuales de un personaje.

    Ejemplos:
    idle, caminar, correr, hablar, consultar,
    recibir_mensaje, entregar_mensaje y usar_tronco.
    """

    def __init__(self):
        self.animaciones = {}
        self.estado_actual = None
        self.direccion = "derecha"

    def agregar(
        self,
        nombre,
        frames,
        duracion_frame=120,
        repetir=True,
        siguiente_estado="idle",
    ):
        self.animaciones[nombre] = Animacion(
            frames=frames,
            duracion_frame=duracion_frame,
            repetir=repetir,
            siguiente_estado=siguiente_estado,
        )

        if self.estado_actual is None:
            self.estado_actual = nombre

    def tiene(self, nombre):
        return nombre in self.animaciones

    def cambiar_estado(self, nombre, reiniciar=False):
        if nombre not in self.animaciones:
            return False

        if nombre == self.estado_actual and not reiniciar:
            return True

        self.estado_actual = nombre
        self.animaciones[nombre].reiniciar()
        return True

    def establecer_direccion(self, direccion):
        if direccion in ("izquierda", "derecha"):
            self.direccion = direccion

    def actualizar(self, delta_ms):
        if self.estado_actual is None:
            return

        animacion = self.animaciones[self.estado_actual]
        termino = animacion.actualizar(delta_ms)

        if termino:
            siguiente = animacion.siguiente_estado

            if siguiente in self.animaciones:
                self.cambiar_estado(siguiente, reiniciar=True)

    def imagen_actual(self):
        if self.estado_actual is None:
            return None

        imagen = self.animaciones[self.estado_actual].imagen_actual()

        if self.direccion == "izquierda":
            return pygame.transform.flip(imagen, True, False)

        return imagen

    def animacion_terminada(self):
        if self.estado_actual is None:
            return True

        return self.animaciones[self.estado_actual].terminada