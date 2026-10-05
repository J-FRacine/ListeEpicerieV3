from __future__ import annotations

from pathlib import Path
import unittest

from recipes_navigation import (
    breadcrumb_parts,
    build_category_navigation,
    recent_recipe_ids,
    recipe_ids_for_navigation,
)


ROOT = Path(__file__).resolve().parents[1]


class RecipesV160Tests(unittest.TestCase):
    def setUp(self):
        self.recipes = [
            {
                "id": 1,
                "name": "Base pour potages",
                "updated_at": "2026-09-10T10:00:00",
            },
            {
                "id": 2,
                "name": "Crème de brocoli",
                "updated_at": "2026-09-20T10:00:00",
            },
            {
                "id": 3,
                "name": "Brownies",
                "updated_at": "2026-09-30T10:00:00",
            },
            {
                "id": 4,
                "name": "À classer",
                "updated_at": "2026-09-01T10:00:00",
            },
        ]
        self.categories = [
            {
                "id": 10,
                "name": "Entrées",
                "parent_id": None,
                "parent_name": None,
            },
            {
                "id": 11,
                "name": "Soupes",
                "parent_id": 10,
                "parent_name": "Entrées",
            },
            {
                "id": 20,
                "name": "Desserts",
                "parent_id": None,
                "parent_name": None,
            },
        ]
        self.assignments = {
            1: {
                "category_id": 11,
                "category_name": "Soupes",
                "parent_id": 10,
                "parent_name": "Entrées",
            },
            2: {
                "category_id": 10,
                "category_name": "Entrées",
                "parent_id": None,
                "parent_name": None,
            },
            3: {
                "category_id": 20,
                "category_name": "Desserts",
                "parent_id": None,
                "parent_name": None,
            },
            4: {
                "category_id": None,
                "category_name": None,
                "parent_id": None,
                "parent_name": None,
            },
        }

    def test_main_category_count_includes_children(self):
        navigation = build_category_navigation(
            self.recipes,
            self.categories,
            self.assignments,
        )
        by_name = {
            row["name"]: row
            for row in navigation["main_categories"]
        }
        self.assertEqual(navigation["total_count"], 4)
        self.assertEqual(navigation["uncategorized_count"], 1)
        self.assertEqual(by_name["Entrées"]["count"], 2)
        self.assertEqual(by_name["Entrées"]["direct_count"], 1)
        self.assertEqual(
            by_name["Entrées"]["children"][0]["count"],
            1,
        )
        self.assertEqual(by_name["Desserts"]["count"], 1)

    def test_main_view_includes_direct_and_child_recipes(self):
        ids = recipe_ids_for_navigation(
            self.recipes,
            self.categories,
            self.assignments,
            view="main",
            main_category_id=10,
        )
        self.assertEqual(ids, {1, 2})

    def test_subcategory_view_is_exact(self):
        ids = recipe_ids_for_navigation(
            self.recipes,
            self.categories,
            self.assignments,
            view="subcategory",
            main_category_id=10,
            subcategory_id=11,
        )
        self.assertEqual(ids, {1})

    def test_uncategorized_view(self):
        ids = recipe_ids_for_navigation(
            self.recipes,
            self.categories,
            self.assignments,
            view="uncategorized",
        )
        self.assertEqual(ids, {4})

    def test_recent_order(self):
        self.assertEqual(
            recent_recipe_ids(self.recipes, limit=3),
            [3, 2, 1],
        )

    def test_breadcrumbs(self):
        self.assertEqual(
            breadcrumb_parts(
                self.categories,
                view="main",
                main_category_id=10,
            ),
            ["Entrées"],
        )
        self.assertEqual(
            breadcrumb_parts(
                self.categories,
                view="subcategory",
                main_category_id=10,
                subcategory_id=11,
            ),
            ["Entrées", "Soupes"],
        )
        self.assertEqual(
            breadcrumb_parts(
                self.categories,
                view="recent",
            ),
            ["Récentes"],
        )

    def test_ui_exposes_catalog_navigation(self):
        source = (ROOT / "recipes.py").read_text(
            encoding="utf-8"
        )
        for expected in (
            '"Parcourir par catégorie"',
            '"Toutes les recettes"',
            '"Récentes"',
            '"Sans catégorie"',
            '"La recherche couvre toutes les catégories."',
            '"Résultats de recherche"',
            "build_category_navigation(",
            "recipe_ids_for_navigation(",
        ):
            self.assertIn(expected, source)

        self.assertNotIn(
            'category_filter = ui.select(',
            source,
        )

    def test_home_does_not_load_recipe_details_first(self):
        source = (ROOT / "recipes.py").read_text(
            encoding="utf-8"
        )
        home_position = source.index(
            'search_state["view"] == "home"'
        )
        items_position = source.index(
            "items = get_items(user_id, family_id)",
            home_position,
        )
        self.assertLess(home_position, items_position)

    def test_version_is_1_6_0(self):
        source = (ROOT / "app_versions.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"recipes": "1.7.0"', source)


if __name__ == "__main__":
    unittest.main()
