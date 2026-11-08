"""Primera misión de Distrito Conecta en multijugador (sin Pygame).

Porta "a grandes rasgos" la misión ``contenido_sospechoso`` del modo de un
jugador: reunir las tres pistas (Darío Veraz, Tomás Red, Ronaldo Vélez),
decidir en la pantalla pública y clasificar la publicación. Las pociones son
de La Copa; ``tipo_pocion`` se sigue publicando por compatibilidad de protocolo.
"""
from collections import Counter

from . import clasificacion
from .presentacion import aplicar_efectos, tipo_pocion

PISTAS = (
    # pista, personaje, entrada del JSON, título, texto (mismos textos del códice).
    ("fuente_ausente", "Darío Veraz", "entrada_centro_verificacion", "Fuente original",
     "No se encontró el archivo original; hay patrones compatibles con IA."),
    ("testimonio_y_contexto", "Tomás Red", "entrada_centro_comunitario", "Testimonio y contexto",
     "El testigo no presenció el hecho ni conoce quién subió el archivo."),
    ("respuesta_kael", "Ronaldo Vélez", "entrada_alcaldia", "Agenda de Ronaldo",
     "La agenda de Ronaldo lo sitúa en un debate, no en el lugar de la imagen."),
)

OPCIONES = {
    "verificar": "Verificar con las pistas antes de publicar",
    "reportar": "Reportar la publicación",
    "dejar_pendiente": "Dejarla pendiente por ahora",
    "compartir": "Compartirla ya: se ve real",
}
CORRECTA = "verificar"
# Efectos de logica_juego.resolver_mision_presente (claves del multijugador).
# "compartir" no existe en el modo de un jugador: es la opción COLGAR.
EFECTOS = {
    "verificar": {"sabiduria": 5, "confianza": 3, "armonia": 2, "susurros_falsos": -3, "desinformacion": -5},
    "reportar": {"confianza": -2, "desinformacion": -3},
    "dejar_pendiente": {"sabiduria": 2},
    "compartir": {"confianza": -6, "armonia": -4, "susurros_falsos": 6, "desinformacion": 8},
}
TEXTOS = {
    "verificar": "La publicación está verificada: la imagen fue generada con IA y no prueba nada contra Ronaldo.",
    "reportar": "Reportaron la publicación. Frena su difusión, pero la comunidad todavía no sabe por qué era falsa.",
    "dejar_pendiente": "La dejaron pendiente. No se difundió, pero sigue circulando sin aclaración.",
    "compartir": "Se compartió una imagen generada con IA. La acusación falsa se volvió viral.",
}
EFECTOS_CLASIFICACION = {
    True: {"sabiduria": 8, "confianza": 3, "desinformacion": -5, "susurros_falsos": -3},
    False: {"sabiduria": -6, "confianza": -5, "desinformacion": 6, "susurros_falsos": 4},
}
EVENTO = "publicacion_presente"


