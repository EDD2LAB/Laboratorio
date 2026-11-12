# Recuperar el control — final cooperativo (protocolo 16)

## Cómo se inicia

Después de investigar y decidir el caso de NÚCLEO, la pantalla ofrece preparar
el final. Un jugador inicia desde la pantalla central. Se puede volver a abrir
con E junto a la estación indicada o desde «Final cooperativo» en el menú de C.
Los bots esperan a que una persona inicie; un equipo solo de bots puede iniciarlo.

Se conserva la decisión y su consecuencia en el expediente. Si fue incorrecta,
el desafío permite reparar la situación después; no reescribe la decisión como
si hubiera sido correcta. «Dejar pendiente» mantiene abierto el caso anterior.

## Cuatro minijuegos enlazados

| Rol | Acción | Dependencia |
| --- | --- | --- |
| Guardián | Compara firma, fecha y permiso de una orden con el registro del consejo | Apaga una mitad del escudo verde |
| Mensajero | Recoge la carga, camina por dos recargas y la entrega en la estación | Disponible en la fase roja, tras apagar el escudo |
| Habitante | Ajusta tres indicadores a sus zonas verdes y mantiene E/Espacio dos segundos | Apaga la otra mitad del escudo y deja estable la conexión |
| Aspirante | Arma una propuesta con prueba contrastada, conexión comprobada y supervisión humana | El consejo la autoriza cuando las otras tres tareas están listas |

La batalla tiene dos fases. **Verde:** una tanda, con aviso de tres segundos y
una pausa de 26 segundos. Durante la pausa, Guardián y Habitante resuelven sus
pruebas en paralelo. Cada aporte apaga una mitad visible del escudo.
**Roja:** dos tandas, cada una anunciada durante 2,5 segundos, con zonas de impacto
más amplias; después hay una pausa de 22 segundos. En estas pausas el Mensajero
recoge, recarga y entrega el módulo, mientras el Aspirante prepara la propuesta.

Las marcas quedan fijas antes del impacto: no persiguen al jugador. Las tareas,
ajustes y recargas alcanzadas se conservan entre tandas. Las consolas rechazan
acciones durante los ataques y se cierran automáticamente para dejar esquivar.
Dentro de cada consola se muestra el tiempo disponible. Al completar las cuatro
tareas cesan los ataques y comienza la activación conjunta.

Las tarjetas del Guardián y las metas del Habitante se sortean en el servidor.
Los cuatro aportes completos permiten confirmar la activación desde la pantalla
central. Los participantes conectados, incluidos los bots, confirman antes de ganar.

Cada rol usa su propio reto. Se pueden observar las otras tareas, sin recibir
sus tarjetas privadas. Si falta un rol o su persona está desconectada, otro
participante puede cubrir esa tarea. Si ya lleva el módulo, puede terminar su
entrega aunque el Mensajero vuelva a conectarse. No se cambia el rol del personaje.

## Fallos, desconexión y reintento

- Tres unidades de señal. Una comparación o propuesta incorrecta consume una;
  ajustar controles no penaliza y pulsar más rápido no acelera la carga.
- Un impacto anunciado derriba a quien permanezca en la marca y consume una
  unidad de señal del equipo por tanda, aunque alcance a varias personas.
- Los caídos no pueden caminar ni usar consolas. Un compañero cercano los ayuda
  con E. Al empezar la pausa se recuperan también automáticamente, evitando que
  una persona sola o todo el equipo caído quede sin salida.
- Si cae el portador, el módulo vuelve al último punto de recarga guardado.
  Los antiguos pulsos de vigilancia no dañan durante este final.
- Sin señal se vuelve a la pantalla central para reintentar. Se conservan los
  casos, las tareas completadas, los ajustes y los puntos de recarga alcanzados.
- La estación queda estabilizada al completar sus dos segundos de carga.
  El Habitante puede ayudar después; no tiene que mantener E durante toda la entrega.
- La carga solo avanza con tiempo del servidor, indicadores alineados y el
  operador cerca y conectado. Si el portador se desconecta, la carga se libera.
- Cada intento tiene su número: acciones retrasadas del anterior se rechazan.
  Las solicitudes repetidas conservan la deduplicación de la campaña.

## Integración

La campaña local con bots y las salas por red comparten `PartidaMovimiento`,
`CampanaCopa` y `FinalCooperativo`. La IA realiza las mismas acciones, recorre
las calles con el navegador existente y no teletransporta a sus personajes.
El servidor valida rol, era, interior, distancia, orden del recorrido, condiciones
de cada reto y confirmación final. El arte se carga y escala solo en el cliente.

La guía cambia al objetivo del final y NÚCLEO se serena al vencer. La victoria
ofrece el informe de los ocho casos; su exportación registra la recuperación
cooperativa sin modificar las referencias legales de los casos anteriores.

No se editaron Hitboxes, mapas ni música. Las estaciones y recargas reutilizan
puntos transitables de la misión actual. El mapa exterior nuevo se integrará
cuando esté listo el trabajo de la compañera.

## Tamaño del estado y expediente

Los snapshots envían el árbol completo y resúmenes de sus fichas. Al abrir un
caso, `expediente_leer` entrega su ficha completa al solicitante; el cliente la
guarda en caché e invalida esa versión si cambia el evento del resultado. Las
pruebas y referencias permanecen en el servidor, sin truncarse. Una lectura
no permite consultar casos no investigados. El informe completo sigue disponible.

Así se mantiene el límite de 32.768 bytes del protocolo también con las tres
eras completadas. Se eliminó además la duplicación de los campos legales que
aparecían dentro del resultado y en la propia ficha.

Al terminar el caso del Futuro, sus antiguas listas de cuentas, conexiones y
registros dejan de repetirse en cada snapshot; sus evidencias siguen en la ficha
del expediente. La prueba con ocho casos, cuatro roles, nombres de 20 caracteres,
identificadores de 16 caracteres, ruta final, marcas y caídos mide como máximo
30.028 bytes, por debajo del límite del protocolo.

## Arte

Panel común y módulo generados con la herramienta integrada de imágenes,
guardados en `Imagenes/FinalCooperativo/`. Textos, botones, indicadores y progreso
son elementos de Pygame. Arte y prompts: `arte_final_cooperativo.md`.
Sin los PNG se conservan los controles y un panel dibujado por código.

## Publicación

Suite completa aprobada: 543 pruebas en 500,834 segundos. Tras los ajustes
finales, 36 pruebas específicas aprobadas y una comprobación adicional del
control del cliente caído. Detalle de recuentos en docs/progreso.md. También se
revisaron visualmente las pantallas de ataque verde, rojo y consola en pausa.

El protocolo 16 requiere actualizar juego y servidor juntos. Implementación
local no significa que ya esté publicada en GitHub ni activa en Render.
