from __future__ import annotations

from pathlib import Path
import unittest

from recipes_chatgpt_import import (
    _normalize_ingredients,
    example_import_payload,
    parse_recipe_import,
    preview_recipe_import,
)


ROOT = Path(__file__).resolve().parents[1]


class RecipesV150Tests(unittest.TestCase):
    def test_import_understands_free_ingredient_kind(self):
        rows = _normalize_ingredients(
            [
                {
                    "name": "Légumes au choix",
                    "note": "selon la saison",
                    "kind": "free",
                },
                {
                    "name": "Oignon",
                    "kind": "grocery",
                },
                {
                    "name": "Fines herbes",
                    "grocery_item": False,
                },
            ]
        )
        self.assertEqual(rows[0]["kind"], "free")
        self.assertEqual(rows[1]["kind"], "grocery")
        self.assertEqual(rows[2]["kind"], "free")

    def test_preview_separates_free_matched_and_missing(self):
        candidate = parse_recipe_import(
            {
                "format": "jf_apps_recipe_import",
                "version": 1,
                "recipe": {
                    "name": "Potage",
                    "servings": 4,
                    "ingredients": [
                        {"name": "Oignon", "kind": "grocery"},
                        {"name": "Légumes au choix", "kind": "free"},
                        {"name": "Bouillon", "kind": "auto"},
                    ],
                    "steps": ["Cuire et mélanger."],
                },
            }
        )
        preview = preview_recipe_import(
            candidate,
            existing_items=[{"name": "Oignon"}],
            existing_recipes=[],
        )
        self.assertEqual(preview["matched_ingredients"], 1)
        self.assertEqual(
            preview["free_ingredients"],
            ["Légumes au choix"],
        )
        self.assertEqual(
            preview["missing_ingredients"],
            ["Bouillon"],
        )

    def test_example_contains_both_ingredient_types(self):
        candidate = parse_recipe_import(example_import_payload())
        kinds = {
            row["kind"]
            for row in candidate["ingredients"]
        }
        self.assertIn("grocery", kinds)
        self.assertIn("free", kinds)

    def test_schema_allows_linked_or_free_recipe_ingredients(self):
        source = (ROOT / "grocery_schema.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "ALTER COLUMN item_id DROP NOT NULL",
            source,
        )
        self.assertIn(
            "ADD COLUMN IF NOT EXISTS free_name TEXT",
            source,
        )
        self.assertIn(
            "grocery_recipe_ingredients_source_check",
            source,
        )
        self.assertIn(
            "ADD COLUMN IF NOT EXISTS is_free BOOLEAN",
            source,
        )

    def test_planning_exposes_free_ingredient_function(self):
        source = (ROOT / "grocery_planning.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "def add_recipe_free_ingredient(",
            source,
        )
        self.assertIn(
            "COALESCE(item.name, ingredient.free_name) AS name",
            source,
        )
        self.assertIn(
            "free_ingredients_skipped",
            source,
        )

    def test_ui_has_two_ingredient_choices(self):
        source = (ROOT / "recipes.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '"Item d’épicerie existant"',
            source,
        )
        self.assertIn(
            '"Ingrédient libre"',
            source,
        )
        self.assertIn(
            "add_recipe_free_ingredient(",
            source,
        )
        self.assertIn(
            "non ajouté automatiquement à l’épicerie",
            source,
        )

    def test_chatgpt_missing_item_creation_is_opt_in(self):
        source = (ROOT / "recipes_chatgpt_import_ui.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '"Créer les ingrédients non reconnus comme items d’épicerie"',
            source,
        )
        self.assertIn(
            "value=False",
            source,
        )

    def test_backup_and_shared_library_preserve_free_type(self):
        backup = (ROOT / "grocery_backup.py").read_text(
            encoding="utf-8"
        )
        sharing = (ROOT / "grocery_sharing.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("(ingredient.item_id IS NULL) AS is_free", backup)
        self.assertIn('ingredient.get("is_free")', backup)
        self.assertIn("(ingredient.item_id IS NULL) AS is_free", sharing)
        self.assertIn("free_ingredients_copied", sharing)

    def test_version_is_1_5_0(self):
        source = (ROOT / "app_versions.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"recipes": "1.5.0"', source)


if __name__ == "__main__":
    unittest.main()
