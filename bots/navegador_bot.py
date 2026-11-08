import heapq
import math

from multijugador.movimiento import VELOCIDAD, orientacion_de


class NavegadorBot:
    PASO = 8
    RADIO_INTERACCION = 68

    def __init__(self, colisiones):
        self.colisiones = colisiones
        self.ruta = []
        self.destino = None
        self.error = ""
        self._reintento_ms = 0.0

    @classmethod
    def _celda(cls, posicion):
        return round(posicion[0] / cls.PASO), round(posicion[1] / cls.PASO)

    @classmethod
    def _posicion(cls, celda):
        return celda[0] * cls.PASO, celda[1] * cls.PASO

    @staticmethod
    def _distancia(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def buscar_ruta(self, origen, destino, radio=None):
        radio = self.RADIO_INTERACCION if radio is None else radio
        inicio = self._celda(origen)
        objetivo = tuple(map(float, destino))
        pendientes = [(0.0, inicio)]
        anterior = {inicio: None}
        costo = {inicio: 0.0}
        encontrado = None
        movimientos = (
            (-1, 0, 1), (1, 0, 1), (0, -1, 1), (0, 1, 1),
            (-1, -1, 1.4142), (-1, 1, 1.4142),
            (1, -1, 1.4142), (1, 1, 1.4142),
        )

        while pendientes:
            _, actual = heapq.heappop(pendientes)
            posicion = self._posicion(actual)
            if self._distancia(posicion, objetivo) <= radio:
                encontrado = actual
                break
            for dx, dy, paso in movimientos:
                vecino = actual[0] + dx, actual[1] + dy
                px, py = self._posicion(vecino)
                if self.colisiones.bloqueado(px, py):
                    continue
                if dx and dy and (
                    self.colisiones.bloqueado(px, self._posicion(actual)[1])
                    or self.colisiones.bloqueado(self._posicion(actual)[0], py)
                ):
                    continue
                nuevo_costo = costo[actual] + paso
                if nuevo_costo >= costo.get(vecino, float("inf")):
                    continue
                anterior[vecino] = actual
                costo[vecino] = nuevo_costo
                heuristica = max(
                    0.0,
                    self._distancia((px, py), objetivo) - radio,
                ) / self.PASO
                heapq.heappush(pendientes, (nuevo_costo + heuristica, vecino))

        if encontrado is None:
            self.ruta = []
            self.error = "No se encontró una ruta transitable hasta el objetivo."
            self.destino = objetivo
            self._reintento_ms = 750
            return None

        camino = []
        paso = encontrado
        while paso is not None:
            camino.append(self._posicion(paso))
            paso = anterior[paso]
        self.ruta = list(reversed(camino))[1:]
        self.destino = objetivo
        self.error = ""
        self._reintento_ms = 0
        return list(self.ruta)

    def avanzar(self, jugador, destino, segundos, radio=None):
        radio = self.RADIO_INTERACCION if radio is None else radio
        actual = (jugador["x"], jugador["y"])
        self._reintento_ms = max(0.0, self._reintento_ms - max(0, segundos) * 1000)
        if self._distancia(actual, destino) <= radio:
            self.ruta = []
            return True
        if self.destino != tuple(map(float, destino)):
            self.destino = None
            self.ruta = []
            self.error = ""
        if self.error and self._reintento_ms:
            return False
        if self.destino is None or not self.ruta:
            radio_ruta = max(0, radio - self.PASO)
            if self.buscar_ruta(actual, destino, radio_ruta) is None:
                return False
        while self.ruta and self._distancia(actual, self.ruta[0]) <= 8:
            self.ruta.pop(0)
        if not self.ruta:
            return self._distancia(actual, destino) <= radio

        siguiente = self.ruta[0]
        dx, dy = siguiente[0] - actual[0], siguiente[1] - actual[1]
        tiempo_hasta_siguiente = self._distancia(actual, siguiente) / VELOCIDAD
        x, y = self.colisiones.mover(
            *actual, dx, dy, min(max(0.0, segundos), tiempo_hasta_siguiente)
        )
        if math.hypot(x - actual[0], y - actual[1]) < 0.01:
            self.ruta = []
            self.error = "El trayecto se bloqueó; se volverá a calcular."
            return False
        jugador["x"], jugador["y"] = x, y
        jugador["orientacion"] = orientacion_de(dx, dy)
        if abs(dx) >= abs(dy):
            jugador["direccion"] = "derecha" if dx > 0 else "izquierda"
        else:
            jugador["direccion"] = "abajo" if dy > 0 else "arriba"
        jugador["animacion"] = "caminar"
        return self._distancia((x, y), destino) <= radio
