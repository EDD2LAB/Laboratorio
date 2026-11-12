"""Campaña cooperativa de La Copa; todo el progreso pertenece al servidor."""
from .mision import MisionPuente
from logica.sorteo_partida import SorteoPartida
from .expediente import ExpedientePartida, campos_legales, ficha_resuelta
from .suministros import EncargoSuministros
from .guia import GuiaCooperativa
from . import clasificacion
from .dialogos import DialogosNPC
from .presentacion import aplicar_efectos, tipo_pocion
from .reparacion import PuenteRed
from copy import deepcopy


CASOS = (
    ("puente_norte", "¿Quién rompió el puente norte?",
     "Alguien dice que Kael rompió el puente por descuido y por eso lo cerraron. ¿Será verdad?", "corregir", None,
     "El puente se dañó por el desgaste y la lluvia, no por Kael. Sigue abierto hoy; mañana habrá mantenimiento parcial."),
    ("agua", "Agua bajo sospecha",
     "Un mensaje viejo dice que el agua de hoy está sucia. ¿Habla del mismo lugar?", "descartar", {
         "guardian": ("Fecha del informe", "El documento citado corresponde a un depósito clausurado hace diez años."),
         "mensajero": ("Ruta del suministro", "La entrega actual procede del manantial nuevo, no del depósito del informe."),
         "habitante": ("Muestra comunitaria", "La muestra de hoy del manantial nuevo superó el control comunitario."),
         "aspirante": ("Acta de sustitución", "El depósito antiguo fue sustituido y desconectado de la red hace diez años."),
     }, "El aviso mezcla fechas y depósitos. Se retira ese aviso antiguo de la circulación."),
    ("tormenta", "La tormenta se acerca",
     "El consejo avisa: esta tarde habrá tormenta. ¿Debemos avisar a los vecinos?", "difundir", {
         "guardian": ("Boletín firmado", "El boletín de hoy está firmado por dos observadores del consejo: tormenta esta tarde."),
         "mensajero": ("Registro de señales", "Dos puestos independientes enviaron hoy la misma alerta de tormenta."),
         "habitante": ("Observación del mirador", "Los observadores registraron hoy viento y nubes compatibles con el boletín."),
         "aspirante": ("Plan preventivo", "El plan vigente confirma la alerta y pide asegurar suministros sin sembrar pánico."),
     }, "La alerta es actual y está contrastada. Difundirla permite preparar a la aldea."),
    ("ayuda", "¿Quién se quedó con la ayuda?",
     "Dicen que Mira guardó para ella toda la ayuda. ¿Qué pasó con las entregas?", "corregir", {
         "guardian": ("Libro de reparto", "El libro firmado registra entregas a tres familias; dos entregas siguen pendientes."),
         "mensajero": ("Carga retenida", "Las dos entregas pendientes están en tránsito: una ruta quedó temporalmente interrumpida."),
         "habitante": ("Recibos familiares", "Tres familias confirman que recibieron materiales hoy y conservan sus recibos."),
         "aspirante": ("Inventario de Mira", "El inventario distingue entregado y pendiente. No hay materiales asignados a uso personal."),
     }, "La acusación total era falsa: hubo entregas y retrasos. Se publica el estado real del reparto."),
)

HABILIDADES = {
    "guardian": ("Revisar mi pista", "Vuelve a Naira y revisa tu pista para reducir los rumores."),
    "mensajero": ("Correo urgente", "Manda tu pista a todos tus compañeros."),
    "habitante": ("Reunir a los vecinos", "Ve con un compañero a ver a Luma. La aldea confiará más en ustedes."),
    "aspirante": ("Explicar con pistas", "Lleva dos pistas al caldero. Ayudarás a que la aldea se lleve mejor."),
}

