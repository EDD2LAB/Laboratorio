"""Escenas del modo de un jugador portadas al multijugador.

Todo lo que se puede se REUTILIZA directamente de ``un_jugador`` (tablilla,
animación de poción, efectos de la tablilla, trivia de clasificación,
resultado de clasificación) pasando un adaptador con la misma interfaz que
``EstadoJuego``. Por red solo llegan ids, tipos y estados; los sprites y
sonidos se cargan aquí una sola vez.
"""
import math

import pygame

from multijugador.presentacion import (ETIQUETAS, NOMBRES_POCION, ORDEN_INDICADORES, POLARIDAD, color_cambio,
                                       texto_cambio)
from multijugador.reparacion import CONFIGURACION as CONFIG_REPARACION, angulo_aguja

ORO = (237, 185, 87)
CREMA = (255, 243, 210)
VERDE = (130, 222, 158)
TINTA = (61, 37, 25)
TURQUESA = (106, 218, 204)
PANTALLA = (12, 28, 44)
DIA_PRESENTE = 1  # índice de los fondos de escena de Distrito Conecta
PALETA_PRESENTE = {"normal": (24, 62, 84), "hover": (36, 90, 116), "presionado": (14, 40, 58),
                   "borde": TURQUESA, "contorno": (6, 16, 28)}
# Opción de la pantalla pública -> (nombre corto, imagen, cuadro si es una hoja de 8).
OPCIONES_PRESENTE = {
    "verificar": ("Verificar", "Estados/estado_fuente_verificada.png", None),
    "reportar": ("Reportar", "Iconos/Nuevos/icono_sancion.png", None),
    "dejar_pendiente": ("Dejar pendiente", "Iconos/Nuevos/icono_tiempo.png", None),
    "compartir": ("Compartir", "Estados/fx_propagacion_tarjeta_8f_1024x128.png", 4),
}
TAMANO_TARJETA = (208, 176)


def en_presente(contexto_o_dimension):
    if isinstance(contexto_o_dimension, dict):
        return contexto_o_dimension.get("dimension") == "presente"
    return contexto_o_dimension == "presente"


def nombre_opcion_presente(clave):
    return OPCIONES_PRESENTE.get(clave, (clave,))[0]


def pantalla(superficie, rect, color=PANTALLA, borde=TURQUESA, radio=12):
    pygame.draw.rect(superficie, color, rect, border_radius=radio)
    pygame.draw.rect(superficie, borde, rect, 2, border_radius=radio)


class AdaptadorEstado:
    """Interfaz mínima de EstadoJuego que usan las funciones de ``juego``."""

    def __init__(self, texto="", resultado=None, dia=0):
        self.texto = texto
        self.resultado = resultado
        self.dia = dia

    def texto_actual(self):
        return self.texto

    def resultado_evento_actual(self):
        return self.resultado

    def juego_terminado(self):
        return False


def tarjeta_categoria(marco, icono, centro=(90, 86), radio=56):
    """Tarjeta para categorías sin PNG propio: se reutiliza el marco real de
    las tarjetas de clasificación y se coloca un ícono real del proyecto en
    el medallión (sin dibujar arte nuevo por código)."""
    tarjeta = marco.copy()
    for r in range(radio, 0, -1):
        k = r / radio
        pygame.draw.circle(tarjeta, (round(24 + 30 * (1 - k)), round(52 + 40 * (1 - k)), round(40 + 26 * (1 - k))), centro, r)
    if icono is not None:
        lado = round(radio * 1.45)
        escala = min(lado / icono.get_width(), lado / icono.get_height())
        icono = pygame.transform.scale(icono, (max(1, round(icono.get_width() * escala)), max(1, round(icono.get_height() * escala))))
        tarjeta.blit(icono, icono.get_rect(center=centro))
    return tarjeta


