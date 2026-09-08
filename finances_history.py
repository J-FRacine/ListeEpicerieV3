from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable


@dataclass
class HistoryPanelHandle:
    start: Any
    end: Any
    query: Any
    amount_exact: Any
    amount_min: Any
    amount_max: Any
    transaction_type: Any
    status: Any
    reconciliation: Any
    category: Any
    tag: Any
    payment: Any
    history_box: Any


def build_history_panel(
    *,
    ui,
    user_id,
    month_value,
    today_value,
    TRANSACTION_TYPES,
    TRANSACTION_STATUSES,
    RECONCILIATION_STATUSES,
    category_options: Callable[[], dict],
    tag_options: Callable[[], dict],
    payment_options: Callable[[], dict],
    on_apply: Callable[[], None],
    on_duplicate_search: Callable[[], None],
    on_monthly_unreconciled: Callable[[], None],
) -> HistoryPanelHandle:
    """Construit les filtres et le conteneur de l'Historique."""

    with ui.card().classes("w-full p-3"):
        ui.label("Historique compact").classes("text-lg font-bold")

        with ui.expansion(
            "Filtres",
            icon="filter_alt",
        ).classes("w-full"):
            with ui.element("div").classes("jf-finance-form-grid"):
                start = ui.input(
                    label="Du",
                    value=month_value.isoformat(),
                ).props(
                    "type=date dense outlined"
                ).classes("jf-finance-field")

                end = ui.input(
                    label="Au",
                    value=today_value.isoformat(),
                ).props(
                    "type=date dense outlined"
                ).classes("jf-finance-field")

                query = ui.input(
                    label="Recherche"
                ).props(
                    "dense outlined clearable"
                ).classes(
                    "jf-finance-field jf-finance-description"
                )

                amount_exact = ui.input(
                    label="Montant exact"
                ).props(
                    "dense outlined clearable inputmode=decimal"
                ).classes("jf-finance-field")

                amount_min = ui.input(
                    label="Montant min."
                ).props(
                    "dense outlined clearable inputmode=decimal"
                ).classes("jf-finance-field")

                amount_max = ui.input(
                    label="Montant max."
                ).props(
                    "dense outlined clearable inputmode=decimal"
                ).classes("jf-finance-field")

            with ui.row().classes("w-full gap-2 flex-wrap"):
                transaction_type = ui.select(
                    {
                        "": "Tous les types",
                        **TRANSACTION_TYPES,
                    },
                    value="",
                    label="Type",
                ).props(
                    "dense outlined options-dense"
                ).classes("min-w-40 grow")

                status = ui.select(
                    {
                        "": "Tous les statuts",
                        **TRANSACTION_STATUSES,
                    },
                    value="",
                    label="Transaction",
                ).props(
                    "dense outlined options-dense"
                ).classes("min-w-40 grow")

                reconciliation = ui.select(
                    {
                        "": "Toutes",
                        **RECONCILIATION_STATUSES,
                    },
                    value="",
                    label="Conciliation",
                ).props(
                    "dense outlined options-dense"
                ).classes("min-w-40 grow")

            with ui.row().classes("w-full gap-2 flex-wrap"):
                category = ui.select(
                    {
                        None: "Toutes",
                        **category_options(),
                    },
                    value=None,
                    label="Catégorie",
                ).props(
                    "dense outlined clearable options-dense"
                ).classes("min-w-52 grow")

                tag = ui.select(
                    {
                        None: "Toutes",
                        **tag_options(),
                    },
                    value=None,
                    label="Étiquette",
                ).props(
                    "dense outlined clearable options-dense"
                ).classes("min-w-44 grow")

                payment = ui.select(
                    {
                        None: "Tous",
                        **payment_options(),
                    },
                    value=None,
                    label="Mode de paiement",
                ).props(
                    "dense outlined clearable options-dense"
                ).classes("min-w-48 grow")

            with ui.row().classes("w-full gap-2 flex-wrap"):
                ui.button(
                    "Appliquer",
                    icon="filter_alt",
                    on_click=on_apply,
                ).props("outline dense color=primary")

                ui.button(
                    "Rechercher les doublons",
                    icon="content_copy",
                    on_click=on_duplicate_search,
                ).props("outline dense color=secondary")

                ui.button(
                    "Vérifier les non conciliées du mois",
                    icon="rule",
                    on_click=on_monthly_unreconciled,
                ).props("outline dense color=secondary")

    history_box = ui.column().classes(
        "jf-finance-history-list mt-2"
    )

    return HistoryPanelHandle(
        start=start,
        end=end,
        query=query,
        amount_exact=amount_exact,
        amount_min=amount_min,
        amount_max=amount_max,
        transaction_type=transaction_type,
        status=status,
        reconciliation=reconciliation,
        category=category,
        tag=tag,
        payment=payment,
        history_box=history_box,
    )


