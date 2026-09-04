"""Résumé, capacité et prévisions Budget sans accès direct à PostgreSQL.

Les façades historiques injectent les services courants à chaque appel.
Les lectures détaillées, écritures et calculs de dépenses variables restent
chez le parent; aucune optimisation des KPI n'est effectuée ici.
"""
from datetime import date, timedelta
from decimal import Decimal

from finances_calculations import (
    add_months as _add_months,
    month_start as _month_start,
    recurrence_dates_between as _recurrence_dates_between,
)


def budget_summary(
    user_id, month_value=None, *,
    list_budget_items,
):
    month = _month_start(month_value or date.today())
    rows = list_budget_items(
        user_id,
        include_inactive=False,
        month_value=month,
        effective_only=True,
    )
    totals = {
        "month": month,
        "monthly_income": Decimal("0.00"),
        "monthly_expense": Decimal("0.00"),
        "biweekly_income": Decimal("0.00"),
        "biweekly_expense": Decimal("0.00"),
    }
    for row in rows:
        key = "income" if row["item_type"] == "income" else "expense"
        totals[f"monthly_{key}"] += Decimal(row["monthly_amount"])
        totals[f"biweekly_{key}"] += Decimal(row["biweekly_amount"])
    totals["monthly_remaining"] = (
        totals["monthly_income"] - totals["monthly_expense"]
    )
    totals["biweekly_remaining"] = (
        totals["biweekly_income"] - totals["biweekly_expense"]
    )
    totals["rows"] = rows
    return totals


def _budget_capacity_summary_v110(
    user_id, month_value, *,
    budget_summary, list_recurrences,
):
    """Capacité disponible pour les dépenses variables du mois affiché."""

    month = _month_start(month_value)
    month_end = _add_months(month, 1) - timedelta(days=1)
    summary = budget_summary(user_id, month)
    active_rows = summary["rows"]
    income_rows = [
        row for row in active_rows
        if row["item_type"] == "income"
    ]

    recurrence_by_id = {
        int(row["id"]): dict(row)
        for row in list_recurrences(user_id)
    }

    linked_income_rows = [
        row for row in income_rows
        if row.get("recurrence_id")
        and int(row["recurrence_id"]) in recurrence_by_id
    ]

    pay_dates = []
    source = "budget"
    if linked_income_rows:
        # Le poste de revenu principal est celui qui représente le plus gros
        # montant par paie. Cela évite qu'un remboursement ponctuel soit compté
        # comme une paie supplémentaire.
        primary_income = max(
            linked_income_rows,
            key=lambda row: Decimal(row["biweekly_amount"]),
        )
        recurrence = recurrence_by_id[int(primary_income["recurrence_id"])]
        pay_dates = _recurrence_dates_between(
            recurrence,
            month,
            month_end,
        )
        source = "recurrence"
    else:
        has_biweekly_income = any(
            row["input_frequency"] == "biweekly"
            for row in income_rows
        )
        if has_biweekly_income:
            # Si le poste Budget n'est pas lié explicitement, chercher une
            # récurrence de revenu active aux deux semaines. On privilégie
            # celle dont le montant est le plus proche du principal revenu
            # bihebdomadaire du Budget. Cela permet de détecter les mois à
            # trois paies sans exiger une liaison parfaite des anciennes données.
            target_amount = max(
                (Decimal(row["biweekly_amount"]) for row in income_rows),
                default=Decimal("0.00"),
            )
            candidates = [
                row for row in recurrence_by_id.values()
                if row.get("transaction_type") == "income"
                and row.get("is_active")
                and row.get("frequency_unit") == "week"
                and int(row.get("frequency_interval") or 1) == 2
            ]
            if candidates:
                recurrence = min(
                    candidates,
                    key=lambda row: (
                        abs(Decimal(row.get("amount") or 0) - target_amount),
                        -Decimal(row.get("amount") or 0),
                    ),
                )
                pay_dates = _recurrence_dates_between(
                    recurrence,
                    month,
                    month_end,
                )
                source = "recurrence_detected"
            else:
                # Sans aucun ancrage de calendrier fiable, conserver le repli
                # prudent de deux paies.
                pay_dates = [month, month]
                source = "fallback_2"

    if pay_dates:
        pay_count = len(pay_dates)
        available_month = (
            Decimal(summary["biweekly_remaining"])
            * Decimal(pay_count)
        )
    else:
        pay_count = 1 if income_rows else 0
        available_month = Decimal(summary["monthly_remaining"])
        source = "monthly"

    return {
        **summary,
        "pay_count": pay_count,
        "pay_dates": pay_dates,
        "pay_count_source": source,
        "remaining_per_pay": Decimal(summary["biweekly_remaining"]),
        "available_month": available_month,
    }


