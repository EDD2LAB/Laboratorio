"""Efectos visuales con el arte real del proyecto, compartidos por ambos modos.

Reglas: cada PNG se carga y escala una sola vez (pygame.transform.scale,
vecino más cercano), las rotaciones se guardan en caché y si falta un
recurso se registra la ruta esperada y se usa un respaldo de desarrollo.
"""
import math
from pathlib import Path

import pygame

IMAGENES = Path(__file__).resolve().parent.parent / "Imagenes"
RUTAS = {
    "flecha": IMAGENES / "Iconos" / "Objetos varios" / "IndicadorDirrKael.png",
    "marcador": IMAGENES / "Iconos" / "Multijugador" / "FlechaPersonaje.png",
    "portal": IMAGENES / "Portal" / "portal_fila_8frames.png",
    "destello": IMAGENES / "Animaciones" / "Destello.png",
    "reparacion": IMAGENES / "Animaciones" / "Efectos" / "EfectoReparacion.png",
}
ANILLOS = {
    "guardian": "AnilloTurquesa.png",
    "mensajero": "AnilloDorado.png",
    "habitante": "AnilloVioleta.png",
    "aspirante": "AnilloCoral.png",
}
_cache = {}
_faltantes = set()


def _cargar(ruta):
    try:
        imagen = pygame.image.load(str(ruta))
        return imagen.convert_alpha() if pygame.display.get_surface() is not None else imagen
    except (pygame.error, FileNotFoundError, OSError):
        if ruta not in _faltantes:
            _faltantes.add(ruta)
            print(f"[Efectos] Falta el recurso esperado: {ruta}")
        return None


def recorte_visible(imagen, umbral=48):
    """Límites del arte visible, ignorando halos casi transparentes."""
    rects = pygame.mask.from_surface(imagen, umbral).get_bounding_rects()
    if not rects:
        return None
    return rects[0].unionall(rects[1:])


def escalar_alto(imagen, alto):
    escala = alto / imagen.get_height()
    return pygame.transform.scale(imagen, (max(1, round(imagen.get_width() * escala)), max(1, round(alto))))


def tira(ruta, cantidad, alto=None, recortar=True):
    clave = ("tira", str(ruta), cantidad, alto, recortar)
    if clave not in _cache:
        imagen = _cargar(ruta)
        cuadros = []
        if imagen is not None:
            ancho = imagen.get_width() / cantidad
            for indice in range(cantidad):
                x = round(indice * ancho)
                cuadro = imagen.subsurface((x, 0, round((indice + 1) * ancho) - x, imagen.get_height()))
                if recortar:
                    limites = recorte_visible(cuadro)
                    if limites is None:
                        continue
                    cuadro = cuadro.subsurface(limites)
                cuadros.append(escalar_alto(cuadro, alto) if alto else cuadro.copy())
        _cache[clave] = cuadros
    return _cache[clave]


def imagen(ruta, tamano=None, alto=None):
    clave = ("img", str(ruta), tamano, alto)
    if clave not in _cache:
        base = _cargar(ruta)
        if base is not None:
            limites = base.get_bounding_rect()
            base = base.subsurface(limites) if limites.width else base
            base = pygame.transform.scale(base, tamano) if tamano else escalar_alto(base, alto) if alto else base.copy()
        _cache[clave] = base
    return _cache[clave]


def halo(radio, color):
    """Gradiente radial RGB para mezclar con BLEND_RGB_ADD (en caché)."""
    clave = ("halo", radio, color)
    if clave not in _cache:
        sup = pygame.Surface((radio * 2, radio * 2))
        sup.fill((0, 0, 0))
        for r in range(radio, 0, -1):
            k = (1 - r / radio) ** 2
            pygame.draw.circle(sup, tuple(round(c * k) for c in color), (radio, radio), r)
        _cache[clave] = sup
    return _cache[clave]


