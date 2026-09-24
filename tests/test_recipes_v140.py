from __future__ import annotations

from io import BytesIO
from pathlib import Path
import unittest

from PIL import Image

from recipes_photo_images import (
    MAX_STORED_BYTES,
    MAX_UPLOAD_BYTES,
    normalize_recipe_photo,
    recipe_photo_to_data_url,
)


ROOT = Path(__file__).resolve().parents[1]


class RecipesV140Tests(unittest.TestCase):
    def _sample_png(self, width=1800, height=1200):
        image = Image.new("RGB", (width, height), (220, 80, 40))
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    def test_photo_is_resized_and_compressed(self):
        result = normalize_recipe_photo(
            self._sample_png(),
            file_name="recette.png",
        )
        self.assertEqual(result["mime_type"], "image/jpeg")
        self.assertLessEqual(max(result["width"], result["height"]), 1200)
        self.assertLessEqual(result["image_size"], MAX_STORED_BYTES)
        self.assertLessEqual(
            max(
                result["thumbnail_width"],
                result["thumbnail_height"],
            ),
            320,
        )
        self.assertGreater(result["thumbnail_size"], 0)

    def test_invalid_or_oversized_photo_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_recipe_photo(b"pas une image")
        with self.assertRaises(ValueError):
            normalize_recipe_photo(b"x" * (MAX_UPLOAD_BYTES + 1))

    def test_photo_data_url_is_available(self):
        result = normalize_recipe_photo(self._sample_png(400, 300))
        url = recipe_photo_to_data_url(result)
        self.assertTrue(url.startswith("data:image/jpeg;base64,"))

    def test_schema_contains_recipe_photo_table(self):
        source = (ROOT / "grocery_schema.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "CREATE TABLE IF NOT EXISTS grocery_recipe_photos",
            source,
        )
        self.assertIn("ON DELETE CASCADE", source)
        self.assertIn("thumbnail_data BYTEA NOT NULL", source)

    def test_ui_places_consult_in_visible_recipe_header(self):
        source = (ROOT / "recipes.py").read_text(encoding="utf-8")
        self.assertNotIn('recipe_expansion.add_slot("header")', source)
        self.assertIn('icon="unfold_more"', source)
        self.assertIn("details_container.set_visibility", source)
        consult_position = source.index('"Consulter"')
        name_position = source.index('recipe["name"]', consult_position)
        self.assertLess(consult_position, name_position)
        self.assertIn('"Photo"', source)

    def test_reader_supports_photo(self):
        source = (ROOT / "recipes_reader.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("photo_data_url=None", source)
        self.assertGreaterEqual(source.count("if photo_data_url:"), 2)

    def test_chatgpt_json_is_collapsed(self):
        source = (ROOT / "recipes_chatgpt_import_ui.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '"Coller du JSON ou voir le JSON source"',
            source,
        )
        self.assertIn("value=False", source)
        self.assertIn("json_source_expansion.value = False", source)

    def test_legacy_site_import_is_no_longer_exposed(self):
        source = (ROOT / "recipes.py").read_text(encoding="utf-8")
        self.assertNotIn('"Importer mon ancien site"', source)
        self.assertNotIn(
            "from recipes_site_import_ui import",
            source,
        )

    def test_backup_contains_recipe_photo(self):
        source = (ROOT / "grocery_backup.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("image_data_base64", source)
        self.assertIn("thumbnail_data_base64", source)
        self.assertIn("grocery_recipe_photos", source)

    def test_version_is_1_4_0(self):
        source = (ROOT / "app_versions.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"recipes": "1.4.2"', source)


if __name__ == "__main__":
    unittest.main()
