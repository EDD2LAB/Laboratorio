"""Primer caso cooperativo. Reglas, evidencias privadas y consecuencias."""
from collections import Counter, OrderedDict
import math
import re
import unicodedata

ROLES = ("guardian", "mensajero", "habitante", "aspirante")
OPCIONES = {
    "corregir": "Corregir y aclarar",
    "difundir": "Difundir sin verificar",
    "descartar": "Descartar el aviso",
}
MENSAJES = ("Necesito ayuda con una fuente.", "Ven al caldero para comparar pruebas.",
            "Tengo una prueba para compartir.", "No difundamos la noticia todavía.")
PRUEBAS = {
    "guardian": ("Acta del consejo", "El acta anuncia mantenimiento parcial para mañana. No ordena cerrar hoy el puente."),
    "mensajero": ("Registro de la ruta", "La ruta del puente funcionó hoy. El registro señala una revisión parcial para mañana."),
    "habitante": ("Testimonio de Luma", "Luma cruzó hoy y leyó el aviso: mañana revisarán unas tablas. Nadie le comunicó un cierre total."),
    "aspirante": ("Propuesta de Mira", "La propuesta presentada al consejo pide reparar unas tablas mañana; no pide cerrar hoy el puente por decisión de Kael."),
}


def normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if not unicodedata.combining(c))


