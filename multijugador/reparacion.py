"""Reparación autoritativa del Puente 1 de La Copa (sin Pygame).

La matemática del minijuego (aguja, zona verde, penalización) es la MISMA que
usa el modo de un jugador (``reparacion_puentes.SistemaReparacionPuente``),
que importa estas funciones en vez de duplicarlas.
"""
import math

CONFIGURACION = {
    "aciertos_necesarios": 3,
    "duracion_recorrido_ms": 1200,
    "angulo_objetivo": math.radians(-25),
    "tolerancia_angulo": math.radians(31),
    "rotacion_objetivo_por_acierto": math.radians(60),
    "penalizacion_por_error": 1,
    "duracion_resultado_ms": 350,
    "duracion_animacion_ms": 800,
}


def angulo_aguja(tiempo_aguja_ms, configuracion=CONFIGURACION):
    periodo = configuracion["duracion_recorrido_ms"]
    fraccion = (tiempo_aguja_ms % periodo) / periodo
    return -math.pi + fraccion * math.pi


def angulo_objetivo(progreso, configuracion=CONFIGURACION):
    return configuracion["angulo_objetivo"] - progreso * configuracion["rotacion_objetivo_por_acierto"]


def dentro_de_zona(angulo, progreso, configuracion=CONFIGURACION):
    diferencia = abs((angulo - angulo_objetivo(progreso, configuracion) + math.pi) % math.tau - math.pi)
    return diferencia <= configuracion["tolerancia_angulo"]


ESTADOS = ("DAMAGED", "MATERIALS_PENDING", "READY_TO_REPAIR", "REPAIR_MINIGAME", "REPAIR_ANIMATION", "REPAIRED")
# Puente 1 = arriba a la izquierda: une la plataforma noroeste con la central
# (misma arista que CONEXIONES_PUENTES_ALDEA del modo de un jugador).
ARISTA = ("plataforma_noroeste", "plataforma_central")
RECT_RESPALDO = (248, 234, 148, 140)


def rect_puente_1(datos_mapa, ancho=960, alto=720):
    for objeto in datos_mapa.get("decoracion", []):
        if objeto.get("name", "").replace("\\", "/").lower().endswith("puentes/puente1.png"):
            return (round(objeto["x"] * ancho), round(objeto["y"] * alto),
                    max(1, round(objeto["w"] * ancho)), max(1, round(objeto["h"] * alto)))
    return RECT_RESPALDO


def distancia_a_rect(x, y, rect):
    rx, ry, rw, rh = rect
    dx = max(rx - x, 0, x - (rx + rw))
    dy = max(ry - y, 0, y - (ry + rh))
    return math.hypot(dx, dy)


