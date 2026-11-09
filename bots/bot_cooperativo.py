import random

from .adaptador_acciones import AdaptadorAccionesBot
from .navegador_bot import NavegadorBot


ESTADOS_BOT = (
    "ESPERANDO",
    "PLANIFICANDO",
    "YENDO_A_FUENTE",
    "INTERACTUANDO_CON_FUENTE",
    "RECOGIENDO_PRUEBA",
    "COMPARTIENDO_PRUEBA",
    "BUSCANDO_ALIADO",
    "YENDO_AL_CALDERO",
    "USANDO_HABILIDAD",
    "ANALIZANDO_PRUEBAS",
    "VOTANDO",
    "RECTIFICANDO",
    "YENDO_POR_SUMINISTRO",
    "TRANSPORTANDO_SUMINISTRO",
    "DEPOSITANDO_SUMINISTRO",
    "CONFIRMANDO_CONTINUACION",
    "ENTREGANDO_SUMINISTRO",
    "SUJETANDO",
    "TRABAJANDO",
    "REPARANDO_PUENTE",
    "ACOMPANANDO",
    "ESPERANDO_EQUIPO",
    "PAUSADO_POR_EVENTO",
    "REEMPLAZADO_POR_HUMANO",
)

DEMORAS_MS = {
    "interactuar": (800, 1200),
    "entregar": (500, 800),
    "habilidad": (600, 900),
    "votar": (900, 1400),
    "continuar": (400, 650),
    "sujetar": (300, 500),
    "trabajar": (700, 950),  # el servidor exige 0,6 s entre pasos
    "rectificar": (700, 1000),
    "presente_analizar": (900, 1400),
    "presente_marcar": (2500, 4000),  # tiempo de mirar el material antes de señalar
    "futuro_resolver": (2500, 4000),
}


