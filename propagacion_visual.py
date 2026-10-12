import pygame


class PropagacionVisual:
    """Señal determinista que recorre una ruta de plataformas en tiempo real."""

    VELOCIDAD_PIXELES_SEGUNDO = 190.0
    DURACION_FRAME_MS = 70

    def __init__(
        self,
        origen,
        destino,
        ruta,
        posiciones,
        puentes,
        sprite,
        velocidad=VELOCIDAD_PIXELES_SEGUNDO,
        tipo="informacion_normal",
    ):
        if len(ruta) < 2:
            raise ValueError("Una propagacion visual necesita al menos un puente.")
        if len(posiciones) != len(ruta) or len(puentes) != len(ruta) - 1:
            raise ValueError("La ruta, sus posiciones y puentes no coinciden.")
        if any(puente is None for puente in puentes):
            raise ValueError("Cada tramo de la ruta debe corresponder a un puente transitable.")
        if velocidad <= 0:
            raise ValueError("La velocidad de propagacion debe ser positiva.")

        self.origen = origen
        self.destino = destino
        self.ruta = list(ruta)
        self.indice_actual = 0
        self.progreso = 0.0
        self.velocidad = float(velocidad)
        self.sprite = list(sprite)
        self.puentes = list(puentes)
        self.posiciones = [pygame.Vector2(posicion) for posicion in posiciones]
        self.activa = True
        self.tipo = tipo
        self.tiempo_animacion_ms = 0.0
        self.posicion = self.posiciones[0].copy()

    @property
    def puente_actual(self):
        if not self.activa or self.indice_actual >= len(self.puentes):
            return None
        return self.puentes[self.indice_actual]

    def actualizar(self, delta_ms):
        if not self.activa:
            return

        restante = self.velocidad * max(0.0, float(delta_ms)) / 1000.0
        self.tiempo_animacion_ms += max(0.0, float(delta_ms))
        while restante > 0 and self.indice_actual < len(self.puentes):
            inicio = self.posiciones[self.indice_actual]
            final = self.posiciones[self.indice_actual + 1]
            longitud = inicio.distance_to(final)
            if longitud <= 0:
                self.indice_actual += 1
                self.progreso = 0.0
                continue

            distancia_restante = longitud * (1.0 - self.progreso)
            if restante >= distancia_restante:
                restante -= distancia_restante
                self.indice_actual += 1
                self.progreso = 0.0
                self.posicion = final.copy()
            else:
                self.progreso += restante / longitud
                restante = 0.0
                self.posicion = inicio.lerp(final, self.progreso)

        if self.indice_actual >= len(self.puentes):
            self.indice_actual = len(self.puentes)
            self.progreso = 1.0
            self.posicion = self.posiciones[-1].copy()
            self.activa = False

    def obtener_frame(self):
        if not self.sprite or not self.activa:
            return None
        indice = int(self.tiempo_animacion_ms // self.DURACION_FRAME_MS) % len(self.sprite)
        return self.sprite[indice]

    @classmethod
    def desde_evento(cls, evento, grafo, sprite, ancho, alto, velocidad=None):
        if evento.get("tipo") != "propagacion":
            raise ValueError("El evento recibido no es una propagacion.")
        ruta = list(evento.get("ruta", ()))
        posiciones = [
            (
                grafo.plataformas[nodo]["posicion"][0] * ancho,
                grafo.plataformas[nodo]["posicion"][1] * alto,
            )
            for nodo in ruta
        ]
        puentes = [
            grafo.obtener_puente(origen, destino)
            for origen, destino in zip(ruta, ruta[1:])
        ]
        argumentos = {}
        if velocidad is not None:
            argumentos["velocidad"] = velocidad
        return cls(
            evento["origen"],
            evento["destino"],
            ruta,
            posiciones,
            puentes,
            sprite,
            tipo=evento.get("clase", "informacion_normal"),
            **argumentos,
        )

    def como_evento(self):
        """Representacion serializable para reconstruir la animacion en clientes."""
        return {
            "tipo": "propagacion",
            "origen": self.origen,
            "destino": self.destino,
            "ruta": list(self.ruta),
            "clase": self.tipo,
        }
