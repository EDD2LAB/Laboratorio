# Red y estabilidad - etapa 2 (11 de noviembre de 2026)

## Protocolo 13

El cliente envía `{"tipo":"ping","t":<monotonic local>}` cada 3 segundos.
El servidor devuelve `{"tipo":"pong","t":<misma marca>}` por el buzón fiable
de acuses. No se modifica el estado por diferencias ni se envía el pong a la UI
como evento de juego. El RTT usa el reloj del cliente, con promedio móvil
(75 % anterior y 25 % muestra nueva). Se descartan respuestas ajenas o repetidas.

El ping no consume los 60 controles por segundo. Tiene un límite propio de una
respuesta por segundo y exige una marca numérica finita. El heartbeat de aiohttp
sigue detectando cortes; no es la medición de RTT que muestra F3.

F3 muestra FPS, RTT y KB/s recibidos, además del diagnóstico de bots. Sin muestra
reciente se muestra que se está midiendo; la campaña sin red muestra Local.
Un RTT de 0 ms puede ocurrir en loopback por la resolución del reloj.

## Redes compartidas

- Consultas y acciones HTTP autenticadas: 300/min por token de sesión.
- Crear/unirse: 60/min por IP, compartidos entre ambas operaciones.
- `/health` no consume estas cuotas ni crea una sesión.
- Un token inválido no crea un contador independiente en memoria.
- Respuesta al exceso: HTTP 429, `Retry-After` y mensaje legible.
- Los mensajes WebSocket conservan su límite independiente de controles.

Las 30 sesiones de la regresión consultan cada 0,6 s durante un minuto simulado:
no comparten la cuota de consultas, aunque estén en la misma IP. Esto no prueba
la capacidad de una instancia de Render para muchas partidas simultáneas.

## Recuperación

- Sala de espera: la lectura reintenta cortes hasta 30 s. No se reenvían crear,
  unirse o iniciar automáticamente, para no duplicar operaciones ambiguas.
- Partida: el cliente reintenta hasta 110 s desde el corte, con espera de 1, 2 y
  después 4 s. Conexiones sanas separan los episodios de reconexión.
- El servidor conserva identidad, rol y progreso durante 120 s sin comunicación.
  En espera se mantiene la caducidad de 45 s.
- Los cortes no provocan una salida explícita en el cliente. Se mantienen las
  acciones pendientes y se reenvían con su identificador original; el servidor
  ya evita aplicarlas dos veces. Reconectar empieza con un snapshot completo.
- Si caduca el anfitrión en partida, se transfiere la sala al humano con actividad
  más reciente. Se conserva la misma partida, sus indicadores y casos. El puesto
  caducado se retira; no se convierte automáticamente en un bot en esta etapa.
- Si no quedan humanos activos, la sala caduca. Si el anfitrión pulsa salir o
  cierra su cliente explícitamente, sigue cerrando la sala como antes.
- Un reinicio/despliegue del servidor borra las salas en memoria. No hay guardado
  persistente ni recuperación de esas salas.

## Empaquetado

El Dockerfile copia los paquetes de servidor, lógica, bots, JSON y hitboxes
permitidos por el dockerignore; excluye cachés de Python. Las reglas cubren los
JSON de nuevas subcarpetas de hitboxes y los módulos de lógica, sin incluir arte
ni instalar Pygame en el servidor.

```powershell
.\.venv\Scripts\python.exe herramientas/verificar_contexto_docker.py
```

La herramienta interpreta las reglas glob y COPY locales usados en este repo;
rechaza sintaxis adicional que no sabe validar. Copia a una carpeta temporal,
importa la aplicación fuera del repo y crea dos humanos más dos bots, avanzando
200 ticks y comprobando que el estado cabe en MAX_MENSAJE. No usa Pygame.

Esta simulación no sustituye una construcción real con Docker: no verifica la
imagen base, instalación de paquetes en Linux ni el usuario del contenedor.
Docker no está disponible en esta PC. El resultado está registrado en
`validacion_docker_etapa2.json`.

Prueba prolongada y benchmark: consultar los comandos del README multijugador.
No publicar tokens ni códigos de salas reales en los informes.
