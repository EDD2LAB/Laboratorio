"""Preparación, combate auxiliar y desenlace compartido. Sin dependencias gráficas."""
import math

PIEZAS = (("bateria", "Batería", "guardian"), ("circuito", "Circuito", "habitante"),
          ("carcasa", "Carcasa", "aspirante"))
RECONFIGURACION = (
    ("NÚCLEO", "Mi capa de control cayó. Repetía lo más compartido, no lo más cierto."),
    ("Archivista", "Desde hoy, cada dato muestra su fuente."),
    ("Representante Humano", "Y ninguna decisión se toma sin una persona que la revise."),
    ("NÚCLEO", "Antes de actuar, preguntaré. Antes de compartir, verificaré."))
EPILOGOS = (("futuro", "Ciudad Núcleo: caen las barreras. Cada pantalla muestra su fuente."),
            ("presente", "Distrito Conecta: lo verificado se distingue. Ronaldo Vélez recupera su nombre."),
            ("la_copa", "La Copa: el puente sigue en pie y el Consejo vuelve a reunirse."))
CIERRE = "Lo que empezó como un rumor cambió a toda una comunidad."


class AventuraFinal:
    def __init__(self, puntos):
        self.puntos = puntos
        self.entregadas = set()
        self.cargas = {}
        self.fabricado = False
        self.municion = 0
        self.reponer_en = 0
        self.disparo_en = {}
        self.minis = []
        self.numero_mini = 0
        self.generar_en = 0
        self.etapa = None
        self.indice = 0
        self.tiempo = 0.0
        self.revision = 0
        self.faltan = []
        self.trazo = None
        self.trazo_hasta = 0

    def materiales(self):
        return [dict(id=clave, nombre=nombre, dimension="futuro", **{k: self.puntos[rol][k] for k in ("x", "y")})
                for clave, nombre, rol in PIEZAS if clave not in self.entregadas and clave not in self.cargas.values()]

    def objetivo(self, identificador):
        if identificador in self.cargas or len(self.entregadas) == 3:
            return self.puntos["mensajero"]
        return next(iter(self.materiales()), self.puntos["mensajero"])

    def preparar(self, operacion, identificador, jugador, solicitud, cerca, reloj):
        if self.faltan:
            raise ValueError("Primero terminen: " + ", ".join(self.faltan) + ". Sigue el portal.")
        if self.fabricado:
            raise ValueError("El equipo ya construyó el módulo y los blásteres.")
        if operacion == "material":
            pieza = next((p for p in self.materiales() if p["id"] == solicitud.get("pieza")), None)
            if identificador in self.cargas or not pieza or not cerca(jugador, pieza):
                raise ValueError("Busca una pieza disponible. Solo puedes llevar una a la vez.")
            self.cargas[identificador] = pieza["id"]
            return "Lleva la pieza al taller del Corredor de Datos."
        if not cerca(jugador, self.puntos["mensajero"]):
            raise ValueError("Acércate al taller del Corredor de Datos.")
        if operacion == "depositar":
            pieza = self.cargas.pop(identificador, None)
            if pieza is None:
                raise ValueError("Primero recoge una pieza.")
            self.entregadas.add(pieza)
            return "¡Pieza entregada! " + str(len(self.entregadas)) + "/3."
        if operacion == "fabricar" and len(self.entregadas) == 3:
            self.fabricado, self.municion = True, 12
            return "¡Módulo y blásteres listos! Reúnanse para empezar."
        raise ValueError("Faltan piezas para fabricar el equipo.")

    def combatir(self, operacion, identificador, jugador, solicitud, reloj, batalla, linea_libre):
        if not self.fabricado:
            raise ValueError("Primero fabriquen el equipo en el taller.")
        if identificador in batalla.derribados:
            raise ValueError("Espera ayuda antes de usar el bláster.")
        if operacion == "municion":
            punto = self.puntos["mensajero"]
            if math.hypot(jugador["x"] - punto["x"], jugador["y"] - punto["y"]) > 68:
                raise ValueError("Las cajas de munición están en el taller.")
            if reloj < self.reponer_en or self.municion >= 24:
                raise ValueError("Esperen la recarga de la caja o utilicen la munición disponible.")
            self.municion = min(24, self.municion + 6)
            self.reponer_en = reloj + 8
            return "Seis cargas nuevas para todo el equipo."
        objetivo = solicitud.get("mini")
        mini = next((m for m in self.minis if type(objetivo) is int and m["id"] == objetivo), None)
        if (not mini or batalla.turno not in ("aviso", "rayo") or self.municion <= 0
                or reloj < self.disparo_en.get(identificador, 0)):
            raise ValueError("Elige un mini-núcleo activo y espera a que recargue el bláster.")
        if math.hypot(jugador["x"] - mini["x"], jugador["y"] - mini["y"]) > 180:
            raise ValueError("Acércate al mini-núcleo para disparar.")
        if not linea_libre((jugador["x"], jugador["y"]), (mini["x"], mini["y"])):
            raise ValueError("Hay una pared entre el bláster y el mini-núcleo.")
        self.trazo = [round(jugador["x"]), round(jugador["y"]), round(mini["x"]), round(mini["y"])]
        self.trazo_hasta = reloj + .18
        self.disparo_en[identificador] = reloj + .6
        self.municion -= 1
        mini["vida"] -= 1
        if mini["vida"] == 0:
            self.minis.remove(mini)
            self.municion = min(24, self.municion + 1)
            return "¡Mini-núcleo desactivado! Recuperaron una carga."
        return "¡Impacto! Falta uno para desactivarlo."

    def actualizar(self, dt, reloj, jugadores, presentes, batalla, hechos):
        if reloj >= self.trazo_hasta:
            self.trazo = None
        for i in set(self.cargas) - set(presentes):
            self.cargas.pop(i)
        if self.etapa is not None:
            if self.etapa == "creditos":
                self.tiempo += dt
            if self.etapa in ("reconfiguracion", "epilogo"):
                self.tiempo += dt
                if self.tiempo >= (7.5 if self.etapa == "reconfiguracion" else 5):
                    self.avanzar()
            return []
        if batalla.turno not in ("aviso", "rayo") or len(hechos) == 4:
            return []
        if reloj >= self.generar_en and len(self.minis) < 2:
            # Reutiliza puntos que el mapa ya validó como caminables.
            rol = ("guardian", "habitante", "aspirante")[self.numero_mini % 3]
            self.numero_mini += 1
            p = self.puntos[rol]
            self.minis.append(dict(id=self.numero_mini, x=p["x"], y=p["y"], vida=2, aviso=2.5))
            self.generar_en = reloj + 12
        golpes = []
        for mini in self.minis:
            mini["aviso"] -= dt
            if mini["aviso"] <= 0:
                mini["aviso"] = 4
                golpes.extend(i for i, j in jugadores.items() if i in presentes and i not in batalla.derribados
                              and j.get("dimension") == "futuro" and not j.get("interior")
                              and math.hypot(j["x"] - mini["x"], j["y"] - mini["y"]) <= 38)
        return sorted(set(golpes))

    def victoria(self):
        if self.etapa is None:
            self.etapa, self.indice, self.tiempo = "reconfiguracion", 0, 0
            self.revision += 1
            self.minis.clear()

    def avanzar(self):
        self.tiempo = 0
        if self.etapa == "reconfiguracion":
            self.indice += 1
            if self.indice == len(RECONFIGURACION):
                self.etapa, self.indice = "epilogo", 0
        elif self.etapa == "epilogo":
            self.indice += 1
            if self.indice == len(EPILOGOS):
                self.etapa, self.indice = "informe", 0
        elif self.etapa == "informe":
            self.etapa = "pantalla"
        elif self.etapa == "pantalla":
            self.etapa = "creditos"
        self.revision += 1

    def publico(self, batalla):
        return dict(disparo=self.trazo, fabricado=self.fabricado, entregadas=sorted(self.entregadas), cargas=dict(self.cargas),
                    materiales=self.materiales(), taller=self.puntos["mensajero"], municion=self.municion,
                    minis=[dict(m, aviso=round(m["aviso"], 1)) for m in self.minis],
                    minis_activos=batalla.turno in ("aviso", "rayo") and self.etapa is None,
                    faltan=list(self.faltan), cierre=dict(etapa=self.etapa, indice=self.indice,
                                                       segundos=round(self.tiempo, 1), revision=self.revision))
