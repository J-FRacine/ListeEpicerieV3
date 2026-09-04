"""Caractérisation Budget : vrais calculs, lectures PostgreSQL simulées."""
import importlib
import subprocess
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from datetime import date
from decimal import Decimal as D
from types import ModuleType
from unittest.mock import MagicMock, Mock, call, patch

db_stub = ModuleType("db")
db_stub.get_connection = Mock(side_effect=AssertionError("SQL non simulé"))
with patch.dict(sys.modules, {"db": db_stub}):
    data = importlib.import_module("finances_data")


def income(amount="1000", **extra):
    return dict(item_type="income", input_frequency="biweekly",
                biweekly_amount=D(amount), monthly_amount=D(amount) * 26 / 12, **extra)


def recurrence(identity=1, amount="1000", **extra):
    values = dict(id=identity, amount=D(amount), transaction_type="income",
                  is_active=True, frequency_unit="week", frequency_interval=2,
                  start_date=date(2026, 10, 2), next_date=date(2026, 12, 11))
    values.update(extra)
    return values


class BudgetTests(unittest.TestCase):
    def capacity(self, rows, recurrences):
        with patch.object(data, "list_budget_items", return_value=rows), \
             patch.object(data, "list_recurrences", return_value=recurrences), \
             patch.object(data, "get_finance_settings", return_value={}):
            return data.budget_capacity_summary(1, "2026-10")

    def test_largest_linked_income_determines_pay_calendar(self):
        result = self.capacity([income("100", recurrence_id=2), income(recurrence_id=1)],
                               [recurrence(), recurrence(2, "100", frequency_unit="month",
                                                         frequency_interval=1)])
        self.assertEqual(result["pay_count_source"], "recurrence")
        self.assertEqual(result["pay_count"], 3)
        self.assertEqual(result["available_month"], D("3300.00"))

    def test_unlinked_income_detects_nearest_active_biweekly_anchor(self):
        result = self.capacity([income()], [recurrence(2, "100", next_date=date(2026, 12, 4)),
                                           recurrence(), recurrence(3, is_active=False)])
        self.assertEqual(result["pay_count_source"], "recurrence_detected")
        self.assertEqual(result["pay_dates"], [date(2026, 10, d) for d in (2, 16, 30)])
        self.assertEqual(result["available_month"], D("3000.00"))

    def test_no_reliable_anchor_falls_back_to_two_pays(self):
        result = self.capacity([income()], [recurrence(is_active=False),
                                           recurrence(2, transaction_type="expense")])
        self.assertEqual(result["pay_count_source"], "fallback_2")
        self.assertEqual(result["pay_dates"], [date(2026, 10, 1)] * 2)
        self.assertEqual(result["available_month"], D("2000.00"))

    def test_rounding_and_custom_amount_per_pay(self):
        for frequency, amount, override, expected in [
            ("monthly", "100", None, (D("100.00"), D("46.15"))),
            ("monthly", "100", "47.125", (D("100.00"), D("47.12"))),
            ("biweekly", "100.125", "999", (D("216.93"), D("100.12"))),
        ]:
            with self.subTest(frequency=frequency, override=override):
                self.assertEqual(data._budget_amounts_from_values(frequency, amount, override), expected)

    def test_period_flags_include_boundaries_and_reject_other_months(self):
        raw = dict(id=1, input_frequency="monthly", input_amount=D("100"),
                   effective_start=date(2026, 10, 31), effective_end=date(2026, 11, 1))
        connection = MagicMock()
        cursor = connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [raw]
        with patch.object(data, "get_connection", connection):
            for month, expected in [(9, False), (10, True), (11, True), (12, False)]:
                with self.subTest(month=month):
                    rows = data._list_budget_items_v111(1, month_value=date(2026, month, 1))
                    self.assertEqual(rows[0]["effective_for_month"], expected)

    def test_capacity_requests_active_effective_rows_through_real_sql_reader(self):
        # Le faux serveur vérifie le contrat SQL puis renvoie les lignes filtrées.
        # Il ne prétend pas exécuter les prédicats PostgreSQL.
        connection = MagicMock()
        cursor = connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        def execute(sql, params):
            if "FROM finance_budget_items AS budget" in sql:
                self.assertIn("(%s OR budget.is_active=TRUE)", sql)
                self.assertIn("budget.effective_start <= %s", sql)
                self.assertIn("budget.effective_end >= %s", sql)
                self.assertEqual(params, [1, False, date(2026, 10, 31), date(2026, 10, 1)])
                cursor.fetchall.return_value = [dict(id=1, item_type="income", input_frequency="monthly",
                                                     input_amount=D("1000"), is_active=True)]
            else:
                self.assertIn("FROM finance_budget_financing_groups", sql)
                cursor.fetchall.return_value = []
        cursor.execute.side_effect = execute
        with patch.object(data, "get_connection", connection), \
             patch.object(data, "list_recurrences", return_value=[]), \
             patch.object(data, "get_finance_settings", return_value={}):
            result = data.budget_capacity_summary(1, "2026-10")
        self.assertEqual(result["available_month"], D("1000.00"))
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(cursor.execute.call_count, 2)

    def test_forecast_reuses_initial_capacity_and_propagates_three_months(self):
        initial = dict(available_month=D("1800"), available_month_base=D("1800"), carry_in=0, pay_count=3)
        with patch.object(data, "get_finance_settings", return_value=dict(carry_month_balance=True, carry_start_month="2026-10")), \
             patch.object(data, "budget_capacity_summary", side_effect=AssertionError("Premier mois recalculé")), \
             patch.object(data, "_budget_capacity_summary_v110", return_value=dict(available_month=D("1200"), pay_count=2)) as base, \
             patch.object(data, "_variable_expense_total_for_month", side_effect=[D("500"), D("1600"), D("900")]):
            result = data.budget_forecast(1, "2026-10", months=3, initial_capacity=initial)
        self.assertEqual(base.call_args_list, [call(1, date(2026, 11, 1)), call(1, date(2026, 12, 1))])
        self.assertEqual([r["carry_in"] for r in result], [D("0"), D("1300"), D("900")])
        self.assertEqual([r["ending_balance"] for r in result], [D("1300"), D("900"), D("1200")])
        self.assertEqual([r["pay_count"] for r in result], [3, 2, 2])
        self.assertEqual(initial["carry_in"], 0)

    def test_forecast_without_initial_capacity_and_carry_activation(self):
        for enabled, start, expected in [(False, "2026-10", [0, 0, 0]),
                                          (True, "2026-11", [0, 0, 80])]:
            with self.subTest(enabled=enabled), \
                 patch.object(data, "get_finance_settings", return_value=dict(carry_month_balance=enabled, carry_start_month=start)), \
                 patch.object(data, "budget_capacity_summary", return_value=dict(available_month=D("100"))) as first, \
                 patch.object(data, "_budget_capacity_summary_v110", return_value=dict(available_month=D("100"))), \
                 patch.object(data, "_variable_expense_total_for_month", return_value=D("20")):
                rows = data.budget_forecast(1, "2026-10", months=3)
                first.assert_called_once_with(1, date(2026, 10, 1))
                self.assertEqual([r["carry_in"] for r in rows], expected)

    def test_variable_total_excludes_fixed_financing_and_excluded_with_one_budget_read(self):
        rows = [dict(transaction_type="expense", amount=D(amount), **extra) for amount, extra in
                [("400", dict(recurrence_id=10)), ("100", dict(installment_plan_id=20)),
                 ("250", dict(budget_excluded=True)), ("50", {}), ("25", {})]]
        rows.append(dict(transaction_type="income", amount=D("1000")))
        with patch.object(data, "_dashboard_month_projection_v190", return_value=dict(transactions=rows)) as projection, \
             patch.object(data, "list_budget_items", return_value=[dict(item_type="expense", recurrence_id=10),
                          dict(budget_financing_group=True, financing_plan_ids=[20])]) as items:
            self.assertEqual(data._variable_expense_total_for_month(1, "2026-10"), D("75.00"))
        items.assert_called_once_with(1, month_value=date(2026, 10, 1), effective_only=True)
        projection.assert_called_once_with(1, date(2026, 10, 1), kpi_limit=1000)

    def test_financing_group_replaces_stored_amount_with_monthly_sum(self):
        connection = MagicMock()
        cursor = connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [dict(budget_item_id=1, plan_ids=[20, 21], plan_names=["A", "B"])]
        for total, expected in [(D("325"), D("150.00")), (None, D("0.00"))]:
            with self.subTest(total=total), patch.object(data, "get_connection", connection), \
                 patch.object(data, "_list_budget_items_v111", return_value=[dict(id=1, monthly_amount=D("999"))]):
                cursor.fetchone.return_value = dict(total=total)
                row = data.list_budget_items(1, month_value="2026-10")[0]
                self.assertEqual(row["monthly_amount"], total or D("0"))
                self.assertEqual(row["biweekly_amount"], expected)
                self.assertTrue(row["budget_financing_group"])
                self.assertEqual(row["financing_plan_ids"], [20, 21])
                sql, params = cursor.execute.call_args.args
                self.assertIn("status IN ('planned','confirmed')", sql)
                self.assertIn("transaction_type='expense'", sql)
                self.assertEqual(params, (1, [20, 21], date(2026, 10, 1), date(2026, 10, 31)))


