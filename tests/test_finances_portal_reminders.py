from __future__ import annotations

import unittest
from datetime import date

import finances_portal


class FinancePortalReminderTests(unittest.TestCase):
    def test_transaction_appears_three_days_before_due_date(self):
        def transactions(*args, **kwargs):
            self.assertEqual(kwargs["status"], "planned")
            self.assertEqual(kwargs["end_date"], date(2026, 9, 25))
            self.assertFalse(kwargs["include_linked_transfer_destinations"])
            return [
                {
                    "id": 10,
                    "transaction_date": date(2026, 9, 25),
                    "description": "Paiement Visa",
                    "amount": "425.00",
                    "status": "planned",
                    "reminder_enabled": True,
                    "payment_method_name": "Visa",
                }
            ]

        rows = finances_portal.collect_finance_portal_reminders(
            1,
            list_transactions_fn=transactions,
            list_recurrences_fn=lambda _user_id: [],
            today_value=date(2026, 9, 22),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["relative_text"], "Prévu dans 3 jours")
        self.assertEqual(rows[0]["amount_text"], "425,00 $")

    def test_unmarked_transaction_is_not_shown(self):
        rows = finances_portal.collect_finance_portal_reminders(
            1,
            list_transactions_fn=lambda *a, **k: [
                {
                    "id": 1,
                    "transaction_date": date(2026, 9, 23),
                    "description": "Sans rappel",
                    "reminder_enabled": False,
                }
            ],
            list_recurrences_fn=lambda _user_id: [],
            today_value=date(2026, 9, 22),
        )
        self.assertEqual(rows, [])

    def test_overdue_planned_transaction_stays_visible(self):
        rows = finances_portal.collect_finance_portal_reminders(
            1,
            list_transactions_fn=lambda *a, **k: [
                {
                    "id": 1,
                    "transaction_date": date(2026, 9, 20),
                    "description": "Paiement en retard",
                    "reminder_enabled": True,
                }
            ],
            list_recurrences_fn=lambda _user_id: [],
            today_value=date(2026, 9, 22),
        )
        self.assertEqual(rows[0]["relative_text"], "En retard de 2 jours")

    def test_future_recurrence_is_shown_before_materialization(self):
        rows = finances_portal.collect_finance_portal_reminders(
            1,
            list_transactions_fn=lambda *a, **k: [],
            list_recurrences_fn=lambda _user_id: [
                {
                    "id": 7,
                    "description": "Assurance",
                    "amount": "81.40",
                    "next_date": date(2026, 9, 24),
                    "is_active": True,
                    "reminder_enabled": True,
                }
            ],
            today_value=date(2026, 9, 22),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "recurrence")
        self.assertEqual(rows[0]["relative_text"], "Prévu dans 2 jours")

    def test_materialized_recurrence_is_not_duplicated(self):
        tx = {
            "id": 80,
            "transaction_date": date(2026, 9, 24),
            "description": "Internet",
            "amount": "70",
            "reminder_enabled": True,
            "recurrence_id": 4,
        }
        recurrence = {
            "id": 4,
            "description": "Internet",
            "amount": "70",
            "next_date": date(2026, 9, 24),
            "is_active": True,
            "reminder_enabled": True,
        }
        rows = finances_portal.collect_finance_portal_reminders(
            1,
            list_transactions_fn=lambda *a, **k: [tx],
            list_recurrences_fn=lambda _user_id: [recurrence],
            today_value=date(2026, 9, 22),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "transaction")

    def test_items_beyond_three_days_are_not_shown(self):
        rows = finances_portal.collect_finance_portal_reminders(
            1,
            list_transactions_fn=lambda *a, **k: [
                {
                    "id": 1,
                    "transaction_date": date(2026, 9, 26),
                    "description": "Trop loin",
                    "reminder_enabled": True,
                }
            ],
            list_recurrences_fn=lambda _user_id: [],
            today_value=date(2026, 9, 22),
        )
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
