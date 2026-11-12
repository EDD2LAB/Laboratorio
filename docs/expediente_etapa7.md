# Etapa 7: expediente AVL compartido

## Libro legible

- Ocho nodos distribuidos por recorrido inorden en un área separada de la
  leyenda. Círculos de radio 18 y áreas clicables de 44 x 44 sin solapamientos.
- Colores por era, gravedad dentro del círculo y orden de resolución debajo.
  La ficha seleccionada indica el nombre completo de la era. El nodo de
  comparación sigue en dorado durante la inserción guiada.
- Las decisiones se nombran según la era del caso, con respaldo en las opciones
  de su misión. «Verificar» en el Futuro significa reconfigurar a NÚCLEO con
  supervisión, sin heredar la etiqueta de verificar una publicación del Presente.
- Resumen con decisión, consecuencia registrada y explicación breve para
  recordar. Las pruebas se consultan en una vista separada. Rueda, RePág/AvPág
  y botones Arriba/Abajo permiten leer contenido largo dentro de un área recortada.
- Las leyes, sanciones y notas existentes no se modifican. Se identifican como
  referencias del proyecto pendientes de revisión del profesor.

## Animación real del AVL

El servidor conserva una descripción compacta de la última inserción: forma
anterior, colocación sin equilibrar y forma tras cada rotación real. Solo lleva
ids de casos ya registrados y relaciones entre ramas; no duplica las pruebas
ni revela eventos futuros. Cubre giros simples y dobles.

El cliente interpola entre esas formas, con 850 ms por paso. Nunca decide la
posición oficial ni envía una inserción al pulsar «Ver cómo se ordenó».
Al terminar muestra el árbol autoritativo. Durante el movimiento se desactivan
los botones de inserción y las áreas de selección de los nodos; cerrar el libro
sigue disponible. Sin metadatos de animación se muestra el árbol estático.

Se conserva el protocolo 14: los campos nuevos son aditivos. La validación de
revisión y paso, los desempates por orden y las reglas de inserción no cambian.

## Comprobaciones

- Seis regresiones nuevas sobre rotaciones simples/dobles, separación de ocho
  nodos, repetición sin modificar estado, decisión por era y lectura completa.
- Simulación del paquete del servidor: dos jugadores y dos bots, 200 ticks,
  ocho casos disponibles, sin importar Pygame. No es un build real de Docker.
- Estado de prueba con cuatro jugadores y ocho fichas con sus pruebas:
  22.723 bytes, por debajo del límite de 32.768. No mide todos los estados posibles.
- Revisión visual de ocho casos y fichas de Ciudad Núcleo en resumen y pruebas.
- Batería general: 513 pruebas aprobadas de 514 (430,507 s). La restante
  comprobaba que todo el contenido legal se dibujara en una sola pantalla;
  se adaptó al nuevo desplazamiento para recorrer y comprobar cada línea.
- Verificación final: 44 pruebas de AVL, libro, leyes y exportación aprobadas
  en 21,922 s. La batería general completa no se repitió después de adaptar esa
  prueba; las modificaciones visuales finales también quedaron cubiertas.

## Alcance y publicación

No se editaron Hitboxes, mapas ni el catálogo legal. El exterior nuevo del
Futuro sigue pendiente del trabajo de la compañera. Música pendiente del usuario.
La batalla y el Modo Feria con QR siguen fuera de esta etapa.

Trabajo local: no implica push ni actualización de Render.
