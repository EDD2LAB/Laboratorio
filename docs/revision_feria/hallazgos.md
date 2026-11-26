# Hallazgos de la auditoría (Fase 1)

Un hallazgo por fila. Impacto en la feria: **alto** (puede cerrar o congelar el juego, atascar
al visitante o romper la partida), **medio** (confunde o degrada de forma notable) o **bajo**
(cosmético o limpieza). Decisión: "sí" cuando cambia lo que el jugador ve o vive, el protocolo,
borra archivos o toca el modo QR de Fernando.

Medido en el PC de desarrollo (Ryzen 7 4800HS, Windows 10, Python 3.14.2, pygame-ce 2.5.8,
pantalla 1920×1080 con escalado de Windows al 150 %).

## D. Rendimiento

| ID | Archivo:línea | Problema | Impacto | Arreglo propuesto | Decisión |
| --- | --- | --- | --- | --- | --- |
| D1 | `interfaz/inicio.py:729` y `:812` | `MenuInicio.ejecutar` dibuja el cuadro completo dos veces (una antes de procesar la entrada para preparar los botones). Campaña en La Copa a 960×720: 37 FPS, cuadro p50 22 ms, p95 30 ms. | alto | Dibujar una vez por cuadro; los clics se prueban contra los botones del cuadro anterior, que es lo que la persona vio. | no |
| D2 | `interfaz/inicio.py:547-550` | Durante la partida, `MenuInicio.dibujar` pinta el fondo animado del menú y un velo `Surface(960×720, SRCALPHA)` nuevo, que luego tapa el mapa entero (unos 1,4 ms por dibujo). | medio | No dibujar fondo ni velo con la partida (y la intro) a pantalla completa; comprobar píxel a píxel que el resultado es idéntico. | no |
| D3 | `bots/navegador_bot.py:55`, `multijugador/movimiento.py:123` | Primera búsqueda de ruta de cada bot con la memoria de colisiones en frío: de 0,5 a 0,8 s en el hilo principal. Son de 3 a 4 congelones en el primer minuto de cada era (La Copa: máx. 535 ms; Distrito Conecta: 812 ms; Ciudad Núcleo: 724 ms). | alto | Ver D4 y D5: memoria compartida por mapa y precalentado. | no |
| D4 | `multijugador/movimiento.py:48-76` | Cada `PartidaMovimiento` (cada Demo nueva) y cada vista del cliente crean su `ColisionesMapa` con `_memoria` vacía: **todos los visitantes** sufren los congelones de D3, aunque el mapa no cambie. | alto | Compartir `_memoria` entre instancias con la misma firma de mapa (solo depende de paredes, zonas y pies, que forman parte de la firma). | no |
| D5 | `logica/zonas_caminables.py:39` | El componente caminable (paso de 8 px, mismas aristas que el A* de los bots) se lee de `cache/` y no precalienta la memoria. Precalentar cuesta 0,69 s en La Copa, 1,03 s en Distrito Conecta y 1,19 s en Ciudad Núcleo. | medio | Precalentar la era inicial durante la barra de carga y las otras en el bucle con un presupuesto de pocos ms por cuadro; el servidor de Render, al arrancar. | no |
| D6 | `multijugador/partida_local.py:67-118`, `bots/gestor_bots.py:85-88` | La campaña local corre el servidor y los bots a 60 Hz dentro del cuadro y arma el estado completo cuatro veces por cuadro (uno por bot y uno para la vista). | medio | Medir después de D1 a D5; si pesa, reutilizar el estado del cuadro o bajar los bots a 20 Hz. | no |
| D7 | `interfaz/partida_multijugador.py:1583` | Cada cuadro escala la capa de efectos (`SRCALPHA`) a 960×720 y la mezcla con alfa sobre el mapa (unos 1,2 ms). | bajo | Medir; solo tocarlo si sigue haciendo falta. | no |
| D8 | `herramientas/benchmark.py` | El benchmark original no medía la campaña con bots, la batalla final ni el bucle real del menú (doble dibujo incluido). | medio | Ampliado: escenarios `campana_*`, `final`, `sala_mixta`, `--tamano` y `herramientas/prueba_larga.py`. | no |

## E. Robustez y recuperación

