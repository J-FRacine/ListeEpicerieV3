from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SpellCastingArchitectureTests(unittest.TestCase):
    def test_atomic_cast_action_locks_and_updates_preparation(self):
        source = (ROOT / "rpg_character_spell_data.py").read_text(encoding="utf-8")
        parsed = ast.parse(source)
        function = next(
            node
            for node in parsed.body
            if isinstance(node, ast.FunctionDef) and node.name == "cast_prepared_spell"
        )
        text = ast.unparse(function)
        self.assertIn("FOR UPDATE", text)
        self.assertIn("used_count", text)
        self.assertIn("Tous les exemplaires préparés", text)
        self.assertIn("reusable", text)

    def test_spells_panel_has_guided_launch_without_removing_manual_adjustment(self):
        source = (ROOT / "rpg_character_spells.py").read_text(encoding="utf-8")
        self.assertIn("open_spell_cast_dialog", source)
        self.assertIn('"Lancer"', source)
        self.assertIn("Marquer 1 emplacement utilisé", source)
        self.assertIn("Rendre 1 utilisation", source)
        self.assertIn("conversion spontanée", source.casefold())

    def test_combat_quick_uses_same_prepared_spell_action(self):
        source = (ROOT / "rpg_combat_session.py").read_text(encoding="utf-8")
        for expected in (
            "Sorts préparés",
            "Lancer le sort",
            "open_spell_cast_dialog",
            "cast_prepared_spell",
            "list_prepared_spells",
            "get_spellcasting_profile",
        ):
            self.assertIn(expected, source)

    def test_casting_modules_stay_separate_from_main_ui_shell(self):
        self.assertTrue((ROOT / "rpg_character_spell_casting.py").exists())
        self.assertTrue((ROOT / "rpg_character_spell_cast_dialog.py").exists())
        self.assertLess((ROOT / "rpg_character_ui.py").stat().st_size, 34_000)


if __name__ == "__main__":
    unittest.main()
