"""Features del modo de un jugador portadas al multijugador."""
import json
import os
import unittest
import uuid

import test_campana_copa as campana_pruebas
from logica.Arboles import ARBOL_CATEGORIAS
from multijugador import clasificacion
from multijugador.campana import CASOS, VARIANTES
from multijugador.dimensiones_red import LA_COPA, PRESENTE, jugadores_visibles
from multijugador.movimiento import ColisionesMapa, PartidaMovimiento
from multijugador.presentacion import (COLOR_ROJO, COLOR_VERDE, POLARIDAD, TIPOS_POCION, color_cambio,
                                       tipo_pocion)
from multijugador.protocolo import MAX_MENSAJE
from multijugador.suministros import EncargoSuministros

ROLES = ("guardian", "mensajero", "habitante", "aspirante")


def crear(n=2, mapa_real=False):
    jugadores = [dict(id=str(i), nombre="J" + str(i), rol=ROLES[i]) for i in range(n)]
    return PartidaMovimiento(jugadores, 0, None if mapa_real else ColisionesMapa({"hitboxes": [], "decoracion": []}))


def Ayuda():
    """Ayudantes de test_campana_copa (sin volver a ejecutar sus pruebas)."""
    return campana_pruebas.CampanaTests()


class PocionesTests(unittest.TestCase):
    def test_cada_opcion_de_los_cuatro_eventos_tiene_tipo_de_pocion(self):
        p = crear()
        for caso in list(CASOS) + list(VARIANTES.values()):
            self.assertIn(caso[3], p.mision.opciones)
        for opcion in p.mision.opciones:
            self.assertIn(tipo_pocion(opcion), TIPOS_POCION)
        publico = p.mision.publico(p.conectados)
        self.assertEqual(set(publico["tipos_pocion"]), set(publico["opciones"]))
        self.assertEqual(publico["tipos_pocion"], {"corregir": "quemar", "difundir": "colgar", "descartar": "ignorar"})

    def test_el_servidor_difunde_la_pocion_una_sola_vez_por_decision(self):
        h, p = Ayuda(), crear()
        h.preparar(p)
        for i in p.jugadores:
            h.accion(p, i, "votar", opcion="difundir")
        resultado = dict(p.mision.resultado)
        self.assertEqual(resultado["tipo_pocion"], "colgar")
        for _ in range(5):  # nuevas resoluciones y estados no crean otro evento
            p.actualizar(p.ultima + 1)
            p.mision.resolver(p.conectados)
        self.assertEqual(p.mision.resultado["evento_id"], resultado["evento_id"])
        avisos = [a for a in p.mision.privado("0")["avisos"] if a["tipo"] == "resultado"]
        self.assertEqual(len(avisos), 1)
        # Rectificar crea una decisión nueva con un evento nuevo.
        for i in p.jugadores:
            p.jugadores[i].update(x=480, y=380)
        h.accion(p, "0", "rectificar")
        for i in p.jugadores:
            h.accion(p, i, "votar", opcion="corregir")
        self.assertEqual(p.mision.resultado["tipo_pocion"], "quemar")
        self.assertGreater(p.mision.resultado["evento_id"], resultado["evento_id"])


