"""Efectos ambientales ligeros para el mapa, sin colisiones ni hojas."""

import math
import random

import pygame


class SistemaParticulas:
    """Actualiza luciérnagas y partículas mágicas con delta_ms."""

    MAX_LUCIERNAGAS = 12
    MAX_PARTICULAS = 60
    PALETA = ((111, 219, 150), (93, 218, 205), (238, 201, 92))
    RADIO_BRILLO = 9

    def __init__(self, ancho, alto, semilla=None):
        self.ancho = ancho
        self.alto = alto
        self.rng = random.Random(semilla)
        self.tiempo = 0.0
        self.luciernagas = [
            self._nueva_luciernaga(indice) for indice in range(self.MAX_LUCIERNAGAS)
        ]
        self.particulas = []
        self._superficies_luciernaga = {}
        for tamano in (1, 2, 3):
            try:
                pixel = pygame.Surface((tamano, tamano), pygame.SRCALPHA)
                pixel.fill((255, 212, 89, 255))
                self._superficies_luciernaga[tamano] = pixel
            except (pygame.error, MemoryError) as error:
                print(f"[advertencia] No se pudo crear el pixel de luciernaga: {error}")
                break

    def _nueva_luciernaga(self, indice):
        return {
            "x": self.rng.randrange(self.ancho),
            "y": self.rng.randrange(self.alto),
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
                "color": self.rng.choice(self.PALETA),
            })

    def actualizar(self, delta_ms):
        delta = max(0, delta_ms) / 1000
        self.tiempo += delta
        for luciernaga in self.luciernagas:
            luciernaga["fase"] += luciernaga["velocidad"] * delta

        vivas = []
        for particula in self.particulas:
            particula["vida"] -= delta
            if particula["vida"] <= 0:
                continue
            particula["x"] += particula["vx"] * delta
            particula["y"] += particula["vy"] * delta
            vivas.append(particula)
        self.particulas = vivas

    def dibujar(self, superficie):
        brillos = pygame.Surface(superficie.get_size(), pygame.SRCALPHA)
        for luciernaga in self.luciernagas:
            x = int(luciernaga["x"] + math.sin(luciernaga["fase"]) * luciernaga["amplitud"])
            y = int(luciernaga["y"] + math.sin(luciernaga["fase"] * 0.7) * 3)
            brillo = (math.sin(self.tiempo * 1.6 + luciernaga["fase_brillo"]) + 1) / 2
            alpha = int(100 + brillo * 155)
            tamano = luciernaga["tamano"]
            pygame.draw.circle(
                brillos,
                (255, 207, 92, int(38 + brillo * 42)),
                (x + tamano // 2, y + tamano // 2),
                self.RADIO_BRILLO,
            )
            pixel = self._superficies_luciernaga.get(tamano)
            if pixel is not None:
                pixel.set_alpha(alpha)
                superficie.blit(pixel, (x, y))
            elif alpha > 2:
                color = (alpha, alpha * 3 // 4, alpha // 3)
                pygame.draw.rect(superficie, color, pygame.Rect(x, y, tamano, tamano))

        for particula in self.particulas:
            proporcion_vida = max(
                0, min(1, particula["vida"] / particula["vida_max"])
            )
            intensidad = int(110 + 145 * proporcion_vida)
            x, y = int(particula["x"]), int(particula["y"])
            pygame.draw.circle(
                brillos,
                (*particula["color"], int(35 + 55 * proporcion_vida)),
                (x + particula["tamano"] // 2, y + particula["tamano"] // 2),
                particula["tamano"] + 4,
            )
            color = tuple(min(255, c * intensidad // 180) for c in particula["color"])
            if intensidad > 0:
                pygame.draw.rect(
                    superficie,
                    color,
                    pygame.Rect(
                        x,
                        y,
                        particula["tamano"],
                        particula["tamano"],
                    ),
                )
        superficie.blit(brillos, (0, 0))
