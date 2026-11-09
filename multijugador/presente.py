"""Misión de Distrito Conecta: tres casos de contenido manipulado con IA (sin Pygame).

Video, nota de voz y foto se resuelven en orden con el mismo esquema: pistas,
análisis de marcas, decisión en el celular, clasificación y caso en el expediente.
Las pociones son de La Copa; ``tipo_pocion`` se sigue publicando por compatibilidad.
"""
import json
from collections import Counter
from pathlib import Path

from . import clasificacion
from .dialogos import identificador_npc
from .dimensiones_red import spawn_interior
from .presentacion import aplicar_efectos, tipo_pocion
from .expediente import campos_legales, ficha_resuelta

MARCAS = json.loads((Path(__file__).resolve().parents[1] / "datos" / "marcas_manipulacion.json").read_text(encoding="utf-8"))

OPCIONES = {
    "verificar": "Verificar con las pistas antes de publicar",
    "reportar": "Reportar la publicación",
    "dejar_pendiente": "Dejarla pendiente por ahora",
    "compartir": "Compartirla ya: se ve real",
}
CORRECTA = "verificar"
EFECTOS = {
    "verificar": {"sabiduria": 5, "confianza": 3, "armonia": 2, "susurros_falsos": -3, "desinformacion": -5},
    "reportar": {"confianza": -2, "desinformacion": -3},
    "dejar_pendiente": {"sabiduria": 2},
    "compartir": {"confianza": -6, "armonia": -4, "susurros_falsos": 6, "desinformacion": 8},
}
# Decir "verificado" sin haber terminado el análisis es tan irresponsable como compartir.
EFECTOS_SIN_ANALISIS = {"sabiduria": -3, "confianza": -4, "susurros_falsos": 3, "desinformacion": 4}
EFECTOS_CLASIFICACION = {
    True: {"sabiduria": 8, "confianza": 3, "desinformacion": -5, "susurros_falsos": -3},
    False: {"sabiduria": -6, "confianza": -5, "desinformacion": 6, "susurros_falsos": 4},
}
OTROS_NPC = {"Influencer": "Lía Nova", "Mensajero urbano": "Mateo Ríos"}
# Edificio -> dónde espera su personaje (proporción de la imagen del interior).
SITIOS_INTERIOR = {"centro_verificacion": (.72, .70), "estacion_mensajero": (.30, .72), "sede_aspirante": (.55, .66),
                   "cafe_digital": (.60, .74)}

