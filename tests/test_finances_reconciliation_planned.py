from __future__ import annotations

import inspect
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock
from test_finances_reconciliation_ui import environment, load, row
from pathlib import Path

import finances_reconciliation
import finances_reconciliation_data


ROOT = Path(__file__).resolve().parents[1]


class PlannedReconciliationTests(unittest.TestCase):
    def planned_environment(self, count):
        env, ui = environment()
        env.update(
            planned_transactions_box=MagicMock(),
            list_transactions=Mock(return_value=[row(i) for i in range(count)]),
            set_transaction_status=Mock(),
            _list_planned_reconciliation_transactions=finances_reconciliation._list_planned_reconciliation_transactions,
            _confirm_planned_reconciliation_transaction=finances_reconciliation._confirm_planned_reconciliation_transaction,
            _planned_transactions_initially_open=finances_reconciliation._planned_transactions_initially_open,
        )
        load('remember_planned_expansion', env)
        load('confirm_planned_transaction', env)
        return env, ui, load('render_planned_transactions', env)

    def test_initial_expansion_and_counter_for_zero_ten_eleven_and_93(self):
        for count, expected in [(0, True), (10, True), (11, False), (93, False)]:
            with self.subTest(count=count):
                self.assertIs(finances_reconciliation._planned_transactions_initially_open(count), expected)
                env, ui, render = self.planned_environment(count)
                render()
                expansion = ui.find('expansion', f'Transactions prévues à confirmer ({count})')
                self.assertIs(expansion[2]['value'], expected)
                buttons = [w for w in ui.widgets if w[0] == 'button' and w[1] == ('Confirmer',)]
                self.assertEqual(len(buttons), count)
                if count == 0:
                    ui.find('label', 'Aucune transaction prévue pour ce mode de paiement.')

    def test_manual_choice_survives_refresh_and_count_change(self):
        for count, choice in [(93, True), (10, False)]:
            with self.subTest(count=count):
                env, ui, render = self.planned_environment(count)
                render()
                ui.find('expansion')[2]['on_value_change'](SimpleNamespace(value=choice))
                env['list_transactions'].return_value = [row()]
                render()
                self.assertIs(ui.find('expansion')[2]['value'], choice)
                ui.find('expansion', 'Transactions prévues à confirmer (1)')

    def test_payment_change_resets_manual_choice_before_refresh(self):
        for count, expected in [(10, True), (93, False)]:
            with self.subTest(count=count):
                env, ui, render = self.planned_environment(count)
                env['planned_expansion_state']['open'] = not expected
                env['reconciliation_payment'].value = 8
                env['refresh_reconciliation_screen'].side_effect = lambda **kwargs: render()
                load('change_reconciliation_payment', env)()
                self.assertIs(ui.find('expansion')[2]['value'], expected)
                env['list_transactions'].assert_called_once_with(
                    7, status='planned', payment_method_id=8,
                    reconciliation_status='unreconciled', limit=500)

    def test_confirm_button_updates_existing_transaction_and_refreshes(self):
        env, ui, render = self.planned_environment(1)
        env['list_transactions'].return_value = [row(44, status='planned')]
        def confirm(user_id, transaction_id, status):
            self.assertEqual((user_id, transaction_id, status), (7, 44, 'confirmed'))
            env['list_transactions'].return_value = []
        env['set_transaction_status'].side_effect = confirm
        env['refresh_all'].side_effect = render
        render()
        ui.find('expansion')[2]['on_value_change'](SimpleNamespace(value=False))
        ui.click('Confirmer')
        env['set_transaction_status'].assert_called_once_with(7, 44, 'confirmed')
        env['refresh_all'].assert_called_once_with()
        self.assertIs(ui.find('expansion', 'Transactions prévues à confirmer (0)')[2]['value'], False)

    def test_confirmation_error_does_not_refresh(self):
        env, ui, render = self.planned_environment(1)
        env['set_transaction_status'].side_effect = ValueError('refus')
        render()
        ui.click('Confirmer')
        env['refresh_all'].assert_not_called()
        ui.notify.assert_called_once_with('refus', type='warning')

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
        self.assertIn('"finances": "1.13.5"', versions)
        self.assertIn('"version": "1.13.5"', versions)
        self.assertIn('"title": "Finances — V1.13.5"', manual)
        self.assertIn("Transactions prévues à confirmer", manual)


if __name__ == "__main__":
    unittest.main()
