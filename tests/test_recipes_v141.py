from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RecipesV141Tests(unittest.TestCase):
    def test_broken_expansion_header_slot_is_removed(self):
        source = (ROOT / "recipes.py").read_text(encoding="utf-8")
        self.assertNotIn('add_slot("header")', source)
        self.assertNotIn("recipe_expansion", source)

    def test_recipe_header_uses_regular_visible_components(self):
        source = (ROOT / "recipes.py").read_text(encoding="utf-8")
        self.assertIn(
            '"w-full items-center gap-3 flex-nowrap px-3 py-3"',
            source,
        )
        self.assertIn('"Consulter"', source)
        self.assertIn('icon="unfold_more"', source)
        self.assertIn("recipe_thumbnail_url", source)
        self.assertIn('recipe["name"]', source)
        self.assertIn("_recipe_caption(", source)

    def test_details_toggle_preserves_open_state(self):
        source = (ROOT / "recipes.py").read_text(encoding="utf-8")
        self.assertIn("details_state", source)
        self.assertIn("save_recipe_open_state(", source)
        self.assertIn("details_container.set_visibility(", source)

    def test_version_is_1_4_1(self):
        source = (ROOT / "app_versions.py").read_text(encoding="utf-8")
        self.assertIn('"recipes": "1.4.1"', source)


if __name__ == "__main__":
    unittest.main()
