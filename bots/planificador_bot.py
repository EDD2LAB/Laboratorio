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
            if not privado.get("suministro"):
                return self._tarea("YENDO_POR_SUMINISTRO", objetivo_rol, "interactuar", objetivo=objetivo_rol["id"])
            if not privado.get("depositado"):
                return self._tarea("YENDO_AL_CALDERO", caldero, "interactuar", objetivo=caldero["id"])
            if not privado.get("preparado"):
                return self._tarea("CONFIRMANDO_CONTINUACION", caldero, "continuar")
            return {"estado": "ESPERANDO_EQUIPO"}

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
    def _tarea(estado, destino, accion, **datos):
        marca_compartida = datos.pop("marca_compartida", None)
        marca_voto = datos.pop("marca_voto", None)
        return {
            "estado": estado,
            "destino": dict(destino),
            "accion": accion,
            "datos": datos,
            "marca_compartida": marca_compartida,
            "marca_voto": marca_voto,
        }
