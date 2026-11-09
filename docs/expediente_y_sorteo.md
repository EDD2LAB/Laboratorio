# Expediente AVL y sorteo de La Copa

El servidor mantiene `ExpedientePartida`. Al resolver cada uno de los cuatro
eventos crea un `Caso` con las pruebas que el equipo encontró, la decisión y
su resultado. Una rectificación actualiza ese mismo caso. No se publican las
pruebas todavía no encontradas ni los eventos futuros.

El primer caso se archiva automáticamente. Los siguientes esperan en una cola;
cualquier compañero conectado puede ayudar a colocarlos. Abrir **T: casos**,
comparar con el círculo dorado y elegir izquierda o derecha. Se ordenan por
gravedad, orden de resolución e identificador. Ante igual gravedad, el nuevo
va a la derecha. El servidor calcula `ruta_insercion()` y valida cada paso;
el cliente no recibe la solución. Al terminar, el AVL realiza las rotaciones
necesarias y todos reciben el mismo árbol. Pulsar un círculo permite leer el
caso y recorrer sus pruebas. Esta actividad no bloquea las misiones.

Cada solicitud contiene caso, revisión y paso. Dos clics simultáneos sobre
el mismo paso no pueden producir una inserción doble. Los reintentos de red
mantienen la deduplicación por `id_solicitud`. El expediente permanece en la
partida del servidor durante una reconexión; no se guarda en disco y un
reinicio del servidor lo pierde, como el resto de la sala.

`datos/casos_expediente.json` define tipo y gravedad educativa (1–9), no
gravedad jurídica. Ley y sanción quedan vacías y pendientes del profesor.
Esta etapa cubre La Copa. El evento de Distrito Conecta, la exportación del
informe y las animaciones de rotación se integrarán después.

## Sorteo

`SorteoPartida` usa un generador independiente por partida y una semilla
aleatoria de 64 bits creada en el servidor. Sortea las variantes coherentes
del agua y la tormenta, y a quién menciona la acusación sobre la ayuda.
La persona mencionada no se convierte en culpable. El primer caso conserva
su función de tutorial. Las pruebas y los metadatos para los bots corresponden
siempre a la variante seleccionada. No se comparte la semilla durante la partida.

Para reproducir un escenario en pruebas:

```python
PartidaMovimiento(jugadores, 0, semilla=935)
ClienteCampanaLocal("Prueba", "guardian", semilla=935)
```

Desde el segundo caso, visitar la fuente entrega además un aviso temporal.
Su duración (90, 120 o 150 segundos) depende de la semilla, el evento y el rol.
Aparece como otra tarjeta en I, se comparte junto a la prueba y conserva la
fecha original al copiarlo. Un aviso caducado deja de transmitirse; volver
a la fuente lo renueva. Las pruebas principales se conservan y los avisos
son complementarios, para investigar con calma. Se usa el reloj del servidor.

## Despliegue

Protocolo **11**: actualizar tanto los clientes como el servidor de Render.
El estado viaja por diferencias (`multijugador/delta.py`): un snapshot al conectar,
reconectar o cambiar de dimensión o edificio y, luego, mensajes `delta` con lo que
cambió; `pedir_snapshot` recupera una base perdida. Añade también `pedir_informe`.
El protocolo 10:
Añade las acciones `presente_analizar`, `presente_marcar`, `presente_siguiente`
(casos manipulados del Presente), `futuro_resolver` (terminales de Ciudad Núcleo),
`entrar_edificio` y `salir_edificio` (interiores). El protocolo 9 trajo las
correcciones de identidad de Mira y la separación entre bots.
El límite LAN pasa a 32 KiB para incluir los cuatro casos archivados;
las pruebas verifican que el estado completo quede dentro de ese límite.
El Dockerfile incluye los módulos de lógica y el catálogo JSON, sin Pygame.
El cambio local no actualiza por sí solo Render.

## Validación local

- `python -m unittest discover -s tests -q`: **207 pruebas aprobadas**.
- Incluye rotaciones LL/RR/LR/RL, 150 inserciones, rectificación sin duplicados,
  validación de pasos, privacidad, reproducibilidad, caducidad, renovación,
  conservación del vencimiento al compartir y controles de la interfaz.
- Revisadas visualmente las pantallas del libro y de un aviso temporal.
- Comprobada la importación de la lógica y el catálogo con las dependencias
  estándar de Python, sin cargar Pygame. No se ejecutó un build de Docker.
