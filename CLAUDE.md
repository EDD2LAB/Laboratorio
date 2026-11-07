# La Copa: Voces en las Alturas

Juego académico 2D en Python + pygame-ce (adaptación del laboratorio "Alcalde
Digital", equipo "Los Guardianes de la Memoria").

## Cómo ejecutar

Todo desde la raíz del proyecto, con el entorno `.venv` (tiene pygame-ce y aiohttp):

- Juego: `.venv\Scripts\python.exe juego.py`
- Pruebas: `.venv\Scripts\python.exe -m unittest discover -s tests`
  (sin pantalla: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`; no hay pytest instalado).
  La prueba `test_bots_cooperativos` ya fallaba antes del refactor.
- Red de seguridad de arranque: `-m unittest discover -s tests -p "test_arranque.py"`
- Servidor multijugador local: `.venv\Scripts\python.exe -m multijugador.servicio_internet`
  y en otra consola `$env:COPA_SERVIDOR_INTERNET="http://127.0.0.1:10000"`.
- Benchmark: `.venv\Scripts\python.exe herramientas/benchmark.py --segundos 60`
- Editores: `.venv\Scripts\python.exe -m editores.hitbox_editor` (igual con
  `alineacion_editor` y `personaje_editor`; usar `-m` para que encuentren los paquetes).

## Mapa de módulos

`juego.py` es el único `.py` en la raíz: solo abre el menú y arranca el modo
elegido. Detalle en `docs/arquitectura.md`.

| Paquete | Responsabilidad |
| --- | --- |
| `nucleo/` | Constantes (`config`), rutas (`rutas`), carga de recursos y utilidades de texto (`recursos`) |
| `logica/` | Árboles de decisión/clasificación, estado del juego, dimensiones, grafo físico, propagación, habilidades, conversaciones |
| `mundo/` | Personajes, mapas, colisiones, cámara, NPC, jugador, grafo de la aldea, creación del mundo, reparación de puentes |
| `un_jugador/` | Escenas y bucle del modo un jugador (HUD, mapa, códice, tablilla, escenas, ventana, `partida.main`) |
| `interfaz/` | Componentes de UI y vista del multijugador (menú inicial, panel cooperativo, HUD de indicadores, efectos) |
| `multijugador/` | Servidor autoritativo, protocolo, salas, misiones cooperativas, clientes |
| `bots/` | Bots cooperativos |
| `graficos/`, `audio/` | Partículas/animaciones y gestor de audio |
| `editores/` | Editores de hitboxes, alineación y personajes |
| `herramientas/` | Benchmark |
| `legado/` | Prototipos sin uso (no se importan) |

## Reglas permanentes

- Juego 2D en pygame; nunca 3D ni cambio de motor.
- Mira es la Aspirante controlable; Kael es NPC, nunca enemigo ni culpable por defecto.
- Pixel art: `pygame.transform.scale`, nunca `smoothscale`; escalar una vez al cargar.
- Multijugador con servidor autoritativo; por red solo viajan ids, estados y eventos, nunca imágenes ni audio.
- Rutas con pathlib relativas a la raíz (`nucleo.rutas.RAIZ`); no inventar rutas, archivos, coordenadas ni resultados de pruebas.
- Ningún módulo carga imágenes, fuentes ni sonidos al importarse: solo después de `pygame.init()`/`set_mode()`.
- Cambios al multijugador deben ser aditivos; no alterar el modo un jugador al portar features.
- Antes de terminar cualquier tarea: correr las pruebas y reportar resultados reales.

## Trabajo en curso

La tarea `multi-principal` (multijugador como modo principal, bots por red,
optimización) está pausada tras su Fase 0; ver `docs/progreso.md`.
