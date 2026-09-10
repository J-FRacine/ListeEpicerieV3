from __future__ import annotations

from decimal import Decimal
import unittest

from rpg_character_rules import (
    ability_modifier,
    ability_modifier_for_character,
    ac_size_modifier,
    combat_maneuver_size_modifier,
    carrying_capacity,
    reduced_speed_for_base,
    equipment_effects,
    apply_equipment_effects,
    armor_class_breakdown,
    armor_class_total,
    touch_armor_class,
    flat_footed_armor_class,
    initiative_total,
    cmb_breakdown,
    cmb_total,
    cmd_breakdown,
    cmd_total,
    save_total,
    skill_class_bonus,
    skill_breakdown,
    skill_total,
    attack_breakdown,
    attack_total,
    pathfinder_reference_checks,
    character_sheet_audit,
)


class RpgAbilityReferenceTests(unittest.TestCase):
    def test_ability_modifier_rounds_down(self):
        expected = {
            7: -2,
            8: -1,
            9: -1,
            10: 0,
            11: 0,
            12: 1,
            18: 4,
        }
        for score, modifier in expected.items():
            with self.subTest(score=score):
                self.assertEqual(ability_modifier(score), modifier)

    def test_temporary_ability_score_overrides_base(self):
        self.assertEqual(ability_modifier(18, 7), -2)
        character = {"dex_score": 18, "dex_temp_score": 7}
        self.assertEqual(
            ability_modifier_for_character(character, "dex"),
            -2,
        )


class RpgSizeAndCapacityReferenceTests(unittest.TestCase):
    def test_size_modifiers_keep_pathfinder_signs(self):
        self.assertEqual(ac_size_modifier("small"), 1)
        self.assertEqual(ac_size_modifier("large"), -1)
        self.assertEqual(combat_maneuver_size_modifier("small"), -1)
        self.assertEqual(combat_maneuver_size_modifier("large"), 1)

    def test_strength_10_medium_biped_capacity(self):
        capacity = carrying_capacity(
            {
                "str_score": 10,
                "size_key": "medium",
                "is_quadruped": False,
                "carrying_capacity_multiplier": 1,
            }
        )
        self.assertEqual(capacity["light_max"], Decimal("33"))
        self.assertEqual(capacity["medium_max"], Decimal("66"))
        self.assertEqual(capacity["heavy_max"], Decimal("100"))
        self.assertEqual(capacity["lift_off_ground_max"], Decimal("200"))
        self.assertEqual(capacity["push_drag_max"], Decimal("500"))

    def test_size_and_quadruped_capacity_multipliers(self):
        small = carrying_capacity(
            {
                "str_score": 10,
                "size_key": "small",
                "is_quadruped": False,
                "carrying_capacity_multiplier": 1,
            }
        )
        quadruped = carrying_capacity(
            {
                "str_score": 10,
                "size_key": "medium",
                "is_quadruped": True,
                "carrying_capacity_multiplier": 1,
            }
        )
        self.assertEqual(small["heavy_max"], Decimal("75.00"))
        self.assertEqual(quadruped["heavy_max"], Decimal("150.0"))

    def test_racial_capacity_multiplier_is_applied(self):
        capacity = carrying_capacity(
            {
                "str_score": 10,
                "size_key": "medium",
                "is_quadruped": False,
                "carrying_capacity_multiplier": 2,
            }
        )
        self.assertEqual(capacity["heavy_max"], Decimal("200"))

    def test_reduced_speed_reference_values(self):
        self.assertEqual(reduced_speed_for_base(5), 5)
        self.assertEqual(reduced_speed_for_base(20), 15)
        self.assertEqual(reduced_speed_for_base(30), 20)
        self.assertEqual(reduced_speed_for_base(40), 30)
        self.assertEqual(reduced_speed_for_base(130), 85)


