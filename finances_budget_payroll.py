"""Ajustement des paies réelles pour la capacité variable du Budget.

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
    """Calcule l'écart entre les paies confirmées et le Budget.

    Une seule transaction est retenue par occurrence de récurrence. Si des
    doublons existent, la transaction ayant le plus grand identifiant gagne,
    ce qui évite de multiplier accidentellement un même dépôt de paie.
    """
    if recurrence_id in (None, "") or expected_per_pay in (None, ""):
        return {
            "realized_pay_count": 0,
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

        if row.get("status") not in (None, "confirmed"):
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
        current_id = int(current.get("id") or 0) if current else -1
        row_id = int(row.get("id") or 0)
        if current is None or row_id >= current_id:
            by_occurrence[occurrence] = row

    actual_total = sum(
        (
            Decimal(row.get("amount") or 0)
            for row in by_occurrence.values()
        ),
        ZERO,
    ).quantize(CENT)

    realized_count = len(by_occurrence)
    expected_total = (
        expected * Decimal(realized_count)
    ).quantize(CENT)
    adjustment = (
        actual_total - expected_total
    ).quantize(CENT)

    return {
        "realized_pay_count": realized_count,
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
    """Lit les revenus confirmés du mois et calcule l'écart de paie."""
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
        status="confirmed",
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
