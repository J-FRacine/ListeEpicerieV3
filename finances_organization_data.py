from __future__ import annotations

import unicodedata


def list_categories(user_id, include_inactive=False, *, get_connection):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    child.*,
                    parent.name AS parent_name,
                    CASE WHEN parent.id IS NULL
                         THEN child.name
                         ELSE parent.name || ' › ' || child.name
                    END AS full_name
                FROM finance_categories child
                LEFT JOIN finance_categories parent ON parent.id=child.parent_id
                WHERE child.user_id=%s
                  AND (%s OR child.is_active=TRUE)
                ORDER BY COALESCE(parent.name, child.name),
                         CASE WHEN parent.id IS NULL THEN 0 ELSE 1 END,
                         child.name;
            """, (user_id, include_inactive))
            return cur.fetchall()


def list_tags(user_id, include_inactive=False, *, get_connection):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM finance_tags
                WHERE user_id=%s AND (%s OR is_active=TRUE)
                ORDER BY name;
            """, (user_id, include_inactive))
            return cur.fetchall()


def _normalized_lookup_name(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )
    return " ".join(text.casefold().split())


def _optional_day(value, label):
    if value in (None, ""):
        return None
    day = int(value)
    if day < 1 or day > 31:
        raise ValueError(f"{label} doit être entre 1 et 31.")
    return day


def list_payment_methods(
    user_id,
    include_inactive=False,
    *,
    get_connection,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    method.id,
                    method.name,
                    method.sort_order,
                    method.is_active,
                    method.method_type,
                    method.statement_day,
                    method.payment_day,
                    method.opening_balance,
                    method.opening_balance_date,
                    method.opening_balance_reconciled,
                    method.credit_limit,
                    method.note,
                    COUNT(transaction.id) AS transaction_count
                FROM finance_payment_methods AS method
                LEFT JOIN finance_transactions AS transaction
                    ON transaction.payment_method_id = method.id
                   AND transaction.user_id = method.user_id
                WHERE method.user_id = %s
                  AND (%s OR method.is_active = TRUE)
                GROUP BY method.id
                ORDER BY
                    method.is_active DESC,
                    method.sort_order,
                    LOWER(method.name),
                    method.id;
                """,
                (user_id, include_inactive),
            )
            return cur.fetchall()