def render_history(
    *,
    ui,
    panel: HistoryPanelHandle,
    user_id,
    list_transactions,
    render_transaction_row,
    money,
) -> None:
    """Rend la liste filtrée de l'Historique sans gérer les dialogues."""

    history_box = panel.history_box
    history_box.clear()

    try:
        rows = list_transactions(
            user_id,
            start_date=panel.start.value or None,
            end_date=panel.end.value or None,
            transaction_type=panel.transaction_type.value or None,
            category_id=panel.category.value or None,
            tag_id=panel.tag.value or None,
            status=panel.status.value or None,
            payment_method_id=panel.payment.value or None,
            reconciliation_status=panel.reconciliation.value or None,
            query=panel.query.value or None,
            amount_exact=panel.amount_exact.value or None,
            amount_min=panel.amount_min.value or None,
            amount_max=panel.amount_max.value or None,
            include_linked_transfer_destinations=False,
        )
    except Exception as error:
        with history_box:
            ui.label(str(error)).classes("text-negative")
        return

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["transaction_date"]].append(row)

    with history_box:
        if not rows:
            ui.label(
                "Aucune transaction."
            ).classes(
                "text-sm jf-muted p-3"
            )
            return

        for day in sorted(grouped, reverse=True):
            day_rows = grouped[day]
            expenses = [
                row
                for row in day_rows
                if row["transaction_type"] == "expense"
            ]
            incomes = [
                row
                for row in day_rows
                if row["transaction_type"] == "income"
            ]

            with ui.element("section").classes(
                "jf-finance-history-day"
            ):
                with ui.element("div").classes("jf-finance-day"):
                    ui.label(day.strftime("%d/%m/%Y"))
                    ui.label(
                        f"{len(day_rows)} transaction(s)"
                    ).classes("text-xs jf-muted")

                with ui.element("div").classes(
                    "jf-finance-history-columns"
                ):
                    with ui.element("div").classes(
                        "jf-finance-history-column"
                    ):
                        with ui.element("div").classes(
                            "jf-finance-history-heading"
                        ):
                            ui.label("Dépenses")
                            ui.label(
                                money(
                                    sum(
                                        (
                                            Decimal(row["amount"])
                                            for row in expenses
                                        ),
                                        Decimal("0.00"),
                                    )
                                )
                            ).classes("text-right")

                        if expenses:
                            for row in expenses:
                                render_transaction_row(row)
                        else:
                            ui.label(
                                "Aucune dépense"
                            ).classes(
                                "jf-finance-empty-column"
                            )

                    with ui.element("div").classes(
                        "jf-finance-history-column"
                    ):
                        with ui.element("div").classes(
                            "jf-finance-history-heading"
                        ):
                            ui.label("Revenus")
                            ui.label(
                                money(
                                    sum(
                                        (
                                            Decimal(row["amount"])
                                            for row in incomes
                                        ),
                                        Decimal("0.00"),
                                    )
                                )
                            ).classes("text-right")

                        if incomes:
                            for row in incomes:
                                render_transaction_row(row)
                        else:
                            ui.label(
                                "Aucun revenu"
                            ).classes(
                                "jf-finance-empty-column"
                            )
