# Ciudad Núcleo (Era III)

El proyecto no tiene arte propio del futuro. `herramientas/generar_futuro.py`
genera una versión provisional a partir del Presente; se ejecuta una vez y la
salida se versiona. Al llegar el arte definitivo se reemplaza el archivo con el
mismo nombre y no hay que tocar el código.

| Qué | Archivo a reemplazar | Nota |
| --- | --- | --- |
| Mapa | `Imagenes/Futuro/generado/MapaFuturo.png` | Misma resolución que `MapaPresente.png`. Si cambia la geometría, actualizar también las colisiones |
| Colisiones | `Hitboxes/Mapas/Futuro/MapaFuturo_hitboxes.json` | Copia de las del Presente |
| Archivista | `Imagenes/Futuro/generado/NPCS/Archivista/` | Derivado del Agente de verificación |
| Corredor de Datos | `Imagenes/Futuro/generado/NPCS/Corredor de Datos/` | Derivado del Mensajero urbano |
| Ciudadano Conectado | `Imagenes/Futuro/generado/NPCS/Ciudadano Conectado/` | Derivado de la Habitante conectada |
| Representante Humano | `Imagenes/Futuro/generado/NPCS/Representante Humano/` | Derivado del Aspirante contemporáneo |

Provisional dibujado por código: el avatar de NÚCLEO
(`VistaPartida._dibujar_nucleo` en el mapa y `ArteAnalisis._componer_nucleo` en
el celular).

## Misión `nucleo_control`

Se llega desde la pantalla pública del Presente al resolver sus tres casos. Los
puntos usan ids de hitboxes existentes:

- `entrada_centro_comunicaciones`: restaurar conexiones (grafo validado con BFS).
- `entrada_alcaldia`: encontrar el registro alterado.
- `entrada_centro_verificacion`: entregar la llave del Corredor de Datos, que
  está junto a `entrada_estudio_lia`.
- `pantalla_publica_presente`: decisión final y regreso a Distrito Conecta.

El caso entra al expediente con ley y sanción vacías, como los demás.
