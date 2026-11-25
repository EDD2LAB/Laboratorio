"""Minijuego de reparación del puente: medidor fijo, zona verde por código y aguja.

El medidor (``Indicador_base.png``) nunca se rota. La zona verde se dibuja encima
como un sector anular con la MISMA geometría que ``dentro_de_zona``: centro en
``angulo_objetivo(progreso)`` y semiancho ``tolerancia_angulo``. Ángulos en
radianes con el eje y hacia abajo: −π a la izquierda, −π/2 arriba y 0 a la derecha.

Respaldos: sin ``Indicador_base.png`` se usa el sistema anterior (``Indicador.png``
rotado); sin ``Aguja_base.png``, ``aguja7.png``; sin ninguna aguja, una raya.
"""
import json
import math

import pygame

from multijugador.reparacion import CONFIGURACION, angulo_objetivo
from nucleo.rutas import IMAGENES

LADO_MEDIDOR = 220
RADIO_CARA_RESPALDO = 64.0  # si falta Indicador_base.json (medida del medidor actual)
ZONA_INTERIOR, ZONA_EXTERIOR = .55, .85  # fracciones del radio de la cara
LARGO_AGUJA_RELATIVO = .8
LARGO_AGUJA_VIEJA = 84  # px desde la perilla hasta la punta (sistema anterior)
TAMANO_FICHA = (46, 25)
PASOS_ARCO = 48
ORO = (237, 185, 87)
ORO_CLARO = (255, 228, 148)
CREMA = (255, 243, 210)
VERDE_TEXTO = (130, 222, 158)
VERDE_ZONA = (145, 232, 26)
ROJO_ERROR = (255, 59, 59)
ESTADOS_ZONA = ("normal", "acierto")
CARPETA = "Indicadores Puente/"
CARPETA_VIEJA = "Expediente/Indicadores-puente/"


def puntos_zona(centro, radio_cara, progreso, configuracion=CONFIGURACION):
    """Polígono del sector anular de la zona verde (misma regla que dentro_de_zona)."""
    objetivo = angulo_objetivo(progreso, configuracion)
    tolerancia = configuracion["tolerancia_angulo"]
    interior, exterior = radio_cara * ZONA_INTERIOR, radio_cara * ZONA_EXTERIOR
    angulos = [objetivo - tolerancia + 2 * tolerancia * i / PASOS_ARCO for i in range(PASOS_ARCO + 1)]
    cx, cy = centro
    afuera = [(cx + exterior * math.cos(a), cy + exterior * math.sin(a)) for a in angulos]
    adentro = [(cx + interior * math.cos(a), cy + interior * math.sin(a)) for a in reversed(angulos)]
    return afuera + adentro


def superficie_zona(lado, radio_cara, progreso, estado):
    """Zona verde lista para pegar sobre el medidor (se crea una vez por progreso y estado)."""
    capa = pygame.Surface((lado, lado), pygame.SRCALPHA)
    puntos = puntos_zona((lado / 2, lado / 2), radio_cara, progreso)
    if estado == "acierto":
        pygame.draw.polygon(capa, (196, 255, 92, 225), puntos)
        pygame.draw.polygon(capa, ORO_CLARO, puntos, 2)
    else:
        pygame.draw.polygon(capa, (*VERDE_ZONA, 150), puntos)
        pygame.draw.polygon(capa, ORO, puntos, 2)
    return capa


def superficie_destello(lado, radio_cara):
    """Aro rojo del error, sobre el borde de madera del medidor."""
    capa = pygame.Surface((lado, lado), pygame.SRCALPHA)
    centro = (lado // 2, lado // 2)
    pygame.draw.circle(capa, (*ROJO_ERROR, 120), centro, round(radio_cara * 1.32), max(4, round(radio_cara * .3)))
    pygame.draw.circle(capa, (*ROJO_ERROR, 235), centro, round(radio_cara * 1.04), 4)
    return capa


def _leer_radio_cara():
    try:
        datos = json.loads((IMAGENES / "Indicadores Puente" / "Indicador_base.json").read_text(encoding="utf-8"))
        return float(datos["radio_cara"]) * LADO_MEDIDOR / float(datos.get("lado", LADO_MEDIDOR))
    except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError):
        return RADIO_CARA_RESPALDO


