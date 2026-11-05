"""Campaña cooperativa de La Copa; todo el progreso pertenece al servidor."""
from .mision import MisionPuente
import random


CASOS = (
    ("puente_norte", "¿Cerraron el puente norte?",
     "Circula que Kael cerró hoy todo el puente norte por decisión propia.", "corregir", None,
     "El puente sigue abierto hoy; mañana habrá mantenimiento parcial."),
    ("agua", "Agua bajo sospecha",
     "Un eco antiguo asegura que el agua del depósito actual está contaminada.", "descartar", {
         "guardian": ("Fecha del informe", "El documento citado corresponde a un depósito clausurado hace diez años."),
         "mensajero": ("Ruta del suministro", "La entrega actual procede del manantial nuevo, no del depósito del informe."),
         "habitante": ("Muestra comunitaria", "La muestra de hoy del manantial nuevo superó el control comunitario."),
         "aspirante": ("Acta de sustitución", "El depósito antiguo fue sustituido y desconectado de la red hace diez años."),
     }, "El aviso mezcla fechas y depósitos. Se retira ese aviso antiguo de la circulación."),
    ("tormenta", "La tormenta se acerca",
     "El consejo avisa de una tormenta esta tarde y recomienda asegurar las rutas.", "difundir", {
         "guardian": ("Boletín firmado", "El boletín de hoy está firmado por dos observadores del consejo: tormenta esta tarde."),
         "mensajero": ("Registro de señales", "Dos puestos independientes enviaron hoy la misma alerta de tormenta."),
         "habitante": ("Observación del mirador", "Los observadores registraron hoy viento y nubes compatibles con el boletín."),
         "aspirante": ("Plan preventivo", "El plan vigente confirma la alerta y pide asegurar suministros sin sembrar pánico."),
     }, "La alerta es actual y está contrastada. Difundirla permite preparar a la aldea."),
    ("ayuda", "¿Quién se quedó con la ayuda?",
     "Acusan a Mira de quedarse con todos los materiales enviados a las familias.", "corregir", {
         "guardian": ("Libro de reparto", "El libro firmado registra entregas a tres familias; dos entregas siguen pendientes."),
         "mensajero": ("Carga retenida", "Las dos entregas pendientes están en tránsito: una ruta quedó temporalmente interrumpida."),
         "habitante": ("Recibos familiares", "Tres familias confirman que recibieron materiales hoy y conservan sus recibos."),
         "aspirante": ("Inventario de Mira", "El inventario distingue entregado y pendiente. No hay materiales asignados a uso personal."),
     }, "La acusación total era falsa: hubo entregas y retrasos. Se publica el estado real del reparto."),
)

HABILIDADES = {
    "guardian": ("Contrastar archivo", "Audita tu prueba en la fuente y reduce 4 puntos de desinformación."),
    "mensajero": ("Correo urgente", "Comparte una prueba con todos los conectados desde cualquier lugar."),
    "habitante": ("Asamblea vecinal", "Reúne a otro jugador en tu fuente para recuperar 4 puntos de confianza."),
    "aspirante": ("Rendir cuentas", "Presenta dos pruebas en el caldero y recupera 4 puntos de armonía."),
}

VARIANTES = {
    "agua": ("agua", "Agua bajo sospecha", "Un aviso pide no beber del depósito hasta terminar una inspección.", "difundir", {
        "guardian": ("Informe vigente", "El informe de hoy confirma contaminación y recomienda suspender el consumo del depósito."),
        "mensajero": ("Ruta alternativa", "Dos inspectores confirmaron la alerta. Ya se distribuye agua segura por una ruta alternativa."),
        "habitante": ("Control de muestras", "Dos muestras independientes de hoy dieron resultado no apto en el depósito señalado."),
        "aspirante": ("Protocolo de cuidado", "El consejo firmó hoy el aviso preventivo y garantiza una fuente alternativa de agua potable."),
    }, "La advertencia estaba contrastada. Se difunde junto con la ubicación del agua segura."),
    "tormenta": ("tormenta", "La tormenta se acerca", "Un mensaje exige evacuar hoy por una supuesta tormenta extrema.", "descartar", {
        "guardian": ("Encabezado omitido", "El mensaje completo dice SIMULACRO. La copia eliminó ese encabezado."),
        "mensajero": ("Registro del envío", "La copia procede del ensayo de alertas; no existe un aviso real de evacuación hoy."),
        "habitante": ("Puesto del mirador", "Los dos observadores confirman condiciones estables. Participaron en un simulacro esta mañana."),
        "aspirante": ("Calendario de ejercicios", "El consejo programó hoy un ejercicio de comunicación, sin evacuación de vecinos."),
    }, "Se retira la copia descontextualizada del simulacro: no existe una orden real de evacuar."),
}

