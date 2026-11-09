from collections import Counter
import math

from multijugador import clasificacion
from multijugador.nucleo import LLAVE, intento_bot as intento_nucleo
from multijugador.presente import intento_bot
from multijugador.reparacion import CONFIGURACION as CONFIG_PUENTE, angulo_objetivo

RADIO_CALDERO = 68  # el servidor exige esta distancia para elegir
RADIO_EMISOR = 56  # junto a quien llamó, dentro del alcance de una entrega directa
ESPERA_ORDEN = 12.0  # segundos que se queda donde lo llamaron si no hay más que hacer
ESPERA_ALIADO = 25.0  # segundos que el Habitante espera compañero para su habilidad
PASO_ACOMPANAR = 40  # solo recalcula la ruta cuando el humano cambia de casilla
DISTANCIA_PULSO = 44  # a menos de esto, un bot con la llave se aparta del pulso
ACIERTO_MARCA = {"facil": .55, "normal": .75, "dificil": .9}  # probabilidad de señalar bien


class PlanificadorBot:
    UMBRALES = {"facil": 0.55, "normal": 0.7, "dificil": 0.8}

    @classmethod
    def mejor_opcion(cls, inventario, excluidas=()):
        """Mejor lectura de las pistas aunque no sean concluyentes (nunca mira la solución)."""
        propuesta = cls.proponer_decision(inventario)["accion_propuesta"]
        if propuesta and propuesta not in excluidas:
            return propuesta
        metadatos = [p.get("metadatos", {}) for p in inventario]
        senales = {
            "corregir": sum(bool(m.get("problema_parcial")) for m in metadatos),
            "difundir": sum(bool(m.get("confirma_riesgo_actual")) for m in metadatos),
            "descartar": sum(bool(m.get("indica_descontextualizacion") or m.get("confirma_ausencia_de_riesgo")
                                  or m.get("fuente_actual_alternativa")) for m in metadatos),
        }
        return max((o for o in senales if o not in excluidas), key=senales.get)

    @staticmethod
    def proponer_decision(inventario):
        metadatos = [p.get("metadatos", {}) for p in inventario]
        riesgos = sum(bool(p.get("confirma_riesgo_actual")) for p in metadatos)
        fuera_contexto = sum(
            bool(p.get("indica_descontextualizacion")) for p in metadatos
        )
        parciales = sum(bool(p.get("problema_parcial")) for p in metadatos)

        if riesgos >= 2:
            return {
                "accion_propuesta": "difundir",
                "confianza": min(0.94, 0.72 + riesgos * 0.06),
                "razon": "Fuentes distintas confirman un riesgo actual.",
            }
        if fuera_contexto >= 2 and riesgos == 0:
            return {
                "accion_propuesta": "descartar",
                "confianza": min(0.92, 0.7 + fuera_contexto * 0.06),
                "razon": "La prueba corresponde a otro contexto o a un simulacro.",
            }
        if parciales >= 2 and riesgos == 0:
            return {
                "accion_propuesta": "corregir",
                "confianza": min(0.9, 0.68 + parciales * 0.05),
                "razon": "La afirmación absoluta contradice un problema parcial documentado.",
            }
        return {
            "accion_propuesta": None,
            "confianza": 0.4,
            "razon": "Las pruebas disponibles todavía no coinciden.",
        }

    def planificar(self, bot, estado, jugadores, memoria, dificultad):
        if bot.posicion.get("dimension", "la_copa") != "la_copa":
            bot.orden = None
            tarea_de_era = self._tareas_nucleo if bot.posicion.get("dimension") == "futuro" else self._analizar_distrito
            return (self._distrito(bot, estado, jugadores, memoria)
                    or tarea_de_era(bot, estado, jugadores, memoria, dificultad)
                    or (self._sin_personas(jugadores) and self._decidir_solos(bot, estado))
                    or self._acompanar(bot, jugadores, estado))
        caso = estado["caso"]
        if caso["fase"] == "final" and self._sin_personas(jugadores):
            return self._al_portal(bot, estado, "presente")
        privado = estado["privado"]
        ronda = caso["ronda"]
        jugadores = [j for j in jugadores if j.get("conectado", True)]
        inventario = privado.get("inventario", [])
        habilidad_usada = privado.get("habilidad_usada", False)
        objetivo_rol = next(
            o for o in caso["objetivos"] if o.get("rol") == bot.rol
        )
        caldero = next(o for o in caso["objetivos"] if o["id"] == "caldero")

        if caso["fase"] == "final":
            bot.orden = None
            return {"estado": "ESPERANDO_EQUIPO"}
        plan_orden = self._cumplir_orden(bot, caso, privado, jugadores, caldero, memoria)
        if plan_orden:
            return plan_orden
        if caso["fase"] == "preparacion":
            return self._preparacion(bot, caso, privado, caldero, memoria, jugadores)

        propia = "pista_" + bot.rol
        if propia not in {p["id"] for p in inventario}:
            return self._tarea("YENDO_A_FUENTE", objetivo_rol, "interactuar", objetivo=objetivo_rol["id"])

        indicador = caso["indicadores"]
        if not habilidad_usada and bot.rol == "mensajero":
            return {"estado": "USANDO_HABILIDAD", "accion": "habilidad"}
        if not habilidad_usada and bot.rol == "guardian" and indicador["desinformacion"] >= 20:
            return self._tarea("USANDO_HABILIDAD", objetivo_rol, "habilidad")
        if not habilidad_usada and bot.rol == "aspirante" and len(inventario) >= 2:
            return self._tarea("USANDO_HABILIDAD", caldero, "habilidad")
        if not habilidad_usada and bot.rol == "habitante" and not bot.sin_ayuda:
            aliado_cerca = any(
                jugador["id"] != bot.identificador
                and (jugador["x"] - bot.posicion["x"]) ** 2
                + (jugador["y"] - bot.posicion["y"]) ** 2 <= 80 ** 2
                for jugador in jugadores
            )
            if aliado_cerca:
                return self._tarea("USANDO_HABILIDAD", objetivo_rol, "habilidad")
            if bot.espera_ayuda_desde is None:
                bot.espera_ayuda_desde = bot.ahora
            if bot.ahora - bot.espera_ayuda_desde <= ESPERA_ALIADO:
                memoria.solicitar_ayuda(bot.identificador, objetivo_rol)
                return {
                    "estado": "BUSCANDO_ALIADO",
                    "destino": dict(objetivo_rol),
                    "esperar": True,
                }
            # Nadie llegó: sigue con el caso sin su habilidad en vez de quedarse allí.
            bot.sin_ayuda = True
            memoria.completar_ayuda(bot.identificador)

        if bot.asistencia_a:
            destino = bot.asistencia_a
            return {
                "estado": "BUSCANDO_ALIADO",
                "destino": destino,
                "esperar": True,
            }

        compartidos = bot.compartidas.get(ronda, set())
        receptor = next(
            (j for j in jugadores if j["id"] != bot.identificador and j["id"] not in compartidos),
            None,
        )
        if receptor:
            if bot.rol == "mensajero" and not habilidad_usada:
                return {"estado": "USANDO_HABILIDAD", "accion": "habilidad"}
            eco = min(
                (o for o in caso["objetivos"] if o["tipo"] == "eco"),
                key=lambda o: (o["x"] - bot.posicion["x"]) ** 2 + (o["y"] - bot.posicion["y"]) ** 2,
            )
            return self._tarea(
                "COMPARTIENDO_PRUEBA",
                eco,
                "entregar",
                destinatario=receptor["id"],
                pista=propia,
                medio="eco",
                marca_compartida=receptor["id"],
            )

        propuesta = self.proponer_decision(inventario)
        bot.confianza_decision = propuesta["confianza"]
        threshold = self.UMBRALES[dificultad]
        if (
            len(inventario) >= 2
            and propuesta["accion_propuesta"]
            and propuesta["confianza"] >= threshold
            and not privado.get("voto")
            and not (bot.sin_difundir and propuesta["accion_propuesta"] == "difundir")
        ):
            memoria.votos_propuestos[bot.identificador] = propuesta
            return self._tarea(
                "VOTANDO",
                caldero,
                "votar",
                opcion=propuesta["accion_propuesta"],
                marca_voto=propuesta["accion_propuesta"],
            )

        # El caso espera la elección de todos: si alguien ya eligió, o lo
        # llamaron al caldero, elige con lo que sabe en lugar de bloquear al equipo.
        if (
            len(inventario) >= 2
            and self._debe_elegir(bot, privado)
            and (caso.get("votos_emitidos") or bot.convocado)
        ):
            return self._votar(bot, inventario, caldero, memoria)

        if caso.get("resultado") and not caso["resultado"].get("correcto") and not caso.get("rectificacion"):
            return self._tarea("RECTIFICANDO", caldero, "rectificar")
        return {"estado": "ANALIZANDO_PRUEBAS"}

    # ------------------------------------------------- órdenes de los ecos
    @staticmethod
    def _debe_elegir(bot, privado):
        voto = privado.get("voto")
        return not voto or (bot.sin_difundir and voto == "difundir")

    def _votar(self, bot, inventario, caldero, memoria):
        """Elige coordinado con los demás bots: dividirse dejaría el caso empatado."""
        excluidas = ("difundir",) if bot.sin_difundir else ()
        opcion = None
        if not self.proponer_decision(inventario)["accion_propuesta"]:
            equipo = Counter(p["accion_propuesta"] for p in memoria.votos_propuestos.values()
                             if p["accion_propuesta"] not in excluidas)
            opcion = equipo.most_common(1)[0][0] if equipo else None
        opcion = opcion or self.mejor_opcion(inventario, excluidas)
        memoria.votos_propuestos[bot.identificador] = {"accion_propuesta": opcion}
        return self._tarea("VOTANDO", caldero, "votar", opcion=opcion, marca_voto=opcion)

    def _cumplir_orden(self, bot, caso, privado, jugadores, caldero, memoria):
        """Un mensaje recibido pasa por delante de cualquier otra tarea."""
        orden = bot.orden
        if not orden:
            return None
        puente = caso.get("puente") or {}
        if puente.get("estado") == "REPAIR_MINIGAME" and puente.get("reparador") == bot.identificador:
            return None  # termina los pocos segundos del minijuego y va
        if orden["tipo"] == "caldero":
            return self._acudir_al_caldero(bot, caso, privado, caldero, memoria)
        return self._acudir_al_emisor(bot, caso, jugadores)

    def _acudir_al_caldero(self, bot, caso, privado, caldero, memoria):
        if self._distancia(bot, caldero) > RADIO_CALDERO:
            return {"estado": "YENDO_AL_CALDERO", "destino": dict(caldero), "esperar": True}
        if caso["fase"] != "investigacion":
            if self._espera_cumplida(bot):
                return None
            return {"estado": "ESPERANDO_EQUIPO", "destino": dict(caldero), "esperar": True}
        inventario = privado.get("inventario", [])
        if not self._debe_elegir(bot, privado):
            bot.orden = None
            return None
        if len(inventario) < 2:
            # Sin dos pistas no puede comparar: las consigue y vuelve a elegir.
            bot.orden = None
            bot.convocado = True
            return None
        return self._votar(bot, inventario, caldero, memoria)

    def _acudir_al_emisor(self, bot, caso, jugadores):
        orden = bot.orden
        emisor = next((j for j in jugadores if j["id"] == orden["emisor"]
                       and j.get("dimension", "la_copa") == "la_copa"), None)
        if emisor is None:
            bot.orden = None
            return None
        destino = {"id": emisor["id"], "nombre": emisor["nombre"], "x": emisor["x"], "y": emisor["y"]}
        if self._distancia(bot, emisor) <= RADIO_EMISOR:
            if self._espera_cumplida(bot):
                return None
            propia = "pista_" + bot.rol
            compartidos = bot.compartidas.get(caso["ronda"], set())
            if (orden["tipo"] == "ayudar" and caso["fase"] == "investigacion"
                    and bot.prueba_propia and emisor["id"] not in compartidos):
                return self._tarea("COMPARTIENDO_PRUEBA", destino, "entregar", destinatario=emisor["id"],
                                   pista=propia, medio="directo", marca_compartida=emisor["id"],
                                   radio=RADIO_EMISOR)
        return {"estado": "ACOMPANANDO", "destino": destino, "esperar": True, "radio": RADIO_EMISOR}

    @staticmethod
    def _espera_cumplida(bot):
        """Cuenta desde que llegó; al terminar el plazo libera la orden."""
        orden = bot.orden
        if orden["llegada"] is None:
            orden["llegada"] = bot.ahora
        if bot.ahora - orden["llegada"] < ESPERA_ORDEN:
            return False
        bot.orden = None
        return True

    @staticmethod
    def _sin_personas(jugadores):
        return not any(j.get("controlador") != "bot" and j.get("conectado", True) for j in jugadores)

    @staticmethod
    def _al_portal(bot, estado, destino):
        x, y, ancho, alto = estado["portales"][bot.posicion.get("dimension", "la_copa")]
        return {"estado": "VIAJANDO", "destino": {"id": "portal", "x": x + ancho // 2, "y": y + alto + 3},
                "accion": "usar_portal", "datos": {"destino": destino}, "radio": 30}

    def _decidir_solos(self, bot, estado):
        """Un equipo solo de bots también decide, clasifica y sigue a la siguiente era."""
        dimension = bot.posicion.get("dimension")
        mision, privado = estado["caso"].get(dimension) or {}, estado["privado"].get(dimension) or {}
        if bot.posicion.get("interior") or mision.get("pistas", 0) < mision.get("total_pistas", 1):
            return None
        pantalla = next(o for o in mision["objetivos"] if o["id"] == dimension + ":pantalla")
        if not mision.get("completada"):
            if dimension == "presente" and not (mision.get("analisis") or {}).get("concluido"):
                return None
            if privado.get("voto"):
                return {"estado": "ESPERANDO_EQUIPO"}
            return self._tarea("VOTANDO", pantalla, "presente_votar", opcion="verificar")
        if dimension == "futuro":
            return {"estado": "ESPERANDO_EQUIPO"}
        if mision.get("fin"):
            return self._al_portal(bot, estado, "futuro")
        if not privado.get("clasificacion"):
            real = clasificacion.CATEGORIA_EVENTO[mision["evento"]["id"]]
            categoria = next(nombre for nombre, ruta in clasificacion.OPCIONES["presente"].items() if ruta == real)
            return {"estado": "ANALIZANDO_PRUEBAS", "accion": "presente_clasificar", "datos": {"categoria": categoria}}
        if not privado.get("listo"):
            return {"estado": "ESPERANDO_EQUIPO", "accion": "presente_siguiente", "datos": {}}
        return {"estado": "ESPERANDO_EQUIPO"}

    @staticmethod
    def _distancia(bot, punto):
        return math.hypot(punto["x"] - bot.posicion["x"], punto["y"] - bot.posicion["y"])

    def _distrito(self, bot, estado, jugadores, memoria):
        """Los bots reúnen pistas y dejan una por persona, la más cercana a ella.

        La decisión y la clasificación siguen siendo de las personas."""
        dimension = bot.posicion.get("dimension")
        privado = estado["privado"].get(dimension) or {}
        humanos = [j for j in jugadores if j.get("controlador") != "bot"
                   and j.get("dimension") == dimension and j.get("conectado", True)]
        halladas = {p["id"] for p in privado.get("inventario", [])}
        pendientes = [n for n in estado["caso"].get("npcs", [])
                      if n["dimension"] == dimension and n.get("pista") and n["pista"] not in halladas]
        if (not humanos and not self._sin_personas(jugadores)) or not pendientes:
            return None
        # Una tarea reservada se termina, aunque la persona se haya movido.
        for objetivo in pendientes:
            if memoria.reservas_preparacion.get("distrito:" + objetivo["pista"]) == bot.identificador:
                return self._hablar_con(bot, estado, objetivo)
        reservadas =sum("distrito:" + o["pista"] in memoria.reservas_preparacion for o in pendientes)
        if len(pendientes) - reservadas <= len(humanos):
            return None
        cercania = lambda o: min((math.hypot(o["x"] - j["x"], o["y"] - j["y"]) for j in humanos), default=0)
        for objetivo in sorted(pendientes, key=cercania, reverse=True):
            if memoria.reservar_preparacion(bot.identificador, "distrito:" + objetivo["pista"]):
                return self._hablar_con(bot, estado, objetivo)
        return None

    def _hablar_con(self, bot, estado, objetivo):
        """Va hasta el personaje; si está en otro edificio, usa las puertas como cualquiera."""
        edificios = (estado["caso"].get("presente") or {}).get("edificios", {})
        destino, mio = objetivo.get("interior"), bot.posicion.get("interior")
        if destino == mio:
            return self._tarea("INVESTIGANDO", objetivo, "hablar_npc", npc=objetivo["id"])
        if mio:
            return self._tarea("INVESTIGANDO", edificios[mio]["salida"], "salir_edificio", radio=30)
        return self._tarea("INVESTIGANDO", edificios[destino], "entrar_edificio", edificio=destino, radio=16)

    def _tareas_nucleo(self, bot, estado, jugadores, memoria, dificultad):
        """Recorren las terminales con los mismos mensajes y dejan una por persona."""
        futuro = estado["caso"].get("futuro") or {}
        inventario = {p["id"] for p in (estado["privado"].get("futuro") or {}).get("inventario", [])}
        humanos = [j for j in jugadores if j.get("controlador") != "bot"
                   and j.get("dimension") == "futuro" and j.get("conectado", True)]
        pendientes = [o for o in futuro.get("objetivos", []) if o.get("tarea") and o["tarea"] not in futuro.get("tareas", [])
                      and o["tarea"] != "llave"]
        terminal_llave = next((o for o in futuro.get("objetivos", []) if o.get("tarea") == "llave" and "llave" not in futuro.get("tareas", [])), None)
        if terminal_llave and futuro.get("portador") == bot.identificador:
            return self._llevar_llave(bot, futuro, terminal_llave)
        if (not humanos and not self._sin_personas(jugadores)) or not pendientes:
            bot.marca_planeada = None
            return None
        objetivo = next((o for o in pendientes if memoria.reservas_preparacion.get("nucleo:" + o["tarea"]) == bot.identificador), None)
        if objetivo is None:
            reservadas = sum("nucleo:" + o["tarea"] in memoria.reservas_preparacion for o in pendientes)
            if len(pendientes) - reservadas <= len(humanos):
                return None
            objetivo = next((o for o in pendientes if memoria.reservar_preparacion(bot.identificador, "nucleo:" + o["tarea"])), None)
            if objetivo is None:
                return None
        if bot.marca_planeada is None:
            bot.marca_planeada = intento_nucleo(objetivo["tarea"], bot._random, ACIERTO_MARCA.get(dificultad, .75))
        return self._tarea("INVESTIGANDO", objetivo, "futuro_resolver", terminal=objetivo["tarea"], **bot.marca_planeada)

    def _llevar_llave(self, bot, futuro, terminal):
        """Va a la terminal, y se aparta si un pulso de vigilancia se le acerca."""
        posicion = bot.posicion
        cercano = min(futuro.get("pulsos", []), key=lambda p: math.hypot(p[0] - posicion["x"], p[1] - posicion["y"]), default=None)
        if cercano is not None:
            distancia = math.hypot(cercano[0] - posicion["x"], cercano[1] - posicion["y"])
            if 0 < distancia < DISTANCIA_PULSO:
                factor = 80 / distancia
                return {"estado": "ESQUIVANDO", "destino": {"id": "esquiva", "x": posicion["x"] + (posicion["x"] - cercano[0]) * factor,
                                                            "y": posicion["y"] + (posicion["y"] - cercano[1]) * factor}, "esperar": True, "radio": 20}
        return self._tarea("INVESTIGANDO", terminal, "futuro_resolver", terminal="llave")

    def _analizar_distrito(self, bot, estado, jugadores, memoria, dificultad):
        """Un bot ayuda a marcar, con los mismos mensajes, y deja la última marca a las personas."""
        presente = estado["caso"].get("presente") or {}
        privado = estado["privado"].get("presente") or {}
        analisis = presente.get("analisis") or {}
        evento = (presente.get("evento") or {}).get("id")
        solos = self._sin_personas(jugadores)
        faltan_para_personas = 0 if solos else 1  # la última marca es de las personas
        if (not analisis.get("disponible") or presente.get("completada")
                or len(analisis.get("halladas", [])) >= analisis.get("minimo", 0) - faltan_para_personas):
            bot.marca_planeada = None
            return None
        if not memoria.reservar_preparacion(bot.identificador, "analisis:" + evento):
            return None
        companero = {} if solos else self._acompanar(bot, jugadores)
        if not solos and "destino" not in companero:
            return None
        companero.pop("esperar", None)
        if not privado.get("analizando"):
            return dict(companero, estado="ANALIZANDO_PRUEBAS", accion="presente_analizar", datos={})
        if bot.marca_planeada is None:
            encontradas = {m["id"] for m in analisis["halladas"]}
            bot.marca_planeada = intento_bot(evento, encontradas, bot._random, ACIERTO_MARCA.get(dificultad, .75))
        return dict(companero, estado="ANALIZANDO_PRUEBAS", accion="presente_marcar", datos=dict(bot.marca_planeada))

    @staticmethod
    def _acompanar(bot, jugadores, estado=None):
        """Fuera de La Copa los bots acompañan al humano más cercano."""
        dimension, interior = bot.posicion.get("dimension"), bot.posicion.get("interior")
        humanos = [j for j in jugadores if j.get("controlador") != "bot" and j.get("dimension") == dimension
                   and j.get("interior") == interior and j.get("conectado", True)]
        if interior and not humanos and estado is not None:  # terminó aquí dentro: vuelve a la calle
            salida = estado["caso"]["presente"]["edificios"][interior]["salida"]
            return PlanificadorBot._tarea("ACOMPANANDO", salida, "salir_edificio", radio=30)
        if not humanos:
            return {"estado": "ESPERANDO_EQUIPO"}
        humano = min(humanos, key=lambda j: (j["x"] - bot.posicion["x"]) ** 2 + (j["y"] - bot.posicion["y"]) ** 2)
        destino = {"id": humano["id"], "x": round(humano["x"] / PASO_ACOMPANAR) * PASO_ACOMPANAR,
                   "y": round(humano["y"] / PASO_ACOMPANAR) * PASO_ACOMPANAR}
        return {"estado": "ACOMPANANDO", "destino": destino, "esperar": True, "radio": 70}

    # ------------------------------------------------------- preparación
    # Mismo flujo que la guía del jugador (campana.privado/encargo.objetivo):
    # recoger -> entregar en el puesto -> actividad en pareja -> (caso 1)
    # reparar el Puente 1 -> confirmar en el caldero.
    def _preparacion(self, bot, caso, privado, caldero, memoria, jugadores):
        encargo = caso.get("encargo") or {}
        yo = bot.identificador
        ronda = caso["ronda"]
        if encargo.get("completo"):
            bot.inicio_reparacion = None
            if not privado.get("preparado"):
                return self._tarea("CONFIRMANDO_CONTINUACION", caldero, "continuar")
            return {"estado": "ESPERANDO_EQUIPO"}
        if encargo.get("materiales_colocados"):
            # Reparar el puente le toca a las personas; los bots solo si no queda ninguna.
            if any(j.get("controlador") == "humano" for j in jugadores):
                return {"estado": "ESPERANDO_EQUIPO"}
            return self._reparar_puente(bot, caso.get("puente") or {}, privado.get("objetivo"), memoria)
        destino = encargo.get("destino") or caldero
        if encargo.get("materiales_listos"):
            ayudante = (encargo.get("actividad") or {}).get("ayudante")
            if ayudante == yo:
                return self._esperar("SUJETANDO", destino, radio=40)
            if ayudante is None:
                if memoria.reservar_preparacion(yo, f"{ronda}:sujetar"):
                    return self._tarea("SUJETANDO", destino, "sujetar", radio=40)
                return self._esperar("ESPERANDO_EQUIPO", destino, radio=40)
            if memoria.reservar_preparacion(yo, f"{ronda}:trabajar:{ayudante}"):
                return self._tarea("TRABAJANDO", destino, "trabajar", radio=40)
            return self._esperar("ESPERANDO_EQUIPO", destino, radio=40)
        if privado.get("carga"):
            return self._tarea("ENTREGANDO_SUMINISTRO", destino, "interactuar", objetivo=destino["id"])
        objetivo = privado.get("objetivo") or destino
        if objetivo.get("id") in (destino.get("id"), caldero["id"]):
            # Nada que recoger (otro lleva el objeto o ya aportó): esperar en el
            # puesto para ayudar en la actividad.
            return self._esperar("ESPERANDO_EQUIPO", destino, radio=40)
        return self._tarea("YENDO_POR_SUMINISTRO", objetivo, "interactuar", objetivo=objetivo["id"])

    def _reparar_puente(self, bot, puente, objetivo_puente, memoria):
        yo = bot.identificador
        estado, reparador = puente.get("estado"), puente.get("reparador")
        if not objetivo_puente:
            return {"estado": "ESPERANDO_EQUIPO"}
        if estado == "REPAIR_MINIGAME" and reparador == yo:
            tiempo = self._tiempo_en_zona(bot, puente.get("progreso", 0))
            if tiempo is None:
                return self._esperar("REPARANDO_PUENTE", objetivo_puente, radio=28)
            return self._tarea("REPARANDO_PUENTE", objetivo_puente, "intento_reparacion",
                               tiempo_aguja_ms=tiempo, radio=28)
        bot.inicio_reparacion = None
        if (estado == "READY_TO_REPAIR" and reparador is None
                and memoria.reservar_preparacion(yo, "puente_1")):
            return self._tarea("REPARANDO_PUENTE", objetivo_puente, "interactuar",
                               objetivo=objetivo_puente["id"], radio=28)
        return {"estado": "ESPERANDO_EQUIPO"}

    @staticmethod
    def _tiempo_en_zona(bot, progreso):
        """Siguiente instante (ms desde que abrió el minijuego) con la aguja en
        el centro de la zona verde; None si todavía no llega."""
        if bot.inicio_reparacion is None:
            bot.inicio_reparacion = bot.ahora
            bot.ultimo_tiempo_aguja = -1.0
        periodo = CONFIG_PUENTE["duracion_recorrido_ms"]
        fase = ((angulo_objetivo(progreso) + math.pi) / math.pi) % 1 * periodo
        vuelta = max(0, math.floor((bot.ultimo_tiempo_aguja - fase) / periodo) + 1)
        tiempo = round(vuelta * periodo + fase, 1)
        if tiempo > (bot.ahora - bot.inicio_reparacion) * 1000:
            return None
        bot.ultimo_tiempo_aguja = tiempo
        return tiempo

    @staticmethod
    def _esperar(estado, destino, radio=None):
        return {"estado": estado, "destino": dict(destino), "esperar": True, "radio": radio}

    @staticmethod
    def _tarea(estado, destino, accion, **datos):
        marca_compartida = datos.pop("marca_compartida", None)
        marca_voto = datos.pop("marca_voto", None)
        radio = datos.pop("radio", None)
        return {
            "estado": estado,
            "destino": dict(destino),
            "accion": accion,
            "datos": datos,
            "marca_compartida": marca_compartida,
            "marca_voto": marca_voto,
            "radio": radio,
        }