class FlechaGuia:
    """Flecha de hojas animada (8 cuadros) que señala un objetivo.

    Sustituye al polígono amarillo dibujado por código: misma lógica de
    orientación (desde el jugador hacia el objetivo) y mismos márgenes.
    """

    ALTO = 36
    PASO_GRADOS = 6

    def __init__(self):
        self.cuadros = tira(RUTAS["flecha"], 8, self.ALTO)
        self._rotadas = {}

    def _rotada(self, indice, grados):
        paso = round(grados / self.PASO_GRADOS) * self.PASO_GRADOS % 360
        clave = (indice, paso)
        if clave not in self._rotadas:
            # El arte apunta a la derecha (0°); pygame rota en sentido antihorario.
            self._rotadas[clave] = pygame.transform.rotate(self.cuadros[indice], -paso)
        return self._rotadas[clave]

    def dibujar(self, superficie, origen, destino, tiempo_ms, limites=None, margen_inferior=122):
        origen, destino = pygame.Vector2(origen), pygame.Vector2(destino)
        direccion = destino - origen
        if direccion.length_squared() < 1:
            return None
        distancia = direccion.length()
        direccion = direccion.normalize()
        ancho, alto = superficie.get_size()
        # Respira hacia el objetivo para invitar a seguirla.
        pulso = (math.sin(tiempo_ms / 170) + 1) / 2
        centro = origen + direccion * (min(62, max(34, distancia * .5)) + pulso * 8)
        izquierda, arriba, derecha, abajo = limites or (30, 42, ancho - 30, alto - margen_inferior)
        centro.x = max(izquierda, min(derecha, centro.x))
        centro.y = max(arriba, min(abajo, centro.y))
        superficie.blit(halo(28, (78, 70, 20)), (centro.x - 28, centro.y - 28), special_flags=pygame.BLEND_RGB_ADD)
        if self.cuadros:
            indice = (tiempo_ms // 95) % len(self.cuadros)
            grados = math.degrees(math.atan2(direccion.y, direccion.x))
            sprite = self._rotada(indice, grados)
            sombra = sprite.copy()
            sombra.fill((0, 0, 0, 110), special_flags=pygame.BLEND_RGBA_MIN)
            superficie.blit(sombra, sombra.get_rect(center=(centro.x + 2, centro.y + 3)))
            superficie.blit(sprite, sprite.get_rect(center=centro))
        else:  # Respaldo de desarrollo si falta IndicadorDirrKael.png.
            perp = pygame.Vector2(-direccion.y, direccion.x)
            puntos = [centro + direccion * 15, centro - direccion * 12 + perp * 9, centro - direccion * 12 - perp * 9]
            pygame.draw.polygon(superficie, (255, 207, 48), puntos)
        return centro


class AdornosMapa:
    """Anillos de rol, marcador del jugador local, portal y ruta de destellos."""

    def __init__(self):
        self.anillos = {rol: imagen(IMAGENES / "Iconos" / "Multijugador" / nombre, (34, 15))
                        for rol, nombre in ANILLOS.items()}
        self.anillos_objetivo = {rol: imagen(IMAGENES / "Iconos" / "Multijugador" / nombre, (46, 20))
                                 for rol, nombre in ANILLOS.items()}
        self.marcador = imagen(RUTAS["marcador"], alto=10)
        self.destellos = tira(RUTAS["destello"], 8, 12)
        self.portal = tira(RUTAS["portal"], 8, recortar=False)
        self._portal_escalado = {}

    def _reducido(self, imagen, escala):
        """El anillo a menor tamaño (personajes pequeños), escalado una sola vez."""
        clave = ("reducido", id(imagen), escala)
        if clave not in _cache:
            _cache[clave] = pygame.transform.scale(
                imagen, (max(1, round(imagen.get_width() * escala)), max(1, round(imagen.get_height() * escala))))
        return _cache[clave]

    def anillo_jugador(self, superficie, rol, centro, color, escala=1):
        anillo = self.anillos.get(rol)
        if anillo:
            anillo = self._reducido(anillo, escala) if escala != 1 else anillo
            superficie.blit(anillo, anillo.get_rect(center=centro))
        else:
            pygame.draw.ellipse(superficie, color, (centro[0] - 14, centro[1] - 5, 28, 9), 2)

    def anillo_objetivo(self, superficie, centro, rol, tiempo_ms, escala_base=1):
        """Anillo que late sobre el suelo del objetivo actual."""
        base = self.anillos_objetivo.get(rol) or self.anillos_objetivo.get("mensajero")
        paso = round(4 * (1 + math.sin(tiempo_ms / 220)))  # 0..8: escalas en caché
        superficie.blit(halo(26, (40, 52, 22)), (centro[0] - 26, centro[1] - 26), special_flags=pygame.BLEND_RGB_ADD)
        if base:
            clave = ("anillo", rol, paso)
            if clave not in _cache:
                escala = .88 + paso * .03
                _cache[clave] = pygame.transform.scale(base, (round(base.get_width() * escala), round(base.get_height() * escala)))
            anillo = self._reducido(_cache[clave], escala_base) if escala_base != 1 else _cache[clave]
            superficie.blit(anillo, anillo.get_rect(center=centro))
        else:
            pygame.draw.ellipse(superficie, (237, 185, 87), (centro[0] - 20, centro[1] - 8, 40, 16), 2)

    def marcador_local(self, superficie, punta, color, tiempo_ms):
        y = punta[1] - 3 + round(math.sin(tiempo_ms / 160) * 2)
        if self.marcador:
            superficie.blit(self.marcador, self.marcador.get_rect(midbottom=(punta[0], y)))
        else:
            pygame.draw.polygon(superficie, color, ((punta[0] - 5, y - 6), (punta[0] + 5, y - 6), (punta[0], y)))

    def ruta(self, superficie, puntos, tiempo_ms):
        """Camino de destellos que avanzan hacia el objetivo."""
        if not puntos:
            return
        avance = tiempo_ms / 280
        for i, punto in enumerate(puntos):
            if i % 3:
                continue
            fase = (i / 3 - avance) % 4
            if fase > 2.2:
                continue
            superficie.blit(halo(7, (60, 50, 16)), (punto[0] - 7, punto[1] - 7), special_flags=pygame.BLEND_RGB_ADD)
            if self.destellos:
                cuadro = self.destellos[int(fase * 3) % len(self.destellos)]
                superficie.blit(cuadro, cuadro.get_rect(center=punto))
            else:
                pygame.draw.circle(superficie, (255, 224, 121), punto, 2)

    def dibujar_portal(self, superficie, rect, tiempo_ms, activo=True):
        if not self.portal:
            return
        rect = pygame.Rect(rect)
        if rect.size not in self._portal_escalado:
            self._portal_escalado[rect.size] = [pygame.transform.scale(c, rect.size) for c in self.portal]
        cuadros = self._portal_escalado[rect.size]
        # Cuadros 3 y 7 = portal abierto; 2 y 6 = encendiéndose.
        secuencia = (2, 3, 7, 3) if activo else (0, 4)
        cuadro = cuadros[secuencia[(tiempo_ms // 160) % len(secuencia)]]
        brillo = halo(rect.width // 2 + 12, (20, 60, 62))
        superficie.blit(brillo, brillo.get_rect(center=rect.center), special_flags=pygame.BLEND_RGB_ADD)
        superficie.blit(cuadro, rect)
