"""Efectos ambientales ligeros para el mapa, sin colisiones ni hojas.

Usa el arte real del proyecto: ``Animales/Luciernaga.png`` (8 cuadros) para
las luciérnagas y ``Animaciones/Destello.png`` (8 cuadros) para las chispas
mágicas. Los sprites se cargan y escalan UNA vez (vecino más cercano) y los
halos se generan una vez y se reutilizan; nada se crea dentro del bucle.
Si falta un PNG se registra su ruta y se usa el dibujo de respaldo.
"""

import math
import random
from pathlib import Path

import pygame

RAIZ_IMAGENES = Path(__file__).resolve().parent.parent / "Imagenes"
RUTA_LUCIERNAGA = RAIZ_IMAGENES / "Animales" / "Luciernaga.png"
RUTA_DESTELLO = RAIZ_IMAGENES / "Animaciones" / "Destello.png"


def _cargar_tira(ruta, cantidad, alto_objetivo):
    """Separa una tira horizontal en cuadros recortados y escalados."""
    try:
        imagen = pygame.image.load(str(ruta))
        if pygame.display.get_surface() is not None:
            imagen = imagen.convert_alpha()
    except (pygame.error, FileNotFoundError, OSError) as error:
        print(f"[Partículas] Falta el recurso {ruta}: {error}")
        return []
    ancho = imagen.get_width() / cantidad
    cuadros = []
    for indice in range(cantidad):
        x = round(indice * ancho)
        cuadro = imagen.subsurface((x, 0, round((indice + 1) * ancho) - x, imagen.get_height()))
        # Umbral de alfa: ignora halos casi transparentes al recortar.
        rects = pygame.mask.from_surface(cuadro, 48).get_bounding_rects()
        if not rects:
            continue
        cuadro = cuadro.subsurface(rects[0].unionall(rects[1:]))
        escala = alto_objetivo / cuadro.get_height()
        cuadros.append(pygame.transform.scale(
            cuadro, (max(1, round(cuadro.get_width() * escala)), max(1, round(alto_objetivo)))))
    return cuadros


def _halo(radio, color):
    """Gradiente radial en RGB para mezclar con suma (sin alfa por píxel)."""
    superficie = pygame.Surface((radio * 2, radio * 2))
    superficie.fill((0, 0, 0))
    for r in range(radio, 0, -1):
        intensidad = (1 - r / radio) ** 2
        pygame.draw.circle(superficie, tuple(round(c * intensidad) for c in color), (radio, radio), r)
    return superficie