| ID | Archivo:línea | Problema | Impacto | Arreglo propuesto | Decisión |
| --- | --- | --- | --- | --- | --- |
| E1 | `interfaz/inicio.py:706-826`, `juego.py:11-13`, `herramientas/empaquetar.ps1` (`--windowed`), `herramientas/feria/Feria.bat:9` | No hay manejador global de errores. Una excepción en la partida (la lógica del servidor y los bots corre en el mismo hilo; `mision.py:122-126` solo captura `ValueError`) cierra el juego. En el `.exe` sin consola, PyInstaller muestra un diálogo "Unhandled exception" y el proceso queda esperando: `Feria.bat` (`start /wait`) **no lo reabre**. | alto | Manejador en `ejecutar`: registrar en `logs/` y volver al menú si hay partida. En `juego.py`: registrar, salir con código 1 (sin diálogo) para que Feria.bat lo reabra. `sys.excepthook`, `threading.excepthook` y `faulthandler`. | no |
| E2 | `nucleo/rutas.py:6`; `print` en audio y arte | En el `.exe` sin consola, `sys.stdout` y `sys.stderr` son `None`: todos los avisos se pierden. | medio | Redirigir `stdout` y `stderr` al registro cuando son `None`. | no |
| E3 | `herramientas/vista_combate.py:315-349` | "Ver la batalla final" no captura errores (solo `try/finally`). La Feria QR sí (`feria/pantalla.py:310-314`). | medio | Capturar, registrar y volver al menú. | no |
| E4 | `juego.py` | El proceso no se declara DPI-aware. Con el escalado del 150 % de este PC, Windows estira la ventana y el pixel art se ve borroso. El manifiesto del `.exe` no trae `dpiAware`. | medio | `SDL_WINDOWS_DPI_AWARENESS=permonitorv2` (lo trae el SDL2 2.32.10 incluido) antes de `pygame.init()`. | no |
| E5 | `interfaz/informe_final.py:55-72` | Exportar el informe escribe en `_internal\informes\` sin `try`: si la carpeta no admite escritura, el `PermissionError` cierra el juego. | medio | `try/except OSError` y mostrar "No se pudo guardar". | no |
| E6 | `interfaz/menu_pausa.py:245` y `:264` | Un doble clic encadena acciones: el segundo clic en "Ajustes" de la pausa cae en "HUD: visible (H)" y oculta el HUD. | bajo | Ignorar clics en botones durante 250 ms después de un cambio de vista. | no |
| E7 | `interfaz/inicio.py:731-732` | En modo feria, la X o Alt+F4 cierran sin confirmar (Feria.bat lo reabre a los 2 s más la carga; mientras tanto se ve el escritorio). | bajo | En modo feria, tratar QUIT en el menú como Esc (confirmar). | sí |
| E8 | `interfaz/menu_pausa.py:97` | **Sospecha:** con `FULLSCREEN`, SDL puede minimizar la ventana al perder el foco (Alt+Tab, notificaciones). | bajo | `SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS=0` antes de `pygame.init()`. | no |
| E9 | `interfaz/inicio.py:28, 69, 178`; `menu_pausa.py:332`; `vista_combate.py:197` | `pygame.image.load` directo, sin respaldo y con `os.path` en vez de `RAIZ` (los 11 archivos existen). | bajo | Usar el cargador con respaldo. | no |
| E10 | `nucleo/recursos.py:172, 190` | `smoothscale` en `cargar_icono_hud` y `cargar_efecto_tablilla`, contra la regla del pixel art. | bajo | Cambiar a `transform.scale` (cambio visual leve). | sí |

## F. Experiencia del visitante

| ID | Archivo:línea | Problema | Impacto | Arreglo propuesto | Decisión |
| --- | --- | --- | --- | --- | --- |
| F1 | `interfaz/partida_multijugador.py:939-948`; `interfaz/menu_pausa.py:421` | F2 (dos veces) salta al final también en modo feria, y la ayuda F1 lo anuncia ("F2 F2: ir al final"). F3 abre un panel de depuración. | medio | Según la decisión del usuario (desactivar, combinación secreta o dejarlo igual). | sí |
| F2 | `interfaz/inicio.py:520`; `feria/pantalla.py:433-468`; `vista_combate.py:326-346` | La vuelta al menú por inactividad solo funciona en la partida. Quedan fuera la Feria QR, "Ver la batalla final" y las vistas del menú (`campana_rol`, `multijugador`, `formulario`, `sala`, `confirmar_salir`, Ajustes y Ayuda). El visitante siguiente encuentra lo que dejó el anterior. | medio | Volver a `principal` tras 120 s en las vistas del menú y salir de "Ver la batalla final". La Feria QR: preguntar. | sí (solo la Feria QR) |
| F3 | `interfaz/inicio.py:516-534` | En modo feria, la inactividad del PC anfitrión de una sala LAN cierra `ServidorSala` y termina la partida de todos los PC. | medio | En modo feria, aplicar la vuelta automática solo a la campaña local. | sí |
| F4 | `interfaz/menu_pausa.py:217-219` → `interfaz/inicio.py:455-458` | Después de la Demo rápida, Pausa → "Sí, volver al menú" deja al visitante en el formulario "CAMPAÑA LOCAL CON BOTS" y no en el menú. | medio | Recordar desde dónde se empezó (Demo → `principal`). | no |
| F5 | `interfaz/inicio.py:125-163`; `interfaz/intro.py:80-81` | Los clics hechos durante la barra de carga (unos 3 s) quedan en cola y se saltan la intro en el primer cuadro. | medio | Vaciar la cola de clics y teclas al terminar la carga. | no |
| F6 | `interfaz/menu_pausa.py:141-199` | En la feria, los ajustes de un visitante (volumen a 0, intro apagada, F11 → ventana) quedan guardados para todos los siguientes. | medio | En modo feria, no guardar en disco y recargar al volver por inactividad. | sí |
| F7 | `interfaz/cooperativo.py:505-512, 829-830` | El panel inicial "TU SIGUIENTE AVENTURA" solo responde al ratón (o Esc): Enter, E y Espacio no hacen nada. | medio | Enter/E = "Aprender jugando", o mostrar "Esc: cerrar". | sí |
| F8 | `interfaz/partida_multijugador.py:282, 1777, 1812` | Letra del HUD de 11 px en el lienzo (unos 16 px reales a 1080p): difícil de leer a 1–2 m. | medio | Subir el HUD a 14 px y la línea de ayuda a 16, revisando solapes. | sí |
| F9 | `interfaz/inicio.py:420-421` | La Demo rápida reutiliza el nombre y el rol que dejó el visitante anterior. | bajo | Al volver por inactividad en modo feria, reiniciar nombre, rol y pestaña de ayuda. | no |
| F10 | `interfaz/menu_pausa.py:418-432`; `LEEME_FERIA.txt:56` | A la tarjeta F1 le falta B. La hoja impresa anuncia F11 al público (ver F6). | bajo | Ajustar la tarjeta y la hoja. | sí |

## I. Feria de los Ecos QR (de Fernando: solo integración y robustez)

| ID | Archivo:línea | Problema | Impacto | Arreglo propuesto | Decisión |
| --- | --- | --- | --- | --- | --- |
| I1 | `herramientas/feria/preparar_pc_feria.ps1:118`; `LEEME_FERIA.txt:14-15` | La regla del firewall solo abre el `.exe` en redes **Privadas**, y la Wi-Fi de este PC está como **Pública** (es lo predeterminado en redes nuevas). El respaldo local (8080) quedaría bloqueado para los celulares. | medio (alto sin internet) | Explicar en el LEEME cómo marcar la red como Privada, o abrir solo los puertos TCP 8080/8081/8090/8765 también en perfil Público. | sí (seguridad) |
| I2 | `feria/pantalla.py:367, 377-391` | Sin internet no pasa al servidor local enseguida: reintenta cada 3 s hasta 90 s ("Conectando…") salvo que se pulse L. | medio | Pasar a local tras 2–3 errores de red sin respuesta HTTP; o al menos poner "pulsa L" en el LEEME. | sí (código de Fernando) |
| I3 | `feria/pantalla.py:381, 413-417`; `feria/remoto.py:57-58` | Con Esc o L durante la conexión, si la sesión de Render se crea después, nadie la termina: queda un hilo `feria-remota` consultando cada 1,5 s (reproducido). | bajo | Terminar la sesión si se canceló mientras se creaba. | sí (código de Fernando) |
| I4 | `feria/web.py:197-213` | Sin Wi-Fi pero con adaptadores virtuales (Hyper-V, VirtualBox), el QR apunta a una IP inalcanzable sin avisar. | bajo | Documentar la tecla I en el LEEME. | no |
| I5 | `feria/pantalla.py:321, 334, 350-353, 490` | El mensaje "El detalle queda en cache/feria_error.log" aparece aunque no se escribió nada, y en el `.exe` la ruta real es `_internal\cache\`. | bajo | Mostrarlo solo si se escribió, con la ruta real. | sí (código de Fernando) |

## L. Repositorio y entorno

| ID | Archivo:línea | Problema | Impacto | Arreglo propuesto | Decisión |
| --- | --- | --- | --- | --- | --- |
| L1 | `README.md:4, 8-11, 30` | Dice protocolo 18 (es 25) y La Copa con 4 casos (son 2; en total 6). No menciona el modo feria, el `.exe` ni la Feria de los Ecos. | medio | Corregir y enlazar los documentos. | no |
| L2 | `multijugador/README.md:3, 23, 44, 70-72` | Dice protocolo 18 y ocho casos (hay 6). El paso 4 del despliegue pide comprobar valores de `/health` que ya no son, y no dice que hay que comprobar `/feria`. | medio | Corregir valores y añadir la comprobación de `/feria`. | no |
| L3 | `README.md:8,11`; `CLAUDE.md:11`; `requirements.txt:1`; `empaquetar.ps1:21`; `Dockerfile.multijugador:1` | Los docs dicen Python 3.12, pero el `.venv` y el `.exe` usan 3.14.2. Render usa 3.12 (Docker). Los 53 `.py` del servidor compilan en 3.12.10. | medio | Según la decisión 3. | sí |
| L4 | git | `multijugador` local va 2 commits por delante de `origin` (arte esencial): `Actualizar.bat` y los otros PC no lo reciben hasta hacer push. | medio | Push (lo hace el usuario). | sí |
| L5 | `docs/arte_esperado.md:11, 25-26, 193-194` | Da por faltantes las viñetas y los finales, que ya existen; pide viñetas 3/4 aunque la intro es de dos. | bajo | Actualizar. | no |
| L6 | `CLAUDE.md:47` | Describe `herramientas/` solo como "Benchmark". | bajo | Ampliar la descripción. | no |
| L7 | `.gitignore` | No cubre `logs/` ni `.venv2/` (solo la ignora el `.gitignore` interno del venv). | bajo | Añadir `logs/` y `.venv*/`. | no |
| L8 | `Actualizar.bat:5-6` (sin versionar) | No revisa si falla `git checkout multijugador`: entonces `git pull` mezclaría en la rama actual. | bajo | `if errorlevel 1` tras el checkout. | sí (decisión 4) |
| L9 | `docs/benchmark_*.json`, `analisis_encuesta/`, `Imagenes/Iconos/Video_icono.mp4` (6,6 MB) | Salidas históricas versionadas. El `.mp4` no lo usa ningún `.py` y entra al `.exe`. | bajo | Dejarlas; excluir el `.mp4` del `.exe`. Borrar algo: preguntar. | sí (borrar) |
| L10 | `requirements.txt`, `multijugador/requirements.txt` | Las dependencias directas están fijadas y coinciden con el `.venv`, pero las de aiohttp no, así que Docker puede instalar otras versiones. | bajo | Opcional: fijar con `pip freeze`. | no |
| L11 | ramas | Ninguna rama local ni remota tiene commits sin unir a `multijugador`. `main` va 8 por detrás. | — | Nada (no se borra ninguna). | no |

## M. Ejecutable y kit de feria

| ID | Archivo:línea | Problema | Impacto | Arreglo propuesto | Decisión |
| --- | --- | --- | --- | --- | --- |
| M1 | `herramientas/feria/LEEME_FERIA.txt:26-34` | No menciona la Feria de los Ecos QR (2.º botón del modo feria): qué necesita, sus teclas y abrirla unos minutos antes para despertar Render. | medio | Añadir una sección. | no |
| M2 | `herramientas/feria/LEEME_FERIA.txt:34` | "Varias PC: usa Multijugador por LAN con un router propio" es falso: el menú tiene `self.internet = True` fijo (`interfaz/inicio.py:72`) y el multijugador necesita internet y Render. | medio | Corregir el texto. | no |
| M3 | `.exe` con `cache/` vacía | La primera campaña del `.exe` recién copiado tarda 9,2 s en crearse (calcula las zonas caminables en frío). | medio | Precalcular `cache/zonas_caminables` al armar el `.exe` e incluirla. | no |
| M4 | `herramientas/empaquetar.ps1:24-30` | Si el `.venv` de quien arma no tiene segno, el `.exe` sale sin QR (PyInstaller solo avisa). El diagnóstico no prueba la Feria QR. | bajo | Comprobar segno antes de armar; probar el QR en el diagnóstico. | no |
| M5 | `Actualizar_exe.bat:15` | `robocopy /E` sobrescribe `_internal\preferencias_usuario.json` y deja archivos de builds anteriores. | bajo | Excluir las preferencias. | sí |
| M6 | `herramientas/empaquetar.ps1` | Entran al `.exe` sin usarse `Video_icono.mp4` (6,5 MB) y `video_manipulado_8f.png` (2,4 MB, original). | bajo | Excluirlos como "assets finales". | no |
| M7 | `herramientas/empaquetar.ps1` | Los `.spec` se regeneran en la raíz en cada build. | bajo | `--specpath build`. | no |

## N. Servidor en Render

| ID | Archivo:línea | Problema | Impacto | Arreglo propuesto | Decisión |
| --- | --- | --- | --- | --- | --- |
| N1 | `herramientas/verificar_contexto_docker.py:52, 95` | Falla en falso cuando `TEMP` usa nombre corto (`SEBAST~1`, como en este PC), y nunca llama a `crear_app()`, así que no comprueba `feria/`. | bajo | `Path.cwd().resolve()` y llamar a `crear_app()`. | no |
| N2 | Render en vivo | `/health` responde protocolo 25, 6 casos y `build 4ef7d36` (= `origin/multijugador`); `/feria` está desplegado. Los 2 commits locales no tocan archivos del servidor: **hoy no hace falta Manual Deploy**. | — | Nada (revisar de nuevo si se cambia el servidor). | no |

## A. Lógica y flujo

| ID | Archivo:línea | Problema | Impacto | Arreglo propuesto | Decisión |
| --- | --- | --- | --- | --- | --- |
| A1 | `multijugador/suministros.py:112-117, 153-161` | En línea, si quien lleva un objeto del encargo del puente se desconecta o sale, su carga queda en `cargas` para siempre: nadie lo recoge y el puente no se repara (reproducido). | alto | Soltar las cargas de quien no está presente, como ya pasa con las cestas. Solo servidor. | no |
| A2 | `multijugador/nucleo.py:242-250`; `multijugador/dialogos.py:171` | En línea, si quien lleva la llave de supervisión sale, la llave queda con esa persona: no se puede votar ni empezar el final (reproducido). | alto | Quitar la llave si su portador ya no está y avisar. Solo servidor. | no |
| A3 | `multijugador/final_cooperativo.py:274-363`; `interfaz/final_cooperativo.py:252-278` | Un doble clic en los minijuegos del Guardián o del Aspirante aplica el segundo clic a la orden siguiente sin verla, y puede costar 2 de las 3 unidades de señal (reproducido). | medio | El cliente ignora un segundo clic en `final:*` antes de 0,4 s. | no |
| A4 | `multijugador/campana.py:165-187`; `multijugador/expediente.py:72-78` | En el informe final, el árbol AVL y el inorden muestran solo los casos que alguien ordenó con T (los bots nunca lo hacen): 1 en el árbol y 5 pendientes, aunque la tabla lista 6 resueltos. | medio | Al llegar a la victoria, insertar en orden los pendientes antes del informe. | sí |
| A5 | `multijugador/final_cooperativo.py:203-211` | "Continuar" del cierre exige estar en la calle: si la victoria llega con la persona dentro de un edificio de Ciudad Núcleo, no puede avanzar (leído en el código). | medio | Atender "continuar" antes de comprobar dimensión e interior. | no |
| A6 | `multijugador/tiempo_real.py:172-196` | El bucle de simulación no protege cada sala: una excepción imprevista detiene la tarea y congela todas las salas sin desconectar a nadie. | alto (preventivo) | `try/except Exception` por sala: registrar y cerrar solo esa sala. | no |
| A7 | `interfaz/partida_multijugador.py:939-948`; `multijugador/movimiento.py:458-492` | F2 salta también para todo el equipo en línea, no archiva los casos saltados y marca el agua como "corregir". | medio | Ver decisión 2. | sí |
| A8 | `multijugador/campana.py:30, 502` | La estrella de equipo exige 2 pistas a todos, bots incluidos, y con personas los bots no comparten entre sí: casi nunca pasa de 4/6. | bajo | Contar solo a quienes deciden. | sí |
| A9 | `multijugador/nucleo.py:292, 342`; `multijugador/presente.py:255`; `interfaz/orientacion.py:43, 52, 156`; `multijugador/suministros.py:100-106` | "Completen las tres terminales" (son 4 tareas); plurales con 1: "faltan 1 pistas", "Faltan 1 personas", "faltan 1 marcas". | bajo | Corregir el número y usar singular con 1. | no |
| A10 | `bots/planificador_bot.py:42-72, 204-215` | Con 3 bots solos en la variante "descartar" del agua nadie llega al umbral y nadie vota: quedan bloqueados. | bajo | Si nadie vota en N s, el primer bot vota su mejor opción. | no |
| A11 | `multijugador/final_cooperativo.py:82, 308` | `invulnerable_hasta` se asigna y nunca se lee. | bajo | Quitarlo. | no |
| A12 | AVL y campaña | Correctos: 4200 inserciones con altura dentro de la cota e inorden ordenado. Los bots solos completan la campaña con 2 semillas (informe a 260–290 s simulados). | — | Añadir la prueba de propiedades a `tests/`. | no |

## B. Bots

| ID | Archivo:línea | Problema | Impacto | Arreglo propuesto | Decisión |
| --- | --- | --- | --- | --- | --- |
| B1 | `bots/planificador_bot.py:350-351`; `multijugador/movimiento.py:554`; `multijugador/mision.py:240-243` | "Hay personas" mira solo quién está *conectado*: si todas pierden la conexión a la vez (misma Wi-Fi), los bots juegan solos. Reproducido: a los 5,6 s votaron y cerraron el caso, y a los 90 s llevaron a todos a Distrito Conecta. Rompe la regla de CLAUDE.md. | alto | Contar como persona presente a todo humano que siga en la partida (hasta los 120 s de gracia). Solo servidor (Manual Deploy). | sí |
| B2 | `multijugador/partida_local.py:67-80` | Los bots de la campaña local no tienen protección: una excepción cierra el juego. | alto (preventivo) | Ver E1, más capturar alrededor de los bots. | no |
| B3 | `bots/final_cooperativo.py:32-35` | En `reintento` un bot pulsa "reintentar" aunque haya personas (`iniciar` sí las espera). | medio | Esperar a las personas también en `reintento`. | sí |
| B4 | `bots/planificador_bot.py:241-242` | El bot da su pista cuando la persona le dio la suya, sin que se la pidan (zona gris). | bajo | Solo con pedido explícito, o documentarlo. | sí |
| B5 | `bots/bot_cooperativo.py:76`; `multijugador/servicio_internet.py:138, 144` | Cuando una persona se va o caduca, ningún bot cubre su rol. | medio | Crear un bot para ese rol. Solo servidor. | sí |
| B6 | `bots/navegador_bot.py:41` | La firma de bloqueos se recalcula en cada arista del A*. | bajo | Una vez por búsqueda. | no |

## C. Multijugador y red

| ID | Archivo:línea | Problema | Impacto | Arreglo propuesto | Decisión |
| --- | --- | --- | --- | --- | --- |
| C1 | `multijugador/movimiento.py:390`; `multijugador/clasificacion.py:46` | `destino=[]` o `categoria=[]` lanzan `TypeError`: aiohttp cierra el WebSocket de ese jugador (solo con un cliente manipulado). | bajo | Validar el tipo `str`. | no |
| C2 | `interfaz/menu_pausa.py:439`; `multijugador/servicio_internet.py:122-141` | La pausa dice "tus compañeros podrán seguir", pero si sale el anfitrión la sala se cierra para todos (verificado). | medio | Texto distinto para el anfitrión, o pasar la sala a otra persona. | sí |
| C3 | `interfaz/inicio.py:516-534` | En modo feria, la inactividad del anfitrión en línea cierra la sala para todos (ver F3). | medio | Inactividad solo en la campaña local. | sí |
| C4 | `multijugador/cliente_internet.py:157`; `multijugador/servidor.py:77` | Tras 110 s sin conexión dice "Vuelve a entrar a la sala", pero una sala iniciada no acepta nuevas entradas. | medio | Texto: "Pidan crear una sala nueva". | no |
| C5 | `multijugador/tiempo_real.py:162-166` y otros | Un microcorte suelta al instante el minijuego del puente, la pieza o el módulo. | bajo | Margen de unos segundos. | sí |
| C6 | `multijugador/cliente_internet.py:253, 296`; `interfaz/inicio.py:294` | El arranque en frío tiene aviso y se puede cancelar, pero a los 60 s dice "No se pudo conectar… Comprueba la dirección" sin aclarar que el servidor sigue despertando. | medio | Consultar `/health` durante unos 90 s con "Despertando el servidor, puede tardar un minuto… N s". Solo cliente. | no |
| C7 | `multijugador/cliente_internet.py:85` | Una respuesta 200 que no es JSON muestra "Expecting value: line 1 column 1 (char 0)"; 502/503 dan un mensaje sin pista. | medio | Traducir: "El servidor está despertando, intenta en unos segundos". | no |
| C8 | `interfaz/inicio.py:72`; `multijugador/cliente_internet.py:33` | Sin internet no hay multijugador entre PC: LAN está desactivado y `validar_url` rechaza `http://192.168.x.x`. | alto si se piensa mostrar multijugador | Aceptar `http` para IP privadas y levantar el servicio en un PC de la red. | sí |
| C9 | `multijugador/servidor.py:68` | El aviso de protocolo distinto es claro, pero no dice la versión de cada lado. | bajo | Añadir las dos versiones. | no |
| C10 | `multijugador/tiempo_real.py:51, 62` | Un JSON inválido por HTTP responde con el texto del parser en inglés. | bajo | "Solicitud inválida." | no |
| C11 | `multijugador/delta.py:37` | `json.loads(json.dumps())` por cliente y tick: unos 0,2 ms. No es problema. | bajo | Nada. | no |
| C12 | servidor | La búsqueda de ruta fría de los bots de relleno (hasta 427 ms) e `iniciar` (0,19 s) corren en el bucle de aiohttp y congelan todas las salas mientras duran. | medio | D4 y D5 (memoria compartida y precalentado al arrancar). | no |

