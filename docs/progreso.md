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
