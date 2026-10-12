"""Registro interno de los recorridos y transmisiones de una informacion."""


class PropagacionInformacion:
    """Conserva una historia de transmisiones sin mostrar el grafo al jugador."""

    COLORES = {
        "normal": (237, 185, 87),
        "verificada": (92, 220, 132),
        "rumor": (184, 112, 244),
        "falsa": (246, 83, 75),
    }

    def __init__(self, identificador, origen, tipo, verificada=False):
        if not identificador:
            raise ValueError("La informacion necesita un id.")
        if not origen:
            raise ValueError("La informacion necesita un origen.")
        if not tipo:
            raise ValueError("La informacion necesita un tipo.")

        self.id = str(identificador)
        self.origen = str(origen)
        self.tipo = str(tipo)
        self.verificada = bool(verificada)
        self.estado_verificacion = "verificada" if self.verificada else "pendiente"
        self.ruta = []
        self.transmisores = []
        self.destinatarios = []
        self.transmisiones = []
        self.decisiones = []
        self.alcance = 0

    def registrar_transmision(
        self, transmisor, receptor, ruta=(), medio="directo", plataforma_origen=None,
        plataforma_destino=None,
    ):
        """Registra un envio y el tramo de plataformas que recorrio."""
        if not transmisor or not receptor:
            raise ValueError("Una transmision necesita transmisor y receptor.")

        ruta = list(ruta or ())
        transmision = {
            "transmisor": str(transmisor),
            "receptor": str(receptor),
            "ruta": ruta,
            "medio": str(medio),
            "plataforma_origen": plataforma_origen,
            "plataforma_destino": plataforma_destino,
        }
        self.transmisiones.append(transmision)
        if transmisor not in self.transmisores:
            self.transmisores.append(str(transmisor))
        self.registrar_receptor(receptor)

        if ruta:
            inicio = 1 if self.ruta and self.ruta[-1] == ruta[0] else 0
            self.ruta.extend(ruta[inicio:])
        return transmision

    def registrar_receptor(self, receptor):
        """Agrega un destinatario una sola vez y actualiza el alcance."""
        if not receptor:
            raise ValueError("El receptor no puede estar vacio.")
        receptor = str(receptor)
        if receptor not in self.destinatarios:
            self.destinatarios.append(receptor)
        self.alcance = len(self.destinatarios)
        return self.alcance

    def registrar_verificacion(self, verificada):
        """Marca la informacion como confirmada o refutada."""
        self.verificada = bool(verificada)
        self.estado_verificacion = "verificada" if self.verificada else "falsa"
        return self.estado_verificacion

    def registrar_decision(self, accion, actor="Guardián", resultado=""):
        if not accion:
            raise ValueError("La decision necesita una accion.")
        decision = {
            "accion": str(accion),
            "actor": str(actor),
            "resultado": str(resultado),
        }
        self.decisiones.append(decision)
        return decision

    def marcar_como_rumor(self):
        """Marca una informacion no comprobada como rumor."""
        if self.estado_verificacion != "verificada":
            self.estado_verificacion = "rumor"
        return self.estado_verificacion

    def obtener_ruta(self):
        return list(self.ruta)

    def obtener_alcance(self):
        return self.alcance

    def color_visual(self):
        if self.estado_verificacion == "falsa":
            clave = "falsa"
        elif self.estado_verificacion == "verificada":
            clave = "verificada"
        elif self.estado_verificacion == "rumor" or self.tipo.casefold() == "rumor":
            clave = "rumor"
        else:
            clave = "normal"
        return self.COLORES[clave]

    def como_dict(self):
        """Devuelve una copia serializable del historial."""
        return {
            "id": self.id,
            "origen": self.origen,
            "tipo": self.tipo,
            "verificada": self.verificada,
            "estado_verificacion": self.estado_verificacion,
            "ruta": self.obtener_ruta(),
            "transmisores": list(self.transmisores),
            "destinatarios": list(self.destinatarios),
            "transmisiones": [dict(item, ruta=list(item["ruta"])) for item in self.transmisiones],
            "decisiones": [dict(item) for item in self.decisiones],
            "alcance": self.obtener_alcance(),
        }
