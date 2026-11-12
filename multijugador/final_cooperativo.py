"""Recuperar el control: cuatro retos autoritativos, sin Pygame ni arte en red.

Protocolo 20: cada rol tiene una parte en la fase verde y otra en la roja.
El escudo cae cuando los cuatro terminan su parte verde; al completar las
cuatro tareas se gana sin volver a confirmar en las consolas.
"""
import random
from multijugador.batalla_cooperativa import BatallaCooperativa
from multijugador.aventura_final import AventuraFinal

ROLES = ("guardian", "mensajero", "habitante", "aspirante")
CAMPOS_ORDEN = ("firma", "fecha", "permiso")
ORDENES_VERDE, ORDENES_ROJA = 3, 2

# Guardián: cada orden copia su registro o cambia un solo dato.
TITULOS_ORDEN = ("Reabrir el sector Puerto", "Cerrar el Mercado de noche", "Apagar las cámaras del Barrio",
                 "Reabrir el Archivo", "Desviar la energía de la Torre", "Liberar las cuentas del Muelle",
                 "Revisar las alarmas de la Plaza")
LEGITIMOS = dict(firma=("Consejo humano", "Consejera Ana Ríos", "Consejo de la ciudad"),
                 fecha=("Hoy", "Ayer", "Esta mañana"),
                 permiso=("Supervisión humana", "Aprobado por el consejo", "Revisión del consejo"))
ALTERADOS = dict(firma=("Cuenta de NÚCLEO", "Firma automática", "Administrador sin cargo"),
                 fecha=("Hace diez años", "Fecha en blanco", "31 de febrero"),
                 permiso=("Control sin revisión", "Acceso total", "Decisión sin consejo"))

# Aspirante: pruebas sacadas del caso de Ciudad Núcleo (multijugador/nucleo.py).
# id -> (título, detalle, tiene fuente)
PRUEBAS = {
    "acta": ("Acta del consejo", "Toda decisión la firma el consejo. Firmas: 3 consejeras.", True),
    "bitacora": ("Bitácora técnica", "03:12 el administrador amplió permisos. Registro del sistema.", True),
    "cuentas": ("Cuentas coordinadas", "Creadas hoy, en el mismo minuto, sin seguidores reales.", True),
    "conexion": ("Sector Puerto", "Restauramos la conexión y comprobamos que volvió a la red.", True),
    "firma_rep": ("Firma del Representante", "Acepta reconfigurar con supervisión humana. Firmado.", True),
    "orden": ("Orden de autorización", "\"Control absoluto aprobado.\" La firma la propia NÚCLEO.", False),
    "voz": ("Post de @ciudad_segura_01", "\"NÚCLEO nos protege a todos.\" Cuenta sin historial.", False),
    "rumor": ("Mensaje reenviado", "\"Dicen que el Ciudadano exagera.\" No dice quién lo escribió.", False),
    "captura": ("Captura de pantalla", "Imagen sin fecha, sin autor y sin enlace al original.", False),
}
# campo -> {id: (etiqueta, correcta)}; la prueba usa las tarjetas de PRUEBAS.
OPCIONES = {
    "conexion": {"comprobada": ("Conexión comprobada", True), "verificada": ("Puerto reconectado y verificado", True),
                 "promesa": ("Conexión sin probar", False), "nucleo_dice": ("NÚCLEO dice que funciona", False),
                 "rapida": ("Reconectar todo sin revisar", False)},
    "limite": {"humana": ("Supervisión humana", True), "firma_consejo": ("Cada orden la firma el consejo", True),
               "revision": ("Revisión humana de sus decisiones", True), "absoluto": ("Control sin revisión", False),
               "urgente": ("NÚCLEO decide solo si es urgente", False), "eficiente": ("Autonomía por eficiencia", False),
               "autosupervision": ("NÚCLEO se vigila a sí mismo", False)},
}
CAMPOS_PROPUESTA = ("prueba", "conexion", "limite")


def opcion_correcta(campo, valor):
    """Las respuestas no viajan en red; los bots y las pruebas preguntan aquí."""
    if campo == "prueba":
        return valor in PRUEBAS and PRUEBAS[valor][2]
    return valor in OPCIONES.get(campo, {}) and OPCIONES[campo][valor][1]