class RpgEquipmentReferenceTests(unittest.TestCase):
    def base_character(self):
        return {
            "str_score": 10,
            "dex_score": 18,
            "size_key": "medium",
            "base_speed": 30,
            "is_quadruped": False,
            "carrying_capacity_multiplier": 1,
            "armor_bonus": 0,
            "shield_bonus": 0,
            "armor_check_penalty": 0,
            "ignore_armor_speed": False,
            "ignore_encumbrance_speed": False,
        }

    def test_medium_load_reduces_speed_and_caps_dex(self):
        effects = equipment_effects(
            self.base_character(),
            [
                {
                    "item_name": "Charge",
                    "item_type": "gear",
                    "quantity": 1,
                    "weight_each": 40,
                    "carried": True,
                    "equipped": False,
                }
            ],
        )
        self.assertEqual(effects["load_key"], "medium")
        self.assertEqual(effects["effective_max_dex_bonus"], 3)
        self.assertEqual(effects["effective_ac_dex_modifier"], 3)
        self.assertEqual(effects["effective_armor_check_penalty"], -3)
        self.assertEqual(effects["final_speed"], 20)

    def test_ignore_encumbrance_speed_keeps_base_speed(self):
        character = self.base_character()
        character["ignore_encumbrance_speed"] = True
        effects = equipment_effects(
            character,
            [
                {
                    "item_name": "Charge",
                    "item_type": "gear",
                    "quantity": 1,
                    "weight_each": 40,
                    "carried": True,
                    "equipped": False,
                }
            ],
        )
        self.assertEqual(effects["load_key"], "medium")
        self.assertEqual(effects["load_speed"], 20)
        self.assertEqual(effects["final_speed"], 30)

    def test_equipped_armor_and_shield_are_combined(self):
        effects = equipment_effects(
            self.base_character(),
            [
                {
                    "item_name": "Armure",
                    "item_type": "armor",
                    "quantity": 1,
                    "weight_each": 10,
                    "carried": True,
                    "equipped": True,
                    "armor_category": "light",
                    "armor_bonus": 5,
                    "shield_bonus": 0,
                    "enhancement_bonus": 1,
                    "max_dex_bonus": 4,
                    "armor_check_penalty": -2,
                    "speed_reduction_applies": False,
                },
                {
                    "item_name": "Bouclier",
                    "item_type": "shield",
                    "quantity": 1,
                    "weight_each": 5,
                    "carried": True,
                    "equipped": True,
                    "armor_category": "none",
                    "armor_bonus": 0,
                    "shield_bonus": 2,
                    "enhancement_bonus": 1,
                    "max_dex_bonus": None,
                    "armor_check_penalty": -1,
                },
            ],
        )
        self.assertEqual(effects["equipment_armor_bonus"], 6)
        self.assertEqual(effects["equipment_shield_bonus"], 3)
        self.assertEqual(effects["equipment_armor_check_penalty"], -3)
        self.assertEqual(effects["effective_max_dex_bonus"], 4)

    def test_apply_equipment_effects_does_not_mutate_source(self):
        character = self.base_character()
        enriched = apply_equipment_effects(character, [])
        self.assertNotIn("equipment_effects", character)
        self.assertIn("equipment_effects", enriched)
        self.assertEqual(enriched["final_speed"], 30)


class RpgCombatReferenceTests(unittest.TestCase):
    def character(self):
        return {
            "str_score": 14,
            "dex_score": 14,
            "con_score": 14,
            "wis_score": 12,
            "size_key": "medium",
            "base_attack_bonus": 3,
            "armor_bonus": 4,
            "shield_bonus": 2,
            "natural_armor_bonus": 1,
            "deflection_bonus": 1,
            "misc_ac_modifier": -1,
            "initiative_misc_modifier": 2,
            "cmb_misc_modifier": 1,
            "cmd_misc_modifier": 2,
        }

    def test_armor_class_three_forms(self):
        breakdown = armor_class_breakdown(self.character())
        self.assertEqual(breakdown["total"], 19)
        self.assertEqual(breakdown["touch"], 12)
        self.assertEqual(breakdown["flat_footed"], 17)
        self.assertEqual(armor_class_total(self.character()), 19)
        self.assertEqual(touch_armor_class(self.character()), 12)
        self.assertEqual(flat_footed_armor_class(self.character()), 17)

    def test_flat_footed_keeps_negative_dexterity(self):
        character = self.character()
        character["dex_score"] = 7
        breakdown = armor_class_breakdown(character)
        self.assertEqual(breakdown["dex_modifier"], -2)
        self.assertEqual(breakdown["flat_footed_dex_modifier"], -2)

    def test_initiative_is_dex_plus_misc(self):
        self.assertEqual(initiative_total(self.character()), 4)

    def test_medium_cmb_uses_strength(self):
        breakdown = cmb_breakdown(self.character())
        self.assertEqual(breakdown["ability_key"], "str")
        self.assertEqual(breakdown["total"], 6)
        self.assertEqual(cmb_total(self.character()), 6)

    def test_tiny_cmb_uses_dexterity_and_special_size_modifier(self):
        character = {
            "size_key": "tiny",
            "base_attack_bonus": 1,
            "str_score": 18,
            "dex_score": 14,
            "cmb_misc_modifier": 0,
        }
        breakdown = cmb_breakdown(character)
        self.assertEqual(breakdown["ability_key"], "dex")
        self.assertEqual(breakdown["size_modifier"], -2)
        self.assertEqual(breakdown["total"], 1)

    def test_cmd_applies_negative_misc_ac_penalty(self):
        character = self.character()
        breakdown = cmd_breakdown(character)
        self.assertEqual(breakdown["automatic_ac_penalty"], -1)
        self.assertEqual(breakdown["total"], 21)
        self.assertEqual(cmd_total(character), 21)

    def test_save_uses_defined_ability(self):
        character = self.character()
        fortitude = {
            "save_key": "fortitude",
            "base_save": 3,
            "magic_modifier": 1,
            "misc_modifier": -1,
            "temporary_modifier": 2,
        }
        fear = {
            "save_key": "fear",
            "base_save": 1,
            "magic_modifier": 0,
            "misc_modifier": 0,
            "temporary_modifier": 0,
        }
        self.assertEqual(save_total(character, fortitude), 7)
        self.assertEqual(save_total(character, fear), 2)

    def test_attack_uses_ac_size_modifier(self):
        character = self.character()
        character["size_key"] = "small"
        attack = {
            "ability_key": "str",
            "magic_bonus": 1,
            "misc_bonus": -1,
        }
        breakdown = attack_breakdown(character, attack)
        self.assertEqual(breakdown["size_modifier"], 1)
        self.assertEqual(breakdown["total"], 6)
        self.assertEqual(attack_total(character, attack), 6)


