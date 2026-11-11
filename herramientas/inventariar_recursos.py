"""Inventario físico reproducible; no cambia imágenes ni conecta recursos al juego.

Uso: python herramientas/inventariar_recursos.py
Lee tamaños PNG con la biblioteca estándar; no requiere Pygame ni Pillow.
"""
import csv
from collections import Counter
from pathlib import Path
import struct

RAIZ = Path(__file__).resolve().parent.parent


def inventariar():
    filas = []
    for carpeta in ("Imagenes", "Audios", "Fuentes"):
        for archivo in sorted((RAIZ / carpeta).rglob("*")):
            if not archivo.is_file():
                continue
            ancho = alto = ""
            if archivo.suffix.lower() == ".png":
                with archivo.open("rb") as entrada:
                    cabecera = entrada.read(24)
                if cabecera[:8] == b"\x89PNG\r\n\x1a\n" and len(cabecera) == 24:
                    ancho, alto = struct.unpack(">II", cabecera[16:24])
            filas.append({"archivo": archivo.relative_to(RAIZ).as_posix(),
                          "bytes": archivo.stat().st_size, "ancho": ancho, "alto": alto})
    return filas


def esperados():
    filas = []

    def agregar(ruta, uso, respaldo, alternativa=""):
        filas.append((ruta, uso, respaldo, alternativa))

    for estado in ("inquieto", "sereno", "saturado"):
        agregar(f"Imagenes/Futuro/nucleo_{estado}_8f.png", "NÚCLEO animado",
                "Avatar por código", f"Imagenes/NPCS/Nucleo/Nucleo{estado.capitalize()}.png")
    for nombre, alternativa in (("Aviso_comunitario", "aviso_comunitario"),
                                ("Generado_con_IA", "Generado_con_IA"),
                                ("Contenido_autentico", "Contenido_autentico"),
                                ("Contenido_manipulado", "Contenido_manipulado"),
                                ("Suplantacion", "suplantación"),
                                ("Control_autonomo", "Control_autonomo")):
        agregar(f"Imagenes/Clasificación/{nombre}.png", "Tarjeta de clasificación",
                "Tarjeta generada", f"Imagenes/Clasificación/{alternativa}.png")
    agregar("Imagenes/Fondos/Inicio/pantalla_inicio_8f.png", "Inicio animado",
            "Fondo actual", "Imagenes/Fondos/Mapas/fondoMenuInicio.png")
    for rol in ("guardian", "mensajero", "habitante", "aspirante", "luma", "mira"):
        agregar(f"Imagenes/Fondos/Carga/carga_{rol}_8f.png", "Transición de portal", "Transición actual")
    for n in range(1, 5):
        agregar(f"Imagenes/Intro/vineta{n}.png", "Intro breve", "Texto resumido por implementar")
    for nombre in ("publicar", "verificar", "reportar", "ignorar"):
        agregar(f"Imagenes/Elementos presente/Celular/capsula_{nombre}.png", "Botón celular", "Botón actual")
    for nombre in ("normal", "seleccionado", "pendiente", "nuevo"):
        agregar(f"Imagenes/Expediente/medallon_{nombre}.png", "Nodo AVL, 64x64", "Círculo actual")
    for nombre in ("bien", "error"):
        agregar(f"Imagenes/Expediente/sello_{nombre}.png", "Resultado, 48x48", "Texto de resultado")
    for sector in ("plaza", "estacion", "sede", "verificacion", "comunitario", "cafe"):
        for estado in ("conectado", "desconectado"):
            agregar(f"Imagenes/Futuro/Terminal/{sector}_{estado}.png", "Terminal, 48x48", "Círculo actual")
    for nombre in ("ficha_vacio", "ficha_logrado", "aguja"):
        agregar(f"Imagenes/Indicadores Puente/{nombre}.png", "Minijuego puente", "Dibujo actual")
    for nombre in ("exclamacion", "interrogacion", "check"):
        agregar(f"Imagenes/Indicadores/{nombre}_4f.png", "Objetivo visual", "Indicador por código por implementar")
    for nombre in ("pista", "compartir", "pedir_pruebas", "verificar", "votar", "entregar", "rumor", "aclaracion", "eco"):
        agregar(f"Imagenes/Iconos/Acciones/{nombre}.png", "Acciones", "Texto actual")
    for nombre in ("PixelifySans", "Nunito", "ShareTechMono"):
        agregar(f"Fuentes/{nombre}.ttf", "Tipografía por era", "Fuente del sistema / Pygame")
    for nombre in ("musica_presente", "musica_presente_tension", "musica_nucleo", "batalla_fase1", "batalla_fase2"):
        agregar(f"Audios/Musica/{nombre}.mp3", "Música por era / batalla", "Ambiente.mp3; conexión pendiente")
    for nombre in ("pista_obtenida", "objetivo_cumplido", "aun_no", "compartir_eco", "rumor_crece", "aclaracion_llega", "voto", "notificacion_celular", "terminal_nucleo", "cambio_epoca"):
        agregar(f"Audios/UI/{nombre}.wav", "Sonido de interfaz", "Silencio; conexión pendiente")
    for nombre in ("nucleo_carga", "nucleo_barrido", "rayo_aviso", "rayo_impacto", "mini_aparicion", "mini_disparo", "mini_explosion", "cambio_fase", "desfragmentador", "emp_onda", "escudo_activar", "escudo_bloqueo", "dron_curacion", "recoger_material", "fabricar", "derribado", "levantado", "nucleo_derrota"):
        agregar(f"Audios/Batalla/{nombre}.wav", "Batalla aún sin implementar", "Silencio")
    agregar("Imagenes/Batalla/HUD/derribado_4f.png", "Jugador caído", "Corazón por código por implementar")
    return filas


