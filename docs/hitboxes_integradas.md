# Hitboxes de La Copa y Distrito Conecta

Se integran los JSON manuales de Keisy Polo publicados en main. El commit
04db4d8 contiene también ajustes de La Copa, además del Futuro; 8b3911c entrega
el exterior del Presente y sus cinco interiores. El Futuro conserva los ajustes
ya integrados en multijugador.

La Copa incorpora 133 paredes. Distrito Conecta incorpora 199 en el exterior,
91 en el Café Digital, 62 en el Centro de Verificación, 79 en la Estación del
Mensajero, 79 en el Estudio del Influencer y 71 en la Sede del Aspirante.
Las paredes se conservan sin editar; cantidades y hashes están registrados en
auditoria_hitboxes_presente.json.

Las rutas activas de los interiores pasan de Hitboxes/Fondos/Mapas/Presente a
Hitboxes/Mapas/Presente en cliente y servidor. Los archivos anteriores quedan
como históricos y no se utilizan. Se conservan las salidas y se añaden puntos
de aparición a los archivos nuevos, que venían sin ellos. Dos apariciones se
ajustan al suelo libre junto a la puerta. El disparador de salida del café se
sitúa al pie de su puerta, para que la guía no apunte al lado interior de la
pared. No se copian las restricciones
rectangulares provisionales de suelo sobre las paredes detalladas nuevas.

Los personajes con pistas y las mesas se sitúan en la zona conectada a la
entrada, para no quedar aislados detrás de muebles. Las apariciones de varias
personas dentro de un edificio usan la misma comprobación de accesibilidad.

Campaña local con bots y salas utilizan el mismo código de colisiones. El
protocolo 21 exige actualizar los clientes y el servidor al publicar. Integrar
estos cambios localmente no equivale a hacer push ni desplegar Render.

Validación de esta integración: 81 pruebas aprobadas en 65,497 segundos. Incluye
los cinco accesos, entradas de cuatro jugadores, pistas y mesas alcanzables,
viajes entre eras, campaña y movimiento por WebSocket. Se inspeccionó además la
superposición de las paredes sobre los seis fondos del Presente. La simulación
del contexto Docker pasa con protocolo 21, dos humanos y cuatro participantes,
78 archivos y 200 ticks, sin Pygame. Esto no constituye un build real de Docker.

## Corrección posterior en La Copa

La suite completa detectó que las 133 paredes nuevas de La Copa dejaban
caminar por el aire: el recorrido desde el inicio pasaba de unas 2400 celdas
(plataformas y puentes) a 10 341. Las fugas estaban en el borde superior de la
plataforma del caldero y en la plataforma superior derecha, donde faltaban
siete paredes de la versión anterior.

Con autorización del usuario se añadieron esas siete paredes, copiadas sin
cambios desde b2bd91b, al final del archivo. Las 133 originales no se editan:
su hash sigue en auditoria_hitboxes_presente.json y las restauradas tienen su
propio registro. El recorrido vuelve a 2379 celdas y todos los objetivos
siguen alcanzables. Conviene que Keisy revise en el editor si prefiere cerrar
esos bordes con su propio trazado.
