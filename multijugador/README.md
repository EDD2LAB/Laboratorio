# Multijugador: campaña cooperativa de La Copa

## Campaña actual (protocolo 4)

Una sala recorre cuatro investigaciones sin desconectarse: puente norte, agua,
tormenta y reparto de ayuda. El agua y la tormenta tienen dos versiones posibles,
seleccionadas por el servidor al crear la partida. La decisión correcta depende
de las pruebas de esa versión; los clientes nunca reciben la solución oficial.
Las opciones son publicar una aclaración, difundir el aviso o retirarlo.

Cada minuto de investigación con al menos dos conectados suma tres puntos de
desinformación. La cuenta se pausa si falta equipo y durante la preparación.
No hay una derrota automática por tiempo. Informar a todos los integrantes con
dos pruebas concede un bono de confianza una vez por caso y 20 puntos extra.
Resolver bien concede 100 puntos, o 80 tras una rectificación; las puntuaciones
se acumulan y el balance final conserva los cuatro resultados.

Entre casos, al menos dos jugadores recogen suministros en sus respectivas
fuentes y los depositan en el caldero. E permite recoger/depositar, y M abre el
panel de preparación. Todos los conectados confirman allí el siguiente caso.
Los suministros son una tarea de transporte; no modifican las colisiones de los
puentes ni incorporan el minijuego de reparación del modo individual.

Q activa una habilidad, una vez por investigación:

| Rol | Acción y requisito |
| --- | --- |
| Guardián | Auditar su prueba en la fuente: -4 desinformación. |
| Mensajero | Entregar su prueba a todos los conectados, desde cualquier lugar. |
| Habitante | Asamblea en su fuente junto a otro jugador: +4 confianza. |
| Aspirante | Rendir cuentas en el caldero con dos pruebas: +4 armonía. |

Todas requieren haber recogido primero la prueba propia. El servidor valida
posiciones y consumos. Las acciones llevan el número de caso y se rechazan si
pertenecen a otra ronda; el historial de acuses se conserva entre casos.

Para publicar esta versión hay que actualizar clientes y servidor a protocolo 4,
desplegar el commit en Render y crear una sala nueva. `/health` debe indicar
`protocolo: 4`, `campana: "la_copa"` y `casos: 4`.

El contenido de Distrito Conecta continúa exclusivamente en el modo individual.
La campaña no guarda partidas después de cerrar el juego o reiniciar el servidor.

## Actualizar cada PC

```powershell
git switch multijugador
git pull origin multijugador
python -m pip install -r multijugador/requirements.txt
python juego.py
```

Pygame debe estar instalado para el juego; el paquete nuevo es aiohttp, usado
por el cliente y el servidor para WebSocket. El servidor no necesita Pygame.

## Jugar desde redes diferentes

El servidor configurado es `https://la-copa-salas.onrender.com`.

1. Elegir Multijugador → Crear partida e introducir el nombre.
2. Compartir el código de seis caracteres con los demás.
3. Los invitados eligen Unirse e introducen nombre y código.
4. Cada jugador elige un rol y se marca como listo.
5. El anfitrión pulsa **Iniciar partida**: todos entran automáticamente a La Copa.
6. Leer la introducción del caso y pulsar Investigar.
7. Moverse con WASD o flechas. E interactúa, Tab cambia entre objetivos cercanos,
   I abre las pruebas y M vuelve a las instrucciones. Esc cierra primero el panel
   abierto; fuera de paneles, Esc o Salir abandona la partida.

## Caso: ¿Cerraron el puente norte?

Circula que Kael cerró hoy todo el puente por decisión propia. Cada rol recibe
una fuente distinta, cuya ubicación está marcada en el mapa:

| Rol | Fuente | Prueba |
| --- | --- | --- |
| Guardián | Naira, al noreste | Acta del consejo |
| Mensajero | Eco de la plataforma central | Registro de ruta |
| Habitante | Luma, al sureste | Testimonio |
| Aspirante | Mira, al suroeste | Propuesta original |

1. Acercarse a la fuente y pulsar E. La pista se incorpora solo al registro del
   jugador que la obtuvo; otros jugadores no reciben su contenido por red.
2. Abrir I, elegir la prueba y destinatario. Entregar cerca de otro jugador o
   acercarse a un Eco para enviarla a distancia. Son copias: el emisor conserva
   su prueba. La recepción queda confirmada en ambos clientes.
3. En los Ecos también se pueden enviar mensajes breves predeterminados.
4. Comparar las pruebas y reunirse cerca del caldero. Se requieren fuentes de
   dos jugadores distintos y una entrega confirmada. Cada votante necesita dos
   pruebas en su registro. El caso funciona con cualquier pareja de roles.
5. Todos los conectados votan; una mayoría decide. En empate se puede cambiar
   el voto. Una ausencia temporal no bloquea al resto si siguen dos conectados.
6. El equipo recibe el mismo resultado, cambios de confianza, armonía y
   desinformación, y estado informativo del puente. No se cierra físicamente
   el puente por una noticia falsa.
7. Si la decisión es incorrecta, pueden abrir una única rectificación desde el
   caldero. Rectificar no elimina automáticamente todos los efectos del error.

El servidor valida distancias, roles, posesión de pruebas, destinatarios y votos.
Las acciones se confirman y se reenvían si se pierde el acuse; el mismo
identificador no aplica dos veces la acción. La votación no puede finalizar
con un único jugador. Para otra partida se crea una sala nueva.

