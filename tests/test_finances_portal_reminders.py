from __future__ import annotations

import sys
import unittest
from datetime import date
from types import ModuleType
from unittest.mock import patch

import finances_portal


TODAY = date(2026, 9, 22)
HORIZON = date(2026, 9, 25)
YESTERDAY = date(2026, 9, 21)


def transaction_reader(*, future=None, overdue=None):
    future = list(future or [])
    overdue = list(overdue or [])
    calls = []

    def read(user_id, **kwargs):
        calls.append((user_id, kwargs))
        if kwargs.get("start_date") == TODAY:
            return future
        if kwargs.get("status") == "planned" and kwargs.get("end_date") == YESTERDAY:
            return overdue
        raise AssertionError(f"Lecture inattendue : {kwargs}")

    read.calls = calls
    return read


class FinancePortalReminderTests(unittest.TestCase):
    def test_default_readers_are_loaded_from_finances_data_not_db(self):
        data_stub = ModuleType("finances_data")

        def list_transactions(_user_id, **kwargs):
            if kwargs.get("start_date") == TODAY:
                return [
                    {
                        "id": 99,
                        "transaction_date": HORIZON,
                        "description": "Raccord réel",
                        "status": "confirmed",
                        "reminder_enabled": True,
                    }
                ]
            if kwargs.get("status") == "planned":
                return []
            raise AssertionError(f"Lecture inattendue : {kwargs}")

        data_stub.list_transactions = list_transactions
        data_stub.list_recurrences = lambda _user_id: []
        db_stub = ModuleType("db")

        with patch.dict(
            sys.modules,
            {"finances_data": data_stub, "db": db_stub},
        ):
            rows = finances_portal.collect_finance_portal_reminders(
                1,
                today_value=TODAY,
            )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["description"], "Raccord réel")

    def test_confirmed_transaction_appears_three_days_before_due_date(self):
        reader = transaction_reader(
            future=[
                {
                    "id": 10,
                    "transaction_date": HORIZON,
                    "description": "Paiement Visa",
                    "amount": "425.00",
                    "status": "confirmed",
                    "reminder_enabled": True,
                    "payment_method_name": "Visa",
                }
            ]
        )

        rows = finances_portal.collect_finance_portal_reminders(
            1,
            list_transactions_fn=reader,
            list_recurrences_fn=lambda _user_id: [],
            today_value=TODAY,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["relative_text"], "Prévu dans 3 jours")
        self.assertEqual(rows[0]["amount_text"], "425,00 $")
        self.assertEqual(len(reader.calls), 2)
        future_call = reader.calls[0][1]
        self.assertEqual(future_call["start_date"], TODAY)
        self.assertEqual(future_call["end_date"], HORIZON)
        self.assertNotIn("status", future_call)
        self.assertFalse(future_call["include_linked_transfer_destinations"])

    def test_planned_future_transaction_still_appears(self):
        reader = transaction_reader(
            future=[
                {
                    "id": 11,
                    "transaction_date": date(2026, 9, 24),
                    "description": "Assurance",
                    "status": "planned",
                    "reminder_enabled": True,
                }
            ]
        )
        rows = finances_portal.collect_finance_portal_reminders(
            1,
            list_transactions_fn=reader,
            list_recurrences_fn=lambda _user_id: [],
            today_value=TODAY,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["relative_text"], "Prévu dans 2 jours")

    def test_unmarked_transaction_is_not_shown(self):
        reader = transaction_reader(
            future=[
                {
                    "id": 1,
                    "transaction_date": date(2026, 9, 23),
                    "description": "Sans rappel",
                    "status": "confirmed",
                    "reminder_enabled": False,
                }
            ]
        )
        rows = finances_portal.collect_finance_portal_reminders(
            1,
            list_transactions_fn=reader,
            list_recurrences_fn=lambda _user_id: [],
            today_value=TODAY,
        )
        self.assertEqual(rows, [])

    def test_overdue_planned_transaction_stays_visible(self):
        reader = transaction_reader(
            overdue=[
                {
                    "id": 1,
                    "transaction_date": date(2026, 9, 20),
                    "description": "Paiement en retard",
                    "status": "planned",
                    "reminder_enabled": True,
                }
            ]
        )
        rows = finances_portal.collect_finance_portal_reminders(
            1,
            list_transactions_fn=reader,
            list_recurrences_fn=lambda _user_id: [],
            today_value=TODAY,
        )
        self.assertEqual(rows[0]["relative_text"], "En retard de 2 jours")

    def test_confirmed_overdue_transaction_is_not_shown(self):
        # Défense supplémentaire : même si un lecteur simulé renvoie une ancienne
        # transaction confirmée dans le lot des retards, elle ne doit pas revenir.
        reader = transaction_reader(
            overdue=[
                {
                    "id": 2,
                    "transaction_date": date(2026, 9, 20),
                    "description": "Déjà réglée",
                    "status": "confirmed",
                    "reminder_enabled": True,
                }
            ]
        )
        rows = finances_portal.collect_finance_portal_reminders(
            1,
            list_transactions_fn=reader,
            list_recurrences_fn=lambda _user_id: [],
            today_value=TODAY,
        )
        self.assertEqual(rows, [])

    def test_future_recurrence_is_shown_before_materialization(self):
        reader = transaction_reader()
        rows = finances_portal.collect_finance_portal_reminders(
            1,
            list_transactions_fn=reader,
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
            today_value=TODAY,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "recurrence")
        self.assertEqual(rows[0]["relative_text"], "Prévu dans 2 jours")

    def test_confirmed_materialized_recurrence_is_not_duplicated(self):
        tx = {
            "id": 80,
            "transaction_date": date(2026, 9, 24),
            "description": "Internet",
            "amount": "70",
            "status": "confirmed",
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
            list_transactions_fn=transaction_reader(future=[tx]),
            list_recurrences_fn=lambda _user_id: [recurrence],
            today_value=TODAY,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "transaction")

    def test_items_beyond_three_days_are_not_shown(self):
        # Le vrai lecteur SQL ne renverrait pas cette ligne grâce à end_date;
        # le garde Python protège aussi la fonction si un lecteur injecté déborde.
        reader = transaction_reader(
            future=[
                {
                    "id": 1,
                    "transaction_date": date(2026, 9, 26),
                    "description": "Trop loin",
                    "status": "confirmed",
                    "reminder_enabled": True,
                }
            ]
        )
        rows = finances_portal.collect_finance_portal_reminders(
            1,
            list_transactions_fn=reader,
            list_recurrences_fn=lambda _user_id: [],
            today_value=TODAY,
        )
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
