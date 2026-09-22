"""Régression V1.14.2 : l'avis Portail reste enregistré pour un statut Confirmée."""
from __future__ import annotations

from decimal import Decimal
import unittest

import finances_card_payments_writes as card_writes
import finances_transactions_writes as transaction_writes


class FakeCursor:
    def __init__(self):
        self.calls = []
        self.rowcount = 1
        self.last_sql = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.last_sql = " ".join(str(sql).split())
        self.calls.append((self.last_sql, params))

    def fetchone(self):
        if "SELECT reconciliation_status, linked_transfer_id" in self.last_sql:
            return {"reconciliation_status": "unreconciled", "linked_transfer_id": None}
        if "INSERT INTO finance_linked_transfers" in self.last_sql:
            return {"id": 88}
        if "INSERT INTO finance_transactions" in self.last_sql and "RETURNING id" in self.last_sql:
            return {"id": 77}
        if "SELECT id FROM finance_linked_transfers" in self.last_sql:
            return {"id": 88}
        raise AssertionError(f"fetchone inattendu après : {self.last_sql}")

    def fetchall(self):
        if "SELECT reconciliation_status FROM finance_transactions" in self.last_sql:
            return []
        if "SELECT id, linked_transfer_role FROM finance_transactions" in self.last_sql:
            return []
        return []


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"))


def text(value, _label, _max_length, required=False):
    result = str(value or "").strip()
    if required and not result:
        raise ValueError("champ requis")
    return result


def reminder_time(value):
    return str(value or "09:00")[:5]


class ReminderPersistenceTests(unittest.TestCase):
    def test_confirmed_transaction_update_keeps_portal_reminder(self):
        conn = FakeConnection()
        transaction_writes.save_transaction(
            user_id=7,
            transaction_id=42,
            transaction_date="2026-09-25",
            transaction_type="expense",
            amount="987",
            description="important",
            category_id=3,
            tag_ids=[],
            note="",
            status="confirmed",
            payment_method_id=None,
            reconciliation_status="unreconciled",
            reconciliation_date=None,
            budget_excluded=False,
            bank_programmed=True,
            reminder_enabled=True,
            reminder_time="09:00",
            TRANSACTION_TYPES={"expense": "Dépense", "income": "Revenu"},
            TRANSACTION_STATUSES={"planned": "À confirmer", "confirmed": "Confirmée"},
            RECONCILIATION_STATUSES={"unreconciled": "À concilier", "reconciled": "Conciliée"},
            normalize_reminder_time=reminder_time,
            money=money,
            text=text,
            get_connection=lambda: conn,
            validate_links=lambda *_args: [],
            validate_payment_method=lambda *_args: None,
        )
        update = next(params for sql, params in conn.cursor_obj.calls
                      if sql.startswith("UPDATE finance_transactions SET"))
        self.assertFalse(update[-5])
        self.assertTrue(update[-4])
        self.assertEqual(update[-3], "09:00")
        self.assertEqual(conn.commits, 1)

    def test_confirmed_transaction_insert_keeps_portal_reminder(self):
        conn = FakeConnection()
        transaction_writes.save_transaction(
            user_id=7,
            transaction_date="2026-09-25",
            transaction_type="expense",
            amount="987",
            description="important",
            status="confirmed",
            bank_programmed=True,
            reminder_enabled=True,
            reminder_time="09:00",
            TRANSACTION_TYPES={"expense": "Dépense", "income": "Revenu"},
            TRANSACTION_STATUSES={"planned": "À confirmer", "confirmed": "Confirmée"},
            RECONCILIATION_STATUSES={"unreconciled": "À concilier", "reconciled": "Conciliée"},
            normalize_reminder_time=reminder_time,
            money=money,
            text=text,
            get_connection=lambda: conn,
            validate_links=lambda *_args: [],
            validate_payment_method=lambda *_args: None,
        )
        insert = next(params for sql, params in conn.cursor_obj.calls
                      if sql.startswith("INSERT INTO finance_transactions") and "RETURNING id" in sql)
        self.assertFalse(insert[-3])
        self.assertTrue(insert[-2])
        self.assertEqual(insert[-1], "09:00")

    def test_confirmed_card_payment_keeps_source_portal_reminder(self):
        conn = FakeConnection()
        card_writes.save_card_payment_transfer(
            user_id=7,
            source_payment_method_id=1,
            destination_payment_method_id=2,
            amount="100",
            source_date="2026-09-25",
            destination_date="2026-09-25",
            description="Paiement Visa",
            status="confirmed",
            bank_programmed=True,
            reminder_enabled=True,
            reminder_time="08:30",
            TRANSACTION_STATUSES={"planned": "À confirmer", "confirmed": "Confirmée"},
            money=money,
            text=text,
            normalize_reminder_time=reminder_time,
            get_connection=lambda: conn,
            validate_card_payment_methods=lambda *_args: (
                {"id": 1, "name": "Banque"},
                {"id": 2, "name": "Visa"},
            ),
        )
        linked = next(params for sql, params in conn.cursor_obj.calls
                      if sql.startswith("INSERT INTO finance_linked_transfers"))
        self.assertFalse(linked[-3])
        self.assertTrue(linked[-2])
        source = next(params for sql, params in conn.cursor_obj.calls
                      if sql.startswith("INSERT INTO finance_transactions") and params[-1] == "source")
        destination = next(params for sql, params in conn.cursor_obj.calls
                           if sql.startswith("INSERT INTO finance_transactions") and params[-1] == "destination")
        self.assertTrue(source[-4])
        self.assertFalse(destination[-4])


if __name__ == "__main__":
    unittest.main()
