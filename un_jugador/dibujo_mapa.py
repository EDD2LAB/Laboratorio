"""Dibujo del mapa: decoraciones, jugador, troncos, propagaciones, depuración F3."""

import math
import pygame
from logica.dimensiones import DIMENSION_LA_COPA
from mundo.camara import (
    dibujar_escena_con_camara,
    posicion_mundo_a_pantalla,
    posicion_pantalla_a_mundo,
)
from mundo.grafo_aldea import _posicion_en_mapa
from nucleo.config import ALTO, ANCHO, CREMA, ORO
from nucleo.recursos import dibujar_sprite_en_rect, envolver_texto
from un_jugador.hud import (
    celular_disponible,
    dibujar_brillo_interaccion,
    dibujar_controles_hud,
    dibujar_flecha_objetivo,
    dibujar_mensaje_mapa,
    dibujar_pistas_mision,
    interaccion_en_mapa,
    objetivo_mision_actual,
    texto_tutorial_primer_evento,
)


def dibujar_capas_mundo(superficie, recursos, mundo, mapa, particulas=None):
    superficie.blit(mapa, (0, 0))
    dibujar_decoraciones_editor(superficie, recursos)
    reparacion = mundo.get("reparacion_puentes")
    if reparacion:
        reparacion.dibujar_mundo(superficie)
    dibujar_troncos_eco(superficie, recursos, mundo)
    dibujar_jugador(superficie, mundo["jugador"])
    dibujar_propagaciones_visuales(superficie, mundo)
    if particulas:
        particulas.dibujar(superficie)


