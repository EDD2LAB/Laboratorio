# Mejora visual de la dimensión Presente

## Alcance

Los cambios se aplican al mapa de la dimensión Presente. La imagen fuente
`Imagenes/Fondos/Mapas/Presente/MapaPresente.png` mide 998 × 576 píxeles, es
opaca hasta los bordes y no tiene franjas vacías que recortar. Se conserva el
asset original: crear una versión recortada no eliminaría espacio sobrante y
podría desalinear las posiciones normalizadas del mapa.

## Escala y cámara

- El lienzo lógico del juego conserva su resolución de 960 × 720 y se escala
  hasta ocupar el área completa de la ventana o pantalla, usando su resolución
  disponible.
- El mapa se dibuja en el rectángulo de mundo de 960 × 554, centrado
  verticalmente (origen `(0, 83)`), y conserva la proporción de la imagen fuente.
- El jugador del Presente usa una caja visual de 22 × 30 píxeles. Los NPC usan
  cajas visuales de 29 × 33 píxeles; Kael y el Mensajero urbano, situados al
  lado izquierdo, usan 24 × 28 píxeles. Sus hitboxes son más pequeñas y quedan
  ancladas a los pies.
- La cámara usa zoom fijo 1,6 y sigue continuamente al jugador con suavizado
  de respuesta 8/s, sin depender de sectores ni puentes. El recorte siempre se
  limita al rectángulo del mapa para no mostrar el fondo exterior al llegar a
  los bordes.
- La conversión de coordenadas del mouse usa el zoom y el recorte activos.
- Al redimensionar la ventana, los eventos del mouse se convierten respecto al
  área completa de renderizado. El escalado del mapa usa vecino más cercano
  para mantener los píxeles definidos.

## Patrullas de NPC

Las rutas están en `Hitboxes/Mapas/Presente/MapaPresente_hitboxes.json` como
waypoints normalizados respecto al mapa. Hay rutas de ciclo y de ida y vuelta.
La posición de cada NPC se ancla por los pies al primer punto de su ruta.

- Velocidad base: 38 píxeles/s, con variación de ±10 %.
- En cada waypoint hay 30 % de probabilidad de pausar entre 500 y 1500 ms.
- Al cambiar de dirección, el NPC usa su reposo direccional durante 120 ms.
- Los sprites de caminata se cargan de las filas direccionales y se animan cada
  140 ms; al no caminar se conserva el sprite de reposo.
- Las patrullas se detienen durante diálogos, escenas fuera del mapa y el
  minijuego de reparación. El movimiento evita el mapa exterior, hitboxes de
  pared o zonas caminables configuradas, al jugador y a otros NPC.
- F3 muestra los límites del mapa y de cámara, hitboxes, rutas y waypoints.

Las rutas actuales recorren tramos algo más largos sobre el pavimento visible
del mapa. No hay un sistema de búsqueda de caminos: si una ruta se bloquea, el
NPC espera y vuelve a intentarlo en su siguiente actualización.

## Verificación

Se añadieron regresiones para la carga de las cinco rutas y sus sprites, el
desplazamiento dependiente del delta, la sincronización de hitboxes y la pausa
durante diálogos. También se comprueban el seguimiento suave de cámara, sus
límites en las cuatro esquinas y la relación de aspecto del viewport.

Validación local: `py -3.11 -m unittest discover -s tests -q` y
`git diff --check`.
