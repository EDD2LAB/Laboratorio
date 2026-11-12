# Ciudad Núcleo (Era III)

El exterior sigue usando el mapa provisional generado a partir del Presente.
Los cinco interiores nuevos ya se usan en la exploración del protocolo 14;
las animaciones de NÚCLEO se conectaron en la etapa 5. Ver
`exploracion_etapa6.md` y `auditoria_exploracion_etapa6.json`.

El mapa nuevo mide 1048 x 577 y el provisional 998 x 576: comprobar geometría,
puertas y puntos caminables antes de sustituirlo. Las paredes de los JSON se
editan a mano; esta etapa no las modifica. No ejecutar el generador sobre arte
definitivo: su protección contra sobrescritura todavía está pendiente.

| Qué | Archivo a reemplazar | Nota |
| --- | --- | --- |
| Mapa | `Imagenes/Futuro/generado/MapaFuturo.png` | Misma resolución que `MapaPresente.png`. Si cambia la geometría, actualizar también las colisiones |
| Colisiones | `Hitboxes/Mapas/Futuro/MapaFuturo_hitboxes.json` | Geometría del provisional; revisión manual antes de cambiar mapa |
| Archivista | `Imagenes/Futuro/generado/NPCS/Archivista/` | Derivado del Agente de verificación |
| Corredor de Datos | `Imagenes/Futuro/generado/NPCS/Corredor de Datos/` | Derivado del Mensajero urbano |
| Ciudadano Conectado | `Imagenes/Futuro/generado/NPCS/Ciudadano Conectado/` | Derivado de la Habitante conectada |
| Representante Humano | `Imagenes/Futuro/generado/NPCS/Representante Humano/` | Derivado del Aspirante contemporáneo |

El avatar de NÚCLEO usa sus animaciones reales, con respaldo por código si faltan.

## Misión `nucleo_control`

Se puede viajar desde los portales por aceptación del equipo, también antes
de completar los casos del Presente. Los puntos usan ids de hitboxes existentes:

- `entrada_estacion_mensajero`: restaurar conexiones (grafo validado con BFS).
- `entrada_sede_aspirante`: encontrar el registro alterado.
- `entrada_verificacion`: entregar la llave del Corredor de Datos, que
  está junto a `entrada_cafe_digital`. Si un pulso de vigilancia (rutas `npc_routes`
  del JSON) toca a quien la lleva, la llave vuelve al Corredor.
- `entrada_centro_comunitario`: el Ciudadano Conectado abre el ataque de cuentas.
- `entrada_sede_aspirante` y `entrada_campana_ronaldo`: Archivista y Representante Humano;
  sin hablar con el Representante no se vota la reconfiguración.
- Barreras: `entrada_cafe_digital`, `entrada_influencer`, `entrada_campana_ronaldo` y
  `entrada_centro_comunitario`, hasta restaurar las conexiones. Los cinco interiores se abren después de
  restaurarlas y ofrecen consultas opcionales.
- `pantalla_publica_presente`: decisión final y regreso a Distrito Conecta.

El caso entra al expediente con la ficha de `datos/casos_expediente.json`,
incluidos los campos legales incorporados en el protocolo 12.
