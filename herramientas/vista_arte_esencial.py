"""Vista previa del arte esencial sin jugar la campaña.

Menú: 1 minijuego del puente · 2 intro · 3 final bueno · 4 final malo · Esc vuelve.
Usa las mismas clases del juego (``interfaz.minijuego_puente``, ``interfaz.intro``
y ``interfaz.finales``); aquí solo se simula el estado que mandaría el servidor.

En el puente: E prueba acertar o fallar, 0/1/2 fijan el progreso, Espacio congela la aguja.

Uso: .venv\\Scripts\\python.exe -m herramientas.vista_arte_esencial
     (sin pantalla: --modo puente --cuadros 30 --captura vista.png)
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame  # noqa: E402

from multijugador.reparacion import CONFIGURACION, angulo_aguja, dentro_de_zona  # noqa: E402

MODOS = ("menu", "puente", "intro", "final_bueno", "final_malo")
INDICADORES = {
    "final_bueno": {"sabiduria": 78, "confianza": 72, "armonia": 70, "desinformacion": 18, "susurros_falsos": 10},
    "final_malo": {"sabiduria": 30, "confianza": 25, "armonia": 35, "desinformacion": 70, "susurros_falsos": 55},
}
CREMA = (255, 243, 210)
ORO = (237, 185, 87)


class Puente:
    """El estado que el servidor manda del puente, simulado en local."""

    def __init__(self):
        self.progreso = 0
        self.tiempo_aguja_ms = 0
        self.congelada = False
        self.estado = "normal"
        self.hasta = 0.0

    def actualizar(self, segundos):
        if not self.congelada:
            self.tiempo_aguja_ms += round(segundos * 1000)
        if self.hasta and time.monotonic() > self.hasta:
            self.estado, self.hasta = "normal", 0.0

    def pulsar_e(self):
        if dentro_de_zona(angulo_aguja(self.tiempo_aguja_ms), self.progreso):
            self.progreso = (self.progreso + 1) % CONFIGURACION["aciertos_necesarios"]
            self.estado = "acierto"
        else:
            self.progreso = max(0, self.progreso - CONFIGURACION["penalizacion_por_error"])
            self.estado = "error"
        self.hasta = time.monotonic() + CONFIGURACION["duracion_resultado_ms"] / 1000

    def fase(self):
        if not self.hasta:
            return None
        duracion = CONFIGURACION["duracion_resultado_ms"] / 1000
        return min(1.0, max(0.0, 1 - (self.hasta - time.monotonic()) / duracion))


class Vista:
    def __init__(self, feria=False):
        from interfaz.minijuego_puente import RecursosPuente
        from nucleo.recursos import cargar_fuente
        self.fuentes = {"fuente_mapa": cargar_fuente(18), "fuente_panel_titulo": cargar_fuente(16),
                        "fuente_panel": cargar_fuente(13)}
        self.fuente_menu, self.fuente_titulo = cargar_fuente(20), cargar_fuente(28)
        self.recursos_puente = RecursosPuente()
        self.feria = feria
        self.modo = "menu"
        self.puente = Puente()
        self.intro = None
        self.final = None

    def abrir(self, modo):
        self.modo = modo
        if modo == "puente":
            self.puente = Puente()
        elif modo == "intro":
            from interfaz.intro import Intro
            self.intro = Intro.crear(feria=self.feria)
            if self.intro is None:
                self.modo = "menu"
        elif modo in INDICADORES:
            from interfaz.finales import PantallaFinal
            from multijugador.presentacion import ETIQUETAS
            self.final = PantallaFinal(INDICADORES[modo], ETIQUETAS["la_copa"], self.fuente_titulo,
                                       self.fuentes["fuente_mapa"], casos=6, total=6)
            print("[Vista] Final cargado:", "nuevo" if self.final.imagen is not None else "sin imagen",
                  "->", self.final.resultado)

    def evento(self, evento):
        """False cuando hay que cerrar la herramienta."""
        if self.modo == "intro" and self.intro is not None:
            self.intro.manejar_evento(evento)
            return True
        if evento.type != pygame.KEYDOWN:
            return True
        if evento.key == pygame.K_ESCAPE:
            if self.modo == "menu":
                return False
            self.modo = "menu"
        elif self.modo == "menu" and evento.unicode in "1234" and evento.unicode:
            self.abrir(MODOS[int(evento.unicode)])
        elif self.modo == "puente":
            if evento.key == pygame.K_e:
                self.puente.pulsar_e()
            elif evento.unicode in ("0", "1", "2") and evento.unicode:
                self.puente.progreso = int(evento.unicode)
            elif evento.key == pygame.K_SPACE:
                self.puente.congelada = not self.puente.congelada
        return True

    def actualizar(self, segundos):
        if self.modo == "puente":
            self.puente.actualizar(segundos)
        elif self.modo == "intro" and self.intro is not None:
            self.intro.actualizar(segundos)
            if self.intro.terminada:
                self.modo = "menu"

    def dibujar(self, lienzo):
        from interfaz.minijuego_puente import dibujar_panel
        lienzo.fill((12, 28, 24))
        if self.modo == "puente":
            p = self.puente
            dibujar_panel(lienzo, self.recursos_puente, self.fuentes, {"progreso": p.progreso, "total": 3},
                          angulo_aguja(p.tiempo_aguja_ms), p.estado, p.fase())
            ayuda = (f"E: probar ({p.estado})  ·  0/1/2: progreso  ·  Espacio: congelar  ·  Esc: menú"
                     f"  ·  aguja: {self.recursos_puente.origen_aguja}")
            self._texto(lienzo, ayuda, 690, self.fuentes["fuente_panel"])
        elif self.modo == "intro" and self.intro is not None:
            self.intro.dibujar(lienzo)
        elif self.modo in INDICADORES and self.final is not None:
            self.final.dibujar(lienzo)
            self._texto(lienzo, "Esc: menú", 700, self.fuentes["fuente_panel"])
        else:
            self._texto(lienzo, "VISTA DEL ARTE ESENCIAL", 200, self.fuente_titulo, ORO)
            for i, linea in enumerate(("1  Minijuego del puente", "2  Intro", "3  Final bueno",
                                       "4  Final malo", "Esc  Salir")):
                self._texto(lienzo, linea, 280 + i * 44, self.fuente_menu)

    @staticmethod
    def _texto(lienzo, texto, y, fuente, color=CREMA):
        render = fuente.render(texto, True, color)
        lienzo.blit(render, render.get_rect(center=(480, y)))


def main(argumentos=None):
    opciones = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    opciones.add_argument("--modo", choices=MODOS, default="menu")
    opciones.add_argument("--cuadros", type=int, default=0, help="termina tras N cuadros (pruebas)")
    opciones.add_argument("--captura", help="guarda el último cuadro en este PNG")
    opciones.add_argument("--progreso", type=int, default=0)
    opciones.add_argument("--resultado", choices=("normal", "acierto", "error"), default="normal",
                          help="estado del medidor en la captura del puente")
    opciones.add_argument("--aguja-ms", type=int, help="fija la aguja en este tiempo (ms)")
    opciones.add_argument("--vineta", type=int, default=1, help="viñeta de la intro en la captura")
    opciones = opciones.parse_args(argumentos)
    pygame.init()
    pantalla = pygame.display.set_mode((960, 720), pygame.SCALED)
    pygame.display.set_caption("Timeless Glitch · Vista del arte esencial")
    vista = Vista(feria=os.environ.get("TG_MODO_FERIA") == "1")
    if opciones.modo != "menu":
        vista.abrir(opciones.modo)
    if vista.modo == "puente":
        vista.puente.progreso = opciones.progreso
        if opciones.aguja_ms is not None:
            vista.puente.tiempo_aguja_ms, vista.puente.congelada = opciones.aguja_ms, True
        if opciones.resultado != "normal":
            duracion = CONFIGURACION["duracion_resultado_ms"] / 1000
            vista.puente.estado = opciones.resultado
            vista.puente.hasta = time.monotonic() + duracion * 10  # se queda visible para la captura
    if vista.modo == "intro":
        for _ in range(opciones.vineta - 1):
            vista.intro.siguiente()
    reloj = pygame.time.Clock()
    cuadro = 0
    while True:
        segundos = reloj.tick(60) / 1000
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT or not vista.evento(evento):
                pygame.quit()
                return 0
        vista.actualizar(segundos)
        vista.dibujar(pantalla)
        pygame.display.flip()
        cuadro += 1
        if opciones.cuadros and cuadro >= opciones.cuadros:
            if opciones.captura:
                pygame.image.save(pantalla, opciones.captura)
            pygame.quit()
            return 0


if __name__ == "__main__":
    sys.exit(main())