class SistemaParticulas:
    """Actualiza luciérnagas y partículas mágicas con delta_ms."""

    MAX_LUCIERNAGAS = 12
    MAX_PARTICULAS = 60
    PALETA = ((111, 219, 150), (93, 218, 205), (238, 201, 92))
    RADIO_BRILLO = 9
    _sprites = None

    def __init__(self, ancho, alto, semilla=None):
        self.ancho = ancho
        self.alto = alto
        self.rng = random.Random(semilla)
        self.tiempo = 0.0
        self.mostrar_luciernagas = True
        self.paleta = self.PALETA
        self.luciernagas = [
            self._nueva_luciernaga(indice) for indice in range(self.MAX_LUCIERNAGAS)
        ]
        self.particulas = []
        self._superficies_luciernaga = {}
        self._halos = {}

    @classmethod
    def _recursos(cls):
        if cls._sprites is None:
            luciernaga = _cargar_tira(RUTA_LUCIERNAGA, 8, 11)
            cls._sprites = {
                "luciernaga": luciernaga,
                "luciernaga_izquierda": [pygame.transform.flip(c, True, False) for c in luciernaga],
                "destellos": {tam: _cargar_tira(RUTA_DESTELLO, 8, tam) for tam in (7, 10, 13, 16)},
            }
        return cls._sprites

    def _halo(self, radio, color):
        clave = (radio, color)
        if clave not in self._halos:
            self._halos[clave] = _halo(radio, color)
        return self._halos[clave]

    def configurar_dimension(self, dimension):
        if dimension == "presente":
            self.mostrar_luciernagas = False
            self.paleta = ((62, 210, 206), (99, 185, 241), (170, 239, 230))
        else:
            self.mostrar_luciernagas = True
            self.paleta = self.PALETA

    def _nueva_luciernaga(self, indice):
        angulo = self.rng.random() * math.tau
        return {
            "x": self.rng.randrange(self.ancho),
            "y": self.rng.randrange(self.alto),
            "vx": math.cos(angulo) * self.rng.uniform(4, 10),
            "vy": math.sin(angulo) * self.rng.uniform(2, 5),
            "fase": self.rng.random() * math.tau,
            "velocidad": self.rng.uniform(0.12, 0.42),
            "amplitud": self.rng.uniform(3, 11),
            "tamano": self.rng.choice((2, 3, 3, 4)),
            "fase_brillo": indice * 0.7 + self.rng.random() * math.tau,
        }

    def emitir(self, x, y, cantidad=10):
        disponibles = self.MAX_PARTICULAS - len(self.particulas)
        for _ in range(min(max(0, cantidad), disponibles)):
            angulo = self.rng.random() * math.tau
            velocidad = self.rng.uniform(8, 34)
            vida = self.rng.uniform(0.65, 1.5)
            self.particulas.append({
                "x": float(x),
                "y": float(y),
                "vx": math.cos(angulo) * velocidad,
                "vy": math.sin(angulo) * velocidad - self.rng.uniform(3, 16),
                "vida": vida,
                "vida_max": vida,
                "tamano": self.rng.choice((2, 3, 3, 4, 5, 6)),
                "color": self.rng.choice(self.paleta),
            })

    def actualizar(self, delta_ms):
        delta = max(0, delta_ms) / 1000
        self.tiempo += delta
        for luciernaga in self.luciernagas:
            luciernaga["fase"] += luciernaga["velocidad"] * delta
            # Deriva lenta con giro suave; reaparece por el borde contrario.
            giro = math.sin(self.tiempo * .3 + luciernaga["fase_brillo"]) * .6 * delta
            vx, vy = luciernaga.get("vx", 0), luciernaga.get("vy", 0)
            luciernaga["vx"] = vx * math.cos(giro) - vy * math.sin(giro)
            luciernaga["vy"] = vx * math.sin(giro) + vy * math.cos(giro)
            luciernaga["x"] = (luciernaga["x"] + luciernaga["vx"] * delta) % self.ancho
            luciernaga["y"] = (luciernaga["y"] + luciernaga["vy"] * delta) % self.alto

        vivas = []
        for particula in self.particulas:
            particula["vida"] -= delta
            if particula["vida"] <= 0:
                continue
            particula["x"] += particula["vx"] * delta
            particula["y"] += particula["vy"] * delta
            particula["vy"] -= 6 * delta  # las chispas flotan hacia arriba
            vivas.append(particula)
        self.particulas = vivas

    def dibujar(self, superficie):
        sprites = self._recursos()
        if self.mostrar_luciernagas:
            for luciernaga in self.luciernagas:
                x = int(luciernaga["x"] + math.sin(luciernaga["fase"]) * luciernaga["amplitud"])
                y = int(luciernaga["y"] + math.sin(luciernaga["fase"] * 0.7) * 3)
                brillo = (math.sin(self.tiempo * 1.6 + luciernaga["fase_brillo"]) + 1) / 2
                nivel = 1 + round(brillo * 5)
                halo = self._halo(self.RADIO_BRILLO + 3, tuple(round(c * nivel / 6 * .55) for c in (255, 207, 92)))
                superficie.blit(halo, halo.get_rect(center=(x, y)), special_flags=pygame.BLEND_RGB_ADD)
                cuadros = sprites["luciernaga" if luciernaga.get("vx", 1) >= 0 else "luciernaga_izquierda"]
                if cuadros:
                    cuadro = cuadros[int(self.tiempo * 10 + luciernaga["fase_brillo"] * 3) % len(cuadros)]
                    superficie.blit(cuadro, cuadro.get_rect(center=(x, y)))
                else:
                    tamano = luciernaga["tamano"]
                    alpha = int(100 + brillo * 155)
                    pygame.draw.rect(superficie, (alpha, alpha * 3 // 4, alpha // 3), (x, y, tamano, tamano))

        for particula in self.particulas:
            vida = max(0, min(1, particula["vida"] / particula["vida_max"]))
            x, y = int(particula["x"]), int(particula["y"])
            nivel = max(1, round(vida * 4))
            halo = self._halo(particula["tamano"] + 5, tuple(round(c * nivel / 4 * .5) for c in particula["color"]))
            superficie.blit(halo, halo.get_rect(center=(x, y)), special_flags=pygame.BLEND_RGB_ADD)
            tamano = min((7, 10, 13, 16), key=lambda t: abs(t - particula["tamano"] * 2.6))
            cuadros = sprites["destellos"].get(tamano)
            if cuadros:
                # La chispa recorre los 8 cuadros del destello durante su vida.
                cuadro = cuadros[min(len(cuadros) - 1, int((1 - vida) * len(cuadros)))]
                superficie.blit(cuadro, cuadro.get_rect(center=(x, y)))
            else:
                intensidad = int(110 + 145 * vida)
                color = tuple(min(255, c * intensidad // 180) for c in particula["color"])
                pygame.draw.rect(superficie, color, (x, y, particula["tamano"], particula["tamano"]))
