from .bot_cooperativo import BotCooperativo
from .memoria_bot import MemoriaEquipo
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

    def actualizar(self, ahora, segundos):
        for bot in self.bots.values():
            if (
                bot.asistencia_para
                and bot.asistencia_para not in self.memoria.solicitudes_ayuda
            ):
                bot.asistencia_a = None
                bot.asistencia_para = None
                self.memoria.liberar_tarea(bot.identificador)
        estado_publico = self.partida.mision.publico(self.partida.conectados)
        jugadores = [
            dict(jugador, conectado=identificador in self.partida.conectados)
            for identificador, jugador in self.partida.jugadores.items()
        ]
        estado_por_bot = {
            identificador: self.partida.estado(identificador)
            for identificador in self.bots
        }
        self._asignar_ayuda(estado_por_bot, jugadores)
        for identificador, bot in self.bots.items():
            estado = estado_por_bot[identificador]
            estado["caso"] = estado_publico
            bot.actualizar(ahora, segundos, estado, jugadores)

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
