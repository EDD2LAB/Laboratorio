"""Ciudad Núcleo (Era III): reconfigurar a NÚCLEO y devolver la supervisión a las personas (sin Pygame).

El administrador del sistema le dio a NÚCLEO el control absoluto sin autorización
del consejo humano. Tres terminales devuelven el acceso; luego el equipo decide.
"""
from collections import Counter

from logica.grafo_fisico import GrafoFisico

from .dialogos import identificador_npc
from .presentacion import aplicar_efectos, tipo_pocion

CASO = "nucleo_control"
TITULO = "NÚCLEO tomó el control"
NOTICIA = ("Sin permiso del consejo humano, le dieron a NÚCLEO el control absoluto. Bloqueó sectores y sus cuentas "
           "automáticas atacan a un Ciudadano Conectado que protesta.")

OPCIONES = {
    "verificar": "Reconfigurar a NÚCLEO con supervisión humana",
    "reportar": "Desconectarlo a la fuerza",
    "dejar_pendiente": "Dejarlo como está",
    "compartir": "Darle aún más control",
}
CORRECTA = "verificar"
EFECTOS = {
    "verificar": {"sabiduria": 6, "confianza": 5, "armonia": 4, "susurros_falsos": -4, "desinformacion": -6},
    "reportar": {"confianza": -3, "armonia": -3, "desinformacion": 2},
    "dejar_pendiente": {"confianza": -2},
    "compartir": {"confianza": -8, "armonia": -6, "susurros_falsos": 6, "desinformacion": 10},
}
TEXTOS = {
    "verificar": "NÚCLEO sigue ayudando a la ciudad, pero ahora las personas supervisan sus decisiones.",
    "reportar": "Apagarlo de golpe dejó sin servicio a media ciudad. El problema era la falta de control humano.",
    "dejar_pendiente": "NÚCLEO sigue sin supervisión y los sectores continúan bloqueados.",
    "compartir": "Con aún más poder, NÚCLEO decide por todos y ya nadie puede revisar sus órdenes.",
}

# (id, nombre, x, y) con posición relativa para dibujar el grafo.
SECTORES = (("plaza", "Plaza", .14, .3), ("mercado", "Mercado", .38, .14), ("archivo", "Archivo", .38, .52),
            ("torre", "Torre", .6, .3), ("puerto", "Puerto", .86, .2), ("barrio", "Barrio", .68, .78),
            ("muelle", "Muelle", .9, .68))
ARISTAS_ABIERTAS = (("plaza", "mercado"), ("mercado", "archivo"), ("mercado", "torre"), ("puerto", "barrio"), ("barrio", "muelle"))
# El sector del Puerto quedó aislado: solo una de estas conexiones lo devuelve a la red.
ARISTAS_BLOQUEADAS = (("plaza", "archivo"), ("torre", "puerto"), ("puerto", "muelle"))
REGISTROS = (
    {"id": "acta", "titulo": "Acta del consejo", "texto": "NÚCLEO asesora; toda decisión la firma el consejo humano.", "firma": "Firmas: 3 consejeras"},
    {"id": "bitacora", "titulo": "Bitácora técnica", "texto": "03:12 El administrador amplió los permisos de NÚCLEO.", "firma": "Firmas: registro del sistema"},
    {"id": "orden", "titulo": "Orden de autorización", "texto": "El consejo aprobó por unanimidad el control absoluto.", "firma": "Firmas: la propia cuenta de NÚCLEO"},
)
REGISTRO_FALSO = "orden"

# tarea, entrada del JSON, título, texto al completarla.
TERMINALES = (
    ("conexiones", "entrada_centro_comunicaciones", "Restaurar conexiones", "El sector aislado volvió a la red de la ciudad."),
    ("archivos", "entrada_alcaldia", "Revisar archivos", "La orden que autorizaba a NÚCLEO era falsa: la firmó él mismo."),
    ("llave", "entrada_centro_verificacion", "Llave de supervisión", "La llave devolvió la supervisión de NÚCLEO a las personas."),
)
LLAVE = "llave_supervision"
TEXTO_LLAVE = "El Corredor de Datos te entregó la llave de supervisión. Llévala al Centro de Verificación."
# NPC -> entrada existente junto a la que está.
NPCS = {"Corredor de Datos": ("entrada_estudio_lia", LLAVE), "Ciudadano Conectado": ("entrada_centro_comunitario", None)}


