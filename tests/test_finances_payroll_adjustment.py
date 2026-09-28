from __future__ import annotations

from datetime import date
from decimal import Decimal as D
import unittest

from finances_budget_payroll import (
    confirmed_primary_income_adjustment,
    payroll_adjustment_from_transactions,
)


class PayrollAdjustmentTests(unittest.TestCase):
    def test_higher_confirmed_pay_increases_available(self):
        rows = [
            dict(
                id=10,
                recurrence_id=7,
                occurrence_date=date(2026, 9, 17),
                transaction_date=date(2026, 9, 17),
                transaction_type="income",
                status="confirmed",
                amount=D("2450.58"),
            )
        ]

        result = payroll_adjustment_from_transactions(
            rows,
            recurrence_id=7,
            expected_per_pay=D("2400.00"),
            month=date(2026, 9, 1),
            month_end=date(2026, 9, 30),
        )

        self.assertEqual(result["realized_pay_count"], 1)
        self.assertEqual(result["actual_pay_total"], D("2450.58"))
        self.assertEqual(
            result["expected_realized_pay_total"],
            D("2400.00"),
        )
        self.assertEqual(
            result["pay_actual_adjustment"],
            D("50.58"),
        )

    def test_lower_confirmed_pay_reduces_available(self):
        result = payroll_adjustment_from_transactions(
            [
                dict(
                    id=11,
                    recurrence_id=7,
                    occurrence_date=date(2026, 9, 3),
                    transaction_type="income",
                    status="confirmed",
                    amount=D("2325.00"),
                ),
                dict(
                    id=12,
                    recurrence_id=7,
                    occurrence_date=date(2026, 9, 17),
                    transaction_type="income",
                    status="confirmed",
                    amount=D("2400.00"),
                ),
            ],
            recurrence_id=7,
            expected_per_pay=D("2400.00"),
            month=date(2026, 9, 1),
            month_end=date(2026, 9, 30),
        )

        self.assertEqual(result["realized_pay_count"], 2)
        self.assertEqual(
            result["pay_actual_adjustment"],
            D("-75.00"),
        )

    def test_other_income_and_other_recurrence_do_not_adjust_pay(self):
        rows = [
            dict(
                id=1,
                recurrence_id=99,
                occurrence_date=date(2026, 9, 17),
                transaction_type="income",
                status="confirmed",
                amount=D("9000"),
            ),
            dict(
                id=2,
                recurrence_id=7,
                occurrence_date=date(2026, 9, 17),
                transaction_type="expense",
                status="confirmed",
                amount=D("10"),
            ),
        ]

        result = payroll_adjustment_from_transactions(
            rows,
            recurrence_id=7,
            expected_per_pay=D("2400"),
            month=date(2026, 9, 1),
            month_end=date(2026, 9, 30),
        )

        self.assertEqual(result["realized_pay_count"], 0)
        self.assertEqual(result["pay_actual_adjustment"], D("0.00"))

    def test_duplicate_occurrence_uses_latest_transaction_id(self):
        rows = [
            dict(
                id=10,
                recurrence_id=7,
                occurrence_date=date(2026, 9, 17),
                transaction_type="income",
                status="confirmed",
                amount=D("2400"),
            ),
            dict(
                id=11,
                recurrence_id=7,
                occurrence_date=date(2026, 9, 17),
                transaction_type="income",
                status="confirmed",
                amount=D("2450"),
            ),
        ]

        result = payroll_adjustment_from_transactions(
            rows,
            recurrence_id=7,
            expected_per_pay=D("2400"),
            month=date(2026, 9, 1),
            month_end=date(2026, 9, 30),
        )

        self.assertEqual(result["realized_pay_count"], 1)
        self.assertEqual(result["actual_pay_total"], D("2450.00"))
        self.assertEqual(result["pay_actual_adjustment"], D("50.00"))

    def test_reader_requests_only_confirmed_income_for_month(self):
        captured = {}

        def reader(user_id, **kwargs):
            captured["user_id"] = user_id
            captured.update(kwargs)
            return []

        result = confirmed_primary_income_adjustment(
            42,
            month=date(2026, 9, 1),
            month_end=date(2026, 9, 30),
            recurrence_id=7,
            expected_per_pay=D("2400"),
            list_transactions=reader,
        )

        self.assertEqual(result["pay_actual_adjustment"], D("0.00"))
        self.assertEqual(captured["user_id"], 42)
        self.assertEqual(captured["transaction_type"], "income")
        self.assertEqual(captured["status"], "confirmed")
        self.assertEqual(captured["start_date"], date(2026, 9, 1))
        self.assertEqual(captured["end_date"], date(2026, 9, 30))
        self.assertFalse(captured["include_linked_transfer_destinations"])


if __name__ == "__main__":
    unittest.main()
