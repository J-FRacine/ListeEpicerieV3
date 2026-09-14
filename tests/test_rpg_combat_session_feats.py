from __future__ import annotations

import unittest

from rpg_combat_session import combat_summary


class CombatSummaryFeatTests(unittest.TestCase):
    def test_feat_modifiers_are_added_without_rewriting_character(self):
        character = {
            "current_hp": 12,
            "max_hp": 20,
            "nonlethal_damage": 0,
        }
        attacks = [{"id": 7, "attack_name": "Masse"}]
        saves = [
            {"save_key": "fortitude"},
            {"save_key": "will"},
        ]

        snapshot = combat_summary(
            character=character,
            attacks=attacks,
            saves=saves,
            selected_attack_id=7,
            temporary_attack_bonus=1,
            armor_class_total=lambda c: 18,
            touch_armor_class=lambda c: 12,
            flat_footed_armor_class=lambda c: 16,
            initiative_total=lambda c: 2,
            cmb_total=lambda c: 4,
            cmd_total=lambda c: 16,
            attack_total=lambda c, a: 5,
            save_total=lambda c, row: (
                6 if row["save_key"] == "fortitude" else 7
            ),
            feat_effects={
                "attack_modifier": -2,
                "initiative_modifier": 4,
                "cmb_modifier": -2,
                "cmd_modifier": 1,
                "save_modifiers": {
                    "all": 1,
                    "fortitude": 2,
                },
            },
        )

        self.assertEqual(snapshot["selected_attack_total"], 4)
        self.assertEqual(snapshot["initiative"], 6)
        self.assertEqual(snapshot["cmb"], 2)
        self.assertEqual(snapshot["cmd"], 17)
        self.assertEqual(snapshot["save_totals"]["fortitude"], 9)
        self.assertEqual(snapshot["save_totals"]["will"], 8)
        self.assertEqual(character["current_hp"], 12)


if __name__ == "__main__":
    unittest.main()
