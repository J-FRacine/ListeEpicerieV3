"""Soldes et projections de Compte, sans accès direct à la base de données.

Les lectures et la construction des lignes projetées sont injectées à l'appel.
Les points d'entrée historiques de finances_data assurent cette liaison.
"""
from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from finances_calculations import (
    add_months as _add_months,
    month_start as _month_start,
    next_date as _next_date,
)


def list_bank_accounts(user_id, include_inactive=False, *, list_payment_methods):
    """Retourne les comptes suivis dans la vue Compte : banque et marge de crédit."""
    return [
        row for row in list_payment_methods(user_id, include_inactive=include_inactive)
        if row.get("method_type") in {"bank", "credit_line"}
    ]


def _bank_effective_rows(
    user_id, payment_method_id, end_date, today_value=None, *,
    list_bank_accounts, list_transactions, list_recurrences, _projection_row,
):
    today = (
        today_value if isinstance(today_value, date)
        else date.fromisoformat(str(today_value)) if today_value
        else date.today()
    )
    accounts = list_bank_accounts(user_id, include_inactive=True)
    account = next(
        (row for row in accounts if int(row["id"]) == int(payment_method_id)),
        None,
    )
    if not account:
        raise ValueError("Compte bancaire ou marge de crédit introuvable.")
    opening_date = account.get("opening_balance_date")
    if not opening_date:
        return account, [], None
    if opening_date > end_date:
        return account, [], opening_date

    existing = [
        dict(row)
        for row in list_transactions(
            user_id,
            start_date=opening_date,
            end_date=end_date,
            payment_method_id=payment_method_id,
            limit=100000,
        )
    ]
    existing_occurrences = {
        (int(row["recurrence_id"]), row.get("occurrence_date") or row["transaction_date"])
        for row in existing if row.get("recurrence_id")
    }
    rows = []
    for row in existing:
        # Les transactions prévues dont la date est passée demeurent visibles.
        # Elles représentent un mouvement encore attendu, mais ne sont pas
        # incluses dans le solde ACTUEL tant qu'elles ne sont pas confirmées.
        row["projected"] = False
        rows.append(row)

    if end_date > today:
        for recurrence in list_recurrences(user_id):
            if not recurrence["is_active"]:
                continue
            if int(recurrence.get("payment_method_id") or 0) != int(payment_method_id):
                continue
            occurrence = recurrence.get("next_date") or recurrence["start_date"]
            while occurrence <= today:
                occurrence = _next_date(
                    occurrence,
                    recurrence["frequency_unit"],
                    recurrence["frequency_interval"],
                )
            while occurrence <= end_date:
                if recurrence.get("end_date") and occurrence > recurrence["end_date"]:
                    break
                key = (int(recurrence["id"]), occurrence)
                if key not in existing_occurrences and occurrence >= opening_date:
                    rows.append(
                        _projection_row(
                            transaction_date=occurrence,
                            transaction_type=recurrence["transaction_type"],
                            amount=recurrence["amount"],
                            description=recurrence["description"],
                            category_id=recurrence.get("category_id"),
                            category_full_name=recurrence.get("category_full_name"),
                            tag_ids=recurrence.get("tag_ids"),
                            tag_names=recurrence.get("tag_names"),
                            payment_method_id=payment_method_id,
                            payment_method_name=account["name"],
                            recurrence_id=recurrence["id"],
                            occurrence_date=occurrence,
                            status="planned",
                            projected=True,
                            budget_excluded=bool(recurrence.get("budget_excluded")),
                            bank_programmed=bool(recurrence.get("bank_programmed")),
                            reminder_enabled=bool(recurrence.get("reminder_enabled")),
                            reminder_time=recurrence.get("reminder_time"),
                        )
                    )
                occurrence = _next_date(
                    occurrence,
                    recurrence["frequency_unit"],
                    recurrence["frequency_interval"],
                )
    rows.sort(
        key=lambda row: (
            row["transaction_date"],
            0 if row["transaction_type"] == "income" else 1,
            int(row.get("id") or 0),
            str(row["description"]).casefold(),
        )
    )
    return account, rows, opening_date


def _signed_transaction_amount(row, method_type="bank"):
    amount = Decimal(row["amount"])
    if method_type == "credit_line":
        # Sur une marge, une dépense augmente la dette et un revenu/remboursement
        # la réduit. Le solde affiché représente donc le montant utilisé.
        return amount if row["transaction_type"] == "expense" else -amount
    return amount if row["transaction_type"] == "income" else -amount


