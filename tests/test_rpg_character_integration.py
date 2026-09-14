"""Raccordements structuraux JDR — Phase 10."""
from __future__ import annotations

import ast
import inspect
from pathlib import Path
import unittest

from rpg_combat_session import build_combat_session

ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "rpg_character_ui.py"
FACADE_PATH = ROOT / "rpg_character.py"


class CharacterIntegrationTests(unittest.TestCase):
    def test_public_facade_wires_all_specialized_panels(self):
        source = FACADE_PATH.read_text(encoding="utf-8")
        text = ast.unparse(ast.parse(source))

        for binding in (
            "_impl._identity_panel = _identity_panel",
            "_impl._progression_panel = _progression_panel",
            "_impl._feats_panel = _feats_panel",
            "_impl._combat_panel = _combat_panel",
            "_impl._equipment_panel = _equipment_panel",
            "_impl._saves_panel = _saves_panel",
            "_impl._skills_panel = _skills_panel",
            "_impl._attacks_panel = _attacks_panel",
        ):
            self.assertIn(binding, text)

        self.assertIn(
            "rpg_character_panel = _impl.rpg_character_panel",
            text,
        )

    def test_tabs_include_dons_without_removing_existing_sections(self):
        parsed = ast.parse(UI_PATH.read_text(encoding="utf-8"))
        panel = next(
            node
            for node in parsed.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "rpg_character_panel"
        )
        tabs = [
            node.args[0].value
            for node in ast.walk(panel)
            if isinstance(node, ast.Call)
            and ast.unparse(node.func) == "ui.tab"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ]
        self.assertEqual(
            tabs,
            [
                "Création guidée",
                "Identité",
                "Progression",
                "Dons",
                "Combat",
                "Équipement",
                "Sauvegardes",
                "Compétences",
                "Attaques",
            ],
        )

    def test_combat_builder_call_matches_signature(self):
        parsed = ast.parse(UI_PATH.read_text(encoding="utf-8"))
        call = next(
            node
            for node in ast.walk(parsed)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "build_combat_session"
        )
        values = {
            keyword.arg: object()
            for keyword in call.keywords
        }
        inspect.signature(build_combat_session).bind(**values)
        self.assertIn("list_rpg_feats", values)
        self.assertIn("collect_feat_combat_effects", values)

    def test_ui_shell_remains_compact(self):
        self.assertLess(UI_PATH.stat().st_size, 30_000)


if __name__ == "__main__":
    unittest.main()