class BudgetArchitectureTests(unittest.TestCase):
    def test_independent_import_in_fresh_process(self):
        script = """
import importlib.abc
import sys
class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'db', 'finances_data', 'nicegui', 'psycopg'}:
            raise AssertionError('Import interdit: ' + fullname)
sys.meta_path.insert(0, Blocker())
import finances_budget_data
assert callable(finances_budget_data.budget_forecast)
"""
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_four_facades_delegate_with_successively_replaced_dependencies(self):
        contracts = {
            "budget_summary": ["list_budget_items"],
            "_budget_capacity_summary_v110": ["budget_summary", "list_recurrences"],
            "budget_capacity_summary": ["_budget_capacity_summary_v110", "get_finance_settings",
                                        "_variable_expense_total_for_month"],
            "budget_forecast": ["budget_capacity_summary", "_budget_capacity_summary_v110",
                                "_variable_expense_total_for_month", "get_finance_settings"],
        }
        for name, dependencies in contracts.items():
            for iteration in range(2):
                with self.subTest(facade=name, replacement=iteration), ExitStack() as stack:
                    replacements = {dep: stack.enter_context(patch.object(data, dep))
                                    for dep in dependencies}
                    target = stack.enter_context(patch.object(data._budget_data, name))
                    result = getattr(data, name)(1, "2026-10")
                    self.assertIs(result, target.return_value)
                    if name == "budget_forecast":
                        replacements.update(months=6, initial_capacity=None)
                    target.assert_called_once_with(1, "2026-10", **replacements)

    def test_forecast_executes_current_services_after_each_replacement(self):
        for amount in (D("100"), D("200")):
            with self.subTest(amount=amount), \
                 patch.object(data, "get_finance_settings", return_value=dict(
                     carry_month_balance=True, carry_start_month="2026-10")) as settings, \
                 patch.object(data, "budget_capacity_summary", return_value=dict(available_month=amount)) as first, \
                 patch.object(data, "_budget_capacity_summary_v110", return_value=dict(available_month=amount)) as base, \
                 patch.object(data, "_variable_expense_total_for_month", return_value=D("10")) as variable:
                rows = data.budget_forecast(1, "2026-10", months=2)
                settings.assert_called_once_with(1)
                first.assert_called_once_with(1, date(2026, 10, 1))
                base.assert_called_once_with(1, date(2026, 11, 1))
                self.assertEqual(variable.call_args_list,
                                 [call(1, date(2026, 10, 1)), call(1, date(2026, 11, 1))])
                self.assertEqual([r["ending_balance"] for r in rows],
                                 [amount - 10, 2 * (amount - 10)])


if __name__ == "__main__":
    unittest.main()
