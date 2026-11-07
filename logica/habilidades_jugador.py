"""Habilidades activas del modo individual."""


class HabilidadJugador:
    """Controla duración y recarga de la habilidad del personaje activo."""

    CONFIGURACIONES = {
        "guardian": {
            "id": "impulso_viento",
            "nombre": "Impulso de viento",
            "duracion_ms": 850,
            "recarga_ms": 6000,
        },
        "periodista": {
            "id": "comunicado_publico",
            "nombre": "Comunicado público",
            "duracion_ms": 0,
            "recarga_ms": 0,
        },
    }

    def __init__(self, personaje):
        if personaje not in self.CONFIGURACIONES:
            raise ValueError(f"No hay habilidades configuradas para {personaje}.")
        self.personaje = personaje
        self.configuracion = self.CONFIGURACIONES[personaje]
        self.tiempo_activo_ms = 0.0
        self.recarga_restante_ms = 0.0
        self.usada = False

    @property
    def disponible(self):
        if self.personaje == "periodista":
            return not self.usada
        return self.recarga_restante_ms <= 0

    @property
    def multiplicador_movimiento(self):
        if self.personaje == "guardian" and self.tiempo_activo_ms > 0:
            return 2.2
        return 1.0

    def activar(self):
        if not self.disponible:
            return False
        if self.personaje == "guardian":
            self.tiempo_activo_ms = self.configuracion["duracion_ms"]
            self.recarga_restante_ms = self.configuracion["recarga_ms"]
        else:
            self.usada = True
        return True

    def actualizar(self, delta_ms):
        delta = max(0.0, float(delta_ms))
        self.tiempo_activo_ms = max(0.0, self.tiempo_activo_ms - delta)
        self.recarga_restante_ms = max(0.0, self.recarga_restante_ms - delta)