## G. Textos y coherencia

| ID | Archivo:línea | Problema | Impacto | Arreglo propuesto | Decisión |
| --- | --- | --- | --- | --- | --- |
| G1 | (no existe) | No hay nota para menores, aunque el expediente y el aviso legal muestran penas de prisión, y el público objetivo es de 8 a 12 años. | alto | Añadir una línea fija, por ejemplo: "Estas penas son para adultos. Los menores de 14 años no responden penalmente; de 14 a 18 aplica el Sistema de Responsabilidad Penal para Adolescentes (Ley 1098 de 2006)." | sí (contenido legal, lo revisa la profesora) |
| G2 | `interfaz/expediente.py:87` | Siempre dice "Contenido legal pendiente de revisión del profesor.", aunque todos los casos están `"verificado"`, y la docente es profesora. | medio | Mostrarlo solo si no está verificado; "del profesor" → "de la profesora". | sí |
| G3 | `interfaz/celular.py:435`; `multijugador/clasificacion.py:14-15` | En Distrito Conecta sale "En realidad era: Suplantacion" (clave interna sin tilde). | medio | Mostrar "Suplantación" y "Contenido auténtico". | no |
| G4 | `multijugador/final_cooperativo.py:34` | "La firma la propia NÚCLEO" (en el resto, NÚCLEO es masculino). | bajo | "La firma el propio NÚCLEO." | no |
| G5 | `feria/pantalla.py:252` | "Era un Acusación Personal" (código de Fernando). | bajo | Solo reportar a Fernando. | sí (Fernando) |
| G6 | `interfaz/celular.py:249, 331, 335` | En Ciudad Núcleo, la pestaña "Decidir" dice "Publicación viral" y "pantalla pública" (términos del Presente), y "CiudadNucleo" sin tilde. `test_coherencia_eras` no lo cubre. | bajo | Textos por era y añadir `celular` a la prueba. | no |
| G7 | `interfaz/menu_pausa.py:43, 420` | Dice "Presente y Futuro" en vez de "Distrito Conecta y Ciudad Núcleo". | bajo | Corregir. | no |
| G8 | `interfaz/cooperativo.py:623` | "una vez por misterio"; el resto dice "por caso". | bajo | "por caso". | no |
| G9 | `interfaz/menu_pausa.py:28-44` | La ayuda F1 no lista F ("Disparar el bláster") ni B. | bajo | Añadirlas. | no |
| G10 | `logica/Arboles.py`, `logica/logica_juego.py`, `un_jugador/*` | Faltan tildes en textos del modo un jugador (no se muestra en la feria). | bajo | No tocar (`un_jugador/` no se modifica). | no |
| G11 | `herramientas/auditar_textos.py` | Solo cuenta palabras y no mide cajas. Medición propia con la fuente real: sin desbordes en aviso legal, títulos, teclas, panel J y botones. | bajo | Añadir la medición de anchos como prueba. | no |
| G12 | `datos/creditos.json`; `interfaz/desenlace.py:11` | Acredita la fuente "Determination", que el código no carga. | bajo | Preguntar si se queda el crédito. | sí |

