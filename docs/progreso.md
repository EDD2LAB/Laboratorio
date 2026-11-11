# Progreso — rama `multi-principal`

Tarea: multijugador como modo principal, modo "Jugar con bots" sobre el mismo
servidor, eliminar el modo un jugador (solo con paridad completa), optimizar a
60 FPS y mínimo lag, reglas en CLAUDE.md.

## Fase actual: 1 (inventario de paridad)

## Hecho
- Fase 0: commit base `de42b04`. Pruebas antes: 107, 1 falla previa
  (`test_bots_cooperativos`, los bots no completan el encargo del caso 1).
  `herramientas/benchmark.py`, `multijugador/servidor_local.py`, métricas de red
  aditivas. Números en `docs/rendimiento.md`.

## Pausa
La tarea se pausó tras la Fase 0 porque se pidió primero modularizar el
proyecto (rama `refactor/modularizar`, creada desde este punto). Al retomar,
partir de esa rama: las rutas de los módulos cambian (solo `juego.py` queda en
la raíz).

## Falta
- Fases 1 a 8.

## Expediente AVL y sorteo — 2026-11-08

- Integrado expediente autoritativo para los cuatro eventos de La Copa,
  actualización por rectificación y cola de inserción paso a paso.
- Consulta compartida con T y validación de cada movimiento del árbol en servidor.
- Sorteo privado por semilla de variantes y persona mencionada en la ayuda;
  el tutorial se conserva. Avisos temporales renovables desde el segundo caso,
  con caducidad del servidor y copias que conservan su vencimiento original.
  Catálogo educativo sin leyes o sanciones inventadas.
- Docker y protocolo 8 preparados. Alcance y pendientes en
  `docs/expediente_y_sorteo.md`.
- Validación final: 207 pruebas aprobadas y revisión visual del expediente
  y de las tarjetas temporales. Cambios locales, pendientes de push y despliegue.

---

# Progreso — rama `arte-pendiente`

Implementa el arte que ya existía en `Imagenes/` y aún no se usaba.

| Bloque | Estado |
| --- | --- |
| A. Expediente AVL | Integrado aparte: ver `docs/expediente_y_sorteo.md` |
| B. Informe y finales | Finales hechos (`interfaz/finales.py`); informe pendiente, depende de A |
| C. Ayuda y accesibilidad | Hecho, salvo la pestaña del árbol AVL, que depende de A |
| D. Ciberacoso | Parcial: análisis, comparador, sellos, avatares y etiqueta. Faltan los eventos de burlas y perfil falso, que no existen en la campaña |
| E. Efectos del celular | Hecho |
| F. Habilidades y propagación | Hecho en el multijugador (`interfaz/efectos_mapa.py`) |
| G. Caldero, troncos, puentes, diálogos | Hecho; las tiras de balanceo no coinciden con los puentes y se conserva la rotación |
| H. Ambiente | Catálogo del editor listo; la niebla se retiró a pedido |
| I. Materiales | Hecho |

Asignación de filas del caldero: 1 estable, 2 peligroso, 3 crítico, 4 campaña terminada.
Barra de recarga: llena si se puede usar, media si falta la prueba propia, vacía si ya se usó.

## Correcciones de claridad del multijugador — 2026-11-08

- Etiquetas de jugadores y NPC distribuidas sin superponer fondos; los personajes
  fuera de cámara dejan de generar nombres pegados a los bordes.
- Botón Casos visible con detalles cerrados, contador de casos por ordenar,
  cursor de mano y ayuda del atajo T. Respeta la opción de ocultar el HUD.
- Los bots en reposo dejan espacio gradualmente, sin mover al jugador, atravesar
  paredes o abandonar el alcance de una interacción. Animación de reposo al llegar.
- La bot Aspirante es Mira y usa su apariencia femenina por defecto. Se conservan
  las variantes elegidas por los jugadores. Kael es un NPC con diálogo propio;
  las propuestas de Mira se consultan en un archivo señalizado en el mapa.
- Integrado `e071830` del equipo: Timeless Glitch, diálogos, apariencias, farol,
  accesibilidad y efectos. Las conversaciones de fuentes renuevan los avisos
  temporales igual que las interacciones directas.
- Corregida la exclusión de `logica/conversaciones.py` del contexto de Docker.
  Verificada la importación del servidor desde ese contexto sin Pygame.
- Protocolo 9; requiere actualizar el juego y el servicio en Render.
- Validación: revisión global de 286 casos y repetición de 60 pruebas afectadas
  (18 de finales, 22 de diálogos, 12 de AVL/sorteo y 8 de claridad), aprobadas.
  Se actualizó la expectativa antigua que dibujaba a Mira como NPC fijo.
  Revisada visualmente la vista integrada del mapa.

---

# Progreso — rama `terminar-cambios` (Fase 3)

Línea base antes de empezar: 338 pruebas, 60,2 FPS, 246,9 KB/s por cliente.

- Bloque A: Kael y Tarek por defecto; quien no se elige queda como NPC y el
  elegido no se duplica; textos del puente norte; regla en CLAUDE.md. La flecha
  `IndicadorDirrKael.png` ya señalaba el objetivo del equipo, no a Kael.
- Bloque B: icono de ventana y logo animado en el menú. No hay ffmpeg en esta
  máquina, así que `Video_icono.mp4` no se convirtió.