class ClasificacionTests(unittest.TestCase):
    def test_cada_evento_tiene_categoria_valida_y_ruta_reconstruible(self):
        for evento in [c[0] for c in CASOS] + ["presente_video", "presente_voz", "presente_foto"]:
            nodo = clasificacion.nodo_evento(evento)
            self.assertTrue(nodo.es_hoja())
            ruta = clasificacion.ruta_evento(evento)
            self.assertEqual(ruta[0], "Tablilla")
            self.assertEqual(tuple(ruta[1:]), clasificacion.CATEGORIA_EVENTO[evento])
            padre = nodo
            while padre.padre is not None:
                self.assertIn(padre, padre.padre.subcategorias)
                padre = padre.padre

    def test_categorias_nuevas_no_cambian_el_arbol_del_modo_un_jugador(self):
        self.assertEqual([n.nombre for n in ARBOL_CATEGORIAS.subcategorias],
                         ["Rumor Politico", "Suceso Natural", "Acusacion Personal"])
        nuevas = [n for n in clasificacion.ARBOL.subcategorias if n.nombre in ("Aviso Comunitario", "Contenido Digital")]
        self.assertEqual(len(nuevas), 2)
        for nodo in nuevas:
            self.assertIs(nodo.padre, clasificacion.ARBOL)

    def test_clasificar_valida_suma_sabiduria_y_no_se_repite(self):
        h, p = Ayuda(), crear()
        self.assertFalse(h.accion(p, "0", "clasificar", categoria="Rumor Político")["ok"])  # aún sin decisión
        h.preparar(p)
        for i in p.jugadores:
            h.accion(p, i, "votar", opcion="corregir")
        antes = p.mision.indicadores["sabiduria"]
        self.assertTrue(h.accion(p, "0", "clasificar", categoria="Rumor Político")["ok"])
        self.assertFalse(h.accion(p, "0", "clasificar", categoria="Suceso Natural")["ok"])
        self.assertTrue(h.accion(p, "1", "clasificar", categoria="Suceso Natural")["ok"])
        self.assertFalse(h.accion(p, "1", "clasificar", categoria="Inventada")["ok"])
        self.assertEqual(p.mision.indicadores["sabiduria"], antes)  # +5 y -5
        self.assertTrue(p.mision.privado("0")["clasificacion"]["correcta"])
        self.assertFalse(p.mision.privado("1")["clasificacion"]["correcta"])


