"""Efectos del combate final que existen solo en el cliente.

El servidor envía estados (blancos, mini-núcleos, el trazo del último disparo,
la señal). Aquí se comparan cuadro a cuadro para descubrir qué acaba de ocurrir
y animarlo: proyectil, chispas, explosión, ondas, temblor y textos flotantes.
No se envía nada por red ni cambia ninguna regla.
"""
import math
import random

import pygame

from interfaz import sprites_combate as sprites
from multijugador.aventura_final import ALCANCE_BLASTER

DURACION_PROYECTIL = .12
DURACION_EXPLOSION = .36
DURACION_GOLPE = .12
RADIO_PULSO_MINI = 38  # igual que el alcance del pulso en aventura_final
LIMITE_REPETICION = .08  # s entre dos copias del mismo sonido


def elegir_objetivo(minis, origen, linea_libre):
    """Mini-núcleo al que irá el disparo de F y si el servidor lo aceptaría.

    Prefiere el más cercano al alcance y sin pared en medio; si no hay ninguno,
    devuelve el más cercano para que la mira muestre por qué no se puede.
    """
    if not minis or origen is None:
        return None, False
    distancia = lambda m: math.hypot(origen[0] - m["x"], origen[1] - m["y"])
    alcanzables = [m for m in minis
                   if distancia(m) <= ALCANCE_BLASTER and linea_libre(origen, (m["x"], m["y"]))]
    if alcanzables:
        return min(alcanzables, key=distancia), True
    return min(minis, key=distancia), False


