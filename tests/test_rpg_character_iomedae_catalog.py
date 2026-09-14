from __future__ import annotations

import unittest

from rpg_character_deities_catalog import DEITY_PROFILES


class IomedaeCatalogTests(unittest.TestCase):
    def test_iomedae_core_reference(self):
        profile = DEITY_PROFILES["iomedae"]
        self.assertEqual(profile["alignment"], "LG")
        self.assertEqual(
            tuple(profile["domains"].keys()),
            ("Glory", "Good", "Law", "Sun", "War"),
        )
        self.assertIn("Longsword", profile["favored_weapon"])
        self.assertEqual(profile["symbol"], "Épée et soleil")
        self.assertEqual(profile["sacred_animal"], "Lion")
        self.assertEqual(profile["sacred_colors"], "Rouge et blanc")
        self.assertEqual(profile["personal_domain_preset"], ("War", "Sun"))

    def test_subdomains_are_grouped_by_parent_domain(self):
        domains = DEITY_PROFILES["iomedae"]["domains"]
        self.assertIn("Heroism", domains["Glory"])
        self.assertIn("Redemption", domains["Good"])
        self.assertIn("Sovereignty", domains["Law"])
        self.assertIn("Light", domains["Sun"])
        self.assertIn("Tactics", domains["War"])


if __name__ == "__main__":
    unittest.main()
