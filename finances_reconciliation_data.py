"""Lectures et résumés Conciliation avec dépendances injectées à chaque appel.

Les corps et les requêtes SQL historiques sont conservés.
"""
from decimal import Decimal


def payment_predicted_balance_summary(user_id, *, get_connection):
    """Soldes cumulatifs sans remise à zéro mensuelle."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    method.id AS payment_method_id,
                    method.name AS payment_method_name,
                    method.method_type,
                    method.statement_day,
                    method.payment_day,
                    method.opening_balance,
                    method.opening_balance_date,
                    method.opening_balance_reconciled,
                    method.is_active,
                    method.sort_order,
                    CASE
                        WHEN method.opening_balance_reconciled = FALSE
                        THEN method.opening_balance
                        ELSE 0
                    END AS opening_balance_pending,
                    COALESCE(
                        SUM(transaction.amount) FILTER (
                            WHERE transaction.reconciliation_status = 'unreconciled'
                              AND transaction.status = 'confirmed'
                              AND transaction.transaction_type = 'expense'
                        ),
                        0
                    ) AS confirmed_expenses,
                    COALESCE(
                        SUM(transaction.amount) FILTER (
                            WHERE transaction.reconciliation_status = 'unreconciled'
                              AND transaction.status = 'confirmed'
                              AND transaction.transaction_type = 'income'
                        ),
                        0
                    ) AS confirmed_incomes,
                    COALESCE(
                        SUM(transaction.amount) FILTER (
                            WHERE transaction.reconciliation_status = 'unreconciled'
                              AND transaction.status = 'planned'
                              AND transaction.transaction_type = 'expense'
                        ),
                        0
                    ) AS planned_expenses,
                    COALESCE(
                        SUM(transaction.amount) FILTER (
                            WHERE transaction.reconciliation_status = 'unreconciled'
                              AND transaction.status = 'planned'
                              AND transaction.transaction_type = 'income'
                        ),
                        0
                    ) AS planned_incomes,
                    COUNT(transaction.id) FILTER (
                        WHERE transaction.reconciliation_status = 'unreconciled'
                          AND transaction.status = 'confirmed'
                    ) AS confirmed_count,
                    COUNT(transaction.id) FILTER (
                        WHERE transaction.reconciliation_status = 'unreconciled'
                          AND transaction.status = 'planned'
                    ) AS planned_count,
                    MIN(transaction.transaction_date) FILTER (
                        WHERE transaction.reconciliation_status = 'unreconciled'
                          AND transaction.status = 'confirmed'
                    ) AS oldest_unreconciled_date,
                    (
                        SELECT MAX(session.reconciliation_date)
                        FROM finance_reconciliation_sessions AS session
                        WHERE session.user_id = method.user_id
                          AND session.payment_method_id = method.id
                          AND session.status = 'completed'
                    ) AS last_reconciliation_date
                FROM finance_payment_methods AS method
                LEFT JOIN finance_transactions AS transaction
                    ON transaction.user_id = method.user_id
                   AND transaction.payment_method_id = method.id
                WHERE method.user_id = %s
                GROUP BY method.id
                ORDER BY
                    method.is_active DESC,
                    method.sort_order,
                    LOWER(method.name),
                    method.id;
                """,
                (user_id,),
            )
            rows = cur.fetchall()

    result = []
    for row in rows:
        current_balance = (
            Decimal(row["opening_balance_pending"])
            + Decimal(row["confirmed_expenses"])
            - Decimal(row["confirmed_incomes"])
        )
        planned_impact = (
            Decimal(row["planned_expenses"])
            - Decimal(row["planned_incomes"])
        )
        result.append(
            {
                **dict(row),
                "current_balance": current_balance,
                "planned_impact": planned_impact,
                "predicted_balance": current_balance + planned_impact,
            }
        )
    return result


def count_unassigned_confirmed_transactions(user_id, *, get_connection):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS total
                FROM finance_transactions
                WHERE user_id = %s
                  AND status = 'confirmed'
                  AND payment_method_id IS NULL;
                """,
                (user_id,),
            )
            return int(cur.fetchone()["total"])


def list_unreconciled_transactions(
    user_id,
    payment_method_id,
    start_date=None,
    end_date=None,
    query=None,
    *,
    list_transactions,
):
    return list_transactions(
        user_id,
        start_date=start_date,
        end_date=end_date,
        status="confirmed",
        payment_method_id=payment_method_id,
        reconciliation_status="unreconciled",
        query=query,
        limit=10000,
    )


def list_unassigned_transactions(
    user_id,
    query=None,
    limit=500,
    *,
    list_transactions,
):
    rows = list_transactions(
        user_id,
        status="confirmed",
        query=query,
        limit=max(int(limit) * 5, 1000),
    )
    return [
        row
        for row in rows
        if row["payment_method_id"] is None
    ][: int(limit)]


def list_reconciliation_sessions(
    user_id,
    payment_method_id=None,
    include_cancelled=True,
    limit=100,
    *,
    get_connection,
):
    conditions = ["session.user_id = %s"]
    params = [user_id]
    if payment_method_id:
        conditions.append("session.payment_method_id = %s")
        params.append(payment_method_id)
    if not include_cancelled:
        conditions.append("session.status = 'completed'")
    params.append(int(limit))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    session.*,
                    method.name AS payment_method_name,
                    COUNT(link.transaction_id)
                        FILTER (WHERE link.is_active = TRUE)
                        AS active_transaction_count,
                    COUNT(link.transaction_id)
                        FILTER (WHERE link.is_active = FALSE)
                        AS removed_transaction_count
                FROM finance_reconciliation_sessions AS session
                JOIN finance_payment_methods AS method
                    ON method.id = session.payment_method_id
                LEFT JOIN finance_reconciliation_session_transactions AS link
                    ON link.session_id = session.id
                WHERE {" AND ".join(conditions)}
                GROUP BY session.id, method.id
                ORDER BY
                    session.statement_date DESC,
                    session.id DESC
                LIMIT %s;
                """,
                params,
            )
            return cur.fetchall()


