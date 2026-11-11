# Etapa 4: movimiento y atascos

## Problemas reproducidos

Antes del cambio, seis regresiones mostraron problemas en servidor, bots y
motor local: costuras entre superficies caminables contiguas, espacio bloqueado
en exceso junto a líneas, roces con objetos pequeños y personajes inmóviles
dentro de un bloqueo temporal de puente.

Las paredes, puntos, imágenes y JSON de Hitboxes conservan su contenido.
Las correcciones pertenecen a la interpretación geométrica y al movimiento.

## Geometría

- Los pies pueden estar cubiertos por la unión de varias zonas caminables;
  ya no es necesario que quepan completos en una sola. Los huecos entre zonas
  siguen bloqueando. Rectángulos y círculos se comprueban conservadoramente.
- Las líneas comparan su grosor real contra el rectángulo de pies. Se elimina
  la aproximación que envolvía los pies en un círculo y bloqueaba espacio extra.
- Se conserva la geometría de círculos, NPC y límites del mapa. Los resultados
  estáticos del servidor siguen almacenados en su caché por posición de píxel.

## Desplazamiento

`logica/movimiento_suave.py` se comparte entre servidor y motor local.
El movimiento usa subpasos de hasta un píxel y deslizamiento por ejes. Rechaza
el corte diagonal entre dos esquinas bloqueadas.

Si un roce pequeño detiene ambos ejes, busca una salida lateral de hasta tres
píxeles y comprueba que permita continuar hacia delante. El desplazamiento
lateral consume el presupuesto de distancia del mismo movimiento. Una pared
larga sigue deteniendo a quien intenta caminar directamente hacia ella.

La velocidad, normalización diagonal, Shift y límite de tiempo por actualización
conservan sus valores. Los límites y todas las superficies fijas se comprueban
en cada paso; no se resuelven atascos trasladando al jugador a otra posición.

## Puente

Si un actor ya está dentro del rectángulo de un bloqueo temporal, puede caminar
para salir sin aumentar su penetración. Quien está fuera sigue sin poder entrar.
La salida también comprueba paredes, NPC, zonas caminables y límites fijos.
Cuando el puente se repara, se retira el bloqueo como antes.

Se conserva el rectángulo de bloqueo original: no se reemplaza por una barrera
más pequeña ni se editan paredes para abrir un atajo.

## Bots

- El punto de inicio de A* se conecta a posiciones de cuadrícula realmente
  alcanzables desde los pies del bot; redondear hacia una pared ya no lo encierra.
- Los puntos de giro se recorren hasta alcanzarlos, sin descartarlos a ocho
  píxeles de distancia y cortar prematuramente una esquina.
- El tiempo restante se usa al pasar al siguiente nodo: la corrección no reduce
  la velocidad de los bots por tener más puntos intermedios.
- Los destinos con radio menor que el paso de cuadrícula pueden enlazarse por
  un tramo final libre aunque sus coordenadas no sean múltiplos de ocho.
- Dentro de un bloqueo temporal, el bot busca una salida cercana alcanzable a
  pie y luego recalcula su camino original. Sigue usando el mismo movimiento
  validado del servidor.

## Validación

Regresiones de costuras y huecos, líneas y segmentos degenerados, roces, esquinas,
deslizamiento diagonal, velocidad, bloqueo/reparación del puente, escape sin
atravesar paredes y navegación de bots. Se comprueban también el motor local,
la campaña cooperativa, el transporte real y el empaquetado simulado.

Protocolo conservado en 13: cambian las reglas de movimiento en el servidor,
no el formato de controles ni de estados. Publicar servidor y clientes juntos
para que sus guías y geometría local utilicen las mismas correcciones.

Los resultados de esta etapa están en `docs/progreso.md`.
