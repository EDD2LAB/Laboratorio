# Textos: inventario y propuestas pendientes de revisión

Generado por `python herramientas/auditar_textos.py`. No modifica el juego.
Se encontraron 1081 candidatos de tres o más palabras; 12 superan 20 palabras.
El listado completo con archivo, línea, conteo y texto está en `textos.csv`.

## Alcance

Auditoría estática de interfaz, multijugador y lógica. Excluye docstrings, rutas y
textos de menos de tres palabras. Los valores interpolados aparecen como {dato}.
Puede incluir mensajes técnicos; no garantiza capturar cada texto construido en ejecución.
Las leyes y sanciones del catálogo JSON no se recortan con esta herramienta.

## Candidatos largos para revisar primero

| Ubicación | Palabras | Texto actual |
| --- | --- | --- |
| `interfaz/menu_pausa.py:58` | 39 | 6. Después ayuden a la aldea: lleven los materiales al lugar marcado, hagan la actividad en pareja y confirmen en el caldero. En el primer caso también reparan el Puente 1: pulsa E tres veces en la zona verde. |
| `interfaz/menu_pausa.py:71` | 36 | 3. Tu celular (C) guarda las pistas. Junto a la pantalla pública decidan en él: Verificar, Denunciar, Ignorar o Publicar. Los bots reúnen las demás pistas y te dejan una; decidir les toca a las personas. |
| `interfaz/menu_pausa.py:53` | 29 | 3. En un tronco eliges con las flechas a quién escribir: a una persona o a todos. Los bots hacen lo que les pidas, por ejemplo venir al caldero. |
| `interfaz/menu_pausa.py:55` | 29 | 4. Vayan al caldero y elijan una poción: Quemar corrige lo falso, Colgar lo difunde e Ignorar no lo comparte. Con bots decide tu elección; entre personas, la mayoría. |
| `interfaz/menu_pausa.py:67` | 26 | 1. Para viajar, ve al portal de La Copa y pulsa E. Cada persona del equipo debe aceptar junto al portal; los bots viajan con ustedes. |
| `interfaz/inicio.py:316` | 25 | No hay conexión con el anfitrión. Comprueba que la sala siga abierta, la IP, el puerto y el permiso de Python en la red privada. |
| `interfaz/partida_multijugador.py:1315` | 25 | Busca a las personas dentro de los edificios: entra por la puerta con E y habla con ellas. Tus pistas quedan en el celular (C). |
| `multijugador/nucleo.py:17` | 25 | Sin permiso del consejo humano, le dieron a NÚCLEO el control absoluto. Bloqueó sectores y sus cuentas automáticas atacan a un Ciudadano Conectado que protesta. |
| `multijugador/suministros.py:10` | 23 | El Puente 1 está roto. Metan tablas, cuerda y la canasta de herramientas en el cesto de la aldea; después reparen el puente. |
| `interfaz/menu_pausa.py:51` | 22 | 2. Necesitas dos pistas. Pulsa I para leerlas y darlas a un compañero cercano, o envíalas desde un Tronco de los Ecos. |
| `interfaz/menu_pausa.py:65` | 22 | Una imagen viral acusa a Ronaldo Vélez. ¿Es real? Aquí la cámara va cerca de tu personaje: recorre el mapa para descubrirlo. |
| `multijugador/suministros.py:17` | 21 | Después de investigar el agua, reúnan en el cesto de la aldea agua segura y provisiones para repartirlas a las familias. |

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
| Pista de la llave de supervisión | El Corredor te dio la llave. Llévala al Centro de Verificación. | 11 |
| Pista sobre firmas de registros | Revisa quién firma y cuándo. La firma debe ser de alguien autorizado. | 12 |
| Entrega del farol en el tutorial | Lleva el farol al tronco brillante. Pulsa E para entregarlo. | 10 |
| Solicitud de una segunda pista | Pide otra pista con I. Comparte también la tuya. | 9 |
