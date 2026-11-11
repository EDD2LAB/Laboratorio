"""RTT de aplicación, sin depender del reloj del servidor ni de Pygame."""
import math
import time


class SondaPing:
    def __init__(self, metricas, reloj=time.monotonic):
        self.metricas, self.reloj = metricas, reloj
        self.ultimo = -math.inf
        self.pendiente = None

    def siguiente(self):
        ahora = self.reloj()
        if ahora - self.ultimo < 3:
            return None
        self.ultimo = self.pendiente = ahora
        return {"tipo": "ping", "t": ahora}

    def recibir(self, mensaje):
        if self.pendiente is None or mensaje.get("t") != self.pendiente:
            return False
        muestra = (self.reloj() - self.pendiente) * 1000
        self.pendiente = None
        if not 0 <= muestra <= 15000:
            return False
        anterior = self.metricas.get("ping_ms")
        self.metricas["ping_ms"] = muestra if anterior is None else anterior * .75 + muestra * .25
        self.metricas["ping_actualizado"] = self.reloj()
        return True
