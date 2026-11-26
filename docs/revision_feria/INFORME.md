# Informe de la revisión para la Feria Gamer

Rama `revision-feria`, unida en `multijugador` (`3d344b7`). Sin push. Protocolo **25** (no cambió).
Detalle de cada hallazgo en `hallazgos.md` y de cada paso en `progreso.md`.

## 1. Qué se corrigió

**Robustez (que no se cierre)**
- E1: no había manejador de errores. Ahora un error en la partida se registra y el juego vuelve al menú. Un error fatal sale con código 1, sin el diálogo de PyInstaller, para que Feria.bat lo reabra.
- E2: en el `.exe` sin consola se perdían todos los avisos; ahora van a `logs/juego.log`.
- E3: un fallo en "Ver la batalla final" cerraba el juego; ahora vuelve al menú.
- E5: exportar el informe sin permiso de escritura cerraba el juego; ahora usa otra carpeta o avisa.
- A6: un error en una sala congelaba todas las salas del servidor; ahora se cierra solo esa sala, con un aviso.
- B2: un fallo de los bots en la campaña local cerraba el juego; ahora se omite ese paso de los bots.

**Lógica y flujo**
- A1: quien se desconectaba llevando un objeto del puente dejaba el encargo bloqueado para siempre; ahora el objeto se suelta.
- A2: lo mismo con la llave de supervisión de Ciudad Núcleo, que dejaba el final sin salida.
- A3: un doble clic en los minijuegos del final respondía la orden siguiente sin verla y costaba señal.
- A4: el árbol AVL del informe final quedaba con 1 caso y 5 pendientes; al ganar, los pendientes entran solos en orden.
- A5: "Continuar" del cierre no funcionaba si la victoria llegaba con la persona dentro de un edificio.
- F4: "Volver al menú" desde la Demo llevaba al formulario de la campaña.
- F5: los clics hechos durante la carga se saltaban la intro.

**Bots y red**
- B1: si todas las personas perdían la conexión, los bots votaban y avanzaban solos. Ahora las esperan durante la gracia de 120 s.
- B3: con personas en la partida, un bot ya no reintenta la batalla por su cuenta.
- C1: un destino o una categoría que no eran texto cerraban el WebSocket.
- C4: el mensaje de reconexión fallida decía "Vuelve a entrar a la sala", algo imposible con la partida ya iniciada.
- C6 y C7: el arranque en frío de Render mostraba "Comprueba la dirección" o "Expecting value…". Ahora dice "Despertando el servidor, puede tardar un minuto… (N s)".
- C9: si la versión del juego no coincide con la del servidor, el aviso dice ahora las dos versiones.
- C10: un JSON inválido respondía en inglés.

**Textos**
- G3: "Suplantacion" sin tilde.
- G4: "la propia NÚCLEO".
- G6: términos del Presente que aparecían en Ciudad Núcleo.
- G7: "Presente y Futuro" en lugar de los nombres de las eras.
- G8: "por misterio".
- G9: faltaban F y B en la ayuda.
- A9: plurales con 1 ("faltan 1 pistas") y "tres terminales" cuando son cuatro.
- C2: el texto de salir le prometía al anfitrión que sus compañeros seguirían, aunque la sala se cerraba.

**Kit y repositorio**
- M2: el LEEME decía que se podía jugar por LAN; el multijugador necesita internet.
- L1 y L2: los README decían protocolo 18 y 8 casos.
- L8: `Actualizar.bat` mezclaba cambios si fallaba el checkout.
- N1: el verificador de Docker fallaba en falso y no probaba `/feria`.

## 2. Qué se mejoró

**Para el visitante (todo lo decidiste tú)**
- Demo rápida: La Copa y, 8 s después de resolverla, la batalla final.
- Salto al final con Ctrl+Shift+F2 (y depuración con Ctrl+Shift+F3); ya no aparece en la ayuda.
- En el panel inicial, Enter o E elige "Aprender jugando".
- HUD más grande: indicadores a 13 px y ayuda a 14 px (antes 11 px).
- En modo feria:
  - los ajustes de un visitante se olvidan al volver al menú por inactividad;
  - la X o Alt+F4 piden confirmación;
  - la inactividad vuelve al menú también desde formularios, ajustes y "Ver la batalla final", pero nunca cierra una sala en línea.
- La Demo empieza siempre limpia: sin el nombre ni el rol del visitante anterior.

**Salas en línea (tus decisiones)**
- Quien sale deja su personaje a un bot.
- Si el anfitrión sale durante la partida, la sala pasa a otra persona.
- Un microcorte de menos de 5 s no suelta lo que la persona lleva.

**Robustez**
- `nucleo/registro.py`: registros en `logs/`, `faulthandler` para fallos de C y errores de hilos.
- El proceso se declara DPI-aware: se ve nítido con el escalado de Windows al 150 % de este PC.
- La pantalla completa no se minimiza al perder el foco.