## H. Arte y audio

| ID | Archivo:línea | Problema | Impacto | Arreglo propuesto | Decisión |
| --- | --- | --- | --- | --- | --- |
| H1 | `un_jugador/tablilla.py:401-403, 580-581` (llamado desde `interfaz/escenas_multijugador.py:163-165`) | La animación de la poción de La Copa hace `smoothscale` y `rotate` en cada cuadro. | medio | Cambiar a `scale` y cachear (en una copia multijugador, sin tocar `un_jugador/`). | no |
| H2 | `nucleo/recursos.py:172, 190` | `smoothscale` al cargar (= E10). | bajo | `scale`. | sí (cambio visual leve) |
| H3 | `interfaz/cooperativo.py:320, 652` | Se reescala un retrato de 438 px en cada cuadro. | bajo | Cachear por (nombre, tamaño). | no |
| H4 | `nucleo/recursos.py:66`; `mundo/mapas.py:395-406, 559-565` | Fondos opacos con `convert_alpha()` y capas `SRCALPHA` de 960×720 en los interiores. | bajo | `convert()` para fondos opacos. Medir. | no |
| H5 | `empaquetar.ps1` | Unos 18 MB de imágenes que nada carga entran al `.exe` (`Video_icono.mp4`, `HojitasAn2-5`, `Vegetación/`, `Pasadonoche`, `Futuro/generado/Terminal/`…). | bajo | Excluirlos al empaquetar, sin borrarlos. | sí (assets de Jimara) |
| H6 | `interfaz/partida_multijugador.py:385`; `audio/musica_mapas.py:13-14` | "victoria" y "game_over" (jingles de 7–8 s) suenan en bucle en la pantalla final. | bajo | Tocarlos una vez y volver a la música. | sí |
| H7 | `Audios/Ambiente.mp3` | La música de La Copa suena 4–5 dB más baja que las otras eras, y su bucle tiene un bache de 0,13 s. | bajo | Ajustar el volumen por defecto. | sí |
| H8 | `nucleo/preferencias.py:14`; `audio/audio_manager.py:28-29`; `empaquetar.ps1:69-76` | Hay tres juegos de volúmenes por defecto distintos. | bajo | Unificarlos. | sí |
| H9 | `audio/audio_manager.py:111-114` | Toda la música se carga como `Sound` (unos 58 MB en RAM). | bajo | Dejarlo (memoria estable). | no |
| H10 | `herramientas/inventariar_recursos.py`; `docs/arte_esperado.md` | Marca las viñetas como pendientes y le faltan 3 sonidos conectados (= L5). | bajo | Actualizar. | no |

