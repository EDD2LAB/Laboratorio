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
# Etapa 3 - orientación infantil (2026-11-11)

- Tarea concreta siempre visible, con fuente, puerta o persona. La flecha y el
  camino de luces comparten ese objetivo; durante el análisis se indica C y se
  deja de enviar al jugador hacia la pantalla para votar.
- Indicadores !, ?, check y tecla de interacción con respaldo por código,
  caché de imágenes/teclas y filtro por escena. Los logros no saltan entre eras
  o interiores. En Núcleo se guían los prerrequisitos de conexiones, archivos,
  llave y firma sin revelar soluciones de los minijuegos.
- F1 abre controles visuales con ocho tarjetas y leyenda de señales. Conserva
  las pestañas anteriores y corrige la ayuda obsoleta de Ciudad Núcleo.
- El celular avisa cuántas marcas faltan analizar antes de elegir, sin bloquear
  decisiones ni cambiar sus consecuencias. Las tres eras muestran pendientes
  de voto y empate sin publicar elecciones privadas de otras personas.
- Protocolo 13 conservado: campos opcionales aditivos de presentación, sin
  acciones nuevas ni cambios en validación de decisiones. El cliente conserva
  el contador como respaldo si aún no recibe ids pendientes del servidor.
- Auditoría estática: 1081 candidatos textuales, 12 con más de 20 palabras;
  CSV completo y siete propuestas cortas en docs/textos.md. No se aplican esas
  propuestas a testimonios, pistas ni normas. Sus límites de análisis estático
  están documentados: no equivale a capturar todas las pantallas dinámicas.
- Revisión completa: 466 pruebas, 465 aprobadas y una dependencia de orden en
  la prueba del ping (podía llegar el snapshot antes del error). Corregida para
  esperar el evento correcto. Repetición final de 54 pruebas de red, guía,
  accesibilidad y Presente: todas aprobadas. Otras 8 de orientación aprobadas
  tras el ajuste final del seguimiento por escena.
- Revisadas capturas de tarea/tecla en La Copa, controles F1 y aviso de análisis
  en celular; comprobado con estado real que la guía busca al Corredor de Datos.
- Rendimiento actual: 33,4 FPS / 8,13 ms de trabajo medio de frame en 15 s con
  cuatro clientes. Se investigó la diferencia respecto al registro anterior de
  60 FPS: la base aislada be2f6df también dio 33,1 FPS / 10,66 ms en 10 s, con
  el mismo intérprete y PC. Comparación corta, sin caída adicional observada de
  esta etapa; no permite atribuir la variación general a una causa concreta.
- Empaquetado simulado: servidor sin Pygame, dos humanos más dos bots y 200
  ticks aprobados. No se hizo una construcción real de Docker.
- No cambiaron paredes, arte ni el catálogo legal. Sin push ni Render para
  esta etapa; las etapas 1 y 2 sí están publicadas en be2f6df.
- Documentación: docs/claridad_etapa3.md. Siguiente etapa: atascos y movimiento.

---
# Etapa 4 - movimiento y atascos (2026-11-11)

- Reproducidos seis fallos en los once casos iniciales: unión de zonas
  caminables, líneas con margen excesivo, roce con objetos pequeños, escape
  de un bloqueo de puente y paridad del motor local.
- Geometría y desplazamiento comunes en logica/movimiento_suave.py, sin Pygame.
  Cobertura por unión de zonas; colisión real segmento/rectángulo para líneas;
  subpasos de hasta 1 px, deslizamiento y ayuda lateral limitada a 3 px que
  consume el mismo presupuesto de movimiento. Se evitan cortes de esquina.
- El bloqueo original del puente permite salir a quien ya está dentro, sin
  profundizar ni atravesar paredes. Sigue impidiendo entrar desde fuera.
- Bots: anclajes alcanzables desde su posición real, giros sin saltar vértices,
  tramos finales para radios pequeños y consumo del tiempo entre nodos sin
  reducir su velocidad. Escape de bloqueo temporal a pie y posterior recálculo.
- Las 16 regresiones finales de movimiento pasan, junto con la suite completa:
  **482 pruebas aprobadas en 298,030 s**. Las campañas con bots, reparación,
  desplazamiento por red y arranque quedan cubiertos por esa suite.
- Comprobación adicional con semilla 42: 960 posiciones en las tres eras y
  cinco interiores coincidieron entre motor local y autoritativo (sin NPC);
  353 movimientos desde posiciones libres conservaron colisión y velocidad.
- Empaquetado simulado: 61 archivos, servidor sin Pygame, 2 humanos + 2 bots,
  200 ticks y estado dentro de MAX_MENSAJE; validacion_docker_etapa4.json.
- Benchmark headless local, cuatro clientes, 15 s: 33,4 FPS, trabajo medio de
  frame 6,55 ms / p95 8,69 ms, unos 3,7 KB/s por cliente. Comparable al registro
  actual de etapa 3 (33,4 FPS); no es una medición de Render ni garantiza un
  rendimiento concreto en otras PC.
- Protocolo 13 conservado; controles y estados mantienen sus formatos.
  Ningún archivo de Hitboxes cambió. Sin push ni despliegue de las etapas 3 y 4.
- Documentación: docs/movimiento_etapa4.md. Sigue presentación, arte y audio.

---
