from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FaithIomedaeIntegrationTests(unittest.TestCase):
    def test_faith_panel_receives_deity_catalog_by_injection(self):
        source = (
            ROOT / "rpg_character.py"
        ).read_text(encoding="utf-8")
        text = ast.unparse(ast.parse(source))
        self.assertIn(
            "deity_profiles=DEITY_PROFILES",
            text,
        )

    def test_faith_module_keeps_iomedae_choice_non_automatic(self):
        source = (
            ROOT / "rpg_character_faith.py"
        ).read_text(encoding="utf-8")
        self.assertIn("Préconfigurer Iomedae", source)
        self.assertIn("personal_domain_preset", source)
        self.assertIn("Guerre / War", source)
        self.assertIn("Soleil / Sun", source)
        self.assertNotIn(
            'domain_1_input.value = "Glory"',
            source,
        )


if __name__ == "__main__":
    unittest.main()