def grafo_con(abierta_extra=None):
    grafo = GrafoFisico([{"id": s[0], "nombre": s[1], "posicion": s[2:]} for s in SECTORES])
    for indice, (a, b) in enumerate(ARISTAS_ABIERTAS):
        grafo.agregar_puente({"id": "abierta" + str(indice), "origen": a, "destino": b})
    for indice, (a, b) in enumerate(ARISTAS_BLOQUEADAS):
        grafo.agregar_puente({"id": "bloqueada" + str(indice), "origen": a, "destino": b,
                              "estado": "normal" if indice == abierta_extra else "bloqueado"})
    return grafo


def red_conectada(grafo):
    """BFS: todos los sectores alcanzables desde la Plaza."""
    return all(grafo.bfs(SECTORES[0][0], s[0]) is not None for s in SECTORES)


def intento_bot(tarea, aleatorio, acierto):
    """Respuesta con la que un bot resuelve su terminal, acertando con probabilidad ``acierto``."""
    falla = aleatorio.random() >= acierto
    if tarea == "conexiones":
        return {"arista": 0 if falla else 1}
    if tarea == "archivos":
        return {"registro": "acta" if falla else REGISTRO_FALSO}
    return {}


class MisionNucleo:
    def __init__(self, colisiones, datos, indicadores, nuevo_evento, expediente=None):
        self.indicadores = indicadores
        self.nuevo_evento = nuevo_evento
        self.expediente = expediente
        hitboxes = {h.get("id"): h for h in datos.get("hitboxes", [])}
        ocupadas = []

        def sitio(entrada, respaldo=(480, 400)):
            hitbox = hitboxes.get(entrada)
            punto = respaldo
            if hitbox and hitbox.get("type", "rect") == "rect":
                punto = ((hitbox["rx"] + hitbox["rw"] / 2) * 960, (hitbox["ry"] + hitbox["rh"]) * 720 + 12)
            x, y = colisiones.inicio_libre(*punto, ocupadas)
            ocupadas.append((x, y))
            return round(x), round(y)

        self.objetivos = []
        for tarea, entrada, titulo, _ in TERMINALES:
            x, y = sitio(entrada)
            self.objetivos.append({"id": "futuro:" + tarea, "nombre": "Terminal · " + titulo, "tipo": "fuente", "tarea": tarea,
                                   "pista": tarea, "dimension": "futuro", "x": x, "y": y})
        self.npcs = []
        for nombre, (entrada, pista) in NPCS.items():
            x, y = sitio(entrada)
            npc = {"id": identificador_npc(nombre), "nombre": nombre, "dimension": "futuro", "x": x, "y": y}
            if pista:
                npc["pista"] = pista
            self.npcs.append(npc)
        x, y = sitio("pantalla_publica_presente", (480, 300))
        self.pantalla = {"id": "futuro:pantalla", "nombre": "Pantalla central · decidir", "tipo": "caldero",
                         "dimension": "futuro", "x": x, "y": y}
        self.objetivos.append(self.pantalla)
        self.tareas = {}  # tarea -> quién la completó
        self.halladas = {}  # la llave del Corredor de Datos
        self.votos = {}
        self.resultado = None

    @property
    def completada(self):
        return bool(self.resultado and self.resultado["opcion"] != "dejar_pendiente")

    @property
    def tareas_listas(self):
        return len(self.tareas) == len(TERMINALES)

    def _objetivo(self, jugador, clave, cerca):
        objetivo = next((o for o in self.objetivos if o["id"] == clave), None)
        if objetivo is None or not cerca(jugador, objetivo):
            raise ValueError("Acércate a la luz y pulsa E.")
        return objetivo

    def _completar(self, identificador, tarea):
        self.tareas.setdefault(tarea, identificador)
        return next(t[3] for t in TERMINALES if t[0] == tarea)

    def interactuar(self, identificador, jugador, clave, cerca):
        objetivo = self._objetivo(jugador, clave, cerca)
        if objetivo["tipo"] != "fuente":
            if self.completada:
                return {"mensaje": "Pueden volver a Distrito Conecta cuando quieran.", "vista": "portal"}
            if not self.tareas_listas:
                faltan = len(TERMINALES) - len(self.tareas)
                return {"mensaje": f"NÚCLEO no acepta órdenes: faltan {faltan} terminales.", "titulo": "Pantalla central", "vista": "fuente"}
            return {"mensaje": "Elijan juntos qué hacer con NÚCLEO.", "vista": "caldero"}
        tarea = objetivo["tarea"]
        if tarea in self.tareas:
            return {"mensaje": self._completar(identificador, tarea), "titulo": objetivo["nombre"], "vista": "fuente"}
        if tarea == "llave":
            if LLAVE not in self.halladas:
                return {"mensaje": "Falta la llave de supervisión. La tiene el Corredor de Datos.", "titulo": objetivo["nombre"], "vista": "fuente"}
            return {"mensaje": self._completar(identificador, tarea), "titulo": objetivo["nombre"], "vista": "fuente"}
        return {"mensaje": "Terminal abierta.", "titulo": objetivo["nombre"], "vista": "terminal", "terminal": tarea}

    def resolver_tarea(self, identificador, jugador, solicitud, cerca):
        tarea = solicitud.get("terminal")
        self._objetivo(jugador, "futuro:" + str(tarea), cerca)
        if tarea in self.tareas:
            return {"mensaje": "Esa terminal ya está resuelta."}
        if tarea == "conexiones":
            arista = solicitud.get("arista")
            if type(arista) is not int or not 0 <= arista < len(ARISTAS_BLOQUEADAS):
                raise ValueError("Elige una conexión bloqueada.")
            if not red_conectada(grafo_con(arista)):
                return {"mensaje": "Esa conexión no devuelve el sector aislado a la red. Prueba otra."}
        elif tarea == "archivos":
            if solicitud.get("registro") not in {r["id"] for r in REGISTROS}:
                raise ValueError("Elige uno de los registros.")
            if solicitud["registro"] != REGISTRO_FALSO:
                return {"mensaje": "Ese registro está firmado por quien debe. Revisa las firmas."}
        elif tarea == "llave":
            if LLAVE not in self.halladas:
                raise ValueError("Falta la llave de supervisión.")
        else:
            raise ValueError("Terminal desconocida.")
        return {"mensaje": "¡Terminal resuelta! " + self._completar(identificador, tarea), "vista": "cerrar"}

    def votar(self, identificador, jugador, opcion, presentes, cerca):
        self._objetivo(jugador, "futuro:pantalla", cerca)
        if self.completada:
            raise ValueError("NÚCLEO ya tiene una decisión.")
        if not self.tareas_listas:
            raise ValueError("Completen las tres terminales antes de decidir.")
        if opcion not in OPCIONES:
            raise ValueError("Decisión inválida.")
        self.votos[identificador] = opcion
        self.resolver(presentes)
        return {"mensaje": "¡El equipo decidió!" if self.resultado else "¡Ya elegiste! Espera a tu equipo."}

    def resolver(self, presentes):
        presentes = set(presentes)
        if self.completada or not presentes or not presentes.issubset(self.votos):
            return
        opcion, cantidad = Counter(self.votos[i] for i in presentes).most_common(1)[0]
        if cantidad <= len(presentes) / 2:
            return
        efectos = dict(EFECTOS[opcion])
        aplicar_efectos(self.indicadores, efectos)
        self.resultado = {"opcion": opcion, "correcto": opcion == CORRECTA, "texto": TEXTOS[opcion], "efectos": efectos,
                          "tipo_pocion": tipo_pocion(opcion), "evento_id": self.nuevo_evento()}
        self.votos.clear()
        if self.completada and self.expediente is not None:
            pruebas = [{"id": t[0], "titulo": t[2], "texto": t[3]} for t in TERMINALES]
            self.expediente.registrar(CASO, TITULO, self.resultado, pruebas)

    def clasificar(self, identificador, opcion):
        raise ValueError("NÚCLEO no se clasifica: decidan qué hacer con él.")

    def publico(self, presentes):
        return {"objetivos": [dict(o) for o in self.objetivos], "pistas": len(self.tareas), "total_pistas": len(TERMINALES),
                "titulo": TITULO, "noticia": NOTICIA, "evento": {"id": CASO, "tipo": "nucleo", "indice": 0, "total": 1},
                "tareas": sorted(self.tareas), "opciones": dict(OPCIONES), "tipos_pocion": {o: tipo_pocion(o) for o in OPCIONES},
                "votos_emitidos": sum(i in self.votos for i in presentes), "votantes": len(presentes),
                "resultado": dict(self.resultado) if self.resultado else None, "completada": self.completada,
                "fin": self.completada, "sin_clasificacion": True,
                "red": {"sectores": [list(s) for s in SECTORES], "abiertas": [list(a) for a in ARISTAS_ABIERTAS],
                        "bloqueadas": [list(a) for a in ARISTAS_BLOQUEADAS]},
                "registros": [dict(r) for r in REGISTROS]}

    def privado(self, identificador):
        inventario = [{"id": t[0], "titulo": t[2] + " · Terminal", "texto": t[3]} for t in TERMINALES if t[0] in self.tareas]
        if LLAVE in self.halladas:
            inventario.append({"id": LLAVE, "titulo": "Corredor de Datos · Llave", "texto": TEXTO_LLAVE})
        return {"inventario": inventario, "voto": self.votos.get(identificador), "clasificacion": None}
