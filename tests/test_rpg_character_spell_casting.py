from __future__ import annotations

import unittest

from rpg_character_spell_casting import (
    SpellCastError,
    available_prepared_spells,
    build_cast_reference,
    remaining_prepared_uses,
    spontaneous_cast_options,
)


class SpellCastingRulesTests(unittest.TestCase):
    def character(self):
        return {
            "wis_score": 18,
            "wis_temp_score": None,
        }

    def profile(self, mode="cure"):
        return {
            "caster_level": 4,
            "ability_key": "wis",
            "spontaneous_mode": mode,
        }

    def prepared(self, **overrides):
        row = {
            "id": 7,
            "catalog_key": "aid",
            "spell_name": "Aid",
            "spell_level": 2,
            "slot_kind": "normal",
            "prepared_count": 2,
            "used_count": 1,
            "summary": "Bonus et PV temporaires.",
            "range_text": "Touch",
            "notes": "",
        }
        row.update(overrides)
        return row

    def test_remaining_uses_and_orisons(self):
        self.assertEqual(remaining_prepared_uses(self.prepared()), 1)
        self.assertEqual(
            remaining_prepared_uses(
                self.prepared(spell_level=0, prepared_count=1, used_count=99)
            ),
            1,
        )

    def test_available_list_hides_exhausted_but_keeps_orisons(self):
        rows = [
            self.prepared(id=1, prepared_count=1, used_count=1),
            self.prepared(id=2, prepared_count=2, used_count=1),
            self.prepared(id=3, spell_level=0, prepared_count=1, used_count=0),
        ]
        self.assertEqual(
            [row["id"] for row in available_prepared_spells(rows)],
            [2, 3],
        )

    def test_spontaneous_cure_uses_normal_non_orison_slots_only(self):
        options = spontaneous_cast_options(self.profile("cure"), self.prepared())
        self.assertEqual(
            [row["name"] for row in options],
            ["Cure Light Wounds", "Cure Moderate Wounds"],
        )
        self.assertEqual(
            spontaneous_cast_options(
                self.profile("cure"), self.prepared(slot_kind="domain")
            ),
            [],
        )
        self.assertEqual(
            spontaneous_cast_options(
                self.profile("cure"), self.prepared(spell_level=0)
            ),
            [],
        )
        self.assertEqual(
            spontaneous_cast_options(self.profile("none"), self.prepared()),
            [],
        )

    def test_prepared_cast_reference_uses_caster_level_and_spell_dc(self):
        reference = build_cast_reference(
            character=self.character(),
            profile=self.profile(),
            prepared_row=self.prepared(),
            catalog_entry={
                "duration_text": "1 min./niveau",
                "target_text": "Créature touchée",
            },
        )
        self.assertEqual(reference["name"], "Aid")
        self.assertEqual(reference["caster_level"], 4)
        self.assertEqual(reference["save_dc"], 16)  # 10 + niv. 2 + SAG +4
        self.assertEqual(reference["remaining_before"], 1)
        self.assertEqual(reference["remaining_after"], 0)
        self.assertFalse(reference["is_spontaneous"])

    def test_spontaneous_reference_uses_converted_spell_level_for_dc(self):
        reference = build_cast_reference(
            character=self.character(),
            profile=self.profile("cure"),
            prepared_row=self.prepared(spell_level=3, spell_name="Prayer"),
            spontaneous_key="cure_light_wounds",
        )
        self.assertTrue(reference["is_spontaneous"])
        self.assertEqual(reference["name"], "Cure Light Wounds")
        self.assertEqual(reference["source_spell_name"], "Prayer")
        self.assertEqual(reference["source_spell_level"], 3)
        self.assertEqual(reference["spell_level"], 1)
        self.assertEqual(reference["save_dc"], 15)  # 10 + niv. 1 + SAG +4
        self.assertIn("1d8", reference["roll_text"])

    def test_invalid_conversion_and_exhausted_spell_are_rejected(self):
        with self.assertRaises(SpellCastError):
            build_cast_reference(
                character=self.character(),
                profile=self.profile("cure"),
                prepared_row=self.prepared(slot_kind="domain"),
                spontaneous_key="cure_light_wounds",
            )
        with self.assertRaisesRegex(SpellCastError, "déjà utilisés"):
            build_cast_reference(
                character=self.character(),
                profile=self.profile(),
                prepared_row=self.prepared(prepared_count=1, used_count=1),
            )


if __name__ == "__main__":
    unittest.main()
