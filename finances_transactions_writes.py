from __future__ import annotations

from datetime import date


def save_transaction(
    user_id,
    transaction_date,
    transaction_type,
    amount,
    description,
    category_id=None,
    tag_ids=None,
    note=None,
    status="confirmed",
    payment_method_id=None,
    reconciliation_status="unreconciled",
    reconciliation_date=None,
    budget_excluded=False,
    bank_programmed=False,
    reminder_enabled=False,
    reminder_time=None,
    transaction_id=None,
    *,
    TRANSACTION_TYPES,
    TRANSACTION_STATUSES,
    RECONCILIATION_STATUSES,
    normalize_reminder_time,
    money,
    text,
    get_connection,
    validate_links,
    validate_payment_method,
):
    if transaction_type not in TRANSACTION_TYPES:
        raise ValueError("Type invalide.")
    if status not in TRANSACTION_STATUSES:
        raise ValueError("Statut invalide.")
    if reconciliation_status not in RECONCILIATION_STATUSES:
        raise ValueError("Statut de conciliation invalide.")

    parsed_date = (
        transaction_date
        if isinstance(transaction_date, date)
        else date.fromisoformat(str(transaction_date))
    )
    parsed_reconciliation_date = (
        reconciliation_date
        if isinstance(reconciliation_date, date)
        else (
            date.fromisoformat(str(reconciliation_date))
            if reconciliation_date
            else None
        )
    )
    if status == "planned":
        reconciliation_status = "unreconciled"
        parsed_reconciliation_date = None
    elif reconciliation_status == "unreconciled":
        parsed_reconciliation_date = None

    normalized_reminder_time = normalize_reminder_time(reminder_time)
    bank_programmed = bool(bank_programmed) if status == "planned" else False
    reminder_enabled = bool(reminder_enabled) if status == "planned" else False

    amount = money(amount)
    description = text(description, "La description", 160, True)
    note = text(note, "La note", 1000)

    with get_connection() as conn:
        with conn.cursor() as cur:
            tags = validate_links(cur, user_id, category_id, tag_ids)
            validated_payment_method = validate_payment_method(
                cur, user_id, payment_method_id
            )

            if transaction_id:
                cur.execute(
                    """
                    SELECT reconciliation_status, linked_transfer_id
                    FROM finance_transactions
                    WHERE id = %s AND user_id = %s
                    FOR UPDATE;
                    """,
                    (transaction_id, user_id),
                )
                current_transaction = cur.fetchone()
                if not current_transaction:
                    raise ValueError("Transaction introuvable.")
                if current_transaction.get("linked_transfer_id"):
                    raise ValueError(
                        "Ce paiement est lié à deux comptes. Utilisez « Modifier le paiement de carte » pour le changer."
                    )
                if current_transaction["reconciliation_status"] == "reconciled":
                    raise ValueError(
                        "Retirez d’abord la conciliation avant de modifier cette transaction."
                    )

                cur.execute(
                    """
                    UPDATE finance_transactions
                    SET
                        transaction_date = %s,
                        transaction_type = %s,
                        amount = %s,
                        description = %s,
                        category_id = %s,
                        note = %s,
                        status = %s,
                        payment_method_id = %s,
                        reconciliation_status = %s,
                        reconciliation_date = %s,
                        budget_excluded = %s,
                        bank_programmed = %s,
                        reminder_enabled = %s,
                        reminder_time = %s,
                        updated_at = NOW()
                    WHERE id = %s
                      AND user_id = %s;
                    """,
                    (
                        parsed_date,
                        transaction_type,
                        amount,
                        description,
                        category_id,
                        note,
                        status,
                        validated_payment_method,
                        reconciliation_status,
                        parsed_reconciliation_date,
                        bool(budget_excluded),
                        bank_programmed,
                        reminder_enabled,
                        normalized_reminder_time,
                        transaction_id,
                        user_id,
                    ),
                )
                if cur.rowcount == 0:
                    raise ValueError("Transaction introuvable.")

                saved_id = int(transaction_id)
                cur.execute(
                    """
                    DELETE FROM finance_transaction_tags
                    WHERE transaction_id = %s;
                    """,
                    (saved_id,),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO finance_transactions (
                        user_id,
                        transaction_date,
                        transaction_type,
                        amount,
                        description,
                        category_id,
                        note,
                        status,
                        payment_method_id,
                        reconciliation_status,
                        reconciliation_date,
                        budget_excluded,
                        bank_programmed,
                        reminder_enabled,
                        reminder_time
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s
                    )
                    RETURNING id;
                    """,
                    (
                        user_id,
                        parsed_date,
                        transaction_type,
                        amount,
                        description,
                        category_id,
                        note,
                        status,
                        validated_payment_method,
                        reconciliation_status,
                        parsed_reconciliation_date,
                        bool(budget_excluded),
                        bank_programmed,
                        reminder_enabled,
                        normalized_reminder_time,
                    ),
                )
                saved_id = int(cur.fetchone()["id"])

            for tag_id in tags:
                cur.execute(
                    """
                    INSERT INTO finance_transaction_tags (
                        transaction_id,
                        tag_id
                    )
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (saved_id, tag_id),
                )

            conn.commit()
            return saved_id


