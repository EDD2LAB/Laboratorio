"""
La Copa: Voces en las Alturas
Interfaz grafica en pygame con mapa, personajes, cinematicas breves y tablilla.

La logica de estructuras de datos queda en logica_juego.py y Arboles.py:
- EstadoJuego administra la cola de tablillas y avanza por el arbol de decisiones.
- Cada raiz de tablilla trae una categoria, tomada del arbol de clasificacion.
"""

import json
import math
import os
import sys
import unicodedata

import pygame

from audio_manager import GestorAudio
from conversaciones import construir_conversacion, construir_mensajes_eco, construir_respuesta_eco
from grafo_fisico import GrafoFisico
from interfaz.boton import Boton, GrupoBotones
from interfaz.dialogo import ControladorDialogo
from interfaz.hud import HUDIndicadores
from interfaz.menu import MenuModal
from interfaz.mensaje_privado import ControladorMensajePrivado
from logica_juego import EstadoJuego
from particulas import SistemaParticulas

ANCHO, ALTO = 960, 720
RELACION_ASPECTO = ANCHO / ALTO
FPS = 60
RUTA_ASSETS = os.path.join(os.path.dirname(__file__), "Imagenes")
RUTA_FUENTE = os.path.join(os.path.dirname(__file__), "Fuentes", "determination.ttf")

CREMA = (255, 243, 210)
TINTA = (61, 37, 25)
MADERA = (111, 75, 43)
ORO = (237, 185, 87)
PANEL_OSCURO = (16, 31, 25, 218)

