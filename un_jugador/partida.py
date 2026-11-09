"""Bucle principal del modo un jugador."""

import json
import math
import os
import pygame
import sys
from audio.audio_manager import GestorAudio
from graficos.particulas import SistemaParticulas
from graficos.propagacion_visual import PropagacionVisual
from interfaz.boton import GrupoBotones
from interfaz.dialogo import ControladorDialogo
from interfaz.hud import HUDIndicadores
from interfaz.mensaje_privado import ControladorMensajePrivado
from interfaz.menu import MenuModal
from logica.conversaciones import construir_conversacion
from logica.conversaciones import construir_mensajes_eco
from logica.conversaciones import construir_respuesta_eco
from logica.dimensiones import DIMENSION_LA_COPA
from logica.dimensiones import DIMENSION_PRESENTE
from logica.dimensiones import EDIFICIOS_PRESENTE
from logica.logica_juego import EstadoJuego
from nucleo.rutas import RAIZ
from mundo.camara import actualizar_camara_mundo, posicion_pantalla_a_mundo
from mundo.creacion import crear_mundo
from mundo.grafo_aldea import _posicion_en_mapa, buscar_ruta_transmision
from mundo.jugador import (
    alternar_interactuable_cercano,
    buscar_interactuable_cercano,
    mover_jugador,
    reiniciar_jugador_en_casa,
)
from mundo.mapas import cargar_mapa_edificio, cargar_mapa_presente, cargar_mapa_principal
from mundo.npcs import actualizar_npcs_presentes
from mundo.personajes import (
    cargar_frames_idle_guardian,
    cargar_frames_tronco_eco,
    cargar_retrato_publicacion,
)
from nucleo.config import (
    ALTO,
    ANCHO,
    CENTRO_CALDERO,
    CREMA,
    DURACION_MINIMA_HISTORIA_DIMENSION_MS,
    DURACION_MINIMA_TUTORIAL_DIMENSION_MS,
    ESCENAS_CON_MAPA,
    ESCENA_ANALISIS,
    ESCENA_AYUDA,
    ESCENA_CELULAR,
    ESCENA_CLASIFICACION,
    ESCENA_CODICE,
    ESCENA_CONSECUENCIA,
    ESCENA_DIALOGO,
    ESCENA_ECO,
    ESCENA_FINAL,
    ESCENA_MAPA,
    ESCENA_MAPA_DESTINO,
    ESCENA_MENSAJE,
    ESCENA_PAUSA,
    ESCENA_RESULTADO,
    ESCENA_TABLILLA,
    ESCENA_TRANSICION_DIMENSION,
    ESCENA_TUTORIAL_DIMENSION,
    ESCENA_VISUAL,
    ESCENA_VOLUMEN,
    ESCENA_ZONA_EN_PROCESO,
    FPS,
    PAGINAS_CODICE,
)
from nucleo.recursos import (
    cargar_efecto_tablilla,
    cargar_fuente,
    cargar_icono_hud,
    cargar_imagen,
    cargar_spritesheet_frames,
    normalizar_ruta,
)
from un_jugador.codice import dibujar_codice, dibujar_tutorial_dimension
from un_jugador.dibujo_mapa import dibujar_mapa
from un_jugador.escenas import (
    dibujar_analisis_publicacion,
    dibujar_escena_dialogo,
    dibujar_escena_mensaje,
    dibujar_interfaz_eco,
    dibujar_transicion_dimension,
    rectangulos_opciones_mision,
)
from un_jugador.hud import (
    celular_disponible,
    dibujar_celular_feed,
    dibujar_mensaje_mapa,
    interaccion_en_mapa,
    rectangulos_selector_mision,
)
from un_jugador.tablilla import (
    accion_tablilla,
    construir_botones,
    construir_botones_clasificacion,
    determinar_resultado_final,
    dibujar_consecuencia_evento,
    dibujar_escena_tablilla,
    dibujar_final,
    dibujar_pociones,
    dibujar_pregunta_clasificacion,
    dibujar_resultado_evento,
    estado_caldero,
    iniciar_animacion_decision,
    reproducir_audio_clasificacion,
    sincronizar_audio_caldero,
)
from un_jugador.ventana import (
    convertir_mouse_a_lienzo,
    crear_ventana,
    presentar_lienzo,
    rect_lienzo_en_ventana,
)


