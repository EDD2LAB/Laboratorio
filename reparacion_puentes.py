"""Mecanica local de recoleccion y reparacion de un puente."""

import math

import pygame


class SistemaReparacionPuente:
    """Gestiona el ciclo de reparacion y expone eventos serializables."""

    MATERIALES = ("tablas", "cuerda", "herramientas")
    PLATAFORMAS_MATERIALES = {
        "plataforma_noreste": "tablas",
        "plataforma_suroeste": "cuerda",
        "plataforma_sureste": "herramientas",
    }
    DESPLAZAMIENTOS_SUELO = {
        "plataforma_noreste": (-24, 118),
        "plataforma_suroeste": (53, 75),
        "plataforma_sureste": (-18, 85),
    }
    CONFIGURACION = {
        "aciertos_necesarios": 3,
        "duracion_recorrido_ms": 1200,
        "tolerancia_angulo": 0.30,
        "penalizacion_por_error": 1,
        "duracion_resultado_ms": 350,
        "duracion_animacion_ms": 800,
    }

    def __init__(self, puente, grafo, recursos, estado_guardado=None):
        if puente.get("id") != "puente_1":
            raise ValueError("La reparacion inicial necesita el objeto puente_1.")

        self.puente = puente
        self.grafo = grafo
        self.recursos = recursos
        self.configuracion = dict(self.CONFIGURACION)
        self.estado = "MATERIALS_PENDING"
        self.progreso = 0
        self.tiempo_aguja_ms = 0.0
        self.tiempo_animacion_ms = 0.0
        self.tiempo_resultado_ms = 0.0
        self.estado_indicador = "normal"
        self.mensaje = "Reúne tablas, cuerda y herramientas para reparar el puente."
        self.tiempo_mensaje_ms = 5000.0
        self.hitbox_puente = puente["rect"].copy()
        self.imagen_original = puente["imagen"]
        self.imagen_danada = self._escalar(
            recursos.get("puente_danado"), puente["rect"].size
        )
        self.imagen_reparada = self._escalar(
            recursos.get("puente_reparado"), puente["rect"].size
        )
        self.frames_reparacion = [
            self._escalar_conservar_proporcion(frame, puente["rect"].size)
            for frame in recursos.get("efecto_reparacion", [])
        ]
        self.indicadores = {
            estado: self._escalar(recursos.get(nombre), (220, 220))
            for estado, nombre in (
                ("normal", "indicador_normal"),
                ("acierto", "indicador_acierto"),
                ("error", "indicador_error"),
            )
        }
        self.materiales_recogidos = set()
        self.objetos_recogidos = set()
        self.interacciones = []
        self.objetos = []
        imagenes_materiales = self.recursos.get("materiales")
        if imagenes_materiales is None:
            imagenes_materiales = self.recortar_spritesheet_materiales(
                self.recursos.get("materiales_spritesheet")
            )
        self.recursos["materiales"] = imagenes_materiales
        self._crear_objetos()
        self._establecer_estado_puente()
        if not self.frames_reparacion:
            print("[Reparación] No se cargó EfectoReparacion; se usará la transición sin efecto.")
        for material in self.MATERIALES:
            if self.recursos["materiales"].get(material) is None:
                print(
                    f"[Reparación] Falta la imagen de {material}; "
                    "se omitirá el objeto visual."
                )

        if estado_guardado:
            self.restaurar(estado_guardado)

    @staticmethod
    def _escalar(imagen, tamano):
        if imagen is None:
            return None
        return pygame.transform.scale(imagen, tamano)

    @staticmethod
    def _escalar_conservar_proporcion(imagen, tamano_maximo):
        if imagen is None:
            return None
        escala = min(
            tamano_maximo[0] / imagen.get_width(),
            tamano_maximo[1] / imagen.get_height(),
        )
        tamano = (
            max(1, round(imagen.get_width() * escala)),
            max(1, round(imagen.get_height() * escala)),
        )
        return pygame.transform.scale(imagen, tamano)

    @classmethod
    def recortar_spritesheet_materiales(cls, spritesheet):
        if spritesheet is None:
            raise RuntimeError("No se cargó HerramientasReparación.png.")
        componentes = sorted(
            pygame.mask.from_surface(spritesheet, 1).get_bounding_rects(),
            key=lambda rect: rect.x,
        )
        if len(componentes) != len(cls.MATERIALES):
            raise ValueError(
                "HerramientasReparación.png debe contener exactamente "
                f"{len(cls.MATERIALES)} objetos separados; se encontraron "
                f"{len(componentes)}."
            )
        return {
            material: spritesheet.subsurface(rect).copy()
            for material, rect in zip(cls.MATERIALES, componentes)
        }

    @property
    def bloquea_paso(self):
        return self.estado != "REPAIRED"

    def _posiciones_plataformas(self):
        puente_grafo = self.grafo.puentes[self.puente["id"]]
        extremos_puente = {puente_grafo["origen"], puente_grafo["destino"]}
        posiciones = []
        for id_plataforma, material in self.PLATAFORMAS_MATERIALES.items():
            if id_plataforma in extremos_puente:
                raise ValueError(
                    f"Los materiales no pueden estar en el extremo roto "
                    f"{id_plataforma}."
                )
            plataforma = self.grafo.plataformas.get(id_plataforma)
            if plataforma is None:
                raise ValueError(
                    f"No existe la plataforma para recoger {material}: "
                    f"{id_plataforma}."
                )
            nodo = pygame.Vector2(plataforma["posicion"])
            if 0 <= nodo.x <= 1 and 0 <= nodo.y <= 1:
                nodo.x *= ANCHO_JUEGO
                nodo.y *= ALTO_JUEGO
            desplazamiento = self.DESPLAZAMIENTOS_SUELO[id_plataforma]
            nodo += pygame.Vector2(desplazamiento)
            posiciones.append((id_plataforma, material, nodo))
        return posiciones

    def _crear_objetos(self):
        nombres = {
            "tablas": "Tablas",
            "cuerda": "Cuerda",
            "herramientas": "Canasta de herramientas",
        }
        imagenes = self.recursos.get("materiales", {})

        for id_plataforma, material, posicion in self._posiciones_plataformas():
            rect = pygame.Rect(0, 0, 38, 38)
            rect.midbottom = round(posicion.x), round(posicion.y)
            imagen = self._escalar_conservar_proporcion(
                imagenes.get(material), rect.size
            )
            identificador = f"material_{material}_puente_1"
            activo = identificador not in self.objetos_recogidos
            objeto = {
                "id": identificador,
                "tipo": material,
                "nombre": nombres[material],
                "plataforma": id_plataforma,
                "rect": rect,
                "imagen": imagen,
                "activo": activo,
            }
            self.objetos.append(objeto)
            self.interacciones.append({
                "id": identificador,
                "tipo": "material_reparacion",
                "accion": "recolectar_material",
                "material": material,
                "rect": rect,
                "activo": activo,
                "distancia": 54,
            })

        self.interacciones.append({
            "id": "reparar_puente_1",
            "tipo": "puente_reparable",
            "accion": "reparar_puente",
            "rect": self.puente["rect"].inflate(24, 20),
            "activo": True,
            "distancia": 68,
        })

    @property
    def minijuego_activo(self):
        return self.estado == "REPAIR_MINIGAME"

    def _establecer_estado_puente(self):
        puente_grafo = self.grafo.puentes.get(self.puente["id"])
        if self.estado == "REPAIRED":
            self.puente["imagen"] = self.imagen_reparada or self.imagen_original
            if puente_grafo:
                puente_grafo.update({"estado": "normal", "transitable": True})
        else:
            self.puente["imagen"] = self.imagen_danada or self.imagen_original
            if puente_grafo:
                puente_grafo.update({"estado": "bloqueado", "transitable": False})

    def solicitar_recoleccion(self, identificador):
        objeto = next(
            (item for item in self.objetos if item["id"] == identificador),
            None,
        )
        if objeto is None or not objeto["activo"]:
            return None

        objeto["activo"] = False
        self.materiales_recogidos.add(objeto["tipo"])
        self.objetos_recogidos.add(identificador)
        for interaccion in self.interacciones:
            if interaccion["id"] == identificador:
                interaccion["activo"] = False
                break

        restantes = set(self.MATERIALES) - self.materiales_recogidos
        self.estado = "MATERIALS_PENDING" if restantes else "READY_TO_REPAIR"
        self.mensaje = (
            f"Recogiste {objeto['nombre']}. "
            f"Materiales pendientes: {', '.join(sorted(restantes)) or 'ninguno'}."
        )
        self.tiempo_mensaje_ms = 3200.0
        return {
            "tipo": "material_recolectado",
            "id": identificador,
            "material": objeto["tipo"],
        }

    def iniciar_reparacion(self):
        if self.estado == "REPAIRED":
            return False
        faltantes = set(self.MATERIALES) - self.materiales_recogidos
        if faltantes:
            self.mensaje = (
                "Aún faltan materiales: " + ", ".join(sorted(faltantes)) + "."
            )
            self.tiempo_mensaje_ms = 2600.0
            return False
        if not self.indicadores["normal"]:
            self.mensaje = "Falta el indicador del minijuego; la reparación no está disponible."
            self.tiempo_mensaje_ms = 3200.0
            print("[Reparación] No se cargó el indicador normal.")
            return False

        self.estado = "REPAIR_MINIGAME"
        self.estado_indicador = "normal"
        self.progreso = 0
        self.tiempo_aguja_ms = 0.0
        self.mensaje = "Pulsa E cuando la aguja entre en la zona verde."
        self.tiempo_mensaje_ms = 5000.0
        return True

    def _angulo_aguja(self):
        periodo = self.configuracion["duracion_recorrido_ms"]
        fraccion = (self.tiempo_aguja_ms % periodo) / periodo
        return -math.pi + fraccion * math.pi

    def intentar_reparacion(self):
        if not self.minijuego_activo:
            return None
        objetivo = -math.pi / 3
        diferencia = abs((self._angulo_aguja() - objetivo + math.pi) % math.tau - math.pi)
        if diferencia <= self.configuracion["tolerancia_angulo"]:
            self.progreso += 1
            self.estado_indicador = "acierto"
            self.mensaje = (
                f"¡Buen trabajo! {self.progreso}/"
                f"{self.configuracion['aciertos_necesarios']} aciertos."
            )
            evento = {
                "tipo": "intento_reparacion",
                "puente_id": self.puente["id"],
                "resultado": "acierto",
                "progreso": self.progreso,
            }
            if self.progreso >= self.configuracion["aciertos_necesarios"]:
                self.estado = "REPAIR_ANIMATION"
                self.tiempo_animacion_ms = 0.0
                self.mensaje = "¡Puente listo! La reparación está en marcha."
                evento["estado"] = self.estado
        else:
            self.estado_indicador = "error"
            self.progreso = max(
                0,
                self.progreso - self.configuracion["penalizacion_por_error"],
            )
            self.mensaje = "Casi. Espera la zona verde y vuelve a intentarlo."
            evento = {
                "tipo": "intento_reparacion",
                "puente_id": self.puente["id"],
                "resultado": "error",
                "progreso": self.progreso,
            }
        self.tiempo_resultado_ms = self.configuracion["duracion_resultado_ms"]
        self.tiempo_mensaje_ms = 1800.0
        return evento

    def actualizar(self, delta_ms):
        delta_ms = max(0.0, float(delta_ms))
        if self.tiempo_mensaje_ms > 0:
            self.tiempo_mensaje_ms = max(0.0, self.tiempo_mensaje_ms - delta_ms)
        if self.minijuego_activo:
            self.tiempo_aguja_ms += delta_ms
        if self.tiempo_resultado_ms > 0:
            self.tiempo_resultado_ms = max(0.0, self.tiempo_resultado_ms - delta_ms)
            if self.tiempo_resultado_ms == 0:
                self.estado_indicador = "normal"
        if self.estado == "REPAIR_ANIMATION":
            self.tiempo_animacion_ms += delta_ms
            if self.tiempo_animacion_ms >= self.configuracion["duracion_animacion_ms"]:
                self.estado = "REPAIRED"
                self.mensaje = "Puente reparado. La ruta vuelve a estar abierta."
                self.tiempo_mensaje_ms = 4200.0
                self._establecer_estado_puente()
                for interaccion in self.interacciones:
                    if interaccion["accion"] == "reparar_puente":
                        interaccion["activo"] = False
                        break

    def dibujar_mundo(self, superficie):
        for objeto in self.objetos:
            if not objeto["activo"]:
                continue
            if objeto["imagen"] is not None:
                superficie.blit(objeto["imagen"], objeto["rect"])
        if self.estado == "REPAIR_ANIMATION" and self.frames_reparacion:
            indice = min(
                len(self.frames_reparacion) - 1,
                int(
                    self.tiempo_animacion_ms
                    / self.configuracion["duracion_animacion_ms"]
                    * len(self.frames_reparacion)
                ),
            )
            frame = self.frames_reparacion[indice]
            superficie.blit(frame, frame.get_rect(center=self.puente["rect"].center))

    def dibujar_interfaz(self, superficie, fuente, fuente_titulo):
        inventario = "  ".join(
            f"{'✓' if material in self.materiales_recogidos else '○'} "
            f"{material.capitalize()}"
            for material in self.MATERIALES
        )
        texto = fuente.render(f"Reparación: {inventario}", True, (255, 243, 210))
        panel = pygame.Rect(12, 98, texto.get_width() + 22, 32)
        pygame.draw.rect(superficie, (16, 31, 25), panel, border_radius=6)
        pygame.draw.rect(superficie, (237, 185, 87), panel, 1, border_radius=6)
        superficie.blit(texto, (panel.x + 11, panel.y + 7))

        if self.tiempo_mensaje_ms > 0 and not self.minijuego_activo:
            mensaje = fuente.render(self.mensaje, True, (255, 243, 210))
            caja = mensaje.get_rect(center=(superficie.get_width() // 2, 588)).inflate(24, 14)
            pygame.draw.rect(superficie, (16, 31, 25), caja, border_radius=7)
            pygame.draw.rect(superficie, (237, 185, 87), caja, 1, border_radius=7)
            superficie.blit(mensaje, mensaje.get_rect(center=caja.center))

        if not self.minijuego_activo:
            return

        panel = pygame.Rect(260, 145, 440, 425)
        velo = pygame.Surface(superficie.get_size(), pygame.SRCALPHA)
        velo.fill((0, 0, 0, 105))
        superficie.blit(velo, (0, 0))
        pygame.draw.rect(superficie, (19, 38, 31), panel, border_radius=14)
        pygame.draw.rect(superficie, (237, 185, 87), panel, 3, border_radius=14)
        titulo = fuente_titulo.render("REPARAR EL PUENTE", True, (255, 228, 148))
        superficie.blit(titulo, titulo.get_rect(center=(panel.centerx, panel.y + 30)))

        indicador = self.indicadores.get(self.estado_indicador)
        if indicador:
            rect_indicador = indicador.get_rect(center=(panel.centerx, panel.y + 215))
            superficie.blit(indicador, rect_indicador)
            centro = rect_indicador.center
            angulo = self._angulo_aguja()
            extremo = (
                round(centro[0] + math.cos(angulo) * 78),
                round(centro[1] + math.sin(angulo) * 78),
            )
            pygame.draw.line(superficie, (255, 249, 218), centro, extremo, 5)
            pygame.draw.circle(superficie, (43, 35, 27), centro, 10)
            pygame.draw.circle(superficie, (255, 211, 100), centro, 6)

        estado_texto = fuente.render(
            f"Aciertos: {self.progreso}/"
            f"{self.configuracion['aciertos_necesarios']}    Pulsa E en la zona verde",
            True,
            (255, 243, 210),
        )
        superficie.blit(
            estado_texto,
            estado_texto.get_rect(center=(panel.centerx, panel.bottom - 34)),
        )

    def snapshot(self):
        return {
            "puente_id": self.puente["id"],
            "estado": self.estado,
            "materiales_recogidos": sorted(self.materiales_recogidos),
            "objetos_recogidos": sorted(self.objetos_recogidos),
            "progreso": self.progreso,
            "tiempo_aguja_ms": self.tiempo_aguja_ms,
            "tiempo_animacion_ms": self.tiempo_animacion_ms,
        }

    def restaurar(self, datos):
        if datos.get("puente_id") != self.puente["id"]:
            raise ValueError("El estado guardado no corresponde a este puente.")
        estados_validos = {
            "MATERIALS_PENDING",
            "READY_TO_REPAIR",
            "REPAIR_MINIGAME",
            "REPAIR_ANIMATION",
            "REPAIRED",
        }
        estado = datos.get("estado")
        if estado not in estados_validos:
            raise ValueError(f"Estado de reparación inválido: {estado}")
        self.estado = estado
        self.materiales_recogidos = set(datos.get("materiales_recogidos", ()))
        self.objetos_recogidos = set(datos.get("objetos_recogidos", ()))
        if not self.objetos_recogidos:
            self.objetos_recogidos = {
                next(
                    objeto["id"]
                    for objeto in self.objetos
                    if objeto["tipo"] == material
                )
                for material in self.materiales_recogidos
            }
        self.progreso = max(
            0,
            min(
                self.configuracion["aciertos_necesarios"],
                int(datos.get("progreso", 0)),
            ),
        )
        self.tiempo_aguja_ms = max(0.0, float(datos.get("tiempo_aguja_ms", 0.0)))
        self.tiempo_animacion_ms = max(
            0.0,
            float(datos.get("tiempo_animacion_ms", 0.0)),
        )
        for objeto in self.objetos:
            objeto["activo"] = objeto["id"] not in self.objetos_recogidos
        for interaccion in self.interacciones:
            if interaccion["accion"] == "recolectar_material":
                interaccion["activo"] = interaccion["id"] not in self.objetos_recogidos
            elif interaccion["accion"] == "reparar_puente":
                interaccion["activo"] = self.estado != "REPAIRED"
        self._establecer_estado_puente()


ANCHO_JUEGO = 960
ALTO_JUEGO = 720