- Bloque C: informe final (`interfaz/informe_final.py`) con recorrido inorden,
  línea de tiempo, reporte, sello, exportación y pestaña AVL en F1.
- Bloque D: Ciudad Núcleo completa (Archivista, Representante, cuentas, barreras,
  pulsos, habilidades); un equipo solo de bots recorre las tres eras.
- Bloque E: estado por diferencias (`multijugador/delta.py`), protocolo 11.
  Antes 246,9 KB/s por cliente (12,4 KB por mensaje: `caso` 9,7 KB, `privado` 1 KB,
  `jugadores` 0,8 KB); después 4,3 KB/s con 19,6 mensajes/s y 60,3 FPS.
# Etapa 1 - base actualizada (2026-11-10)

- Integrados `origin/multijugador` (`eb1318b`, 28 imágenes nuevas) y
  `origin/main` (`383f7a2`, análisis de encuesta), sin conflictos ni pérdida
  de los archivos aportados. Las ramas locales se alinean al cerrar la etapa.
- Preparado `.venv` con Python 3.12.10, pygame-ce 2.5.8 y aiohttp 3.14.5;
  requirements de cliente y narración opcional. `pip check` sin incompatibilidades.
- README principal y multijugador reescritos, CLAUDE actualizado y docs del
  Futuro corregidos. Los estados históricos siguientes se conservan como historial.
- `/health`: tres eras, ocho casos y protocolo 12, sin cambiar mensajes de
  partida. Importación y consulta del servicio comprobadas sin importar Pygame.
- Inventario generado: 741 archivos físicos (714 en Imagenes, 24 en Audios,
  3 en Fuentes; incluye archivos auxiliares) y 94 rutas concretas del plan.
  CSV con tamaños PNG y documento con alternativas, pendientes e identidades
  de retratos por confirmar. El arte nuevo aún no está conectado al juego.
- Suite completa con pygame-ce: **443 pruebas aprobadas en 281,914 s**.
  Quedan avisos de cinco imágenes antiguas ausentes y cortes de red simulados
  por pruebas; ya no aparecen avisos de `pygame.Window`.
- Benchmark headless local, 4 clientes, 15 s: **60 FPS**, trabajo de frame
  medio 3,87 ms / p95 4,64 ms, aproximadamente 4,0 KB/s por cliente.
  No mide Render, varias salas ni redes diferentes.
- Ningún JSON de Hitboxes cambió. Sin borrado de ramas ni despliegue en Render.
- Ramas remotas ya contenidas, solo candidatas a revisar antes de borrar:
  Botones, botones, Logica-arboles, arte-pendiente, leyes-penas y npc-dialogos.
  No se borró ninguna; esa acción requiere confirmación específica.

---
# Etapa 2 - red y estabilidad (2026-11-11)

- Protocolo 13: ping/pong de aplicación cada 3 s por WebSocket y LAN, promedio
  móvil de RTT y F3 con FPS, ping y KB/s. El ping usa una cuota independiente
  del movimiento y no se entrega como evento de juego.
- HTTP: consultas por token (300/min); crear y unirse por IP (60/min), con
  respuesta 429 y Retry-After. Regresión de 30 sesiones con IP compartida,
  consultando cada 0,6 s durante un minuto simulado, sin rechazos.
- Reconexión: lectura de espera recuperable hasta 30 s; en partida se conserva
  identidad y rol por 120 s, con reintentos del cliente durante 110 s. Si caduca
  el anfitrión con otro humano activo, se conserva y transfiere la sala. Una
  salida explícita sigue cerrándola. No se añade persistencia entre reinicios.
- Corregidos el aviso de recuperación del lobby, el plazo tras intentos lentos,
  la limpieza de sockets antiguos y el manejo de clientes sin métricas en F3.
- Docker copia los paquetes de lógica y JSON/hitboxes permitidos, con cachés
  excluidas. Herramienta de simulación de reglas y COPY: 60 archivos, aplicación
  importada sin Pygame y sala de 2 humanos + 2 bots durante 200 ticks; estado
  dentro de MAX_MENSAJE. Resultado en `validacion_docker_etapa2.json`.
  Docker no está instalado: no se realizó una construcción real de Linux.
- Primera suite: 457 pruebas, 7 errores al leer métricas de clientes simulados.
  Corregido el acceso opcional; segunda suite: **457 aprobadas en 259,458 s**.
  Tras los ajustes finales, **30 pruebas de red aprobadas** (15 nuevas, 8 de
  salas y 7 de movimiento). El caso adicional de intentos lentos se añadió
  después de iniciar la suite completa y se validó en ese grupo de 15.
- Estabilidad: 45 s, cuatro clientes, 2981 estados, tres cortes simulados y
  tres reconexiones. `estabilidad_etapa2.json`. Los cortes ahora se pueden
  programar con `--cortes 8 20 32`; los valores por defecto se conservan.
- Benchmark local headless de 15 s: 60,2 FPS, 4,04 ms de trabajo medio de frame,
  p95 5,03 ms y unos 4,1 KB/s por cliente. RTT local 0 ms por resolución del
  reloj; corregido el benchmark para no confundirlo con muestra ausente.
- F3 renderizado e inspeccionado. Sin cambios en Hitboxes. Sin push ni Render.
- Se requiere actualizar servidor y PC al protocolo 13 al publicar esta etapa.
  Ver `docs/red_estabilidad.md` para límites, recuperación y pruebas.

---
