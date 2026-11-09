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