class PuenteYMaterialesTests(unittest.TestCase):
    def test_evento_1_exige_tres_materiales_con_1_2_3_y_4_jugadores(self):
        for n in range(1, 5):
            with self.subTest(jugadores=n):
                p = crear(n)
                e = p.mision.encargo
                self.assertEqual([m[0] for m in e.config["materiales"]], ["tablas", "cuerdas", "herramientas"])
                for indice, (material, _, fuente) in enumerate(e.config["materiales"]):
                    self.assertFalse(e.materiales_listos)
                    jugador = str(indice % n)
                    e.recoger(jugador, fuente, material)
                    e.entregar(jugador)
                self.assertTrue(e.materiales_listos)
                self.assertEqual(len(e.entregados), 3)

    def test_material_no_se_recoge_dos_veces_ni_por_dos_jugadores(self):
        h, p = Ayuda(), crear(2)
        h.preparar(p)
        for i in p.jugadores:
            h.accion(p, i, "votar", opcion="corregir")
        e = p.mision.encargo
        f = e.fuente("herramientas")
        for i in p.jugadores:
            p.jugadores[i].update(x=f["x"], y=f["y"])
        self.assertTrue(h.accion(p, "0", "recoger_suministro", objetivo=f["id"], material="herramientas")["ok"])
        self.assertFalse(h.accion(p, "1", "recoger_suministro", objetivo=f["id"], material="herramientas")["ok"])
        p.jugadores["0"].update(x=e.destino["x"], y=e.destino["y"])
        self.assertTrue(h.accion(p, "0", "depositar")["ok"])
        p.jugadores["0"].update(x=f["x"], y=f["y"])
        self.assertFalse(h.accion(p, "0", "recoger_suministro", objetivo=f["id"], material="herramientas")["ok"])
        publico = p.mision.publico(p.conectados)["encargo"]
        self.assertTrue(next(m for m in publico["materiales"] if m["id"] == "herramientas")["entregado"])

    def test_puente_1_roto_reparado_con_3_aciertos_y_una_sola_vez(self):
        h, p = Ayuda(), crear(2)
        puente = p.mision.puente
        self.assertEqual(puente.estado, "DAMAGED")
        self.assertEqual(p.colisiones.bloqueos, [puente.rect])
        self.assertFalse(puente.publico()["arista"]["transitable"])
        x, y, w, hh = puente.rect
        self.assertTrue(p.colisiones.bloqueado(x + w / 2, y + hh / 2))
        h.preparar(p)
        for i in p.jugadores:
            h.accion(p, i, "votar", opcion="corregir")
        for i in ("0", "1"):
            h.fuente(p, i)
            h.accion(p, i, "recoger_suministro")
            d = p.mision.encargo.destino
            p.jugadores[i].update(x=d["x"], y=d["y"])
            h.accion(p, i, "depositar")
        h.completar_materiales(p)
        ids = list(p.jugadores)
        for i in ids:
            p.jugadores[i].update(x=d["x"], y=d["y"])
        h.accion(p, ids[0], "sujetar")
        for _ in range(3):
            p.actualizar(p.ultima + 1)
            h.accion(p, ids[1], "trabajar")
        e = p.mision.encargo
        self.assertTrue(e.materiales_colocados)
        self.assertFalse(e.completo)  # colocar materiales no gana el evento
        p.actualizar(p.ultima + 1)
        self.assertEqual(puente.estado, "READY_TO_REPAIR")
        self.assertFalse(h.accion(p, "0", "continuar")["ok"])
        o = p.mision.objetivo_puente
        for i in ids:
            p.jugadores[i].update(x=o["x"], y=o["y"])
        self.assertEqual(h.accion(p, "0", "interactuar", objetivo="puente_1")["vista"], "reparar")
        self.assertFalse(h.accion(p, "1", "interactuar", objetivo="puente_1")["ok"])  # ya en reparación
        # Un error resta progreso como en el modo de un jugador.
        p.actualizar(p.ultima + 1)
        self.assertTrue(h.accion(p, "0", "intento_reparacion", tiempo_aguja_ms=campana_pruebas.tiempo_acierto(puente))["ok"])
        self.assertEqual(puente.progreso, 1)
        p.actualizar(p.ultima + 1)
        from multijugador.reparacion import angulo_aguja, dentro_de_zona
        inicio = int(puente.ultimo_tiempo_aguja) + 1
        fallo = next(t for t in range(inicio, inicio + 1200) if not dentro_de_zona(angulo_aguja(t), puente.progreso))
        self.assertEqual(h.accion(p, "0", "intento_reparacion", tiempo_aguja_ms=fallo)["resultado"], "error")
        self.assertEqual(puente.progreso, 0)
        # Desconexión: el minijuego se libera sin perder los materiales.
        p.conectados.discard("0")
        p.actualizar(p.ultima + 1)
        self.assertIsNone(puente.reparador)
        self.assertTrue(e.materiales_colocados)
        p.conectados.add("0")
        h.reparar_puente(p, "1")
        self.assertEqual(puente.estado, "REPAIRED")
        self.assertEqual(p.colisiones.bloqueos, [])
        self.assertTrue(puente.publico()["arista"]["transitable"])
        self.assertTrue(e.completo)
        self.assertNotIn("vista", h.accion(p, "0", "interactuar", objetivo="puente_1"))
        self.assertEqual(puente.estado, "REPAIRED")

    def test_intento_fuera_de_tiempo_o_de_otro_jugador_se_rechaza(self):
        from multijugador.reparacion import PuenteRed
        puente = PuenteRed({})
        jugadores = {"a": {"x": 390, "y": 390, "nombre": "A"}, "b": {"x": 390, "y": 390, "nombre": "B"}}
        with self.assertRaises(ValueError):
            puente.abrir("a", jugadores, 0)  # faltan materiales
        puente.preparar(True)
        puente.abrir("a", jugadores, 0)
        with self.assertRaises(ValueError):
            puente.intentar("b", 100, 1)
        with self.assertRaises(ValueError):
            puente.intentar("a", 999999, 1)
        with self.assertRaises(ValueError):
            puente.intentar("a", float("nan"), 1)


