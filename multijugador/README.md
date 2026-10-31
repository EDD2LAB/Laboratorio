# Sala de espera multijugador

Ejecutar `python juego.py` y elegir **Multijugador**. El botón de conexión
alterna entre **Internet** y **Red local**.

## Internet: computadores en redes diferentes

El servicio central debe estar publicado antes de usar este modo. En esta
copia `configuracion.json` deja la dirección vacía porque todavía no existe
un despliegue público. No se inventa una dirección ni se usa la IP doméstica.

1. Introducir la misma dirección HTTPS del servicio en las PC.
2. Un jugador crea la sala y recibe un código de seis caracteres.
3. Los demás eligen Unirse y escriben ese código.
4. Elegir roles, marcarse como listos y confirmar desde el anfitrión.

Todos hacen conexiones salientes HTTPS; no es necesario abrir puertos del
router, compartir IP pública ni instalar una VPN. El creador administra la
sala, pero el servidor se ejecuta en el alojamiento, no en su PC.

La URL puede introducirse en la interfaz o configurarse para todas las copias
en `multijugador/configuracion.json`, campo `servidor_internet`. También se
admite la variable de entorno `COPA_SERVIDOR_INTERNET`.

### Publicar el servicio en Render

Preparación incluida: `Dockerfile.multijugador`, `render.yaml` y comprobación
de salud `/health`. No requiere instalar Pygame en el servidor.

1. Crear una cuenta en Render y conectar el repositorio de GitHub.
2. Subir primero esta implementación a la rama `multijugador`.
3. Crear un Blueprint con `render.yaml` desde esa rama. El archivo solicita
   una única instancia del plan `free` y desactiva despliegues automáticos.
   Si se configura como Web Service manual, usar Docker y la ruta
   `Dockerfile.multijugador`; mantener `/health` como Health Check Path.
4. Esperar a que el despliegue esté activo y comprobar `https://TU-SERVICIO/health`.
   Debe responder `{"ok": true}`. Esa dirección es un ejemplo, no una URL real.
5. Copiar la URL HTTPS base (sin `/health`) en el juego o en la configuración.
6. Probar una PC por Wi-Fi y otra usando una red distinta, por ejemplo un
   punto de acceso móvil. Ambas deben ver los mismos roles y jugadores.

Documentación de referencia:
- https://render.com/docs/blueprint-spec
- https://render.com/docs/docker
- https://render.com/docs/health-checks

El plan de pruebas puede tardar en arrancar tras inactividad. Se puede cancelar
la conexión desde el juego; la primera solicitud espera hasta 60 segundos.
Las salas viven en memoria: reiniciar o desplegar el servidor las cierra.
Mantener **una sola instancia y proceso** hasta incorporar almacenamiento
compartido. No hay reconexión de sesión en esta fase; una ausencia de más de
45 segundos libera al jugador y, si era el creador, cierra su sala.

### Prueba técnica local del servicio Internet

Ejecutar `python -m multijugador.servicio_internet` y usar
`http://127.0.0.1:10000` en clientes del mismo equipo. Solo se admite HTTP
sin cifrar para loopback. Para uso externo, el alojamiento debe proporcionar
HTTPS. La consulta periódica de estado es para la sala de espera; el movimiento
en tiempo real será una entrega posterior.

## Crear y unirse desde PC diferentes

1. Todos deben tener esta misma versión y estar en la misma red local.
   Seleccionar el modo **Red local** en Multijugador.
2. El anfitrión elige **Crear partida**, introduce nombre y puerto y crea la sala.
3. La sala muestra las direcciones IPv4 locales del anfitrión. Si aparecen varias,
   usar la del adaptador Wi-Fi/Ethernet de la red compartida (`ipconfig`).
4. Los demás eligen **Unirse a partida**, escriben su nombre, la IP del anfitrión
   y el mismo puerto (por defecto **45871 TCP**).
5. Si Windows lo solicita, permitir Python en la **red privada**. Una red Wi-Fi
   de invitados o institucional puede impedir que dos equipos se comuniquen.
6. Elegir roles diferentes, marcarse como listos y confirmar el equipo desde
   el anfitrión. Cambiar de rol cancela el estado Listo.

El anfitrión juega como uno de los cuatro participantes; el servidor no consume
otro cupo. Se requieren dos participantes listos para confirmar. Los roles sin
jugador quedan libres; todavía no hay asistentes automáticos.

## Alcance de esta entrega

Menú inicial, formularios, sala TCP, selección exclusiva de cuatro roles,
preparación y confirmación sincronizadas, liberación de cupos al salir, errores
de conexión y cierre al salir el anfitrión. La confirmación muestra el mismo
equipo en todas las PC; **todavía no inicia movimiento multijugador en La Copa**.
El botón **Un jugador** abre el modo individual existente.

El servidor valida todas las acciones de la sala. La red se procesa en hilos
separados de Pygame. No se implementan reconexión, chat libre ni migración de
anfitrión en esta fase. En red local se utiliza IP; en Internet, código de sala.

## Comprobar la implementación

`python -m unittest discover -s tests -p "test_sala*.py" -v`

Las pruebas usan clientes TCP y HTTP reales en el mismo equipo. Debe completarse
una prueba manual adicional entre dos PC y una prueba entre redes diferentes
cuando exista el despliegue HTTPS público.
