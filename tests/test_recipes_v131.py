from __future__ import annotations

from pathlib import Path
import unittest

from recipes_chatgpt_import import parse_recipe_import
from recipes_extras import normalize_nutrition, nutrition_rows

ROOT = Path(__file__).resolve().parents[1]

class RecipesV131Tests(unittest.TestCase):
    def test_rich_chatgpt_nutrition_format_is_accepted(self):
        payload = {
            "format": "jf_apps_recipe_import",
            "version": 1,
            "recipe": {
                "name": "Brownies cheesecake chocolat-érable",
                "description": "Dessert",
                "servings": 16,
                "category": "Desserts",
                "ingredients": [{"name": "Cacao", "quantity": 1, "unit": "tasse", "order": 1}],
                "steps": [{"order": 1, "text": "Mélanger et cuire."}],
                "source": {"type": "chatgpt", "label": "Recette préparée avec ChatGPT"},
                "nutrition": {
                    "basis": "Estimation pour 16 portions, avec cacao et graines de chia, sans noix ni amandes facultatives.",
                    "serving_size": "1 carré (1/16 de la recette)",
                    "estimated": True,
                    "whole_recipe": {"calories_kcal": 4060, "protein_g": 72, "carbohydrates_g": 401, "sugars_g": 253, "fiber_g": 33, "fat_g": 255, "saturated_fat_g": 143, "sodium_mg": 1085},
                    "per_serving": {"calories_kcal": 255, "protein_g": 4.5, "carbohydrates_g": 25, "sugars_g": 16, "fiber_g": 2.0, "fat_g": 16, "saturated_fat_g": 9, "sodium_mg": 70},
                    "notes": ["Valeurs approximatives; elles peuvent varier.", "Les noix facultatives ne sont pas incluses."],
                },
            },
        }
        candidate = parse_recipe_import(payload)
        nutrition = candidate["extra"]["nutrition"]
        self.assertEqual(nutrition["basis"], "per_serving")
        self.assertEqual(nutrition["calories_kcal"], 255.0)
        self.assertEqual(nutrition["serving_size"], "1 carré (1/16 de la recette)")
        self.assertIn("Estimation pour 16 portions", nutrition["basis_note"])
        self.assertEqual(len(nutrition["notes"]), 2)
        self.assertEqual(candidate["extra"]["source"]["name"], "Recette préparée avec ChatGPT")
        rows = nutrition_rows(nutrition, 16)
        calories = next(row for row in rows if row["key"] == "calories_kcal")
        self.assertEqual(calories["per_serving_text"], "255 kcal")
        self.assertEqual(calories["whole_recipe_text"], "4060 kcal")

    def test_original_flat_format_remains_accepted(self):
        nutrition = normalize_nutrition({"basis":"per_serving","estimated":True,"calories_kcal":250,"protein_g":8})
        self.assertEqual(nutrition["basis"], "per_serving")
        self.assertEqual(nutrition["calories_kcal"], 250.0)

    def test_whole_recipe_only_format_is_accepted(self):
        nutrition = normalize_nutrition({"basis":"Estimation maison","estimated":True,"whole_recipe":{"calories_kcal":1000,"protein_g":40}})
        self.assertEqual(nutrition["basis"], "whole_recipe")
        self.assertEqual(nutrition["calories_kcal"], 1000.0)

    def test_version_is_1_3_1(self):
        source = (ROOT / "app_versions.py").read_text(encoding="utf-8")
        self.assertIn('"recipes": "1.4.0"', source)

if __name__ == "__main__":
    unittest.main()