ESCENA_MAPA = "mapa"
ESCENA_TABLILLA = "tablilla"
ESCENA_CONSECUENCIA = "consecuencia"
ESCENA_CLASIFICACION = "clasificacion"
ESCENA_RESULTADO = "resultado"
ESCENA_DIALOGO = "dialogo"
ESCENA_MENSAJE = "mensaje_privado"
ESCENA_MAPA_DESTINO = "mapa_destino"
ESCENA_FINAL = "final"
ESCENA_PAUSA = "pausa"
ESCENA_VISUAL = "visual"
ESCENA_VOLUMEN = "volumen"
ESCENA_AYUDA = "ayuda"
CENTRO_TABLILLA = (ANCHO // 2, 330)
CENTRO_TABLILLA_CENTRADA = (ANCHO // 2, 330)
CENTRO_CALDERO = (ANCHO // 2, 380)
TAMANO_HITBOX_PIES = (12, 8)
VELOCIDAD_GUARDIAN = 155
DISTANCIA_INTERACCION = 58
ESCENA_ECO = "eco_tronco"


def normalizar_ruta(ruta):
    texto = ruta.replace("\\", "/").lower()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(caracter for caracter in texto if unicodedata.category(caracter) != "Mn")


def buscar_asset(nombre):
    """Busca tanto rutas históricas como recursos reubicados por carpetas."""
    ruta = os.path.join(RUTA_ASSETS, nombre)
    if os.path.isfile(ruta):
        return ruta

    objetivo = normalizar_ruta(nombre)
    objetivo_nombre = normalizar_ruta(os.path.basename(nombre))
    coincidencia_por_nombre = None
    for carpeta, _, archivos in os.walk(RUTA_ASSETS):
        for archivo in archivos:
            ruta_real = os.path.join(carpeta, archivo)
            relativa = os.path.relpath(ruta_real, RUTA_ASSETS)
            if normalizar_ruta(relativa) == objetivo:
                return ruta_real
            if coincidencia_por_nombre is None and normalizar_ruta(archivo) == objetivo_nombre:
                coincidencia_por_nombre = ruta_real
    if coincidencia_por_nombre:
        return coincidencia_por_nombre
    return ruta


def cargar_imagen(nombre, tamano=None, requerido=True):
    """Carga una imagen desde Imagenes/. Si no es requerida, permite placeholder."""
    ruta = buscar_asset(nombre)
    try:
        imagen = pygame.image.load(ruta).convert_alpha()
    except (pygame.error, FileNotFoundError) as error:
        if requerido:
            raise RuntimeError(f"No se pudo cargar el recurso: {ruta}") from error
        return None
    if tamano:
        imagen = pygame.transform.scale(imagen, tamano)
    return imagen


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


def cargar_spritesheet_frames(nombre, cantidad=8):
    imagen = cargar_imagen(nombre, requerido=False)
    if imagen is None:
        print(f"[advertencia] No se encontró la hoja de sprites: {nombre}")
        return []
    ancho_frame = imagen.get_width() // cantidad
    if ancho_frame < 1:
        print(f"[advertencia] Spritesheet inválido (sin {cantidad} frames): {nombre}")
        return []
    return [
        imagen.subsurface(pygame.Rect(indice * ancho_frame, 0, ancho_frame, imagen.get_height())).copy()
        for indice in range(cantidad)
    ]


def cargar_frames_tronco_eco():
    frames = []
    for indice_fila in range(1, 5):
        frames.extend(cargar_spritesheet_frames(
            os.path.join("Tronco ecos", f"Tronco-ecos-fila{indice_fila}.png"),
            cantidad=4,
        ))
    return frames


def dibujar_cascada_animada(superficie, recursos):
    frames = recursos.get("frames_cascada", [])
    if not frames:
        return
    mapa_manana = recursos["mapas_dia"][0]
    ancho_mapa, alto_mapa = mapa_manana.get_size()
    ancho, alto = superficie.get_size()
    escala_x = ancho / ancho_mapa
    escala_y = alto / alto_mapa
    rect_mapa_manana = pygame.Rect(
        round(ancho_mapa * 320 / 1679),
        0,
        max(1, round(ancho_mapa * 430 / 1679)),
        max(1, round(alto_mapa * 920 / 937)),
    )
    rect = pygame.Rect(
        round(rect_mapa_manana.x * escala_x),
        round(rect_mapa_manana.y * escala_y),
        max(1, round(rect_mapa_manana.width * escala_x)),
        max(1, round(rect_mapa_manana.height * escala_y)),
    )
    frames_por_mapa = recursos.setdefault("frames_cascada_por_mapa", {})
    clave_cache = (0, rect.size)
    if clave_cache not in frames_por_mapa:
        mascara_mapa_manana = pygame.Surface(rect_mapa_manana.size, pygame.SRCALPHA)
        for y in range(rect_mapa_manana.height):
            for x in range(rect_mapa_manana.width):
                rojo, verde, azul = mapa_manana.get_at((
                    rect_mapa_manana.x + x, rect_mapa_manana.y + y
                ))[:3]
                es_agua = (
                    azul > 140 and verde > 130
                    and azul > rojo * 1.35 and verde > rojo * 1.25
                )
                es_espuma = (
                    azul > 185 and verde > 185
                    and azul >= rojo and verde >= rojo
                )
                es_espuma_clara = (
                    rojo > 220 and verde > 220 and azul > 220
                    and max(rojo, verde, azul) - min(rojo, verde, azul) < 45
                )
                if es_agua or es_espuma or es_espuma_clara:
                    mascara_mapa_manana.set_at((x, y), (255, 255, 255, 255))
        mascara = pygame.transform.scale(mascara_mapa_manana, rect.size)

        frames_por_mapa[clave_cache] = []
        for frame_original in frames:
            frame = pygame.transform.scale(frame_original, rect.size)
            frame.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            frames_por_mapa[clave_cache].append(frame)

    frames_animados = frames_por_mapa[clave_cache]
    frame = frames_animados[(pygame.time.get_ticks() // 120) % len(frames_animados)]
    superficie.blit(frame, rect)
    for objeto in recursos["decoraciones"]:
        if (
            not objeto["puente"]
            and not objeto["frames"]
            and not objeto["tronco_eco"]
            and objeto["personaje"] != "Guardián"
            and objeto["rect"].colliderect(rect)
        ):
            superficie.blit(objeto["imagen"], objeto["rect"])


def cargar_frames_idle_guardian():
    orientaciones = (
        "abajo",
        "abajo_derecha",
        "derecha",
        "arriba_derecha",
        "arriba",
        "arriba_izquierda",
        "izquierda",
        "abajo_izquierda",
    )
    return {
        orientacion: cargar_imagen(
            os.path.join("NPCS", "Guardian", f"Fila 1 - {indice}. Guardián.png"),
            requerido=False,
        )
        for indice, orientacion in enumerate(orientaciones, start=1)
    }


def cargar_mapa_principal():
    """Carga el mapa usando en todos los momentos las hitboxes del fondo de mañana."""
    ruta_hitboxes = os.path.join(
        os.path.dirname(__file__),
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
        imagen_original = cargar_imagen(objeto["name"])
        recorte = objeto.get("crop")
        rect = pygame.Rect(
            round(objeto["x"] * ANCHO),
            round(objeto["y"] * ALTO),
            max(1, round(objeto["w"] * ANCHO)),
            max(1, round(objeto["h"] * ALTO)),
        )
        personaje = personaje_de_decoracion(objeto["name"])
        nombre_normalizado = normalizar_ruta(objeto["name"])
        es_puente = nombre_normalizado.startswith("puentes/")
        nombre_puente = os.path.splitext(os.path.basename(objeto["name"]))[0]
        cantidad_frames = max(1, int(objeto.get("frames", 1)))
        imagenes_frames = []
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
            imagen = pygame.transform.scale(imagen, rect.size)

        hitbox = rect.copy()
        if personaje == "Guardián":
            hitbox.inflate_ip(-round(rect.width * 0.4), -round(rect.height * 0.4))
        decoraciones.append({
            "id": f"puente_{nombre_puente[6:].lower()}" if es_puente else None,
            "nombre": objeto["name"],
            "personaje": personaje,
            "rect": rect,
            "hitbox": hitbox,
            "imagen": imagen,
            "puente": es_puente,
            "frames": imagenes_frames,
            "tronco_eco": nombre_normalizado.startswith("tronco ecos/"),
        })

    decoraciones.sort(key=lambda objeto: objeto["puente"], reverse=True)
    for mapa_dia in mapas_dia:
        for objeto in decoraciones:
            if (
                objeto["personaje"] != "Guardián"
                and not objeto["puente"]
                and not objeto["tronco_eco"]
                and not objeto["frames"]
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
        }
        if interaccion["accion"] == "puerta" and interaccion["destino"]:
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

    guardian = next(
        (objeto for objeto in decoraciones if objeto["personaje"] == "Guardián"),
        None,
    )
    if guardian is None:
        print("[advertencia] No se encontró la decoración del Guardián; usando posición inicial central.")
    return mapa, decoraciones, interacciones, hitboxes, guardian, mapas_dia


def cargar_fuente(tamano):
    """Usa la tipografía pixel-art incluida con el proyecto."""
    if not os.path.isfile(RUTA_FUENTE):
        raise RuntimeError(f"No se encontró la fuente del juego: {RUTA_FUENTE}")
    return pygame.font.Font(RUTA_FUENTE, tamano)


def cargar_icono_hud(nombre):
    """Extrae el emblema de una barra ilustrada sin deformar su proporción.

    Los cinco recursos no comparten el mismo formato: el de Desinformación es
    mucho más bajo. Usar la tira completa producía un HUD desigual; el icono
    sí conserva una zona cuadrada consistente en todos los recursos.
    """
    imagen = cargar_imagen(nombre)
    # Algunos PNG tienen píxeles semitransparentes aislados fuera del dibujo.
    # La máscara con umbral localiza el bloque real del arte y evita que esos
    # píxeles falsos alteren el cálculo del recorte.
    componentes = pygame.mask.from_surface(imagen, 32).get_bounding_rects()
    limites = max(componentes, key=lambda rect: rect.width * rect.height) if componentes else imagen.get_rect()
    imagen = imagen.subsurface(limites).copy()
    # Las composiciones provienen de archivos exportados con lienzos muy
    # distintos. Estos límites separan el medallón de la etiqueta de texto de
    # cada recurso antes de normalizarlo a una misma medida.
    proporcion_icono = {
        "Barra_sabiduría.png": 1.20,
        "Barra_confianza.png": 1.20,
        "Barra_armonía.png": 1.05,
        "Barra_susurros_falsos.png": 1.08,
        "Barra_desinformación.png": 1.35,
    }.get(nombre, 1.0)
    ancho_icono = min(imagen.get_width(), round(imagen.get_height() * proporcion_icono))
    icono = imagen.subsurface((0, 0, ancho_icono, imagen.get_height())).copy()
    # Se deja aire transparente alrededor del emblema. Así las hojas y los
    # adornos no quedan pegados ni parecen cortados por el borde del HUD.
    icono_escalado = pygame.transform.smoothscale(icono, (42, 42))
    contenedor = pygame.Surface((48, 48), pygame.SRCALPHA)
    contenedor.blit(icono_escalado, (3, 3))
    return contenedor


def cargar_efecto_tablilla(nombre):
    """Convierte un spritesheet horizontal de 12 pasos en fotogramas útiles."""
    spritesheet = cargar_imagen(nombre)
    cantidad = 12
    ancho_frame = spritesheet.get_width() // cantidad
    cuadros = []
    for indice in range(cantidad):
        cuadro = spritesheet.subsurface((indice * ancho_frame, 0, ancho_frame, spritesheet.get_height())).copy()
        limites = cuadro.get_bounding_rect()
        if limites.width and limites.height:
            cuadro = cuadro.subsurface(limites).copy()
            escala = min(390 / cuadro.get_width(), 360 / cuadro.get_height(), 1)
            cuadro = pygame.transform.smoothscale(
                cuadro, (max(1, round(cuadro.get_width() * escala)), max(1, round(cuadro.get_height() * escala)))
            )
        cuadros.append(cuadro)
    return cuadros


def superficie_con_alpha(tamano, color):
    superficie = pygame.Surface(tamano, pygame.SRCALPHA)
    superficie.fill(color)
    return superficie


def envolver_texto(texto, fuente, ancho_maximo):
    palabras, lineas, actual = texto.split(), [], ""
    for palabra in palabras:
        prueba = f"{actual} {palabra}".strip()
        if fuente.size(prueba)[0] <= ancho_maximo:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


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


def crear_jugador_local(recursos):
    decoracion = recursos.get("guardian")
    if decoracion:
        sprite_rect = decoracion["rect"].copy()
        imagen_idle = decoracion["imagen"]
    else:
        sprite_rect = pygame.Rect(ANCHO // 2, ALTO // 2, 36, 58)
        imagen_idle = None
    pies = pygame.Rect(0, 0, *TAMANO_HITBOX_PIES)
    pies.midbottom = sprite_rect.midbottom
    frames_caminar = recursos.get("guardian_walk_frames")
    if not isinstance(frames_caminar, dict):
        frames_caminar = {}
    return {
        "id": "guardian",
        "rect": sprite_rect,
        "pies": pies,
        "posicion_x": float(pies.x),
        "posicion_y": float(pies.y),
        "imagen_idle": imagen_idle,
        "frames_idle": recursos.get("guardian_idle_frames", {}),
        "frames_caminar": frames_caminar,
        "frames_hablar": recursos.get("guardian_talk_frames", []),
        "frames_eco": recursos.get("guardian_eco_frames", []),
        "tiempo_animacion": 0.0,
        "indice_frame": 0,
        "estado_visual": "idle",
        "direccion": "abajo",
        "en_movimiento": False,
    }


def _rect_hits_line(rect, x1, y1, x2, y2, grosor):
    dx, dy = x2 - x1, y2 - y1
    longitud_cuadrada = dx * dx + dy * dy
    if longitud_cuadrada == 0:
        px, py = x1, y1
    else:
        t = max(0, min(1, ((rect.centerx - x1) * dx + (rect.centery - y1) * dy) / longitud_cuadrada))
        px, py = x1 + t * dx, y1 + t * dy
    radio = math.hypot(rect.width, rect.height) / 2 + grosor / 2
    return (rect.centerx - px) ** 2 + (rect.centery - py) ** 2 <= radio * radio


def colision_hitbox_mapa(rect, hitbox):
    tipo = hitbox.get("type", "rect")
    if tipo == "rect":
        obstaculo = pygame.Rect(
            round(hitbox.get("rx", 0) * ANCHO),
            round(hitbox.get("ry", 0) * ALTO),
            max(1, round(hitbox.get("rw", 0) * ANCHO)),
            max(1, round(hitbox.get("rh", 0) * ALTO)),
        )
        return rect.colliderect(obstaculo)
    if tipo == "circle":
        cx, cy = hitbox.get("cx", 0) * ANCHO, hitbox.get("cy", 0) * ALTO
        radio = max(4, hitbox.get("r", 0) * ANCHO)
        nx = max(rect.left, min(cx, rect.right))
        ny = max(rect.top, min(cy, rect.bottom))
        return (cx - nx) ** 2 + (cy - ny) ** 2 <= radio * radio
    if tipo == "line":
        return _rect_hits_line(
            rect,
            hitbox.get("x1", 0) * ANCHO,
            hitbox.get("y1", 0) * ALTO,
            hitbox.get("x2", 0) * ANCHO,
            hitbox.get("y2", 0) * ALTO,
            max(2, hitbox.get("thickness", 0.008) * ANCHO),
        )
    return False


def contiene_zona_caminable(rect, hitbox):
    if hitbox.get("type", "rect") == "rect":
        zona = pygame.Rect(
            round(hitbox.get("rx", 0) * ANCHO),
            round(hitbox.get("ry", 0) * ALTO),
            max(1, round(hitbox.get("rw", 0) * ANCHO)),
            max(1, round(hitbox.get("rh", 0) * ALTO)),
        )
        return zona.contains(rect)
    if hitbox.get("type") == "circle":
        cx, cy = hitbox.get("cx", 0) * ANCHO, hitbox.get("cy", 0) * ALTO
        radio = hitbox.get("r", 0) * ANCHO
        return all((x - cx) ** 2 + (y - cy) ** 2 <= radio * radio for x, y in (
            rect.topleft, rect.topright, rect.bottomleft, rect.bottomright
        ))
    return False


def jugador_bloqueado(rect, mundo):
    if not pygame.Rect(0, 0, ANCHO, ALTO).contains(rect):
        return True
    if any(
        hitbox.get("role", "wall") == "wall" and colision_hitbox_mapa(rect, hitbox)
        for hitbox in mundo["hitboxes"]
    ):
        return True
    zonas_caminables = [
        hitbox for hitbox in mundo["hitboxes"]
        if hitbox.get("role") == "walkable"
    ]
    if zonas_caminables and not any(
        contiene_zona_caminable(rect, zona) for zona in zonas_caminables
    ):
        return True
    return any(
        personaje["rect"].colliderect(rect) for personaje in mundo["personajes"]
    )


def ajustar_inicio_jugador(jugador, mundo):
    origen = jugador["pies"]
    if not jugador_bloqueado(origen, mundo):
        return

    for distancia in range(1, 65):
        for desplazamiento_y in range(-distancia, distancia + 1):
            desplazamiento_x = distancia - abs(desplazamiento_y)
            desplazamientos = (
                [(0, desplazamiento_y)]
                if desplazamiento_x == 0
                else [(-desplazamiento_x, desplazamiento_y), (desplazamiento_x, desplazamiento_y)]
            )
            for dx, dy in desplazamientos:
                candidato = origen.move(dx, dy)
                if jugador_bloqueado(candidato, mundo):
                    continue
                if any(
                    jugador_bloqueado(candidato.move(paso_x, paso_y), mundo)
                    for paso in range(1, 4)
                    for paso_x, paso_y in (
                        (-paso, 0), (paso, 0), (0, -paso), (0, paso)
                    )
                ):
                    continue
                jugador["pies"] = candidato
                jugador["posicion_x"] = float(candidato.x)
                jugador["posicion_y"] = float(candidato.y)
                jugador["rect"].midbottom = candidato.midbottom
                return

    raise RuntimeError("No se encontró una posición inicial libre para el Guardián.")


def _posicion_interaccion(jugador, interactuable):
    rect = interactuable["rect"]
    x = max(rect.left, min(jugador["pies"].centerx, rect.right))
    y = max(rect.top, min(jugador["pies"].centery, rect.bottom))
    return math.hypot(jugador["pies"].centerx - x, jugador["pies"].centery - y)


def buscar_interactuable_cercano(jugador, mundo):
    candidatos = [
        *mundo["personajes"],
        *mundo["interacciones"],
    ]
    cercanos = [
        (distancia, objeto)
        for objeto in candidatos
        if objeto.get("activo", True)
        and (distancia := _posicion_interaccion(jugador, objeto)) <= objeto.get("distancia", DISTANCIA_INTERACCION)
    ]
    cercanos.sort(key=lambda elemento: elemento[0])
    if not cercanos:
        mundo["interacciones_cercanas"] = []
        mundo["interaccion_seleccionada"] = None
        return None, None
    mundo["interacciones_cercanas"] = cercanos
    ids = [objeto.get("id", objeto.get("personaje", objeto["accion"])) for _, objeto in cercanos]
    seleccionada = mundo.get("interaccion_seleccionada")
    if seleccionada not in ids:
        seleccionada = ids[0]
        mundo["interaccion_seleccionada"] = seleccionada
    indice = ids.index(seleccionada)
    distancia, interactuable = cercanos[indice]
    interactuable["alternativas_cercanas"] = len(cercanos)
    interactuable["indice_alternativa"] = indice + 1
    return interactuable, distancia


def alternar_interactuable_cercano(mundo, sentido=1):
    cercanos = mundo.get("interacciones_cercanas", [])
    if len(cercanos) < 2:
        return
    ids = [objeto.get("id", objeto.get("personaje", objeto["accion"])) for _, objeto in cercanos]
    actual = mundo.get("interaccion_seleccionada")
    indice = ids.index(actual) if actual in ids else 0
    mundo["interaccion_seleccionada"] = ids[(indice + sentido) % len(ids)]


def reiniciar_jugador_en_casa(mundo):
    jugador = mundo["jugador"]
    jugador["pies"] = mundo["posicion_casa"].copy()
    jugador["posicion_x"] = float(jugador["pies"].x)
    jugador["posicion_y"] = float(jugador["pies"].y)
    jugador["rect"].midbottom = jugador["pies"].midbottom
    jugador["direccion"] = "abajo"
    jugador["en_movimiento"] = False
    jugador["estado_visual"] = "idle"
    jugador["indice_frame"] = 0
    jugador["tiempo_animacion"] = 0.0
    mundo["interaccion_seleccionada"] = None


PLATAFORMAS_ALDEA = (
    {"id": "plataforma_central", "nombre": "Plataforma Central", "posicion": [0.50, 0.50]},
    {"id": "plataforma_noroeste", "nombre": "Plataforma Noroeste", "posicion": [0.20, 0.22]},
    {"id": "plataforma_noreste", "nombre": "Plataforma Noreste", "posicion": [0.80, 0.22]},
    {"id": "plataforma_suroeste", "nombre": "Plataforma Suroeste", "posicion": [0.20, 0.68]},
    {"id": "plataforma_sureste", "nombre": "Plataforma Sureste", "posicion": [0.80, 0.68]},
    {"id": "plataforma_borde_oeste_norte", "nombre": "Borde Oeste Norte", "posicion": [0.02, 0.45]},
    {"id": "plataforma_borde_este_norte", "nombre": "Borde Este Norte", "posicion": [0.98, 0.45]},
    {"id": "plataforma_borde_oeste_sur", "nombre": "Borde Oeste Sur", "posicion": [0.02, 0.91]},
    {"id": "plataforma_borde_este_sur", "nombre": "Borde Este Sur", "posicion": [0.98, 0.91]},
)

CONEXIONES_PUENTES_ALDEA = (
    ("puente_1", "plataforma_noroeste", "plataforma_central"),
    ("puente_2", "plataforma_noreste", "plataforma_central"),
    ("puente_3", "plataforma_noroeste", "plataforma_borde_oeste_norte"),
    ("puente_4", "plataforma_noreste", "plataforma_borde_este_norte"),
    ("puente_5", "plataforma_suroeste", "plataforma_borde_oeste_sur"),
    ("puente_6", "plataforma_suroeste", "plataforma_central"),
    ("puente_7", "plataforma_central", "plataforma_sureste"),
    ("puente_8", "plataforma_sureste", "plataforma_borde_este_sur"),
)


def crear_grafo_fisico(decoraciones):
    """Asocia plataformas (posiciones normalizadas 0..1) y puentes del mapa."""
    puentes_visuales = {
        objeto["id"]: objeto
        for objeto in decoraciones
        if objeto.get("puente") and objeto.get("id")
    }
    puentes = []
    for puente_id, origen, destino in CONEXIONES_PUENTES_ALDEA:
        if puente_id not in puentes_visuales:
            raise RuntimeError(f"No se encontro la decoracion del {puente_id}.")
        puentes.append({
            "id": puente_id,
            "origen": origen,
            "destino": destino,
            "estado": "normal",
        })
    return GrafoFisico(PLATAFORMAS_ALDEA, puentes)


def mover_jugador(jugador, mundo, teclas, delta_ms):
    dx = int(teclas[pygame.K_d] or teclas[pygame.K_RIGHT]) - int(teclas[pygame.K_a] or teclas[pygame.K_LEFT])
    dy = int(teclas[pygame.K_s] or teclas[pygame.K_DOWN]) - int(teclas[pygame.K_w] or teclas[pygame.K_UP])
    velocidad = VELOCIDAD_GUARDIAN * (
        1.65 if teclas[pygame.K_LSHIFT] or teclas[pygame.K_RSHIFT] else 1.0
    )
    movimiento = dx != 0 or dy != 0
    jugador["en_movimiento"] = movimiento
    if not movimiento:
        return
    direcciones_diagonales = {
        (1, 1): "abajo_derecha",
        (1, -1): "arriba_derecha",
        (-1, -1): "arriba_izquierda",
        (-1, 1): "abajo_izquierda",
    }
    direccion = direcciones_diagonales.get((dx, dy))
    if direccion is None:
        direccion = "arriba" if dy < 0 else "abajo" if dy > 0 else (
            "derecha" if dx > 0 else "izquierda"
        )
    if direccion != jugador["direccion"]:
        jugador["direccion"] = direccion
        jugador["indice_frame"] = 0
    if dx and dy:
        direccion_movimiento = "derecha" if dx > 0 else "izquierda"
    else:
        direccion_movimiento = direccion
    jugador["direccion_movimiento"] = direccion_movimiento
    if dx and dy:
        dx *= math.sqrt(0.5)
        dy *= math.sqrt(0.5)
    delta = min(max(delta_ms, 0), 100) / 1000
    pasos = max(1, math.ceil(velocidad * delta / 3))
    paso_x = dx * velocidad * delta / pasos
    paso_y = dy * velocidad * delta / pasos
    posicion_x = jugador.get("posicion_x", float(jugador["pies"].x))
    posicion_y = jugador.get("posicion_y", float(jugador["pies"].y))
    jugador["tiempo_animacion"] += delta_ms
    while jugador["tiempo_animacion"] >= 110:
        jugador["tiempo_animacion"] -= 110
        frames_direccion = jugador["frames_caminar"].get(
            jugador.get("direccion_movimiento", jugador["direccion"]), []
        )
        if frames_direccion:
            jugador["indice_frame"] = (jugador["indice_frame"] + 1) % len(frames_direccion)

    for _ in range(pasos):
        for eje, movimiento_eje in (("x", paso_x), ("y", paso_y)):
            if not movimiento_eje:
                continue
            pies = jugador["pies"].copy()
            candidato = (posicion_x if eje == "x" else posicion_y) + movimiento_eje
            setattr(pies, eje, round(candidato))
            if not pygame.Rect(0, 0, ANCHO, ALTO).contains(pies):
                continue
            if not jugador_bloqueado(pies, mundo):
                jugador["pies"] = pies
                if eje == "x":
                    posicion_x = candidato
                else:
                    posicion_y = candidato
    jugador["posicion_x"] = posicion_x
    jugador["posicion_y"] = posicion_y
    jugador["rect"].midbottom = jugador["pies"].midbottom


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
    pygame.draw.rect(superficie, (255, 230, 40), jugador["pies"], 1)
    for personaje in mundo["personajes"]:
        pygame.draw.rect(superficie, (200, 130, 255), personaje["rect"], 1)
    for objeto in mundo["interacciones"]:
        color = (
            (200, 130, 255) if objeto.get("role") == "other"
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
        f"F3 | {estado_control} | {nombre} | {distancia:.0f}px | "
        f"luciernagas: {cantidad_luciernagas} | particulas: {cantidad_particulas}"
    )
    superficie.blit(fuente_debug.render(detalle, True, (255, 255, 255)), (8, 8))
    dibujar_debug_grafo(superficie, mundo["grafo_fisico"], mundo["decoraciones"])
    fuente_historial = pygame.font.Font(None, 15)
    y_historial = 28
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


def _posicion_en_mapa(plataforma, ancho=ANCHO, alto=ALTO):
    x, y = plataforma["posicion"]
    return round(x * ancho), round(y * alto)


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


def dibujar_decoraciones_editor(superficie, recursos):
    """Dibuja puentes y animaciones que fueron colocados desde el editor."""
    tiempo = pygame.time.get_ticks()
    for objeto in recursos["decoraciones"]:
        if objeto.get("personaje") == "Guardián" or objeto.get("tronco_eco"):
            continue
        if objeto.get("puente"):
            superficie.blit(objeto["imagen"], objeto["rect"])
        elif objeto.get("frames") and not objeto.get("tronco_eco"):
            frames = objeto["frames"]
            frame = frames[(tiempo // 140) % len(frames)]
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
        imagen = jugador["frames_idle"].get(jugador["direccion"]) or jugador["imagen_idle"]
    if imagen:
        imagen = pygame.transform.scale(imagen, jugador["rect"].size)
        if (
            jugador["direccion"] in ("izquierda", "arriba_izquierda", "abajo_izquierda")
            and jugador["estado_visual"] in ("hablar", "usar_eco")
        ):
            imagen = pygame.transform.flip(imagen, True, False)
        superficie.blit(imagen, jugador["rect"])


def dibujar_troncos_eco(superficie, recursos, mundo):
    for interaccion in mundo["interacciones"]:
        if interaccion.get("accion") != "usar_eco_tronco" or not interaccion.get("activo", True):
            continue
        frames = interaccion.get("frames") or recursos.get("frames_tronco_eco", [])
        if not frames:
            continue
        frame = frames[(pygame.time.get_ticks() // 140) % len(frames)]
        rect = interaccion["rect"]
        tamano = rect.size if interaccion.get("frames") else (58, 64)
        imagen = pygame.transform.scale(frame, tamano)
        superficie.blit(imagen, imagen.get_rect(midbottom=rect.midbottom))


def dibujar_mapa(
    superficie, recursos, mundo, estado, mouse_pos, hud,
    interactuable=None, distancia=None, particulas=None, debug=False, resaltar=True,
):
    superficie.blit(recursos["mapas_dia"][estado.dia], (0, 0))
    dibujar_cascada_animada(superficie, recursos)
    dibujar_decoraciones_editor(superficie, recursos)
    dibujar_troncos_eco(superficie, recursos, mundo)
    jugador = mundo["jugador"]
    dibujar_jugador(superficie, jugador)
    if particulas:
        particulas.dibujar(superficie)
    if debug:
        dibujar_debug_mapa(
            superficie, mundo, jugador, interactuable, distancia or 0,
            particulas, "EXPLORANDO", estado.propagaciones_informacion,
        )

    interaccion = interaccion_en_mapa(mouse_pos, mundo) if resaltar else None
    if interaccion:
        cache = recursos.setdefault("brillos_interaccion", {})
        objeto = interaccion.get("objeto")
        if objeto:
            dibujar_brillo_interaccion(superficie, objeto["imagen"], objeto["rect"], cache)
        else:
            rect = interaccion["rect"]
            luz = pygame.Surface(rect.size, pygame.SRCALPHA)
            for margen, alpha in ((0, 12), (4, 18), (8, 24)):
                zona = luz.get_rect().inflate(-margen * 2, -margen * 2)
                if zona.width > 0 and zona.height > 0:
                    pygame.draw.ellipse(luz, (*ORO, alpha), zona)
            superficie.blit(luz, rect)
        if interaccion["accion"] == "npc":
            texto = f"Clic para hablar con {interaccion['personaje']}"
        elif interaccion["accion"] == "tablilla":
            texto = "Clic en el Caldero para abrir la tablilla"
        elif interaccion["accion"] == "otro":
            texto = "Objeto interactuable"
        elif interaccion["accion"] == "puerta":
            texto = "Clic para viajar al mapa Central"
        else:
            texto = "Objeto interactuable"
    else:
        texto = "WASD o flechas: moverse | E: interactuar | Tab: alternar | F3: depuracion"
    hud.dibujar(superficie)
    dibujar_mensaje_mapa(superficie, recursos["fuente_mapa"], texto)
    if interactuable:
        nombres = {
            "npc": f"Hablar con {interactuable.get('personaje', 'personaje')}",
            "tablilla": "Examinar el Caldero",
            "usar_eco_tronco": "Usar Eco de Troncos",
            "puerta": "Viajar",
            "otro": "Interactuar",
        }
        etiqueta = f"[E] {nombres.get(interactuable.get('accion'), 'Interactuar')}"
        if interactuable.get("alternativas_cercanas", 0) > 1:
            etiqueta = (
                f"[Tab] cambiar ({interactuable['indice_alternativa']}/"
                f"{interactuable['alternativas_cercanas']}) | {etiqueta}"
            )
        indicador = recursos["fuente_mapa"].render(etiqueta, True, CREMA)
        caja = indicador.get_rect(midbottom=(jugador["rect"].centerx, jugador["rect"].top - 5)).inflate(14, 8)
        pygame.draw.rect(superficie, (18, 31, 25), caja, border_radius=5)
        pygame.draw.rect(superficie, ORO, caja, 1, border_radius=5)
        superficie.blit(indicador, indicador.get_rect(center=caja.center))


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
    superficie.blit(recursos["fondo_tablilla"], (0, 0))
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


def dibujar_pregunta_clasificacion(superficie, recursos, botones, mouse_pos):
    """Pide la clasificación sin mostrar cuál era la categoría real."""
    superficie.blit(recursos["fondo_tablilla"], (0, 0))
    # En clasificación el HUD no se muestra: la tablilla recupera el centro.
    rect = recursos["tablilla"].get_rect(center=CENTRO_TABLILLA_CENTRADA)
    superficie.blit(recursos["tablilla"], rect)
    titulo = recursos["fuente_panel_titulo"].render("¿CÓMO CLASIFICARÍAS ESTA TABLILLA?", True, TINTA)
    superficie.blit(titulo, titulo.get_rect(center=(rect.centerx, rect.y + 190)))
    # El texto de ayuda se ajusta al interior útil del pergamino para que no
    # se salga por los bordes en ninguna resolución.
    lineas = envolver_texto(
        "Elige la categoría que consideres correcta",
        recursos["fuente_panel"],
        320,
    )
    y = rect.y + 238
    for linea in lineas:
        detalle = recursos["fuente_panel"].render(linea, True, TINTA)
        superficie.blit(detalle, detalle.get_rect(center=(rect.centerx, y)))
        y += 22
    for boton in botones:
        boton.dibujar(superficie, mouse_pos)


def dibujar_resultado_evento(superficie, recursos, estado):
    """Compara la respuesta de trivia con la categoría real del árbol."""
    superficie.blit(recursos["fondo_tablilla"], (0, 0))
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
    progreso = 1 - animacion["restante"] / animacion["duracion"]
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
    superficie.blit(recursos["fondo_tablilla"], (0, 0))
    hud.dibujar(superficie)
    if animacion:
        dibujar_tablilla_en_efecto(superficie, recursos, estado, animacion)
    else:
        dibujar_tablilla(superficie, recursos["tablilla"], estado, recursos["fuente_texto"], recursos["fuente_categoria"])

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
    """La quema necesita tiempo suficiente para consumir toda la tablilla."""
    clave = clave_pocion(opcion)
    duracion = 1.65 if clave == "quemar" else 1.25
    return {"clave": clave, "opcion": opcion, "restante": duracion, "duracion": duracion}


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


def dibujar_escena_dialogo(
    superficie, recursos, dialogos, mouse_pos, hud, jugador=None, particulas=None, mundo=None
):
    """El diálogo se superpone al mapa y bloquea sus demás interacciones."""
    superficie.blit(recursos["mapas_dia"][recursos.get("dia", 0)], (0, 0))
    dibujar_cascada_animada(superficie, recursos)
    dibujar_decoraciones_editor(superficie, recursos)
    if jugador:
        if particulas:
            particulas.dibujar(superficie)
        dibujar_jugador(superficie, jugador)
    hud.dibujar(superficie)
    dialogos.dibujar(superficie, mouse_pos, ANCHO, ALTO)


def dibujar_escena_mensaje(
    superficie, recursos, mensajes, mouse_pos, hud, jugador=None, mundo=None
):
    """El pergamino se presenta sobre el mapa y bloquea las demás acciones."""
    superficie.blit(recursos["mapas_dia"][recursos.get("dia", 0)], (0, 0))
    dibujar_cascada_animada(superficie, recursos)
    dibujar_decoraciones_editor(superficie, recursos)
    if jugador:
        dibujar_jugador(superficie, jugador)
    hud.dibujar(superficie)
    mensajes.dibujar(superficie, mouse_pos)


def dibujar_interfaz_eco(
    superficie, recursos, jugador, estado_eco, contactos, mensajes, mundo=None
):
    superficie.blit(recursos["mapas_dia"][recursos.get("dia", 0)], (0, 0))
    dibujar_cascada_animada(superficie, recursos)
    dibujar_decoraciones_editor(superficie, recursos)
    dibujar_jugador(superficie, jugador)
    panel = pygame.Rect(190, 150, 580, 420)
    superficie.blit(superficie_con_alpha(panel.size, (17, 34, 28, 242)), panel.topleft)
    pygame.draw.rect(superficie, ORO, panel, 3, border_radius=14)
    frames_tronco = recursos.get("frames_tronco_eco", [])
    if frames_tronco:
        frame = frames_tronco[(pygame.time.get_ticks() // 140) % len(frames_tronco)]
        superficie.blit(pygame.transform.scale(frame, (64, 72)), (panel.right - 102, panel.y + 18))
    titulo = recursos["fuente_panel_titulo"].render("ECO DE TRONCOS", True, ORO)
    superficie.blit(titulo, titulo.get_rect(center=(panel.centerx, panel.y + 38)))
    if not contactos:
        lineas = ["No hay personajes disponibles en este mapa.", "Esc para volver."]
    elif estado_eco["respuesta"]:
        lineas = [
            f"Mensaje enviado a {contactos[estado_eco['destinatario']]}:",
            mensajes[estado_eco["mensaje"]][1],
            estado_eco["respuesta"],
            "Enter o Esc para volver.",
        ]
    else:
        destinatario = contactos[estado_eco["destinatario"]]
        mensaje = mensajes[estado_eco["mensaje"]][1]
        lineas = [
            f"Destinatario:  < {destinatario} >",
            f"Mensaje:  < {mensaje} >",
            "Arriba/abajo: destinatario | Izquierda/derecha: mensaje",
            "E o Enter: enviar | Esc: cancelar",
        ]
    # Los testimonios pueden ocupar varias líneas: ajustar dentro del panel.
    fuente = recursos["fuente_panel"]
    bloques = [envolver_texto(linea, fuente, panel.width - 56) for linea in lineas]
    alto = sum(len(bloque) * (fuente.get_linesize() + 3) + 10 for bloque in bloques)
    if alto > panel.height - 110:
        fuente = cargar_fuente(16)
        bloques = [envolver_texto(linea, fuente, panel.width - 56) for linea in lineas]
    y = panel.y + 100
    for bloque in bloques:
        for linea in bloque:
            texto = fuente.render(linea, True, CREMA)
            superficie.blit(texto, texto.get_rect(midtop=(panel.centerx, y)))
            y += fuente.get_linesize() + 3
        y += 10



def crear_fondo_tablilla(mapa):
    fondo = mapa.copy()
    velo = superficie_con_alpha((ANCHO, ALTO), (7, 18, 14, 178))
    fondo.blit(velo, (0, 0))
    return fondo


def crear_mundo(recursos):
    personajes = [
        {
            "id": f"personaje_{indice}_{objeto['personaje'].lower()}",
            "tipo": "personaje",
            "accion": "npc",
            "personaje": objeto["personaje"],
            "rect": objeto["hitbox"].copy(),
            "objeto": objeto,
            "activo": True,
            "distancia": DISTANCIA_INTERACCION,
        }
        for indice, objeto in enumerate(recursos["decoraciones"])
        if objeto["personaje"] and objeto["personaje"] != "Guardián"
    ]
    for interaccion in recursos["interacciones"]:
        if interaccion.get("accion") != "npc" or not interaccion.get("personaje"):
            continue
        if any(actor["personaje"] == interaccion["personaje"] for actor in personajes):
            continue
        personajes.append({
            "id": interaccion["id"],
            "tipo": "personaje",
            "accion": "npc",
            "personaje": interaccion["personaje"],
            "rect": interaccion["rect"],
            "activo": interaccion.get("activo", True),
            "distancia": DISTANCIA_INTERACCION,
        })
    mundo = {
        "decoraciones": recursos["decoraciones"],
        "interacciones": recursos["interacciones"],
        "hitboxes": recursos.get("hitboxes", []),
        "personajes": personajes,
        "jugador": crear_jugador_local(recursos),
        "grafo_fisico": crear_grafo_fisico(recursos["decoraciones"]),
    }
    ajustar_inicio_jugador(mundo["jugador"], mundo)
    mundo["posicion_casa"] = mundo["jugador"]["pies"].copy()
    mundo["interacciones_cercanas"] = []
    mundo["interaccion_seleccionada"] = None
    return mundo


def tamano_ventana_inicial():
    info = pygame.display.Info()
    max_ancho = max(640, int(info.current_w * 0.92))
    max_alto = max(480, int(info.current_h * 0.86))
    if max_ancho / max_alto > RELACION_ASPECTO:
        alto = max_alto
        ancho = int(alto * RELACION_ASPECTO)
    else:
        ancho = max_ancho
        alto = int(ancho / RELACION_ASPECTO)
    return ancho, alto


def crear_ventana(pantalla_completa, maximizada=False):
    """Crea ventana redimensionable o pantalla completa sin estirar el lienzo."""
    if pantalla_completa:
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pantalla = pygame.display.set_mode(tamano_ventana_inicial(), pygame.RESIZABLE)
    if maximizada:
        from pygame._sdl2 import Window

        Window.from_display_module().maximize()
    return pantalla


def rect_lienzo_en_ventana(tamano_ventana):
    # La interfaz ocupa el monitor completo.  La conversión del mouse usa los
    # dos ejes por separado, así que los botones mantienen sus hitboxes aunque
    # la relación del monitor sea distinta a la del lienzo base.
    return pygame.Rect((0, 0), tamano_ventana)


def convertir_mouse_a_lienzo(posicion, rect_lienzo):
    if not rect_lienzo.collidepoint(posicion):
        return (-1, -1)
    escala_x = ANCHO / rect_lienzo.width
    escala_y = ALTO / rect_lienzo.height
    x = int((posicion[0] - rect_lienzo.x) * escala_x)
    y = int((posicion[1] - rect_lienzo.y) * escala_y)
    return (x, y)


def presentar_lienzo(pantalla, lienzo):
    """Amplía el juego a toda la pantalla, sin bandas ni fondos auxiliares."""
    rect_destino = rect_lienzo_en_ventana(pantalla.get_size())
    escalado = pygame.transform.scale(lienzo, rect_destino.size)
    pantalla.blit(escalado, rect_destino)
    return rect_destino


def main():
    pygame.init()
    gestor_audio = GestorAudio(os.path.dirname(__file__))
    pantalla_completa = True
    ventana_maximizada = False
    pantalla = crear_ventana(pantalla_completa, ventana_maximizada)
    pygame.display.set_caption("La Copa: Voces en las Alturas")
    reloj = pygame.time.Clock()
    lienzo = pygame.Surface((ANCHO, ALTO))

    fuente_texto = cargar_fuente(22)
    fuente_categoria = cargar_fuente(13)
    fuente_boton = cargar_fuente(19)
    fuente_indicador = cargar_fuente(11)
    fuente_mapa = cargar_fuente(18)
    fuente_panel_titulo = cargar_fuente(16)
    fuente_panel = cargar_fuente(13)
    fuente_resultado = cargar_fuente(28)

    mapa, decoraciones, interacciones, hitboxes, guardian, mapas_dia = cargar_mapa_principal()
    retratos_dialogo = {
        objeto["personaje"]: pygame.transform.scale(objeto["imagen"], (78, 78))
        for objeto in decoraciones
        if objeto["personaje"]
    }
    recursos = {
        "mapa": mapa,
        "mapas_dia": mapas_dia,
        "frames_cascada": cargar_spritesheet_frames(
            os.path.join("Animaciones Ambiente", "Cascada_animación.png")
        ),
        "dia": 0,
        "decoraciones": decoraciones,
        "interacciones": interacciones,
        "hitboxes": hitboxes,
        "guardian": guardian,
        "guardian_walk_frames": {
            "abajo": cargar_spritesheet_frames(
                os.path.join("NPCS", "Guardian", "Fila 2. Guardián.png")
            ),
            "derecha": cargar_spritesheet_frames(
                os.path.join("NPCS", "Guardian", "Fila 3. Guardián.png")
            ),
            "arriba": cargar_spritesheet_frames(
                os.path.join("NPCS", "Guardian", "Fila 4. Guardián.png")
            ),
            "izquierda": cargar_spritesheet_frames(
                os.path.join("NPCS", "Guardian", "Fila 5. Guardián.png")
            ),
        },
        "guardian_idle_frames": cargar_frames_idle_guardian(),
        "frames_tronco_eco": cargar_frames_tronco_eco(),
        "guardian_talk_frames": cargar_spritesheet_frames(
            os.path.join("NPCS", "Guardian", "Guardian_hablando.png")
        ),
        "guardian_eco_frames": cargar_spritesheet_frames(
            os.path.join("NPCS", "Guardian", "Guardian_interaccion_ecos.png")
        ),
        "fondo_tablilla": crear_fondo_tablilla(mapa),
        "fondo_clasificacion": cargar_imagen("FondoClasificacion.png", (860, 505)),
        "tablilla": cargar_imagen("Tablilla.png", (460, 460)),
        "colgar": cargar_imagen("Colgar.png", (190, 127)),
        "consultar": cargar_imagen("Consultar.png", (190, 127)),
        "quemar": cargar_imagen("Quemar.png", (190, 127)),
        "ignorar": cargar_imagen("Ignorar.png", (190, 127)),
        "pergamino_mensaje": cargar_imagen("Mensaje_privado.png", (570, 410)),
        "pociones": {
            "colgar": cargar_imagen(os.path.join("Pociones", "pocion_amarilla.png"), (42, 42)),
            "consultar": cargar_imagen(os.path.join("Pociones", "pocion_azul.png"), (42, 42)),
            "quemar": cargar_imagen(os.path.join("Pociones", "pocion_roja.png"), (42, 42)),
            "ignorar": cargar_imagen(os.path.join("Pociones", "pocion_morada.png"), (42, 42)),
        },
        "efectos_decision": {
            "colgar": cargar_efecto_tablilla("Colgar_tablilla.png"),
            "consultar": cargar_efecto_tablilla("Consultar_tablilla.png"),
            "quemar": cargar_efecto_tablilla("Quemar_tablilla.png"),
            "ignorar": cargar_efecto_tablilla("Ignorar_tablilla.png"),
        },
        "final_positivo": cargar_imagen(os.path.join("Finales", "Final_positivo.jpeg"), (ANCHO, ALTO)),
        "final_negativo": cargar_imagen(os.path.join("Finales", "Game_over.jpeg"), (ANCHO, ALTO)),
        "fuente_texto": fuente_texto,
        "fuente_categoria": fuente_categoria,
        "fuente_boton": fuente_boton,
        "fuente_indicador": fuente_indicador,
        "fuente_mapa": fuente_mapa,
        "fuente_panel_titulo": fuente_panel_titulo,
        "fuente_panel": fuente_panel,
        "fuente_resultado": fuente_resultado,
    }

    iconos_hud = {
        "sabiduria": cargar_icono_hud("Barra_sabiduría.png"),
        "confianza_consejo": cargar_icono_hud("Barra_confianza.png"),
        "armonia": cargar_icono_hud("Barra_armonía.png"),
        "susurros_falsos": cargar_icono_hud("Barra_susurros_falsos.png"),
        "desinformación": cargar_icono_hud("Barra_desinformación.png"),
    }

    estado = EstadoJuego()
    mundo = crear_mundo(recursos)

    botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
    grupo_botones = GrupoBotones(botones)
    dialogos = ControladorDialogo(fuente_texto, fuente_panel_titulo, fuente_boton)
    mensajes = ControladorMensajePrivado(
        fuente_panel_titulo, fuente_panel, fuente_boton, recursos["pergamino_mensaje"]
    )
    hud = HUDIndicadores(fuente_indicador, iconos_hud)
    pausa = MenuModal(fuente_resultado, fuente_texto, fuente_boton)
    visual = MenuModal(fuente_resultado, fuente_texto, fuente_boton)
    volumen = MenuModal(fuente_resultado, fuente_texto, fuente_boton)
    volumen.conectar_audio(gestor_audio)
    volumen.configurar([("volver", "Volver")])
    ayuda = MenuModal(fuente_resultado, fuente_texto, fuente_boton)
    fondo_menu = cargar_imagen(os.path.join("Fondos", "Fondo_pausa.png"))
    for menu in (pausa, visual, volumen, ayuda):
        menu.establecer_fondo(fondo_menu, 0.6)

    def configurar_menu_visual():
        visual.configurar([
            ("modo_pantalla_completa", "Pantalla completa"),
            ("modo_ventana_maximizada", "Ventana maximizada"),
            ("modo_ventana_normal", "Ventana normal"),
            ("volver", "Volver"),
        ])
    conversaciones = {
        "Kael": {"personaje": "Kael", "texto": "Quiero conocer qué dicen los habitantes antes de responder.", "respuestas": []},
        "Mira": {"personaje": "Mira", "texto": "Guardián, circula un rumor sobre el Puente Norte.", "respuestas": []},
        "Tarek": {"personaje": "Tarek", "texto": "Escuché golpes extraños en el Tronco de Ecos.", "respuestas": []},
        "Luma": {"personaje": "Luma", "texto": "Algunas tablillas están llegando sin una fuente clara.", "respuestas": []},
        "Darek": {"personaje": "Darek", "texto": "Vi pasar un eco entre plataformas. Puede ayudarnos a seguir la ruta del rumor.", "respuestas": []},
        "Mensajero": {"personaje": "Mensajero", "texto": "Puedo llevar un mensaje privado entre plataformas. La ruta más corta no siempre es la más segura.", "respuestas": ["Entrega el mensaje"]},
        "Guardián": {"personaje": "Guardián", "texto": "Escucha a la aldea y revisa la tablilla antes de decidir qué hacer con ella.", "respuestas": ["Consultar tablilla"]},
        "Naira": {"personaje": "Naira", "texto": "Las plataformas están conectadas por puentes; cuidemos la confianza de quienes viven aquí.", "respuestas": ["Consultar tablilla"]},
        "Sabio de las Raíces": {
            "personaje": "Sabio de las Raíces",
            "texto": "Los ecos del tronco guardan lo que la aldea comparte. Escucha antes de decidir.",
            "respuestas": [],
        },
    }
    dialogos_posteriores = {
        nombre: {
            "personaje": nombre,
            "texto": f"{nombre} ya compartió lo que sabe por ahora.",
            "respuestas": [],
        }
        for nombre in conversaciones
    }
    estado_personajes = {
        personaje["personaje"]: {
            "dialogo_inicial": conversaciones.get(personaje["personaje"], {}),
            "dialogo_posterior": dialogos_posteriores.get(personaje["personaje"], {}),
            "dialogos_condicionados": {},
            "confianza": 0,
            "conversacion_vista": False,
            "disponible": personaje.get("activo", True),
            "plataforma_actual": personaje.get("plataforma", ""),
        }
        for personaje in mundo["personajes"]
    }
    conversaciones_vistas = set()
    personaje_dialogo_activo = None
    clave_dialogo_activo = None

    def plataforma_cercana(posicion):
        return min(
            mundo["grafo_fisico"].plataformas.values(),
            key=lambda plataforma: math.dist(
                posicion, _posicion_en_mapa(plataforma)
            ),
        )["id"]

    def registrar_transmision(transmisor, receptor, medio, origen_pos, destino_pos):
        propagacion = estado.propagacion_actual
        if propagacion is None:
            return None
        grafo = mundo["grafo_fisico"]
        origen_id = plataforma_cercana(origen_pos)
        destino_id = plataforma_cercana(destino_pos)
        ruta = grafo.buscar_camino(origen_id, destino_id)
        if ruta is None:
            raise RuntimeError(
                f"No existe ruta para la transmision entre {origen_id} y {destino_id}."
            )
        propagacion.registrar_transmision(
            transmisor,
            receptor,
            ruta,
            medio,
            origen_id,
            destino_id,
        )
        return ruta

    def difundir_resultado_tablilla():
        propagacion = estado.propagacion_actual
        resultado = estado.resultado_evento_actual()
        if not propagacion or not resultado:
            return
        camino = resultado.get("camino", [])
        if not camino:
            return

        accion = accion_tablilla(camino[0])
        texto_resultado = resultado.get("resultado", "")
        propagacion.registrar_decision(accion or camino[0], resultado=texto_resultado)
        texto_normalizado = normalizar_ruta(texto_resultado)
        if accion == "consultar":
            refutada = (
                camino[-1].casefold() == "no"
                or "exagerado" in texto_normalizado
                or "rumor falso" in texto_normalizado
                or "no es cierto" in texto_normalizado
            )
            confirmada = (
                camino[-1].casefold() == "si"
                or "verdad confirmada" in texto_normalizado
                or ("confirma" in texto_normalizado and not refutada)
            )
            if refutada or confirmada:
                propagacion.registrar_verificacion(confirmada and not refutada)
        elif accion == "ignorar":
            propagacion.marcar_como_rumor()
        elif accion == "colgar" and propagacion.tipo == "rumor":
            propagacion.marcar_como_rumor()

        if accion not in ("colgar", "consultar"):
            return
        origen = mundo["jugador"]["pies"].center
        for personaje in mundo["personajes"]:
            if not personaje.get("activo", True):
                continue
            registrar_transmision(
                "Guardián",
                personaje["personaje"],
                "tablilla",
                origen,
                personaje["rect"].center,
            )

    def abrir_dialogo_personaje(nombre):
        nonlocal personaje_dialogo_activo, clave_dialogo_activo
        personaje_dialogo_activo = nombre
        jugador = mundo["jugador"]
        jugador["en_movimiento"] = False
        jugador["estado_visual"] = "hablar"
        jugador["indice_frame"] = 0
        objetivo = next(
            (personaje for personaje in mundo["personajes"] if personaje["personaje"] == nombre),
            None,
        )
        estado_personajes.setdefault(nombre, {
            "dialogo_inicial": conversaciones.get(nombre, {}),
            "dialogo_posterior": dialogos_posteriores.get(nombre, {}),
            "dialogos_condicionados": {},
            "confianza": 0,
            "conversacion_vista": False,
            "disponible": True,
            "plataforma_actual": "",
        })
        if objetivo:
            jugador["direccion"] = (
                "izquierda" if objetivo["rect"].centerx < jugador["pies"].centerx else "derecha"
            )
        estado_personaje = estado_personajes.get(nombre, {})
        dialogo, clave_dialogo_activo = construir_conversacion(
            nombre, estado, conversaciones_vistas
        )
        dialogos.iniciar(dialogo, retratos_dialogo)
        if objetivo:
            registrar_transmision(
                nombre,
                "Guardián",
                "conversacion",
                objetivo["rect"].center,
                jugador["pies"].center,
            )

    def registrar_evento(evento):
            eventos_serializables.append(evento)
            print(f"[evento local] {json.dumps(evento, ensure_ascii=False)}")

    def abrir_caldero():
            if estado.evento_resuelto():
                escena_actual = ESCENA_RESULTADO if estado.evento_clasificado() else ESCENA_CONSECUENCIA
                return escena_actual
            opciones = estado.opciones_actuales()
            botones_locales = construir_botones(opciones, recursos, fuente_boton)
            botones.clear()
            botones.extend(botones_locales)
            grupo_botones.reemplazar(botones)
            return ESCENA_TABLILLA

    nombres_contacto = list(dict.fromkeys(
        personaje["personaje"]
        for personaje in mundo["personajes"]
        if personaje["personaje"] != "Guardián"
        and estado_personajes.get(personaje["personaje"], {}).get("disponible", True)
    ))
    mensajes_eco = construir_mensajes_eco(estado)
    eco_ui = {"destinatario": 0, "mensaje": 0, "respuesta": ""}
    eventos_serializables = []
    sistema_particulas = SistemaParticulas(ANCHO, ALTO)
    sistema_particulas.emitir(*CENTRO_CALDERO, 24)
    depuracion_activa = False
    tiempo_particulas_ambientales = 0
    estado_caldero_efectos = estado_caldero(estado)
    usos_pociones = {"colgar": 1, "consultar": 1, "quemar": 1, "ignorar": 1}
    pocion_animacion = None
    escena = ESCENA_MAPA
    escena_anterior = ESCENA_MAPA
    gestor_audio.al_cambiar_escena(None, escena)
    escena_audio_anterior = escena
    estado_caldero_anterior = estado_caldero(estado)
    estado_caldero_actual = estado_caldero_anterior
    interactuable_cercano, distancia_interactuable = buscar_interactuable_cercano(
        mundo["jugador"], mundo
    )

    corriendo = True
    cursor_actual = None
    while corriendo:
        delta_ms = reloj.tick(FPS)
        delta_segundos = delta_ms / 1000
        sistema_particulas.actualizar(delta_ms)
        tiempo_particulas_ambientales += delta_ms
        if tiempo_particulas_ambientales >= 850:
            tiempo_particulas_ambientales %= 850
            sistema_particulas.emitir(ANCHO // 2, ALTO // 2 - 32, 4)
            sistema_particulas.emitir(*CENTRO_CALDERO, 4)
        rect_lienzo = rect_lienzo_en_ventana(pantalla.get_size())
        mouse_pos = convertir_mouse_a_lienzo(pygame.mouse.get_pos(), rect_lienzo)

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                corriendo = False
            elif evento.type == pygame.VIDEORESIZE:
                if not pantalla_completa:
                    pantalla = pygame.display.set_mode(evento.size, pygame.RESIZABLE)
            elif evento.type == pygame.KEYDOWN and (
                evento.key == pygame.K_F11
                or (evento.key == pygame.K_RETURN and getattr(evento, "mod", 0) & pygame.KMOD_ALT)
            ):
                pantalla_completa = not pantalla_completa
                pantalla = crear_ventana(pantalla_completa, ventana_maximizada)
                if escena == ESCENA_VISUAL:
                    configurar_menu_visual()
            elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_F3:
                depuracion_activa = not depuracion_activa
            elif escena == ESCENA_ECO and evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    escena = ESCENA_MAPA
                    eco_ui["respuesta"] = ""
                    mundo["jugador"]["estado_visual"] = "idle"
                elif eco_ui["respuesta"] and evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    escena = ESCENA_MAPA
                    eco_ui["respuesta"] = ""
                    mundo["jugador"]["estado_visual"] = "idle"
                elif not eco_ui["respuesta"] and nombres_contacto:
                    if evento.key in (pygame.K_UP, pygame.K_DOWN):
                        paso = -1 if evento.key == pygame.K_UP else 1
                        eco_ui["destinatario"] = (eco_ui["destinatario"] + paso) % len(nombres_contacto)
                    elif evento.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        paso = -1 if evento.key == pygame.K_LEFT else 1
                        eco_ui["mensaje"] = (eco_ui["mensaje"] + paso) % len(mensajes_eco)
                    elif evento.key in (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER):
                        tronco = interactuable_cercano
                        receptor = nombres_contacto[eco_ui["destinatario"]]
                        mensaje_id, texto_mensaje = mensajes_eco[eco_ui["mensaje"]]
                        registrar_evento({
                            "tipo": "eco_tronco",
                            "emisor_id": mundo["jugador"]["id"],
                            "receptor_id": receptor.lower().replace(" ", "_"),
                            "mensaje_id": mensaje_id,
                            "tronco_origen_id": tronco.get("id", "eco_tronco"),
                            "timestamp": pygame.time.get_ticks(),
                        })
                        destino = next(
                            persona for persona in mundo["personajes"]
                            if persona["personaje"] == receptor
                        )
                        registrar_transmision(
                            "Guardián",
                            receptor,
                            "eco",
                            mundo["jugador"]["pies"].center,
                            destino["rect"].center,
                        )
                        eco_ui["respuesta"] = construir_respuesta_eco(receptor, mensaje_id, estado)
                        sistema_particulas.emitir(480, 380, 12)
            elif escena in (
                ESCENA_TABLILLA, ESCENA_CONSECUENCIA, ESCENA_CLASIFICACION, ESCENA_RESULTADO
            ) and evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                if escena != ESCENA_TABLILLA and estado.evento_resuelto():
                    reiniciar_jugador_en_casa(mundo)
                escena = ESCENA_MAPA
            elif escena == ESCENA_PAUSA:
                accion = pausa.manejar_evento(
                    evento, convertir_mouse_a_lienzo(getattr(evento, "pos", pygame.mouse.get_pos()), rect_lienzo)
                )
                if accion in ("continuar", "volver"):
                    escena = escena_anterior
                elif accion == "ayuda":
                    ayuda.configurar([("volver", "Volver")])
                    escena = ESCENA_AYUDA
                elif accion == "visual":
                    configurar_menu_visual()
                    escena = ESCENA_VISUAL
                elif accion == "volumen":
                    escena = ESCENA_VOLUMEN
                elif accion == "salir":
                    corriendo = False
            elif escena == ESCENA_VISUAL:
                accion = visual.manejar_evento(
                    evento,
                    convertir_mouse_a_lienzo(
                        getattr(evento, "pos", pygame.mouse.get_pos()), rect_lienzo
                    ),
                )
                if accion == "modo_pantalla_completa":
                    pantalla_completa = True
                    pantalla = crear_ventana(pantalla_completa, ventana_maximizada)
                    configurar_menu_visual()
                elif accion == "modo_ventana_maximizada":
                    pantalla_completa = False
                    ventana_maximizada = True
                    pantalla = crear_ventana(pantalla_completa, ventana_maximizada)
                    configurar_menu_visual()
                elif accion == "modo_ventana_normal":
                    pantalla_completa = False
                    ventana_maximizada = False
                    pantalla = crear_ventana(pantalla_completa, ventana_maximizada)
                    configurar_menu_visual()
                elif accion == "volver":
                    escena = ESCENA_PAUSA
            elif escena == ESCENA_VOLUMEN:
                accion = volumen.manejar_evento(
                    evento, convertir_mouse_a_lienzo(getattr(evento, "pos", pygame.mouse.get_pos()), rect_lienzo)
                )
                if accion == "volver":
                    escena = ESCENA_PAUSA
            elif escena == ESCENA_AYUDA:
                accion = ayuda.manejar_evento(
                    evento, convertir_mouse_a_lienzo(getattr(evento, "pos", pygame.mouse.get_pos()), rect_lienzo)
                )
                if accion:
                    escena = ESCENA_PAUSA
            elif escena == ESCENA_DIALOGO:
                resultado_dialogo = dialogos.manejar_evento(
                    evento, convertir_mouse_a_lienzo(getattr(evento, "pos", pygame.mouse.get_pos()), rect_lienzo)
                )
                if resultado_dialogo:
                    tipo, respuesta = resultado_dialogo
                    personaje_que_respondio = personaje_dialogo_activo
                    if personaje_dialogo_activo:
                        conversaciones_vistas.add(clave_dialogo_activo)
                        if personaje_dialogo_activo in estado_personajes:
                            estado_personajes[personaje_dialogo_activo]["conversacion_vista"] = True
                        personaje_dialogo_activo = None
                    mundo["jugador"]["estado_visual"] = "idle"
                    if tipo == "respuesta" and respuesta in ("Te ayudaré", "Entrega el mensaje"):
                        mensajero = next(
                            (
                                persona for persona in mundo["personajes"]
                                if persona["personaje"] == "Mensajero"
                            ),
                            None,
                        )
                        if mensajero and personaje_que_respondio == "Mensajero":
                            registrar_transmision(
                                "Mensajero",
                                "Guardián",
                                "mensajero",
                                mensajero["rect"].center,
                                mundo["jugador"]["pies"].center,
                            )
                        mensajes.abrir({
                            "remitente": "Sabio de las Raíces",
                            "destinatario": "Guardián",
                            "texto": "El puente norte necesita una revisión. Consulta a quienes vieron el rayo antes de compartir la tablilla.",
                        })
                        escena = ESCENA_MENSAJE
                    elif tipo == "respuesta" and respuesta == "Consultar tablilla":
                        botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
                        grupo_botones.reemplazar(botones)
                        escena = ESCENA_TABLILLA
                    else:
                        escena = ESCENA_MAPA
            elif escena == ESCENA_MENSAJE:
                if mensajes.manejar_evento(
                    evento, convertir_mouse_a_lienzo(getattr(evento, "pos", pygame.mouse.get_pos()), rect_lienzo)
                ):
                    escena = ESCENA_MAPA
            elif escena == ESCENA_FINAL:
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_r:
                    estado = EstadoJuego()
                    recursos["dia"] = 0
                    conversaciones_vistas.clear()
                    clave_dialogo_activo = None
                    estado_caldero_anterior = estado_caldero_actual
                    estado_caldero_actual = sincronizar_audio_caldero(
                        gestor_audio, estado, estado_caldero_anterior
                    )
                    mundo = crear_mundo(recursos)
                    botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
                    grupo_botones.reemplazar(botones)
                    usos_pociones = {"colgar": 1, "consultar": 1, "quemar": 1, "ignorar": 1}
                    pocion_animacion = None
                    escena = ESCENA_MAPA
                elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                    corriendo = False
            elif escena == ESCENA_MAPA_DESTINO:
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                    escena = ESCENA_MAPA
                elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    escena = ESCENA_MAPA
            elif escena == ESCENA_MAPA and evento.type == pygame.KEYDOWN and evento.key == pygame.K_e:
                if interactuable_cercano:
                    jugador = mundo["jugador"]
                    jugador["en_movimiento"] = False
                    jugador["estado_visual"] = "idle"
                    accion = interactuable_cercano.get("accion")
                    if accion == "npc":
                        abrir_dialogo_personaje(interactuable_cercano["personaje"])
                        registrar_evento({
                            "tipo": "interaccion_personaje",
                            "actor_id": jugador["id"],
                            "objetivo_id": interactuable_cercano["personaje"].lower().replace(" ", "_"),
                        })
                        sistema_particulas.emitir(jugador["pies"].centerx, jugador["pies"].centery, 6)
                        escena = ESCENA_DIALOGO
                    elif accion == "tablilla":
                        registrar_evento({"tipo": "usar_caldero", "actor_id": jugador["id"]})
                        sistema_particulas.emitir(*CENTRO_CALDERO, 14)
                        escena = abrir_caldero()
                    elif accion == "usar_eco_tronco":
                        mensajes_eco = construir_mensajes_eco(estado)
                        eco_ui.update({"destinatario": 0, "mensaje": 0, "respuesta": ""})
                        jugador["estado_visual"] = "usar_eco"
                        jugador["indice_frame"] = 0
                        registrar_evento({
                            "tipo": "usar_eco_tronco",
                            "actor_id": jugador["id"],
                            "objeto_id": interactuable_cercano.get("id", "eco_tronco"),
                        })
                        escena = ESCENA_ECO
                    elif accion == "puerta":
                        destino = interactuable_cercano.get("imagen_destino")
                        if destino:
                            recursos["mapa_destino"] = destino
                            escena = ESCENA_MAPA_DESTINO
                    elif accion == "otro":
                        registrar_evento({
                            "tipo": "interaccion_otro",
                            "actor_id": jugador["id"],
                            "objeto_id": interactuable_cercano.get("id", "otro"),
                        })
                        sistema_particulas.emitir(
                            *interactuable_cercano["rect"].center, 6
                        )
            elif escena == ESCENA_MAPA and evento.type == pygame.KEYDOWN and evento.key == pygame.K_TAB:
                alternar_interactuable_cercano(mundo)
            elif evento.type == pygame.KEYDOWN and evento.key in (pygame.K_ESCAPE, pygame.K_p):
                escena_anterior = escena
                pausa.configurar([
                    ("continuar", "Continuar"),
                    ("visual", "Visual"),
                    ("ayuda", "Ayuda"),
                    ("volumen", "Volumen"),
                    ("salir", "Salir"),
                ])
                escena = ESCENA_PAUSA
            elif escena == ESCENA_MAPA and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                posicion = convertir_mouse_a_lienzo(evento.pos, rect_lienzo)
                interaccion = interaccion_en_mapa(posicion, mundo)
                if (
                    interaccion
                    and interaccion["accion"] == "tablilla"
                    and any(
                        objeto.get("accion") == "tablilla"
                        for _, objeto in mundo.get("interacciones_cercanas", [])
                    )
                ):
                    registrar_evento({"tipo": "usar_caldero", "actor_id": mundo["jugador"]["id"]})
                    escena = abrir_caldero()
                elif interaccion and interaccion["accion"] == "npc":
                    abrir_dialogo_personaje(interaccion["personaje"])
                    registrar_evento({
                        "tipo": "interaccion_personaje",
                        "actor_id": mundo["jugador"]["id"],
                        "objetivo_id": interaccion["personaje"].lower().replace(" ", "_"),
                    })
                    escena = ESCENA_DIALOGO
                elif interaccion and interaccion["accion"] == "puerta":
                    recursos["mapa_destino"] = interaccion["imagen_destino"]
                    escena = ESCENA_MAPA_DESTINO
                elif interaccion and interaccion["accion"] == "otro":
                    registrar_evento({
                        "tipo": "interaccion_otro",
                        "actor_id": mundo["jugador"]["id"],
                        "objeto_id": interaccion.get("id", "otro"),
                    })
                    sistema_particulas.emitir(*interaccion["rect"].center, 6)
            elif evento.type == pygame.KEYDOWN:
                opcion_teclado = grupo_botones.manejar_teclado(evento)
                if opcion_teclado and escena == ESCENA_CLASIFICACION:
                    estado.clasificar_evento(opcion_teclado)
                    reproducir_audio_clasificacion(gestor_audio, estado)
                    estado_caldero_anterior = estado_caldero_actual
                    estado_caldero_actual = sincronizar_audio_caldero(
                        gestor_audio, estado, estado_caldero_anterior
                    )
                    botones = []
                    grupo_botones.reemplazar(botones)
                    escena = ESCENA_RESULTADO
                elif opcion_teclado and escena == ESCENA_TABLILLA:
                    pocion_animacion = iniciar_animacion_decision(opcion_teclado)
            elif escena == ESCENA_RESULTADO and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                estado.continuar_despues_resultado()
                recursos["dia"] = estado.dia
                reiniciar_jugador_en_casa(mundo)
                botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
                grupo_botones.reemplazar(botones)
                if estado.juego_terminado():
                    escena = ESCENA_FINAL
                else:
                    escena = ESCENA_MAPA
            elif escena == ESCENA_CONSECUENCIA and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                botones = construir_botones(estado.opciones_clasificacion_actuales(), recursos, fuente_boton)
                grupo_botones.reemplazar(botones)
                escena = ESCENA_CLASIFICACION
            elif escena == ESCENA_CLASIFICACION and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                pos_lienzo = convertir_mouse_a_lienzo(evento.pos, rect_lienzo)
                for boton in botones:
                    if boton.fue_clickeado(pos_lienzo):
                        estado.clasificar_evento(boton.texto)
                        reproducir_audio_clasificacion(gestor_audio, estado)
                        estado_caldero_anterior = estado_caldero_actual
                        estado_caldero_actual = sincronizar_audio_caldero(
                            gestor_audio, estado, estado_caldero_anterior
                        )
                        botones = []
                        grupo_botones.reemplazar(botones)
                        escena = ESCENA_RESULTADO
                        break
            elif escena == ESCENA_TABLILLA and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                pos_lienzo = convertir_mouse_a_lienzo(evento.pos, rect_lienzo)
                if not pocion_animacion:
                    for boton in botones:
                        if boton.fue_clickeado(pos_lienzo):
                            pocion_animacion = iniciar_animacion_decision(boton.texto)
                            break

        jugador = mundo["jugador"]
        if escena == ESCENA_MAPA:
            mover_jugador(jugador, mundo, pygame.key.get_pressed(), delta_ms)
        elif jugador["estado_visual"] in ("hablar", "usar_eco"):
            frames_estado = (
                jugador["frames_eco"]
                if jugador["estado_visual"] == "usar_eco"
                else jugador["frames_hablar"]
            )
            jugador["tiempo_animacion"] += delta_ms
            while jugador["tiempo_animacion"] >= 150:
                jugador["tiempo_animacion"] -= 150
                if frames_estado:
                    jugador["indice_frame"] = (jugador["indice_frame"] + 1) % len(frames_estado)
        interactuable_cercano, distancia_interactuable = buscar_interactuable_cercano(
            jugador, mundo
        )

        hud.actualizar(estado.indicadores, delta_segundos)

        if pocion_animacion:
            pocion_animacion["restante"] -= delta_segundos
            if pocion_animacion["restante"] <= 0:
                opcion = pocion_animacion["opcion"]
                if opcion in estado.opciones_actuales():
                    estado.elegir_opcion(opcion)
                    accion = accion_tablilla(opcion)
                    if accion:
                        gestor_audio.procesar_evento({
                            "tipo": "decision_tablilla",
                            "accion": accion,
                        })
                        if accion == "consultar":
                            sistema_particulas.emitir(*CENTRO_CALDERO, 12)
                    if estado.evento_resuelto():
                        difundir_resultado_tablilla()
                    estado_caldero_anterior = estado_caldero_actual
                    estado_caldero_actual = sincronizar_audio_caldero(
                        gestor_audio, estado, estado_caldero_anterior
                    )
                botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
                grupo_botones.reemplazar(botones)
                pocion_animacion = None
                if estado.evento_resuelto():
                    escena = ESCENA_CONSECUENCIA

        if escena != escena_audio_anterior:
            resultado_audio = determinar_resultado_final(estado) if escena == ESCENA_FINAL else None
            gestor_audio.al_cambiar_escena(escena_audio_anterior, escena, resultado_audio)
            escena_audio_anterior = escena
            if escena == ESCENA_FINAL:
                sistema_particulas.emitir(*CENTRO_CALDERO, 24)
        nuevo_estado_caldero_efectos = estado_caldero(estado)
        if nuevo_estado_caldero_efectos != estado_caldero_efectos:
            if nuevo_estado_caldero_efectos == "critico":
                sistema_particulas.emitir(*CENTRO_CALDERO, 20)
            estado_caldero_efectos = nuevo_estado_caldero_efectos
        if escena not in (ESCENA_PAUSA, ESCENA_VISUAL, ESCENA_AYUDA, ESCENA_VOLUMEN):
            gestor_audio.actualizar()

        cursor_deseado = (pygame.SYSTEM_CURSOR_HAND
                          if escena == ESCENA_MAPA and interaccion_en_mapa(mouse_pos, mundo)
                          else pygame.SYSTEM_CURSOR_ARROW)
        if cursor_deseado != cursor_actual:
            pygame.mouse.set_cursor(cursor_deseado)
            cursor_actual = cursor_deseado

        if escena == ESCENA_MAPA:
            dibujar_mapa(
                lienzo, recursos, mundo, estado, mouse_pos, hud,
                interactuable_cercano, distancia_interactuable,
                sistema_particulas, depuracion_activa,
            )
        elif escena == ESCENA_PAUSA:
            dibujar_mapa(lienzo, recursos, mundo, estado, mouse_pos, hud, resaltar=False)
            pausa.dibujar(
                lienzo,
                "PAUSA",
                ["La Red de Ecos espera tu decisión.", "ESC o P: continuar"],
                mouse_pos,
            )
        elif escena == ESCENA_VISUAL:
            dibujar_mapa(lienzo, recursos, mundo, estado, mouse_pos, hud, resaltar=False)
            modo_actual = (
                "Pantalla completa" if pantalla_completa
                else "Ventana maximizada" if ventana_maximizada
                else "Ventana normal"
            )
            visual.dibujar(
                lienzo,
                "VISUAL",
                [f"Modo actual: {modo_actual}. Selecciona una opcion."],
                mouse_pos,
            )
        elif escena == ESCENA_VOLUMEN:
            dibujar_mapa(lienzo, recursos, mundo, estado, mouse_pos, hud, resaltar=False)
            volumen.dibujar(lienzo, "VOLUMEN", ["Ajusta la música y los efectos de sonido."], mouse_pos)
        elif escena == ESCENA_AYUDA:
            dibujar_mapa(lienzo, recursos, mundo, estado, mouse_pos, hud, resaltar=False)
            ayuda.dibujar(
                lienzo,
                "AYUDA",
                [
                    "Acércate al Caldero y pulsa E para abrir la tablilla; Tab alterna interacciones cercanas.",
                    "Clic en los personajes: conversar y reunir testimonios.",
                    "Clic en la salida derecha: visitar la zona Central; clic o Esc para volver.",
                    "Tablillas: decide si colgar, consultar, quemar o ignorar.",
                    "Ecos y Mensajero: comparten pistas entre plataformas.",
                    "Pócimas: anticipan consecuencias; úsalas con cuidado.",
                    "Mantén Sabiduría, Confianza y Armonía saludables.",
                    "Evita que Susurros Falsos y Desinformación crezcan.",
                ],
                mouse_pos,
            )
        elif escena == ESCENA_DIALOGO:
            dialogos.actualizar(delta_segundos)
            dibujar_escena_dialogo(
                lienzo, recursos, dialogos, mouse_pos, hud,
                mundo["jugador"], sistema_particulas, mundo,
            )
        elif escena == ESCENA_MENSAJE:
            mensajes.actualizar(delta_segundos)
            dibujar_escena_mensaje(
                lienzo, recursos, mensajes, mouse_pos, hud, mundo["jugador"], mundo
            )
        elif escena == ESCENA_ECO:
            dibujar_interfaz_eco(
                lienzo, recursos, mundo["jugador"], eco_ui, nombres_contacto, mensajes_eco, mundo
            )
        elif escena == ESCENA_MAPA_DESTINO:
            lienzo.blit(recursos["mapa_destino"], (0, 0))
            dibujar_mensaje_mapa(
                lienzo,
                recursos["fuente_mapa"],
                "Zona Central. Haz clic o pulsa Esc para volver al mapa principal.",
            )
        elif escena == ESCENA_CONSECUENCIA:
            dibujar_consecuencia_evento(lienzo, recursos, estado)
        elif escena == ESCENA_CLASIFICACION:
            dibujar_pregunta_clasificacion(lienzo, recursos, botones, mouse_pos)
        elif escena == ESCENA_RESULTADO:
            dibujar_resultado_evento(lienzo, recursos, estado)
        elif escena == ESCENA_FINAL:
            dibujar_final(lienzo, recursos, estado)
        else:
            dibujar_escena_tablilla(lienzo, recursos, estado, botones, mouse_pos, hud, pocion_animacion)
            dibujar_pociones(lienzo, recursos, usos_pociones, pocion_animacion, mouse_pos)

        presentar_lienzo(pantalla, lienzo)
        pygame.display.flip()
    gestor_audio.detener_todo()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