**Feria de los Ecos QR (arreglos mínimos, sin cambiar cómo se juega)**
- Sin internet pasa al servidor local tras 3 fallos (antes esperaba hasta 90 s).
- Ya no deja una sesión viva en Render si se cancela.
- El aviso del registro solo aparece si de verdad se escribió.

**Kit**
- LEEME_FERIA reescrito (Feria QR, red Privada, Render, registros, Demo, SmartScreen).
- `empaquetar.ps1` exige segno e incluye la caché de zonas caminables: la primera Demo del `.exe` pasa de 9,2 a 6,6 s.
- `.gitignore` con `logs/` y `.venv*/`.
- La versión de Python está documentada: 3.14 para el cliente y el `.exe`, 3.12 para Render.

**Herramientas**
- `benchmark.py` por escenarios.
- `prueba_larga.py`.
- `partida_bots.py`.
- `diagnostico_exe.py` comprueba también la Demo, la inactividad, F2, los registros y el QR local.

## 3. Qué se optimizó

Mismo PC (Ryzen 7 4800HS), sin pantalla, bucle real del menú.

**Campaña con bots**

| Escenario (960×720) | FPS antes → 60 s → 20 s | Cuadro p95 (ms) antes → 60 s → 20 s | Peor cuadro (ms) antes → 60 s → 20 s |
| --- | --- | --- | --- |
| La Copa | 52,3 → 60,7 → 60,1 | 21,2 → 12,7 → 16,8 | 536 → 103 → 121 |
| Distrito Conecta | 56,6 → 59,3* → 55,1 | 21,9 → 19,0* → 26,1 | 890 → 93* → 102 |
| Ciudad Núcleo | 55,7 → 59,1 → 56,2 | 20,6 → 19,6 → 23,1 | 1158 → 217 → 242 |
| Final | 56,9 → 59,6 → 57,6 | 20,3 → 14,6 → 22,2 | 961 → 212 → 224 |
| La Copa a 1920×1080 | 49,1 → 60,4 → 56,3 | 22,3 → 14,4 → 22,3 | 573 → 100 → 115 |

- La corrida de 20 s de hoy queda casi entera dentro del precalentado de las otras eras (3 ms por cuadro), por eso su p95 es más alto. La de 60 s refleja mejor el juego ya caliente.
- \* Una corrida de 60 s de Distrito Conecta dio un único cuadro de 69 s que no se repitió al repetirla (59,3 FPS y 93 ms como máximo). Parece una pausa del sistema del portátil.

**Otros congelones**
- Primera ruta de cada bot: de 535/812/724 ms a 26/65/55 ms (La Copa, Distrito Conecta, Ciudad Núcleo).
- Salto al final: de 703 ms a 39 ms.

**Servidor en red**

| Escenario | Tick p95 | Datos por cliente |
| --- | --- | --- |
| 4 personas | 1,09 → 1,12 ms | 4,3 KB/s |
| 2 personas y 2 bots | 1,68 → 2,02 ms | 3,0 KB/s |

**Memoria**
- Prueba larga de 30 minutos, solo antes de los cambios: en la campaña se estabiliza en unos 810 MB y en el final pasa de 588 a 686 MB.
- La prueba de después no se corrió, porque se pidió no hacerlo.

**Ejecutable**
- 156,5 → 156,7 MB (zip de 131,9 MB).
- La primera Demo tarda 6,6 s (antes 9,2).

## 4. Pruebas

- Antes: 736 pruebas.
- Ahora: 780, todas OK en `multijugador`.
- Pruebas nuevas:
  - `test_robustez_feria`
  - `test_memoria_colisiones`
  - `test_desconexiones_feria`
  - `test_decisiones_feria`
  - `test_red_feria`
  - `test_humo_campana` (propiedades AVL y campaña completa con 4 bots)
- Se actualizaron 6 pruebas para reflejar las reglas nuevas que decidiste (bots, salida de la sala, reintento y tamaño del HUD).
- Partidas completas solo con bots: 9 de 9 llegaron al informe, con el árbol AVL completo. Cubren las dos variantes del agua y las tres dificultades, y cada una tardó entre 9 y 20 s reales.
- Dos clientes en la misma PC: OK (ping de 1,5 ms y se ven moverse).
- Docker simulado: OK, y `/health` responde con protocolo 25.
- Diagnóstico del `.exe` desde `%TEMP%\prueba_tg`: OK.

## 5. Pendiente y por qué

