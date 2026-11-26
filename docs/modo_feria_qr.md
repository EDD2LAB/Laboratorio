# Modo Feria de los Ecos con QR

## Propósito

El Modo Feria de los Ecos es una experiencia breve para presentar el juego ante visitantes, docentes o jurados. Convierte la pantalla principal en una demostración colectiva: las personas escanean un código QR con su celular, responden una situación de información responsable y observan cómo la decisión del grupo altera La Copa en tiempo real.

No es una campaña nueva ni reemplaza el modo Feria técnico existente de Timeless Glitch. El modo técnico prepara una computadora para exhibición; esta propuesta agrega una dinámica participativa con QR para hacer memorable la demostración.

## Alcance

El modo se realiza **solamente en el mapa de La Copa**. No utiliza Distrito Conecta ni Ciudad Núcleo.

La Copa es suficiente porque ya contiene los elementos educativos y visuales adecuados:

- Tablillas con mensajes públicos.
- Caldero de los Ecos.
- Puentes y rutas de propagación.
- Ecos de Troncos.
- Habitantes, fuentes y testimonios.
- Indicadores de Sabiduría, Confianza, Armonía, Susurros Falsos y Desinformación.
- Árbol de clasificación y decisiones sobre información.

Distrito Conecta y Ciudad Núcleo permanecen intactos dentro de la campaña normal. El progreso, inventario, expediente AVL, misiones, votaciones, roles y finales de los tres mundos no se modifican desde el Modo Feria.

## Experiencia del visitante

La exhibición usa una pantalla grande y los celulares de los visitantes.

1. La pantalla muestra La Copa y una tablilla colectiva.
2. Aparece un panel con un código QR y la instrucción de participar.
3. El visitante escanea el QR sin instalar una aplicación ni crear una cuenta.
4. En el celular recibe una microdecisión de menos de un minuto.
5. El visitante elige cómo reaccionar y responde una pregunta de clasificación o confiabilidad.
6. La pantalla principal registra la respuesta y muestra un Eco que se propaga por los puentes.
7. Al cerrar la ronda, la pantalla revela el resultado colectivo, la categoría real de la información y una enseñanza breve.

La participación debe ser anónima. El sistema no necesita pedir nombre, correo, teléfono ni cuenta personal.

## Contenido de una ronda

Cada ronda dura aproximadamente dos o tres minutos y usa una tablilla corta. La estructura recomendada es:

1. **Situación:** aparece una tablilla con un mensaje posible de La Copa.
2. **Decisión:** el visitante escoge Compartir, Verificar, Detener o Ignorar.
3. **Pregunta educativa:** identifica si se trata de un Rumor Político, Suceso Natural o Acusación Personal; también puede elegir cuál fuente parece más confiable.
4. **Propagación:** se animan los Ecos sobre los puentes según el voto recibido.
5. **Resultado:** se revela la clasificación correcta y el efecto acumulado de la comunidad.
6. **Cierre:** se muestra una frase corta y comienza otra ronda para el siguiente grupo.

Ejemplos de casos para la feria:

- “Kael cerrará el puente norte esta noche”, sin fuente directa.
- “Un rayo dañó todas las plataformas del Mirador Alto”, basado en un testimonio incompleto.
- “Mira ocultó materiales de reparación”, sin testigos verificables.
- “El Consejo anunció una nueva ruta”, con apariencia oficial pero sin sello ni fecha.

Los casos de feria son independientes de los casos de campaña. Se guardan en un catálogo propio y no se añaden al expediente AVL de una partida real.

## Reacción visual de La Copa

Las respuestas del público se muestran como parte de La Red de Ecos.

- Una respuesta responsable ilumina puentes con colores verdes, dorados o azules.
- Una respuesta que comparte información sin confirmar alimenta una propagación morada o roja.
- El Caldero brilla en verde y oro cuando predominan las verificaciones.
- El Caldero se torna morado ante dudas colectivas y rojo ante desinformación dominante.
- El resultado de cada ronda actualiza los indicadores de feria, no los indicadores de la campaña.

Al completar varias rondas, la pantalla ofrece un resultado global, por ejemplo:

- Guardianes que verificaron antes de compartir.
- Mensajes detenidos antes de propagarse.
- Rumores compartidos sin fuente.
- Estado final de La Copa.

Un resultado positivo hace que el Caldero libere luz y que la aldea se ilumine. Un resultado crítico muestra grietas, humo y una invitación a verificar mejor la siguiente ronda.

## Arquitectura aislada

