"""HUD del modo un jugador: objetivo, flecha guía, pistas, celular y controles."""

import math
import pygame
from logica.dimensiones import DIMENSION_LA_COPA
from logica.dimensiones import DIMENSION_PRESENTE
from mundo.camara import posicion_mundo_a_pantalla
from nucleo.config import ALTO, ANCHO, CENTRO_CALDERO, CREMA, ORO
from nucleo.recursos import dibujar_sprite_en_rect, envolver_texto, superficie_con_alpha


def dibujar_mensaje_mapa(superficie, fuente, texto):
    panel = pygame.Rect(205, ALTO - 86, 550, 54)
    fondo = superficie_con_alpha(panel.size, (20, 32, 27, 225))
    superficie.blit(fondo, panel.topleft)
    pygame.draw.rect(superficie, ORO, panel, width=2, border_radius=10)
    lineas = envolver_texto(texto, fuente, panel.width - 28)
    y = panel.y + 10
    for linea in lineas[:2]:
        render = fuente.render(linea, True, CREMA)
        superficie.blit(render, (panel.x + 14, y))
        y += 22


def texto_tutorial_primer_evento(estado, mundo, conversaciones_vistas):
    if (
        mundo.get("dimension") != DIMENSION_LA_COPA
        or estado.tablillas_resueltas
        or estado.evento_resuelto()
    ):
        return None

    ruta_categoria = estado.ruta_categoria_actual()
    categoria = ruta_categoria[1] if len(ruta_categoria) > 1 else "Primer evento"
    categoria = {
        "Rumor Politico": "Rumor político",
        "Suceso Natural": "Suceso natural",
        "Acusacion Personal": "Acusación personal",
    }.get(categoria, categoria)
    if conversaciones_vistas:
        return (
            f"EVENTO: {categoria}. Ahora ve al Caldero central y pulsa E "
            "para revisar la tablilla."
        )
    return (
        f"PRIMER EVENTO: {categoria}. Habla con alguien (E); luego "
        "consulta la tablilla del Caldero."
    )


def celular_disponible(estado):
    return estado.dimension_actual == DIMENSION_PRESENTE


def instrucciones_dimension(dimension):
    if dimension == DIMENSION_PRESENTE:
        return (
            "DISTRITO CONECTA · CONTROLES BÁSICOS",
            (
                "Muévete con WASD o las flechas. Acércate a alguien y pulsa E para hablar.",
                "Investiga la publicación y reúne testimonios antes de clasificarla.",
                "C abre el celular y su feed; J abre misiones, pistas e historia.",
                "Q difunde una corrección después de verificarla. Esc abre/cierra menús.",
            ),
        )
    return (
        "LA COPA · CONTROLES BÁSICOS",
        (
            "Muévete con WASD o las flechas. Acércate a alguien y pulsa E para hablar.",
            "Escucha testimonios y ve al Caldero para investigar y decidir sobre tablillas.",
            "J abre misiones, pistas e historia. Q activa el impulso del Guardián.",
            "Misión secundaria: reúne tablas, cuerda y herramientas; repara el Puente Norte.",
        ),
    )


def rectangulos_selector_mision():
    return (
        pygame.Rect(116, 188, 350, 34),
        pygame.Rect(494, 188, 350, 34),
    )


def controles_hud(estado):
    controles = [
        ("WASD / flechas", "Moverse"),
        ("E", "Interactuar"),
        ("J", "Bitácora"),
        ("Q", "Habilidad"),
        ("Tab", "Cambiar objetivo"),
        ("Esc / P", "Pausa"),
    ]
    if celular_disponible(estado):
        controles.append(("C", "Celular"))
    return controles


def rect_controles_hud(hud, estado):
    alto_indicadores = max(58, len(hud.objetivos) * 52 + 10)
    controles = controles_hud(estado)
    return pygame.Rect(
        9,
        8 + alto_indicadores + 5,
        216,
        18 + len(controles) * 20,
    )


def dibujar_controles_hud(superficie, fuente, hud, estado):
    controles = controles_hud(estado)
    panel = rect_controles_hud(hud, estado)
    pygame.draw.rect(superficie, (10, 27, 20, 200), panel, border_radius=8)
    pygame.draw.rect(superficie, (202, 151, 77), panel, 1, border_radius=8)
    for indice, (tecla, accion) in enumerate(controles):
        y = panel.y + 7 + indice * 20
        etiqueta_tecla = fuente.render(tecla, True, (255, 220, 136))
        etiqueta_accion = fuente.render(accion, True, CREMA)
        superficie.blit(etiqueta_tecla, (panel.x + 8, y))
        superficie.blit(etiqueta_accion, (panel.x + 90, y))


