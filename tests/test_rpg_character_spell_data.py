from __future__ import annotations

import importlib
import sys
import unittest
from types import ModuleType
from unittest.mock import Mock, patch


db_stub = ModuleType("db")
db_stub.get_connection = Mock(side_effect=AssertionError("Accès PostgreSQL interdit dans ces tests"))
with patch.dict(sys.modules, {"db": db_stub}):
    data = importlib.import_module("rpg_character_spell_data")


class SpellDataNormalizationTests(unittest.TestCase):
    def test_default_profile_uses_character_level_and_wisdom(self):
        profile = data._default_profile({"id": 7, "character_level": 4})
        self.assertEqual(profile["class_key"], "cleric")
        self.assertEqual(profile["class_level"], 4)
        self.assertEqual(profile["caster_level"], 4)
        self.assertEqual(profile["ability_key"], "wis")
        self.assertTrue(profile["is_default"])

    def test_preparation_normalizes_orison_usage_to_zero(self):
        row = data._normalize_preparation(
            {
                "spell_name": "Guidance",
                "spell_level": 0,
                "slot_kind": "normal",
                "prepared_count": 1,
                "used_count": 1,
            }
        )
        self.assertEqual(row["used_count"], 0)

    def test_preparation_rejects_domain_orison(self):
        with self.assertRaisesRegex(ValueError, "oraison"):
            data._normalize_preparation(
                {
                    "spell_name": "Test",
                    "spell_level": 0,
                    "slot_kind": "domain",
                    "prepared_count": 1,
                }
            )

    def test_preparation_rejects_used_above_prepared(self):
        with self.assertRaisesRegex(ValueError, "dépasser"):
            data._normalize_preparation(
                {
                    "spell_name": "Bless",
                    "spell_level": 1,
                    "slot_kind": "normal",
                    "prepared_count": 1,
                    "used_count": 2,
                }
            )


if __name__ == "__main__":
    unittest.main()
