from __future__ import annotations

import unittest

from rpg_character_spell_rules import (
    SpellRuleError,
    ability_modifier_from_score,
    cleric_slot_table,
    effective_ability_score,
    max_cleric_spell_level,
    prepared_usage_summary,
    validate_preparation_capacity,
)


class SpellRulesTests(unittest.TestCase):
    def test_level_one_cleric_with_wisdom_18_gets_bonus_spell(self):
        rows = cleric_slot_table(1, 18)
        zero = next(row for row in rows if row["spell_level"] == 0)
        first = next(row for row in rows if row["spell_level"] == 1)
        self.assertEqual(zero["normal_slots"], 3)
        self.assertEqual(zero["domain_slots"], 0)
        self.assertEqual(first["base_slots"], 1)
        self.assertEqual(first["bonus_slots"], 1)
        self.assertEqual(first["normal_slots"], 2)
        self.assertEqual(first["domain_slots"], 1)
        self.assertEqual(first["save_dc"], 15)

    def test_level_four_cleric_progression_matches_reference(self):
        rows = {row["spell_level"]: row for row in cleric_slot_table(4, 18)}
        self.assertEqual(set(rows), {0, 1, 2})
        self.assertEqual(rows[0]["normal_slots"], 4)
        self.assertEqual(rows[1]["base_slots"], 3)
        self.assertEqual(rows[2]["base_slots"], 2)
        self.assertEqual(rows[1]["domain_slots"], 1)
        self.assertEqual(rows[2]["domain_slots"], 1)
        self.assertEqual(rows[2]["normal_slots"], 3)
        self.assertEqual(max_cleric_spell_level(4), 2)

    def test_high_level_progression_reaches_ninth_level_spells(self):
        rows = {row["spell_level"]: row for row in cleric_slot_table(17, 19)}
        self.assertIn(9, rows)
        self.assertEqual(rows[9]["base_slots"], 1)
        self.assertEqual(rows[9]["domain_slots"], 1)

    def test_effective_ability_prefers_temporary_score(self):
        character = {"wis_score": 16, "wis_temp_score": 20}
        self.assertEqual(effective_ability_score(character, "wis"), 20)
        self.assertEqual(ability_modifier_from_score(20), 5)

    def test_prepared_usage_keeps_orisons_reusable(self):
        slots = cleric_slot_table(3, 16)
        prepared = [
            {"spell_level": 0, "slot_kind": "normal", "prepared_count": 2, "used_count": 2},
            {"spell_level": 1, "slot_kind": "normal", "prepared_count": 2, "used_count": 1},
            {"spell_level": 1, "slot_kind": "domain", "prepared_count": 1, "used_count": 1},
        ]
        rows = {row["spell_level"]: row for row in prepared_usage_summary(slots, prepared)}
        self.assertEqual(rows[0]["normal_used"], 0)
        self.assertEqual(rows[0]["normal_available"], 2)
        self.assertEqual(rows[1]["normal_available"], 1)
        self.assertEqual(rows[1]["domain_available"], 0)

    def test_capacity_rejects_second_domain_spell_same_level(self):
        slots = cleric_slot_table(4, 18)
        existing = [
            {"id": 1, "spell_level": 1, "slot_kind": "domain", "prepared_count": 1}
        ]
        with self.assertRaisesRegex(SpellRuleError, "Trop d’emplacements"):
            validate_preparation_capacity(
                slot_rows=slots,
                existing_rows=existing,
                spell_level=1,
                slot_kind="domain",
                prepared_count=1,
            )

    def test_capacity_rejects_inaccessible_spell_level(self):
        with self.assertRaisesRegex(SpellRuleError, "n’est pas accessible"):
            validate_preparation_capacity(
                slot_rows=cleric_slot_table(2, 18),
                existing_rows=[],
                spell_level=2,
                slot_kind="normal",
                prepared_count=1,
            )

    def test_capacity_rejects_insufficient_wisdom(self):
        slots = cleric_slot_table(3, 10)
        with self.assertRaisesRegex(SpellRuleError, "caractéristique"):
            validate_preparation_capacity(
                slot_rows=slots,
                existing_rows=[],
                spell_level=1,
                slot_kind="normal",
                prepared_count=1,
            )


if __name__ == "__main__":
    unittest.main()
