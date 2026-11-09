"""Sprites de personajes y NPC, decoraciones animadas del presente y jugador local."""

import re
import math
import os
import pygame
import random
from nucleo.rutas import RAIZ
from logica.dimensiones import DIMENSION_PRESENTE
from nucleo.config import (
    ALTO,
    ANCHO,
    NOMBRE_JUGADOR_PRESENTE,
    PAUSA_PATRULLA_NPC_MS,
    TAMANO_HITBOX_PIES,
    VARIACION_VELOCIDAD_NPC,
    VELOCIDAD_PATRULLA_NPC,
)
from nucleo.recursos import cargar_imagen, cargar_spritesheet_frames, normalizar_ruta


def personaje_de_decoracion(nombre):
    ruta = normalizar_ruta(nombre)
    if "guardian" in ruta:
        return "Guardián"
    if "/mensajero/" in ruta:
        return "Mensajero"
    if "habitante hombre" in ruta:
        return "Tarek"
    if "habitante mujer" in ruta:
        return "Luma"
    if "aspirante mujer" in ruta:
        return "Mira"
    if "/darek/" in ruta:
        return "Darek"
    if "/naira/" in ruta:
        return "Naira"
    if "/odran/" in ruta:
        return "Sabio de las Raíces"
    if "aspirante hombre" in ruta:
        return "Kael"
    return None


ORIENTACIONES_SPRITE = (
    "abajo",
    "abajo_derecha",
    "derecha",
    "arriba_derecha",
    "arriba",
    "arriba_izquierda",
    "izquierda",
    "abajo_izquierda",
)

TAMANO_JUGADOR = (36, 50)
ESCALA_PERSONAJE_PRESENTE = 0.6
ESCALA_NPC_PRESENTE = 0.5
TAMANO_JUGADOR_PRESENTE = (
    max(1, round(TAMANO_JUGADOR[0] * ESCALA_PERSONAJE_PRESENTE)),
    max(1, round(TAMANO_JUGADOR[1] * ESCALA_PERSONAJE_PRESENTE)),
)
DIRECCION_A_FILA_REPOSO = {
    "abajo": 1,
    "abajo_derecha": 1,
    "derecha": 2,
    "arriba_derecha": 2,
    "arriba": 3,
    "arriba_izquierda": 3,
    "izquierda": 4,
    "abajo_izquierda": 1,
}
ARCHIVOS_REPOSO_PERSONAJES = {
    "Guardián": (
        "NPCS/Guardian/Reposo/Guardian_reposo_fila1.png",
        "NPCS/Guardian/Reposo/Guardian_reposo_fila2.png",
        "NPCS/Guardian/Reposo/Guardian_reposo_fila3.png",
        "NPCS/Guardian/Reposo/Guardian_reposo_fila4.png",
    ),
    "Mensajero": (
        "NPCS/mensajero/Reposo/Mensajero_reposo_fila1.png",
        "NPCS/mensajero/Reposo/Mensajero_reposo_fila2.png",
        "NPCS/mensajero/Reposo/Mensajero_reposo_fila3.png",
        "NPCS/mensajero/Reposo/Mensajero_reposo_fila4.png",
    ),
    "Tarek": (
        "NPCS/Habitante hombre/Reposo/Habitante_hombre_reposo_fila1.png",
        "NPCS/Habitante hombre/Reposo/Habitante_hombre_reposo_fila2.png",
        "NPCS/Habitante hombre/Reposo/Habitante_hombre_reposo_fila3.png",
        "NPCS/Habitante hombre/Reposo/Habitante_hombre_reposo_fila4.png",
    ),
    "Luma": (
        "NPCS/Habitante mujer/Reposo/Habitante_femenina-reposo_fila1.png",
        "NPCS/Habitante mujer/Reposo/Habitante_femenina-reposo_fila2.png",
        "NPCS/Habitante mujer/Reposo/Habitante_femenina-reposo_fila3.png",
        "NPCS/Habitante mujer/Reposo/Habitante_femenina-reposo_fila4.png",
    ),
    "Mira": (
        "NPCS/Aspirante mujer/Reposo/Aspirante_mujer_reposo_fila1.png",
        "NPCS/Aspirante mujer/Reposo/Aspirante_mujer_reposo _fila2.png",
        "NPCS/Aspirante mujer/Reposo/Aspirante_mujer_reposo _fila3.png",
        "NPCS/Aspirante mujer/Reposo/Aspirante_mujer_reposo_ fila4.png",
    ),
    "Kael": (
        "NPCS/Aspirante hombre/Reposo/Aspirante_a_cacique-reposo_fila1.png",
        "NPCS/Aspirante hombre/Reposo/Aspirante_a_cacique-reposo_fila2.png",
        "NPCS/Aspirante hombre/Reposo/Aspirante_a_cacique-reposo_fila3.png",
        "NPCS/Aspirante hombre/Reposo/Aspirante_a_cacique-reposo_fila4.png",
    ),
}
ARCHIVOS_DIRECCIONALES_PERSONAJES = {
    "Darek": "NPCS/Darek/Darek_fila1-{indice}.png",
    "Naira": "NPCS/Naira/Naira_fila1-{indice}.png",
    "Sabio de las Raíces": "NPCS/Odran/Odran_fila1-{indice}.png",
}


