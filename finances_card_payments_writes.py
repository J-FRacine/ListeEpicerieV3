from __future__ import annotations

from datetime import date


def save_card_payment_transfer(
    user_id,
    source_payment_method_id,
    destination_payment_method_id,
    amount,
    source_date,
    destination_date=None,
    description=None,
    note=None,
    status="planned",
    bank_programmed=False,
    reminder_enabled=False,
    reminder_time=None,
    transfer_id=None,
    *,
    TRANSACTION_STATUSES,
    money,
    text,
    normalize_reminder_time,
    get_connection,
    validate_card_payment_methods,
):
    if status not in TRANSACTION_STATUSES:
        raise ValueError("Statut invalide.")

    parsed_source_date = (
        source_date
        if isinstance(source_date, date)
        else date.fromisoformat(str(source_date))
    )
    parsed_destination_date = (
        destination_date
        if isinstance(destination_date, date)
        else (
            date.fromisoformat(str(destination_date))
            if destination_date
            else parsed_source_date
        )
    )
    amount = money(amount)
    note = text(note, "La note", 1000)
    normalized_reminder_time = normalize_reminder_time(reminder_time)
    bank_programmed = bool(bank_programmed) if status == "planned" else False
    reminder_enabled = bool(reminder_enabled) if status == "planned" else False

    with get_connection() as conn:
        with conn.cursor() as cur:
            source, destination = validate_card_payment_methods(
                cur,
                user_id,
                source_payment_method_id,
                destination_payment_method_id,
            )
            normalized_description = text(
                description or f"Paiement {destination['name']}",
                "La description",
                160,
                True,
            )

            if transfer_id:
                cur.execute(
                    """
                    SELECT id
                    FROM finance_linked_transfers
                    WHERE id = %s AND user_id = %s
                    FOR UPDATE;
                    """,
                    (transfer_id, user_id),
                )
                if not cur.fetchone():
                    raise ValueError("Paiement de carte introuvable.")

                cur.execute(
                    """
                    SELECT reconciliation_status
                    FROM finance_transactions
                    WHERE user_id = %s
                      AND linked_transfer_id = %s
                    FOR UPDATE;
                    """,
                    (user_id, transfer_id),
                )
                linked_rows = cur.fetchall()
                if any(
                    row["reconciliation_status"] == "reconciled"
                    for row in linked_rows
                ):
                    raise ValueError(
                        "Retirez d’abord la conciliation du paiement de carte avant de le modifier."
                    )

                cur.execute(
                    """
                    UPDATE finance_linked_transfers
                    SET source_payment_method_id = %s,
                        destination_payment_method_id = %s,
                        amount = %s,
                        source_date = %s,
                        destination_date = %s,
                        description = %s,
                        note = %s,
                        status = %s,
                        bank_programmed = %s,
                        reminder_enabled = %s,
                        reminder_time = %s,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s;
                    """,
                    (
                        source["id"],
                        destination["id"],
                        amount,
                        parsed_source_date,
                        parsed_destination_date,
                        normalized_description,
                        note,
                        status,
                        bank_programmed,
                        reminder_enabled,
                        normalized_reminder_time,
                        transfer_id,
                        user_id,
                    ),
                )
                linked_id = int(transfer_id)
            else:
                cur.execute(
                    """
                    INSERT INTO finance_linked_transfers (
                        user_id,
                        transfer_type,
                        source_payment_method_id,
                        destination_payment_method_id,
                        amount,
                        source_date,
                        destination_date,
                        description,
                        note,
                        status,
                        bank_programmed,
                        reminder_enabled,
                        reminder_time
                    )
                    VALUES (
                        %s, 'credit_card_payment', %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING id;
                    """,
                    (
                        user_id,
                        source["id"],
                        destination["id"],
                        amount,
                        parsed_source_date,
                        parsed_destination_date,
                        normalized_description,
                        note,
                        status,
                        bank_programmed,
                        reminder_enabled,
                        normalized_reminder_time,
                    ),
                )
                linked_id = int(cur.fetchone()["id"])

            cur.execute(
                """
                SELECT id, linked_transfer_role
                FROM finance_transactions
                WHERE user_id = %s
                  AND linked_transfer_id = %s;
                """,
                (user_id, linked_id),
            )
            existing = {
                row["linked_transfer_role"]: int(row["id"])
                for row in cur.fetchall()
            }

            transaction_values = (
                (
                    "source",
                    parsed_source_date,
                    "expense",
                    source["id"],
                    bank_programmed,
                    reminder_enabled,
                    normalized_reminder_time,
                ),
                (
                    "destination",
                    parsed_destination_date,
                    "income",
                    destination["id"],
                    False,
                    False,
                    normalized_reminder_time,
                ),
            )
            for (
                role,
                transaction_date_value,
                transaction_type,
                payment_method_id,
                transaction_bank_programmed,
                transaction_reminder_enabled,
                transaction_reminder_time,
            ) in transaction_values:
                existing_id = existing.get(role)

                if existing_id:
                    cur.execute(
                        """
                        UPDATE finance_transactions
                        SET transaction_date = %s,
                            transaction_type = %s,
                            amount = %s,
                            description = %s,
                            category_id = NULL,
                            note = %s,
                            status = %s,
                            recurrence_id = NULL,
                            occurrence_date = NULL,
                            payment_method_id = %s,
                            reconciliation_status = 'unreconciled',
                            reconciliation_date = NULL,
                            reconciliation_session_id = NULL,
                            budget_excluded = TRUE,
                            bank_programmed = %s,
                            reminder_enabled = %s,
                            reminder_time = %s,
                            linked_transfer_role = %s,
                            updated_at = NOW()
                        WHERE id = %s AND user_id = %s;
                        """,
                        (
                            transaction_date_value,
                            transaction_type,
                            amount,
                            normalized_description,
                            note,
                            status,
                            payment_method_id,
                            transaction_bank_programmed,
                            transaction_reminder_enabled,
                            transaction_reminder_time,
                            role,
                            existing_id,
                            user_id,
                        ),
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
                            recurrence_id,
                            occurrence_date,
                            payment_method_id,
                            reconciliation_status,
                            reconciliation_date,
                            budget_excluded,
                            bank_programmed,
                            reminder_enabled,
                            reminder_time,
                            linked_transfer_id,
                            linked_transfer_role
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, NULL, %s, %s,
                            NULL, NULL, %s, 'unreconciled', NULL,
                            TRUE, %s, %s, %s, %s, %s
                        );
                        """,
                        (
                            user_id,
                            transaction_date_value,
                            transaction_type,
                            amount,
                            normalized_description,
                            note,
                            status,
                            payment_method_id,
                            transaction_bank_programmed,
                            transaction_reminder_enabled,
                            transaction_reminder_time,
                            linked_id,
                            role,
                        ),
                    )

            conn.commit()
            return linked_id
