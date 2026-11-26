import math

from .bot_cooperativo import BotCooperativo
from .memoria_bot import MemoriaEquipo
from .navegador_bot import NavegadorBot
from .planificador_bot import PlanificadorBot

# Puerta frente a la que espera cada rol cuando nadie le pide nada (hitbox de entrada del mapa).
# En el Futuro es la misma calle que su personaje (multijugador.nucleo.NPCS).
CASAS = {
    "presente": {"guardian": "entrada_cafe_digital", "mensajero": "entrada_estacion_mensajero",
                 "habitante": "entrada_centro_comunitario", "aspirante": "entrada_sede_aspirante"},
    "futuro": {"guardian": "entrada_sede_aspirante", "mensajero": "entrada_cafe_digital",
               "habitante": "entrada_centro_comunitario", "aspirante": "entrada_campana_ronaldo"},
}
SEPARACION_CASA = 40  # su sitio frente a la casa no tapa puertas, terminales ni personajes
# Quieto y sin nada que hacer, el bot se aparta de lo que otros pueden usar.
APARTARSE_DE_OBJETOS = {"la_copa": 40, "interior": 30, "otra": 26}
ESTADOS_LIBRES = ("EN_SU_ZONA", "ESPERANDO_EQUIPO", "ESPERANDO", "ANALIZANDO_PRUEBAS", "ACOMPANANDO")


def frente_de_entrada(datos, entrada):
    """Punto de la calle delante de una entrada del mapa (None si no existe)."""
    hitbox = next((h for h in datos.get("hitboxes", []) if h.get("id") == entrada), None)
    if hitbox is None:
        return None
    if "frente_rx" in hitbox and datos.get("rect_mapa"):
        x0, y0, ancho, alto = datos["rect_mapa"]
        return x0 + hitbox["frente_rx"] * ancho, y0 + hitbox["frente_ry"] * alto
    if hitbox.get("type", "rect") == "rect":
        return (hitbox["rx"] + hitbox["rw"] / 2) * 960, (hitbox["ry"] + hitbox["rh"]) * 720 + 12
    return None


