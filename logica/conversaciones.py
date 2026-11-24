"""Testimonios y reacciones vinculados al estado real de la partida."""

TESTIMONIOS = {
    "Rumor Politico": {
        "Kael": ("Le propuse al consejo revisar las tablas del puente norte porque la lluvia las había dañado. ¿Quién te contó que yo lo rompí?",
                 "Proponer una revisión no es romper un puente. El consejo lo cerró por seguridad hasta repararlo."),
        "Mira": ("Escuché que Kael rompió el puente, pero yo no estaba allí.",
                 "Mi información viene de otra persona. No deberías presentarla como si yo hubiera visto lo que pasó."),
        "Tarek": ("Después de la lluvia vi las tablas del puente mojadas y astilladas. No vi a nadie golpearlas.",
                  "Desde que lo cerraron cruzamos por otra ruta. Pregunta al consejo por qué lo cerró."),
        "Luma": ("El mensaje llegó por los Ecos sin decir quién vio a Kael romper el puente.",
                 "Cada vez que lo repiten suena más seguro, aunque sigue faltando la fuente original."),
        "Mensajero": ("Desde que el consejo cerró el puente llevo los mensajes por otra ruta.",
                      "Puedo confirmar que el puente está cerrado, no quién tuvo la culpa. Pregunta por qué lo cerraron."),
        "Naira": ("Las familias necesitan saber por dónde cruzar mientras reparan el puente. Una noticia incompleta puede asustarlas.",
                  "El consejo cerró el puente por seguridad. Lo que falta comprobar es por qué se dañó, no si está cerrado."),
        "Darek": ("Oí el rumor sobre Kael junto al cesto, pero nadie dijo quién lo vio.",
                  "Si nadie lo vio, no podemos contarlo como si fuera cierto."),
        "Sabio de las Raíces": ("Las lluvias de esta temporada pudrieron más de una tabla. Antes de culpar a alguien, revisa el puente.",
                                "La madera vieja cede sola. Un rumor no explica una tabla podrida."),
    },
    # El caso del agua tiene dos variantes (aviso viejo o aviso de hoy): ningún
    # testimonio revela cuál salió; todos invitan a comparar fecha y depósito.
    "Aviso Comunitario": {
        "Kael": ("Escuché el aviso del agua, pero nadie me dijo de qué depósito hablaba.",
                 "Antes de decidir, pregunta la fecha del aviso y qué depósito nombra."),
        "Mira": ("El aviso del agua me llegó por los Ecos. No sé si es de hoy o de hace tiempo.",
                 "Un aviso sin fecha puede proteger o puede asustar sin razón. Hay que compararlo con las pistas."),
        "Tarek": ("Escuché el aviso en el tronco, pero no dijo de qué depósito hablaba.",
                  "Pregunta quién tomó las muestras y cuándo lo hizo."),
        "Luma": ("En los Ecos el aviso del agua suena cada vez más urgente, pero nadie cita la fuente.",
                 "Busca el primer mensaje: ¿qué fecha tiene y quién lo firmó?"),
        "Mensajero": ("Puedo llevar el aviso del agua, pero primero quiero saber si es de hoy.",
                      "Repetir un aviso viejo confunde; callar uno real también hace daño. Por eso hay que verificarlo."),
        "Naira": ("El archivo del consejo guarda los informes del agua con su fecha. Compara la del aviso con la de hoy.",
                  "Un informe dice de qué depósito habla y cuándo se escribió. Esos dos datos deciden qué hacer."),
        "Darek": ("Mi familia ya está guardando agua por si acaso. ¿Alguien sabe de qué depósito habla el aviso?",
                  "No quiero difundir algo que asuste sin razón, ni callar algo que nos proteja."),
        "Sabio de las Raíces": ("El agua de La Copa ha salido de varios depósitos a lo largo de los años.",
                                "Pregunta qué depósito nombra el aviso y si todavía está conectado a la red."),
    },
}

# Lo que comentan los vecinos sobre la última decisión (por tipo de poción).
REACCIONES = {
    "Rumor Politico": {
        "Colgarla": "La acusación contra Kael se difundió sin verificar y ahora hay dudas entre las familias.",
        "Quemarla": "Se corrigió el rumor: el puente se cerró por el daño de la lluvia, no por culpa de Kael.",
        "Consultar": "Consultar la tablilla permitió revisar el rumor antes de tomar una decisión.",
        "Ignorarla": "Descartaron el rumor, pero también lo cierto: algunas familias no saben que el puente sigue cerrado.",
    },
    "Aviso Comunitario": {
        "Colgarla": "El aviso del agua se difundió por toda la aldea.",
        "Quemarla": "Se corrigió el aviso del agua antes de que siguiera circulando.",
        "Consultar": "Revisar el aviso del agua permitió comparar fechas y depósitos.",
        "Ignorarla": "El aviso del agua dejó de circular.",
    },
}