class BotCooperativo:
    def __init__(self, jugador, partida, navegador, planificador, memoria, dificultad):
        self.identificador = jugador["id"]
        self.rol = jugador["rol"]
        self.nombre = jugador["nombre"]
        self.dimension = "la_copa"
        self.interior = None
        self.estado = "ESPERANDO"
        self.objetivo_actual = None
        self.posicion = partida.jugadores[self.identificador]
        self.ruta = []
        self.prueba_propia = None
        self.pruebas_conocidas = set()
        self.habilidad_usada = False
        self.suministro_recogido = False
        self.suministro_depositado = False
        self.ahora = 0.0
        self.marca_planeada = None  # lo que va a señalar en un análisis del Presente
        self.inicio_reparacion = None  # reloj local al abrir el minijuego del puente
        self.ultimo_tiempo_aguja = -1.0
        self.voto_propuesto = None
        self.confianza_decision = 0.0
        self.tiempo_espera = 0.0
        self.ultimo_error = ""
        self.reintentos = 0
        self.reemplaza_humano = False
        self.asistencia_a = None
        self.asistencia_para = None
        self.compartidas = {}
        # Órdenes recibidas por los Troncos de los Ecos (ver PlanificadorBot).
        self.orden = None
        self.sin_difundir = False
        self.convocado = False  # debe volver al caldero a elegir cuando pueda
        self.espera_ayuda_desde = None
        self.sin_ayuda = False  # dejó de esperar compañero para su habilidad
        self._ultimo_aviso = 0
        self._ronda = -1
        self._accion = None
        self._datos_accion = {}
        self._tiempo_accion = 0.0
        self._planificador = planificador
        self._memoria = memoria
        self._adaptador = AdaptadorAccionesBot(partida, self.identificador)
        self._navegador = NavegadorBot(navegador)
        self._random = random.Random("LaCopa:" + self.identificador)
        self._dificultad = dificultad

    def actualizar(self, ahora, segundos, estado_partida, jugadores):
        if self.reemplaza_humano:
            self.estado = "REEMPLAZADO_POR_HUMANO"
            self.posicion["animacion"] = "reposo"
            return
        self.ahora = ahora
        lugar = (self.posicion.get("dimension", "la_copa"), self.posicion.get("interior"))
        if lugar != (self.dimension, self.interior):
            # Cambió de mapa o de edificio: lo que hacía en el anterior terminó.
            self.dimension, self.interior = lugar
            self._accion = None
            self._datos_accion = {}
            self._tiempo_accion = 0
            self.inicio_reparacion = None
            self._navegador.destino = None
            self._navegador.ruta = []
            try:
                self._navegador.colisiones = self._adaptador.partida.colisiones_de_jugador(self.posicion)
            except (AttributeError, OSError, ValueError) as error:
                self.ultimo_error = str(error)
        caso = estado_partida["caso"]
        if caso["ronda"] != self._ronda:
            self._ronda = caso["ronda"]
            self.compartidas.pop(self._ronda, None)
            self.orden = None
            self.sin_difundir = self.convocado = self.sin_ayuda = False
            self.espera_ayuda_desde = None
            self._accion = None
            self._datos_accion = {}
            self._tiempo_accion = 0
            self._navegador.destino = None
        self._sincronizar_estado(estado_partida["privado"])
        self._leer_ecos(estado_partida["privado"])

        plan = self._planificador.planificar(
            self, estado_partida, jugadores, self._memoria, self._dificultad
        )
        self.estado = plan["estado"]
        destino = plan.get("destino")
        if plan.get("accion") != self._accion or plan.get("datos", {}) != self._datos_accion:
            self._accion = plan.get("accion")
            self._datos_accion = dict(plan.get("datos", {}))
            self._tiempo_accion = self._demora(self._accion) if self._accion else 0
            self._navegador.destino = None
        if destino:
            self.objetivo_actual = destino
            llegado = self._navegador.avanzar(
                self.posicion,
                (destino["x"], destino["y"]),
                segundos,
                plan.get("radio"),
            )
            self.ruta = list(self._navegador.ruta)
            if not llegado:
                if self._navegador.error:
                    self.ultimo_error = self._navegador.error
                return
        else:
            self.objetivo_actual = None
            self.posicion["animacion"] = "reposo"
            if not self._accion:
                return

        if plan.get("esperar"):
            return
        if self._tiempo_accion > 0:
            self._tiempo_accion = max(0.0, self._tiempo_accion - max(0, segundos) * 1000)
            if self._tiempo_accion > 0:
                return

        acuse = self._adaptador.solicitar(
            self._accion,
            ahora,
            **self._datos_accion,
        )
        if not acuse.get("ok"):
            self.ultimo_error = acuse.get("mensaje", "La acción fue rechazada.")
            self.reintentos += 1
            self._tiempo_accion = 1000
            if self.rol == "habitante" and self._accion == "habilidad":
                self._memoria.solicitar_ayuda(
                    self.identificador,
                    plan.get("destino", self.objetivo_actual or {}),
                )
                self._accion = None
            return

        self.ultimo_error = ""
        self.reintentos = 0
        if self._accion in ("presente_marcar", "futuro_resolver"):
            self.marca_planeada = None
        if self._accion == "hablar_npc" and acuse.get("dialogo"):
            # Los bots no tienen ventana: escuchan y dan la primera respuesta útil.
            self._adaptador.solicitar("responder_npc", ahora, npc=acuse["dialogo"]["npc"],
                                      respuesta=acuse["dialogo"]["respuestas"][0])
        if plan.get("marca_compartida"):
            self.compartidas.setdefault(self._ronda, set()).add(plan["marca_compartida"])
        if plan.get("marca_voto"):
            self.voto_propuesto = plan["marca_voto"]
        if self._accion == "habilidad":
            self.habilidad_usada = True
            if self.rol == "mensajero":
                self.compartidas.setdefault(self._ronda, set()).update(
                    jugador["id"]
                    for jugador in jugadores
                    if jugador["id"] != self.identificador
                )
            if self.rol == "habitante":
                self._memoria.completar_ayuda(self.identificador)
        self._sincronizar_estado(self._adaptador.estado()["privado"])
        self._accion = None
        self._datos_accion = {}
        self.posicion["animacion"] = "reposo"

    def _leer_ecos(self, privado):
        """El último mensaje recibido manda sobre lo que el bot estuviera haciendo."""
        for aviso in privado.get("avisos", []):
            if aviso["id"] <= self._ultimo_aviso:
                continue
            self._ultimo_aviso = aviso["id"]
            orden = aviso.get("orden")
            if orden == "no_difundir":
                self.sin_difundir = True
            elif orden and aviso.get("emisor") != self.identificador:
                self.orden = {"tipo": orden, "emisor": aviso.get("emisor"), "llegada": None}

    def _sincronizar_estado(self, privado):
        inventario = privado.get("inventario", [])
        self.pruebas_conocidas = {prueba["id"] for prueba in inventario}
        self.prueba_propia = (
            "pista_" + self.rol
            if "pista_" + self.rol in self.pruebas_conocidas
            else None
        )
        self.habilidad_usada = privado.get("habilidad_usada", False)
        self.suministro_recogido = privado.get("suministro", False)
        self.suministro_depositado = privado.get("depositado", False)

    def _demora(self, accion):
        if accion not in DEMORAS_MS:
            return 0
        minimo, maximo = DEMORAS_MS[accion]
        if self._dificultad == "facil":
            minimo, maximo = minimo // 2, maximo // 2
        elif self._dificultad == "dificil":
            minimo, maximo = round(minimo * 1.35), round(maximo * 1.35)
        return self._random.uniform(minimo, maximo)

    def serializar(self):
        return {
            "identificador": self.identificador,
            "rol": self.rol,
            "estado": self.estado,
            "objetivo": self.objetivo_actual.get("id") if self.objetivo_actual else None,
            "posicion": [self.posicion["x"], self.posicion["y"]],
            "ruta": [list(p) for p in self.ruta],
            "pruebas": sorted(self.pruebas_conocidas),
            "habilidad_usada": self.habilidad_usada,
            "suministro_recogido": self.suministro_recogido,
            "suministro_depositado": self.suministro_depositado,
            "voto": self.voto_propuesto,
            "confianza": self.confianza_decision,
            "reemplaza_humano": self.reemplaza_humano,
        }