class PuenteRed:
    ID = "puente_1"

    def __init__(self, datos_mapa):
        self.rect = rect_puente_1(datos_mapa)
        self.estado = "DAMAGED"
        self.progreso = 0
        self.reparador = None
        self.inicio = 0.0
        self.ultimo_intento = -10.0
        self.ultimo_tiempo_aguja = -1.0
        self.inicio_animacion = 0.0
        self.evento = 0  # crece con cada intento; los clientes no repiten efectos
        self.ultimo = None
        self.evento_reparacion = 0

    @property
    def bloquea_paso(self):
        return self.estado != "REPAIRED"

    @property
    def reparado(self):
        return self.estado == "REPAIRED"

    def preparar(self, materiales_colocados):
        """Avanza DAMAGED/MATERIALS_PENDING/READY según el encargo del caso 1."""
        if self.estado in ("DAMAGED", "MATERIALS_PENDING", "READY_TO_REPAIR"):
            self.estado = "READY_TO_REPAIR" if materiales_colocados else "MATERIALS_PENDING"

    def cerca(self, jugador, radio=44):
        return distancia_a_rect(jugador["x"], jugador["y"], self.rect) <= radio

    def abrir(self, identificador, jugadores, ahora):
        if self.estado == "REPAIRED":
            raise ValueError("El puente ya está reparado.")
        if self.estado in ("DAMAGED", "MATERIALS_PENDING"):
            raise ValueError("Primero coloquen tablas, cuerda y canasta de herramientas en el cesto.")
        if self.estado == "REPAIR_ANIMATION":
            raise ValueError("¡El puente se está reparando!")
        if self.reparador not in (None, identificador):
            raise ValueError(jugadores[self.reparador]["nombre"] + " ya está reparando el puente.")
        if not self.cerca(jugadores[identificador]):
            raise ValueError("Acércate al Puente 1 y pulsa E.")
        if self.reparador != identificador:
            self.reparador = identificador
            self.inicio = ahora
            self.ultimo_tiempo_aguja = -1.0
        self.estado = "REPAIR_MINIGAME"
        return {"mensaje": "Pulsa E cuando la aguja entre en la zona verde.", "vista": "reparar"}

    def intentar(self, identificador, tiempo_aguja_ms, ahora):
        if self.estado != "REPAIR_MINIGAME" or self.reparador != identificador:
            raise ValueError("Abre la reparación junto al Puente 1.")
        if not isinstance(tiempo_aguja_ms, (int, float)) or isinstance(tiempo_aguja_ms, bool) or not math.isfinite(tiempo_aguja_ms):
            raise ValueError("Intento inválido.")
        # El cliente mide su aguja desde que abrió el minijuego: no puede
        # adelantarse más de 1,5 s al reloj del servidor ni volver atrás.
        if not self.ultimo_tiempo_aguja < tiempo_aguja_ms <= (ahora - self.inicio) * 1000 + 1500:
            raise ValueError("Intento fuera de tiempo. Vuelve a intentarlo.")
        if ahora - self.ultimo_intento < .25:
            raise ValueError("Espera a que la aguja vuelva a moverse.")
        self.ultimo_intento = ahora
        self.ultimo_tiempo_aguja = tiempo_aguja_ms
        self.evento += 1
        acierto = dentro_de_zona(angulo_aguja(tiempo_aguja_ms), self.progreso)
        if acierto:
            self.progreso += 1
            if self.progreso >= CONFIGURACION["aciertos_necesarios"]:
                self.estado = "REPAIR_ANIMATION"
                self.inicio_animacion = ahora
                self.reparador = None
                self.evento_reparacion = self.evento
        else:
            self.progreso = max(0, self.progreso - CONFIGURACION["penalizacion_por_error"])
        self.ultimo = {"id": self.evento, "resultado": "acierto" if acierto else "error", "jugador": identificador}
        total = CONFIGURACION["aciertos_necesarios"]
        mensaje = (f"¡Buen trabajo! {self.progreso}/{total} aciertos." if acierto else
                   "Casi. Espera la zona verde y vuelve a intentarlo.")
        if self.estado == "REPAIR_ANIMATION":
            mensaje = "¡Puente listo! La reparación está en marcha."
        return {"mensaje": mensaje, "resultado": self.ultimo["resultado"], "progreso": self.progreso}

    def cerrar(self, identificador):
        if self.reparador == identificador and self.estado == "REPAIR_MINIGAME":
            self.liberar()

    def liberar(self):
        """Libera el minijuego (p. ej., desconexión) sin perder materiales."""
        self.reparador = None
        if self.estado == "REPAIR_MINIGAME":
            self.estado = "READY_TO_REPAIR"

    def actualizar(self, ahora, presentes):
        if self.reparador is not None and self.reparador not in presentes:
            self.liberar()
        if self.estado == "REPAIR_ANIMATION" and ahora - self.inicio_animacion >= CONFIGURACION["duracion_animacion_ms"] / 1000:
            self.estado = "REPAIRED"
            return True
        return False

    def publico(self):
        return {"id": self.ID, "estado": self.estado, "progreso": self.progreso,
                "total": CONFIGURACION["aciertos_necesarios"], "reparador": self.reparador,
                "rect": list(self.rect), "ultimo": dict(self.ultimo) if self.ultimo else None,
                "evento_reparacion": self.evento_reparacion,
                "arista": {"origen": ARISTA[0], "destino": ARISTA[1], "transitable": self.reparado}}
