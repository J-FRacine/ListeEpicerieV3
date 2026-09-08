"""Écritures Conciliation avec services injectés à chaque appel.

Le SQL, les validations et les frontières transactionnelles sont conservés.
"""
from datetime import date
from decimal import Decimal


def bulk_assign_payment_method(
    user_id,
    transaction_ids,
    payment_method_id,
    *,
    _validate_payment_method,
    get_connection,
):
    ids = sorted({int(value) for value in (transaction_ids or [])})
    if not ids:
        raise ValueError("Sélectionnez au moins une transaction.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            validated_method = _validate_payment_method(
                cur,
                user_id,
                payment_method_id,
            )
            cur.execute(
                """
                UPDATE finance_transactions
                SET payment_method_id = %s,
                    updated_at = NOW()
                WHERE user_id = %s
                  AND id = ANY(%s);
                """,
                (validated_method, user_id, ids),
            )
            if cur.rowcount != len(ids):
                raise ValueError(
                    "Certaines transactions sélectionnées sont introuvables."
                )
            conn.commit()
    return len(ids)


def create_reconciliation_session(
    user_id,
    payment_method_id,
    transaction_ids,
    statement_date,
    statement_balance=None,
    due_date=None,
    reconciliation_date=None,
    note=None,
    include_opening_balance=False,
    difference_resolution="balanced",
    difference_explanation=None,
    *,
    _decimal_value,
    _text,
    _validate_payment_method,
    get_connection,
):
    ids = sorted({int(value) for value in (transaction_ids or [])})
    parsed_statement_date = (
        statement_date
        if isinstance(statement_date, date)
        else date.fromisoformat(str(statement_date))
    )
    parsed_due_date = (
        due_date
        if isinstance(due_date, date)
        else (date.fromisoformat(str(due_date)) if due_date else None)
    )
    parsed_reconciliation_date = (
        reconciliation_date
        if isinstance(reconciliation_date, date)
        else (
            date.fromisoformat(str(reconciliation_date))
            if reconciliation_date
            else date.today()
        )
    )
    parsed_statement_balance = _decimal_value(
        statement_balance, "Le solde du relevé", allow_blank=True
    )
    cleaned_note = _text(note, "La note", 1000)
    cleaned_explanation = _text(
        difference_explanation, "L’explication de l’écart", 1000
    )
    resolution = str(difference_resolution or "balanced").strip().lower()
    if resolution not in {"balanced", "justified", "carry"}:
        raise ValueError("Traitement de la différence invalide.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            payment_method_id = _validate_payment_method(
                cur, user_id, payment_method_id
            )
            cur.execute(
                """
                SELECT *
                FROM finance_payment_methods
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
                """,
                (payment_method_id, user_id),
            )
            method = cur.fetchone()
            if not method:
                raise ValueError("Mode de paiement introuvable.")

            # Le dernier relevé finalisé devient la référence du suivant.
            cur.execute(
                """
                SELECT
                    id, statement_date, statement_balance, expected_balance,
                    closing_reference_balance
                FROM finance_reconciliation_sessions
                WHERE user_id = %s
                  AND payment_method_id = %s
                  AND status = 'completed'
                ORDER BY statement_date DESC, id DESC
                LIMIT 1
                FOR UPDATE;
                """,
                (user_id, payment_method_id),
            )
            previous = cur.fetchone()
            if previous:
                reference_balance = previous.get("closing_reference_balance")
                if reference_balance is None:
                    reference_balance = previous.get("statement_balance")
                if reference_balance is None:
                    reference_balance = previous.get("expected_balance")
                reference_balance = Decimal(reference_balance or 0)
                reference_date = previous.get("statement_date")
            else:
                reference_balance = Decimal(method.get("opening_balance") or 0)
                reference_date = method.get("opening_balance_date")

            opening_amount = Decimal("0.00")
            # Dès la première séance V1.9, le solde initial devient le point
            # de référence du relevé et ne doit plus rester artificiellement
            # dans le solde « à concilier » des mois suivants.
            if (
                previous is None
                and not method["opening_balance_reconciled"]
                and Decimal(method["opening_balance"] or 0) != 0
            ):
                include_opening_balance = True

            if include_opening_balance:
                if method["opening_balance_reconciled"]:
                    raise ValueError("Le solde initial est déjà concilié.")
                opening_amount = Decimal(method["opening_balance"] or 0)
                if opening_amount == 0:
                    include_opening_balance = False

            transaction_total = Decimal("0.00")
            if ids:
                cur.execute(
                    """
                    SELECT id, transaction_type, amount
                    FROM finance_transactions
                    WHERE user_id = %s
                      AND payment_method_id = %s
                      AND id = ANY(%s)
                      AND status = 'confirmed'
                      AND reconciliation_status = 'unreconciled'
                    FOR UPDATE;
                    """,
                    (user_id, payment_method_id, ids),
                )
                selected = cur.fetchall()
                if len(selected) != len(ids):
                    raise ValueError(
                        "Une transaction sélectionnée n’est plus disponible "
                        "pour cette conciliation."
                    )
                for row in selected:
                    transaction_total += (
                        Decimal(row["amount"])
                        if row["transaction_type"] == "expense"
                        else -Decimal(row["amount"])
                    )

            if not ids and not include_opening_balance:
                raise ValueError(
                    "Sélectionnez au moins une transaction ou le solde initial."
                )

            selected_total = transaction_total
            expected_balance = reference_balance + transaction_total
            difference = (
                parsed_statement_balance - expected_balance
                if parsed_statement_balance is not None
                else None
            )

            if difference is None or abs(difference) < Decimal(".01"):
                resolution = "balanced"
                cleaned_explanation = None
            elif resolution == "justified":
                if not cleaned_explanation:
                    raise ValueError(
                        "Expliquez la différence avant de la clore comme écart justifié."
                    )
            elif resolution == "balanced":
                raise ValueError(
                    "La conciliation ne balance pas. Choisissez de justifier ou de reporter l’écart."
                )

            if resolution == "carry":
                closing_reference_balance = expected_balance
            elif parsed_statement_balance is not None:
                closing_reference_balance = parsed_statement_balance
            else:
                closing_reference_balance = expected_balance

            cur.execute(
                """
                INSERT INTO finance_reconciliation_sessions (
                    user_id, payment_method_id, statement_date,
                    statement_balance, due_date, reconciliation_date, note,
                    selected_total, difference, included_opening_balance,
                    opening_balance_amount, reference_balance, reference_date,
                    expected_balance, closing_reference_balance,
                    difference_resolution, difference_explanation
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id;
                """,
                (
                    user_id, payment_method_id, parsed_statement_date,
                    parsed_statement_balance, parsed_due_date,
                    parsed_reconciliation_date, cleaned_note, selected_total,
                    difference, bool(include_opening_balance), opening_amount,
                    reference_balance, reference_date, expected_balance,
                    closing_reference_balance, resolution, cleaned_explanation,
                ),
            )
            session_id = int(cur.fetchone()["id"])

            for transaction_id in ids:
                cur.execute(
                    """
                    INSERT INTO finance_reconciliation_session_transactions (
                        session_id, transaction_id
                    )
                    VALUES (%s, %s);
                    """,
                    (session_id, transaction_id),
                )

            if ids:
                cur.execute(
                    """
                    UPDATE finance_transactions
                    SET reconciliation_status = 'reconciled',
                        reconciliation_date = %s,
                        reconciliation_session_id = %s,
                        updated_at = NOW()
                    WHERE user_id = %s
                      AND id = ANY(%s);
                    """,
                    (
                        parsed_reconciliation_date, session_id, user_id, ids,
                    ),
                )

            if include_opening_balance:
                cur.execute(
                    """
                    UPDATE finance_payment_methods
                    SET opening_balance_reconciled = TRUE,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s;
                    """,
                    (payment_method_id, user_id),
                )

            # Une finalisation réussie remplace le brouillon éventuel de la carte.
            cur.execute(
                """
                DELETE FROM finance_reconciliation_drafts
                WHERE user_id=%s AND payment_method_id=%s;
                """,
                (user_id, payment_method_id),
            )

            conn.commit()

    return {
        "session_id": session_id,
        "selected_total": selected_total,
        "reference_balance": reference_balance,
        "expected_balance": expected_balance,
        "statement_balance": parsed_statement_balance,
        "difference": difference,
        "difference_resolution": resolution,
        "closing_reference_balance": closing_reference_balance,
        "transaction_count": len(ids),
    }


