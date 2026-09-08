from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
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
@dataclass
class HistoryActions:
    remove_dialog: Callable[[dict], None]
    confirm_transaction: Callable[[int], None]
    change_reconciliation: Callable[[int, str], None]
    render_transaction_row: Callable[[dict], None]
    open_history_row: Callable[[dict], None]
    duplicate_search_dialog: Callable[[], None]
    monthly_unreconciled_dialog: Callable[[], None]
    add_month_label_end: Callable[[str], str]


def build_history_actions(
    *,
    ui,
    panel: HistoryPanelHandle,
    user_id,
    TRANSACTION_TYPES,
    TRANSACTION_STATUSES,
    RECONCILIATION_STATUSES,
    signed,
    money,
    delete_transaction,
    set_transaction_status,
    set_transaction_reconciliation,
    get_card_payment_transfer,
    get_transaction,
    card_payment_dialog,
    transaction_dialog,
    find_potential_duplicate_transactions,
    list_month_unreconciled_transactions,
    set_bank_transaction_seen,
    get_month_value,
    refresh_all,
) -> HistoryActions:
    """Construit les actions et dialogues de l'Historique."""

    def remove_dialog(row):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-md p-4"):
                ui.label(
                    "Supprimer cette transaction?"
                ).classes(
                    "text-lg font-bold"
                )
                ui.label(
                    f"{row['description']} — "
                    f"{signed(row['amount'], row['transaction_type'])}"
                )
                if row.get("linked_transfer_id"):
                    ui.label(
                        "Ce paiement est lié au compte bancaire et à la carte "
                        "de crédit. Les deux côtés seront supprimés ensemble."
                    ).classes("text-sm jf-muted")

                def remove():
                    try:
                        delete_transaction(
                            user_id,
                            row["id"],
                        )
                    except Exception as error:
                        ui.notify(
                            str(error),
                            type="warning",
                        )
                        return

                    dialog.close()
                    ui.notify(
                        "Transaction supprimée.",
                        type="positive",
                    )
                    refresh_all()

                with ui.row().classes(
                    "w-full justify-end gap-2"
                ):
                    ui.button(
                        "Annuler",
                        on_click=dialog.close,
                    ).props("flat")
                    ui.button(
                        "Supprimer",
                        icon="delete",
                        on_click=remove,
                    ).props("color=negative")

        dialog.open()

    def confirm_transaction(transaction_id):
        try:
            set_transaction_status(
                user_id,
                transaction_id,
                "confirmed",
            )
        except Exception as error:
            ui.notify(
                str(error),
                type="warning",
            )
            return

        ui.notify(
            "Transaction confirmée.",
            type="positive",
        )
        refresh_all()

    def change_reconciliation(
        transaction_id,
        current_status,
    ):
        new_status = (
            "unreconciled"
            if current_status == "reconciled"
            else "reconciled"
        )
        reconciliation_date = (
            date.today()
            if new_status == "reconciled"
            else None
        )

        try:
            set_transaction_reconciliation(
                user_id,
                transaction_id,
                new_status,
                reconciliation_date,
            )
        except Exception as error:
            ui.notify(
                str(error),
                type="warning",
            )
            return

        ui.notify(
            (
                "Transaction conciliée."
                if new_status == "reconciled"
                else "Transaction remise à concilier."
            ),
            type="positive",
        )
        refresh_all()

    def open_history_row(row):
        if row.get("linked_transfer_id"):
            try:
                transfer = get_card_payment_transfer(
                    user_id,
                    row["linked_transfer_id"],
                )
            except Exception as error:
                ui.notify(str(error), type="warning")
                return
            card_payment_dialog(
                user_id,
                refresh_all,
                transfer=transfer,
            )
        else:
            transaction_dialog(
                user_id,
                refresh_all,
                get_transaction(user_id, row["id"]),
            )

    def render_transaction_row(row):
        with ui.element("article").classes("jf-finance-row"):
            ui.label(
                row["description"]
            ).classes(
                "jf-finance-main"
            )

            meta = []
            if row["category_full_name"]:
                meta.append(row["category_full_name"])
            if row["tag_names"]:
                meta.append(" • ".join(row["tag_names"]))

            if (
                row.get("linked_transfer_id")
                and row.get("linked_transfer_role") == "source"
            ):
                meta.append(
                    (
                        f"{row.get('linked_transfer_source_name') or row.get('payment_method_name') or 'Compte'}"
                        f" → {row.get('linked_transfer_destination_name') or 'Carte'}"
                    )
                )
            elif row.get("payment_method_name"):
                meta.append(row["payment_method_name"])

            if row["status"] == "planned":
                meta.append("À confirmer")
            if row.get("budget_excluded"):
                meta.append("Hors budget")
            if row.get("bank_programmed"):
                meta.append("Programmé")
            if row.get("reminder_enabled"):
                meta.append(
                    "Rappel "
                    + str(row.get("reminder_time") or "09:00")[:5]
                )

            meta.append(
                RECONCILIATION_STATUSES.get(
                    row.get("reconciliation_status")
                    or "unreconciled",
                    "À concilier",
                )
            )

            ui.label(
                " — ".join(meta)
                or "Sans catégorie"
            ).classes(
                "jf-finance-meta"
            )

            amount_css = (
                "jf-finance-expense"
                if row["transaction_type"] == "expense"
                else "jf-finance-income"
            )
            ui.label(
                signed(
                    row["amount"],
                    row["transaction_type"],
                )
            ).classes(
                f"jf-finance-amount {amount_css}"
            )

            with ui.element("div").classes(
                "jf-finance-actions"
            ):
                if row["status"] == "planned":
                    ui.button(
                        icon="check",
                        on_click=(
                            lambda _event=None,
                            selected_id=row["id"]:
                            confirm_transaction(selected_id)
                        ),
                    ).props(
                        "flat dense round size=sm color=positive"
                    ).tooltip(
                        "Confirmer la transaction"
                    )

                reconciliation_icon = (
                    "undo"
                    if row.get("reconciliation_status")
                    == "reconciled"
                    else "done_all"
                )
                reconciliation_tooltip = (
                    "Remettre à concilier"
                    if row.get("reconciliation_status")
                    == "reconciled"
                    else "Marquer conciliée"
                )

                ui.button(
                    icon=reconciliation_icon,
                    on_click=(
                        lambda _event=None,
                        selected_id=row["id"],
                        current=row.get(
                            "reconciliation_status"
                        )
                        or "unreconciled":
                        change_reconciliation(
                            selected_id,
                            current,
                        )
                    ),
                ).props(
                    "flat dense round size=sm color=secondary"
                ).tooltip(
                    reconciliation_tooltip
                )

                if row.get("linked_transfer_id"):
                    ui.button(
                        icon="edit",
                        on_click=(
                            lambda _event=None,
                            selected=row:
                            open_history_row(selected)
                        ),
                    ).props(
                        "flat dense round size=sm color=primary"
                    ).tooltip(
                        "Modifier le paiement de carte"
                    )
                else:
                    ui.button(
                        icon="edit",
                        on_click=(
                            lambda _event=None,
                            selected=row:
                            open_history_row(selected)
                        ),
                    ).props(
                        "flat dense round size=sm color=primary"
                    ).tooltip(
                        "Modifier"
                    )

                ui.button(
                    icon="delete",
                    on_click=(
                        lambda _event=None,
                        selected=row:
                        remove_dialog(selected)
                    ),
                ).props(
                    "flat dense round size=sm color=negative"
                ).tooltip(
                    "Supprimer"
                )

    def duplicate_search_dialog():
        with ui.dialog() as duplicate_dialog:
            with ui.card().classes(
                "w-full max-w-5xl p-4"
            ):
                ui.label(
                    "Doublons potentiels"
                ).classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "Même montant exact avec des dates séparées de "
                    "2 jours ou moins. Aucune transaction n’est "
                    "supprimée automatiquement."
                ).classes(
                    "text-sm jf-muted"
                )

                with ui.element("div").classes(
                    "jf-finance-form-grid"
                ):
                    duplicate_start = ui.input(
                        label="Du — facultatif",
                        value=panel.start.value or "",
                    ).props(
                        "type=date dense outlined clearable"
                    ).classes(
                        "jf-finance-field"
                    )
                    duplicate_end = ui.input(
                        label="Au — facultatif",
                        value=panel.end.value or "",
                    ).props(
                        "type=date dense outlined clearable"
                    ).classes(
                        "jf-finance-field"
                    )

                same_type = ui.checkbox(
                    "Comparer seulement les transactions du même type "
                    "(dépense avec dépense, revenu avec revenu)",
                    value=True,
                )
                duplicate_results_box = ui.column().classes(
                    "w-full gap-2 mt-2"
                )

                @ui.refreshable
                def render_duplicate_results():
                    duplicate_results_box.clear()
                    try:
                        groups = find_potential_duplicate_transactions(
                            user_id,
                            start_date=(
                                duplicate_start.value or None
                            ),
                            end_date=(
                                duplicate_end.value or None
                            ),
                            same_type=bool(same_type.value),
                            window_days=2,
                        )
                    except Exception as error:
                        with duplicate_results_box:
                            ui.label(
                                str(error)
                            ).classes(
                                "text-negative"
                            )
                        return

                    with duplicate_results_box:
                        if not groups:
                            ui.label(
                                "Aucun doublon potentiel trouvé."
                            ).classes(
                                "text-sm text-positive p-3"
                            )
                            return

                        ui.label(
                            f"{len(groups)} groupe(s) de "
                            "doublons potentiels."
                        ).classes(
                            "text-sm font-semibold"
                        )

                        for group in groups:
                            with ui.card().classes(
                                "w-full p-3"
                            ):
                                group_type = (
                                    TRANSACTION_TYPES.get(
                                        group.get(
                                            "transaction_type"
                                        ),
                                        "Tous types",
                                    )
                                )
                                ui.label(
                                    f"{money(group['amount'])} "
                                    f"— {group_type}"
                                ).classes(
                                    "font-bold"
                                )

                                for candidate in group[
                                    "transactions"
                                ]:
                                    with ui.row().classes(
                                        "w-full items-center "
                                        "justify-between gap-2 "
                                        "flex-wrap border-t pt-2"
                                    ):
                                        with ui.column().classes(
                                            "gap-0 min-w-0 grow"
                                        ):
                                            ui.label(
                                                candidate[
                                                    "transaction_date"
                                                ].strftime(
                                                    "%d/%m/%Y"
                                                )
                                                + " — "
                                                + candidate[
                                                    "description"
                                                ]
                                            ).classes(
                                                "font-semibold"
                                            )

                                            meta = [
                                                candidate.get(
                                                    "category_full_name"
                                                )
                                                or "Sans catégorie",
                                                candidate.get(
                                                    "payment_method_name"
                                                )
                                                or "Sans mode",
                                                TRANSACTION_STATUSES.get(
                                                    candidate.get(
                                                        "status"
                                                    ),
                                                    candidate.get(
                                                        "status",
                                                        "",
                                                    ),
                                                ),
                                            ]
                                            if candidate.get(
                                                "import_source"
                                            ):
                                                meta.append(
                                                    "Source : "
                                                    + str(
                                                        candidate[
                                                            "import_source"
                                                        ]
                                                    )
                                                )
                                            ui.label(
                                                " — ".join(meta)
                                            ).classes(
                                                "text-xs jf-muted"
                                            )

                                        ui.label(
                                            signed(
                                                candidate["amount"],
                                                candidate[
                                                    "transaction_type"
                                                ],
                                            )
                                        ).classes(
                                            "font-bold"
                                        )

                                        with ui.row().classes(
                                            "gap-0"
                                        ):
                                            ui.button(
                                                icon="open_in_new",
                                                on_click=(
                                                    lambda _event=None,
                                                    selected=candidate:
                                                    open_history_row(
                                                        selected
                                                    )
                                                ),
                                            ).props(
                                                "flat dense round "
                                                "size=sm color=primary"
                                            ).tooltip(
                                                "Ouvrir / modifier"
                                            )

                                            def ask_delete(
                                                _event=None,
                                                selected=candidate,
                                            ):
                                                with ui.dialog() as delete_dialog:
                                                    with ui.card().classes(
                                                        "w-full max-w-md p-4"
                                                    ):
                                                        ui.label(
                                                            "Supprimer ce doublon potentiel ?"
                                                        ).classes(
                                                            "text-lg font-bold"
                                                        )
                                                        ui.label(
                                                            selected[
                                                                "description"
                                                            ]
                                                            + " — "
                                                            + signed(
                                                                selected[
                                                                    "amount"
                                                                ],
                                                                selected[
                                                                    "transaction_type"
                                                                ],
                                                            )
                                                        )

                                                        def delete_now():
                                                            try:
                                                                delete_transaction(
                                                                    user_id,
                                                                    selected[
                                                                        "id"
                                                                    ],
                                                                )
                                                            except Exception as error:
                                                                ui.notify(
                                                                    str(
                                                                        error
                                                                    ),
                                                                    type=(
                                                                        "warning"
                                                                    ),
                                                                )
                                                                return
                                                            delete_dialog.close()
                                                            ui.notify(
                                                                "Transaction supprimée.",
                                                                type=(
                                                                    "positive"
                                                                ),
                                                            )
                                                            render_duplicate_results.refresh()
                                                            refresh_all()

                                                        with ui.row().classes(
                                                            "w-full justify-end gap-2"
                                                        ):
                                                            ui.button(
                                                                "Annuler",
                                                                on_click=(
                                                                    delete_dialog.close
                                                                ),
                                                            ).props(
                                                                "flat"
                                                            )
                                                            ui.button(
                                                                "Supprimer",
                                                                icon="delete",
                                                                on_click=(
                                                                    delete_now
                                                                ),
                                                            ).props(
                                                                "color=negative"
                                                            )
                                                delete_dialog.open()

                                            ui.button(
                                                icon="delete",
                                                on_click=ask_delete,
                                            ).props(
                                                "flat dense round "
                                                "size=sm color=negative"
                                            ).tooltip(
                                                "Supprimer"
                                            )

                with ui.row().classes(
                    "w-full justify-between gap-2 mt-2 flex-wrap"
                ):
                    ui.button(
                        "Relancer la recherche",
                        icon="search",
                        on_click=lambda:
                        render_duplicate_results.refresh(),
                    ).props(
                        "outline color=primary"
                    )
                    ui.button(
                        "Fermer",
                        on_click=duplicate_dialog.close,
                    ).props("flat")

                duplicate_start.on_value_change(
                    lambda event:
                    render_duplicate_results.refresh()
                )
                duplicate_end.on_value_change(
                    lambda event:
                    render_duplicate_results.refresh()
                )
                same_type.on_value_change(
                    lambda event:
                    render_duplicate_results.refresh()
                )
                render_duplicate_results()

        duplicate_dialog.open()

    def add_month_label_end(month_text):
        month_start = date.fromisoformat(
            str(month_text) + "-01"
        )
        if month_start.month == 12:
            next_month = date(
                month_start.year + 1,
                1,
                1,
            )
        else:
            next_month = date(
                month_start.year,
                month_start.month + 1,
                1,
            )
        return (
            next_month - timedelta(days=1)
        ).isoformat()

    def monthly_unreconciled_dialog():
        with ui.dialog() as validation_dialog:
            with ui.card().classes(
                "w-full max-w-5xl p-4"
            ):
                ui.label(
                    "Vérifier les transactions non conciliées"
                ).classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "Cette liste sert à repérer les transactions "
                    "oubliées, en erreur ou potentiellement en double. "
                    "Une transaction non conciliée n’est pas "
                    "automatiquement une erreur."
                ).classes(
                    "text-sm jf-muted"
                )

                month_input = ui.input(
                    label="Mois à vérifier",
                    value=get_month_value().strftime("%Y-%m"),
                ).props(
                    "type=month dense outlined"
                ).classes(
                    "w-full max-w-xs"
                )
                monthly_box = ui.column().classes(
                    "w-full gap-2 mt-2"
                )

                @ui.refreshable
                def render_monthly_unreconciled():
                    monthly_box.clear()
                    try:
                        rows = (
                            list_month_unreconciled_transactions(
                                user_id,
                                month_input.value,
                            )
                        )
                        duplicate_groups = (
                            find_potential_duplicate_transactions(
                                user_id,
                                start_date=(
                                    month_input.value
                                    + "-01"
                                ),
                                end_date=(
                                    add_month_label_end(
                                        month_input.value
                                    )
                                ),
                                same_type=True,
                                window_days=2,
                            )
                        )
                    except Exception as error:
                        with monthly_box:
                            ui.label(
                                str(error)
                            ).classes(
                                "text-negative"
                            )
                        return

                    duplicate_ids = {
                        int(candidate["id"])
                        for group in duplicate_groups
                        for candidate
                        in group["transactions"]
                    }

                    grouped_rows = defaultdict(list)
                    for row in rows:
                        grouped_rows[
                            (
                                row.get(
                                    "payment_method_id"
                                ),
                                row.get(
                                    "payment_method_name"
                                )
                                or "Sans mode de paiement",
                                row.get(
                                    "payment_method_type"
                                ),
                            )
                        ].append(row)

                    with monthly_box:
                        if not rows:
                            ui.label(
                                "Aucune transaction non conciliée "
                                "pour ce mois."
                            ).classes(
                                "text-sm text-positive p-3"
                            )
                            return

                        ui.label(
                            f"{len(rows)} transaction(s) "
                            "confirmée(s) encore non conciliée(s)."
                        ).classes(
                            "font-semibold"
                        )

                        for (
                            _method_id,
                            method_name,
                            method_type,
                        ), method_rows in grouped_rows.items():
                            expenses = sum(
                                (
                                    Decimal(row["amount"])
                                    for row in method_rows
                                    if row[
                                        "transaction_type"
                                    ]
                                    == "expense"
                                ),
                                Decimal("0.00"),
                            )
                            incomes = sum(
                                (
                                    Decimal(row["amount"])
                                    for row in method_rows
                                    if row[
                                        "transaction_type"
                                    ]
                                    == "income"
                                ),
                                Decimal("0.00"),
                            )

                            with ui.card().classes(
                                "w-full p-3"
                            ):
                                ui.label(
                                    method_name
                                ).classes(
                                    "font-bold"
                                )
                                ui.label(
                                    f"{len(method_rows)} "
                                    "transaction(s) — Dépenses "
                                    f"{money(expenses)} — "
                                    "Revenus/crédits "
                                    f"{money(incomes)}"
                                ).classes(
                                    "text-xs jf-muted"
                                )

                                for row in sorted(
                                    method_rows,
                                    key=lambda item: (
                                        item[
                                            "transaction_date"
                                        ],
                                        int(item["id"]),
                                    ),
                                ):
                                    with ui.row().classes(
                                        "w-full items-center "
                                        "justify-between gap-2 "
                                        "border-t pt-2 flex-wrap"
                                    ):
                                        with ui.column().classes(
                                            "gap-0 min-w-0 grow"
                                        ):
                                            title = (
                                                row[
                                                    "transaction_date"
                                                ].strftime(
                                                    "%d/%m/%Y"
                                                )
                                                + " — "
                                                + row[
                                                    "description"
                                                ]
                                            )
                                            if (
                                                int(row["id"])
                                                in duplicate_ids
                                            ):
                                                title += (
                                                    " — doublon potentiel"
                                                )
                                            ui.label(
                                                title
                                            ).classes(
                                                "font-semibold"
                                            )

                                            source = ""
                                            if row.get(
                                                "import_source"
                                            ):
                                                source = (
                                                    " — Source : "
                                                    + str(
                                                        row[
                                                            "import_source"
                                                        ]
                                                    )
                                                )
                                            ui.label(
                                                (
                                                    row.get(
                                                        "category_full_name"
                                                    )
                                                    or "Sans catégorie"
                                                )
                                                + source
                                            ).classes(
                                                "text-xs jf-muted"
                                            )

                                        ui.label(
                                            signed(
                                                row["amount"],
                                                row[
                                                    "transaction_type"
                                                ],
                                            )
                                        ).classes(
                                            "font-bold"
                                        )

                                        with ui.row().classes(
                                            "gap-0"
                                        ):
                                            ui.button(
                                                icon="edit",
                                                on_click=(
                                                    lambda _event=None,
                                                    selected=row:
                                                    open_history_row(
                                                        selected
                                                    )
                                                ),
                                            ).props(
                                                "flat dense round "
                                                "size=sm color=primary"
                                            ).tooltip(
                                                "Modifier"
                                            )

                                            if method_type == "bank":

                                                def mark_seen(
                                                    _event=None,
                                                    selected=row,
                                                ):
                                                    try:
                                                        set_bank_transaction_seen(
                                                            user_id,
                                                            selected[
                                                                "id"
                                                            ],
                                                            True,
                                                            date.today(),
                                                        )
                                                    except Exception as error:
                                                        ui.notify(
                                                            str(
                                                                error
                                                            ),
                                                            type=(
                                                                "warning"
                                                            ),
                                                        )
                                                        return

                                                    ui.notify(
                                                        "Transaction marquée Vu.",
                                                        type=(
                                                            "positive"
                                                        ),
                                                    )
                                                    render_monthly_unreconciled.refresh()
                                                    refresh_all()

                                                ui.button(
                                                    icon="done_all",
                                                    on_click=(
                                                        mark_seen
                                                    ),
                                                ).props(
                                                    "flat dense round "
                                                    "size=sm "
                                                    "color=positive"
                                                ).tooltip(
                                                    "Marquer Vu"
                                                )

                        if duplicate_ids:
                            ui.label(
                                f"{len(duplicate_ids)} "
                                "transaction(s) de ce mois "
                                "appartiennent à au moins un "
                                "groupe de doublons potentiels."
                            ).classes(
                                "text-xs text-warning"
                            )

                def refresh_month(_event=None):
                    render_monthly_unreconciled.refresh()

                month_input.on_value_change(
                    refresh_month
                )

                with ui.row().classes(
                    "w-full justify-between gap-2 mt-2 flex-wrap"
                ):
                    ui.button(
                        "Rechercher les doublons",
                        icon="content_copy",
                        on_click=lambda:
                        duplicate_search_dialog(),
                    ).props(
                        "outline color=secondary"
                    )
                    ui.button(
                        "Fermer",
                        on_click=validation_dialog.close,
                    ).props("flat")

                render_monthly_unreconciled()

        validation_dialog.open()

    return HistoryActions(
        remove_dialog=remove_dialog,
        confirm_transaction=confirm_transaction,
        change_reconciliation=change_reconciliation,
        render_transaction_row=render_transaction_row,
        open_history_row=open_history_row,
        duplicate_search_dialog=duplicate_search_dialog,
        monthly_unreconciled_dialog=monthly_unreconciled_dialog,
        add_month_label_end=add_month_label_end,
    )
