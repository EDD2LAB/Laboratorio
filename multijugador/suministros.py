"""Encargos de transporte con carga, dos aportes distintos y efectos únicos."""

ENCARGOS = (
    {"titulo": "Asegurar la pasarela", "motivo": "Preparen el mantenimiento anunciado: lleven tablas y cuerdas al puesto de trabajo.",
     "materiales": (("tablas", "Tablas", "archivo"), ("cuerdas", "Cuerdas", "propuesta")),
     "destino": "eco_central", "lugar": "Puesto de mantenimiento", "efecto": "Pasarela preparada", "indicador": "armonia", "delta": 4},
    {"titulo": "Abastecer a las familias", "motivo": "Después de investigar el agua, entreguen agua segura y provisiones a las familias.",
     "materiales": (("agua", "Agua segura", "archivo"), ("provisiones", "Provisiones", "propuesta")),
     "destino": "testigo", "lugar": "Familias de Luma", "efecto": "Reserva comunitaria abastecida", "indicador": "confianza", "delta": 4},
    {"titulo": "Preparar un boletín verificado", "motivo": "Pongan por escrito el resultado de la alerta: lleven pergaminos y tinta al archivo.",
     "materiales": (("pergaminos", "Pergaminos", "testigo"), ("tinta", "Tinta", "propuesta")),
     "destino": "archivo", "lugar": "Archivo de Naira", "efecto": "Boletín verificado publicado", "indicador": "desinformacion", "delta": -6},
)


class EncargoSuministros:
    def __init__(self, ronda, objetivos):
        self.config = ENCARGOS[ronda]
        self.cargas = {}
        self.entregados = {}  # material -> jugador; cada persona aporta una carga.
        self.recompensado = False
        self.ayudante = None
        self.progreso = 0
        self.ultima_accion = -10
        self.objetivos = {o["id"]: o for o in objetivos}
        central = next(o["id"] for o in objetivos if o.get("rol") == "mensajero")
        self.destino = self.objetivos[central if self.config["destino"] == "eco_central" else self.config["destino"]]

    @property
    def materiales_listos(self):
        return len(self.entregados) == 2 and len(set(self.entregados.values())) == 2

    @property
    def completo(self):
        return self.materiales_listos and self.progreso >= 3

    def revisar_ayudante(self, presentes, jugadores):
        import math
        j = jugadores.get(self.ayudante)
        if not j or self.ayudante not in presentes or math.hypot(j["x"]-self.destino["x"], j["y"]-self.destino["y"]) > 68:
            self.ayudante = None

    def actividad(self, jugador, accion, ahora, presentes, jugadores):
        import math
        def cerca(i):
            j = jugadores[i]
            return math.hypot(j["x"] - self.destino["x"], j["y"] - self.destino["y"]) <= 68
        if not self.materiales_listos or self.completo:
            raise ValueError("Primero traigan los dos materiales. Si ya terminaron, vuelvan al caldero.")
        if jugador not in presentes or not cerca(jugador):
            raise ValueError("Acércate al círculo verde del puesto para ayudar.")
        self.revisar_ayudante(presentes, jugadores)
        if accion == "sujetar":
            self.ayudante = jugador
            return "¡Tú ayudas! Quédate aquí mientras otro compañero hace la tarea."
        if accion != "trabajar":
            raise ValueError("Elige ayudar o hacer la tarea.")
        if not self.ayudante or self.ayudante == jugador:
            raise ValueError("Necesitas que otro compañero pulse 'Yo ayudo' y se quede en el puesto.")
        if ahora - self.ultima_accion < .6:
            raise ValueError("¡Bien! Espera a que se llene el brillo y vuelve a pulsar.")
        self.ultima_accion = ahora
        self.progreso += 1
        return "¡Bien hecho! " + str(self.progreso) + " de 3 pasos."

    def fuente(self, material):
        return self.objetivos[next(m[2] for m in self.config["materiales"] if m[0] == material)]

    def nombre(self, material):
        return next(m[1] for m in self.config["materiales"] if m[0] == material)

    def recoger(self, jugador, objetivo, material=None):
        if self.materiales_listos or jugador in self.entregados.values():
            raise ValueError("Tu aporte ya está entregado o el encargo está completo.")
        disponibles = [m[0] for m in self.config["materiales"] if m[2] == objetivo and m[0] not in self.entregados]
        if material is not None and (not isinstance(material, str) or material not in disponibles):
            raise ValueError("Ese material no está disponible en este punto.")
        if not disponibles:
            raise ValueError("En este punto no quedan materiales necesarios para el encargo.")
        material = material or disponibles[0]
        self.cargas[jugador] = material
        return "Llevas " + self.nombre(material) + ". Destino: " + self.config["lugar"] + "."

    def entregar(self, jugador):
        material = self.cargas.get(jugador)
        if jugador in self.entregados.values():
            return "Tu entrega ya quedó registrada."
        if not material:
            raise ValueError("Primero recoge uno de los materiales del encargo.")
        if material in self.entregados:
            raise ValueError("Ese material ya fue entregado. Cambia tu carga en el otro punto de recogida.")
        self.entregados[material] = jugador
        self.cargas.pop(jugador)
        return "Entrega confirmada: " + self.nombre(material) + "."

    def objetivo(self, jugador, jugadores):
        if self.materiales_listos and not self.completo:
            return dict(self.destino, nombre=self.config["lugar"])
        if self.completo or jugador in self.entregados.values():
            return self.objetivos["caldero"]
        if jugador in self.cargas and self.cargas[jugador] not in self.entregados:
            return dict(self.destino, nombre=self.config["lugar"])
        faltantes = [m[0] for m in self.config["materiales"] if m[0] not in self.entregados]
        reservados = {m for i, m in self.cargas.items() if i != jugador and i in jugadores}
        material = next((m for m in faltantes if m not in reservados), faltantes[0])
        return dict(self.fuente(material), nombre="Recoger " + self.nombre(material))

    def publico(self):
        return {"titulo": self.config["titulo"], "motivo": self.config["motivo"],
                "materiales": [{"id": m, "nombre": nombre, "fuente": dict(self.fuente(m)), "entregado": m in self.entregados}
                               for m, nombre, _ in self.config["materiales"]],
                "destino": dict(self.destino, nombre=self.config["lugar"]), "completo": self.completo,
                "materiales_listos": self.materiales_listos,
                "actividad": {"ayudante": self.ayudante, "progreso": self.progreso, "total": 3,
                              "verbo": ("Colocar una tabla", "Repartir una cesta", "Pegar un sello")[ENCARGOS.index(self.config)]},
                "efecto": self.config["efecto"], "cargas": dict(self.cargas)}
