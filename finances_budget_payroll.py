"""Ajustement des paies prévues ou réelles pour la capacité du Budget.

Ce module reste indépendant de PostgreSQL et de NiceGUI. Les lecteurs de
transactions sont injectés afin que les calculs puissent être testés sans DB.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal


CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def _as_date(value):
    if isinstance(value, date):
        return value
    if value in (None, ""):
        return None
    return date.fromisoformat(str(value))


def payroll_adjustment_from_transactions(
    rows,
    *,
    recurrence_id,
    expected_per_pay,
    month,
    month_end,
):
    """Calcule l'écart des occurrences matérialisées par rapport au Budget.

    Les transactions Prévue et Confirmée sont prises en compte lorsqu'elles
    appartiennent à la récurrence de revenu principale.

    Une occurrence normale au montant budgété produit un écart de 0.
    Une occurrence modifiée individuellement ajuste immédiatement la capacité
    du mois, même si elle est encore Prévue.

    Une seule transaction est retenue par occurrence de récurrence.
    """
    if recurrence_id in (None, "") or expected_per_pay in (None, ""):
        return {
            "realized_pay_count": 0,
            "adjusted_pay_count": 0,
            "actual_pay_total": ZERO,
            "expected_realized_pay_total": ZERO,
            "pay_actual_adjustment": ZERO,
        }

    recurrence_id = int(recurrence_id)
    expected = Decimal(expected_per_pay).quantize(CENT)
    start = _as_date(month)
    end = _as_date(month_end)

    by_occurrence = {}

    for raw in rows or []:
        row = dict(raw)

        status = row.get("status")
        if status not in (None, "planned", "confirmed"):
            continue
        if row.get("transaction_type") not in (None, "income"):
            continue

        row_recurrence_id = row.get("recurrence_id")
        if row_recurrence_id in (None, ""):
            continue
        if int(row_recurrence_id) != recurrence_id:
            continue

        occurrence = _as_date(
            row.get("occurrence_date")
            or row.get("transaction_date")
        )
        if occurrence is None or occurrence < start or occurrence > end:
            continue

        current = by_occurrence.get(occurrence)
        if current is None:
            by_occurrence[occurrence] = row
            continue

        current_status = current.get("status")
        if current_status != "confirmed" and status == "confirmed":
            by_occurrence[occurrence] = row
            continue

        if current_status == status:
            current_id = int(current.get("id") or 0)
            row_id = int(row.get("id") or 0)
            if row_id >= current_id:
                by_occurrence[occurrence] = row

    actual_total = sum(
        (
            Decimal(row.get("amount") or 0)
            for row in by_occurrence.values()
        ),
        ZERO,
    ).quantize(CENT)

    adjusted_count = len(by_occurrence)
    realized_count = sum(
        1
        for row in by_occurrence.values()
        if row.get("status") in (None, "confirmed")
    )

    expected_total = (
        expected * Decimal(adjusted_count)
    ).quantize(CENT)

    adjustment = (
        actual_total - expected_total
    ).quantize(CENT)

    return {
        "realized_pay_count": realized_count,
        "adjusted_pay_count": adjusted_count,
        "actual_pay_total": actual_total,
        "expected_realized_pay_total": expected_total,
        "pay_actual_adjustment": adjustment,
    }


def confirmed_primary_income_adjustment(
    user_id,
    *,
    month,
    month_end,
    recurrence_id,
    expected_per_pay,
    list_transactions,
):
    """Lit les occurrences prévues/confirmées et calcule leur écart au Budget.

    Le nom historique de cette fonction est conservé pour compatibilité avec
    les autres modules de Finances.
    """
    if recurrence_id in (None, "") or expected_per_pay in (None, ""):
        return payroll_adjustment_from_transactions(
            [],
            recurrence_id=recurrence_id,
            expected_per_pay=expected_per_pay,
            month=month,
            month_end=month_end,
        )

    rows = list_transactions(
        user_id,
        start_date=month,
        end_date=month_end,
        transaction_type="income",
        include_linked_transfer_destinations=False,
        limit=100000,
    )

    return payroll_adjustment_from_transactions(
        rows,
        recurrence_id=recurrence_id,
        expected_per_pay=expected_per_pay,
        month=month,
        month_end=month_end,
    )
