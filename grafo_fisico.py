"""Grafo de navegacion interna para las plataformas y puentes de la aldea."""

from collections import deque


class GrafoFisico:
    """Representa plataformas como nodos y puentes transitables como aristas."""

    DURACION_PUENTE_MS = 650
    DURACION_RESPLANDOR_MS = 900

    def __init__(self, plataformas=(), puentes=()):
        self.plataformas = {}
        self.puentes = {}
        self._adyacencia = {}
        self._propagaciones = []

        for plataforma in plataformas:
            self.agregar_plataforma(plataforma)
        for puente in puentes:
            self.agregar_puente(puente)

    def agregar_plataforma(self, plataforma):
        plataforma_id = plataforma.get("id")
        if not plataforma_id:
            raise ValueError("Cada plataforma necesita un id.")
        if plataforma_id in self.plataformas:
            raise ValueError(f"Id de plataforma duplicado: {plataforma_id}")

        posicion = plataforma.get("posicion")
        if not isinstance(posicion, (list, tuple)) or len(posicion) != 2:
            raise ValueError(f"La posicion de {plataforma_id} debe contener [x, y].")

        self.plataformas[plataforma_id] = {
            "id": plataforma_id,
            "nombre": plataforma.get("nombre", plataforma_id),
            "posicion": list(posicion),
            "vecinos": [],
        }
        self._adyacencia[plataforma_id] = []

    def agregar_puente(self, puente):
        puente_id = puente.get("id")
        origen = puente.get("origen")
        destino = puente.get("destino")
        if not puente_id:
            raise ValueError("Cada puente necesita un id.")
        if puente_id in self.puentes:
            raise ValueError(f"Id de puente duplicado: {puente_id}")
        if origen not in self.plataformas or destino not in self.plataformas:
            raise ValueError(f"El puente {puente_id} referencia una plataforma inexistente.")
        if origen == destino:
            raise ValueError(f"El puente {puente_id} no puede conectar la plataforma consigo misma.")

        registro = {
            "id": puente_id,
            "origen": origen,
            "destino": destino,
            "estado": puente.get("estado", "normal"),
            "transitable": puente.get("transitable", True),
        }
        self.puentes[puente_id] = registro
        self._adyacencia[origen].append((destino, puente_id))
        self._adyacencia[destino].append((origen, puente_id))
        self.plataformas[origen]["vecinos"].append(destino)
        self.plataformas[destino]["vecinos"].append(origen)

    def _validar_plataforma(self, plataforma_id):
        if plataforma_id not in self.plataformas:
            raise KeyError(f"Plataforma desconocida: {plataforma_id}")

    def _vecinos_transitables(self, plataforma_id):
        return [
            (vecino, puente_id)
            for vecino, puente_id in self._adyacencia[plataforma_id]
            if self.puentes[puente_id]["transitable"]
            and self.puentes[puente_id]["estado"] != "bloqueado"
        ]

    def obtener_vecinos(self, plataforma_id):
        """Devuelve los ids de las plataformas conectadas por puentes transitables."""
        self._validar_plataforma(plataforma_id)
        vecinos = []
        for vecino, _ in self._vecinos_transitables(plataforma_id):
            if vecino not in vecinos:
                vecinos.append(vecino)
        return vecinos

    def existe_camino(self, origen, destino):
        """Indica si existe una ruta transitable entre dos plataformas."""
        return self.buscar_camino(origen, destino) is not None

    def buscar_camino(self, origen, destino, algoritmo="bfs"):
        """Devuelve ids de plataforma desde origen hasta destino, o None."""
        self._validar_plataforma(origen)
        self._validar_plataforma(destino)
        if algoritmo not in ("bfs", "dfs"):
            raise ValueError("El algoritmo debe ser 'bfs' o 'dfs'.")
        if origen == destino:
            return [origen]

        pendientes = deque([origen])
        anteriores = {origen: None}
        while pendientes:
            actual = pendientes.popleft() if algoritmo == "bfs" else pendientes.pop()
            vecinos = self._vecinos_transitables(actual)
            if algoritmo == "dfs":
                vecinos = list(reversed(vecinos))
            for vecino, _ in vecinos:
                if vecino in anteriores:
                    continue
                anteriores[vecino] = actual
                if vecino == destino:
                    camino = []
                    paso = destino
                    while paso is not None:
                        camino.append(paso)
                        paso = anteriores[paso]
                    return list(reversed(camino))
                pendientes.append(vecino)
        return None

    def bfs(self, origen, destino):
        """Busca una ruta usando primero en anchura."""
        return self.buscar_camino(origen, destino, algoritmo="bfs")

    def dfs(self, origen, destino):
        """Busca una ruta usando primero en profundidad."""
        return self.buscar_camino(origen, destino, algoritmo="dfs")

    def distancia_entre_plataformas(self, origen, destino):
        """Devuelve la cantidad de puentes de la ruta mas corta, o None."""
        camino = self.bfs(origen, destino)
        return len(camino) - 1 if camino is not None else None

    def _obtener_puente(self, origen, destino):
        for vecino, puente_id in self._adyacencia[origen]:
            puente = self.puentes[puente_id]
            if vecino == destino and puente["transitable"] and puente["estado"] != "bloqueado":
                return puente_id
        return None

    def obtener_puente(self, origen, destino):
        """Devuelve el id del puente transitable que conecta dos nodos vecinos."""
        self._validar_plataforma(origen)
        self._validar_plataforma(destino)
        return self._obtener_puente(origen, destino)

    def iniciar_propagacion(
        self, origen, destino, duracion_puente_ms=None, color=(80, 220, 255),
        medio="directo", demora_ms=0,
    ):
        """Encola una señal visual que recorre los puentes de la ruta."""
        camino = self.bfs(origen, destino)
        if camino is None:
            raise ValueError(f"No existe una ruta transitable entre {origen} y {destino}.")

        puente_ids = [
            self._obtener_puente(actual, siguiente)
            for actual, siguiente in zip(camino, camino[1:])
        ]
        if any(puente_id is None for puente_id in puente_ids):
            raise RuntimeError("La ruta contiene una conexion sin puente transitable.")

        duracion = (
            self.DURACION_PUENTE_MS
            if duracion_puente_ms is None
            else duracion_puente_ms
        )
        if duracion <= 0:
            raise ValueError("La duracion de cada puente debe ser positiva.")
        if demora_ms < 0:
            raise ValueError("La demora de una propagacion no puede ser negativa.")
        propagacion = {
            "origen": origen,
            "destino": destino,
            "camino": camino,
            "puentes": puente_ids,
            "tiempo_ms": 0.0,
            "duracion_puente_ms": duracion,
            "color": tuple(color),
            "medio": medio,
            "demora_ms": demora_ms,
        }
        self._propagaciones.append(propagacion)
        return propagacion

    def actualizar_propagaciones(self, delta_ms):
        """Avanza las señales y retira sus resplandores ya terminados."""
        delta_ms = max(0.0, float(delta_ms))
        for propagacion in self._propagaciones:
            propagacion["tiempo_ms"] += delta_ms
        self._propagaciones = [
            propagacion
            for propagacion in self._propagaciones
            if propagacion["tiempo_ms"]
            <= propagacion["demora_ms"]
            + len(propagacion["puentes"]) * propagacion["duracion_puente_ms"]
            + self.DURACION_RESPLANDOR_MS
        ]

    def obtener_estado_visual_propagaciones(self):
        """Expone los puentes iluminados y el avance de cada señal activa."""
        estados = []
        for propagacion in self._propagaciones:
            puentes = propagacion["puentes"]
            tiempo_activo = propagacion["tiempo_ms"] - propagacion["demora_ms"]
            if not puentes or tiempo_activo < 0:
                continue
            duracion = propagacion["duracion_puente_ms"]
            indice_actual = min(int(tiempo_activo // duracion), len(puentes) - 1)
            avance = min(1.0, (tiempo_activo % duracion) / duracion)
            if tiempo_activo >= len(puentes) * duracion:
                indice_actual = len(puentes) - 1
                avance = 1.0
            camino = propagacion["camino"]
            estados.append({
                "puentes_iluminados": puentes[:indice_actual],
                "puente_actual": puentes[indice_actual],
                "avance": avance,
                "camino": camino,
                "origen_tramo": camino[indice_actual],
                "destino_tramo": camino[indice_actual + 1],
                "color": propagacion["color"],
                "medio": propagacion["medio"],
            })
        return estados
