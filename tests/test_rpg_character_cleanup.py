from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class JdrCleanupTests(unittest.TestCase):
    def test_ui_shell_contains_no_legacy_panel_bodies(self):
        path = ROOT / "rpg_character_ui.py"
        parsed = ast.parse(path.read_text(encoding="utf-8"))
        top_functions = {
            node.name
            for node in parsed.body
            if isinstance(node, ast.FunctionDef)
        }
        self.assertEqual(
            top_functions,
            {
                "_safe_notify_error",
                "_character_url",
                "_create_character_dialog",
                "_delete_character_dialog",
                "rpg_character_panel",
            },
        )
        for dead_name in (
            "_identity_panel",
            "_progression_panel",
            "_combat_panel",
            "_equipment_panel",
            "_saves_panel",
            "_skills_panel",
            "_attack_dialog",
            "_attacks_panel",
            "_calculation_rules_dialog",
            "_equipment_dialog",
            "_skill_dialog",
        ):
            self.assertNotIn(dead_name, top_functions)

    def test_facade_has_all_runtime_panel_bindings(self):
        source = (ROOT / "rpg_character.py").read_text(encoding="utf-8")
        parsed = ast.parse(source)
        text = ast.unparse(parsed)

        for binding in (
            "_impl.get_rpg_character = _get_rpg_character",
            "_impl._identity_panel = _identity_panel",
            "_impl._progression_panel = _progression_panel",
            "_impl._combat_panel = _combat_panel",
            "_impl._equipment_panel = _equipment_panel",
            "_impl._saves_panel = _saves_panel",
            "_impl._skills_panel = _skills_panel",
            "_impl._attacks_panel = _attacks_panel",
        ):
            self.assertIn(binding, text)

        self.assertNotIn("traceback", source)
        self.assertNotIn("ERREUR TECHNIQUE NON GÉRÉE", source)

    def test_new_helper_modules_are_framework_and_db_independent(self):
        for name in (
            "rpg_character_styles.py",
            "rpg_character_equipment_dialogs.py",
            "rpg_character_skill_dialogs.py",
            "rpg_character_rules_dialog.py",
        ):
            parsed = ast.parse(
                (ROOT / name).read_text(encoding="utf-8")
            )
            imports = set()
            for node in ast.walk(parsed):
                if isinstance(node, ast.Import):
                    imports.update(a.name for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module)

            self.assertTrue(
                {
                    "nicegui",
                    "db",
                    "rpg_character",
                    "rpg_character_ui",
                }.isdisjoint(imports),
                name,
            )

    def test_ui_shell_is_substantially_smaller_than_legacy_baseline(self):
        size = (ROOT / "rpg_character_ui.py").stat().st_size
        self.assertLess(size, 35_000)

    def test_styles_preserve_core_classes(self):
        source = (
            ROOT / "rpg_character_styles.py"
        ).read_text(encoding="utf-8")
        for css_class in (
            ".jf-rpg-main-tabs",
            ".jf-rpg-ability-grid",
            ".jf-rpg-combat-grid",
            ".jf-rpg-equipment-card",
            ".jf-rpg-skill-card",
            ".jf-rpg-section-actions",
        ):
            self.assertIn(css_class, source)


if __name__ == "__main__":
    unittest.main()
