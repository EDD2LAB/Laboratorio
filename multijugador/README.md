# Campaña cooperativa multijugador

## Estado actual: protocolo 18

Salas por código desde distintas PC y redes, mediante el servicio HTTPS de
`configuracion.json`. No exige abrir puertos en los routers de los jugadores.
El servidor público mantiene el estado oficial; quien crea la sala organiza
el equipo desde su cliente. Hay hasta cuatro jugadores, con roles exclusivos;
el servidor no ocupa un cupo. Los puestos vacíos se completan con bots.
La campaña local con bots usa la misma lógica sin depender de Render.

| Era | Contenido |
| --- | --- |
| La Copa | 4 casos: puente, agua, tormenta y ayuda; variantes, pistas privadas, avisos temporales, intercambio, votos, suministros, reparación y habilidades |
| Distrito Conecta | 3 casos: video, voz y perfil/foto; interiores, fuentes, análisis de manipulación, decisión y clasificación desde el celular |
| Ciudad Núcleo | 1 caso con 4 tareas: conexiones, registro, llave y cuentas; barreras, pulsos, habilidades y decisión sobre supervisión humana |

Los portales están disponibles desde el inicio. El equipo viaja cuando los
humanos de la dimensión aceptan; los bots acompañan y se conserva el progreso.
Kael y Tarek son las apariencias por defecto; Mira y Luma son alternativas.
En La Copa, el personaje elegido no se duplica como NPC.

El expediente AVL compartido registra ocho casos, permite inserciones guiadas
y consulta de pruebas y fichas legales. El informe incluye el recorrido inorden
y se exporta a `informes/`. Las normas se revisan con el profesor.

## Red y límites actuales

- HTTP para la sala de espera; WebSocket para movimiento y acciones en partida,
  en el mismo servicio y puerto.
- Estado completo al entrar/reconectar/cambiar de escena; después diferencias
  con revisión base y recuperación por `pedir_snapshot`.
- Servidor autoritativo: valida movimiento, alcance, decisiones y consumos.
  Por red no viajan imágenes, audio ni la semilla privada del sorteo.
- El cliente intenta recuperar el mapa durante 110 s; el servidor conserva el
  personaje y el rol durante 120 s sin comunicación. Si el anfitrión caduca y
  queda otro humano activo, transfiere la sala conservando la partida. Salir
  explícitamente como anfitrión sigue cerrándola. En espera, la sesión caduca a los 45 s.
- Las salas viven en memoria: reiniciar o desplegar pierde las partidas.
- F3 muestra FPS, RTT y KB/s. Ping/pong cada 3 s por LAN y WebSocket, con
  promedio móvil. HTTP limita las consultas por sesión (300/min); crear y
  unirse tienen un límite independiente por IP (60/min). Los límites responden
  429 con Retry-After. Consultar `../docs/red_estabilidad.md`.
- Cinco interiores del Futuro y diez consultas opcionales implementados localmente. Pendientes: geometría exterior nueva del Futuro y demás etapas de `../docs/etapas.md`.

## Ejecutar en desarrollo

Instalar `requirements.txt` de la raíz en `.venv` (ver README principal).

```powershell
.\.venv\Scripts\python.exe -m multijugador.servicio_internet
```

En otra consola de la misma PC:

```powershell
$env:COPA_SERVIDOR_INTERNET = "http://127.0.0.1:10000"
.\.venv\Scripts\python.exe juego.py
```

HTTP sin cifrar se admite únicamente en loopback; para el servicio público se
usa HTTPS. El TCP histórico se conserva para pruebas: no es el transporte de
movimiento que ofrece el menú actual.

## Desplegar en Render

1. Ejecutar las pruebas, revisar y publicar la versión en `multijugador`.
2. Abrir `la-copa-salas`: **Manual Deploy → Deploy latest commit**.
3. Esperar a **Deploy succeeded | Live**.
4. Consultar `https://la-copa-salas.onrender.com/health`: comprobar `ok`,
   `protocolo: 18`, `casos: 8`, tres entradas de `eras` (4, 3 y 1 casos), y
   que `build` corresponda al commit publicado.
5. Actualizar las PC y abrir una sala nueva. No desplegar durante una partida.

`render.yaml` conserva una instancia gratuita, Docker y despliegue manual.
El servicio puede tardar en despertar tras inactividad: comprobar antes de una
presentación. `/health` describe la capacidad de la campaña, no el progreso de
una sala ni la calidad de la conexión de los jugadores.

Cada archivo nuevo usado por el servidor debe estar permitido en
`Dockerfile.multijugador.dockerignore` y en los `COPY` del Dockerfile.
El servidor requiere aiohttp; funciona sin Pygame ni arte.

## Pruebas

```powershell
$env:SDL_VIDEODRIVER = "dummy"
$env:SDL_AUDIODRIVER = "dummy"
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe herramientas/benchmark.py --segundos 60 --participantes clientes
.\.venv\Scripts\python.exe tests/soak_multijugador.py --segundos 600 --salida resultado_estabilidad.json
```

La última orden es opcional para pruebas prolongadas. Las pruebas locales no
sustituyen una partida entre PC y redes distintas. No publicar tokens en registros.
El protocolo 13 añade ping/pong por WebSocket: actualizar servidor y clientes
antes de probar por Internet. Reiniciar Render no permite recuperar salas
perdidas: hay que crear una nueva.

El protocolo 14 añade Elia, Arel y exploración opcional en los interiores de ambas
ciudades. Actualizar servidor y clientes al publicar; ver `../docs/exploracion_etapa6.md`.

Protocolo 18: final cooperativo por roles, reintentos y lectura de fichas del
expediente a demanda. Compatible con campaña con bots y salas en línea; ver
`../docs/final_cooperativo.md`. Requiere publicar y desplegar servidor y clientes
juntos. El contenido puede estar validado localmente sin estar activo en Render.

El protocolo 16 incorporó el combate cooperativo: rayos verdes y rojos anunciados,
pausas para los cuatro minijuegos y recuperación de compañeros. Cliente y
servidor deben actualizarse juntos. Detalles en `../docs/final_cooperativo.md`.

El protocolo 17 añade la preparación de la rebelión, bláster con F, munición
compartida y mini-núcleos. El cierre sincronizado incluye reconfiguración,
epílogos, informe, resultado de las tres eras y créditos. Detalles en
`../docs/desenlace_tres_eras.md`. Aún requiere publicación y despliegue conjuntos.

El protocolo 18 activa el mapa definitivo y las paredes propias del Futuro,
incluidos sus cinco interiores. Se validan rutas de las estaciones y apariciones
de cuatro personas en una misma zona conectada. Ver `../docs/futuro.md`.
