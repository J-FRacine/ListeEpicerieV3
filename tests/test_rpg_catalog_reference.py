from __future__ import annotations

import unittest

from rpg_character_catalog import (
    RACE_PROFILES,
    RACE_LABELS,
    infer_race_key,
    get_race_profile,
)


class RpgRaceCatalogReferenceTests(unittest.TestCase):
    def test_expected_base_races_are_available(self):
        self.assertEqual(
            set(RACE_PROFILES),
            {
                "human",
                "dwarf",
                "elf",
                "gnome",
                "half_elf",
                "half_orc",
                "halfling",
                "custom",
            },
        )
        self.assertEqual(RACE_LABELS["human"], "Humain")
        self.assertEqual(RACE_LABELS["dwarf"], "Nain")
        self.assertEqual(RACE_LABELS["elf"], "Elfe")
        self.assertEqual(RACE_LABELS["halfling"], "Halfelin")

    def test_dwarf_profile_keeps_speed_exceptions(self):
        dwarf = get_race_profile("dwarf")
        self.assertEqual(dwarf["base_speed"], 20)
        self.assertTrue(dwarf["ignore_armor_speed"])
        self.assertTrue(dwarf["ignore_encumbrance_speed"])
        self.assertEqual(dwarf["ability_adjustments"], "+2 CON, +2 SAG, −2 CHA")

    def test_small_races_remain_small_and_speed_20(self):
        for race_key in ("gnome", "halfling"):
            with self.subTest(race=race_key):
                profile = get_race_profile(race_key)
                self.assertEqual(profile["size_key"], "small")
                self.assertEqual(profile["base_speed"], 20)

    def test_infer_race_key_accepts_french_english_accents_and_hyphens(self):
        expected = {
            "Humain": "human",
            "human": "human",
            "Nain": "dwarf",
            "Elfe": "elf",
            "Demi-elfe": "half_elf",
            "demi elfe": "half_elf",
            "Half-Elf": "half_elf",
            "Demi-orque": "half_orc",
            "demi orc": "half_orc",
            "Half Orc": "half_orc",
            "Halfelin": "halfling",
        }
        for text, race_key in expected.items():
            with self.subTest(text=text):
                self.assertEqual(infer_race_key(text), race_key)

    def test_unknown_race_is_custom(self):
        self.assertEqual(infer_race_key("Vistani personnalisé"), "custom")
        self.assertEqual(infer_race_key(None), "custom")

    def test_get_race_profile_returns_a_deep_copy(self):
        first = get_race_profile("human")
        first["label"] = "Modifié"
        second = get_race_profile("human")
        self.assertEqual(second["label"], "Humain")

    def test_unknown_profile_returns_custom_defaults(self):
        profile = get_race_profile("not-a-race")
        self.assertEqual(profile["label"], "Autre / personnalisée")
        self.assertEqual(profile["size_key"], "medium")
        self.assertEqual(profile["base_speed"], 30)


if __name__ == "__main__":
    unittest.main()