class IndicadoresTests(unittest.TestCase):
    def test_polaridad_de_colores(self):
        buenos = [k for k, v in POLARIDAD.items() if v == "bueno"]
        malos = [k for k, v in POLARIDAD.items() if v == "malo"]
        self.assertEqual(set(buenos), {"sabiduria", "confianza", "armonia"})
        self.assertEqual(set(malos), {"susurros_falsos", "desinformacion"})
        for nombre in buenos:
            self.assertEqual(color_cambio(nombre, 5), COLOR_VERDE)
            self.assertEqual(color_cambio(nombre, -5), COLOR_ROJO)
        for nombre in malos:
            self.assertEqual(color_cambio(nombre, 5), COLOR_ROJO)
            self.assertEqual(color_cambio(nombre, -5), COLOR_VERDE)

    def test_mismos_indicadores_y_valores_iniciales_que_un_jugador(self):
        from logica.logica_juego import EstadoJuego
        inicial = EstadoJuego().indicadores
        p = crear()
        equivalencias = {"sabiduria": "sabiduria", "confianza": "confianza_consejo", "armonia": "armonia",
                         "susurros_falsos": "susurros_falsos", "desinformacion": "desinformación"}
        self.assertEqual({k: p.mision.indicadores[k] for k in equivalencias},
                         {k: inicial[v] for k, v in equivalencias.items()})


