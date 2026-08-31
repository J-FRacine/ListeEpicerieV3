from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

CENT = Decimal("0.01")


def money(value, *, allow_zero=False) -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(CENT)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Le montant est invalide.")
    if allow_zero:
        if amount < 0:
            raise ValueError("Le montant ne peut pas être négatif.")
    elif amount <= 0:
        raise ValueError("Le montant doit être supérieur à zéro.")
    return amount


def decimal_value(value, label, *, allow_blank=False):
    if value in (None, ""):
        if allow_blank:
            return None
        return Decimal("0.00")
    try:
        return Decimal(str(value)).quantize(CENT)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{label} est invalide.")


def text_value(value, label, maximum, *, required=False):
    cleaned = str(value or "").strip()
    if required and not cleaned:
        raise ValueError(f"{label} est obligatoire.")
    if len(cleaned) > maximum:
        raise ValueError(f"{label} ne peut pas dépasser {maximum} caractères.")
    return cleaned or None


def optional_date(value, label):
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise ValueError(f"{label} est invalide.") from error