SEMANTICA_PRUEBAS = {
    "Acta del consejo": {"problema_parcial": True},
    "Registro de la ruta": {"problema_parcial": True},
    "Testimonio de Luma": {"problema_parcial": True},
    "Propuesta de Mira": {"problema_parcial": True},
    "Fecha del informe": {"antigua": True, "indica_descontextualizacion": True},
    "Ruta del suministro": {"fuente_actual_alternativa": True},
    "Muestra comunitaria": {"confirma_ausencia_de_riesgo": True},
    "Acta de sustitución": {"indica_descontextualizacion": True},
    "Informe vigente": {"confirma_riesgo_actual": True},
    "Ruta alternativa": {"confirma_riesgo_actual": True},
    "Control de muestras": {"confirma_riesgo_actual": True},
    "Protocolo de cuidado": {"confirma_riesgo_actual": True},
    "Boletín firmado": {"confirma_riesgo_actual": True},
    "Registro de señales": {"confirma_riesgo_actual": True},
    "Observación del mirador": {"confirma_riesgo_actual": True},
    "Plan preventivo": {"confirma_riesgo_actual": True},
    "Encabezado omitido": {"indica_descontextualizacion": True},
    "Registro del envío": {"indica_descontextualizacion": True},
    "Puesto del mirador": {"indica_descontextualizacion": True},
    "Calendario de ejercicios": {"indica_descontextualizacion": True},
    "Libro de reparto": {"problema_parcial": True},
    "Carga retenida": {"problema_parcial": True},
    "Recibos familiares": {"problema_parcial": True},
    "Inventario de Mira": {"problema_parcial": True},
}