class MisionPresente:
    def __init__(self, colisiones, datos, indicadores, nuevo_evento):
        self.indicadores = indicadores  # mismo diccionario del equipo
        self.nuevo_evento = nuevo_evento
        hitboxes = {h.get("id"): h for h in datos.get("hitboxes", [])}
        self.objetivos = []
        ocupadas = []
        for pista, personaje, entrada, titulo, _ in PISTAS:
            x, y = self._frente(hitboxes.get(entrada), (480, 400))
            x, y = colisiones.inicio_libre(x, y, ocupadas)
            ocupadas.append((x, y))
            self.objetivos.append({"id": "presente:" + pista, "nombre": personaje + " · " + titulo, "tipo": "fuente",
                                   "pista": pista, "dimension": "presente", "x": round(x), "y": round(y)})
        x, y = self._frente(hitboxes.get("pantalla_publica_presente"), (480, 300))
        x, y = colisiones.inicio_libre(x, y, ocupadas)
        self.objetivos.append({"id": "presente:pantalla", "nombre": "Pantalla pública · decidir", "tipo": "caldero",
                               "dimension": "presente", "x": round(x), "y": round(y)})
        self.halladas = {}
        self.votos = {}
        self.resultado = None
        self.clasificaciones = {}

    @staticmethod
    def _frente(hitbox, respaldo):
        if not hitbox or hitbox.get("type", "rect") != "rect":
            return respaldo
        return ((hitbox["rx"] + hitbox["rw"] / 2) * 960, (hitbox["ry"] + hitbox["rh"]) * 720 + 12)

    @property
    def completada(self):
        return bool(self.resultado and self.resultado["opcion"] != "dejar_pendiente")

    def _objetivo(self, jugador, clave, cerca):
        objetivo = next((o for o in self.objetivos if o["id"] == clave), None)
        if objetivo is None or not cerca(jugador, objetivo):
            raise ValueError("Acércate a la luz y pulsa E.")
        return objetivo

    def interactuar(self, identificador, jugador, clave, cerca):
        objetivo = self._objetivo(jugador, clave, cerca)
        if objetivo["tipo"] == "fuente":
            pista = objetivo["pista"]
            datos = next(p for p in PISTAS if p[0] == pista)
            self.halladas.setdefault(pista, identificador)
            return {"mensaje": datos[4], "titulo": datos[1] + " · " + datos[3], "vista": "fuente"}
        if len(self.halladas) < len(PISTAS):
            faltan = len(PISTAS) - len(self.halladas)
            return {"mensaje": f"Investiguen antes de decidir: faltan {faltan} pistas.", "vista": "fuente",
                    "titulo": "Pantalla pública"}
        return {"mensaje": "Elijan juntos qué hacer con la publicación.",
                "vista": "resultado" if self.completada else "caldero"}

    def votar(self, identificador, jugador, opcion, presentes, cerca):
        self._objetivo(jugador, "presente:pantalla", cerca)
        if self.completada:
            raise ValueError("La publicación ya tiene una decisión.")
        if len(self.halladas) < len(PISTAS):
            raise ValueError("Reúnan las tres pistas antes de decidir.")
        if opcion not in OPCIONES:
            raise ValueError("Decisión inválida.")
        self.votos[identificador] = opcion
        self.resolver(presentes)
        if self.resultado:
            return {"mensaje": "¡El equipo decidió! Miren la consecuencia."}
        return {"mensaje": "¡Ya elegiste! Espera a tu equipo de Distrito Conecta."}

    def resolver(self, presentes):
        presentes = set(presentes)
        if self.completada or not presentes or not presentes.issubset(self.votos):
            return
        opcion, cantidad = Counter(self.votos[i] for i in presentes).most_common(1)[0]
        if cantidad <= len(presentes) / 2:
            return
        efectos = dict(EFECTOS[opcion])
        aplicar_efectos(self.indicadores, efectos)
        self.resultado = {"opcion": opcion, "correcto": opcion == CORRECTA, "texto": TEXTOS[opcion],
                          "efectos": efectos, "tipo_pocion": tipo_pocion(opcion), "evento_id": self.nuevo_evento()}
        self.votos.clear()

    def clasificar(self, identificador, opcion):
        if not self.resultado:
            raise ValueError("Primero decidan qué hacer con la publicación.")
        if identificador in self.clasificaciones:
            raise ValueError("Ya clasificaste esta publicación.")
        correcta = clasificacion.evaluar(EVENTO, opcion, "presente")
        efectos = dict(EFECTOS_CLASIFICACION[correcta])
        aplicar_efectos(self.indicadores, efectos)
        self.clasificaciones[identificador] = {"opcion": opcion, "correcta": correcta, "efectos": efectos,
                                               "categoria": clasificacion.ruta_evento(EVENTO)}
        return {"mensaje": "¡Correcto! Era contenido generado con IA." if correcta else
                "La imagen sí fue generada con IA.", "vista": "clasificacion_resultado"}

    def publico(self, presentes):
        return {"objetivos": [dict(o) for o in self.objetivos], "pistas": len(self.halladas), "total_pistas": len(PISTAS),
                "titulo": "Publicación viral sobre Ronaldo",
                "noticia": "Una imagen acusa a Ronaldo, pero su origen no está confirmado. Investiga antes de compartirla.",
                "opciones": dict(OPCIONES), "tipos_pocion": {o: tipo_pocion(o) for o in OPCIONES},
                "votos_emitidos": sum(i in self.votos for i in presentes), "votantes": len(presentes),
                "resultado": dict(self.resultado) if self.resultado else None, "completada": self.completada,
                "clasificacion_opciones": list(clasificacion.OPCIONES["presente"])}

    def privado(self, identificador):
        inventario = [{"id": p[0], "titulo": p[1] + " · " + p[3], "texto": p[4]} for p in PISTAS if p[0] in self.halladas]
        return {"inventario": inventario, "voto": self.votos.get(identificador),
                "clasificacion": self.clasificaciones.get(identificador)}
