from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PortalRecipesAccessTests(unittest.TestCase):
    def test_recipes_is_independent_app_definition(self):
        source = (
            ROOT / "app_access.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"recipes": {', source)
        self.assertIn("'recipes'", source)
        self.assertIn(
            "user_app_access_app_key_check",
            source,
        )

    def test_existing_grocery_users_keep_recipes_access_once(self):
        source = (
            ROOT / "app_access.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "recipes_access_migrated",
            source,
        )
        self.assertIn(
            "WHERE NOT profile.recipes_access_migrated",
            source,
        )
        self.assertIn(
            "SET recipes_access_migrated = TRUE",
            source,
        )
        self.assertIn(
            "ALTER COLUMN recipes_access_migrated",
            source,
        )

    def test_portal_card_and_route_use_recipes_permission(self):
        source = (
            ROOT / "app.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'if "recipes" in allowed_app_keys:',
            source,
        )
        recipe_route = source.index(
            "if normalized_tab in RECIPE_TABS:"
        )
        following = source[
            recipe_route:recipe_route + 700
        ]
        self.assertIn(
            '"recipes"',
            following,
        )

    def test_users_screen_exposes_recipes(self):
        access = (
            ROOT / "app_access.py"
        ).read_text(encoding="utf-8")
        users = (
            ROOT / "users.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            '"label": "Recettes"',
            access,
        )
        self.assertIn(
            'value=["grocery", "recipes"]',
            users,
        )

    def test_portal_version_is_1_5_0(self):
        source = (
            ROOT / "app_versions.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'PORTAL_VERSION = "1.5.0"',
            source,
        )


if __name__ == "__main__":
    unittest.main()
