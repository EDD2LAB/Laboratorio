# Arquitectura (tras `refactor/modularizar`)

Refactor puro: el código se movió sin reescribirse. `juego.py` pasó de 6141
líneas a 20 y es el único `.py` en la raíz.

## De `juego.py` a módulos

| Bloque original de `juego.py` | Módulo |
| --- | --- |
| Constantes (lienzo, colores, escenas, tiempos, datos de continuidad) | `nucleo/config.py` |
| Rutas de la raíz del proyecto | `nucleo/rutas.py` (nuevo, pathlib) |
| `buscar_asset`, `cargar_imagen`, spritesheets, fuentes, íconos del HUD, efectos de tablilla, `envolver_texto`, `superficie_con_alpha`, `dibujar_sprite_en_rect` | `nucleo/recursos.py` |
| Sprites de personajes/NPC, decoraciones del presente, `crear_jugador_local` | `mundo/personajes.py` |
| `cargar_mapa_principal`, `cargar_mapa_presente`, `cargar_mapa_edificio`, mapeo de hitboxes | `mundo/mapas.py` |
| Colisiones con hitboxes y zonas caminables | `mundo/colisiones.py` |
| Cámara y conversión de coordenadas | `mundo/camara.py` |
| Patrullas de NPC del presente | `mundo/npcs.py` |
| Movimiento del jugador e interactuables | `mundo/jugador.py` |
| Plataformas/puentes de la aldea (`crear_grafo_fisico`) | `mundo/grafo_aldea.py` |
| `crear_mundo` | `mundo/creacion.py` |
| HUD: objetivo, flecha guía, pistas, celular, controles | `un_jugador/hud.py` |
| Dibujo del mapa, decoraciones, jugador, troncos, F3 | `un_jugador/dibujo_mapa.py` |
| Códice y tutorial de dimensión | `un_jugador/codice.py` |
| Tablilla: pociones, consecuencia, clasificación, final | `un_jugador/tablilla.py` |
| Análisis de publicación, transición, diálogo, mensaje, eco | `un_jugador/escenas.py` |
| Ventana y presentación del lienzo | `un_jugador/ventana.py` |
| `main()` (bucle del modo un jugador) | `un_jugador/partida.py` |

## Archivos de la raíz movidos a paquetes

| Antes | Ahora |
| --- | --- |
| `Arboles.py`, `logica_juego.py`, `dimensiones.py`, `grafo_fisico.py`, `propagacion_informacion.py`, `habilidades_jugador.py`, `conversaciones.py` | `logica/` |
| `audio_manager.py` | `audio/` |
| `animacion.py`, `particulas.py`, `propagacion_visual.py` | `graficos/` |
| `reparacion_puentes.py` | `mundo/` |
| `hitbox_editor.py`, `alineacion_editor.py`, `personaje_editor.py` | `editores/` |
| `Botones.py`, `Logica.py`, `animaciones.py` (sin importadores) | `legado/` |

`interfaz/`, `multijugador/`, `bots/`, `herramientas/` y `tests/` no cambiaron
de estructura; solo se actualizaron sus imports.

## Dependencias entre capas (sin ciclos)

`nucleo` → `logica`, `graficos`, `audio` → `mundo` → `un_jugador` → `juego.py`.
`interfaz` (multijugador) usa `nucleo`, `mundo` y `un_jugador`.
El servidor (`multijugador/`) no importa Pygame; solo usa `logica/Arboles.py`.