def objetivo_mision_actual(
    estado,
    mundo,
    conversaciones_vistas,
    mision_seleccionada="principal",
):
    """Devuelve el siguiente destino claro; las pistas abiertas no fuerzan una ruta."""
    if mundo.get("edificio_interior"):
        salida = next(
            (
                objeto for objeto in mundo.get("interacciones", [])
                if objeto.get("accion") == "salir_edificio"
                and objeto.get("activo", True)
            ),
            None,
        )
        return (
            (salida["rect"].center, "Salir del edificio")
            if salida else None
        )
    if mundo.get("dimension") == DIMENSION_LA_COPA:
        if mision_seleccionada == "secundaria":
            reparacion = mundo.get("reparacion_puentes")
            if reparacion is None or reparacion.estado == "REPAIRED":
                return None
            faltantes = set(reparacion.MATERIALES) - reparacion.materiales_recogidos
            if faltantes:
                siguiente_material = next(
                    (
                        material
                        for material in reparacion.PLATAFORMAS_MATERIALES.values()
                        if material in faltantes
                    ),
                    None,
                )
                interaccion = next(
                    (
                        objeto for objeto in mundo["interacciones"]
                        if objeto.get("accion") == "recolectar_material"
                        and objeto.get("material") == siguiente_material
                        and objeto.get("activo")
                    ),
                    None,
                )
                if interaccion:
                    return (
                        interaccion["rect"].center,
                        f"Recoger {siguiente_material}",
                    )
                return None
            puente = next(
                (
                    objeto for objeto in mundo["interacciones"]
                    if objeto.get("accion") == "reparar_puente"
                    and objeto.get("activo")
                ),
                None,
            )
            return (
                (puente["rect"].center, "Reconstruir Puente Norte")
                if puente else None
            )
        if estado.juego_terminado():
            portal = next(
                (
                    objeto for objeto in mundo["interacciones"]
                    if objeto.get("accion") == "portal_temporal" and objeto.get("activo")
                ),
                None,
            )
            return (portal["rect"].center, "Portal al presente") if portal else None
        if estado.tablillas_resueltas or conversaciones_vistas:
            caldero = next(
                (
                    objeto for objeto in mundo["interacciones"]
                    if objeto.get("accion") == "tablilla"
                ),
                None,
            )
            return (
                caldero["rect"].center if caldero else CENTRO_CALDERO,
                "Caldero central",
            )
        return None

    if mundo.get("dimension") != DIMENSION_PRESENTE:
        return None
    mision = estado.mision_presente
    if mision["estado"] == "completada":
        return None

    if not mision.get("publicacion_examinada"):
        pantalla = next(
            (
                objeto for objeto in mundo["interacciones"]
                if objeto.get("accion") == "examinar_publicacion"
                or objeto.get("tipo") == "pantalla_publica"
            ),
            None,
        )
        return (pantalla["rect"].center, "Publicación digital") if pantalla else None

    personaje_por_pista = {
        "fuente_ausente": "Darío Veraz",
        "testimonio_y_contexto": "Tomás Red",
        "respuesta_kael": "Ronaldo Vélez",
    }
    if any(pista not in mision["pistas"] for pista in personaje_por_pista):
        return None

    pantalla = next(
        (
            objeto for objeto in mundo["interacciones"]
            if objeto.get("accion") == "examinar_publicacion"
            or objeto.get("tipo") == "pantalla_publica"
        ),
        None,
    )
    return (pantalla["rect"].center, "Clasificar la publicación") if pantalla else None


_FLECHA_GUIA = None


