import json
import random
import unittest
import uuid

from logica.expediente_avl import Caso, ExpedienteAVL
from logica.sorteo_partida import SorteoPartida
from multijugador.campana import CASOS, VARIANTES
from multijugador.expediente import ExpedientePartida
from multijugador.movimiento import ColisionesMapa, PartidaMovimiento


class AVLTests(unittest.TestCase):
    def verificar(self, arbol):
        def visitar(nodo, minimo=None, maximo=None):
            if not nodo:
                return 0
            clave = nodo.caso.clave
            self.assertTrue(minimo is None or minimo < clave)
            self.assertTrue(maximo is None or clave < maximo)
            a = visitar(nodo.izquierda, minimo, clave)
            b = visitar(nodo.derecha, clave, maximo)
            self.assertLessEqual(abs(a - b), 1)
            self.assertEqual(nodo.altura, 1 + max(a, b))
            return nodo.altura
        visitar(arbol.raiz)

    def test_cuatro_rotaciones(self):
        for valores in ((3, 2, 1), (1, 2, 3), (3, 1, 2), (1, 3, 2)):
            arbol = ExpedienteAVL()
            for orden, gravedad in enumerate(valores):
                arbol.insertar(Caso(str(gravedad), "Caso", gravedad, orden, {}))
                self.verificar(arbol)
            self.assertEqual(arbol.raiz.caso.gravedad, 2)
            self.assertTrue(arbol.rotaciones)

    def test_muchas_inserciones_y_empates(self):
        orden = list(range(150))
        random.Random(84).shuffle(orden)
        arbol = ExpedienteAVL()
        for i in orden:
            arbol.insertar(Caso(str(i), "Caso", 1 + i % 5, i, {}))
            self.verificar(arbol)
        self.assertEqual(len(arbol.casos), 150)

    def test_actualizar_sin_duplicar_y_sin_cambiar_clave(self):
        arbol = ExpedienteAVL()
        arbol.insertar(Caso("a", "Caso", 2, 0, {"rectificado": False}))
        self.assertFalse(arbol.insertar(Caso("a", "Caso", 2, 0, {"rectificado": True})))
        self.assertEqual(len(arbol.casos), 1)
        with self.assertRaises(ValueError):
            arbol.insertar(Caso("a", "Caso", 3, 0, {}))
        copia = arbol.publico()
        copia["raiz"]["caso"]["datos"].clear()
        self.assertTrue(arbol.raiz.caso.datos["rectificado"])


class RegistroTests(unittest.TestCase):
    def registrar(self, e, evento, revision=1):
        e.registrar(evento, evento, {"evento_id": revision, "opcion": "corregir"}, [{"texto": "Prueba"}])

    def test_ruta_validada_version_y_turno_compartido(self):
        e = ExpedientePartida()
        self.registrar(e, "puente_norte")
        self.registrar(e, "agua")
        datos = dict(caso="agua", revision=e.revision, paso=0, direccion="izquierda")
        with self.assertRaises(ValueError):
            e.paso_insercion(datos)
        self.assertEqual(e.paso, 0)
        datos["direccion"] = "derecha"
        e.paso_insercion(datos)
        with self.assertRaises(ValueError):
            e.paso_insercion(datos)
        self.assertEqual(e.arbol.publico()["total"], 2)

    def test_rectificacion_actualiza_caso_pendiente_y_archivado(self):
        e = ExpedientePartida()
        self.registrar(e, "puente_norte")
        self.registrar(e, "puente_norte", 2)
        self.assertEqual(e.arbol.publico()["total"], 1)
        self.assertEqual(e.arbol.casos["puente_norte"].datos["resultado"]["evento_id"], 2)
        self.registrar(e, "agua")
        self.registrar(e, "agua", 3)
        self.assertEqual(len(e.pendientes), 1)
        self.assertEqual(e.pendientes[0].datos["resultado"]["evento_id"], 3)

    def test_cola_completa_y_rotaciones_sin_revelar_ruta(self):
        e = ExpedientePartida()
        for evento in ("puente_norte", "agua", "tormenta", "ayuda"):
            self.registrar(e, evento)
        while e.pendientes:
            caso = e.pendientes[0]
            ruta = e.arbol.ruta_insercion(caso)
            estado = e.publico()
            self.assertNotIn("direccion", estado)
            e.paso_insercion(dict(caso=caso.id, revision=e.revision, paso=e.paso,
                                 direccion=ruta[e.paso]["direccion"]))
        self.assertEqual(e.publico()["total"], 4)
        AVLTests().verificar(e.arbol)


class SorteoTests(unittest.TestCase):
    def test_semilla_reproduce_variantes_y_acusacion_sin_azar_global(self):
        random.seed(111)
        antes = random.getstate()
        a = SorteoPartida(935).casos(CASOS, VARIANTES)
        self.assertEqual(random.getstate(), antes)
        self.assertEqual(a, SorteoPartida(935).casos(CASOS, VARIANTES))
        variantes = {tuple(c[3] for c in SorteoPartida(i).casos(CASOS, VARIANTES)) for i in range(30)}
        self.assertEqual(len(variantes), 4)
        self.assertEqual(a[-1][3], "corregir")
        self.assertEqual(CASOS[-1][4]["aspirante"][0], "Inventario de Mira")

    def test_rechaza_semillas_invalidas(self):
        for semilla in (True, -1, 2**64, "123"):
            with self.assertRaises(ValueError):
                SorteoPartida(semilla)