def bank_cashflow_month(
    user_id, payment_method_id, month_value, today_value=None, *,
    list_bank_accounts, list_transactions, list_recurrences, _projection_row,
):
    month = _month_start(month_value)
    next_month = _add_months(month, 1)
    month_end = next_month - timedelta(days=1)
    today = (
        today_value if isinstance(today_value, date)
        else date.fromisoformat(str(today_value)) if today_value
        else date.today()
    )
    account, rows, opening_date = _bank_effective_rows(
        user_id, payment_method_id, month_end, today_value=today,
        list_bank_accounts=list_bank_accounts,
        list_transactions=list_transactions,
        list_recurrences=list_recurrences,
        _projection_row=_projection_row,
    )
    if not opening_date or opening_date > month_end:
        return {
            "account": account, "month": month, "month_end": month_end,
            "available": False, "opening_date": opening_date, "rows": [],
        }

    method_type = account.get("method_type") or "bank"
    opening_balance = Decimal(account.get("opening_balance") or 0)
    balance = opening_balance

    # Solde actuel = uniquement les mouvements confirmés jusqu'à aujourd'hui.
    current_balance = opening_balance if opening_date <= today else None
    if current_balance is not None:
        for row in rows:
            tx_date = row["transaction_date"]
            if tx_date > today:
                break
            if row.get("status") == "confirmed" and not row.get("projected"):
                current_balance += _signed_transaction_amount(row, method_type)

    start_balance = balance
    display_rows = []
    minimum_balance = None
    maximum_balance = None

    for row in rows:
        tx_date = row["transaction_date"]
        if tx_date < month:
            balance += _signed_transaction_amount(row, method_type)
            start_balance = balance
            continue
        if tx_date > month_end:
            continue
        balance += _signed_transaction_amount(row, method_type)
        display = dict(row)
        display["running_balance"] = balance
        display_rows.append(display)
        if minimum_balance is None or balance < minimum_balance:
            minimum_balance = balance
        if maximum_balance is None or balance > maximum_balance:
            maximum_balance = balance

    if minimum_balance is None:
        minimum_balance = start_balance
    else:
        minimum_balance = min(start_balance, minimum_balance)
    if maximum_balance is None:
        maximum_balance = start_balance
    else:
        maximum_balance = max(start_balance, maximum_balance)

    result = {
        "account": account,
        "month": month,
        "month_end": month_end,
        "available": True,
        "opening_date": opening_date,
        "start_balance": start_balance,
        "current_balance": current_balance,
        "minimum_balance": minimum_balance,
        "maximum_balance": maximum_balance,
        "end_balance": balance,
        "rows": display_rows,
        "is_credit_line": method_type == "credit_line",
    }
    if method_type == "credit_line":
        limit = account.get("credit_limit")
        limit = Decimal(limit) if limit is not None else None
        result["credit_limit"] = limit
        result["current_available_credit"] = (
            limit - current_balance
            if limit is not None and current_balance is not None
            else None
        )
        result["minimum_available_credit"] = (
            limit - maximum_balance if limit is not None else None
        )
        result["end_available_credit"] = (
            limit - balance if limit is not None else None
        )
    return result


def bank_cashflow_year_summary(
    user_id, payment_method_id, year, today_value=None, *,
    list_bank_accounts, list_transactions, list_recurrences, _projection_row,
):
    year = int(year)
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    today = (
        today_value if isinstance(today_value, date)
        else date.fromisoformat(str(today_value)) if today_value
        else date.today()
    )
    account, rows, opening_date = _bank_effective_rows(
        user_id, payment_method_id, end, today_value=today,
        list_bank_accounts=list_bank_accounts,
        list_transactions=list_transactions,
        list_recurrences=list_recurrences,
        _projection_row=_projection_row,
    )
    if not opening_date or opening_date > end:
        return {"account": account, "year": year, "available": False, "months": []}
    method_type = account.get("method_type") or "bank"
    balance = Decimal(account.get("opening_balance") or 0)
    for row in rows:
        if row["transaction_date"] < start:
            balance += _signed_transaction_amount(row, method_type)
    by_month = defaultdict(list)
    for row in rows:
        if start <= row["transaction_date"] <= end:
            by_month[row["transaction_date"].month].append(row)
    months = []
    for month_number in range(1, 13):
        month_start = date(year, month_number, 1)
        month_end = date(year, month_number, monthrange(year, month_number)[1])
        if month_end < opening_date:
            months.append({
                "month": month_start,
                "month_end": month_end,
                "available": False,
                "start_balance": None,
                "minimum_balance": None,
                "maximum_balance": None,
                "end_balance": None,
            })
            continue
        start_balance = balance
        minimum = balance
        maximum = balance
        for row in by_month.get(month_number, []):
            balance += _signed_transaction_amount(row, method_type)
            minimum = min(minimum, balance)
            maximum = max(maximum, balance)
        month_row = {
            "month": month_start,
            "month_end": month_end,
            "available": True,
            "start_balance": start_balance,
            "minimum_balance": minimum,
            "maximum_balance": maximum,
            "end_balance": balance,
        }
        if method_type == "credit_line" and account.get("credit_limit") is not None:
            limit = Decimal(account["credit_limit"])
            month_row["end_available_credit"] = limit - balance
            month_row["minimum_available_credit"] = limit - maximum
        months.append(month_row)
    return {
        "account": account,
        "year": year,
        "available": True,
        "months": months,
        "is_credit_line": method_type == "credit_line",
    }
