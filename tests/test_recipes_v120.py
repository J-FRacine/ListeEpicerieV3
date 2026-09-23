from __future__ import annotations

from pathlib import Path
import unittest

from recipes_categories import category_matches_filter, category_path
from recipes_site_import import (
    is_navigation_page,
    parse_recipe_html,
    source_recipe_category,
)


ROOT = Path(__file__).resolve().parents[1]


NAVIGATION_HTML = """
<html>
<head><title>Les bases - Recettes de l'Ours</title></head>
<body>
<h1>Les bases</h1>
<div>Cuisson courge spaghetti</div>
<div>Bases de grand-maman</div>
<div>Pain</div>
<div>Pâtes</div>
<ul>
<li>Bases de grand-maman</li>
<li>Pain</li>
<li>Pâtes</li>
</ul>
<a href="/view/recettes-de-lours/les-bases/cuisson-courge-spaghetti">
Cuisson courge spaghetti
</a>
<a href="/view/recettes-de-lours/les-bases/bases-de-grand-maman">
Bases de grand-maman
</a>
<a href="/view/recettes-de-lours/les-bases/pain">Pain</a>
<a href="/view/recettes-de-lours/les-bases/pates">Pâtes</a>
</body>
</html>
"""


REAL_RECIPE_HTML = """
<html>
<head><title>Burrata et tomates sur plaque - Recettes de l'Ours</title></head>
<body>
<h1>Burrata et tomates sur plaque</h1>
<div>Huile olive 60% 1/3 tasse</div>
<div>Vinaigre balsamique 40% 1/4 t</div>
<div>Tomates</div>
<div>Prosciutto</div>
<div>Parmesan</div>
<div>2 c a soupe de sucre</div>
<div>Ail au goût</div>
<div>Sel et poivre</div>
<ul>
<li>Couper les tomates en tranches</li>
<li>Mélanger les tomates et les épices</li>
<li>Mettre au four 425F pendant 25 minutes</li>
</ul>
</body>
</html>
"""


class RecipesV120Tests(unittest.TestCase):
    def test_navigation_page_is_never_a_recipe(self):
        url = "https://sites.google.com/view/recettes-de-lours/les-bases"
        self.assertTrue(is_navigation_page(NAVIGATION_HTML, url))
        self.assertIsNone(parse_recipe_html(NAVIGATION_HTML, url))

    def test_real_headingless_recipe_remains_supported(self):
        url = (
            "https://sites.google.com/view/recettes-de-lours/"
            "entrées/tomates-burrata"
        )
        recipe = parse_recipe_html(REAL_RECIPE_HTML, url)
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["name"], "Burrata et tomates sur plaque")
        self.assertEqual(recipe["source_category"], "Entrées")
        self.assertEqual(recipe["source_subcategory"], "")

    def test_nested_site_path_becomes_recipe_category_and_subcategory(self):
        category, subcategory = source_recipe_category(
            "https://sites.google.com/view/recettes-de-lours/"
            "les-bases/pain/pain-blanc"
        )
        self.assertEqual(category, "Les bases")
        self.assertEqual(subcategory, "Pain")

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

    def test_schema_contains_recipe_categories_and_safe_foreign_key(self):
        source = (ROOT / "grocery_schema.py").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS grocery_recipe_categories", source)
        self.assertIn("ADD COLUMN IF NOT EXISTS recipe_category_id", source)
        self.assertIn("grocery_recipes_recipe_category_id_fkey", source)
        self.assertIn("ON DELETE SET NULL", source)

    def test_recipes_ui_exposes_categories_and_bulk_delete(self):
        source = (ROOT / "recipes.py").read_text(encoding="utf-8")
        self.assertIn('"Catégories"', source)
        self.assertIn('"Supprimer plusieurs"', source)
        self.assertIn("set_recipe_category", source)
        self.assertIn("category_matches_filter", source)

    def test_backup_preserves_recipe_categories(self):
        source = (ROOT / "grocery_backup.py").read_text(encoding="utf-8")
        self.assertIn('"recipe_categories"', source)
        self.assertIn('"recipe_category"', source)
        self.assertIn('"recipe_category_parent"', source)

    def test_version_is_1_2_0(self):
        source = (ROOT / "app_versions.py").read_text(encoding="utf-8")
        self.assertIn('"recipes": "1.2.0"', source)


if __name__ == "__main__":
    unittest.main()
