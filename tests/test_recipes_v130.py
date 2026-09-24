from __future__ import annotations

from pathlib import Path
import json
import unittest

from recipes_chatgpt_import import (
    IMPORT_FORMAT,
    IMPORT_VERSION,
    example_import_payload,
    parse_recipe_import,
    preview_recipe_import,
)
from recipes_extras import (
    normalize_nutrition,
    normalize_recipe_extra,
    nutrition_rows,
)


ROOT = Path(__file__).resolve().parents[1]


class RecipesV130Tests(unittest.TestCase):
    def test_chatgpt_import_format_v1_accepts_full_recipe(self):
        candidate = parse_recipe_import(example_import_payload())
        self.assertEqual(candidate["format"], IMPORT_FORMAT)
        self.assertEqual(candidate["version"], IMPORT_VERSION)
        self.assertEqual(candidate["name"], "Nom de la recette")
        self.assertEqual(candidate["servings"], 4)
        self.assertEqual(candidate["category"], "Desserts")
        self.assertEqual(candidate["extra"]["tags"], ["congélation", "dessert"])
        self.assertEqual(candidate["extra"]["prep_time_minutes"], 20)
        self.assertEqual(candidate["extra"]["cook_time_minutes"], 30)
        self.assertEqual(candidate["instructions"], "Préchauffer le four.")
        self.assertEqual(
            candidate["extra"]["nutrition"]["calories_kcal"],
            285.0,
        )

    def test_chatgpt_import_rejects_unknown_version(self):
        payload = example_import_payload()
        payload["version"] = 99
        with self.assertRaises(ValueError):
            parse_recipe_import(payload)

    def test_preview_detects_duplicate_and_missing_items(self):
        candidate = parse_recipe_import(example_import_payload())
        preview = preview_recipe_import(
            candidate,
            existing_items=[],
            existing_recipes=[{"name": "Nom de la recette"}],
        )
        self.assertTrue(preview["duplicate"])
        self.assertEqual(preview["matched_ingredients"], 0)
        self.assertEqual(preview["missing_ingredients"], ["Farine"])

    def test_nutrition_converts_per_serving_to_whole_recipe(self):
        nutrition = normalize_nutrition(
            {
                "basis": "per_serving",
                "estimated": True,
                "calories_kcal": 285,
                "protein_g": 8.5,
            }
        )
        rows = nutrition_rows(nutrition, 4)
        calories = next(
            row for row in rows
            if row["key"] == "calories_kcal"
        )
        protein = next(
            row for row in rows
            if row["key"] == "protein_g"
        )
        self.assertEqual(calories["per_serving_text"], "285 kcal")
        self.assertEqual(calories["whole_recipe_text"], "1140 kcal")
        self.assertEqual(protein["per_serving_text"], "8,5 g")
        self.assertEqual(protein["whole_recipe_text"], "34 g")

    def test_nutrition_converts_whole_recipe_to_per_serving(self):
        rows = nutrition_rows(
            {
                "basis": "whole_recipe",
                "estimated": False,
                "calories_kcal": 1200,
                "sodium_mg": 800,
            },
            4,
        )
        calories = next(
            row for row in rows
            if row["key"] == "calories_kcal"
        )
        sodium = next(
            row for row in rows
            if row["key"] == "sodium_mg"
        )
        self.assertEqual(calories["per_serving_text"], "300 kcal")
        self.assertEqual(sodium["per_serving_text"], "200 mg")

    def test_recipe_extra_preserves_tags_source_and_nutrition(self):
        extra = normalize_recipe_extra(
            {
                "prep_time_minutes": 10,
                "cook_time_minutes": 45,
                "tags": ["Rapide", "Congélation", "rapide"],
                "source": {
                    "name": "ChatGPT",
                    "url": "https://example.test/recipe",
                },
                "nutrition": {
                    "basis": "per_serving",
                    "estimated": True,
                    "calories_kcal": 250,
                },
            }
        )
        self.assertEqual(extra["tags"], ["Rapide", "Congélation"])
        self.assertEqual(extra["source"]["name"], "ChatGPT")
        self.assertEqual(
            extra["nutrition"]["calories_kcal"],
            250.0,
        )

    def test_schema_adds_recipe_extra_jsonb(self):
        source = (ROOT / "grocery_schema.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "ADD COLUMN IF NOT EXISTS recipe_extra JSONB",
            source,
        )
        self.assertIn(
            "NOT NULL DEFAULT '{}'::jsonb",
            source,
        )

    def test_recipes_ui_exposes_chatgpt_and_nutrition(self):
        source = (ROOT / "recipes.py").read_text(encoding="utf-8")
        self.assertIn('"Importer depuis ChatGPT"', source)
        self.assertIn('"Valeurs nutritives"', source)
        self.assertIn("save_recipe_metadata", source)
        self.assertIn("recipe_extra_search_text", source)

    def test_reader_displays_nutrition(self):
        source = (ROOT / "recipes_reader.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"Valeurs nutritives"', source)
        self.assertIn("nutrition_rows", source)
        self.assertIn("Nutrition estimée", source)

    def test_backup_preserves_recipe_extra(self):
        source = (ROOT / "grocery_backup.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"recipe_extra"', source)
        self.assertIn("recipe.recipe_extra", source)
        self.assertIn("json.dumps(", source)

    def test_version_is_1_3_1(self):
        source = (ROOT / "app_versions.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"recipes": "1.4.2"', source)


if __name__ == "__main__":
    unittest.main()
