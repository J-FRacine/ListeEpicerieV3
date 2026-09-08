"""Écritures Financements avec dépendances injectées à chaque appel.

Les corps, le SQL et les frontières de transaction sont conservés.
"""
from decimal import Decimal


def _plan_transaction_note(plan, installment_number):
    pieces = [
        f"Versement {installment_number}/{plan['total_installments']}",
        str(plan.get("provider_name") or "").strip(),
    ]
    if plan.get("note"):
        pieces.append(str(plan["note"]).strip())
    return " — ".join(piece for piece in pieces if piece)[:1000]


def _rebuild_installment_transactions(cur, user_id, plan_id, *, _next_date, _plan_transaction_note):
    cur.execute(
        """
        SELECT *
        FROM finance_installment_plans
        WHERE id=%s AND user_id=%s
        FOR UPDATE;
        """,
        (plan_id, user_id),
    )
    plan = cur.fetchone()
    if not plan:
        raise ValueError("Plan de financement introuvable.")

    # Les versements déjà confirmés font partie de l'historique réel et ne sont
    # jamais reconstruits. Les prévisions, elles, sont régénérées.
    cur.execute(
        """
        SELECT installment_number, amount
        FROM finance_transactions
        WHERE user_id=%s
          AND installment_plan_id=%s
          AND status='confirmed';
        """,
        (user_id, plan_id),
    )
    confirmed_rows = cur.fetchall()
    confirmed_numbers = {
        int(row["installment_number"])
        for row in confirmed_rows
        if row.get("installment_number") is not None
    }
    confirmed_amount = sum(
        (Decimal(row["amount"]) for row in confirmed_rows),
        Decimal("0.00"),
    )

    cur.execute(
        """
        DELETE FROM finance_transactions
        WHERE user_id=%s
          AND installment_plan_id=%s
          AND status='planned'
          AND reconciliation_status='unreconciled';
        """,
        (user_id, plan_id),
    )

    if not plan["is_active"]:
        return

    total = int(plan["total_installments"])
    baseline_completed = int(plan["completed_installments"])
    if baseline_completed >= total or not plan.get("next_due_date"):
        return

    cur.execute(
        """
        SELECT tag_id
        FROM finance_installment_plan_tags
        WHERE plan_id=%s
        ORDER BY tag_id;
        """,
        (plan_id,),
    )
    tag_ids = [int(row["tag_id"]) for row in cur.fetchall()]

    remaining_numbers = [
        number
        for number in range(baseline_completed + 1, total + 1)
        if number not in confirmed_numbers
    ]
    if not remaining_numbers:
        return

    base_due = plan["next_due_date"]
    standard_amount = Decimal(plan["installment_amount"])
    zero_cost = (
        Decimal(plan["annual_interest_rate"]) == 0
        and Decimal(plan["fees_total"]) == 0
    )
    balance_after_confirmed = max(
        Decimal("0.00"),
        Decimal(plan["remaining_balance"]) - confirmed_amount,
    )

    for position, installment_number in enumerate(remaining_numbers):
        offset = installment_number - (baseline_completed + 1)
        due = base_due
        for _ in range(offset):
            due = _next_date(
                due,
                plan["frequency_unit"],
                int(plan["frequency_interval"]),
            )

        amount = standard_amount
        if zero_cost and position == len(remaining_numbers) - 1:
            previous_count = max(0, len(remaining_numbers) - 1)
            adjusted = (
                balance_after_confirmed
                - standard_amount * Decimal(previous_count)
            )
            if adjusted > 0:
                amount = adjusted.quantize(Decimal("0.01"))

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
                budget_excluded,
                bank_programmed,
                reminder_enabled,
                reminder_time,
                installment_plan_id,
                installment_number
            )
            VALUES (
                %s,%s,'expense',%s,%s,%s,%s,'planned',%s,
                'unreconciled',%s,FALSE,FALSE,'09:00',%s,%s
            )
            RETURNING id;
            """,
            (
                user_id,
                due,
                amount,
                plan["description"],
                plan.get("category_id"),
                _plan_transaction_note(plan, installment_number),
                plan.get("payment_method_id"),
                bool(plan.get("budget_excluded")),
                plan_id,
                installment_number,
            ),
        )
        transaction_id = int(cur.fetchone()["id"])
        for tag_id in tag_ids:
            cur.execute(
                """
                INSERT INTO finance_transaction_tags (
                    transaction_id,
                    tag_id
                )
                VALUES (%s,%s)
                ON CONFLICT DO NOTHING;
                """,
                (transaction_id, tag_id),
            )


def _save_installment_plan_v111(
    user_id,
    *,
    plan_type,
    provider_name,
    description,
    original_amount,
    total_installments,
    next_due_date,
    payment_method_id,
    category_id=None,
    tag_ids=None,
    purchase_date=None,
    completed_installments=0,
    remaining_balance=None,
    installment_amount=None,
    annual_interest_rate=0,
    fees_total=0,
    frequency_unit="month",
    frequency_interval=1,
    budget_excluded=False,
    note=None,
    plan_id=None,
    FREQUENCY_UNITS,
    INSTALLMENT_PLAN_TYPES,
    _automatic_installment_amount,
    _decimal_value,
    _money,
    _optional_date_value,
    _rebuild_installment_transactions,
    _text,
    _validate_links,
    _validate_payment_method,
    analyze_installment_progress,
    get_connection,
):
    if plan_type not in INSTALLMENT_PLAN_TYPES:
        raise ValueError("Type de financement invalide.")
    provider_name = _text(
        provider_name,
        "Le commerçant ou programme",
        120,
        True,
    )
    description = _text(description, "La description", 160, True)
    original = _money(original_amount)
    try:
        total_count = int(total_installments)
    except (TypeError, ValueError) as error:
        raise ValueError("Le nombre total de versements est invalide.") from error
    if total_count < 1 or total_count > 1200:
        raise ValueError("Le nombre total de versements doit être entre 1 et 1200.")

    purchase = _optional_date_value(purchase_date, "La date d’achat")
    next_due = _optional_date_value(
        next_due_date,
        "La prochaine échéance",
    )

    interest_rate = _decimal_value(
        annual_interest_rate,
        "Le taux d’intérêt",
        allow_blank=True,
    ) or Decimal("0.00")
    if interest_rate < 0:
        raise ValueError("Le taux d’intérêt ne peut pas être négatif.")
    fees = _decimal_value(
        fees_total,
        "Les frais",
        allow_blank=True,
    ) or Decimal("0.00")
    if fees < 0:
        raise ValueError("Les frais ne peuvent pas être négatifs.")

    if frequency_unit not in FREQUENCY_UNITS:
        raise ValueError("Fréquence invalide.")
    try:
        interval = int(frequency_interval or 1)
    except (TypeError, ValueError) as error:
        raise ValueError("L’intervalle de fréquence est invalide.") from error
    if interval < 1 or interval > 365:
        raise ValueError("L’intervalle de fréquence est invalide.")

    supplied_completed = completed_installments not in (None, "")
    completed_count = None
    if supplied_completed:
        try:
            completed_count = int(completed_installments)
        except (TypeError, ValueError) as error:
            raise ValueError("Le nombre de versements déjà effectués est invalide.") from error
        if completed_count < 0 or completed_count > total_count:
            raise ValueError("Le nombre de versements déjà effectués est invalide.")

    provisional_remaining = (
        _money(remaining_balance, allow_zero=True)
        if remaining_balance not in (None, "")
        else None
    )
    provisional_payment = (
        _money(installment_amount)
        if installment_amount not in (None, "")
        else None
    )

    # Si le nombre déjà effectué est inconnu mais que le solde et le versement
    # sont disponibles, on estime la progression avant de générer l’échéancier.
    progress = analyze_installment_progress(
        original_amount=original,
        remaining_balance=provisional_remaining,
        installment_amount=provisional_payment,
        total_installments=total_count,
        completed_installments=completed_count if supplied_completed else None,
    )
    completed_estimated = (not supplied_completed and provisional_remaining is not None)
    if completed_count is None:
        completed_count = int(progress["estimated_completed_installments"] or 0)

    remaining_count = total_count - completed_count
    if remaining_count > 0 and next_due is None:
        raise ValueError("Indiquez la date du prochain versement.")

    if provisional_remaining is None:
        if completed_count == 0:
            remaining = original
        else:
            remaining = max(
                Decimal("0.00"),
                (original - (Decimal(completed_count) * (provisional_payment or (original / Decimal(total_count))))).quantize(Decimal("0.01")),
            )
    else:
        remaining = provisional_remaining

    if remaining_count == 0:
        remaining = Decimal("0.00")

    if provisional_payment is None:
        payment = _automatic_installment_amount(
            remaining,
            remaining_count,
            interest_rate,
            fees,
            frequency_unit,
            interval,
        )
        if payment <= 0 and remaining_count:
            raise ValueError("Le montant du versement ne peut pas être calculé.")
    else:
        payment = provisional_payment

    note = _text(note, "La note", 1000)

    with get_connection() as conn:
        with conn.cursor() as cur:
            tags = _validate_links(cur, user_id, category_id, tag_ids)
            method_id = _validate_payment_method(
                cur,
                user_id,
                payment_method_id,
            )
            if method_id is None:
                raise ValueError("Choisissez le mode de paiement des versements.")
            cur.execute(
                """
                SELECT method_type
                FROM finance_payment_methods
                WHERE id=%s AND user_id=%s;
                """,
                (method_id, user_id),
            )
            method = cur.fetchone()
            if plan_type == "credit_card" and (
                not method or method["method_type"] != "credit_card"
            ):
                raise ValueError(
                    "Un plan de versements sur carte doit être associé à une carte de crédit."
                )

            is_active = completed_count < total_count
            if plan_id:
                cur.execute(
                    """
                    UPDATE finance_installment_plans
                    SET plan_type=%s,
                        provider_name=%s,
                        description=%s,
                        original_amount=%s,
                        purchase_date=%s,
                        total_installments=%s,
                        completed_installments=%s,
                        completed_installments_estimated=%s,
                        remaining_balance=%s,
                        installment_amount=%s,
                        annual_interest_rate=%s,
                        fees_total=%s,
                        frequency_unit=%s,
                        frequency_interval=%s,
                        next_due_date=%s,
                        payment_method_id=%s,
                        category_id=%s,
                        budget_excluded=%s,
                        note=%s,
                        is_active=%s,
                        updated_at=NOW()
                    WHERE id=%s AND user_id=%s;
                    """,
                    (
                        plan_type,
                        provider_name,
                        description,
                        original,
                        purchase,
                        total_count,
                        completed_count,
                        completed_estimated,
                        remaining,
                        payment,
                        interest_rate,
                        fees,
                        frequency_unit,
                        interval,
                        next_due,
                        method_id,
                        category_id,
                        bool(budget_excluded),
                        note,
                        is_active,
                        plan_id,
                        user_id,
                    ),
                )
                if cur.rowcount == 0:
                    raise ValueError("Plan de financement introuvable.")
                saved_id = int(plan_id)
            else:
                cur.execute(
                    """
                    INSERT INTO finance_installment_plans (
                        user_id,
                        plan_type,
                        provider_name,
                        description,
                        original_amount,
                        purchase_date,
                        total_installments,
                        completed_installments,
                        completed_installments_estimated,
                        remaining_balance,
                        installment_amount,
                        annual_interest_rate,
                        fees_total,
                        frequency_unit,
                        frequency_interval,
                        next_due_date,
                        payment_method_id,
                        category_id,
                        budget_excluded,
                        note,
                        is_active
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                    )
                    RETURNING id;
                    """,
                    (
                        user_id,
                        plan_type,
                        provider_name,
                        description,
                        original,
                        purchase,
                        total_count,
                        completed_count,
                        completed_estimated,
                        remaining,
                        payment,
                        interest_rate,
                        fees,
                        frequency_unit,
                        interval,
                        next_due,
                        method_id,
                        category_id,
                        bool(budget_excluded),
                        note,
                        is_active,
                    ),
                )
                saved_id = int(cur.fetchone()["id"])

            cur.execute(
                "DELETE FROM finance_installment_plan_tags WHERE plan_id=%s;",
                (saved_id,),
            )
            for tag_id in tags:
                cur.execute(
                    """
                    INSERT INTO finance_installment_plan_tags (plan_id, tag_id)
                    VALUES (%s,%s);
                    """,
                    (saved_id, tag_id),
                )

            _rebuild_installment_transactions(cur, user_id, saved_id)
            conn.commit()
            return saved_id


def toggle_installment_plan(user_id, plan_id, is_active, *, _rebuild_installment_transactions, get_connection):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE finance_installment_plans
                SET is_active=%s, updated_at=NOW()
                WHERE id=%s AND user_id=%s;
                """,
                (bool(is_active), plan_id, user_id),
            )
            if cur.rowcount == 0:
                raise ValueError("Plan de financement introuvable.")
            if is_active:
                _rebuild_installment_transactions(cur, user_id, plan_id)
            else:
                cur.execute(
                    """
                    DELETE FROM finance_transactions
                    WHERE user_id=%s
                      AND installment_plan_id=%s
                      AND status='planned'
                      AND reconciliation_status='unreconciled';
                    """,
                    (user_id, plan_id),
                )
            conn.commit()


