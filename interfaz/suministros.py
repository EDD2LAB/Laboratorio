"""Iconos y señales del encargo.

Tablas, cuerda y canasta de herramientas usan el arte real
(Herramientas/HerramientasReparación.png, recortado una vez por
SistemaReparacionPuente.recortar_spritesheet_materiales); agua, provisiones,
pergaminos y tinta, Assets eventos/. El farol no tiene arte: conserva su icono.
"""
import pygame

from nucleo.recursos import cargar_imagen

# id de material en red -> clave del recorte del spritesheet.
CLAVES_SPRITE = {"tablas": "tablas", "cuerdas": "cuerda", "herramientas": "herramientas"}
RUTAS_EVENTOS = {"agua": "Assets eventos/agua.png", "provisiones": "Assets eventos/proviciones.png",
                 "pergaminos": "Assets eventos/pergaminon.png", "tinta": "Assets eventos/tinta.png"}
_sprites = {}


def clave_cesto(encargo):
    """Se llena al meter todo y vuelve a vaciarse cuando los objetos ya se usaron."""
    return "lleno" if encargo and encargo.get("materiales_listos") and not encargo.get("materiales_colocados") else "vacio"


def configurar_sprites(materiales):
    """Escala una vez cada material a los dos tamaños que se dibujan."""
    _sprites.clear()
    imagenes = {material: (materiales or {}).get(clave) for material, clave in CLAVES_SPRITE.items()}
    for material, ruta in RUTAS_EVENTOS.items():
        imagen = cargar_imagen(ruta, requerido=False)
        if imagen is None:
            print("[Arte] Falta la imagen:", ruta)
        else:
            imagenes[material] = imagen.subsurface(imagen.get_bounding_rect())
    for material, imagen in imagenes.items():
        if imagen is None:
            continue
        for tamano in (26, 34):
            escala = min(tamano / imagen.get_width(), tamano / imagen.get_height())
            _sprites[(material, tamano)] = pygame.transform.scale(
                imagen, (max(1, round(imagen.get_width() * escala)), max(1, round(imagen.get_height() * escala))))


def dibujar_carga(superficie, material, centro, tamano=26):
    x, y = centro
    sprite = _sprites.get((material, tamano))
    if sprite is not None:
        placa = pygame.Rect(0, 0, tamano + 10, tamano + 8)
        placa.center = centro
        pygame.draw.ellipse(superficie, (10, 24, 18), placa.move(0, tamano // 2 - 2).inflate(-6, -placa.height + 8))
        superficie.blit(sprite, sprite.get_rect(center=centro))
        return
    pygame.draw.rect(superficie, (15, 35, 27), (x-16, y-15, 32, 30), border_radius=4)
    if material == "herramientas":
        pygame.draw.ellipse(superficie, (169, 120, 67), (x-12, y-4, 24, 15))
        pygame.draw.arc(superficie, (218, 185, 111), (x-9, y-12, 18, 16), 0, 3.14, 2)
    elif material == "farol":
        pygame.draw.circle(superficie, (255, 226, 116), (x, y), 10)
        pygame.draw.rect(superficie, (186, 123, 57), (x-9, y-12, 18, 5))
        pygame.draw.rect(superficie, (186, 123, 57), (x-9, y+8, 18, 5))
    elif material == "tablas":
        for dy in (-9, -2, 5):
            pygame.draw.rect(superficie, (179, 120, 65), (x-12, y+dy, 24, 5))
            pygame.draw.line(superficie, (95, 62, 39), (x-9, y+dy+2), (x+9, y+dy+2))
    elif material == "cuerdas":
        for radio in (11, 7, 3):
            pygame.draw.circle(superficie, (223, 189, 116), (x, y), radio, 2)
    elif material == "pergaminos":
        pygame.draw.rect(superficie, (242, 224, 175), (x-9, y-11, 18, 22))
        for dy in (-5, 0, 5):
            pygame.draw.line(superficie, (145, 101, 64), (x-5, y+dy), (x+5, y+dy))
    elif material == "provisiones":
        pygame.draw.ellipse(superficie, (169, 120, 67), (x-11, y-6, 22, 18))
        pygame.draw.rect(superficie, (218, 185, 111), (x-5, y-10, 10, 5))
    else:
        color = (90, 193, 233) if material == "agua" else (175, 117, 219)
        pygame.draw.rect(superficie, color, (x-8, y-7, 16, 18), border_radius=3)
        pygame.draw.rect(superficie, (228, 213, 168), (x-4, y-12, 8, 5))


def dibujar_encargos(superficie, caso, fuente):
    encargo = caso.get("encargo")
    if encargo:
        llevados = set(encargo.get("cargas", {}).values())
        colocados = [m for m in encargo["materiales"] if m["entregado"]]
        d = encargo["destino"]
        if not encargo.get("materiales_listos"):
            for i, material in enumerate(colocados):
                # Lo que ya entró asoma sobre el cesto hasta que se llena.
                dibujar_carga(superficie, material["id"], (d["x"] - (len(colocados) - 1) * 14 + i * 28, d["y"] - 60))
        for material in encargo["materiales"]:
            if material["entregado"] or material["id"] in llevados:
                continue  # El objeto ya no está en su punto de recogida.
            o = material["fuente"]
            x, y = o["x"] + 23, o["y"] - 22
            dibujar_carga(superficie, material["id"], (x, y), 34)
            texto = fuente.render(material["nombre"] + " · E", True, (255, 239, 191))
            caja = texto.get_rect(midtop=(x, y+17))
            caja.clamp_ip(superficie.get_rect().inflate(-10, -10))
            pygame.draw.rect(superficie, (15, 35, 27), caja.inflate(6, 4))
            superficie.blit(texto, caja)
        d = encargo["destino"]
        pygame.draw.circle(superficie, (128, 238, 180), (d["x"], d["y"]), 24, 3)
        progreso = encargo.get("actividad", {}).get("progreso", 0)
        if encargo.get("materiales_listos"):
            for i in range(3):
                x, y = d["x"]-27+i*19, d["y"]-72
                color = (246, 202, 105) if i < progreso else (48, 74, 51)
                pygame.draw.rect(superficie, color, (x, y, 15, 8), border_radius=2)
        etiqueta = fuente.render("¡GRACIAS, EQUIPO!" if encargo["completo"] else "AHORA: REPARAR EL PUENTE 1" if encargo.get("materiales_colocados")
                                 else "AYUDAR JUNTOS · E" if encargo.get("materiales_listos")
                                 else f"METER EN EL CESTO · E  {len(colocados)}/{len(encargo['materiales'])}", True, (128, 238, 180))
        superficie.blit(etiqueta, etiqueta.get_rect(midtop=(d["x"], d["y"]+28)))
    # Todas las obras comparten el cesto: solo se rotula la última.
    for obra in (caso.get("obras", []) + ([encargo] if encargo and encargo["completo"] else []))[-1:]:
        d = obra["destino"]
        x, y = d["x"]-22, d["y"]-36
        pygame.draw.line(superficie, (225, 189, 105), (x, y), (x, y+28), 3)
        pygame.draw.polygon(superficie, (100, 223, 152), ((x, y), (x+18, y+6), (x, y+12)))
        texto = fuente.render(obra["efecto"], True, (128, 238, 180))
        caja = texto.get_rect(midtop=(d["x"], d["y"]+46))
        caja.clamp_ip(superficie.get_rect().inflate(-10, -10))
        pygame.draw.rect(superficie, (15, 35, 27), caja.inflate(6, 4))
        superficie.blit(texto, caja)
