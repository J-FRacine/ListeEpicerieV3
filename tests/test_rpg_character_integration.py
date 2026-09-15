"""Raccordements structuraux JDR — V1.8.0."""
from __future__ import annotations

import ast
import inspect
from pathlib import Path
import unittest

import app_versions
from rpg_combat_session import build_combat_session

ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "rpg_character_ui.py"
FACADE_PATH = ROOT / "rpg_character.py"


class CharacterIntegrationTests(unittest.TestCase):
    def test_public_facade_wires_all_specialized_panels(self):
        source = FACADE_PATH.read_text(encoding="utf-8")
        text = ast.unparse(ast.parse(source))

        for binding in (
            "_impl._portrait_block = _portrait_block",
            "_impl._identity_panel = _identity_panel",
            "_impl._faith_panel = _faith_panel",
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

    def test_tabs_include_faith_and_dons_without_removing_sections(self):
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
                "Foi",
                "Progression",
                "Dons",
                "Combat",
                "Équipement",
                "Sauvegardes",
                "Compétences",
                "Attaques",
            ],
        )

    def test_faith_routes_are_available(self):
        source = UI_PATH.read_text(encoding="utf-8")
        parsed = ast.parse(source)
        text = ast.unparse(parsed)

        for route in (
            "'foi': faith_tab",
            "'faith': faith_tab",
            "'domaines': faith_tab",
            "'domains': faith_tab",
        ):
            self.assertIn(route, text)

        self.assertIn(
            "_faith_panel(user_id, character)",
            text,
        )

    def test_combat_builder_call_still_matches_signature(self):
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
        self.assertIn(
            "collect_feat_combat_effects",
            values,
        )

    def test_ui_shell_remains_compact(self):
        self.assertLess(UI_PATH.stat().st_size, 32_000)


    def test_declared_versions(self):
        self.assertEqual(
            app_versions.APP_VERSIONS["rpg"],
            "1.8.0",
        )
        self.assertEqual(
            app_versions.APP_VERSIONS["finances"],
            "1.13.6",
        )
        note = next(
            row
            for row in app_versions.RELEASE_NOTES
            if row["app_key"] == "rpg"
        )
        self.assertEqual(note["version"], "1.8.0")


if __name__ == "__main__":
    unittest.main()
