import math

from multijugador.reparacion import CONFIGURACION as CONFIG_PUENTE, angulo_objetivo


class PlanificadorBot:
    UMBRALES = {"facil": 0.55, "normal": 0.7, "dificil": 0.8}

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
            return self._acompanar(bot, jugadores)
        caso = estado["caso"]
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
            return {"estado": "ESPERANDO_EQUIPO"}
        if caso["fase"] == "preparacion":
            return self._preparacion(bot, caso, privado, caldero, memoria)

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
        if not habilidad_usada and bot.rol == "habitante":
            aliado_cerca = any(
                jugador["id"] != bot.identificador
                and (jugador["x"] - bot.posicion["x"]) ** 2
                + (jugador["y"] - bot.posicion["y"]) ** 2 <= 80 ** 2
                for jugador in jugadores
            )
            if aliado_cerca:
                return self._tarea("USANDO_HABILIDAD", objetivo_rol, "habilidad")
            memoria.solicitar_ayuda(bot.identificador, objetivo_rol)
            if (
                (objetivo_rol["x"] - bot.posicion["x"]) ** 2
                + (objetivo_rol["y"] - bot.posicion["y"]) ** 2 > 48 ** 2
            ):
                return {
                    "estado": "BUSCANDO_ALIADO",
                    "destino": dict(objetivo_rol),
                    "esperar": True,
                }

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
        ):
            memoria.votos_propuestos[bot.identificador] = propuesta
            return self._tarea(
                "VOTANDO",
                caldero,
                "votar",
                opcion=propuesta["accion_propuesta"],
                marca_voto=propuesta["accion_propuesta"],
            )

        if caso.get("resultado") and not caso["resultado"].get("correcto") and not caso.get("rectificacion"):
            return self._tarea("RECTIFICANDO", caldero, "rectificar")
        return {"estado": "ANALIZANDO_PRUEBAS"}

    @staticmethod
    def _acompanar(bot, jugadores):
        """Fuera de La Copa los bots acompañan al humano más cercano."""
        dimension = bot.posicion.get("dimension")
        humanos = [j for j in jugadores if j.get("controlador") != "bot"
                   and j.get("dimension") == dimension and j.get("conectado", True)]
        if not humanos:
            return {"estado": "ESPERANDO_EQUIPO"}
        humano = min(humanos, key=lambda j: (j["x"] - bot.posicion["x"]) ** 2 + (j["y"] - bot.posicion["y"]) ** 2)
        return {"estado": "ACOMPANANDO", "destino": {"id": humano["id"], "x": humano["x"], "y": humano["y"]},
                "esperar": True, "radio": 70}

    # ------------------------------------------------------- preparación
    # Mismo flujo que la guía del jugador (campana.privado/encargo.objetivo):
    # recoger -> entregar en el puesto -> actividad en pareja -> (caso 1)
    # reparar el Puente 1 -> confirmar en el caldero.
    def _preparacion(self, bot, caso, privado, caldero, memoria):
        encargo = caso.get("encargo") or {}
        yo = bot.identificador
        ronda = caso["ronda"]
        if encargo.get("completo"):
            bot.inicio_reparacion = None
            if not privado.get("preparado"):
                return self._tarea("CONFIRMANDO_CONTINUACION", caldero, "continuar")
            return {"estado": "ESPERANDO_EQUIPO"}
        if encargo.get("materiales_colocados"):
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
