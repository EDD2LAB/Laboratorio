"""Selección de la pista local a partir del mapa y el progreso compartido."""
from logica.dimensiones import DIMENSIONES


def pista_actual(dimension, contexto, indicadores):
    pista = DIMENSIONES.get(dimension, DIMENSIONES["la_copa"])["musica"]
    if dimension != "futuro":
        return pista
    final = contexto.get("desafio_final") or {}
    cierre = final.get("aventura", {}).get("cierre", {})
    etapa = cierre.get("etapa")
    if etapa in ("pantalla", "creditos"):
        from interfaz.finales import determinar_final
        return determinar_final(indicadores)
    if etapa == "epilogo":
        from multijugador.aventura_final import EPILOGOS
        indice = max(0, min(len(EPILOGOS)-1, cierre.get("indice", 0)))
        return DIMENSIONES[EPILOGOS[indice][0]]["musica"]
    if final.get("fase") == "activo":
        fase = 2 if final.get("batalla", {}).get("fase") == 2 else 1
        return "batalla_fase" + str(fase)
    return pista
