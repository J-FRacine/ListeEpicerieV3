from __future__ import annotations

from pathlib import Path
import unittest

from recipes_reader import ingredient_label, instruction_steps, recipe_matches


ROOT = Path(__file__).resolve().parents[1]


class RecipesV1Tests(unittest.TestCase):
    def test_instruction_steps_preserve_line_order(self):
        self.assertEqual(
            instruction_steps("Préparer les légumes.\n\nCuire 20 minutes.\nServir."),
            ["Préparer les légumes.", "Cuire 20 minutes.", "Servir."],
        )

    def test_recipe_search_includes_ingredient_name_and_note(self):
        recipe = {
            "name": "Soupe maison",
            "description": "Repas rapide",
            "instructions": "Mijoter.",
        }
        ingredients = [
            {"name": "Tomates", "category": "Légumes", "note": "en dés"}
        ]
        self.assertTrue(recipe_matches(recipe, ingredients, "tomates"))
        self.assertTrue(recipe_matches(recipe, ingredients, "EN DÉS"))
        self.assertFalse(recipe_matches(recipe, ingredients, "poulet"))

    def test_ingredient_label_keeps_existing_quantity_semantics(self):
        self.assertEqual(ingredient_label({"name": "Lait", "quantity": 1}), "Lait")
        self.assertEqual(ingredient_label({"name": "Oeufs", "quantity": 3}), "Oeufs (3)")

    def test_recipes_is_declared_as_standalone_portal_app(self):
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        versions = (ROOT / "app_versions.py").read_text(encoding="utf-8")
        self.assertIn('"recipes": {', app_source)
        self.assertIn('app_key="recipes"', app_source)
        self.assertIn('title="Recettes"', app_source)
        self.assertIn('badge=version_label("recipes")', app_source)
        self.assertIn('"recipes": "1.4.0"', versions)

    def test_recipes_keeps_grocery_access_and_existing_data_model(self):
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        recipe_route = app_source.index("if normalized_tab in RECIPE_TABS:")
        grocery_check = app_source.index('"grocery",', recipe_route)
        recipe_panel = app_source.index("recipes_panel()", recipe_route)
        self.assertLess(grocery_check, recipe_panel)
        reader_source = (ROOT / "recipes_reader.py").read_text(encoding="utf-8")
        self.assertIn("wakeLock", reader_source)
        self.assertIn("Ajouter à la liste d’épicerie", reader_source)


if __name__ == "__main__":
    unittest.main()