class EfectosCombate:
    def __init__(self, semilla=7):
        self.azar = random.Random(semilla)
        self.t = None
        self.dt = 0.0
        self.turno = None
        self.aviso_total = 3.0
        self.trazo = None
        self.ultimo_disparo = -9.0
        self.minis = {}
        self.golpes = {}
        self.integridad = None
        self.corazon_perdido = -9.0
        self.derribado = False
        self.sacudida_hasta = 0.0
        self.fuerza = 0
        self.proyectiles, self.explosiones, self.ondas, self.chispas, self.textos, self.fogonazos = [], [], [], [], [], []
        self._fuente = None
        # Sonidos pendientes ``(nombre, volumen)``; la vista los reproduce y vacía.
        self.sonidos = []
        self._ultimo_sonido = {}
        self.fase_batalla = None
        self.derribados = set()
        self.preparacion = None
        self.t_inicio_combate = None

    def sonar(self, nombre, volumen=1.0):
        """Encola un sonido; si el mismo sonó hace menos de 80 ms, sube el volumen
        del anterior en vez de apilar otro (tres rayos = un estallido más fuerte)."""
        if self.t is None:
            return
        if self.t - self._ultimo_sonido.get(nombre, -9) < LIMITE_REPETICION:
            for i, (pendiente, anterior) in enumerate(self.sonidos):
                if pendiente == nombre:
                    self.sonidos[i] = (nombre, min(1.0, max(anterior, volumen) + .15))
            return
        self._ultimo_sonido[nombre] = self.t
        self.sonidos.append((nombre, volumen))

    def tomar_sonidos(self):
        pendientes, self.sonidos = self.sonidos, []
        return pendientes

    def _preparacion(self, aventura):
        """Antes del combate: piezas recogidas o entregadas y fabricación."""
        estado = (len(aventura.get("cargas", {})), len(aventura.get("entregadas", [])), bool(aventura.get("fabricado")))
        if self.preparacion is not None:
            if estado[2] and not self.preparacion[2]:
                self.sonar("fabricar")
            elif estado[0] > self.preparacion[0] or estado[1] > self.preparacion[1]:
                self.sonar("recoger_material", .8)
        self.preparacion = estado

    # --- Detección de sucesos -------------------------------------------------
    def actualizar(self, final, ahora_ms, yo_id=None, posicion=None):
        t = ahora_ms / 1000
        self.dt = 0.0 if self.t is None else max(0.0, min(.1, t - self.t))
        self.t = t
        if final.get("fase") in ("preparacion", "activo"):
            self._preparacion(final.get("aventura", {}))
        else:
            self.preparacion = None
        if final.get("fase") != "activo":
            self.turno, self.trazo, self.minis, self.integridad = None, None, {}, None
            self.fase_batalla, self.derribados, self.t_inicio_combate = None, set(), None
            self._envejecer()
            return
        batalla, aventura = final.get("batalla", {}), final.get("aventura", {})
        turno = batalla.get("turno")
        color = self.color_fase(batalla.get("fase", 1))
        if self.fase_batalla == 1 and batalla.get("fase") == 2:
            self.sonar("cambio_fase")
        self.fase_batalla = batalla.get("fase")
        if turno == "aviso" and self.turno != "aviso":
            self.aviso_total = max(.5, float(batalla.get("segundos", 3.0)))
            self.sonar("rayo_aviso", .7)
        if turno == "rayo" and self.turno != "rayo":
            for x, y in batalla.get("blancos", []):
                self.ondas.append([x, y, t, 30 if batalla.get("fase") == 2 else 22, color])
                self._chispas(x, y, 10, color)
            self.sacudir(.25, 2)
            self.sonar("rayo_impacto", min(1.0, .7 + .1 * len(batalla.get("blancos", []))))
        self.turno = turno
        derribados = set(batalla.get("derribados", []))
        caido = yo_id is not None and yo_id in derribados
        if caido and not self.derribado:
            self.sacudir(.4, 3)
        if derribados - self.derribados:
            self.sonar("derribado", 1.0 if caido and not self.derribado else .5)
        if self.derribados - derribados:
            self.sonar("levantado", 1.0 if self.derribado and not caido else .5)
        self.derribado, self.derribados = caido, derribados

        trazo = aventura.get("disparo")
        if trazo and trazo != self.trazo:
            self.proyectiles.append([*trazo, t])
            self.fogonazos.append([trazo[0], trazo[1], t])
            self.ultimo_disparo = t
            propio = posicion is not None and math.hypot(trazo[0] - posicion[0], trazo[1] - posicion[1]) < 12
            self.sonar("blaster_disparo", 1.0 if propio else .45)  # los tiros ajenos, más bajos
        self.trazo = trazo

        actuales = {m["id"]: m for m in aventura.get("minis", [])}
        for ident, mini in actuales.items():
            previo = self.minis.get(ident)
            if previo is None:
                self.ondas.append([mini["x"], mini["y"], t, 14, (246, 70, 122)])  # aparece
                if self.t_inicio_combate is not None:
                    self.sonar("mini_aparicion", .7)
                continue
            if mini.get("vida", 0) < previo.get("vida", 0):
                self.golpes[ident] = t
                self._chispas(mini["x"], mini["y"], 6, (255, 226, 238))
                self.sonar("mini_golpe", .8)
            if mini.get("aviso", 0) > previo.get("aviso", 0) + .5:
                self.ondas.append([mini["x"], mini["y"], t, RADIO_PULSO_MINI, (246, 70, 122)])  # descarga
                self.sonar("mini_disparo", .8)
        for ident, previo in self.minis.items():
            if ident not in actuales and previo.get("vida", 0) <= 1 and t - self.ultimo_disparo < 1.0:
                self.explosiones.append([previo["x"], previo["y"], t])
                self._chispas(previo["x"], previo["y"], 14, (246, 70, 122))
                self.textos.append([previo["x"], previo["y"] - 12, t, "+1", (104, 243, 241)])
                self.sacudir(.15, 1)
                self.sonar("mini_explosion")
        self.minis = {ident: dict(m) for ident, m in actuales.items()}
        self.t_inicio_combate = t  # desde el segundo cuadro, los minis nuevos suenan

        integridad = final.get("integridad")
        if self.integridad is not None and integridad is not None and integridad < self.integridad:
            self.corazon_perdido = t
            self.sacudir(.3, 2)
            self.sonar("senal_perdida", .8)
        self.integridad = integridad
        self._envejecer()

    def _chispas(self, x, y, cantidad, color):
        for _ in range(cantidad):
            angulo = self.azar.uniform(0, math.tau)
            rapidez = self.azar.uniform(25, 70)
            self.chispas.append([x, y, math.cos(angulo) * rapidez, math.sin(angulo) * rapidez - 15,
                                 self.azar.uniform(.25, .5), color])

    def _envejecer(self):
        t, dt = self.t, self.dt
        for chispa in self.chispas:
            chispa[0] += chispa[2] * dt
            chispa[1] += chispa[3] * dt
            chispa[3] += 90 * dt
            chispa[4] -= dt
        self.chispas = [c for c in self.chispas if c[4] > 0]
        llegados = [p for p in self.proyectiles if t - p[4] >= DURACION_PROYECTIL]
        for p in llegados:
            self._chispas(p[2], p[3], 5, (104, 243, 241))
        self.proyectiles = [p for p in self.proyectiles if p not in llegados]
        self.explosiones = [e for e in self.explosiones if t - e[2] < DURACION_EXPLOSION]
        self.ondas = [o for o in self.ondas if t - o[2] < .35]
        self.textos = [x for x in self.textos if t - x[2] < .9]
        self.fogonazos = [f for f in self.fogonazos if t - f[2] < .08]

    # --- Consultas para el dibujo ---------------------------------------------
    @staticmethod
    def color_fase(fase):
        return (102, 250, 155) if fase == 1 else (255, 98, 109)

    def sacudir(self, segundos, fuerza):
        if self.t is None:
            return
        self.sacudida_hasta = max(self.sacudida_hasta, self.t + segundos)
        self.fuerza = max(self.fuerza if self.t < self.sacudida_hasta else 0, fuerza)

    def desplazamiento(self, ahora_ms):
        """Temblor de cámara en píxeles del mapa (×3 en pantalla)."""
        if self.t is None or ahora_ms / 1000 >= self.sacudida_hasta:
            self.fuerza = 0
            return 0, 0
        return self.azar.randint(-self.fuerza, self.fuerza), self.azar.randint(-self.fuerza, self.fuerza)

    def recien_golpeado(self, ident):
        return self.t is not None and self.t - self.golpes.get(ident, -9) < DURACION_GOLPE

    def perdio_senal(self, segundos=.6):
        return self.t is not None and self.t - self.corazon_perdido < segundos

    # --- Dibujo en la capa del mundo --------------------------------------------
    def dibujar(self, superficie):
        if self.t is None:
            return
        t = self.t
        for x, y, inicio, radio, color in self.ondas:
            avance = (t - inicio) / .35
            pygame.draw.circle(superficie, color, (round(x), round(y)), max(2, round(radio * avance)), 1)
        for x0, y0, x1, y1, inicio in self.proyectiles:
            avance = min(1, (t - inicio) / DURACION_PROYECTIL)
            x, y = x0 + (x1 - x0) * avance, y0 + (y1 - y0) * avance
            cola = max(0, avance - .35)
            cx, cy = x0 + (x1 - x0) * cola, y0 + (y1 - y0) * cola
            pygame.draw.line(superficie, (26, 120, 132), (cx, cy), (x, y), 3)
            pygame.draw.line(superficie, (104, 243, 241), (cx, cy), (x, y), 1)
            pygame.draw.rect(superficie, (226, 255, 252), (round(x) - 1, round(y) - 1, 3, 3))
        for x, y, _ in self.fogonazos:
            pygame.draw.rect(superficie, (226, 255, 252), (round(x) - 1, round(y) - 3, 3, 3))
            pygame.draw.rect(superficie, (104, 243, 241), (round(x) - 3, round(y) - 2, 7, 1))
            pygame.draw.rect(superficie, (104, 243, 241), (round(x), round(y) - 5, 1, 7))
        for x, y, inicio in self.explosiones:
            cuadro = min(5, int((t - inicio) / DURACION_EXPLOSION * 6))
            imagen = sprites.explosion(cuadro)
            superficie.blit(imagen, imagen.get_rect(center=(round(x), round(y))))
        for x, y, _, _, vida, color in self.chispas:
            tono = color if vida > .15 else tuple(c // 2 for c in color)
            superficie.fill(tono, (round(x), round(y), 1, 1))
        if self.textos:
            if self._fuente is None:
                self._fuente = pygame.font.Font(None, 14)
            for x, y, inicio, texto, color in self.textos:
                subida = (t - inicio) * 18
                for desplazamiento, tinta in (((1, 1), sprites.CONTORNO), ((0, 0), color)):
                    imagen = self._fuente.render(texto, False, tinta)  # sin suavizado: píxel nítido
                    superficie.blit(imagen, imagen.get_rect(center=(round(x) + desplazamiento[0],
                                                                    round(y - subida) + desplazamiento[1])))