def delete_installment_plan(user_id, plan_id, *, get_connection):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM finance_installment_plans
                WHERE id=%s AND user_id=%s
                FOR UPDATE;
                """,
                (plan_id, user_id),
            )
            if not cur.fetchone():
                raise ValueError("Plan de financement introuvable.")
            cur.execute(
                """
                DELETE FROM finance_transactions
                WHERE user_id=%s
                  AND installment_plan_id=%s
                  AND status='planned'
                  AND reconciliation_status='unreconciled';
                """,
                (user_id, plan_id),
            )
            # Les versements déjà confirmés sont conservés dans l'historique.
            cur.execute(
                """
                UPDATE finance_transactions
                SET installment_plan_id=NULL,
                    installment_number=NULL,
                    updated_at=NOW()
                WHERE user_id=%s
                  AND installment_plan_id=%s
                  AND status='confirmed';
                """,
                (user_id, plan_id),
            )
            cur.execute(
                """
                DELETE FROM finance_installment_plans
                WHERE id=%s AND user_id=%s;
                """,
                (plan_id, user_id),
            )
            conn.commit()


def save_installment_plan(
    user_id,
    *,
    plan_type,
    provider_name,
    description,
    original_amount,
    total_installments,
    next_due_date,
    payment_method_id,
    plan_id=None,
    purchase_date=None,
    completed_installments=0,
    remaining_balance=None,
    installment_amount=None,
    annual_interest_rate=0,
    fees_total=0,
    frequency_unit="month",
    frequency_interval=1,
    category_id=None,
    tag_ids=None,
    budget_excluded=False,
    note=None,
    payment_includes_interest=True,
    _automatic_installment_amount,
    _decimal_value,
    _money,
    _save_installment_plan_v111,
    analyze_installment_progress,
    get_connection,
):
    """Enregistre un financement; calcule le versement total si intérêts exclus."""

    rate = _decimal_value(annual_interest_rate, "Le taux d’intérêt", allow_blank=True) or Decimal("0.00")
    base_payment = (
        _money(installment_amount)
        if installment_amount not in (None, "")
        else None
    )
    includes = bool(payment_includes_interest) or rate <= 0
    calculated = None
    actual_payment = base_payment
    completed_for_save = completed_installments
    completed_was_estimated_here = False

    if rate > 0 and not includes:
        total_count = int(total_installments or 0)
        if completed_installments not in (None, ""):
            completed = int(completed_installments or 0)
        elif (
            base_payment is not None
            and remaining_balance not in (None, "")
            and total_count > 0
        ):
            progress = analyze_installment_progress(
                original_amount=original_amount,
                remaining_balance=remaining_balance,
                installment_amount=base_payment,
                total_installments=total_count,
                completed_installments=None,
            )
            completed = int(progress["estimated_completed_installments"])
            # Le calcul des intérêts doit utiliser la progression estimée avec le
            # montant de base saisi. On transmet donc cette progression au moteur
            # V1.11 afin qu'il ne la réestime pas avec le versement total calculé.
            completed_for_save = completed
            completed_was_estimated_here = True
        else:
            completed = 0
        remaining_count = max(1, total_count - completed)
        principal = (
            _money(remaining_balance, allow_zero=True)
            if remaining_balance not in (None, "")
            else _money(original_amount)
        )
        calculated = _automatic_installment_amount(
            principal,
            remaining_count,
            rate,
            _decimal_value(fees_total, "Les frais", allow_blank=True) or Decimal("0.00"),
            frequency_unit,
            int(frequency_interval or 1),
        )
        actual_payment = calculated

    saved_id = _save_installment_plan_v111(
        user_id,
        plan_type=plan_type,
        provider_name=provider_name,
        description=description,
        original_amount=original_amount,
        total_installments=total_installments,
        next_due_date=next_due_date,
        payment_method_id=payment_method_id,
        plan_id=plan_id,
        purchase_date=purchase_date,
        completed_installments=completed_for_save,
        remaining_balance=remaining_balance,
        installment_amount=actual_payment,
        annual_interest_rate=annual_interest_rate,
        fees_total=fees_total,
        frequency_unit=frequency_unit,
        frequency_interval=frequency_interval,
        category_id=category_id,
        tag_ids=tag_ids,
        budget_excluded=budget_excluded,
        note=note,
    )
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE finance_installment_plans
                SET payment_includes_interest=%s,
                    base_installment_amount=%s,
                    calculated_installment_amount=%s,
                    completed_installments_estimated=CASE
                        WHEN %s THEN TRUE
                        ELSE completed_installments_estimated
                    END,
                    updated_at=NOW()
                WHERE id=%s AND user_id=%s;
                """,
                (
                    includes,
                    base_payment if base_payment is not None else actual_payment,
                    calculated,
                    completed_was_estimated_here,
                    saved_id,
                    user_id,
                ),
            )
            conn.commit()
    return saved_id