EVENTOS = (
    {
        "id": "presente_video", "tipo": "video", "marcas": "video_manipulado", "minimo": 2,
        "etiqueta": "contenido_manipulado", "sello": "manipulado",
        "titulo": "El video de las donaciones",
        "noticia": "Un video muestra a Ronaldo Vélez sacando dinero de una caja de donaciones. ¿Es real?",
        "pistas": (
            # pista, personaje, edificio donde está, título, texto.
            ("fuente_ausente", "Darío Veraz", "centro_verificacion", "Fuente original",
             "Encontré el video original: Ronaldo mete monedas en la caja. Ya pueden compararlo en Analizar."),
            ("testimonio_y_contexto", "Tomás Red", "estacion_mensajero", "Testimonio y contexto",
             "El testigo no presenció el hecho ni conoce quién subió el archivo."),
            ("respuesta_kael", "Ronaldo Vélez", "sede_aspirante", "Agenda de Ronaldo",
             "La agenda de Ronaldo confirma que ese día hizo una donación pública."),
        ),
        "textos": {
            "verificar": "Verificado: el video está editado para mostrar lo contrario de lo que pasó. No prueba nada contra Ronaldo.",
            "reportar": "Reportaron el video. Frena su difusión, pero la comunidad no sabe por qué era falso.",
            "dejar_pendiente": "Lo dejaron pendiente. No se difundió, pero sigue circulando sin aclaración.",
            "compartir": "Se compartió un video manipulado. La acusación falsa se volvió viral.",
        },
        "sin_analisis": "Dijeron que estaba verificado sin terminar de compararlo con el original. Es igual de irresponsable.",
        "clasificacion": ("¡Correcto! Era contenido manipulado.", "El video fue manipulado a partir de uno real."),
    },
    {
        "id": "presente_voz", "tipo": "audio", "marcas": "audio_suplantado", "minimo": 2,
        "etiqueta": "contenido_ia", "sello": "suplantacion",
        "titulo": "La nota de voz",
        "noticia": "Circula una nota de voz en la que Ronaldo admitiría el robo. ¿De verdad es su voz?",
        "pistas": (
            ("audio_original", "Ronaldo Vélez", "sede_aspirante", "Audio original",
             "En la Sede guardamos la grabación auténtica de mi discurso. Compárenla con la nota de voz."),
        ),
        "textos": {
            "verificar": "Verificado: la voz fue clonada con IA. Ronaldo nunca dijo esas palabras.",
            "reportar": "Reportaron la nota de voz, pero no explicaron que era una voz clonada.",
            "dejar_pendiente": "La dejaron pendiente. La nota de voz sigue circulando.",
            "compartir": "Se compartió una voz clonada con IA. Muchos creyeron que era Ronaldo.",
        },
        "sin_analisis": "Dijeron que estaba verificada sin terminar de escucharla. Nadie sabe aún si la voz era real.",
        "clasificacion": ("¡Correcto! Es una suplantación.", "Alguien se hizo pasar por Ronaldo clonando su voz."),
    },
    {
        "id": "presente_foto", "tipo": "foto", "marcas": "foto_manipulada", "minimo": 3,
        "etiqueta": "contenido_manipulado", "sello": "manipulado",
        "titulo": "La foto del perfil falso",
        "noticia": "Un perfil con la cara de la Habitante conectada publica insultos y pide dinero a sus seguidores.",
        "pistas": (
            ("foto_original", "Elías Vega", "cafe_digital", "Foto original",
             "Esa selfie se tomó aquí, en el Café Digital. Tenemos la foto original para compararla."),
        ),
        "textos": {
            "verificar": "Verificado: la foto fue alterada y el perfil es falso. La víctima recupera su identidad.",
            "reportar": "Reportaron el perfil, pero sus seguidores no saben que la foto era falsa.",
            "dejar_pendiente": "Lo dejaron pendiente. El perfil falso sigue pidiendo dinero.",
            "compartir": "Se compartió el perfil falso. Más personas enviaron dinero a quien suplantaba a la víctima.",
        },
        "sin_analisis": "Dijeron que estaba verificado sin examinar la foto. El perfil falso sigue activo.",
        "clasificacion": ("¡Correcto! Es una suplantación.", "Usaron la cara de otra persona para hacerse pasar por ella."),
    },
)


def _numero(valor):
    return type(valor) in (int, float) and valor == valor


def marca_en(evento, datos):
    """Marca del evento que corresponde al punto señalado por el jugador, o None."""
    marcas = MARCAS[evento["marcas"]]["marcas"]
    if evento["tipo"] == "video":
        frame = datos.get("frame")
        if type(frame) is not int:
            raise ValueError("Señala un cuadro del video.")
        return next((m for m in marcas if frame in m["frames"]), None)
    if evento["tipo"] == "audio":
        zona, segundo = datos.get("zona"), datos.get("segundo")
        if zona is not None:
            return next((m for m in marcas if m.get("toda_la_pista") and m["id"] == zona), None)
        if not _numero(segundo):
            raise ValueError("Señala un instante del audio.")
        return next((m for m in marcas if "rango" in m and m["rango"][0] <= segundo <= m["rango"][1]), None)
    x, y = datos.get("x"), datos.get("y")
    if not _numero(x) or not _numero(y):
        raise ValueError("Señala un punto de la foto.")
    return next((m for m in marcas if m["rect"][0] <= x <= m["rect"][0] + m["rect"][2]
                 and m["rect"][1] <= y <= m["rect"][1] + m["rect"][3]), None)


