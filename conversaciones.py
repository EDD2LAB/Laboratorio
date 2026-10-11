"""Testimonios y reacciones vinculados al estado real de la partida."""

TESTIMONIOS = {
    "Rumor Politico": {
        "Kael": ("Estuve hablando del puente norte con el consejo. ¿Quién te contó que quiero cerrarlo?", "Una propuesta, una discusión y una decisión no son lo mismo. Pide que te expliquen cuál ocurrió."),
        "Mira": ("Escuché que Kael quiere cerrar el puente, pero no estuve en la reunión.", "Mi información viene de otra persona. No deberías presentarla como si yo hubiera visto la reunión."),
        "Tarek": ("Vi gente reunida cerca del puente. No pude escuchar lo que discutían.", "Que hubiera una reunión no demuestra que hayan decidido cerrar el paso."),
        "Luma": ("El mensaje llegó por los Ecos sin decir quién escuchó a Kael.", "Cada vez que lo repiten suena más seguro, aunque sigue faltando la fuente original."),
        "Mensajero": ("Crucé el puente esta mañana. Estaba abierto cuando pasé.", "Puedo confirmar cómo estaba esta mañana, pero eso no prueba qué planea el consejo para después."),
        "Naira": ("Las familias necesitan saber si podrán cruzar. Una noticia incompleta puede asustarlas.", "Pregunta también cuándo ocurriría el supuesto cierre; sin fecha no podemos organizar las rutas."),
    },
    "Suceso Natural": {
        "Kael": ("Antes de cambiar las rutas necesitamos saber dónde cayó el rayo.", "Un aviso preciso ayuda más que decir que toda la aldea está en peligro."),
        "Mira": ("Escuché el trueno anoche. Todavía no he visto los daños.", "Haber oído el trueno no me permite decir qué golpeó el rayo."),
        "Tarek": ("Vi un destello cerca del Mirador Alto anoche y después escuché el trueno.", "Puedo señalar dónde vi el destello. No alcancé a ver qué objeto recibió el impacto."),
        "Luma": ("Los Ecos hablan de un rayo cerca del Mirador Alto; algunas versiones ya dicen que destruyó el puente.", "Conviene separar el aviso original de los daños que otros añadieron al repetirlo."),
        "Mensajero": ("Puedo llevar el aviso a las plataformas cercanas al Mirador Alto.", "El mensaje debe indicar el lugar y la hora, sin añadir daños que nadie comprobó."),
        "Naira": ("Podemos revisar los caminos cercanos al Mirador antes de usarlos.", "Avisar a tiempo permite preparar las rutas sin provocar miedo innecesario."),
    },
    "Acusacion Personal": {
        "Kael": ("Antes de juzgar a Mira, quiero escuchar qué ocurrió y quién estuvo presente.", "Una acusación puede dañar su reputación incluso después de corregirla."),
        "Mira": ("Quiero que escuchen mi versión antes de repetir lo que dice esa tablilla.", "Pregunta a quienes estuvieron allí y compara sus relatos con el mío."),
        "Tarek": ("No presencié lo que se cuenta de Mira. No puedo confirmarlo.", "Que muchas personas lo repitan no me convierte en testigo."),
        "Luma": ("La historia sobre Mira cambia cada vez que pasa por un Eco.", "Busca la primera versión y pregunta qué partes se añadieron después."),
        "Mensajero": ("Puedo llevar una consulta a quienes estuvieron con Mira.", "Un mensaje privado permite pedir detalles sin difundir primero la acusación."),
        "Naira": ("Escuchemos a Mira y a las personas involucradas antes de decidir.", "Necesitamos hechos concretos, no comentarios sobre cómo creemos que es ella."),
    },
}

REACCIONES = {
    "Rumor Politico": {
        "Colgarla": "La noticia sobre Kael se difundió sin verificar y ahora hay dudas entre las familias.",
        "Quemarla": "La tablilla desapareció, pero seguimos sin saber si lo que decía era cierto.",
        "Consultar": "Consultar la tablilla permitió revisar el rumor antes de tomar una decisión.",
    },
    "Suceso Natural": {
        "Colgarla": "El aviso del rayo llegó a la aldea y pudimos prepararnos.",
        "Quemarla": "Al desaparecer el aviso del rayo, las plataformas se quedaron sin información útil.",
        "Consultar": "El suceso se confirmó y las plataformas cercanas recibieron el aviso.",
        "Ignorarla": "El aviso llegó tarde y algunas rutas quedaron sin preparar.",
    },
    "Acusacion Personal": {
        "Colgarla": "El mensaje sobre Mira se está propagando y aumenta la desconfianza.",
        "Quemarla": "La tablilla ya no circula y se evitó un conflicto entre habitantes.",
        "Consultar": "La consulta aportó información antes de juzgar a Mira.",
        "Ignorarla": "La tablilla se perdió entre otras, pero las dudas sobre Mira siguen circulando.",
    },
}


def construir_conversacion(nombre, estado, vistas):
    """Las conversaciones vistas se registran por tablilla y personaje."""
    ruta = estado.ruta_categoria_actual()
    categoria = ruta[1] if len(ruta) > 1 else ""
    clave = (estado.tablillas_resueltas, nombre)
    inicial, ampliacion = TESTIMONIOS.get(categoria, {}).get(nombre, (
        "Escucha a quienes estuvieron presentes y compara sus testimonios.",
        "Revisa de dónde viene cada mensaje antes de compartirlo.",
    ))
    texto = ampliacion if clave in vistas else inicial
    if categoria == "Acusacion Personal" and "reparar" in estado.texto_actual().lower():
        texto = {
            "Mira": "Propuse ayudar a reparar el puente. Pregunta al consejo qué ayuda se necesita antes de repetir otras versiones.",
            "Kael": "Podemos discutir la propuesta de reparación de Mira con el consejo. Primero hay que revisar los daños.",
            "Mensajero": "Puedo llevar al consejo la propuesta de Mira para reparar el puente.",
        }.get(nombre, "La tablilla habla de reparar el puente. Comparemos la propuesta de Mira con lo que escuchó el consejo.")
    elif "Consultar" in estado.camino_decision_actual:
        texto = ampliacion
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
        "Rumor Politico": ("Kael y el puente norte", "¿Quién escuchó la propuesta de Kael sobre el puente?"),
        "Suceso Natural": ("el rayo del Mirador Alto", "¿Quién vio el rayo y dónde cayó?"),
        "Acusacion Personal": ("la tablilla sobre Mira", "Escuchemos a Mira y a quienes estuvieron presentes."),
    }.get(categoria, ("las noticias de la aldea", "Comparemos las fuentes de las noticias."))
    if categoria == "Acusacion Personal" and "reparar" in estado.texto_actual().lower():
        tema, consulta = "la reparación del puente", "¿Qué propone Mira para reparar el puente?"
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
