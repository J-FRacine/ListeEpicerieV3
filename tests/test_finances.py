"""Régressions métier sans serveur PostgreSQL ni dépendance externe."""
import importlib
import sys
import unittest
from datetime import date
from decimal import Decimal as D
from types import ModuleType
from unittest.mock import Mock, patch

from finances_calculations import automatic_installment_amount, analyze_installment_progress


# Charger les vrais fragments via le chargeur de production. Toute tentative
# d'accès SQL non explicitement simulée fait échouer le test immédiatement.
db_stub = ModuleType("db")
db_stub.get_connection = Mock(side_effect=AssertionError("Accès PostgreSQL interdit dans ces tests"))
with patch.dict(sys.modules, {"db": db_stub}):
    data = importlib.import_module("finances_data")


def transaction(amount, kind="expense", day=5, **values):
    return dict(amount=D(amount), transaction_type=kind,
                transaction_date=date(2026, 1, day), description="Test",
                status="confirmed", **values)


class FinancesTests(unittest.TestCase):
    def test_three_pay_month_and_following_two_pay_month(self):
        rows = [dict(item_type="income", recurrence_id=1,
                     input_frequency="biweekly", biweekly_amount=D("1000"),
                     monthly_amount=D("2166.67")),
                dict(item_type="expense", biweekly_amount=D("400"),
                     monthly_amount=D("866.67"))]
        # Ancrage futur : le calcul doit retrouver les paies historiques.
        recurrence = dict(id=1, is_active=True, frequency_unit="week",
                          frequency_interval=2, start_date=date(2026, 1, 2),
                          next_date=date(2026, 3, 13))
        with patch.object(data, "list_budget_items", return_value=rows), \
             patch.object(data, "list_recurrences", return_value=[recurrence]), \
             patch.object(data, "get_finance_settings", return_value={}):
            january = data.budget_capacity_summary(1, "2026-01")
            february = data.budget_capacity_summary(1, "2026-02")
        self.assertEqual(january["pay_dates"], [date(2026, 1, d) for d in (2, 16, 30)])
        self.assertEqual(january["pay_count"], 3)
        self.assertEqual(january["available_month"], D("1800.00"))
        self.assertEqual(february["pay_count"], 2)
        self.assertEqual(february["available_month"], D("1200.00"))

    def test_financing_without_interest_includes_fees(self):
        self.assertEqual(automatic_installment_amount("1200", 12, "0", "60", "month", 1), D("105.00"))

    def test_financing_with_interest(self):
        # Prêt de 1 200 $, 12 versements mensuels, taux annuel de 12 %.
        self.assertEqual(automatic_installment_amount("1200", 12, "12", "0", "month", 1), D("106.62"))

    def test_financing_completed(self):
        self.assertEqual(automatic_installment_amount("1200", 0, "12", "0", "month", 1), D("0.00"))
        result = analyze_installment_progress(original_amount="1200", remaining_balance="0",
                                             installment_amount="100", total_installments=12,
                                             completed_installments=12)
        self.assertEqual(result["estimated_remaining_installments"], 0)
        self.assertEqual(result["expected_remaining_balance"], D("0.00"))
        self.assertFalse(result["is_inconsistent"])

    def test_bank_current_and_projected_balances(self):
        account = dict(id=1, name="Banque", method_type="bank",
                       opening_balance=D("1000"), opening_balance_date=date(2026, 1, 1))
        rows = [transaction("500", "income", 2), transaction("200", day=3),
                transaction("100", day=4), transaction("1500", day=20)]
        rows[2]["status"] = rows[3]["status"] = "planned"
        with patch.object(data, "list_bank_accounts", return_value=[account]), \
             patch.object(data, "list_transactions", return_value=rows), \
             patch.object(data, "list_recurrences", return_value=[]):
            result = data.bank_cashflow_month(1, 1, "2026-01", today_value=date(2026, 1, 10))
        self.assertEqual(result["start_balance"], D("1000"))
        self.assertEqual(result["current_balance"], D("1300"))
        self.assertEqual(result["end_balance"], D("-300"))
        self.assertEqual(result["minimum_balance"], D("-300"))
        self.assertEqual([r["running_balance"] for r in result["rows"]],
                         [D("1500"), D("1300"), D("1200"), D("-300")])

    def test_credit_line_uses_debt_direction(self):
        account = dict(id=1, name="Marge", method_type="credit_line", credit_limit=D("5000"),
                       opening_balance=D("1000"), opening_balance_date=date(2026, 1, 1))
        with patch.object(data, "list_bank_accounts", return_value=[account]), \
             patch.object(data, "list_transactions", return_value=[transaction("200"), transaction("50", "income", 6)]), \
             patch.object(data, "list_recurrences", return_value=[]):
            result = data.bank_cashflow_month(1, 1, "2026-01", today_value=date(2026, 1, 10))
        self.assertEqual(result["current_balance"], D("1150"))
        self.assertEqual(result["end_balance"], D("1150"))
        self.assertEqual(result["current_available_credit"], D("3850"))

    def test_fixed_budget_and_financing_are_not_counted_twice(self):
        rows = [transaction("400", recurrence_id=10, projection_bucket="realized"),
                transaction("100", installment_plan_id=20, projection_bucket="upcoming"),
                transaction("50", projection_bucket="realized"),
                transaction("25", projection_bucket="upcoming")]
        projection = dict(transactions=rows, realized={}, upcoming={}, total={}, kpis={})
        budget_rows = [dict(item_type="expense", recurrence_id=10),
                       dict(item_type="expense", budget_financing_group=True, financing_plan_ids=[20])]
        with patch.object(data, "_dashboard_month_projection_v190", return_value=projection), \
             patch.object(data, "list_budget_items", return_value=budget_rows), \
             patch.object(data, "list_categories", return_value=[]), \
             patch.object(data, "list_tags", return_value=[]), \
             patch.object(data, "budget_capacity_summary", return_value={"available_month": D("600")}):
            result = data.dashboard_month_projection(1, "2026-01", today_value=date(2026, 1, 10))
        self.assertEqual(result["fixed_budget"]["total"], D("500"))
        self.assertEqual(result["realized"]["expenses"], D("50"))
        self.assertEqual(result["upcoming"]["expenses"], D("25"))
        self.assertEqual(result["total"]["expenses"], D("75"))
        self.assertEqual(result["remaining_available"], D("525"))
        self.assertEqual(len(result["upcoming_transactions"]), 1)
        self.assertEqual(result["kpis"]["expense"]["categories"][0]["total"], D("75"))


if __name__ == "__main__":
    unittest.main()
