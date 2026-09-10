from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

from rpg_combat_session import (
    CombatSessionHandle,
    adjusted_current_hp,
    adjusted_nonlethal,
    combat_summary,
    find_attack,
    hp_update_payload,
)

ROOT = Path(__file__).resolve().parents[1]


class CombatSessionPureTests(unittest.TestCase):
    def character(self):
        return {
            "id": 7,
            "current_hp": 23,
            "max_hp": 31,
            "nonlethal_damage": 2,
            "str_score": 14,
            "dex_score": 12,
            "con_score": 14,
            "int_score": 10,
            "wis_score": 10,
            "cha_score": 8,
            "str_temp_score": None,
            "dex_temp_score": None,
            "con_temp_score": None,
            "int_temp_score": None,
            "wis_temp_score": None,
            "cha_temp_score": None,
            "speed": None,
            "damage_reduction": None,
            "spell_resistance": None,
            "base_attack_bonus": 3,
            "armor_bonus": 4,
            "shield_bonus": 0,
            "natural_armor_bonus": 0,
            "deflection_bonus": 0,
            "misc_ac_modifier": 0,
            "armor_check_penalty": 0,
            "initiative_misc_modifier": 0,
            "grapple_misc_modifier": 0,
            "cmb_misc_modifier": 0,
            "cmd_misc_modifier": 0,
        }

    def test_damage_and_healing_keep_negative_hp_possible(self):
        self.assertEqual(adjusted_current_hp(5, damage=9), -4)
        self.assertEqual(adjusted_current_hp(-4, healing=7), 3)
        self.assertEqual(adjusted_current_hp(10, damage=-3, healing=-2), 10)

    def test_nonlethal_never_goes_below_zero(self):
        self.assertEqual(adjusted_nonlethal(4, added=3, removed=2), 5)
        self.assertEqual(adjusted_nonlethal(2, removed=20), 0)

    def test_find_attack_accepts_numeric_string_and_missing(self):
        attacks = [{"id": 3, "attack_name": "Épée"}, {"id": 8}]
        self.assertEqual(find_attack(attacks, "3")["attack_name"], "Épée")
        self.assertIsNone(find_attack(attacks, 99))
        self.assertIsNone(find_attack(attacks, "x"))

    def test_combat_summary_uses_existing_rule_callbacks(self):
        snapshot = combat_summary(
            character=self.character(),
            attacks=[{"id": 3, "attack_name": "Épée", "damage": "1d8+2"}],
            saves=[
                {"save_key": "fortitude", "base_save": 3},
                {"save_key": "reflex", "base_save": 1},
            ],
            selected_attack_id=3,
            temporary_attack_bonus=2,
            armor_class_total=lambda c: 17,
            touch_armor_class=lambda c: 11,
            flat_footed_armor_class=lambda c: 16,
            initiative_total=lambda c: 1,
            cmb_total=lambda c: 5,
            cmd_total=lambda c: 16,
            attack_total=lambda c, a: 6,
            save_total=lambda c, s: s["base_save"] + 2,
        )
        self.assertEqual(snapshot["selected_attack_total"], 8)
        self.assertEqual(snapshot["armor_class"], 17)
        self.assertEqual(snapshot["save_totals"]["fortitude"], 5)
        self.assertEqual(snapshot["save_totals"]["reflex"], 3)

    def test_combat_summary_without_attack_has_no_total(self):
        snapshot = combat_summary(
            character=self.character(),
            attacks=[],
            saves=[],
            selected_attack_id=None,
            temporary_attack_bonus=5,
            armor_class_total=lambda c: 10,
            touch_armor_class=lambda c: 10,
            flat_footed_armor_class=lambda c: 10,
            initiative_total=lambda c: 0,
            cmb_total=lambda c: 0,
            cmd_total=lambda c: 10,
            attack_total=lambda c, a: 99,
            save_total=lambda c, s: 99,
        )
        self.assertIsNone(snapshot["selected_attack"])
        self.assertIsNone(snapshot["selected_attack_total"])

    def test_hp_update_payload_preserves_existing_combat_values(self):
        payload = hp_update_payload(
            self.character(),
            current_hp=12,
            nonlethal_damage=7,
        )
        self.assertEqual(payload["current_hp"], 12)
        self.assertEqual(payload["nonlethal_damage"], 7)
        self.assertEqual(payload["base_attack_bonus"], 3)
        self.assertEqual(payload["armor_bonus"], 4)
        self.assertEqual(payload["str_score"], 14)

    def test_handle_is_lazy(self):
        callback = Mock()
        handle = CombatSessionHandle(callback)
        callback.assert_not_called()
        handle.open()
        callback.assert_called_once_with()


class CombatSessionArchitectureTests(unittest.TestCase):
    def test_import_does_not_require_nicegui_or_database_modules(self):
        script = r"""
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'nicegui', 'db', 'psycopg', 'psycopg2'}:
        raise AssertionError(name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import rpg_combat_session
assert callable(rpg_combat_session.build_combat_session)
"""
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