def dibujar_debug_mapa(
    superficie, mundo, jugador, interactuable, distancia, particulas, estado_control,
    propagaciones=None,
):
    for hitbox in mundo["hitboxes"]:
        if hitbox.get("role") == "walkable":
            if hitbox.get("type", "rect") == "rect":
                rect = pygame.Rect(
                    round(hitbox.get("rx", 0) * ANCHO),
                    round(hitbox.get("ry", 0) * ALTO),
                    max(1, round(hitbox.get("rw", 0) * ANCHO)),
                    max(1, round(hitbox.get("rh", 0) * ALTO)),
                )
                pygame.draw.rect(superficie, (100, 220, 140), rect, 1)
            elif hitbox.get("type") == "circle":
                centro = (round(hitbox["cx"] * ANCHO), round(hitbox["cy"] * ALTO))
                pygame.draw.circle(superficie, (100, 220, 140), centro, round(hitbox["r"] * ANCHO), 1)
            continue
        if hitbox.get("role") != "wall":
            continue
        if hitbox.get("type", "rect") == "rect":
            rect = pygame.Rect(
                round(hitbox.get("rx", 0) * ANCHO),
                round(hitbox.get("ry", 0) * ALTO),
                max(1, round(hitbox.get("rw", 0) * ANCHO)),
                max(1, round(hitbox.get("rh", 0) * ALTO)),
            )
            pygame.draw.rect(superficie, (60, 140, 255), rect, 1)
        elif hitbox.get("type") == "line":
            pygame.draw.line(
                superficie, (60, 140, 255),
                (round(hitbox["x1"] * ANCHO), round(hitbox["y1"] * ALTO)),
                (round(hitbox["x2"] * ANCHO), round(hitbox["y2"] * ALTO)),
                max(1, round(hitbox.get("thickness", 0.008) * ANCHO)),
            )
        elif hitbox.get("type") == "circle":
            pygame.draw.circle(
                superficie,
                (60, 140, 255),
                (round(hitbox["cx"] * ANCHO), round(hitbox["cy"] * ALTO)),
                max(1, round(hitbox["r"] * ANCHO)),
                1,
            )
    if mundo.get("spawn_presente"):
        pygame.draw.circle(
            superficie,
            (255, 190, 75),
            mundo["spawn_presente"],
            10,
            2,
        )
    pygame.draw.rect(superficie, (255, 230, 40), jugador["pies"], 1)
    for personaje in mundo["personajes"]:
        pygame.draw.rect(superficie, (200, 130, 255), personaje["rect"], 1)
    for objeto in mundo["decoraciones"]:
        ruta = objeto.get("ruta_npc")
        if not ruta:
            continue
        puntos = ruta["points"]
        pygame.draw.lines(
            superficie,
            (255, 110, 110),
            ruta["pattern"] == "loop",
            puntos,
            1,
        )
        for indice, punto in enumerate(puntos):
            pygame.draw.circle(superficie, (255, 210, 80), punto, 3)
            etiqueta = pygame.font.Font(None, 12).render(
                str(indice + 1),
                True,
                (255, 255, 255),
            )
            superficie.blit(etiqueta, (punto[0] + 4, punto[1] - 4))
    for objeto in mundo["interacciones"]:
        color = (
            (200, 130, 255) if objeto.get("role") == "other"
            else (75, 230, 220) if objeto.get("tipo") == "pantalla_publica"
            else (40, 240, 200) if objeto.get("tipo") == "eco_tronco"
            else (90, 220, 120)
        )
        pygame.draw.rect(superficie, color, objeto["rect"], 2)
        etiqueta = objeto.get("id", objeto.get("accion", "interaccion"))
        superficie.blit(pygame.font.Font(None, 12).render(etiqueta, True, color), objeto["rect"].topleft)
    fuente_debug = pygame.font.Font(None, 18)
    nombre = interactuable.get("id", interactuable.get("personaje", "?")) if interactuable else "ninguno"
    cantidad_luciernagas = len(particulas.luciernagas) if particulas else 0
    cantidad_particulas = len(particulas.particulas) if particulas else 0
    detalle = (
        f"F3 | {mundo.get('dimension', DIMENSION_LA_COPA)} | "
        f"{mundo.get('escena_actual', '?')} | {estado_control} | "
        f"{mundo.get('mision', 'tablillas')} | {nombre} | {distancia:.0f}px | "
        f"luciernagas: {cantidad_luciernagas} | particulas: {cantidad_particulas}"
    )
    superficie.blit(fuente_debug.render(detalle, True, (255, 255, 255)), (8, 8))
    rect_mapa = mundo.get("rect_mapa")
    camara = mundo.get("camara")
    if rect_mapa:
        pygame.draw.rect(superficie, (255, 190, 75), rect_mapa, 1)
    if camara:
        ancho_vista = round(ANCHO / camara["zoom"])
        alto_vista = round(ALTO / camara["zoom"])
        rect_vista = pygame.Rect(
            round(camara["x"]),
            round(camara["y"]),
            ancho_vista,
            alto_vista,
        )
        pygame.draw.rect(superficie, (80, 235, 255), rect_vista, 1)
        medida_mapa = (
            f"{rect_mapa.width}x{rect_mapa.height}"
            if rect_mapa
            else f"{ANCHO}x{ALTO}"
        )
        detalle_camara = (
            f"cam=({camara['x']:.1f},{camara['y']:.1f}) "
            f"vista={ancho_vista}x{alto_vista} "
            f"mapa={medida_mapa} zoom={camara['zoom']:.2f}"
        )
        superficie.blit(
            fuente_debug.render(detalle_camara, True, (155, 235, 255)),
            (8, 25),
        )
    dibujar_debug_grafo(superficie, mundo["grafo_fisico"], mundo["decoraciones"])
    fuente_historial = pygame.font.Font(None, 15)
    y_historial = 45 if camara else 28
    for propagacion in (propagaciones or [])[-3:]:
        tramos = " | ".join(
            f"{tramo['transmisor']} -> {tramo['receptor']} "
            f"[{' > '.join(tramo['ruta']) or 'sin puente'}] ({tramo['medio']})"
            for tramo in propagacion.transmisiones
        ) or "sin transmisiones"
        lineas = [
            f"{propagacion.id} | origen: {propagacion.origen} | tipo: {propagacion.tipo} | "
            f"verificacion: {propagacion.estado_verificacion} | alcance: {propagacion.obtener_alcance()}",
            *envolver_texto(f"Tramos: {tramos}", fuente_historial, ANCHO - 28),
            f"Transmisores: {' -> '.join(propagacion.transmisores) or 'ninguno'}",
            f"Receptores: {', '.join(propagacion.destinatarios) or 'ninguno'}",
        ]
        for linea in lineas:
            y = y_historial
            panel = pygame.Surface((ANCHO - 16, 17), pygame.SRCALPHA)
            panel.fill((10, 24, 19, 205))
            superficie.blit(panel, (8, y))
            superficie.blit(fuente_historial.render(linea, True, (255, 244, 194)), (12, y + 1))
            y_historial += 18
        y_historial += 4
    activas = mundo["propagaciones_visuales"]
    superficie.blit(
        fuente_debug.render(f"Propagaciones activas: {len(activas)}", True, (255, 224, 128)),
        (8, y_historial),
    )
    for indice, propagacion in enumerate(activas[:3]):
        if not propagacion.activa:
            continue
        tramo = min(propagacion.indice_actual, len(propagacion.ruta) - 2)
        nodo_actual = propagacion.ruta[tramo]
        linea = (
            f"{propagacion.origen}->{propagacion.destino} "
            f"ruta:{' > '.join(propagacion.ruta)} nodo:{nodo_actual} "
            f"pos:({propagacion.posicion.x:.0f},{propagacion.posicion.y:.0f}) "
            f"avance:{propagacion.progreso:.2f}"
        )
        superficie.blit(
            fuente_debug.render(linea, True, (255, 244, 194)),
            (8, y_historial + 18 * (indice + 1)),
        )


