"""Carga de mapas (La Copa, Distrito Conecta, interiores) y adaptación de hitboxes al lienzo."""

import re
import json
import os
import pygame
from logica.dimensiones import DIMENSION_PRESENTE
from logica.dimensiones import EDIFICIOS_PRESENTE
from nucleo.rutas import RAIZ
from mundo.personajes import (
    _cargar_decoraciones_presentes,
    _cargar_frames_idle_personaje,
    _direccion_desde_nombre_sprite,
    cargar_personaje_periodista,
    personaje_de_decoracion,
)
from nucleo.config import ALTO, ANCHO, DISTANCIA_INTERACCION
from nucleo.recursos import (
    buscar_asset,
    cargar_imagen,
    cargar_spritesheet_frames,
    es_hoja_portales,
    normalizar_ruta,
    recortar_portal_final,
)


# Lugar de Mapaunificado.png en el mundo 960x720 (x, y, ancho, alto), hallado
# comparándolo con Pr_MañanaLumi.png: así hitboxes y objetos no cambian de sitio.
REGISTRO_MAPA_UNIFICADO = (38, 0, 881, 719)
BORDE_FUSION_MAPA = 36


def cargar_fondo_unificado(zoom):
    """Fondo de La Copa a ``zoom`` veces el mundo. Mapaunificado no llega a las
    franjas laterales: ahí sigue el mapa anterior, fundido con degradado."""
    base = cargar_imagen(
        os.path.join("Fondos", "Mapas", "Pr_MañanaLumi.png"),
        (ANCHO * zoom, ALTO * zoom),
    ).convert()
    x, y, ancho, alto = (valor * zoom for valor in REGISTRO_MAPA_UNIFICADO)
    unificado = cargar_imagen(os.path.join("Fondos", "Mapas", "Mapaunificado.png"), (ancho, alto))
    borde = BORDE_FUSION_MAPA * zoom
    for indice in range(borde):
        alfa = round(255 * (indice + 1) / borde)
        for columna in (indice, ancho - 1 - indice):
            unificado.fill((255, 255, 255, alfa), (columna, 0, 1, alto), special_flags=pygame.BLEND_RGBA_MULT)
    base.blit(unificado, (x, y))
    return base


def cargar_fondo_presente(configuracion, rect_mapa, zoom):
    """Mapa de Distrito Conecta a ``zoom`` veces, escalado una vez desde el original."""
    imagen = pygame.image.load(buscar_asset(configuracion["mapa"])).convert()
    return pygame.transform.scale(imagen, (rect_mapa[2] * zoom, rect_mapa[3] * zoom))


def npcs_presente_ampliados(decoraciones, zoom, origen):
    """NPC de Distrito Conecta a ``zoom`` veces, en coordenadas de la capa ampliada."""
    from mundo.personajes import _cargar_sprite_direccional as cargar_idle, preparar_hablando, preparar_reposo
    ampliados = []
    for objeto in decoraciones:
        r = objeto["rect"]
        rect = pygame.Rect((r.x - origen[0]) * zoom, (r.y - origen[1]) * zoom, r.width * zoom, r.height * zoom)
        idle = cargar_idle(objeto["nombre"], rect.size)
        ampliados.append(dict(objeto, rect=rect, hitbox=rect,
                              imagen=idle.get(objeto["direccion"]) or idle.get("abajo") or objeto["imagen"]))
        preparar_reposo(ampliados[-1])
        preparar_hablando(ampliados[-1])
    return ampliados


