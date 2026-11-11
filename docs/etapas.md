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

La etapa 2 está implementada localmente con protocolo 13; ver
`docs/red_estabilidad.md` y los resultados en `docs/progreso.md`. Requiere
publicación y despliegue antes de usarla con el servidor de Render.

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

## Línea base del análisis previo

En `5d1f74f`: 442 pruebas aprobadas. Medición headless de 15 s con cuatro
clientes locales: 60 FPS y unos 4,1 KB/s por cliente. No es una medición de Render
ni una validación con múltiples redes. La validación de esta etapa se registra
en `docs/progreso.md`.
