# Prompt para Claude Code: rama `coherencia-eras`

> Lánzalo **después** de unir `copa-dos-eventos` en `multijugador`. Varios arreglos suponen que La Copa ya tiene solo `puente_norte` y `tormenta`.

---

Trabaja en el repositorio EDD2LAB/laboratorio. Crea la rama `coherencia-eras` desde `multijugador` (debe incluir ya `copa-dos-eventos`).

**Antes de cambiar nada:**
1. Corre la suite completa: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv\Scripts\python.exe -m unittest discover -s tests`. Anota el número real de pruebas y fallos.
2. Corre `.venv\Scripts\python.exe herramientas/benchmark.py --segundos 60` y guarda el resultado.

**Regla permanente:** no toques ninguna hitbox de pared. Este trabajo es solo de lógica y textos.

## Objetivo
Que cada era hable solo de sí misma y que la historia de La Copa no se contradiga. Sin cambios de protocolo salvo que sea inevitable. Si cambias el protocolo, súbelo de número y avísame.

## 1. Restos de los casos quitados (comprobar primero)
- `logica/sorteo_partida.py`, `SorteoPartida.casos`: el código supone que el **último** caso es `ayuda`. Cambia "Mira" en su texto por una persona sorteada y renombra la pista del aspirante a "Inventario del reparto". Con dos casos, eso caería sobre `tormenta`. Si `copa-dos-eventos` no lo quitó, quítalo y deja `self.persona` sin uso o elimínalo.
- `multijugador/suministros.py`, `ENCARGOS`: se elige por `ronda`. Confirma que después de `puente_norte` sale el encargo del puente, y que el del agua no aparece en ningún momento.
- Borra lo que quede de `agua` y `ayuda` en `logica/conversaciones.py` ("Acusacion Personal" de TESTIMONIOS y REACCIONES, el bloque "reparar"/Mira y el tema "la tablilla sobre Mira" en `construir_mensajes_eco`), en `multijugador/clasificacion.py`, en `datos/casos_expediente.json` y en `SEMANTICA_PRUEBAS` y `AVISOS_RECIENTES` de `campana.py`.
- Número de casos: no lo escribas a mano. Sácalo de los datos (`len(CASOS)`, `len(EVENTOS)` y 1) en estos lugares:
  - `interfaz/menu_pausa.py`: "Son cuatro casos".
  - `interfaz/expediente.py`: "Ocho casos, tres eras".
  - `interfaz/desenlace.py`: "la historia de los ocho casos".
  - `interfaz/finales.py`: `casos=8`.
  - `estrellas_total=11` en `campana.py`, y los respaldos `11` en `cooperativo.py` y `partida_multijugador.py`. Calcula el total según los casos y encargos reales.
  - CLAUDE.md: "4 casos en La Copa".

## 2. La historia del puente se contradice
Hoy el caso dice que el puente "sigue abierto hoy; mañana habrá mantenimiento parcial". Pero el Puente 1 empieza roto y bloqueado (`reparacion.py`, estado DAMAGED), y después del caso el equipo lo repara.
Reescribe la verdad del caso así: **Kael no rompió el puente. Se dañó por el desgaste y la lluvia, y el consejo lo cerró por seguridad hasta repararlo.** Kael solo propuso revisarlo. Cambia en ese sentido:
- `multijugador/campana.py` (CASOS, texto de conclusión) y el duplicado en `multijugador/mision.py` (línea ~249 y `PRUEBAS`). En las pruebas, nadie puede decir que "cruzó hoy sin problemas" ni que "hoy está abierto".
- `logica/conversaciones.py`, "Rumor Politico": el Mensajero dice "Crucé el puente esta mañana. Estaba abierto". Cámbialo por algo coherente con el cierre por seguridad.
- La ficha del expediente de `puente_norte` dice tipo "Acusación Personal", pero la clasificación correcta del caso es "Rumor Político". Unifica (sugerencia: tipo "Rumor sobre un aspirante" o "Rumor Político") sin tocar la ley ni la pena.

## 3. Testimonios de la tormenta
Los testimonios de "Suceso Natural" hablan de un rayo en el Mirador Alto que "destruyó el puente". Eso no corresponde al caso `tormenta` (alerta real o copia de un simulacro). Reescríbelos para ese caso **sin revelar cuál de las dos versiones salió en el sorteo**. Ejemplo: "Escuché la alerta en un tronco, pero no vi si el mensaje venía completo". Haz lo mismo con las REACCIONES y con el tema de `construir_mensajes_eco`.

## 4. Fugas entre eras
- **Indicadores en Ciudad Núcleo:** `multijugador/presentacion.py`, `ETIQUETAS` no tiene `"futuro"`, así que el HUD y la pantalla final del futuro muestran "Confianza del Consejo" y "Susurros Falsos". Agrega etiquetas propias. Sugerencia: Pensamiento crítico, Supervisión humana, Convivencia, Cuentas automáticas, Desinformación. Haz que `etiquetas_hud` y los respaldos de `partida_multijugador.py` y `desenlace.py` usen la era actual.
- **Aviso genérico:** `interfaz/partida_multijugador.py` ~985 dice "Acércate a una fuente, al caldero, al portal…" en las tres eras. Haz un texto por era (pantalla pública en el Presente, pantalla central y terminales en el Futuro).
- **Nombre del bot en La Copa:** `multijugador/partida_local.py`, `_nombre_bot` llama "Mateo · Mensajero" al bot. Mateo Ríos es del Presente. En La Copa debe ser "Mensajero".
- **Habilidad del Habitante:** `campana.py` HABILIDADES dice "Ve con un compañero a ver a Luma". Si el Habitante eligió a Luma, se habla a sí misma. Usa un texto que no nombre a Luma, o que cambie según la apariencia elegida.
- **Ícono del poder en el Futuro:** el HUD del poder (Q) solo se dibuja en La Copa, pero en el Futuro Q usa `futuro.habilidad`. Muestra en el Futuro su propio estado (`futuro.habilidades_usadas`) y su nombre (Lupa de Memoria, Impulso del Viento, Voz Comunitaria, Comunicado Público). En el Presente Q no hace nada: o le das una habilidad, o en la ayuda de controles dices que es de La Copa y Ciudad Núcleo.
- **Edificio con nombre del Presente en el Futuro:** en el Futuro el edificio se llama "Centro de Supervisión" (`logica/dimensiones.py`), pero `nucleo.py` (TEXTO_LLAVE), `conversaciones.py` (Corredor de Datos) y `menu_pausa.py` dicen "Centro de Verificación". Usa "Centro de Supervisión" en el Futuro.

## 5. Distrito Conecta
- **Tomás Red usa el sprite de una chica** ("Habitante conectada", `mundo/personajes.py`), y el caso `presente_foto` habla de "la Habitante conectada". **[DECISIÓN: Sebastián confirma el nombre]** Renombra al personaje con un nombre femenino. Propuesta: "Tania Red", descendiente de Tarek. Cambia el nombre en `PERSONAJES_DISTRITO`, `PERSONAJE_DE_ROL`, `TESTIMONIOS_PRESENTE`, las pistas de `presente.py`, `menu_pausa.py`, `nucleo/config.py` (CONTINUIDAD_PERSONAJES) y las pruebas. En `presente_foto`, nombra a la víctima: "Un perfil con la cara de Tania Red publica insultos…".
- **Ayuda de Distrito Conecta en `menu_pausa.py`:**
  - Dice que las pistas son de "Darío Veraz, Tomás Red y Ronaldo Vélez". Eso solo vale para el video. Hazlo genérico: "Habla con las personas marcadas…".
  - Dice "Verificar, Denunciar, Ignorar o Publicar". Las opciones reales son Verificar, Reportar, Dejar pendiente y Compartir (`presente.py`), y el resumen corto es `DECISION_CORTA` de `campana.py`. Usa los mismos cuatro nombres en la ayuda, el celular y el resumen.
- **Nota legal de `presente_video`** (`datos/casos_expediente.json`): dice "Es la misma conducta del rumor de La Copa". Sin el caso `ayuda`, La Copa es injuria y esto es calumnia. Cámbiala por: "En La Copa, el rumor sobre Kael era injuria; aquí se le atribuye un delito, por eso es calumnia". No toques leyes ni penas.
- Limpieza interna, sin cambio visible: la pista `respuesta_kael` de `presente.py` puede llamarse `agenda_ronaldo`. Hazlo solo si no rompe el protocolo ni las partidas guardadas; si no, déjala.

## 6. Final y créditos
- `interfaz/finales.py`: "{lider} guía al Consejo; NÚCLEO trabaja bajo supervisión humana" mezcla a Kael con el futuro. Cámbialo por un cierre de las tres eras. Sugerencia: "Kael guía al Consejo de La Copa, Ronaldo recupera su nombre y NÚCLEO trabaja bajo supervisión humana". Con Mira, igual.
- `interfaz/desenlace.py`: los créditos dicen "Los Guardianes de la Memoria". Lee el nombre del equipo de `datos/creditos.json` (agrega la clave `"equipo"`, vacía por ahora). Si está vacío, muestra solo "Estructuras de Datos 2".

## 7. Prueba de regresión nueva
Agrega `tests/test_coherencia_eras.py`:
- Ningún texto del Presente ni del Futuro (eventos, pistas, testimonios, ayuda de `menu_pausa`, etiquetas, epílogos del Presente y del Futuro, textos de `nucleo.py`) contiene nombres o palabras de La Copa. Reutiliza la expresión `COPA` de `tests/test_leyes_penas.py`, ampliada con "caldero", "tronco", "poción" y "tablilla".
- `ETIQUETAS` tiene las tres eras con las mismas claves que `INDICADORES_INICIALES`.
- Ningún texto de La Copa nombra personajes del Presente ni del Futuro.
- El total de estrellas y el número de casos mostrados coinciden con los datos.
- Las pruebas del puente no contienen "abierto hoy" ni "sin problemas".

## DOCKER
Si agregas un archivo que use el servidor, agrégalo a `Dockerfile.multijugador.dockerignore` (es una lista blanca). Simula el contexto de Docker con esa lista y arranca una sala con `python -m multijugador.servicio_internet`: debe responder `/health` y aceptar una partida con bots hasta el primer caso.

## Al terminar
Corre otra vez la suite completa y el benchmark. Reporta el antes y el después con números reales, la lista de archivos cambiados y cualquier punto que hayas dejado sin hacer.

Une en multijugador, corre las pruebas y avísame. No hagas push.
