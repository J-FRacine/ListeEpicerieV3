from __future__ import annotations

import ast
from pathlib import Path
import unittest

import app_versions

ROOT = Path(__file__).resolve().parents[1]


class MagicArchitectureTests(unittest.TestCase):
    def test_phase_keeps_official_version_during_validation(self):
        self.assertEqual(app_versions.APP_VERSIONS["rpg"], "1.7.0")

    def test_magic_schema_is_non_destructive(self):
        source = (
            ROOT / "rpg_character_magic_schema.py"
        ).read_text(encoding="utf-8")
        upper = source.upper()
        self.assertIn("CREATE TABLE IF NOT EXISTS", upper)
        self.assertIn("RPG_CHARACTER_MAGIC_ITEM_DETAILS", upper)
        self.assertIn("RPG_CHARACTER_EQUIPMENT_CONTAINMENT", upper)
        self.assertIn("ON DELETE CASCADE", upper)
        self.assertNotIn("DROP TABLE", upper)
        self.assertNotIn("TRUNCATE", upper)

    def test_facade_wires_magic_equipment_and_saves(self):
        source = (ROOT / "rpg_character.py").read_text(encoding="utf-8")
        text = ast.unparse(ast.parse(source))
        for expected in (
            "_impl.list_rpg_equipment = _list_rpg_equipment",
            "_impl.list_rpg_saves = _list_rpg_saves",
            "_impl.save_total = _save_total_with_magic",
            "_impl.apply_equipment_effects = _apply_equipment_effects",
        ):
            self.assertIn(expected, text)

    def test_equipment_panel_exposes_magic_item_actions(self):
        source = (
            ROOT / "rpg_character_equipment.py"
        ).read_text(encoding="utf-8")
        self.assertIn("Objet magique", source)
        self.assertIn("use_magic_item_charge", source)
        self.assertIn("magic_item_dialog", source)

    def test_saves_panel_accounts_for_ephemeral_magic_item_bonus(self):
        source = (
            ROOT / "rpg_character_saves.py"
        ).read_text(encoding="utf-8")
        self.assertIn("magic_item_bonus", source)
        self.assertIn("Objet magique (résistance)", source)


if __name__ == "__main__":
    unittest.main()
