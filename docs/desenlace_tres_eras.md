# Final cooperativo completo en protocolo 17

Implementación local que amplía la batalla y los cuatro minijuegos del protocolo
16. No modifica el mapa exterior ni sus paredes. Campaña con bots y salas en
línea usan las mismas reglas del servidor.

## Secuencia

1. Investigar el caso de NÚCLEO. Si falta La Copa o Distrito Conecta, la guía
   dirige al portal y el servidor impide iniciar la rebelión.
2. Ayudar a la rebelión: recoger batería, circuito y carcasa en puntos ya
   caminables, transportar una pieza por persona y entregarlas en el taller
   del Corredor de Datos. Las tres piezas permiten fabricar módulo y blásteres.
3. Fase verde: conservar el sistema de rayos anunciados y pausas; Guardián y
   Habitante completan sus minijuegos para apagar el escudo.
4. Fase roja: Mensajero transporta el módulo y Aspirante prepara la autorización
   durante las pausas. Las tareas y recargas se conservan al reintentar.
5. Cada participante, incluidos los bots, confirma desde la estación de su rol.
   Sin límite de tres segundos. Las cuatro tareas detienen los ataques.
6. Reconfiguración: cuatro intervenciones de NÚCLEO, Archivista y Representante
   Humano. NÚCLEO se muestra sereno; nunca se destruye.
7. Epílogos del Futuro, Presente y La Copa. Cada escena dura cinco segundos y
   puede adelantarse para el equipo. El servidor conserva escena y revisión.
8. Informe AVL completo, con exportación de los ocho casos. Se avanza al resultado
   cuando el equipo termina de revisarlo.
9. Pantalla de las tres eras, con los umbrales originales de `determinar_final`:
   victoria con promedio positivo >= 55 y negativos < 100; humo en otro caso.
   Se muestran Kael o Mira según la apariencia elegida y el número de casos.
10. Créditos desplazables y regreso al menú. Los integrantes se leen de
    `datos/creditos.json`; los cuatro registros están vacíos para no inventar nombres.

## Combate auxiliar

- F dispara al mini-núcleo más cercano. El servidor exige distancia <= 180,
  línea de visión sin paredes, munición disponible y 0,6 s entre disparos.
- Dos impactos desactivan cada mini-núcleo. Hay como máximo dos; se generan
  espaciados al menos doce segundos en estaciones ya validadas del mapa.
- Son emisores fijos de pulsos cortos: su radio de peligro se señala en el suelo.
  Sus temporizadores y ataques se suspenden durante las pausas de los minijuegos.
- Munición compartida: doce cargas al fabricar, máximo 24. R junto al taller
  repone seis, con ocho segundos entre reposiciones para todo el equipo.
- Desactivar un mini-núcleo devuelve una carga. Quedarse sin munición permite
  seguir esquivando y resolviendo minijuegos: nunca bloquea la victoria.
- E ayuda a compañeros caídos. Los bots esquivan, disparan y ayudan; también
  transportan piezas y fabrican usando el mismo protocolo que una persona.

## Sincronización y reconexión

El estado oficial incluye materiales, cargas, fabricación, munición, enemigos,
confirmaciones y subpaso del desenlace. Las acciones repetidas conservan la
deduplicación de la campaña. Avanzar una escena requiere su revisión actual;
dos solicitudes retrasadas no saltan dos escenas. Cualquier participante puede
avanzar para el equipo mediante el botón identificado con esa función.

La desconexión durante la recolección libera la pieza en su punto original.
Al reconectar durante el cierre, el cliente presenta el subpaso actual. Si cae
directamente en el resultado, cuenta los casos desde el expediente sin necesitar
la caché del informe. El expediente mantiene sus pruebas y referencias completas.

## Arte y audio

Se reutilizan `FinalCooperativo/ConsolaSupervision.png`, el módulo turquesa y las
animaciones existentes de NÚCLEO. Blásteres, piezas, cajas, consolas y mini-núcleos
tienen dibujos de pixel art por código, sin requerir imágenes nuevas.

Las ilustraciones opcionales `Imagenes/Finales/epilogo_futuro.png`,
`epilogo_presente.png`, `epilogo_copa.png`, `Final_tres_eras.png` y
`Final_humo_tres_eras.png` se cargan una vez si existen. En esta copia local no
se encontraron: se usan fondos de las eras y las ilustraciones finales anteriores.

Se buscan `musica_nucleo.mp3`, `batalla_fase1.mp3` y `batalla_fase2.mp3` en
`Audios/Música/`, `Audios/Musica/` y `Audios/`. Si faltan, se usa Ambiente.mp3.
La música de victoria o derrota se reserva para la pantalla final de las tres eras.

## Publicación

Protocolo 17: actualizar clientes y servidor juntos cuando se publique.
La implementación local no implica push ni despliegue en Render.
