# Multijugador: sala y exploración compartida

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
6. Moverse con WASD o flechas. Esc o Salir abandona la partida.

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

El modo individual se conserva. Todavía no están sincronizadas las tablillas,
diálogos, inventarios, entregas, habilidades, portales ni las otras dimensiones.
La simulación actual permite explorar juntos, no resolver una partida cooperativa.
No hay predicción local ni reconexión de sesión; con latencia alta la respuesta
al teclado puede tardar en llegar, aunque se interpole el dibujo.

## Actualizar el servidor de Render

Esta entrega usa **protocolo 2**. No es compatible con el servidor anterior:
actualizar tanto Render como las PC antes de probar una sala.

1. Publicar el commit de esta entrega en la rama `multijugador`.
2. En Render abrir el servicio `la-copa-salas`.
3. Seleccionar **Manual Deploy → Deploy latest commit** y esperar a Live.
4. Abrir `https://la-copa-salas.onrender.com/health`.
5. La respuesta debe incluir `"protocolo": 2` y `"movimiento": true`.

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
