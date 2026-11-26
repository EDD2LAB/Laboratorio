# Revisión para la Feria Gamer: registro de avance

Rama `revision-feria`, creada desde `multijugador` en `aa96ae2` (25 de noviembre de 2026).
Si la sesión se corta, retomar desde aquí.

## Paso 0: git

- `multijugador` local iba 2 commits por delante de `origin/multijugador` (`4ef7d36`) y 0 por detrás:
  `git fetch` no trajo nada nuevo, así que no hubo que unir nada.
- Sin cambios pendientes salvo `Actualizar.bat`, que no está en git (decisión pendiente).

## Fase 0: línea base

- [x] Suite completa: **736 pruebas, 0 fallos** (517 s, con los auditores corriendo a la vez).
- [x] Benchmark ampliado (`herramientas/benchmark.py --escenario ...`): campaña con bots por era,
      batalla final, sala de 4 clientes, sala mixta (2 personas y 2 bots del servidor) y tamaño de pantalla.
- [x] Prueba larga nueva: `herramientas/prueba_larga.py` (ciclo Demo → F2 → menú).
- [x] Benchmark completo en `benchmark_antes.json`. Campaña: 49–57 FPS, cuadro p95 de 20–23 ms
      y congelones de hasta 1,2 s. Sala en red: 59,5 FPS, tick p95 de 1,1–1,7 ms y 3–4,4 KB/s por cliente.
- [ ] Prueba larga de 30 minutos (se corre sobre una copia de la línea base).
- [x] `.exe` armado en 64 s: 156,5 MB (zip de 131,8 MB). El diagnóstico desde `%TEMP%\prueba_tg`,
      sin Python en el PATH, da OK en 19 s; la primera campaña tarda 9,2 s con la caché vacía.

## Fase 1: auditoría

- [x] 105 hallazgos en `hallazgos.md` (con subagentes de solo lectura para A, B/C, E/F, G/H e I/L/M/N).
- [x] Primera y segunda tanda de preguntas respondidas.

## Decisiones del usuario (25 de noviembre)

1. Demo rápida: **La Copa y luego salto a la batalla final**.
2. F2: **combinación secreta** (Ctrl+Shift+F2 dos veces), fuera de la ayuda; F3 igual.
3. Python: **3.14 para el cliente y el `.exe`, 3.12 para el servidor (Docker)**; solo documentación.
4. `.bat`: **subir los tres** (con `Actualizar.bat` corregido).
5. Nota para menores: **agregarla** (queda pendiente de revisión de la profesora).
6. Cortes de conexión: **los bots esperan a las personas** mientras sigan en la partida (servidor, Manual Deploy).
7. AVL: **completar el árbol al ganar** con los casos pendientes.
8. Modo feria: **no guardar ajustes**; se restauran al volver al menú por inactividad.
9. Visitante: **Enter/E en el panel inicial**, **HUD más grande**, **confirmar al cerrar en feria** e
   **inactividad solo en la campaña local**.
10. Bots en línea: **reintento espera a las personas**, **un bot cubre a quien se va**,
    **la sala pasa a otra persona si sale el anfitrión** y **margen de unos segundos en microcortes**.
11. Feria QR: **arreglos mínimos** (pasar a local tras fallos de red, cerrar la sesión cancelada, mensaje del log).
12. Firewall: **solo documentar** (el LEEME explica cómo marcar la red como Privada).

## Fase 2: correcciones

- [x] `c219df1` Robustez: registro de errores, un solo dibujo por cuadro, recuperación al menú.
- [x] `89a8f68` Bots sin congelones, desconexiones, Demo rápida y decisiones 1–8, textos, red, docs, kit.
- [x] `6b16f42` Tercera tanda (decisiones 9–12) y salto al final sin tirón.
- [x] Pruebas nuevas: propiedades AVL y campaña completa con 4 bots (`tests/test_humo_campana.py`);
      herramienta `herramientas/partida_bots.py`.

Pendiente de decisión (para el informe): G2 aviso "pendiente de revisión", G12 crédito de la fuente,
H5/M6 excluir del `.exe` imágenes sin uso, H6 jingles en bucle, H7/H8 volúmenes, A8 estrellas,
B4 pista sin pedir, C8 multijugador sin internet, E10/H2 smoothscale, L9 archivos históricos, M5 robocopy.
No se hará (riesgo): H1 smoothscale de la poción (vive en `un_jugador/`, que no se toca).

## Fase 3: verificación final

(en curso)
