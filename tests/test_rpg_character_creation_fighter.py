from __future__ import annotations

import ast
import importlib.util
import inspect
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "rpg_character_creation.py"
GUIDES = ROOT / "rpg_character_guides.py"

spec = importlib.util.spec_from_file_location("rpg_character_creation_v141", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class FighterCreationIntegrationTests(unittest.TestCase):
    def test_builder_keeps_v140_dependency_contract(self):
        names = list(inspect.signature(mod.build_character_creation_panel).parameters)
        self.assertEqual(
            names,
            [
                "ui", "user_id", "character", "get_rpg_character",
                "update_rpg_character_identity", "update_rpg_character_combat",
                "list_rpg_saves", "update_rpg_saves", "list_rpg_skills",
                "update_rpg_skills", "list_rpg_equipment", "list_rpg_attacks",
                "character_sheet_audit", "apply_equipment_effects",
                "armor_class_total", "touch_armor_class", "flat_footed_armor_class",
                "initiative_total", "cmb_total", "cmd_total", "ability_modifier",
                "format_modifier", "get_race_profile", "race_labels", "size_labels",
                "ability_labels", "ability_long_labels", "save_definitions",
                "character_url", "notify_error",
            ],
        )

    def test_source_contains_fighter_level_four_helpers(self):
        text = MODULE.read_text(encoding="utf-8")
        for expected in (
            "Repères Fighter / Guerrier",
            "Appliquer les repères de classe du niveau",
            "Appliquer les repères de compétences de classe",
            "Humain ou Elfe pour un Fighter avec une orientation magique?",
            "Catalogue de référence — armes et armures courantes",
            "Entraînement aux armures 1",
            "Échec sorts profanes",
        ):
            self.assertIn(expected, text)

    def test_fighter_guides_are_imported_as_pure_helpers(self):
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)]
        guide_import = next(node for node in imports if node.module == "rpg_character_guides")
        imported = {alias.name for alias in guide_import.names}
        for expected in (
            "fighter_reference", "fighter_feat_counts", "fighter_skill_rank_budget",
            "is_fighter", "is_fighter_class_skill", "race_comparison",
            "gear_preset_options", "gear_reference_lines",
            "cleric_reference", "cleric_spell_reference", "cleric_skill_rank_budget",
            "is_cleric", "is_cleric_class_skill",
        ):
            self.assertIn(expected, imported)

    def test_creation_module_stays_decoupled_from_nicegui_database_and_rules(self):
        text = MODULE.read_text(encoding="utf-8")
        for forbidden in (
            "from nicegui", "import nicegui", "from db", "import db",
            "rpg_character_data", "rpg_character_rules",
        ):
            self.assertNotIn(forbidden, text)
        self.assertTrue(GUIDES.exists())


    def test_new_character_with_unselected_race_is_detected(self):
        self.assertTrue(
            mod.race_selection_pending({"race_key": "custom", "race": None})
        )
        self.assertFalse(
            mod.race_selection_pending({"race_key": "human", "race": "Humain"})
        )
        self.assertFalse(
            mod.race_selection_pending({"race_key": "custom", "race": "Dhampir"})
        )

    def test_identity_step_defers_persistence_until_race_when_needed(self):
        text = MODULE.read_text(encoding="utf-8")
        self.assertIn("if race_selection_pending(working):", text)
        self.assertIn("les deux étapes seront enregistrées ensemble", text)
        self.assertIn("Sous-classe / archétype (facultatif)", text)

    def test_steps_remain_unchanged(self):
        self.assertEqual(
            [step[0] for step in mod.CREATION_STEPS],
            ["identity", "race", "abilities", "combat", "skills", "gear", "summary"],
        )


if __name__ == "__main__":
    unittest.main()