VARIANTES = {
    "agua": ("agua", "Agua bajo sospecha", "Un aviso dice: no beban esa agua, usen el manantial seguro. ¿Es un aviso de hoy?", "difundir", {
        "guardian": ("Informe vigente", "El informe de hoy confirma contaminación y recomienda suspender el consumo del depósito."),
        "mensajero": ("Ruta alternativa", "Dos inspectores confirmaron la alerta. Ya se distribuye agua segura por una ruta alternativa."),
        "habitante": ("Control de muestras", "Dos muestras independientes de hoy dieron resultado no apto en el depósito señalado."),
        "aspirante": ("Protocolo de cuidado", "El consejo firmó hoy el aviso preventivo y garantiza una fuente alternativa de agua potable."),
    }, "La advertencia estaba contrastada. Se difunde junto con la ubicación del agua segura."),
    "tormenta": ("tormenta", "La tormenta se acerca", "Un mensaje dice: ¡salgan de sus casas, viene una gran tormenta! ¿Es un aviso real?", "descartar", {
        "guardian": ("Encabezado omitido", "El mensaje completo dice SIMULACRO. La copia eliminó ese encabezado."),
        "mensajero": ("Registro del envío", "La copia procede del ensayo de alertas; no existe un aviso real de evacuación hoy."),
        "habitante": ("Puesto del mirador", "Los dos observadores confirman condiciones estables. Participaron en un simulacro esta mañana."),
        "aspirante": ("Calendario de ejercicios", "El consejo programó hoy un ejercicio de comunicación, sin evacuación de vecinos."),
    }, "Se retira la copia descontextualizada del simulacro: no existe una orden real de evacuar."),
}

AVISOS_RECIENTES = {
    "agua": "El punto de reparto de agua segura está atendido para recibir consultas.",
    "tormenta": "El puesto del mirador está atendido para confirmar los avisos.",
    "ayuda": "El equipo de reparto recibe consultas sobre las entregas pendientes.",
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
    "Inventario del reparto": {"problema_parcial": True},
}


DECISION_CORTA = {"verificar": "Verificar", "reportar": "Reportar", "dejar_pendiente": "Ignorar", "compartir": "Publicar",
                  "corregir": "Corregir", "difundir": "Difundir", "descartar": "Descartar"}
ACCIONES_ANALISIS = ("presente_analizar", "presente_marcar", "presente_siguiente")


