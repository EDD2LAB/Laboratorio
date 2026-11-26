"""Prueba larga sin pantalla: el juego abierto durante horas, como en la feria.

Usa el bucle REAL del menú (``MenuInicio.ejecutar``) y repite un ciclo:
Demo rápida en La Copa (la persona camina al azar y los bots juegan) →
salto al final cooperativo (F2) → vuelta al menú → otra Demo rápida.
Cada minuto anota la memoria del proceso, los FPS, el cuadro p95, los
tirones (> 50 ms), los hilos vivos y los objetos que sigue el recolector.

Uso:
    python herramientas/prueba_larga.py --minutos 30 --salida docs/revision_feria/prueba_larga.json
"""
import argparse
import gc
import json
import os
from pathlib import Path
import sys
import threading
import time

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from herramientas.benchmark import EntradaSimulada, RelojMedido, memoria_mb, resumen_cuadros  # noqa: E402

# Fracción de cada ciclo en que empieza cada parte (ciclo de 300 s: 150 s de La Copa,
# 120 s del final y 30 s en el menú).
CICLO = (("campana", 0), ("final", .5), ("menu", .9))


def ejecutar(minutos, semilla=11, duracion_ciclo=300, muestra_cada=60):
    import interfaz.inicio as inicio
    import interfaz.partida_multijugador as vista_partida
    from multijugador.dimensiones_red import LA_COPA

    pygame.init()
    menu = inicio.MenuInicio()
    menu.pantalla = pygame.display.set_mode((960, 720))
    cuadros, muestras, cambios = [], [], []
    estado = {"parte": None, "ciclo": -1, "desde_muestra": 0, "inicio": time.perf_counter(),
              "ultima_muestra": time.perf_counter(), "transicion": False, "cargando": False}

    def cambiar(parte, ciclo):
        antes = time.perf_counter()
        estado["cargando"] = True
        try:
            hacer_cambio(parte)
        finally:
            estado["cargando"] = False
        cambios.append({"ciclo": ciclo, "parte": parte, "segundos": round(time.perf_counter() - antes, 2)})
        estado["transicion"] = True

    def hacer_cambio(parte):
        if parte == "campana":
            menu.pausa.cerrar()
            menu.iniciar_campana("Visitante", "guardian", "normal", LA_COPA, "principal")
            menu.intro = None
        elif parte == "final" and menu.cliente is not None:
            menu.cliente.actuar("saltar_al_final")
        elif parte == "menu":
            menu.limpiar_conexion()
            menu.vista = "principal"

    def al_cuadro(ahora):
        transcurrido = ahora - estado["inicio"]
        ciclo, dentro = int(transcurrido // duracion_ciclo), transcurrido % duracion_ciclo / duracion_ciclo
        parte = [nombre for nombre, desde in CICLO if dentro >= desde][-1]
        if (parte, ciclo) != (estado["parte"], estado["ciclo"]):
            estado["parte"], estado["ciclo"] = parte, ciclo
            cambiar(parte, ciclo)
        if ahora - estado["ultima_muestra"] >= muestra_cada:
            nuevos = cuadros[estado["desde_muestra"]:]
            duracion = ahora - estado["ultima_muestra"]
            muestras.append({
                "minuto": round(transcurrido / 60, 1), "parte": parte, "memoria_mb": memoria_mb(),
                "fps": round(len(nuevos) / duracion, 1), "cuadro_ms": resumen_cuadros(nuevos),
                "hilos": threading.active_count(), "objetos_gc": len(gc.get_objects()),
            })
            estado["desde_muestra"], estado["ultima_muestra"] = len(cuadros), ahora
            print(json.dumps(muestras[-1], ensure_ascii=False), flush=True)

    entrada = EntradaSimulada(minutos * 60, semilla, al_cuadro=al_cuadro)
    reloj_original, eventos_original = pygame.time.Clock, pygame.event.get
    tecla_original, foco_original = vista_partida.tecla_activa, pygame.key.get_focused
    registro = []

    class Reloj(RelojMedido):
        def tick(self, fps=0):
            if estado["cargando"]:  # la barra de carga tiene su propio reloj
                return self._reloj.tick(fps)
            antes = len(registro)
            resultado = super().tick(fps)
            if len(registro) > antes:
                if estado["transicion"]:
                    estado["transicion"] = False  # el cuadro de la carga no cuenta como tirón de juego
                else:
                    cuadros.append(registro[-1])
            return resultado

    pygame.time.Clock = lambda: Reloj(registro, reloj_original)
    pygame.event.get = entrada.eventos
    vista_partida.tecla_activa = entrada.tecla_activa
    pygame.key.get_focused = lambda: True
    memoria_inicial = memoria_mb()
    try:
        menu.ejecutar()
    finally:
        pygame.time.Clock, pygame.event.get = reloj_original, eventos_original
        vista_partida.tecla_activa, pygame.key.get_focused = tecla_original, foco_original
    resultado = {"minutos": minutos, "memoria_inicial_mb": memoria_inicial, "memoria_final_mb": memoria_mb(),
                 "hilos_al_final": threading.active_count(), "muestras": muestras, "cambios": cambios,
                 "cuadro_total_ms": resumen_cuadros(cuadros)}
    pygame.quit()
    return resultado


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutos", type=float, default=30)
    parser.add_argument("--ciclo", type=float, default=300, help="segundos de cada ciclo campaña → final → menú")
    parser.add_argument("--muestra", type=float, default=60, help="segundos entre muestras")
    parser.add_argument("--salida")
    args = parser.parse_args()
    resultado = ejecutar(args.minutos, duracion_ciclo=args.ciclo, muestra_cada=args.muestra)
    texto = json.dumps(resultado, ensure_ascii=False, indent=2)
    print(texto)
    if args.salida:
        Path(args.salida).write_text(texto, encoding="utf-8")


if __name__ == "__main__":
    main()
