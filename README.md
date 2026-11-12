# Timeless Glitch

Juego educativo 2D para investigar información y decidir en equipo.
Rama compartida: `multijugador`. Protocolo actual: **18**.

## Instalación en Windows / PowerShell

Usar Python **3.12** de 64 bits, desde la carpeta del proyecto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe juego.py
```

No hace falta activar el entorno ni cambiar la política de PowerShell.
`pygame-ce` proporciona el módulo `pygame`: no instalar también el paquete
`pygame` en este entorno. El Python global no se modifica.
La narración es opcional: instalar `requirements-voz.txt` para usar las voces
del sistema. Tras la instalación, la campaña local con bots no necesita Internet.

## Cómo jugar

- Campaña local con bots: una persona y tres compañeros automáticos.
- Crear/unirse: salas por código desde diferentes PC y redes, usando el servicio
  configurado en `multijugador/configuracion.json`.
- Roles exclusivos: Guardián, Mensajero, Habitante y Aspirante. Los puestos
  libres se completan con bots al iniciar.
- Tres eras: La Copa (4 casos), Distrito Conecta (3) y Ciudad Núcleo (1 caso
  con 4 tareas). Portales con aceptación del equipo.
- Expediente AVL compartido, informe final y fichas legales. Arte y audio locales.
- F1: controles visuales. El mapa muestra la tarea actual y señales de interacción;
  el celular avisa si falta analizar y las votaciones indican quién falta.

Todos deben usar una versión compatible con el servidor. Tras actualizar,
cerrar y abrir el juego. Reiniciar el servidor pierde las salas en memoria.

## Desarrollo y validación

```powershell
$env:SDL_VIDEODRIVER = "dummy"
$env:SDL_AUDIODRIVER = "dummy"
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe herramientas/benchmark.py --segundos 60 --participantes clientes
```

Antes de jugar en esa misma consola, quitar las variables de pruebas sin ventana:
`Remove-Item Env:SDL_VIDEODRIVER, Env:SDL_AUDIODRIVER`.
Las pruebas locales no sustituyen una partida entre PC y redes distintas.

- [Multijugador y despliegue](multijugador/README.md).
- [Estado y etapas](docs/etapas.md).
- [Recursos disponibles y pendientes](docs/arte_esperado.md).
- [Arquitectura](docs/arquitectura.md).

Las paredes se editan a mano en el editor de hitboxes. No sustituir el mapa
del futuro sin comprobar su geometría contra las colisiones existentes.