class CampanaCopa(MisionPuente):
    def __init__(self, jugadores, datos_mapa, semilla=None):
        super().__init__(jugadores, datos_mapa)
        self.opciones = {"corregir": "Corregir las partes equivocadas", "difundir": "Compartirlo: las pistas lo confirman", "descartar": "No compartirlo: es un aviso falso"}
        self.sorteo = SorteoPartida(semilla)
        self.casos = self.sorteo.casos(CASOS, VARIANTES)
        self.expediente = ExpedientePartida()
        self.avisos_recientes = {i: {} for i in jugadores}
        self.dialogos = DialogosNPC(self, datos_mapa)
        from .exploracion import ExploracionInteriores
        self.exploracion = ExploracionInteriores()
        self.ronda = 0
        self.metadatos_pruebas = self._metadatos(self.pruebas)
        self.resumen = []
        self.preparados = set()
        self.encargo = EncargoSuministros(0, self.objetivos)
        self.obras = []
        self.materiales = self.encargo.cargas
        self.depositos = set()
        self.habilidades_usadas = set()
        self.presion = 0.0
        self.oleadas = 0
        self.bono_equipo = False
        self.puntos = 0
        self.puntos_caso = 0
        self.acompanante = GuiaCooperativa(jugadores)
        self.reloj = 0.0
        self.presentes = set(jugadores)
        # Puente 1 (arriba a la izquierda) roto desde el inicio de la partida.
        self.puente = PuenteRed(datos_mapa)
        self.objetivos.append(self._objetivo_puente(datos_mapa))
        self.clasificaciones = {}
        # Ganchos que instala PartidaMovimiento (portal y Distrito Conecta).
        self.viajar = None
        self.cancelar_viaje = None
        self.presente = None
        self.presentes_presente = set()
        self.futuro = None
        self.presentes_futuro = set()

    def _objetivo_puente(self, datos_mapa):
        from .movimiento import ColisionesMapa
        colisiones = ColisionesMapa(datos_mapa)
        colisiones.bloqueos = [self.puente.rect]
        x, y, w, h = self.puente.rect
        # Extremo inferior derecho: el lado de la plataforma central.
        px, py = colisiones.inicio_libre(x + w + 6, y + h + 4)
        return {"id": PuenteRed.ID, "nombre": "Puente 1 · reparar", "tipo": "puente", "x": round(px), "y": round(py)}

    @property
    def objetivo_puente(self):
        return next(o for o in self.objetivos if o["id"] == PuenteRed.ID)

    def _cerca_presente(self, jugador, objetivo, radio=68):
        import math
        return (jugador.get("dimension") == objetivo["dimension"] and jugador.get("interior") == objetivo.get("interior")
                and math.hypot(jugador["x"] - objetivo["x"], jugador["y"] - objetivo["y"]) <= radio)

    def _ejecutar_presente(self, identificador, solicitud):
        accion = solicitud.get("accion")
        jugador = self.jugadores[identificador]
        en_futuro = jugador.get("dimension") == "futuro"
        if accion == "futuro_resolver" or (accion == "interactuar" and solicitud.get("objetivo", "").startswith("futuro:")):
            en_futuro = True
        if accion == "habilidad":
            return self.futuro.habilidad(identificador, jugador, self._cerca_presente)
        mision, presentes = (self.futuro, self.presentes_futuro) if en_futuro else (self.presente, self.presentes_presente)
        if mision is None:
            raise ValueError("Esa dimensión no está disponible.")
        if accion == "interactuar":
            return mision.interactuar(identificador, jugador, solicitud.get("objetivo"), self._cerca_presente)
        if accion == "futuro_resolver":
            return mision.resolver_tarea(identificador, jugador, solicitud, self._cerca_presente)
        if accion == "presente_votar":
            return mision.votar(identificador, jugador, solicitud.get("opcion"), presentes, self._cerca_presente)
        if accion == "presente_clasificar":
            return mision.clasificar(identificador, solicitud.get("categoria"))
        if accion in ACCIONES_ANALISIS and jugador.get("dimension") != "presente":
            raise ValueError("Esa acción es de Distrito Conecta.")
        if accion == "presente_analizar":
            return self.presente.analizar(identificador)
        if accion == "presente_marcar":
            return self.presente.marcar(identificador, solicitud)
        if accion == "presente_siguiente":
            return self.presente.siguiente(identificador, self.presentes_presente)
        raise ValueError("Acción desconocida.")

    def informe(self):
        """Datos del informe final: los casos de las tres eras, resueltos o no."""
        from .nucleo import CASO, OPCIONES as OPCIONES_NUCLEO, TITULO
        from .presente import EVENTOS, OPCIONES as OPCIONES_PRESENTE
        guardados = {c.id: c for c in list(self.expediente.arbol.casos.values()) + self.expediente.pendientes}
        definidos = [(c[0], c[1], "La Copa", self.opciones) for c in self.casos]
        definidos += [(e["id"], e["titulo"], "Distrito Conecta", OPCIONES_PRESENTE) for e in EVENTOS]
        definidos.append((CASO, TITULO, "Ciudad Núcleo", OPCIONES_NUCLEO))
        filas = []
        for identificador, titulo, era, opciones in definidos:
            ficha, caso = ficha_resuelta(identificador), guardados.get(identificador)
            datos = caso.datos if caso else {}
            resultado = datos.get("resultado", {})
            filas.append({"id": identificador, "titulo": titulo, "era": era, "tipo": datos.get("tipo", ficha["tipo"]), "gravedad": caso.gravedad if caso else ficha["gravedad"],
                          "resuelto": caso is not None, "orden": caso.orden if caso else len(guardados) + len(filas),
                          "decision": opciones.get(resultado.get("opcion"), resultado.get("opcion")),
                          "decision_corta": DECISION_CORTA.get(resultado.get("opcion")),
                          "correcto": bool(resultado.get("correcto")), "norma": datos.get("ley"), "pena": datos.get("sancion")})
        filas.sort(key=lambda f: (f["gravedad"], f["orden"]))
        arbol = self.expediente.arbol.publico()
        return {"casos": filas, "raiz": arbol["raiz"], "total_arbol": arbol["total"],
                "inorden": [c.id for c in self.expediente.arbol.inorden()]}

    def _clasificar(self, identificador, opcion):
        if not self.resultado:
            raise ValueError("Primero decidan qué contar a la aldea.")
        if identificador in self.clasificaciones:
            raise ValueError("Ya clasificaste este evento.")
        evento = self.casos[self.ronda][0]
        correcta = clasificacion.evaluar(evento, opcion, "la_copa")
        # Misma regla que el modo de un jugador: la trivia vale ±5 de sabiduría.
        efectos = {"sabiduria": 5 if correcta else -5}
        aplicar_efectos(self.indicadores, efectos)
        self.clasificaciones[identificador] = {"opcion": opcion, "correcta": correcta, "efectos": efectos,
                                               "categoria": clasificacion.ruta_evento(evento)}
        return {"mensaje": "¡Clasificación correcta!" if correcta else "Esa no era la categoría.",
                "vista": "clasificacion_resultado"}

    def _reparar(self, identificador, solicitud):
        accion = solicitud.get("accion")
        if accion == "cerrar_reparacion":
            self.puente.cerrar(identificador)
            return {"mensaje": "Puedes volver a intentarlo cuando quieras."}
        if accion == "intento_reparacion":
            return self.puente.intentar(identificador, solicitud.get("tiempo_aguja_ms"), self.reloj)
        self._objetivo(identificador, PuenteRed.ID)
        if self.puente.reparado:
            return {"mensaje": "El Puente 1 ya está reparado. ¡La ruta está abierta!"}
        if self.ronda or self.fase != "preparacion":
            return {"mensaje": "El Puente 1 está roto. Lo repararán después de resolver el primer caso.",
                    "titulo": "Puente 1", "vista": "fuente"}
        return self.puente.abrir(identificador, self.jugadores, self.reloj)

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
        accion = solicitud.get("accion")
        if accion == "expediente_paso":
            if identificador not in presentes:
                raise ValueError("Debes estar conectado para ordenar un caso.")
            return self.expediente.paso_insercion(solicitud)
        # El portal y Distrito Conecta no pertenecen a un caso de La Copa.
        if accion == "usar_portal":
            if self.viajar is None:
                raise ValueError("El portal no está disponible.")
            return self.viajar(identificador, solicitud.get("destino"))
        if accion == "cancelar_portal":
            if self.cancelar_viaje is None:
                raise ValueError("El portal no está disponible.")
            return self.cancelar_viaje(identificador)
        if accion == "pedir_informe":
            return {"mensaje": "", "vista": "informe", "informe": self.informe()}
        if accion == "entrar_edificio":
            return self.entrar_edificio(identificador, solicitud.get("edificio"))
        if accion == "salir_edificio":
            return self.salir_edificio(identificador)
        if accion == "explorar_sector":
            return self.exploracion.inspeccionar(identificador, solicitud.get("objetivo"),
                                                 self.jugadores, self._cerca_presente)
        if accion in ("hablar_npc", "responder_npc"):
            return self.dialogos.ejecutar(identificador, solicitud)
        objetivo_pedido = solicitud.get("objetivo")
        if accion == "habilidad" and self.jugadores[identificador].get("dimension") == "futuro":
            return self._ejecutar_presente(identificador, solicitud)
        if accion in ("presente_votar", "presente_clasificar", "futuro_resolver") + ACCIONES_ANALISIS or (
                accion == "interactuar" and isinstance(objetivo_pedido, str) and objetivo_pedido.startswith(("presente:", "futuro:"))):
            return self._ejecutar_presente(identificador, solicitud)
        if solicitud.get("ronda", 0) != self.ronda:
            raise ValueError("La acción pertenece a otro caso. Revisa el objetivo actual.")
        accion = solicitud.get("accion")
        self.presentes = set(presentes)
        if accion in ("iniciar_tutorial", "saltar_tutorial") or (accion == "interactuar" and self.fase == "investigacion"):
            respuesta = self.acompanante.tutorial(self, identificador, solicitud)
            if respuesta is not None:
                return respuesta
        if accion in ("intento_reparacion", "cerrar_reparacion") or (accion == "interactuar" and objetivo_pedido == PuenteRed.ID):
            return self._reparar(identificador, solicitud)
        if accion == "clasificar":
            return self._clasificar(identificador, solicitud.get("categoria"))
        if accion == "pedir_pista":
            return self.acompanante.pedir(self, identificador, self.reloj, presentes)
        if accion in ("sujetar", "trabajar"):
            if self.fase != "preparacion":
                raise ValueError("Ahora sigue la tarea que aparece en el mapa.")
            mensaje = self.encargo.actividad(identificador, accion, self.reloj, presentes, self.jugadores)
            self._premiar_encargo(presentes)
            return {"mensaje": mensaje, "vista": "actividad"}
        if accion == "interactuar" and self.fase == "preparacion":
            objetivo = self._objetivo(identificador, solicitud.get("objetivo"))
            if objetivo["id"] == self.encargo.destino["id"]:
                if identificador in self.encargo.cargas:
                    return self._ejecutar(identificador, {**solicitud, "accion": "depositar"}, ahora, presentes)
                if self.encargo.materiales_listos and not self.encargo.materiales_colocados:
                    return {"mensaje": "Uno ayuda y el otro hace la tarea. ¡Pueden turnarse!", "vista": "actividad"}
                if self.encargo.materiales_colocados and not self.encargo.completo:
                    return {"mensaje": "¡Materiales colocados! Ahora vayan al Puente 1 y pulsen E para repararlo.", "vista": "introduccion"}
                return {"mensaje": self.encargo.config["motivo"], "vista": "introduccion"}
            if any(m[2] == objetivo["id"] for m in self.encargo.config["materiales"]):
                return self._ejecutar(identificador, {**solicitud, "accion": "recoger_suministro", "objetivo": objetivo["id"]}, ahora, presentes)
            if objetivo["id"] == "caldero":
                return {"mensaje": "Revisen el encargo y confirmen aquí el próximo caso cuando esté completo.", "vista": "introduccion"}
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
                clave = solicitud.get("objetivo")
                if clave is None:
                    fuente = self.encargo.objetivo(identificador, presentes)
                    clave = fuente["id"]
                self._objetivo(identificador, clave)
                mensaje = self.encargo.recoger(identificador, clave, solicitud.get("material"))
                return {"mensaje": mensaje, "vista": "introduccion"}
            if accion == "depositar":
                self._objetivo(identificador, self.encargo.destino["id"])
                mensaje = self.encargo.entregar(identificador)
                self.depositos = set(self.encargo.entregados.values())
                self._premiar_encargo(presentes)
                return {"mensaje": mensaje + (" Encargo completo: " + self.encargo.config["efecto"] if self.encargo.completo else " ¡Materiales listos! Ahora hagan la actividad juntos." if self.encargo.materiales_listos else " Falta el otro material. Pídele ayuda a un compañero."), "vista": "introduccion"}
            self._objetivo(identificador, "caldero")
            if not self.encargo.completo or len(presentes) < 2:
                raise ValueError("Entreguen ambos materiales con dos jugadores distintos en el destino señalado.")
            self.preparados.add(identificador)
            if set(presentes).issubset(self.preparados):
                self._siguiente()
                return {"mensaje": "Comienza una nueva investigación.", "vista": "introduccion"}
            return {"mensaje": "Listo para continuar. Esperando al resto del equipo."}
        if self.fase != "investigacion" and accion in ("votar",):
            raise ValueError("La investigación ya terminó.")
        respuesta = super()._ejecutar(identificador, solicitud, ahora, presentes)
        if accion == "interactuar" and self.ronda and self.fase == "investigacion":
            rol = self.jugadores[identificador]["rol"]
            fuente = next(o for o in self.objetivos if o.get("rol") == rol)
            if solicitud.get("objetivo") == fuente["id"]:
                aviso = self._renovar_aviso(identificador)
                respuesta["mensaje"] += " Aviso temporal: " + aviso["texto"]
        if accion == "entregar":
            pista = solicitud.get("pista")
            aviso = self.avisos_recientes[identificador].get(pista)
            if aviso and self.reloj < aviso["vence"]:
                receptor = solicitud.get("destinatario")
                from .mision import TODOS
                receptores = ((set(presentes) & self.jugadores.keys()) - {identificador}) if receptor == TODOS else {receptor}
                for receptor in receptores:
                    anterior = self.avisos_recientes[receptor].get(pista)
                    if anterior is None or anterior["vence"] < aviso["vence"]:
                        self.avisos_recientes[receptor][pista] = deepcopy(aviso)
        if accion == "interactuar" and respuesta.get("titulo"):
            rol = self.jugadores[identificador]["rol"]
            metadatos = self.metadatos_pruebas.get(rol)
            if metadatos:
                respuesta["metadatos"] = dict(metadatos)
        return respuesta

    def _renovar_aviso(self, identificador):
        """Único registro para la fuente directa y su conversación validada."""
        if not self.ronda or self.fase != "investigacion":
            return None
        evento = self.casos[self.ronda][0]
        rol = self.jugadores[identificador]["rol"]
        aviso = {"texto": AVISOS_RECIENTES[evento], "vence": self.reloj + self.sorteo.vigencia(evento, rol)}
        self.avisos_recientes[identificador]["pista_" + rol] = aviso
        return aviso

    def _siguiente(self):
        self.resumen.append({"caso": self.casos[self.ronda][1], **self.resultado})
        self.obras.append(self.encargo.publico())
        self.ronda += 1
        self.encargo = EncargoSuministros(self.ronda, self.objetivos) if self.ronda < 3 else None
        self.pruebas = self.casos[self.ronda][4]
        self.metadatos_pruebas = self._metadatos(self.pruebas)
        self.correcta = self.casos[self.ronda][3]
        self.conocidas = {i: set() for i in self.jugadores}
        self.avisos_recientes = {i: {} for i in self.jugadores}
        self.halladas.clear()
        self.entregas.clear()
        self.votos.clear()
        self.resultado = None
        self.rectificacion = False
        self.preparados.clear()
        self.acompanante.pedidos.clear()
        self.materiales = self.encargo.cargas if self.encargo else {}
        self.depositos.clear()
        self.habilidades_usadas.clear()
        self.presion = 0.0
        self.oleadas = 0
        self.bono_equipo = False
        self.puntos_caso = 0
        self.clasificaciones.clear()
        # No borrar los acuses: una retransmisión antigua nunca afecta al nuevo caso.
        self._avisar(self.jugadores, "Nuevo caso: " + self.casos[self.ronda][1])

    def _premiar_encargo(self, presentes):
        if not self.encargo.completo or self.encargo.recompensado:
            return
        self.encargo.recompensado = True
        config = self.encargo.config
        nombre = config["indicador"]
        self.indicadores[nombre] = max(0, min(100, self.indicadores[nombre] + config["delta"]))
        self.puntos += 30
        self.acompanante.estrellas.add("encargo:" + str(self.ronda))
        self._registrar(config["efecto"] + ": +30 puntos de cooperación.")
        self._avisar(presentes, "¡Lo hicieron juntos! " + config["efecto"] + ". Ganaron una estrella.", "logro")

    def texto_resultado(self, texto, correcto):
        if correcto:
            self.acompanante.estrellas.add("caso:" + str(self.ronda))
        premio = ((80 if self.rectificacion else 100) if correcto else 0) + (20 if self.bono_equipo else 0)
        self.puntos += premio - self.puntos_caso
        self.puntos_caso = premio
        if self.ronda:
            texto = (self.casos[self.ronda][5] if correcto else
                "Las pistas cuentan otra cosa. " + ("La aldea sigue aprendiendo. Vamos a ayudar con la siguiente tarea." if self.rectificacion else "Pueden leer las pistas e intentarlo una vez más."))
        return texto + " " + ("Campaña terminada. Revisen el balance del equipo." if self.ronda == len(self.casos) - 1 else "Ahora abran M: la aldea necesita materiales concretos en el destino señalado.")

    def actualizar(self, segundos, presentes):
        self.presentes = set(presentes)
        self.reloj += max(0, min(segundos, 1))
        if self.ronda == 0 and self.encargo and self.encargo.config.get("requiere_puente"):
            self.puente.preparar(self.encargo.materiales_colocados)
        if self.puente.actualizar(self.reloj, presentes):
            self._avisar(self.jugadores, "¡El Puente 1 quedó reparado! La ruta vuelve a estar abierta.", "logro")
            self._registrar("El equipo reparó el Puente 1.")
            if self.encargo and self.encargo.config.get("requiere_puente"):
                self.encargo.puente_reparado = True
                self._premiar_encargo(presentes)
        if self.presente is not None:
            self.presente.resolver(self.presentes_presente)
        if self.futuro is not None:
            self.futuro.resolver(self.presentes_futuro)
            self.futuro.actualizar(segundos, self.jugadores)
        self.acompanante.actualizar(self)
        if self.encargo:
            self.encargo.revisar_ayudante(presentes, self.jugadores)
        if self.fase != "investigacion" or len(presentes) < 2:
            return
        if self.ronda > 0:
            self.presion += max(0, min(segundos, 1))
        oleadas = int(self.presion // 60)
        if oleadas > self.oleadas:
            self.oleadas = oleadas
            self.indicadores["desinformacion"] = min(100, self.indicadores["desinformacion"] + 3)
            self._avisar(presentes, "El rumor está creciendo. ¡Comparen sus pistas! No perderán la partida por tardar.")
        if not self.bono_equipo and all(len(self.conocidas[i]) >= 2 for i in self.jugadores):
            self.bono_equipo = True
            self.acompanante.estrellas.add("equipo:" + str(self.ronda))
            self.indicadores["confianza"] = min(100, self.indicadores["confianza"] + 3)
            self._avisar(presentes, "¡Todos tienen dos pistas! Ganaron una estrella por ayudarse.")

    def resolver(self, presentes):
        if (self.fase == "preparacion" and len(presentes) >= 2 and self.encargo.completo
                and set(presentes).issubset(self.preparados)):
            self._siguiente()
            return
        puente = self.estado_puente
        super().resolver(presentes)
        if self.resultado:
            caso = self.casos[self.ronda]
            # La ficha depende de la respuesta correcta y la persona sorteadas.
            ficha = ficha_resuelta(caso[0], caso[3], self.sorteo.persona)
            self.resultado.update(campos_legales(ficha))
            pruebas = [{"id": pista, "titulo": self.pruebas[pista.removeprefix("pista_")][0],
                        "texto": self.pruebas[pista.removeprefix("pista_")][1]}
                       for pista in sorted(self.halladas)]
            self.expediente.registrar(caso[0], caso[1], self.resultado, pruebas, ficha)
        if self.ronda:
            self.estado_puente = puente

    def publico(self, presentes):
        estado = super().publico(presentes)
        caso = self.casos[self.ronda]
        estado.update(id=caso[0], titulo=f"{self.ronda + 1}/{len(self.casos)} · {caso[1]}", noticia=caso[2],
                      fase=self.fase, ronda=self.ronda, total_casos=len(self.casos),
                      encargo=self.encargo.publico() if self.fase == "preparacion" else None, obras=list(self.obras),
                      suministros=len(self.depositos), preparados=len(set(presentes) & self.preparados),
                      balance=list(self.resumen) + ([{"caso": caso[1], **self.resultado}] if self.resultado else []),
                      estrellas=len(self.acompanante.estrellas), estrellas_total=11,
                      tutorial_cargas=[i for i, t in self.acompanante.tutoriales.items() if t["estado"] == "activo" and t["paso"] == 2],
                      sin_prisa=self.ronda == 0, puntos=self.puntos, bono_equipo=self.bono_equipo,
                      proxima_oleada=max(0, 60 - int(self.presion % 60)),
                      oleadas=self.oleadas, habilidades_usadas=sorted(self.habilidades_usadas),
                      npcs=self.dialogos.publico(), npcs_en_dialogo=self.dialogos.nombres_en_dialogo(),
                      exploracion=self.exploracion.publico(),
                      opciones=dict(self.opciones),
                      tipos_pocion={clave: tipo_pocion(clave) for clave in self.opciones},
                      clasificacion_opciones=list(clasificacion.OPCIONES["la_copa"]),
                      puente=self.puente.publico(), dimension_completa=self.fase == "final",
                      presente=self.presente.publico(self.presentes_presente) if self.presente else None,
                      futuro=self.futuro.publico(self.presentes_futuro) if self.futuro else None,
                      expediente=self.expediente.publico())
        return estado

    def privado(self, identificador):
        estado = super().privado(identificador)
        if not estado:
            return {}
        for pista in estado["inventario"]:
            pista["la_tienen"] = [i for i, conocidas in self.conocidas.items() if pista["id"] in conocidas]
            aviso = self.avisos_recientes[identificador].get(pista["id"])
            if aviso:
                vigente = self.reloj < aviso["vence"]
                pista["temporal"] = {"vigente": vigente, "segundos": max(0, int(aviso["vence"] - self.reloj)),
                                     "texto": aviso["texto"] if vigente else
                                     "Este aviso caducó. Vuelve a la fuente para renovarlo. Tus pruebas originales siguen guardadas."}
        rol = self.jugadores[identificador]["rol"]
        estado.update(habilidad=HABILIDADES[rol][0], descripcion_habilidad=HABILIDADES[rol][1],
                      habilidad_usada=identificador in self.habilidades_usadas,
                      suministro=identificador in self.materiales, depositado=identificador in self.depositos,
                      preparado=identificador in self.preparados)
        estado["clasificacion"] = self.clasificaciones.get(identificador)
        if self.presente is not None:
            estado["presente"] = self.presente.privado(identificador)
        if self.futuro is not None:
            estado["futuro"] = self.futuro.privado(identificador)
        if self.fase == "preparacion" and self.encargo.materiales_colocados and not self.encargo.completo:
            estado["objetivo"] = dict(self.objetivo_puente)
            reparador = self.puente.reparador
            estado["instruccion"] = ("¡El puente se está reparando!" if self.puente.estado == "REPAIR_ANIMATION" else
                                     self.jugadores[reparador]["nombre"] + " está reparando el Puente 1." if reparador not in (None, identificador) else
                                     "Ve al Puente 1 (arriba a la izquierda) y pulsa E. Acierta 3 veces en la zona verde.")
        elif self.fase == "preparacion":
            objetivo = self.encargo.objetivo(identificador, self.jugadores)
            estado["objetivo"] = objetivo
            carga = self.encargo.cargas.get(identificador)
            estado["carga"] = self.encargo.nombre(carga) if carga else None
            estado["instruccion"] = ("Encargo completo. Confirmen en el caldero." if self.encargo.completo else
                                      "Tu aporte está entregado. Ayuda a coordinar al equipo." if identificador in self.depositos and objetivo.get("id") == "caldero" else
                                      "Llevas " + estado["carga"] + ". Ve a " + self.encargo.config["lugar"] + " y pulsa E." if carga and carga not in self.encargo.entregados else
                                      "Ve a " + objetivo["nombre"] + " y pulsa E.")
        elif self.fase == "final":
            estado["instruccion"] = "¡La Copa está completa! Sigue la flecha hasta el portal y pulsa E. (M: balance)"
        return self.acompanante.datos(self, identificador, estado)
