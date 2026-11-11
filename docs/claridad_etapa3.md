# Etapa 3: orientación para niños de 8 a 12 años

## Cambios

- Una instrucción concreta visible en el mapa: fuente de la pista en La Copa,
  puerta o persona en Distrito Conecta, y siguiente tarea/prerrequisito en Núcleo.
- La flecha y el camino usan el mismo objetivo que la instrucción. Durante el
  análisis del celular no mandan al jugador hacia una votación prematura.
- Indicadores: `!` para la tarea actual, `?` para una pista nueva en la escena,
  check al obtener la pista o completar el objetivo. La tecla aparece cerca del
  punto de interacción. No son hitboxes nuevas ni revelan respuestas oficiales.
- F1 empieza por Controles: tarjetas con teclas, acciones y una leyenda de los
  indicadores. Conserva Reglas, Clasificación y Árbol AVL. Se corrigió la ayuda
  que todavía decía que no se podía viajar a Ciudad Núcleo.
- El celular muestra cuántas marcas faltan en Analizar, incluso al abrir Decidir.
  No se bloquean decisiones ni se alteran sus consecuencias: investigar sigue
  siendo una elección del equipo; ahora conoce el requisito antes de votar.
- En las tres eras se muestra quién falta por elegir y cuándo no hay mayoría,
  indicando que se puede hablar y cambiar un voto. El servidor solo publica ids
  pendientes y la existencia del empate, no la elección privada de cada jugador.
- Nuevos campos opcionales `faltan_votar` y `empate` en los contextos digitales.
  Se conserva protocolo 13: son metadatos aditivos, sin acciones nuevas. El
  cliente conserva el contador de pendientes si el servidor aún no los envía.

## Arte y carga

`interfaz/orientacion.py` busca `Indicadores/exclamacion_4f.png`,
`interrogacion_4f.png`, `check_4f.png` y `tecla_<X>.png` dentro de Imagenes.
Las teclas esperan tiras horizontales de dos cuadros. Los indicadores esperan
cuatro. Si faltan o su ancho no se puede dividir, se dibujan con figuras y texto.
Las imágenes se cargan y escalan una vez; las teclas se guardan en caché por
nombre y tamaño. No se reemplaza ni se pide regenerar el arte que ya existe.

Los marcadores se filtran por dimensión e interior, y respetan ocultar el HUD.
Los logros visuales no se confunden con un viaje ni con un cambio de caso.

## Textos pendientes de aprobación

`herramientas/auditar_textos.py` genera `docs/textos.csv` y `docs/textos.md`.
Es un inventario estático de candidatos: registra archivo, línea y palabras,
incluye algunas etiquetas técnicas y no reconstruye todos los textos dinámicos.
Las propuestas de tarjetas breves no se aplican al juego ni recortan normas,
testimonios o pruebas. Se revisa su contexto antes de aprobarlas.

El objetivo de 20 palabras es una pauta para las propuestas, no un límite que
corte silenciosamente los textos educativos durante la partida.

## Validación

Pruebas de guía y acciones, análisis de material, pendientes y empates sin
revelar votos, prerrequisitos de Núcleo, indicadores sin imágenes y carga en
caché. Capturas revisadas de la tarea en La Copa, F1 y aviso de análisis en el
celular. Las paredes y los archivos de contenido legal no se modifican.
Resultados completos en `docs/progreso.md`.
