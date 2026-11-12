# Etapa 6: exploración (protocolo 14)

## Implementado localmente

- Elia y Arel aparecen en La Copa, cerca de fuentes ya existentes. Sus puntos
  se buscan en suelo accesible, sin modificar decoraciones ni paredes del JSON.
  E abre dos preguntas de ayuda y Esc permite volver. Elia ayuda a comparar
  fuentes y hablar cuando hay desacuerdos; Arel explica pistas y suministros.
  No revelan soluciones, votan ni regalan pruebas. Se usan sus sprites reales.
- Cinco interiores del Futuro: Centro de Supervisión, Observatorio de Mensajes,
  Archivo del Consejo, Café de Datos y Estación de Enlaces. Se puede entrar y
  salir individualmente; los demás jugadores solo se ven en la misma era y sala.
- Diez consultas opcionales (cinco por ciudad) sobre fuentes, alcance, firmas,
  testimonios y rutas. Un punto de información señala el lugar; E abre una
  tarjeta y el contador del equipo. Las visitas se conservan al viajar y
  reconectar con la misma sesión. Repetirlas no duplica visitas ni genera puntos.
- El servidor valida era, sala y cercanía al consultar, entrar, salir o conversar.
  Los interiores permanecen bloqueados hasta restaurar las conexiones de NÚCLEO. Sus tareas principales siguen en el exterior; no se trasladan
  dentro de edificios ni se cambian sus soluciones o el comportamiento de bots.
- Las visitas no son requisito de victoria. En un interior del Futuro la guía
  señala primero la consulta pendiente y después la salida. No se dibujan allí
  el avatar exterior de NÚCLEO ni sus pulsos.
- Cachés de interiores y personajes separadas por era. Arte nuevo a resolución
  original y escalado una vez. Si falta una imagen de un interior del Futuro,
  se conserva el fondo de su plantilla del Presente.

## Geometría comprobada y límite pendiente

Los interiores nuevos y sus plantillas existentes miden 344 x 192 y conservan
la planta isométrica. Se reutilizan los JSON ya editados por el equipo. La
auditoría encuentra 20 recorridos transitables (a consulta y salida en diez
salas) y salidas exteriores libres. Esto verifica acceso, no cada mueble del arte.

El **exterior nuevo del Futuro sigue sin activarse**: mide 1048 x 577, frente
a 998 x 576 del activo. Aunque se parecen, cambian elementos, escaleras y
alineación. Encajarlo a la fuerza no verifica las paredes, puertas ni el portal.
La instrucción del proyecto reserva los cambios de paredes a edición manual.
Por eso se conserva el exterior provisional y no se declara cerrada toda la
geometría de la etapa 6. Hace falta revisar esos elementos sobre el PNG nuevo
con el editor de hitboxes y después verificar sus accesos antes de cambiar ruta.

Comprobación reproducible, sin Pygame ni escritura de Hitboxes:

```powershell
.\.venv\Scripts\python.exe herramientas/auditar_exploracion.py --salida docs/auditoria_exploracion_etapa6.json
```

Resultados en `auditoria_exploracion_etapa6.json`. El informe no debe confundirse
con una certificación de la geometría nueva del mapa exterior.

## Publicación

Validación del 11 de noviembre de 2026: 508 pruebas completas aprobadas en
348,768 s, incluidas ocho regresiones nuevas de exploración. Antes de esa
ejecución se aprobaron 54 pruebas de las partes afectadas. La auditoría de
accesos pasó sus 20 recorridos. No se modificó ningún archivo de Hitboxes.

La primera ejecución encontró una diferencia en el rechazo de puertas
bloqueadas. Se restauró la regla anterior y se comprobó de nuevo todo el conjunto.

El protocolo 14 requiere actualizar servidor y todas las PC. No implica que
Render esté actualizado: esta etapa se valida localmente antes de publicarse.
Música pendiente de selección del usuario. No se ha cambiado el contenido legal
ni se ha implementado la batalla o el Modo Feria con QR.
