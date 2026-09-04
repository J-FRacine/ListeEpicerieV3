"""Caractérisation de Compte : vrais calculs, lectures SQL simulées."""
import importlib
import sys
import subprocess
from pathlib import Path
import unittest
from contextlib import contextmanager
from datetime import date
from decimal import Decimal as D
from types import ModuleType
from unittest.mock import MagicMock, Mock, patch


db_stub = ModuleType("db")
db_stub.get_connection = Mock(side_effect=AssertionError("Accès PostgreSQL interdit"))
with patch.dict(sys.modules, {"db": db_stub}):
    data = importlib.import_module("finances_data")


def account(**changes):
    values = dict(id=1, name="Compte", method_type="bank", is_active=True,
                  opening_balance=D("1000"), opening_balance_date=date(2026, 12, 1))
    return {**values, **changes}


def movement(identifier, day, amount, kind="expense", **changes):
    values = dict(id=identifier, transaction_date=date.fromisoformat(day),
                  amount=D(amount), transaction_type=kind, description="Mouvement",
                  payment_method_id=1, user_id=7, status="confirmed")
    return {**values, **changes}


def recurrence(**changes):
    values = dict(id=10, payment_method_id=1, is_active=True, amount=D("100"),
                  transaction_type="expense", description="Récurrence",
                  start_date=date(2027, 1, 15), next_date=date(2027, 1, 15),
                  frequency_unit="week", frequency_interval=2, end_date=None)
    return {**values, **changes}


@contextmanager
def readings(rows=(), recurrences=(), selected_account=None):
    """Simuler les lectures uniquement; ne remplacer aucun calcul de Compte."""
    with patch.object(data, "list_bank_accounts", return_value=[selected_account or account()]), \
         patch.object(data, "list_transactions", return_value=list(rows)), \
         patch.object(data, "list_recurrences", return_value=list(recurrences)):
        yield


