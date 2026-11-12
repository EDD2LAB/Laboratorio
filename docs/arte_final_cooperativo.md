# Arte propio del final cooperativo

Generación con `image_gen`, herramienta integrada, sin CLI ni API key.
Los originales se conservaron en la carpeta de imágenes generadas de Codex;
las copias consumidas por el juego están dentro del repositorio:

- `Imagenes/FinalCooperativo/ConsolaSupervision.png`: fondo opaco del panel.
  Se escala una vez a 900 x 675. Los cuatro retos comparten el marco y sus
  controles se dibujan por código en las posiciones comprobadas por las pruebas.
- `Imagenes/FinalCooperativo/ModuloSupervision.png`: módulo con transparencia
  real, recortado al contenido y ajustado a 16 x 24 para el mapa.

## Prompt del panel

Create one production-ready raster background for a 2D cooperative children's pixel-art game, UI-mockup asset. Landscape 4:3 composition. A futuristic human-supervision console in a lush teal cyberpunk city, matching retro 16-bit RPG pixel art: navy and deep turquoise panels, restrained cyan circuit lights and warm gold metal border, small leaves around the outer edges, an abstract glowing cyan core device centered near the TOP border only. Large almost-flat very dark teal central area covering 80 percent of the image, reserved for game text and controls that will be drawn in code. Crisp square pixels and stepped outlines, limited palette, no gradients or blurry photorealism. No text, letters, numerals, characters, logos, buttons or watermark. Decorative details only near the edges; no gameplay objects in the central usable area. Opaque background. The final asset will be scaled with nearest-neighbor into a 860 by 590 panel; keep borders regular and the center uncluttered.

El panel definitivo se ajustó a 900 x 675 al revisar los cuatro minijuegos,
conservando la proporción 4:3 y dejando margen para las instrucciones.

## Prompt del módulo

Use case: stylized-concept. Production game sprite for a retro 16-bit pixel-art 2D cooperative cyberpunk fantasy game for children. Exactly one portable supervision energy module, isolated and centered, with a genuinely transparent background. Small upright hexagonal brass and dark navy technological casing, bright turquoise crystal core, tiny warm gold locking tabs and readable chunky square-pixel highlights. Front-facing near-flat icon, slightly isometric depth. Recognizable simple silhouette when displayed at 32x32 pixels. No ground, no shadow outside the object, no pedestal, no text, no border, no character, no extra objects. Hard crisp pixel edges, limited palette, no realistic rendering and no smooth gradients.

Se verificó alfa 0 en el exterior del objeto. El juego usa el módulo como
ilustración de la carga; no transporta el PNG por red ni cambia las colisiones.