class RpgSkillReferenceTests(unittest.TestCase):
    def test_class_bonus_requires_at_least_one_rank(self):
        self.assertEqual(
            skill_class_bonus({"ranks": 0, "class_skill": True}),
            0,
        )
        self.assertEqual(
            skill_class_bonus({"ranks": 1, "class_skill": True}),
            3,
        )

    def test_skill_breakdown_includes_armor_penalty_and_class_bonus(self):
        character = {
            "dex_score": 14,
            "effective_armor_check_penalty": -3,
        }
        skill = {
            "ability_key": "dex",
            "ranks": Decimal("2"),
            "misc_modifier": 1,
            "class_skill": True,
            "armor_check_applies": True,
            "double_armor_penalty": False,
        }
        breakdown = skill_breakdown(character, skill)
        self.assertEqual(breakdown["ability_modifier"], 2)
        self.assertEqual(breakdown["class_bonus"], 3)
        self.assertEqual(breakdown["armor_penalty"], -3)
        self.assertEqual(breakdown["total"], Decimal("5"))
        self.assertEqual(skill_total(character, skill), Decimal("5"))

    def test_double_armor_penalty_is_doubled_once(self):
        character = {
            "str_score": 14,
            "effective_armor_check_penalty": -3,
        }
        skill = {
            "ability_key": "str",
            "ranks": 1,
            "misc_modifier": 0,
            "class_skill": False,
            "armor_check_applies": True,
            "double_armor_penalty": True,
        }
        self.assertEqual(
            skill_breakdown(character, skill)["armor_penalty"],
            -6,
        )


class RpgAuditReferenceTests(unittest.TestCase):
    def test_embedded_reference_checks_all_pass(self):
        checks = pathfinder_reference_checks()
        self.assertEqual(len(checks), 5)
        self.assertTrue(all(check["passed"] for check in checks))

    def test_audit_detects_common_entry_errors(self):
        character = {"dex_score": 12, "armor_check_penalty": 2}
        skills = [
            {
                "skill_name": "Acrobaties",
                "english_name": "Acrobatics",
                "ability_key": "dex",
                "ranks": 1,
                "misc_modifier": 3,
                "class_skill": True,
                "trained_only": False,
                "armor_check_applies": True,
                "double_armor_penalty": False,
            },
            {
                "skill_name": "Sabotage",
                "ability_key": "dex",
                "ranks": 0,
                "misc_modifier": 0,
                "class_skill": False,
                "trained_only": True,
                "armor_check_applies": False,
                "double_armor_penalty": True,
            },
        ]
        audit = character_sheet_audit(character, skills)
        details = "\n".join(warning["detail"] for warning in audit["warnings"])
        self.assertIn("signe négatif", details)
        self.assertIn("bonus automatique", details)
        self.assertIn("exige une formation", details)
        self.assertIn("option Armure", details)
        self.assertEqual(
            audit["reference_checks_passed"],
            audit["reference_checks_total"],
        )


if __name__ == "__main__":
    unittest.main()
