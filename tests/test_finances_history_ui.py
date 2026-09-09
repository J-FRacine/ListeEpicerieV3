"""Protection du raccord Historique/transactions après retrait des copies mortes."""
from __future__ import annotations

import ast
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import unittest
from unittest.mock import Mock

from finances_history import HistoryActions, build_history_actions


ROOT = Path(__file__).resolve().parents[1]


def parent_source() -> str:
    return "".join(
        path.read_text(encoding="utf-8")
        for path in sorted(ROOT.glob("finances_part_*.pyfrag"))
    )


def history_block() -> str:
    text = parent_source()
    start = text.index("        # HISTORIQUE")
    end = text.index("        # RÉCURRENCES", start)
    return text[start:end]


def actions_environment():
    refresh_all = Mock(name="refresh_all")
    delete_transaction = Mock(name="delete_transaction")
    set_transaction_status = Mock(name="set_transaction_status")
    set_transaction_reconciliation = Mock(name="set_transaction_reconciliation")
    get_card_payment_transfer = Mock(
        name="get_card_payment_transfer",
        return_value={"id": 88, "amount": 125},
    )
    get_transaction = Mock(
        name="get_transaction",
        return_value={"id": 44, "description": "Épicerie"},
    )
    card_payment_dialog = Mock(name="card_payment_dialog")
    transaction_dialog = Mock(name="transaction_dialog")
    find_duplicates = Mock(name="find_duplicates", return_value=[])
    list_unreconciled = Mock(name="list_unreconciled", return_value=[])
    set_bank_seen = Mock(name="set_bank_seen")

    actions = build_history_actions(
        ui=Mock(name="ui"),
        panel=SimpleNamespace(
            start=SimpleNamespace(value="2026-09-01"),
            end=SimpleNamespace(value="2026-09-30"),
        ),
        user_id=7,
        TRANSACTION_TYPES={"expense": "Dépense", "income": "Revenu"},
        TRANSACTION_STATUSES={"planned": "À confirmer", "confirmed": "Confirmée"},
        RECONCILIATION_STATUSES={
            "unreconciled": "À concilier",
            "reconciled": "Conciliée",
        },
        signed=lambda value, kind: f"{kind}:{value}",
        money=lambda value: str(value),
        delete_transaction=delete_transaction,
        set_transaction_status=set_transaction_status,
        set_transaction_reconciliation=set_transaction_reconciliation,
        get_card_payment_transfer=get_card_payment_transfer,
        get_transaction=get_transaction,
        card_payment_dialog=card_payment_dialog,
        transaction_dialog=transaction_dialog,
        find_potential_duplicate_transactions=find_duplicates,
        list_month_unreconciled_transactions=list_unreconciled,
        set_bank_transaction_seen=set_bank_seen,
        get_month_value=lambda: date(2026, 9, 1),
        refresh_all=refresh_all,
    )
    deps = dict(
        refresh_all=refresh_all,
        delete_transaction=delete_transaction,
        set_transaction_status=set_transaction_status,
        set_transaction_reconciliation=set_transaction_reconciliation,
        get_card_payment_transfer=get_card_payment_transfer,
        get_transaction=get_transaction,
        card_payment_dialog=card_payment_dialog,
        transaction_dialog=transaction_dialog,
        find_duplicates=find_duplicates,
        list_unreconciled=list_unreconciled,
        set_bank_seen=set_bank_seen,
    )
    return actions, deps