def suavizar_cascada(objeto, margen=36):
    """La cascada se dibuja completa sobre el mapa para que se vea correr el
    agua; solo se desvanece junto al borde del cuadro, para que no se vea un
    corte recto. Modifica ``objeto`` (una vez, al cargar)."""
    limpios = []
    for cuadro in objeto["origenes"]:
        contorno = cuadro.copy()
        contorno.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
        # El agua llega hasta el borde del cuadro: ahí se desvanece poco a poco.
        ancho, alto = contorno.get_size()
        for indice in range(margen):
            alfa = round(255 * (indice + 1) / (margen + 1))
            for franja in ((0, indice, ancho, 1), (0, alto - 1 - indice, ancho, 1),
                           (indice, 0, 1, alto), (ancho - 1 - indice, 0, 1, alto)):
                contorno.fill((255, 255, 255, alfa), franja, special_flags=pygame.BLEND_RGBA_MULT)
        limpio = cuadro.copy()
        limpio.blit(contorno, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        limpios.append(limpio)
    objeto["origenes"] = limpios
    objeto["frames"] = [pygame.transform.scale(limpio, objeto["rect"].size) for limpio in limpios]
    objeto["imagen"] = objeto["frames"][0]


def decoraciones_ampliadas(decoraciones, zoom):
    """Copias de las decoraciones a ``zoom`` veces, escaladas desde su imagen original."""
    ampliadas = []
    for objeto in decoraciones:
        r = objeto["rect"]
        rect = pygame.Rect(r.x * zoom, r.y * zoom, r.width * zoom, r.height * zoom)
        frames = [pygame.transform.scale(origen, rect.size) for origen in objeto["origenes"]]
        ampliadas.append(dict(
            objeto, original=objeto, rect=rect, hitbox=rect, imagen=frames[0],
            frames=frames if objeto["frames"] else [],
        ))
    return ampliadas


def cargar_mapa_principal():
    """Carga el mapa usando en todos los momentos las hitboxes del fondo de mañana."""
    ruta_hitboxes = os.path.join(
        str(RAIZ),
        "Hitboxes",
        "Mapas",
        "Pr_MañanaLumi_hitboxes.json",
    )
    with open(ruta_hitboxes, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)

    fondos_por_dia = (
        os.path.join("Fondos", "Mapas", "Pr_MañanaLumi.png"),
        os.path.join("Fondos", "Mapas", "Pr_Atardecer.png"),
        os.path.join("Fondos", "Mapas", "Pr_Noche.png"),
    )
    mapas_dia = [
        cargar_imagen(nombre, (ANCHO, ALTO))
        for nombre in fondos_por_dia
    ]
    decoraciones = []
    for objeto in datos.get("decoracion", []):
        nombre_normalizado = normalizar_ruta(objeto["name"])
        imagen_original = recortar_portal_final(
            cargar_imagen(objeto["name"]),
            objeto["name"],
        )
        recorte = objeto.get("crop")
        rect = pygame.Rect(
            round(objeto["x"] * ANCHO),
            round(objeto["y"] * ALTO),
            max(1, round(objeto["w"] * ANCHO)),
            max(1, round(objeto["h"] * ALTO)),
        )
        personaje = personaje_de_decoracion(objeto["name"])
        direccion = _direccion_desde_nombre_sprite(objeto["name"])
        frames_idle = (
            _cargar_frames_idle_personaje(personaje, objeto["name"])
            if personaje
            else {}
        )
        es_fondo_animado = nombre_normalizado.endswith("cascada_animacion.png")
        es_puente = nombre_normalizado.startswith("puentes/")
        nombre_archivo = os.path.basename(nombre_normalizado)
        # En el set de arte, estos cuatro PNG son escaleras; aunque estén en
        # la carpeta Puentes, son estructuras rígidas y nunca se balancean.
        es_escalera = (
            "escalera" in nombre_normalizado
            or nombre_archivo in {"puente3.png", "puente4.png", "puente5.png", "puente8.png"}
        )
        nombre_puente = os.path.splitext(os.path.basename(objeto["name"]))[0]
        cantidad_frames = (
            1 if es_hoja_portales(objeto["name"])
            else max(1, int(objeto.get("frames", 1)))
        )
        imagenes_frames = []
        origenes = []  # cuadros sin escalar, para ampliarlos sin perder detalle
        if cantidad_frames > 1 and not es_puente:
            ancho_frame = imagen_original.get_width() // cantidad_frames
            for indice_frame in range(cantidad_frames):
                frame = imagen_original.subsurface((
                    indice_frame * ancho_frame, 0, ancho_frame, imagen_original.get_height()
                )).copy()
                if recorte:
                    x = max(0, min(frame.get_width() - 1, round(recorte["x"] * frame.get_width())))
                    y = max(0, min(frame.get_height() - 1, round(recorte["y"] * frame.get_height())))
                    ancho = max(1, min(frame.get_width() - x, round(recorte["w"] * frame.get_width())))
                    alto = max(1, min(frame.get_height() - y, round(recorte["h"] * frame.get_height())))
                    frame = frame.subsurface((x, y, ancho, alto)).copy()
                origenes.append(frame)
                imagenes_frames.append(pygame.transform.scale(frame, rect.size))
            imagen = imagenes_frames[0] if imagenes_frames else imagen_original
        else:
            imagen = imagen_original
            if recorte:
                x = max(0, min(imagen.get_width() - 1, round(recorte["x"] * imagen.get_width())))
                y = max(0, min(imagen.get_height() - 1, round(recorte["y"] * imagen.get_height())))
                ancho = max(1, min(imagen.get_width() - x, round(recorte["w"] * imagen.get_width())))
                alto = max(1, min(imagen.get_height() - y, round(recorte["h"] * imagen.get_height())))
                imagen = imagen.subsurface((x, y, ancho, alto)).copy()
            origenes.append(imagen)
            imagen = pygame.transform.scale(imagen, rect.size)

        hitbox = rect.copy()
        if personaje == "Guardián":
            hitbox.inflate_ip(-round(rect.width * 0.4), -round(rect.height * 0.4))
        decoraciones.append({
            "id": f"puente_{nombre_puente[6:].lower()}" if es_puente else None,
            "nombre": objeto["name"],
            "personaje": personaje,
            "direccion": direccion,
            "frames_idle": frames_idle,
            "rect": rect,
            "hitbox": hitbox,
            "imagen": imagen,
            "puente": es_puente,
            "fondo_animado": es_fondo_animado,
            "escalera": es_escalera,
            "puente_animable": es_puente and not es_escalera,
            "frames": imagenes_frames,
            "origenes": origenes,
            "tronco_eco": nombre_normalizado.startswith("tronco ecos/"),
            # Diseño del tronco: campo opcional "variante" o el archivo elegido en el editor.
            "variante_tronco": int(objeto.get("variante") or (re.search(r"fila([1-4])", nombre_normalizado) or (0, 1))[1]),
            # La mariposa vuela alrededor del punto del editor (dibujar_mariposa).
            "mariposa": nombre_normalizado.endswith("animales/mariposa.png"),
        })

    decoraciones.sort(
        key=lambda objeto: (
            not objeto.get("fondo_animado"),
            not objeto["puente"],
        ),
    )
    for mapa_dia in mapas_dia:
        for objeto in decoraciones:
            if (
                objeto["personaje"] != "Guardián"
                and not objeto["puente"]
                and not objeto["tronco_eco"]
                and not objeto["frames"]
                and not objeto["frames_idle"]
            ):
                mapa_dia.blit(objeto["imagen"], objeto["rect"])
    mapa = mapas_dia[0]

    interacciones = []
    hitboxes = datos.get("hitboxes", [])
    for indice, hitbox in enumerate(hitboxes):
        if hitbox.get("role") not in ("interactable", "other"):
            continue
        tipo_forma = hitbox.get("type", "rect")
        if tipo_forma == "rect":
            rect = pygame.Rect(
                round(hitbox["rx"] * ANCHO),
                round(hitbox["ry"] * ALTO),
                max(1, round(hitbox["rw"] * ANCHO)),
                max(1, round(hitbox["rh"] * ALTO)),
            )
        elif tipo_forma == "circle":
            cx = round(hitbox["cx"] * ANCHO)
            cy = round(hitbox["cy"] * ALTO)
            radio = max(1, round(hitbox["r"] * ANCHO))
            rect = pygame.Rect(cx - radio, cy - radio, radio * 2, radio * 2)
        else:
            continue
        interaccion = {
            "id": hitbox.get("id", f"interaccion_{indice + 1}"),
            "tipo": "eco_tronco" if hitbox.get("action") == "usar_eco_tronco" else hitbox.get("action", "interaccion"),
            "rect": rect,
            "accion": hitbox.get("action"),
            "personaje": hitbox.get("npc_character"),
            "destino": hitbox.get("target_image"),
            "role": hitbox.get("role"),
            "plataforma": hitbox.get("plataforma", ""),
            "activo": hitbox.get("activo", True),
            "zona_en_proceso": hitbox.get("zona_en_proceso", False),
        }
        if (
            interaccion["accion"] == "puerta"
            and interaccion["destino"]
            and not interaccion["zona_en_proceso"]
        ):
            interaccion["imagen_destino"] = cargar_imagen(interaccion["destino"], (ANCHO, ALTO))
        interacciones.append(interaccion)

    for indice, objeto in enumerate(decoraciones):
        if not objeto["tronco_eco"]:
            continue
        interacciones.append({
            "id": f"eco_tronco_decoracion_{indice + 1}",
            "tipo": "eco_tronco",
            "accion": "usar_eco_tronco",
            "rect": objeto["rect"],
            "activo": True,
            "frames": cargar_spritesheet_frames(objeto["nombre"], cantidad=4),
        })

    portal = next(
        (objeto for objeto in decoraciones if es_hoja_portales(objeto["nombre"])),
        None,
    )
    if portal:
        interaccion_portal = next(
            (
                interaccion for interaccion in interacciones
                if interaccion.get("id") == "portal_zona_en_proceso"
            ),
            None,
        )
        if interaccion_portal is None:
            interaccion_portal = {
                "id": "portal_dimension_presente",
                "rect": portal["rect"].copy(),
                "activo": False,
            }
            interacciones.append(interaccion_portal)
        interaccion_portal.update({
            "tipo": "portal_temporal",
            "accion": "portal_temporal",
            "activo": False,
            "zona_en_proceso": False,
        })

    guardian = next(
        (objeto for objeto in decoraciones if objeto["personaje"] == "Guardián"),
        None,
    )
    if guardian is None:
        print("[advertencia] No se encontró la decoración del Guardián; usando posición inicial central.")
    return mapa, decoraciones, interacciones, hitboxes, guardian, mapas_dia


def _rect_de_hitbox(hitbox):
    tipo_forma = hitbox.get("type", "rect")
    if tipo_forma == "rect":
        return pygame.Rect(
            round(hitbox.get("rx", 0) * ANCHO),
            round(hitbox.get("ry", 0) * ALTO),
            max(1, round(hitbox.get("rw", 0) * ANCHO)),
            max(1, round(hitbox.get("rh", 0) * ALTO)),
        )
    if tipo_forma == "circle":
        cx = round(hitbox.get("cx", 0) * ANCHO)
        cy = round(hitbox.get("cy", 0) * ALTO)
        radio = max(1, round(hitbox.get("r", 0) * ANCHO))
        return pygame.Rect(cx - radio, cy - radio, radio * 2, radio * 2)
    return None


def _mapear_hitbox_a_ventana(hitbox, rect_mapa):
    """Convierte coordenadas normalizadas del archivo a las del lienzo 960x720."""
    hitbox_mapeada = dict(hitbox)
    tipo_forma = hitbox.get("type", "rect")
    if tipo_forma == "rect":
        hitbox_mapeada.update({
            "rx": (rect_mapa.x + hitbox.get("rx", 0) * rect_mapa.width) / ANCHO,
            "ry": (rect_mapa.y + hitbox.get("ry", 0) * rect_mapa.height) / ALTO,
            "rw": hitbox.get("rw", 0) * rect_mapa.width / ANCHO,
            "rh": hitbox.get("rh", 0) * rect_mapa.height / ALTO,
        })
    elif tipo_forma == "circle":
        hitbox_mapeada.update({
            "cx": (rect_mapa.x + hitbox.get("cx", 0) * rect_mapa.width) / ANCHO,
            "cy": (rect_mapa.y + hitbox.get("cy", 0) * rect_mapa.height) / ALTO,
            "r": hitbox.get("r", 0) * rect_mapa.width / ANCHO,
        })
    elif tipo_forma == "line":
        for eje, dimension_mapa, origen, dimension_lienzo in (
            ("x", rect_mapa.width, rect_mapa.x, ANCHO),
            ("y", rect_mapa.height, rect_mapa.y, ALTO),
        ):
            for extremo in ("1", "2"):
                clave = f"{eje}{extremo}"
                hitbox_mapeada[clave] = (
                    origen + hitbox.get(clave, 0) * dimension_mapa
                ) / dimension_lienzo
        hitbox_mapeada["thickness"] = (
            hitbox.get("thickness", 0.008) * rect_mapa.width / ANCHO
        )
    return hitbox_mapeada


def _posicion_spawn_desde_datos(datos_spawn, rect_mapa):
    if isinstance(datos_spawn, (list, tuple)) and len(datos_spawn) == 2:
        return round(datos_spawn[0]), round(datos_spawn[1])
    if isinstance(datos_spawn, dict) and "x" in datos_spawn and "y" in datos_spawn:
        return round(datos_spawn["x"]), round(datos_spawn["y"])
    if isinstance(datos_spawn, dict) and "rx" in datos_spawn and "ry" in datos_spawn:
        centro_x = datos_spawn["rx"] + datos_spawn.get("rw", 0) / 2
        centro_y = datos_spawn["ry"] + datos_spawn.get("rh", 0) / 2
        return (
            round(rect_mapa.x + centro_x * rect_mapa.width),
            round(rect_mapa.y + centro_y * rect_mapa.height),
        )
    return None


def cargar_mapa_presente(configuracion):
    """Carga una vez el mapa presente y su JSON, sin inventar geometría."""
    ruta_mapa = buscar_asset(configuracion["mapa"])
    if not os.path.isfile(ruta_mapa):
        print(f"[Dimensiones] No se encontró MapaPresente.png: {ruta_mapa}")
        return None
    try:
        imagen_original = pygame.image.load(ruta_mapa).convert_alpha()
    except pygame.error as error:
        print(f"[Dimensiones] No se pudo cargar MapaPresente.png: {error}")
        return None

    factor = min(ANCHO / imagen_original.get_width(), ALTO / imagen_original.get_height())
    tamano = (
        max(1, round(imagen_original.get_width() * factor)),
        max(1, round(imagen_original.get_height() * factor)),
    )
    rect_mapa = pygame.Rect((0, 0), tamano)
    rect_mapa.center = (ANCHO // 2, ALTO // 2)
    mapa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    mapa.fill((18, 27, 38, 255))
    mapa.blit(pygame.transform.scale(imagen_original, tamano), rect_mapa)

    ruta_hitboxes = os.path.join(
        str(RAIZ),
        "Hitboxes",
        *configuracion["hitboxes"].split("/"),
    )
    try:
        with open(ruta_hitboxes, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except FileNotFoundError:
        print(f"[Dimensiones] No se encontró el JSON de hitboxes: {ruta_hitboxes}")
        datos = {}
    except json.JSONDecodeError as error:
        print(f"[Dimensiones] JSON de hitboxes inválido: {error}")
        datos = {}
    if not isinstance(datos, dict):
        datos = {}

    hitboxes_originales = datos.get("hitboxes", [])
    hitboxes = [
        _mapear_hitbox_a_ventana(hitbox, rect_mapa)
        for hitbox in hitboxes_originales
        if isinstance(hitbox, dict)
    ]
    interacciones = []
    posicion_spawn = None
    for indice, hitbox in enumerate(hitboxes):
        accion = hitbox.get("action", hitbox.get("accion"))
        if accion == "entrada_edificio":
            accion = "entrar_edificio"
        tipo_objeto = hitbox.get("tipo")
        if accion == "punto_spawn" or tipo_objeto == "punto_spawn":
            rect_spawn = _rect_de_hitbox(hitbox)
            if rect_spawn:
                posicion_spawn = rect_spawn.center
            continue
        if hitbox.get("role") not in ("interactable", "other"):
            continue
        rect = _rect_de_hitbox(hitbox)
        if rect is None:
            continue
        if hitbox.get("dimension", DIMENSION_PRESENTE) != DIMENSION_PRESENTE:
            continue
        interacciones.append({
            "id": hitbox.get("id", f"interaccion_presente_{indice + 1}"),
            "tipo": tipo_objeto or accion or "interaccion",
            "accion": accion or "otro",
            "edificio_id": hitbox.get("edificio_id"),
            "nombre_edificio": hitbox.get("nombre_edificio"),
            "personaje": hitbox.get("npc_character"),
            "npc_animation": hitbox.get("npc_animation"),
            "rect": rect,
            "role": hitbox.get("role"),
            "dimension": DIMENSION_PRESENTE,
            "datos": hitbox.get("datos", {}),
            "activo": hitbox.get("activo", True),
            "distancia": hitbox.get("distancia", DISTANCIA_INTERACCION),
        })

    if posicion_spawn is None and isinstance(datos, dict):
        spawn_datos = datos.get("spawn", {})
        if isinstance(spawn_datos, dict):
            candidatos_spawn = [spawn_datos.get("default")]
            by_origin = spawn_datos.get("by_origin", {})
            if isinstance(by_origin, dict):
                candidatos_spawn.extend(
                    valor for origen, valor in by_origin.items()
                    if "mapapresente.png" in normalizar_ruta(str(origen))
                )
            posicion_spawn = next(
                (
                    posicion for posicion in (
                        _posicion_spawn_desde_datos(valor, rect_mapa)
                        for valor in candidatos_spawn
                    )
                    if posicion is not None
                ),
                None,
            )
        if posicion_spawn is None:
            posicion_spawn = _posicion_spawn_desde_datos(
                datos.get("spawn_presente"),
                rect_mapa,
            )

    if posicion_spawn is None:
        posicion_spawn = tuple(configuracion["spawn"])
        print(
            "[Dimensiones] No se encontró spawn_presente; "
            "se utiliza el valor predeterminado."
        )
    if not hitboxes:
        print("[Dimensiones] El mapa presente todavía no tiene hitboxes.")
    if not any(
        objeto["tipo"] == "pantalla_publica"
        or objeto["accion"] == "examinar_publicacion"
        for objeto in interacciones
    ):
        print(
            "[Dimensiones] No hay pantalla_publica configurada; "
            "añádela desde el editor de hitboxes."
        )

    decoraciones = _cargar_decoraciones_presentes(datos, rect_mapa)
    if not any(interaccion.get("id") == "pantalla_publica_presente" for interaccion in interacciones):
        rect_publicacion = pygame.Rect(
            rect_mapa.x + round(rect_mapa.width * 0.49),
            rect_mapa.y + round(rect_mapa.height * 0.30),
            max(28, round(rect_mapa.width * 0.08)),
            max(28, round(rect_mapa.height * 0.08)),
        )
        interacciones.append({
            "id": "pantalla_publica_presente",
            "tipo": "pantalla_publica",
            "accion": "examinar_publicacion",
            "rect": rect_publicacion,
            "role": "interactable",
            "dimension": DIMENSION_PRESENTE,
            "datos": {},
            "activo": True,
            "distancia": DISTANCIA_INTERACCION,
        })

    return {
        "mapa": mapa,
        "mapas_dia": [mapa],
        "decoraciones": decoraciones,
        "interacciones": interacciones,
        "hitboxes": hitboxes,
        "guardian": None,
        "jugador_presente": cargar_personaje_periodista(),
        "spawn_dimension": posicion_spawn,
        "rect_mapa": rect_mapa,
        "grafo": datos.get("grafo", {}),
    }


def cargar_mapa_edificio(edificio_id, dimension=DIMENSION_PRESENTE):
    """Carga el interior existente y las hitboxes editables de un edificio."""
    from logica.dimensiones import EDIFICIOS_FUTURO
    edificio = (EDIFICIOS_FUTURO if dimension == "futuro" else EDIFICIOS_PRESENTE).get(edificio_id)
    if edificio is None:
        raise ValueError(f"El edificio del presente no esta configurado: {edificio_id}")

    ruta_imagen = buscar_asset(edificio["interior"])
    if dimension == "futuro" and not os.path.isfile(ruta_imagen):
        ruta_imagen = buscar_asset(EDIFICIOS_PRESENTE[edificio_id]["interior"])
    if not os.path.isfile(ruta_imagen):
        raise FileNotFoundError(
            f"No existe el interior configurado para {edificio['nombre']}: {ruta_imagen}"
        )
    imagen_original = pygame.image.load(ruta_imagen).convert_alpha()
    factor = min(ANCHO / imagen_original.get_width(), ALTO / imagen_original.get_height())
    tamano = (
        max(1, round(imagen_original.get_width() * factor)),
        max(1, round(imagen_original.get_height() * factor)),
    )
    rect_mapa = pygame.Rect((0, 0), tamano)
    rect_mapa.center = (ANCHO // 2, ALTO // 2)
    mapa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    mapa.fill((18, 27, 38, 255))
    mapa.blit(pygame.transform.scale(imagen_original, tamano), rect_mapa)

    ruta_hitboxes = os.path.join(
        str(RAIZ),
        "Hitboxes",
        *edificio["interior_hitboxes"].split("/"),
    )
    with open(ruta_hitboxes, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
    hitboxes = [
        _mapear_hitbox_a_ventana(hitbox, rect_mapa)
        for hitbox in datos.get("hitboxes", [])
        if isinstance(hitbox, dict)
    ]
    interacciones = []
    for indice, hitbox in enumerate(hitboxes):
        if hitbox.get("role") not in ("interactable", "other"):
            continue
        rect = _rect_de_hitbox(hitbox)
        if rect is None:
            continue
        interacciones.append({
            "id": hitbox.get("id", f"interior_{edificio_id}_{indice + 1}"),
            "tipo": hitbox.get("tipo", hitbox.get("action", "interaccion")),
            "accion": hitbox.get("action", "otro"),
            "edificio_id": edificio_id,
            "nombre_edificio": hitbox.get("nombre_edificio"),
            "rect": rect,
            "role": hitbox.get("role"),
            "dimension": dimension,
            "datos": hitbox.get("datos", {}),
            "activo": hitbox.get("activo", True),
            "distancia": hitbox.get("distancia", DISTANCIA_INTERACCION),
        })

    spawn = _posicion_spawn_desde_datos(datos.get("spawn", {}).get("default"), rect_mapa)
    if spawn is None:
        raise ValueError(f"No hay spawn editable configurado para {edificio['nombre']}.")
    return {
        "mapa": mapa,
        "mapas_dia": [mapa],
        "decoraciones": [],
        "interacciones": interacciones,
        "hitboxes": hitboxes,
        "guardian": None,
        "spawn_dimension": spawn,
        "rect_mapa": rect_mapa,
        "grafo": {},
        "dimension": DIMENSION_PRESENTE,
        "edificio_interior": edificio_id,
    }
