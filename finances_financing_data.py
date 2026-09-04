"""Lectures et calculs des plans de financement.

Les accès externes sont injectés par les façades de ``finances_data`` afin que
ce module reste indépendant de PostgreSQL et de l'interface.
"""
from datetime import timedelta
from decimal import Decimal

from finances_calculations import add_months, month_start, next_date


def _list_installment_plans_v111(
    user_id, include_inactive=True, *, get_connection, next_date, FREQUENCY_UNITS
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    plan.*,
                    payment_method.name AS payment_method_name,
                    payment_method.method_type AS payment_method_type,
                    CASE
                        WHEN parent.id IS NULL THEN category.name
                        ELSE parent.name || ' › ' || category.name
                    END AS category_full_name,
                    COALESCE(
                        ARRAY_AGG(tag.id ORDER BY tag.name)
                        FILTER (WHERE tag.id IS NOT NULL),
                        ARRAY[]::BIGINT[]
                    ) AS tag_ids,
                    COALESCE(
                        ARRAY_AGG(tag.name ORDER BY tag.name)
                        FILTER (WHERE tag.id IS NOT NULL),
                        ARRAY[]::TEXT[]
                    ) AS tag_names,
                    (
                        SELECT COUNT(*)
                        FROM finance_transactions AS tx
                        WHERE tx.installment_plan_id=plan.id
                          AND tx.status='confirmed'
                    ) AS confirmed_tracked_count,
                    (
                        SELECT COUNT(*)
                        FROM finance_transactions AS tx
                        WHERE tx.installment_plan_id=plan.id
                          AND tx.status='planned'
                    ) AS planned_count,
                    COALESCE((
                        SELECT SUM(tx.amount)
                        FROM finance_transactions AS tx
                        WHERE tx.installment_plan_id=plan.id
                          AND tx.status='confirmed'
                    ), 0) AS confirmed_tracked_amount
,
                    (
                        SELECT MIN(tx.transaction_date)
                        FROM finance_transactions AS tx
                        WHERE tx.installment_plan_id=plan.id
                          AND tx.status='planned'
                    ) AS next_planned_date
                FROM finance_installment_plans AS plan
                LEFT JOIN finance_payment_methods AS payment_method
                    ON payment_method.id=plan.payment_method_id
                LEFT JOIN finance_categories AS category
                    ON category.id=plan.category_id
                LEFT JOIN finance_categories AS parent
                    ON parent.id=category.parent_id
                LEFT JOIN finance_installment_plan_tags AS plan_tag
                    ON plan_tag.plan_id=plan.id
                LEFT JOIN finance_tags AS tag
                    ON tag.id=plan_tag.tag_id
                WHERE plan.user_id=%s
                  AND (%s OR plan.is_active=TRUE)
                GROUP BY
                    plan.id,
                    payment_method.id,
                    payment_method.name,
                    payment_method.method_type,
                    category.id,
                    parent.id,
                    parent.name
                ORDER BY
                    plan.is_active DESC,
                    plan.next_due_date NULLS LAST,
                    LOWER(plan.provider_name),
                    LOWER(plan.description),
                    plan.id;
                """,
                (user_id, include_inactive),
            )
            result = []
            for raw in cur.fetchall():
                row = dict(raw)
                confirmed_count = int(row.get("confirmed_tracked_count") or 0)
                completed = min(
                    int(row["total_installments"]),
                    int(row["completed_installments"]) + confirmed_count,
                )
                row["display_completed_installments"] = completed
                row["display_remaining_installments"] = max(
                    0,
                    int(row["total_installments"]) - completed,
                )
                confirmed_amount = Decimal(
                    row.get("confirmed_tracked_amount") or 0
                )
                if (
                    Decimal(row["annual_interest_rate"]) == 0
                    and Decimal(row["fees_total"]) == 0
                ):
                    row["estimated_remaining_balance"] = max(
                        Decimal("0.00"),
                        Decimal(row["remaining_balance"]) - confirmed_amount,
                    )
                else:
                    # Avec intérêts/frais, le capital restant réel dépend du
                    # relevé du fournisseur; on conserve donc le solde saisi.
                    row["estimated_remaining_balance"] = Decimal(
                        row["remaining_balance"]
                    )
                effective_next = row.get("next_planned_date") or row.get("next_due_date")
                row["display_next_due_date"] = effective_next
                remaining_display = int(row.get("display_remaining_installments") or 0)
                if effective_next and remaining_display > 0:
                    end_date = effective_next
                    for _ in range(max(0, remaining_display - 1)):
                        end_date = next_date(
                            end_date,
                            row["frequency_unit"],
                            int(row["frequency_interval"] or 1),
                        )
                    row["estimated_end_date"] = end_date
                else:
                    row["estimated_end_date"] = None
                unit_key = row.get("frequency_unit")
                interval = int(row.get("frequency_interval") or 1)
                if interval == 1:
                    row["payment_terms_label"] = {
                        "day": "Quotidien",
                        "week": "Hebdomadaire",
                        "month": "Mensuel",
                        "year": "Annuel",
                    }.get(unit_key, FREQUENCY_UNITS.get(unit_key, str(unit_key or "")))
                else:
                    plural_unit = {
                        "day": "jours",
                        "week": "semaines",
                        "month": "mois",
                        "year": "ans",
                    }.get(unit_key, str(FREQUENCY_UNITS.get(unit_key, unit_key or "")).lower())
                    row["payment_terms_label"] = f"Tous les {interval} {plural_unit}"
                row["progress_estimated"] = bool(
                    row.get("completed_installments_estimated", False)
                )
                result.append(row)
            return result


def list_installment_plans(
    user_id, include_inactive=True, *, _list_installment_plans_v111
):
    rows = [dict(row) for row in _list_installment_plans_v111(user_id, include_inactive)]
    for row in rows:
        rate = Decimal(row.get("annual_interest_rate") or 0)
        row["payment_includes_interest"] = bool(row.get("payment_includes_interest", True))
        row["base_installment_amount"] = Decimal(
            row.get("base_installment_amount") or row.get("installment_amount") or 0
        )
        row["calculated_installment_amount"] = (
            Decimal(row["calculated_installment_amount"])
            if row.get("calculated_installment_amount") is not None
            else None
        )
        if rate > 0 and not row["payment_includes_interest"]:
            total_payment = Decimal(row.get("installment_amount") or 0)
            base = Decimal(row.get("base_installment_amount") or 0)
            row["estimated_interest_per_payment"] = max(
                Decimal("0.00"), total_payment - base
            ).quantize(Decimal("0.01"))
        else:
            row["estimated_interest_per_payment"] = None
    return rows


def get_installment_plan(user_id, plan_id, *, list_installment_plans):
    rows = list_installment_plans(user_id, include_inactive=True)
    for row in rows:
        if int(row["id"]) == int(plan_id):
            return row
    raise ValueError("Plan de financement introuvable.")


def _project_installment_plan_payments_for_month(plan, month_value):
    """Calcule les échéances d'un financement dans un mois si elles ne sont pas matérialisées.

    Les transactions planifiées/confirmées restent prioritaires. Ce calcul sert de
    filet de sécurité pour les anciens plans ou une projection qui n'aurait pas
    encore généré ses lignes finance_transactions.
    """

    if not plan.get("is_active"):
        return Decimal("0.00"), 0

    month = month_start(month_value)
    month_end = add_months(month, 1) - timedelta(days=1)
    due = plan.get("display_next_due_date") or plan.get("next_due_date")
    remaining = int(plan.get("display_remaining_installments") or 0)
    if not due or remaining <= 0:
        return Decimal("0.00"), 0

    amount = Decimal(plan.get("installment_amount") or 0)
    balance = Decimal(
        plan.get("estimated_remaining_balance", plan.get("remaining_balance", 0))
        or 0
    )
    zero_cost = (
        Decimal(plan.get("annual_interest_rate") or 0) == 0
        and Decimal(plan.get("fees_total") or 0) == 0
    )
    total = Decimal("0.00")
    count = 0

    for position in range(remaining):
        if due > month_end:
            break
        if due >= month:
            payment = amount
            if zero_cost and position == remaining - 1:
                previous = amount * Decimal(max(0, remaining - 1))
                final_amount = balance - previous
                if final_amount > 0:
                    payment = final_amount.quantize(Decimal("0.01"))
            total += payment
            count += 1
        due = next_date(
            due,
            plan.get("frequency_unit") or "month",
            int(plan.get("frequency_interval") or 1),
        )

    return total.quantize(Decimal("0.01")), count


def financing_month_summary(
    user_id,
    month_value,
    *,
    get_connection,
    list_installment_plans,
    _project_installment_plan_payments_for_month,
):
    month = month_start(month_value)
    month_end = add_months(month, 1) - timedelta(days=1)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tx.installment_plan_id,
                       COALESCE(SUM(tx.amount),0) AS payments,
                       COUNT(*)::INTEGER AS payment_count
                FROM finance_transactions AS tx
                JOIN finance_installment_plans AS plan
                  ON plan.id=tx.installment_plan_id
                WHERE tx.user_id=%s
                  AND tx.transaction_type='expense'
                  AND tx.status IN ('planned','confirmed')
                  AND tx.transaction_date BETWEEN %s AND %s
                GROUP BY tx.installment_plan_id;
                """,
                (user_id, month, month_end),
            )
            materialized = {
                int(row["installment_plan_id"]): {
                    "payments": Decimal(row["payments"] or 0),
                    "payment_count": int(row["payment_count"] or 0),
                }
                for row in cur.fetchall()
            }

    plans = list_installment_plans(user_id, include_inactive=False)
    payments = Decimal("0.00")
    payment_count = 0
    for plan in plans:
        actual = materialized.get(int(plan["id"]))
        if actual is not None:
            payments += actual["payments"]
            payment_count += actual["payment_count"]
            continue
        projected, projected_count = _project_installment_plan_payments_for_month(
            plan, month
        )
        payments += projected
        payment_count += projected_count

    # Les transactions historiques d'un plan devenu inactif restent comptées
    # dans le mois où elles existent réellement.
    active_ids = {int(plan["id"]) for plan in plans}
    for plan_id, actual in materialized.items():
        if plan_id not in active_ids:
            payments += actual["payments"]
            payment_count += actual["payment_count"]

    remaining = sum(
        (Decimal(row.get("estimated_remaining_balance", row.get("remaining_balance", 0)))
         for row in plans),
        Decimal("0.00"),
    )
    return {
        "month": month,
        "payments": payments.quantize(Decimal("0.01")),
        "payment_count": int(payment_count),
        "remaining_balances": remaining.quantize(Decimal("0.01")),
        "active_plan_count": len(plans),
    }
