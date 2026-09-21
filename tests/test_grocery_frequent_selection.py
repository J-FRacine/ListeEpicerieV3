from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import sys
import types
import unittest

import app_versions


ROOT = Path(__file__).resolve().parents[1]
GROCERY_ITEMS_PATH = ROOT / "grocery_items.py"
ITEMS_UI_PATH = ROOT / "items.py"
SCHEMA_PATH = ROOT / "grocery_schema.py"
BACKUP_PATH = ROOT / "grocery_backup.py"
MANUAL_PATH = ROOT / "manual.py"


def load_grocery_items():
    fake_db = types.ModuleType("db")
    fake_db.get_connection = lambda: None
    fake_db._require_family_access = lambda *args, **kwargs: None

    fake_common = types.ModuleType("grocery_common")
    fake_common.log_activity = lambda *args, **kwargs: None

    previous_db = sys.modules.get("db")
    previous_common = sys.modules.get("grocery_common")
    sys.modules["db"] = fake_db
    sys.modules["grocery_common"] = fake_common
    try:
        spec = importlib.util.spec_from_file_location(
            "_grocery_items_frequent_test_target",
            GROCERY_ITEMS_PATH,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("Impossible de charger grocery_items.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_db is None:
            sys.modules.pop("db", None)
        else:
            sys.modules["db"] = previous_db
        if previous_common is None:
            sys.modules.pop("grocery_common", None)
        else:
            sys.modules["grocery_common"] = previous_common


items_data = load_grocery_items()


class QueryCursor:
    def __init__(self):
        self.sql = ""
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return []


class QueryConnection:
    def __init__(self, cursor):
        self.cursor_object = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_object


class CountCursor:
    def __init__(self, total):
        self.total = total
        self.sql = ""
        self.params = None

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params

    def fetchone(self):
        return {"total": self.total}


class FrequentSelectionTests(unittest.TestCase):
    def test_limit_is_exactly_ten(self):
        self.assertEqual(items_data.MAX_FREQUENT_ITEMS, 10)
        cursor = QueryCursor()
        connection = QueryConnection(cursor)
        original_get_connection = items_data._db.get_connection
        original_access = items_data._db._require_family_access
        try:
            items_data._db.get_connection = lambda: connection
            items_data._db._require_family_access = lambda *args: None
            items_data.get_frequent_items(7, 9, limit=999)
        finally:
            items_data._db.get_connection = original_get_connection
            items_data._db._require_family_access = original_access

        self.assertIn("item.frequent_selected = TRUE", cursor.sql)
        self.assertNotIn("item.needed = 0", cursor.sql)
        self.assertIn("LIMIT 10", cursor.sql)
        self.assertEqual(cursor.params, (9,))

    def test_capacity_accepts_ninth_selection(self):
        cursor = CountCursor(9)
        items_data._ensure_frequent_selection_capacity(
            cursor,
            family_id=3,
            item_id=77,
            selected=True,
            current_selected=False,
        )
        self.assertIn("frequent_selected = TRUE", cursor.sql)
        self.assertEqual(cursor.params, (3, 77))

    def test_capacity_rejects_eleventh_selection(self):
        cursor = CountCursor(10)
        with self.assertRaisesRegex(ValueError, "limité à 10 items"):
            items_data._ensure_frequent_selection_capacity(
                cursor,
                family_id=3,
                item_id=77,
                selected=True,
                current_selected=False,
            )

    def test_existing_selection_does_not_consume_an_extra_slot(self):
        cursor = CountCursor(10)
        items_data._ensure_frequent_selection_capacity(
            cursor,
            family_id=3,
            item_id=77,
            selected=True,
            current_selected=True,
        )
        self.assertEqual(cursor.sql, "")

    def test_update_item_keeps_backward_compatible_optional_parameter(self):
        signature = inspect.signature(items_data.update_item)
        self.assertIn("frequent_selected", signature.parameters)
        self.assertIsNone(signature.parameters["frequent_selected"].default)
        source = GROCERY_ITEMS_PATH.read_text(encoding="utf-8")
        self.assertIn("frequent_selected = %s", source)
        self.assertIn("item.frequent_selected,", source)

    def test_selected_item_stays_visible_while_already_needed(self):
        cursor = QueryCursor()
        connection = QueryConnection(cursor)
        original_get_connection = items_data._db.get_connection
        original_access = items_data._db._require_family_access
        try:
            items_data._db.get_connection = lambda: connection
            items_data._db._require_family_access = lambda *args: None
            items_data.get_frequent_items(7, 9, limit=10)
        finally:
            items_data._db.get_connection = original_get_connection
            items_data._db._require_family_access = original_access

        self.assertIn("item.frequent_selected = TRUE", cursor.sql)
        self.assertNotIn("item.needed = 0", cursor.sql)

    def test_frequent_ui_marks_items_already_in_needs(self):
        source = ITEMS_UI_PATH.read_text(encoding="utf-8")
        self.assertIn('"check_circle"', source)
        self.assertIn('"Déjà présent dans les besoins"', source)
        self.assertIn('color=positive', source)
        self.assertIn('est déjà dans les besoins', source)

    def test_edit_dialog_has_second_checkbox_and_section_uses_ten(self):
        source = ITEMS_UI_PATH.read_text(encoding="utf-8")
        self.assertIn('"Présent dans les besoins"', source)
        self.assertIn('"Dans « Souvent ajoutés »"', source)
        self.assertIn('"w-full items-center gap-6 flex-wrap"', source)
        self.assertIn("limit=10,", source)
        self.assertIn("frequent_selected=bool(", source)
        self.assertNotIn("limit=8,", source)

    def test_schema_seeds_existing_usage_only_once_and_caps_at_ten(self):
        source = SCHEMA_PATH.read_text(encoding="utf-8")
        self.assertIn("column_name = 'frequent_selected'", source)
        self.assertIn(
            "ADD COLUMN frequent_selected BOOLEAN NOT NULL DEFAULT FALSE",
            source,
        )
        self.assertIn("ROW_NUMBER() OVER", source)
        self.assertIn("ranked.position <= 10", source)
        self.assertIn("needed = 0", source)
        self.assertIn("times_needed > 0", source)

    def test_family_backup_preserves_selection_and_old_backups_remain_compatible(self):
        source = BACKUP_PATH.read_text(encoding="utf-8")
        self.assertIn("item.frequent_selected,", source)
        self.assertIn('"frequent_selected": bool(', source)
        self.assertIn('if "frequent_selected" in item:', source)
        self.assertIn("frequent_selected = None", source)
        self.assertIn("frequent_selected = COALESCE(", source)

    def test_manual_explains_explicit_selection_and_limit(self):
        source = MANUAL_PATH.read_text(encoding="utf-8")
        self.assertIn("Dans « Souvent ajoutés »", source)
        self.assertIn("10 items maximum", source)
        self.assertIn("sauvegardes de famille", source)

    def test_official_version_stays_120_until_browser_validation(self):
        self.assertEqual(app_versions.APP_VERSIONS["grocery"], "1.2.0")


if __name__ == "__main__":
    unittest.main()
