from __future__ import annotations


def get_card_payment_transfer(
    user_id,
    transfer_id,
    *,
    get_connection,
):
    if not transfer_id:
        return None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    transfer.*,
                    source.name AS source_payment_method_name,
                    destination.name AS destination_payment_method_name,
                    source_transaction.id AS source_transaction_id,
                    source_transaction.reconciliation_status
                        AS source_reconciliation_status,
                    destination_transaction.id AS destination_transaction_id,
                    destination_transaction.reconciliation_status
                        AS destination_reconciliation_status
                FROM finance_linked_transfers AS transfer
                JOIN finance_payment_methods AS source
                    ON source.id = transfer.source_payment_method_id
                JOIN finance_payment_methods AS destination
                    ON destination.id = transfer.destination_payment_method_id
                LEFT JOIN finance_transactions AS source_transaction
                    ON source_transaction.linked_transfer_id = transfer.id
                   AND source_transaction.linked_transfer_role = 'source'
                LEFT JOIN finance_transactions AS destination_transaction
                    ON destination_transaction.linked_transfer_id = transfer.id
                   AND destination_transaction.linked_transfer_role = 'destination'
                WHERE transfer.id = %s
                  AND transfer.user_id = %s
                  AND transfer.transfer_type = 'credit_card_payment';
                """,
                (transfer_id, user_id),
            )
            row = cur.fetchone()

    return dict(row) if row else None


def list_card_payment_transfers(
    user_id,
    limit=10000,
    *,
    get_connection,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    transfer.*,
                    source.name AS source_payment_method_name,
                    destination.name AS destination_payment_method_name,
                    source_transaction.id AS source_transaction_id,
                    source_transaction.reconciliation_status
                        AS source_reconciliation_status,
                    destination_transaction.id AS destination_transaction_id,
                    destination_transaction.reconciliation_status
                        AS destination_reconciliation_status
                FROM finance_linked_transfers AS transfer
                JOIN finance_payment_methods AS source
                    ON source.id = transfer.source_payment_method_id
                JOIN finance_payment_methods AS destination
                    ON destination.id = transfer.destination_payment_method_id
                LEFT JOIN finance_transactions AS source_transaction
                    ON source_transaction.linked_transfer_id = transfer.id
                   AND source_transaction.linked_transfer_role = 'source'
                LEFT JOIN finance_transactions AS destination_transaction
                    ON destination_transaction.linked_transfer_id = transfer.id
                   AND destination_transaction.linked_transfer_role = 'destination'
                WHERE transfer.user_id = %s
                  AND transfer.transfer_type = 'credit_card_payment'
                ORDER BY transfer.source_date DESC, transfer.id DESC
                LIMIT %s;
                """,
                (user_id, int(limit)),
            )
            return [dict(row) for row in cur.fetchall()]
