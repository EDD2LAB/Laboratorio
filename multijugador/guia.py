"""Aprendizaje y ayuda entre jugadores; no revela soluciones ni pistas ajenas."""
import math


class GuiaCooperativa:
    def __init__(self, jugadores):
        self.tutoriales = {i: {"estado": "pendiente", "paso": 0} for i in jugadores}
        self.pedidos = {}
        self.ultimo_pedido = {}
        self.estrellas = set()

    def tutorial(self, mision, i, solicitud):
        accion = solicitud.get("accion")
        t = self.tutoriales[i]
        if accion == "saltar_tutorial":
            t.update(estado="terminado", paso=3)
            return {"mensaje": "¡Listo! Sigue tu tarea del mapa."}
        if accion == "iniciar_tutorial":
            if mision.ronda or mision.fase != "investigacion" or t["estado"] == "terminado":
                raise ValueError("Ya sabes jugar. Sigue la tarea del mapa.")
            if t["estado"] == "pendiente":
                j = mision.jugadores[i]
                t.update(estado="activo", paso=0, origen=(j["x"], j["y"]))
            return {"mensaje": "Camina con las flechas hasta el caldero brillante."}
        if t["estado"] != "activo" or accion != "interactuar":
            return None
        clave = solicitud.get("objetivo")
        if t["paso"] == 0 and clave == "caldero":
            return {"mensaje": "Primero camina un poco con las flechas. Después pulsa E junto al caldero."}
        if t["paso"] == 1 and clave == "caldero":
            mision._objetivo(i, clave)
            t["paso"] = 2
            return {"mensaje": "¡Hola! Lleva este farol al Tronco de los Ecos que brilla: sigue la luz y allí pulsa E.",
                    "titulo": "Guía del caldero", "vista": "fuente"}
        eco = next(o for o in mision.objetivos if o.get("rol") == "mensajero")
        if t["paso"] == 2 and clave == eco["id"]:
            mision._objetivo(i, clave)
            t.update(estado="terminado", paso=3)
            mision._avisar([i], "¡Lo hiciste! Ya sabes caminar, hablar y entregar. Ahora busca tu primera pista.", "logro")
            return {"mensaje": "¡Farol entregado! Ya puedes ayudar a la aldea."}
        return None

    def actualizar(self, mision):
        for i, t in self.tutoriales.items():
            if i not in mision.jugadores:
                continue
            if mision.ronda or mision.resultado:
                t.update(estado="terminado", paso=3)
            if t["estado"] == "activo" and t["paso"] == 0:
                j = mision.jugadores[i]
                if math.hypot(j["x"] - t["origen"][0], j["y"] - t["origen"][1]) >= 24:
                    t["paso"] = 1

    def pedir(self, mision, i, ahora, presentes):
        if mision.fase != "investigacion":
            raise ValueError("Ahora toca ayudar con el encargo del mapa.")
        if len(mision.conocidas[i]) >= 2:
            return {"mensaje": "¡Ya tienes dos pistas! Ve al caldero para elegir con tu equipo."}
        if ahora - self.ultimo_pedido.get(i, -100) < 5:
            raise ValueError("Tu pedido ya llegó. Dale un momento a tu compañero.")
        candidatos = [j for j in presentes if j != i and j in mision.jugadores]
        if not candidatos:
            raise ValueError("Espera a que vuelva un compañero para pedirle una pista.")
        # Primero quien tiene una pista nueva; entre iguales, una persona antes que un bot.
        candidatos.sort(key=lambda j: (not bool(mision.conocidas[j] - mision.conocidas[i]),
                                       mision.jugadores[j].get("controlador") == "bot"))
        receptor = candidatos[0]
        self.ultimo_pedido[i] = ahora
        self.pedidos[i] = receptor
        mision._avisar([receptor], mision.jugadores[i]["nombre"] + " necesita una pista. Abre I para ayudar.", "pedido", emisor=i)
        return {"mensaje": "Le pediste una pista a " + mision.jugadores[receptor]["nombre"] + "."}

    def pedir_ayuda(self, mision, i, ahora, presentes):
        """Encargo: pide a un compañero que lleve uno de los objetos que faltan."""
        encargo = mision.encargo
        if mision.fase != "preparacion" or encargo is None:
            raise ValueError("Ahora no hay objetos que llevar.")
        if encargo.materiales_listos:
            raise ValueError("Ya están todos los objetos en el cesto.")
        if ahora - self.ultimo_pedido.get(("encargo", i), -100) < 3:
            raise ValueError("Tu pedido ya llegó. Dale un momento a tu compañero.")
        libres = [m[0] for m in encargo.config["materiales"]
                  if m[0] not in encargo.entregados and m[0] not in encargo.cargas.values()]
        if not libres:
            raise ValueError("Los objetos que faltan ya los lleva alguien.")
        candidatos = [j for j in presentes if j != i and j in mision.jugadores
                      and mision.jugadores[j].get("dimension", "la_copa") == "la_copa" and j not in encargo.cargas
                      and (encargo.config.get("aportes_libres") or j not in encargo.entregados.values())]
        if not candidatos:
            raise ValueError("Ahora no hay un compañero libre para ayudarte.")
        # Primero un bot libre: está para eso; las personas reciben el aviso si no hay bots.
        candidatos.sort(key=lambda j: mision.jugadores[j].get("controlador") != "bot")
        receptor = candidatos[0]
        self.ultimo_pedido[("encargo", i)] = ahora
        mision._avisar([receptor], mision.jugadores[i]["nombre"] + " te pide ayuda para llevar un objeto al cesto.",
                       "pedido_encargo", emisor=i)
        return {"mensaje": mision.jugadores[receptor]["nombre"] + " va a llevar un objeto al cesto."}

    def datos(self, m, i, estado):
        t = self.tutoriales[i]
        caldero = next(o for o in m.objetivos if o["id"] == "caldero")
        eco = next(o for o in m.objetivos if o.get("rol") == "mensajero")
        guia = {"paso": "buscar", "titulo": "1. Busca tu pista", "detalle": "Ve a la luz y pulsa E para hablar.",
                "objetivo": estado["objetivo"], "accion": "interactuar", "boton": "Hablar · E"}
        if t["estado"] == "activo":
            paso = t["paso"]
            guia.update(paso="tutorial", titulo=("Camina con las flechas", "Habla con el guía", "Entrega el farol")[paso],
                        detalle=("Acércate al caldero brillante.", "Junto al caldero, pulsa E.", "Ve al tronco brillante y pulsa E.")[paso],
                        objetivo=eco if paso == 2 else caldero)
            if paso == 0:
                guia.update(accion="mapa", boton="Flechas: caminar")
        elif m.fase == "preparacion":
            e = m.encargo
            guia.update(paso="encargo", titulo="4. Ayuda a la aldea", detalle=estado["instruccion"],
                        objetivo=estado["objetivo"], boton="Ayudar · E", ayuda=not e.materiales_listos)
            if e.materiales_listos and not e.materiales_colocados:
                guia.update(titulo="¡Hagan la tarea juntos!", detalle="Uno ayuda y el otro trabaja. Acérquense al cesto.",
                            objetivo=dict(e.destino, nombre=e.config["lugar"]), boton="Abrir actividad · E")
            elif e.materiales_colocados and not e.completo:
                guia.update(paso="puente", titulo="¡Reparen el Puente 1!", detalle=estado["instruccion"],
                            objetivo=estado["objetivo"], boton="Reparar · E")
        elif m.fase == "final":
            guia.update(paso="final", titulo="¡Aldea a salvo!", detalle="Sigue la flecha hasta el portal y pulsa E para viajar. M: estrellas del equipo.", objetivo=None, accion="balance", boton="Ver estrellas")
        elif not m.resultado:
            rol = m.jugadores[i]["rol"]
            if "pista_" + rol not in m.conocidas[i]:
                pass
            elif len(m.conocidas[i]) < 2:
                guia.update(paso="compartir", titulo="2. Consigue otra pista", detalle="Pide una pista a un compañero. Tú también puedes compartir la tuya.",
                            objetivo=eco, accion="pedir_pista", boton="Pedir una pista")
            else:
                pendientes = [j for j, receptor in self.pedidos.items() if receptor == i and j in m.presentes and j in m.jugadores
                              and len(m.conocidas[j]) < 2 and m.conocidas[i] - m.conocidas[j]]
                if pendientes:
                    guia.update(paso="compartir", titulo="Ayuda a " + m.jugadores[pendientes[0]]["nombre"],
                                detalle="En el tronco puedes enviarle una pista con I.", objetivo=eco, boton="Compartir pistas", accion="inventario")
                else:
                    guia.update(paso="decidir", titulo="3. Elijan juntos", detalle="Ve al caldero. Lee las pistas y elige con tu equipo.", objetivo=caldero, boton="Elegir · E")
        estado.update(tutorial={k: v for k, v in t.items() if k != "origen"}, guia=guia,
                      pedidos=[{"id": j, "nombre": m.jugadores[j]["nombre"]} for j, receptor in self.pedidos.items()
                               if receptor == i and j in m.jugadores and len(m.conocidas[j]) < 2])
        return estado
