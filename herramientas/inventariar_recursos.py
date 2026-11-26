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


# Sonidos que audio/audio_manager.py (SONIDOS_BATALLA) carga si existen.
SONIDOS_CONECTADOS = {"rayo_aviso", "rayo_impacto", "mini_explosion", "mini_disparo", "mini_aparicion", "derribado",
                      "levantado", "cambio_fase", "recoger_material", "fabricar", "blaster_disparo", "mini_golpe",
                      "senal_perdida"}
FINALES = (("Imagenes/Finales/epilogo_futuro.png", "Viñeta de Ciudad Núcleo", "Mapa del Futuro oscurecido"),
           ("Imagenes/Finales/epilogo_presente.png", "Viñeta de Distrito Conecta", "Mapa del Presente oscurecido"),
           ("Imagenes/Finales/epilogo_copa.png", "Viñeta de La Copa", "Fondo de La Copa oscurecido"),
           ("Imagenes/Finales/Final_tres_eras.png", "Resultado positivo", "Final_positivo.jpeg"),
           ("Imagenes/Finales/Final_humo_tres_eras.png", "Resultado de humo", "Game_over.jpeg"))


def esperados():
    filas = []

    def agregar(ruta, uso, respaldo, alternativa="", conectado=False):
        """``conectado``: el código ya usa ``alternativa`` (o la ruta esperada si existe)."""
        filas.append((ruta, uso, respaldo, alternativa, conectado))

    for estado in ("inquieto", "sereno", "saturado"):
        agregar(f"Imagenes/Futuro/nucleo_{estado}_8f.png", "NÚCLEO animado",
                "Avatar por código", f"Imagenes/NPCS/Nucleo/Nucleo{estado.capitalize()}.png", True)
    for nombre, alternativa in (("Aviso_comunitario", "aviso_comunitario"),
                                ("Generado_con_IA", "Generado_con_IA"),
                                ("Contenido_autentico", "Contenido_autentico"),
                                ("Contenido_manipulado", "Contenido_manipulado"),
                                ("Suplantacion", "suplantación"),
                                ("Control_autonomo", "Control_autonomo")):
        agregar(f"Imagenes/Clasificación/{nombre}.png", "Tarjeta de clasificación",
                "Tarjeta generada", f"Imagenes/Clasificación/{alternativa}.png", True)
    agregar("Imagenes/Fondos/Inicio/pantalla_inicio_8f.png", "Inicio animado",
            "Fondo actual", "Imagenes/Fondos/Mapas/fondoMenuInicio.png")
    for rol in ("guardian", "mensajero", "habitante", "aspirante", "luma", "mira"):
        agregar(f"Imagenes/Fondos/Carga/carga_{rol}_8f.png", "Transición de portal", "Transición actual")
    for n in range(1, 3):  # intro de dos viñetas (interfaz/intro.py)
        agregar(f"Imagenes/Intro/vineta{n}.png", "Intro breve", "Se salta la viñeta", conectado=True)
    # interfaz/celular.py: la cápsula marca tu voto y es la imagen de la consecuencia.
    for nombre, alternativa in (("publicar", "colgar"), ("verificar", "Verificar"), ("reportar", "Denunciar"),
                                ("ignorar", "ignorar")):
        agregar(f"Imagenes/Elementos presente/Celular/capsula_{nombre}.png", "Botón celular", "Botón actual",
                f"Imagenes/Pociones/{alternativa}-capsula.png", True)
    # interfaz/expediente.py: nodos del AVL y sello del resultado de cada caso.
    for nombre in ("normal", "seleccionado", "pendiente", "nuevo"):
        agregar(f"Imagenes/Expediente/medallon_{nombre}.png", "Nodo AVL, 64x64", "Círculo actual",
                f"Imagenes/Expediente/Medallon{nombre.capitalize()}.png", True)
    for nombre, alternativa in (("bien", "correcto"), ("error", "error")):
        agregar(f"Imagenes/Expediente/sello_{nombre}.png", "Resultado, 48x48", "Texto de resultado",
                f"Imagenes/Expediente/sello_{alternativa}.png", True)
    for sector in ("plaza", "estacion", "sede", "verificacion", "comunitario", "cafe"):
        for estado in ("conectado", "desconectado"):
            agregar(f"Imagenes/Futuro/Terminal/{sector}_{estado}.png", "Terminal, 48x48", "Círculo actual")
    # interfaz/escenas_multijugador.py: aguja y fichas de aciertos del minijuego.
    for nombre, alternativa in (("ficha_vacio", "ficha_vacio"), ("ficha_logrado", "ficha_logrado"), ("aguja", "aguja7")):
        agregar(f"Imagenes/Indicadores Puente/{nombre}.png", "Minijuego puente", "Dibujo actual",
                f"Imagenes/Expediente/Indicadores-puente/{alternativa}.png", True)
    for nombre in ("exclamacion", "interrogacion", "check"):
        agregar(f"Imagenes/Indicadores/{nombre}_4f.png", "Objetivo visual", "Indicador por código implementado")
    for nombre in ("pista", "compartir", "pedir_pruebas", "verificar", "votar", "entregar", "rumor", "aclaracion", "eco"):
        agregar(f"Imagenes/Iconos/Acciones/{nombre}.png", "Acciones", "Texto actual")
    for nombre in ("PixelifySans", "Nunito", "ShareTechMono"):
        agregar(f"Fuentes/{nombre}.ttf", "Tipografía por era", "Fuente del sistema / Pygame")
    # audio/audio_manager.py busca la música en Audios/Música/, Audios/Musica/ y Audios/.
    for nombre in ("musica_presente", "musica_presente_tension", "musica_nucleo", "batalla_fase1", "batalla_fase2"):
        agregar(f"Audios/Musica/{nombre}.mp3", "Música por era / batalla", "Ambiente.mp3",
                f"Audios/Música/{nombre}.mp3", nombre != "musica_presente_tension")
    for nombre in ("pista_obtenida", "objetivo_cumplido", "aun_no", "compartir_eco", "rumor_crece", "aclaracion_llega", "voto", "notificacion_celular", "terminal_nucleo", "cambio_epoca"):
        agregar(f"Audios/UI/{nombre}.wav", "Sonido de interfaz", "Silencio; conexión pendiente")
    for nombre in ("nucleo_carga", "nucleo_barrido", "rayo_aviso", "rayo_impacto", "mini_aparicion", "mini_disparo", "mini_explosion", "cambio_fase", "desfragmentador", "emp_onda", "escudo_activar", "escudo_bloqueo", "dron_curacion", "recoger_material", "fabricar", "derribado", "levantado", "nucleo_derrota"):
        # audio/audio_manager.py (SONIDOS_BATALLA) carga los que existen.
        agregar(f"Audios/Batalla/{nombre}.wav", "Sonido del combate final", "Silencio", "", nombre in SONIDOS_CONECTADOS)
    agregar("Imagenes/Batalla/HUD/derribado_4f.png", "Jugador caído", "Corazón roto en pixel art por código (interfaz/sprites_combate.py)")
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
    conectados, pendientes, faltan = [], [], []
    for ruta, uso, respaldo, alternativa, conectado in esperados():
        real = ruta if ruta in existentes else alternativa if alternativa in existentes else None
        if real and conectado:
            conectados.append(f"| `{ruta}` | `{real}` | {uso} |")
        elif real:
            nota = "Existe; conexión pendiente" if real == ruta else f"Alternativa existente: `{real}`; adaptar"
            pendientes.append(f"| `{ruta}` | {nota} | {uso} | {respaldo} |")
        else:
            faltan.append(f"| `{ruta}` | {uso} | {respaldo} |")
    lineas += ["", "## Lo que falta de verdad", "",
               "Ni la ruta esperada ni otro archivo equivalente existen. El juego usa el respaldo.", "",
               "| Archivo esperado | Uso / tamaño previsto | Respaldo actual |", "| --- | --- | --- |", *faltan,
               "", "## Existe, pero todavía no está conectado", "",
               "| Archivo esperado | Estado | Uso / tamaño previsto | Respaldo |", "| --- | --- | --- | --- |", *pendientes,
               "", "## Ya conectado (a veces con otro nombre)", "",
               "Los archivos no se renombran ni se mueven: el código usa el nombre real.", "",
               "| Ruta del plan | Archivo que usa el juego | Uso |", "| --- | --- | --- |", *conectados]
    lineas += ["", "## Familias con nombres o formatos variables", "",
               "- Retratos: los seis roles/apariencias ya tienen carpetas de cuatro expresiones.",
               "  Kael y Tarek usan sus retratos de aspirante y habitante en los diálogos.",
               "  Nuevos retratos individuales abajo: no asumir cuatro expresiones ni identidad para NPC2.",
               "- Elia y Arel están en La Copa con sus sprites y conversaciones de ayuda.",
               "- Teclas: faltan los recursos `Imagenes/Indicadores/tecla_<X>.png`; respaldo por código ya conectado en mapa y F1.",
               "  `tecla_E.png` también se usa junto al objetivo resaltado; respaldo por código si falta.",
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
               "| Naira | `Imagenes/Retratos/NairaRetraro.png`; imagen individual integrada sin deformar |",
               "| Odran | `Imagenes/Retratos/OdranRetrato.png`; imagen individual integrada sin deformar |",
               "| Darek | `Imagenes/Retratos/DarekRetrato.png`; imagen individual integrada sin deformar |",
               "| Ronaldo Vélez | `Imagenes/Retratos/RonaldoVelezRetrato.png`; imagen individual integrada sin deformar |",
               "| Mateo Ríos | Candidato `Mensajero-urbano-Retraro.png`; confirmar identidad y adaptar |",
               "| Elías Vega y Tania Red | Sin retrato identificado por nombre |",
               "| Elia y Arel | Hay sprites; sin retrato identificado por nombre |",
               "| Archivista, Corredor de Datos, Ciudadano Conectado, Representante Humano | Sin retratos propios identificados por nombre; posible reutilización por confirmar |",
               "", "`NPC2retrato.png` y `Habitante_Conectada-Retrato.png` no permiten identificar",
               "con certeza a todos los personajes solicitados. Confirmar con el equipo antes de pedir duplicados.",
               "", "El mapa nuevo mide 1048 x 577 y el provisional 998 x 576. Revisar alineación",
               "con paredes, puertas y puntos de aparición antes de reemplazarlo. Los estados",
               "de NÚCLEO no deben dividirse suponiendo ocho cuadros: comprobar cada tira.", "",
               "", "## Cierre de las tres eras (protocolo 17)", "",
               "| Archivo opcional | Uso | Estado | Respaldo sin el archivo |", "| --- | --- | --- | --- |"]
    for ruta, uso, respaldo in FINALES:
        lineas.append(f"| {ruta} | {uso} | {'Existe' if ruta in existentes else 'Falta'} | {respaldo} |")
    lineas += ["", "Las ilustraciones se ajustan a 960 x 720 con transform.scale, una vez al cargar.",
               "Las piezas, blásteres, cajas, mini-núcleos y consolas tienen gráficos por código: no exigen",
               "imágenes nuevas. Se reutiliza NPCS/Nucleo/NucleoSereno.png para la reconfiguración.", "",
               "", "## Mapa definitivo activado en protocolo 18", "",
               "El exterior de Ciudad Núcleo y sus cinco interiores ya usan las imágenes de",
               "Imagenes/Fondos/Mapas/Futuro/ y las hitboxes propias de Hitboxes/Mapas/Futuro/.",
               "Las menciones anteriores al exterior provisional describen etapas históricas.",
               "La geometría se validó junto a las estaciones y recorridos del final cooperativo.",
               "Detalles y hashes de las paredes originales: futuro.md y auditoria_mapa_futuro.json.", ""]
    (destino / "arte_esperado.md").write_text("\n".join(lineas), encoding="utf-8")
    print(f"Inventario: {len(filas)} archivos; {len(esperados())} rutas del plan revisadas.")


if __name__ == "__main__":
    main()