**Decisiones pendientes (no implementadas)**
- G2: el aviso legal del expediente.
- G12: el crédito de la fuente "Determination", que el juego no carga.
- H5/M6: sacar del `.exe` unos 18 MB de imágenes sin uso, sin borrarlas.
- H6: los jingles del final suenan en bucle.
- H7/H8: volúmenes por defecto (La Copa suena 4–5 dB más baja).
- A8: la estrella de equipo cuenta a los bots.
- B4: un bot da su pista sin que se la pidan.
- C8: no hay multijugador sin internet.
- E10/H2: `smoothscale` en dos íconos.
- L9: archivos históricos versionados.
- M5: `robocopy` sobrescribe las preferencias del `.exe`.

**No se hizo**
- H1: `smoothscale` cada cuadro en la poción; está en `un_jugador/`, que no se toca.
- Tirones de 100–240 ms que quedan: el primer dibujo tras cargar y la primera ruta guía del HUD en Ciudad Núcleo (cuadrícula de 4 px).
- La prueba larga de después.

**Necesita a otra persona**
- **Profesora:** el texto legal del expediente. Por tu indicación de hoy:
  - la línea que decía "pendiente de revisión" ahora dice "Resumen legal con fines educativos.";
  - quité la nota sobre responsabilidad penal de menores.
- **Fernando:** la Feria QR dice "Era un Acusación Personal" (G5) y puede apuntar a una IP virtual sin avisar (I4); solo se le reportan.
- **Jimara:** decidir qué assets sin uso pueden quedar fuera del `.exe` (H5).

## 6. Decisiones que tomé por mi cuenta

- Los clics se prueban contra los botones del cuadro anterior: es lo que permite dibujar una sola vez por cuadro.
- Si la vista cambia entre cuadros, esos botones se descartan.
- La memoria de colisiones se comparte por mapa y se precalienta:
  - la era inicial, en la barra de carga (la primera Demo carga unos segundos más);
  - las demás, poco a poco durante el juego;
  - el servidor, en un hilo al arrancar.
- Las otras eras se precargan durante la intro: un pequeño tirón ahí en vez de 0,7 s al viajar.
- Más de 3 errores en 10 s cierran el juego a propósito, para que Feria.bat lo reabra limpio.
- Margen de microcorte: 5 s. Espera de la Demo antes de saltar: 8 s.
- La línea de ayuda queda en 14 px. Subí de 5 % a 5,5 % el umbral de la prueba de área del HUD.
- No uso `--specpath`, por el riesgo con las rutas de los datos.

## 7. Para la feria: lo que debes saber

**Qué abrir y en qué orden**
1. Conecta los parlantes.
2. Marca la Wi-Fi como **Privada**.
3. Abre `https://la-copa-salas.onrender.com/health` unos 10 minutos antes y espera a que diga `"protocolo": 25`.
4. Abre "Timeless Glitch - Feria" (Feria.bat). La primera vez, SmartScreen pide "Más información → Ejecutar de todas formas".

**Salto al final:** **Ctrl+Shift+F2** dos veces en menos de 3 s, durante la partida. Ctrl+Shift+F3 muestra la depuración. No están en la ayuda.

**Sin internet:**
- "Demo rápida" y "Campaña con bots" funcionan.
- No hay multijugador entre PC.
- La Feria QR pasa sola al servidor local (o pulsa L).

**Render:**
- Abre `/health` antes, porque tarda hasta un minuto en despertar.
- **No despliegues ese día.**

**Feria de los Ecos QR:**
- Con internet: los votos van por Render.
- Sin internet: los celulares deben estar en la misma Wi-Fi, la red como Privada y el firewall preparado con `preparar_pc_feria.ps1`.
- Si el QR muestra una IP rara, pulsa I.
- Espacio o Enter muestran el resultado, N abre una ronda nueva y Esc vuelve al menú.

**Registros y cierres:**
- Los errores quedan en `C:\TimelessGlitch\logs\errores.log` y la salida en `logs\juego.log`.
- Si hay un error, el juego vuelve solo al menú. Si se cierra, Feria.bat lo reabre en 2 s.
- Para salir de verdad, cierra primero la ventana negra de Feria.bat y después el juego (Esc → Salir → Sí, cerrar).

**Manual Deploy:** **sí hace falta**, pero solo después de hacer push y no el día de la feria. El servidor cambió en:
- los bots, que esperan a las personas y cubren a quien se va;
- las salas, que se cierran solas si fallan y pasan a otra persona si sale el anfitrión;
- el margen de microcortes;
- los objetos y la llave que se sueltan;
- el árbol AVL completo;
- el precalentado de mapas.

El protocolo sigue en 25, así que un servidor sin desplegar sigue funcionando con el juego nuevo, solo que sin estos arreglos.

**Pendiente tuyo:**
- Push de `multijugador` (yo no lo hice).
- Volver a armar el `.exe` con `Actualizar_exe.bat`: el `.exe` de `dist/` se armó antes del cambio de texto del expediente.
