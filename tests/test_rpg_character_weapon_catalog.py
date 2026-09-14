from __future__ import annotations

import unittest

from rpg_character_weapon_catalog import (
    WEAPON_TEMPLATES,
    weapon_template_values,
)


class WeaponCatalogTests(unittest.TestCase):
    def test_iomedae_longsword_template(self):
        template = WEAPON_TEMPLATES["iomedae_longsword"]
        self.assertEqual(template["item_name"], "Épée longue")
        self.assertEqual(template["weapon_critical"], "19-20/x2")
        self.assertEqual(
            template["weapon_damage_type"],
            "Tranchant",
        )

    def test_medium_and_small_damage(self):
        self.assertEqual(
            weapon_template_values(
                "iomedae_longsword",
                "medium",
            )["weapon_damage"],
            "1d8",
        )
        self.assertEqual(
            weapon_template_values(
                "iomedae_longsword",
                "small",
            )["weapon_damage"],
            "1d6",
        )

    def test_unknown_size_does_not_invent_damage(self):
        self.assertEqual(
            weapon_template_values(
                "iomedae_longsword",
                "huge",
            )["weapon_damage"],
            "",
        )


if __name__ == "__main__":
    unittest.main()
