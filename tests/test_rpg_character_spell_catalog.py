from __future__ import annotations

import unittest

from rpg_character_spell_catalog import (
    CLERIC_SPELLS,
    catalog_rows,
    domain_spell_rows,
    normalize_domain,
)


class SpellCatalogTests(unittest.TestCase):
    def test_catalog_contains_core_low_level_cleric_spells(self):
        for key in (
            "guidance",
            "cure_light_wounds",
            "protection_from_chaos",
            "protection_from_evil",
            "protection_from_good",
            "protection_from_law",
            "spiritual_weapon",
            "searing_light",
            "divine_power",
        ):
            self.assertIn(key, CLERIC_SPELLS)


    def test_level_one_contains_all_four_protection_from_variants(self):
        expected = {
            "Protection from Chaos",
            "Protection from Evil",
            "Protection from Good",
            "Protection from Law",
        }
        names = {
            row["name"]
            for row in CLERIC_SPELLS.values()
            if int(row["spell_level"]) == 1
        }
        self.assertTrue(expected.issubset(names))
        for key in (
            "protection_from_chaos",
            "protection_from_evil",
            "protection_from_good",
            "protection_from_law",
        ):
            self.assertEqual(CLERIC_SPELLS[key]["school"], "Abjuration")
            self.assertEqual(CLERIC_SPELLS[key]["range_text"], "Touch")

    def test_war_and_sun_domain_lists_are_available(self):
        rows = domain_spell_rows(["War", "Sun"], 4)
        names = {(row["domain_source"], row["spell_level"], row["name"]) for row in rows}
        self.assertIn(("War", 1, "Magic Weapon"), names)
        self.assertIn(("War", 2, "Spiritual Weapon"), names)
        self.assertIn(("Sun", 1, "Endure Elements"), names)
        self.assertIn(("Sun", 3, "Searing Light"), names)
        self.assertTrue(all(row["slot_kind"] == "domain" for row in rows))

    def test_french_domain_aliases_are_supported(self):
        self.assertEqual(normalize_domain("Guerre"), "war")
        self.assertEqual(normalize_domain("Soleil"), "sun")
        rows = domain_spell_rows(["Guerre", "Soleil"], 1)
        self.assertEqual(len(rows), 2)

    def test_catalog_filters_to_accessible_spell_level(self):
        rows = catalog_rows(max_spell_level=2, domains=["War", "Sun"])
        self.assertTrue(rows)
        self.assertTrue(all(int(row["spell_level"]) <= 2 for row in rows))


if __name__ == "__main__":
    unittest.main()