def main():
    filas = inventariar()
    destino = RAIZ / "docs"
    with (destino / "inventario_recursos.csv").open("w", encoding="utf-8-sig", newline="") as salida:
        escritor = csv.DictWriter(salida, fieldnames=("archivo", "bytes", "ancho", "alto"))
        escritor.writeheader()
        escritor.writerows(filas)
    existentes = {f["archivo"] for f in filas}
    resumen = Counter(f["archivo"].split("/")[0] for f in filas)
    lineas = ["# Arte y audio esperados - inventario físico", "",
              "Generado con `python herramientas/inventariar_recursos.py`. Todos los archivos",
              "y tamaños PNG están en `inventario_recursos.csv`. Existir no significa estar",
              "conectado al juego ni tener geometría, cuadros o identidad ya validados.", "",
              "## Archivos encontrados", ""]
    lineas += [f"- {carpeta}: {cantidad} archivos." for carpeta, cantidad in sorted(resumen.items())]
    lineas += ["", "## Recursos del plan", "",
               "Las rutas alternativas se registran explícitamente: no se renombran ni se usan automáticamente.",
               "La columna respaldo describe la alternativa actual o la prevista si dice por implementar.", "",
               "| Archivo esperado | Estado físico | Uso / tamaño previsto | Respaldo |",
               "| --- | --- | --- | --- |"]
    for ruta, uso, respaldo, alternativa in esperados():
        estado = "Existe; conexión pendiente" if ruta in existentes else "Falta en ruta esperada"
        if ruta not in existentes and alternativa in existentes:
            estado = f"Alternativa existente: `{alternativa}`; adaptar"
        lineas.append(f"| `{ruta}` | {estado} | {uso} | {respaldo} |")
    lineas += ["", "## Familias con nombres o formatos variables", "",
               "- Retratos: los seis roles/apariencias ya tienen carpetas de cuatro expresiones.",
               "  Kael y Tarek están registrados como aspirante y habitante; falta conectar sus diálogos.",
               "  Nuevos retratos individuales abajo: no asumir cuatro expresiones ni identidad para NPC2.",
               "- Elia y Arel tienen sprites, pero falta agregarlos al mapa y al diálogo.",
               "- Teclas: faltan los recursos `Imagenes/Indicadores/tecla_<X>.png` del plan.",
               "- Icono animado: falta `Imagenes/Iconos/icono_animado_<N>f.png`; existe brillo por código.",
               "- Balanceo: las tiras existentes deben compararse contra el tamaño de cada puente antes de conectarlas.",
               "- `herramientas/componer_pantallas.py` no existe en esta revisión.",
               "- Falta el prompt completo de batalla: este inventario no puede certificar todo su arte.", "",
               "## Arte nuevo para revisar antes de conectarlo", "",
               "| Archivo | Dimensiones PNG |", "| --- | --- |"]
    for f in filas:
        ruta = f["archivo"]
        if ruta.startswith(("Imagenes/Fondos/Mapas/Futuro/", "Imagenes/NPCS/Nucleo/")) or (
                ruta.startswith("Imagenes/Retratos/") and ruta.count("/") == 2):
            lineas.append(f"| `{ruta}` | {f['ancho']} x {f['alto']} |")
    lineas += ["", "## Retratos solicitados en el plan", "",
               "| Personaje | Recurso físico / pendiente |", "| --- | --- |",
               "| Naira | `Imagenes/Retratos/NairaRetraro.png`; imagen individual, adaptar |",
               "| Odran | `Imagenes/Retratos/OdranRetrato.png`; imagen individual, adaptar |",
               "| Darek | `Imagenes/Retratos/DarekRetrato.png`; imagen individual, adaptar |",
               "| Ronaldo Vélez | `Imagenes/Retratos/RonaldoVelezRetrato.png`; imagen individual, adaptar |",
               "| Mateo Ríos | Candidato `Mensajero-urbano-Retraro.png`; confirmar identidad y adaptar |",
               "| Elías Vega y Tomás Red | Sin retrato identificado por nombre |",
               "| Elia y Arel | Hay sprites; sin retrato identificado por nombre |",
               "| Archivista, Corredor de Datos, Ciudadano Conectado, Representante Humano | Sin retratos propios identificados por nombre; posible reutilización por confirmar |",
               "", "`NPC2retrato.png` y `Habitante_Conectada-Retrato.png` no permiten identificar",
               "con certeza a todos los personajes solicitados. Confirmar con el equipo antes de pedir duplicados.",
               "", "El mapa nuevo mide 1048 x 577 y el provisional 998 x 576. Revisar alineación",
               "con paredes, puertas y puntos de aparición antes de reemplazarlo. Los estados",
               "de NÚCLEO no deben dividirse suponiendo ocho cuadros: comprobar cada tira.", ""]
    (destino / "arte_esperado.md").write_text("\n".join(lineas), encoding="utf-8")
    print(f"Inventario: {len(filas)} archivos; {len(esperados())} rutas del plan revisadas.")


if __name__ == "__main__":
    main()
