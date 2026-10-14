from __future__ import annotations


def mark_transaction_programmed_and_dismiss_reminder(
    user_id,
    transaction_id,
    *,
    get_connection,
):
    """Marque une transaction prévue comme programmée auprès de la banque.

    L'opération ne confirme pas la transaction et ne la concilie pas.
    Le rappel est désactivé immédiatement. Pour un paiement de carte lié,
    le même état est également conservé dans finance_linked_transfers.
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

            if row.get("status") != "planned":
                raise ValueError(
                    "Seule une transaction encore prévue peut être marquée "
                    "comme programmée."
                )

            linked_transfer_id = row.get("linked_transfer_id")
            linked_transfer_role = row.get("linked_transfer_role")

            if linked_transfer_id:
                if linked_transfer_role not in (None, "source"):
                    raise ValueError(
                        "Le côté technique d’un paiement lié ne peut pas "
                        "être programmé depuis le Portail."
                    )

                cur.execute(
                    """
                    UPDATE finance_linked_transfers
                    SET
                        bank_programmed = TRUE,
                        reminder_enabled = FALSE,
                        updated_at = NOW()
                    WHERE id = %s
                      AND user_id = %s;
                    """,
                    (linked_transfer_id, user_id),
                )
                if cur.rowcount == 0:
                    raise ValueError("Paiement lié introuvable.")

            cur.execute(
                """
                UPDATE finance_transactions
                SET
                    bank_programmed = TRUE,
                    reminder_enabled = FALSE,
                    updated_at = NOW()
                WHERE id = %s
                  AND user_id = %s
                  AND status = 'planned';
                """,
                (transaction_id, user_id),
            )
            if cur.rowcount == 0:
                raise ValueError("Transaction introuvable ou déjà confirmée.")

            conn.commit()

    return True
