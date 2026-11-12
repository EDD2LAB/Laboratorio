"""Ciudad Núcleo (Era III): reconfigurar a NÚCLEO y devolver la supervisión a las personas (sin Pygame).

El administrador del sistema le dio a NÚCLEO el control absoluto sin autorización
del consejo humano. Tres terminales devuelven el acceso; luego el equipo decide.
"""
from collections import Counter
import math

from logica.grafo_fisico import GrafoFisico

from .dialogos import identificador_npc
from .presentacion import aplicar_efectos, tipo_pocion, estado_votacion
from .expediente import campos_legales, ficha_resuelta

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
    ("conexiones", "entrada_estacion_mensajero", "Restaurar conexiones", "El sector aislado volvió a la red de la ciudad."),
    ("archivos", "entrada_sede_aspirante", "Revisar archivos", "La orden que autorizaba a NÚCLEO era falsa: la firmó él mismo."),
    ("llave", "entrada_verificacion", "Llave de supervisión", "La llave devolvió la supervisión de NÚCLEO a las personas."),
    ("cuentas", "entrada_centro_comunitario", "Ataque coordinado", "Las cuentas eran de NÚCLEO. El Ciudadano no estaba solo contra la ciudad: estaba contra una máquina."),
)
LLAVE = "llave_supervision"
FIRMA = "firma_representante"
GUIA_FIRMAS = "guia_de_firmas"
TEXTO_LLAVE = "El Corredor de Datos te entregó la llave de supervisión. Llévala al Centro de Verificación."
TEXTOS_PISTA = {
    GUIA_FIRMAS: ("Archivista · Cómo leer un registro", "Una orden vale si la firma quien tiene autoridad para darla. Mira primero la firma y luego la fecha."),
    FIRMA: ("Representante Humano · Firma", "El Representante Humano acepta firmar la reconfiguración: NÚCLEO seguirá, pero bajo supervisión."),
}
# NPC -> entrada existente junto a la que está y la pista que entrega.
NPCS = {"Corredor de Datos": ("entrada_cafe_digital", LLAVE), "Ciudadano Conectado": ("entrada_centro_comunitario", None),
        "Archivista": ("entrada_sede_aspirante", GUIA_FIRMAS), "Representante Humano": ("entrada_campana_ronaldo", FIRMA)}
# Barrera de NÚCLEO en las entradas que no son terminales.
ENTRADAS_CON_BARRERA = ("entrada_cafe_digital", "entrada_influencer", "entrada_campana_ronaldo", "entrada_centro_comunitario")
VELOCIDAD_PULSO = 60.0
RADIO_PULSO = 16
SEGUNDOS_IMPULSO = 6
IMPULSO_VELOCIDAD = 1.5
CUENTAS = (
    {"id": "voz_1", "avatar": 0, "nombre": "@ciudad_segura_01", "creada": "Creada hoy · 0 seguidores reales",
     "publicaciones": [("03:12:07", "Ese ciudadano miente sobre NÚCLEO."), ("03:40:07", "NÚCLEO nos protege a todos.")]},
    {"id": "voz_2", "avatar": 1, "nombre": "@ciudad_segura_02", "creada": "Creada hoy · 0 seguidores reales",
     "publicaciones": [("03:12:07", "Ese ciudadano engaña sobre NÚCLEO."), ("03:40:07", "NÚCLEO nos cuida a todos.")]},
    {"id": "voz_3", "avatar": 2, "nombre": "@orden_y_calma_7", "creada": "Creada hoy · 0 seguidores reales",
     "publicaciones": [("03:12:07", "Ese ciudadano exagera sobre NÚCLEO."), ("03:40:07", "NÚCLEO nos salva a todos.")]},
    {"id": "vecina", "avatar": 3, "nombre": "@vecina_del_muelle", "creada": "Desde hace 6 años · 214 seguidores",
     "publicaciones": [("08:21:40", "No comparto su protesta, pero tiene derecho a hacerla."), ("19:05:12", "¿Alguien sabe cuándo abren el Muelle?")]},
)
CUENTA_REAL = "vecina"
CUENTAS_AUTOMATICAS = {c["id"] for c in CUENTAS} - {CUENTA_REAL}


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
    if tarea == "cuentas":
        return {"cuentas": sorted(CUENTAS_AUTOMATICAS if not falla else {CUENTA_REAL, "voz_1", "voz_2"})}
    return {}


