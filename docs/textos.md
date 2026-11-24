# Textos: inventario y propuestas pendientes de revisión

Generado por `python herramientas/auditar_textos.py`. No modifica el juego.
Se encontraron 1373 candidatos de tres o más palabras; 27 superan 20 palabras.
El listado completo con archivo, línea, conteo y texto está en `textos.csv`.

## Alcance

Auditoría estática de interfaz, multijugador y lógica. Excluye docstrings, rutas y
textos de menos de tres palabras. Los valores interpolados aparecen como {dato}.
Puede incluir mensajes técnicos; no garantiza capturar cada texto construido en ejecución.
Las leyes y sanciones del catálogo JSON no se recortan con esta herramienta.

## Candidatos largos para revisar primero

| Ubicación | Palabras | Texto actual |
| --- | --- | --- |
| `interfaz/menu_pausa.py:59` | 72 | 6. Después ayuden a la aldea: lleva los materiales al lugar marcado (pulsa B para pedir que un bot lleve uno), haz la actividad en pareja (un bot ayuda y tú trabajas) y confirma en el caldero. En el primer caso también reparan el Puente 1: pulsa E tres veces en la zona verde. En el caso del agua, toma cada cesta del cesto (E) y llévala caminando hasta una familia marcada. |
| `interfaz/menu_pausa.py:73` | 36 | 3. Tu celular (C) guarda las pistas. Junto a la pantalla pública decidan en él: Publicar, Verificar, Denunciar o Ignorar. Las pistas, el análisis y la decisión les tocan a las personas; los bots las acompañan. |
| `interfaz/menu_pausa.py:54` | 34 | 3. En un tronco eliges con las flechas a quién escribir: a una persona o a todos. Los bots solo te ayudan en lo que necesita dos personas: no investigan ni eligen por ti. |
| `interfaz/menu_pausa.py:67` | 33 | Tres publicaciones virales usan la tecnología para engañar: un video editado, una voz clonada y una foto robada. ¿Son reales? Aquí la cámara va cerca de tu personaje: recorre el mapa para descubrirlo. |
| `interfaz/menu_pausa.py:56` | 29 | 4. Vayan al caldero y elijan una poción: Quemar corrige lo falso, Colgar lo difunde e Ignorar no lo comparte. Con bots decide tu elección; entre personas, la mayoría. |
| `multijugador/dialogos.py:196` | 28 | Busca los cestos del encargo, recoge una carga y llévala al destino iluminado. El equipo ve las entregas. Si ya llevas algo, entrégalo antes de recoger otra carga. |
| `interfaz/menu_pausa.py:71` | 27 | 2. Habla con las personas marcadas (E) hasta reunir las pistas del caso. Cada caso tiene las suyas y quien las tiene aparece marcado en el mapa. |
| `multijugador/dialogos.py:194` | 27 | Cada uno puede contar qué prueba encontró. Escuchen las razones del otro antes de elegir en el caldero. Pueden cambiar un voto para llegar a un acuerdo. |
| `interfaz/menu_pausa.py:69` | 26 | 1. Para viajar, ve al portal de La Copa y pulsa E. Cada persona del equipo debe aceptar junto al portal; los bots viajan con ustedes. |
| `multijugador/suministros.py:19` | 26 | Después de investigar el agua, reúnan en el cesto de la aldea agua segura y provisiones. Luego tomen las cestas y llévenlas caminando a cada familia. |
| `interfaz/inicio.py:374` | 25 | No hay conexión con el anfitrión. Comprueba que la sala siga abierta, la IP, el puerto y el permiso de Python en la red privada. |
| `interfaz/partida_multijugador.py:1725` | 25 | Busca a las personas dentro de los edificios: entra por la puerta con E y habla con ellas. Tus pistas quedan en el celular (C). |
| `multijugador/campana.py:18` | 25 | El puente se dañó por el desgaste y la lluvia, no por Kael. El consejo lo cerró por seguridad hasta repararlo; Kael solo propuso revisarlo. |
| `multijugador/dialogos.py:195` | 25 | Abre I, elige la pista y un compañero. El Mensajero puede llevarla. También puedes hablar con alguien cercano. Compartir una pista ayuda a investigar juntos. |
| `multijugador/mision.py:257` | 25 | El puente se dañó por el desgaste y la lluvia, no por Kael. El consejo lo cerró por seguridad hasta repararlo; Kael solo propuso revisarlo. |
| `multijugador/nucleo.py:17` | 25 | Sin permiso del consejo humano, le dieron a NÚCLEO el control absoluto. Bloqueó sectores y sus cuentas automáticas atacan a un Ciudadano Conectado que protesta. |
| `interfaz/menu_pausa.py:86` | 24 | Q: cada rol tiene un poder en esta era: Lupa de Memoria, Impulso del Viento, Voz Comunitaria o Comunicado Público. Se usa una vez. |
| `multijugador/dialogos.py:193` | 24 | Abre I y compara quién habla, la fecha y el lugar. Busca algo en lo que coincidan fuentes independientes. Yo no voto por ustedes. |
| `multijugador/exploracion.py:7` | 24 | Compara dos fuentes. Mira quién publicó el mensaje, cuándo lo hizo y qué pruebas aporta. Una imagen llamativa no demuestra que algo sea cierto. |
| `multijugador/exploracion.py:8` | 24 | Una publicación puede llegar a muchas personas y aun así ser falsa. Antes de compartirla, pregunta: ¿quién la creó y dónde está el original? |
| `multijugador/exploracion.py:9` | 24 | La firma dice quién se hace responsable de un documento. Compara autor, fecha y permiso: una cuenta no puede darse autoridad a sí misma. |
| `logica/conversaciones.py:5` | 23 | Le propuse al consejo revisar las tablas del puente norte porque la lluvia las había dañado. ¿Quién te contó que yo lo rompí? |
| `multijugador/exploracion.py:11` | 23 | Conserva el origen y la fecha al llevar un mensaje. Si descubres un error, envía también la corrección a quienes recibieron el aviso. |
| `multijugador/suministros.py:10` | 23 | El Puente 1 está roto. Metan tablas, cuerda y la canasta de herramientas en el cesto de la aldea; después reparen el puente. |
| `interfaz/menu_pausa.py:52` | 22 | 2. Necesitas dos pistas. Pulsa I para leerlas y darlas a un compañero cercano, o envíalas desde un Tronco de los Ecos. |
| `interfaz/menu_pausa.py:63` | 21 | Q: tu poder, una vez por caso tras recoger tu pista. T o el botón Casos: lo descubierto y el expediente. |
| `multijugador/exploracion.py:10` | 21 | Escucha a alguien que estuvo allí. Después busca otra fuente independiente. Dos copias del mismo mensaje siguen siendo una sola fuente. |

## Propuestas que todavía NO se aplican

Objetivo de lectura: hasta 20 palabras por tarjeta. Revisar el contexto completo
y el mensaje educativo antes de aprobar cada propuesta; no son sustituciones automáticas.
Los avisos breves deberían caber en dos líneas. Las pruebas y normas completas deben
seguir disponibles en el expediente aunque se aprueben resúmenes.

| Tarjeta / finalidad | Propuesta | Palabras |
| --- | --- | --- |
| Pista del agua: fecha del informe | El informe habla de un depósito cerrado hace diez años. | 10 |
| Pista del agua: sustitución | El depósito antiguo fue desconectado. El agua actual viene del manantial nuevo. | 12 |
| Pista del video original | El video original muestra a Ronaldo poniendo monedas. Compáralo en Analizar. | 11 |
| Pista de la llave de supervisión | El Corredor te dio la llave. Llévala al Centro de Supervisión. | 11 |
| Pista sobre firmas de registros | Revisa quién firma y cuándo. La firma debe ser de alguien autorizado. | 12 |
| Entrega del farol en el tutorial | Lleva el farol al tronco brillante. Pulsa E para entregarlo. | 10 |
| Solicitud de una segunda pista | Pide otra pista con I. Comparte también la tuya. | 9 |
