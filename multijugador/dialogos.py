"""Conversaciones con los NPC en el multijugador (sin Pygame).

Reutiliza logica.conversaciones con un adaptador del estado de la campaña. Cada
respuesta va solo a quien habló; lo visto se recuerda por jugador.
"""
import unicodedata

from logica.conversaciones import construir_conversacion

from . import clasificacion
from .presentacion import tipo_pocion

# Fragmento de la ruta del sprite colocado en el mapa -> personaje.
PATRONES_COPA = (("/naira/", "Naira"), ("/odran/", "Sabio de las Raices"), ("/darek/", "Darek"),
                 ("habitante mujer", "Luma"), ("habitante hombre", "Tarek"), ("aspirante mujer", "Mira"), ("aspirante hombre", "Kael"))
NOMBRES_CON_TILDE = {"Sabio de las Raices": "Sabio de las Raíces"}
# Quien juega un rol ya es ese personaje en Distrito Conecta.
PERSONAJE_DE_ROL = {"guardian": "Elías Vega", "mensajero": "Mateo Ríos", "habitante": "Tomás Red", "aspirante": "Ronaldo Vélez"}
VER_CUENTAS = "Ver las cuentas que te atacan"
CAMINOS = {"colgar": "Colgarla", "quemar": "Quemarla", "consultar": "Consultar", "ignorar": "Ignorarla"}


def _normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).replace("\\", "/").lower())
                   if unicodedata.category(c) != "Mn")


def personajes_elegidos(jugadores):
    """Personajes de La Copa que ya están en manos de alguien (sin apariencia: Kael y Tarek)."""
    elegidos = set()
    for jugador in jugadores:
        mujer = jugador.get("apariencia") == "mujer"
        if jugador.get("rol") == "aspirante":
            elegidos.add("Mira" if mujer else "Kael")
        elif jugador.get("rol") == "habitante":
            elegidos.add("Luma" if mujer else "Tarek")
    return elegidos


def identificador_npc(nombre):
    return _normalizar(nombre).replace(" ", "_")


def npcs_de_la_copa(datos_mapa):
    """NPC colocados en el mapa, en el mismo punto que sus objetivos."""
    npcs = []
    for objeto in datos_mapa.get("decoracion", []):
        ruta = _normalizar(objeto["name"])
        nombre = next((n for patron, n in PATRONES_COPA if patron in ruta), None)
        # Algunas carpetas de otros personajes están anidadas en «Aspirante hombre».
        if nombre == "Kael" and any(p in ruta for p in ("habitante", "guardian", "mensajero", "aspirante mujer")):
            continue
        if nombre:
            nombre = NOMBRES_CON_TILDE.get(nombre, nombre)
            npcs.append({"id": identificador_npc(nombre), "nombre": nombre, "dimension": "la_copa",
                         "x": round((objeto["x"] + objeto["w"] / 2) * 960), "y": round((objeto["y"] + objeto["h"]) * 720)})
    return npcs


class EstadoConversacion:
    """La interfaz de EstadoJuego que necesita construir_conversacion."""

    def __init__(self, campana):
        self.tablillas_resueltas = campana.ronda
        self._ruta = clasificacion.ruta_evento(campana.casos[campana.ronda][0])
        self._noticia = campana.casos[campana.ronda][2]
        resultado = campana.resultado or {}
        self.camino_decision_actual = [CAMINOS[tipo_pocion(resultado["opcion"])]] if resultado.get("opcion") else []
        self.historial_decisiones = [
            {"camino": [CAMINOS[tipo_pocion(decision["opcion"])]], "categoria": clasificacion.ruta_evento(campana.casos[indice][0])}
            for indice, decision in enumerate(campana.resumen) if decision.get("opcion")]

    def ruta_categoria_actual(self):
        return self._ruta

    def texto_actual(self):
        return self._noticia