class PortalTests(unittest.TestCase):
    def ir_al_portal(self, p, i):
        x, y, w, h = p.estado(i)["portales"][p.jugadores[i]["dimension"]]
        destino = p.colisiones_de(p.jugadores[i]["dimension"]).inicio_libre(x - 10, y + h)
        p.jugadores[i].update(x=destino[0], y=destino[1])

    def viajar(self, p, i, destino):
        """Viaje en grupo: ``i`` propone y luego aceptan los demás humanos de su dimensión."""
        origen = p.jugadores[i]["dimension"]
        orden = [i] + [j for j in p.jugadores if j != i and p.jugadores[j]["dimension"] == origen]
        acuse = None
        for j in orden:
            self.ir_al_portal(p, j)
            acuse = p.actuar(j, dict(accion="usar_portal", destino=destino, ronda=p.mision.ronda,
                                     id_solicitud=uuid.uuid4().hex), p.ultima)
            if not acuse["ok"]:
                return acuse
        return acuse

    def test_el_equipo_viaja_junto_solo_si_todos_aceptan(self):
        p = crear(2, mapa_real=True)
        self.ir_al_portal(p, "0")
        primero = p.actuar("0", dict(accion="usar_portal", destino=PRESENTE, ronda=0, id_solicitud=uuid.uuid4().hex), 0)
        self.assertTrue(primero["ok"])
        self.assertEqual(p.jugadores["0"]["dimension"], LA_COPA)  # espera al compañero
        self.assertEqual(p.estado("1")["viaje"]["faltan"], ["B"] if p.jugadores["1"]["nombre"] == "B" else [p.jugadores["1"]["nombre"]])
        # Cancelar retira la aceptación.
        p.actuar("0", dict(accion="cancelar_portal", ronda=0, id_solicitud=uuid.uuid4().hex), 0)
        self.assertIsNone(p.estado("0")["viaje"])
        self.assertTrue(self.viajar(p, "0", PRESENTE)["ok"])
        self.assertEqual({j["dimension"] for j in p.jugadores.values()}, {PRESENTE})

    def test_alejarse_del_portal_retira_la_aceptacion(self):
        p = crear(2, mapa_real=True)
        self.ir_al_portal(p, "0")
        p.actuar("0", dict(accion="usar_portal", destino=PRESENTE, ronda=0, id_solicitud=uuid.uuid4().hex), 0)
        p.jugadores["0"].update(x=480, y=420)
        p.actualizar(p.ultima + .1)
        self.assertIsNone(p.viaje)

    def test_bots_viajan_y_te_dejan_todas_las_pistas(self):
        from multijugador.partida_local import ClienteCampanaLocal
        cliente = ClienteCampanaLocal("Prueba", "guardian")
        p = cliente._partida
        self.ir_al_portal(p, "local")
        cliente.actuar("usar_portal", destino=PRESENTE)
        self.assertEqual({j["dimension"] for j in p.jugadores.values()}, {PRESENTE})
        for _ in range(500):
            cliente.actualizar(.15)
        presente = p.mision.presente
        self.assertEqual(presente.halladas, {})  # las pistas las reúne la persona
        self.assertIsNone(presente.resultado)  # la decisión no la toman ellos
        humano = p.jugadores["local"]
        for identificador, bot in cliente._bots.bots.items():
            # Quien aún tiene una pista espera dentro de su edificio; los demás acompañan.
            self.assertIn(bot.estado, ("ACOMPANANDO", "ESPERANDO_EN_SU_EDIFICIO"))
            j = p.jugadores[identificador]
            if bot.estado == "ACOMPANANDO":
                self.assertLessEqual(((j["x"] - humano["x"]) ** 2 + (j["y"] - humano["y"]) ** 2) ** .5, 110)
        cliente.cerrar()

    def test_con_dos_personas_los_bots_con_pista_las_esperan_dentro(self):
        from bots.gestor_bots import GestorBots
        roles = ("guardian", "mensajero", "habitante", "aspirante")
        p = PartidaMovimiento([dict(id=str(i), nombre=str(i), rol=roles[i]) for i in range(2)]
                              + [dict(id="bot_" + r, nombre=r, rol=r, controlador="bot") for r in roles[2:]], 0)
        gestor = GestorBots(p, {"0", "1"})
        p.colisiones_de(PRESENTE)
        p._viajar_equipo(LA_COPA, PRESENTE)
        ahora = 0
        for _ in range(500):
            ahora += .15
            p.actualizar(ahora)
            gestor.actualizar(ahora, .15)
        # Tomás y Ronaldo son bots: guardan su pista y esperan en su edificio.
        self.assertEqual(p.mision.presente.halladas, {})
        self.assertEqual(p.jugadores["bot_habitante"]["interior"], "estacion_mensajero")
        self.assertEqual(p.jugadores["bot_aspirante"]["interior"], "sede_aspirante")

    def test_portal_funciona_antes_y_despues_y_conserva_indicadores(self):
        h, p = Ayuda(), crear(2, mapa_real=True)
        self.assertFalse(p.mision.publico(p.conectados)["dimension_completa"])
        p.mision.indicadores["confianza"] = 77
        lejos = p.actuar("0", dict(accion="usar_portal", destino=PRESENTE, ronda=0, id_solicitud=uuid.uuid4().hex), 0)
        self.assertFalse(lejos["ok"])
        self.assertTrue(self.viajar(p, "0", PRESENTE)["ok"])
        self.assertEqual(p.jugadores["0"]["dimension"], PRESENTE)
        self.assertFalse(p.mapas[PRESENTE].bloqueado(p.jugadores["0"]["x"], p.jugadores["0"]["y"]))
        self.assertEqual(p.mision.indicadores["confianza"], 77)
        self.assertTrue(self.viajar(p, "0", "futuro")["ok"])  # viaje libre
        self.assertFalse(self.viajar(p, "0", "futuro")["ok"])  # ya está allí
        self.assertTrue(self.viajar(p, "0", LA_COPA)["ok"])
        self.assertEqual(p.jugadores["0"]["dimension"], LA_COPA)
        self.assertFalse(p.colisiones.bloqueado(p.jugadores["0"]["x"], p.jugadores["0"]["y"]))
        # Tras completar La Copa el portal sigue funcionando igual.
        for ronda, caso in enumerate(p.mision.casos):
            h.preparar(p)
            for i in p.jugadores:
                h.accion(p, i, "votar", opcion=caso[3])
            if ronda < 3:
                h.avanzar(p)
        self.assertTrue(p.mision.publico(p.conectados)["dimension_completa"])
        valores = dict(p.mision.indicadores)
        self.assertTrue(self.viajar(p, "1", PRESENTE)["ok"])
        self.assertEqual(p.mision.indicadores, valores)

    def test_flecha_solo_al_completar_los_cuatro_eventos(self):
        h, p = Ayuda(), crear(2)
        for ronda, caso in enumerate(p.mision.casos):
            self.assertFalse(p.mision.publico(p.conectados)["dimension_completa"])
            h.preparar(p)
            for i in p.jugadores:
                h.accion(p, i, "votar", opcion=caso[3])
            if ronda < 3:
                self.assertFalse(p.mision.publico(p.conectados)["dimension_completa"])
                h.avanzar(p)
        self.assertTrue(p.mision.publico(p.conectados)["dimension_completa"])

    def test_quien_cambia_de_dimension_no_se_ve_ni_interactua_en_la_anterior(self):
        p = crear(2, mapa_real=True)
        # El portal mueve al equipo completo; aquí se simula un jugador que
        # quedó en otra dimensión (p. ej., al reconectarse) para la visibilidad.
        x, y = p.colisiones_de(PRESENTE).inicio_libre(480, 620)
        p.jugadores["0"].update(dimension=PRESENTE, x=x, y=y)
        jugadores = p.estado("1")["jugadores"]
        self.assertEqual([j["id"] for j in jugadores_visibles(jugadores, LA_COPA)], ["1"])
        self.assertEqual([j["id"] for j in jugadores_visibles(jugadores, PRESENTE)], ["0"])
        self.assertEqual(len(jugadores), 2)  # sin duplicados
        self.assertEqual(p.presentes_en(LA_COPA), {"1"})
        # Aunque comparta coordenadas, no puede usar objetos de La Copa.
        caldero = next(o for o in p.mision.objetivos if o["id"] == "caldero")
        p.jugadores["0"].update(x=caldero["x"], y=caldero["y"])
        self.assertFalse(p.mision._cerca("0", caldero))

    def test_mision_presente_pistas_decision_y_clasificacion(self):
        p = crear(2, mapa_real=True)
        self.assertTrue(self.viajar(p, "0", PRESENTE)["ok"])
        m = p.mision.presente
        accion = lambda **d: p.actuar("0", dict(ronda=p.mision.ronda, id_solicitud=uuid.uuid4().hex, **d), p.ultima)
        pantalla = m.objetivos[-1]
        p.jugadores["0"].update(x=pantalla["x"], y=pantalla["y"])
        self.assertFalse(accion(accion="presente_votar", opcion="verificar")["ok"])  # faltan pistas
        for n in [n for n in p.mision.dialogos.publico() if n["dimension"] == PRESENTE and n.get("pista")]:
            p.jugadores["0"].update(x=n["x"], y=n["y"], interior=n.get("interior"))
            self.assertTrue(accion(accion="hablar_npc", npc=n["id"])["ok"])
        p.jugadores["0"].update(x=pantalla["x"], y=pantalla["y"], interior=None)
        self.assertTrue(accion(accion="presente_analizar")["ok"])
        for frame in (0, 5):
            self.assertTrue(accion(accion="presente_marcar", frame=frame)["ok"])
        antes = dict(p.mision.indicadores)
        self.assertTrue(accion(accion="presente_votar", opcion="verificar")["ok"])
        # El equipo viajó junto: la pantalla pública espera el voto del compañero.
        self.assertFalse(m.completada)
        p.jugadores["1"].update(x=pantalla["x"], y=pantalla["y"])
        self.assertTrue(p.actuar("1", dict(accion="presente_votar", opcion="verificar", ronda=p.mision.ronda,
                                           id_solicitud=uuid.uuid4().hex), p.ultima)["ok"])
        self.assertTrue(m.completada)
        self.assertEqual(m.resultado["tipo_pocion"], "consultar")
        self.assertEqual(p.mision.indicadores["desinformacion"], max(0, antes["desinformacion"] - 5))
        self.assertTrue(accion(accion="presente_clasificar", categoria="Contenido manipulado")["ok"])
        self.assertTrue(p.mision.privado("0")["presente"]["clasificacion"]["correcta"])
        self.assertTrue(p.mision.publico(p.presentes_en(LA_COPA))["presente"]["completada"])

    def test_estado_cabe_en_el_protocolo_lan(self):
        h, p = Ayuda(), crear(4, mapa_real=True)
        for ronda, caso in enumerate(p.mision.casos):
            h.preparar(p)
            for i in p.jugadores:
                h.accion(p, i, "votar", opcion=caso[3])
            if ronda < 3:
                h.avanzar(p)
        # También debe caber el libro completo, no solo el primer caso y su cola.
        expediente = p.mision.expediente
        while expediente.pendientes:
            caso = expediente.pendientes[0]
            ruta = expediente.arbol.ruta_insercion(caso)
            expediente.paso_insercion(dict(caso=caso.id, revision=expediente.revision,
                                          paso=expediente.paso, direccion=ruta[expediente.paso]["direccion"]))
        self.assertEqual(expediente.publico()["total"], 4)
        tamano = len(json.dumps({"mundo": p.estado("0")}, ensure_ascii=False).encode())
        self.assertLess(tamano, MAX_MENSAJE)


