from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WeaponArchitectureTests(unittest.TestCase):
    def test_schema_is_automatic_and_non_destructive(self):
        source = (
            ROOT / "rpg_character_weapon_schema.py"
        ).read_text(encoding="utf-8")
        upper = source.upper()
        self.assertIn("CREATE TABLE IF NOT EXISTS", upper)
        self.assertIn("RPG_CHARACTER_WEAPON_DETAILS", upper)
        self.assertIn("RPG_CHARACTER_ATTACK_WEAPON_LINKS", upper)
        self.assertIn("ON DELETE CASCADE", upper)
        self.assertNotIn("DROP TABLE", upper)
        self.assertNotIn("TRUNCATE", upper)

    def test_facade_patches_combat_quick_attack_source(self):
        source = (
            ROOT / "rpg_character.py"
        ).read_text(encoding="utf-8")
        text = ast.unparse(ast.parse(source))
        self.assertIn(
            "_impl.list_rpg_attacks = _list_rpg_attacks",
            text,
        )
        self.assertIn(
            "list_rpg_attacks=_list_rpg_attacks",
            text,
        )
        self.assertIn(
            "list_rpg_equipment=_list_rpg_equipment",
            text,
        )

    def test_pure_modules_do_not_import_ui_or_db(self):
        for name in (
            "rpg_character_weapon_catalog.py",
            "rpg_character_weapon_rules.py",
        ):
            parsed = ast.parse(
                (ROOT / name).read_text(encoding="utf-8")
            )
            imports = set()
            for node in ast.walk(parsed):
                if isinstance(node, ast.Import):
                    imports.update(
                        alias.name for alias in node.names
                    )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module)
            self.assertTrue(
                {
                    "nicegui",
                    "db",
                    "rpg_character",
                    "rpg_character_ui",
                }.isdisjoint(imports)
            )

    def test_equipment_ui_has_iomedae_preset_and_link_action(self):
        source = (
            ROOT / "rpg_character_equipment.py"
        ).read_text(encoding="utf-8")
        self.assertIn("Épée longue d’Iomedae", source)
        self.assertIn("create_attack_from_weapon", source)

    def test_attack_ui_supports_equipment_link_and_grip(self):
        source = (
            ROOT / "rpg_character_attacks.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "Arme physique liée (Équipement)",
            source,
        )
        self.assertIn(
            "Prise pour cette attaque",
            source,
        )
        self.assertIn(
            "Reprendre les valeurs de l’arme",
            source,
        )

    def test_phase_keeps_large_data_module_as_existing_dependency(self):
        data_path = ROOT / "rpg_character_data.py"
        weapon_data_path = ROOT / "rpg_character_weapon_data.py"
        self.assertTrue(data_path.exists())
        self.assertTrue(weapon_data_path.exists())

        source = (
            ROOT / "rpg_character.py"
        ).read_text(encoding="utf-8")
        text = ast.unparse(ast.parse(source))
        self.assertIn(
            "import rpg_character_data as _data",
            text,
        )


if __name__ == "__main__":
    unittest.main()
