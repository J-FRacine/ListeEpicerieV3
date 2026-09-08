from __future__ import annotations

from decimal import Decimal, InvalidOperation


def list_transactions(
    user_id,
    start_date=None,
    end_date=None,
    transaction_type=None,
    category_id=None,
    tag_id=None,
    status=None,
    payment_method_id=None,
    reconciliation_status=None,
    query=None,
    transaction_id=None,
    include_linked_transfer_destinations=True,
    amount_exact=None,
    amount_min=None,
    amount_max=None,
    limit=1000,
    *,
    get_connection,
):
    conditions = [
        "t.user_id = %s",
    ]
    params = [
        user_id,
    ]

    for sql, value in (
        (
            "t.id = %s",
            transaction_id,
        ),
        (
            "t.transaction_date >= %s",
            start_date,
        ),
        (
            "t.transaction_date <= %s",
            end_date,
        ),
        (
            "t.transaction_type = %s",
            transaction_type,
        ),
        (
            "t.category_id = %s",
            category_id,
        ),
        (
            "t.status = %s",
            status,
        ),
        (
            "t.payment_method_id = %s",
            payment_method_id,
        ),
        (
            "t.reconciliation_status = %s",
            reconciliation_status,
        ),
    ):
        if value not in (
            None,
            "",
        ):
            conditions.append(
                sql
            )
            params.append(
                value
            )

    if not include_linked_transfer_destinations:
        conditions.append(
            "(t.linked_transfer_role IS NULL OR t.linked_transfer_role <> 'destination')"
        )

    if tag_id:
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM finance_transaction_tags AS selected_tag
                WHERE selected_tag.transaction_id = t.id
                  AND selected_tag.tag_id = %s
            )
            """
        )
        params.append(
            tag_id
        )

    if query:
        conditions.append(
            """
            (
                LOWER(t.description) LIKE LOWER(%s)
                OR LOWER(
                    COALESCE(
                        t.note,
                        ''
                    )
                ) LIKE LOWER(%s)
                OR LOWER(
                    COALESCE(
                        payment_method.name,
                        ''
                    )
                ) LIKE LOWER(%s)
            )
            """
        )
        pattern = (
            f"%{str(query).strip()}%"
        )
        params.extend(
            [
                pattern,
                pattern,
                pattern,
            ]
        )

    def _amount_filter_value(value, label):
        if value in (None, ""):
            return None
        text = str(value).strip().replace(" ", "").replace(",", ".")
        try:
            parsed = Decimal(text).copy_abs().quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError, TypeError) as error:
            raise ValueError(f"{label} est invalide.") from error
        return parsed

    exact_value = _amount_filter_value(amount_exact, "Le montant")
    min_value = _amount_filter_value(amount_min, "Le montant minimum")
    max_value = _amount_filter_value(amount_max, "Le montant maximum")
    if min_value is not None and max_value is not None and min_value > max_value:
        raise ValueError("Le montant minimum ne peut pas dépasser le montant maximum.")
    if exact_value is not None:
        conditions.append("ABS(t.amount) = %s")
        params.append(exact_value)
    else:
        if min_value is not None:
            conditions.append("ABS(t.amount) >= %s")
            params.append(min_value)
        if max_value is not None:
            conditions.append("ABS(t.amount) <= %s")
            params.append(max_value)

    params.append(
        int(limit)
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    t.*,
                    payment_method.name
                        AS payment_method_name,
                    payment_method.method_type
                        AS payment_method_type,
                    linked_transfer.transfer_type
                        AS linked_transfer_type,
                    linked_transfer.source_payment_method_id
                        AS linked_transfer_source_payment_method_id,
                    linked_transfer.destination_payment_method_id
                        AS linked_transfer_destination_payment_method_id,
                    linked_transfer.source_date
                        AS linked_transfer_source_date,
                    linked_transfer.destination_date
                        AS linked_transfer_destination_date,
                    source_method.name
                        AS linked_transfer_source_name,
                    destination_method.name
                        AS linked_transfer_destination_name,
                    CASE
                        WHEN parent.id IS NULL
                        THEN category.name
                        ELSE parent.name
                             || ' › '
                             || category.name
                    END AS category_full_name,
                    COALESCE(
                        ARRAY_AGG(
                            tag.id
                            ORDER BY tag.name
                        )
                        FILTER (
                            WHERE tag.id IS NOT NULL
                        ),
                        ARRAY[]::BIGINT[]
                    ) AS tag_ids,
                    COALESCE(
                        ARRAY_AGG(
                            tag.name
                            ORDER BY tag.name
                        )
                        FILTER (
                            WHERE tag.id IS NOT NULL
                        ),
                        ARRAY[]::TEXT[]
                    ) AS tag_names
                FROM finance_transactions AS t
                LEFT JOIN finance_categories AS category
                    ON category.id = t.category_id
                LEFT JOIN finance_categories AS parent
                    ON parent.id = category.parent_id
                LEFT JOIN finance_payment_methods AS payment_method
                    ON payment_method.id = t.payment_method_id
                LEFT JOIN finance_linked_transfers AS linked_transfer
                    ON linked_transfer.id = t.linked_transfer_id
                LEFT JOIN finance_payment_methods AS source_method
                    ON source_method.id = linked_transfer.source_payment_method_id
                LEFT JOIN finance_payment_methods AS destination_method
                    ON destination_method.id = linked_transfer.destination_payment_method_id
                LEFT JOIN finance_transaction_tags AS transaction_tag
                    ON transaction_tag.transaction_id = t.id
                LEFT JOIN finance_tags AS tag
                    ON tag.id = transaction_tag.tag_id
                WHERE {" AND ".join(conditions)}
                GROUP BY
                    t.id,
                    category.id,
                    parent.id,
                    parent.name,
                    payment_method.id,
                    payment_method.name,
                    payment_method.method_type,
                    linked_transfer.id,
                    linked_transfer.transfer_type,
                    linked_transfer.source_payment_method_id,
                    linked_transfer.destination_payment_method_id,
                    linked_transfer.source_date,
                    linked_transfer.destination_date,
                    source_method.id,
                    source_method.name,
                    destination_method.id,
                    destination_method.name
                ORDER BY
                    t.transaction_date DESC,
                    t.id DESC
                LIMIT %s;
                """,
                params,
            )
            return cur.fetchall()


def get_transaction(
    user_id,
    transaction_id,
    *,
    list_transactions,
):
    rows = list_transactions(user_id, transaction_id=transaction_id)
    if not rows:
        raise ValueError("Transaction introuvable.")
    return rows[0]

