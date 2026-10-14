from __future__ import annotations

from datetime import date

from finances_calculations import next_date as _next_date


def _as_date(value):
    if isinstance(value, date):
        return value
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError) as error:
        raise ValueError("Date d’échéance invalide.") from error


def mark_transaction_done_from_portal(user_id, transaction_id, *, get_connection):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, status, linked_transfer_id, linked_transfer_role
                FROM finance_transactions
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
                """,
                (transaction_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Transaction introuvable.")

            status = str(row.get("status") or "")
            if status not in {"planned", "confirmed"}:
                raise ValueError("Statut de transaction non pris en charge.")

            linked_transfer_id = row.get("linked_transfer_id")
            linked_transfer_role = row.get("linked_transfer_role")
            mark_programmed = status == "planned"

            if linked_transfer_id:
                if linked_transfer_role not in (None, "source"):
                    raise ValueError(
                        "Le côté technique d’un paiement lié ne peut pas être traité depuis le Portail."
                    )
                cur.execute(
                    """
                    UPDATE finance_linked_transfers
                    SET bank_programmed = CASE WHEN %s THEN TRUE ELSE bank_programmed END,
                        reminder_enabled = FALSE,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s;
                    """,
                    (mark_programmed, linked_transfer_id, user_id),
                )

            cur.execute(
                """
                UPDATE finance_transactions
                SET bank_programmed = CASE
                        WHEN status = 'planned' THEN TRUE
                        ELSE bank_programmed
                    END,
                    reminder_enabled = FALSE,
                    updated_at = NOW()
                WHERE id = %s AND user_id = %s;
                """,
                (transaction_id, user_id),
            )
            if cur.rowcount == 0:
                raise ValueError("Transaction introuvable.")
            conn.commit()

    return {
        "transaction_id": int(transaction_id),
        "bank_programmed": mark_programmed,
        "reminder_disabled": True,
    }


def mark_recurrence_occurrence_programmed(
    user_id,
    recurrence_id,
    due_date,
    *,
    get_connection,
):
    """Crée seulement l'occurrence visée comme transaction prévue programmée.

    La récurrence conserve son rappel pour les occurrences suivantes.
    """
    occurrence = _as_date(due_date)
    if occurrence is None:
        raise ValueError("Date d’échéance introuvable.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM finance_recurrences
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
                """,
                (recurrence_id, user_id),
            )
            recurrence = cur.fetchone()
            if not recurrence:
                raise ValueError("Récurrence introuvable.")
            if not bool(recurrence.get("is_active", True)):
                raise ValueError("Cette récurrence n’est plus active.")
            if not bool(recurrence.get("reminder_enabled")):
                raise ValueError("Le rappel de cette récurrence est désactivé.")

            current_next = _as_date(recurrence.get("next_date")) or _as_date(
                recurrence.get("start_date")
            )

            if current_next != occurrence:
                cur.execute(
                    """
                    SELECT id, status
                    FROM finance_transactions
                    WHERE user_id = %s
                      AND recurrence_id = %s
                      AND occurrence_date = %s
                    FOR UPDATE;
                    """,
                    (user_id, recurrence_id, occurrence),
                )
                existing = cur.fetchone()
                if not existing:
                    raise ValueError(
                        "Cette échéance a changé. Rechargez le Portail."
                    )
                cur.execute(
                    """
                    UPDATE finance_transactions
                    SET bank_programmed = CASE
                            WHEN status = 'planned' THEN TRUE
                            ELSE bank_programmed
                        END,
                        reminder_enabled = FALSE,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s;
                    """,
                    (existing["id"], user_id),
                )
                conn.commit()
                return {
                    "transaction_id": int(existing["id"]),
                    "bank_programmed": str(existing.get("status") or "") == "planned",
                    "reminder_disabled": True,
                }

            end_date = _as_date(recurrence.get("end_date"))
            if end_date and occurrence > end_date:
                raise ValueError("Cette récurrence est terminée.")

            cur.execute(
                """
                INSERT INTO finance_transactions (
                    user_id, transaction_date, transaction_type, amount,
                    description, category_id, payment_method_id, note,
                    status, reconciliation_status, recurrence_id,
                    occurrence_date, budget_excluded, bank_programmed,
                    reminder_enabled, reminder_time
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    'planned', 'unreconciled', %s, %s, %s,
                    TRUE, FALSE, %s
                )
                ON CONFLICT (recurrence_id, occurrence_date)
                DO UPDATE SET
                    bank_programmed = CASE
                        WHEN finance_transactions.status = 'planned'
                        THEN TRUE
                        ELSE finance_transactions.bank_programmed
                    END,
                    reminder_enabled = FALSE,
                    updated_at = NOW()
                RETURNING id, status;
                """,
                (
                    user_id,
                    occurrence,
                    recurrence["transaction_type"],
                    recurrence["amount"],
                    recurrence["description"],
                    recurrence.get("category_id"),
                    recurrence.get("payment_method_id"),
                    recurrence.get("note"),
                    recurrence_id,
                    occurrence,
                    bool(recurrence.get("budget_excluded")),
                    recurrence.get("reminder_time") or "09:00",
                ),
            )
            transaction = cur.fetchone()
            transaction_id = int(transaction["id"])

            cur.execute(
                """
                SELECT tag_id
                FROM finance_recurrence_tags
                WHERE recurrence_id = %s;
                """,
                (recurrence_id,),
            )
            for tag in cur.fetchall() or []:
                cur.execute(
                    """
                    INSERT INTO finance_transaction_tags (transaction_id, tag_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (transaction_id, tag["tag_id"]),
                )

            next_occurrence = _next_date(
                occurrence,
                recurrence["frequency_unit"],
                recurrence["frequency_interval"],
            )
            still_active = not (end_date and next_occurrence > end_date)

            cur.execute(
                """
                UPDATE finance_recurrences
                SET next_date = %s,
                    is_active = %s,
                    updated_at = NOW()
                WHERE id = %s AND user_id = %s;
                """,
                (next_occurrence, still_active, recurrence_id, user_id),
            )
            conn.commit()

    return {
        "transaction_id": transaction_id,
        "bank_programmed": str(transaction.get("status") or "") == "planned",
        "reminder_disabled": True,
    }
