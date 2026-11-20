# Prompt para Claude Code: rama `feria-exe`

> Lánzalo en la PC con Windows donde se va a mostrar el juego (o en la PC del equipo y luego copias `dist\`). Puede ir antes o después de `coherencia-eras`; si va después, el .exe ya sale con los textos corregidos.

---

Trabaja en el repositorio EDD2LAB/laboratorio, en Windows. Crea la rama `feria-exe` desde `multijugador`.

**Antes de cambiar nada:**
1. Corre la suite completa: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv\Scripts\python.exe -m unittest discover -s tests`. Anota el número real de pruebas y fallos.
2. Corre `.venv\Scripts\python.exe herramientas/benchmark.py --segundos 60` y guarda el resultado.

**Regla permanente:** no toques ninguna hitbox de pared.

## Parte 1: el ejecutable (`herramientas/empaquetar.ps1`)
Crea un script de PowerShell que, ejecutado desde la raíz del proyecto, haga esto:
1. Instale `pyinstaller` y `pillow` en el `.venv` si faltan. Agrega `requirements-empaquetar.txt` con las versiones fijas; no los agregues a `requirements.txt`.
2. Corra PyInstaller sobre `juego.py` con nombre `TimelessGlitch`, `--onedir --windowed --noconfirm` y el ícono convertido de `Imagenes/Iconos/Icono_juego.png`. Debe incluir como datos:
   - las carpetas `Imagenes`, `Audios`, `Fuentes`, `Hitboxes` y `datos`;
   - `multijugador/configuracion.json`;
   - cualquier otro archivo no `.py` que el código lea. Búscalos con grep de `RAIZ /`, `Path(__file__)` y `read_text`; no supongas la lista.
   - Si `audio/narracion.py` (pyttsx3) no está instalado, el juego debe seguir funcionando sin narración.
3. Deje en `dist\TimelessGlitch\_internal\preferencias_usuario.json` las preferencias de feria: pantalla completa y volúmenes 0.8 / 0.5 / 0.4 / 0.7. Usa las claves reales de `nucleo/preferencias.py`.
4. Copie a `dist\TimelessGlitch\` los archivos `Feria.bat` y `LEEME_FERIA.txt` (Parte 2).
5. Comprima `dist\TimelessGlitch` en `dist\TimelessGlitch.zip`.

Comprueba en `nucleo/rutas.py` que `RAIZ` apunta a `_internal` dentro del .exe y que las preferencias se pueden escribir ahí. Si algo se lee relativo al directorio actual en lugar de `RAIZ`, corrígelo.

**Verificación obligatoria (sin inventar resultados):**
- Arranca `dist\TimelessGlitch\TimelessGlitch.exe` desde una carpeta distinta del repositorio, por ejemplo copiada a `%TEMP%\prueba_tg\`, con `.venv` fuera del PATH. Debe abrir el menú.
- Prueba una "Campaña con bots" hasta el primer caso de La Copa, entra por el portal a Distrito Conecta y a Ciudad Núcleo, y vuelve al menú.
- Si no puedes jugarla de forma interactiva, haz un build de diagnóstico sin `--windowed` y arranca con `SDL_VIDEODRIVER=dummy` hasta crear la campaña local. Reporta exactamente qué probaste.
- Reporta el tamaño final de la carpeta y del .zip.

## Parte 2: archivos de feria
- **`herramientas/feria/Feria.bat`:** abre `TimelessGlitch.exe` desde su misma carpeta (`%~dp0`) y lo vuelve a abrir 2 segundos después si se cierra. La ventana se llama "Timeless Glitch - Feria" y, si se cierra esa ventana, deja de relanzar el juego.
- **`herramientas/feria/preparar_pc_feria.ps1`:** un script que **yo ejecutaré a mano** como administrador. No lo ejecutes tú. Debe:
  - Desactivar el atajo de Teclas especiales, Teclas filtro y Teclas de alternancia, para que Shift×5 no salte encima del juego.
  - Poner suspensión y apagado de pantalla en "Nunca" con corriente (`powercfg`).
  - Crear un acceso directo de `Feria.bat` (minimizado, con el ícono del juego) en el escritorio y en la carpeta de inicio del usuario.
  - Permitir `TimelessGlitch.exe` en el firewall para redes privadas (para la LAN).
  - Tener una opción `-Deshacer` que restaure todo lo anterior.
  - Imprimir lo que cambió.
- **`herramientas/feria/LEEME_FERIA.txt`:** guía corta para el día de la feria:
  - copiar la carpeta a `C:\TimelessGlitch\`;
  - ejecutar `preparar_pc_feria.ps1` y luego `-Deshacer` al terminar;
  - usar "Campaña con bots" sin internet, o LAN con un router propio;
  - lo que se hace a mano: pausar Windows Update, activar No molestar, cerrar Discord, Steam y OneDrive, poner el fondo del logo y ocultar los íconos;
  - cómo salir de verdad: cerrar primero la ventana "Timeless Glitch - Feria" y luego el juego;
  - la lista de controles para imprimir junto al teclado.

## Parte 3: modo feria dentro del juego
Agrégalo **sin cambiar el modo normal**. Se activa con la variable `TG_MODO_FERIA=1`, que `Feria.bat` define, o con la clave `"modo_feria": true` en las preferencias.
- En el menú de inicio, en modo feria, aparece un botón destacado **"Demo rápida"**. Crea una campaña con bots (dificultad normal) igual a "Campaña con bots". Los demás botones siguen ahí.
- **Inactividad:** dentro de una partida, si pasan 120 s sin teclas ni clics de la persona, aparece un aviso de 10 s: "¿Sigues ahí? Pulsa cualquier tecla". Si nadie responde, vuelve al menú de inicio y cierra la campaña local limpiamente (servidor local, bots, hilos y audio).
- En modo feria, el botón "Salir" del menú de inicio pide confirmación. Así un visitante no cierra el juego por accidente, aunque `Feria.bat` lo reabriría igual.
- **Atajo a la batalla final:** solo si existe una forma limpia de usar lo que ya hay. `herramientas/vista_combate.py` abre el combate sin servidor ni campaña; puedes mostrarlo desde el menú en modo feria como **"Ver la batalla final"**, con Esc para volver al menú. Si eso exige tocar la lógica del servidor o del protocolo, no lo hagas y dímelo.
- No cambies el protocolo de red. Si fuera inevitable, súbelo de número y avísame.
- Agrega pruebas:
  - Sin la variable, el menú es idéntico al actual.
  - Con la variable, aparece "Demo rápida".
  - El temporizador de inactividad vuelve al menú. Simula el tiempo; no esperes 120 s reales.
  - Al volver por inactividad no quedan hilos ni servidores locales vivos.

## DOCKER
Este trabajo no debería tocar el servidor. Confirma que `Dockerfile.multijugador.dockerignore` no necesita archivos nuevos. Simula el contexto de Docker con esa lista blanca y arranca una sala con `python -m multijugador.servicio_internet`: debe responder `/health`.

## Al terminar
- Corre otra vez la suite completa y el benchmark. Reporta el antes y el después con números reales.
- Confirma que `build/`, `dist/` y `*.spec` están en `.gitignore` y que no se subió ningún binario.
- Reporta la lista de archivos nuevos o cambiados y la ruta exacta del `.zip` listo para la feria.

Une en multijugador, corre las pruebas y avísame. No hagas push.
