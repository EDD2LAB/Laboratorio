import json
import os
import tempfile
import unittest

import pygame

from editores.hitbox_editor import load_hitboxes, save_hitboxes


class HitboxEditorTests(unittest.TestCase):
    def test_present_map_hitboxes_are_visible_and_editable_in_the_editor(self):
        project_root = os.path.dirname(os.path.dirname(__file__))
        ruta = os.path.join(
            project_root,
            "Hitboxes",
            "Mapas",
            "Presente",
            "MapaPresente_hitboxes.json",
        )
        hitboxes, spawn, _, _ = load_hitboxes(ruta)
        entradas = [
            hitbox for hitbox in hitboxes
            if hitbox.get("action") == "entrar_edificio"
        ]
        paredes = [
            hitbox for hitbox in hitboxes
            if hitbox.get("role") == "wall"
        ]
        self.assertGreaterEqual(len(hitboxes), 45)
        self.assertGreaterEqual(len(paredes), 30)
        self.assertEqual(len(entradas), 7)
        self.assertEqual(len({
            hitbox["edificio_id"] for hitbox in entradas
        }), 7)
        self.assertIn("default", spawn)

    def test_saving_preserves_game_metadata_not_managed_by_editor(self):
        project_root = os.path.dirname(os.path.dirname(__file__))
        image_path = os.path.join(
            project_root,
            "Imagenes",
            "Fondos",
            "Mapas",
            "Presente",
            "MapaPresente.png",
        )
        metadata = {
            "spawn_presente": {"x": 480, "y": 620},
            "npc_routes": {"reportera": {"points": [{"rx": 0.2, "ry": 0.3}]}},
            "grafo": {"nodos": [{"id": "plaza"}]},
            "edificios_presentes": {"alcaldia": {"interior": "existing.png"}},
        }
        with tempfile.TemporaryDirectory() as directorio:
            ruta = os.path.join(directorio, "hitboxes.json")
            with open(ruta, "w", encoding="utf-8") as archivo:
                json.dump(metadata, archivo)

            save_hitboxes(
                ruta,
                [],
                pygame.Rect(0, 0, 998, 576),
                image_path,
            )

            with open(ruta, "r", encoding="utf-8") as archivo:
                saved = json.load(archivo)
        for clave, valor in metadata.items():
            self.assertEqual(saved[clave], valor)
        self.assertEqual(saved["hitboxes"], [])


if __name__ == "__main__":
    unittest.main()