class RecursosPuente:
    """Carga única (después de set_mode) de todo lo que dibuja el minijuego."""

    def __init__(self, cargar=None):
        if cargar is None:
            from nucleo.recursos import cargar_imagen as cargar
        lado = LADO_MEDIDOR
        self.medidor = cargar(CARPETA + "Indicador_base.png", (lado, lado), requerido=False)
        self.radio_cara = _leer_radio_cara() if self.medidor is not None else RADIO_CARA_RESPALDO
        self.indicadores_viejos = {}
        if self.medidor is None:  # respaldo: el medidor anterior, que se rota con el progreso
            self.indicadores_viejos = {
                estado: cargar(CARPETA + archivo, (lado, lado), requerido=False)
                for estado, archivo in (("normal", "Indicador.png"), ("acierto", "IndicadorAcierto.png"),
                                        ("error", "IndicadorError.png"))}
        self.zonas = {}
        self.destello = None
        if self.medidor is not None:
            for progreso in range(CONFIGURACION["aciertos_necesarios"] + 1):
                for estado in ESTADOS_ZONA:
                    self.zonas[progreso, estado] = superficie_zona(lado, self.radio_cara, progreso, estado)
            self.destello = superficie_destello(lado, self.radio_cara)
        self.largo_aguja = (round(self.radio_cara * LARGO_AGUJA_RELATIVO) if self.medidor is not None
                            else LARGO_AGUJA_VIEJA)
        self.aguja, self.origen_aguja = self._cargar_aguja(cargar)
        self.fichas = {}
        for estado, archivo in (("logrado", "ficha_logrado.png"), ("vacio", "ficha_vacio.png")):
            ficha = cargar(CARPETA_VIEJA + archivo, requerido=False)
            if ficha is not None:
                ficha = ficha.subsurface(ficha.get_bounding_rect(min_alpha=128))
                self.fichas[estado] = pygame.transform.scale(ficha, TAMANO_FICHA)
        self._agujas = {}
        self._rotados = {}

    def _cargar_aguja(self, cargar):
        """Lienzo cuadrado con el eje de la aguja en el centro y la punta hacia arriba."""
        largo = self.largo_aguja
        nueva = cargar(CARPETA + "Aguja_base.png", (2 * largo + 1, 2 * largo + 1), requerido=False)
        if nueva is not None:  # ya viene con el remache en el centro del lienzo
            return nueva, "Aguja_base"
        vieja = cargar(CARPETA_VIEJA + "aguja7.png", requerido=False)
        if vieja is None:
            return None, "raya"
        vieja = vieja.subsurface(vieja.get_bounding_rect(min_alpha=40))
        ancho = max(4, round(vieja.get_width() * largo / vieja.get_height()))
        vieja = pygame.transform.scale(vieja, (ancho, largo))
        lienzo = pygame.Surface((2 * largo, 2 * largo), pygame.SRCALPHA)
        lienzo.blit(vieja, vieja.get_rect(midbottom=(largo, largo + ancho // 2)))
        return lienzo, "aguja7"

    @property
    def disponible(self):
        return self.medidor is not None or bool(self.indicadores_viejos.get("normal"))

    def aguja_rotada(self, angulo):
        """La aguja apuntando a ``angulo`` (radianes, eje y hacia abajo), en pasos de 2 grados."""
        if self.aguja is None:
            return None
        grados = round((-math.degrees(angulo) - 90) / 2) * 2
        if grados not in self._agujas:
            self._agujas[grados] = pygame.transform.rotate(self.aguja, grados)
        return self._agujas[grados]

    def capas(self, estado, progreso):
        """(medidor, zona) para el medidor nuevo; el medidor es siempre la misma superficie."""
        clave = min(progreso, CONFIGURACION["aciertos_necesarios"])
        return self.medidor, self.zonas.get((clave, "acierto" if estado == "acierto" else "normal"))

    def indicador_rotado(self, estado, progreso):
        """Respaldo: el medidor anterior rotado (solo si falta Indicador_base.png)."""
        base = self.indicadores_viejos.get(estado) or self.indicadores_viejos.get("normal")
        if base is None or not progreso:
            return base
        clave = (estado, progreso)
        if clave not in self._rotados:
            grados = math.degrees(progreso * CONFIGURACION["rotacion_objetivo_por_acierto"])
            rotada = pygame.transform.rotate(base, grados)
            lienzo = pygame.Surface(base.get_size(), pygame.SRCALPHA)
            lienzo.blit(rotada, rotada.get_rect(center=lienzo.get_rect().center))
            self._rotados[clave] = lienzo
        return self._rotados[clave]


def dibujar_medidor(superficie, recursos, centro, progreso, angulo, estado="normal", fase=None):
    """Medidor, zona, efectos del resultado y UNA aguja. ``fase`` va de 0 a 1 durante el resultado."""
    if recursos.medidor is not None:
        medidor, zona = recursos.capas(estado, progreso)
        caja = medidor.get_rect(center=centro)
        superficie.blit(medidor, caja)
        if zona is not None:
            superficie.blit(zona, caja)
        if fase is not None and estado == "acierto":
            _chispas(superficie, caja.center, recursos.radio_cara, progreso, fase)
        elif fase is not None and estado == "error" and recursos.destello is not None:
            recursos.destello.set_alpha(round(255 * (1 - fase * .7)))
            superficie.blit(recursos.destello, caja)
    else:
        indicador = recursos.indicador_rotado(estado, progreso)
        if indicador is None:
            return False
        caja = indicador.get_rect(center=centro)
        superficie.blit(indicador, caja)
    aguja = recursos.aguja_rotada(angulo)
    if aguja is not None:
        superficie.blit(aguja, aguja.get_rect(center=caja.center))
    else:
        largo = recursos.largo_aguja
        extremo = (round(caja.centerx + math.cos(angulo) * largo), round(caja.centery + math.sin(angulo) * largo))
        pygame.draw.line(superficie, (255, 249, 218), caja.center, extremo, 5)
        pygame.draw.circle(superficie, (43, 35, 27), caja.center, 10)
        pygame.draw.circle(superficie, (255, 211, 100), caja.center, 6)
    return True


def _chispas(superficie, centro, radio_cara, progreso, fase):
    """Chispas doradas breves que salen de la zona tras un acierto."""
    objetivo = angulo_objetivo(progreso)  # salen de la zona que se ve en ese momento
    tolerancia = CONFIGURACION["tolerancia_angulo"]
    radio = radio_cara * (ZONA_EXTERIOR + .1 + .35 * fase)
    tamano = max(1, round(4 * (1 - fase)))
    for i in range(9):
        angulo = objetivo - tolerancia + 2 * tolerancia * i / 8
        punto = (round(centro[0] + radio * math.cos(angulo)), round(centro[1] + radio * math.sin(angulo)))
        pygame.draw.circle(superficie, (255, 215, 90), punto, tamano + (i % 2))
        if tamano > 1:
            pygame.draw.circle(superficie, (255, 250, 210), punto, tamano - 1)


def dibujar_panel(superficie, recursos, fuentes, puente, angulo, estado="normal", fase=None):
    """Panel completo del minijuego (lo usan la partida y la herramienta de vista)."""
    fuente, titulo_f, chica = fuentes["fuente_mapa"], fuentes["fuente_panel_titulo"], fuentes["fuente_panel"]
    rect = pygame.Rect(260, 145, 440, 425)
    velo = pygame.Surface(superficie.get_size(), pygame.SRCALPHA)
    velo.fill((0, 0, 0, 105))
    superficie.blit(velo, (0, 0))
    pygame.draw.rect(superficie, (19, 38, 31), rect, border_radius=14)
    pygame.draw.rect(superficie, ORO, rect, 3, border_radius=14)
    titulo = titulo_f.render("REPARAR EL PUENTE", True, ORO_CLARO)
    superficie.blit(titulo, titulo.get_rect(center=(rect.centerx, rect.y + 30)))
    progreso = puente.get("progreso", 0)
    if not dibujar_medidor(superficie, recursos, (rect.centerx, rect.y + 215), progreso, angulo, estado, fase):
        aviso = fuente.render("Falta Indicadores Puente/Indicador_base.png", True, CREMA)
        superficie.blit(aviso, aviso.get_rect(center=(rect.centerx, rect.y + 215)))
    total = puente.get("total", 3)
    fichas = recursos.fichas
    paso = TAMANO_FICHA[0] + 8 if len(fichas) == 2 else 44
    for i in range(total):
        centro = (rect.centerx - (total - 1) * paso // 2 + i * paso, rect.bottom - 70)
        if len(fichas) == 2:
            ficha = fichas["logrado" if i < progreso else "vacio"]
            superficie.blit(ficha, ficha.get_rect(center=centro))
            continue
        pygame.draw.circle(superficie, (102, 200, 112) if i < progreso else (42, 69, 49), centro, 13)
        pygame.draw.circle(superficie, ORO, centro, 13, 2)
    texto = fuente.render(f"Aciertos: {progreso}/{total}    Pulsa E en la zona verde", True, CREMA)
    superficie.blit(texto, texto.get_rect(center=(rect.centerx, rect.bottom - 34)))
    ayuda = chica.render("ESC: dejar que otro compañero lo intente", True, VERDE_TEXTO)
    superficie.blit(ayuda, ayuda.get_rect(center=(rect.centerx, rect.y + 56)))