def main():
    pygame.init()
    gestor_audio = GestorAudio(str(RAIZ))
    pantalla_completa = True
    ventana_maximizada = False
    pantalla = crear_ventana(pantalla_completa, ventana_maximizada)
    pygame.display.set_caption("Timeless Glitch")
    reloj = pygame.time.Clock()
    lienzo = pygame.Surface((ANCHO, ALTO))

    fuente_texto = cargar_fuente(22)
    fuente_categoria = cargar_fuente(13)
    fuente_boton = cargar_fuente(19)
    fuente_indicador = cargar_fuente(11)
    fuente_mapa = cargar_fuente(18)
    fuente_panel_titulo = cargar_fuente(16)
    fuente_panel = cargar_fuente(13)
    fuente_resultado = cargar_fuente(28)

    mapa, decoraciones, interacciones, hitboxes, guardian, mapas_dia = cargar_mapa_principal()
    frames_propagacion = cargar_spritesheet_frames(
        os.path.join("Animaciones Ambiente", "Destello.png"),
        cantidad=8,
    )
    if len(frames_propagacion) != 8:
        raise RuntimeError("No se pudo cargar el spritesheet Destello para la propagacion por puentes.")
    retratos_dialogo = {
        objeto["personaje"]: pygame.transform.scale(objeto["imagen"], (78, 78))
        for objeto in decoraciones
        if objeto["personaje"]
    }
    recursos = {
        "mapa": mapa,
        "mapas_dia": mapas_dia,
        "dimension": DIMENSION_LA_COPA,
        "frames_propagacion": frames_propagacion,
        "dia": 0,
        "decoraciones": decoraciones,
        "interacciones": interacciones,
        "hitboxes": hitboxes,
        "guardian": guardian,
        "assets_reparacion_puentes": {
            "puente_danado": cargar_imagen(
                os.path.join("Puentes", "Puente1Roto.png"),
                requerido=False,
            ),
            "puente_reparado": cargar_imagen(
                os.path.join("Puentes", "Puente1.png"),
                requerido=False,
            ),
            "efecto_reparacion": cargar_spritesheet_frames(
                os.path.join("Animaciones", "Efectos", "EfectoReparacion.png"),
                cantidad=8,
            ),
            "indicador_normal": cargar_imagen(
                os.path.join("Indicadores Puente", "Indicador.png"),
                (220, 220),
                requerido=False,
            ),
            "indicador_acierto": cargar_imagen(
                os.path.join("Indicadores Puente", "IndicadorAcierto.png"),
                (220, 220),
                requerido=False,
            ),
            "indicador_error": cargar_imagen(
                os.path.join("Indicadores Puente", "IndicadorError.png"),
                (220, 220),
                requerido=False,
            ),
            "materiales_spritesheet": cargar_imagen(
                os.path.join("Herramientas", "HerramientasReparación.png")
            ),
        },
        "iconos_habilidad": {
            "guardian": cargar_imagen(
                os.path.join("Iconos", "Habilidad", "ImpulsoVientRecarg.png"),
                (44, 44),
            ),
            "periodista": cargar_imagen(
                os.path.join("Iconos", "Habilidad", "ComunicadoPubActive.png"),
                (44, 44),
            ),
        },
        "guardian_walk_frames": {
            "abajo": cargar_spritesheet_frames(
                os.path.join("NPCS", "Guardian", "Fila 2. Guardián.png")
            ),
            "derecha": cargar_spritesheet_frames(
                os.path.join("NPCS", "Guardian", "Fila 3. Guardián.png")
            ),
            "arriba": cargar_spritesheet_frames(
                os.path.join("NPCS", "Guardian", "Fila 4. Guardián.png")
            ),
            "izquierda": cargar_spritesheet_frames(
                os.path.join("NPCS", "Guardian", "Fila 5. Guardián.png")
            ),
        },
        "guardian_idle_frames": cargar_frames_idle_guardian(),
        "frames_tronco_eco": cargar_frames_tronco_eco(),
        "guardian_talk_frames": cargar_spritesheet_frames(
            os.path.join("NPCS", "Guardian", "Guardian_hablando.png")
        ),
        "guardian_eco_frames": cargar_spritesheet_frames(
            os.path.join("NPCS", "Guardian", "Guardian_interaccion_ecos.png")
        ),
        "fondo_clasificacion": cargar_imagen("FondoClasificacion.png", (860, 505)),
        "panel_clasificacion": cargar_imagen("Cartel_decision.png", (840, 315)),
        "botones_clasificacion": {
            "rumor_politico": cargar_imagen("Rumor_politico.png", (180, 200)),
            "suceso_natural": cargar_imagen("Suceso_natural.png", (180, 200)),
            "acusacion_personal": cargar_imagen("Acusacion_personal.png", (180, 200)),
        },
        "tablilla": cargar_imagen("Tablilla.png", (460, 460)),
        "colgar": cargar_imagen("Colgar.png", (190, 127)),
        "consultar": cargar_imagen("Consultar.png", (190, 127)),
        "quemar": cargar_imagen("Quemar.png", (190, 127)),
        "ignorar": cargar_imagen("Ignorar.png", (190, 127)),
        "pergamino_mensaje": cargar_imagen("Mensaje_privado.png", (570, 410)),
        "fondo_feed_digital": cargar_imagen(
            os.path.join("Iconos", "Objetos varios", "FeedRedSocial.jpg"),
            (ANCHO, ALTO),
        ),
        "imagen_publicacion_aspirante": cargar_retrato_publicacion(),
        "pociones": {
            "colgar": cargar_imagen(os.path.join("Pociones", "pocion_amarilla.png"), (42, 42)),
            "consultar": cargar_imagen(os.path.join("Pociones", "pocion_azul.png"), (42, 42)),
            "quemar": cargar_imagen(os.path.join("Pociones", "pocion_roja.png"), (42, 42)),
            "ignorar": cargar_imagen(os.path.join("Pociones", "pocion_morada.png"), (42, 42)),
        },
        "efectos_decision": {
            "colgar": cargar_efecto_tablilla("Colgar_tablilla.png"),
            "consultar": cargar_efecto_tablilla("Consultar_tablilla.png"),
            "quemar": cargar_efecto_tablilla("Quemar_tablilla.png"),
            "ignorar": cargar_efecto_tablilla("Ignorar_tablilla.png"),
        },
        "final_positivo": cargar_imagen(os.path.join("Finales", "Final_positivo.jpeg"), (ANCHO, ALTO)),
        "final_negativo": cargar_imagen(os.path.join("Finales", "Game_over.jpeg"), (ANCHO, ALTO)),
        "fuente_texto": fuente_texto,
        "fuente_categoria": fuente_categoria,
        "fuente_boton": fuente_boton,
        "fuente_indicador": fuente_indicador,
        "fuente_mapa": fuente_mapa,
        "fuente_panel_titulo": fuente_panel_titulo,
        "fuente_panel": fuente_panel,
        "fuente_resultado": fuente_resultado,
    }

    iconos_hud = {
        "sabiduria": cargar_icono_hud("Barra_sabiduría.png"),
        "confianza_consejo": cargar_icono_hud("Barra_confianza.png"),
        "armonia": cargar_icono_hud("Barra_armonía.png"),
        "susurros_falsos": cargar_icono_hud("Barra_susurros_falsos.png"),
        "desinformación": cargar_icono_hud("Barra_desinformación.png"),
    }

    estado = EstadoJuego()
    mundo = crear_mundo(recursos)
    recursos["mundo"] = mundo
    estado.gestor_dimensiones.guardar_recursos(DIMENSION_LA_COPA, {
        clave: recursos[clave]
        for clave in (
            "mapa",
            "mapas_dia",
            "dia",
            "decoraciones",
            "interacciones",
            "hitboxes",
            "guardian",
        )
    })

    botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
    grupo_botones = GrupoBotones(botones)
    dialogos = ControladorDialogo(fuente_texto, fuente_panel_titulo, fuente_boton)
    mensajes = ControladorMensajePrivado(
        fuente_panel_titulo, fuente_panel, fuente_boton, recursos["pergamino_mensaje"]
    )
    hud = HUDIndicadores(fuente_indicador, iconos_hud)
    hud.establecer_etiquetas({
        "sabiduria": "Sabiduría",
        "confianza_consejo": "Confianza del Consejo",
        "armonia": "Armonía",
        "susurros_falsos": "Susurros Falsos",
        "desinformación": "Desinformación",
    })
    pausa = MenuModal(fuente_resultado, fuente_texto, fuente_boton)
    visual = MenuModal(fuente_resultado, fuente_texto, fuente_boton)
    volumen = MenuModal(fuente_resultado, fuente_texto, fuente_boton)
    volumen.conectar_audio(gestor_audio)
    volumen.configurar([("volver", "Volver")])
    ayuda = MenuModal(fuente_resultado, fuente_texto, fuente_boton)
    fondo_menu = cargar_imagen(os.path.join("Fondos", "Fondo_pausa.png"))
    for menu in (pausa, visual, volumen, ayuda):
        menu.establecer_fondo(fondo_menu, 0.6)

    def configurar_menu_visual():
        visual.configurar([
            ("modo_pantalla_completa", "Pantalla completa"),
            ("modo_ventana_maximizada", "Ventana maximizada"),
            ("modo_ventana_normal", "Ventana normal"),
            ("volver", "Volver"),
        ])
    conversaciones = {
        "Kael": {"personaje": "Kael", "texto": "Quiero conocer qué dicen los habitantes antes de responder.", "respuestas": []},
        "Mira": {"personaje": "Mira", "texto": "Guardián, circula un rumor sobre el Puente Norte.", "respuestas": []},
        "Tarek": {"personaje": "Tarek", "texto": "Escuché golpes extraños en el Tronco de Ecos.", "respuestas": []},
        "Luma": {"personaje": "Luma", "texto": "Algunas tablillas están llegando sin una fuente clara.", "respuestas": []},
        "Darek": {"personaje": "Darek", "texto": "Vi pasar un eco entre plataformas. Puede ayudarnos a seguir la ruta del rumor.", "respuestas": []},
        "Mensajero": {"personaje": "Mensajero", "texto": "Puedo llevar un mensaje privado entre plataformas. La ruta más corta no siempre es la más segura.", "respuestas": ["Entrega el mensaje"]},
        "Guardián": {"personaje": "Guardián", "texto": "Escucha a la aldea y revisa la tablilla antes de decidir qué hacer con ella.", "respuestas": ["Consultar tablilla"]},
        "Naira": {"personaje": "Naira", "texto": "Las plataformas están conectadas por puentes; cuidemos la confianza de quienes viven aquí.", "respuestas": ["Consultar tablilla"]},
        "Sabio de las Raíces": {
            "personaje": "Sabio de las Raíces",
            "texto": "Los ecos del tronco guardan lo que la aldea comparte. Escucha antes de decidir.",
            "respuestas": [],
        },
        "Darío Veraz": {
            "personaje": "Darío Veraz",
            "texto": "Heredé el método de Odran: separo lo observado de lo supuesto. No hay archivo fuente; revisemos el contexto.",
            "respuestas": [],
        },
        "Ronaldo Vélez": {
            "personaje": "Ronaldo Vélez",
            "texto": "Soy descendiente de Kael. La agenda me sitúa en un debate, no en el lugar de la imagen.",
            "respuestas": [],
        },
        "Tomás Red": {
            "personaje": "Tomás Red",
            "texto": "Como Tarek, suelo estar conectado a lo que comparte la comunidad; vi el post, no el hecho.",
            "respuestas": [],
        },
        "Lía Nova": {
            "personaje": "Lía Nova",
            "texto": "Luma contaba historias en la aldea; yo las difundo como influencer, pero el alcance no confirma su verdad.",
            "respuestas": [],
        },
        "Mateo Ríos": {
            "personaje": "Mateo Ríos",
            "texto": "Como el antiguo Mensajero, conecto a la gente por la ciudad. Llevaré una corrección con datos confirmados.",
            "respuestas": [],
        },
    }
    dialogos_posteriores = {
        nombre: {
            "personaje": nombre,
            "texto": f"{nombre} ya compartió lo que sabe por ahora.",
            "respuestas": [],
        }
        for nombre in conversaciones
    }
    estado_personajes = {
        personaje["personaje"]: {
            "dialogo_inicial": conversaciones.get(personaje["personaje"], {}),
            "dialogo_posterior": dialogos_posteriores.get(personaje["personaje"], {}),
            "dialogos_condicionados": {},
            "confianza": 0,
            "conversacion_vista": False,
            "disponible": personaje.get("activo", True),
            "plataforma_actual": personaje.get("plataforma", ""),
        }
        for personaje in mundo["personajes"]
    }
    conversaciones_vistas = set()
    recursos["conversaciones_vistas"] = conversaciones_vistas
    personaje_dialogo_activo = None
    clave_dialogo_activo = None

    def plataforma_cercana(posicion):
        return min(
            mundo["grafo_fisico"].plataformas.values(),
            key=lambda plataforma: math.dist(
                posicion, _posicion_en_mapa(plataforma)
            ),
        )["id"]

    def registrar_transmision(transmisor, receptor, medio, origen_pos, destino_pos):
        propagacion = estado.propagacion_actual
        grafo = mundo["grafo_fisico"]
        if not grafo.plataformas:
            print(
                f"[Grafo] No hay nodos configurados para {DIMENSION_PRESENTE}; "
                "se omite esta propagación."
            )
            return []
        origen_id = plataforma_cercana(origen_pos)
        destino_id = plataforma_cercana(destino_pos)
        resultado_ruta = buscar_ruta_transmision(
            grafo,
            origen_id,
            destino_id,
        )
        if resultado_ruta is None:
            return []
        ruta, puente_ids = resultado_ruta
        if propagacion is not None:
            propagacion.registrar_transmision(
                transmisor,
                receptor,
                ruta,
                medio,
                origen_id,
                destino_id,
            )

        tipo_visual = "informacion_normal"
        if propagacion:
            tipo_visual = {
                "verificada": "informacion_verificada",
                "rumor": "rumor",
                "falsa": "informacion_falsa",
            }.get(propagacion.estado_verificacion, tipo_visual)
        evento_visual = {
            "tipo": "propagacion",
            "origen": origen_id,
            "destino": destino_id,
            "ruta": list(ruta),
            "clase": tipo_visual,
            "medio": medio,
            "transmisor": transmisor,
            "receptor": receptor,
        }
        if len(ruta) > 1:
            visual = PropagacionVisual(
                origen_id,
                destino_id,
                ruta,
                [_posicion_en_mapa(grafo.plataformas[nodo]) for nodo in ruta],
                puente_ids,
                recursos["frames_propagacion"],
                tipo=tipo_visual,
            )
            mundo["propagaciones_visuales"].append(visual)
        registrar_evento(evento_visual)
        return ruta

    def difundir_resultado_tablilla():
        propagacion = estado.propagacion_actual
        resultado = estado.resultado_evento_actual()
        if not propagacion or not resultado:
            return
        camino = resultado.get("camino", [])
        if not camino:
            return

        accion = accion_tablilla(camino[0])
        texto_resultado = resultado.get("resultado", "")
        propagacion.registrar_decision(accion or camino[0], resultado=texto_resultado)
        texto_normalizado = normalizar_ruta(texto_resultado)
        if accion == "consultar":
            refutada = (
                camino[-1].casefold() == "no"
                or "exagerado" in texto_normalizado
                or "rumor falso" in texto_normalizado
                or "no es cierto" in texto_normalizado
            )
            confirmada = (
                camino[-1].casefold() == "si"
                or "verdad confirmada" in texto_normalizado
                or ("confirma" in texto_normalizado and not refutada)
            )
            if refutada or confirmada:
                propagacion.registrar_verificacion(confirmada and not refutada)
        elif accion == "ignorar":
            propagacion.marcar_como_rumor()
        elif accion == "colgar" and propagacion.tipo == "rumor":
            propagacion.marcar_como_rumor()

        if accion not in ("colgar", "consultar"):
            return
        origen = mundo["jugador"]["pies"].center
        for personaje in mundo["personajes"]:
            if not personaje.get("activo", True):
                continue
            registrar_transmision(
                mundo["jugador"]["nombre"],
                personaje["personaje"],
                "tablilla",
                origen,
                personaje["rect"].center,
            )

    def abrir_dialogo_personaje(nombre):
        nonlocal personaje_dialogo_activo, clave_dialogo_activo
        personaje_dialogo_activo = nombre
        mundo["npc_en_dialogo"] = nombre
        jugador = mundo["jugador"]
        jugador["en_movimiento"] = False
        jugador["estado_visual"] = "hablar"
        jugador["indice_frame"] = 0
        objetivo = next(
            (personaje for personaje in mundo["personajes"] if personaje["personaje"] == nombre),
            None,
        )
        estado_personajes.setdefault(nombre, {
            "dialogo_inicial": conversaciones.get(nombre, {}),
            "dialogo_posterior": dialogos_posteriores.get(nombre, {}),
            "dialogos_condicionados": {},
            "confianza": 0,
            "conversacion_vista": False,
            "disponible": True,
            "plataforma_actual": "",
        })
        if objetivo:
            jugador["direccion"] = (
                "izquierda" if objetivo["rect"].centerx < jugador["pies"].centerx else "derecha"
            )
        estado_personaje = estado_personajes.get(nombre, {})
        dialogo, clave_dialogo_activo = construir_conversacion(
            nombre, estado, conversaciones_vistas
        )
        dialogos.iniciar(dialogo, retratos_dialogo)
        if objetivo:
            registrar_transmision(
                nombre,
                mundo["jugador"]["nombre"],
                "conversacion",
                objetivo["rect"].center,
                jugador["pies"].center,
            )

    def agregar_publicacion_feed(evento):
        if not celular_disponible(estado):
            return
        tipo = evento.get("tipo", "actividad")
        titulos = {
            "cambio_dimension": "Llegada al Distrito Conecta",
            "examinar_publicacion": "Nueva publicación en revisión",
            "correccion_publicada": "Corrección difundida",
            "correccion_recibida": "La comunidad recibió la corrección",
            "interaccion_personaje": "Conversación con la comunidad",
            "usar_caldero": "Decisión sobre una tablilla",
            "usar_eco_tronco": "Mensaje compartido por un Eco",
            "decision_tablilla": "Decisión sobre un rumor",
            "clasificacion_publicacion": "Clasificación de imagen",
            "decision_mision": "Decisión sobre la publicación",
            "clasificacion_evento": "Clasificación de un evento",
        }
        titulo = titulos.get(tipo, tipo.replace("_", " ").capitalize())
        detalle = evento.get("texto")
        if tipo == "decision_tablilla":
            nombres_decisiones = {
                "colgar": "difundir",
                "consultar": "consultar",
                "quemar": "quemar",
                "ignorar": "ignorar",
            }
            detalle = (
                "Elegiste "
                + nombres_decisiones.get(evento.get("decision"), "resolver")
                + " la tablilla."
            )
        elif tipo == "decision_mision":
            nombres_decisiones = {
                "revisar_fuente": "revisar la fuente",
                "comparar_evidencia": "comparar testimonios y contexto",
                "clasificar_ia": "imagen generada por IA",
                "clasificar_real": "imagen auténtica",
                "dejar_pendiente": "dejarla pendiente",
                "reportar": "reportarla",
                "verificar": "verificarla antes de compartir",
            }
            detalle = (
                "Decidiste "
                + nombres_decisiones.get(evento.get("decision"), "continuar investigando")
                + "."
            )
        elif tipo == "clasificacion_publicacion":
            detalle = f"Clasificaste la imagen como {evento.get('clasificacion', 'sin especificar')}."
        elif tipo == "clasificacion_evento":
            resultado = "correctamente" if evento.get("acerto") else "de forma incorrecta"
            detalle = (
                f"Clasificaste el evento como {evento.get('clasificacion', 'sin especificar')} "
                f"{resultado}."
            )
        elif tipo == "correccion_publicada":
            detalle = "La corrección se difundió con las pistas reunidas."
        elif tipo == "interaccion_personaje":
            detalle = f"Conversaste con {evento.get('objetivo_id', 'un personaje').replace('_', ' ')}."
        elif tipo == "cambio_dimension":
            detalle = "La historia continúa en el presente."
        if not detalle:
            detalle = f"Se registró la acción: {tipo.replace('_', ' ')}."
        feed = recursos.setdefault("feed_digital", [])
        feed.append({
            "titulo": titulo,
            "texto": detalle,
            "tipo": tipo,
        })
        del feed[:-20]

    def registrar_evento(evento):
            eventos_serializables.append(evento)
            agregar_publicacion_feed(evento)
            print(f"[evento local] {json.dumps(evento, ensure_ascii=False)}")

    def cargar_dimension_presente():
        nonlocal mundo, interactuable_cercano, distancia_interactuable
        nonlocal tiempo_particulas_ambientales
        gestor_dimensiones = estado.gestor_dimensiones
        recursos_presente = gestor_dimensiones.recursos_por_dimension.get(
            DIMENSION_PRESENTE
        )
        if recursos_presente is None:
            recursos_presente = cargar_mapa_presente(
                gestor_dimensiones.obtener_configuracion(DIMENSION_PRESENTE)
            )
        if recursos_presente is None:
            gestor_dimensiones.cancelar_transicion()
            return False

        estado.guardar_progreso_dimension()
        gestor_dimensiones.guardar_recursos(DIMENSION_PRESENTE, recursos_presente)
        gestor_dimensiones.activar_dimension(DIMENSION_PRESENTE)
        recursos.update(recursos_presente)
        recursos["dimension"] = DIMENSION_PRESENTE
        recursos["dia"] = 0
        retratos_dialogo.update({
            objeto["personaje"]: pygame.transform.scale(objeto["imagen"], (78, 78))
            for objeto in recursos_presente["decoraciones"]
            if objeto.get("personaje")
        })
        hud.establecer_etiquetas({
            "sabiduria": "Alfabetización digital",
            "confianza_consejo": "Confianza pública",
            "armonia": "Convivencia digital",
            "susurros_falsos": "Contenido viral dudoso",
            "desinformación": "Desinformación",
        })
        recursos["mensaje_dimension"] = (
            "Acércate a una pantalla pública y pulsa E para examinar la publicación."
            if any(
                objeto["tipo"] == "pantalla_publica"
                or objeto["accion"] == "examinar_publicacion"
                for objeto in recursos_presente["interacciones"]
            )
            else "Añade una pantalla pública desde el editor de hitboxes para iniciar la misión."
        )
        mundo = crear_mundo(recursos)
        mundo["dimension"] = DIMENSION_PRESENTE
        mundo["spawn_presente"] = recursos_presente["spawn_dimension"]
        recursos["mundo"] = mundo
        estado.iniciar_mision_presente()
        if not recursos.get("publicacion_inicial_feed_creada"):
            feed = recursos.setdefault("feed_digital", [])
            feed.append({
                "titulo": "Publicación viral sobre Ronaldo",
                "texto": (
                    "Una imagen acusa a Ronaldo, pero su origen no está confirmado. "
                    "Investiga antes de compartirla."
                ),
                "tipo": "publicacion_sospechosa",
            })
            recursos["publicacion_inicial_feed_creada"] = True
        estado.guardar_progreso_dimension()
        sistema_particulas.configurar_dimension(DIMENSION_PRESENTE)
        sistema_particulas.particulas.clear()
        tiempo_particulas_ambientales = 0
        interactuable_cercano, distancia_interactuable = buscar_interactuable_cercano(
            mundo["jugador"],
            mundo,
        )

        musica = gestor_dimensiones.obtener_configuracion(DIMENSION_PRESENTE)["musica"]
        if not gestor_audio.reproducir_musica(musica, en_bucle=True, fade_ms=900):
            print(
                f"[Audio] No existe {musica}; "
                "se conserva temporalmente el ambiente actual."
            )
            gestor_audio.reproducir_musica("ambiente", en_bucle=True, fade_ms=900)
        return True

    def entrar_edificio(edificio_id, mundo_actual, estado_actual):
        nonlocal mundo, interactuable_cercano, distancia_interactuable
        if estado_actual.dimension_actual != DIMENSION_PRESENTE:
            recursos["mensaje_dimension"] = "Los edificios solo se pueden abrir en el presente."
            return False
        if mundo_actual.get("edificio_interior"):
            return False
        edificio = EDIFICIOS_PRESENTE.get(edificio_id)
        if edificio is None:
            recursos["mensaje_dimension"] = "Esta puerta no tiene un edificio configurado."
            return False
        try:
            recursos_interior = cargar_mapa_edificio(edificio_id)
        except (FileNotFoundError, ValueError, json.JSONDecodeError, pygame.error) as error:
            print(f"[Edificios] No se pudo abrir {edificio['nombre']}: {error}")
            recursos["mensaje_dimension"] = (
                f"No se puede entrar a {edificio['nombre']}: falta configurar su interior."
            )
            return False

        rect_mapa_exterior = recursos.get("rect_mapa") or pygame.Rect(0, 0, ANCHO, ALTO)
        rx, ry = edificio["spawn_exterior"]
        posicion_salida = (
            rect_mapa_exterior.x + round(rx * rect_mapa_exterior.width),
            rect_mapa_exterior.y + round(ry * rect_mapa_exterior.height),
        )
        recursos_anteriores = {
            clave: (clave in recursos, recursos.get(clave))
            for clave in recursos_interior
        }
        recursos["contexto_edificio"] = {
            "mundo_exterior": mundo_actual,
            "recursos_exteriores": recursos_anteriores,
            "posicion_salida": posicion_salida,
        }
        recursos.update(recursos_interior)
        mundo = crear_mundo(recursos)
        mundo["dimension"] = DIMENSION_PRESENTE
        mundo["edificio_interior"] = edificio_id
        recursos["mundo"] = mundo
        recursos["mensaje_dimension"] = (
            f"{edificio['nombre']}: {edificio['funcion']}. "
            "La flecha amarilla marca la salida; pulsa E."
        )
        interactuable_cercano, distancia_interactuable = buscar_interactuable_cercano(
            mundo["jugador"],
            mundo,
        )
        registrar_evento({
            "tipo": "entrada_edificio",
            "edificio_id": edificio_id,
        })
        return True

    def salir_edificio(mundo_actual, estado_actual):
        nonlocal mundo, interactuable_cercano, distancia_interactuable
        contexto = recursos.get("contexto_edificio")
        if estado_actual.dimension_actual != DIMENSION_PRESENTE or not contexto:
            return False

        for clave, (existia, valor) in contexto["recursos_exteriores"].items():
            if existia:
                recursos[clave] = valor
            else:
                recursos.pop(clave, None)
        mundo = contexto["mundo_exterior"]
        recursos["mundo"] = mundo
        jugador = mundo["jugador"]
        jugador["pies"].center = contexto["posicion_salida"]
        jugador["rect"].midbottom = jugador["pies"].midbottom
        jugador["posicion_x"] = float(jugador["pies"].x)
        jugador["posicion_y"] = float(jugador["pies"].y)
        jugador["en_movimiento"] = False
        jugador["estado_visual"] = "idle"
        jugador["direccion"] = "arriba"
        mundo["interaccion_seleccionada"] = None
        recursos.pop("contexto_edificio", None)
        recursos["mensaje_dimension"] = "Volviste a la calle del Distrito Conecta."
        interactuable_cercano, distancia_interactuable = buscar_interactuable_cercano(
            mundo["jugador"],
            mundo,
        )
        registrar_evento({
            "tipo": "salida_edificio",
            "edificio_id": mundo_actual.get("edificio_interior", "edificio"),
        })
        return True

    def abrir_publicacion(interaccion):
        nonlocal escena, indice_opcion_mision, mensaje_mision
        jugador = mundo["jugador"]
        jugador["en_movimiento"] = False
        jugador["estado_visual"] = "idle"
        jugador["indice_frame"] = 0
        indice_opcion_mision = 0
        mensaje_mision = ""
        estado.mision_presente["publicacion_examinada"] = True
        if estado.mision_presente["estado"] == "bloqueada":
            estado.iniciar_mision_presente()
        estado.guardar_progreso_dimension()
        escena = ESCENA_ANALISIS
        registrar_evento({
            "tipo": "examinar_publicacion",
            "dimension": DIMENSION_PRESENTE,
            "objeto_id": interaccion.get("id", "pantalla_publica"),
            "actor_id": jugador["id"],
            "mision": estado.mision_actual,
        })

    def procesar_opcion_mision(indice):
        nonlocal escena, mensaje_mision
        decisiones = (
            "revisar_fuente",
            "comparar_evidencia",
            "clasificar_ia",
            "clasificar_real",
            "dejar_pendiente",
            "reportar",
            "verificar",
        )
        if estado.mision_presente["estado"] == "completada":
            return
        if indice < 0 or indice >= len(decisiones):
            raise ValueError(f"Opción de misión inválida: {indice}")
        decision = decisiones[indice]
        if not estado.resolver_mision_presente(decision):
            faltantes = [
                pista.replace("_", " ")
                for pista in estado.PISTAS_PARA_VERIFICAR
                if pista not in estado.mision_presente["pistas"]
            ]
            mensaje_mision = (
                "Investiga antes de verificar o clasificar. Reúne estas pistas: "
                + ", ".join(faltantes)
                + "."
            )
            return
        tipo_evento = (
            "clasificacion_publicacion"
            if decision in ("clasificar_ia", "clasificar_real")
            else "decision_mision"
        )
        registrar_evento({
            "tipo": tipo_evento,
            "dimension": DIMENSION_PRESENTE,
            "mision": estado.mision_actual,
            "decision": decision,
            "clasificacion": (
                "imagen generada por IA"
                if decision == "clasificar_ia"
                else "imagen auténtica"
                if decision == "clasificar_real"
                else None
            ),
            "evidencias": list(estado.mision_presente["pistas"]),
        })
        if decision in ("revisar_fuente", "comparar_evidencia"):
            mensaje_mision = (
                "No se identifica una fuente original."
                if decision == "revisar_fuente"
                else "El contexto disponible no confirma la acusación."
            )
            return
        if decision in ("clasificar_ia", "clasificar_real"):
            mensaje_mision = (
                "¡Correcto! La evidencia confirma una imagen generada por IA."
                if estado.mision_presente.get("clasificacion_correcta")
                else "La imagen sí fue generada por IA. La clasificación incorrecta afectó tus indicadores."
            )
            recursos["mensaje_dimension"] = mensaje_mision
            return
        if decision == "verificar":
            recursos["mensaje_dimension"] = (
                "La publicación está verificada. Pulsa Q para difundir la corrección."
            )
        mundo["jugador"]["estado_visual"] = "idle"
        escena = ESCENA_MAPA

    def difundir_correccion_publica():
        if (
            estado.dimension_actual != DIMENSION_PRESENTE
            or estado.mision_presente.get("decision") not in ("verificar", "clasificar_ia")
            or (
                estado.mision_presente.get("decision") == "clasificar_ia"
                and not estado.mision_presente.get("clasificacion_correcta")
            )
            or estado.mision_presente.get("correccion_difundida")
        ):
            return False

        habilidad = mundo.get("habilidad")
        if habilidad is None or not habilidad.activar():
            return False

        registrar_evento({
            "tipo": "correccion_publicada",
            "actor_id": mundo["jugador"]["id"],
            "mision": estado.mision_actual,
            "evidencias": list(estado.mision_presente["pistas"]),
            "canal": "comunicado_publico",
        })
        for personaje in mundo["personajes"]:
            if not personaje.get("activo", True):
                continue
            registrar_evento({
                "tipo": "correccion_recibida",
                "actor_id": mundo["jugador"]["id"],
                "objetivo_id": personaje["id"],
                "evidencias": list(estado.mision_presente["pistas"]),
            })
            if personaje.get("rect"):
                sistema_particulas.emitir(*personaje["rect"].center, 5)

        estado.mision_presente["correccion_difundida"] = True
        estado.guardar_progreso_dimension()
        recursos["mensaje_dimension"] = (
            "Corrección difundida: se aclara la publicación sin acusar a nadie."
        )
        return True

    def iniciar_transicion_presente():
        nonlocal escena, tiempo_transicion_dimension, dimension_presente_cargada
        if not estado.juego_terminado():
            return False
        gestor_dimensiones = estado.gestor_dimensiones
        gestor_dimensiones.desbloquear_dimension(DIMENSION_PRESENTE)
        estado.guardar_progreso_dimension()
        evento = gestor_dimensiones.iniciar_transicion(DIMENSION_PRESENTE)
        if evento is None:
            return False
        registrar_evento(evento)
        tiempo_transicion_dimension = 0
        dimension_presente_cargada = False
        mundo["jugador"]["en_movimiento"] = False
        escena = ESCENA_TRANSICION_DIMENSION
        return True

    def saltar_a_dimension_siguiente():
        nonlocal escena, tiempo_tutorial_dimension
        if estado.dimension_actual != DIMENSION_LA_COPA:
            return False

        gestor_dimensiones = estado.gestor_dimensiones
        gestor_dimensiones.desbloquear_dimension(DIMENSION_PRESENTE)
        if gestor_dimensiones.iniciar_transicion(DIMENSION_PRESENTE) is None:
            return False
        if not cargar_dimension_presente():
            recursos["error_dimension"] = (
                "No se pudo cargar Distrito Conecta. La dimensión actual sigue disponible."
            )
            escena = ESCENA_ZONA_EN_PROCESO
            return False

        tiempo_tutorial_dimension = DURACION_MINIMA_TUTORIAL_DIMENSION_MS
        escena = ESCENA_MAPA
        return True

    def usar_portal_temporal():
        if (
            estado.dimension_actual == DIMENSION_LA_COPA
            and estado.juego_terminado()
            and DIMENSION_PRESENTE in estado.dimensiones_desbloqueadas
        ):
            return iniciar_transicion_presente()
        recursos["mensaje_dimension"] = (
            "El portal se abrirá al completar La Copa."
            if estado.dimension_actual == DIMENSION_LA_COPA
            else "No hay otra dimensión disponible desde aquí."
        )
        return False

    def abrir_caldero():
            if estado.evento_resuelto():
                escena_actual = ESCENA_RESULTADO if estado.evento_clasificado() else ESCENA_CONSECUENCIA
                return escena_actual
            opciones = estado.opciones_actuales()
            botones_locales = construir_botones(opciones, recursos, fuente_boton)
            botones.clear()
            botones.extend(botones_locales)
            grupo_botones.reemplazar(botones)
            return ESCENA_TABLILLA

    nombres_contacto = list(dict.fromkeys(
        personaje["personaje"]
        for personaje in mundo["personajes"]
        if personaje["personaje"] != "Guardián"
        and estado_personajes.get(personaje["personaje"], {}).get("disponible", True)
    ))
    mensajes_eco = construir_mensajes_eco(estado)
    eco_ui = {"destinatario": 0, "mensaje": 0, "respuesta": ""}
    eventos_serializables = []
    sistema_particulas = SistemaParticulas(ANCHO, ALTO)
    sistema_particulas.emitir(*CENTRO_CALDERO, 24)
    depuracion_activa = False
    tiempo_particulas_ambientales = 0
    tiempo_transicion_dimension = 0
    dimension_presente_cargada = False
    indice_opcion_mision = 0
    indice_pagina_codice = 0
    mensaje_mision = ""
    tiempo_tutorial_dimension = 0
    estado_caldero_efectos = estado_caldero(estado)
    usos_pociones = {"colgar": 1, "consultar": 1, "quemar": 1, "ignorar": 1}
    pocion_animacion = None
    escena = ESCENA_TUTORIAL_DIMENSION
    escena_anterior = ESCENA_MAPA
    gestor_audio.al_cambiar_escena(None, escena)
    escena_audio_anterior = escena
    estado_caldero_anterior = estado_caldero(estado)
    estado_caldero_actual = estado_caldero_anterior
    interactuable_cercano, distancia_interactuable = buscar_interactuable_cercano(
        mundo["jugador"], mundo
    )

    corriendo = True
    cursor_actual = None
    while corriendo:
        delta_ms = reloj.tick(FPS)
        delta_segundos = delta_ms / 1000
        habilidad_jugador = mundo.get("habilidad")
        if habilidad_jugador:
            habilidad_jugador.actualizar(delta_ms)
        if escena in ESCENAS_CON_MAPA:
            for propagacion_visual in mundo["propagaciones_visuales"]:
                propagacion_visual.actualizar(delta_ms)
            mundo["propagaciones_visuales"] = [
                propagacion_visual
                for propagacion_visual in mundo["propagaciones_visuales"]
                if propagacion_visual.activa
            ]
        sistema_particulas.actualizar(delta_ms)
        tiempo_particulas_ambientales += delta_ms
        if tiempo_particulas_ambientales >= 850:
            tiempo_particulas_ambientales %= 850
            sistema_particulas.emitir(ANCHO // 2, ALTO // 2 - 32, 4)
            sistema_particulas.emitir(*CENTRO_CALDERO, 4)
        rect_lienzo = rect_lienzo_en_ventana(pantalla.get_size())
        mouse_pos = convertir_mouse_a_lienzo(pygame.mouse.get_pos(), rect_lienzo)

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                corriendo = False
            elif evento.type == pygame.VIDEORESIZE:
                if not pantalla_completa:
                    pantalla = pygame.display.set_mode(evento.size, pygame.RESIZABLE)
            elif evento.type == pygame.KEYDOWN and (
                evento.key == pygame.K_F11
                or (evento.key == pygame.K_RETURN and getattr(evento, "mod", 0) & pygame.KMOD_ALT)
            ):
                pantalla_completa = not pantalla_completa
                pantalla = crear_ventana(pantalla_completa, ventana_maximizada)
                if escena == ESCENA_VISUAL:
                    configurar_menu_visual()
            elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_F3:
                depuracion_activa = not depuracion_activa
            elif (
                evento.type == pygame.KEYDOWN
                and evento.key == pygame.K_F1
                and estado.dimension_actual == DIMENSION_LA_COPA
                and escena not in (
                    ESCENA_FINAL,
                    ESCENA_TRANSICION_DIMENSION,
                    ESCENA_ZONA_EN_PROCESO,
                )
            ):
                saltar_a_dimension_siguiente()
            elif escena == ESCENA_CELULAR and evento.type == pygame.KEYDOWN and evento.key in (
                pygame.K_c,
                pygame.K_ESCAPE,
            ):
                escena = ESCENA_MAPA
            elif escena == ESCENA_CODICE and evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_j, pygame.K_ESCAPE):
                    escena = ESCENA_MAPA
                elif evento.key in (pygame.K_1, pygame.K_2):
                    if indice_pagina_codice == 0:
                        recursos["mision_objetivo_seleccionada"] = (
                            "principal" if evento.key == pygame.K_1 else "secundaria"
                        )
                    else:
                        indice_pagina_codice = evento.key - pygame.K_1
                elif evento.key in (pygame.K_LEFT, pygame.K_a):
                    indice_pagina_codice = (
                        indice_pagina_codice - 1
                    ) % len(PAGINAS_CODICE)
                elif evento.key in (pygame.K_RIGHT, pygame.K_d):
                    indice_pagina_codice = (
                        indice_pagina_codice + 1
                    ) % len(PAGINAS_CODICE)
                elif evento.key == pygame.K_3:
                    indice_pagina_codice = 2
            elif escena == ESCENA_CODICE and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if indice_pagina_codice == 0:
                    posicion = convertir_mouse_a_lienzo(evento.pos, rect_lienzo)
                    for rect, mision in zip(
                        rectangulos_selector_mision(),
                        ("principal", "secundaria"),
                    ):
                        if rect.collidepoint(posicion):
                            recursos["mision_objetivo_seleccionada"] = mision
                            break
            elif escena == ESCENA_TUTORIAL_DIMENSION and evento.type == pygame.KEYDOWN:
                if tiempo_tutorial_dimension >= DURACION_MINIMA_TUTORIAL_DIMENSION_MS:
                    escena = ESCENA_MAPA
            elif (
                escena == ESCENA_MAPA
                and evento.type == pygame.KEYDOWN
                and evento.key == pygame.K_c
                and celular_disponible(estado)
            ):
                escena = ESCENA_CELULAR
            elif escena == ESCENA_MAPA and evento.type == pygame.KEYDOWN and evento.key == pygame.K_j:
                indice_pagina_codice = 0
                escena = ESCENA_CODICE
            elif escena == ESCENA_TRANSICION_DIMENSION:
                if (
                    evento.type == pygame.KEYDOWN
                    and dimension_presente_cargada
                    and tiempo_transicion_dimension >= DURACION_MINIMA_HISTORIA_DIMENSION_MS
                ):
                    tiempo_tutorial_dimension = 0
                    escena = ESCENA_TUTORIAL_DIMENSION
            elif escena == ESCENA_ANALISIS:
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE:
                        escena = ESCENA_MAPA
                        mundo["jugador"]["estado_visual"] = "idle"
                    elif estado.mision_presente["estado"] != "completada":
                        if evento.key in (pygame.K_UP, pygame.K_DOWN):
                            paso = -1 if evento.key == pygame.K_UP else 1
                            indice_opcion_mision = (
                                indice_opcion_mision + paso
                            ) % len(rectangulos_opciones_mision())
                        elif evento.key in (
                            pygame.K_1, pygame.K_2, pygame.K_3,
                                pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7,
                        ):
                            procesar_opcion_mision(evento.key - pygame.K_1)
                        elif evento.key in (
                            pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE,
                        ):
                            procesar_opcion_mision(indice_opcion_mision)
                elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    posicion = convertir_mouse_a_lienzo(evento.pos, rect_lienzo)
                    for indice, rect in enumerate(rectangulos_opciones_mision()):
                        if (
                            rect.collidepoint(posicion)
                            and estado.mision_presente["estado"] != "completada"
                        ):
                            indice_opcion_mision = indice
                            procesar_opcion_mision(indice)
                            break
            elif escena == ESCENA_ECO and evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    escena = ESCENA_MAPA
                    eco_ui["respuesta"] = ""
                    mundo["jugador"]["estado_visual"] = "idle"
                elif eco_ui["respuesta"] and evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    escena = ESCENA_MAPA
                    eco_ui["respuesta"] = ""
                    mundo["jugador"]["estado_visual"] = "idle"
                elif not eco_ui["respuesta"] and nombres_contacto:
                    if evento.key in (pygame.K_UP, pygame.K_DOWN):
                        paso = -1 if evento.key == pygame.K_UP else 1
                        eco_ui["destinatario"] = (eco_ui["destinatario"] + paso) % len(nombres_contacto)
                    elif evento.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        paso = -1 if evento.key == pygame.K_LEFT else 1
                        eco_ui["mensaje"] = (eco_ui["mensaje"] + paso) % len(mensajes_eco)
                    elif evento.key in (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER):
                        tronco = interactuable_cercano
                        receptor = nombres_contacto[eco_ui["destinatario"]]
                        mensaje_id, texto_mensaje = mensajes_eco[eco_ui["mensaje"]]
                        registrar_evento({
                            "tipo": "eco_tronco",
                            "emisor_id": mundo["jugador"]["id"],
                            "receptor_id": receptor.lower().replace(" ", "_"),
                            "mensaje_id": mensaje_id,
                            "tronco_origen_id": tronco.get("id", "eco_tronco"),
                            "timestamp": pygame.time.get_ticks(),
                        })
                        destino = next(
                            persona for persona in mundo["personajes"]
                            if persona["personaje"] == receptor
                        )
                        registrar_transmision(
                            mundo["jugador"]["nombre"],
                            receptor,
                            "eco",
                            mundo["jugador"]["pies"].center,
                            destino["rect"].center,
                        )
                        eco_ui["respuesta"] = construir_respuesta_eco(receptor, mensaje_id, estado)
                        sistema_particulas.emitir(480, 380, 12)
            elif escena in (
                ESCENA_TABLILLA, ESCENA_CONSECUENCIA, ESCENA_CLASIFICACION, ESCENA_RESULTADO
            ) and evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                if escena != ESCENA_TABLILLA and estado.evento_resuelto():
                    reiniciar_jugador_en_casa(mundo)
                escena = ESCENA_MAPA
            elif escena == ESCENA_PAUSA:
                accion = pausa.manejar_evento(
                    evento, convertir_mouse_a_lienzo(getattr(evento, "pos", pygame.mouse.get_pos()), rect_lienzo)
                )
                if accion in ("continuar", "volver"):
                    escena = escena_anterior
                elif accion == "ayuda":
                    ayuda.configurar([("volver", "Volver")])
                    escena = ESCENA_AYUDA
                elif accion == "visual":
                    configurar_menu_visual()
                    escena = ESCENA_VISUAL
                elif accion == "volumen":
                    escena = ESCENA_VOLUMEN
                elif accion == "salir":
                    corriendo = False
            elif escena == ESCENA_VISUAL:
                accion = visual.manejar_evento(
                    evento,
                    convertir_mouse_a_lienzo(
                        getattr(evento, "pos", pygame.mouse.get_pos()), rect_lienzo
                    ),
                )
                if accion == "modo_pantalla_completa":
                    pantalla_completa = True
                    pantalla = crear_ventana(pantalla_completa, ventana_maximizada)
                    configurar_menu_visual()
                elif accion == "modo_ventana_maximizada":
                    pantalla_completa = False
                    ventana_maximizada = True
                    pantalla = crear_ventana(pantalla_completa, ventana_maximizada)
                    configurar_menu_visual()
                elif accion == "modo_ventana_normal":
                    pantalla_completa = False
                    ventana_maximizada = False
                    pantalla = crear_ventana(pantalla_completa, ventana_maximizada)
                    configurar_menu_visual()
                elif accion == "volver":
                    escena = ESCENA_PAUSA
            elif escena == ESCENA_VOLUMEN:
                accion = volumen.manejar_evento(
                    evento, convertir_mouse_a_lienzo(getattr(evento, "pos", pygame.mouse.get_pos()), rect_lienzo)
                )
                if accion == "volver":
                    escena = ESCENA_PAUSA
            elif escena == ESCENA_AYUDA:
                accion = ayuda.manejar_evento(
                    evento, convertir_mouse_a_lienzo(getattr(evento, "pos", pygame.mouse.get_pos()), rect_lienzo)
                )
                if accion:
                    escena = ESCENA_PAUSA
            elif escena == ESCENA_DIALOGO:
                resultado_dialogo = dialogos.manejar_evento(
                    evento, convertir_mouse_a_lienzo(getattr(evento, "pos", pygame.mouse.get_pos()), rect_lienzo)
                )
                if resultado_dialogo:
                    tipo, respuesta = resultado_dialogo
                    personaje_que_respondio = personaje_dialogo_activo
                    if (
                        tipo == "respuesta"
                        and estado.dimension_actual == DIMENSION_PRESENTE
                        and estado.mision_presente["estado"] in ("activa", "pendiente")
                    ):
                        pistas_por_personaje = {
                            "Darío Veraz": "fuente_ausente",
                            "Tomás Red": "testimonio_y_contexto",
                            "Ronaldo Vélez": "respuesta_kael",
                        }
                        pista = pistas_por_personaje.get(personaje_que_respondio)
                        if pista and estado.registrar_pista_presente(pista):
                            estado.guardar_progreso_dimension()
                            recursos["mensaje_dimension"] = (
                                "Pista registrada: " + pista.replace("_", " ") + "."
                            )
                    if personaje_dialogo_activo:
                        conversaciones_vistas.add(clave_dialogo_activo)
                        if personaje_dialogo_activo in estado_personajes:
                            estado_personajes[personaje_dialogo_activo]["conversacion_vista"] = True
                        personaje_dialogo_activo = None
                    mundo["npc_en_dialogo"] = None
                    mundo["jugador"]["estado_visual"] = "idle"
                    if tipo == "respuesta" and respuesta in ("Te ayudaré", "Entrega el mensaje"):
                        mensajero = next(
                            (
                                persona for persona in mundo["personajes"]
                                if persona["personaje"] == "Mensajero"
                            ),
                            None,
                        )
                        if mensajero and personaje_que_respondio == "Mensajero":
                            registrar_transmision(
                                "Mensajero",
                                mundo["jugador"]["nombre"],
                                "mensajero",
                                mensajero["rect"].center,
                                mundo["jugador"]["pies"].center,
                            )
                        mensajes.abrir({
                            "remitente": "Sabio de las Raíces",
                            "destinatario": mundo["jugador"]["nombre"],
                            "texto": "El puente norte necesita una revisión. Consulta a quienes vieron el rayo antes de compartir la tablilla.",
                        })
                        escena = ESCENA_MENSAJE
                    elif tipo == "respuesta" and respuesta == "Consultar tablilla":
                        botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
                        grupo_botones.reemplazar(botones)
                        escena = ESCENA_TABLILLA
                    else:
                        escena = ESCENA_MAPA
            elif escena == ESCENA_MENSAJE:
                if mensajes.manejar_evento(
                    evento, convertir_mouse_a_lienzo(getattr(evento, "pos", pygame.mouse.get_pos()), rect_lienzo)
                ):
                    escena = ESCENA_MAPA
            elif escena == ESCENA_FINAL:
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_r:
                    recursos_la_copa = estado.gestor_dimensiones.recursos_por_dimension.get(
                        DIMENSION_LA_COPA
                    )
                    estado = EstadoJuego()
                    if recursos_la_copa:
                        recursos.update(recursos_la_copa)
                    recursos.pop("sistema_reparacion_puentes", None)
                    recursos.pop("estado_reparacion_guardado", None)
                    recursos["dimension"] = DIMENSION_LA_COPA
                    recursos.pop("spawn_dimension", None)
                    recursos.pop("rect_mapa", None)
                    recursos.pop("mensaje_dimension", None)
                    recursos["feed_digital"] = []
                    recursos.pop("publicacion_inicial_feed_creada", None)
                    recursos["dia"] = 0
                    estado.gestor_dimensiones.guardar_recursos(
                        DIMENSION_LA_COPA,
                        recursos_la_copa or {
                            clave: recursos[clave]
                            for clave in (
                                "mapa",
                                "mapas_dia",
                                "dia",
                                "decoraciones",
                                "interacciones",
                                "hitboxes",
                                "guardian",
                            )
                        },
                    )
                    hud.establecer_etiquetas({
                        "sabiduria": "Sabiduría",
                        "confianza_consejo": "Confianza del Consejo",
                        "armonia": "Armonía",
                        "susurros_falsos": "Susurros Falsos",
                        "desinformación": "Desinformación",
                    })
                    sistema_particulas.configurar_dimension(DIMENSION_LA_COPA)
                    conversaciones_vistas.clear()
                    clave_dialogo_activo = None
                    estado_caldero_anterior = estado_caldero_actual
                    estado_caldero_actual = sincronizar_audio_caldero(
                        gestor_audio, estado, estado_caldero_anterior
                    )
                    mundo = crear_mundo(recursos)
                    botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
                    grupo_botones.reemplazar(botones)
                    usos_pociones = {"colgar": 1, "consultar": 1, "quemar": 1, "ignorar": 1}
                    pocion_animacion = None
                    escena = ESCENA_MAPA
                elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                    corriendo = False
            elif escena in (ESCENA_MAPA_DESTINO, ESCENA_ZONA_EN_PROCESO):
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                    escena = ESCENA_MAPA
                elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    escena = ESCENA_MAPA
            elif escena == ESCENA_MAPA and evento.type == pygame.KEYDOWN and evento.key == pygame.K_q:
                habilidad = mundo.get("habilidad")
                if habilidad and habilidad.personaje == "guardian":
                    if habilidad.activar():
                        multiplicador = f"{habilidad.multiplicador_movimiento:.1f}".replace(
                            ".", ","
                        )
                        duracion = f"{habilidad.configuracion['duracion_ms'] / 1000:.2f}".replace(
                            ".", ","
                        )
                        recursos["mensaje_dimension"] = (
                            "Impulso de viento: velocidad x"
                            f"{multiplicador} durante {duracion} s. "
                            f"Recarga: {habilidad.configuracion['recarga_ms'] / 1000:.0f} s."
                        )
                    else:
                        recursos["mensaje_dimension"] = (
                            f"Impulso recargando: "
                            f"{habilidad.recarga_restante_ms / 1000:.1f}s."
                        )
                elif habilidad and habilidad.personaje == "periodista":
                    if estado.mision_presente.get("decision") == "clasificar_real":
                        recursos["mensaje_dimension"] = (
                            "La imagen era generada por IA; no se puede difundir una corrección con una clasificación incorrecta."
                        )
                    elif (
                        estado.mision_presente.get("decision")
                        not in ("verificar", "clasificar_ia")
                        or (
                            estado.mision_presente.get("decision") == "clasificar_ia"
                            and not estado.mision_presente.get("clasificacion_correcta")
                        )
                    ):
                        recursos["mensaje_dimension"] = (
                            "Reúne las pistas y verifica la publicación antes de corregirla."
                        )
                    elif estado.mision_presente.get("correccion_difundida"):
                        recursos["mensaje_dimension"] = (
                            "La corrección ya fue difundida por el distrito."
                        )
                    elif not difundir_correccion_publica():
                        recursos["mensaje_dimension"] = (
                            "No se pudo difundir la corrección; vuelve a intentarlo."
                        )
                else:
                    recursos["mensaje_dimension"] = "Este personaje no tiene una habilidad activa."
            elif escena == ESCENA_MAPA and evento.type == pygame.KEYDOWN and evento.key == pygame.K_e:
                reparacion = mundo.get("reparacion_puentes")
                if reparacion and reparacion.minijuego_activo:
                    evento_reparacion = reparacion.intentar_reparacion()
                    if evento_reparacion:
                        registrar_evento(evento_reparacion)
                elif interactuable_cercano:
                    jugador = mundo["jugador"]
                    jugador["en_movimiento"] = False
                    jugador["estado_visual"] = "idle"
                    accion = interactuable_cercano.get("accion")
                    if accion == "recolectar_material" and reparacion:
                        evento_material = reparacion.solicitar_recoleccion(
                            interactuable_cercano["id"]
                        )
                        if evento_material:
                            registrar_evento(evento_material)
                            sistema_particulas.emitir(
                                *interactuable_cercano["rect"].center,
                                8,
                            )
                    elif accion == "reparar_puente" and reparacion:
                        reparacion.iniciar_reparacion()
                    elif accion == "entrar_edificio":
                        entrar_edificio(
                            interactuable_cercano.get("edificio_id"),
                            mundo,
                            estado,
                        )
                    elif accion == "salir_edificio":
                        salir_edificio(mundo, estado)
                    elif accion == "npc":
                        abrir_dialogo_personaje(interactuable_cercano["personaje"])
                        registrar_evento({
                            "tipo": "interaccion_personaje",
                            "actor_id": jugador["id"],
                            "objetivo_id": interactuable_cercano["personaje"].lower().replace(" ", "_"),
                        })
                        sistema_particulas.emitir(jugador["pies"].centerx, jugador["pies"].centery, 6)
                        escena = ESCENA_DIALOGO
                    elif accion == "tablilla":
                        registrar_evento({"tipo": "usar_caldero", "actor_id": jugador["id"]})
                        sistema_particulas.emitir(*CENTRO_CALDERO, 14)
                        escena = abrir_caldero()
                    elif accion == "usar_eco_tronco":
                        mensajes_eco = construir_mensajes_eco(estado)
                        eco_ui.update({"destinatario": 0, "mensaje": 0, "respuesta": ""})
                        jugador["estado_visual"] = "usar_eco"
                        jugador["indice_frame"] = 0
                        registrar_evento({
                            "tipo": "usar_eco_tronco",
                            "actor_id": jugador["id"],
                            "objeto_id": interactuable_cercano.get("id", "eco_tronco"),
                        })
                        escena = ESCENA_ECO
                    elif accion == "puerta":
                        if interactuable_cercano.get("zona_en_proceso"):
                            escena = ESCENA_ZONA_EN_PROCESO
                        else:
                            destino = interactuable_cercano.get("imagen_destino")
                            if destino:
                                recursos["mapa_destino"] = destino
                                escena = ESCENA_MAPA_DESTINO
                    elif accion == "portal_temporal":
                        usar_portal_temporal()
                    elif (
                        accion == "examinar_publicacion"
                        or interactuable_cercano.get("tipo") == "pantalla_publica"
                        or interactuable_cercano.get("tipo") == "publicacion_digital"
                    ):
                        abrir_publicacion(interactuable_cercano)
                    elif accion == "otro":
                        registrar_evento({
                            "tipo": "interaccion_otro",
                            "actor_id": jugador["id"],
                            "objeto_id": interactuable_cercano.get("id", "otro"),
                        })
                        sistema_particulas.emitir(
                            *interactuable_cercano["rect"].center, 6
                        )
            elif escena == ESCENA_MAPA and evento.type == pygame.KEYDOWN and evento.key == pygame.K_TAB:
                alternar_interactuable_cercano(mundo)
            elif evento.type == pygame.KEYDOWN and evento.key in (pygame.K_ESCAPE, pygame.K_p):
                escena_anterior = escena
                pausa.configurar([
                    ("continuar", "Continuar"),
                    ("visual", "Visual"),
                    ("ayuda", "Ayuda"),
                    ("volumen", "Volumen"),
                    ("salir", "Salir"),
                ])
                escena = ESCENA_PAUSA
            elif escena == ESCENA_MAPA and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                posicion = posicion_pantalla_a_mundo(
                    convertir_mouse_a_lienzo(evento.pos, rect_lienzo),
                    mundo,
                )
                interaccion = interaccion_en_mapa(posicion, mundo)
                if (
                    interaccion
                    and interaccion["accion"] == "tablilla"
                    and any(
                        objeto.get("accion") == "tablilla"
                        for _, objeto in mundo.get("interacciones_cercanas", [])
                    )
                ):
                    registrar_evento({"tipo": "usar_caldero", "actor_id": mundo["jugador"]["id"]})
                    escena = abrir_caldero()
                elif interaccion and interaccion["accion"] == "npc":
                    abrir_dialogo_personaje(interaccion["personaje"])
                    registrar_evento({
                        "tipo": "interaccion_personaje",
                        "actor_id": mundo["jugador"]["id"],
                        "objetivo_id": interaccion["personaje"].lower().replace(" ", "_"),
                    })
                    escena = ESCENA_DIALOGO
                elif interaccion and interaccion["accion"] == "entrar_edificio":
                    entrar_edificio(interaccion.get("edificio_id"), mundo, estado)
                elif interaccion and interaccion["accion"] == "salir_edificio":
                    salir_edificio(mundo, estado)
                elif interaccion and interaccion["accion"] == "puerta":
                    if interaccion.get("zona_en_proceso"):
                        escena = ESCENA_ZONA_EN_PROCESO
                    else:
                        recursos["mapa_destino"] = interaccion["imagen_destino"]
                        escena = ESCENA_MAPA_DESTINO
                elif interaccion and interaccion["accion"] == "portal_temporal":
                    usar_portal_temporal()
                elif interaccion and interaccion["accion"] == "otro":
                    registrar_evento({
                        "tipo": "interaccion_otro",
                        "actor_id": mundo["jugador"]["id"],
                        "objeto_id": interaccion.get("id", "otro"),
                    })
                    sistema_particulas.emitir(*interaccion["rect"].center, 6)
            elif evento.type == pygame.KEYDOWN:
                opcion_teclado = grupo_botones.manejar_teclado(evento)
                if opcion_teclado and escena == ESCENA_CLASIFICACION:
                    estado.clasificar_evento(opcion_teclado)
                    resultado_clasificacion = estado.resultado_evento_actual()
                    registrar_evento({
                        "tipo": "clasificacion_evento",
                        "clasificacion": opcion_teclado,
                        "acerto": resultado_clasificacion["clasificacion_correcta"],
                    })
                    reproducir_audio_clasificacion(gestor_audio, estado)
                    estado_caldero_anterior = estado_caldero_actual
                    estado_caldero_actual = sincronizar_audio_caldero(
                        gestor_audio, estado, estado_caldero_anterior
                    )
                    botones = []
                    grupo_botones.reemplazar(botones)
                    escena = ESCENA_RESULTADO
                elif opcion_teclado and escena == ESCENA_TABLILLA:
                    pocion_animacion = iniciar_animacion_decision(opcion_teclado)
            elif escena == ESCENA_RESULTADO and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                estado.continuar_despues_resultado()
                recursos["dia"] = estado.dia
                reiniciar_jugador_en_casa(mundo)
                botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
                grupo_botones.reemplazar(botones)
                if estado.juego_terminado():
                    estado.gestor_dimensiones.desbloquear_dimension(DIMENSION_PRESENTE)
                    estado.guardar_progreso_dimension()
                    portal = next(
                        (
                            objeto for objeto in mundo["interacciones"]
                            if objeto.get("accion") == "portal_temporal"
                        ),
                        None,
                    )
                    if portal:
                        portal["activo"] = True
                    recursos["mensaje_dimension"] = (
                        "La Copa está completa. Camina hasta el portal y pulsa E para viajar al presente."
                    )
                    escena = ESCENA_MAPA
                else:
                    escena = ESCENA_MAPA
            elif escena == ESCENA_CONSECUENCIA and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                botones = construir_botones_clasificacion(
                    estado.opciones_clasificacion_actuales(), recursos, fuente_boton
                )
                grupo_botones.reemplazar(botones)
                escena = ESCENA_CLASIFICACION
            elif escena == ESCENA_CLASIFICACION and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                pos_lienzo = convertir_mouse_a_lienzo(evento.pos, rect_lienzo)
                for boton in botones:
                    if boton.fue_clickeado(pos_lienzo):
                        estado.clasificar_evento(boton.texto)
                        resultado_clasificacion = estado.resultado_evento_actual()
                        registrar_evento({
                            "tipo": "clasificacion_evento",
                            "clasificacion": boton.texto,
                            "acerto": resultado_clasificacion["clasificacion_correcta"],
                        })
                        reproducir_audio_clasificacion(gestor_audio, estado)
                        estado_caldero_anterior = estado_caldero_actual
                        estado_caldero_actual = sincronizar_audio_caldero(
                            gestor_audio, estado, estado_caldero_anterior
                        )
                        botones = []
                        grupo_botones.reemplazar(botones)
                        escena = ESCENA_RESULTADO
                        break
            elif escena == ESCENA_TABLILLA and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                pos_lienzo = convertir_mouse_a_lienzo(evento.pos, rect_lienzo)
                if not pocion_animacion:
                    for boton in botones:
                        if boton.fue_clickeado(pos_lienzo):
                            pocion_animacion = iniciar_animacion_decision(boton.texto)
                            break

        if escena == ESCENA_TRANSICION_DIMENSION:
            tiempo_transicion_dimension += delta_ms
            if tiempo_transicion_dimension >= 2000 and not dimension_presente_cargada:
                dimension_presente_cargada = cargar_dimension_presente()
                if not dimension_presente_cargada:
                    recursos["error_dimension"] = (
                        "No se pudo cargar MapaPresente.png. "
                        "La Copa sigue disponible."
                    )
                    escena = ESCENA_ZONA_EN_PROCESO
        elif escena == ESCENA_TUTORIAL_DIMENSION:
            tiempo_tutorial_dimension += delta_ms
        jugador = mundo["jugador"]
        reparacion = mundo.get("reparacion_puentes")
        if reparacion:
            reparacion.actualizar(delta_ms)
        mundo["escena_actual"] = escena
        mundo["mision"] = (
            estado.mision_actual
            if estado.dimension_actual == DIMENSION_PRESENTE
            else "tablillas"
        )
        if escena == ESCENA_MAPA and not (
            reparacion and reparacion.minijuego_activo
        ):
            mover_jugador(jugador, mundo, pygame.key.get_pressed(), delta_ms)
        elif jugador["estado_visual"] in ("hablar", "usar_eco"):
            frames_estado = (
                jugador["frames_eco"]
                if jugador["estado_visual"] == "usar_eco"
                else jugador["frames_hablar"]
            )
            jugador["tiempo_animacion"] += delta_ms
            while jugador["tiempo_animacion"] >= 150:
                jugador["tiempo_animacion"] -= 150
                if frames_estado:
                    jugador["indice_frame"] = (jugador["indice_frame"] + 1) % len(frames_estado)
        mundo["npc_pausados"] = bool(
            reparacion and reparacion.minijuego_activo
        )
        actualizar_npcs_presentes(mundo, delta_ms)
        actualizar_camara_mundo(mundo, delta_ms)
        interactuable_cercano, distancia_interactuable = buscar_interactuable_cercano(
            jugador, mundo
        )

        hud.actualizar(estado.indicadores, delta_segundos)

        if pocion_animacion:
            pocion_animacion["tiempo_transcurrido"] += delta_segundos
            pocion_animacion["restante"] = (
                pocion_animacion["duracion"] - pocion_animacion["tiempo_transcurrido"]
            )
            if pocion_animacion["restante"] <= 0:
                opcion = pocion_animacion["opcion"]
                if opcion in estado.opciones_actuales():
                    estado.elegir_opcion(opcion)
                    accion = accion_tablilla(opcion)
                    if accion:
                        registrar_evento({
                            "tipo": "decision_tablilla",
                            "decision": accion,
                            "actor_id": jugador["id"],
                            "texto": estado.texto_actual(),
                        })
                        gestor_audio.procesar_evento({
                            "tipo": "decision_tablilla",
                            "accion": accion,
                        })
                        if accion == "consultar":
                            sistema_particulas.emitir(*CENTRO_CALDERO, 12)
                    if estado.evento_resuelto():
                        difundir_resultado_tablilla()
                    estado_caldero_anterior = estado_caldero_actual
                    estado_caldero_actual = sincronizar_audio_caldero(
                        gestor_audio, estado, estado_caldero_anterior
                    )
                botones = construir_botones(estado.opciones_actuales(), recursos, fuente_boton)
                grupo_botones.reemplazar(botones)
                pocion_animacion = None
                if estado.evento_resuelto():
                    escena = ESCENA_CONSECUENCIA

        if escena != escena_audio_anterior:
            resultado_audio = determinar_resultado_final(estado) if escena == ESCENA_FINAL else None
            gestor_audio.al_cambiar_escena(escena_audio_anterior, escena, resultado_audio)
            escena_audio_anterior = escena
            if escena == ESCENA_FINAL:
                sistema_particulas.emitir(*CENTRO_CALDERO, 24)
        nuevo_estado_caldero_efectos = estado_caldero(estado)
        if nuevo_estado_caldero_efectos != estado_caldero_efectos:
            if nuevo_estado_caldero_efectos == "critico":
                sistema_particulas.emitir(*CENTRO_CALDERO, 20)
            estado_caldero_efectos = nuevo_estado_caldero_efectos
        if escena not in (ESCENA_PAUSA, ESCENA_VISUAL, ESCENA_AYUDA, ESCENA_VOLUMEN):
            gestor_audio.actualizar()

        posicion_mouse_mundo = posicion_pantalla_a_mundo(mouse_pos, mundo)
        cursor_deseado = (pygame.SYSTEM_CURSOR_HAND
                          if escena == ESCENA_MAPA and interaccion_en_mapa(posicion_mouse_mundo, mundo)
                          else pygame.SYSTEM_CURSOR_ARROW)
        if cursor_deseado != cursor_actual:
            pygame.mouse.set_cursor(cursor_deseado)
            cursor_actual = cursor_deseado

        if escena == ESCENA_MAPA:
            dibujar_mapa(
                lienzo, recursos, mundo, estado, mouse_pos, hud,
                interactuable_cercano, distancia_interactuable,
                sistema_particulas, depuracion_activa,
            )
        elif escena == ESCENA_PAUSA:
            dibujar_mapa(lienzo, recursos, mundo, estado, mouse_pos, hud, resaltar=False)
            pausa.dibujar(
                lienzo,
                "PAUSA",
                ["La Red de Ecos espera tu decisión.", "ESC o P: continuar"],
                mouse_pos,
            )
        elif escena == ESCENA_VISUAL:
            dibujar_mapa(lienzo, recursos, mundo, estado, mouse_pos, hud, resaltar=False)
            modo_actual = (
                "Pantalla completa" if pantalla_completa
                else "Ventana maximizada" if ventana_maximizada
                else "Ventana normal"
            )
            visual.dibujar(
                lienzo,
                "VISUAL",
                [f"Modo actual: {modo_actual}. Selecciona una opcion."],
                mouse_pos,
            )
        elif escena == ESCENA_VOLUMEN:
            dibujar_mapa(lienzo, recursos, mundo, estado, mouse_pos, hud, resaltar=False)
            volumen.dibujar(lienzo, "VOLUMEN", ["Ajusta la música y los efectos de sonido."], mouse_pos)
        elif escena == ESCENA_AYUDA:
            dibujar_mapa(lienzo, recursos, mundo, estado, mouse_pos, hud, resaltar=False)
            controles = [
                "Muévete con WASD o flechas; acércate y pulsa E para interactuar.",
                "J: abre la bitácora de misiones, pistas e historia.",
                "Habla con personajes para reunir testimonios; Tab cambia el objetivo cercano.",
                "Mantén Sabiduría, Confianza y Armonía saludables; evita que crezcan Desinformación y Susurros Falsos.",
            ]
            if estado.dimension_actual == DIMENSION_PRESENTE:
                controles.extend((
                    "C: abre el celular/feed. Investiga a Darío, Tomás y Ronaldo antes de clasificar.",
                    "Q: difunde una corrección después de verificar la publicación.",
                ))
            else:
                controles.extend((
                    "Misión secundaria: reúne tablas, cuerda y herramientas; repara el Puente Norte con tres aciertos.",
                    "Q: activa el impulso de viento del Guardián.",
                    "Escucha testimonios y revisa las tablillas en el Caldero central.",
                ))
            ayuda.dibujar(
                lienzo,
                "AYUDA",
                controles,
                mouse_pos,
            )
        elif escena == ESCENA_TUTORIAL_DIMENSION:
            dibujar_tutorial_dimension(
                lienzo,
                recursos,
                mundo,
                estado,
                hud,
                estado.dimension_actual,
                mouse_pos,
                tiempo_tutorial_dimension >= DURACION_MINIMA_TUTORIAL_DIMENSION_MS,
            )
        elif escena == ESCENA_CODICE:
            dibujar_codice(
                lienzo,
                recursos,
                estado,
                mundo,
                hud,
                indice_pagina_codice,
                conversaciones_vistas,
                mouse_pos,
                recursos.get("mision_objetivo_seleccionada", "principal"),
            )
        elif escena == ESCENA_DIALOGO:
            dialogos.actualizar(delta_segundos)
            dibujar_escena_dialogo(
                lienzo, recursos, dialogos, mouse_pos, hud,
                mundo["jugador"], sistema_particulas, mundo,
            )
        elif escena == ESCENA_MENSAJE:
            mensajes.actualizar(delta_segundos)
            dibujar_escena_mensaje(
                lienzo, recursos, mensajes, mouse_pos, hud, mundo["jugador"], mundo
            )
        elif escena == ESCENA_ECO:
            dibujar_interfaz_eco(
                lienzo, recursos, mundo["jugador"], eco_ui, nombres_contacto, mensajes_eco, mundo
            )
        elif escena == ESCENA_CELULAR:
            dibujar_mapa(lienzo, recursos, mundo, estado, mouse_pos, hud)
            dibujar_celular_feed(lienzo, recursos, estado)
        elif escena == ESCENA_ANALISIS:
            dibujar_analisis_publicacion(
                lienzo,
                recursos,
                mundo,
                estado,
                hud,
                indice_opcion_mision,
                mouse_pos,
            )
            if mensaje_mision:
                aviso = recursos["fuente_mapa"].render(mensaje_mision, True, (255, 213, 122))
                lienzo.blit(aviso, aviso.get_rect(center=(ANCHO // 2, 395)))
        elif escena == ESCENA_TRANSICION_DIMENSION:
            dibujar_transicion_dimension(
                lienzo,
                recursos,
                mundo,
                estado,
                hud,
                sistema_particulas,
                mouse_pos,
                tiempo_transicion_dimension,
                dimension_presente_cargada,
            )
        elif escena == ESCENA_MAPA_DESTINO:
            lienzo.blit(recursos["mapa_destino"], (0, 0))
            dibujar_mensaje_mapa(
                lienzo,
                recursos["fuente_mapa"],
                "Zona Central. Haz clic o pulsa Esc para volver al mapa principal.",
            )
        elif escena == ESCENA_ZONA_EN_PROCESO:
            lienzo.fill((0, 0, 0))
            titulo = recursos["fuente_resultado"].render(
                "DIMENSIÓN NO DISPONIBLE",
                True,
                CREMA,
            )
            lienzo.blit(titulo, titulo.get_rect(center=(ANCHO // 2, ALTO // 2 - 24)))
            instruccion = recursos["fuente_mapa"].render(
                recursos.get(
                    "error_dimension",
                    "Pulsa Esc o haz clic para regresar",
                ),
                True,
                CREMA,
            )
            lienzo.blit(
                instruccion,
                instruccion.get_rect(center=(ANCHO // 2, ALTO // 2 + 28)),
            )
        elif escena == ESCENA_CONSECUENCIA:
            dibujar_consecuencia_evento(lienzo, recursos, estado)
        elif escena == ESCENA_CLASIFICACION:
            dibujar_pregunta_clasificacion(lienzo, recursos, estado, botones, mouse_pos)
        elif escena == ESCENA_RESULTADO:
            dibujar_resultado_evento(lienzo, recursos, estado)
        elif escena == ESCENA_FINAL:
            dibujar_final(lienzo, recursos, estado)
        else:
            dibujar_escena_tablilla(lienzo, recursos, estado, botones, mouse_pos, hud, pocion_animacion)
            dibujar_pociones(lienzo, recursos, usos_pociones, pocion_animacion, mouse_pos)

        presentar_lienzo(pantalla, lienzo)
        pygame.display.flip()
    gestor_audio.detener_todo()
    pygame.quit()
    sys.exit()