def remove_transaction_from_reconciliation_session(
    user_id,
    session_id,
    transaction_id,
    *,
    _refresh_reconciliation_session_totals,
    get_connection,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status
                FROM finance_reconciliation_sessions
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
                """,
                (session_id, user_id),
            )
            session = cur.fetchone()
            if not session:
                raise ValueError("Séance de conciliation introuvable.")
            if session["status"] != "completed":
                raise ValueError("Cette séance est déjà annulée.")

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
            if cur.rowcount == 0:
                raise ValueError(
                    "Cette transaction ne fait plus partie de la séance."
                )

            cur.execute(
                """
                UPDATE finance_transactions
                SET reconciliation_status = 'unreconciled',
                    reconciliation_date = NULL,
                    reconciliation_session_id = NULL,
                    updated_at = NOW()
                WHERE id = %s
                  AND user_id = %s;
                """,
                (transaction_id, user_id),
            )
            _refresh_reconciliation_session_totals(cur, session_id)
            conn.commit()


def cancel_reconciliation_session(
    user_id,
    session_id,
    *,
    get_connection,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM finance_reconciliation_sessions
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
                """,
                (session_id, user_id),
            )
            session = cur.fetchone()
            if not session:
                raise ValueError("Séance de conciliation introuvable.")
            if session["status"] == "cancelled":
                raise ValueError("Cette séance est déjà annulée.")

            cur.execute(
                """
                SELECT transaction_id
                FROM finance_reconciliation_session_transactions
                WHERE session_id = %s
                  AND is_active = TRUE;
                """,
                (session_id,),
            )
            ids = [int(row["transaction_id"]) for row in cur.fetchall()]

            if ids:
                cur.execute(
                    """
                    UPDATE finance_transactions
                    SET reconciliation_status = 'unreconciled',
                        reconciliation_date = NULL,
                        reconciliation_session_id = NULL,
                        updated_at = NOW()
                    WHERE user_id = %s
                      AND id = ANY(%s);
                    """,
                    (user_id, ids),
                )
                cur.execute(
                    """
                    UPDATE finance_reconciliation_session_transactions
                    SET is_active = FALSE,
                        removed_at = NOW()
                    WHERE session_id = %s
                      AND is_active = TRUE;
                    """,
                    (session_id,),
                )

            if session["included_opening_balance"]:
                cur.execute(
                    """
                    UPDATE finance_payment_methods
                    SET opening_balance_reconciled = FALSE,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s;
                    """,
                    (session["payment_method_id"], user_id),
                )

            cur.execute(
                """
                UPDATE finance_reconciliation_sessions
                SET status = 'cancelled',
                    cancelled_at = NOW()
                WHERE id = %s;
                """,
                (session_id,),
            )
            conn.commit()