def dibujar_debug_grafo(superficie, grafo, decoraciones):
    """Dibuja conexiones e ids del grafo solo cuando F3 esta activo."""
    fuente = pygame.font.Font(None, 13)
    decoraciones_por_id = {
        objeto.get("id"): objeto
        for objeto in decoraciones
        if objeto.get("puente")
    }
    for puente in grafo.puentes.values():
        origen = grafo.plataformas[puente["origen"]]
        destino = grafo.plataformas[puente["destino"]]
        pygame.draw.line(
            superficie,
            (80, 235, 255),
            _posicion_en_mapa(origen),
            _posicion_en_mapa(destino),
            1,
        )
        decoracion = decoraciones_por_id.get(puente["id"])
        if decoracion:
            etiqueta = fuente.render(puente["id"], True, (255, 245, 150))
            etiqueta_rect = etiqueta.get_rect(center=decoracion["rect"].center)
            pygame.draw.rect(
                superficie, (12, 28, 35), etiqueta_rect.inflate(4, 2), border_radius=2
            )
            superficie.blit(etiqueta, etiqueta_rect)

    for plataforma in grafo.plataformas.values():
        centro = _posicion_en_mapa(plataforma)
        pygame.draw.circle(superficie, (255, 235, 90), centro, 5)
        pygame.draw.circle(superficie, (22, 35, 24), centro, 3)
        etiqueta = fuente.render(plataforma["id"], True, (255, 255, 255))
        etiqueta_rect = etiqueta.get_rect(midtop=(centro[0], centro[1] + 6))
        etiqueta_rect.clamp_ip(superficie.get_rect())
        pygame.draw.rect(
            superficie, (12, 28, 22), etiqueta_rect.inflate(4, 2), border_radius=2
        )
        superficie.blit(etiqueta, etiqueta_rect)


