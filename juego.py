"""
La Copa: Voces en las Alturas
Interfaz grafica en pygame con mapa, personajes, cinematicas breves y tablilla.

La logica de estructuras de datos queda en logica_juego.py y Arboles.py:
- EstadoJuego administra la cola de tablillas y avanza por el arbol de decisiones.
- Cada raiz de tablilla trae una categoria, tomada del arbol de clasificacion.
"""

import json
import math
import os
import random
import sys
import unicodedata

import pygame

from audio.audio_manager import GestorAudio
from logica.conversaciones import construir_conversacion, construir_mensajes_eco, construir_respuesta_eco
from logica.dimensiones import DIMENSION_LA_COPA, DIMENSION_PRESENTE, EDIFICIOS_PRESENTE
from logica.grafo_fisico import GrafoFisico
from logica.habilidades_jugador import HabilidadJugador
from interfaz.boton import Boton, GrupoBotones
from interfaz.dialogo import ControladorDialogo
from interfaz.hud import HUDIndicadores
from interfaz.menu import MenuModal
from interfaz.mensaje_privado import ControladorMensajePrivado
from logica.logica_juego import EstadoJuego
from graficos.particulas import SistemaParticulas
from graficos.propagacion_visual import PropagacionVisual
from mundo.reparacion_puentes import SistemaReparacionPuente
from nucleo.rutas import RAIZ
from nucleo.config import (  # noqa: F401  (transición del refactor)
    ALTO,
    ANCHO,
    CAMARA_RESPUESTA,
    CENTRO_CALDERO,
    CENTRO_TABLILLA,
    CENTRO_TABLILLA_CENTRADA,
    CONTINUIDAD_PERSONAJES,
    CREMA,
    DISTANCIA_INTERACCION,
    DURACION_MINIMA_HISTORIA_DIMENSION_MS,
    DURACION_MINIMA_TUTORIAL_DIMENSION_MS,
    ESCENAS_CON_MAPA,
    ESCENA_ANALISIS,
    ESCENA_AYUDA,
    ESCENA_CELULAR,
    ESCENA_CLASIFICACION,
    ESCENA_CODICE,
    ESCENA_CONSECUENCIA,
    ESCENA_DIALOGO,
    ESCENA_ECO,
    ESCENA_FINAL,
    ESCENA_MAPA,
    ESCENA_MAPA_DESTINO,
    ESCENA_MENSAJE,
    ESCENA_PAUSA,
    ESCENA_RESULTADO,
    ESCENA_TABLILLA,
    ESCENA_TRANSICION_DIMENSION,
    ESCENA_TUTORIAL_DIMENSION,
    ESCENA_VISUAL,
    ESCENA_VOLUMEN,
    ESCENA_ZONA_EN_PROCESO,
    FPS,
    MADERA,
    NOMBRE_JUGADOR_PRESENTE,
    ORO,
    PAGINAS_CODICE,
    PANEL_OSCURO,
    PAUSA_PATRULLA_NPC_MS,
    PROBABILIDAD_PAUSA_NPC,
    RADIO_WAYPOINT_NPC,
    RELACION_ASPECTO,
    RUTA_ASSETS,
    RUTA_FUENTE,
    TAMANO_HITBOX_PIES,
    TINTA,
    VARIACION_VELOCIDAD_NPC,
    VELOCIDAD_GUARDIAN,
    VELOCIDAD_PATRULLA_NPC,
    ZOOM_MAPA_PRESENTE,
)
from nucleo.recursos import (  # noqa: F401  (transición del refactor)
    buscar_asset,
    cargar_efecto_tablilla,
    cargar_fuente,
    cargar_icono_hud,
    cargar_imagen,
    cargar_spritesheet_frames,
    dibujar_sprite_en_rect,
    envolver_texto,
    es_hoja_portales,
    normalizar_ruta,
    recortar_portal_final,
    superficie_con_alpha,
)
from mundo.personajes import (  # noqa: F401  (transición del refactor)
    ARCHIVOS_DIRECCIONALES_PERSONAJES,
    ARCHIVOS_REPOSO_PERSONAJES,
    DIRECCION_A_FILA_REPOSO,
    ESCALA_NPC_PRESENTE,
    ESCALA_PERSONAJE_PRESENTE,
    ORIENTACIONES_SPRITE,
    PERSONAJES_PRESENTES,
    TAMANO_JUGADOR,
    TAMANO_JUGADOR_PRESENTE,
    _cargar_decoraciones_presentes,
    _cargar_frames_idle_personaje,
    _cargar_ruta_npc,
    _cargar_sprite_direccional,
    _direccion_desde_nombre_sprite,
    _escalar_frames,
    _escalar_sprite_en_caja,
    cargar_frames_idle_guardian,
    cargar_frames_tronco_eco,
    cargar_personaje_periodista,
    cargar_retrato_publicacion,
    crear_jugador_local,
    personaje_de_decoracion,
)
from mundo.mapas import (  # noqa: F401  (transición del refactor)
    _mapear_hitbox_a_ventana,
    _posicion_spawn_desde_datos,
    _rect_de_hitbox,
    cargar_mapa_edificio,
    cargar_mapa_presente,
    cargar_mapa_principal,
)
from mundo.colisiones import (  # noqa: F401  (transición del refactor)
    _rect_hits_line,
    colision_hitbox_mapa,
    contiene_zona_caminable,
    jugador_bloqueado,
)
from mundo.camara import (  # noqa: F401  (transición del refactor)
    _limitar_camara,
    actualizar_camara_mundo,
    dibujar_escena_con_camara,
    posicion_mundo_a_pantalla,
    posicion_pantalla_a_mundo,
)
from mundo.npcs import (  # noqa: F401  (transición del refactor)
    _direccion_npc,
    _siguiente_waypoint_npc,
    actualizar_npcs_presentes,
)
from mundo.jugador import (  # noqa: F401  (transición del refactor)
    _posicion_interaccion,
    ajustar_inicio_jugador,
    alternar_interactuable_cercano,
    buscar_interactuable_cercano,
    mover_jugador,
    reiniciar_jugador_en_casa,
    tecla_activa,
)
from mundo.grafo_aldea import (  # noqa: F401  (transición del refactor)
    CONEXIONES_PUENTES_ALDEA,
    PLATAFORMAS_ALDEA,
    _posicion_en_mapa,
    buscar_ruta_transmision,
    crear_grafo_fisico,
)
from un_jugador.hud import (  # noqa: F401  (transición del refactor)
    _FLECHA_GUIA,
    celular_disponible,
    controles_hud,
    dibujar_brillo_interaccion,
    dibujar_celular_feed,
    dibujar_controles_hud,
    dibujar_flecha_objetivo,
    dibujar_mensaje_mapa,
    dibujar_pistas_mision,
    instrucciones_dimension,
    interaccion_en_mapa,
    objetivo_mision_actual,
    rect_controles_hud,
    rectangulos_selector_mision,
    texto_tutorial_primer_evento,
)
from un_jugador.dibujo_mapa import (  # noqa: F401  (transición del refactor)
    _mapa_actual_recursos,
    dibujar_capas_mundo,
    dibujar_debug_grafo,
    dibujar_debug_mapa,
    dibujar_decoraciones_editor,
    dibujar_fondo_mundo,
    dibujar_habilidad_jugador,
    dibujar_jugador,
    dibujar_mapa,
    dibujar_propagaciones_visuales,
    dibujar_puente_balanceandose,
    dibujar_troncos_eco,
    posicion_visual_en_puente,
)
from un_jugador.codice import (  # noqa: F401  (transición del refactor)
    construir_contenido_codice,
    dibujar_codice,
    dibujar_tutorial_dimension,
)
from un_jugador.tablilla import (  # noqa: F401  (transición del refactor)
    accion_tablilla,
    buscar_imagen_para_opcion,
    clave_pocion,
    construir_botones,
    construir_botones_clasificacion,
    crear_fondo_tablilla,
    determinar_resultado_final,
    dibujar_animacion_pocion,
    dibujar_arbol_clasificacion,
    dibujar_arbol_decision,
    dibujar_consecuencia_evento,
    dibujar_escena_tablilla,
    dibujar_final,
    dibujar_nodo_clasificacion,
    dibujar_pociones,
    dibujar_pregunta_clasificacion,
    dibujar_resultado_evento,
    dibujar_tablilla,
    dibujar_tablilla_en_efecto,
    estado_caldero,
    fondo_tablilla_actual,
    formatear_categoria,
    imagen_boton_clasificacion,
    iniciar_animacion_decision,
    lineas_efecto,
    nombre_indicador,
    rectangulos_pociones,
    reproducir_audio_clasificacion,
    sincronizar_audio_caldero,
)
from un_jugador.escenas import (  # noqa: F401  (transición del refactor)
    dibujar_analisis_publicacion,
    dibujar_escena_dialogo,
    dibujar_escena_mensaje,
    dibujar_interfaz_eco,
    dibujar_transicion_dimension,
    rectangulos_opciones_mision,
)
from mundo.creacion import (  # noqa: F401  (transición del refactor)
    crear_mundo,
)
from un_jugador.ventana import (  # noqa: F401  (transición del refactor)
    convertir_mouse_a_lienzo,
    crear_ventana,
    presentar_lienzo,
    rect_lienzo_en_ventana,
    tamano_ventana_inicial,
)
from un_jugador.partida import (  # noqa: F401  (transición del refactor)
    main,
)


if __name__ == "__main__":
    from interfaz.inicio import mostrar_menu_inicio

    if mostrar_menu_inicio() == "individual":
        main()
    else:
        pygame.quit()