class HistoryCleanupTests(unittest.TestCase):
    def test_module_imports_without_ui_database_or_legacy_modules(self):
        script = r'''
import builtins
real_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'nicegui', 'finances', 'finances_data', 'db', 'psycopg'}:
        raise AssertionError(name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded
import finances_history
'''
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_parent_history_uses_extracted_panel_actions_and_renderer(self):
        block = history_block()
        self.assertIn("_history_ui.build_history_panel(", block)
        self.assertIn("_history_ui.build_history_actions(", block)
        self.assertIn("_history_ui.render_history(", block)
        self.assertIn("refresh_all=lambda: refresh_all()", block)
        self.assertEqual(block.count("def render_history("), 1)

    def test_old_duplicate_history_implementations_are_removed(self):
        block = history_block()
        for name in (
            "remove_dialog",
            "confirm_transaction",
            "change_reconciliation",
            "render_transaction_row",
            "_open_history_row",
            "duplicate_search_dialog",
            "monthly_unreconciled_dialog",
            "_add_month_label_end",
        ):
            self.assertNotIn(f"            def {name}(", block, name)
        self.assertNotIn("Ancienne implémentation conservée temporairement", block)
        self.assertNotIn("return\n\n                # Ancienne implémentation", block)

    def test_history_fragments_leave_recurrences_intact_after_render(self):
        text = parent_source()
        history = text.index("        # HISTORIQUE")
        render = text.index("            render_history()", history)
        recurrences = text.index("        # RÉCURRENCES", render)
        self.assertLess(history, render)
        self.assertLess(render, recurrences)
        self.assertIn("recurrences_panel = build_recurrences_panel(", text[recurrences:])
        self.assertIn("def recurrence_dialog", (ROOT / "finances_recurrences.py").read_text(encoding="utf-8"))

    def test_building_actions_is_lazy(self):
        actions, deps = actions_environment()
        self.assertIsInstance(actions, HistoryActions)
        for dependency in deps.values():
            dependency.assert_not_called()

    def test_linked_transfer_opens_card_payment_editor(self):
        actions, deps = actions_environment()
        row = {"id": 44, "linked_transfer_id": 77}
        actions.open_history_row(row)
        deps["get_card_payment_transfer"].assert_called_once_with(7, 77)
        deps["card_payment_dialog"].assert_called_once_with(
            7,
            deps["refresh_all"],
            transfer={"id": 88, "amount": 125},
        )
        deps["transaction_dialog"].assert_not_called()
        deps["refresh_all"].assert_not_called()

    def test_regular_transaction_opens_transaction_editor(self):
        actions, deps = actions_environment()
        actions.open_history_row({"id": 44, "linked_transfer_id": None})
        deps["get_transaction"].assert_called_once_with(7, 44)
        deps["transaction_dialog"].assert_called_once_with(
            7,
            deps["refresh_all"],
            {"id": 44, "description": "Épicerie"},
        )
        deps["card_payment_dialog"].assert_not_called()

    def test_confirm_and_reconciliation_mutations_refresh_after_success(self):
        actions, deps = actions_environment()
        actions.confirm_transaction(44)
        deps["set_transaction_status"].assert_called_once_with(7, 44, "confirmed")
        deps["refresh_all"].assert_called_once_with()

        deps["refresh_all"].reset_mock()
        actions.change_reconciliation(44, "unreconciled")
        call = deps["set_transaction_reconciliation"].call_args
        self.assertEqual(call.args[:3], (7, 44, "reconciled"))
        self.assertIsInstance(call.args[3], date)
        deps["refresh_all"].assert_called_once_with()

        deps["refresh_all"].reset_mock()
        actions.change_reconciliation(44, "reconciled")
        deps["set_transaction_reconciliation"].assert_called_with(
            7, 44, "unreconciled", None
        )
        deps["refresh_all"].assert_called_once_with()

    def test_failed_mutation_does_not_refresh(self):
        actions, deps = actions_environment()
        deps["set_transaction_status"].side_effect = ValueError("refus")
        actions.confirm_transaction(44)
        deps["refresh_all"].assert_not_called()

    def test_month_end_helper_handles_leap_year_and_december(self):
        actions, _ = actions_environment()
        self.assertEqual(actions.add_month_label_end("2024-02"), "2024-02-29")
        self.assertEqual(actions.add_month_label_end("2026-12"), "2026-12-31")


if __name__ == "__main__":
    unittest.main()
