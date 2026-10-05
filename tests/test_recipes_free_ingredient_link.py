from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RecipesFreeIngredientLinkTests(unittest.TestCase):
    def test_data_layer_has_conversion_function(self):
        source = (
            ROOT / "grocery_planning.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "def link_recipe_free_ingredient_to_item(",
            source,
        )
        self.assertIn(
            "SET item_id = %s,",
            source,
        )
        self.assertIn(
            "free_name = NULL",
            source,
        )
        self.assertIn(
            "Cet item est déjà utilisé dans cette recette",
            source,
        )

    def test_db_reexports_conversion_function(self):
        source = (
            ROOT / "db.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "link_recipe_free_ingredient_to_item,",
            source,
        )

    def test_ui_has_link_checkbox(self):
        source = (
            ROOT / "recipes.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            '"Relier à un item de la liste d’épicerie"',
            source,
        )
        self.assertIn(
            "link_recipe_free_ingredient_to_item(",
            source,
        )
        self.assertIn(
            "has_grocery_access",
            source,
        )

    def test_reader_can_hide_grocery_actions(self):
        source = (
            ROOT / "recipes_reader.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "on_add_to_needs=None",
            source,
        )
        self.assertIn(
            "if on_add_to_needs is not None:",
            source,
        )


if __name__ == "__main__":
    unittest.main()
