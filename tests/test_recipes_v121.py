from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RecipesV121HistoricalTests(unittest.TestCase):
    def test_legacy_google_sites_import_is_removed(self):
        source = (ROOT / "recipes.py").read_text(encoding="utf-8")
        self.assertNotIn('"Importer mon ancien site"', source)
        self.assertNotIn(
            "from recipes_site_import_ui import",
            source,
        )

    def test_legacy_modules_are_only_tombstones(self):
        parser = (ROOT / "recipes_site_import.py").read_text(
            encoding="utf-8"
        )
        ui_source = (ROOT / "recipes_site_import_ui.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("retiré", parser)
        self.assertIn("retirée", ui_source)
        self.assertNotIn("crawl_google_site", parser)
        self.assertNotIn("open_recipe_site_import_dialog", ui_source)


if __name__ == "__main__":
    unittest.main()
