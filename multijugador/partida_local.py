"""Adaptador local de la campaña cooperativa para una persona y tres bots."""
from queue import Queue
import time
import uuid

from bots.gestor_bots import GestorBots
from .dimensiones_red import DIMENSIONES_RED, LA_COPA
from .movimiento import PartidaMovimiento
from .protocolo import ROLES

PRESUPUESTO_CALENTADO = .003  # segundos por cuadro para precalentar los otros mapas
# Demo rápida de la feria: La Copa y, al resolverla, el final de Ciudad Núcleo.
ESPERA_DEMO = 8.0  # segundos para ver el resultado de La Copa antes de viajar
AVISO_DEMO = "¡Resolvieron La Copa! En la Demo rápida viajamos ahora a la batalla final de Ciudad Núcleo."


class ClienteCampanaLocal:
    def __init__(self, nombre, rol_humano, dificultad="normal", semilla=None, apariencia=None, era=LA_COPA, demo=False):
        if rol_humano not in ROLES:
            raise ValueError("El rol elegido no existe.")
        if era not in DIMENSIONES_RED:
            raise ValueError("La era elegida no existe.")
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
        self._partida = PartidaMovimiento(jugadores, 0, semilla=semilla)
        if era != LA_COPA:
            # Empezar directamente en la era elegida: todo el equipo viaja junto.
            self._partida._viajar_equipo(LA_COPA, era)
        self._bots = GestorBots(self._partida, self.identificador, dificultad)
        # Memoria de colisiones: la era inicial ahora (en la barra de carga) y las demás
        # poco a poco, para que la primera ruta de cada bot no congele la partida.
        era_inicial = era
        self._calentado = self._partida.calentador(primero=era_inicial)
        for dimension, colisiones, origen in self._partida.mapas_para_calentar():
            if dimension == era_inicial:
                from logica.zonas_caminables import calentar_todo
                calentar_todo(colisiones, origen)
        self._movimiento = (0, 0)
        self._correr = False
        self._secuencia = 0
        self._ahora = 0.0
        self._revision = 0
        self._cerrado = False
        self.demo = demo
        self._demo_lista = None  # instante en que La Copa quedó resuelta (Demo rápida)
        self._publicar_estado()

    @staticmethod
    def _nombre_bot(rol):
        return {
            "guardian": "Guardián",
            "mensajero": "Mensajero",
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

    def calentar(self, presupuesto=PRESUPUESTO_CALENTADO):
        """Avanza el precalentado de los otros mapas durante ``presupuesto`` segundos."""
        if self._calentado is None:
            return
        fin = time.perf_counter() + presupuesto
        try:
            while time.perf_counter() < fin:
                next(self._calentado)
        except StopIteration:
            self._calentado = None

    def actualizar(self, segundos):
        if self._cerrado:
            return
        self.calentar()
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
        try:
            self._bots.actualizar(self._ahora, delta)
        except Exception:  # noqa: BLE001 - un fallo de los bots no debe cerrar la partida
            # Los bots no son críticos: se salta su paso y se registra (pocas veces, sin inundar).
            self._fallos_bots = getattr(self, "_fallos_bots", 0) + 1
            if self._fallos_bots <= 5:
                import traceback
                print("[Bots] Paso omitido por un error:\n" + traceback.format_exc(), flush=True)
        self._revisar_demo()
        self._publicar_estado()

    def _revisar_demo(self):
        """Demo rápida: unos segundos después de resolver La Copa, el equipo salta al final."""
        if not self.demo or self._demo_lista == "hecho" or self._partida.mision.fase != "final":
            return
        if self._demo_lista is None:
            self._demo_lista = self._ahora
            return
        if self._ahora - self._demo_lista < ESPERA_DEMO:
            return
        self._demo_lista = "hecho"
        try:
            self._partida.saltar_al_final(self.identificador, aviso=AVISO_DEMO)
        except ValueError:
            pass  # ya estaban en el final

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