class RecursosEscenas:
    """Carga única de los recursos visuales del modo de un jugador."""

    def __init__(self, fondo_mapa, decoraciones):
        from nucleo.recursos import (
            cargar_efecto_tablilla,
            cargar_fuente,
            cargar_icono_hud,
            cargar_imagen,
            cargar_spritesheet_frames,
        )
        from mundo.reparacion_puentes import SistemaReparacionPuente
        cargar = cargar_imagen
        fondo = fondo_mapa.copy()
        for objeto in decoraciones:
            if not objeto.get("cesto"):
                fondo.blit(objeto["imagen"], objeto["rect"])
        velo = pygame.Surface((960, 720), pygame.SRCALPHA)
        velo.fill((7, 18, 14, 178))
        fondo.blit(velo, (0, 0))
        self.fondo_tablilla = fondo
        self.r = {
            "mapas_dia": [fondo_mapa], "fondos_tablilla_por_dia": {0: fondo},
            "tablilla": cargar("Tablilla.png", (460, 460)),
            "colgar": cargar("Colgar.png", (190, 127)), "consultar": cargar("Consultar.png", (190, 127)),
            "quemar": cargar("Quemar.png", (190, 127)), "ignorar": cargar("Ignorar.png", (190, 127)),
            "pociones": {
                "colgar": cargar("Pociones/pocion_amarilla.png", (42, 42)),
                "consultar": cargar("Pociones/pocion_azul.png", (42, 42)),
                "quemar": cargar("Pociones/pocion_roja.png", (42, 42)),
                "ignorar": cargar("Pociones/pocion_morada.png", (42, 42)),
            },
            "efectos_decision": {clave: cargar_efecto_tablilla(clave.capitalize() + "_tablilla.png")
                                 for clave in ("colgar", "consultar", "quemar", "ignorar")},
            "fondo_clasificacion": cargar("FondoClasificacion.png", (860, 505)),
            "panel_clasificacion": cargar("Cartel_decision.png", (840, 315)),
            # "Aviso Comunitario" y las categorías de Distrito Conecta no tienen
            # PNG: construir_botones_clasificacion usa el botón de texto.
            "botones_clasificacion": {
                "rumor_politico": cargar("Rumor_politico.png", (180, 200)),
                "suceso_natural": cargar("Suceso_natural.png", (180, 200)),
                "acusacion_personal": cargar("Acusacion_personal.png", (180, 200)),
            },
            "fuente_texto": cargar_fuente(22), "fuente_categoria": cargar_fuente(13),
            "fuente_boton": cargar_fuente(19), "fuente_mapa": cargar_fuente(18),
            "fuente_panel_titulo": cargar_fuente(16), "fuente_panel": cargar_fuente(13),
            "fuente_resultado": cargar_fuente(28),
        }
        # Categorías sin PNG propio (sin arte en el repositorio): tarjeta con
        # el marco real de Suceso_natural.png e íconos existentes.
        marco = self.r["botones_clasificacion"]["suceso_natural"]
        for clave, icono in (("aviso_comunitario", "Iconos/registro.png"),
                             ("generado_con_ia", "Estados/estado_contenido_ia.png"),
                             ("contenido_autentico", "Estados/estado_fuente_verificada.png")):
            imagen_icono = cargar(icono, requerido=False)
            if imagen_icono is None:
                print("[Multijugador] Falta el ícono esperado:", icono)
            self.r["botones_clasificacion"][clave] = tarjeta_categoria(marco, imagen_icono)
        self.iconos_hud = {
            "sabiduria": cargar_icono_hud("Barra_sabiduría.png"),
            "confianza": cargar_icono_hud("Barra_confianza.png"),
            "armonia": cargar_icono_hud("Barra_armonía.png"),
            "susurros_falsos": cargar_icono_hud("Barra_susurros_falsos.png"),
            "desinformacion": cargar_icono_hud("Barra_desinformación.png"),
        }
        indicador = {estado: cargar("Indicadores Puente/" + archivo, (220, 220), requerido=False)
                     for estado, archivo in (("normal", "Indicador.png"), ("acierto", "IndicadorAcierto.png"),
                                             ("error", "IndicadorError.png"))}
        self.indicadores_puente = indicador
        self.puente_roto = cargar("Puentes/Puente1Roto.png", requerido=False)
        self.efecto_reparacion = cargar_spritesheet_frames("Animaciones/Efectos/EfectoReparacion.png", 8)
        try:
            self.materiales = SistemaReparacionPuente.recortar_spritesheet_materiales(
                cargar("Herramientas/HerramientasReparación.png", requerido=False))
        except (RuntimeError, ValueError) as error:
            print("[Multijugador] Sin sprites de materiales:", error)
            self.materiales = {}
        self._rotados = {}
        self.fondo_presente = None  # lo prepara la vista al cargar Distrito Conecta
        self.r_presente = self.r
        self.iconos_presente = {}
        self.icono_publicacion = None
        self._tarjetas_presente = {}

    def preparar_presente(self, mapa):
        """Escenas de decisión de Distrito Conecta sobre su propio mapa.

        Se escala una sola vez, al cargar la dimensión."""
        from nucleo.recursos import cargar_spritesheet_frames
        from interfaz.arte import icono as cargar_icono
        factor = max(960 / mapa.get_width(), 720 / mapa.get_height())
        ampliado = pygame.transform.scale(mapa, (max(960, round(mapa.get_width() * factor)),
                                                 max(720, round(mapa.get_height() * factor))))
        recorte = pygame.Rect(0, 0, 960, 720)
        recorte.center = ampliado.get_rect().center
        fondo = ampliado.subsurface(recorte).copy()
        velo = pygame.Surface((960, 720), pygame.SRCALPHA)
        velo.fill((6, 16, 32, 170))
        fondo.blit(velo, (0, 0))
        self.fondo_presente = fondo
        self.r["mapas_dia"] = [self.r["mapas_dia"][0], fondo]
        self.r["fondos_tablilla_por_dia"][DIA_PRESENTE] = fondo
        # Los marcos de pergamino se cambian por pantallas; el texto queda en su sitio.
        pregunta = pygame.Surface(self.r["panel_clasificacion"].get_size(), pygame.SRCALPHA)
        pantalla(pregunta, pygame.Rect(60, 86, 720, 118))
        resultado = pygame.Surface(self.r["fondo_clasificacion"].get_size(), pygame.SRCALPHA)
        pantalla(resultado, pygame.Rect(60, 150, 740, 330), (232, 241, 246), (56, 160, 190))
        self.r_presente = dict(self.r, panel_clasificacion=pregunta, fondo_clasificacion=resultado)
        for clave, (_, ruta, cuadro) in OPCIONES_PRESENTE.items():
            if cuadro is None:
                self.iconos_presente[clave] = cargar_icono(ruta, (72, 72))
                continue
            cuadros = cargar_spritesheet_frames(ruta, 8)
            if len(cuadros) > cuadro:
                imagen = cuadros[cuadro]
                imagen = imagen.subsurface(imagen.get_bounding_rect())
                factor = min(72 / imagen.get_width(), 72 / imagen.get_height())
                self.iconos_presente[clave] = pygame.transform.scale(
                    imagen, (round(imagen.get_width() * factor), round(imagen.get_height() * factor)))
        self.icono_publicacion = cargar_icono("Estados/estado_sin_fuente.png", (104, 104))

    def tarjeta_presente(self, clave, texto):
        """Tarjeta de una opción de la pantalla pública (se compone una vez)."""
        from nucleo.recursos import envolver_texto
        if (clave, texto) not in self._tarjetas_presente:
            tarjeta = pygame.Surface(TAMANO_TARJETA, pygame.SRCALPHA)
            pantalla(tarjeta, tarjeta.get_rect(), (20, 50, 70))
            imagen = self.iconos_presente.get(clave)
            if imagen is not None:
                tarjeta.blit(imagen, imagen.get_rect(center=(TAMANO_TARJETA[0] // 2, 50)))
            nombre = self.r["fuente_boton"].render(nombre_opcion_presente(clave), True, CREMA)
            tarjeta.blit(nombre, nombre.get_rect(center=(TAMANO_TARJETA[0] // 2, 104)))
            for i, linea in enumerate(envolver_texto(texto, self.r["fuente_panel"], TAMANO_TARJETA[0] - 20)[:3]):
                render = self.r["fuente_panel"].render(linea, True, VERDE)
                tarjeta.blit(render, render.get_rect(midtop=(TAMANO_TARJETA[0] // 2, 122 + i * 15)))
            self._tarjetas_presente[(clave, texto)] = tarjeta
        return self._tarjetas_presente[(clave, texto)]

    def indicador_rotado(self, estado, progreso):
        base = self.indicadores_puente.get(estado) or self.indicadores_puente.get("normal")
        if base is None or not progreso:
            return base
        clave = (estado, progreso)
        if clave not in self._rotados:
            grados = math.degrees(progreso * CONFIG_REPARACION["rotacion_objetivo_por_acierto"])
            rotada = pygame.transform.rotate(base, grados)
            lienzo = pygame.Surface(base.get_size(), pygame.SRCALPHA)
            lienzo.blit(rotada, rotada.get_rect(center=lienzo.get_rect().center))
            self._rotados[clave] = lienzo
        return self._rotados[clave]


class AnimacionPocion:
    """Lanzamiento, splash y efecto sobre la tablilla, como el modo de un jugador."""

    def __init__(self, tipo, texto, evento_id):
        from un_jugador.tablilla import iniciar_animacion_decision
        self.datos = iniciar_animacion_decision(tipo)
        self.estado = AdaptadorEstado(texto)
        self.evento_id = evento_id

    @property
    def terminada(self):
        return self.datos["tiempo_transcurrido"] >= self.datos["duracion"]

    def actualizar(self, segundos):
        self.datos["tiempo_transcurrido"] = min(self.datos["duracion"], self.datos["tiempo_transcurrido"] + segundos)
        self.datos["restante"] = self.datos["duracion"] - self.datos["tiempo_transcurrido"]

    def dibujar(self, superficie, recursos):
        from un_jugador.tablilla import (
            dibujar_animacion_pocion,
            dibujar_tablilla,
            dibujar_tablilla_en_efecto,
        )
        r = recursos.r
        superficie.blit(recursos.fondo_tablilla, (0, 0))
        if self.datos["tiempo_transcurrido"] >= self.datos["duracion_lanzamiento"] + self.datos["duracion_splash"]:
            dibujar_tablilla_en_efecto(superficie, r, self.estado, self.datos)
        else:
            dibujar_tablilla(superficie, r["tablilla"], self.estado, r["fuente_texto"], r["fuente_categoria"])
        dibujar_animacion_pocion(superficie, r, self.datos)


def estado_caldero(indicadores):
    """Misma regla que un_jugador.tablilla.estado_caldero (desinformación + susurros)."""
    total = indicadores.get("desinformacion", 0) + indicadores.get("susurros_falsos", 0)
    return "critico" if total >= 100 else "peligroso" if total >= 55 else "estable"


def dibujar_decision(panel, superficie, contexto, opciones, tipos, falta, mensaje, votos):
    """Tablilla del evento y una poción por opción (botones del modo de un jugador)."""
    if en_presente(contexto):
        return dibujar_decision_presente(panel, superficie, contexto, opciones, falta, mensaje, votos)
    from nucleo.recursos import envolver_texto
    from un_jugador.tablilla import dibujar_pociones, dibujar_tablilla
    from interfaz.boton import Boton
    r = panel.vista.escenas.r
    superficie.blit(panel.vista.escenas.fondo_tablilla, (0, 0))
    dibujar_tablilla(superficie, r["tablilla"], AdaptadorEstado(contexto.get("noticia", "")),
                           r["fuente_texto"], r["fuente_categoria"])
    titulo = r["fuente_resultado"].render("¿QUÉ POCIÓN USAMOS?", True, ORO)
    superficie.blit(titulo, titulo.get_rect(center=(480, 34)))
    panel.texto_lineas(superficie, mensaje, 70, 60, 620, r["fuente_mapa"], ORO if falta else CREMA)
    panel.texto_lineas(superficie, votos, 70, 86, 620, r["fuente_panel"], VERDE)
    dibujar_pociones(superficie, r, {}, None, panel.vista.mouse)
    claves = list(opciones)
    separacion = 28
    ancho_total = 190 * len(claves) + separacion * (len(claves) - 1)
    x = (960 - ancho_total) / 2 + 95
    prefijo = "presente_votar:" if contexto.get("dimension") == "presente" else "votar:"
    for clave in claves:
        tipo = tipos.get(clave, "ignorar")
        boton = Boton(opciones[clave], r[tipo], (round(x), 640), r["fuente_boton"], desactivado=bool(falta))
        boton.dibujar(superficie, panel.vista.mouse)
        panel.botones[prefijo + clave] = boton
        # La frase completa de la opción, debajo del nombre de la poción.
        lineas = envolver_texto(opciones[clave], r["fuente_panel"], 186)
        alto = len(lineas) * 15 + 8
        caja = pygame.Rect(0, 0, 196, alto)
        caja.midbottom = (round(x), 574)
        fondo = pygame.Surface(caja.size, pygame.SRCALPHA)
        fondo.fill((14, 31, 23, 228))
        superficie.blit(fondo, caja)
        pygame.draw.rect(superficie, ORO if panel.privado_voto(contexto) == clave else (110, 82, 45), caja, 2, border_radius=6)
        for i, linea in enumerate(lineas):
            texto = r["fuente_panel"].render(linea, True, CREMA)
            superficie.blit(texto, texto.get_rect(midtop=(caja.centerx, caja.y + 4 + i * 15)))
        x += 190 + separacion


def dibujar_decision_presente(panel, superficie, contexto, opciones, falta, mensaje, votos):
    """La pantalla pública de Distrito Conecta: una publicación y qué hacer con ella."""
    recursos = panel.vista.escenas
    r = recursos.r
    superficie.blit(recursos.fondo_presente, (0, 0))
    titulo = r["fuente_resultado"].render("¿QUÉ HACEMOS CON ESTA PUBLICACIÓN?", True, TURQUESA)
    superficie.blit(titulo, titulo.get_rect(center=(480, 34)))
    panel.texto_lineas(superficie, mensaje, 70, 60, 820, r["fuente_mapa"], ORO if falta else CREMA)
    panel.texto_lineas(superficie, votos, 70, 86, 820, r["fuente_panel"], VERDE)
    caja = pygame.Rect(190, 152, 580, 240)
    pantalla(superficie, caja)
    cabecera = pygame.Rect(caja.x + 2, caja.y + 2, caja.width - 4, 36)
    pygame.draw.rect(superficie, (24, 62, 84), cabecera, border_top_left_radius=10, border_top_right_radius=10)
    etiqueta = r["fuente_panel_titulo"].render("PANTALLA PÚBLICA", True, TURQUESA)
    superficie.blit(etiqueta, etiqueta.get_rect(midleft=(caja.x + 18, cabecera.centery)))
    if recursos.icono_publicacion is not None:
        superficie.blit(recursos.icono_publicacion, recursos.icono_publicacion.get_rect(center=(caja.x + 78, caja.y + 132)))
    y = panel.texto_lineas(superficie, contexto.get("titulo", ""), caja.x + 150, caja.y + 56, 405, r["fuente_mapa"], ORO)
    panel.texto_lineas(superficie, contexto.get("noticia", ""), caja.x + 150, y + 8, 405, r["fuente_mapa"], CREMA)
    from interfaz.boton import Boton
    ancho, separacion = TAMANO_TARJETA[0], 20
    x = (960 - (ancho * len(opciones) + separacion * (len(opciones) - 1))) // 2 + ancho // 2
    for clave, texto in opciones.items():
        boton = Boton(texto, recursos.tarjeta_presente(clave, texto), (x, 510), r["fuente_boton"], desactivado=bool(falta))
        boton.dibujar(superficie, panel.vista.mouse)
        panel.botones["presente_votar:" + clave] = boton
        if panel.privado_voto(contexto) == clave:
            pygame.draw.rect(superficie, ORO, boton.rect.inflate(6, 6), 3, border_radius=14)
        x += ancho + separacion


def dibujar_consecuencia(panel, superficie, resultado, dimension):
    """Mismo panel que un_jugador.tablilla.dibujar_consecuencia_evento, con colores por
    polaridad: verde si ayuda (bueno↑ o malo↓), rojo si perjudica."""
    recursos = panel.vista.escenas
    r = recursos.r
    presente = en_presente(dimension)
    superficie.blit(recursos.fondo_presente if presente else recursos.fondo_tablilla, (0, 0))
    rect = pygame.Rect(178, 150, 604, 400)
    fondo = pygame.Surface(rect.size, pygame.SRCALPHA)
    fondo.fill((*PANTALLA, 242) if presente else (18, 36, 29, 238))
    superficie.blit(fondo, rect)
    color = TURQUESA if presente else ORO
    pygame.draw.rect(superficie, color, rect, 3, border_radius=16)
    titulo = r["fuente_panel_titulo"].render("CONSECUENCIA DE LA DECISIÓN", True, color)
    superficie.blit(titulo, titulo.get_rect(center=(rect.centerx, rect.y + 40)))
    tipo = resultado.get("tipo_pocion")
    icono = recursos.iconos_presente.get(resultado.get("opcion")) if presente else r["pociones"].get(tipo)
    if icono is not None:
        if presente:
            icono = pygame.transform.scale(icono, (icono.get_width() * 2 // 3, icono.get_height() * 2 // 3))
        superficie.blit(icono, icono.get_rect(center=(rect.x + 50, rect.y + 40)))
        superficie.blit(icono, icono.get_rect(center=(rect.right - 50, rect.y + 40)))
    y = panel.texto_lineas(superficie, resultado.get("texto", ""), rect.x + 40, rect.y + 80, rect.width - 80, r["fuente_mapa"])
    y += 8
    for nombre in ORDEN_INDICADORES:
        cambio = resultado.get("efectos", {}).get(nombre)
        if not cambio or nombre not in POLARIDAD:
            continue
        texto = r["fuente_panel"].render(texto_cambio(nombre, cambio, dimension), True, color_cambio(nombre, cambio))
        superficie.blit(texto, texto.get_rect(center=(rect.centerx, y + 10)))
        y += 24
    return rect


def dibujar_minijuego(panel, superficie, puente, tiempo_aguja_ms, estado_indicador):
    """Mismo minijuego que SistemaReparacionPuente.dibujar_interfaz."""
    recursos = panel.vista.escenas
    fuente, titulo_f = recursos.r["fuente_mapa"], recursos.r["fuente_panel_titulo"]
    rect = pygame.Rect(260, 145, 440, 425)
    velo = pygame.Surface(superficie.get_size(), pygame.SRCALPHA)
    velo.fill((0, 0, 0, 105))
    superficie.blit(velo, (0, 0))
    pygame.draw.rect(superficie, (19, 38, 31), rect, border_radius=14)
    pygame.draw.rect(superficie, ORO, rect, 3, border_radius=14)
    titulo = titulo_f.render("REPARAR EL PUENTE", True, (255, 228, 148))
    superficie.blit(titulo, titulo.get_rect(center=(rect.centerx, rect.y + 30)))
    progreso = puente.get("progreso", 0)
    indicador = recursos.indicador_rotado(estado_indicador, progreso)
    if indicador:
        caja = indicador.get_rect(center=(rect.centerx, rect.y + 215))
        superficie.blit(indicador, caja)
        angulo = angulo_aguja(tiempo_aguja_ms)
        extremo = (round(caja.centerx + math.cos(angulo) * 78), round(caja.centery + math.sin(angulo) * 78))
        pygame.draw.line(superficie, (255, 249, 218), caja.center, extremo, 5)
        pygame.draw.circle(superficie, (43, 35, 27), caja.center, 10)
        pygame.draw.circle(superficie, (255, 211, 100), caja.center, 6)
    else:
        panel.texto_lineas(superficie, "Falta Indicadores Puente/Indicador.png", rect.x + 30, rect.y + 200, 380, fuente)
    total = puente.get("total", 3)
    for i in range(total):
        centro = (rect.centerx - (total - 1) * 22 + i * 44, rect.bottom - 70)
        pygame.draw.circle(superficie, (102, 200, 112) if i < progreso else (42, 69, 49), centro, 13)
        pygame.draw.circle(superficie, ORO, centro, 13, 2)
    texto = fuente.render(f"Aciertos: {progreso}/{total}    Pulsa E en la zona verde", True, CREMA)
    superficie.blit(texto, texto.get_rect(center=(rect.centerx, rect.bottom - 34)))
    ayuda = recursos.r["fuente_panel"].render("ESC: dejar que otro compañero lo intente", True, VERDE)
    superficie.blit(ayuda, ayuda.get_rect(center=(rect.centerx, rect.y + 56)))


def dibujar_portal(panel, superficie, destinos, origen):
    from interfaz.boton import Boton
    r = panel.vista.escenas.r
    velo = pygame.Surface((960, 720), pygame.SRCALPHA)
    velo.fill((4, 12, 20, 205))
    superficie.blit(velo, (0, 0))
    rect = pygame.Rect(170, 120, 620, 440)
    pygame.draw.rect(superficie, (14, 32, 36), rect, border_radius=16)
    pygame.draw.rect(superficie, (106, 218, 204), rect, 3, border_radius=16)
    titulo = r["fuente_resultado"].render("¿A QUÉ ÉPOCA VIAJAMOS?", True, (231, 255, 247))
    superficie.blit(titulo, titulo.get_rect(center=(480, 168)))
    viaje = panel.vista.viaje()
    if viaje:
        acepte = panel.vista.identificador in viaje["aceptan"]
        estado = ("Aceptaste ir a " + viaje["nombre"] + "." if acepte else "Proponen ir a " + viaje["nombre"] + ".")
        if viaje["faltan"]:
            estado += " Faltan: " + ", ".join(viaje["faltan"]) + "."
        panel.texto_lineas(superficie, estado, 210, 200, 540, r["fuente_panel"], (255, 222, 112))
    else:
        panel.texto_lineas(superficie, "El equipo viaja junto: todos deben venir al portal y aceptar. "
                           "Los indicadores viajan con ustedes.", 210, 200, 540, r["fuente_panel"], VERDE)
    for i, destino in enumerate(destinos):
        texto = destino["epoca"] + " · " + destino["nombre"] + ("" if destino["disponible"] else " (en construcción)")
        if viaje and viaje["destino"] == destino["id"] and panel.vista.identificador not in viaje["aceptan"]:
            texto = "Aceptar: " + texto
        boton = Boton(texto, centro=(480, 290 + i * 78), fuente=r["fuente_boton"], tamano=(470, 58),
                      desactivado=not destino["disponible"])
        boton.dibujar(superficie, panel.vista.mouse)
        panel.botones["viajar:" + destino["id"]] = boton
        emblema = panel.vista.arte.emblemas_portal.get(destino["id"])
        if emblema is not None:
            superficie.blit(emblema, emblema.get_rect(center=(208, 290 + i * 78)))
    if viaje and panel.vista.identificador in viaje["aceptan"]:
        boton = Boton("Ya no quiero viajar", centro=(480, 515), fuente=r["fuente_boton"], tamano=(330, 48))
        boton.dibujar(superficie, panel.vista.mouse)
        panel.botones["cancelar_portal"] = boton


class Transicion:
    """Fundido del modo de un jugador (velo, anillos y título del destino)."""

    DURACION = 2.6

    def __init__(self, nombre, emblema=None):
        self.nombre = nombre
        self.emblema = emblema.copy() if emblema is not None else None
        self.t = 0.0

    @property
    def terminada(self):
        return self.t >= self.DURACION

    def actualizar(self, segundos, particulas):
        anterior = self.t
        self.t += segundos
        if int(anterior / .26) != int(self.t / .26) and self.t < 1.6:
            particulas.emitir(480, 360, 5)

    def dibujar(self, superficie, fuente):
        t = self.t
        alpha = round(235 * (1 - min(1, max(0, t - 1.2) / 1.2))) if t > 1.2 else round(235 * min(1, t / .5))
        velo = pygame.Surface((960, 720), pygame.SRCALPHA)
        velo.fill((5, 14, 24, max(0, alpha)))
        superficie.blit(velo, (0, 0))
        fase = min(1.0, t / 1.4)
        for indice in range(3):
            radio = round((40 + ((t * 180 + indice * 92) % 310)) * fase)
            if radio > 0:
                pygame.draw.circle(superficie, (69, 220, 210), (480, 360), radio, 2)
        if t > .6:
            titulo = fuente.render(self.nombre.upper(), True, (231, 255, 247))
            opacidad = round(255 * min(1, (t - .6) / .4) * min(1, (self.DURACION - t) / .5))
            titulo.set_alpha(opacidad)
            superficie.blit(titulo, titulo.get_rect(center=(480, 108)))
            if self.emblema is not None:
                self.emblema.set_alpha(opacidad)
                superficie.blit(self.emblema, self.emblema.get_rect(center=(480, 360)))


def etiquetas_hud(dimension):
    return ETIQUETAS.get(dimension, ETIQUETAS["la_copa"])


def nombre_pocion(tipo):
    return NOMBRES_POCION.get(tipo, tipo)
