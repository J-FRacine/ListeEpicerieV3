from __future__ import annotations

import unittest

from rpg_character_skill_dialogs import (
    skill_breakdown_text,
    skill_display_name,
)


class SkillHelperTests(unittest.TestCase):
    def test_display_name_preserves_french_and_english(self):
        self.assertEqual(
            skill_display_name("Perception", "Perception"),
            "Perception — Perception",
        )
        self.assertEqual(
            skill_display_name("Dressage", ""),
            "Dressage",
        )

    def test_breakdown_text_keeps_existing_formula(self):
        value = skill_breakdown_text(
            {
                "ability_key": "cha",
                "ability_modifier": -2,
                "ranks": 1,
                "class_bonus": 3,
                "misc_modifier": 0,
                "armor_penalty": -4,
                "total": -2,
            },
            ability_labels={"cha": "CHA"},
            format_modifier=lambda number: f"{int(number):+d}",
        )
        self.assertEqual(
            value,
            "CHA -2 + rangs +1 + classe +3 + divers +0 + armure -4 = total -2",
        )


if __name__ == "__main__":
    unittest.main()
