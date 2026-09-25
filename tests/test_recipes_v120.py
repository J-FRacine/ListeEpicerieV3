from __future__ import annotations

from pathlib import Path
import unittest

from recipes_categories import category_matches_filter, category_path


ROOT = Path(__file__).resolve().parents[1]


class RecipesV120HistoricalTests(unittest.TestCase):
    def test_category_filter_includes_direct_children(self):
        rows = [
            {"id": 10, "name": "Les bases", "parent_id": None},
            {
                "id": 11,
                "name": "Pain",
                "parent_id": 10,
                "parent_name": "Les bases",
            },
        ]
        self.assertTrue(category_matches_filter(10, 10, rows))
        self.assertTrue(category_matches_filter(11, 10, rows))
        self.assertFalse(category_matches_filter(None, 10, rows))
        self.assertTrue(category_matches_filter(None, 0, rows))
        self.assertEqual(category_path(rows[1]), "Les bases › Pain")

    def test_schema_keeps_recipe_categories(self):
        source = (ROOT / "grocery_schema.py").read_text(encoding="utf-8")
        self.assertIn(
            "CREATE TABLE IF NOT EXISTS grocery_recipe_categories",
            source,
        )
        self.assertIn("ADD COLUMN IF NOT EXISTS recipe_category_id", source)

    def test_recipes_ui_keeps_categories_and_bulk_delete(self):
        source = (ROOT / "recipes.py").read_text(encoding="utf-8")
        self.assertIn('"Catégories"', source)
        self.assertIn('"Supprimer plusieurs"', source)
        self.assertIn("set_recipe_category", source)

    def test_version_is_1_4_0(self):
        source = (ROOT / "app_versions.py").read_text(encoding="utf-8")
        self.assertIn('"recipes": "1.5.0"', source)


if __name__ == "__main__":
    unittest.main()