def _ruta_pulso(ruta, rect):
    """Puntos en el lienzo y largo de su recorrido a velocidad constante."""
    x0, y0, ancho, alto = rect
    puntos = [(x0 + p["rx"] * ancho, y0 + p["ry"] * alto) for p in ruta["points"]]
    if ruta["pattern"] == "ping_pong":
        puntos = puntos + puntos[-2:0:-1]
    return puntos + puntos[:1]


def posicion_en_ruta(puntos, distancia):
    tramos = [(a, b, math.hypot(b[0] - a[0], b[1] - a[1])) for a, b in zip(puntos, puntos[1:])]
    distancia %= max(.001, sum(t[2] for t in tramos))
    for a, b, largo in tramos:
        if distancia <= largo and largo:
            avance = distancia / largo
            return a[0] + (b[0] - a[0]) * avance, a[1] + (b[1] - a[1]) * avance
        distancia -= largo
    return puntos[0]


class MisionNucleo:
    def __init__(self, colisiones, datos, indicadores, nuevo_evento, expediente=None):
        self.indicadores = indicadores
        self.nuevo_evento = nuevo_evento
        self.expediente = expediente
        hitboxes = {h.get("id"): h for h in datos.get("hitboxes", [])}
        ocupadas = []
        from logica.zonas_caminables import componente, ancla
        from .dimensiones_red import spawn_presente
        origen = colisiones.inicio_libre(*spawn_presente(datos))
        accesibles = componente(colisiones, origen)

        def sitio(entrada, respaldo=(480, 400)):
            hitbox = hitboxes.get(entrada)
            punto = respaldo
            if hitbox and "frente_rx" in hitbox:  # la calle justo delante de la puerta
                x0, y0, ancho, alto = datos["rect_mapa"]
                punto = (x0 + hitbox["frente_rx"] * ancho, y0 + hitbox["frente_ry"] * alto)
            elif hitbox and hitbox.get("type", "rect") == "rect":
                punto = ((hitbox["rx"] + hitbox["rw"] / 2) * 960, (hitbox["ry"] + hitbox["rh"]) * 720 + 12)
            x, y = ancla(accesibles, punto, ocupadas)
            ocupadas.append((x, y))
            return round(x), round(y)

        self.objetivos = []
        self.edificios = {}
        for tarea, entrada, titulo, _ in TERMINALES:
            if tarea == "cuentas":
                continue  # es el propio Ciudadano Conectado
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
            if nombre == "Ciudadano Conectado":
                self.objetivos.append({"id": "futuro:cuentas", "nombre": "Ciudadano Conectado · cuentas", "tipo": "fuente", "tarea": "cuentas",
                                       "pista": "cuentas", "dimension": "futuro", "x": x, "y": y})
        x, y = sitio("pantalla_publica_presente", (480, 300))
        self.pantalla = {"id": "futuro:pantalla", "nombre": "Pantalla central · decidir", "tipo": "caldero",
                         "dimension": "futuro", "x": x, "y": y}
        self.objetivos.append(self.pantalla)
        self.barreras = [[round(hitboxes[e]["rx"] * 960), round(hitboxes[e]["ry"] * 720), round(hitboxes[e]["rw"] * 960), round(hitboxes[e]["rh"] * 720)]
                         for e in ENTRADAS_CON_BARRERA if e in hitboxes]
        self.barreras_evento = None
        rect = datos.get("rect_mapa") or (0, 0, 960, 720)
        self.rutas_pulso = [_ruta_pulso(r, rect) for r in datos.get("npc_routes", {}).values()]
        self.reloj = 0.0
        self.avisar = lambda receptores, texto, tipo="info": None
        self.habilidades_usadas = set()
        self.impulso_hasta = {}
        self.registro_resaltado = None
        self.cuenta_descartada = None
        self.comunicado = None
        self.tareas = {}  # tarea -> quién la completó
        self.halladas = {}  # la llave del Corredor de Datos
        self.votos = {}
        self.resultado = None
        from .final_cooperativo import FinalCooperativo
        self.final = FinalCooperativo(self.objetivos)

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
        if tarea == "conexiones" and self.barreras_evento is None:
            self.barreras_evento = self.nuevo_evento()
        return next(t[3] for t in TERMINALES if t[0] == tarea)

    @property
    def barreras_activas(self):
        return "conexiones" not in self.tareas

    @property
    def portador(self):
        return self.halladas.get(LLAVE)

    def posiciones_pulsos(self):
        return [posicion_en_ruta(ruta, self.reloj * VELOCIDAD_PULSO) for ruta in self.rutas_pulso]

    def actualizar(self, segundos, jugadores):
        """Los pulsos recorren sus rutas; si tocan al portador, la llave vuelve al Corredor."""
        self.reloj += max(0, min(segundos, 1))
        portador = jugadores.get(self.portador) if self.portador else None
        if portador is None or portador.get("dimension") != "futuro" or portador.get("interior") or "llave" in self.tareas:
            return
        if any(math.hypot(portador["x"] - x, portador["y"] - y) <= RADIO_PULSO for x, y in self.posiciones_pulsos()):
            quien = self.halladas.pop(LLAVE)
            self.avisar([quien], "Un pulso de NÚCLEO detectó la llave. Volvió al Corredor de Datos.", "info")

    def factor_impulso(self, identificador):
        return IMPULSO_VELOCIDAD if self.impulso_hasta.get(identificador, 0) > self.reloj else 1.0

    def habilidad(self, identificador, jugador, cerca):
        """El poder de cada rol en esta era; una vez por partida."""
        if identificador in self.habilidades_usadas:
            raise ValueError("Ya usaste tu poder en Ciudad Núcleo.")
        rol = jugador["rol"]
        if rol == "guardian":
            self._objetivo(jugador, "futuro:archivos", cerca)
            self.registro_resaltado = REGISTRO_FALSO
            mensaje = "La Lupa de Memoria resalta una firma sospechosa."
        elif rol == "mensajero":
            if self.portador != identificador:
                raise ValueError("El Impulso del Viento funciona mientras llevas la llave.")
            self.impulso_hasta[identificador] = self.reloj + SEGUNDOS_IMPULSO
            mensaje = "¡Impulso del Viento! Corre hasta la terminal."
        elif rol == "habitante":
            self._objetivo(jugador, "futuro:cuentas", cerca)
            self.cuenta_descartada = CUENTA_REAL
            mensaje = "La Voz Comunitaria reconoce a una vecina real entre las cuentas."
        else:
            if not (self.resultado and self.resultado["correcto"]):
                raise ValueError("El Comunicado Público llega después de la decisión correcta.")
            grafo = grafo_con(1)
            ruta = [s[1] for s in SECTORES if grafo.bfs(SECTORES[0][0], s[0]) is not None]
            aplicar_efectos(self.indicadores, {"confianza": 4})
            self.comunicado = {"evento_id": self.nuevo_evento(), "ruta": ruta}
            mensaje = "El comunicado recorrió la red: " + " → ".join(ruta) + "."
        self.habilidades_usadas.add(identificador)
        return {"mensaje": mensaje}

    def interactuar(self, identificador, jugador, clave, cerca):
        objetivo = self._objetivo(jugador, clave, cerca)
        if objetivo["tipo"] != "fuente":
            if self.completada:
                if self.final.fase != "victoria":
                    return {"mensaje": "Recuperemos el control juntos.", "vista": "final_cooperativo"}
                return {"mensaje": "Pueden volver a Distrito Conecta cuando quieran.", "vista": "portal"}
            if not self.tareas_listas:
                faltan = len(TERMINALES) - len(self.tareas)
                return {"mensaje": f"NÚCLEO no acepta órdenes: faltan {faltan} terminales.", "titulo": "Pantalla central", "vista": "fuente"}
            aviso = "Elijan juntos qué hacer con NÚCLEO." if FIRMA in self.halladas else "Para reconfigurarlo hace falta hablar antes con el Representante Humano."
            return {"mensaje": aviso, "vista": "caldero"}
        tarea = objetivo["tarea"]
        if tarea in self.tareas:
            return {"mensaje": self._completar(identificador, tarea), "titulo": objetivo["nombre"], "vista": "fuente"}
        if tarea == "llave":
            if self.portador is None:
                return {"mensaje": "Falta la llave de supervisión. La tiene el Corredor de Datos.", "titulo": objetivo["nombre"], "vista": "fuente"}
            if self.portador != identificador:
                return {"mensaje": "La llave la lleva otro compañero: debe traerla hasta aquí.", "titulo": objetivo["nombre"], "vista": "fuente"}
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
            if self.portador != identificador:
                raise ValueError("Falta la llave de supervisión.")
        elif tarea == "cuentas":
            cuentas = solicitud.get("cuentas")
            if (type(cuentas) is not list or len(set(map(str, cuentas))) != len(cuentas) or any(type(c) is not str for c in cuentas)
                    or not set(cuentas) <= {c["id"] for c in CUENTAS}):
                raise ValueError("Marca cuentas de la lista, sin repetir.")
            if set(cuentas) != CUENTAS_AUTOMATICAS:
                return {"mensaje": "Compara la hora, las frases y la fecha de creación: una cuenta no encaja."}
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
        if opcion == CORRECTA and FIRMA not in self.halladas:
            raise ValueError("Antes de reconfigurar a NÚCLEO hablen con el Representante Humano.")
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
                          "tipo_pocion": tipo_pocion(opcion), "evento_id": self.nuevo_evento(),
                          **campos_legales(ficha_resuelta(CASO))}
        self.votos.clear()
        if self.completada:
            self.final.preparar(self.resultado["evento_id"])
        if self.completada and self.expediente is not None:
            pruebas = [{"id": t[0], "titulo": t[2], "texto": t[3]} for t in TERMINALES]
            self.expediente.registrar(CASO, TITULO, self.resultado, pruebas)

    def clasificar(self, identificador, opcion):
        raise ValueError("NÚCLEO no se clasifica: decidan qué hacer con él.")

    def publico(self, presentes):
        return {"objetivos": [dict(o) for o in self.objetivos], "edificios": self.edificios,
                "desafio_final": self.final.publico(),
                "pistas": len(self.tareas), "total_pistas": len(TERMINALES),
                "titulo": TITULO, "noticia": NOTICIA, "evento": {"id": CASO, "tipo": "nucleo", "indice": 0, "total": 1},
                "tareas": sorted(self.tareas), "opciones": dict(OPCIONES), "tipos_pocion": {o: tipo_pocion(o) for o in OPCIONES},
                "votos_emitidos": sum(i in self.votos for i in presentes), "votantes": len(presentes),
                **estado_votacion(self.votos, presentes, self.resultado),
                "resultado": dict(self.resultado) if self.resultado else None, "completada": self.completada,
                "fin": self.completada, "sin_clasificacion": True,
                "portador": self.portador, "pulsos": [[round(x), round(y)] for x, y in self.posiciones_pulsos()],
                "barreras": self.barreras, "barreras_activas": self.barreras_activas, "barreras_evento": self.barreras_evento,
                "registro_resaltado": self.registro_resaltado, "cuenta_descartada": self.cuenta_descartada,
                "comunicado": self.comunicado, "cuentas": [dict(c) for c in CUENTAS] if not self.completada else [],
                "red": None if self.completada else {"sectores": [list(s) for s in SECTORES], "abiertas": [list(a) for a in ARISTAS_ABIERTAS],
                        "bloqueadas": [list(a) for a in ARISTAS_BLOQUEADAS]},
                "registros": [dict(r) for r in REGISTROS] if not self.completada else []}

    def privado(self, identificador):
        inventario = [{"id": t[0], "titulo": t[2] + " · Terminal", "texto": t[3]} for t in TERMINALES if t[0] in self.tareas]
        if LLAVE in self.halladas:
            inventario.append({"id": LLAVE, "titulo": "Corredor de Datos · Llave", "texto": TEXTO_LLAVE})
        inventario += [{"id": clave, "titulo": titulo, "texto": texto} for clave, (titulo, texto) in TEXTOS_PISTA.items() if clave in self.halladas]
        return {"inventario": inventario, "voto": self.votos.get(identificador), "clasificacion": None,
                "habilidad_usada": identificador in self.habilidades_usadas}