No hace falta compartir IP doméstica, instalar VPN ni abrir puertos del router.
Las solicitudes de sala utilizan HTTPS y el mapa utiliza WebSocket seguro en
el mismo servicio. La URL se guarda en `configuracion.json`; puede reemplazarse
para pruebas con la variable `COPA_SERVIDOR_INTERNET`.

## Qué está implementado

- Sala de 2–4 jugadores con roles exclusivos y validación en el servidor.
- Transición del equipo al mapa y puntos de aparición separados y libres.
- Posiciones calculadas en el servidor con las hitboxes del mapa de mañana.
- Paredes rectangulares, circulares y líneas; obstáculos de NPC no jugables.
- Velocidad limitada, diagonales normalizadas y controles con secuencia.
- Simulación y estados a 20 Hz; dibujo interpolado a 60 FPS.
- Personajes de los cuatro roles, reposo y movimiento en cuatro direcciones.
- Recorte de hojas mediante sus separaciones transparentes y alineación inferior.
- Nombres, color por rol y marcador del jugador local.
- Los jugadores se atraviesan entre sí para no bloquear los puentes.
- Un control sin renovación deja de mover al personaje después de 350 ms.
- Al salir un invitado desaparece del mapa; los demás continúan.
- Al salir el anfitrión se cierra la sala para todos.

El modo individual se conserva. La campaña incluye habilidades de rol y cuatro
casos, con variantes. El catálogo individual de tablillas, las conversaciones
libres, los objetos consumibles y las otras dimensiones no se comparten por red.
Los cortes breves de WebSocket tienen hasta tres reintentos automáticos y
conservan temporalmente el rol, posición y sesión. Cerrar el juego o salir
explícitamente no recupera la sesión al abrirlo de nuevo. No hay predicción
local; con latencia alta la respuesta al teclado puede tardar en llegar.

## Actualizar el servidor de Render

Esta entrega usa **protocolo 4**. No es compatible con el servidor anterior:
actualizar tanto Render como las PC antes de probar una sala.

1. Publicar el commit de esta entrega en la rama `multijugador`.
2. En Render abrir el servicio `la-copa-salas`.
3. Seleccionar **Manual Deploy → Deploy latest commit** y esperar a Live.
4. Abrir `https://la-copa-salas.onrender.com/health`.
5. La respuesta debe incluir `"protocolo": 4`, `"movimiento": true` y
   `"mision": "puente_norte"`. El campo `build` identifica el commit desplegado.

Docker instala aiohttp y copia solo el código del servidor y los JSON de
hitboxes. HTTP y WebSocket escuchan en el mismo `PORT`. El servicio mantiene
una sola instancia/proceso; las salas son temporales y se pierden al reiniciar
o desplegar. No actualizar mientras otros están probando una partida.

Los despliegues automáticos siguen desactivados en `render.yaml`. Si el servicio
está detenido por inactividad, la primera conexión puede tardar; el juego deja
cancelarla. Una sesión sin comunicación durante 45 segundos se retira de la sala.

Referencias oficiales:
- https://render.com/docs/websocket
- https://render.com/docs/deploys
- https://docs.aiohttp.org/en/stable/web_reference.html

## Pruebas de desarrollo

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Incluyen cuatro clientes WebSocket reales, autenticación, inicio, movimiento,
colisiones, límites de velocidad, desconexión, aislamiento de salas y compatibilidad.
Las pruebas locales no sustituyen una prueba manual entre dos PC con redes distintas.

La campaña se comprueba con las seis parejas de roles, un equipo de cuatro y
dos clientes WebSocket reales completando los cuatro casos. Las regresiones
incluyen variantes, habilidades, presión, preparación con una ausencia temporal,
rectificación sin duplicar puntos y rechazo de acciones de rondas anteriores.

Validación de la entrega anterior (31 de octubre de 2026): 32 pruebas aprobadas,
caso completo comprobado desde la interfaz con dos clientes y prueba prolongada
de 600 segundos con cuatro clientes, 42.517 estados y tres cortes recuperados.
El servidor y los clientes de estas verificaciones se ejecutaron localmente.

Prueba prolongada opcional de diez minutos, con cuatro clientes, controles,
acciones confirmadas y tres interrupciones de WebSocket:

```powershell
python tests/soak_multijugador.py --segundos 600 --salida resultado_estabilidad.json
```

Los registros `[Red]` incluyen tipo de fallo y códigos HTTP/WS sin mostrar tokens.
Los reintentos se renuevan después de una conexión sana; no se agotan por cortes
aislados a lo largo de toda la partida. Las conexiones respetan los proxies
configurados en el entorno. Reiniciar Render pierde las salas en memoria:
la reconexión no recupera una sala cuyo servidor ya fue reiniciado.

Para iniciar el servicio local:

```powershell
python -m multijugador.servicio_internet
```

En una consola de cliente del mismo equipo:

```powershell
$env:COPA_SERVIDOR_INTERNET = "http://127.0.0.1:10000"
python juego.py
```

HTTP sin cifrar se admite únicamente en loopback. El transporte TCP de la
primera sala se conserva para pruebas, pero no aparece en el menú ni implementa
el nuevo movimiento compartido.
