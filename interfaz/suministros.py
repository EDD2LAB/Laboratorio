"""Iconos y señales del encargo.

Tablas, cuerda y canasta de herramientas usan el arte real
(Herramientas/HerramientasReparación.png, recortado una vez por
SistemaReparacionPuente.recortar_spritesheet_materiales). Los materiales sin
arte en el repositorio conservan su icono de píxeles.
"""
import pygame

# id de material en red -> clave del recorte del spritesheet.
CLAVES_SPRITE = {"tablas": "tablas", "cuerdas": "cuerda", "herramientas": "herramientas"}
_sprites = {}


def configurar_sprites(materiales):
    """Escala una vez cada material a los dos tamaños que se dibujan."""
    _sprites.clear()
    for material, clave in CLAVES_SPRITE.items():
        imagen = (materiales or {}).get(clave)
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
        for i, material in enumerate(colocados):
            # Los objetos entregados quedan colocados junto al puesto.
            dibujar_carga(superficie, material["id"], (d["x"] - (len(colocados) - 1) * 15 + i * 30, d["y"] - 4))
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
                x, y = d["x"]-27+i*19, d["y"]-25
                color = (246, 202, 105) if i < progreso else (48, 74, 51)
                pygame.draw.rect(superficie, color, (x, y, 15, 8), border_radius=2)
        etiqueta = fuente.render("¡GRACIAS, EQUIPO!" if encargo["completo"] else "AHORA: REPARAR EL PUENTE 1" if encargo.get("materiales_colocados")
                                 else "AYUDAR JUNTOS · E" if encargo.get("materiales_listos") else "ENTREGAR · E", True, (128, 238, 180))
        superficie.blit(etiqueta, etiqueta.get_rect(midtop=(d["x"], d["y"]+28)))
    for obra in caso.get("obras", []) + ([encargo] if encargo and encargo["completo"] else []):
        d = obra["destino"]
        x, y = d["x"]-22, d["y"]-36
        pygame.draw.line(superficie, (225, 189, 105), (x, y), (x, y+28), 3)
        pygame.draw.polygon(superficie, (100, 223, 152), ((x, y), (x+18, y+6), (x, y+12)))
        texto = fuente.render(obra["efecto"], True, (128, 238, 180))
        caja = texto.get_rect(midtop=(d["x"], d["y"]+46))
        caja.clamp_ip(superficie.get_rect().inflate(-10, -10))
        pygame.draw.rect(superficie, (15, 35, 27), caja.inflate(6, 4))
        superficie.blit(texto, caja)
