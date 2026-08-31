from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def month_start(value) -> date:
    """Normalise une valeur date/AAAA-MM au premier jour du mois."""
    if isinstance(value, date):
        return value.replace(day=1)
    text = str(value or "")
    if len(text) == 7:
        text += "-01"
    return date.fromisoformat(text).replace(day=1)


def add_months(value: date, months: int) -> date:
    """Décale une date en conservant son jour lorsque le mois le permet."""
    absolute = value.year * 12 + value.month - 1 + int(months)
    year, month_index = divmod(absolute, 12)
    month = month_index + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def next_date(current: date, unit: str, interval: int) -> date:
    """Occurrence suivante d'une récurrence JF Finances."""
    interval = int(interval)
    if unit == "day":
        return current + timedelta(days=interval)
    if unit == "week":
        return current + timedelta(weeks=interval)
    if unit == "month":
        return add_months(current, interval)
    if unit == "year":
        return add_months(current, interval * 12)
    raise ValueError("Fréquence invalide.")


def periods_per_year(unit: str, interval: int) -> Decimal:
    """Nombre théorique de versements par année pour une fréquence."""
    interval = max(1, int(interval or 1))
    if unit == "day":
        return Decimal("365") / Decimal(interval)
    if unit == "week":
        return Decimal("52") / Decimal(interval)
    if unit == "month":
        return Decimal("12") / Decimal(interval)
    if unit == "year":
        return Decimal("1") / Decimal(interval)
    return Decimal("12")


def automatic_installment_amount(
    principal,
    remaining_count,
    annual_interest_rate,
    fees_total,
    frequency_unit,
    frequency_interval,
) -> Decimal:
    """Versement amorti standard, arrondi au cent.

    Cette fonction ne fait aucune validation UI/DB; elle est volontairement
    pure afin que Budget, Financements et les tests utilisent le même calcul.
    """
    principal = Decimal(principal) + Decimal(fees_total)
    remaining_count = int(remaining_count)
    if remaining_count <= 0:
        return ZERO
    annual_rate = Decimal(annual_interest_rate) / Decimal("100")
    if annual_rate <= 0:
        return (principal / Decimal(remaining_count)).quantize(CENT)
    periods = periods_per_year(frequency_unit, frequency_interval)
    periodic = annual_rate / periods
    factor = (Decimal("1") + periodic) ** (-remaining_count)
    payment = principal * periodic / (Decimal("1") - factor)
    return payment.quantize(CENT)


def analyze_installment_progress(
    *,
    original_amount,
    remaining_balance,
    installment_amount,
    total_installments,
    completed_installments=None,
):
    """Estime la progression d'un plan à versements fixes.

    Le résultat est une aide à la saisie. Les intérêts, frais ou versements
    variables peuvent légitimement créer un écart avec cette estimation.
    """
    original = Decimal(str(original_amount or 0)).copy_abs().quantize(CENT)
    remaining = (
        Decimal(str(remaining_balance)).copy_abs().quantize(CENT)
        if remaining_balance not in (None, "")
        else None
    )
    total = int(total_installments or 0)
    payment = (
        Decimal(str(installment_amount)).copy_abs().quantize(CENT)
        if installment_amount not in (None, "")
        else None
    )
    if total <= 0:
        return {
            "estimated_completed_installments": 0,
            "estimated_remaining_installments": 0,
            "expected_remaining_balance": None,
            "balance_difference": None,
            "is_inconsistent": False,
        }

    if payment is None or payment <= 0:
        payment = (
            (original / Decimal(total)).quantize(CENT, rounding=ROUND_HALF_UP)
            if original > 0
            else None
        )

    estimated_completed = 0
    estimated_remaining = total
    if remaining is not None and payment and payment > 0:
        if remaining <= 0:
            estimated_remaining = 0
        else:
            estimated_remaining = int(
                (remaining / payment).to_integral_value(rounding=ROUND_CEILING)
            )
            estimated_remaining = max(0, min(total, estimated_remaining))
        estimated_completed = max(0, total - estimated_remaining)

        paid = max(ZERO, original - remaining)
        completed_from_paid = int(
            (paid / payment).to_integral_value(rounding=ROUND_HALF_UP)
        )
        completed_from_paid = max(0, min(total, completed_from_paid))
        expected_paid = (Decimal(completed_from_paid) * payment).quantize(CENT)
        if abs(paid - expected_paid) <= Decimal("0.02"):
            estimated_completed = completed_from_paid
            estimated_remaining = max(0, total - estimated_completed)

    expected_remaining = None
    difference = None
    inconsistent = False
    if completed_installments not in (None, "") and payment and payment > 0:
        manual_completed = max(0, min(total, int(completed_installments)))
        expected_remaining = max(
            ZERO,
            (original - Decimal(manual_completed) * payment).quantize(CENT),
        )
        if remaining is not None:
            difference = (remaining - expected_remaining).quantize(CENT)
            inconsistent = abs(difference) > Decimal("0.02")

    return {
        "estimated_completed_installments": estimated_completed,
        "estimated_remaining_installments": estimated_remaining,
        "expected_remaining_balance": expected_remaining,
        "balance_difference": difference,
        "is_inconsistent": inconsistent,
    }


def recurrence_dates_between(recurrence, start_date: date, end_date: date):
    """Occurrences réelles d'une récurrence dans une période inclusive.

    Pour les fréquences fixes en jours/semaines, ``next_date`` est l'ancrage
    opérationnel. On peut reculer depuis cet ancrage pour les mois antérieurs,
    ce qui conserve le cycle exact d'une paie aux deux semaines.
    """
    if not recurrence or not recurrence.get("is_active"):
        return []

    unit = recurrence["frequency_unit"]
    interval = int(recurrence.get("frequency_interval") or 1)
    recurrence_start = recurrence.get("start_date")
    recurrence_end = recurrence.get("end_date")
    anchor = recurrence.get("next_date")

    if recurrence_end and recurrence_end < start_date:
        return []

    if anchor and unit in {"day", "week"}:
        step_days = interval if unit == "day" else interval * 7
        occurrence = anchor
        safety = 0
        while occurrence > start_date and safety < 2000:
            candidate = occurrence - timedelta(days=step_days)
            if candidate < start_date:
                break
            if recurrence_start and candidate < recurrence_start:
                break
            occurrence = candidate
            safety += 1
        while occurrence < start_date and safety < 4000:
            occurrence += timedelta(days=step_days)
            safety += 1
    else:
        occurrence = anchor or recurrence_start
        if not occurrence:
            return []
        safety = 0
        while occurrence < start_date and safety < 2000:
            occurrence = next_date(occurrence, unit, interval)
            safety += 1

    dates = []
    while occurrence <= end_date and safety < 6000:
        if recurrence_start and occurrence < recurrence_start:
            occurrence = next_date(occurrence, unit, interval)
            safety += 1
            continue
        if recurrence_end and occurrence > recurrence_end:
            break
        dates.append(occurrence)
        occurrence = next_date(occurrence, unit, interval)
        safety += 1
    return dates
