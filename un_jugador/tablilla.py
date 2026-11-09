"""Tablilla: decisiones con pociones, consecuencia, clasificación y final."""

import math
import pygame
from interfaz.boton import Boton
from nucleo.config import ALTO, ANCHO, CENTRO_TABLILLA, CREMA, MADERA, ORO, PANEL_OSCURO, TINTA
from nucleo.recursos import envolver_texto, normalizar_ruta, superficie_con_alpha
from un_jugador.dibujo_mapa import dibujar_decoraciones_editor, dibujar_troncos_eco


def buscar_imagen_para_opcion(texto, imagenes):
    texto = texto.lower()
    if "colgar" in texto:
        return imagenes["colgar"]
    if "consultar" in texto:
        return imagenes["consultar"]
    if "quemar" in texto:
        return imagenes["quemar"]
    if "ignorar" in texto:
        return imagenes["ignorar"]
    return None


def construir_botones(opciones, imagenes, fuente):
    if not opciones:
        return []
    imagenes_opciones = [buscar_imagen_para_opcion(opcion, imagenes) for opcion in opciones]
    anchos = [imagen.get_width() if imagen else max(164, fuente.size(opcion)[0] + 28) for opcion, imagen in zip(opciones, imagenes_opciones)]
    separacion = 28
    ancho_total = sum(anchos) + separacion * (len(opciones) - 1)
    cursor = (ANCHO - ancho_total) / 2
    botones = []
    for opcion, imagen, ancho in zip(opciones, imagenes_opciones, anchos):
        centro = (int(cursor + ancho / 2), 635)
        botones.append(Boton(opcion, imagen, centro, fuente))
        cursor += ancho + separacion
    return botones


