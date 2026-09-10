from __future__ import annotations

import importlib.util
import pathlib
import unittest
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE = ROOT / "rpg_character_creation.py"
spec = importlib.util.spec_from_file_location("rpg_character_creation", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class CreationPureTests(unittest.TestCase):
    def test_identity_payload_preserves_contract_and_updates(self):
        character = {field: f"v:{field}" for field in mod.IDENTITY_FIELDS}
        payload = mod.identity_payload(character, class_name="Roublard", character_level=1)
        self.assertEqual(set(payload), set(mod.IDENTITY_FIELDS))
        self.assertEqual(payload["class_name"], "Roublard")
        self.assertEqual(payload["character_level"], 1)
        self.assertEqual(payload["race_key"], "v:race_key")

    def test_combat_payload_preserves_all_fields(self):
        character = {field: 0 for field in mod.COMBAT_FIELDS}
        character.update(str_score=12, cmb_misc_modifier=4, grapple_misc_modifier=None)
        payload = mod.combat_payload(character, max_hp=9)
        self.assertEqual(set(payload), set(mod.COMBAT_FIELDS))
        self.assertEqual(payload["str_score"], 12)
        self.assertEqual(payload["max_hp"], 9)
        self.assertEqual(payload["grapple_misc_modifier"], 4)

    def test_skill_update_rows_only_changes_guided_fields(self):
        skills = [{
            "id": 7,
            "skill_name": "Perception",
            "english_name": "Perception",
            "ability_key": "wis",
            "ranks": Decimal("1"),
            "misc_modifier": 2,
            "class_skill": False,
            "trained_only": False,
            "armor_check_applies": False,
            "double_armor_penalty": False,
        }]
        rows = mod.skill_update_rows(skills, ranks={7: 3}, class_skills={7: True})
        self.assertEqual(rows[0]["ranks"], 3)
        self.assertTrue(rows[0]["class_skill"])
        self.assertEqual(rows[0]["misc_modifier"], 2)
        self.assertEqual(rows[0]["ability_key"], "wis")
        self.assertEqual(rows[0]["skill_name"], "Perception")

    def test_used_skill_ranks_supports_mapping_and_rows(self):
        self.assertEqual(mod.used_skill_ranks({1: 2, 2: "3"}), Decimal("5"))
        self.assertEqual(mod.used_skill_ranks([{"ranks": 1}, {"ranks": Decimal("2")}]), Decimal("3"))

    def test_creation_warnings_are_non_blocking_and_useful(self):
        warnings = mod.creation_warnings(
            {"class_name": "", "race": "", "max_hp": 0},
            saves=[], skills=[], equipment=[], attacks=[],
        )
        self.assertIn("Classe à préciser.", warnings)
        self.assertIn("Race à préciser.", warnings)
        self.assertIn("PV maximums à vérifier.", warnings)
        self.assertTrue(any("Vigueur" in value for value in warnings))
        self.assertTrue(any("attaque" in value.lower() for value in warnings))

    def test_creation_warnings_clear_when_core_sheet_is_filled(self):
        warnings = mod.creation_warnings(
            {"class_name": "Guerrier", "race": "Humain", "max_hp": 10},
            saves=[{"save_key": key} for key in ("fortitude", "reflex", "will")],
            skills=[{"ranks": 1}],
            equipment=[{"id": 1}],
            attacks=[{"id": 1}],
        )
        self.assertEqual(warnings, [])

    def test_module_has_no_project_or_nicegui_imports(self):
        text = MODULE.read_text(encoding="utf-8")
        for forbidden in ("from nicegui", "import nicegui", "from db", "import db", "rpg_character_data", "rpg_character_rules"):
            self.assertNotIn(forbidden, text)

    def test_steps_are_complete_and_ordered(self):
        self.assertEqual(
            [step[0] for step in mod.CREATION_STEPS],
            ["identity", "race", "abilities", "combat", "skills", "gear", "summary"],
        )


if __name__ == "__main__":
    unittest.main()
