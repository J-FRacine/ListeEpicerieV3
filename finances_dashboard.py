"""Panneau Tableau construit avec ses services et le curseur mensuel partagé."""
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable


@dataclass
class DashboardPanelHandle:
    on_refresh: Callable[[], None]

    def refresh(self) -> None:
        self.on_refresh()


def build_dashboard_panel(
    *,
    ui,
    user_id,
    dashboard_tab,
    month_state,
    tabs,
    account_tab,
    reconciliation_tab,
    PAYMENT_METHOD_TYPES,
    dashboard_month_projection,
    budget_capacity_summary,
    goal_progress,
    payment_predicted_balance_summary,
    count_unassigned_confirmed_transactions,
    list_bank_accounts,
    bank_cashflow_month,
    get_transaction,
    set_month_carryover,
    _money,
    _balance_money,
    _month_label,
    _transaction_dialog,
    refresh_all,
) -> DashboardPanelHandle:
    # TABLEAU
    with ui.tab_panel(
        dashboard_tab
    ).classes(
        "px-0"
    ):
        dashboard_box = ui.column().classes(
            "w-full gap-2"
        )

        @ui.refreshable
        def render_dashboard():
            dashboard_box.clear()

            projection = dashboard_month_projection(
                user_id,
                month_state.value,
            )
            summary = {
                "expenses": projection["realized"]["expenses"],
                "planned_count": projection["upcoming"]["count"],
            }
            capacity = projection.get("capacity") or budget_capacity_summary(
                user_id, month_state.value
            )
            goals = goal_progress(
                user_id,
                month_state.value,
            )
            kpis = projection["kpis"]
            predicted_rows = payment_predicted_balance_summary(
                user_id
            )
            unassigned_count = count_unassigned_confirmed_transactions(
                user_id
            )
            bank_accounts = list_bank_accounts(user_id)
            cash_summary = None
            if bank_accounts:
                primary_account = next(
                    (
                        row for row in bank_accounts
                        if row.get("method_type") == "bank"
                    ),
                    bank_accounts[0],
                )
                try:
                    cash_summary = bank_cashflow_month(
                        user_id, int(primary_account["id"]), month_state.value
                    )
                except Exception:
                    cash_summary = None

            def open_kpi_detail(
                dimension,
                selected_kpi,
                transaction_type,
            ):
                selected_id = selected_kpi.get("id")
                selected_name = selected_kpi["name"]

                def matches(row):
                    if row["transaction_type"] != transaction_type:
                        return False
                    if bool(row.get("budget_excluded")):
                        return False
                    if transaction_type == "expense" and bool(row.get("fixed_budget")):
                        return False

                    if dimension == "category":
                        row_category_id = row.get("category_id")
                        if selected_id is None:
                            return row_category_id is None
                        return (
                            row_category_id is not None
                            and int(row_category_id) == int(selected_id)
                        )

                    row_tag_ids = [
                        int(value)
                        for value in (row.get("tag_ids") or [])
                        if value is not None
                    ]
                    if selected_id is not None:
                        return int(selected_id) in row_tag_ids

                    return selected_name.casefold() in {
                        str(value).casefold()
                        for value in (row.get("tag_names") or [])
                    }

                detail_rows = sorted(
                    (
                        row
                        for row in projection["transactions"]
                        if matches(row)
                    ),
                    key=lambda row: (
                        row["projection_bucket"] != "realized",
                        row["transaction_date"],
                        str(row["description"]).casefold(),
                    ),
                )

                realized_rows = [
                    row
                    for row in detail_rows
                    if row["projection_bucket"] == "realized"
                ]
                upcoming_rows = [
                    row
                    for row in detail_rows
                    if row["projection_bucket"] == "upcoming"
                ]
                realized_total = sum(
                    (
                        Decimal(row["amount"])
                        for row in realized_rows
                    ),
                    Decimal("0.00"),
                )
                upcoming_total = sum(
                    (
                        Decimal(row["amount"])
                        for row in upcoming_rows
                    ),
                    Decimal("0.00"),
                )

                with ui.dialog() as dialog:
                    with ui.card().classes(
                        "w-full max-w-4xl p-4"
                    ):
                        with ui.row().classes(
                            "w-full items-start justify-between gap-2"
                        ):
                            with ui.column().classes("gap-0 min-w-0"):
                                ui.label(
                                    selected_name
                                ).classes(
                                    "text-xl font-bold"
                                ).tooltip(
                                    selected_name
                                )
                                ui.label(
                                    (
                                        f"{_month_label(month_state.value)} — "
                                        + (
                                            "Catégorie"
                                            if dimension == "category"
                                            else "Étiquette"
                                        )
                                    )
                                ).classes(
                                    "text-sm jf-muted"
                                )
                            ui.button(
                                icon="close",
                                on_click=dialog.close,
                            ).props(
                                "flat round dense"
                            )

                        with ui.element("div").classes(
                            "jf-finance-kpi-detail-summary mt-2"
                        ):
                            for label, value, css in (
                                (
                                    "Réalisé",
                                    realized_total,
                                    (
                                        "jf-finance-expense"
                                        if transaction_type == "expense"
                                        else "jf-finance-income"
                                    ),
                                ),
                                (
                                    "À venir",
                                    upcoming_total,
                                    "jf-muted",
                                ),
                                (
                                    "Total prévu",
                                    realized_total + upcoming_total,
                                    (
                                        "jf-finance-expense"
                                        if transaction_type == "expense"
                                        else "jf-finance-income"
                                    ),
                                ),
                            ):
                                with ui.element("div").classes(
                                    "jf-finance-summary"
                                ):
                                    ui.label(label).classes(
                                        "jf-finance-summary-label"
                                    )
                                    ui.label(
                                        _money(value)
                                    ).classes(
                                        "jf-finance-summary-value "
                                        + css
                                    )

                        def edit_from_detail(transaction_id):
                            transaction = get_transaction(
                                user_id,
                                transaction_id,
                            )
                            if not transaction:
                                ui.notify(
                                    "Transaction introuvable.",
                                    type="warning",
                                )
                                return
                            dialog.close()
                            _transaction_dialog(
                                user_id,
                                refresh_all,
                                transaction,
                            )

                        def render_detail_group(
                            title,
                            rows,
                            *,
                            empty_message,
                        ):
                            ui.label(title).classes(
                                "text-base font-bold mt-2"
                            )
                            if not rows:
                                ui.label(
                                    empty_message
                                ).classes(
                                    "text-sm jf-muted"
                                )
                                return

                            with ui.element("div").classes(
                                "jf-finance-kpi-detail-list"
                            ):
                                for row in rows:
                                    with ui.element("div").classes(
                                        "jf-finance-kpi-detail-row"
                                    ):
                                        ui.label(
                                            row["transaction_date"].strftime(
                                                "%d/%m/%Y"
                                            )
                                        ).classes(
                                            "jf-finance-kpi-detail-date"
                                        )

                                        with ui.column().classes(
                                            "gap-0 min-w-0"
                                        ):
                                            ui.label(
                                                row["description"]
                                            ).classes(
                                                "jf-finance-kpi-detail-name"
                                            ).tooltip(
                                                row["description"]
                                            )
                                            meta_parts = []
                                            if dimension == "category":
                                                meta_parts.extend(
                                                    row.get("tag_names")
                                                    or []
                                                )
                                            else:
                                                if row.get(
                                                    "category_full_name"
                                                ):
                                                    meta_parts.append(
                                                        row[
                                                            "category_full_name"
                                                        ]
                                                    )
                                            if row.get(
                                                "payment_method_name"
                                            ):
                                                meta_parts.append(
                                                    row[
                                                        "payment_method_name"
                                                    ]
                                                )
                                            if row.get("projected"):
                                                meta_parts.append(
                                                    "Récurrence projetée"
                                                )
                                            elif row.get("status") == "planned":
                                                meta_parts.append(
                                                    "À confirmer"
                                                )
                                            ui.label(
                                                " • ".join(meta_parts)
                                                or "Transaction"
                                            ).classes(
                                                "jf-finance-kpi-detail-meta"
                                            )

                                        ui.label(
                                            _money(row["amount"])
                                        ).classes(
                                            "jf-finance-kpi-detail-amount "
                                            + (
                                                "jf-finance-expense"
                                                if transaction_type == "expense"
                                                else "jf-finance-income"
                                            )
                                        )

                                        with ui.element("div").classes(
                                            "jf-finance-kpi-detail-actions"
                                        ):
                                            if (
                                                row.get("id") is not None
                                                and not row.get("projected")
                                            ):
                                                ui.button(
                                                    icon="edit",
                                                    on_click=(
                                                        lambda _event=None,
                                                        selected_id=int(
                                                            row["id"]
                                                        ):
                                                        edit_from_detail(
                                                            selected_id
                                                        )
                                                    ),
                                                ).props(
                                                    "flat dense round "
                                                    "size=sm color=primary"
                                                ).tooltip(
                                                    "Ouvrir la transaction"
                                                )
                                            else:
                                                ui.icon(
                                                    "visibility"
                                                ).classes(
                                                    "text-sm jf-muted"
                                                ).tooltip(
                                                    "Projection consultative"
                                                )

                        render_detail_group(
                            "Réalisé",
                            realized_rows,
                            empty_message=(
                                "Aucune transaction réalisée."
                            ),
                        )
                        render_detail_group(
                            "À venir",
                            upcoming_rows,
                            empty_message=(
                                "Aucune transaction à venir."
                            ),
                        )

                dialog.open()

            with dashboard_box:
                with ui.row().classes(
                    "w-full items-center "
                    "justify-center gap-1"
                ):
                    ui.button(
                        icon="chevron_left",
                        on_click=lambda: (
                            change_month(-1)
                        ),
                    ).props(
                        "flat dense round"
                    )
                    ui.label(
                        _month_label(
                            month_state.value
                        )
                    ).classes(
                        "font-bold min-w-40 "
                        "text-center"
                    )
                    ui.button(
                        icon="chevron_right",
                        on_click=lambda: (
                            change_month(1)
                        ),
                    ).props(
                        "flat dense round"
                    )

                if cash_summary and cash_summary.get("available"):
                    is_credit_line = bool(cash_summary.get("is_credit_line"))
                    with ui.element("div").classes("jf-finance-bank-strip"):
                        with ui.row().classes("w-full items-center justify-between gap-2 flex-wrap"):
                            with ui.column().classes("gap-0"):
                                ui.label(
                                    ("Marge de crédit — " if is_credit_line else "Compte bancaire — ")
                                    + cash_summary["account"]["name"]
                                ).classes("font-bold")
                                ui.label(
                                    "Projection de la dette et du crédit disponible."
                                    if is_credit_line
                                    else "Projection de trésorerie incluant les mouvements hors budget."
                                ).classes("text-xs jf-muted")
                            ui.button("Voir le compte", icon="account_balance", on_click=lambda: tabs.set_value(account_tab)).props("flat dense color=primary")
                        with ui.element("div").classes("jf-finance-summary-grid mt-2"):
                            if is_credit_line:
                                current_debt = (
                                    cash_summary.get("current_balance")
                                    if cash_summary.get("current_balance") is not None
                                    else cash_summary["start_balance"]
                                )
                                bank_values = [
                                    ("Dette début", cash_summary["start_balance"]),
                                    ("Dette actuelle", current_debt),
                                    ("Plus haut prévu", cash_summary["maximum_balance"]),
                                    ("Dette fin de mois", cash_summary["end_balance"]),
                                ]
                                if cash_summary.get("end_available_credit") is not None:
                                    bank_values.append(
                                        ("Crédit disponible fin", cash_summary["end_available_credit"])
                                    )
                            else:
                                bank_values = [
                                    ("Solde début", cash_summary["start_balance"]),
                                    ("Solde actuel", cash_summary.get("current_balance") if cash_summary.get("current_balance") is not None else cash_summary["start_balance"]),
                                    ("Plus bas prévu", cash_summary["minimum_balance"]),
                                    ("Fin de mois prévue", cash_summary["end_balance"]),
                                ]
                            for bank_label, bank_value in bank_values:
                                with ui.element("div").classes("jf-finance-summary"):
                                    ui.label(bank_label).classes("jf-finance-summary-label")
                                    if is_credit_line and "Dette" in bank_label:
                                        css = "jf-finance-expense" if Decimal(bank_value) > 0 else "jf-finance-income"
                                    else:
                                        css = "jf-finance-expense" if Decimal(bank_value) < 0 else "jf-finance-income"
                                    ui.label(_balance_money(bank_value)).classes("jf-finance-summary-value " + css)
                elif bank_accounts:
                    with ui.element("div").classes("jf-finance-report-note"):
                        ui.label("Compte ou marge : indique un solde de référence et sa date dans Organisation > Modes de paiement pour activer la projection.").classes("text-sm")

                ui.label(
                    "Dépenses variables du mois"
                ).classes("text-lg font-bold mt-1")
                ui.label(
                    "Le Budget calcule d’abord ce qui reste après les dépenses fixes; "
                    "le Tableau suit l’utilisation de cette capacité."
                ).classes("text-xs jf-muted")

                pay_count = int(capacity.get("pay_count") or 0)
                carry_enabled = bool(capacity.get("carry_enabled"))
                carry_in = Decimal(capacity.get("carry_in") or 0)
                base_available = Decimal(
                    capacity.get(
                        "available_month_base",
                        capacity.get("available_month", 0),
                    )
                )
                adjusted_available = Decimal(
                    capacity.get("available_month", 0)
                )
                values = [
                    (
                        "Reste par paie",
                        capacity.get("remaining_per_pay", Decimal("0.00")),
                        "jf-finance-income"
                        if Decimal(capacity.get("remaining_per_pay", 0)) >= 0
                        else "jf-finance-expense",
                    ),
                ]
                if carry_enabled:
                    values.extend(
                        [
                            (
                                f"Disponible de base — {pay_count} paie(s)",
                                base_available,
                                "jf-finance-income"
                                if base_available >= 0
                                else "jf-finance-expense",
                            ),
                            (
                                "Report du mois précédent",
                                carry_in,
                                "jf-finance-income"
                                if carry_in >= 0
                                else "jf-finance-expense",
                            ),
                            (
                                "Disponible ajusté ce mois",
                                adjusted_available,
                                "jf-finance-income"
                                if adjusted_available >= 0
                                else "jf-finance-expense",
                            ),
                        ]
                    )
                else:
                    values.append(
                        (
                            f"Disponible ce mois — {pay_count} paie(s)",
                            adjusted_available,
                            "jf-finance-income"
                            if adjusted_available >= 0
                            else "jf-finance-expense",
                        )
                    )
                values.extend(
                    [
                        (
                            "Dépenses réalisées",
                            projection["realized"]["expenses"],
                            "jf-finance-expense",
                        ),
                        (
                            "Dépenses à venir",
                            projection["upcoming"]["expenses"],
                            "jf-finance-expense",
                        ),
                        (
                            "Total prévu variable",
                            projection["total"]["expenses"],
                            "jf-finance-expense",
                        ),
                        (
                            "Reste disponible ce mois",
                            projection.get(
                                "remaining_available", Decimal("0.00")
                            ),
                            "jf-finance-income"
                            if Decimal(
                                projection.get("remaining_available", 0)
                            ) >= 0
                            else "jf-finance-expense",
                        ),
                    ]
                )
                with ui.element("div").classes("jf-finance-summary-grid"):
                    for label, value, css in values:
                        with ui.element("div").classes("jf-finance-summary"):
                            ui.label(label).classes("jf-finance-summary-label")
                            # Contrairement à _money(), _balance_money()
                            # conserve explicitement le signe négatif.
                            ui.label(_balance_money(value)).classes(
                                "jf-finance-summary-value " + css
                            )

                carry_toggle = ui.checkbox(
                    "Reporter le solde positif ou négatif au mois suivant",
                    value=carry_enabled,
                ).classes("text-sm")

                def change_month_carry(event):
                    try:
                        set_month_carryover(
                            user_id,
                            bool(event.value),
                            month_state.value,
                        )
                    except Exception as error:
                        ui.notify(str(error), type="warning")
                        return
                    refresh_all()

                carry_toggle.on_value_change(change_month_carry)
                if carry_enabled and capacity.get("carry_start_month"):
                    ui.label(
                        "Report actif à partir de "
                        + _month_label(capacity["carry_start_month"])
                        + ". Le premier mois n’a pas de report entrant; "
                        "son solde final alimente le mois suivant."
                    ).classes("text-xs jf-muted")

                if capacity.get("pay_dates"):
                    ui.label(
                        "Paies du mois : "
                        + ", ".join(
                            value.strftime("%d/%m")
                            for value in capacity["pay_dates"]
                        )
                    ).classes("text-xs jf-muted")
                elif capacity.get("pay_count_source") == "fallback_2":
                    ui.label(
                        "Deux paies sont utilisées par défaut. Associez le revenu du Budget "
                        "à sa récurrence aux deux semaines pour détecter automatiquement les mois à 3 paies."
                    ).classes("text-xs jf-muted")

                upcoming_rows = projection[
                    "upcoming_transactions"
                ]
                if upcoming_rows:
                    ui.label(
                        "Transactions à venir"
                    ).classes(
                        "text-lg font-bold mt-1"
                    )

                    with ui.element("div").classes(
                        "jf-finance-summary-grid"
                    ):
                        for label, value, css in (
                            (
                                "Dépenses variables à venir",
                                projection["upcoming"]["expenses"],
                                "jf-finance-expense",
                            ),
                            (
                                "Total variable prévu",
                                projection["total"]["expenses"],
                                "jf-finance-expense",
                            ),
                            (
                                "Reste disponible après prévisions",
                                projection.get("remaining_available", Decimal("0.00")),
                                "jf-finance-income" if Decimal(projection.get("remaining_available", 0)) >= 0 else "jf-finance-expense",
                            ),
                        ):
                            with ui.element("div").classes(
                                "jf-finance-summary"
                            ):
                                ui.label(label).classes(
                                    "jf-finance-summary-label"
                                )
                                ui.label(
                                    _balance_money(value)
                                ).classes(
                                    "jf-finance-summary-value "
                                    + css
                                )

                    expense_count = sum(
                        1 for row in upcoming_rows
                        if row["transaction_type"] == "expense"
                    )
                    detail_label = (
                        f"Voir les dépenses à venir — {expense_count} dépense(s)"
                    )
                    with ui.expansion(
                        detail_label,
                        icon="event_note",
                        value=False,
                    ).classes("w-full jf-finance-card"):
                        with ui.element("div").classes(
                            "jf-finance-upcoming-grid"
                        ):
                            for transaction_type, title, css in (
                                (
                                    "expense",
                                    "Dépenses variables prévues",
                                    "jf-finance-expense",
                                ),
                            ):
                                rows = [
                                    row
                                    for row in upcoming_rows
                                    if row["transaction_type"]
                                    == transaction_type
                                ]
                                with ui.element("section").classes(
                                    "jf-finance-card"
                                ):
                                    ui.label(title).classes(
                                        "text-sm font-bold"
                                    )
                                    if not rows:
                                        ui.label(
                                            "Aucune transaction."
                                        ).classes(
                                            "text-xs jf-muted"
                                        )

                                    for row in rows:
                                        with ui.element("div").classes(
                                            "jf-finance-upcoming-row"
                                        ):
                                            ui.label(
                                                row[
                                                    "transaction_date"
                                                ].strftime("%d/%m")
                                            ).classes(
                                                "jf-finance-upcoming-date"
                                            )
                                            with ui.column().classes(
                                                "gap-0 min-w-0"
                                            ):
                                                ui.label(
                                                    row["description"]
                                                ).classes(
                                                    "jf-finance-upcoming-name"
                                                ).tooltip(
                                                    row["description"]
                                                )
                                                meta = []
                                                if row.get(
                                                    "linked_transfer_id"
                                                ) and row.get(
                                                    "linked_transfer_role"
                                                ) == "source":
                                                    meta.append(
                                                        (
                                                            f"{row.get('linked_transfer_source_name') or row.get('payment_method_name') or 'Compte'}"
                                                            f" → {row.get('linked_transfer_destination_name') or 'Carte'}"
                                                        )
                                                    )
                                                elif row.get(
                                                    "payment_method_name"
                                                ):
                                                    meta.append(
                                                        row[
                                                            "payment_method_name"
                                                        ]
                                                    )
                                                if row.get("projected"):
                                                    meta.append(
                                                        "Récurrence projetée"
                                                    )
                                                elif row.get("status") == "planned":
                                                    meta.append(
                                                        "À confirmer"
                                                    )
                                                if row.get("budget_excluded"):
                                                    meta.append("Hors budget")
                                                if row.get("bank_programmed"):
                                                    meta.append("Programmé")
                                                if row.get("installment_number"):
                                                    meta.append(
                                                        "Versement " + str(row["installment_number"])
                                                    )
                                                ui.label(
                                                    " — ".join(meta)
                                                    or "Transaction postdatée"
                                                ).classes(
                                                    "jf-finance-upcoming-meta"
                                                )
                                            ui.label(
                                                _money(row["amount"])
                                            ).classes(
                                                "jf-finance-upcoming-amount "
                                                + css
                                            )

                if goals:
                    ui.label(
                        "Objectifs du mois"
                    ).classes(
                        "text-lg font-bold mt-1"
                    )

                    for goal in goals:
                        percent = max(
                            0,
                            min(
                                100,
                                goal[
                                    "percentage"
                                ],
                            ),
                        )

                        with ui.element(
                            "div"
                        ).classes(
                            "jf-finance-card"
                        ):
                            with ui.row().classes(
                                "w-full justify-between gap-2"
                            ):
                                ui.label(
                                    goal[
                                        "target_name"
                                    ]
                                ).classes(
                                    "text-sm font-bold"
                                )
                                ui.label(
                                    (
                                        f"{_money(goal['spent'])} / "
                                        f"{_money(goal['available'])}"
                                    )
                                ).classes(
                                    "text-xs font-bold "
                                    "text-right"
                                )

                            with ui.element(
                                "div"
                            ).classes(
                                "jf-finance-progress mt-1"
                            ):
                                ui.element(
                                    "div"
                                ).style(
                                    f"width:{percent:.1f}%"
                                )

                            with ui.row().classes(
                                "w-full justify-between gap-2"
                            ):
                                ui.label(
                                    (
                                        "Reste : "
                                        f"{_money(goal['remaining'])}"
                                    )
                                ).classes(
                                    "text-xs jf-muted"
                                )
                                if goal[
                                    "carry_in"
                                ]:
                                    ui.label(
                                        (
                                            "Report : "
                                            f"{_money(goal['carry_in'])}"
                                        )
                                    ).classes(
                                        "text-xs jf-muted "
                                        "text-right"
                                    )

                def render_kpi_table(
                    title,
                    rows,
                    *,
                    empty_message,
                    color_class,
                    dimension,
                    transaction_type,
                ):
                    with ui.element("section").classes(
                        "jf-finance-card"
                    ):
                        ui.label(title).classes(
                            "text-sm font-bold"
                        )
                        if not rows:
                            ui.label(
                                empty_message
                            ).classes(
                                "text-xs jf-muted"
                            )
                            return

                        with ui.element("div").classes(
                            "jf-finance-kpi-list"
                        ):
                            with ui.element("div").classes(
                                "jf-finance-kpi-header"
                            ):
                                ui.label("Nom")
                                ui.label("Réalisé").classes(
                                    "text-right"
                                )
                                ui.label("À venir").classes(
                                    "text-right"
                                )
                                ui.label("Total prévu").classes(
                                    "text-right"
                                )
                                ui.label("% du total").classes(
                                    "text-right"
                                )

                            displayed_total = sum(
                                (Decimal(row["total"]) for row in rows),
                                Decimal("0.00"),
                            )

                            for row in rows:
                                with ui.element("div").classes(
                                    "jf-finance-kpi-row"
                                ):
                                    ui.button(
                                        row["name"],
                                        on_click=(
                                            lambda _event=None,
                                            selected=dict(row),
                                            selected_dimension=dimension,
                                            selected_type=transaction_type:
                                            open_kpi_detail(
                                                selected_dimension,
                                                selected,
                                                selected_type,
                                            )
                                        ),
                                    ).props(
                                        "flat dense no-caps"
                                    ).classes(
                                        "jf-finance-kpi-link"
                                    ).tooltip(
                                        (
                                            "Voir les transactions — "
                                            + row["name"]
                                        )
                                    )
                                    ui.label(
                                        _money(row["realized"])
                                    ).classes(
                                        "jf-finance-kpi-value "
                                        + color_class
                                    )
                                    ui.label(
                                        _money(row["upcoming"])
                                    ).classes(
                                        "jf-finance-kpi-value jf-muted"
                                    )
                                    ui.label(
                                        _money(row["total"])
                                    ).classes(
                                        "jf-finance-kpi-value "
                                        "jf-finance-kpi-total "
                                        + color_class
                                    )
                                    percent = (
                                        Decimal(row["total"]) * Decimal("100") / displayed_total
                                        if displayed_total else Decimal("0")
                                    )
                                    ui.label(
                                        f"{percent:.1f} %".replace(".", ",")
                                    ).classes("jf-finance-kpi-value jf-muted")

                            displayed_realized = sum(
                                (Decimal(row["realized"]) for row in rows),
                                Decimal("0.00"),
                            )
                            displayed_upcoming = sum(
                                (Decimal(row["upcoming"]) for row in rows),
                                Decimal("0.00"),
                            )
                            with ui.element("div").classes(
                                "jf-finance-kpi-row font-bold"
                            ):
                                ui.label("Total des KPI affichés").classes(
                                    "jf-finance-kpi-link font-bold"
                                )
                                ui.label(_money(displayed_realized)).classes(
                                    "jf-finance-kpi-value " + color_class
                                )
                                ui.label(_money(displayed_upcoming)).classes(
                                    "jf-finance-kpi-value jf-muted"
                                )
                                ui.label(_money(displayed_total)).classes(
                                    "jf-finance-kpi-value jf-finance-kpi-total "
                                    + color_class
                                )
                                ui.label(
                                    "100,0 %" if displayed_total else "0,0 %"
                                ).classes("jf-finance-kpi-value font-bold")

                        if dimension == "tag":
                            ui.label(
                                "Les étiquettes peuvent se chevaucher : leurs pourcentages ne représentent pas nécessairement des parts exclusives du total général."
                            ).classes("text-[0.65rem] jf-muted mt-1")

                for transaction_type, heading, color_class in (
                    (
                        "expense",
                        "KPI des dépenses",
                        "jf-finance-expense",
                    ),
                ):
                    type_kpis = kpis[transaction_type]
                    if not (
                        type_kpis["categories"]
                        or type_kpis["tags"]
                    ):
                        continue

                    ui.label(heading).classes(
                        "text-lg font-bold mt-1"
                    )
                    with ui.element("div").classes(
                        "jf-finance-kpi-grid"
                    ):
                        render_kpi_table(
                            "Par catégorie",
                            type_kpis["categories"],
                            empty_message=(
                                "Aucune transaction catégorisée."
                            ),
                            color_class=color_class,
                            dimension="category",
                            transaction_type=transaction_type,
                        )
                        render_kpi_table(
                            "Par étiquette",
                            type_kpis["tags"],
                            empty_message=(
                                "Aucune transaction étiquetée."
                            ),
                            color_class=color_class,
                            dimension="tag",
                            transaction_type=transaction_type,
                        )

                    if transaction_type == "expense":
                        ui.label(
                            "Une transaction portant plusieurs étiquettes "
                            "peut apparaître dans plusieurs lignes. "
                            "Les totaux par étiquette ne doivent pas être "
                            "additionnés pour obtenir le total général."
                        ).classes(
                            "text-xs jf-muted"
                        )

                if unassigned_count:
                    with ui.element("div").classes(
                        "jf-finance-warning-card mt-1"
                    ):
                        with ui.row().classes(
                            "w-full items-center justify-between gap-2"
                        ):
                            ui.label(
                                f"{unassigned_count} transaction(s) "
                                "confirmée(s) sans mode de paiement"
                            ).classes("text-sm font-bold")
                            ui.button(
                                "Classer",
                                icon="playlist_add_check",
                                on_click=lambda: tabs.set_value(
                                    reconciliation_tab
                                ),
                            ).props("flat dense color=primary")

                if predicted_rows:
                    ui.label(
                        "Soldes prévus par mode de paiement"
                    ).classes("text-lg font-bold mt-1")
                    ui.label(
                        "Cumulatifs sur tous les mois; aucune remise à zéro "
                        "automatique au début du mois."
                    ).classes("text-xs jf-muted")

                    with ui.element("div").classes(
                        "jf-finance-balance-grid"
                    ):
                        for row in predicted_rows:
                            if (
                                not row["is_active"]
                                and Decimal(row["predicted_balance"]) == 0
                            ):
                                continue

                            with ui.element("section").classes(
                                "jf-finance-balance-card"
                            ):
                                with ui.row().classes(
                                    "w-full items-start "
                                    "justify-between gap-2"
                                ):
                                    with ui.column().classes("gap-0 min-w-0"):
                                        ui.label(
                                            row["payment_method_name"]
                                        ).classes("text-sm font-bold")
                                        ui.label(
                                            PAYMENT_METHOD_TYPES.get(
                                                row["method_type"],
                                                "Autre",
                                            )
                                        ).classes("text-xs jf-muted")
                                    ui.label(
                                        f"{row['confirmed_count']} à concilier"
                                    ).classes(
                                        "jf-finance-reconciliation-chip"
                                    )

                                ui.label(
                                    _balance_money(row["predicted_balance"])
                                ).classes(
                                    "jf-finance-balance-main mt-1"
                                )
                                ui.label("Solde prévu").classes(
                                    "text-xs jf-muted text-right w-full"
                                )

                                with ui.element("div").classes(
                                    "jf-finance-balance-line mt-1"
                                ):
                                    ui.label("Confirmé non concilié")
                                    ui.label(
                                        _balance_money(row["current_balance"])
                                    )

                                if Decimal(row["planned_impact"]) != 0:
                                    with ui.element("div").classes(
                                        "jf-finance-balance-line"
                                    ):
                                        ui.label("Transactions prévues")
                                        ui.label(
                                            _balance_money(row["planned_impact"])
                                        )

                                if Decimal(
                                    row["opening_balance_pending"]
                                ) != 0:
                                    with ui.element("div").classes(
                                        "jf-finance-balance-line"
                                    ):
                                        ui.label("Ajustement initial")
                                        ui.label(
                                            _balance_money(
                                                row["opening_balance_pending"]
                                            )
                                        )

                                if row["oldest_unreconciled_date"]:
                                    ui.label(
                                        "Plus ancienne : "
                                        + row[
                                            "oldest_unreconciled_date"
                                        ].strftime("%d/%m/%Y")
                                    ).classes("text-xs jf-muted mt-1")

                                if row["last_reconciliation_date"]:
                                    ui.label(
                                        "Dernière conciliation : "
                                        + row[
                                            "last_reconciliation_date"
                                        ].strftime("%d/%m/%Y")
                                    ).classes("text-xs jf-muted")

                                ui.button(
                                    "Concilier",
                                    icon="fact_check",
                                    on_click=lambda: tabs.set_value(
                                        reconciliation_tab
                                    ),
                                ).props(
                                    "flat dense color=primary"
                                ).classes("mt-1")

        async def change_month(offset, reset=False):
            if reset:
                month_state.reset()
            else:
                month_state.shift(offset)
            render_dashboard.refresh()

        render_dashboard()


    return DashboardPanelHandle(on_refresh=lambda: render_dashboard.refresh())