def get_reconciliation_session(
    user_id,
    session_id,
    *,
    get_connection,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    session.*,
                    method.name AS payment_method_name
                FROM finance_reconciliation_sessions AS session
                JOIN finance_payment_methods AS method
                    ON method.id = session.payment_method_id
                WHERE session.id = %s
                  AND session.user_id = %s;
                """,
                (session_id, user_id),
            )
            session = cur.fetchone()
            if not session:
                raise ValueError("Séance de conciliation introuvable.")

            cur.execute(
                """
                SELECT
                    transaction.id,
                    transaction.transaction_date,
                    transaction.transaction_type,
                    transaction.amount,
                    transaction.description,
                    transaction.reconciliation_date,
                    link.is_active,
                    link.removed_at
                FROM finance_reconciliation_session_transactions AS link
                JOIN finance_transactions AS transaction
                    ON transaction.id = link.transaction_id
                WHERE link.session_id = %s
                ORDER BY
                    transaction.transaction_date,
                    transaction.id;
                """,
                (session_id,),
            )
            transactions = cur.fetchall()

    return {
        "session": session,
        "transactions": transactions,
    }


def list_reconciliation_session_links(user_id, *, get_connection):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    link.*,
                    session.user_id
                FROM finance_reconciliation_session_transactions AS link
                JOIN finance_reconciliation_sessions AS session
                    ON session.id = link.session_id
                WHERE session.user_id = %s
                ORDER BY link.session_id, link.transaction_id;
                """,
                (user_id,),
            )
            return cur.fetchall()


def reconciliation_reference_summary(
    user_id,
    payment_method_id,
    *,
    _validate_payment_method,
    get_connection,
):
    """Retourne le point de départ du prochain relevé de carte.

    Un écart justifié est absorbé parce que le solde réel du relevé devient
    la nouvelle référence. Un écart reporté conserve le solde attendu comme
    référence afin que l'écart demeure visible au prochain relevé.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            payment_method_id = _validate_payment_method(
                cur, user_id, payment_method_id
            )
            cur.execute(
                """
                SELECT
                    id, name, method_type, opening_balance, opening_balance_date
                FROM finance_payment_methods
                WHERE id = %s AND user_id = %s;
                """,
                (payment_method_id, user_id),
            )
            method = cur.fetchone()
            if not method:
                raise ValueError("Mode de paiement introuvable.")

            cur.execute(
                """
                SELECT
                    id, statement_date, statement_balance, expected_balance,
                    closing_reference_balance, difference, difference_resolution
                FROM finance_reconciliation_sessions
                WHERE user_id = %s
                  AND payment_method_id = %s
                  AND status = 'completed'
                ORDER BY statement_date DESC, id DESC
                LIMIT 1;
                """,
                (user_id, payment_method_id),
            )
            previous = cur.fetchone()

    if previous:
        balance = previous.get("closing_reference_balance")
        if balance is None:
            balance = previous.get("statement_balance")
        if balance is None:
            balance = previous.get("expected_balance")
        if balance is None:
            balance = Decimal("0.00")
        return {
            "payment_method_id": payment_method_id,
            "payment_method_name": method["name"],
            "reference_balance": Decimal(balance),
            "reference_date": previous.get("statement_date"),
            "source": "previous_statement",
            "previous_session_id": previous.get("id"),
            "previous_difference": previous.get("difference"),
            "previous_difference_resolution": previous.get("difference_resolution"),
        }

    return {
        "payment_method_id": payment_method_id,
        "payment_method_name": method["name"],
        "reference_balance": Decimal(method.get("opening_balance") or 0),
        "reference_date": method.get("opening_balance_date"),
        "source": "opening_balance",
        "previous_session_id": None,
        "previous_difference": None,
        "previous_difference_resolution": None,
    }


def list_reconciliation_drafts(user_id, *, get_connection):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT draft.*, method.name AS payment_method_name
                FROM finance_reconciliation_drafts AS draft
                JOIN finance_payment_methods AS method
                  ON method.id=draft.payment_method_id
                WHERE draft.user_id=%s
                ORDER BY draft.updated_at DESC, draft.id DESC;
                """,
                (user_id,),
            )
            return cur.fetchall()


def get_reconciliation_draft(user_id, payment_method_id, *, get_connection):
    if payment_method_id in (None, ""):
        return None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT draft.*, method.name AS payment_method_name
                FROM finance_reconciliation_drafts AS draft
                JOIN finance_payment_methods AS method
                  ON method.id=draft.payment_method_id
                WHERE draft.user_id=%s AND draft.payment_method_id=%s;
                """,
                (user_id, int(payment_method_id)),
            )
            row = cur.fetchone()
    return dict(row) if row else None
