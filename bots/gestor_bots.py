import math

from .bot_cooperativo import BotCooperativo
from .memoria_bot import MemoriaEquipo
from .navegador_bot import NavegadorBot
from .planificador_bot import PlanificadorBot


class GestorBots:
    def __init__(self, partida, identificador_humano, dificultad="normal"):
        """``identificador_humano``: un id (campaña local) o varios (sala en línea)."""
        if dificultad not in ("facil", "normal", "dificil"):
            raise ValueError("Dificultad de bots no válida.")
        humanos = ({identificador_humano} if isinstance(identificador_humano, str)
                   else set(identificador_humano))
        jugadores = list(partida.jugadores.values())
        roles = [jugador["rol"] for jugador in jugadores]
        if len(roles) != len(set(roles)):
            raise ValueError("No puede haber dos controladores para el mismo rol.")
        for jugador in jugadores:
            jugador["controlador"] = "humano" if jugador["id"] in humanos else "bot"
        self.memoria = MemoriaEquipo(jugadores)
        self.planificador = PlanificadorBot()
        self.bots = {
            jugador["id"]: BotCooperativo(
                jugador,
                partida,
                partida.colisiones,
                self.planificador,
                self.memoria,
                dificultad,
            )
            for jugador in jugadores
            if jugador["id"] not in humanos
        }
        self.partida = partida
        self.identificador_humano = identificador_humano
        self.dificultad = dificultad
        self._clave_caso = None

    def actualizar(self, ahora, segundos):
        caso = self.partida.mision.publico(self.partida.conectados)
        clave_caso = (caso["ronda"], caso.get("rectificacion"))
        if clave_caso != self._clave_caso:
            self._clave_caso = clave_caso
            self.memoria.nueva_ronda()  # los votos propuestos valen para un solo intento
        for bot in self.bots.values():
            if (
                bot.asistencia_para
                and bot.asistencia_para not in self.memoria.solicitudes_ayuda
            ):
                bot.asistencia_a = None
                bot.asistencia_para = None
                self.memoria.liberar_tarea(bot.identificador)
        estado_publico = caso
        jugadores = [
            dict(jugador, conectado=identificador in self.partida.conectados)
            for identificador, jugador in self.partida.jugadores.items()
        ]
        estado_por_bot = {
            identificador: self.partida.estado(identificador)
            for identificador in self.bots
        }
        self._asignar_ayuda(estado_por_bot, jugadores)
        # Una ruta nueva por actualización: si varios bots cambian de destino a
        # la vez se reparten el cálculo en cuadros seguidos y no hay tirón.
        NavegadorBot.rutas_disponibles = 1
        for identificador, bot in self.bots.items():
            estado = estado_por_bot[identificador]
            estado["caso"] = estado_publico
            bot.actualizar(ahora, segundos, estado, jugadores)
        NavegadorBot.rutas_disponibles = math.inf
        self._separar_bots(segundos)

    def _separar_bots(self, segundos):
        """Los bots en reposo dejan espacio sin empujar humanos ni atravesar paredes."""
        from multijugador.movimiento import VELOCIDAD
        dt = max(0, min(segundos, .15))
        if not dt:
            return
        puente = self.partida.mision.puente
        for indice, bot in enumerate(self.bots.values()):
            yo = bot.posicion
            if (bot.reemplaza_humano or yo.get("animacion") != "reposo"
                    or bot.identificador == puente.reparador):
                continue
            dimension = yo.get("dimension", "la_copa")
            otros = [j for i, j in self.partida.jugadores.items() if i != bot.identificador
                     and i in self.partida.conectados and j.get("dimension", "la_copa") == dimension]
            if not otros:
                continue
            def espacio(x, y):
                return min(math.hypot(x - j["x"], y - j["y"]) for j in otros)
            actual = espacio(yo["x"], yo["y"])
            separacion = 30 if dimension == "la_copa" else 14
            if actual >= separacion:
                continue
            cercano = min(otros, key=lambda j: math.hypot(yo["x"] - j["x"], yo["y"] - j["y"]))
            dx, dy = yo["x"] - cercano["x"], yo["y"] - cercano["y"]
            angulo = math.atan2(dy, dx) if dx or dy else indice * math.tau / max(1, len(self.bots))
            paso = min(20 * dt, separacion - actual)
            colisiones = self.partida.colisiones_de(dimension)
            mejor, margen = (yo["x"], yo["y"]), actual
            destino = bot.objetivo_actual
            radio = bot.radio_objetivo
            alcance = max(radio or 0, math.hypot(yo["x"] - destino["x"], yo["y"] - destino["y"])) if destino else None
            for giro in (0, 1, -1, 2, -2, 3, -3, 4):
                direccion = angulo + giro * math.pi / 4
                x, y = colisiones.mover(yo["x"], yo["y"], math.cos(direccion), math.sin(direccion), dt,
                                        factor=paso / (VELOCIDAD * dt))
                if destino and math.hypot(x - destino["x"], y - destino["y"]) > alcance + .001:
                    continue
                libre = espacio(x, y)
                if libre > margen + .001:
                    mejor, margen = (x, y), libre
            yo["x"], yo["y"] = mejor

    def _asignar_ayuda(self, estados, jugadores):
        peticiones = list(self.memoria.solicitudes_ayuda.items())
        for habitante_id, destino in peticiones:
            habitante = self.bots.get(habitante_id)
            if not habitante:
                continue
            aliado = next(
                (
                    jugador for jugador in jugadores
                    if jugador["id"] != habitante_id
                    and (jugador["x"] - habitante.posicion["x"]) ** 2
                    + (jugador["y"] - habitante.posicion["y"]) ** 2 <= 80 ** 2
                ),
                None,
            )
            if aliado:
                continue
            ayudante = next(
                (
                    bot for bot in self.bots.values()
                    if bot.identificador != habitante_id
                    and bot.prueba_propia
                    and bot.asistencia_a is None
                ),
                None,
            )
            if ayudante:
                ayudante.asistencia_a = destino
                ayudante.asistencia_para = habitante_id
                self.memoria.reservar_tarea(
                    ayudante.identificador,
                    "ayudar:" + habitante_id,
                )

    def estado_publico_bots(self):
        return {
            identificador: {
                "estado": bot.estado,
                "objetivo": bot.objetivo_actual,
                "ruta": list(bot.ruta),
                "confianza": bot.confianza_decision,
                "pruebas": sorted(bot.pruebas_conocidas),
                "error": bot.ultimo_error,
            }
            for identificador, bot in self.bots.items()
        }

    def serializar(self):
        return {
            "dificultad": self.dificultad,
            "identificador_humano": self.identificador_humano,
            "bots": {
                identificador: bot.serializar()
                for identificador, bot in self.bots.items()
            },
            "memoria": {
                "pruebas_compartidas": sorted(self.memoria.pruebas_compartidas),
                "tareas_en_progreso": dict(self.memoria.tareas_en_progreso),
            },
        }
