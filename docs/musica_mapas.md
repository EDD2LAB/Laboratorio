# Música por mapa

La Copa conserva Audios/Ambiente.mp3. Distrito Conecta utiliza
Audios/Música/musica_presente.mp3 y Ciudad Núcleo utiliza
Audios/Música/musica_nucleo.mp3. Los interiores mantienen la pista de su era.

En la batalla del Futuro se reproducen batalla_fase1.mp3 y batalla_fase2.mp3
según la fase oficial. En preparación, reintento y reconfiguración vuelve la
música de la ciudad. Los epílogos usan la pista de la era mostrada; la pantalla
del resultado y los créditos conservan victoria o game_over según los indicadores.

La vista actualiza la selección al recibir el estado, incluso si no cambia de
mapa. El gestor mantiene la reproducción de la pista actual y hace transición
entre canales al cambiar, sin recargar los archivos en cada paquete. Se usan
los controles de volumen y silencio existentes.

Campaña local con bots y multijugador comparten esta selección. Los audios se
cargan en cada PC y no se envían por red. No requiere cambiar el protocolo ni
desplegar el servidor; sí actualizar los clientes cuando se publique el cambio.
