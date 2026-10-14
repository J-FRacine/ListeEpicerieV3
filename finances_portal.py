from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation


PORTAL_REMINDER_LOOKAHEAD_DAYS = 3


def _as_date(value):
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _money_text(value):
    try:
        amount = Decimal(str(value or 0)).copy_abs().quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return ""
    return f"{amount:,.2f} $".replace(",", " ").replace(".", ",")


def _relative_due_text(due_date, today_value):
    delta = (due_date - today_value).days
    if delta < 0:
        days = abs(delta)
        return "En retard de 1 jour" if days == 1 else f"En retard de {days} jours"
    if delta == 0:
        return "Prévu aujourd’hui"
    if delta == 1:
        return "Prévu demain"
    return f"Prévu dans {delta} jours"


def collect_finance_portal_reminders(
    user_id,
    *,
    list_transactions_fn=None,
    list_recurrences_fn=None,
    today_value=None,
    lookahead_days=PORTAL_REMINDER_LOOKAHEAD_DAYS,
):
    if list_transactions_fn is None or list_recurrences_fn is None:
        from finances_data import (
            list_recurrences as db_list_recurrences,
            list_transactions as db_list_transactions,
        )
        if list_transactions_fn is None:
            list_transactions_fn = db_list_transactions
        if list_recurrences_fn is None:
            list_recurrences_fn = db_list_recurrences

    today_value = today_value or date.today()
    lookahead_days = max(0, int(lookahead_days))
    horizon = today_value + timedelta(days=lookahead_days)

    future_rows = list_transactions_fn(
        user_id,
        start_date=today_value,
        end_date=horizon,
        include_linked_transfer_destinations=False,
        limit=500,
    )
    overdue_rows = list_transactions_fn(
        user_id,
        status="planned",
        end_date=today_value - timedelta(days=1),
        include_linked_transfer_destinations=False,
        limit=500,
    )
    transaction_rows = list(overdue_rows or []) + list(future_rows or [])

    reminders = []
    materialized_recurrences = set()

    for row in transaction_rows:
        if not bool(row.get("reminder_enabled")):
            continue

        status = str(row.get("status") or "").strip()
        if status == "planned" and bool(row.get("bank_programmed")):
            continue

        due_date = _as_date(row.get("transaction_date"))
        if due_date is None or due_date > horizon:
            continue
        if due_date < today_value and status != "planned":
            continue

        recurrence_id = row.get("recurrence_id")
        if recurrence_id:
            materialized_recurrences.add((int(recurrence_id), due_date))

        reminders.append({
            "kind": "transaction",
            "id": row.get("id"),
            "recurrence_id": recurrence_id,
            "due_date": due_date,
            "description": str(row.get("description") or "Transaction").strip(),
            "amount_text": _money_text(row.get("amount")),
            "payment_method_name": str(row.get("payment_method_name") or "").strip(),
            "relative_text": _relative_due_text(due_date, today_value),
            "days_until_due": (due_date - today_value).days,
            "can_mark_done": row.get("id") not in (None, ""),
        })

    for row in list_recurrences_fn(user_id) or []:
        if not bool(row.get("is_active", True)):
            continue
        if not bool(row.get("reminder_enabled")):
            continue

        due_date = _as_date(row.get("next_date"))
        if due_date is None or due_date > horizon:
            continue

        recurrence_id = row.get("id")
        if recurrence_id and (int(recurrence_id), due_date) in materialized_recurrences:
            continue

        reminders.append({
            "kind": "recurrence",
            "id": recurrence_id,
            "recurrence_id": recurrence_id,
            "due_date": due_date,
            "description": str(row.get("description") or "Récurrence").strip(),
            "amount_text": _money_text(row.get("amount")),
            "payment_method_name": str(row.get("payment_method_name") or "").strip(),
            "relative_text": _relative_due_text(due_date, today_value),
            "days_until_due": (due_date - today_value).days,
            "can_mark_done": recurrence_id not in (None, ""),
        })

    reminders.sort(key=lambda row: (
        row["due_date"],
        str(row["description"]).casefold(),
        str(row.get("id") or ""),
    ))
    return reminders


def mark_finance_portal_item_done(user_id, *, kind, item_id, due_date=None):
    from db import get_connection
    from finances_portal_writes import (
        mark_recurrence_occurrence_programmed,
        mark_transaction_done_from_portal,
    )

    if kind == "recurrence":
        return mark_recurrence_occurrence_programmed(
            user_id,
            item_id,
            due_date,
            get_connection=get_connection,
        )

    return mark_transaction_done_from_portal(
        user_id,
        item_id,
        get_connection=get_connection,
    )


def finances_portal_reminder(user_id, *, ui_module=None, today_value=None):
    if ui_module is None:
        from nicegui import ui as ui_module

    try:
        rows = collect_finance_portal_reminders(user_id, today_value=today_value)
    except Exception as error:
        print("Avis Finances du Portail indisponibles :", error)
        return

    if not rows:
        return

    def mark_done(row):
        try:
            result = mark_finance_portal_item_done(
                user_id,
                kind=row["kind"],
                item_id=row["id"],
                due_date=row["due_date"],
            )
        except Exception as error:
            ui_module.notify(
                str(error) or "Impossible de modifier cette échéance.",
                type="negative",
            )
            return

        ui_module.notify(
            "Échéance marquée comme programmée. Le rappel est retiré."
            if result.get("bank_programmed")
            else "Rappel retiré.",
            type="positive",
        )
        ui_module.navigate.to("/?tab=portail")

    with ui_module.element("div").classes(
        "w-full mt-3 rounded-xl border border-orange-200 bg-orange-50 px-3 py-3"
    ):
        with ui_module.row().classes(
            "w-full items-start justify-between gap-3 flex-wrap"
        ):
            with ui_module.column().classes("gap-1 grow min-w-0"):
                with ui_module.row().classes("items-center gap-2"):
                    ui_module.icon("notifications_active").classes(
                        "text-orange-700 text-xl"
                    )
                    ui_module.label("Échéances Finances").classes(
                        "font-bold text-orange-900"
                    )
                ui_module.label(
                    "Transactions et paiements marqués pour rappel "
                    f"dans les {PORTAL_REMINDER_LOOKAHEAD_DAYS} prochains jours."
                ).classes("text-xs text-orange-800")

            ui_module.button(
                "Ouvrir Finances",
                icon="account_balance_wallet",
                on_click=lambda: ui_module.navigate.to(
                    "/?tab=finances&section=historique"
                ),
            ).props("flat dense no-caps color=primary")

        for row in rows:
            with ui_module.row().classes(
                "w-full items-center gap-2 flex-nowrap py-1"
            ):
                icon = "warning" if row["days_until_due"] < 0 else "event"
                ui_module.icon(icon).classes("text-orange-700 text-lg shrink-0")

                with ui_module.column().classes("gap-0 grow min-w-0"):
                    title = row["description"]
                    if row["amount_text"]:
                        title += f" — {row['amount_text']}"
                    ui_module.label(title).classes(
                        "text-sm font-semibold whitespace-normal"
                    ).style("overflow-wrap:anywhere;")

                    details = [row["relative_text"]]
                    if row["payment_method_name"]:
                        details.append(row["payment_method_name"])
                    ui_module.label(" · ".join(details)).classes(
                        "text-xs text-orange-800"
                    )

                if row.get("can_mark_done"):
                    ui_module.button(
                        "Fait",
                        icon="task_alt",
                        on_click=lambda _event, selected=row: mark_done(selected),
                    ).props(
                        "outline dense no-caps color=positive"
                    ).classes("shrink-0")