class AccountCharacterizationTests(unittest.TestCase):
    def test_movements_before_displayed_month_carry_forward(self):
        rows = [movement(1, "2026-12-10", "500", "income"),
                movement(2, "2026-12-20", "200"),
                movement(3, "2027-01-05", "100")]
        with readings(rows):
            result = data.bank_cashflow_month(7, 1, "2027-01", today_value=date(2027, 1, 31))
        self.assertEqual(result["start_balance"], D("1300"))
        self.assertEqual(result["current_balance"], D("1200"))
        self.assertEqual(result["end_balance"], D("1200"))
        self.assertEqual([r["id"] for r in result["rows"]], [3])
        self.assertEqual(result["rows"][0]["running_balance"], D("1200"))

    def test_month_without_movements_keeps_carried_balance(self):
        with readings([movement(1, "2026-12-10", "200")]):
            result = data.bank_cashflow_month(7, 1, "2027-01", today_value=date(2027, 1, 31))
        self.assertEqual(result["rows"], [])
        for key in ("start_balance", "current_balance", "minimum_balance", "maximum_balance", "end_balance"):
            self.assertEqual(result[key], D("800"), key)

    def test_year_summary_carries_december_balance_into_january(self):
        december = movement(1, "2026-12-20", "200")
        january = movement(2, "2027-01-05", "300", "income")
        # Les lectures de chaque année respectent la borne de fin demandée.
        with readings([december]):
            previous = data.bank_cashflow_year_summary(7, 1, 2026, today_value=date(2027, 1, 31))
        with readings([december, january]):
            current = data.bank_cashflow_year_summary(7, 1, 2027, today_value=date(2027, 1, 31))
        self.assertEqual(len(previous["months"]), 12)
        self.assertEqual(len(current["months"]), 12)
        self.assertFalse(previous["months"][10]["available"])
        self.assertEqual(previous["months"][11]["end_balance"], D("800"))
        first = current["months"][0]
        self.assertEqual(first["month"], date(2027, 1, 1))
        self.assertEqual(first["start_balance"], D("800"))
        self.assertEqual(first["end_balance"], D("1100"))
        self.assertEqual(current["months"][1]["start_balance"], D("1100"))
        self.assertEqual(current["months"][11]["end_balance"], D("1100"))

    def test_existing_occurrence_is_not_projected_twice(self):
        for occurrence_date in (None, date(2027, 1, 15)):
            with self.subTest(occurrence_date=occurrence_date):
                # Une occurrence explicite reste la clé même si la transaction a été déplacée.
                day = "2027-01-16" if occurrence_date else "2027-01-15"
                existing = movement(1, day, "100", recurrence_id=10, occurrence_date=occurrence_date)
                with readings([existing], [recurrence()]):
                    result = data.bank_cashflow_month(7, 1, "2027-01", today_value=date(2027, 1, 10))
                self.assertEqual(len(result["rows"]), 2)
                projected = [r for r in result["rows"] if r["projected"]]
                self.assertEqual([r["transaction_date"] for r in projected], [date(2027, 1, 29)])
                self.assertEqual(result["end_balance"], D("800"))

    def test_inactive_recurrence_is_not_projected(self):
        with readings(recurrences=[recurrence(is_active=False)]):
            result = data.bank_cashflow_month(7, 1, "2027-01", today_value=date(2027, 1, 10))
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["end_balance"], D("1000"))

    def test_finished_recurrence_stops_at_end_date(self):
        for end, dates, balance in ((date(2027, 1, 14), [], D("1000")),
                                    (date(2027, 1, 15), [date(2027, 1, 15)], D("900"))):
            with self.subTest(end=end), readings(recurrences=[recurrence(end_date=end)]):
                result = data.bank_cashflow_month(7, 1, "2027-01", today_value=date(2027, 1, 10))
            self.assertEqual([r["transaction_date"] for r in result["rows"]], dates)
            self.assertEqual(result["end_balance"], balance)

    def test_other_account_transaction_is_filtered_by_real_reader(self):
        rows = [movement(1, "2027-01-05", "100"),
                movement(2, "2027-01-05", "9000", payment_method_id=2)]
        cursor = MagicMock()

        def execute(sql, params):
            # Contrat de la vraie list_transactions, sans moteur PostgreSQL.
            query = " ".join(sql.split())
            self.assertIn("t.user_id = %s", query)
            self.assertIn("t.payment_method_id = %s", query)
            self.assertIn("t.transaction_date >= %s", query)
            self.assertIn("t.transaction_date <= %s", query)
            self.assertEqual(list(params), [7, date(2026, 12, 1), date(2027, 1, 31), 1, 100000])
            cursor.fetchall.return_value = [r for r in rows if r["payment_method_id"] == params[3]]

        cursor.execute.side_effect = execute
        connection = MagicMock()
        connection.__enter__.return_value.cursor.return_value.__enter__.return_value = cursor
        with patch.object(data, "get_connection", return_value=connection), \
             patch.object(data, "list_bank_accounts", return_value=[account()]), \
             patch.object(data, "list_recurrences", return_value=[]):
            result = data.bank_cashflow_month(7, 1, "2027-01", today_value=date(2027, 1, 31))
        cursor.execute.assert_called_once()
        self.assertEqual([r["id"] for r in result["rows"]], [1])
        self.assertEqual(result["current_balance"], D("900"))
        self.assertEqual(result["end_balance"], D("900"))

    def test_same_day_movements_have_deterministic_order(self):
        rows = [movement(8, "2027-01-15", "400"),
                movement(9, "2027-01-15", "200", "income"),
                movement(3, "2027-01-15", "100")]
        for shuffled in (rows, list(reversed(rows))):
            with self.subTest(order=[r["id"] for r in shuffled]), readings(shuffled):
                result = data.bank_cashflow_month(7, 1, "2027-01", today_value=date(2027, 1, 31))
            self.assertEqual([r["id"] for r in result["rows"]], [9, 3, 8])
            self.assertEqual([r["running_balance"] for r in result["rows"]],
                             [D("1200"), D("1100"), D("700")])
            self.assertEqual(result["maximum_balance"], D("1200"))
            self.assertEqual(result["minimum_balance"], D("700"))

    def test_credit_line_over_limit_has_negative_available_credit(self):
        selected = account(method_type="credit_line", opening_balance=D("900"), credit_limit=D("1000"))
        rows = [movement(1, "2027-01-05", "200"),
                movement(2, "2027-01-20", "50", "income", status="planned")]
        with readings(rows, selected_account=selected):
            month = data.bank_cashflow_month(7, 1, "2027-01", today_value=date(2027, 1, 10))
            year = data.bank_cashflow_year_summary(7, 1, 2027, today_value=date(2027, 1, 10))
        self.assertEqual(month["current_balance"], D("1100"))
        self.assertEqual(month["current_available_credit"], D("-100"))
        self.assertEqual(month["minimum_available_credit"], D("-100"))
        self.assertEqual(month["end_balance"], D("1050"))
        self.assertEqual(month["end_available_credit"], D("-50"))
        self.assertEqual(year["months"][0]["minimum_available_credit"], D("-100"))
        self.assertEqual(year["months"][0]["end_available_credit"], D("-50"))

    def test_budget_excluded_movement_still_affects_account(self):
        with readings([movement(1, "2027-01-05", "250", budget_excluded=True)]):
            result = data.bank_cashflow_month(7, 1, "2027-01", today_value=date(2027, 1, 31))
        self.assertEqual(result["current_balance"], D("750"))
        self.assertEqual(result["end_balance"], D("750"))
        self.assertTrue(result["rows"][0]["budget_excluded"])


