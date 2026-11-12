# Ciudad Núcleo en protocolo 18

El juego ya utiliza el exterior definitivo `Imagenes/Fondos/Mapas/Futuro/MapaFuturo.png`
de 1048 x 577 y sus paredes propias. El mapa generado a partir del Presente se
conserva como recurso histórico, pero no es el exterior activo.

## Geometría incorporada

Se importaron exclusivamente los seis JSON de `Hitboxes/Mapas/Futuro/` entregados
en `04db4d8abb518286fadb508aa1e9aad33890b3fe` (rama main). No se incorporaron los
cambios de otras eras ni los cambios remotos de lógica de bots en esta etapa.

| Lugar | Imagen y JSON de hitboxes, con el mismo nombre base |
| --- | --- |
| Exterior | MapaFuturo |
| Centro de Supervisión | Centro-Verif-FuturoInt |
| Observatorio de Mensajes | estudioInflu-Futuroint |
| Archivo del Consejo | Sede-Aspirante-FuturoInt |
| Café de Datos | CafefuturoInt |
| Estación de Enlaces | EstacióndeMensajeriaInt |

Las imágenes están en `Imagenes/Fondos/Mapas/Futuro/` y los JSON en
`Hitboxes/Mapas/Futuro/`. Cliente y servidor cargan los mismos archivos y usan
la misma transformación al lienzo 960 x 720. Los interiores tienen resolución
344 x 192; el editor guardó sus medidas ampliadas con proporción equivalente.
La normalización y el rectángulo final de dibujo coinciden en ambos lados.

Los cinco interiores traían paredes, sin apariciones ni salidas. Se añadieron
solo el spawn, una salida junto a la entrada visible y una interacción de mesa.
Las paredes originales se conservan exactamente: sus cantidades y hashes están
en `auditoria_mapa_futuro.json`, junto con las rutas comprobadas.

## Apariciones y rutas

- La aparición exterior se corrige primero a una posición libre. A partir de
  ella se colocan los cuatro participantes en el mismo componente conectado.
- La misma regla se aplica al entrar varias personas a cada interior.
- Las terminales y NPC del Futuro se anclan a zonas accesibles desde la entrada.
  Se corrigieron dos NPC que quedaban aislados por las paredes nuevas.
- Materiales, taller, mini-núcleos, recargas y consolas del final reutilizan esas
  estaciones transitables. No hay puntos de combate inventados fuera del mapa.
- Las cinco mesas se ubican junto al mobiliario visible y tienen una ruta de
  regreso a la salida. El portal y las cinco puertas exteriores son alcanzables.
- El análisis de conectividad se guarda en caché por geometría; no se repite
  durante cada cuadro de juego.

## Protección y publicación

No se reemplaza una imagen interior ausente por una del Presente con otras
paredes: se informa del recurso que falta. El generador provisional cancela su
trabajo si ya existe el JSON exterior, para no destruir el trabajo manual.
Las futuras modificaciones de paredes siguen haciéndose en el editor.

El servidor empaqueta las seis hitboxes y `logica/zonas_caminables.py` con las
reglas actuales del contexto de Docker. Protocolo 18 exige actualizar juego y
servidor juntos. Implementación local no significa push ni despliegue.

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

Validación final: 564 pruebas aprobadas en 677,243 segundos.