## J. Código limpio

| ID | Archivo:línea | Problema | Impacto | Arreglo propuesto | Decisión |
| --- | --- | --- | --- | --- | --- |
| J1 | varios (ruff F/E9/B) | 47 avisos de ruff, casi todos en `tests/` y `editores/` (imports sin uso, `f` sin variables). En el juego: `multijugador/cliente_internet.py:287` (`revision` sin uso), `feria/pantalla.py:7, 13` (imports sin uso, de Fernando). Sin errores reales. | bajo | Quitar los imports y variables sin uso fuera de `feria/`. | no |
| J2 | `tests/test_feria_ecos.py:94` | Caracteres de retroceso literales dentro de una cadena (ruff PLE2510). | bajo | Escribir `\b`. | no |

## K. Pruebas

| ID | Archivo:línea | Problema | Impacto | Arreglo propuesto | Decisión |
| --- | --- | --- | --- | --- | --- |
| K1 | `tests/` | Línea base: 736 pruebas, 0 fallos (517 s). Ninguna cubre el bucle real del menú con errores, la vuelta al menú por inactividad en todas las vistas ni la desconexión con objetos en la mano. | medio | Pruebas nuevas por cada arreglo de A, B, E y F. | no |
| K2 | `tests/test_expediente_avl.py` | Prueba 150 inserciones y las cuatro rotaciones, pero no propiedades con muchas claves aleatorias. | bajo | Prueba de propiedades (altura, balance, inorden). | no |
| K3 | `tests/` | No hay prueba de humo de toda la campaña con bots hasta el final. | medio | Prueba de humo sin pantalla: 4 bots desde La Copa hasta el informe (unos 300 s simulados). | no |
