from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recipes_extras import normalize_recipe_extra
from recipes_food_catalog import match_food
from recipes_ingredient_analysis import (
    analyze_ingredient,
    build_nutrition_estimate,
    grams_from_measurement,
    parse_measurement,
    parse_number,
    serialize_metrics,
)
from recipes_pdf import build_recipe_pdf


ROOT = Path(__file__).resolve().parents[1]


class RecipesV180Tests(unittest.TestCase):
    def test_fraction_parser(self):
        self.assertAlmostEqual(parse_number("1/2"), 0.5)
        self.assertAlmostEqual(parse_number("1 1/2"), 1.5)
        self.assertAlmostEqual(parse_number("2/3"), 2 / 3)
        self.assertAlmostEqual(parse_number("½"), 0.5)

    def test_flour_cup_converts_by_density(self):
        measurement = parse_measurement("1 1/2 tasse")
        grams, source = grams_from_measurement(
            measurement,
            "flour_all_purpose",
        )
        self.assertGreater(grams, 175)
        self.assertLess(grams, 185)
        self.assertIn("ingrédient", source)

    def test_explicit_grams_override_volume(self):
        measurement = parse_measurement("1 tasse (120 g)")
        grams, source = grams_from_measurement(
            measurement,
            "flour_all_purpose",
        )
        self.assertEqual(grams, 120.0)
        self.assertEqual(source, "Poids indiqué")

    def test_count_uses_average_piece_weight(self):
        row = analyze_ingredient(
            {
                "id": 10,
                "name": "Œufs",
                "quantity": 1,
                "note": "2",
                "is_free": True,
            }
        )
        self.assertEqual(row["food_key"], "egg")
        self.assertEqual(row["grams"], 100.0)

    def test_food_matching_prefers_specific_names(self):
        self.assertEqual(
            match_food("Farine de blé entier"),
            "flour_whole_wheat",
        )
        self.assertEqual(
            match_food("Tofu soyeux"),
            "silken_tofu",
        )

    def test_nutrition_estimate_uses_grams(self):
        result = build_nutrition_estimate(
            [
                {
                    "name": "Banane",
                    "food_key": "banana",
                    "grams": 100,
                }
            ],
            2,
        )
        nutrition = result["nutrition"]
        self.assertEqual(result["used_count"], 1)
        self.assertAlmostEqual(nutrition["calories_kcal"], 89.0)
        self.assertTrue(nutrition["estimated"])
        self.assertEqual(nutrition["basis"], "whole_recipe")

    def test_unresolved_ingredient_is_explicitly_skipped(self):
        result = build_nutrition_estimate(
            [
                {
                    "name": "Épices au goût",
                    "food_key": "",
                    "grams": None,
                }
            ],
            4,
        )
        self.assertEqual(result["used_count"], 0)
        self.assertEqual(result["skipped_count"], 1)
        self.assertIn("Épices au goût", result["nutrition"]["notes"][0])

    def test_recipe_extra_preserves_metric_overrides(self):
        extra = normalize_recipe_extra(
            {
                "ingredient_metrics": {
                    "12": {
                        "grams": 180.5,
                        "food_key": "flour_all_purpose",
                        "source": "manual",
                    }
                }
            }
        )
        self.assertEqual(
            extra["ingredient_metrics"]["12"]["grams"],
            180.5,
        )
        self.assertEqual(
            extra["ingredient_metrics"]["12"]["food_key"],
            "flour_all_purpose",
        )

    def test_metric_serialization_is_keyed_by_ingredient_id(self):
        metrics = serialize_metrics(
            [
                {
                    "ingredient_id": 3,
                    "food_key": "banana",
                    "grams": 118,
                    "metric_source": "manual",
                }
            ]
        )
        self.assertEqual(metrics["3"]["grams"], 118.0)
        self.assertEqual(metrics["3"]["source"], "manual")

    def test_pdf_is_generated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "recette.pdf"
            build_recipe_pdf(
                recipe={
                    "name": "Recette test",
                    "description": "Description",
                    "servings": 2,
                    "instructions": "Mélanger.\nCuire.",
                },
                ingredients=[
                    {
                        "id": 1,
                        "name": "Farine",
                        "quantity": 1,
                        "note": "1 tasse",
                    }
                ],
                extras={
                    "ingredient_metrics": {
                        "1": {
                            "grams": 120,
                            "food_key": "flour_all_purpose",
                            "source": "auto",
                        }
                    },
                    "nutrition": None,
                    "source": {"name": "", "url": ""},
                },
                output_path=output,
                include_photo=False,
                include_nutrition=False,
                include_metric=True,
            )
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 500)

    def test_ui_exposes_measure_nutrition_and_export_actions(self):
        recipes_source = (ROOT / "recipes.py").read_text(encoding="utf-8")
        nutrition_ui = (ROOT / "recipes_extras_ui.py").read_text(encoding="utf-8")
        reader = (ROOT / "recipes_reader.py").read_text(encoding="utf-8")
        for expected in (
            '"Mesures"',
            '"PDF / courriel"',
            "open_measurement_converter_dialog",
            "open_recipe_export_dialog",
        ):
            self.assertIn(expected, recipes_source)
        self.assertIn('"Calculer automatiquement"', nutrition_ui)
        self.assertIn('"Imprimer / PDF / courriel"', reader)
        self.assertIn("metric_label", reader)

    def test_version_is_1_8_0(self):
        source = (ROOT / "app_versions.py").read_text(encoding="utf-8")
        self.assertIn('"recipes": "1.8.0"', source)


if __name__ == "__main__":
    unittest.main()
