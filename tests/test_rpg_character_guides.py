from __future__ import annotations

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE = ROOT / "rpg_character_guides.py"
spec = importlib.util.spec_from_file_location("rpg_character_guides", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class FighterGuideTests(unittest.TestCase):
    def test_fighter_aliases(self):
        self.assertTrue(mod.is_fighter("Fighter"))
        self.assertTrue(mod.is_fighter("Guerrier"))
        self.assertTrue(mod.is_fighter("Fighter standard"))
        self.assertFalse(mod.is_fighter("Magus"))

    def test_level_four_reference(self):
        row = mod.fighter_reference(4)
        self.assertIsNotNone(row)
        self.assertEqual(row["hit_die"], "d10")
        self.assertEqual(row["bab"], 4)
        self.assertEqual(row["fortitude"], 4)
        self.assertEqual(row["reflex"], 1)
        self.assertEqual(row["will"], 1)
        self.assertIn("Don de combat bonus", row["specials"])

    def test_levels_one_to_four_and_milestones(self):
        self.assertEqual(mod.fighter_reference(1)["fortitude"], 2)
        self.assertEqual(mod.fighter_reference(2)["fortitude"], 3)
        self.assertEqual(mod.fighter_reference(3)["reflex"], 1)
        self.assertIsNone(mod.fighter_reference(5))
        text = " | ".join(mod.fighter_cumulative_milestones(4))
        self.assertIn("Bravoure +1", text)
        self.assertIn("Entraînement aux armures 1", text)
        self.assertIn("Augmentation générale de caractéristique +1", text)

    def test_feat_counts_level_four(self):
        base = mod.fighter_feat_counts(4)
        human = mod.fighter_feat_counts(4, "human")
        elf = mod.fighter_feat_counts(4, "elf")
        self.assertEqual(base["general"], 2)
        self.assertEqual(base["fighter_bonus"], 3)
        self.assertEqual(base["total"], 5)
        self.assertEqual(human["human_bonus"], 1)
        self.assertEqual(human["total"], 6)
        self.assertEqual(elf["total"], 5)

    def test_skill_rank_budget(self):
        fighter = mod.fighter_skill_rank_budget(4, 14, "elf")
        human = mod.fighter_skill_rank_budget(4, 14, "human")
        self.assertEqual(fighter["per_level"], 4)
        self.assertEqual(fighter["fighter_total"], 16)
        self.assertEqual(fighter["total_without_favored_class"], 16)
        self.assertEqual(human["human_standard_bonus"], 4)
        self.assertEqual(human["total_without_favored_class"], 20)
        # Pathfinder accorde au minimum 1 rang de classe par niveau.
        self.assertEqual(mod.fighter_skill_rank_budget(4, 3)["per_level"], 1)

    def test_fighter_class_skills(self):
        self.assertTrue(mod.is_fighter_class_skill({"skill_key": "climb"}))
        self.assertTrue(mod.is_fighter_class_skill({"skill_key": "craft_2"}))
        self.assertTrue(mod.is_fighter_class_skill({"skill_key": "profession_1"}))
        self.assertTrue(mod.is_fighter_class_skill({"english_name": "Knowledge (dungeoneering)"}))
        self.assertFalse(mod.is_fighter_class_skill({"skill_key": "perception", "skill_name": "Perception"}))

    def test_human_and_elf_comparison(self):
        human = mod.race_comparison("Humain")
        elf = mod.race_comparison("Elfe")
        self.assertEqual(human["race_key"], "human")
        self.assertIn("+2", human["ability_adjustments"])
        self.assertIn("6 dons", human["fighter_note"])
        self.assertEqual(elf["race_key"], "elf")
        self.assertIn("+2 DEX", elf["ability_adjustments"])
        self.assertIn("−2 CON", elf["ability_adjustments"])
        self.assertIn("aucun sort", elf["magic"])

    def test_core_armor_and_shield_presets(self):
        shirt = mod.gear_preset("chain_shirt")["equipment"]
        self.assertEqual((shirt["armor_bonus"], shirt["max_dex_bonus"], shirt["armor_check_penalty"], shirt["arcane_spell_failure"], shirt["weight_each"]), (4, 4, -2, 20, 25))
        breastplate = mod.gear_preset("breastplate")["equipment"]
        self.assertEqual((breastplate["armor_bonus"], breastplate["max_dex_bonus"], breastplate["armor_check_penalty"], breastplate["arcane_spell_failure"], breastplate["weight_each"]), (6, 3, -4, 25, 30))
        chainmail = mod.gear_preset("chainmail")["equipment"]
        self.assertEqual((chainmail["armor_bonus"], chainmail["max_dex_bonus"], chainmail["armor_check_penalty"], chainmail["arcane_spell_failure"], chainmail["weight_each"]), (6, 2, -5, 30, 40))
        plate = mod.gear_preset("full_plate")["equipment"]
        self.assertEqual((plate["armor_bonus"], plate["max_dex_bonus"], plate["armor_check_penalty"], plate["arcane_spell_failure"], plate["weight_each"]), (9, 1, -6, 35, 50))
        shield = mod.gear_preset("heavy_steel_shield")["equipment"]
        self.assertEqual((shield["shield_bonus"], shield["armor_check_penalty"], shield["arcane_spell_failure"], shield["weight_each"]), (2, -2, 15, 15))

    def test_core_weapon_presets(self):
        sword = mod.gear_preset("longsword")
        self.assertEqual(sword["equipment"]["weight_each"], 4)
        self.assertEqual(sword["attack"]["damage"], "1d8")
        self.assertEqual(sword["attack"]["critical"], "19-20/x2")
        rapier = mod.gear_preset("rapier")
        self.assertEqual(rapier["attack"]["damage"], "1d6")
        self.assertEqual(rapier["attack"]["critical"], "18-20/x2")
        greatsword = mod.gear_preset("greatsword")
        self.assertEqual(greatsword["attack"]["damage"], "2d6")
        self.assertEqual(greatsword["equipment"]["weight_each"], 8)
        bow = mod.gear_preset("longbow")
        self.assertEqual(bow["attack"]["ability_key"], "dex")
        self.assertEqual(bow["attack"]["damage"], "1d8")
        self.assertEqual(bow["attack"]["critical"], "x3")
        self.assertEqual(bow["attack"]["attack_range"], "100 pi")

    def test_reference_lines_explain_where_values_go(self):
        armor = " | ".join(mod.gear_reference_lines("breastplate"))
        weapon = " | ".join(mod.gear_reference_lines("longsword"))
        self.assertIn("Équipement", armor)
        self.assertIn("bonus CA +6", armor)
        self.assertIn("Attaques", weapon)
        self.assertIn("1d8", weapon)

    def test_module_has_no_ui_or_database_dependencies(self):
        text = MODULE.read_text(encoding="utf-8")
        for forbidden in (
            "from nicegui",
            "import nicegui",
            "from db",
            "import db",
            "rpg_character_data",
            "rpg_character_rules",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
