r"""Editor independiente de posiciones e hitboxes del mapa.

Ejecuta:
    .\.venv\Scripts\python.exe Hitbox.py

Guarda la configuracion en:
    Hitboxes/mapa_hitboxes.json
"""

import os
import sys

import pygame

import juego


def cargar_recursos_editor():
    mapa = juego.cargar_imagen("Mapa.png", (juego.ANCHO, juego.ALTO))
    fuente_etiqueta = pygame.font.SysFont("arial", 13, bold=True)
    return {
        "mapa": mapa,
        "guardian_quieto": juego.cargar_sprite("Fila 1 - 5. Guardian.png", (86, 86)),
        "aspirante_quieto": juego.cargar_sprite("Fila 1 - 3. Aspirante_a_cacique-Idle.png", (78, 78)),
        "mensajero_quieto": juego.cargar_sprite(os.path.join("mensajero", "fila 1 - 7.png"), (78, 78)),
        "tarek_quieto": juego.cargar_sprite("HabHombre Fila 1- 3.png", (76, 76)),
        "luma_quieta": juego.cargar_sprite("HabMujer Fila 1 - 7.png", (76, 76)),
        "fuente_etiqueta": fuente_etiqueta,
    }


def dibujar_mundo_editor(lienzo, recursos, mundo, editor):
    lienzo.blit(recursos["mapa"], (0, 0))
    for actor in mundo["actores"]:
        actor.dibujar(lienzo, recursos["fuente_etiqueta"])
    mundo["guardian"].dibujar(lienzo, recursos["fuente_etiqueta"])
    juego.dibujar_editor(lienzo, mundo, editor, recursos["fuente_etiqueta"])


def main():
    pygame.init()
    pantalla = pygame.display.set_mode(juego.tamano_ventana_inicial(), pygame.RESIZABLE)
    pygame.display.set_caption("Editor de Hitboxes - La Copa")
    pygame.display.set_icon(juego.cargar_imagen("icono.png", (32, 32)))
    reloj = pygame.time.Clock()
    lienzo = pygame.Surface((juego.ANCHO, juego.ALTO))

    recursos = cargar_recursos_editor()
    mundo = juego.crear_mundo(recursos, juego.cargar_config_mapa())
    editor = juego.crear_estado_editor()
    editor["activo"] = True
    editor["mensaje"] = "Editor listo. Ajusta personajes, tablilla e hitboxes; presiona S para guardar."
    editor["mensaje_timer"] = 240

    corriendo = True
    while corriendo:
        rect_lienzo = juego.rect_lienzo_en_ventana(pantalla.get_size())

        for evento in pygame.event.get():
            if hasattr(evento, "pos"):
                evento.pos_lienzo = juego.convertir_mouse_a_lienzo(evento.pos, rect_lienzo)

            if evento.type == pygame.QUIT:
                corriendo = False
            elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                corriendo = False
            elif evento.type == pygame.VIDEORESIZE:
                pantalla = pygame.display.set_mode(evento.size, pygame.RESIZABLE)
            else:
                juego.manejar_evento_editor(evento, mundo, editor)
                if not editor["activo"]:
                    editor["activo"] = True

        dibujar_mundo_editor(lienzo, recursos, mundo, editor)
        juego.presentar_lienzo(pantalla, lienzo)
        pygame.display.flip()
        reloj.tick(juego.FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
