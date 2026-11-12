"""Recuperar el control: cuatro retos autoritativos, sin Pygame ni arte en red."""
import random
from multijugador.batalla_cooperativa import BatallaCooperativa

ROLES = ("guardian", "mensajero", "habitante", "aspirante")
PROPUESTA = {
    "prueba": (("informe", "Informe contrastado"), ("rumor", "Mensaje sin fuente")),
    "conexion": (("comprobada", "Conexión comprobada"), ("promesa", "Conexión sin probar")),
    "limite": (("humana", "Supervisión humana"), ("absoluto", "Control sin revisión")),
}
CORRECTA = dict(prueba="informe", conexion="comprobada", limite="humana")


class FinalCooperativo:
    def __init__(self, objetivos, semilla=None):
        self.azar = random.Random(semilla)
        self.batalla = BatallaCooperativa()
        por_id = {o["id"]: o for o in objetivos}
        self.puntos = {rol: {k: v for k, v in por_id["futuro:" + tarea].items() if k in ("id", "nombre", "dimension", "x", "y")} for rol, tarea in
                       (("guardian", "archivos"), ("mensajero", "llave"),
                        ("habitante", "conexiones"), ("aspirante", "pantalla"))}
        self.fase = "bloqueado"
        self.ronda = 0
        self.reloj = 0.0
        self.integridad = 3
        self.hechos = set()
        self.avisos = ""
        self.activaciones = set()
        self.portador = None
        self.tramo = 0
        self.ruta = [dict(self.puntos["guardian"]), dict(self.puntos["aspirante"]), dict(self.puntos["habitante"])]
        self.recogida = self.puntos["mensajero"]
        self.invulnerable_hasta = 0
        self.valores = [0, 6, 0]
        self.metas = [3, 3, 3]
        self.propuesta = {}
        self.carga = 0.0
        self.mantener_hasta = 0
        self.estacion_hasta = 0
        self.operador = None
        self.registro = {}
        self.orden = {}
        self.campo_falso = None
        self.modulo = ""
        self.evento_id = None

    def preparar(self, evento):
        if self.fase != "bloqueado":
            return
        azar = self.azar
        self.evento_id = evento
        self.registro = dict(firma="Consejo humano", fecha="Hoy", permiso="Supervisión humana")
        self.orden = dict(self.registro)
        self.campo_falso = azar.choice(tuple(self.registro))
        self.orden[self.campo_falso] = dict(firma="Cuenta de NÚCLEO", fecha="Hace diez años", permiso="Control sin revisión")[self.campo_falso]
        self.metas = [azar.randint(2, 4) for _ in range(3)]
        self.modulo = "turquesa"
        self.fase = "preparacion"
        self.avisos = "El equipo ya investigó. Ahora vamos a recuperar el control juntos."

    def _fallo(self, texto):
        self.integridad -= 1
        self.avisos = texto
        if self.integridad <= 0:
            self.fase = "reintento"
            self.portador = None
            self.avisos = "La señal se cortó. Reintenten: los casos y los pasos completados se conservan."
        return dict(mensaje=self.avisos, acierto=False, vista="final_cooperativo")

    def objetivo(self, rol):
        if len(self.hechos) == 4:
            return self.puntos["aspirante"]
        if rol == "mensajero" and "mensajero" not in self.hechos:
            return self.recogida if self.portador is None else self.ruta[min(self.tramo, len(self.ruta) - 1)]
        return self.puntos[rol]

    def ejecutar(self, identificador, jugador, solicitud, jugadores, presentes, cerca):
        if self.fase == "bloqueado":
            raise ValueError("Primero investiguen el caso de NÚCLEO y tomen una decisión.")
        if type(solicitud.get("ronda_final")) is not int or solicitud["ronda_final"] != self.ronda:
            raise ValueError("El desafío cambió. Revisa el intento actual.")
        if jugador.get("dimension") != "futuro" or jugador.get("interior"):
            raise ValueError("Vuelve a la ciudad para participar en el final.")
        operacion = solicitud.get("operacion")
        rol = solicitud.get("rol", jugador["rol"])
        if rol not in ROLES:
            raise ValueError("Elige un rol válido.")
        ocupados = {j["rol"] for i, j in jugadores.items() if i in presentes and j.get("dimension") == "futuro"}
        transportando = rol == "mensajero" and self.portador == identificador
        if rol != jugador["rol"] and rol in ocupados and not transportando:
            raise ValueError("Esa tarea le corresponde a tu compañero.")
        objetivo = self.puntos["aspirante"] if operacion in ("iniciar", "reintentar", "activar") else self.objetivo(rol)
        if operacion == "auxiliar":
            aliado = solicitud.get("aliado")
            objetivo = jugadores.get(aliado, {}) if type(aliado) is str else {}
        if "x" not in objetivo or not cerca(jugador, objetivo):
            raise ValueError("Acércate a la estación indicada por la luz del mapa.")
        if self.fase == "activo" and operacion not in ("iniciar", "reintentar"):
            if identificador in self.batalla.derribados:
                raise ValueError("Espera ayuda de un compañero o la siguiente recarga.")
            if operacion not in ("auxiliar", "activar"):
                if self.batalla.turno != "recarga":
                    raise ValueError("¡Esquiva los rayos! Las consolas se usan durante la recarga.")
                if rol in ("mensajero", "aspirante") and self.batalla.fase == 1:
                    raise ValueError("Primero Guardián y Habitante deben apagar el escudo.")
        if operacion in ("iniciar", "reintentar") and self.fase == "activo":
            return dict(mensaje="El desafío ya está en marcha.", vista="final_cooperativo", silencioso=True)
        if operacion == "activar" and self.fase == "victoria":
            return dict(mensaje=self.avisos, vista="final_cooperativo", silencioso=True)
        if operacion == "iniciar" and self.fase == "preparacion":
            self.fase = "activo"
            self.batalla.reiniciar(self.hechos)
            self.ronda += 1
            self.avisos = "¡Sal de las marcas! Cuando NÚCLEO recargue, usen las estaciones."
        elif operacion == "reintentar" and self.fase == "reintento":
            self.integridad = 3
            self.fase = "activo"
            self.batalla.reiniciar(self.hechos)
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
        elif operacion == "activar":
            if len(self.hechos) != 4:
                raise ValueError("Faltan tareas de los roles antes de activar.")
            self.activaciones.add(identificador)
            if presentes and set(presentes).issubset(self.activaciones):
                self.fase = "victoria"
                self.avisos = "¡Lo lograron! NÚCLEO ayuda a la ciudad bajo supervisión humana."
        elif rol == "guardian" and operacion == "comparar":
            if type(solicitud.get("campo")) is not str or solicitud["campo"] not in self.registro:
                raise ValueError("Señala firma, fecha o permiso.")
            if "guardian" in self.hechos:
                return dict(mensaje="La orden ya fue verificada.", vista="final_cooperativo")
            if solicitud["campo"] != self.campo_falso:
                return self._fallo("Ese dato coincide. Compara las dos tarjetas con calma.")
            self.hechos.add("guardian")
            self.avisos = "¡Orden verificada! Transporten el módulo " + self.modulo + "."
        elif rol == "habitante" and operacion == "ajustar":
            indice, delta = solicitud.get("indice"), solicitud.get("delta")
            if type(indice) is not int or not 0 <= indice < 3 or type(delta) is not int or delta not in (-1, 1):
                raise ValueError("Ajuste inválido.")
            if "habitante" not in self.hechos:
                self.valores[indice] = max(0, min(6, self.valores[indice] + delta))
        elif rol == "habitante" and operacion == "mantener":
            if any(abs(v - m) > 0 for v, m in zip(self.valores, self.metas)):
                raise ValueError("Coloca los tres indicadores en su zona verde antes de mantener E.")
            self.operador = identificador
            self.mantener_hasta = self.reloj + 1.5
            if "habitante" in self.hechos:
                self.estacion_hasta = self.reloj + 10
        elif rol == "mensajero" and operacion == "recoger":
            if "guardian" not in self.hechos:
                raise ValueError("Espera a que el Guardián verifique el módulo.")
            if self.portador is not None or "mensajero" in self.hechos:
                raise ValueError("El módulo ya está en camino o fue entregado.")
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
                    raise ValueError("El Habitante debe estabilizar primero la estación.")
                self.hechos.add("mensajero")
                self.portador = None
                self.avisos = "¡Módulo entregado! Falta la autorización del consejo."
        elif rol == "aspirante" and operacion == "elegir":
            campo, valor = solicitud.get("campo"), solicitud.get("valor")
            if type(campo) is not str or type(valor) is not str or campo not in PROPUESTA or valor not in {v[0] for v in PROPUESTA[campo]}:
                raise ValueError("Elige una tarjeta de la propuesta.")
            if "aspirante" not in self.hechos:
                self.propuesta[campo] = valor
        elif rol == "aspirante" and operacion == "autorizar":
            if not {"guardian", "habitante", "mensajero"}.issubset(self.hechos):
                raise ValueError("Reúne primero la verificación, la estación y la entrega.")
            if self.propuesta != CORRECTA:
                return self._fallo("Revisa tu propuesta: pruebas comprobadas y supervisión humana.")
            self.hechos.add("aspirante")
            self.avisos = "¡Consejo autorizado! Reúnanse en la pantalla y activen juntos."
        else:
            raise ValueError("Esa acción no corresponde a este minijuego.")
        if self.fase == "activo" and self.batalla.fase == 1 and {"guardian", "habitante"} <= self.hechos:
            self.batalla.reiniciar(self.hechos)
        return dict(mensaje=self.avisos or "Ajuste guardado.", vista="final_cooperativo", silencioso=True)

    def actualizar(self, segundos, jugadores, pulsos, cerca, presentes=None):
        dt = max(0, min(segundos, 1))
        self.reloj += dt
        if self.fase != "activo":
            return
        if presentes is not None:
            if self.portador is not None and self.portador not in presentes:
                self.portador = None
            if len(self.hechos) == 4 and presentes and set(presentes).issubset(self.activaciones):
                self.fase = "victoria"
                self.avisos = "¡Lo lograron! NÚCLEO ayuda a la ciudad bajo supervisión humana."
                return
        golpes = self.batalla.actualizar(dt, jugadores, set(jugadores) if presentes is None else presentes, self.hechos)
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
        if jugador and self.valores == self.metas and (presentes is None or self.operador in presentes) and self.reloj <= self.mantener_hasta and cerca(jugador, self.puntos["habitante"]):
            self.carga = min(2, self.carga + dt)
            if self.carga >= 2:
                self.hechos.add("habitante")
                self.estacion_hasta = self.reloj + 10
                if self.batalla.fase == 1 and "guardian" in self.hechos:
                    self.batalla.reiniciar(self.hechos)

    def publico(self):
        if self.fase == "bloqueado":
            return dict(fase=self.fase)
        return dict(fase=self.fase, ronda=self.ronda, evento_id=self.evento_id, integridad=self.integridad,
                    batalla=self.batalla.publico(),
                    hechos=sorted(self.hechos), aviso=self.avisos, activaciones=sorted(self.activaciones),
                    puntos=self.puntos, ruta=self.ruta if "guardian" in self.hechos else [],
                    recogida=self.recogida, tramo=self.tramo, portador=self.portador,
                    modulo=self.modulo if "guardian" in self.hechos else None,
                    carga=round(self.carga, 2), estacion_activa="habitante" in self.hechos)

    def privado(self, rol):
        if self.fase == "bloqueado":
            return {}
        if rol == "guardian":
            return dict(registro=dict(self.registro), orden=dict(self.orden))
        if rol == "habitante":
            return dict(valores=list(self.valores), metas=list(self.metas))
        if rol == "aspirante":
            return dict(opciones=PROPUESTA, propuesta=dict(self.propuesta))
        return {}
