from __future__ import annotations

from datetime import date


def set_transaction_reconciliation(
    user_id,
    transaction_id,
    reconciliation_status,
    reconciliation_date=None,
    *,
    RECONCILIATION_STATUSES,
    refresh_reconciliation_session_totals,
    get_connection,
):
    if reconciliation_status not in RECONCILIATION_STATUSES:
        raise ValueError("Statut de conciliation invalide.")

    parsed_date = (
        reconciliation_date
        if isinstance(reconciliation_date, date)
        else (
            date.fromisoformat(str(reconciliation_date))
            if reconciliation_date
            else None
        )
    )
    if reconciliation_status == "unreconciled":
        parsed_date = None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT reconciliation_session_id
                FROM finance_transactions
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
                """,
                (transaction_id, user_id),
            )
            current = cur.fetchone()
            if not current:
                raise ValueError("Transaction introuvable.")

            session_id = current["reconciliation_session_id"]

            if reconciliation_status == "unreconciled" and session_id:
                cur.execute(
                    """
                    UPDATE finance_reconciliation_session_transactions
                    SET is_active = FALSE,
                        removed_at = NOW()
                    WHERE session_id = %s
                      AND transaction_id = %s
                      AND is_active = TRUE;
                    """,
                    (session_id, transaction_id),
                )

            cur.execute(
                """
                UPDATE finance_transactions
                SET reconciliation_status = %s,
                    reconciliation_date = %s,
                    reconciliation_session_id = %s,
                    updated_at = NOW()
                WHERE id = %s AND user_id = %s;
                """,
                (
                    reconciliation_status,
                    parsed_date,
                    (
                        None
                        if reconciliation_status == "unreconciled"
                        else session_id
                    ),
                    transaction_id,
                    user_id,
                ),
            )

            if session_id:
                refresh_reconciliation_session_totals(
                    cur,
                    session_id,
                )

            conn.commit()
