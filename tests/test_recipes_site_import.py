from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RecipesLegacySiteImportRemovalTests(unittest.TestCase):
    def test_old_site_import_has_no_runtime_code(self):
        parser_source = (ROOT / "recipes_site_import.py").read_text(
            encoding="utf-8"
        )
        ui_source = (ROOT / "recipes_site_import_ui.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("urllib.request", parser_source)
        self.assertNotIn("urlopen(", parser_source)
        self.assertNotIn("crawl_google_site", parser_source)
        self.assertNotIn("nicegui", ui_source)


if __name__ == "__main__":
    unittest.main()
