# Rendimiento

Herramienta: `python herramientas/benchmark.py --segundos 60` (headless, servidor
real en 127.0.0.1, 4 participantes por WebSocket, cliente 0 dibujando con
`SDL_VIDEODRIVER=dummy`). PC de desarrollo: Windows 10, Python 3.14.2, pygame-ce 2.5.8.

## Antes (rama `multi-principal`, commit base `de42b04`)

Participantes: 1 cliente dibujando + 3 clientes que caminan al azar (todavía no
había bots por red). Datos crudos: `docs/benchmark_antes.json`, perfil:
`docs/perfil_antes.txt`.

| Métrica | Valor |
| --- | --- |
| FPS medio (Clock.tick(60)) | 57,1 |
| Frame p50 / p95 / p99 (actualizar + dibujar) | 2,95 / 5,57 / 11,58 ms |
| Tick del servidor p50 / p95 / máx | 1,58 / 3,01 / 12,14 ms |
| Mensajes/s por cliente | 19,2 |
| Bytes/s por cliente | ~118 000 (≈ 6,1 KB por estado completo) |
| Ping | no se medía |

Perfil cProfile de 30 s (incluye hilos del servidor y del cliente), funciones
con más tiempo propio:

| Función | Tiempo propio | Nota |
| --- | --- | --- |
| `multijugador/movimiento.py:bloqueado` | 9,05 s | Recalcula cada hitbox (123) en cada consulta. |
| `dict.get` (21 M llamadas) | 3,26 s | Casi todo desde `bloqueado`. |
| `pygame.time.Clock.tick` | 2,83 s | Espera del límite de 60 FPS (no es trabajo). |
| `Surface.blit` (145 k) | 1,95 s | ~122 blits por frame. |
| `builtins.max` (7,2 M) | 1,03 s | `bloqueado`. |
| `movimiento.py:rectangulo` (465 k) | 0,83 s | Conversión de hitbox repetida. |
| `math.hypot` (3,1 M) | 0,70 s | |
| `builtins.min` (3,1 M) | 0,47 s | |
| `partida_multijugador.py:dibujar` | 0,36 s | |
| `Font.render` (27 k ≈ 23 por frame) | 0,34 s | Texto sin caché. |
| `round` (2 M) | 0,34 s | `bloqueado`/`rectangulo`. |
| `juego.py:111 normalizar_ruta` (962 k) | 0,25 s | `es_hoja_portales` por decoración y frame. |
| `json.encoder.iterencode` | 0,21 s | Estado completo en cada tick. |
| `json.decoder.raw_decode` | 0,21 s | |

Conclusiones que guían las fases 5 y 6:
1. Colisiones: precalcular geometría en píxeles y filtrar con rejilla espacial.
2. Red: ~118 KB/s por cliente; hace falta enviar deltas y solo lo de la dimensión.
3. Cliente: cachear textos y quitar trabajo de cadenas por frame.

## Después

(se completa en la fase 7)