class DialogosNPC:
    def __init__(self, campana, datos_mapa):
        self.campana = campana
        self.npcs_copa = npcs_de_la_copa(datos_mapa)
        self.vistas = {}  # jugador -> claves de conversación ya escuchadas
        self.abiertos = {}  # jugador -> {"npc", "clave", "respuestas"}

    def _visibles(self):
        presente = self.campana.presente
        elegidos = personajes_elegidos(self.campana.jugadores.values())
        npcs = [n for n in self.npcs_copa if n["nombre"] not in elegidos]
        if presente is not None:
            # Si alguien juega a quien tiene la pista, se le habla a ese jugador, esté donde esté.
            gemelos = {PERSONAJE_DE_ROL[j["rol"]]: j for j in self.campana.jugadores.values()}
            for npc in presente.npcs:
                jugador = gemelos.get(npc["nombre"])
                if jugador is None or (npc.get("pista") and jugador.get("dimension") != "presente"):
                    npcs.append(npc)  # quien lo juega está en otra era: el personaje sigue en su edificio
                elif npc.get("pista"):
                    npcs.append(dict(npc, x=round(jugador["x"]), y=round(jugador["y"]), jugador=jugador["id"],
                                     interior=jugador.get("interior")))
        if self.campana.futuro is not None:
            npcs += self.campana.futuro.npcs
        return npcs

    def publico(self):
        return self._visibles()

    def nombres_en_dialogo(self):
        """Personajes con alguien hablándoles ahora (cada jugador ve su diálogo)."""
        por_id = {n["id"]: n for n in self._visibles()}
        nombres = set()
        for jugador, abierto in self.abiertos.items():
            npc = por_id.get(abierto["npc"])
            if npc and self.campana.jugadores.get(jugador, {}).get("dimension", "la_copa") == npc["dimension"]:
                nombres.add(npc["nombre"])
        return sorted(nombres)

    def ejecutar(self, identificador, solicitud):
        if solicitud.get("accion") == "hablar_npc":
            return self._hablar(identificador, solicitud.get("npc"))
        return self._responder(identificador, solicitud.get("npc"), solicitud.get("respuesta"))

    def _hablar(self, identificador, npc_id):
        npc = next((n for n in self._visibles() if n["id"] == npc_id), None)
        if npc is None:
            raise ValueError("Ese personaje no está aquí.")
        if not self.campana._cerca(identificador, npc):
            raise ValueError("Acércate a " + npc["nombre"] + " para hablar.")
        vistas = self.vistas.setdefault(identificador, set())
        dialogo, clave = construir_conversacion(npc["nombre"], EstadoConversacion(self.campana), vistas)
        if npc["dimension"] == "presente" and npc.get("pista"):  # el personaje cuenta la pista de este caso
            dialogo = dict(dialogo, texto=self.campana.presente.texto_pista(npc["pista"]))
        if npc["nombre"] == "Ciudadano Conectado" and "cuentas" not in self.campana.futuro.tareas:
            dialogo = dict(dialogo, respuestas=[VER_CUENTAS, *dialogo["respuestas"]])
        self.abiertos[identificador] = {"npc": npc_id, "clave": clave, "respuestas": list(dialogo["respuestas"])}
        self._registrar_pista(identificador, npc)
        return {"mensaje": "", "vista": "dialogo_npc", "silencioso": True,
                "dialogo": dict(dialogo, npc=npc_id, event_id=self.campana.siguiente_evento())}

    def _registrar_pista(self, identificador, npc):
        """Si el testimonio es una pista del caso, queda una sola vez para el grupo."""
        campana = self.campana
        if npc["dimension"] != "la_copa":
            if npc.get("pista"):
                getattr(campana, npc["dimension"]).halladas.setdefault(npc["pista"], identificador)
            return
        jugador = campana.jugadores[identificador]
        propia = any(o.get("rol") == jugador["rol"] and (o["x"], o["y"]) == (npc["x"], npc["y"]) for o in campana.objetivos)
        if propia and campana.fase == "investigacion":
            campana._renovar_aviso(identificador)
            pista = "pista_" + jugador["rol"]
            campana.conocidas[identificador].add(pista)
            if pista not in campana.halladas:
                campana.halladas[pista] = identificador
                campana._avisar([identificador], "¡Encontraste una pista! Abre I para leerla y compartirla.")
                campana._registrar(f"{jugador['nombre']} registró una prueba de su fuente.")

    def _responder(self, identificador, npc_id, respuesta):
        abierto = self.abiertos.get(identificador)
        if abierto is None or abierto["npc"] != npc_id:
            raise ValueError("Esa conversación ya terminó.")
        if respuesta is not None and respuesta not in abierto["respuestas"]:
            raise ValueError("Esa respuesta no está disponible.")
        del self.abiertos[identificador]
        self.vistas.setdefault(identificador, set()).add(abierto["clave"])
        if respuesta == VER_CUENTAS:
            return {"mensaje": "Estas cuentas lo atacan. ¿Cuáles son automáticas?", "vista": "terminal", "terminal": "cuentas"}
        if respuesta == "Entrega el mensaje":
            return {"mensaje": "Elige a quién llevarle el mensaje.", "vista": "eco_mensajes"}
        if respuesta == "Consultar tablilla":
            caldero = next(o for o in self.campana.objetivos if o["id"] == "caldero")
            if self.campana._cerca(identificador, caldero):
                return {"mensaje": "Elijan juntos qué hacer con la tablilla.", "vista": "caldero"}
            return {"mensaje": "Ve al caldero central para revisar la tablilla."}
        return {"mensaje": "", "silencioso": True}