class FinalCooperativo:
    def __init__(self, objetivos, semilla=None):
        self.azar = random.Random(semilla)
        self.batalla = BatallaCooperativa()
        por_id = {o["id"]: o for o in objetivos}
        self.puntos = {rol: {k: v for k, v in por_id["futuro:" + tarea].items() if k in ("id", "nombre", "dimension", "x", "y")} for rol, tarea in
                       (("guardian", "archivos"), ("mensajero", "llave"),
                        ("habitante", "conexiones"), ("aspirante", "pantalla"))}
        self.aventura = AventuraFinal(self.puntos)
        self.fase = "bloqueado"
        self.ronda = 0
        self.reloj = 0.0
        self.integridad = 3
        self.hechos = set()   # roles con sus dos partes terminadas
        self.verde = set()    # roles con la parte verde terminada
        self.roja_iniciada = False
        self.avisos = ""
        self.activaciones = set()  # se conserva vacío en el estado público por compatibilidad
        self.portador = None
        self.tramo = 0
        self.luces = 0
        self.ruta = [dict(self.puntos["guardian"]), dict(self.puntos["aspirante"]), dict(self.puntos["habitante"])]
        self.recogida = self.puntos["mensajero"]
        self.invulnerable_hasta = 0
        self.valores = [0, 6, 0]
        self.metas = [3, 3, 3]
        self.propuesta = {}
        self.opciones = {}
        self.mazo = []
        self.seleccion = set()
        self.carga = 0.0
        self.mantener_hasta = 0
        self.operador = None
        self.ordenes = []
        self.paso_orden = 0
        self.modulo = ""
        self.evento_id = None

    # --- Preparación ----------------------------------------------------------------
    def _orden(self, titulo, alterada):
        azar = self.azar
        registro = {campo: azar.choice(LEGITIMOS[campo]) for campo in CAMPOS_ORDEN}
        orden, falso = dict(registro), None
        if alterada:
            falso = azar.choice(CAMPOS_ORDEN)
            orden[falso] = azar.choice(ALTERADOS[falso])
        return dict(titulo=titulo, registro=registro, orden=orden, falso=falso)

    def _metas_distintas(self):
        """Metas con la misma suma que los valores actuales: el rompecabezas siempre tiene solución."""
        suma = sum(self.valores)  # entre 6 y 12 (ver preparar): siempre hay varias soluciones
        mejor = None
        for _ in range(200):
            a = self.azar.randint(max(1, suma - 10), min(5, suma - 2))
            b = self.azar.randint(max(1, suma - a - 5), min(5, suma - a - 1))
            metas = [a, b, suma - a - b]
            distancia = sum(abs(m - v) for m, v in zip(metas, self.valores))
            if distancia >= 4:
                return metas
            if distancia and (mejor is None or distancia > mejor[0]):
                mejor = (distancia, metas)
        return mejor[1] if mejor else [self.valores[1], self.valores[2], self.valores[0]]

    def preparar(self, evento):
        if self.fase != "bloqueado":
            return
        azar = self.azar
        self.evento_id = evento
        titulos = azar.sample(TITULOS_ORDEN, ORDENES_VERDE + ORDENES_ROJA)
        # Al menos una orden legítima y una alterada en cada fase.
        verdes = [True, False, azar.random() < .5]
        rojas = [True, False]
        azar.shuffle(verdes)
        azar.shuffle(rojas)
        self.ordenes = [self._orden(t, a) for t, a in zip(titulos, verdes + rojas)]
        self.valores = [azar.randint(1, 5) for _ in range(3)]
        while not 6 <= sum(self.valores) <= 12:
            self.valores = [azar.randint(1, 5) for _ in range(3)]
        self.metas = self._metas_distintas()
        con = azar.sample([i for i, p in PRUEBAS.items() if p[2]], 3)
        sin = azar.sample([i for i, p in PRUEBAS.items() if not p[2]], 3)
        self.mazo = con + sin
        azar.shuffle(self.mazo)
        prueba = [azar.choice(con)] + azar.sample(sin, 2)
        azar.shuffle(prueba)
        self.opciones = {"prueba": prueba}
        for campo, banco in OPCIONES.items():
            buenas = [i for i, (_, ok) in banco.items() if ok]
            malas = [i for i, (_, ok) in banco.items() if not ok]
            elegidas = [azar.choice(buenas)] + azar.sample(malas, 2)
            azar.shuffle(elegidas)
            self.opciones[campo] = elegidas
        self.modulo = "turquesa"
        self.fase = "preparacion"
        self.avisos = "El equipo ya investigó. Ahora vamos a recuperar el control juntos."

    # --- Utilidades -----------------------------------------------------------------
    def _fallo(self, texto):
        self.integridad -= 1
        self.avisos = texto
        if self.integridad <= 0:
            self.fase = "reintento"
            self.portador = None
            self.avisos = "La señal se cortó. Reintenten: los casos y los pasos completados se conservan."
        return dict(mensaje=self.avisos, acierto=False, vista="final_cooperativo")

    @property
    def fase_roja(self):
        return self.batalla.fase == 2

    def parte_lista(self, rol):
        """¿Terminó el rol lo que le toca en la fase actual?"""
        return rol in self.hechos or (not self.fase_roja and rol in self.verde)

    def _revisar_fases(self):
        if self.fase != "activo":
            return
        if not self.fase_roja and set(ROLES) <= self.verde:
            self.batalla.reiniciar(self.hechos, self.verde)
        if self.fase_roja and not self.roja_iniciada:
            # NÚCLEO descalibra la estación al pasar a los rayos rojos.
            self.roja_iniciada = True
            self.metas = self._metas_distintas()
            self.carga, self.mantener_hasta = 0.0, 0
        if len(self.hechos) == 4 and self.fase == "activo":
            self.fase = "victoria"
            self.aventura.victoria()
            self.avisos = "¡Lo lograron! NÚCLEO ayuda a la ciudad bajo supervisión humana."

    def objetivo(self, rol, identificador=None):
        if self.fase == "preparacion" and not self.aventura.fabricado:
            return self.aventura.objetivo(identificador)
        if rol == "mensajero" and "mensajero" not in self.hechos and self.fase == "activo":
            if not self.fase_roja:
                return self.ruta[min(self.luces, len(self.ruta) - 1)]
            return self.recogida if self.portador is None else self.ruta[min(self.tramo, len(self.ruta) - 1)]
        return self.puntos[rol]

    # --- Acciones -------------------------------------------------------------------
    def ejecutar(self, identificador, jugador, solicitud, jugadores, presentes, cerca, linea_libre=None):
        if self.fase == "bloqueado":
            raise ValueError("Primero investiguen el caso de NÚCLEO y tomen una decisión.")
        if type(solicitud.get("ronda_final")) is not int or solicitud["ronda_final"] != self.ronda:
            raise ValueError("El desafío cambió. Revisa el intento actual.")
        if jugador.get("dimension") != "futuro" or jugador.get("interior"):
            raise ValueError("Vuelve a la ciudad para participar en el final.")
        operacion = solicitud.get("operacion")
        if operacion == "continuar":
            if (self.fase != "victoria" or type(solicitud.get("revision_cierre")) is not int
                    or solicitud.get("revision_cierre") != self.aventura.revision):
                raise ValueError("El cierre cambió. Revisa la escena actual.")
            self.aventura.avanzar()
            return dict(mensaje="", silencioso=True)
        if operacion in ("material", "depositar", "fabricar"):
            if self.fase != "preparacion":
                raise ValueError("La preparación ya terminó.")
            mensaje = self.aventura.preparar(operacion, identificador, jugador, solicitud, cerca, self.reloj)
            return dict(mensaje=mensaje, vista="final_cooperativo", silencioso=True)
        if operacion in ("disparar", "municion"):
            if self.fase != "activo" or len(self.hechos) == 4:
                raise ValueError("El combate no está activo.")
            mensaje = self.aventura.combatir(operacion, identificador, jugador, solicitud, self.reloj, self.batalla,
                                              linea_libre or (lambda a, b: False))
            return dict(mensaje=mensaje, silencioso=True)
        rol = solicitud.get("rol", jugador["rol"])
        if rol not in ROLES:
            raise ValueError("Elige un rol válido.")
        ocupados = {j["rol"] for i, j in jugadores.items() if i in presentes and j.get("dimension") == "futuro"}
        transportando = rol == "mensajero" and self.portador == identificador
        if rol != jugador["rol"] and rol in ocupados and not transportando:
            raise ValueError("Esa tarea le corresponde a tu compañero.")
        objetivo = self.puntos["aspirante"] if operacion in ("iniciar", "reintentar") else self.objetivo(rol, identificador)
        if operacion == "auxiliar":
            aliado = solicitud.get("aliado")
            objetivo = jugadores.get(aliado, {}) if type(aliado) is str else {}
        if "x" not in objetivo or not cerca(jugador, objetivo):
            raise ValueError("Acércate a la estación indicada por la luz del mapa.")
        if self.fase == "activo" and operacion not in ("iniciar", "reintentar"):
            if identificador in self.batalla.derribados:
                raise ValueError("Espera ayuda de un compañero o la siguiente recarga.")
            if operacion != "auxiliar" and self.batalla.turno != "recarga":
                raise ValueError("¡Esquiva los rayos! Las consolas se usan durante la recarga.")
        if operacion in ("iniciar", "reintentar") and self.fase == "activo":
            return dict(mensaje="El desafío ya está en marcha.", vista="final_cooperativo", silencioso=True)
        if operacion == "iniciar" and self.fase == "preparacion":
            if self.aventura.faltan:
                raise ValueError("Primero terminen: " + ", ".join(self.aventura.faltan) + ". Vuelvan por el portal.")
            if not self.aventura.fabricado:
                raise ValueError("Ayuden a la rebelión: lleven tres piezas al taller y fabriquen el equipo.")
            self.fase = "activo"
            self.batalla.reiniciar(self.hechos, self.verde)
            self.ronda += 1
            self.avisos = "¡Sal de las marcas! Cuando NÚCLEO recargue, los cuatro usan sus estaciones."
        elif operacion == "reintentar" and self.fase == "reintento":
            for mini in self.aventura.minis:
                mini["aviso"] = 2.5
            self.aventura.generar_en = self.reloj + 3
            self.integridad = 3
            self.fase = "activo"
            self.batalla.reiniciar(self.hechos, self.verde)
            self.ronda += 1
            self.avisos = "Señal recuperada. Continúen desde el último paso."
        elif self.fase != "activo":
            raise ValueError("Revisa el estado del desafío antes de continuar.")
        elif operacion == "auxiliar":
            aliado = solicitud.get("aliado")
            otro = jugadores.get(aliado) if type(aliado) is str else None
            if (not otro or aliado not in presentes or otro.get("dimension") != "futuro"
                    or otro.get("interior") or aliado not in self.batalla.derribados or not cerca(jugador, otro)):
                raise ValueError("Acércate a un compañero caído para ayudarlo.")
            self.batalla.derribados.remove(aliado)
            self.avisos = "¡Compañero recuperado! Salgan de las marcas."
        elif self.parte_lista(rol):
            return dict(mensaje="Esta parte ya está lista. Esquiva y ayuda a tu equipo.", vista="final_cooperativo",
                        silencioso=True)
        elif rol == "guardian" and operacion == "comparar":
            resultado = self._guardian(solicitud.get("campo"))
            if resultado:
                return resultado
        elif rol == "habitante" and operacion == "ajustar":
            indice, delta = solicitud.get("indice"), solicitud.get("delta")
            if type(indice) is not int or not 0 <= indice < 3 or type(delta) is not int or delta not in (-1, 1):
                raise ValueError("Ajuste inválido.")
            vecino = (indice + 1) % 3  # circuitos acoplados: lo que sube uno lo cede el siguiente
            if not (0 <= self.valores[indice] + delta <= 6 and 0 <= self.valores[vecino] - delta <= 6):
                raise ValueError("Ese circuito no puede moverse más: prueba con otro.")
            self.valores[indice] += delta
            self.valores[vecino] -= delta
            self.carga = 0.0
        elif rol == "habitante" and operacion == "mantener":
            if self.valores != self.metas:
                raise ValueError("Coloca los tres indicadores en su zona verde antes de mantener E.")
            self.operador = identificador
            self.mantener_hasta = self.reloj + 1.5
        elif rol == "mensajero" and operacion == "encender":
            if self.fase_roja:
                raise ValueError("Las luces ya están encendidas: recoge el módulo.")
            self.luces += 1
            if self.luces >= len(self.ruta):
                self.verde.add("mensajero")
                self.avisos = "¡Ruta encendida! El módulo podrá viajar en la fase roja."
            else:
                self.avisos = "Luz encendida. Sigue hacia la siguiente."
        elif rol == "mensajero" and operacion == "recoger":
            if not self.fase_roja:
                raise ValueError("Primero enciende la ruta. El módulo viaja en la fase roja.")
            if self.portador is not None:
                raise ValueError("El módulo ya está en camino.")
            self.portador = identificador
            self.invulnerable_hasta = self.reloj + 3
            self.avisos = "Lleva el módulo por los puntos de recarga iluminados."
        elif rol == "mensajero" and operacion == "recargar":
            if self.portador != identificador:
                raise ValueError("Necesitas llevar el módulo.")
            if self.tramo < len(self.ruta) - 1:
                self.recogida = dict(self.ruta[self.tramo])
                self.tramo += 1
                self.avisos = "Recarga guardada. Sigue hacia la siguiente luz."
            else:
                if "habitante" not in self.hechos:
                    raise ValueError("El Habitante debe recalibrar primero la estación.")
                self.hechos.add("mensajero")
                self.portador = None
                self.avisos = "¡Módulo entregado! Falta la autorización del consejo."
        elif rol == "aspirante" and operacion == "marcar":
            prueba = solicitud.get("prueba")
            if self.fase_roja or type(prueba) is not str or prueba not in self.mazo:
                raise ValueError("Elige una de las pruebas reunidas.")
            self.seleccion ^= {prueba}
        elif rol == "aspirante" and operacion == "guardar":
            if self.fase_roja:
                raise ValueError("Las pruebas ya están guardadas.")
            if self.seleccion != {p for p in self.mazo if PRUEBAS[p][2]}:
                return self._fallo("Alguna prueba no tiene fuente o falta una. Revisa quién la firma.")
            self.verde.add("aspirante")
            self.avisos = "¡Pruebas guardadas! Con ellas armarás la propuesta."
        elif rol == "aspirante" and operacion == "elegir":
            campo, valor = solicitud.get("campo"), solicitud.get("valor")
            if (not self.fase_roja or type(campo) is not str or type(valor) is not str
                    or campo not in self.opciones or valor not in self.opciones[campo]):
                raise ValueError("Elige una tarjeta de la propuesta.")
            self.propuesta[campo] = valor
        elif rol == "aspirante" and operacion == "autorizar":
            if not self.fase_roja:
                raise ValueError("La propuesta se presenta en la fase roja.")
            if not {"guardian", "habitante", "mensajero"}.issubset(self.hechos):
                raise ValueError("Reúne primero la verificación, la estación y la entrega.")
            if set(self.propuesta) != set(CAMPOS_PROPUESTA) or not all(
                    opcion_correcta(c, v) for c, v in self.propuesta.items()):
                return self._fallo("Revisa tu propuesta: una prueba con fuente, una conexión comprobada y control humano.")
            self.hechos.add("aspirante")
            self.avisos = "¡Consejo autorizado! NÚCLEO vuelve a estar bajo supervisión humana."
        else:
            raise ValueError("Esa acción no corresponde a este minijuego.")
        self._revisar_fases()
        return dict(mensaje=self.avisos or "Ajuste guardado.", vista="final_cooperativo", silencioso=True)

    def _guardian(self, campo):
        if type(campo) is not str or campo not in CAMPOS_ORDEN + ("aprobar",):
            raise ValueError("Señala firma, fecha o permiso, o aprueba la orden.")
        orden = self.ordenes[self.paso_orden]
        if campo != (orden["falso"] or "aprobar"):
            if orden["falso"] is None:
                return self._fallo("Esa orden era legítima: los tres datos coinciden con el registro.")
            return self._fallo("Esa orden tiene un dato alterado. Compara las dos tarjetas con calma.")
        self.paso_orden += 1
        if self.paso_orden == ORDENES_VERDE:
            self.verde.add("guardian")
            self.avisos = "¡Órdenes verificadas! El módulo " + self.modulo + " es auténtico."
        elif self.paso_orden == ORDENES_VERDE + ORDENES_ROJA:
            self.hechos.add("guardian")
            self.avisos = "¡NÚCLEO no pudo colar sus órdenes!"
        else:
            self.avisos = "Orden revisada. Sigue con la próxima."
        return None

    def actualizar(self, segundos, jugadores, pulsos, cerca, presentes=None):
        dt = max(0, min(segundos, 1))
        self.reloj += dt
        if self.fase == "victoria":
            self.aventura.actualizar(dt, self.reloj, jugadores, set(jugadores) if presentes is None else presentes, self.batalla, self.hechos)
            return
        if self.fase == "preparacion":
            for i in set(self.aventura.cargas) - (set(jugadores) if presentes is None else presentes):
                self.aventura.cargas.pop(i)
        if self.fase != "activo":
            return
        if presentes is not None and self.portador is not None and self.portador not in presentes:
            self.portador = None
        golpes = self.batalla.actualizar(dt, jugadores, set(jugadores) if presentes is None else presentes, self.hechos, self.verde)
        golpes = sorted(set(golpes) | set(self.aventura.actualizar(dt, self.reloj, jugadores,
                        set(jugadores) if presentes is None else presentes, self.batalla, self.hechos)))
        self.batalla.derribados.update(golpes)
        if golpes:
            if self.portador in golpes:
                self.portador = None
            self._fallo("Un rayo alcanzó al equipo. Ayuden a los caídos o esperen la recarga.")
            if self.fase != "activo":
                return
        if self.batalla.turno != "recarga":
            self.mantener_hasta = 0
            return
        jugador = jugadores.get(self.operador)
        if (jugador and not self.parte_lista("habitante") and self.valores == self.metas
                and (presentes is None or self.operador in presentes) and self.reloj <= self.mantener_hasta
                and cerca(jugador, self.puntos["habitante"])):
            self.carga = min(2, self.carga + dt)
            if self.carga >= 2:
                self.carga = 0.0
                (self.hechos if self.fase_roja else self.verde).add("habitante")
                self.avisos = "¡Estación estable!" if not self.fase_roja else "¡Estación recalibrada! Ya se puede entregar el módulo."
                self._revisar_fases()

    # --- Estado ---------------------------------------------------------------------
    def publico(self):
        if self.fase == "bloqueado":
            return dict(fase=self.fase)
        return dict(fase=self.fase, ronda=self.ronda, evento_id=self.evento_id, integridad=self.integridad,
                    batalla=self.batalla.publico(), aventura=self.aventura.publico(self.batalla),
                    hechos=sorted(self.hechos), verde=sorted(self.verde), aviso=self.avisos,
                    activaciones=sorted(self.activaciones),
                    puntos=self.puntos, ruta=self.ruta, luces=self.luces,
                    recogida=self.recogida, tramo=self.tramo, portador=self.portador,
                    modulo=self.modulo if "guardian" in self.verde else None,
                    carga=round(self.carga, 2), estacion_activa=self.parte_lista("habitante"))

    def privado(self, rol):
        if self.fase == "bloqueado":
            return {}
        if rol == "guardian":
            if self.paso_orden >= len(self.ordenes):
                return dict(numero=self.paso_orden, total=len(self.ordenes))
            orden = self.ordenes[self.paso_orden]
            return dict(titulo=orden["titulo"], registro=dict(orden["registro"]), orden=dict(orden["orden"]),
                        numero=self.paso_orden + 1, total=len(self.ordenes),
                        parte=ORDENES_VERDE if self.paso_orden < ORDENES_VERDE else len(self.ordenes))
        if rol == "habitante":
            return dict(valores=list(self.valores), metas=list(self.metas), acoplados=True)
        if rol == "aspirante":
            if not self.fase_roja:
                return dict(pruebas=[dict(id=p, titulo=PRUEBAS[p][0], detalle=PRUEBAS[p][1]) for p in self.mazo],
                            seleccion=sorted(self.seleccion))
            opciones = {campo: [(v, PRUEBAS[v][0] if campo == "prueba" else OPCIONES[campo][v][0]) for v in valores]
                        for campo, valores in self.opciones.items()}
            return dict(opciones=opciones, propuesta=dict(self.propuesta))
        return {}
