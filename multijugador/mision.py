"""Primer caso cooperativo. Reglas, evidencias privadas y consecuencias."""
from collections import Counter, OrderedDict
import math
import re
import unicodedata

from .presentacion import INDICADORES_INICIALES, aplicar_efectos, tipo_pocion

ROLES = ("guardian", "mensajero", "habitante", "aspirante")
OPCIONES = {
    "corregir": "Corregir y aclarar",
    "difundir": "Difundir sin verificar",
    "descartar": "Descartar el aviso",
}
MENSAJES = ("¿Me ayudas a buscar una pista?", "Ven al caldero para comparar pistas.",
            "Tengo una pista para compartir.", "No difundamos la noticia todavía.")
# Lo que hace un bot al recibir cada mensaje de MENSAJES (mismo orden).
ORDENES_ECO = ("ayudar", "caldero", "recibir", "no_difundir")
TODOS = "todos"  # destinatario de un eco que llega a todo el equipo
PRUEBAS = {
    "guardian": ("Acta del consejo", "El papel del consejo dice: mañana arreglarán unas tablas. Hoy el puente está abierto."),
    "mensajero": ("Registro de la ruta", "Hoy llevé mensajes por el puente. Mañana revisarán unas tablas."),
    "habitante": ("Testimonio de Luma", "Luma cuenta: crucé hoy sin problemas. El aviso dice que mañana arreglarán unas tablas."),
    "aspirante": ("Propuesta de Mira", "Mira pidió arreglar unas tablas mañana. No pidió cerrar hoy el puente."),
}


def normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if not unicodedata.combining(c))


