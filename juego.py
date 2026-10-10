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
from interfaz.boton import Boton, GrupoBotones
from interfaz.dialogo import ControladorDialogo
from interfaz.hud import HUDIndicadores
from interfaz.menu import MenuModal
from interfaz.mensaje_privado import ControladorMensajePrivado
from logica_juego import EstadoJuego

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
ESCENA_AYUDA = "ayuda"
CENTRO_TABLILLA = (ANCHO // 2, 330)
CENTRO_TABLILLA_CENTRADA = (ANCHO // 2, 330)
CENTRO_CALDERO = (ANCHO // 2, 380)
HITBOX_CALDERO = pygame.Rect(CENTRO_CALDERO[0] - 52, CENTRO_CALDERO[1] - 48, 104, 96)


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
    if "/naira/" in ruta:
        return "Naira"
    if "aspirante hombre" in ruta:
        return "Kael"
    return None


def cargar_mapa_principal():
    """Carga el fondo y las capas interactivas definidas por el editor."""
    ruta_hitboxes = os.path.join(
        os.path.dirname(__file__),
        "Hitboxes",
        "Mapas",
        "Pr1SinP(Espacio)_hitboxes.json",
    )
    with open(ruta_hitboxes, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)

    mapa = cargar_imagen(os.path.join("Fondos", "Mapas", "Pr1SinP(Espacio).png"), (ANCHO, ALTO))
    decoraciones = []
    for objeto in datos.get("decoracion", []):
        imagen = cargar_imagen(objeto["name"])
        recorte = objeto.get("crop")
        if recorte:
            x = max(0, min(imagen.get_width() - 1, round(recorte["x"] * imagen.get_width())))
            y = max(0, min(imagen.get_height() - 1, round(recorte["y"] * imagen.get_height())))
            ancho = max(1, min(imagen.get_width() - x, round(recorte["w"] * imagen.get_width())))
            alto = max(1, min(imagen.get_height() - y, round(recorte["h"] * imagen.get_height())))
            imagen = imagen.subsurface((x, y, ancho, alto)).copy()

        rect = pygame.Rect(
            round(objeto["x"] * ANCHO),
            round(objeto["y"] * ALTO),
            max(1, round(objeto["w"] * ANCHO)),
            max(1, round(objeto["h"] * ALTO)),
        )
        imagen = pygame.transform.scale(imagen, rect.size)
        personaje = personaje_de_decoracion(objeto["name"])
        hitbox = rect.copy()
        if personaje == "Guardián":
            hitbox.inflate_ip(-round(rect.width * 0.4), -round(rect.height * 0.4))
        decoraciones.append({
            "nombre": objeto["name"],
            "personaje": personaje,
            "rect": rect,
            "hitbox": hitbox,
            "imagen": imagen,
            "puente": normalizar_ruta(objeto["name"]).startswith("puentes/"),
        })

    decoraciones.sort(key=lambda objeto: objeto["puente"], reverse=True)
    for objeto in decoraciones:
        mapa.blit(objeto["imagen"], objeto["rect"])

    interacciones = []
    for hitbox in datos.get("hitboxes", []):
        if hitbox.get("role") != "interactable":
            continue
        if hitbox.get("type", "rect") == "rect":
            rect = pygame.Rect(
                round(hitbox["rx"] * ANCHO),
                round(hitbox["ry"] * ALTO),
                max(1, round(hitbox["rw"] * ANCHO)),
                max(1, round(hitbox["rh"] * ALTO)),
            )
        else:
            continue
        interaccion = {
            "rect": rect,
            "accion": hitbox.get("action"),
            "destino": hitbox.get("target_image"),
        }
        if interaccion["accion"] == "puerta" and interaccion["destino"]:
            interaccion["imagen_destino"] = cargar_imagen(interaccion["destino"], (ANCHO, ALTO))
        interacciones.append(interaccion)

    return mapa, decoraciones, interacciones


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


def cargar_frame_caldero(nombre, indice=1):
    """Extrae un solo fotograma del spritesheet horizontal del Caldero."""
    spritesheet = cargar_imagen(nombre)
    ancho_frame = spritesheet.get_width() // 4
    area = pygame.Rect(ancho_frame * indice, 0, ancho_frame, spritesheet.get_height())
    return pygame.transform.scale(spritesheet.subsurface(area).copy(), (72, 72))


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
    if HITBOX_CALDERO.collidepoint(posicion):
        return {"accion": "tablilla", "rect": HITBOX_CALDERO}

    for objeto in reversed(mundo["decoraciones"]):
        if objeto["personaje"] and objeto["hitbox"].collidepoint(posicion):
            return {
                "accion": "npc",
                "personaje": objeto["personaje"],
                "rect": objeto["hitbox"],
            }

    for interaccion in mundo["interacciones"]:
        if interaccion["rect"].collidepoint(posicion):
            return interaccion
    return None


def dibujar_mapa(superficie, recursos, mundo, estado, mouse_pos, hud):
    superficie.blit(recursos["mapa"], (0, 0))

    # El Caldero expresa visualmente la salud informativa de la aldea.
    desinformacion = estado.indicadores["desinformación"] + estado.indicadores["susurros_falsos"]
    positivos = sum(estado.indicadores[nombre] for nombre in ("sabiduria", "confianza_consejo", "armonia")) / 3
    indice_caldero = 3 if desinformacion >= 100 else 2 if desinformacion >= 55 else 0 if positivos >= 65 else 1
    caldero = recursos["calderos"][indice_caldero]
    superficie.blit(caldero, caldero.get_rect(center=CENTRO_CALDERO))

    hud.dibujar(superficie)
    interaccion = interaccion_en_mapa(mouse_pos, mundo)
    if interaccion:
        pygame.draw.rect(superficie, ORO, interaccion["rect"], width=2, border_radius=5)
        if interaccion["accion"] == "npc":
            texto = f"Clic para hablar con {interaccion['personaje']}"
        elif interaccion["accion"] == "tablilla":
            texto = "Clic en el Caldero para abrir la tablilla"
        else:
            texto = "Clic para viajar al mapa Central"
    else:
        texto = "Haz clic en el Caldero para consultar una tablilla o en un personaje para hablar."
    dibujar_mensaje_mapa(superficie, recursos["fuente_mapa"], texto)


def buscar_imagen_para_opcion(texto, imagenes):
    texto = texto.lower()
    if "colgar" in texto:
        return imagenes["colgar"]
    if "consultar" in texto:
        return imagenes["consultar"]
    if "quemar" in texto:
        return imagenes["quemar"]
    # Ignorar se representa como botón de texto: su recurso de imagen es una
    # lámina de sprites y no un botón individual.
    if "ignorar" in texto:
        return None
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
    superficie.blit(recursos["mapa"], (0, 0))
    velo = superficie_con_alpha((ANCHO, ALTO), (6, 18, 12, 94))
    superficie.blit(velo, (0, 0))
    superficie.blit(ilustracion, ilustracion.get_rect(center=(ANCHO // 2, 347)))
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


def dibujar_escena_dialogo(superficie, recursos, dialogos, mouse_pos, hud):
    """El diálogo se superpone al mapa y bloquea sus demás interacciones."""
    superficie.blit(recursos["mapa"], (0, 0))
    hud.dibujar(superficie)
    dialogos.dibujar(superficie, mouse_pos, ANCHO, ALTO)


def dibujar_escena_mensaje(superficie, recursos, mensajes, mouse_pos, hud):
    """El pergamino se presenta sobre el mapa y bloquea las demás acciones."""
    superficie.blit(recursos["mapa"], (0, 0))
    hud.dibujar(superficie)
    mensajes.dibujar(superficie, mouse_pos)


def crear_fondo_tablilla(mapa):
    fondo = mapa.copy()
    velo = superficie_con_alpha((ANCHO, ALTO), (7, 18, 14, 178))
    fondo.blit(velo, (0, 0))
    return fondo


def crear_mundo(recursos):
    return {
        "decoraciones": recursos["decoraciones"],
        "interacciones": recursos["interacciones"],
    }


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


def crear_ventana(pantalla_completa):
    """Crea ventana redimensionable o pantalla completa sin estirar el lienzo."""
    if pantalla_completa:
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    return pygame.display.set_mode(tamano_ventana_inicial(), pygame.RESIZABLE)


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
    pantalla = crear_ventana(pantalla_completa)
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

    mapa, decoraciones, interacciones = cargar_mapa_principal()
    retratos_dialogo = {
        objeto["personaje"]: pygame.transform.scale(objeto["imagen"], (78, 78))
        for objeto in decoraciones
        if objeto["personaje"]
    }
    recursos = {
        "mapa": mapa,
        "decoraciones": decoraciones,
        "interacciones": interacciones,
        "fondo_tablilla": crear_fondo_tablilla(mapa),
        "fondo_clasificacion": cargar_imagen("FondoClasificacion.png", (860, 505)),
        "tablilla": cargar_imagen("Tablilla.png", (460, 460)),
        "colgar": cargar_imagen("Colgar.png", (190, 127)),
        "consultar": cargar_imagen("Consultar.png", (190, 127)),
        "quemar": cargar_imagen("Quemar.png", (190, 127)),
        "pergamino_mensaje": cargar_imagen("Mensaje_privado.png", (570, 410)),
        "calderos": [
            pygame.transform.scale(
                cargar_frame_caldero(os.path.join("Caldero", f"Caldero-ecos-fila{indice}.png")),
                (52, 52),
            )
            for indice in range(1, 5)
        ],
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
        "final_positivo": cargar_imagen(os.path.join("Finales", "Final_positivo.jpeg"), (520, 293)),
        "final_negativo": cargar_imagen(os.path.join("Finales", "Game_over.jpeg"), (520, 293)),
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
    ayuda = MenuModal(fuente_resultado, fuente_texto, fuente_boton)
    conversaciones = {
        "Kael": {"personaje": "Kael", "texto": "Algunos quieren cerrar el puente norte, pero primero debemos comprobar qué ocurrió.", "respuestas": ["Consultar tablilla"]},
        "Mira": {"personaje": "Mira", "texto": "Escuché un rumor sobre el puente norte. Antes de compartirlo, necesitamos pruebas.", "respuestas": ["Te ayudaré", "Necesito más pruebas"]},
        "Tarek": {"personaje": "Tarek", "texto": "Yo vi el rayo cerca del Mirador Alto. No escuché que el puente se hubiera cerrado.", "respuestas": ["Gracias por tu testimonio"]},
        "Luma": {"personaje": "Luma", "texto": "Los Ecos de Troncos repiten la noticia muy rápido. Una tablilla sin verificar puede confundir a toda la aldea.", "respuestas": ["Lo tendré en cuenta"]},
        "Mensajero": {"personaje": "Mensajero", "texto": "Puedo llevar un mensaje privado entre plataformas. La ruta más corta no siempre es la más segura.", "respuestas": ["Entrega el mensaje"]},
        "Guardián": {"personaje": "Guardián", "texto": "Escucha a la aldea y revisa la tablilla antes de decidir qué hacer con ella.", "respuestas": ["Consultar tablilla"]},
        "Naira": {"personaje": "Naira", "texto": "Las plataformas están conectadas por puentes; cuidemos la confianza de quienes viven aquí.", "respuestas": ["Consultar tablilla"]},
    }
    usos_pociones = {"colgar": 1, "consultar": 1, "quemar": 1, "ignorar": 1}
    pocion_animacion = None
    escena = ESCENA_MAPA
    escena_anterior = ESCENA_MAPA
    gestor_audio.al_cambiar_escena(None, escena)
    escena_audio_anterior = escena
    estado_caldero_anterior = estado_caldero(estado)
    estado_caldero_actual = estado_caldero_anterior

    corriendo = True
    while corriendo:
        delta_ms = reloj.tick(FPS)
        delta_segundos = delta_ms / 1000
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
                pantalla = crear_ventana(pantalla_completa)
            elif escena == ESCENA_PAUSA:
                accion = pausa.manejar_evento(
                    evento, convertir_mouse_a_lienzo(getattr(evento, "pos", pygame.mouse.get_pos()), rect_lienzo)
                )
                if accion in ("continuar", "volver"):
                    escena = escena_anterior
                elif accion == "ayuda":
                    ayuda.configurar([("volver", "Volver")])
                    escena = ESCENA_AYUDA
                elif accion == "salir":
                    corriendo = False
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
                    if tipo == "respuesta" and respuesta in ("Te ayudaré", "Entrega el mensaje"):
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
            elif evento.type == pygame.KEYDOWN and evento.key in (pygame.K_ESCAPE, pygame.K_p):
                escena_anterior = escena
                pausa.configurar([
                    ("continuar", "Continuar"),
                    ("ayuda", "Ayuda"),
                    ("salir", "Salir"),
                ])
                escena = ESCENA_PAUSA
            elif escena == ESCENA_MAPA and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                posicion = convertir_mouse_a_lienzo(evento.pos, rect_lienzo)
                interaccion = interaccion_en_mapa(posicion, mundo)
                if interaccion and interaccion["accion"] == "tablilla":
                    botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
                    grupo_botones.reemplazar(botones)
                    escena = ESCENA_TABLILLA
                elif interaccion and interaccion["accion"] == "npc":
                    dialogos.iniciar(conversaciones[interaccion["personaje"]], retratos_dialogo)
                    escena = ESCENA_DIALOGO
                elif interaccion and interaccion["accion"] == "puerta":
                    recursos["mapa_destino"] = interaccion["imagen_destino"]
                    escena = ESCENA_MAPA_DESTINO
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
        if escena not in (ESCENA_PAUSA, ESCENA_AYUDA):
            gestor_audio.actualizar()

        if escena == ESCENA_MAPA:
            dibujar_mapa(lienzo, recursos, mundo, estado, mouse_pos, hud)
        elif escena == ESCENA_PAUSA:
            dibujar_mapa(lienzo, recursos, mundo, estado, mouse_pos, hud)
            pausa.dibujar(
                lienzo,
                "PAUSA",
                ["La Red de Ecos espera tu decisión.", "ESC o P: continuar"],
                mouse_pos,
            )
        elif escena == ESCENA_AYUDA:
            dibujar_mapa(lienzo, recursos, mundo, estado, mouse_pos, hud)
            ayuda.dibujar(
                lienzo,
                "AYUDA",
                [
                    "Clic en el Caldero o el Guardian: abrir la tablilla.",
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
            dibujar_escena_dialogo(lienzo, recursos, dialogos, mouse_pos, hud)
        elif escena == ESCENA_MENSAJE:
            mensajes.actualizar(delta_segundos)
            dibujar_escena_mensaje(lienzo, recursos, mensajes, mouse_pos, hud)
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