def _escalar_frames(frames, tamano):
    return [
        frame if frame.get_size() == tamano else pygame.transform.scale(frame, tamano)
        for frame in frames
    ]


def _escalar_sprite_en_caja(imagen, tamano):
    limites = imagen.get_bounding_rect(min_alpha=32)
    if not limites.width or not limites.height:
        return pygame.Surface(tamano, pygame.SRCALPHA)
    sprite = imagen.subsurface(limites)
    escala = min(tamano[0] / sprite.get_width(), tamano[1] / sprite.get_height())
    sprite_escalado = pygame.transform.scale(
        sprite,
        (
            max(1, round(sprite.get_width() * escala)),
            max(1, round(sprite.get_height() * escala)),
        ),
    )
    lienzo = pygame.Surface(tamano, pygame.SRCALPHA)
    lienzo.blit(sprite_escalado, sprite_escalado.get_rect(midbottom=(tamano[0] // 2, tamano[1])))
    return lienzo


def _cargar_sprite_direccional(nombre, tamano):
    frames = [
        _escalar_sprite_en_caja(frame, tamano)
        for frame in cargar_spritesheet_frames(nombre, 8)
    ]
    if len(frames) != len(ORIENTACIONES_SPRITE):
        return {}
    return dict(zip(ORIENTACIONES_SPRITE, frames))


def _direccion_desde_nombre_sprite(nombre):
    ruta = normalizar_ruta(os.path.basename(nombre))
    for indice, orientacion in enumerate(ORIENTACIONES_SPRITE, start=1):
        if (
            f"fila 1 - {indice}" in ruta
            or f"fila 1- {indice}" in ruta
            or f"fila1-{indice}" in ruta
        ):
            return orientacion
    return "abajo"


def _cargar_frames_idle_personaje(personaje, nombre_sprite=None):
    archivos_reposo = ARCHIVOS_REPOSO_PERSONAJES.get(personaje)
    if archivos_reposo:
        frames_por_fila = {
            fila: cargar_spritesheet_frames(archivo, 8)
            for fila, archivo in enumerate(archivos_reposo, start=1)
        }
        return {
            orientacion: frames_por_fila[DIRECCION_A_FILA_REPOSO[orientacion]]
            for orientacion in ORIENTACIONES_SPRITE
            if frames_por_fila[DIRECCION_A_FILA_REPOSO[orientacion]]
        }

    plantilla = ARCHIVOS_DIRECCIONALES_PERSONAJES.get(personaje)
    if plantilla:
        frames = {}
        for indice, orientacion in enumerate(ORIENTACIONES_SPRITE, start=1):
            imagen = cargar_imagen(
                plantilla.format(indice=indice),
                requerido=False,
            )
            if imagen is not None:
                frames[orientacion] = [imagen]
        return frames

    return {}


def cargar_personaje_periodista():
    """Carga reposo en ocho direcciones y caminata del periodista."""
    carpeta = os.path.join("NPCS", "NPC Mundo2")
    tamano = TAMANO_JUGADOR_PRESENTE
    idle = _cargar_sprite_direccional(
        os.path.join(carpeta, "NPC2-mundo2-Fila1.png"),
        tamano,
    )
    caminar = {}
    for direccion, fila in (
        ("abajo", 2),
        ("derecha", 3),
        ("arriba", 4),
        ("izquierda", 5),
    ):
        frames = cargar_spritesheet_frames(
            os.path.join(carpeta, f"NPC2-mundo2-Fila{fila}.png"),
            8,
        )
        caminar[direccion] = _escalar_frames(frames, tamano)
    if len(idle) != len(ORIENTACIONES_SPRITE) or any(
        not caminar[direccion]
        for direccion in ("abajo", "derecha", "izquierda", "arriba")
    ):
        raise RuntimeError(
            "No se pudieron cargar los sprites direccionales del periodista."
        )
    return {
        "id": "periodista",
        "nombre": NOMBRE_JUGADOR_PRESENTE,
        "tamano": tamano,
        "frames_idle": idle,
        "frames_caminar": caminar,
    }


def cargar_retrato_publicacion():
    frames = cargar_spritesheet_frames(
        os.path.join(
            "NPCS",
            "Aspirante Contempóraneo",
            "Aspirante_contemporaneo-Fila1.png",
        ),
        8,
    )
    return frames[0] if frames else None


PERSONAJES_PRESENTES = (
    {
        "clave": "Agente de verificación",
        "nombre": "Darío Veraz",
        "sprite": os.path.join(
            "NPCS",
            "Agente de verificación",
            "Agente_de_verificacion-Fila1.png",
        ),
        "sprite_caminar": os.path.join(
            "NPCS",
            "Agente de verificación",
            "Agente_de_verificacion-Fila{fila}.png",
        ),
    },
    {
        "clave": "Kael",
        "nombre": "Ronaldo Vélez",
        "escala": 0.42,
        "sprite": os.path.join(
            "NPCS",
            "Aspirante Contempóraneo",
            "Aspirante_contemporaneo-Fila1.png",
        ),
        "sprite_caminar": os.path.join(
            "NPCS",
            "Aspirante Contempóraneo",
            "Aspirante_contemporaneo-Fila{fila}.png",
        ),
    },
    {
        "clave": "Habitante Conectada",
        "nombre": "Tomás Red",
        "sprite": os.path.join(
            "NPCS",
            "Habitante Conectada",
            "Habitante_conectada-Fila1.png",
        ),
        "sprite_caminar": os.path.join(
            "NPCS",
            "Habitante Conectada",
            "Habitante_conectada-Fila{fila}.png",
        ),
    },
    {
        "clave": "Influencer",
        "nombre": "Lía Nova",
        "sprite": os.path.join("NPCS", "Influencer", "Influencer_fila1.png"),
        "sprite_caminar": os.path.join(
            "NPCS",
            "Influencer",
            "Influencer_fila{fila}.png",
        ),
    },
    {
        "clave": "Mensajero urbano",
        "nombre": "Mateo Ríos",
        "escala": 0.42,
        "sprite": os.path.join(
            "NPCS",
            "Mensajero urbano",
            "Mensajero_urbano-Fila1.png",
        ),
        "sprite_caminar": os.path.join(
            "NPCS",
            "Mensajero urbano",
            "Mensajero_urbano-Fila{fila}.png",
        ),
    },
)


# Equivalencias de CONTINUIDAD_PERSONAJES: rol -> (nombre, hoja, última fila).
# Filas: 1 reposo en 8 orientaciones; 2-5 caminar recto; 6-9 caminar en diagonal.
PERSONAJES_DISTRITO = {
    "guardian": ("Elías Vega", "NPCS/NPC Mundo2/NPC2-mundo2-Fila{fila}.png", 5),
    "mensajero": ("Mateo Ríos", "NPCS/Mensajero urbano/Mensajero_urbano-Fila{fila}.png", 9),
    "habitante": ("Tomás Red", "NPCS/Habitante Conectada/Habitante_conectada-Fila{fila}.png", 9),
    "aspirante": ("Ronaldo Vélez", "NPCS/Aspirante Contempóraneo/Aspirante_contemporaneo-Fila{fila}.png", 9),
}
FILAS_CAMINAR = {
    "abajo": 2, "derecha": 3, "arriba": 4, "izquierda": 5,
    "abajo_derecha": 6, "arriba_derecha": 7, "arriba_izquierda": 8, "abajo_izquierda": 9,
}
RECTA_EQUIVALENTE = {
    "abajo_derecha": "derecha", "arriba_derecha": "derecha",
    "arriba_izquierda": "izquierda", "abajo_izquierda": "izquierda",
}


def _recortar_juntos(frames):
    """Recorta todos los cuadros por igual: el personaje no tiembla al animarse."""
    limites = frames[0].get_bounding_rect()
    for frame in frames[1:]:
        limites.union_ip(frame.get_bounding_rect())
    return [frame.subsurface(limites).copy() for frame in frames]


def archivos_reposo_de(nombre_sprite):
    """Hojas de reposo (una por fila) de la carpeta del personaje; [] si no tiene."""
    carpeta = os.path.dirname(str(nombre_sprite).replace("\\", "/"))
    if not carpeta.lower().startswith("npcs/"):
        return []
    # El mapa guarda algunas rutas anidadas ("NPCS/Aspirante hombre/Habitante mujer").
    carpeta = "NPCS/" + carpeta.rsplit("/", 1)[-1]
    base = os.path.join(str(RAIZ), "Imagenes", *carpeta.split("/"))
    encontrados = []
    for relativa in ("", "Reposo"):
        directorio = os.path.join(base, relativa) if relativa else base
        if os.path.isdir(directorio):
            encontrados += [os.path.join(carpeta, relativa, archivo).replace("\\", "/") for archivo in os.listdir(directorio)
                            if "reposo" in archivo.casefold() and archivo.lower().endswith(".png")]
    fila = lambda ruta: int(re.findall(r"\d+", os.path.basename(ruta).split(".")[0].replace("Num", ""))[0])
    return sorted(encontrados, key=fila) if len(encontrados) == 4 else []


def cuadros_reposo_de(nombre_sprite, orientacion):
    """Los ocho cuadros de reposo de una orientación; [] si no tiene."""
    archivos = archivos_reposo_de(nombre_sprite)
    if not archivos:
        return []
    return _recortar_juntos(cargar_spritesheet_frames(archivos[DIRECCION_A_FILA_REPOSO[orientacion] - 1], 8))


def preparar_reposo(objeto):
    """Da a un NPC colocado su animación de reposo, del mismo alto que su sprite.

    Se hace una vez por tamaño de dibujo; sin hojas de reposo queda como estaba."""
    orientacion = objeto.get("direccion") if objeto.get("direccion") in ORIENTACIONES_SPRITE else "abajo"
    cuadros = cuadros_reposo_de(objeto.get("nombre", ""), orientacion)
    limites = objeto["imagen"].get_bounding_rect()
    if len(cuadros) < 2 or not limites.height:
        return
    factor = limites.height / cuadros[0].get_height()
    objeto["cuadros_reposo"] = [
        pygame.transform.scale(c, (max(1, round(c.get_width() * factor)), limites.height)) for c in cuadros]
    objeto["ancla_reposo"] = (objeto["rect"].x + limites.centerx, objeto["rect"].y + limites.bottom)


def cargar_personajes_distrito(altura):
    """Clips de los equivalentes de Distrito Conecta, a ``altura`` píxeles (una sola vez)."""
    personajes = {}
    for rol, (_, plantilla, ultima_fila) in PERSONAJES_DISTRITO.items():
        reposo = cargar_spritesheet_frames(plantilla.format(fila=1), len(ORIENTACIONES_SPRITE))
        clips = {("reposo", orientacion): (cuadros_reposo_de(plantilla, orientacion) or _recortar_juntos([frame]))
                 for orientacion, frame in zip(ORIENTACIONES_SPRITE, reposo)}
        for orientacion, fila in FILAS_CAMINAR.items():
            if fila <= ultima_fila:
                clips[("caminar", orientacion)] = _recortar_juntos(
                    cargar_spritesheet_frames(plantilla.format(fila=fila), 8))
        for orientacion, recta in RECTA_EQUIVALENTE.items():
            clips.setdefault(("caminar", orientacion), clips[("caminar", recta)])
        for orientacion in ORIENTACIONES_SPRITE:
            clips[("correr", orientacion)] = clips[("caminar", orientacion)]
        escala = altura / max(f.get_height() for frames in clips.values() for f in frames)
        escalados = {}  # las orientaciones que comparten hoja comparten sus cuadros
        for clave, frames in clips.items():
            if id(frames) not in escalados:
                escalados[id(frames)] = [
                    pygame.transform.scale(f, (max(1, round(f.get_width() * escala)), max(1, round(f.get_height() * escala))))
                    for f in frames
                ]
        personajes[rol] = {clave: escalados[id(frames)] for clave, frames in clips.items()}
    return personajes


def _cargar_ruta_npc(datos_ruta, rect_mapa, nombre):
    if not isinstance(datos_ruta, dict):
        return None
    patron = datos_ruta.get("pattern")
    puntos_datos = datos_ruta.get("points")
    if patron not in ("loop", "ping_pong") or not isinstance(puntos_datos, list):
        print(f"[Dimensiones] Ruta inválida para {nombre}; no se moverá.")
        return None
    puntos = []
    try:
        for punto in puntos_datos:
            rx = float(punto["rx"])
            ry = float(punto["ry"])
            if not (math.isfinite(rx) and math.isfinite(ry) and 0 <= rx <= 1 and 0 <= ry <= 1):
                raise ValueError("waypoint fuera del mapa")
            puntos.append((
                round(rect_mapa.x + rx * rect_mapa.width),
                round(rect_mapa.y + ry * rect_mapa.height),
            ))
    except (KeyError, TypeError, ValueError) as error:
        print(f"[Dimensiones] Ruta inválida para {nombre}: {error}; no se moverá.")
        return None
    if len(puntos) < 2:
        print(f"[Dimensiones] Ruta incompleta para {nombre}; no se moverá.")
        return None
    return {"pattern": patron, "points": puntos}


def _cargar_decoraciones_presentes(datos, rect_mapa):
    posiciones = datos.get("npc_positions", {})
    rutas = datos.get("npc_routes", {})
    if not isinstance(rutas, dict):
        print("[Dimensiones] npc_routes inválido; no se moverán los NPC.")
        rutas = {}
    decoraciones = []
    for personaje in PERSONAJES_PRESENTES:
        sitio = posiciones.get(personaje["clave"])
        if not isinstance(sitio, dict):
            continue
        rx = float(sitio.get("rx", 0.5))
        ry = float(sitio.get("ry", 0.5))
        rw = max(0.01, float(sitio.get("rw", 0.06)))
        rh = max(0.01, float(sitio.get("rh", 0.12)))
        centro = (
            round(rect_mapa.x + rx * rect_mapa.width),
            round(rect_mapa.y + ry * rect_mapa.height),
        )
        rect_sitio = pygame.Rect(
            0,
            0,
            max(1, round(rw * rect_mapa.width)),
            max(1, round(rh * rect_mapa.height)),
        )
        rect_sitio.center = centro
        ruta = _cargar_ruta_npc(
            rutas.get(personaje["clave"], {}),
            rect_mapa,
            personaje["nombre"],
        )
        if ruta:
            rect_sitio.midbottom = ruta["points"][0]
        rect = pygame.Rect(
            0,
            0,
            max(
                1,
                round(
                    rect_sitio.width
                    * personaje.get("escala", ESCALA_NPC_PRESENTE)
                ),
            ),
            max(
                1,
                round(
                    rect_sitio.height
                    * personaje.get("escala", ESCALA_NPC_PRESENTE)
                ),
            ),
        )
        rect.midbottom = rect_sitio.midbottom
        idle = _cargar_sprite_direccional(personaje["sprite"], rect.size)
        if not idle:
            print(
                f"[Dimensiones] No se pudo cargar el reposo de "
                f"{personaje['nombre']}."
            )
            continue
        caminar = {}
        for direccion, fila in (
            ("abajo", 2),
            ("derecha", 3),
            ("arriba", 4),
            ("izquierda", 5),
        ):
            frames = cargar_spritesheet_frames(
                personaje["sprite_caminar"].format(fila=fila),
                8,
            )
            if not frames:
                raise RuntimeError(
                    f"No se pudieron cargar los frames de caminata de "
                    f"{personaje['nombre']} ({direccion})."
                )
            caminar[direccion] = [
                _escalar_sprite_en_caja(frame, rect.size)
                for frame in frames
            ]
        hitbox = pygame.Rect(
            0,
            0,
            max(1, round(rect.width * 0.45)),
            max(1, round(rect.height * 0.25)),
        )
        hitbox.midbottom = rect.midbottom
        direccion = sitio.get("direccion", "abajo")
        if direccion not in ORIENTACIONES_SPRITE:
            direccion = "abajo"
        generador_ruta = random.Random(
            sum(ord(caracter) for caracter in personaje["clave"])
        )
        decoraciones.append({
            "id": f"npc_presente_{personaje['clave'].lower().replace(' ', '_')}",
            "nombre": personaje["sprite"],
            "personaje": personaje["nombre"],
            "rect": rect,
            "hitbox": hitbox,
            "posicion_ruta_x": float(rect.midbottom[0]),
            "posicion_ruta_y": float(rect.midbottom[1]),
            "imagen": idle["abajo"],
            "frames_idle": idle,
            "frames_caminar": caminar,
            "ruta_npc": ruta,
            "indice_waypoint": 1 if ruta else 0,
            "direccion_ruta": 1,
            "estado_ruta": "IDLE",
            "tiempo_estado_ms": generador_ruta.uniform(*PAUSA_PATRULLA_NPC_MS),
            "tiempo_frame_ms": 0.0,
            "indice_frame": 0,
            "random_ruta": generador_ruta,
            "velocidad_ruta": VELOCIDAD_PATRULLA_NPC * generador_ruta.uniform(
                1 - VARIACION_VELOCIDAD_NPC,
                1 + VARIACION_VELOCIDAD_NPC,
            ),
            "sprite_preparado": True,
            "direccion": direccion,
            "puente": False,
            "fondo_animado": False,
            "escalera": False,
            "puente_animable": False,
            "frames": [],
            "tronco_eco": False,
        })
    return decoraciones


def cargar_frames_tronco_eco():
    frames = []
    for indice_fila in range(1, 5):
        frames.extend(cargar_spritesheet_frames(
            os.path.join("Tronco ecos", f"Tronco-ecos-fila{indice_fila}.png"),
            cantidad=4,
        ))
    return frames


def cargar_variantes_tronco_eco():
    """Cada fila es un diseño de tronco con sus cuatro cuadros (1..4 -> cuadros)."""
    return {fila: cargar_spritesheet_frames(os.path.join("Tronco ecos", f"Tronco-ecos-fila{fila}.png"), cantidad=4)
            for fila in range(1, 5)}


def cargar_frames_idle_guardian():
    return _cargar_frames_idle_personaje("Guardián")


def crear_jugador_local(recursos):
    es_dimension_presente = recursos.get("dimension") == DIMENSION_PRESENTE
    personaje_presente = (
        recursos.get("jugador_presente")
        if es_dimension_presente
        else None
    )
    usa_personaje_presente = bool(
        personaje_presente and personaje_presente.get("frames_idle")
    )
    tamano_jugador = (
        TAMANO_JUGADOR_PRESENTE if usa_personaje_presente else TAMANO_JUGADOR
    )
    decoracion = recursos.get("guardian")
    if personaje_presente and personaje_presente.get("frames_idle"):
        sprite_rect = pygame.Rect(
            0,
            0,
            *tamano_jugador,
        )
        imagen_idle = personaje_presente["frames_idle"].get("abajo")
    elif decoracion:
        sprite_rect = pygame.Rect(0, 0, *tamano_jugador)
        sprite_rect.midbottom = decoracion["rect"].midbottom
        imagen_idle = decoracion["imagen"]
    elif es_dimension_presente:
        raise RuntimeError(
            "No se pudo cargar el personaje del Distrito Conecta; "
            "se cancela la creación del jugador para no mostrar al Guardián."
        )
    else:
        sprite_rect = pygame.Rect(ANCHO // 2, ALTO // 2, *tamano_jugador)
        imagen_idle = None
    pies = pygame.Rect(0, 0, *TAMANO_HITBOX_PIES)
    pies.midbottom = sprite_rect.midbottom
    spawn = recursos.get("spawn_dimension")
    if spawn is not None:
        pies.center = spawn
        sprite_rect.midbottom = pies.midbottom
    direccion_inicial = (
        "abajo"
        if usa_personaje_presente
        else decoracion.get("direccion", "abajo") if decoracion else "abajo"
    )
    frames_caminar = (
        personaje_presente.get("frames_caminar", {})
        if usa_personaje_presente
        else recursos.get("guardian_walk_frames")
    )
    if not isinstance(frames_caminar, dict):
        frames_caminar = {}
    return {
        "id": "periodista" if usa_personaje_presente else "guardian",
        "nombre": (
            NOMBRE_JUGADOR_PRESENTE if usa_personaje_presente else "Guardián"
        ),
        "rect": sprite_rect,
        "pies": pies,
        "posicion_x": float(pies.x),
        "posicion_y": float(pies.y),
        "imagen_idle": imagen_idle,
        "frames_idle": (
            personaje_presente.get("frames_idle", {})
            if usa_personaje_presente
            else (
                decoracion.get("frames_idle", {})
                if decoracion
                else recursos.get("guardian_idle_frames", {})
            )
        ),
        "frames_caminar": frames_caminar,
        "frames_hablar": (
            []
            if usa_personaje_presente
            else recursos.get("guardian_talk_frames", [])
        ),
        "frames_eco": (
            []
            if usa_personaje_presente
            else recursos.get("guardian_eco_frames", [])
        ),
        "tiempo_animacion": 0.0,
        "indice_frame": 0,
        "estado_visual": "idle",
        "direccion": direccion_inicial,
        "en_movimiento": False,
    }