def delete_transaction(user_id, transaction_id, *, get_connection):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT reconciliation_status, linked_transfer_id
                FROM finance_transactions
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
                """,
                (transaction_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Transaction introuvable.")

            linked_transfer_id = row.get("linked_transfer_id")
            if linked_transfer_id:
                cur.execute(
                    """
                    SELECT reconciliation_status
                    FROM finance_transactions
                    WHERE user_id = %s
                      AND linked_transfer_id = %s
                    FOR UPDATE;
                    """,
                    (user_id, linked_transfer_id),
                )
                linked_rows = cur.fetchall()
                if any(
                    linked_row["reconciliation_status"] == "reconciled"
                    for linked_row in linked_rows
                ):
                    raise ValueError(
                        "Retirez d’abord la conciliation du paiement de carte avant de le supprimer."
                    )
                cur.execute(
                    """
                    DELETE FROM finance_linked_transfers
                    WHERE id = %s AND user_id = %s;
                    """,
                    (linked_transfer_id, user_id),
                )
                conn.commit()
                return

            if row["reconciliation_status"] == "reconciled":
                raise ValueError(
                    "Retirez d’abord la conciliation avant de supprimer cette transaction."
                )

            cur.execute(
                """
                DELETE FROM finance_transactions
                WHERE id = %s AND user_id = %s;
                """,
                (transaction_id, user_id),
            )
            conn.commit()


def set_transaction_status(
    user_id,
    transaction_id,
    status,
    *,
    TRANSACTION_STATUSES,
    get_connection,
):
    if status not in TRANSACTION_STATUSES:
        raise ValueError("Statut invalide.")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT linked_transfer_id
                FROM finance_transactions
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
                """,
                (transaction_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Transaction introuvable.")
            linked_transfer_id = row.get("linked_transfer_id")
            if linked_transfer_id:
                cur.execute(
                    """
                    UPDATE finance_linked_transfers
                    SET status = %s,
                        bank_programmed = CASE
                            WHEN %s = 'planned' THEN bank_programmed
                            ELSE FALSE
                        END,
                        reminder_enabled = CASE
                            WHEN %s = 'planned' THEN reminder_enabled
                            ELSE FALSE
                        END,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s;
                    """,
                    (status, status, status, linked_transfer_id, user_id),
                )
                cur.execute(
                    """
                    UPDATE finance_transactions
                    SET status = %s,
                        bank_programmed = CASE
                            WHEN %s = 'planned'
                                 AND linked_transfer_role = 'source'
                            THEN bank_programmed
                            ELSE FALSE
                        END,
                        reminder_enabled = CASE
                            WHEN %s = 'planned'
                                 AND linked_transfer_role = 'source'
                            THEN reminder_enabled
                            ELSE FALSE
                        END,
                        updated_at = NOW()
                    WHERE user_id = %s
                      AND linked_transfer_id = %s;
                    """,
                    (status, status, status, user_id, linked_transfer_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE finance_transactions
                    SET status=%s,
                        bank_programmed = CASE
                            WHEN %s = 'planned' THEN bank_programmed
                            ELSE FALSE
                        END,
                        reminder_enabled = CASE
                            WHEN %s = 'planned' THEN reminder_enabled
                            ELSE FALSE
                        END,
                        updated_at=NOW()
                    WHERE id=%s AND user_id=%s;
                    """,
                    (status, status, status, transaction_id, user_id),
                )
            conn.commit()
