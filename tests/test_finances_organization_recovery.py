"""Contrats de récupération Organisation depuis le main GitHub V1.13.2."""
from __future__ import annotations

import ast
import inspect
from pathlib import Path
import unittest
from unittest.mock import Mock

import finances_organization_data as data
import finances_organization_writes as writes

ROOT = Path(__file__).resolve().parents[1]

READ_FUNCTIONS = {
    "list_categories",
    "list_tags",
    "_normalized_lookup_name",
    "_optional_day",
    "list_payment_methods",
}
WRITE_FUNCTIONS = {
    "ensure_default_finance_categories",
    "save_category",
    "toggle_category",
    "set_category_dashboard_visible",
    "save_tag",
    "get_or_create_finance_category",
    "get_or_create_finance_tag",
    "toggle_tag",
    "set_tag_dashboard_visible",
    "ensure_default_finance_payment_methods",
    "save_payment_method",
    "toggle_payment_method",
    "move_payment_method",
}


class OrganizationRecoveryTests(unittest.TestCase):
    def test_data_module_contains_only_reads_and_helpers(self):
        tree = ast.parse((ROOT / "finances_organization_data.py").read_text(encoding="utf-8"))
        functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        self.assertEqual(functions, READ_FUNCTIONS)

    def test_writes_module_contains_expected_thirteen_functions(self):
        tree = ast.parse((ROOT / "finances_organization_writes.py").read_text(encoding="utf-8"))
        functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        self.assertEqual(functions, WRITE_FUNCTIONS)

    def test_writes_module_has_no_database_ui_or_legacy_imports(self):
        tree = ast.parse((ROOT / "finances_organization_writes.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue({"db", "psycopg", "nicegui", "finances", "finances_data"}.isdisjoint(imported))
        self.assertLessEqual(imported, {"__future__", "datetime"})

    def test_facades_route_reads_and_writes_to_separate_modules(self):
        text = (ROOT / "finances_data_part_02.pyfrag").read_text(encoding="utf-8")
        self.assertIn("import finances_organization_data as _organization_data", text)
        self.assertIn("import finances_organization_writes as _organization_writes", text)
        for name in READ_FUNCTIONS:
            self.assertIn(f"_organization_data.{name}(", text, name)
        for name in WRITE_FUNCTIONS:
            self.assertIn(f"_organization_writes.{name}(", text, name)

    def test_tag_write_signatures_receive_connection_explicitly(self):
        for function in (writes.toggle_tag, writes.set_tag_dashboard_visible):
            parameter = inspect.signature(function).parameters["get_connection"]
            self.assertEqual(parameter.kind, inspect.Parameter.KEYWORD_ONLY)

    def test_normalized_lookup_name_handles_accents_case_and_spaces(self):
        self.assertEqual(data._normalized_lookup_name("  Épicerie   DU Coin  "), "epicerie du coin")
        self.assertEqual(data._normalized_lookup_name("CAFÉ"), data._normalized_lookup_name("cafe"))

    def test_optional_day_accepts_blank_and_bounds(self):
        self.assertIsNone(data._optional_day(None, "Jour"))
        self.assertIsNone(data._optional_day("", "Jour"))
        self.assertEqual(data._optional_day("1", "Jour"), 1)
        self.assertEqual(data._optional_day(31, "Jour"), 31)

    def test_optional_day_rejects_out_of_range_values(self):
        for value in (0, 32, -1, 99):
            with self.subTest(value=value), self.assertRaises(ValueError):
                data._optional_day(value, "Jour")

    def test_quick_category_reactivates_existing_match_without_creation(self):
        existing = {
            "id": 12,
            "name": "Épicerie",
            "full_name": "Maison › Épicerie",
            "parent_id": 9,
            "is_active": False,
        }
        list_categories = Mock(return_value=[existing])
        toggle_category = Mock()
        save_category = Mock()
        result = writes.get_or_create_finance_category(
            7,
            "  epicerie ",
            parent_id=9,
            category_type="expense",
            _text=lambda value, *_args: str(value).strip(),
            _normalized_lookup_name=data._normalized_lookup_name,
            list_categories=list_categories,
            toggle_category=toggle_category,
            save_category=save_category,
        )
        self.assertEqual(result, {"id": 12, "created": False, "name": "Épicerie", "full_name": "Maison › Épicerie"})
        toggle_category.assert_called_once_with(7, 12, True)
        save_category.assert_not_called()

    def test_quick_tag_creates_then_rereads_new_tag(self):
        created = {"id": 22, "name": "Vacances", "is_active": True}
        list_tags = Mock(side_effect=[[], [created]])
        toggle_tag = Mock()
        save_tag = Mock()
        result = writes.get_or_create_finance_tag(
            7,
            " Vacances ",
            _text=lambda value, *_args: str(value).strip(),
            _normalized_lookup_name=data._normalized_lookup_name,
            list_tags=list_tags,
            toggle_tag=toggle_tag,
            save_tag=save_tag,
        )
        self.assertEqual(result, {"id": 22, "created": True, "name": "Vacances"})
        save_tag.assert_called_once_with(7, " Vacances ")
        toggle_tag.assert_not_called()
        self.assertEqual(list_tags.call_count, 2)


if __name__ == "__main__":
    unittest.main()
