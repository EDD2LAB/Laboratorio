# Timeless Glitch

Juego académico 2D en Python + pygame-ce, adaptación del laboratorio "Alcalde
Digital" del equipo "Los Guardianes de la Memoria".
La primera dimensión sigue llamándose La Copa (Era I).

## Cómo ejecutar

Todo desde la raíz del proyecto, con el entorno `.venv` (tiene pygame-ce y aiohttp):

- Instalación: `py -3.12 -m venv .venv` y `.venv\Scripts\python.exe -m pip install -r requirements.txt`.
- Narración opcional: `requirements-voz.txt`. No instalar pygame y pygame-ce juntos.

- Juego: `.venv\Scripts\python.exe juego.py`
- Pruebas: `.venv\Scripts\python.exe -m unittest discover -s tests`
  (sin pantalla: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`; no hay pytest instalado).
  - Red de seguridad de arranque: `-m unittest discover -s tests -p "test_arranque.py"`
- Servidor multijugador local: `.venv\Scripts\python.exe -m multijugador.servicio_internet`
  y en otra consola `$env:COPA_SERVIDOR_INTERNET="http://127.0.0.1:10000"`.
- Benchmark: `.venv\Scripts\python.exe herramientas/benchmark.py --segundos 60`
- Editores: `.venv\Scripts\python.exe -m editores.hitbox_editor` (igual con
  `alineacion_editor` y `personaje_editor`; usar `-m` para que encuentren los paquetes).

## Mapa de módulos

`juego.py` es el único `.py` en la raíz: solo abre el menú. Detalle en
`docs/arquitectura.md`.

| Paquete | Responsabilidad |
| --- | --- |
| `nucleo/` | Constantes (`config`), rutas (`rutas`), carga de recursos y utilidades de texto (`recursos`), preferencias del jugador (`preferencias`, modo de pantalla) |
| `logica/` | Árboles de decisión/clasificación, estado del juego, dimensiones, grafo físico, propagación, habilidades, conversaciones |
| `mundo/` | Personajes, mapas, colisiones, cámara, NPC, jugador, grafo de la aldea, creación del mundo, reparación de puentes |
| `un_jugador/` | Escenas que reutiliza el multijugador (tablilla, dibujo del mapa, ventana). El modo un jugador ya no se ofrece en el menú; `partida.main` queda sin entrada |
| `interfaz/` | Componentes de UI y vista del multijugador (menú inicial, menú de pausa con Esc, presentación 4:3 con bandas negras, panel cooperativo, HUD de indicadores, efectos) |
| `multijugador/` | Servidor autoritativo, protocolo, salas, misiones cooperativas, clientes |
| `bots/` | Bots cooperativos (campaña local y relleno de roles libres en salas en línea) |
| `graficos/`, `audio/` | Partículas/animaciones y gestor de audio |
| `editores/` | Editores de hitboxes, alineación y personajes |
| `herramientas/` | Benchmark |
| `legado/` | Prototipos sin uso (no se importan) |

## Reglas permanentes

- Juego 2D en pygame; nunca 3D ni cambio de motor.
- El Aspirante puede ser Kael (predeterminado) o Mira, y el Habitante Tarek (predeterminado) o Luma, solo en La Copa; el Guardián y el Mensajero no eligen. El que no se elige queda como NPC y el elegido no se duplica. En La Copa se rumora que Kael rompió el puente y que alguien se robó la ayuda: los rumores son falsos o exagerados. Ni Kael ni Mira son culpables ni enemigos en ningún resultado. En el Presente, Ronaldo Vélez (descendiente de Kael) es el Aspirante.
- Pixel art: `pygame.transform.scale`, nunca `smoothscale`; escalar una vez al cargar.
- Multijugador con servidor autoritativo; por red solo viajan ids, estados y eventos, nunca imágenes ni audio.
- Rutas con pathlib relativas a la raíz (`nucleo.rutas.RAIZ`); no inventar rutas, archivos, coordenadas ni resultados de pruebas.
- Ningún módulo carga imágenes, fuentes ni sonidos al importarse: solo después de `pygame.init()`/`set_mode()`.
- Cambios al multijugador deben ser aditivos; no alterar el modo un jugador al portar features.
- Antes de terminar cualquier tarea: correr las pruebas y reportar resultados reales.
- Las hitboxes de pared se editan a mano. No modificarlas al integrar arte o mecánicas.
- Con personas en la partida, los bots no resuelven nada que una persona pueda hacer sola:
  solo ponen la segunda persona que exige el servidor (segundo investigador, la pista que se
  les pide, el aporte de otra persona, sujetar en la actividad, un objeto del encargo por cada
  pedido con B o el eco). No votan, no confirman, no usan
  habilidades ni investigan en Distrito Conecta o Ciudad Núcleo. Solos (sin personas) sí juegan.

## Trabajo en curso

Rama compartida: `multijugador`. Protocolo 14. Tres eras disponibles (4 casos en
La Copa, 3 en Distrito Conecta y 1 en Ciudad Núcleo), campaña local con bots y
bots de relleno en salas. Kael y Tarek son las apariencias predeterminadas.
El expediente AVL, informe final y estados por diferencias están integrados.

Plan vigente: `docs/etapas.md`; inventario de arte: `docs/arte_esperado.md`.
`docs/progreso.md` conserva el historial: sus estados antiguos no describen la
versión actual. Las etapas posteriores no están completas por aparecer en el plan.
