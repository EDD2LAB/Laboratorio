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


---

# Progreso — rama `arte-pendiente`

Implementa el arte que ya existía en `Imagenes/` y aún no se usaba.

| Bloque | Estado |
| --- | --- |
| A. Expediente AVL | Pendiente: faltan `logica/expediente_avl.py` y `datos/casos_expediente.json` |
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