def dibujar_flecha_objetivo(superficie, mundo, objetivo, fuente):
    posicion_objetivo, etiqueta = objetivo
    jugador = mundo["jugador"]
    origen = pygame.Vector2(posicion_mundo_a_pantalla(jugador["pies"].center, mundo))
    destino = pygame.Vector2(posicion_mundo_a_pantalla(posicion_objetivo, mundo))
    direccion = destino - origen
    if direccion.length_squared() == 0:
        return
    # Flecha de hojas animada (arte real IndicadorDirrKael.png) en lugar del
    # polígono dibujado por código; misma orientación y mismos márgenes.
    global _FLECHA_GUIA
    if _FLECHA_GUIA is None:
        from interfaz.efectos_visuales import FlechaGuia
        _FLECHA_GUIA = FlechaGuia()
    _FLECHA_GUIA.dibujar(superficie, origen, destino, pygame.time.get_ticks())

    texto = fuente.render(f"OBJETIVO: {etiqueta}", True, (255, 226, 104))
    panel = texto.get_rect(midtop=(ANCHO // 2, 14)).inflate(22, 12)
    pygame.draw.rect(superficie, (18, 30, 25), panel, border_radius=7)
    pygame.draw.rect(superficie, (255, 207, 48), panel, 2, border_radius=7)
    superficie.blit(texto, texto.get_rect(center=panel.center))


def dibujar_pistas_mision(superficie, recursos, estado):
    if (
        estado.dimension_actual != DIMENSION_PRESENTE
        or estado.mision_presente["estado"] == "completada"
        or not estado.mision_presente.get("publicacion_examinada")
    ):
        return
    pistas = estado.mision_presente["pistas"]
    tareas = {
        "fuente_ausente": "Rastrea el archivo original.",
        "testimonio_y_contexto": "Contrasta el contexto con habitantes.",
        "respuesta_kael": "Revisa la agenda de Ronaldo Vélez.",
    }
    faltantes = [
        texto for pista, texto in tareas.items()
        if pista not in pistas
    ]
    if faltantes:
        lineas = ["PISTAS: investiga antes de concluir.", *faltantes]
    else:
        lineas = ["PISTAS completas.", "Vuelve a la publicación y clasifica la imagen."]

    fuente = recursos["fuente_categoria"]
    panel = pygame.Rect(690, 438, 256, 150)
    fondo = superficie_con_alpha(panel.size, (14, 30, 35, 226))
    superficie.blit(fondo, panel.topleft)
    pygame.draw.rect(superficie, (244, 194, 73), panel, 2, border_radius=8)
    y = panel.y + 12
    for texto in lineas:
        for linea in envolver_texto(texto, fuente, panel.width - 22):
            superficie.blit(fuente.render(linea, True, CREMA), (panel.x + 11, y))
            y += 20


def dibujar_celular_feed(superficie, recursos, estado):
    feed = recursos.get("feed_digital", [])
    superficie.blit(recursos["fondo_feed_digital"], (0, 0))
    entradas = list(reversed(feed[-10:]))
    actual = entradas[0] if entradas else {
        "titulo": "Bitácora digital",
        "texto": "Tus decisiones y publicaciones aparecerán aquí.",
        "tipo": "inicial",
    }

    nombre = recursos["fuente_panel_titulo"].render(
        "Elías Vega · Distrito Conecta",
        True,
        (31, 49, 62),
    )
    superficie.blit(nombre, (164, 91))
    rect_imagen = pygame.Rect(104, 194, 126, 126)
    pygame.draw.rect(superficie, (39, 50, 72), rect_imagen.inflate(6, 6), border_radius=5)
    imagen_publicacion = recursos.get("imagen_publicacion_aspirante")
    if imagen_publicacion:
        dibujar_sprite_en_rect(superficie, imagen_publicacion, rect_imagen)
    else:
        pygame.draw.rect(superficie, (167, 193, 214), rect_imagen, border_radius=5)

    fuente = recursos["fuente_panel"]
    titulo = fuente.render(actual["titulo"][:48], True, (30, 42, 59))
    superficie.blit(titulo, (246, 202))
    texto = actual["texto"]
    lineas = envolver_texto(texto, fuente, 355)
    for indice, linea in enumerate(lineas[:4]):
        render = fuente.render(linea, True, (44, 53, 69))
        superficie.blit(render, (246, 228 + indice * 23))
    clasificacion = estado.mision_presente.get("clasificacion")
    if clasificacion:
        etiqueta_clasificacion = (
            "IMAGEN GENERADA POR IA"
            if clasificacion == "generada_por_ia"
            else "IMAGEN AUTÉNTICA"
        )
        resultado_clasificacion = (
            "correcta" if estado.mision_presente.get("clasificacion_correcta")
            else "incorrecta"
        )
        estado_clasificacion = (
            f"{etiqueta_clasificacion} · clasificación {resultado_clasificacion}"
        )
    else:
        estado_clasificacion = "ORIGEN DE LA IMAGEN SIN CONFIRMAR"
    etiqueta_estado = recursos["fuente_categoria"].render(
        estado_clasificacion,
        True,
        (129, 59, 39) if clasificacion and not estado.mision_presente.get("clasificacion_correcta") else (38, 70, 83),
    )
    superficie.blit(etiqueta_estado, (246, 326))

    pistas = estado.mision_presente["pistas"]
    resumen = (
        f"Pistas reunidas: {len(pistas)}/{len(estado.PISTAS_PARA_VERIFICAR)}"
        if estado.dimension_actual == DIMENSION_PRESENTE
        else f"Decisiones registradas: {len(feed)}"
    )
    render_resumen = recursos["fuente_categoria"].render(
        resumen,
        True,
        (38, 70, 83),
    )
    superficie.blit(render_resumen, (90, 392))

    for indice in range(8):
        y = 116 + indice * 51
        if indice < len(entradas):
            titulo_feed = entradas[indice]["titulo"]
            texto_feed = recursos["fuente_categoria"].render(
                titulo_feed[:24],
                True,
                (42, 53, 70),
            )
            superficie.blit(texto_feed, (729, y))
        else:
            texto_feed = recursos["fuente_categoria"].render(
                "# DistritoConecta",
                True,
                (42, 53, 70),
            )
            superficie.blit(texto_feed, (729, y))

    panel_actividad = pygame.Rect(51, 553, 618, 137)
    pygame.draw.rect(superficie, (19, 39, 49), panel_actividad, border_radius=8)
    pygame.draw.rect(superficie, (83, 181, 178), panel_actividad, 2, border_radius=8)
    titulo_actividad = recursos["fuente_categoria"].render(
        "ACTIVIDAD RECIENTE",
        True,
        (153, 222, 214),
    )
    superficie.blit(titulo_actividad, (panel_actividad.x + 14, panel_actividad.y + 10))
    for indice, entrada in enumerate(entradas[1:4]):
        render_actividad = recursos["fuente_categoria"].render(
            entrada["titulo"][:60],
            True,
            CREMA,
        )
        superficie.blit(
            render_actividad,
            (panel_actividad.x + 14, panel_actividad.y + 34 + indice * 20),
        )
    instruccion = recursos["fuente_categoria"].render(
        "C o Esc: cerrar el celular · tus decisiones actualizan el feed",
        True,
        (153, 222, 214),
    )
    superficie.blit(
        instruccion,
        (panel_actividad.x + 14, panel_actividad.bottom - 24),
    )


def interaccion_en_mapa(posicion, mundo):
    for objeto in reversed(mundo["decoraciones"]):
        if (
            objeto["personaje"] and objeto["personaje"] != "Guardián"
            and objeto["hitbox"].collidepoint(posicion)
        ):
            return {
                "accion": "npc",
                "personaje": objeto["personaje"],
                "rect": objeto["hitbox"],
                "objeto": objeto,
            }

    for interaccion in mundo["interacciones"]:
        if interaccion.get("activo", True) and interaccion["rect"].collidepoint(posicion):
            return interaccion
    return None


def dibujar_brillo_interaccion(superficie, imagen, rect, cache):
    """Halo dorado que sigue la silueta, con una pulsación discreta."""
    if imagen not in cache:
        silueta = pygame.mask.from_surface(imagen).to_surface(
            setcolor=(*ORO, 255), unsetcolor=(0, 0, 0, 0))
        halo = pygame.Surface((rect.width + 20, rect.height + 20), pygame.SRCALPHA)
        for radio, alpha in ((9, 12), (6, 20), (3, 32)):
            silueta.set_alpha(alpha)
            for angulo in range(0, 360, 30):
                radianes = math.radians(angulo)
                halo.blit(silueta, (10 + round(math.cos(radianes) * radio),
                                    10 + round(math.sin(radianes) * radio)))
        cache[imagen] = halo
    halo = cache[imagen]
    halo.set_alpha(round(180 + 35 * math.sin(pygame.time.get_ticks() / 350)))
    superficie.blit(halo, (rect.x - 10, rect.y - 10))
    # Mantener el sprite nítido sobre el halo.
    superficie.blit(imagen, rect)