class VistaClienteTests(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        import pygame
        self.pygame = pygame
        pygame.init()
        pygame.display.set_mode((960, 720))

    def tearDown(self):
        self.pygame.quit()

    def test_la_animacion_de_pocion_se_reproduce_una_vez_por_evento(self):
        from interfaz.partida_multijugador import VistaPartida
        h, p = Ayuda(), PartidaMovimiento([dict(id="0", nombre="A", rol="guardian"), dict(id="1", nombre="B", rol="habitante")], 0)
        v = VistaPartida("0", {"mundo": p.estado("0")})
        h.preparar(p)
        for i in p.jugadores:
            h.accion(p, i, "votar", opcion="corregir")
        v.recibir({"mundo": p.estado("0")})
        self.assertIsNotNone(v.animacion_pocion)
        self.assertEqual(v.animacion_pocion.datos["clave"], "quemar")
        v.animacion_pocion = None
        for _ in range(3):  # el mismo evento llega varias veces
            v.recibir({"mundo": p.estado("0")})
        self.assertIsNone(v.animacion_pocion)
        self.assertFalse(v.dimension_completa())

    def test_cliente_cambia_de_mapa_y_oculta_a_la_otra_dimension(self):
        from interfaz.partida_multijugador import VistaPartida
        p = PartidaMovimiento([dict(id="0", nombre="A", rol="guardian"), dict(id="1", nombre="B", rol="habitante")], 0)
        v = VistaPartida("0", {"mundo": p.estado("0")})
        self.assertEqual(set(v.jugadores), {"0", "1"})
        PortalTests.ir_al_portal(None, p, "0")
        p.actuar("0", dict(accion="usar_portal", destino=PRESENTE, ronda=0, id_solicitud=uuid.uuid4().hex), 0)
        v.recibir({"mundo": p.estado("0")})
        self.assertEqual(v.dimension, LA_COPA)  # falta que acepte el compañero
        lienzo = self.pygame.Surface((960, 720))
        v.dibujar(lienzo, "T")  # aviso del viaje propuesto
        PortalTests.ir_al_portal(None, p, "1")
        p.actuar("1", dict(accion="usar_portal", destino=PRESENTE, ronda=0, id_solicitud=uuid.uuid4().hex), 0)
        v.recibir({"mundo": p.estado("0")})
        self.assertEqual(v.dimension, PRESENTE)
        self.assertEqual(set(v.jugadores), {"0", "1"})  # el equipo viajó junto
        yo = p.jugadores["0"]
        self.assertEqual(tuple(v.jugadores["0"]["posicion"]), (yo["x"], yo["y"]))  # sin recorrer el mapa
        self.assertIsNotNone(v.transicion)
        lienzo = self.pygame.Surface((960, 720))
        v.dibujar(lienzo, "T")
        v.panel.abrir("portal")
        v.dibujar(lienzo, "T")
        self.assertIn("viajar:la_copa", v.panel.botones)
        self.assertFalse(v.panel.botones["viajar:futuro"].desactivado)


if __name__ == "__main__":
    unittest.main()
