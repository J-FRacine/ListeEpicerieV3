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


class _FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)
        self.executed = []
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=()):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None


class _FakeConnection:
    def __init__(self, rows):
        self.cursor_value = _FakeCursor(rows)
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commits += 1


class SpellCastPersistenceTests(unittest.TestCase):
    def _character(self):
        return {
            "id": 7,
            "character_level": 4,
            "class_name": "Cleric",
            "str_score": 10,
            "str_temp_score": None,
            "dex_score": 10,
            "dex_temp_score": None,
            "con_score": 10,
            "con_temp_score": None,
            "int_score": 10,
            "int_temp_score": None,
            "wis_score": 18,
            "wis_temp_score": None,
            "cha_score": 10,
            "cha_temp_score": None,
        }

    def test_cast_prepared_spell_atomically_increments_usage(self):
        connection = _FakeConnection(
            [
                self._character(),
                {
                    "id": 12,
                    "spell_name": "Aid",
                    "spell_level": 2,
                    "slot_kind": "normal",
                    "prepared_count": 2,
                    "used_count": 0,
                },
            ]
        )
        with patch.object(data, "_ensure"), patch.object(
            data, "get_connection", return_value=connection
        ):
            result = data.cast_prepared_spell(1, 7, 12)

        self.assertEqual(result["used_count"], 1)
        self.assertEqual(result["remaining"], 1)
        self.assertFalse(result["reusable"])
        self.assertEqual(connection.commits, 1)
        statements = "\n".join(sql for sql, _ in connection.cursor_value.executed)
        self.assertIn("FOR UPDATE", statements)
        self.assertIn("UPDATE rpg_character_prepared_spells", statements)

    def test_cast_orison_does_not_consume_usage(self):
        connection = _FakeConnection(
            [
                self._character(),
                {
                    "id": 13,
                    "spell_name": "Guidance",
                    "spell_level": 0,
                    "slot_kind": "normal",
                    "prepared_count": 1,
                    "used_count": 0,
                },
            ]
        )
        with patch.object(data, "_ensure"), patch.object(
            data, "get_connection", return_value=connection
        ):
            result = data.cast_prepared_spell(1, 7, 13)

        self.assertTrue(result["reusable"])
        self.assertEqual(result["used_count"], 0)
        statements = "\n".join(sql for sql, _ in connection.cursor_value.executed)
        self.assertNotIn("UPDATE rpg_character_prepared_spells", statements)


if __name__ == "__main__":
    unittest.main()
