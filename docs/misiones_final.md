# Misiones del final cooperativo (protocolo 20)

Reemplaza las reglas de los minijuegos de `final_cooperativo.md` y
`desenlace_tres_eras.md`. La preparación, los blásteres, los mini-núcleos,
la señal, el reintento y el cierre de las tres eras no cambian.

## Por qué cambió

Antes, cada minijuego se resolvía con uno o dos clics, la respuesta del
Aspirante era siempre la misma y en cada fase la mitad del equipo solo
esquivaba. Ahora **cada rol tiene una parte en la fase verde y otra en la
roja**, las respuestas cambian entre partidas y las pausas son más cortas.

## Ritmo

| Fase | Aviso | Pausa para trabajar |
| --- | --- | --- |
| Verde | 3 s, una descarga | 15 s (antes 26) |
| Roja | 2,5 s, dos descargas | 14 s (antes 22) |

El escudo cae cuando **los cuatro** terminan su parte verde. Al completar las
cuatro tareas se gana directamente: ya no hay que volver a cada consola a
confirmar.

## Qué hace cada rol

| Rol | Fase verde | Fase roja |
| --- | --- | --- |
| Guardián | Revisa 3 órdenes. Cada una es legítima (*Aprobar orden*) o tiene un dato alterado (firma, fecha o permiso). Hay al menos una de cada tipo. | Revisa 2 órdenes más que NÚCLEO intenta colar. |
| Habitante | Tres circuitos **acoplados**: lo que sube uno lo cede el siguiente (el 3 cede al 1). Cuando coinciden con sus metas, mantiene E o Espacio 2 s. | NÚCLEO descalibra la estación con metas nuevas; hay que recalibrarla antes de la entrega del módulo. |
| Mensajero | Enciende las 3 luces de la ruta yendo a cada punto. | Lleva el módulo por las luces y lo entrega (como antes). Si un rayo lo alcanza, suelta el módulo pero conserva las recargas. |
| Aspirante | Reúne pruebas: de 6 tarjetas del caso real, marca las 3 que tienen fuente y las guarda. | Arma la propuesta: una prueba con fuente, el estado de la conexión y el límite de NÚCLEO. Cada campo tiene 3 opciones al azar de un banco, con opciones tentadoras como «NÚCLEO decide solo si es urgente». |

Las tarjetas salen del caso de Ciudad Núcleo (`multijugador/nucleo.py`): el
acta del consejo, la bitácora técnica, las cuentas coordinadas, el sector
Puerto reconectado y la firma del Representante tienen fuente; la orden
firmada por la propia NÚCLEO, el post de @ciudad_segura_01, el mensaje
reenviado sin autor y la captura sin fecha no la tienen.

Equivocarse en una orden, guardar pruebas incorrectas o presentar una
propuesta incorrecta cuesta un punto de señal, como antes.

## Red y bots

- Las respuestas (`falso` de cada orden, qué tarjeta tiene fuente, qué opción
  es correcta) nunca viajan en el estado público ni privado. Los bots las
  consultan en el servidor con `opcion_correcta()` y `PRUEBAS`.
- Nuevas operaciones de `final_accion`: `encender` (Mensajero), `marcar` y
  `guardar` (Aspirante) y `comparar` con `campo="aprobar"` (Guardián).
  Desaparece `activar`.
- Nuevos campos públicos: `verde` (roles con la parte verde lista) y `luces`.
- Con personas en la sala, los bots siguen sin resolver la parte de un rol
  que juega una persona; cubren solo los roles ausentes.

## Bláster sin munición (protocolo 22)

Los disparos son ilimitados: solo hay 0,6 s de espera entre disparos de cada
persona, que la barra inferior muestra como recarga. Desaparecen el contador
compartido, la tecla R, la caja del taller y la carga devuelta al destruir un
mini-núcleo. Así se evitan reglas que no pedían ninguna decisión.

Cada cambio de protocolo exige actualizar juego y servidor juntos. Implementación local
no significa push ni despliegue.
