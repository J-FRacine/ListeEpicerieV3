from __future__ import annotations


def mark_transaction_done_from_portal(
    user_id,
    transaction_id,
    *,
    get_connection,
):
    """Traite l'action « Fait » d'un rappel Finances du Portail.

    - Transaction prévue : marque « Programmée à la banque » et désactive le
      rappel, sans confirmer ni concilier.
    - Transaction déjà confirmée : désactive seulement le rappel.
    - Paiement de carte lié : synchronise également l'état du transfert.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    status,
                    linked_transfer_id,
                    linked_transfer_role
                FROM finance_transactions
                WHERE id = %s
                  AND user_id = %s
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
                        "Le côté technique d’un paiement lié ne peut pas "
                        "être traité depuis le Portail."
                    )

                cur.execute(
                    """
                    UPDATE finance_linked_transfers
                    SET
                        bank_programmed = CASE
                            WHEN %s THEN TRUE
                            ELSE bank_programmed
                        END,
                        reminder_enabled = FALSE,
                        updated_at = NOW()
                    WHERE id = %s
                      AND user_id = %s;
                    """,
                    (
                        mark_programmed,
                        linked_transfer_id,
                        user_id,
                    ),
                )
                if cur.rowcount == 0:
                    raise ValueError("Paiement lié introuvable.")

            cur.execute(
                """
                UPDATE finance_transactions
                SET
                    bank_programmed = CASE
                        WHEN status = 'planned' THEN TRUE
                        ELSE bank_programmed
                    END,
                    reminder_enabled = FALSE,
                    updated_at = NOW()
                WHERE id = %s
                  AND user_id = %s;
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