El Modo Feria debe tener estado propio y temporal. Su entrada desde el menú puede llamarse **Feria de los Ecos QR**.

```text
Menú principal
├── Campaña normal
│   ├── La Copa
│   ├── Distrito Conecta
│   └── Ciudad Núcleo
├── Multijugador
└── Feria de los Ecos QR
    ├── Pantalla grande de La Copa
    ├── Sesión QR temporal
    ├── Casos breves de feria
    └── Resultado colectivo
```

El estado recomendado es:

```text
SesionFeria
├── codigo_sesion
├── ronda_actual
├── casos_disponibles
├── respuestas_por_dispositivo
├── conteo_por_decision
├── conteo_por_clasificacion
├── participantes_unicos
├── indicadores_feria
├── estado_caldero
└── tiempo_restante
```

Reglas de aislamiento:

- No leer ni escribir el progreso de campaña.
- No modificar el expediente AVL.
- No gastar suministros, habilidades ni inventario.
- No modificar roles, partidas online ni salas existentes.
- No guardar votos como preferencias permanentes.
- Al salir, destruir la sesión temporal y volver al menú.

Se pueden reutilizar componentes visuales existentes de La Copa, pero los datos deben pertenecer exclusivamente a `SesionFeria`.

## QR y página móvil

El QR se genera dinámicamente al iniciar una sesión. Debe incluir la dirección local de la computadora y un identificador de sesión, por ejemplo:

```text
http://IP-DEL-EQUIPO:8080/feria/AB12CD
```

La página móvil debe ser ligera y tener solo:

- Nombre de la ronda.
- Texto de la tablilla.
- Cuatro botones de decisión.
- Una pregunta de clasificación o fuente.
- Confirmación de voto recibido.

Para evitar votos repetidos, se puede guardar una cookie o token temporal del navegador. Cada dispositivo puede votar una vez por ronda; al iniciar una nueva ronda vuelve a quedar habilitado.

La opción más estable para una feria es que todos se conecten a la misma red Wi-Fi local. No debe requerir Internet. Un router propio o punto de acceso del computador basta para la demostración.

## Imágenes nuevas

Se reutilizan el mapa, Caldero normal, puentes, personajes, tablillas, botones, HUD, tipografía y efectos de propagación ya disponibles. Solo se necesitan ocho activos exclusivos:

| Activo | Uso | Tamaño recomendado |
| --- | --- | --- |
| Panel del QR | Marco de madera y pergamino vacío donde se dibuja el QR real | 1024 x 768 |
| Icono de celular | Indica que el visitante debe participar desde el teléfono | 256 x 256 |
| Sello de voto recibido | Confirmación visual de respuesta registrada | 256 x 256 |
| Icono de espera | Estado mientras llegan más respuestas | 256 x 256 |
| Icono de resultado colectivo | Resume que la decisión la tomó la comunidad | 256 x 256 |
| Caldero positivo de feria | Resultado con decisiones responsables | 512 x 512 |
| Caldero crítico de feria | Resultado con desinformación dominante | 512 x 512 |
| Marco final de resultados | Panel para estadísticas y cierre de sesión | 1024 x 768 |

El QR no se diseña como imagen: se genera por código y se coloca dentro del Panel del QR. Los textos también se dibujan con la fuente del juego para evitar errores de escritura en imágenes generadas.

## Flujo de pantalla grande

```text
Inicio Feria
    ↓
Presentación del caso y QR
    ↓
Recepción de respuestas
    ↓
Ecos viajan por los puentes
    ↓
Resultado colectivo y clasificación real
    ↓
Estado del Caldero
    ↓
Nueva ronda o resumen final
```

Durante la recepción de respuestas, la pantalla puede mostrar el total de participantes sin revelar el voto individual:

```text
Voces reunidas: 18
La comunidad está decidiendo...
```

Tras cerrar la ronda, sí se muestran los porcentajes colectivos y una explicación educativa corta.

## Fases de implementación

### Fase 1: prototipo local

- Botón de Feria de los Ecos QR en el menú.
- Mapa de La Copa sin modificar la campaña.
- Una ronda fija con cuatro decisiones.
- QR generado localmente.
- Página móvil con un único voto.
- Resultado mostrado en la pantalla grande.

### Fase 2: dinámica visual

- Propagación de Ecos por los puentes según cada voto.
- Indicadores temporales de feria.
- Estados positivo, dudoso y crítico del Caldero.
- Las ocho imágenes exclusivas integradas.

### Fase 3: experiencia de exhibición

- Tres o cuatro casos rotativos.
- Temporizador por ronda.
- Reinicio automático para el siguiente grupo.
- Resumen final de la sesión.
- Mensaje educativo adaptado al resultado colectivo.

