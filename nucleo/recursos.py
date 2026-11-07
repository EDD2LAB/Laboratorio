"""Búsqueda y carga de recursos (imágenes, spritesheets, fuentes) y utilidades de superficie y texto."""

import os
import pygame
import unicodedata
from nucleo.config import RUTA_ASSETS, RUTA_FUENTE


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


def es_hoja_portales(nombre):
    return os.path.basename(normalizar_ruta(nombre)) == "portales 4x4.png"


def recortar_portal_final(imagen, nombre):
    """Limita la hoja 4x4 al portal de la esquina inferior derecha."""
    if not es_hoja_portales(nombre):
        return imagen
    ancho_celda = imagen.get_width() // 4
    alto_celda = imagen.get_height() // 4
    return imagen.subsurface((
        ancho_celda * 3,
        alto_celda * 3,
        ancho_celda,
        alto_celda,
    )).copy()


def cargar_spritesheet_frames(nombre, cantidad=8):
    imagen = cargar_imagen(nombre, requerido=False)
    if imagen is None:
        print(f"[advertencia] No se encontró la hoja de sprites: {nombre}")
        return []
    if cantidad < 1 or imagen.get_width() < cantidad:
        print(f"[advertencia] Spritesheet inválido (sin {cantidad} frames): {nombre}")
        return []
    return [
        imagen.subsurface(pygame.Rect(
            round(indice * imagen.get_width() / cantidad),
            0,
            round((indice + 1) * imagen.get_width() / cantidad)
            - round(indice * imagen.get_width() / cantidad),
            imagen.get_height(),
        )).copy()
        for indice in range(cantidad)
    ]


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


def dibujar_sprite_en_rect(superficie, imagen, rect):
    if not imagen:
        return
    limites = imagen.get_bounding_rect(min_alpha=32)
    if not limites.width or not limites.height:
        return
    sprite = imagen.subsurface(limites)
    escala = min(rect.width / sprite.get_width(), rect.height / sprite.get_height())
    sprite_escalado = pygame.transform.scale(
        sprite,
        (
            max(1, round(sprite.get_width() * escala)),
            max(1, round(sprite.get_height() * escala)),
        ),
    )
    superficie.blit(sprite_escalado, sprite_escalado.get_rect(midbottom=rect.midbottom))
