"""Encargos de transporte con carga, dos aportes distintos y efectos únicos."""

CESTO = "Cesto de la aldea"  # todos los encargos se reúnen en el mismo cesto

ENCARGOS = (
    # Primer evento: SIEMPRE 3 objetos (tablas, cuerda y canasta de
    # herramientas), sin importar cuántos jugadores haya. Antes eran 2 porque
    # esta configuración solo listaba dos materiales y materiales_listos exigía
    # exactamente 2; no dependía del número de jugadores.
    {"titulo": "Reparar el Puente 1", "motivo": "El Puente 1 está roto. Metan tablas, cuerda y la canasta de herramientas en el cesto de la aldea; después reparen el puente.",
     "materiales": (("tablas", "Tablas", "archivo"), ("cuerdas", "Cuerda", "propuesta"),
                    ("herramientas", "Canasta de herramientas", "testigo")),
     "lugar": CESTO, "efecto": "Puente 1 reparado", "indicador": "armonia", "delta": 4, "sitio": "puente_1",
     # Cada objeto es único (nadie puede llevar el que ya carga otro) y una
     # misma persona puede aportar más de uno, de a uno por vez.
     "objetos_unicos": True, "aportes_libres": True, "requiere_puente": True},
    # Segundo evento: reunir agua y provisiones y después repartir las cestas
    # caminando hasta cada familia (una cesta por viaje).
    {"titulo": "Abastecer a las familias", "motivo": "Después de investigar el agua, reúnan en el cesto de la aldea agua segura y provisiones. Luego tomen las cestas y llévenlas caminando a cada familia.",
     "materiales": (("agua", "Agua segura", "archivo"), ("provisiones", "Provisiones", "propuesta")),
     "lugar": CESTO, "efecto": "Reserva comunitaria abastecida", "indicador": "confianza", "delta": 4, "sitio": "testigo", "desvio_bandera": (-36, -6),
     "reparto": True},
)


def _faltan(cantidad):
    return "Falta 1." if cantidad == 1 else "Faltan " + str(cantidad) + "."


