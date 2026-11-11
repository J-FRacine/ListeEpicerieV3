"""Matérialisation contrôlée d'une occurrence projetée de récurrence."""
from __future__ import annotations

from datetime import date
from typing import Any


def _as_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError) as error:
        raise ValueError("Date d’occurrence invalide.") from error


def materialize_projected_occurrence(
    user_id,
    recurrence_id,
    occurrence_date,
    *,
    get_connection,
):
    occurrence = _as_date(occurrence_date)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM finance_recurrences
                WHERE id = %s
                  AND user_id = %s
                FOR UPDATE;
                """,
                (int(recurrence_id), int(user_id)),
            )
            recurrence = cur.fetchone()
            if not recurrence:
                raise ValueError("Récurrence introuvable.")

            start_date = _as_date(recurrence["start_date"])
            end_date = (
                _as_date(recurrence["end_date"])
                if recurrence.get("end_date")
                else None
            )
            if occurrence < start_date:
                raise ValueError(
                    "Cette occurrence précède le début de la récurrence."
                )
            if end_date and occurrence > end_date:
                raise ValueError(
                    "Cette occurrence dépasse la fin de la récurrence."
                )

            cur.execute(
                """
                SELECT id
                FROM finance_transactions
                WHERE user_id = %s
                  AND recurrence_id = %s
                  AND occurrence_date = %s
                FOR UPDATE;
                """,
                (int(user_id), int(recurrence_id), occurrence),
            )
            existing = cur.fetchone()
            if existing:
                conn.commit()
                return int(existing["id"])

            cur.execute(
                """
                INSERT INTO finance_transactions (
                    user_id,
                    transaction_date,
                    transaction_type,
                    amount,
                    description,
                    category_id,
                    payment_method_id,
                    note,
                    status,
                    reconciliation_status,
                    recurrence_id,
                    occurrence_date,
                    budget_excluded,
                    bank_programmed,
                    reminder_enabled,
                    reminder_time
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, 'planned', 'unreconciled',
                    %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (recurrence_id, occurrence_date)
                DO NOTHING
                RETURNING id;
                """,
                (
                    int(user_id),
                    occurrence,
                    recurrence["transaction_type"],
                    recurrence["amount"],
                    recurrence["description"],
                    recurrence.get("category_id"),
                    recurrence.get("payment_method_id"),
                    recurrence.get("note"),
                    int(recurrence_id),
                    occurrence,
                    bool(recurrence.get("budget_excluded")),
                    bool(recurrence.get("bank_programmed")),
                    bool(recurrence.get("reminder_enabled")),
                    recurrence.get("reminder_time") or "09:00",
                ),
            )
            inserted = cur.fetchone()

            if inserted:
                transaction_id = int(inserted["id"])
                cur.execute(
                    """
                    INSERT INTO finance_transaction_tags (
                        transaction_id,
                        tag_id
                    )
                    SELECT %s, tag_id
                    FROM finance_recurrence_tags
                    WHERE recurrence_id = %s
                    ON CONFLICT DO NOTHING;
                    """,
                    (transaction_id, int(recurrence_id)),
                )
            else:
                cur.execute(
                    """
                    SELECT id
                    FROM finance_transactions
                    WHERE user_id = %s
                      AND recurrence_id = %s
                      AND occurrence_date = %s;
                    """,
                    (int(user_id), int(recurrence_id), occurrence),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError(
                        "L’occurrence n’a pas pu être créée."
                    )
                transaction_id = int(row["id"])

            conn.commit()
            return transaction_id