class CampanaCopa(MisionPuente):
    def __init__(self, jugadores, datos_mapa):
        super().__init__(jugadores, datos_mapa)
        self.opciones = {"corregir": "Publicar una aclaración", "difundir": "Difundir el aviso", "descartar": "Retirar el aviso"}
        self.casos = tuple(random.choice((caso, VARIANTES[caso[0]])) if caso[0] in VARIANTES else caso for caso in CASOS)
        self.ronda = 0
        self.metadatos_pruebas = self._metadatos(self.pruebas)
        self.resumen = []
        self.preparados = set()
        self.materiales = set()
        self.depositos = set()
        self.habilidades_usadas = set()
        self.presion = 0.0
        self.oleadas = 0
        self.bono_equipo = False
        self.puntos = 0
        self.puntos_caso = 0

    @staticmethod
    def _metadatos(pruebas):
        return {
            rol: dict(SEMANTICA_PRUEBAS.get(prueba[0], {}))
            for rol, prueba in pruebas.items()
        }

    @property
    def fase(self):
        if not self.resultado:
            return "investigacion"
        if self.ronda == len(self.casos) - 1:
            return "final"
        return "preparacion"

    def _ejecutar(self, identificador, solicitud, ahora, presentes):
        if solicitud.get("ronda", 0) != self.ronda:
            raise ValueError("La acción pertenece a otro caso. Revisa el objetivo actual.")
        accion = solicitud.get("accion")
        if accion == "interactuar" and self.fase == "preparacion":
            objetivo = self._objetivo(identificador, solicitud.get("objetivo"))
            if objetivo.get("rol") == self.jugadores[identificador]["rol"]:
                respuesta = self._ejecutar(identificador, {**solicitud, "accion": "recoger_suministro"}, ahora, presentes)
                return {**respuesta, "vista": "introduccion"}
            if objetivo["id"] == "caldero":
                if identificador in self.materiales:
                    self.depositos.add(identificador)
                return {"mensaje": "Preparen los suministros y confirmen el próximo caso.", "vista": "introduccion"}
        if accion == "rectificar":
            respuesta = super()._ejecutar(identificador, solicitud, ahora, presentes)
            self.preparados.clear()
            return respuesta
        if accion == "habilidad":
            if self.fase != "investigacion" or identificador in self.habilidades_usadas:
                raise ValueError("Tu habilidad está disponible una vez por investigación.")
            rol = self.jugadores[identificador]["rol"]
            if "pista_" + rol not in self.conocidas[identificador]:
                raise ValueError("Primero recoge la prueba de tu fuente.")
            fuente = next(o for o in self.objetivos if o.get("rol") == rol)
            if rol == "mensajero":
                for receptor in presentes:
                    if receptor != identificador:
                        pista = "pista_mensajero"
                        if pista not in self.conocidas[receptor]:
                            self.conocidas[receptor].add(pista)
                            self.entregas.append({"emisor": identificador, "receptor": receptor, "pista": pista, "medio": "correo"})
                self._avisar(presentes, "El Mensajero entregó su prueba por correo urgente.")
            else:
                self._objetivo(identificador, "caldero" if rol == "aspirante" else fuente["id"])
                if rol == "habitante" and not any(i != identificador and self._cerca(i, self.jugadores[identificador], 80) for i in presentes):
                    raise ValueError("Invita a otro jugador a tu fuente para celebrar la asamblea.")
                if rol == "aspirante" and len(self.conocidas[identificador]) < 2:
                    raise ValueError("Necesitas dos pruebas para rendir cuentas.")
                indicador, delta = {"guardian": ("desinformacion", -4), "habitante": ("confianza", 4), "aspirante": ("armonia", 4)}[rol]
                self.indicadores[indicador] = max(0, min(100, self.indicadores[indicador] + delta))
            self.habilidades_usadas.add(identificador)
            self._registrar(self.jugadores[identificador]["nombre"] + " usó " + HABILIDADES[rol][0] + ".")
            return {"mensaje": "Habilidad completada. Se recargará en el próximo caso."}
        if accion in ("recoger_suministro", "depositar", "continuar"):
            if self.fase != "preparacion":
                raise ValueError("Esta tarea solo está disponible entre investigaciones.")
            if accion == "recoger_suministro":
                fuente = next(o for o in self.objetivos if o.get("rol") == self.jugadores[identificador]["rol"])
                self._objetivo(identificador, fuente["id"])
                self.materiales.add(identificador)
                return {"mensaje": "Recogiste suministros. Llévalos al caldero."}
            self._objetivo(identificador, "caldero")
            if accion == "depositar":
                if identificador not in self.materiales:
                    raise ValueError("Recoge primero los suministros en tu fuente.")
                self.depositos.add(identificador)
                return {"mensaje": "Suministros depositados. Se necesitan aportes de dos jugadores."}
            if len(self.depositos) < 2 or len(presentes) < 2:
                raise ValueError("Faltan suministros de dos jugadores distintos y dos conectados.")
            self.preparados.add(identificador)
            if set(presentes).issubset(self.preparados):
                self._siguiente()
                return {"mensaje": "Comienza una nueva investigación.", "vista": "introduccion"}
            return {"mensaje": "Listo para continuar. Esperando al resto del equipo."}
        if self.fase != "investigacion" and accion in ("votar",):
            raise ValueError("La investigación ya terminó.")
        respuesta = super()._ejecutar(identificador, solicitud, ahora, presentes)
        if accion == "interactuar" and respuesta.get("titulo"):
            rol = self.jugadores[identificador]["rol"]
            metadatos = self.metadatos_pruebas.get(rol)
            if metadatos:
                respuesta["metadatos"] = dict(metadatos)
        return respuesta

    def _siguiente(self):
        self.resumen.append({"caso": self.casos[self.ronda][1], **self.resultado})
        self.ronda += 1
        self.pruebas = self.casos[self.ronda][4]
        self.metadatos_pruebas = self._metadatos(self.pruebas)
        self.correcta = self.casos[self.ronda][3]
        self.conocidas = {i: set() for i in self.jugadores}
        self.halladas.clear()
        self.entregas.clear()
        self.votos.clear()
        self.resultado = None
        self.rectificacion = False
        self.preparados.clear()
        self.materiales.clear()
        self.depositos.clear()
        self.habilidades_usadas.clear()
        self.presion = 0.0
        self.oleadas = 0
        self.bono_equipo = False
        self.puntos_caso = 0
        # No borrar los acuses: una retransmisión antigua nunca afecta al nuevo caso.
        self._avisar(self.jugadores, "Nuevo caso: " + self.casos[self.ronda][1])

    def texto_resultado(self, texto, correcto):
        premio = ((80 if self.rectificacion else 100) if correcto else 0) + (20 if self.bono_equipo else 0)
        self.puntos += premio - self.puntos_caso
        self.puntos_caso = premio
        if self.ronda:
            texto = (self.casos[self.ronda][5] if correcto else
                "La decisión no coincide con las pruebas. " + ("La rectificación terminó." if self.rectificacion else "Pueden rectificar una vez o asumir las consecuencias."))
        return texto + " " + ("Campaña terminada. Revisen el balance del equipo." if self.ronda == len(self.casos) - 1 else "Ahora lleven suministros de sus fuentes al caldero y confirmen el siguiente caso.")

    def actualizar(self, segundos, presentes):
        if self.fase != "investigacion" or len(presentes) < 2:
            return
        self.presion += max(0, min(segundos, 1))
        oleadas = int(self.presion // 60)
        if oleadas > self.oleadas:
            self.oleadas = oleadas
            self.indicadores["desinformacion"] = min(100, self.indicadores["desinformacion"] + 3)
            self._avisar(presentes, "El rumor sigue circulando: +3 desinformación. Comparen las pruebas.")
        if not self.bono_equipo and all(len(self.conocidas[i]) >= 2 for i in self.jugadores):
            self.bono_equipo = True
            self.indicadores["confianza"] = min(100, self.indicadores["confianza"] + 3)
            self._avisar(presentes, "Objetivo de equipo: todos tienen dos pruebas. +3 confianza y bono al resolver.")

    def resolver(self, presentes):
        if (self.fase == "preparacion" and len(presentes) >= 2 and len(self.depositos) >= 2
                and set(presentes).issubset(self.preparados)):
            self._siguiente()
            return
        puente = self.estado_puente
        super().resolver(presentes)
        if self.ronda:
            self.estado_puente = puente

    def publico(self, presentes):
        estado = super().publico(presentes)
        caso = self.casos[self.ronda]
        estado.update(id=caso[0], titulo=f"{self.ronda + 1}/{len(self.casos)} · {caso[1]}", noticia=caso[2],
                      fase=self.fase, ronda=self.ronda, total_casos=len(self.casos),
                      suministros=len(self.depositos), preparados=len(set(presentes) & self.preparados),
                      balance=list(self.resumen) + ([{"caso": caso[1], **self.resultado}] if self.resultado else []),
                      puntos=self.puntos, bono_equipo=self.bono_equipo,
                      proxima_oleada=max(0, 60 - int(self.presion % 60)),
                      opciones=dict(self.opciones))
        return estado

    def privado(self, identificador):
        estado = super().privado(identificador)
        if not estado:
            return estado
        rol = self.jugadores[identificador]["rol"]
        estado.update(habilidad=HABILIDADES[rol][0], descripcion_habilidad=HABILIDADES[rol][1],
                      habilidad_usada=identificador in self.habilidades_usadas,
                      suministro=identificador in self.materiales, depositado=identificador in self.depositos,
                      preparado=identificador in self.preparados)
        if self.fase == "preparacion":
            estado["instruccion"] = ("En el caldero, confirma el siguiente caso." if identificador in self.depositos else
                                      "Lleva tus suministros al caldero." if identificador in self.materiales else
                                      "Vuelve a tu fuente y recoge suministros con M.")
        elif self.fase == "final":
            estado["instruccion"] = "Campaña completada. Abre M para ver el balance."
        return estado