class EncargoSuministros:
    def __init__(self, ronda, objetivos, familias=()):
        self.config = ENCARGOS[ronda]
        # Reparto a pie: quién lleva una cesta y qué familias ya recibieron la suya.
        self.familias = [dict(f) for f in familias][:3] if self.config.get("reparto") else []
        self.cestas = set()
        self.servidas = {}
        self.cargas = {}
        self.entregados = {}  # material -> jugador; cada persona aporta una carga.
        self.recompensado = False
        self.ayudante = None
        self.progreso = 0
        self.ultima_accion = -10
        self.objetivos = {o["id"]: o for o in objetivos}
        self._lista_objetivos = objetivos  # el Puente 1 se agrega después de crear el primer encargo
        self.puente_reparado = False
        self.destino = self.objetivos["cesto"]

    @property
    def materiales_listos(self):
        total = len(self.config["materiales"])
        aportantes = 1 if self.config.get("aportes_libres") else total
        return len(self.entregados) == total and len(set(self.entregados.values())) >= aportantes

    @property
    def reparto(self):
        """El encargo termina repartiendo cestas a pie (si hay familias en el mapa)."""
        return bool(self.familias)

    @property
    def total_actividad(self):
        return len(self.familias) if self.reparto else 3

    @property
    def reparto_activo(self):
        return self.reparto and self.materiales_listos and not self.materiales_colocados

    @property
    def materiales_colocados(self):
        """Materiales entregados y actividad terminada (o todas las cestas repartidas)."""
        return self.materiales_listos and self.progreso >= self.total_actividad

    def familias_pendientes(self):
        return [dict(f, tipo="familia") for f in self.familias if f["id"] not in self.servidas]

    def familia(self, clave):
        familia = next((f for f in self.familias if f["id"] == clave), None)
        if familia is None:
            raise ValueError("Esa familia no espera una cesta.")
        return familia

    def tomar_cesta(self, jugador):
        if not self.reparto_activo:
            raise ValueError("Primero reúnan el agua y las provisiones en el cesto.")
        if jugador in self.cestas:
            raise ValueError("Ya llevas una cesta: llévala a una familia que la espera.")
        if len(self.cestas) >= len(self.familias_pendientes()):
            raise ValueError("Ya hay una cesta en camino para cada familia que falta.")
        self.cestas.add(jugador)
        return "Tomaste una cesta. Camina hasta una familia que la espera y pulsa E."

    def entregar_cesta(self, jugador, clave):
        familia = self.familia(clave)
        if not self.reparto_activo:
            raise ValueError("Ahora no hay cestas por repartir.")
        if jugador not in self.cestas:
            raise ValueError("Primero toma una cesta en el cesto de la aldea.")
        if clave in self.servidas:
            raise ValueError(familia["persona"] + " ya recibió su cesta.")
        self.cestas.discard(jugador)
        self.servidas[clave] = jugador
        self.progreso += 1
        faltan = self.total_actividad - self.progreso
        return ("¡" + familia["persona"] + " recibió su cesta! " +
                (_faltan(faltan) + " Vuelve al cesto por otra." if faltan else "¡Repartieron todas las cestas!"))

    def instruccion_reparto(self, jugador):
        faltan = self.total_actividad - self.progreso
        if jugador in self.cestas:
            return "Llevas una cesta. Camina hasta una familia marcada y pulsa E. " + _faltan(faltan)
        return "Toma una cesta en el cesto de la aldea (E) y llévala a una familia. " + _faltan(faltan)

    @property
    def completo(self):
        return self.materiales_colocados and (self.puente_reparado or not self.config.get("requiere_puente"))

    def revisar_ayudante(self, presentes, jugadores):
        import math
        self.cestas &= set(presentes)  # quien se fue suelta su cesta: otra persona puede llevarla
        for jugador in [i for i in self.cargas if i not in presentes]:
            self.cargas.pop(jugador)  # y también el objeto del encargo (cada uno es único)
        j = jugadores.get(self.ayudante)
        if not j or self.ayudante not in presentes or math.hypot(j["x"]-self.destino["x"], j["y"]-self.destino["y"]) > 68:
            self.ayudante = None

    def actividad(self, jugador, accion, ahora, presentes, jugadores):
        import math
        def cerca(i):
            j = jugadores[i]
            if j.get("dimension", "la_copa") != "la_copa":
                return False
            return math.hypot(j["x"] - self.destino["x"], j["y"] - self.destino["y"]) <= 68
        if not self.materiales_listos or self.materiales_colocados:
            raise ValueError("Primero traigan los materiales. Si ya terminaron, vuelvan al caldero.")
        if jugador not in presentes or not cerca(jugador):
            raise ValueError("Acércate al círculo verde del cesto para ayudar.")
        self.revisar_ayudante(presentes, jugadores)
        if accion == "sujetar":
            self.ayudante = jugador
            return "¡Tú ayudas! Quédate aquí mientras otro compañero hace la tarea."
        if accion != "trabajar":
            raise ValueError("Elige ayudar o hacer la tarea.")
        if not self.ayudante or self.ayudante == jugador:
            raise ValueError("Necesitas que otro compañero pulse 'Yo ayudo' y se quede junto al cesto.")
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
        if self.materiales_listos or (jugador in self.entregados.values() and not self.config.get("aportes_libres")):
            raise ValueError("Tu aporte ya está entregado o el encargo está completo.")
        ocupados = {m for i, m in self.cargas.items() if i != jugador} if self.config.get("objetos_unicos") else set()
        disponibles = [m[0] for m in self.config["materiales"] if m[2] == objetivo and m[0] not in self.entregados
                       and m[0] not in ocupados]
        if self.config.get("objetos_unicos") and material in ocupados:
            raise ValueError("Otro compañero ya lleva ese objeto.")
        if material is not None and (not isinstance(material, str) or material not in disponibles):
            raise ValueError("Ese material no está disponible en este punto.")
        if not disponibles:
            raise ValueError("En este punto no quedan materiales necesarios para el encargo.")
        material = material or disponibles[0]
        self.cargas[jugador] = material
        return "Llevas " + self.nombre(material) + ". Destino: " + self.config["lugar"] + "."

    def entregar(self, jugador):
        material = self.cargas.get(jugador)
        if jugador in self.entregados.values() and not (self.config.get("aportes_libres") and material):
            return "Tu entrega ya quedó registrada."
        if not material:
            raise ValueError("Primero recoge uno de los materiales del encargo.")
        if material in self.entregados:
            raise ValueError("Ese material ya fue entregado. Cambia tu carga en el otro punto de recogida.")
        self.entregados[material] = jugador
        self.cargas.pop(jugador)
        # Quien llevaba el mismo material ya no lo necesita: lo suelta para no
        # quedarse cargando un objeto que nadie puede entregar.
        for otro in [i for i, m in self.cargas.items() if m == material]:
            self.cargas.pop(otro)
        return "Entrega confirmada: " + self.nombre(material) + "."

    def objetivo(self, jugador, jugadores):
        if self.reparto_activo:
            pendientes = self.familias_pendientes()
            if jugador in self.cestas and pendientes:
                yo = jugadores.get(jugador, self.destino)
                import math
                cercana = min(pendientes, key=lambda f: math.hypot(f["x"] - yo["x"], f["y"] - yo["y"]))
                return dict(cercana, nombre="Llevar la cesta a " + cercana["persona"])
            return dict(self.destino, nombre="Tomar una cesta del " + self.config["lugar"].lower())
        if self.materiales_listos and not self.materiales_colocados:
            return dict(self.destino, nombre=self.config["lugar"])
        if self.materiales_colocados and not self.completo:
            return None  # La campaña indica el Puente 1.
        if jugador in self.cargas and self.cargas[jugador] not in self.entregados:
            return dict(self.destino, nombre=self.config["lugar"])
        faltantes = [m[0] for m in self.config["materiales"] if m[0] not in self.entregados]
        if self.completo or not faltantes or (jugador in self.entregados.values() and not self.config.get("aportes_libres")):
            return self.objetivos["caldero"]
        reservados = {m for i, m in self.cargas.items() if i != jugador and i in jugadores}
        material = next((m for m in faltantes if m not in reservados), None)
        if material is None:
            if self.config.get("objetos_unicos"):
                return dict(self.destino, nombre=self.config["lugar"])
            material = faltantes[0]
        return dict(self.fuente(material), nombre="Recoger " + self.nombre(material))

    @property
    def sitio(self):
        """[x, y] de la obra terminada (su bandera verde): el puente, las familias, el archivo."""
        clave = self.config.get("sitio")
        sitio = next((dict(o) for o in self._lista_objetivos if o["id"] == clave), dict(self.destino))
        if "bandera" in sitio:  # el Puente 1 la lleva en medio del puente
            sitio["x"], sitio["y"] = sitio.pop("bandera")
        else:  # a un lado del personaje que está allí, para que no la tape
            dx, dy = self.config.get("desvio_bandera", (0, 0))
            sitio["x"], sitio["y"] = sitio["x"] + dx, sitio["y"] + dy
        return [sitio["x"], sitio["y"]]

    def obra(self):
        """Lo justo para la bandera de una obra terminada: viaja en cada estado de red."""
        return {"efecto": self.config["efecto"], "sitio": self.sitio, "completo": True}

    def publico(self):
        return {"titulo": self.config["titulo"], "motivo": self.config["motivo"],
                "requiere_puente": bool(self.config.get("requiere_puente")), "materiales_colocados": self.materiales_colocados,
                "materiales": [{"id": m, "nombre": nombre, "fuente": dict(self.fuente(m)), "entregado": m in self.entregados}
                               for m, nombre, _ in self.config["materiales"]],
                "destino": dict(self.destino, nombre=self.config["lugar"]), "completo": self.completo,
                "materiales_listos": self.materiales_listos,
                "actividad": {"ayudante": self.ayudante, "progreso": self.progreso, "total": self.total_actividad,
                              "verbo": ("Colocar una tabla", "Repartir una cesta")[ENCARGOS.index(self.config)]},
                "reparto": {"familias": [dict(f, servida=f["id"] in self.servidas) for f in self.familias],
                            "cestas": sorted(self.cestas)} if self.reparto else None,
                "efecto": self.config["efecto"], "cargas": dict(self.cargas), "sitio": self.sitio,
                # Quién ya aportó y si una sola persona puede aportarlo todo (lo usan los bots).
                "aportantes": sorted(set(self.entregados.values())), "aportes_libres": bool(self.config.get("aportes_libres"))}
