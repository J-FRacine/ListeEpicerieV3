from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FeatArchitectureTests(unittest.TestCase):
    def test_shell_has_dons_tab_and_combat_receives_feats(self):
        source = (
            ROOT / "rpg_character_ui.py"
        ).read_text(encoding="utf-8")
        parsed = ast.parse(source)
        text = ast.unparse(parsed)

        self.assertIn("ui.tab('Dons', icon='military_tech')", text)
        self.assertIn("'dons': feats_tab", text)
        self.assertIn("_feats_panel(user_id, character)", text)
        self.assertIn("list_rpg_feats=list_rpg_feats", text)
        self.assertIn(
            "collect_feat_combat_effects=collect_feat_combat_effects",
            text,
        )

    def test_facade_wires_feat_panel(self):
        source = (
            ROOT / "rpg_character.py"
        ).read_text(encoding="utf-8")
        parsed = ast.parse(source)
        text = ast.unparse(parsed)

        self.assertIn(
            "_impl._feats_panel = _feats_panel",
            text,
        )
        self.assertIn(
            "build_feats_panel",
            source,
        )

    def test_feat_schema_is_automatic_and_cascades_with_character(self):
        source = (
            ROOT / "rpg_character_feats_data.py"
        ).read_text(encoding="utf-8")
        upper = source.upper()
        self.assertIn(
            "CREATE TABLE IF NOT EXISTS RPG_CHARACTER_FEATS",
            upper,
        )
        self.assertIn("ON DELETE CASCADE", upper)
        self.assertIn("ON DELETE SET NULL", upper)
        self.assertNotIn("DROP TABLE", upper)
        self.assertNotIn("TRUNCATE", upper)

    def test_ui_module_keeps_dependencies_injected(self):
        path = ROOT / "rpg_character_feats.py"
        parsed = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

        self.assertTrue(
            {
                "nicegui",
                "db",
                "rpg_character",
                "rpg_character_ui",
            }.isdisjoint(imports)
        )


if __name__ == "__main__":
    unittest.main()
