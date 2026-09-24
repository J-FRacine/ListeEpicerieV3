from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RecipesV142Tests(unittest.TestCase):
    def test_toggle_captures_its_own_context(self):
        source = (ROOT / "recipes.py").read_text(encoding="utf-8")

        self.assertIn(
            "context=details_context",
            source,
        )
        self.assertIn(
            'container = context.get("container")',
            source,
        )
        self.assertIn(
            'details_context["container"] = details_container',
            source,
        )

    def test_old_late_bound_state_pattern_is_removed(self):
        source = (ROOT / "recipes.py").read_text(encoding="utf-8")

        self.assertNotIn(
            'new_value = not details_state["open"]',
            source,
        )

    def test_each_toggle_keeps_recipe_id_and_context(self):
        source = (ROOT / "recipes.py").read_text(encoding="utf-8")

        # Vérifie la logique utile sans dépendre de l'indentation exacte.
        self.assertIn(
            "selected_recipe_id=recipe_id",
            source,
        )
        self.assertIn(
            "context=details_context",
            source,
        )
        self.assertIn(
            "save_recipe_open_state(",
            source,
        )
        self.assertIn(
            'details_context["container"] = details_container',
            source,
        )

    def test_version_is_1_4_2(self):
        source = (ROOT / "app_versions.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"recipes": "1.4.2"', source)


if __name__ == "__main__":
    unittest.main()