def imagen_boton_clasificacion(imagen, texto, fuente):
    boton = imagen.copy()
    lineas = envolver_texto(texto, fuente, boton.get_width() - 34)
    alto_linea = fuente.get_linesize()
    alto_total = len(lineas) * alto_linea
    y = int(boton.get_height() * .86 - alto_total / 2)
    for linea in lineas:
        etiqueta = fuente.render(linea, True, TINTA)
        sombra = fuente.render(linea, True, (255, 235, 168))
        rect = etiqueta.get_rect(center=(boton.get_width() // 2, y + alto_linea // 2))
        boton.blit(sombra, rect.move(1, 1))
        boton.blit(etiqueta, rect)
        y += alto_linea
    return boton


def construir_botones_clasificacion(opciones, recursos, fuente):
    if not opciones:
        return []
    imagenes = []
    for opcion in opciones:
        clave = normalizar_ruta(opcion).replace(" ", "_")
        base = recursos["botones_clasificacion"].get(clave)
        imagenes.append(imagen_boton_clasificacion(base, opcion, fuente) if base else None)

    anchos = [
        imagen.get_width() if imagen else max(164, fuente.size(opcion)[0] + 28)
        for opcion, imagen in zip(opciones, imagenes)
    ]
    separacion = 36
    ancho_total = sum(anchos) + separacion * (len(opciones) - 1)
    cursor = (ANCHO - ancho_total) / 2
    botones = []
    for opcion, imagen, ancho in zip(opciones, imagenes, anchos):
        centro = (int(cursor + ancho / 2), 570)
        botones.append(Boton(opcion, imagen, centro, fuente))
        cursor += ancho + separacion
    return botones


def dibujar_tablilla(superficie, tablilla, estado, fuente_texto, fuente_categoria):
    # Se desplaza a la derecha para reservar un margen real al HUD.
    rect = tablilla.get_rect(center=CENTRO_TABLILLA)
    superficie.blit(tablilla, rect)

    lineas = envolver_texto(estado.texto_actual(), fuente_texto, 365)
    y = rect.y + 265 - len(lineas) * 31 // 2
    for linea in lineas:
        texto = fuente_texto.render(linea, True, TINTA)
        superficie.blit(texto, texto.get_rect(center=(rect.centerx, y)))
        y += 31


def formatear_categoria(ruta):
    """Convierte la ruta interna del árbol en texto natural para el jugador."""
    nombres = {
        "Rumor Politico": "Rumor Político",
        "Suceso Natural": "Suceso Natural",
        "Acusacion Personal": "Acusación Personal",
    }
    ruta_visible = [nombres.get(nombre, nombre) for nombre in ruta if nombre != "Tablilla"]
    return ruta_visible[0] if ruta_visible else "Sin clasificación", ruta_visible[1:]


def nombre_indicador(nombre):
    nombres_visibles = {
        "grietas_puentes": "Desinformación",
        "desinformación": "Desinformación",
    }
    return nombres_visibles.get(nombre, nombre.replace("_", " ").capitalize())


def lineas_efecto(efecto):
    return [f"{'+' if valor > 0 else ''}{valor} {nombre_indicador(nombre)}" for nombre, valor in efecto.items()]


def estado_caldero(estado):
    desinformacion = estado.indicadores["desinformación"] + estado.indicadores["susurros_falsos"]
    if desinformacion >= 100:
        return "critico"
    if desinformacion >= 55:
        return "peligroso"
    return "estable"


def sincronizar_audio_caldero(gestor_audio, estado, estado_anterior):
    estado_actual = estado_caldero(estado)
    if estado_actual != estado_anterior:
        gestor_audio.procesar_evento({"tipo": "caldero", "estado": estado_actual})
    return estado_actual


def reproducir_audio_clasificacion(gestor_audio, estado):
    resultado = estado.resultado_evento_actual()
    if resultado and resultado["clasificacion_jugador"] is not None:
        gestor_audio.procesar_evento({
            "tipo": "clasificacion",
            "correcta": resultado["clasificacion_correcta"],
        })


def dibujar_consecuencia_evento(superficie, recursos, estado):
    """Muestra la consecuencia de la decisión antes de preguntar la categoría."""
    superficie.blit(fondo_tablilla_actual(recursos, estado), (0, 0))
    resultado = estado.resultado_evento_actual()
    panel = pygame.Rect(178, 175, 604, 345)
    fondo = superficie_con_alpha(panel.size, (18, 36, 29, 238))
    superficie.blit(fondo, panel.topleft)
    pygame.draw.rect(superficie, ORO, panel, width=3, border_radius=16)
    titulo = recursos["fuente_panel_titulo"].render("CONSECUENCIA DE TU DECISIÓN", True, ORO)
    superficie.blit(titulo, titulo.get_rect(center=(panel.centerx, panel.y + 52)))
    for indice, linea in enumerate(envolver_texto(resultado["resultado"], recursos["fuente_mapa"], panel.width - 80)):
        texto = recursos["fuente_mapa"].render(linea, True, CREMA)
        superficie.blit(texto, texto.get_rect(center=(panel.centerx, panel.y + 112 + indice * 28)))
    for indice, linea in enumerate(lineas_efecto(resultado["efecto_decision"])):
        color = (112, 207, 120) if linea.startswith("+") else (225, 106, 84)
        texto = recursos["fuente_panel"].render(linea, True, color)
        superficie.blit(texto, texto.get_rect(center=(panel.centerx, panel.y + 190 + indice * 28)))
    continuar = recursos["fuente_panel"].render("Haz clic para clasificar la tablilla", True, ORO)
    superficie.blit(continuar, continuar.get_rect(center=(panel.centerx, panel.bottom - 42)))


def dibujar_pregunta_clasificacion(superficie, recursos, estado, botones, mouse_pos,
                                   encabezado="¿CÓMO CLASIFICARÍAS ESTA TABLILLA?"):
    """Pide la clasificación sin mostrar cuál era la categoría real."""
    superficie.blit(fondo_tablilla_actual(recursos, estado), (0, 0))
    # En clasificación el HUD no se muestra para dejar aire al panel central.
    panel = recursos["panel_clasificacion"]
    rect = panel.get_rect(center=(ANCHO // 2, 238))
    superficie.blit(panel, rect)
    titulo = recursos["fuente_resultado"].render(encabezado, True, CREMA)
    superficie.blit(titulo, titulo.get_rect(center=(rect.centerx, rect.y + 122)))
    # El texto de ayuda se ajusta al interior útil del pergamino para que no
    # se salga por los bordes en ninguna resolución.
    lineas = envolver_texto(
        "Elige la categoría que consideres correcta",
        recursos["fuente_panel"],
        rect.width - 220,
    )
    y = rect.y + 168
    for linea in lineas:
        detalle = recursos["fuente_panel"].render(linea, True, CREMA)
        superficie.blit(detalle, detalle.get_rect(center=(rect.centerx, y)))
        y += 24
    for boton in botones:
        boton.dibujar(superficie, mouse_pos)


def dibujar_resultado_evento(superficie, recursos, estado):
    """Compara la respuesta de trivia con la categoría real del árbol."""
    superficie.blit(fondo_tablilla_actual(recursos, estado), (0, 0))
    resultado = estado.resultado_evento_actual()
    categoria, subcategorias = formatear_categoria(resultado["categoria"])
    marco = recursos["fondo_clasificacion"]
    rect = marco.get_rect(center=(ANCHO // 2, 355))
    superficie.blit(marco, rect)

    clasificacion = resultado["clasificacion_jugador"]
    acerto = resultado["clasificacion_correcta"]
    estado_respuesta = "CORRECTA" if acerto else "INCORRECTA"
    respuesta = recursos["fuente_panel"].render(
        f"Tu clasificación: {clasificacion} ({estado_respuesta})",
        True,
        (43, 120, 55) if acerto else (170, 63, 43),
    )
    superficie.blit(respuesta, respuesta.get_rect(center=(rect.centerx, rect.y + 182)))
    cambio_sabiduria = resultado.get("efecto_clasificacion", {}).get("sabiduria", 0)
    efecto = recursos["fuente_panel"].render(
        f"Sabiduría: {'+' if cambio_sabiduria > 0 else ''}{cambio_sabiduria} puntos",
        True,
        (43, 120, 55) if cambio_sabiduria > 0 else (170, 63, 43),
    )
    superficie.blit(efecto, efecto.get_rect(center=(rect.centerx, rect.y + 204)))
    introduccion = recursos["fuente_mapa"].render("En realidad era un", True, TINTA)
    superficie.blit(introduccion, introduccion.get_rect(center=(rect.centerx, rect.y + 240)))
    categoria_texto = recursos["fuente_resultado"].render(categoria.upper(), True, (48, 121, 61))
    superficie.blit(categoria_texto, categoria_texto.get_rect(center=(rect.centerx, rect.y + 288)))
    if subcategorias:
        detalle = recursos["fuente_panel"].render(f"Subcategoría: {' · '.join(subcategorias)}", True, TINTA)
        superficie.blit(detalle, detalle.get_rect(center=(rect.centerx, rect.y + 328)))

    consecuencia = envolver_texto(resultado["resultado"], recursos["fuente_mapa"], rect.width - 150)
    y = rect.y + 378
    for linea in consecuencia:
        texto = recursos["fuente_mapa"].render(linea, True, TINTA)
        superficie.blit(texto, texto.get_rect(center=(rect.centerx, y)))
        y += 27
    continuar = recursos["fuente_panel"].render("Haz clic para continuar", True, MADERA)
    superficie.blit(continuar, continuar.get_rect(center=(rect.centerx, rect.bottom - 56)))


def dibujar_arbol_clasificacion(superficie, estado, fuente_titulo, fuente):
    panel = pygame.Rect(24, 174, 250, 214)
    fondo = superficie_con_alpha(panel.size, PANEL_OSCURO)
    superficie.blit(fondo, panel.topleft)
    pygame.draw.rect(superficie, ORO, panel, width=2, border_radius=10)
    titulo = fuente_titulo.render("Arbol de clasificacion", True, ORO)
    superficie.blit(titulo, (panel.x + 12, panel.y + 10))

    raiz = (panel.centerx, panel.y + 43)
    ramas = {
        "Rumor Politico": (panel.x + 52, panel.y + 93),
        "Suceso Natural": (panel.centerx, panel.y + 93),
        "Acusacion Personal": (panel.right - 52, panel.y + 93),
    }
    hojas = {
        "Rumor Politico": ((panel.x + 35, panel.y + 157), (panel.x + 69, panel.y + 157),
                           ("Aspirante", "Consejo")),
        "Suceso Natural": ((panel.centerx - 17, panel.y + 157), (panel.centerx + 17, panel.y + 157),
                           ("Clima", "Fauna")),
        "Acusacion Personal": ((panel.right - 69, panel.y + 157), (panel.right - 35, panel.y + 157),
                                ("Aspirantes", "Habitantes")),
    }
    ruta_actual = estado.ruta_categoria_actual()
    pygame.draw.line(superficie, ORO, raiz, ramas["Rumor Politico"], 2)
    pygame.draw.line(superficie, ORO, raiz, ramas["Suceso Natural"], 2)
    pygame.draw.line(superficie, ORO, raiz, ramas["Acusacion Personal"], 2)
    dibujar_nodo_clasificacion(superficie, raiz, "Tablilla", ORO, fuente)
    for nombre, posicion in ramas.items():
        color = (101, 184, 105) if nombre in ruta_actual else ORO
        dibujar_nodo_clasificacion(superficie, posicion, nombre, color, fuente)
        punto_a, punto_b, nombres_hoja = hojas[nombre]
        pygame.draw.line(superficie, color, posicion, punto_a, 2)
        pygame.draw.line(superficie, color, posicion, punto_b, 2)
        for punto, nombre_hoja in zip((punto_a, punto_b), nombres_hoja):
            color_hoja = (101, 184, 105) if nombre_hoja in ruta_actual else (219, 184, 96)
            dibujar_nodo_clasificacion(superficie, punto, nombre_hoja, color_hoja, fuente)


def dibujar_nodo_clasificacion(superficie, posicion, nombre, color, fuente):
    pygame.draw.circle(superficie, color, posicion, 5)
    etiqueta = fuente.render(nombre, True, CREMA)
    rect = etiqueta.get_rect(midtop=(posicion[0], posicion[1] + 7))
    superficie.blit(etiqueta, rect)


def dibujar_arbol_decision(superficie, estado, fuente_titulo, fuente):
    panel = pygame.Rect(682, 188, 248, 182)
    fondo = superficie_con_alpha(panel.size, PANEL_OSCURO)
    superficie.blit(fondo, panel.topleft)
    pygame.draw.rect(superficie, ORO, panel, width=2, border_radius=10)
    titulo = fuente_titulo.render("Arbol de decisiones", True, ORO)
    superficie.blit(titulo, (panel.x + 12, panel.y + 10))

    if estado.juego_terminado():
        texto = fuente.render("Hoja final: resumen", True, CREMA)
        superficie.blit(texto, (panel.x + 18, panel.y + 66))
        return

    raiz = (panel.centerx, panel.y + 64)
    pygame.draw.circle(superficie, (219, 184, 96), raiz, 12)
    nodo = fuente.render("Nodo actual", True, CREMA)
    superficie.blit(nodo, nodo.get_rect(center=(raiz[0], raiz[1] - 28)))

    opciones = estado.opciones_actuales()
    if not opciones:
        hoja = fuente.render("Hoja: efecto aplicado", True, CREMA)
        superficie.blit(hoja, hoja.get_rect(center=(panel.centerx, panel.y + 120)))
        return

    ancho = min(190, 52 * max(1, len(opciones) - 1))
    inicio_x = panel.centerx - ancho // 2
    for i, opcion in enumerate(opciones):
        x = inicio_x + int(i * (ancho / max(1, len(opciones) - 1)))
        y = panel.y + 128
        pygame.draw.line(superficie, (219, 184, 96), raiz, (x, y), 2)
        pygame.draw.circle(superficie, (101, 159, 105), (x, y), 9)
        etiqueta = opcion[:12]
        texto = fuente.render(etiqueta, True, CREMA)
        superficie.blit(texto, texto.get_rect(center=(x, y + 22)))


def dibujar_tablilla_en_efecto(superficie, recursos, estado, animacion):
    """Anima la tablilla real para que la decisión afecte al objeto, no a un icono."""
    tiempo_efecto = (
        animacion["tiempo_transcurrido"]
        - animacion["duracion_lanzamiento"]
        - animacion["duracion_splash"]
    )
    progreso = max(
        0.0,
        min(1.0, tiempo_efecto / animacion["duracion_efecto"]),
    )
    tablilla = recursos["tablilla"].copy()
    lineas = envolver_texto(estado.texto_actual(), recursos["fuente_texto"], 365)
    y = 265 - len(lineas) * 31 // 2
    for linea in lineas:
        texto = recursos["fuente_texto"].render(linea, True, TINTA)
        tablilla.blit(texto, texto.get_rect(center=(tablilla.get_width() // 2, y)))
        y += 31

    clave = animacion["clave"]
    colores = {
        "colgar": (248, 202, 76),
        "consultar": (80, 181, 255),
        "quemar": (255, 77, 35),
        "ignorar": (179, 97, 230),
    }
    color = colores[clave]
    borde_quema = []

    # La textura también ocurre sobre la tablilla: no se trata de un icono
    # superpuesto sino del objeto del juego respondiendo a la elección.
    velo = pygame.Surface(tablilla.get_size(), pygame.SRCALPHA)
    pulso = math.sin(progreso * math.pi)
    if clave == "quemar":
        # El fuego cierra desde todos los bordes, conservando un trozo central
        # cada vez menor de pergamino.
        ancho_tablilla, alto_tablilla = tablilla.get_size()
        mascara = pygame.Surface(tablilla.get_size(), pygame.SRCALPHA)
        mascara.fill((0, 0, 0, 0))
        if progreso < .985:
            inset_x = ancho_tablilla * progreso * .50
            inset_y = alto_tablilla * progreso * .50
            amplitud = 22 * progreso
            for indice in range(6):
                x = inset_x + (ancho_tablilla - inset_x * 2) * indice / 5
                y = inset_y + math.sin(indice * 2.7) * amplitud
                borde_quema.append((int(x), int(y)))
            for indice in range(1, 6):
                x = ancho_tablilla - inset_x + math.cos(indice * 2.1) * amplitud
                y = inset_y + (alto_tablilla - inset_y * 2) * indice / 5
                borde_quema.append((int(x), int(y)))
            for indice in range(1, 6):
                x = ancho_tablilla - inset_x - (ancho_tablilla - inset_x * 2) * indice / 5
                y = alto_tablilla - inset_y + math.sin(indice * 2.2 + 1) * amplitud
                borde_quema.append((int(x), int(y)))
            for indice in range(1, 5):
                x = inset_x + math.cos(indice * 2.4 + 1) * amplitud
                y = alto_tablilla - inset_y - (alto_tablilla - inset_y * 2) * indice / 5
                borde_quema.append((int(x), int(y)))
            pygame.draw.polygon(mascara, (255, 255, 255, 255), borde_quema)
            pygame.draw.lines(velo, (48, 20, 10, 230), True, borde_quema, 14)
            pygame.draw.lines(velo, (230, 86, 18, 245), True, borde_quema, 5)
    elif clave == "consultar":
        linea_y = int((tablilla.get_height() + 54) * progreso) - 27
        pygame.draw.rect(velo, (*color, 56), (0, linea_y - 28, tablilla.get_width(), 56))
        pygame.draw.line(velo, (*color, 255), (18, linea_y), (tablilla.get_width() - 18, linea_y), 5)
        pygame.draw.rect(velo, (*color, int(85 + 70 * pulso)), velo.get_rect(), width=5, border_radius=16)
    elif clave == "ignorar":
        pygame.draw.rect(velo, (28, 18, 47, int(188 * progreso)), velo.get_rect(), border_radius=18)
    else:  # colgar
        pygame.draw.rect(velo, (*color, int(68 * (1 - progreso))), velo.get_rect(), width=7, border_radius=18)
    tablilla.blit(velo, (0, 0))
    if clave == "quemar":
        tablilla.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    escala, angulo, desplazamiento, alfa = 1.0, 0, (0, 0), 255
    if clave == "quemar":
        # La desaparición la controla la máscara de fuego, no un fundido.
        angulo = math.sin(progreso * 36) * (1 - progreso) * 1.5
    elif clave == "consultar":
        escala = 1 + 0.05 * abs(pygame.math.Vector2(1, 0).rotate(progreso * 720).x)
    elif clave == "colgar":
        desplazamiento = (0, -86 * progreso)
        escala = 1 - 0.12 * progreso
    elif clave == "ignorar":
        desplazamiento = (122 * progreso, 38 * progreso)
        alfa = int(255 * (1 - 0.90 * progreso))
        angulo = 12 * progreso

    ancho = max(1, round(tablilla.get_width() * escala))
    alto = max(1, round(tablilla.get_height() * escala))
    tablilla = pygame.transform.smoothscale(tablilla, (ancho, alto))
    if angulo:
        tablilla = pygame.transform.rotate(tablilla, angulo)
    tablilla.set_alpha(alfa)
    centro = (CENTRO_TABLILLA[0] + desplazamiento[0], CENTRO_TABLILLA[1] + desplazamiento[1])
    rect = tablilla.get_rect(center=centro)

    # Resplandor grande detrás de la tablilla, limitado para no tapar el mapa.
    halo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    radio = int(135 + 95 * pulso)
    pygame.draw.circle(halo, (*color, int(24 + 42 * pulso)), centro, radio)
    pygame.draw.circle(halo, (*color, int(28 + 34 * pulso)), centro, max(20, radio - 36))
    superficie.blit(halo, (0, 0))
    superficie.blit(tablilla, rect)

    if clave == "quemar" and borde_quema:
        # Un borde carbonizado rompe la tablilla y los trozos caen: no hay una
        # capa de llamas decorativa cubriendo el pergamino.
        fragmentos = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        borde_global = [
            (rect.left + int(x / recursos["tablilla"].get_width() * rect.width), rect.top + int(y / recursos["tablilla"].get_height() * rect.height))
            for x, y in borde_quema
        ]
        for indice, (x, base) in enumerate(borde_global):
            if indice < len(borde_global) - 1:
                siguiente = borde_global[indice + 1]
                pygame.draw.line(fragmentos, (34, 18, 11, 238), (x, base), siguiente, 10)
                pygame.draw.line(fragmentos, (182, 73, 27, 215), (x, base), siguiente, 3)
            # Pequeñas lenguas de fuego adheridas a todo el contorno, no solo
            # al borde inferior. Apuntan hacia fuera del pergamino.
            if indice % 2 == 0:
                dx, dy = x - rect.centerx, base - rect.centery
                distancia = max(1, math.hypot(dx, dy))
                nx, ny = dx / distancia, dy / distancia
                tx, ty = -ny, nx
                largo = int(13 + 20 * pulso + indice % 4 * 4)
                punta = (int(x + nx * largo), int(base + ny * largo))
                izquierda = (int(x + tx * 7), int(base + ty * 7))
                derecha = (int(x - tx * 7), int(base - ty * 7))
                pygame.draw.polygon(fragmentos, (226, 62, 10, 235), [izquierda, derecha, punta])
                punta_interior = (int(x + nx * (largo * .62)), int(base + ny * (largo * .62)))
                pygame.draw.polygon(fragmentos, (255, 178, 28, 245), [(x, base), izquierda, punta_interior, derecha])
            if indice % 2 == 0:
                caida = int(16 + progreso * (42 + indice * 4))
                tamano = 5 + indice % 5
                deriva = int(math.sin(progreso * 9 + indice) * (10 + indice % 3 * 5))
                pygame.draw.polygon(
                    fragmentos,
                    (202, 133, 79, int(235 * (1 - progreso * .35))),
                    [(x - tamano, base + 3), (x + tamano, base + 5), (x + deriva + 2, base + caida), (x + deriva - 5, base + caida - 3)],
                )
        for indice in range(16):
            x, borde_y = borde_global[indice % len(borde_global)]
            dx, dy = x - rect.centerx, borde_y - rect.centery
            distancia = max(1, math.hypot(dx, dy))
            y = borde_y + int(dy / distancia * (18 + (indice % 5) * 12 * progreso))
            x += int(dx / distancia * (18 + (indice % 5) * 12 * progreso))
            pygame.draw.circle(fragmentos, (72, 42, 26, int(190 * (1 - progreso * .25))), (x, y), 2 + indice % 3)
        superficie.blit(fragmentos, (0, 0))
    elif clave == "consultar":
        brillo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        y_scan = rect.top + int(rect.height * progreso)
        pygame.draw.line(brillo, (*color, 255), (rect.left + 22, y_scan), (rect.right - 22, y_scan), 4)
        pygame.draw.rect(brillo, (*color, 165), rect, width=3, border_radius=18)
        # Retícula que inspecciona directamente el contenido de la tablilla.
        x_lente = rect.left + int(rect.width * (0.18 + progreso * .64))
        radio_lente = int(27 + 8 * pulso)
        pygame.draw.circle(brillo, (*color, 72), (x_lente, y_scan), radio_lente)
        pygame.draw.circle(brillo, (*color, 245), (x_lente, y_scan), radio_lente, 3)
        pygame.draw.line(brillo, (*color, 230), (x_lente + radio_lente // 2, y_scan + radio_lente // 2), (x_lente + radio_lente + 16, y_scan + radio_lente + 16), 4)
        for indice in range(7):
            px = rect.left + 30 + (indice * 53) % max(1, rect.width - 60)
            pygame.draw.circle(brillo, (*color, 180), (px, y_scan), 3)
        for indice in range(3):
            radio_onda = int(42 + progreso * 105 + indice * 30)
            pygame.draw.circle(brillo, (*color, max(0, 120 - indice * 32)), rect.center, radio_onda, 2)
        superficie.blit(brillo, (0, 0))
    elif clave == "colgar":
        cuerdas = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        for x in (rect.left + rect.width // 3, rect.right - rect.width // 3):
            pygame.draw.line(cuerdas, (104, 59, 31, 255), (x + 2, 0), (x + 2, rect.top + 20), 7)
            pygame.draw.line(cuerdas, (247, 210, 116, 230), (x, 0), (x, rect.top + 18), 3)
        for indice in range(10):
            angulo_destello = progreso * 6.5 + indice * math.tau / 10
            distancia = 125 + indice % 3 * 28
            x = int(rect.centerx + math.cos(angulo_destello) * distancia)
            y = int(rect.centery + math.sin(angulo_destello) * distancia * .65)
            pygame.draw.circle(cuerdas, (255, 224, 120, int(210 * pulso)), (x, y), 3 + indice % 3)
        superficie.blit(cuerdas, (0, 0))
    else:  # ignorar
        sombra = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        for indice in range(4):
            distancia = (indice + 1) * 18 * progreso
            sombra_rect = rect.move(-distancia, -distancia // 3)
            pygame.draw.rect(sombra, (*color, int(40 * (1 - indice / 5))), sombra_rect, width=3, border_radius=18)
        for indice in range(14):
            x = rect.left + (indice * 37) % max(1, rect.width)
            y = rect.top + (indice * 61) % max(1, rect.height)
            pygame.draw.circle(sombra, (*color, int(110 * progreso)), (x, y), 3 + indice % 3)
        pygame.draw.rect(sombra, (12, 8, 24, int(105 * progreso)), rect, width=7, border_radius=18)
        superficie.blit(sombra, (0, 0))


def dibujar_escena_tablilla(superficie, recursos, estado, botones, mouse_pos, hud, animacion=None):
    superficie.blit(fondo_tablilla_actual(recursos, estado), (0, 0))
    hud.dibujar(superficie)
    if animacion and animacion["tiempo_transcurrido"] >= (
        animacion["duracion_lanzamiento"] + animacion["duracion_splash"]
    ):
        dibujar_tablilla_en_efecto(superficie, recursos, estado, animacion)
    else:
        dibujar_tablilla(superficie, recursos["tablilla"], estado, recursos["fuente_texto"], recursos["fuente_categoria"])

    if animacion:
        dibujar_animacion_pocion(superficie, recursos, animacion)

    if estado.juego_terminado():
        aviso = recursos["fuente_boton"].render("Ronda terminada - Presiona ESC para salir", True, CREMA)
        superficie.blit(aviso, aviso.get_rect(center=(ANCHO // 2, 635)))
    else:
        for boton in botones:
            boton.dibujar(superficie, mouse_pos)


def clave_pocion(opcion):
    opcion = opcion.lower()
    if "colgar" in opcion:
        return "colgar"
    if "consultar" in opcion:
        return "consultar"
    if "quemar" in opcion:
        return "quemar"
    return "ignorar"


def accion_tablilla(opcion):
    texto = normalizar_ruta(opcion)
    for accion in ("colgar", "consultar", "quemar", "ignorar"):
        if accion in texto:
            return accion
    return None


def iniciar_animacion_decision(opcion):
    """Muestra el lanzamiento y el impacto antes de aplicar la decisión."""
    clave = clave_pocion(opcion)
    duracion_efecto = 1.65 if clave == "quemar" else 1.25
    duracion_lanzamiento = 0.48
    duracion_splash = 0.32
    duracion = duracion_lanzamiento + duracion_splash + duracion_efecto
    return {
        "clave": clave,
        "opcion": opcion,
        "restante": duracion,
        "duracion": duracion,
        "duracion_lanzamiento": duracion_lanzamiento,
        "duracion_splash": duracion_splash,
        "duracion_efecto": duracion_efecto,
        "tiempo_transcurrido": 0.0,
    }


def dibujar_animacion_pocion(superficie, recursos, animacion):
    tiempo = animacion["tiempo_transcurrido"]
    lanzamiento = animacion["duracion_lanzamiento"]
    splash = animacion["duracion_splash"]
    imagen = recursos["pociones"][animacion["clave"]]
    nombre = {
        "colgar": "Colgar",
        "consultar": "Consultar",
        "quemar": "Quemar",
        "ignorar": "Ignorar",
    }[animacion["clave"]]
    if tiempo < lanzamiento:
        progreso = tiempo / lanzamiento
        inicio = pygame.Vector2(350, 610)
        fin = pygame.Vector2(*CENTRO_TABLILLA)
        posicion = inicio.lerp(fin, progreso)
        posicion.y -= math.sin(progreso * math.pi) * 76
        botella = pygame.transform.smoothscale(imagen, (74, 74))
        botella = pygame.transform.rotate(botella, -progreso * 300)
        botella.set_alpha(255)
        superficie.blit(botella, botella.get_rect(center=posicion))
        texto_fase = f"Lanzando poción de {nombre}..."
    elif tiempo < lanzamiento + splash:
        progreso = (tiempo - lanzamiento) / splash
        duracion_alfa = max(0, round(255 * (1 - progreso)))
        color = {
            "colgar": (255, 207, 48),
            "consultar": (80, 181, 255),
            "quemar": (255, 87, 32),
            "ignorar": (179, 97, 230),
        }[animacion["clave"]]
        splash_surface = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        centro = CENTRO_TABLILLA
        radio = int(20 + progreso * 82)
        pygame.draw.circle(splash_surface, (*color, duracion_alfa // 3), centro, radio)
        pygame.draw.circle(splash_surface, (*color, duracion_alfa), centro, radio, 6)
        for indice in range(10):
            angulo = indice * math.tau / 10
            distancia = 24 + progreso * 66
            gota = (
                round(centro[0] + math.cos(angulo) * distancia),
                round(centro[1] + math.sin(angulo) * distancia),
            )
            pygame.draw.circle(
                splash_surface,
                (*color, duracion_alfa),
                gota,
                max(2, round(7 * (1 - progreso * 0.6))),
            )
        superficie.blit(splash_surface, (0, 0))
        texto_fase = "¡Splash! Aplicando la decisión..."
    else:
        texto_fase = f"Efecto de la poción: {nombre}"

    render_fase = recursos["fuente_panel_titulo"].render(texto_fase, True, CREMA)
    caja_fase = render_fase.get_rect(midtop=(ANCHO // 2, 116)).inflate(24, 12)
    pygame.draw.rect(superficie, (18, 31, 25), caja_fase, border_radius=7)
    pygame.draw.rect(superficie, ORO, caja_fase, 2, border_radius=7)
    superficie.blit(render_fase, render_fase.get_rect(center=caja_fase.center))


def rectangulos_pociones(recursos):
    return {
        clave: recursos["pociones"][clave].get_rect(center=(744 + indice * 52, 88))
        for indice, clave in enumerate(("colgar", "consultar", "quemar", "ignorar"))
    }


def dibujar_pociones(superficie, recursos, usos, animacion, mouse_pos):
    """Inventario compacto: cada decisión lanza automáticamente su pócima."""
    nombres = {"colgar": "Colgar", "consultar": "Consultar", "quemar": "Quemar", "ignorar": "Ignorar"}
    rectangulos = rectangulos_pociones(recursos)
    for clave, rect in rectangulos.items():
        imagen = recursos["pociones"][clave].copy()
        superficie.blit(imagen, rect)
        contador = recursos["fuente_categoria"].render("∞", True, CREMA)
        superficie.blit(contador, contador.get_rect(bottomright=(rect.right + 3, rect.bottom + 3)))
        if rect.collidepoint(mouse_pos):
            aviso = recursos["fuente_categoria"].render(
                f"Poción de {nombres[clave]}: se activa al tomar esa decisión", True, CREMA
            )
            fondo = superficie_con_alpha((aviso.get_width() + 16, 26), (14, 31, 23, 225))
            posicion = (ANCHO - fondo.get_width() - 14, 122)
            superficie.blit(fondo, posicion)
            superficie.blit(aviso, (posicion[0] + 8, posicion[1] + 5))
    if animacion:
        # El efecto se dibuja dentro de dibujar_tablilla_en_efecto. Aquí se
        # evita mostrar la mini-tablilla de la hoja de sprites como adorno.
        pass
    return rectangulos


def determinar_resultado_final(estado):
    positivos = sum(estado.indicadores[nombre] for nombre in ("sabiduria", "confianza_consejo", "armonia")) / 3
    negativo = estado.indicadores["susurros_falsos"] + estado.indicadores["desinformación"]
    return "victoria" if positivos >= 55 and negativo < 100 else "game_over"


def dibujar_final(superficie, recursos, estado):
    victoria = determinar_resultado_final(estado) == "victoria"
    ilustracion = recursos["final_positivo"] if victoria else recursos["final_negativo"]
    superficie.blit(ilustracion, (0, 0))
    titulo = recursos["fuente_resultado"].render("LA COPA FLORECE" if victoria else "LA COPA SE CUBRE DE HUMO", True, CREMA)
    superficie.blit(titulo, titulo.get_rect(center=(ANCHO // 2, 88)))
    detalle = recursos["fuente_texto"].render(
        "Mira será la nueva Cacique" if victoria else "El Consejo deberá recomponer la confianza", True, CREMA
    )
    superficie.blit(detalle, detalle.get_rect(center=(ANCHO // 2, 124)))
    resumen_panel = pygame.Rect(300, 496, 360, 132)
    superficie.blit(superficie_con_alpha(resumen_panel.size, (10, 24, 17, 220)), resumen_panel.topleft)
    pygame.draw.rect(superficie, ORO, resumen_panel, width=2, border_radius=10)
    resumen = [
        f"Sabiduría: {estado.indicadores['sabiduria']}",
        f"Confianza: {estado.indicadores['confianza_consejo']}",
        f"Armonía: {estado.indicadores['armonia']}",
        f"Desinformación: {estado.indicadores['desinformación']}",
    ]
    for indice, linea in enumerate(resumen):
        texto = recursos["fuente_panel"].render(linea, True, CREMA)
        superficie.blit(texto, texto.get_rect(center=(ANCHO // 2, 510 + indice * 24)))
    instruccion = recursos["fuente_boton"].render("R: reiniciar    ESC: salir", True, ORO)
    superficie.blit(instruccion, instruccion.get_rect(center=(ANCHO // 2, 655)))



def crear_fondo_tablilla(recursos, dia):
    dia = max(0, min(int(dia), len(recursos["mapas_dia"]) - 1))
    fondo = recursos["mapas_dia"][dia].copy()
    dibujar_decoraciones_editor(fondo, recursos, animar=False)
    mundo = recursos.get("mundo")
    if mundo:
        dibujar_troncos_eco(fondo, recursos, mundo, animar=False)
    velo = superficie_con_alpha((ANCHO, ALTO), (7, 18, 14, 178))
    fondo.blit(velo, (0, 0))
    return fondo


def fondo_tablilla_actual(recursos, estado):
    dia = max(0, min(int(getattr(estado, "dia", recursos.get("dia", 0))), len(recursos["mapas_dia"]) - 1))
    cache = recursos.setdefault("fondos_tablilla_por_dia", {})
    if dia not in cache:
        cache[dia] = crear_fondo_tablilla(recursos, dia)
    return cache[dia]
