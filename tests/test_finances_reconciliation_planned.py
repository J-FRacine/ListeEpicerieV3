from __future__ import annotations

import inspect
import unittest
from datetime import date
from pathlib import Path

import finances_reconciliation
import finances_reconciliation_data


ROOT = Path(__file__).resolve().parents[1]


class PlannedReconciliationTests(unittest.TestCase):
    def test_planned_reader_uses_selected_method_and_planned_status(self):
        captured = {}

        def fake_list_transactions(user_id, **kwargs):
            captured["user_id"] = user_id
            captured.update(kwargs)
            return [
                {"id": 9, "transaction_date": date(2026, 9, 20)},
                {"id": 4, "transaction_date": date(2026, 9, 10)},
            ]

        rows = finances_reconciliation._list_planned_reconciliation_transactions(
            12,
            7,
            list_transactions=fake_list_transactions,
        )

        self.assertEqual([row["id"] for row in rows], [4, 9])
        self.assertEqual(captured["user_id"], 12)
        self.assertEqual(captured["status"], "planned")
        self.assertEqual(captured["payment_method_id"], 7)
        self.assertEqual(captured["reconciliation_status"], "unreconciled")
        self.assertEqual(captured["limit"], 500)

    def test_planned_reader_without_method_returns_empty_without_query(self):
        called = False

        def fake_list_transactions(*args, **kwargs):
            nonlocal called
            called = True
            return []

        rows = finances_reconciliation._list_planned_reconciliation_transactions(
            12,
            None,
            list_transactions=fake_list_transactions,
        )

        self.assertEqual(rows, [])
        self.assertFalse(called)

    def test_confirmation_reuses_existing_confirmed_status_write(self):
        calls = []

        def fake_set_status(*args):
            calls.append(args)
            return "ok"

        result = (
            finances_reconciliation._confirm_planned_reconciliation_transaction(
                12,
                44,
                set_transaction_status=fake_set_status,
            )
        )

        self.assertEqual(result, "ok")
        self.assertEqual(calls, [(12, 44, "confirmed")])

    def test_builder_requires_planned_read_and_confirmation_dependencies(self):
        params = inspect.signature(
            finances_reconciliation.build_reconciliation_panel
        ).parameters
        self.assertIn("list_transactions", params)
        self.assertIn("set_transaction_status", params)

    def test_confirmed_reconciliation_query_remains_separate(self):
        source = inspect.getsource(
            finances_reconciliation_data.list_unreconciled_transactions
        )
        self.assertIn('status="confirmed"', source)
        self.assertIn('reconciliation_status="unreconciled"', source)

    def test_parent_wires_both_existing_services(self):
        source = (ROOT / "finances_part_10.pyfrag").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "list_transactions=lambda *args, **kwargs: list_transactions(*args, **kwargs)",
            source,
        )
        self.assertIn(
            "set_transaction_status=lambda *args, **kwargs: set_transaction_status(*args, **kwargs)",
            source,
        )

    def test_version_manual_and_release_notes_are_updated(self):
        versions = (ROOT / "app_versions.py").read_text(encoding="utf-8")
        manual = (ROOT / "manual.py").read_text(encoding="utf-8")
        self.assertIn('"finances": "1.13.4"', versions)
        self.assertIn('"version": "1.13.4"', versions)
        self.assertIn('"title": "Finances — V1.13.4"', manual)
        self.assertIn("Transactions prévues à confirmer", manual)


if __name__ == "__main__":
    unittest.main()