def budget_capacity_summary(
    user_id, month_value, *,
    _budget_capacity_summary_v110, get_finance_settings, _variable_expense_total_for_month,
):
    """Capacité variable avec report optionnel du solde mensuel."""

    month = _month_start(month_value)
    base = dict(_budget_capacity_summary_v110(user_id, month))
    base_available = Decimal(base["available_month"])
    settings = get_finance_settings(user_id)
    carry_enabled = bool(settings.get("carry_month_balance"))
    carry_start = settings.get("carry_start_month")
    carry_in = Decimal("0.00")

    if carry_enabled and carry_start:
        carry_start = _month_start(carry_start)
        if month > carry_start:
            cursor = carry_start
            safety = 0
            while cursor < month and safety < 600:
                cursor_base = _budget_capacity_summary_v110(
                    user_id,
                    cursor,
                )
                cursor_available = Decimal(cursor_base["available_month"])
                cursor_expenses = _variable_expense_total_for_month(
                    user_id,
                    cursor,
                )
                carry_in = (
                    cursor_available + carry_in - cursor_expenses
                ).quantize(Decimal("0.01"))
                cursor = _add_months(cursor, 1)
                safety += 1

    base["available_month_base"] = base_available
    base["carry_enabled"] = carry_enabled
    base["carry_start_month"] = carry_start
    base["carry_in"] = carry_in
    base["available_month"] = (
        base_available + carry_in
    ).quantize(Decimal("0.01"))
    return base


def budget_forecast(
    user_id, start_month, months=6, initial_capacity=None, *,
    budget_capacity_summary, _budget_capacity_summary_v110, _variable_expense_total_for_month, get_finance_settings,
):
    """Prévision de la capacité variable et du solde de fin de mois.

    ``initial_capacity`` permet de réutiliser la capacité déjà calculée pour
    le premier mois. Le report est ensuite propagé séquentiellement.
    Les dépenses variables restent calculées par
    ``_variable_expense_total_for_month()``, qui passe encore par
    ``_dashboard_month_projection_v190()`` et ses KPI. L'optimisation
    supplémentaire de ce chemin KPI n'est pas réalisée dans cette extraction.
    """

    start = _month_start(start_month)
    month_count = max(1, min(int(months or 6), 24))
    settings = get_finance_settings(user_id)
    carry_enabled = bool(settings.get("carry_month_balance"))
    carry_start = settings.get("carry_start_month")
    carry_start = _month_start(carry_start) if carry_start else None

    first_capacity = (
        dict(initial_capacity)
        if initial_capacity is not None
        else budget_capacity_summary(user_id, start)
    )
    carry = Decimal(first_capacity.get("carry_in", 0) or 0)
    result = []

    for offset in range(month_count):
        month = _add_months(start, offset)
        if offset == 0:
            capacity = first_capacity
        else:
            # Les mois suivants n'ont besoin que de la capacité de base.
            # Le report est déjà connu grâce au solde du mois précédent.
            capacity = _budget_capacity_summary_v110(user_id, month)
            if not (carry_enabled and carry_start and month > carry_start):
                carry = Decimal("0.00")

        base = Decimal(
            capacity.get("available_month_base", capacity["available_month"])
        )
        expenses = _variable_expense_total_for_month(user_id, month)
        ending = (base + carry - expenses).quantize(Decimal("0.01"))
        result.append(
            {
                "month": month,
                "available_base": base,
                "carry_in": carry,
                "variable_expenses": expenses,
                "ending_balance": ending,
                "pay_count": int(capacity.get("pay_count", 0)),
            }
        )

        # Le résultat d'un mois devient le report du mois suivant seulement à
        # partir du mois d'activation du report.
        if carry_enabled and carry_start and month >= carry_start:
            carry = ending
        else:
            carry = Decimal("0.00")

    return result
