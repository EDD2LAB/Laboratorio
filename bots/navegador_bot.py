import heapq
import math

from multijugador.movimiento import VELOCIDAD, orientacion_de


class NavegadorBot:
    PASO = 8
    RADIO_INTERACCION = 68
    rutas_disponibles = math.inf  # GestorBots lo limita mientras actualiza

    def __init__(self, colisiones):
        self.colisiones = colisiones
        self.ruta = []
        self.destino = None
        self.error = ""
        self._reintento_ms = 0.0
        self._salida_bloqueo = None

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
        centro = self._celda(origen)
        objetivo = tuple(map(float, destino))
        # La celda redondeada puede caer dentro de una pared. Conectar solo
        # puntos de la cuadrícula alcanzables desde la posición real.
        inicios = [(centro[0] + dx, centro[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
        inicios = [c for c in inicios if not self.colisiones.bloqueado(*self._posicion(c))
                   and self.colisiones.trayecto_libre(origen, self._posicion(c))]
        costo = {c: self._distancia(origen, self._posicion(c)) / self.PASO for c in inicios}
        pendientes = [(valor + max(0, self._distancia(self._posicion(c), objetivo) - radio) / self.PASO, c)
                      for c, valor in costo.items()]
        heapq.heapify(pendientes)
        anterior = {c: None for c in inicios}
        encontrado = None
        enlace_final = False
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
            if (radio < self.PASO and self._distancia(posicion, objetivo) <= self.PASO
                    and not self.colisiones.bloqueado(*objetivo)
                    and self.colisiones.trayecto_libre(posicion, objetivo)):
                encontrado, enlace_final = actual, True
                break
            for dx, dy, paso in movimientos:
                vecino = actual[0] + dx, actual[1] + dy
                px, py = self._posicion(vecino)
                if self.colisiones.bloqueado(px, py):
                    continue
                if not self.colisiones.trayecto_libre(posicion, (px, py)):
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
        self.ruta = list(reversed(camino))
        if enlace_final:
            self.ruta.append(objetivo)
        self.destino = objetivo
        self.error = ""
        self._reintento_ms = 0
        return list(self.ruta)

    def avanzar(self, jugador, destino, segundos, radio=None):
        radio = self.RADIO_INTERACCION if radio is None else radio
        actual = (jugador["x"], jugador["y"])
        self._reintento_ms = max(0.0, self._reintento_ms - max(0, segundos) * 1000)
        if self.colisiones.bloqueado(*actual):
            salida = self._salida_bloqueo
            if salida is None or self.colisiones.bloqueado(*salida):
                salida = self.colisiones.salida_bloqueo(*actual)
            self._salida_bloqueo = salida
            self.ruta, self.destino = [], None
            if salida is None:
                self.error = "El bot espera una salida transitable."
                jugador["animacion"] = "reposo"
                return False
            self.error = ""
            self._mover_hacia(jugador, salida, segundos)
            return False
        self._salida_bloqueo = None
        if self._distancia(actual, destino) <= radio:
            self.ruta = []
            jugador["animacion"] = "reposo"
            return True
        if self.destino != tuple(map(float, destino)):
            self.destino = None
            self.ruta = []
            self.error = ""
        if self.error and self._reintento_ms:
            return False
        if self.destino is None or not self.ruta:
            if NavegadorBot.rutas_disponibles <= 0:
                return False  # le toca calcular en el próximo cuadro
            NavegadorBot.rutas_disponibles -= 1
            radio_ruta = max(0, radio - self.PASO)
            if self.buscar_ruta(actual, destino, radio_ruta) is None:
                return False
        restante = max(0.0, min(segundos, .15))
        while self.ruta and restante > 1e-8:
            actual = jugador["x"], jugador["y"]
            if self._distancia(actual, destino) <= radio:
                return True
            if self._distancia(actual, self.ruta[0]) <= 1e-5:
                self.ruta.pop(0)
                continue
            siguiente = self.ruta[0]
            dt = min(restante, self._distancia(actual, siguiente) / (VELOCIDAD * self.colisiones.factor_velocidad))
            if not self._mover_hacia(jugador, siguiente, dt):
                return False
            restante -= dt
        return self._distancia((jugador["x"], jugador["y"]), destino) <= radio

    def _mover_hacia(self, jugador, siguiente, segundos):
        actual = jugador["x"], jugador["y"]
        dx, dy = siguiente[0] - actual[0], siguiente[1] - actual[1]
        distancia = self._distancia(actual, siguiente)
        if distancia < 1e-8:
            jugador["animacion"] = "reposo"
            return True
        tiempo_hasta_siguiente = distancia / (VELOCIDAD * self.colisiones.factor_velocidad)
        x, y = self.colisiones.mover(
            *actual, dx / distancia, dy / distancia, min(max(0.0, segundos), tiempo_hasta_siguiente)
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
        return True