def dibujar_puente_balanceandose(superficie, objeto, tiempo):
    """Da vida a los puentes sin mover sus hitboxes ni alterar el grafo."""
    rect_base = objeto["rect"]
    # Cada puente empieza en una fase distinta para que no se balanceen como
    # un bloque rígido. La curva sinusoidal evita cambios bruscos de dirección.
    fase = sum(ord(caracter) for caracter in objeto.get("id") or objeto["nombre"]) * .071
    oscilacion = math.sin(tiempo / 1050 + fase)
    amplitud_x = min(13, max(5, round(rect_base.width * .028)))
    desplazamiento_x = round(oscilacion * amplitud_x)
    inclinacion = oscilacion * 1.35
    imagen = pygame.transform.rotate(objeto["imagen"], inclinacion)
    rect_visual = imagen.get_rect(center=(rect_base.centerx + desplazamiento_x, rect_base.centery))
    superficie.blit(imagen, rect_visual)


def dibujar_decoraciones_editor(superficie, recursos, animar=True):
    """Dibuja puentes y animaciones que fueron colocados desde el editor."""
    tiempo = pygame.time.get_ticks() if animar else 0
    for objeto in recursos["decoraciones"]:
        if (
            objeto.get("personaje") == "Guardián"
            or objeto.get("tronco_eco")
        ):
            continue
        if objeto.get("frames_idle"):
            frames_caminar = objeto.get("frames_caminar", {}).get(
                objeto.get("direccion", "abajo"),
                [],
            )
            if objeto.get("estado_ruta") == "WALKING" and frames_caminar:
                imagen = frames_caminar[
                    objeto.get("indice_frame", 0) % len(frames_caminar)
                ]
                superficie.blit(
                    imagen,
                    imagen.get_rect(midbottom=objeto["rect"].midbottom),
                )
                continue
            frames = objeto["frames_idle"].get(
                objeto.get("direccion", "abajo"),
                objeto["frames_idle"].get("abajo", []),
            )
            if not isinstance(frames, (list, tuple)):
                frames = [frames]
            imagen_idle = (
                frames[(pygame.time.get_ticks() // 180) % len(frames)]
                if frames and animar
                else frames[0] if frames else None
            )
            if imagen_idle:
                if objeto.get("sprite_preparado"):
                    superficie.blit(
                        imagen_idle,
                        imagen_idle.get_rect(midbottom=objeto["rect"].midbottom),
                    )
                else:
                    dibujar_sprite_en_rect(
                        superficie,
                        imagen_idle,
                        objeto["rect"],
                    )
            continue
        if objeto.get("puente_animable"):
            dibujar_puente_balanceandose(superficie, objeto, tiempo)
        elif objeto.get("puente"):
            superficie.blit(objeto["imagen"], objeto["rect"])
        elif objeto.get("frames") and not objeto.get("tronco_eco"):
            frames = objeto["frames"]
            frame = frames[(tiempo // 140) % len(frames)] if animar else frames[0]
            superficie.blit(frame, objeto["rect"])


def dibujar_jugador(superficie, jugador):
    frames_caminar = jugador["frames_caminar"].get(
        jugador.get("direccion_movimiento", jugador["direccion"]), []
    )
    if jugador["estado_visual"] == "usar_eco" and jugador["frames_eco"]:
        imagen = jugador["frames_eco"][jugador["indice_frame"] % len(jugador["frames_eco"])]
    elif jugador["estado_visual"] == "hablar" and jugador["frames_hablar"]:
        imagen = jugador["frames_hablar"][jugador["indice_frame"] % len(jugador["frames_hablar"])]
    elif jugador["en_movimiento"] and frames_caminar:
        imagen = frames_caminar[jugador["indice_frame"] % len(frames_caminar)]
    else:
        imagen = jugador["frames_idle"].get(
            jugador["direccion"],
            jugador["frames_idle"].get("abajo", jugador["imagen_idle"]),
        )
        if isinstance(imagen, (list, tuple)):
            imagen = (
                imagen[(pygame.time.get_ticks() // 180) % len(imagen)]
                if imagen
                else jugador["imagen_idle"]
            )
    if imagen:
        if (
            jugador["direccion"] in ("izquierda", "arriba_izquierda", "abajo_izquierda")
            and jugador["estado_visual"] in ("hablar", "usar_eco")
        ):
            imagen = pygame.transform.flip(imagen, True, False)
        dibujar_sprite_en_rect(superficie, imagen, jugador["rect"])
    else:
        pygame.draw.ellipse(superficie, (45, 93, 103), jugador["rect"])
        pygame.draw.ellipse(superficie, (196, 239, 226), jugador["rect"], 2)


def dibujar_troncos_eco(superficie, recursos, mundo, animar=True):
    for interaccion in mundo["interacciones"]:
        if interaccion.get("accion") != "usar_eco_tronco" or not interaccion.get("activo", True):
            continue
        frames = interaccion.get("frames") or recursos.get("frames_tronco_eco", [])
        if not frames:
            continue
        frame = frames[(pygame.time.get_ticks() // 140) % len(frames)] if animar else frames[0]
        rect = interaccion["rect"]
        tamano = rect.size if interaccion.get("frames") else (58, 64)
        imagen = pygame.transform.scale(frame, tamano)
        superficie.blit(imagen, imagen.get_rect(midbottom=rect.midbottom))


def posicion_visual_en_puente(propagacion, puente, grafo):
    indice = propagacion.indice_actual
    origen = grafo.plataformas[propagacion.ruta[indice]]["posicion"]
    destino = grafo.plataformas[propagacion.ruta[indice + 1]]["posicion"]
    dx = destino[0] - origen[0]
    dy = destino[1] - origen[1]
    longitud = math.hypot(dx, dy)
    if longitud == 0:
        return puente["rect"].center, 0.0

    direccion_x = dx / longitud
    direccion_y = dy / longitud
    semilongitudes = []
    if direccion_x:
        semilongitudes.append(puente["rect"].width / (2 * abs(direccion_x)))
    if direccion_y:
        semilongitudes.append(puente["rect"].height / (2 * abs(direccion_y)))
    semilongitud = min(semilongitudes) * 0.85
    avance = (propagacion.progreso * 2 - 1) * semilongitud
    centro = puente["rect"].center
    posicion = (
        round(centro[0] + direccion_x * avance),
        round(centro[1] + direccion_y * avance),
    )
    angulo = -math.degrees(math.atan2(direccion_y, direccion_x))
    return posicion, angulo


def dibujar_propagaciones_visuales(superficie, mundo):
    puente_por_id = {
        objeto.get("id"): objeto
        for objeto in mundo["decoraciones"]
        if objeto.get("puente") and objeto.get("id")
    }
    grafo = mundo["grafo_fisico"]
    for propagacion in mundo["propagaciones_visuales"]:
        if not propagacion.activa:
            continue
        puente = puente_por_id.get(propagacion.puente_actual)
        frame = propagacion.obtener_frame()
        if puente and frame:
            posicion, angulo = posicion_visual_en_puente(
                propagacion,
                puente,
                grafo,
            )
            imagen = pygame.transform.smoothscale(frame, (72, 72))
            imagen = pygame.transform.rotate(imagen, angulo)
            superficie.blit(imagen, imagen.get_rect(center=posicion))


def dibujar_habilidad_jugador(superficie, recursos, mundo, estado):
    habilidad = mundo.get("habilidad")
    if habilidad is None:
        return

    iconos = recursos.get("iconos_habilidad", {})
    imagen = iconos.get(habilidad.personaje)
    if imagen is None:
        return

    panel = pygame.Rect(10, ALTO - 84, 185, 68)
    pygame.draw.rect(superficie, (18, 31, 25), panel, border_radius=8)
    pygame.draw.rect(superficie, ORO, panel, 1, border_radius=8)
    superficie.blit(imagen, (panel.x + 8, panel.y + 12))

    fuente = recursos["fuente_categoria"]
    titulo = fuente.render(habilidad.configuracion["nombre"], True, CREMA)
    superficie.blit(titulo, (panel.x + 58, panel.y + 12))
    if habilidad.personaje == "guardian":
        if habilidad.tiempo_activo_ms > 0:
            estado_habilidad = "Impulso activo"
        elif habilidad.disponible:
            estado_habilidad = "Q: usar"
        else:
            estado_habilidad = f"Recarga {habilidad.recarga_restante_ms / 1000:.1f}s"
    elif estado.mision_presente.get("correccion_difundida"):
        estado_habilidad = "Corrección difundida"
    elif estado.mision_presente.get("decision") in ("verificar", "clasificar_ia"):
        estado_habilidad = "Q: difundir corrección"
    else:
        estado_habilidad = "Requiere verificación"
    detalle = fuente.render(estado_habilidad, True, (143, 225, 210))
    superficie.blit(detalle, (panel.x + 58, panel.y + 38))


def dibujar_mapa(
    superficie, recursos, mundo, estado, mouse_pos, hud,
    interactuable=None, distancia=None, particulas=None, debug=False, resaltar=True,
):
    mapas = recursos["mapas_dia"]
    indice_mapa = min(max(estado.dia, 0), len(mapas) - 1)
    camara = mundo.get("camara")
    escena = (
        pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        if camara
        else superficie
    )
    if camara:
        escena.fill((18, 27, 38, 255))
    dibujar_capas_mundo(
        escena,
        recursos,
        mundo,
        mapas[indice_mapa],
        particulas,
    )
    reparacion = mundo.get("reparacion_puentes")
    jugador = mundo["jugador"]
    if debug:
        dibujar_debug_mapa(
            escena, mundo, jugador, interactuable, distancia or 0,
            particulas, "EXPLORANDO", estado.propagaciones_informacion,
        )

    posicion_mouse_mundo = posicion_pantalla_a_mundo(mouse_pos, mundo)
    interaccion = interaccion_en_mapa(posicion_mouse_mundo, mundo) if resaltar else None
    if interaccion:
        cache = recursos.setdefault("brillos_interaccion", {})
        objeto = interaccion.get("objeto")
        if objeto:
            dibujar_brillo_interaccion(escena, objeto["imagen"], objeto["rect"], cache)
        else:
            rect = interaccion["rect"]
            luz = pygame.Surface(rect.size, pygame.SRCALPHA)
            for margen, alpha in ((0, 12), (4, 18), (8, 24)):
                zona = luz.get_rect().inflate(-margen * 2, -margen * 2)
                if zona.width > 0 and zona.height > 0:
                    pygame.draw.ellipse(luz, (*ORO, alpha), zona)
            escena.blit(luz, rect)
        if interaccion["accion"] == "npc":
            texto = f"Clic para hablar con {interaccion['personaje']}"
        elif interaccion["accion"] == "tablilla":
            texto = "Clic en el Caldero para abrir la tablilla"
        elif interaccion["accion"] == "otro":
            texto = "Objeto interactuable"
        elif interaccion["accion"] == "puerta":
            texto = (
                "Clic para viajar a otra zona"
                if interaccion.get("zona_en_proceso")
                else "Clic para viajar al mapa Central"
            )
        elif interaccion["accion"] == "portal_temporal":
            texto = "Camina hasta el portal y pulsa E para ir al presente"
        elif interaccion["accion"] == "entrar_edificio":
            texto = f"Clic para entrar a {interaccion.get('nombre_edificio', 'edificio')}"
        elif interaccion["accion"] == "salir_edificio":
            texto = "Clic para volver a la calle"
        else:
            texto = "Objeto interactuable"
    if camara:
        dibujar_escena_con_camara(superficie, escena, mundo)
    objetivo = objetivo_mision_actual(
        estado,
        mundo,
        recursos.get("conversaciones_vistas", set()),
        recursos.get("mision_objetivo_seleccionada", "principal"),
    )
    if objetivo:
        dibujar_flecha_objetivo(
            superficie,
            mundo,
            objetivo,
            recursos["fuente_mapa"],
        )
    dibujar_pistas_mision(superficie, recursos, estado)
    if celular_disponible(estado):
        etiqueta_celular = recursos["fuente_categoria"].render(
            "C: celular",
            True,
            CREMA,
        )
        panel_celular = etiqueta_celular.get_rect(topright=(ANCHO - 14, 14)).inflate(18, 12)
        pygame.draw.rect(superficie, (18, 31, 25), panel_celular, border_radius=6)
        pygame.draw.rect(superficie, ORO, panel_celular, 1, border_radius=6)
        superficie.blit(etiqueta_celular, etiqueta_celular.get_rect(center=panel_celular.center))
    if interaccion is None:
        texto = "WASD/flechas: moverse | E: interactuar | J: misiones"
        if celular_disponible(estado):
            texto += " | C: celular"
    texto_tutorial = texto_tutorial_primer_evento(
        estado,
        mundo,
        recursos.get("conversaciones_vistas", set()),
    )
    if texto_tutorial:
        texto = texto_tutorial
    hud.dibujar(superficie)
    dibujar_controles_hud(
        superficie,
        recursos["fuente_categoria"],
        hud,
        estado,
    )
    dibujar_habilidad_jugador(superficie, recursos, mundo, estado)
    if reparacion:
        reparacion.dibujar_interfaz(
            superficie,
            recursos["fuente_categoria"],
            recursos["fuente_panel_titulo"],
        )
    dibujar_mensaje_mapa(superficie, recursos["fuente_mapa"], texto)
    if interactuable:
        nombres = {
            "npc": f"Hablar con {interactuable.get('personaje', 'personaje')}",
            "tablilla": "Examinar el Caldero",
            "usar_eco_tronco": "Usar Eco de Troncos",
            "puerta": "Viajar",
            "entrar_edificio": f"Entrar a {interactuable.get('nombre_edificio', 'edificio')}",
            "salir_edificio": "Volver a la calle",
            "otro": "Interactuar",
            "examinar_publicacion": "Examinar publicación",
            "terminal_verificacion": "Usar terminal",
            "publicacion_digital": "Examinar publicación",
            "portal_temporal": "Atravesar portal",
            "punto_spawn": "Punto de aparición",
        }
        if interactuable.get("tipo") == "pantalla_publica":
            nombres["examinar_publicacion"] = "Examinar publicación"
        etiqueta = f"[E] {nombres.get(interactuable.get('accion'), 'Interactuar')}"
        if interactuable.get("alternativas_cercanas", 0) > 1:
            etiqueta = (
                f"[Tab] cambiar ({interactuable['indice_alternativa']}/"
                f"{interactuable['alternativas_cercanas']}) | {etiqueta}"
            )
        indicador = recursos["fuente_mapa"].render(etiqueta, True, CREMA)
        posicion_jugador = posicion_mundo_a_pantalla(
            jugador["rect"].center, mundo
        )
        caja = indicador.get_rect(
            midbottom=(posicion_jugador[0], posicion_jugador[1] - 5)
        ).inflate(14, 8)
        pygame.draw.rect(superficie, (18, 31, 25), caja, border_radius=5)
        pygame.draw.rect(superficie, ORO, caja, 1, border_radius=5)
        superficie.blit(indicador, indicador.get_rect(center=caja.center))
    if recursos.get("mensaje_dimension") and not interactuable:
        dibujar_mensaje_mapa(
            superficie,
            recursos["fuente_mapa"],
            recursos["mensaje_dimension"],
        )


def _mapa_actual_recursos(recursos):
    mapas = recursos["mapas_dia"]
    indice = min(max(recursos.get("dia", 0), 0), len(mapas) - 1)
    return mapas[indice]


def dibujar_fondo_mundo(superficie, recursos, mundo, particulas=None):
    camara = mundo.get("camara")
    escena = (
        pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        if camara
        else superficie
    )
    if camara:
        escena.fill((18, 27, 38, 255))
    dibujar_capas_mundo(
        escena,
        recursos,
        mundo,
        _mapa_actual_recursos(recursos),
        particulas,
    )
    if camara:
        dibujar_escena_con_camara(superficie, escena, mundo)