class IntegracionTests(unittest.TestCase):
    def crear(self):
        return PartidaMovimiento([{"id": "a", "nombre": "A", "rol": "guardian"},
                                  {"id": "b", "nombre": "B", "rol": "habitante"}], 0,
                                 ColisionesMapa({"hitboxes": [], "decoracion": []}), semilla=89)

    def test_resolucion_registra_solo_pruebas_halladas_y_no_filtra_semilla(self):
        p = self.crear()
        m = p.mision
        m.halladas["pista_guardian"] = "a"
        m.votos = {"a": "corregir", "b": "corregir"}
        m.resolver(p.conectados)
        m.resolver(p.conectados)
        publico = m.publico(p.conectados)
        self.assertEqual(publico["expediente"]["total"], 1)
        pruebas = publico["expediente"]["raiz"]["caso"]["datos"]["pruebas"]
        self.assertEqual([prueba["id"] for prueba in pruebas], ["pista_guardian"])
        self.assertNotIn("semilla", json.dumps(publico))
        self.assertNotIn("Informe vigente", json.dumps(publico))
        self.assertIsNone(publico["expediente"]["raiz"]["caso"]["datos"]["ley"])

    def test_solicitud_repetida_y_desconexion(self):
        p = self.crear()
        e = p.mision.expediente
        for evento in ("puente_norte", "agua"):
            e.registrar(evento, evento, {"evento_id": evento}, [])
        solicitud = dict(accion="expediente_paso", id_solicitud=uuid.uuid4().hex,
                         caso="agua", revision=1, paso=0, direccion="derecha")
        a = p.actuar("a", solicitud, 0)
        self.assertTrue(a["ok"])
        self.assertEqual(a, p.actuar("a", solicitud, 0))
        self.assertEqual(len(e.arbol.casos), 2)
        e.registrar("tormenta", "Tormenta", {"evento_id": 3}, [])
        p.conectados.discard("b")
        solicitud.update(id_solicitud=uuid.uuid4().hex, caso="tormenta", revision=e.revision, paso=0)
        self.assertFalse(p.actuar("b", solicitud, 0)["ok"])

    def test_aviso_temporal_caduca_no_se_rejuvenece_al_compartir_y_se_renueva_en_fuente(self):
        p = self.crear()
        m = p.mision
        m.ronda = 1
        m.pruebas = m.casos[1][4]
        m.metadatos_pruebas = m._metadatos(m.pruebas)
        m.correcta = m.casos[1][3]
        def accion(i, nombre, **datos):
            return p.actuar(i, dict(accion=nombre, ronda=1, id_solicitud=uuid.uuid4().hex, **datos), p.ultima)
        fuente = next(o for o in m.objetivos if o.get("rol") == "guardian")
        p.jugadores["a"].update(x=fuente["x"], y=fuente["y"])
        self.assertTrue(accion("a", "interactuar", objetivo=fuente["id"])["ok"])
        aviso = m.avisos_recientes["a"]["pista_guardian"]
        vencimiento = aviso["vence"]
        self.assertIn(vencimiento, (90, 120, 150))
        self.assertFalse(m.privado("b")["inventario"])
        p.jugadores["b"].update(x=fuente["x"], y=fuente["y"])
        m.reloj = 10
        self.assertTrue(accion("a", "entregar", pista="pista_guardian", destinatario="b", medio="directo")["ok"])
        self.assertEqual(m.avisos_recientes["b"]["pista_guardian"]["vence"], vencimiento)
        m.reloj = vencimiento
        tarjeta = m.privado("b")["inventario"][0]
        self.assertFalse(tarjeta["temporal"]["vigente"])
        self.assertNotIn(aviso["texto"], tarjeta["temporal"]["texto"])
        self.assertEqual(tarjeta["texto"], m.pruebas["guardian"][1])
        m.avisos_recientes["b"].clear()
        self.assertTrue(accion("a", "entregar", pista="pista_guardian", destinatario="b", medio="directo")["ok"])
        self.assertFalse(m.avisos_recientes["b"])
        self.assertTrue(accion("a", "interactuar", objetivo=fuente["id"])["ok"])
        self.assertGreater(m.avisos_recientes["a"]["pista_guardian"]["vence"], vencimiento)

    def test_tutorial_no_tiene_pistas_con_caducidad(self):
        p = self.crear()
        m = p.mision
        fuente = next(o for o in m.objetivos if o.get("rol") == "guardian")
        p.jugadores["a"].update(x=fuente["x"], y=fuente["y"])
        m.actuar("a", dict(accion="interactuar", objetivo=fuente["id"], id_solicitud=uuid.uuid4().hex), 0, p.conectados)
        self.assertFalse(m.avisos_recientes["a"])