def save_reconciliation_draft(
    user_id,
    payment_method_id,
    transaction_ids,
    *,
    statement_date=None,
    statement_balance=None,
    due_date=None,
    reconciliation_date=None,
    note=None,
    include_opening_balance=False,
    difference_explanation=None,
    filter_start=None,
    filter_end=None,
    filter_query=None,
    sort_direction="asc",
    _decimal_value,
    _optional_date_value,
    _text,
    _validate_payment_method,
    get_connection,
):
    """Sauvegarde le travail de conciliation sans concilier les transactions."""

    ids = sorted({int(value) for value in (transaction_ids or [])})
    statement = _optional_date_value(statement_date, "La date du relevé")
    due = _optional_date_value(due_date, "La date de paiement")
    reconciled_on = _optional_date_value(
        reconciliation_date, "La date de conciliation"
    )
    start = _optional_date_value(filter_start, "La date de début du filtre")
    end = _optional_date_value(filter_end, "La date de fin du filtre")
    balance = _decimal_value(
        statement_balance, "Le solde du relevé", allow_blank=True
    )
    cleaned_note = _text(note, "La note", 1000)
    cleaned_explanation = _text(
        difference_explanation, "L’explication de l’écart", 1000
    )
    cleaned_query = _text(filter_query, "La recherche", 300)
    sort_value = str(sort_direction or "asc").strip().lower()
    if sort_value not in {"asc", "desc"}:
        sort_value = "asc"

    with get_connection() as conn:
        with conn.cursor() as cur:
            method_id = _validate_payment_method(cur, user_id, payment_method_id)
            if method_id is None:
                raise ValueError("Choisissez un mode de paiement.")
            cur.execute(
                """
                INSERT INTO finance_reconciliation_drafts (
                    user_id, payment_method_id, statement_date,
                    statement_balance, due_date, reconciliation_date,
                    note, include_opening_balance, difference_explanation,
                    filter_start, filter_end, filter_query, sort_direction,
                    selected_transaction_ids
                )
                VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                ON CONFLICT (user_id, payment_method_id) DO UPDATE
                SET statement_date=EXCLUDED.statement_date,
                    statement_balance=EXCLUDED.statement_balance,
                    due_date=EXCLUDED.due_date,
                    reconciliation_date=EXCLUDED.reconciliation_date,
                    note=EXCLUDED.note,
                    include_opening_balance=EXCLUDED.include_opening_balance,
                    difference_explanation=EXCLUDED.difference_explanation,
                    filter_start=EXCLUDED.filter_start,
                    filter_end=EXCLUDED.filter_end,
                    filter_query=EXCLUDED.filter_query,
                    sort_direction=EXCLUDED.sort_direction,
                    selected_transaction_ids=EXCLUDED.selected_transaction_ids,
                    updated_at=NOW()
                RETURNING id;
                """,
                (
                    user_id,
                    method_id,
                    statement,
                    balance,
                    due,
                    reconciled_on,
                    cleaned_note,
                    bool(include_opening_balance),
                    cleaned_explanation,
                    start,
                    end,
                    cleaned_query,
                    sort_value,
                    ids,
                ),
            )
            draft_id = int(cur.fetchone()["id"])
            conn.commit()
    return draft_id


def delete_reconciliation_draft(user_id, payment_method_id, *, get_connection):
    if payment_method_id in (None, ""):
        return 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM finance_reconciliation_drafts
                WHERE user_id=%s AND payment_method_id=%s;
                """,
                (user_id, int(payment_method_id)),
            )
            count = cur.rowcount
            conn.commit()
    return count
