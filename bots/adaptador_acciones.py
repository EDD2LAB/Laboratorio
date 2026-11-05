import uuid


class AdaptadorAccionesBot:
    """Enruta acciones del bot por la misma API de la partida que usa el jugador."""

    def __init__(self, partida, identificador):
        self.partida = partida
        self.identificador = identificador

    def estado(self):
        return self.partida.estado(self.identificador)

    def solicitar(self, accion, ahora, **datos):
        publico = self.partida.mision.publico(self.partida.conectados)
        solicitud = {
            "accion": accion,
            "id_solicitud": uuid.uuid4().hex,
            "ronda": publico["ronda"],
            **datos,
        }
        return self.partida.actuar(self.identificador, solicitud, ahora)
