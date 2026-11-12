"""Los bots leen las mismas tarjetas y usan las mismas acciones que los jugadores."""
import math
from multijugador.final_cooperativo import CORRECTA


def planificar(bot, estado, jugadores, tarea):
    final = (estado["caso"].get("futuro") or {}).get("desafio_final") or {}
    fase = final.get("fase")
    if fase in (None, "bloqueado", "victoria"):
        return None
    puntos = final["puntos"]
    if bot.posicion.get("interior"):
        salida = estado["caso"]["futuro"]["edificios"][bot.posicion["interior"]]["salida"]
        return tarea("ACOMPANANDO", salida, "salir_edificio", radio=30)
    humanos = [j for j in jugadores if j.get("controlador") != "bot" and j.get("conectado", True)]
    def accion(destino, operacion, **datos):
        return tarea("TRABAJANDO", destino, "final_accion", operacion=operacion, rol=bot.rol, ronda_final=final["ronda"], radio=40, **datos)
    if fase in ("preparacion", "reintento"):
        if fase == "preparacion" and humanos:
            return dict(estado="ESPERANDO_EQUIPO", esperar=True)
        return accion(puntos["aspirante"], "iniciar" if fase == "preparacion" else "reintentar")
    hechos = final["hechos"]
    if len(hechos) == 4:
        if bot.identificador in final["activaciones"]:
            return dict(estado="ESPERANDO_EQUIPO", esperar=True)
        return accion(puntos["aspirante"], "activar")
    batalla = final.get("batalla", {})
    if bot.identificador in batalla.get("derribados", []):
        return dict(estado="ESPERANDO_AYUDA", esperar=True)
    if batalla.get("turno") in ("aviso", "rayo"):
        blancos = batalla.get("blancos", [])
        def distancia(punto):
            return min((math.hypot(punto["x"] - x, punto["y"] - y) for x, y in blancos), default=1000)
        if distancia(bot.posicion) < 44:
            # Solo candidatos caminables y alcanzables, obtenidos de la posición real.
            colisiones = bot._navegador.colisiones
            candidatos = [dict(x=bot.posicion["x"] + dx, y=bot.posicion["y"] + dy)
                          for dx, dy in ((48, 0), (-48, 0), (0, 48), (0, -48), (40, 40), (-40, 40), (40, -40), (-40, -40))]
            candidatos = [c for c in candidatos if not colisiones.bloqueado(c["x"], c["y"])
                          and colisiones.trayecto_libre((bot.posicion["x"], bot.posicion["y"]), (c["x"], c["y"]))]
            if candidatos:
                destino = max(candidatos, key=distancia)
                return dict(estado="ESQUIVANDO", destino=destino, esperar=True, radio=4)
        elif batalla.get("derribados"):
            aliado = next((j for j in jugadores if j["id"] in batalla["derribados"]
                           and not j.get("interior") and j.get("dimension") == "futuro"
                           and math.hypot(j["x"] - bot.posicion["x"], j["y"] - bot.posicion["y"]) <= 68), None)
            if aliado:
                return accion(aliado, "auxiliar", aliado=aliado["id"])
        return dict(estado="ESPERANDO_RECARGA", esperar=True)
    if batalla.get("fase") == 1 and bot.rol in ("mensajero", "aspirante"):
        return dict(estado="ESPERANDO_EQUIPO", esperar=True)
    datos = estado["privado"].get("final_cooperativo", {}).get(bot.rol, {})
    if bot.rol == "guardian" and "guardian" not in hechos:
        registro, orden = datos.get("registro", {}), datos.get("orden", {})
        campo = next((c for c in registro if registro[c] != orden[c]), None)
        return accion(puntos["guardian"], "comparar", campo=campo) if campo else None
    if bot.rol == "habitante" and "habitante" not in hechos:
        for i, (valor, meta) in enumerate(zip(datos.get("valores", []), datos.get("metas", []))):
            if valor != meta:
                return accion(puntos["habitante"], "ajustar", indice=i, delta=1 if valor < meta else -1)
        return accion(puntos["habitante"], "mantener")
    if bot.rol == "mensajero" and "mensajero" not in hechos:
        if "guardian" not in hechos:
            return dict(estado="ESPERANDO_EQUIPO", esperar=True)
        if final["portador"] is None:
            return accion(final["recogida"], "recoger")
        if final["portador"] != bot.identificador:
            return dict(estado="ESPERANDO_EQUIPO", esperar=True)
        return accion(final["ruta"][final["tramo"]], "recargar")
    if bot.rol == "aspirante" and "aspirante" not in hechos:
        for campo, valor in CORRECTA.items():
            if datos.get("propuesta", {}).get(campo) != valor:
                return accion(puntos["aspirante"], "elegir", campo=campo, valor=valor)
        if {"guardian", "habitante", "mensajero"}.issubset(hechos):
            return accion(puntos["aspirante"], "autorizar")
    return dict(estado="ESPERANDO_EQUIPO", esperar=True)
