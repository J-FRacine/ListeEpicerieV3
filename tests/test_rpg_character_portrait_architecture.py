from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PortraitArchitectureTests(unittest.TestCase):
    def test_portrait_ui_keeps_dependencies_injected(self):
        parsed = ast.parse(
            (ROOT / "rpg_character_portrait.py").read_text(
                encoding="utf-8"
            )
        )
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

    def test_portrait_schema_is_automatic_private_and_cascading(self):
        source = (
            ROOT / "rpg_character_portrait_data.py"
        ).read_text(encoding="utf-8")
        upper = source.upper()

        self.assertIn(
            "CREATE TABLE IF NOT EXISTS RPG_CHARACTER_PORTRAITS",
            upper,
        )
        self.assertIn("IMAGE_DATA BYTEA NOT NULL", upper)
        self.assertIn("ON DELETE CASCADE", upper)
        self.assertIn("ON CONFLICT (CHARACTER_ID)", upper)
        self.assertIn("USER_ID = %S", upper)
        self.assertNotIn("DROP TABLE", upper)
        self.assertNotIn("TRUNCATE", upper)

    def test_facade_wires_portrait_block(self):
        source = (
            ROOT / "rpg_character.py"
        ).read_text(encoding="utf-8")
        text = ast.unparse(ast.parse(source))
        self.assertIn(
            "_impl._portrait_block = _portrait_block",
            text,
        )
        self.assertIn("build_portrait_block", source)
        self.assertIn("get_rpg_portrait", source)
        self.assertIn("save_rpg_portrait", source)

    def test_shell_renders_portrait_without_new_tab(self):
        source = (
            ROOT / "rpg_character_ui.py"
        ).read_text(encoding="utf-8")
        text = ast.unparse(ast.parse(source))
        self.assertIn(
            "_portrait_block(user_id, character)",
            text,
        )
        self.assertNotIn("ui.tab('Portrait'", text)

    def test_requirements_adds_pillow_without_removing_stack(self):
        requirements = (
            ROOT / "requirements.txt"
        ).read_text(encoding="utf-8").splitlines()
        for dependency in (
            "nicegui",
            "psycopg[binary]",
            "reportlab",
            "pywebpush",
            "cryptography",
            "httpx",
            "Pillow",
        ):
            self.assertIn(dependency, requirements)


if __name__ == "__main__":
    unittest.main()