class GestorBots:
    def __init__(self, partida, identificador_humano, dificultad="normal"):
        """``identificador_humano``: un id (campaña local) o varios (sala en línea)."""
        if dificultad not in ("facil", "normal", "dificil"):
            raise ValueError("Dificultad de bots no válida.")
        humanos = ({identificador_humano} if isinstance(identificador_humano, str)
                   else set(identificador_humano))
        if not isinstance(identificador_humano, str):
            identificador_humano = humanos  # el mismo conjunto: agregar() lo actualiza
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

    def agregar(self, identificador):
        """Un bot toma el personaje de una persona que se fue (mismo id: su progreso sigue)."""
        jugador = self.partida.jugadores.get(identificador)
        if jugador is None or identificador in self.bots:
            return
        jugador["controlador"] = "bot"
        self.memoria.roles_humanos = {r: i for r, i in self.memoria.roles_humanos.items() if i != identificador}
        self.memoria.roles_bots[jugador["rol"]] = identificador
        bot = BotCooperativo(jugador, self.partida, self.partida.colisiones, self.planificador, self.memoria, self.dificultad)
        bot.reemplaza_humano = True
        self.bots[identificador] = bot
        if isinstance(self.identificador_humano, set):
            self.identificador_humano.discard(identificador)

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
        zonas_disponibles = 1  # el sitio de espera de cada bot, también de a uno por cuadro
        for identificador, bot in self.bots.items():
            estado = estado_por_bot[identificador]
            estado["caso"] = estado_publico
            if zonas_disponibles and self._zona_de_casa(bot, estado):
                zonas_disponibles -= 1
            bot.actualizar(ahora, segundos, estado, jugadores)
        NavegadorBot.rutas_disponibles = math.inf
        self._separar_bots(segundos, self._interactuables(estado_publico))

    @staticmethod
    def _interactuables(caso):
        """dimensión -> objetos que se usan con E (fuentes, ecos, cestos, terminales, pantallas)."""
        puntos = {"la_copa": caso.get("objetivos", [])}
        for dimension in CASAS:
            puntos[dimension] = (caso.get(dimension) or {}).get("objetivos", [])
        return puntos

    def _zona_de_casa(self, bot, estado):
        """En Distrito Conecta y Ciudad Núcleo cada bot espera frente a su edificio, no en el portal."""
        dimension = bot.posicion.get("dimension", "la_copa")
        if dimension not in CASAS or dimension in bot.zonas or bot.rol not in CASAS[dimension]:
            return False
        try:
            colisiones = self.partida.colisiones_de(dimension)
        except (AttributeError, OSError, ValueError):
            return
        frente = frente_de_entrada(colisiones.datos, CASAS[dimension][bot.rol])
        if frente is None:
            return
        caso = estado["caso"]
        mision = caso.get(dimension) or {}
        puntos = list(mision.get("objetivos", [])) + list((mision.get("edificios") or {}).values())
        puntos += [n for n in caso.get("npcs", []) if n.get("dimension") == dimension
                   and not n.get("jugador") and not n.get("interior")]
        puntos += [otro.zonas[dimension] for otro in self.bots.values() if otro is not bot and dimension in otro.zonas]
        portal = (estado.get("portales") or {}).get(dimension)
        if portal:
            puntos.append({"x": portal[0] + portal[2] / 2, "y": portal[1] + portal[3]})
        # Solo calles a las que se llega a pie desde la llegada del portal (como los NPC del Futuro).
        from logica.zonas_caminables import ancla, componente
        from multijugador.dimensiones_red import spawn_presente
        try:
            accesibles = componente(colisiones, colisiones.inicio_libre(*spawn_presente(colisiones.datos)))
            ocupados = [(p["x"], p["y"]) for p in puntos if "x" in p and "y" in p]
            x, y = ancla(accesibles, frente, ocupados, SEPARACION_CASA)
        except ValueError:
            return
        bot.zonas[dimension] = {"id": "zona", "x": round(x), "y": round(y), "apartada": True}
        return True

    def _separar_bots(self, segundos, interactuables=None):
        """Los bots en reposo dejan espacio sin empujar humanos ni atravesar paredes.

        Sin una acción pendiente, también se apartan de los objetos que se usan con E."""
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
                     and i in self.partida.conectados and j.get("dimension", "la_copa") == dimension
                     and j.get("interior") == yo.get("interior")]
            separacion = 34 if dimension == "la_copa" or yo.get("interior") else 20
            objetos = []
            if interactuables and not bot._accion and bot.estado in ESTADOS_LIBRES:
                destino = bot.objetivo_actual or {}
                objetos = [(o["x"], o["y"]) for o in interactuables.get(dimension, ())
                           if o.get("interior") == yo.get("interior")
                           and (o["x"], o["y"]) != (destino.get("x"), destino.get("y"))]
            if not otros and not objetos:
                continue
            clave = "la_copa" if dimension == "la_copa" else "interior" if yo.get("interior") else "otra"
            escala = separacion / APARTARSE_DE_OBJETOS[clave]  # distancia a objetos en unidades de separación
            vecinos = [(j["x"], j["y"], 1.0) for j in otros] + [(x, y, escala) for x, y in objetos]
            def espacio(x, y):
                return min(math.hypot(x - a, y - b) * k for a, b, k in vecinos)
            actual = espacio(yo["x"], yo["y"])
            if actual >= separacion:
                continue
            cercano = min(vecinos, key=lambda v: math.hypot(yo["x"] - v[0], yo["y"] - v[1]) * v[2])
            dx, dy = yo["x"] - cercano[0], yo["y"] - cercano[1]
            angulo = math.atan2(dy, dx) if dx or dy else indice * math.tau / max(1, len(self.bots))
            paso = min(20 * dt, separacion - actual)
            colisiones = self.partida.colisiones_de_jugador(yo)
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