TESTIMONIOS_PRESENTE = {
    "Darío Veraz": (
        "Mi trabajo es separar los hechos de los rumores. Encontré el video original: compáralo con el que circula.",
        "Compara cuadro por cuadro. Verificar exige contrastar también el testimonio y el contexto.",
    ),
    "Ronaldo Vélez": (
        "Aspiro a la Alcaldía. Ese día hice una donación pública; mi agenda lo confirma.",
        "Lo que circula no demuestra culpabilidad. Compárenlo con el material original antes de creerlo.",
    ),
    "Tania Red": (
        "Estoy conectada a lo que comparte la comunidad. Vi la publicación, pero no el hecho ni su archivo original.",
        "No vi a Ronaldo en ese lugar. Comprueba el contexto antes de compartir la imagen.",
    ),
    "Lía Nova": (
        "Soy influencer y cuento historias a mucha gente. Este video circula mucho, pero primero comprobemos su origen.",
        "El alcance no convierte una publicación en verdad. Busquemos una fuente verificable antes de amplificarla.",
    ),
    "Mateo Ríos": (
        "Soy mensajero: conecto a la gente por la ciudad. Puedo llevar una corrección con datos confirmados.",
        "Una corrección clara debe enlazar la fuente y explicar qué parte del mensaje era dudosa.",
    ),
    "Elías Vega": (
        "Como periodista cuido lo que se publica. Una foto dice más cuando sabes de dónde salió.",
        "Antes de creer en una imagen, busca la original y compárala.",
    ),
    "Archivista": (
        "Guardo los registros de la ciudad. Una orden vale si la firma quien tiene autoridad para darla.",
        "Mira primero la firma y luego la fecha. Un documento puede decir cualquier cosa.",
    ),
    "Representante Humano": (
        "El consejo nunca autorizó esto. Firmo la reconfiguración: NÚCLEO seguirá, pero supervisado por personas.",
        "No queremos apagarlo. Queremos que alguien pueda revisar lo que decide.",
    ),
    "Corredor de Datos": (
        "Antes de que NÚCLEO bloqueara los sectores saqué la llave de supervisión. Llévala a la terminal del Centro de Supervisión.",
        "La llave no apaga a NÚCLEO: solo hace que las personas vuelvan a revisar lo que decide.",
    ),
    "Ciudadano Conectado": (
        "Protesté porque nadie autorizó a NÚCLEO, y sus cuentas automáticas empezaron a atacarme.",
        "No quiero destruirlo. Quiero que alguien pueda revisar sus decisiones.",
    ),
}


def construir_conversacion(nombre, estado, vistas):
    """Las conversaciones vistas se registran por tablilla y personaje."""
    if nombre in TESTIMONIOS_PRESENTE:
        clave = ("presente", nombre)
        inicial, ampliacion = TESTIMONIOS_PRESENTE[nombre]
        texto = ampliacion if clave in vistas else inicial
        return {
            "personaje": nombre,
            "texto": texto,
            "respuestas": ["Gracias por la información"],
        }, clave

    ruta = estado.ruta_categoria_actual()
    categoria = ruta[1] if len(ruta) > 1 else ""
    clave = (estado.tablillas_resueltas, nombre)
    inicial, ampliacion = TESTIMONIOS.get(categoria, {}).get(nombre, (
        "Escucha a quienes estuvieron presentes y compara sus testimonios.",
        "Revisa de dónde viene cada mensaje antes de compartirlo.",
    ))
    texto = ampliacion if clave in vistas else inicial
    if "Consultar" in estado.camino_decision_actual:
        texto = ampliacion
    if (
        not estado.tablillas_resueltas
        and not estado.historial_decisiones
        and clave not in vistas
    ):
        texto += " Para investigar, escucha a los vecinos y luego revisa la tablilla en el Caldero central."
    if estado.historial_decisiones:
        ultima = estado.historial_decisiones[-1]
        camino = ultima.get("camino", [])
        categoria_anterior = ultima.get("categoria", [])
        if camino and len(categoria_anterior) > 1:
            reaccion = REACCIONES.get(categoria_anterior[1], {}).get(camino[0], "")
            if reaccion:
                texto = f"{reaccion} {texto}"
    respuestas = ["Gracias por la información"]
    if nombre == "Mensajero":
        respuestas.insert(0, "Entrega el mensaje")
    if nombre in ("Naira", "Guardián", "Sabio de las Raíces"):
        respuestas.insert(0, "Consultar tablilla")
    return {"personaje": nombre, "texto": texto, "respuestas": respuestas}, clave


def construir_mensajes_eco(estado):
    """Mensajes que se pueden enviar sin afirmar hechos aún no verificados."""
    ruta = estado.ruta_categoria_actual()
    categoria = ruta[1] if len(ruta) > 1 else ""
    tema, consulta = {
        "Rumor Politico": ("Kael y el puente norte", "¿Quién vio lo que pasó con el puente norte?"),
        "Aviso Comunitario": ("el aviso del agua", "¿De qué depósito y de qué fecha habla el aviso del agua?"),
    }.get(categoria, ("las noticias de la aldea", "Comparemos las fuentes de las noticias."))
    mensajes = [
        ("consulta_fuente", consulta),
        ("verificar_tablilla", f"Necesito verificar lo que se dice sobre {tema}."),
        ("mensaje_reservado", "No difundas el mensaje hasta revisar sus fuentes."),
    ]
    if "Consultar" in estado.camino_decision_actual:
        mensajes.append(("consulta_en_curso", "Estoy consultando la tablilla. ¿Puedes aportar un testimonio?"))
    if estado.historial_decisiones:
        ultima = estado.historial_decisiones[-1]
        ruta_anterior, camino = ultima.get("categoria", []), ultima.get("camino", [])
        if len(ruta_anterior) > 1 and camino:
            reaccion = REACCIONES.get(ruta_anterior[1], {}).get(camino[0])
            if reaccion:
                mensajes.append(("ultima_decision", reaccion))
    return mensajes


def construir_respuesta_eco(nombre, mensaje_id, estado):
    if mensaje_id == "ultima_decision":
        texto = "Recibido. Tendré en cuenta lo ocurrido al revisar los próximos mensajes."
    elif mensaje_id == "mensaje_reservado":
        texto = "Esperaré antes de difundirlo. Primero revisaré de dónde viene."
    else:
        # Compartir un testimonio por el tronco no cuenta como conversación vista.
        dialogo, _ = construir_conversacion(nombre, estado, set())
        texto = dialogo["texto"]
    return f"{nombre}: {texto}"