## Pruebas necesarias

- Verificar que una campaña normal no cambie después de jugar Feria.
- Verificar que salir de Feria elimine todos los votos temporales.
- Probar varios celulares en la misma Wi-Fi.
- Probar voto repetido desde el mismo celular.
- Probar pérdida de conexión de un visitante.
- Comprobar que el QR corresponde a la sesión activa.
- Comprobar que el juego funciona sin Internet usando red local.
- Probar una ronda completa frente a pantalla grande con al menos cinco participantes.

## Mensaje de presentación

La idea central para explicar el modo a un jurado es:

> No usamos árboles y grafos solo como requisito técnico. Los convertimos en la manera en que una comunidad clasifica, comparte, verifica o distorsiona información.

El visitante deja de ser espectador: se convierte en una voz de La Copa y observa en tiempo real cómo una decisión aparentemente pequeña puede proteger o afectar a toda una comunidad conectada.

## Estado de la implementación

**Fase 1 implementada** en el paquete `feria/` (aparte del juego):

| Archivo | Contenido |
| --- | --- |
| `feria/casos.py` | Cuatro casos propios con categoría del árbol de La Copa, verdad y enseñanza |
| `feria/sesion.py` | `SesionFeria` en memoria: un voto por celular y ronda, resultado colectivo |
| `feria/web.py` | Rutas `/feria/...` (página, ronda, voto y control del anfitrión) y servidor local en un hilo |
| `feria/remoto.py` | `SesionRemota`: la pantalla controla su sesión en Render desde un hilo |
| `feria/movil.py` | Página del celular: HTML sin recursos externos ni datos personales |
| `feria/qr.py` | QR con `segno`, módulos enteros y zona blanca |
| `feria/pantalla.py` | Pantalla grande sobre La Copa con el arte de `Imagenes/Modo feria/` |

Del juego solo cambia el menú: el botón **Feria de los Ecos QR** (también en
el menú del modo feria técnico). La pantalla corre su propio bucle y, al salir
con Esc, detiene el servidor y borra la sesión. No toca campaña, expediente,
preferencias, salas ni protocolo.

**Votos por internet (Render) y respaldo local**

El servidor de Render registra las mismas rutas bajo `/feria` (aditivas: no
cambian las salas ni el protocolo). Al entrar a la feria la pantalla crea su
sesión allí (`POST /feria/nueva`) y la controla con una clave que solo ella
conoce (`/estado` y `/control`); los celulares abren
`https://la-copa-salas.onrender.com/feria/CÓDIGO` con sus datos móviles, sin
entrar a ninguna Wi-Fi. Si Render estaba dormido (responde, pero aún no atiende),
la pantalla espera hasta 90 s; si no hay internet (tres intentos seguidos sin
ninguna respuesta HTTP, unos 6 s) o con **L**, usa el servidor local de antes.
Una sesión que llega a crearse después de cancelar con Esc o L se termina sola. Una sesión de
internet se borra al salir con Esc o tras 10 minutos sin su pantalla.
`COPA_FERIA_SERVIDOR` elige otro servidor (vacía: solo red local). Hace falta
desplegar Render a mano para que tenga estas rutas.

**En otros computadores**

Basta con `git pull` y abrir el juego como siempre (Jugar.bat o ▶ de VS Code).
El QR usa `segno`: si no está instalada, se toma del `.venv` del proyecto o de
la copia incluida en `feria/_vendor` (BSD, Python puro), así que no hay que
instalar nada nuevo. Con internet, los votos van por Render y no hace falta
abrir el firewall.

**Cómo usarla en la feria**

1. Con internet en el computador no hace falta nada más: los visitantes usan
   sus datos móviles. Abrir la feria unos minutos antes despierta a Render.
2. Solo red local: computador y celulares en la misma Wi-Fi (la zona con
   cobertura móvil de Windows evita redes que aíslan a los clientes; la tecla
   **I** cambia de red). La primera vez, Windows pregunta si Python puede
   recibir conexiones: aceptar.
3. Menú → Feria de los Ecos QR. Los visitantes escanean y votan.
4. Espacio o «Ver resultado» cierra la ronda; N o «Nueva ronda» abre la siguiente.
   «Votar aquí» permite votar con el ratón a quien no tenga celular.

El servidor local usa el puerto 8080 (o 8081, 8090, 8765 si está ocupado).
Pendiente para fases siguientes: propagación por los puentes, temporizador y
rondas automáticas y resumen de la sesión.
