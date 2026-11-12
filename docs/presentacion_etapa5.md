# Etapa 5: presentación visual, sin música

Alcance autorizado: integrar imágenes disponibles, mejorar la respuesta visual
y revisar tamaños y posiciones. La música queda pendiente de selección del usuario.

- Diálogos: retratos propios de Naira, Odran, Darek y Ronaldo Vélez, recortados
  al contenido visible y encajados en 78 x 88 sin deformar. Kael y Tarek usan
  sus retratos existentes; antes podían mostrar la apariencia del jugador.
- Clasificación: ilustraciones reales para aviso comunitario y categorías
  digitales. Las tarjetas conservan su proporción dentro del área clicable
  de 180 x 200. El celular usa miniaturas de 34 x 38 junto a etiquetas claras,
  sin revelar la categoría correcta ni cambiar las decisiones disponibles.
- NÚCLEO: reposo de ocho cuadros y estados de nueve cuadros, inferidos por
  celdas cuadradas. Inquieto durante la investigación, carga al reunir las
  pistas, sereno con resultado correcto y saturado al cederle control.
  Cuadros de 32 x 32 en el mundo, en el centro del avatar anterior; retrato
  de 104 x 104 en el celular. No se adelanta la derrota ni la batalla.
- Botones: frases envueltas antes de reducirse, siempre dentro del botón.
  La etiqueta se guarda en una caché limitada; el estado presionado desplaza
  ligeramente el texto. Se conservan bloqueo, teclado y áreas clicables.
- Avisos: «Listo» y «Atención» distinguen confirmaciones y rechazos por
  texto y color, también para el narrador. Los avisos generales no se prefijan.
- Respaldos: sin retrato se conserva el sprite anterior; sin tarjetas se
  conservan las generadas o las opciones de texto; sin tira válida se mantiene
  el avatar por código. Sin cargas de recursos al importar módulos.

## Límites deliberados

No se modificaron mapas, paredes, portales, colisiones, reglas, protocolo ni
contenido legal. El mapa nuevo del Futuro requiere revisar su geometría en
la etapa de exploración: mide distinto al provisional. No se asignaron los
retratos ambiguos a personajes por suposición. La tarjeta de control autónomo
está disponible, pero no crea una clasificación nueva en el Futuro.

El inventario y su generador reflejan los recursos conectados. Introducción,
fuentes nuevas y generador de pantallas no forman parte de estos tres cambios.

## Validación (2026-11-11)

- 500 pruebas completas aprobadas en 314,645 s.
- Tras los ajustes finales de tamaño y contraste: 42 pruebas de presentación,
  Ciudad Núcleo y contenido manipulado aprobadas en 16,967 s.
- Revisión visual de diálogo con Naira, clasificación en el celular y NÚCLEO
  sobre el mapa; sin deformaciones, etiquetas fuera del botón ni avatar sobredimensionado.
- Persisten los cinco avisos anteriores de imágenes de eventos ausentes
  (`agua`, `proviciones`, `pergaminon`, `tinta`, `farol`); no son fallos de pruebas.
- Validado localmente. No publicado en GitHub ni desplegado en Render.
