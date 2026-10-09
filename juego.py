"""
La Copa: Voces en las Alturas
Interfaz grafica en pygame con mapa, personajes, cinematicas breves y tablilla.

La logica de estructuras de datos queda en logica_juego.py y Arboles.py:
- EstadoJuego administra la cola de tablillas y avanza por el arbol de decisiones.
- Cada raiz de tablilla trae una categoria, tomada del arbol de clasificacion.
"""

import os
import sys
import unicodedata

import pygame

from animaciones import ControladorAnimaciones
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
MADERA_OSCURA = (55, 35, 24)
ORO = (237, 185, 87)
VERDE_PROFUNDO = (18, 45, 35)
PANEL_OSCURO = (16, 31, 25, 218)

ESCENA_MAPA = "mapa"
ESCENA_TABLILLA = "tablilla"
ESCENA_CONSECUENCIA = "consecuencia"
ESCENA_CLASIFICACION = "clasificacion"
ESCENA_RESULTADO = "resultado"
ESCENA_DIALOGO = "dialogo"
ESCENA_MENSAJE = "mensaje_privado"
ESCENA_FINAL = "final"
ESCENA_PAUSA = "pausa"
ESCENA_AYUDA = "ayuda"
CENTRO_TABLILLA = (565, 330)
CENTRO_TABLILLA_CENTRADA = (ANCHO // 2, 330)


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


def cargar_animacion_guardian():
    nombres = [
        "Fila 1 - 1. Guardian.png",
        "Fila 1 - 2. Guardian.png",
        "Fila 1 - 3. Guardian.png",
        "Fila 1 - 4. Guardian.png",
        "Fila 1 - 5. Guardian.png",
        "Fila 1 - 6. Guardian.png",
        "Fila 1 - 7. Guardian.png",
        "Fila 1 - 8. Guardian.png",
    ]
    cuadros = []
    for nombre in nombres:
        # En Windows el archivo real usa tilde; si no coincide, usamos el retrato.
        cuadro = cargar_imagen(nombre, (70, 70), requerido=False)
        if cuadro:
            cuadros.append(cuadro)
    if cuadros:
        return cuadros
    return [cargar_imagen("Guardian.jpeg", (70, 70))]


def cargar_sprite(nombre, tamano):
    return cargar_imagen(nombre, tamano)


def cargar_spritesheet(nombre, cantidad, tamano):
    spritesheet = cargar_imagen(nombre)
    ancho_frame = spritesheet.get_width() // cantidad
    alto_frame = spritesheet.get_height()
    frames = []
    for indice in range(cantidad):
        area = pygame.Rect(indice * ancho_frame, 0, ancho_frame, alto_frame)
        frame = spritesheet.subsurface(area).copy()
        frames.append(pygame.transform.scale(frame, tamano))
    return frames


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
            escala = min(260 / cuadro.get_width(), 250 / cuadro.get_height(), 1)
            cuadro = pygame.transform.smoothscale(
                cuadro, (max(1, round(cuadro.get_width() * escala)), max(1, round(cuadro.get_height() * escala)))
            )
        cuadros.append(cuadro)
    return cuadros


def cargar_animacion_aspirante():
    nombres = [
        "Fila 1 - 1 . Aspirante_a_cacique-Idle .png",
        "Fila 1 - 2. Aspirante_a_cacique-Idle.png",
        "Fila 1 - 3. Aspirante_a_cacique-Idle.png",
        "Fila 1 - 4. Aspirante_a_cacique-Idle.png",
        "Fila 1 - 5. Aspirante_a_cacique-Idle.png",
        "Fila 1- 6. Aspirante_a_cacique-Idle.png",
        "Fila 1 - 7. Aspirante_a_cacique-Idle.png",
        "Fila 1 - 8. Aspirante_a_cacique-Idle.png",
    ]
    cuadros = []
    for nombre in nombres:
        cuadro = cargar_imagen(nombre, (66, 66), requerido=False)
        if cuadro:
            cuadros.append(cuadro)
    if cuadros:
        return cuadros
    return [cargar_imagen("Aspirante.jpeg", (66, 66))]


def cargar_animacion_mensajero():
    nombres = [
        os.path.join("mensajero", "fila1 -1.png"),
        os.path.join("mensajero", "fila 1- 2.png"),
        os.path.join("mensajero", "fila 1- 3.png"),
        os.path.join("mensajero", "fila 1- 4.png"),
        os.path.join("mensajero", "fila 1 - 5.png"),
        os.path.join("mensajero", "fila 1 - 6.png"),
        os.path.join("mensajero", "fila 1 - 7.png"),
        os.path.join("mensajero", "fila 1 - 8.png"),
    ]
    cuadros = []
    for nombre in nombres:
        cuadro = cargar_imagen(nombre, (66, 66), requerido=False)
        if cuadro:
            cuadros.append(cuadro)
    if cuadros:
        return cuadros
    return [cargar_imagen("Mensajero.jpeg", (66, 66))]


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


class Actor:
    def __init__(
        self,
        nombre,
        imagen_quieto,
        posicion,
        etiqueta,
        escala_sombra=1.0,
    ):
        self.nombre = nombre
        self.posicion = pygame.Vector2(posicion)
        self.etiqueta = etiqueta
        self.escala_sombra = escala_sombra

        self.animaciones = ControladorAnimaciones()
        self.animaciones.agregar(
            "idle",
            [imagen_quieto],
            duracion_frame=200,
            repetir=True,
        )

        self.destino = None
        self.velocidad = 100
        self.en_movimiento = False

    def agregar_animacion(
        self,
        nombre,
        frames,
        duracion_frame=120,
        repetir=True,
        siguiente_estado="idle",
    ):
        self.animaciones.agregar(
            nombre,
            frames,
            duracion_frame,
            repetir,
            siguiente_estado,
        )

    def cambiar_estado(self, estado, reiniciar=False):
        return self.animaciones.cambiar_estado(estado, reiniciar)

    def mover_hacia(self, destino, velocidad=100, estado="caminar"):
        self.destino = pygame.Vector2(destino)
        self.velocidad = velocidad
        self.en_movimiento = True

        if self.destino.x < self.posicion.x:
            self.animaciones.establecer_direccion("izquierda")
        else:
            self.animaciones.establecer_direccion("derecha")

        if self.animaciones.tiene(estado):
            self.cambiar_estado(estado)

    def detener(self):
        self.destino = None
        self.en_movimiento = False
        self.cambiar_estado("idle")

    def actualizar(self, delta_ms):
        if self.en_movimiento and self.destino is not None:
            desplazamiento = self.destino - self.posicion
            distancia = desplazamiento.length()

            avance = self.velocidad * delta_ms / 1000

            if distancia <= avance:
                self.posicion = self.destino
                self.detener()
            elif distancia > 0:
                self.posicion += desplazamiento.normalize() * avance

        self.animaciones.actualizar(delta_ms)

    def dibujar(self, superficie, fuente, posicion=None, imagen=None):
        pos = pygame.Vector2(posicion) if posicion else self.posicion

        if imagen is None:
            imagen = self.animaciones.imagen_actual()

        if imagen is None:
            return

        sombra_w = int(50 * self.escala_sombra)

        sombra = pygame.Surface((sombra_w, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(
            sombra,
            (0, 0, 0, 90),
            sombra.get_rect(),
        )
        superficie.blit(
            sombra,
            (int(pos.x - sombra_w / 2), int(pos.y + 42)),
        )

        rect = imagen.get_rect(
            midbottom=(int(pos.x), int(pos.y + 48))
        )
        superficie.blit(imagen, rect)

        texto = fuente.render(self.etiqueta, True, CREMA)
        placa = texto.get_rect(
            center=(int(pos.x), int(pos.y - 27))
        ).inflate(12, 7)

        fondo_placa = pygame.Surface(placa.size, pygame.SRCALPHA)
        pygame.draw.rect(
            fondo_placa,
            (19, 38, 30, 190),
            fondo_placa.get_rect(),
            border_radius=7,
        )
        superficie.blit(fondo_placa, placa.topleft)
        superficie.blit(
            texto,
            texto.get_rect(center=placa.center),
        )

class Casa:
    def __init__(self, nombre, centro, color, vieja=False):
        self.nombre = nombre
        self.centro = centro
        self.color = color
        self.vieja = vieja

    def dibujar(self, superficie, fuente):
        x, y = self.centro
        ancho, alto = (112, 78) if self.vieja else (96, 66)
        base = pygame.Rect(x - ancho // 2, y - alto // 2 + 12, ancho, alto)
        techo = [(x - ancho // 2 - 8, base.y + 10), (x, base.y - 38), (x + ancho // 2 + 8, base.y + 10)]
        pygame.draw.ellipse(superficie, (0, 0, 0, 80), (x - ancho // 2, base.bottom - 8, ancho, 18))
        pygame.draw.rect(superficie, self.color, base, border_radius=8)
        pygame.draw.polygon(superficie, MADERA_OSCURA if self.vieja else MADERA, techo)
        pygame.draw.rect(superficie, (230, 190, 95), (x - 10, base.y + 28, 20, base.height - 28), border_radius=4)
        pygame.draw.rect(superficie, (47, 29, 20), base, width=2, border_radius=8)
        pygame.draw.polygon(superficie, (47, 29, 20), techo, width=2)
        if self.vieja:
            for dx in (-34, 0, 31):
                pygame.draw.line(superficie, (74, 49, 32), (x + dx, base.y + 5), (x + dx - 8, base.bottom - 5), 2)

        etiqueta = fuente.render(self.nombre, True, CREMA)
        placa = etiqueta.get_rect(center=(x, base.bottom + 16)).inflate(12, 5)
        pygame.draw.rect(superficie, (19, 38, 30, 178), placa, border_radius=6)
        superficie.blit(etiqueta, etiqueta.get_rect(center=placa.center))


def punto_intermedio(a, b, t):
    return pygame.Vector2(a).lerp(pygame.Vector2(b), max(0.0, min(1.0, t)))


def dibujar_puente(superficie, inicio, fin):
    pygame.draw.line(superficie, (67, 43, 28), inicio, fin, 12)
    pygame.draw.line(superficie, (157, 108, 62), inicio, fin, 7)
    vector = pygame.Vector2(fin) - pygame.Vector2(inicio)
    largo = vector.length()
    if largo == 0:
        return
    direccion = vector.normalize()
    normal = pygame.Vector2(-direccion.y, direccion.x)
    pasos = max(3, int(largo // 44))
    for i in range(1, pasos):
        punto = pygame.Vector2(inicio).lerp(fin, i / pasos)
        pygame.draw.line(superficie, (72, 47, 31), punto - normal * 8, punto + normal * 8, 2)


def dibujar_arbol_central(superficie, centro, fuente):
    x, y = centro
    pygame.draw.ellipse(superficie, (0, 0, 0, 90), (x - 95, y + 58, 190, 25))
    pygame.draw.rect(superficie, (92, 57, 33), (x - 21, y - 6, 42, 94), border_radius=18)
    for radio, dx, dy, color in (
        (76, -34, -54, (37, 102, 58)),
        (88, 31, -60, (42, 118, 65)),
        (94, 0, -105, (32, 91, 54)),
        (66, 0, -34, (49, 132, 72)),
    ):
        pygame.draw.circle(superficie, color, (x + dx, y + dy), radio)
    pygame.draw.circle(superficie, (240, 200, 93), (x + 35, y - 92), 5)
    pygame.draw.circle(superficie, (240, 200, 93), (x - 45, y - 58), 4)
    etiqueta = fuente.render("Arbol central", True, CREMA)
    superficie.blit(etiqueta, etiqueta.get_rect(center=(x, y + 112)))


def dibujar_indicadores(superficie, indicadores, fuente):
    panel = pygame.Rect(18, 18, 326, 168)
    fondo = superficie_con_alpha(panel.size, PANEL_OSCURO)
    superficie.blit(fondo, panel.topleft)
    pygame.draw.rect(superficie, (183, 133, 68), panel, width=2, border_radius=10)
    titulo = fuente.render("LA COPA", True, ORO)
    superficie.blit(titulo, (panel.x + 15, panel.y + 10))

    for indice, (nombre, valor) in enumerate(indicadores.items()):
        y = panel.y + 43 + indice * 22
        etiqueta = fuente.render(nombre.replace("_", " ").capitalize(), True, CREMA)
        superficie.blit(etiqueta, (panel.x + 14, y))
        numero = fuente.render(f"{valor}/100", True, CREMA)
        superficie.blit(numero, numero.get_rect(midright=(panel.right - 82, y + 9)))
        barra = pygame.Rect(panel.right - 72, y + 5, 58, 8)
        pygame.draw.rect(superficie, (9, 24, 17), barra, border_radius=4)
        color = (196, 90, 54) if "susurros" in nombre or "desinformación" in nombre else (104, 184, 104)
        pygame.draw.rect(superficie, color, (barra.x, barra.y, int(barra.width * valor / 100), barra.height), border_radius=4)


def texto_cinematica(estado):
    dia = estado.tablillas_resueltas + 1
    if estado.juego_terminado():
        return "Cierre del dia: el Guardian regresa al arbol central para revisar el resumen."
    return f"Dia {dia}: el Guardian va en linea recta hacia una nueva tablilla."


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


def dibujar_mapa(superficie, recursos, mundo, estado, tiempo_ms, inicio_escena, hud):
    superficie.blit(recursos["mapa"], (0, 0))

    # El Caldero expresa visualmente la salud informativa de la aldea.
    desinformacion = estado.indicadores["desinformación"] + estado.indicadores["susurros_falsos"]
    positivos = sum(estado.indicadores[nombre] for nombre in ("sabiduria", "confianza_consejo", "armonia")) / 3
    indice_caldero = 3 if desinformacion >= 100 else 2 if desinformacion >= 55 else 0 if positivos >= 65 else 1
    caldero = recursos["calderos"][indice_caldero]
    superficie.blit(caldero, caldero.get_rect(center=(ANCHO // 2, 350)))

    for actor in mundo["actores"]:
        actor.dibujar(superficie, recursos["fuente_etiqueta"])

    progreso = (tiempo_ms - inicio_escena) / 3300
    destino_guardian = (mundo["arbol"][0], mundo["arbol"][1] - 70)
    pos_guardian = punto_intermedio(mundo["casa_guardian"], destino_guardian, progreso)
    if progreso < 1:
        indice_frame = (tiempo_ms // 120) % len(recursos["guardian_caminando"])
        imagen_guardian = recursos["guardian_caminando"][indice_frame]
    else:
        imagen_guardian = recursos["guardian_quieto"]
    mundo["guardian"].dibujar(superficie, recursos["fuente_etiqueta"], pos_guardian, imagen_guardian)

    hud.dibujar(superficie)
    dibujar_mensaje_mapa(superficie, recursos["fuente_mapa"], texto_cinematica(estado))


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


def dibujar_escena_tablilla(superficie, recursos, estado, botones, mouse_pos, hud):
    superficie.blit(recursos["fondo_tablilla"], (0, 0))
    hud.dibujar(superficie)
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
        if usos[clave] <= 0:
            imagen.fill((80, 80, 80, 180), special_flags=pygame.BLEND_RGBA_MULT)
        superficie.blit(imagen, rect)
        contador = recursos["fuente_categoria"].render(str(usos[clave]), True, CREMA)
        superficie.blit(contador, contador.get_rect(bottomright=(rect.right + 3, rect.bottom + 3)))
        if rect.collidepoint(mouse_pos):
            aviso = recursos["fuente_categoria"].render(
                f"Poción de {nombres[clave]}: se usa al tomar esa decisión", True, CREMA
            )
            fondo = superficie_con_alpha((aviso.get_width() + 16, 26), (14, 31, 23, 225))
            posicion = (ANCHO - fondo.get_width() - 14, 122)
            superficie.blit(fondo, posicion)
            superficie.blit(aviso, (posicion[0] + 8, posicion[1] + 5))
    if animacion:
        progreso = 1 - animacion["restante"] / animacion["duracion"]
        cuadros = recursos["efectos_decision"][animacion["clave"]]
        indice = min(len(cuadros) - 1, int(progreso * len(cuadros)))
        cuadro = cuadros[indice]
        superficie.blit(cuadro, cuadro.get_rect(center=(CENTRO_TABLILLA[0], CENTRO_TABLILLA[1] + 15)))
    return rectangulos


def dibujar_final(superficie, recursos, estado, mouse_pos):
    positivos = sum(estado.indicadores[nombre] for nombre in ("sabiduria", "confianza_consejo", "armonia")) / 3
    negativo = estado.indicadores["susurros_falsos"] + estado.indicadores["desinformación"]
    victoria = positivos >= 55 and negativo < 100
    fondo = recursos["final_positivo"] if victoria else recursos["final_negativo"]
    superficie.blit(fondo, (0, 0))
    velo = superficie_con_alpha((ANCHO, ALTO), (6, 18, 12, 94))
    superficie.blit(velo, (0, 0))
    titulo = recursos["fuente_resultado"].render("LA COPA FLORECE" if victoria else "LA COPA SE CUBRE DE HUMO", True, CREMA)
    superficie.blit(titulo, titulo.get_rect(center=(ANCHO // 2, 160)))
    detalle = recursos["fuente_texto"].render(
        "Mira será la nueva Cacique" if victoria else "El Consejo deberá recomponer la confianza", True, CREMA
    )
    superficie.blit(detalle, detalle.get_rect(center=(ANCHO // 2, 205)))
    resumen = [
        f"Sabiduría: {estado.indicadores['sabiduria']}",
        f"Confianza: {estado.indicadores['confianza_consejo']}",
        f"Armonía: {estado.indicadores['armonia']}",
        f"Desinformación: {estado.indicadores['desinformación']}",
    ]
    for indice, linea in enumerate(resumen):
        texto = recursos["fuente_panel"].render(linea, True, CREMA)
        superficie.blit(texto, texto.get_rect(center=(ANCHO // 2, 270 + indice * 30)))
    instruccion = recursos["fuente_boton"].render("R: reiniciar    ESC: salir", True, ORO)
    superficie.blit(instruccion, instruccion.get_rect(center=(ANCHO // 2, 600)))


def dibujar_escena_dialogo(superficie, recursos, mundo, estado, dialogos, mouse_pos, hud):
    """El diálogo se superpone al mapa y bloquea sus demás interacciones."""
    superficie.blit(recursos["mapa"], (0, 0))
    for actor in mundo["actores"]:
        actor.dibujar(superficie, recursos["fuente_etiqueta"])
    mundo["guardian"].dibujar(superficie, recursos["fuente_etiqueta"])
    hud.dibujar(superficie)
    dialogos.dibujar(superficie, mouse_pos, ANCHO, ALTO)


def dibujar_escena_mensaje(superficie, recursos, mundo, mensajes, mouse_pos, hud):
    """El pergamino se presenta sobre el mapa y bloquea las demás acciones."""
    superficie.blit(recursos["mapa"], (0, 0))
    for actor in mundo["actores"]:
        actor.dibujar(superficie, recursos["fuente_etiqueta"])
    mundo["guardian"].dibujar(superficie, recursos["fuente_etiqueta"])
    hud.dibujar(superficie)
    mensajes.dibujar(superficie, mouse_pos)


def crear_fondo_tablilla(mapa):
    fondo = mapa.copy()
    velo = superficie_con_alpha((ANCHO, ALTO), (7, 18, 14, 178))
    fondo.blit(velo, (0, 0))
    return fondo


def crear_mundo(recursos):
    arbol = (ANCHO // 2, 360)
    casa_guardian = (ANCHO // 2, 142)
    actores = [
        Actor("aspirante", recursos["aspirante_quieto"], (178, 342), "Kael"),
        Actor("mira", recursos["mira_quieta"], (700, 135), "Mira"),
        Actor("mensajero", recursos["mensajero_quieto"], (783, 342), "Mensajero"),
        Actor("habitante_1", recursos["tarek_quieto"], (220, 566), "Tarek"),
        Actor("habitante_2", recursos["luma_quieta"], (740, 566), "Luma"),
    ]
    return {
        "arbol": arbol,
        "casa_guardian": casa_guardian,
        "actores": actores,
        "guardian": Actor("guardian", recursos["guardian_quieto"], casa_guardian, "Guardian", escala_sombra=1.15),
    }


def iniciar_cinematica_mapa(mundo):
    destino = (
        mundo["arbol"][0],
        mundo["arbol"][1] - 70,
    )
    mundo["guardian"].mover_hacia(
        destino,
        velocidad=95,
        estado="caminar",
    )


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
    pantalla_completa = True
    pantalla = crear_ventana(pantalla_completa)
    pygame.display.set_caption("La Copa: Voces en las Alturas")
    reloj = pygame.time.Clock()
    lienzo = pygame.Surface((ANCHO, ALTO))

    fuente_texto = cargar_fuente(22)
    fuente_categoria = cargar_fuente(13)
    fuente_boton = cargar_fuente(19)
    fuente_indicador = cargar_fuente(11)
    fuente_etiqueta = cargar_fuente(13)
    fuente_mapa = cargar_fuente(18)
    fuente_panel_titulo = cargar_fuente(16)
    fuente_panel = cargar_fuente(13)
    fuente_resultado = cargar_fuente(28)

    mapa = cargar_imagen("Mapa.png", (ANCHO, ALTO))
    recursos = {
        "mapa": mapa,
        "fondo_tablilla": crear_fondo_tablilla(mapa),
        "fondo_clasificacion": cargar_imagen("FondoClasificacion.png", (860, 505)),
        "tablilla": cargar_imagen("Tablilla.png", (460, 460)),
        "colgar": cargar_imagen("Colgar.png", (190, 127)),
        "consultar": cargar_imagen("Consultar.png", (190, 127)),
        "quemar": cargar_imagen("Quemar.png", (190, 127)),
        "pergamino_mensaje": cargar_imagen("Mensaje_privado.png", (570, 410)),
        "calderos": [
            cargar_frame_caldero(os.path.join("Caldero", f"Caldero-ecos-fila{indice}.png"))
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
        "final_positivo": cargar_imagen(os.path.join("Finales", "Final_positivo.jpeg"), (ANCHO, ALTO)),
        "final_negativo": cargar_imagen(os.path.join("Finales", "Game_over.jpeg"), (ANCHO, ALTO)),
        "guardian_quieto": cargar_sprite("Fila 1 - 1. Guardian.png", (86, 86)),
        "guardian_caminando": cargar_spritesheet("Fila 2. Guardian.png", 8, (86, 86)),
        "guardian_hablando": [cargar_imagen("Guardian_hablando.png", (86, 86), requerido=False) or cargar_imagen("Guardian.jpeg", (86, 86))],
        "guardian_consultando": [cargar_imagen("Guardian_consultando.png", (86, 86), requerido=False) or cargar_imagen("Guardian.jpeg", (86, 86))],
        "aspirante_quieto": cargar_sprite("Fila 1 - 3. Aspirante_a_cacique-Idle.png", (78, 78)),
        "mira_quieta": cargar_sprite("MujerAspirante Fila 1 - 8.png", (78, 78)),
        "mensajero_quieto": cargar_sprite(os.path.join("mensajero", "fila 1 - 7.png"), (78, 78)),
        "tarek_quieto": cargar_sprite("HabHombre Fila 1- 3.png", (76, 76)),
        "luma_quieta": cargar_sprite("HabMujer Fila 1 - 7.png", (76, 76)),
        "fuente_texto": fuente_texto,
        "fuente_categoria": fuente_categoria,
        "fuente_boton": fuente_boton,
        "fuente_indicador": fuente_indicador,
        "fuente_etiqueta": fuente_etiqueta,
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
    guardian = mundo["guardian"]

    guardian.agregar_animacion(
        "caminar",
        recursos["guardian_caminando"],
        duracion_frame=120,
        repetir=True,
    )
    guardian.agregar_animacion(
        "hablar",
        recursos["guardian_hablando"],
        duracion_frame=140,
        repetir=True,
    )
    guardian.agregar_animacion(
        "consultar",
        recursos["guardian_consultando"],
        duracion_frame=120,
        repetir=False,
        siguiente_estado="idle",
    )

    botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
    grupo_botones = GrupoBotones(botones)
    dialogos = ControladorDialogo(fuente_texto, fuente_panel_titulo, fuente_boton)
    mensajes = ControladorMensajePrivado(
        fuente_panel_titulo, fuente_panel, fuente_boton, recursos["pergamino_mensaje"]
    )
    hud = HUDIndicadores(fuente_indicador, iconos_hud)
    pausa = MenuModal(fuente_resultado, fuente_texto, fuente_boton)
    ayuda = MenuModal(fuente_resultado, fuente_texto, fuente_boton)
    retratos_dialogo = {
        "Mira": recursos["aspirante_quieto"],
        "Mensajero": recursos["mensajero_quieto"],
        "Tarek": recursos["tarek_quieto"],
        "Luma": recursos["luma_quieta"],
        "Guardián": recursos["guardian_quieto"],
    }
    conversaciones = [
        {"personaje": "Mira", "texto": "Guardián, escuché un rumor sobre el puente norte. Antes de compartirlo, necesitamos pruebas.", "respuestas": ["Te ayudaré", "Necesito más pruebas"]},
        {"personaje": "Tarek", "texto": "Yo vi el rayo cerca del Mirador Alto. No escuché que el puente se hubiera cerrado.", "respuestas": ["Gracias por tu testimonio"]},
        {"personaje": "Luma", "texto": "Los Ecos de Troncos repiten la noticia muy rápido. Una tablilla sin verificar puede confundir a toda la aldea.", "respuestas": ["Lo tendré en cuenta"]},
        {"personaje": "Mensajero", "texto": "Puedo llevar un mensaje privado entre plataformas. La ruta más corta no siempre es la más segura.", "respuestas": ["Entrega el mensaje"]},
    ]
    indice_conversacion = 0
    usos_pociones = {"colgar": 1, "consultar": 1, "quemar": 1, "ignorar": 1}
    pocion_animacion = None
    escena = ESCENA_MAPA
    escena_anterior = ESCENA_MAPA
    inicio_escena = pygame.time.get_ticks()
    iniciar_cinematica_mapa(mundo)
    duracion_cinematica = 3900

    corriendo = True
    while corriendo:
        delta_ms = reloj.tick(FPS)
        delta_segundos = delta_ms / 1000
        tiempo_ms = pygame.time.get_ticks()
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
                    if tipo == "respuesta" and respuesta == "Te ayudaré":
                        mensajes.abrir({
                            "remitente": "Sabio de las Raíces",
                            "destinatario": "Guardián",
                            "texto": "El puente norte necesita una revisión. Consulta a quienes vieron el rayo antes de compartir la tablilla.",
                        })
                        escena = ESCENA_MENSAJE
                    else:
                        escena = ESCENA_MAPA
                        inicio_escena = pygame.time.get_ticks()
            elif escena == ESCENA_MENSAJE:
                if mensajes.manejar_evento(
                    evento, convertir_mouse_a_lienzo(getattr(evento, "pos", pygame.mouse.get_pos()), rect_lienzo)
                ):
                    escena = ESCENA_MAPA
                    inicio_escena = pygame.time.get_ticks()
            elif escena == ESCENA_FINAL:
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_r:
                    estado = EstadoJuego()
                    mundo = crear_mundo(recursos)
                    guardian = mundo["guardian"]
                    botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
                    grupo_botones.reemplazar(botones)
                    usos_pociones = {"colgar": 1, "consultar": 1, "quemar": 1, "ignorar": 1}
                    pocion_animacion = None
                    escena = ESCENA_MAPA
                    inicio_escena = pygame.time.get_ticks()
                    iniciar_cinematica_mapa(mundo)
                elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                    corriendo = False
            elif evento.type == pygame.KEYDOWN and evento.key in (pygame.K_ESCAPE, pygame.K_p):
                escena_anterior = escena
                pausa.configurar([
                    ("continuar", "Continuar"),
                    ("ayuda", "Ayuda"),
                    ("salir", "Salir"),
                ])
                escena = ESCENA_PAUSA
            elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_d and escena == ESCENA_MAPA:
                # Punto de integración temporal: B podrá iniciar este mismo
                # controlador desde un hitbox o una conversación desbloqueada.
                dialogos.iniciar(conversaciones[indice_conversacion], retratos_dialogo)
                indice_conversacion = (indice_conversacion + 1) % len(conversaciones)
                escena = ESCENA_DIALOGO
            elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_m and escena == ESCENA_MAPA:
                mensajes.abrir({
                    "remitente": "Mensajero",
                    "destinatario": "Guardián",
                    "texto": "Tengo un mensaje del Sabio. Reúne testimonios antes de decidir el destino de una tablilla.",
                })
                escena = ESCENA_MENSAJE
            elif evento.type == pygame.KEYDOWN:
                opcion_teclado = grupo_botones.manejar_teclado(evento)
                if opcion_teclado and escena == ESCENA_CLASIFICACION:
                    estado.clasificar_evento(opcion_teclado)
                    botones = []
                    grupo_botones.reemplazar(botones)
                    escena = ESCENA_RESULTADO
                elif opcion_teclado and escena == ESCENA_TABLILLA:
                    clave = clave_pocion(opcion_teclado)
                    if usos_pociones[clave] > 0:
                        usos_pociones[clave] -= 1
                        pocion_animacion = {"clave": clave, "opcion": opcion_teclado, "restante": 0.72, "duracion": 0.72}
                    else:
                        estado.elegir_opcion(opcion_teclado)
                        botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
                        grupo_botones.reemplazar(botones)
                        if estado.evento_resuelto():
                            escena = ESCENA_CONSECUENCIA
            elif escena == ESCENA_RESULTADO and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                estado.continuar_despues_resultado()
                botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
                grupo_botones.reemplazar(botones)
                if estado.juego_terminado():
                    escena = ESCENA_FINAL
                else:
                    escena = ESCENA_MAPA
                    inicio_escena = pygame.time.get_ticks()
                    iniciar_cinematica_mapa(mundo)
            elif escena == ESCENA_CONSECUENCIA and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                botones = construir_botones(estado.opciones_clasificacion_actuales(), recursos, fuente_boton)
                grupo_botones.reemplazar(botones)
                escena = ESCENA_CLASIFICACION
            elif escena == ESCENA_CLASIFICACION and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                pos_lienzo = convertir_mouse_a_lienzo(evento.pos, rect_lienzo)
                for boton in botones:
                    if boton.fue_clickeado(pos_lienzo):
                        estado.clasificar_evento(boton.texto)
                        botones = []
                        grupo_botones.reemplazar(botones)
                        escena = ESCENA_RESULTADO
                        break
            elif escena == ESCENA_TABLILLA and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                pos_lienzo = convertir_mouse_a_lienzo(evento.pos, rect_lienzo)
                if not pocion_animacion:
                    for boton in botones:
                        if boton.fue_clickeado(pos_lienzo):
                            clave = clave_pocion(boton.texto)
                            if usos_pociones[clave] > 0:
                                usos_pociones[clave] -= 1
                                pocion_animacion = {"clave": clave, "opcion": boton.texto, "restante": 0.72, "duracion": 0.72}
                            else:
                                estado.elegir_opcion(boton.texto)
                                botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
                                grupo_botones.reemplazar(botones)
                                if estado.evento_resuelto():
                                    escena = ESCENA_CONSECUENCIA
                            break

        mundo["guardian"].actualizar(delta_ms)
        for actor in mundo["actores"]:
            actor.actualizar(delta_ms)
        hud.actualizar(estado.indicadores, delta_segundos)

        if pocion_animacion:
            pocion_animacion["restante"] -= delta_segundos
            if pocion_animacion["restante"] <= 0:
                estado.elegir_opcion(pocion_animacion["opcion"])
                botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
                grupo_botones.reemplazar(botones)
                pocion_animacion = None
                if estado.evento_resuelto():
                    escena = ESCENA_CONSECUENCIA

        if escena == ESCENA_MAPA and tiempo_ms - inicio_escena >= duracion_cinematica:
            escena = ESCENA_TABLILLA
            botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
            grupo_botones.reemplazar(botones)

        if escena == ESCENA_MAPA:
            dibujar_mapa(lienzo, recursos, mundo, estado, tiempo_ms, inicio_escena, hud)
        elif escena == ESCENA_PAUSA:
            dibujar_mapa(lienzo, recursos, mundo, estado, tiempo_ms, inicio_escena, hud)
            pausa.dibujar(
                lienzo,
                "PAUSA",
                ["La Red de Ecos espera tu decisión.", "ESC o P: continuar"],
                mouse_pos,
            )
        elif escena == ESCENA_AYUDA:
            dibujar_mapa(lienzo, recursos, mundo, estado, tiempo_ms, inicio_escena, hud)
            ayuda.dibujar(
                lienzo,
                "AYUDA",
                [
                    "Tablillas: decide si colgar, consultar, quemar o ignorar.",
                    "Diálogos: reúne testimonios antes de actuar.",
                    "Ecos y Mensajero: comparten pistas entre plataformas.",
                    "Pócimas: anticipan consecuencias; úsalas con cuidado.",
                    "Mantén Sabiduría, Confianza y Armonía saludables.",
                    "Evita que Susurros Falsos y Desinformación crezcan.",
                ],
                mouse_pos,
            )
        elif escena == ESCENA_DIALOGO:
            dialogos.actualizar(delta_segundos)
            dibujar_escena_dialogo(lienzo, recursos, mundo, estado, dialogos, mouse_pos, hud)
        elif escena == ESCENA_MENSAJE:
            mensajes.actualizar(delta_segundos)
            dibujar_escena_mensaje(lienzo, recursos, mundo, mensajes, mouse_pos, hud)
        elif escena == ESCENA_CONSECUENCIA:
            dibujar_consecuencia_evento(lienzo, recursos, estado)
        elif escena == ESCENA_CLASIFICACION:
            dibujar_pregunta_clasificacion(lienzo, recursos, botones, mouse_pos)
        elif escena == ESCENA_RESULTADO:
            dibujar_resultado_evento(lienzo, recursos, estado)
        elif escena == ESCENA_FINAL:
            dibujar_final(lienzo, recursos, estado, mouse_pos)
        else:
            dibujar_escena_tablilla(lienzo, recursos, estado, botones, mouse_pos, hud)
            dibujar_pociones(lienzo, recursos, usos_pociones, pocion_animacion, mouse_pos)

        presentar_lienzo(pantalla, lienzo)
        pygame.display.flip()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