class MisionPuente:
    def __init__(self, jugadores, datos_mapa):
        self.jugadores = jugadores  # referencia al estado autoritativo
        self.conocidas = {i: set() for i in jugadores}
        self.halladas = {}
        self.entregas = []
        self.votos = {}
        self.resultado = None
        self.rectificacion = False
        self.indicadores = {"confianza": 50, "armonia": 50, "desinformacion": 0}
        self.estado_puente = "sin_verificar"
        self.historial = []
        self.notificaciones = {i: [] for i in jugadores}
        self.procesadas = {i: OrderedDict() for i in jugadores}
        self.ultimo_eco = {}
        self.secuencia = 0
        self.objetivos = [
            {"id": "caldero", "nombre": "Caldero · decisión del equipo", "tipo": "caldero", "x": 480, "y": 380},
            {"id": "archivo", "nombre": "Naira · archivo del consejo", "tipo": "fuente", "rol": "guardian", "x": 786, "y": 261},
            {"id": "testigo", "nombre": "Luma · testimonio", "tipo": "fuente", "rol": "habitante", "x": 808, "y": 562},
            {"id": "propuesta", "nombre": "Mira · propuesta original", "tipo": "fuente", "rol": "aspirante", "x": 205, "y": 531},
        ]
        patrones = {"naira": "archivo", "habitante mujer": "testigo", "aspirante mujer": "propuesta"}
        ecos = []
        for objeto in datos_mapa.get("decoracion", []):
            nombre = normalizar(objeto["name"])
            x, y = round((objeto["x"] + objeto["w"] / 2) * 960), round((objeto["y"] + objeto["h"]) * 720)
            for patron, clave in patrones.items():
                if patron in nombre:
                    objetivo = next(o for o in self.objetivos if o["id"] == clave)
                    objetivo.update(x=x, y=y)
            if "tronco ecos" in nombre:
                ecos.append({"id": f"eco_{len(ecos)}", "nombre": "Tronco de los Ecos", "tipo": "eco", "x": x, "y": y})
        if not ecos:
            ecos = [{"id": "eco_0", "nombre": "Tronco de los Ecos", "tipo": "eco", "x": 474, "y": 466}]
        central = min(ecos, key=lambda o: math.hypot(o["x"] - 480, o["y"] - 420))
        central.update(rol="mensajero", nombre="Eco central · registro de ruta")
        self.objetivos.extend(ecos)

    def _cerca(self, identificador, objetivo, radio=68):
        jugador = self.jugadores[identificador]
        return math.hypot(jugador["x"] - objetivo["x"], jugador["y"] - objetivo["y"]) <= radio

    def _objetivo(self, identificador, clave):
        objetivo = next((o for o in self.objetivos if o["id"] == clave), None)
        if objetivo is None or not self._cerca(identificador, objetivo):
            raise ValueError("Acércate al personaje u objeto para interactuar.")
        return objetivo

    def _avisar(self, receptores, texto, tipo="info"):
        self.secuencia += 1
        aviso = {"id": self.secuencia, "texto": texto, "tipo": tipo}
        for receptor in receptores:
            lista = self.notificaciones.setdefault(receptor, [])
            lista.append(dict(aviso))
            del lista[:-20]

    def _registrar(self, texto):
        self.historial.append(texto)
        del self.historial[:-10]

    def actuar(self, identificador, solicitud, ahora, presentes):
        if identificador not in self.jugadores:
            raise ValueError("El jugador no está en la partida.")
        clave = solicitud.get("id_solicitud", "")
        if not isinstance(clave, str) or not re.fullmatch(r"[a-f0-9]{32}", clave):
            raise ValueError("Solicitud de acción inválida.")
        memoria = self.procesadas.setdefault(identificador, OrderedDict())
        if clave in memoria:
            return dict(memoria[clave])
        try:
            respuesta = self._ejecutar(identificador, solicitud, ahora, presentes)
            acuse = {"tipo": "acuse", "id_solicitud": clave, "ok": True, **respuesta}
        except ValueError as error:
            acuse = {"tipo": "acuse", "id_solicitud": clave, "ok": False, "mensaje": str(error)}
        memoria[clave] = acuse
        while len(memoria) > 128:
            memoria.popitem(last=False)
        return dict(acuse)

    def _ejecutar(self, identificador, solicitud, ahora, presentes):
        accion = solicitud.get("accion")
        jugador = self.jugadores[identificador]
        if accion == "interactuar":
            destino = solicitud.get("objetivo")
            if isinstance(destino, str) and destino.startswith("jugador:"):
                receptor = destino.split(":", 1)[1]
                otro = self.jugadores.get(receptor)
                if not otro or receptor == identificador or not self._cerca(identificador, otro, 64):
                    raise ValueError("Acércate al otro jugador para compartir pruebas.")
                return {"mensaje": f"Puedes compartir una pista con {otro['nombre']}.", "vista": "compartir", "destinatario": receptor}
            objetivo = self._objetivo(identificador, destino)
            if objetivo.get("rol") == jugador["rol"]:
                pista = "pista_" + jugador["rol"]
                self.conocidas[identificador].add(pista)
                if pista not in self.halladas:
                    self.halladas[pista] = identificador
                    self._avisar([identificador], "Registraste una prueba. Abre I para leerla y compartirla.")
                    self._registrar(f"{jugador['nombre']} registró una prueba de su fuente.")
                titulo, texto = PRUEBAS[jugador["rol"]]
                return {"mensaje": texto, "titulo": titulo, "vista": "eco" if objetivo["tipo"] == "eco" else "fuente"}
            if objetivo["tipo"] == "caldero":
                return {"mensaje": "Comparen las pruebas y decidan juntos qué comunicar.", "vista": "resultado" if self.resultado else "caldero"}
            if objetivo["tipo"] == "eco":
                return {"mensaje": "Envía mensajes breves o copias de tus pruebas al equipo.", "vista": "eco"}
            return {"mensaje": "Esta fuente aporta una prueba a otro rol. Busca tu objetivo marcado en el mapa.", "vista": "fuente", "titulo": objetivo["nombre"]}
        if accion == "entregar":
            receptor, pista = solicitud.get("destinatario"), solicitud.get("pista")
            if not isinstance(pista, str) or pista not in self.conocidas[identificador]:
                raise ValueError("No tienes esa prueba para compartir.")
            if not isinstance(receptor, str) or receptor == identificador or receptor not in self.jugadores or receptor not in presentes:
                raise ValueError("El destinatario no está disponible.")
            medio = solicitud.get("medio")
            if medio == "directo":
                if not self._cerca(identificador, self.jugadores[receptor], 64):
                    raise ValueError("El otro jugador está demasiado lejos para una entrega directa.")
            elif medio == "eco":
                if not any(o["tipo"] == "eco" and self._cerca(identificador, o) for o in self.objetivos):
                    raise ValueError("Debes estar cerca de un Tronco de los Ecos.")
            else:
                raise ValueError("Medio de entrega inválido.")
            if pista in self.conocidas[receptor]:
                return {"mensaje": "Ese jugador ya tiene esta prueba."}
            self.conocidas[receptor].add(pista)
            self.entregas.append({"emisor": identificador, "receptor": receptor, "pista": pista, "medio": medio})
            self._avisar([receptor], f"{jugador['nombre']} te entregó una prueba. Puedes leerla con I.", "entrega")
            self._avisar([identificador], f"Entrega confirmada a {self.jugadores[receptor]['nombre']}.", "entrega")
            self._registrar(f"{jugador['nombre']} compartió una prueba con {self.jugadores[receptor]['nombre']}.")
            return {"mensaje": "Prueba entregada y recepción confirmada."}
        if accion == "eco":
            if not any(o["tipo"] == "eco" and self._cerca(identificador, o) for o in self.objetivos):
                raise ValueError("Acércate a un Tronco de los Ecos.")
            indice = solicitud.get("mensaje")
            if type(indice) is not int or not 0 <= indice < len(MENSAJES):
                raise ValueError("Mensaje no permitido.")
            if ahora - self.ultimo_eco.get(identificador, -10) < 2:
                raise ValueError("Espera dos segundos antes de enviar otro eco.")
            self.ultimo_eco[identificador] = ahora
            self._avisar(presentes, f"Eco de {jugador['nombre']}: {MENSAJES[indice]}", "eco")
            return {"mensaje": "Eco recibido por los jugadores conectados."}
        if accion in ("votar", "rectificar"):
            self._objetivo(identificador, "caldero")
            if accion == "rectificar":
                if not self.resultado or self.resultado["correcto"] or self.rectificacion:
                    raise ValueError("No hay una decisión pendiente de rectificar.")
                self.rectificacion = True
                self.resultado = None
                self.votos.clear()
                self._avisar(presentes, "El equipo revisará su decisión. Vuelvan a votar en el caldero.")
                return {"mensaje": "Se abrió una única oportunidad de rectificación.", "vista": "caldero"}
            if self.resultado:
                raise ValueError("El caso ya tiene un resultado.")
            if len(presentes) < 2 or len(set(self.halladas.values())) < 2 or not self.entregas:
                raise ValueError("Necesitan pruebas de dos jugadores distintos y una entrega confirmada.")
            if len(self.conocidas[identificador]) < 2:
                raise ValueError("Necesitas dos pruebas en tu registro. Pide a un compañero que te comparta una.")
            opcion = solicitud.get("opcion")
            if not isinstance(opcion, str) or opcion not in OPCIONES:
                raise ValueError("Decisión inválida.")
            self.votos[identificador] = opcion
            self.resolver(presentes)
            return {"mensaje": "Voto registrado. Puedes cambiarlo mientras no haya resultado."}
        raise ValueError("Acción desconocida.")

    def resolver(self, presentes):
        presentes = set(presentes) & self.jugadores.keys()
        if self.resultado or len(presentes) < 2 or not presentes.issubset(self.votos):
            return
        conteo = Counter(self.votos[i] for i in presentes)
        opcion, cantidad = conteo.most_common(1)[0]
        if cantidad <= len(presentes) / 2:
            return  # Empate: los participantes pueden cambiar su voto.
        correcto = opcion == "corregir"
        if correcto:
            efectos = {"confianza": 8 if self.rectificacion else 12, "armonia": 8, "desinformacion": -10}
            texto = "El cierre total de hoy era un rumor. Publicaron una aclaración con fuentes: mañana habrá mantenimiento parcial."
            self.estado_puente = "revision_programada"
        elif opcion == "difundir":
            efectos = {"confianza": -12, "armonia": -8, "desinformacion": 20}
            texto = "Se difundió un cierre que no ocurrió. La alarma confundió a la comunidad."
            texto += " La rectificación también fue incorrecta; el caso terminó." if self.rectificacion else " Todavía pueden rectificar una vez."
            self.estado_puente = "alarma_injustificada"
        else:
            efectos = {"confianza": -6, "armonia": -4, "desinformacion": 8}
            texto = "Descartaron también el aviso útil de mantenimiento. La comunidad sigue sin saber qué ocurrirá mañana."
            if self.rectificacion:
                texto += " La oportunidad de rectificación terminó."
            self.estado_puente = "aviso_pendiente"
        for nombre, cambio in efectos.items():
            self.indicadores[nombre] = max(0, min(100, self.indicadores[nombre] + cambio))
        self.resultado = {"opcion": opcion, "correcto": correcto, "texto": texto, "efectos": efectos}
        self._registrar("Decisión del equipo: " + OPCIONES[opcion])
        self._avisar(self.jugadores.keys(), texto, "resultado")

    def publico(self, presentes):
        participantes = set(presentes) & self.jugadores.keys()
        empate = bool(participantes) and participantes.issubset(self.votos) and self.resultado is None
        return {
            "id": "puente_norte", "titulo": "¿Cerraron el puente norte?",
            "noticia": "Circula que Kael cerró hoy todo el puente norte por decisión propia.",
            "objetivos": [dict(o) for o in self.objetivos], "pruebas_halladas": len(self.halladas),
            "investigadores": len(set(self.halladas.values())), "entregas": len(self.entregas),
            "votos_emitidos": sum(i in self.votos for i in participantes), "votantes": len(participantes),
            "empate": empate, "resultado": self.resultado, "rectificacion": self.rectificacion,
            "indicadores": dict(self.indicadores), "estado_puente": self.estado_puente,
            "historial": list(self.historial), "opciones": dict(OPCIONES), "mensajes_eco": list(MENSAJES),
        }

    def privado(self, identificador):
        if identificador not in self.jugadores:
            return {}
        rol = self.jugadores[identificador]["rol"]
        objetivo = next(o for o in self.objetivos if o.get("rol") == rol)
        inventario = []
        for pista in sorted(self.conocidas[identificador]):
            rol_pista = pista.removeprefix("pista_")
            titulo, texto = PRUEBAS[rol_pista]
            inventario.append({"id": pista, "titulo": titulo, "texto": texto, "origen": self.halladas[pista]})
        if self.resultado:
            instruccion = "Revisa el resultado común en el caldero."
        elif "pista_" + rol not in self.conocidas[identificador]:
            instruccion = "Ve a " + objetivo["nombre"] + " y pulsa E."
        elif len(inventario) < 2:
            instruccion = "Comparte tu prueba y pide otra con I."
        else:
            instruccion = "Acérquense al caldero y voten con las pruebas."
        return {"inventario": inventario, "objetivo": dict(objetivo), "voto": self.votos.get(identificador),
                "avisos": list(self.notificaciones[identificador]), "instruccion": instruccion}
