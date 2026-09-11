from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUIDES = ROOT / "rpg_character_guides.py"
CREATION = ROOT / "rpg_character_creation.py"

spec = importlib.util.spec_from_file_location("rpg_character_guides_cleric", GUIDES)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class ClericGuideTests(unittest.TestCase):
    def test_cleric_aliases_and_level_four_reference(self):
        self.assertTrue(mod.is_cleric("Clerc"))
        self.assertTrue(mod.is_cleric("Cleric"))
        self.assertTrue(mod.is_cleric("Clerc standard"))
        self.assertFalse(mod.is_cleric("Fighter"))
        row = mod.cleric_reference(4)
        self.assertEqual(row["hit_die"], "d8")
        self.assertEqual((row["bab"], row["fortitude"], row["reflex"], row["will"]), (3, 4, 1, 4))
        self.assertEqual(row["channel_dice"], "2d6")
        self.assertEqual(row["spells_per_day"], {0: "4", 1: "3+1 domaine", 2: "2+1 domaine"})

    def test_cleric_level_progression_one_to_four(self):
        expected = {
            1: (0, 2, 0, 2, "1d6"),
            2: (1, 3, 0, 3, "1d6"),
            3: (2, 3, 1, 3, "2d6"),
            4: (3, 4, 1, 4, "2d6"),
        }
        for level, values in expected.items():
            row = mod.cleric_reference(level)
            self.assertEqual(
                (row["bab"], row["fortitude"], row["reflex"], row["will"], row["channel_dice"]),
                values,
            )
        self.assertIsNone(mod.cleric_reference(5))

    def test_human_cleric_feats_and_skill_budget(self):
        feats = mod.cleric_feat_counts(4, "human")
        self.assertEqual(feats, {"general": 2, "human_bonus": 1, "total": 3})
        budget = mod.cleric_skill_rank_budget(4, 12, "human")
        self.assertEqual(budget["per_level"], 3)
        self.assertEqual(budget["cleric_total"], 12)
        self.assertEqual(budget["human_standard_bonus"], 4)
        self.assertEqual(budget["total_without_favored_class"], 16)

    def test_cleric_class_skills(self):
        for key in (
            "appraise", "diplomacy", "heal", "knowledge_arcana",
            "knowledge_history", "knowledge_nobility", "knowledge_planes",
            "knowledge_religion", "linguistics", "sense_motive", "spellcraft",
            "craft_1", "profession_2",
        ):
            self.assertTrue(mod.is_cleric_class_skill({"skill_key": key}), key)
        self.assertFalse(mod.is_cleric_class_skill({"skill_key": "stealth", "skill_name": "Discrétion"}))

    def test_spell_and_channel_reference_uses_wisdom_and_charisma(self):
        info = mod.cleric_spell_reference(4, wisdom_score=18, charisma_score=14)
        self.assertEqual(info["max_spell_level"], 2)
        self.assertEqual(info["minimum_wisdom"], 12)
        self.assertEqual(info["save_dcs"], {1: 15, 2: 16})
        self.assertEqual(info["channel_uses_per_day"], 5)
        self.assertEqual(info["channel_dc"], 14)
        self.assertEqual(info["channel_dice"], "2d6")

    def test_creation_ui_contains_cleric_guidance_without_schema_dependency(self):
        text = CREATION.read_text(encoding="utf-8")
        for expected in (
            "Repères Clerc / Cleric",
            "Humain pour un Clerc",
            "Repères de caractéristiques Clerc",
            "Résumé Clerc",
            "Les sorts de Clerc sont divins",
            "deux domaines",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("ALTER TABLE", text)


if __name__ == "__main__":
    unittest.main()