class AccountArchitectureTests(unittest.TestCase):
    def test_module_import_without_database_or_legacy_module(self):
        # Processus neuf : aucun module déjà importé ne peut masquer un cycle.
        script = """
import importlib.abc
import sys
class BlockLegacyImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'db', 'finances_data', 'psycopg', 'nicegui'}:
            raise AssertionError('Import interdit : ' + fullname)
sys.meta_path.insert(0, BlockLegacyImports())
import finances_account_data
assert callable(finances_account_data.bank_cashflow_month)
assert callable(finances_account_data.bank_cashflow_year_summary)
"""
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_account_list_resolves_current_payment_reader(self):
        # Deux remplacements successifs après l'import doivent être visibles.
        for identifier in (41, 42):
            with self.subTest(identifier=identifier):
                rows = [account(id=identifier), account(id=99, method_type="credit_card")]
                with patch.object(data, "list_payment_methods", return_value=rows) as reader:
                    result = data.list_bank_accounts(7, include_inactive=True)
                self.assertEqual([row["id"] for row in result], [identifier])
                reader.assert_called_once_with(7, include_inactive=True)

    def test_cashflow_delegates_resolve_current_dependencies(self):
        # Le chargement isolé avec patch.dict restaure sys.modules ensuite.
        # Observer le module effectivement utilisé par la façade historique.
        extracted = data._account_data
        for name, period in (("bank_cashflow_month", "2027-01"),
                             ("bank_cashflow_year_summary", 2027)):
            for replacement in (1, 2):
                with self.subTest(entry=name, replacement=replacement):
                    with patch.object(data, "list_bank_accounts") as accounts, \
                         patch.object(data, "list_transactions") as transactions, \
                         patch.object(data, "list_recurrences") as recurrences, \
                         patch.object(data, "_projection_row") as projection, \
                         patch.object(extracted, name, return_value={"delegated": True}) as delegate:
                        result = getattr(data, name)(7, 1, period, today_value=date(2027, 1, 10))
                        delegate.assert_called_once_with(
                            7, 1, period, today_value=date(2027, 1, 10),
                            list_bank_accounts=accounts, list_transactions=transactions,
                            list_recurrences=recurrences, _projection_row=projection,
                        )
                        self.assertEqual(result, {"delegated": True})


if __name__ == "__main__":
    unittest.main()
