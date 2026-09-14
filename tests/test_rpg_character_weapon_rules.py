from __future__ import annotations

import unittest

from rpg_character_weapon_rules import (
    attack_defaults_from_weapon,
    merge_attacks_with_weapons,
    merge_equipment_with_weapon_details,
    weapon_attack_bonus,
)


class WeaponRulesTests(unittest.TestCase):
    def test_masterwork_bonus_does_not_stack_with_magic(self):
        self.assertEqual(
            weapon_attack_bonus({
                "weapon_masterwork": True,
                "weapon_enhancement_bonus": 0,
            }),
            1,
        )
        self.assertEqual(
            weapon_attack_bonus({
                "weapon_masterwork": True,
                "weapon_enhancement_bonus": 2,
            }),
            2,
        )

    def test_linked_weapon_becomes_magic_source(self):
        attack = {
            "id": 3,
            "attack_name": "Épée",
            "ability_key": "str",
            "magic_bonus": 9,
            "misc_bonus": 0,
            "damage": None,
            "critical": None,
            "attack_range": None,
            "attack_type": None,
            "ammunition_current": None,
            "ammunition_max": None,
        }
        link = {
            3: {
                "attack_id": 3,
                "linked_equipment_id": 8,
                "linked_equipment_name": "Épée longue",
                "grip_mode": "two_handed",
                "weapon_damage": "1d8",
                "weapon_critical": "19-20/x2",
                "weapon_damage_type": "Tranchant",
                "weapon_range": None,
                "weapon_masterwork": True,
                "weapon_enhancement_bonus": 2,
                "weapon_ammunition_current": None,
                "weapon_ammunition_max": None,
            }
        }
        row = merge_attacks_with_weapons(
            [attack],
            link,
        )[0]
        self.assertEqual(row["manual_magic_bonus"], 9)
        self.assertEqual(row["magic_bonus"], 2)
        self.assertEqual(row["damage"], "1d8")
        self.assertEqual(row["critical"], "19-20/x2")
        self.assertEqual(row["attack_type"], "Tranchant")

    def test_attack_specific_damage_overrides_weapon_base(self):
        row = merge_attacks_with_weapons(
            [{
                "id": 1,
                "attack_name": "Épée à deux mains",
                "ability_key": "str",
                "magic_bonus": 0,
                "misc_bonus": 0,
                "damage": "1d8+4",
                "critical": "19-20/x2",
                "attack_range": None,
                "attack_type": "Tranchant",
                "ammunition_current": None,
                "ammunition_max": None,
            }],
            {
                1: {
                    "linked_equipment_id": 2,
                    "linked_equipment_name": "Épée longue",
                    "grip_mode": "two_handed",
                    "weapon_damage": "1d8",
                    "weapon_critical": "19-20/x2",
                    "weapon_damage_type": "Tranchant",
                    "weapon_enhancement_bonus": 0,
                    "weapon_masterwork": False,
                }
            },
        )[0]
        self.assertEqual(row["damage"], "1d8+4")
        self.assertFalse(row["damage_inherited"])

    def test_equipment_merge_keeps_linked_attacks(self):
        rows = merge_equipment_with_weapon_details(
            [{
                "id": 10,
                "item_name": "Arc",
                "item_type": "weapon",
                "proficiency_required": None,
            }],
            {
                10: {
                    "equipment_id": 10,
                    "weapon_damage": "1d8",
                    "weapon_handedness": "two_handed",
                    "weapon_proficiency_required": "Armes de guerre",
                }
            },
            {
                10: [{
                    "attack_id": 99,
                    "attack_name": "Tir",
                }]
            },
        )
        self.assertEqual(
            rows[0]["proficiency_required"],
            "Armes de guerre",
        )
        self.assertEqual(
            rows[0]["linked_attacks"][0]["attack_id"],
            99,
        )

    def test_attack_defaults_use_physical_weapon(self):
        values = attack_defaults_from_weapon({
            "id": 7,
            "item_name": "Espadon",
            "weapon_damage": "2d6",
            "weapon_critical": "19-20/x2",
            "weapon_damage_type": "Tranchant",
            "weapon_range": None,
            "weapon_handedness": "two_handed",
        })
        self.assertEqual(values["linked_equipment_id"], 7)
        self.assertEqual(values["damage"], "2d6")
        self.assertEqual(values["grip_mode"], "two_handed")


if __name__ == "__main__":
    unittest.main()
