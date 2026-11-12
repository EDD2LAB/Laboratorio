# Etapas de trabajo - 10 de noviembre de 2026

## Etapa 1: base actualizada

- Integrados el arte de `eb1318b` y el análisis de encuesta de `383f7a2`, sin
  modificar los archivos aportados por sus autores.
- Instalación aislada en `.venv`, Python 3.12, pygame-ce 2.5.8 y aiohttp 3.14.5.
- README principal y de red actualizados; `/health` describe tres eras y ocho
  casos. Protocolo 12 conservado: no cambian los mensajes de partida.
- Inventario reproducible en `docs/inventario_recursos.csv`; estado respecto
  al plan en `docs/arte_esperado.md`.
- Integrar el arte en Git no lo conecta todavía al juego. Se mantiene el mapa
  provisional hasta comprobar geometría y paredes del mapa nuevo.
- Push y despliegue se realizan al publicar la etapa; una versión local validada
  no significa que ya esté activa en Render.

## Trabajo restante

El protocolo local actual es 15. Render conserva la última versión publicada
hasta realizar el próximo push y despliegue.

Las etapas 1 y 2 se publicaron y desplegaron en Render en `be2f6df`.
Las etapas 3 y 4 se publicaron junto con el resaltado del equipo en `bef84e9`.
La etapa 3 se implementó en `58cc8c0`: ver `docs/claridad_etapa3.md`.
La etapa 4 corrige movimiento y atascos: ver `docs/movimiento_etapa4.md`.

| Etapa | Alcance | Criterio de cierre |
| --- | --- | --- |
| 2. Red | Ping, límites por sesión, recuperación y Docker | Varias salas con IP compartida, contenedor y reconexión comprobados |
| 3. Claridad | Tarea visible, objetivos, controles, análisis, empates y textos cortos | Un jugador nuevo entiende qué hacer; textos revisados antes de recortarlos |
| 4. Movimiento | Esquinas, objetos, puente y bots | Atascos corregidos sin alterar paredes de JSON |
| 5. Presentación | Arte, respaldos, música, sonidos, fuentes, intro y generador seguro | Recursos usados si existen y respaldo si faltan |
| 6. Exploración | Elia, Arel, geometría del Futuro e interiores con contenido | Entradas y salidas caminables y tareas con propósito |
| 7. Expediente | Ocho nodos legibles, decisión por era, rotaciones y explicación infantil | Árbol consistente con servidor; contenido legal revisado por profesor |
| 8. Batalla | Diseño completo, rebelión, preparación y final cooperativo | Victoria y derrota claras; NÚCLEO reconfigurado bajo supervisión humana |

El Modo Feria con QR sigue sin implementar y es una ampliación posterior.
El PDF refiere un prompt de batalla que no incluye: falta ese diseño completo.
No borrar ramas del equipo sin confirmación específica.

La presentación visual de la etapa 5 se trabaja en `docs/presentacion_etapa5.md`.
La música queda pendiente por petición del usuario. Esto no completa las etapas 6 a 8.

La exploración de la etapa 6 está implementada localmente; el mapa exterior nuevo
del Futuro sigue pendiente de revisión manual. Ver `docs/exploracion_etapa6.md`.

La etapa 7 mejora el expediente compartido y su animación; ver
`docs/expediente_etapa7.md`. El contenido legal sigue pendiente del profesor.

## Línea base del análisis previo

En `5d1f74f`: 442 pruebas aprobadas. Medición headless de 15 s con cuatro
clientes locales: 60 FPS y unos 4,1 KB/s por cliente. No es una medición de Render
ni una validación con múltiples redes. La validación de esta etapa se registra
en `docs/progreso.md`.

El final cooperativo acordado con el usuario se implementa en
`docs/final_cooperativo.md`: cuatro minijuegos enlazados y reintento sin perder
casos. No implementa un prompt de batalla que no haya sido entregado. Música y
mapa exterior nuevo del Futuro siguen pendientes.