def intento_bot(evento_id, encontradas, aleatorio, acierto):
    """Datos con los que un bot señala: acierta con probabilidad ``acierto``."""
    evento = next(e for e in EVENTOS if e["id"] == evento_id)
    marcas = [m for m in MARCAS[evento["marcas"]]["marcas"] if m["id"] not in encontradas]
    marca = aleatorio.choice(marcas) if marcas else None
    falla = marca is None or aleatorio.random() >= acierto
    if evento["tipo"] == "video":
        # Todos los cuadros tienen marca: fallar es volver a una ya encontrada.
        return {"frame": 0 if falla else marca["frames"][0]}
    if evento["tipo"] == "audio":
        if falla:
            return {"segundo": .2}  # primera frase: no hay ninguna marca puntual
        if marca.get("toda_la_pista"):
            return {"zona": marca["id"]}
        return {"segundo": sum(marca["rango"]) / 2}
    if falla:
        return {"x": .2, "y": .95}  # la chaqueta: fuera de todas las marcas
    x, y, ancho, alto = marca["rect"]
    return {"x": x + ancho / 2, "y": y + alto / 2}


class MisionPresente:
    def __init__(self, colisiones, datos, indicadores, nuevo_evento, expediente, interiores, edificios):
        self.indicadores = indicadores  # mismo diccionario del equipo
        self.nuevo_evento = nuevo_evento
        self.expediente = expediente
        hitboxes = {h.get("id"): h for h in datos.get("hitboxes", [])}
        x, y = colisiones.inicio_libre(*self._frente(hitboxes.get("pantalla_publica_presente"), (480, 300)))
        self.pantalla = {"id": "presente:pantalla", "nombre": "Pantalla pública · decidir", "tipo": "caldero",
                         "dimension": "presente", "x": round(x), "y": round(y)}
        self.edificios = {clave: dict(puerta, salida=self._salida(interiores[clave])) for clave, puerta in edificios.items()}
        # Quien tiene la pista espera dentro de su edificio.
        self.personajes_evento = [[self._personaje(interiores, pista, personaje, edificio) for pista, personaje, edificio, _, _ in evento["pistas"]]
                                  for evento in EVENTOS]
        # Quienes no dan pista están donde los puso el editor.
        rect = datos.get("rect_mapa") or (0, 0, 960, 720)
        self.npcs_fijos = []
        ocupadas = [(self.pantalla["x"], self.pantalla["y"])]
        for clave, nombre in OTROS_NPC.items():
            sitio = datos.get("npc_positions", {}).get(clave)
            if sitio:
                x, y = colisiones.inicio_libre(round(rect[0] + sitio["rx"] * rect[2]),
                                               round(rect[1] + (sitio["ry"] + sitio.get("rh", .12) / 2) * rect[3]), ocupadas)
                self.npcs_fijos.append({"id": identificador_npc(nombre), "nombre": nombre, "dimension": "presente",
                                        "x": round(x), "y": round(y)})
        self.indice = 0
        self.resueltos = []
        self._reiniciar_caso()

    def _reiniciar_caso(self):
        self.halladas = {}
        self.votos = {}
        self.resultado = None
        self.clasificaciones = {}
        self.marcas = {}
        self.analizando = set()
        self.conclusion_id = None
        self.listos = set()

    @staticmethod
    def _salida(interior):
        x, y = interior.inicio_libre(*spawn_interior(interior.datos))
        return {"x": round(x), "y": round(y)}

    @staticmethod
    def _personaje(interiores, pista, nombre, edificio):
        mapa = interiores[edificio]
        rx, ry = SITIOS_INTERIOR[edificio]
        izquierda, arriba, ancho, alto = mapa.datos["rect_mapa"]
        x, y = mapa.inicio_libre(izquierda + rx * ancho, arriba + ry * alto)
        return {"id": identificador_npc(nombre), "nombre": nombre, "dimension": "presente", "interior": edificio,
                "x": round(x), "y": round(y), "pista": pista}

    def texto_pista(self, pista):
        return next(p[4] for p in self.evento["pistas"] if p[0] == pista)

    @staticmethod
    def _frente(hitbox, respaldo):
        if not hitbox or hitbox.get("type", "rect") != "rect":
            return respaldo
        return ((hitbox["rx"] + hitbox["rw"] / 2) * 960, (hitbox["ry"] + hitbox["rh"]) * 720 + 12)

    @property
    def evento(self):
        return EVENTOS[self.indice]

    @property
    def objetivos(self):
        return [self.pantalla]

    @property
    def npcs(self):
        return self.personajes_evento[self.indice] + self.npcs_fijos

    @property
    def completada(self):
        return bool(self.resultado and self.resultado["opcion"] != "dejar_pendiente")

    @property
    def fin(self):
        return self.completada and self.indice == len(EVENTOS) - 1

    @property
    def concluido(self):
        return len(self.marcas) >= self.evento["minimo"]

    @property
    def analisis_disponible(self):
        return self.evento["pistas"][0][0] in self.halladas

    def _objetivo(self, jugador, clave, cerca):
        objetivo = next((o for o in self.objetivos if o["id"] == clave), None)
        if objetivo is None or not cerca(jugador, objetivo):
            raise ValueError("Acércate a la luz y pulsa E.")
        return objetivo

    def interactuar(self, identificador, jugador, clave, cerca):
        self._objetivo(jugador, clave, cerca)
        pistas = self.evento["pistas"]
        if len(self.halladas) < len(pistas):
            faltan = len(pistas) - len(self.halladas)
            return {"mensaje": f"Investiguen antes de decidir: faltan {faltan} pistas.", "vista": "fuente",
                    "titulo": "Pantalla pública"}
        if self.fin:
            return {"mensaje": "¡Resolvieron los tres casos de Distrito Conecta!", "vista": "portal"}
        return {"mensaje": "Elijan juntos qué hacer con la publicación.",
                "vista": "resultado" if self.completada else "caldero"}

    def analizar(self, identificador):
        if not self.analisis_disponible:
            raise ValueError("Primero consigue la pista del material original.")
        self.analizando.add(identificador)
        return {"mensaje": "Busquen las marcas de la manipulación.", "vista": "analizar"}

    def marcar(self, identificador, datos):
        if identificador not in self.analizando:
            raise ValueError("Abre el análisis en el celular para marcar.")
        if self.completada:
            raise ValueError("Este caso ya tiene una decisión.")
        marca = marca_en(self.evento, datos)
        if marca is None:
            return {"mensaje": "Aquí no se ve nada extraño. Sigue buscando."}
        if marca["id"] in self.marcas:
            return {"mensaje": "El equipo ya encontró esa marca."}
        self.marcas[marca["id"]] = identificador
        if self.concluido and self.conclusion_id is None:
            self.conclusion_id = self.nuevo_evento()
        return {"mensaje": "¡Marca encontrada! " + marca["texto"] + "."}

    def votar(self, identificador, jugador, opcion, presentes, cerca):
        self._objetivo(jugador, "presente:pantalla", cerca)
        if self.completada:
            raise ValueError("La publicación ya tiene una decisión.")
        if len(self.halladas) < len(self.evento["pistas"]):
            raise ValueError("Reúnan las pistas antes de decidir.")
        if opcion not in OPCIONES:
            raise ValueError("Decisión inválida.")
        self.votos[identificador] = opcion
        self.resolver(presentes)
        if self.resultado:
            return {"mensaje": "¡El equipo decidió! Miren la consecuencia."}
        return {"mensaje": "¡Ya elegiste! Espera a tu equipo de Distrito Conecta."}

    def resolver(self, presentes):
        presentes = set(presentes)
        if self.completada:
            if presentes and presentes.issubset(self.listos) and not self.fin:
                self.resueltos.append({"id": self.evento["id"], "titulo": self.evento["titulo"],
                                       "correcto": self.resultado["correcto"]})
                self.indice += 1
                self._reiniciar_caso()
            return
        if not presentes or not presentes.issubset(self.votos):
            return
        opcion, cantidad = Counter(self.votos[i] for i in presentes).most_common(1)[0]
        if cantidad <= len(presentes) / 2:
            return
        evento = self.evento
        apresurada = opcion == CORRECTA and not self.concluido
        efectos = dict(EFECTOS_SIN_ANALISIS if apresurada else EFECTOS[opcion])
        aplicar_efectos(self.indicadores, efectos)
        self.resultado = {"opcion": opcion, "correcto": opcion == CORRECTA and not apresurada,
                          "texto": evento["sin_analisis"] if apresurada else evento["textos"][opcion],
                          "efectos": efectos, "tipo_pocion": tipo_pocion(opcion), "evento_id": self.nuevo_evento(),
                          **campos_legales(ficha_resuelta(evento["id"]))}
        self.votos.clear()
        if self.completada and self.expediente is not None:
            self.expediente.registrar(evento["id"], evento["titulo"], self.resultado, self._pruebas())

    def _pruebas(self):
        evento = self.evento
        pruebas = [{"id": p[0], "titulo": p[1] + " · " + p[3], "texto": p[4]} for p in evento["pistas"] if p[0] in self.halladas]
        return pruebas + [{"id": m["id"], "titulo": "Marca encontrada", "texto": m["texto"]}
                          for m in MARCAS[evento["marcas"]]["marcas"] if m["id"] in self.marcas]

    def clasificar(self, identificador, opcion):
        if not self.resultado:
            raise ValueError("Primero decidan qué hacer con la publicación.")
        if identificador in self.clasificaciones:
            raise ValueError("Ya clasificaste esta publicación.")
        evento = self.evento
        correcta = clasificacion.evaluar(evento["id"], opcion, "presente")
        efectos = dict(EFECTOS_CLASIFICACION[correcta])
        aplicar_efectos(self.indicadores, efectos)
        self.clasificaciones[identificador] = {"opcion": opcion, "correcta": correcta, "efectos": efectos,
                                               "categoria": clasificacion.ruta_evento(evento["id"])}
        return {"mensaje": evento["clasificacion"][0 if correcta else 1], "vista": "clasificacion_resultado"}

    def siguiente(self, identificador, presentes):
        if not self.completada:
            raise ValueError("Primero decidan qué hacer con este caso.")
        if self.fin:
            raise ValueError("Ya resolvieron todos los casos de Distrito Conecta.")
        if identificador not in self.clasificaciones:
            raise ValueError("Clasifica la publicación antes de seguir.")
        self.listos.add(identificador)
        self.resolver(presentes)
        return {"mensaje": "Listo para el siguiente caso."}

    def publico_analisis(self):
        evento = self.evento
        halladas = []
        for marca in MARCAS[evento["marcas"]]["marcas"]:
            if marca["id"] in self.marcas:
                halladas.append({clave: valor for clave, valor in marca.items()})
        return {"disponible": self.analisis_disponible, "total": len(MARCAS[evento["marcas"]]["marcas"]),
                "minimo": evento["minimo"], "halladas": halladas, "concluido": self.concluido,
                "conclusion_id": self.conclusion_id}

    def publico(self, presentes):
        evento = self.evento
        return {"objetivos": [dict(o) for o in self.objetivos], "pistas": len(self.halladas),
                "total_pistas": len(evento["pistas"]), "titulo": evento["titulo"], "noticia": evento["noticia"],
                "evento": {"id": evento["id"], "tipo": evento["tipo"], "indice": self.indice, "total": len(EVENTOS),
                           "sello": evento["sello"]},
                "edificios": self.edificios,
                "analisis": self.publico_analisis(),
                "etiqueta": evento["etiqueta"] if self.concluido else "sin_fuente",
                "casos_resueltos": [dict(r) for r in self.resueltos], "fin": self.fin,
                "opciones": dict(OPCIONES), "tipos_pocion": {o: tipo_pocion(o) for o in OPCIONES},
                "votos_emitidos": sum(i in self.votos for i in presentes), "votantes": len(presentes),
                "resultado": dict(self.resultado) if self.resultado else None, "completada": self.completada,
                "listos": sum(i in self.listos for i in presentes),
                "clasificacion_opciones": list(clasificacion.OPCIONES["presente"])}

    def privado(self, identificador):
        inventario = [{"id": p[0], "titulo": p[1] + " · " + p[3], "texto": p[4]}
                      for p in self.evento["pistas"] if p[0] in self.halladas]
        return {"inventario": inventario, "voto": self.votos.get(identificador),
                "clasificacion": self.clasificaciones.get(identificador),
                "analizando": identificador in self.analizando, "listo": identificador in self.listos}