class MisionPuente:
    def __init__(self, jugadores, datos_mapa):
        self.pruebas = PRUEBAS
        self.opciones = OPCIONES
        self.correcta = "corregir"
        self.jugadores = jugadores  # referencia al estado autoritativo
        self.conocidas = {i: set() for i in jugadores}
        self.halladas = {}
        self.entregas = []
        self.votos = {}
        self.resultado = None
        self.rectificacion = False
        # Mismos indicadores y valores iniciales que el modo de un jugador.
        self.indicadores = dict(INDICADORES_INICIALES)
        self.eventos = 0  # identificador único de cada efecto visual difundido
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
            {"id": "propuesta", "nombre": "Archivo de propuestas de Mira", "tipo": "fuente", "rol": "aspirante", "x": 205, "y": 531},
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
        # El tronco de la plataforma central es el cesto de los encargos de la
        # aldea; la fuente del Mensajero pasa al tronco más cercano a él.
        cercania = lambda o: math.hypot(o["x"] - 480, o["y"] - 420)
        central = min(ecos, key=cercania)
        self.objetivos.append({"id": "cesto", "nombre": "Cesto de la aldea", "tipo": "cesto", "x": central["x"], "y": central["y"]})
        if len(ecos) > 1:
            ecos.remove(central)
        min(ecos, key=cercania).update(rol="mensajero", nombre="Eco central · registro de ruta")
        self.objetivos.extend(ecos)

    def siguiente_evento(self):
        self.eventos += 1
        return self.eventos

    def _cerca(self, identificador, objetivo, radio=68):
        jugador = self.jugadores[identificador]
        # Quien está en otra dimensión no puede interactuar con este mapa.
        if (jugador.get("dimension", "la_copa") != objetivo.get("dimension", "la_copa")
                or jugador.get("interior") != objetivo.get("interior")):
            return False
        return math.hypot(jugador["x"] - objetivo["x"], jugador["y"] - objetivo["y"]) <= radio

    def _objetivo(self, identificador, clave):
        objetivo = next((o for o in self.objetivos if o["id"] == clave), None)
        if objetivo is None or not self._cerca(identificador, objetivo):
            raise ValueError("Acércate a la luz y pulsa E.")
        return objetivo

    def _avisar(self, receptores, texto, tipo="info", **datos):
        self.secuencia += 1
        aviso = {"id": self.secuencia, "texto": texto, "tipo": tipo, **datos}
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
                    self._avisar([identificador], "¡Encontraste una pista! Abre I para leerla y compartirla.")
                    self._registrar(f"{jugador['nombre']} registró una prueba de su fuente.")
                titulo, texto = self.pruebas[jugador["rol"]]
                return {"mensaje": texto, "titulo": titulo, "vista": "eco" if objetivo["tipo"] == "eco" else "fuente"}
            if objetivo["tipo"] == "caldero":
                return {"mensaje": "Lean sus pistas y elijan juntos qué contar a la aldea.", "vista": "resultado" if self.resultado else "caldero"}
            if objetivo["tipo"] == "eco":
                return {"mensaje": "Envía mensajes breves o copias de tus pruebas al equipo.", "vista": "eco"}
            if objetivo["tipo"] == "cesto":
                return {"mensaje": "Aquí se reúne lo que necesita la aldea. Cuando haya un encargo, trae cada objeto y pulsa E.",
                        "vista": "fuente", "titulo": objetivo["nombre"]}
            return {"mensaje": "Este personaje ayuda a otro compañero. Tu personaje está marcado con una luz.", "vista": "fuente", "titulo": objetivo["nombre"]}
        if accion == "entregar":
            receptor, pista = solicitud.get("destinatario"), solicitud.get("pista")
            if not isinstance(pista, str) or pista not in self.conocidas[identificador]:
                raise ValueError("Primero busca una pista para compartir.")
            medio = solicitud.get("medio")
            a_todos = receptor == TODOS and medio == "eco"
            if not a_todos and (not isinstance(receptor, str) or receptor == identificador
                                or receptor not in self.jugadores or receptor not in presentes):
                raise ValueError("El destinatario no está disponible.")
            if medio == "directo":
                if not self._cerca(identificador, self.jugadores[receptor], 64):
                    raise ValueError("El otro jugador está demasiado lejos para una entrega directa.")
            elif medio == "eco":
                if not any(o["tipo"] == "eco" and self._cerca(identificador, o) for o in self.objetivos):
                    raise ValueError("Debes estar cerca de un Tronco de los Ecos.")
            else:
                raise ValueError("Medio de entrega inválido.")
            receptores = [i for i in presentes if i != identificador and i in self.jugadores] if a_todos else [receptor]
            nuevos = [i for i in receptores if pista not in self.conocidas[i]]
            if not nuevos:
                return {"mensaje": "Todos ya tienen esta prueba." if a_todos else "Ese jugador ya tiene esta prueba."}
            for nuevo in nuevos:
                self.conocidas[nuevo].add(pista)
                self.entregas.append({"emisor": identificador, "receptor": nuevo, "pista": pista, "medio": medio})
                self._avisar([nuevo], f"{jugador['nombre']} te mandó una pista. Léela con I.", "entrega")
                self._avisar([identificador], f"{self.jugadores[nuevo]['nombre']} recibió tu pista.", "entrega")
                self._registrar(f"{jugador['nombre']} compartió una prueba con {self.jugadores[nuevo]['nombre']}.")
            return {"mensaje": "¡El equipo recibió la pista!" if a_todos else "¡Tu compañero recibió la pista!"}
        if accion == "eco":
            if not any(o["tipo"] == "eco" and self._cerca(identificador, o) for o in self.objetivos):
                raise ValueError("Acércate a un Tronco de los Ecos.")
            indice = solicitud.get("mensaje")
            if type(indice) is not int or not 0 <= indice < len(MENSAJES):
                raise ValueError("Mensaje no permitido.")
            destinatario = solicitud.get("destinatario", TODOS)
            if destinatario != TODOS and (not isinstance(destinatario, str) or destinatario == identificador
                                          or destinatario not in self.jugadores or destinatario not in presentes):
                raise ValueError("El destinatario no está disponible.")
            if ahora - self.ultimo_eco.get(identificador, -10) < 2:
                raise ValueError("Espera dos segundos antes de enviar otro eco.")
            self.ultimo_eco[identificador] = ahora
            datos = {"orden": ORDENES_ECO[indice], "emisor": identificador}
            if destinatario == TODOS:
                self._avisar(presentes, f"Eco de {jugador['nombre']}: {MENSAJES[indice]}", "eco", **datos)
                return {"mensaje": "Eco recibido por los jugadores conectados."}
            self._avisar([destinatario], f"Eco de {jugador['nombre']} para ti: {MENSAJES[indice]}", "eco", **datos)
            return {"mensaje": f"Eco enviado a {self.jugadores[destinatario]['nombre']}."}
        if accion in ("votar", "rectificar"):
            self._objetivo(identificador, "caldero")
            if accion == "rectificar":
                if not self.resultado or self.resultado["correcto"] or self.rectificacion:
                    raise ValueError("No hay una decisión pendiente de rectificar.")
                self.rectificacion = True
                self.resultado = None
                self.votos.clear()
                self._avisar(presentes, "¡Podemos intentarlo otra vez! Lean las pistas y elijan en el caldero.")
                return {"mensaje": "Pueden intentarlo una vez más.", "vista": "caldero"}
            if self.resultado:
                raise ValueError("El caso ya tiene un resultado.")
            if len(presentes) < 2 or len(set(self.halladas.values())) < 2 or not self.entregas:
                raise ValueError("Dos compañeros deben buscar sus pistas y compartir al menos una.")
            if len(self.conocidas[identificador]) < 2:
                raise ValueError("Te falta una pista. Pulsa Pedir una pista para pedir ayuda.")
            opcion = solicitud.get("opcion")
            if not isinstance(opcion, str) or opcion not in OPCIONES:
                raise ValueError("Decisión inválida.")
            self.votos[identificador] = opcion
            self.resolver(presentes)
            return {"mensaje": "¡Ya elegiste! Espera a tu equipo. Puedes cambiar tu elección."}
        raise ValueError("Acción desconocida.")

    def resolver(self, presentes):
        presentes = set(presentes) & self.jugadores.keys()
        if self.resultado or len(presentes) < 2 or not presentes.issubset(self.votos):
            return
        # Con personas en la partida deciden ellas: los bots no las superan en votos.
        decisores = {i for i in presentes if self.jugadores[i].get("controlador") != "bot"} or presentes
        conteo = Counter(self.votos[i] for i in decisores)
        opcion, cantidad = conteo.most_common(1)[0]
        if cantidad <= len(decisores) / 2:
            return  # Empate: los participantes pueden cambiar su voto.
        correcto = opcion == self.correcta
        if correcto:
            efectos = {"confianza": 8 if self.rectificacion else 12, "armonia": 8, "susurros_falsos": -5, "desinformacion": -10}
            texto = "El puente se dañó por el desgaste y la lluvia, no por Kael. Sigue abierto hoy; mañana habrá mantenimiento parcial."
            self.estado_puente = "revision_programada"
        elif opcion == "difundir":
            efectos = {"confianza": -12, "armonia": -8, "susurros_falsos": 10, "desinformacion": 20}
            texto = "Se difundió un cierre que no ocurrió. La alarma confundió a la comunidad."
            texto += " La rectificación también fue incorrecta; el caso terminó." if self.rectificacion else " Todavía pueden rectificar una vez."
            self.estado_puente = "alarma_injustificada"
        else:
            efectos = {"confianza": -6, "armonia": -4, "susurros_falsos": 4, "desinformacion": 8}
            texto = "Descartaron también el aviso útil de mantenimiento. La comunidad sigue sin saber qué ocurrirá mañana."
            if self.rectificacion:
                texto += " La oportunidad de rectificación terminó."
            self.estado_puente = "aviso_pendiente"
        aplicar_efectos(self.indicadores, efectos)
        texto = self.texto_resultado(texto, correcto)
        # tipo_pocion y evento_id son solo presentación: todos los clientes
        # reproducen una vez la poción, el caldero y el sonido de ese tipo.
        self.resultado = {"opcion": opcion, "correcto": correcto, "texto": texto, "efectos": efectos,
                          "tipo_pocion": tipo_pocion(opcion), "evento_id": self.siguiente_evento()}
        self._registrar("Decisión del equipo: " + self.opciones[opcion])
        self._avisar(self.jugadores.keys(), texto, "resultado")

    def texto_resultado(self, texto, correcto):
        return texto

    def publico(self, presentes):
        participantes = set(presentes) & self.jugadores.keys()
        empate = bool(participantes) and participantes.issubset(self.votos) and self.resultado is None
        return {
            "id": "puente_norte", "titulo": "¿Quién rompió el puente norte?",
            "noticia": "Alguien dice que Kael rompió el puente por descuido y por eso lo cerraron. ¿Será verdad?",
            "objetivos": [dict(o) for o in self.objetivos], "pruebas_halladas": len(self.halladas),
            "investigadores": len(set(self.halladas.values())), "entregas": len(self.entregas),
            "votos_emitidos": sum(i in self.votos for i in participantes), "votantes": len(participantes),
            "empate": empate, "resultado": self.resultado, "rectificacion": self.rectificacion,
            "indicadores": dict(self.indicadores), "estado_puente": self.estado_puente,
            "historial": list(self.historial), "opciones": dict(self.opciones), "mensajes_eco": list(MENSAJES),
        }

    def privado(self, identificador):
        if identificador not in self.jugadores:
            return {}
        rol = self.jugadores[identificador]["rol"]
        objetivo = next(o for o in self.objetivos if o.get("rol") == rol)
        inventario = []
        for pista in sorted(self.conocidas[identificador]):
            rol_pista = pista.removeprefix("pista_")
            titulo, texto = self.pruebas[rol_pista]
            inventario.append({
                "id": pista,
                "titulo": titulo,
                "texto": texto,
                "origen": self.halladas[pista],
                "metadatos": dict(
                    getattr(self, "metadatos_pruebas", {}).get(rol_pista, {})
                ),
            })
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
