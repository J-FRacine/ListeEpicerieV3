from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FaithArchitectureTests(unittest.TestCase):
    def test_schema_is_automatic_and_non_destructive(self):
        source = (
            ROOT / "rpg_character_faith_data.py"
        ).read_text(encoding="utf-8")
        upper = source.upper()

        for column in (
            "DOMAIN_1 TEXT",
            "SUBDOMAIN_1 TEXT",
            "DOMAIN_2 TEXT",
            "SUBDOMAIN_2 TEXT",
            "FAITH_NOTES TEXT",
        ):
            self.assertIn(column, upper)

        self.assertIn(
            "ALTER TABLE RPG_CHARACTERS",
            upper,
        )
        self.assertIn(
            "ADD COLUMN IF NOT EXISTS",
            upper,
        )
        self.assertNotIn("DROP TABLE", upper)
        self.assertNotIn("TRUNCATE", upper)

    def test_deity_remains_same_historical_column(self):
        source = (
            ROOT / "rpg_character_faith_data.py"
        ).read_text(encoding="utf-8")
        self.assertIn("deity = %s", source)
        self.assertNotIn("faith_deity", source)

    def test_faith_ui_has_no_framework_or_db_back_reference(self):
        parsed = ast.parse(
            (ROOT / "rpg_character_faith.py").read_text(
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

    def test_facade_wires_faith_panel(self):
        source = (
            ROOT / "rpg_character.py"
        ).read_text(encoding="utf-8")
        text = ast.unparse(ast.parse(source))

        self.assertIn(
            "_impl._faith_panel = _faith_panel",
            text,
        )
        self.assertIn(
            "build_faith_panel",
            source,
        )


if __name__ == "__main__":
    unittest.main()
