"""Adaptador local de la campaña cooperativa para una persona y tres bots."""
from queue import Queue
import uuid

from bots.gestor_bots import GestorBots
from .movimiento import PartidaMovimiento
from .protocolo import NOMBRES_ROLES, ROLES


class ClienteCampanaLocal:
    def __init__(self, nombre, rol_humano, dificultad="normal", apariencia=None):
        if rol_humano not in ROLES:
            raise ValueError("El rol elegido no existe.")
        jugadores = []
        for rol in ROLES:
            es_humano = rol == rol_humano
            jugadores.append({
                "id": "local" if es_humano else "bot_" + rol,
                "nombre": nombre.strip() if es_humano else self._nombre_bot(rol),
                "rol": rol, "apariencia": apariencia if es_humano else None,
            })
        self.identificador = "local"
        self.eventos = Queue(maxsize=128)
        self._partida = PartidaMovimiento(jugadores, 0)
        self._bots = GestorBots(self._partida, self.identificador, dificultad)
        self._movimiento = (0, 0)
        self._correr = False
        self._secuencia = 0
        self._ahora = 0.0
        self._revision = 0
        self._cerrado = False
        self._publicar_estado()

    @staticmethod
    def _nombre_bot(rol):
        return {
            "guardian": "Guardián",
            "mensajero": "Mateo · Mensajero",
            "habitante": "Tarek · Habitante",
            "aspirante": "Kael · Aspirante",
        }[rol]

    def mover(self, dx, dy, correr=False):
        if dx not in (-1, 0, 1) or dy not in (-1, 0, 1):
            raise ValueError("Dirección de movimiento inválida.")
        self._movimiento = (dx, dy)
        self._correr = bool(correr)

    def actuar(self, accion, **datos):
        if self._cerrado:
            return
        solicitud = {
            "accion": accion,
            "id_solicitud": uuid.uuid4().hex,
            "ronda": self._partida.mision.ronda,
            **datos,
        }
        acuse = self._partida.actuar(self.identificador, solicitud, self._ahora)
        self._encolar(acuse)

    def actualizar(self, segundos):
        if self._cerrado:
            return
        delta = max(0.0, min(float(segundos), 0.15))
        self._ahora += delta
        dx, dy = self._movimiento
        self._partida.recibir(
            self.identificador,
            {"dx": dx, "dy": dy, "seq": self._secuencia, "correr": self._correr},
            self._ahora,
        )
        self._secuencia += 1
        self._partida.actualizar(self._ahora)
        self._bots.actualizar(self._ahora, delta)
        self._publicar_estado()

    def _publicar_estado(self):
        estado_mundo = self._partida.estado(self.identificador)
        estados_bots = self._bots.estado_publico_bots()
        for jugador in estado_mundo["jugadores"]:
            detalle = estados_bots.get(jugador["id"])
            if detalle:
                jugador.update(
                    controlador="bot",
                    bot_estado=detalle["estado"],
                    bot_objetivo=(
                        detalle["objetivo"].get("nombre")
                        if detalle["objetivo"] else ""
                    ),
                    bot_confianza=detalle["confianza"],
                    bot_pruebas=detalle["pruebas"],
                    bot_error=detalle["error"],
                )
            else:
                jugador["controlador"] = "humano"
        self._revision += 1
        self._encolar({
            "tipo": "estado",
            "revision": self._revision,
            "iniciada": True,
            "fase": "partida",
            "jugadores": estado_mundo["jugadores"],
            "mundo": estado_mundo,
        })

    def _encolar(self, evento):
        if self.eventos.full():
            restantes = []
            while not self.eventos.empty():
                anterior = self.eventos.get_nowait()
                if anterior.get("tipo") != "estado":
                    restantes.append(anterior)
            for anterior in restantes[-16:]:
                self.eventos.put_nowait(anterior)
        if not self.eventos.full():
            self.eventos.put_nowait(evento)

    def cerrar(self):
        self._cerrado = True

    def serializar(self):
        return {
            "ronda": self._partida.mision.ronda,
            "fase": self._partida.mision.fase,
            "jugador": self.identificador,
            "roles": {
                jugador["rol"]: jugador["id"]
                for jugador in self._partida.jugadores.values()
            },
            "bots": self._bots.serializar(),
        }
