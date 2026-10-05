from __future__ import annotations

import io
import json
from pathlib import Path
import unittest
import zipfile

from recipes_batch_import import (
    batch_summary,
    mark_batch_duplicates,
    parse_recipe_upload,
)


ROOT = Path(__file__).resolve().parents[1]


def recipe_payload(name):
    return {
        "format": "jf_apps_recipe_import",
        "version": 1,
        "recipe": {
            "name": name,
            "description": "",
            "servings": 4,
            "ingredients": [
                {
                    "name": "Oignon",
                    "quantity": "1",
                    "unit": "",
                    "note": "",
                    "order": 1,
                    "kind": "auto",
                }
            ],
            "steps": [
                {
                    "order": 1,
                    "text": "Cuire.",
                }
            ],
        },
    }


class RecipesBatchImportTests(unittest.TestCase):
    def test_single_json(self):
        content = json.dumps(
            recipe_payload("Soupe")
        ).encode("utf-8")
        rows = parse_recipe_upload("soupe.json", content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["candidate"]["name"], "Soupe")
        self.assertFalse(rows[0]["error"])

    def test_zip_with_multiple_json(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(
            buffer,
            "w",
            zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.writestr(
                "a.json",
                json.dumps(recipe_payload("A")),
            )
            archive.writestr(
                "dossier/b.json",
                json.dumps(recipe_payload("B")),
            )
            archive.writestr(
                "notes.txt",
                "ignoré",
            )

        rows = parse_recipe_upload(
            "recettes.zip",
            buffer.getvalue(),
        )
        self.assertEqual(
            [row["candidate"]["name"] for row in rows],
            ["A", "B"],
        )

    def test_invalid_json_does_not_block_other_files(self):
        good = {
            "source_name": "bon.json",
            "candidate": recipe_payload("Bon")["recipe"],
            "error": "",
        }
        bad_rows = parse_recipe_upload(
            "mauvais.json",
            b"{pas du json",
        )
        rows = mark_batch_duplicates(
            [good] + bad_rows,
            existing_recipes=[],
        )
        summary = batch_summary(rows)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["invalid"], 1)
        self.assertEqual(summary["selected"], 1)

    def test_existing_and_internal_duplicates_are_not_selected(self):
        entries = [
            {
                "source_name": "a.json",
                "candidate": recipe_payload("Soupe")["recipe"],
                "error": "",
            },
            {
                "source_name": "b.json",
                "candidate": recipe_payload("Soupe")["recipe"],
                "error": "",
            },
            {
                "source_name": "c.json",
                "candidate": recipe_payload("Tarte")["recipe"],
                "error": "",
            },
        ]
        rows = mark_batch_duplicates(
            entries,
            existing_recipes=[{"name": "Tarte"}],
        )
        self.assertFalse(rows[0]["duplicate_existing"])
        self.assertTrue(rows[0]["selected"])
        self.assertTrue(rows[1]["duplicate_batch"])
        self.assertFalse(rows[1]["selected"])
        self.assertTrue(rows[2]["duplicate_existing"])
        self.assertFalse(rows[2]["selected"])

    def test_ui_supports_multiple_and_zip(self):
        source = (
            ROOT / "recipes_chatgpt_import_ui.py"
        ).read_text(encoding="utf-8")
        self.assertIn("max_files=50", source)
        self.assertIn('accept=".json,.zip', source)
        self.assertIn('"Importer la sélection"', source)
        self.assertIn('"Tout sélectionner"', source)
        self.assertIn("reuse_existing_items", source)

    def test_version_is_1_7_0(self):
        source = (
            ROOT / "app_versions.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"recipes": "1.7.0"', source)


if __name__ == "__main__":
    unittest.main()
