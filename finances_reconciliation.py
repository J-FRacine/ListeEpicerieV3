"""Panneau Conciliation avec services injectés et handle de rafraîchissement."""
from dataclasses import dataclass
from typing import Callable
from datetime import date
from decimal import Decimal


@dataclass
class ReconciliationPanelHandle:
    on_refresh: Callable[[], None]
    on_reload_options: Callable[[], None]

    def refresh(self):
        self.on_refresh()

    def reload_options(self):
        self.on_reload_options()


def _list_planned_reconciliation_transactions(
    user_id,
    payment_method_id,
    *,
    list_transactions,
    limit=500,
):
    # Transactions prevues du mode choisi, separees des lignes conciliables.
    if payment_method_id in (None, ""):
        return []
    rows = list_transactions(
        user_id,
        status="planned",
        payment_method_id=payment_method_id,
        reconciliation_status="unreconciled",
        limit=limit,
    )
    return sorted(
        list(rows),
        key=lambda row: (
            row["transaction_date"],
            int(row["id"]),
        ),
    )


def _confirm_planned_reconciliation_transaction(
    user_id,
    transaction_id,
    *,
    set_transaction_status,
):
    # Reutilise l'ecriture existante; aucune nouvelle transaction n'est creee.
    return set_transaction_status(
        user_id,
        transaction_id,
        "confirmed",
    )


def build_reconciliation_panel(
    *,
    RECONCILIATION_SESSION_STATUSES,
    _balance_money,
    _card_payment_dialog,
    _money,
    _payment_effect,
    _payment_options,
    _signed,
    _transaction_dialog,
    bulk_assign_payment_method,
    cancel_reconciliation_session,
    create_reconciliation_session,
    delete_reconciliation_draft,
    get_card_payment_transfer,
    get_reconciliation_draft,
    get_reconciliation_session,
    list_payment_methods,
    list_reconciliation_drafts,
    list_reconciliation_sessions,
    list_unassigned_transactions,
    list_unreconciled_transactions,
    list_transactions,
    payment_predicted_balance_summary,
    reconciliation_reference_summary,
    reconciliation_tab,
    refresh_all,
    remove_transaction_from_reconciliation_session,
    save_reconciliation_draft,
    set_transaction_status,
    ui,
    user_id,
) -> ReconciliationPanelHandle:
    # CONCILIATION
    with ui.tab_panel(reconciliation_tab).classes("px-0"):
        payment_options = _payment_options(
            user_id,
            include_none=False,
        )
        saved_reconciliation_drafts = list_reconciliation_drafts(user_id)
        draft_payment_id = (
            int(saved_reconciliation_drafts[0]["payment_method_id"])
            if saved_reconciliation_drafts
            else None
        )
        first_payment_id = (
            draft_payment_id
            if draft_payment_id in payment_options
            else (next(iter(payment_options)) if payment_options else None)
        )
        reconciliation_selected = set()
        reconciliation_rows_by_id = {}
        unassigned_selected = set()
        reconciliation_method_rows = {
            int(row["id"]): dict(row)
            for row in list_payment_methods(user_id, include_inactive=True)
        }

        with ui.card().classes("w-full p-3"):
            ui.label("Conciliation par relevé").classes(
                "text-xl font-bold"
            )
            ui.label(
                "Les soldes traversent les mois. Une transaction "
                "disparaît du solde confirmé dès sa conciliation."
            ).classes("text-xs jf-muted")

            reconciliation_payment = ui.select(
                payment_options,
                value=first_payment_id,
                label="Mode de paiement",
            ).props(
                "dense outlined options-dense"
            ).classes("w-full mt-2")

            with ui.element("div").classes(
                "jf-finance-reconcile-toolbar mt-2"
            ):
                reconciliation_start = ui.input(
                    label="Du — facultatif",
                    value="",
                ).props(
                    "type=date dense outlined"
                ).classes("jf-finance-field")

                reconciliation_end = ui.input(
                    label="Au — facultatif",
                    value="",
                ).props(
                    "type=date dense outlined"
                ).classes("jf-finance-field")

                reconciliation_query = ui.input(
                    label="Rechercher",
                ).props(
                    "dense outlined clearable"
                ).classes(
                    "jf-finance-field jf-finance-reconcile-search"
                )

                reconciliation_sort = ui.select(
                    {
                        "asc": "Date ascendante",
                        "desc": "Date descendante",
                    },
                    value="asc",
                    label="Tri",
                ).props(
                    "dense outlined options-dense"
                ).classes("jf-finance-field")

            with ui.row().classes("w-full justify-end gap-2 mt-2 flex-wrap"):
                ui.button(
                    "Actualiser",
                    icon="refresh",
                    on_click=lambda: (
                        refresh_reconciliation_screen()
                    ),
                ).props("outline dense color=primary")
                ui.button(
                    "Ajouter une transaction",
                    icon="add",
                    on_click=lambda: _transaction_dialog(
                        user_id,
                        refresh_all,
                        default_payment_method_id=(
                            reconciliation_payment.value
                        ),
                    ),
                ).props("outline dense color=primary")

        reconciliation_draft_box = ui.column().classes(
            "w-full gap-2"
        )
        reconciliation_balance_box = ui.column().classes(
            "w-full gap-2"
        )

        with ui.card().classes("w-full p-3"):
            ui.label("Données du relevé").classes(
                "text-lg font-bold"
            )

            with ui.element("div").classes(
                "jf-finance-form-grid"
            ):
                statement_date = ui.input(
                    label="Date du relevé",
                    value=date.today().isoformat(),
                ).props(
                    "type=date dense outlined"
                ).classes("jf-finance-field")

                statement_balance = ui.number(
                    label="Solde du relevé",
                    step=.01,
                ).props(
                    "dense outlined clearable"
                ).classes("jf-finance-field")

                due_date = ui.input(
                    label="Date de paiement",
                    value="",
                ).props(
                    "type=date dense outlined"
                ).classes(
                    "jf-finance-field jf-finance-description"
                )

            reconciliation_date_input = ui.input(
                label="Date de conciliation",
                value=date.today().isoformat(),
            ).props(
                "type=date dense outlined"
            ).classes("w-full")

            reconciliation_note = ui.textarea(
                label="Note facultative",
            ).props(
                "dense outlined autogrow maxlength=1000"
            ).classes("w-full")

            difference_explanation = ui.textarea(
                label="Explication d’un écart justifié — si nécessaire",
            ).props(
                "dense outlined autogrow maxlength=1000"
            ).classes("w-full")
            ui.label(
                "Si le relevé ne balance pas, vous pourrez soit clore l’écart comme justifié (il ne sera pas reporté), soit le reporter au prochain relevé."
            ).classes("text-xs jf-muted")

            include_opening_balance = ui.checkbox(
                "Inclure l’ajustement initial",
                value=False,
            ).classes("text-sm")
            opening_balance_label = ui.label("").classes(
                "text-xs jf-muted"
            )

        def save_current_reconciliation_draft():
            selected_id = reconciliation_payment.value
            if not selected_id:
                ui.notify("Choisissez d’abord un mode de paiement.", type="warning")
                return
            try:
                save_reconciliation_draft(
                    user_id,
                    selected_id,
                    list(reconciliation_selected),
                    statement_date=statement_date.value or None,
                    statement_balance=statement_balance.value,
                    due_date=due_date.value or None,
                    reconciliation_date=reconciliation_date_input.value or None,
                    note=reconciliation_note.value,
                    include_opening_balance=include_opening_balance.value,
                    difference_explanation=difference_explanation.value or None,
                    filter_start=reconciliation_start.value or None,
                    filter_end=reconciliation_end.value or None,
                    filter_query=reconciliation_query.value or None,
                    sort_direction=reconciliation_sort.value or "asc",
                )
            except Exception as error:
                ui.notify(str(error), type="warning")
                return
            ui.notify(
                "Conciliation enregistrée en cours. Vous pouvez quitter cet onglet et la reprendre plus tard.",
                type="positive",
            )
            render_reconciliation_draft.refresh()

        def resume_reconciliation_draft(draft):
            reconciliation_selected.clear()
            reconciliation_selected.update(
                int(value) for value in (draft.get("selected_transaction_ids") or [])
            )
            statement_date.value = (
                draft["statement_date"].isoformat()
                if draft.get("statement_date")
                else date.today().isoformat()
            )
            statement_balance.value = draft.get("statement_balance")
            due_date.value = (
                draft["due_date"].isoformat() if draft.get("due_date") else ""
            )
            reconciliation_date_input.value = (
                draft["reconciliation_date"].isoformat()
                if draft.get("reconciliation_date")
                else date.today().isoformat()
            )
            reconciliation_note.value = draft.get("note") or ""
            difference_explanation.value = draft.get("difference_explanation") or ""
            include_opening_balance.value = bool(draft.get("include_opening_balance"))
            reconciliation_start.value = (
                draft["filter_start"].isoformat() if draft.get("filter_start") else ""
            )
            reconciliation_end.value = (
                draft["filter_end"].isoformat() if draft.get("filter_end") else ""
            )
            reconciliation_query.value = draft.get("filter_query") or ""
            reconciliation_sort.value = draft.get("sort_direction") or "asc"
            render_reconciliation_transactions.refresh()
            render_reconciliation_selection.refresh()
            render_reconciliation_balance.refresh()
            ui.notify("Conciliation en cours reprise.", type="positive")

        def abandon_reconciliation_draft():
            selected_id = reconciliation_payment.value
            if not selected_id:
                return
            try:
                delete_reconciliation_draft(user_id, selected_id)
            except Exception as error:
                ui.notify(str(error), type="warning")
                return
            render_reconciliation_draft.refresh()
            ui.notify("Brouillon de conciliation abandonné.", type="info")

        @ui.refreshable
        def render_reconciliation_draft():
            reconciliation_draft_box.clear()
            selected_id = reconciliation_payment.value
            if not selected_id:
                return
            try:
                draft = get_reconciliation_draft(user_id, selected_id)
            except Exception as error:
                with reconciliation_draft_box:
                    ui.label(str(error)).classes("text-negative")
                return
            if not draft:
                return
            with reconciliation_draft_box:
                with ui.card().classes("w-full p-3 border-l-4 border-primary"):
                    with ui.row().classes("w-full items-center justify-between gap-2 flex-wrap"):
                        with ui.column().classes("gap-0"):
                            ui.label("Conciliation en cours enregistrée").classes("font-bold")
                            saved = draft.get("updated_at")
                            selected_count = len(draft.get("selected_transaction_ids") or [])
                            detail = f"{selected_count} transaction(s) sélectionnée(s)"
                            if saved:
                                try:
                                    detail += " — sauvegardée le " + saved.strftime("%d/%m/%Y %H:%M")
                                except Exception:
                                    pass
                            ui.label(detail).classes("text-xs jf-muted")
                        with ui.row().classes("gap-2"):
                            ui.button(
                                "Reprendre",
                                icon="play_arrow",
                                on_click=lambda _event=None, saved_draft=draft: resume_reconciliation_draft(saved_draft),
                            ).props("color=primary dense")
                            ui.button(
                                "Abandonner",
                                icon="delete_outline",
                                on_click=abandon_reconciliation_draft,
                            ).props("outline color=negative dense")

        ui.label("Transactions prévues à confirmer").classes(
            "text-lg font-bold mt-1"
        )
        ui.label(
            "Les versements de financement et les autres transactions prévues "
            "du mode de paiement sélectionné apparaissent ici séparément. "
            "Confirmez seulement ce qui est réellement apparu; la transaction "
            "passera ensuite dans la liste à concilier."
        ).classes("text-xs jf-muted")
        planned_transactions_box = ui.column().classes(
            "w-full gap-1"
        )

        def confirm_planned_transaction(transaction_id):
            try:
                _confirm_planned_reconciliation_transaction(
                    user_id,
                    transaction_id,
                    set_transaction_status=set_transaction_status,
                )
            except Exception as error:
                ui.notify(str(error), type="warning")
                return
            ui.notify(
                "Transaction confirmée; elle peut maintenant être conciliée.",
                type="positive",
            )
            refresh_all()

        @ui.refreshable
        def render_planned_transactions():
            planned_transactions_box.clear()
            selected_id = reconciliation_payment.value

            with planned_transactions_box:
                if not selected_id:
                    ui.label(
                        "Aucun mode de paiement sélectionné."
                    ).classes("text-sm jf-muted")
                    return

                try:
                    rows = _list_planned_reconciliation_transactions(
                        user_id,
                        selected_id,
                        list_transactions=list_transactions,
                    )
                except Exception as error:
                    ui.label(str(error)).classes("text-negative")
                    return

                if not rows:
                    ui.label(
                        "Aucune transaction prévue pour ce mode de paiement."
                    ).classes("text-sm jf-muted p-3")
                    return

                ui.label(
                    f"{len(rows)} transaction(s) prévue(s)"
                ).classes("text-xs jf-muted")

                for row in rows:
                    transaction_id = int(row["id"])
                    with ui.element("div").classes(
                        "jf-finance-reconcile-row"
                    ):
                        ui.icon("schedule").classes("text-warning")
                        ui.label(
                            row["transaction_date"].strftime("%d/%m/%Y")
                        ).classes("jf-finance-reconcile-date")

                        with ui.column().classes("gap-0 min-w-0"):
                            ui.label(row["description"]).classes(
                                "jf-finance-reconcile-description"
                            )
                            meta = []
                            if row.get("installment_plan_id"):
                                installment_meta = "Versement de financement"
                                if row.get("installment_number"):
                                    installment_meta += (
                                        " #" + str(row["installment_number"])
                                    )
                                meta.append(installment_meta)
                            elif row.get("linked_transfer_id"):
                                meta.append("Paiement de carte lié")
                            if row.get("category_full_name"):
                                meta.append(row["category_full_name"])
                            if row.get("bank_programmed"):
                                meta.append("Programmé")
                            ui.label(
                                " — ".join(meta) or "À confirmer"
                            ).classes("text-xs jf-muted truncate")

                        amount_class = (
                            "jf-finance-expense"
                            if row["transaction_type"] == "expense"
                            else "jf-finance-income"
                        )
                        ui.label(
                            _payment_effect(
                                row["amount"],
                                row["transaction_type"],
                            )
                        ).classes(
                            "jf-finance-reconcile-amount " + amount_class
                        )
                        ui.button(
                            "Confirmer",
                            icon="check_circle",
                            on_click=(
                                lambda _event=None, selected=transaction_id:
                                confirm_planned_transaction(selected)
                            ),
                        ).props(
                            "outline dense color=primary"
                        )

        ui.label("Transactions non conciliées").classes(
            "text-lg font-bold mt-1"
        )
        reconciliation_transactions_box = ui.column().classes(
            "w-full gap-1"
        )
        reconciliation_selection_box = ui.column().classes(
            "w-full"
        )

        def selected_reconciliation_total():
            total = Decimal("0.00")
            for transaction_id in reconciliation_selected:
                row = reconciliation_rows_by_id.get(
                    int(transaction_id)
                )
                if not row:
                    continue
                amount_value = Decimal(row["amount"])
                total += (
                    amount_value
                    if row["transaction_type"] == "expense"
                    else -amount_value
                )

            return total

        @ui.refreshable
        def render_reconciliation_balance():
            reconciliation_balance_box.clear()
            selected_id = reconciliation_payment.value

            with reconciliation_balance_box:
                if not selected_id:
                    include_opening_balance.visible = False
                    opening_balance_label.visible = False
                    ui.label(
                        "Créez d’abord un mode de paiement."
                    ).classes("text-sm jf-muted")
                    return

                selected_summary = next(
                    (
                        row
                        for row in payment_predicted_balance_summary(
                            user_id
                        )
                        if int(row["payment_method_id"])
                        == int(selected_id)
                    ),
                    None,
                )
                if not selected_summary:
                    return

                with ui.element("div").classes(
                    "jf-finance-summary-grid"
                ):
                    with ui.element("div").classes(
                        "jf-finance-summary"
                    ):
                        ui.label(
                            "Confirmé à concilier"
                        ).classes("jf-finance-summary-label")
                        ui.label(
                            _balance_money(
                                selected_summary["current_balance"]
                            )
                        ).classes(
                            "jf-finance-summary-value"
                        )

                    with ui.element("div").classes(
                        "jf-finance-summary"
                    ):
                        ui.label("Solde prévu").classes(
                            "jf-finance-summary-label"
                        )
                        ui.label(
                            _balance_money(
                                selected_summary["predicted_balance"]
                            )
                        ).classes(
                            "jf-finance-summary-value"
                        )

                    with ui.element("div").classes(
                        "jf-finance-summary"
                    ):
                        ui.label("Transactions").classes(
                            "jf-finance-summary-label"
                        )
                        ui.label(
                            str(selected_summary["confirmed_count"])
                        ).classes(
                            "jf-finance-summary-value"
                        )

                opening_pending = Decimal(
                    selected_summary["opening_balance_pending"]
                )
                has_opening = opening_pending != 0
                include_opening_balance.visible = has_opening
                opening_balance_label.visible = has_opening
                opening_balance_label.set_text(
                    (
                        "Ajustement initial disponible : "
                        + _balance_money(opening_pending)
                    )
                    if has_opening
                    else ""
                )
                if not has_opening:
                    include_opening_balance.value = False

        def toggle_reconciliation_selection(
            transaction_id,
            value,
        ):
            transaction_id = int(transaction_id)
            if value:
                reconciliation_selected.add(transaction_id)
            else:
                reconciliation_selected.discard(transaction_id)
            render_reconciliation_selection.refresh()

        @ui.refreshable
        def render_reconciliation_transactions():
            reconciliation_transactions_box.clear()
            selected_id = reconciliation_payment.value

            with reconciliation_transactions_box:
                if not selected_id:
                    reconciliation_rows_by_id.clear()
                    ui.label(
                        "Aucun mode de paiement sélectionné."
                    ).classes("text-sm jf-muted")
                    return

                try:
                    # Liste complète des transactions admissibles : elle sert
                    # à conserver les cases cochées même lorsqu'un filtre,
                    # un tri ou une modification rafraîchit l'écran.
                    all_rows = list_unreconciled_transactions(
                        user_id, selected_id
                    )
                    rows = list_unreconciled_transactions(
                        user_id,
                        selected_id,
                        start_date=(
                            reconciliation_start.value or None
                        ),
                        end_date=(
                            reconciliation_end.value or None
                        ),
                        query=(
                            reconciliation_query.value or None
                        ),
                    )
                except Exception as error:
                    ui.label(str(error)).classes("text-negative")
                    return

                reconciliation_rows_by_id.clear()
                reconciliation_rows_by_id.update(
                    {int(row["id"]): row for row in all_rows}
                )
                eligible_ids = set(reconciliation_rows_by_id)
                removed = reconciliation_selected - eligible_ids
                if removed:
                    reconciliation_selected.difference_update(removed)
                    ui.notify(
                        f"{len(removed)} transaction(s) sélectionnée(s) ont été retirées parce qu’elles ne sont plus admissibles à cette conciliation.",
                        type="info",
                    )

                rows = list(rows)
                rows.sort(
                    key=lambda row: (
                        row["transaction_date"],
                        int(row["id"]),
                    ),
                    reverse=(reconciliation_sort.value == "desc"),
                )
                visible_ids = {int(row["id"]) for row in rows}

                if not rows:
                    ui.label(
                        "Aucune transaction confirmée à concilier."
                    ).classes("text-sm jf-muted p-3")
                    return

                with ui.row().classes(
                    "w-full items-center justify-between gap-2"
                ):
                    ui.label(
                        f"{len(rows)} transaction(s) affichée(s) — "
                        f"{len(reconciliation_selected)} sélectionnée(s)"
                    ).classes("text-xs jf-muted")

                    def select_all_rows():
                        reconciliation_selected.update(visible_ids)
                        render_reconciliation_transactions.refresh()
                        render_reconciliation_selection.refresh()

                    def clear_all_rows():
                        reconciliation_selected.clear()
                        render_reconciliation_transactions.refresh()
                        render_reconciliation_selection.refresh()

                    with ui.row().classes("gap-1"):
                        ui.button(
                            "Tout", on_click=select_all_rows
                        ).props("flat dense color=primary")
                        ui.button(
                            "Aucun", on_click=clear_all_rows
                        ).props("flat dense color=primary")

                def edit_reconciliation_row(row):
                    if row.get("linked_transfer_id"):
                        try:
                            transfer = get_card_payment_transfer(
                                user_id, row["linked_transfer_id"]
                            )
                        except Exception as error:
                            ui.notify(str(error), type="warning")
                            return
                        _card_payment_dialog(
                            user_id, refresh_all, transfer=transfer
                        )
                    else:
                        _transaction_dialog(
                            user_id, refresh_all, transaction=row
                        )

                for row in rows:
                    transaction_id = int(row["id"])
                    with ui.element("div").classes(
                        "jf-finance-reconcile-row"
                    ):
                        ui.checkbox(
                            value=(
                                transaction_id in reconciliation_selected
                            ),
                            on_change=(
                                lambda event, selected=transaction_id:
                                toggle_reconciliation_selection(
                                    selected, event.value
                                )
                            ),
                        ).props("dense")

                        ui.label(
                            row["transaction_date"].strftime("%d/%m/%Y")
                        ).classes("jf-finance-reconcile-date")

                        with ui.column().classes("gap-0 min-w-0"):
                            ui.label(row["description"]).classes(
                                "jf-finance-reconcile-description"
                            )
                            if (
                                row.get("linked_transfer_id")
                                and row.get("linked_transfer_role") == "destination"
                            ):
                                meta = (
                                    "Paiement reçu de "
                                    + str(
                                        row.get("linked_transfer_source_name")
                                        or "compte bancaire"
                                    )
                                )
                                if row.get("budget_excluded"):
                                    meta += " — Hors budget"
                            else:
                                meta = (
                                    row["category_full_name"]
                                    or "Sans catégorie"
                                )
                                if row["tag_names"]:
                                    meta += " — " + " • ".join(
                                        row["tag_names"]
                                    )
                            ui.label(meta).classes(
                                "text-xs jf-muted truncate"
                            )

                        amount_class = (
                            "jf-finance-expense"
                            if row["transaction_type"] == "expense"
                            else "jf-finance-income"
                        )
                        ui.label(
                            _payment_effect(
                                row["amount"], row["transaction_type"]
                            )
                        ).classes(
                            "jf-finance-reconcile-amount " + amount_class
                        )
                        ui.button(
                            icon="edit",
                            on_click=(
                                lambda _event=None, selected=row:
                                edit_reconciliation_row(selected)
                            ),
                        ).props(
                            "flat dense round size=sm color=primary"
                        ).tooltip(
                            "Modifier sans perdre la sélection en cours"
                        )

        @ui.refreshable
        def render_reconciliation_selection():
            reconciliation_selection_box.clear()
            movement_total = selected_reconciliation_total()
            selected_id = reconciliation_payment.value

            reference = None
            if selected_id:
                try:
                    reference = reconciliation_reference_summary(
                        user_id, selected_id
                    )
                except Exception:
                    reference = None

            reference_balance = (
                Decimal(reference["reference_balance"])
                if reference
                else Decimal("0.00")
            )
            expected_balance = reference_balance + movement_total
            statement_value = (
                Decimal(str(statement_balance.value))
                if statement_balance.value not in (None, "")
                else None
            )
            difference = (
                statement_value - expected_balance
                if statement_value is not None
                else None
            )

            with reconciliation_selection_box:
                with ui.element("div").classes(
                    "jf-finance-selection-summary"
                ):
                    with ui.element("div").classes(
                        "jf-finance-balance-line"
                    ):
                        reference_label = "Solde précédent"
                        if reference and reference.get("reference_date"):
                            reference_label += (
                                " ("
                                + reference["reference_date"].strftime("%d/%m/%Y")
                                + ")"
                            )
                        ui.label(reference_label)
                        ui.label(_balance_money(reference_balance))

                    with ui.element("div").classes(
                        "jf-finance-balance-line"
                    ):
                        ui.label("Mouvements sélectionnés")
                        ui.label(_balance_money(movement_total))

                    with ui.element("div").classes(
                        "jf-finance-balance-line"
                    ):
                        ui.label("Solde attendu")
                        ui.label(_balance_money(expected_balance)).classes(
                            "font-bold"
                        )

                    if statement_value is not None:
                        with ui.element("div").classes(
                            "jf-finance-balance-line"
                        ):
                            ui.label("Solde du relevé")
                            ui.label(_balance_money(statement_value))

                    if difference is not None:
                        with ui.element("div").classes(
                            "jf-finance-balance-line"
                        ):
                            ui.label("Différence")
                            ui.label(_balance_money(difference)).classes(
                                "text-positive"
                                if abs(difference) < Decimal(".01")
                                else "text-negative"
                            )

                    ui.label(
                        "Solde précédent + mouvements sélectionnés = solde attendu; le relevé réel permet de mesurer la différence."
                    ).classes("text-xs jf-muted mt-1")

                    def finalize_now(resolution="balanced", program_payment=False):
                        selected_payment_id = reconciliation_payment.value
                        statement_date_value = statement_date.value
                        due_date_value = due_date.value or None
                        try:
                            result = create_reconciliation_session(
                                user_id=user_id,
                                payment_method_id=selected_payment_id,
                                transaction_ids=list(reconciliation_selected),
                                statement_date=statement_date_value,
                                statement_balance=statement_balance.value,
                                due_date=due_date_value,
                                reconciliation_date=reconciliation_date_input.value,
                                note=reconciliation_note.value,
                                include_opening_balance=include_opening_balance.value,
                                difference_resolution=resolution,
                                difference_explanation=(difference_explanation.value or None),
                            )
                        except Exception as error:
                            ui.notify(str(error), type="warning")
                            return

                        reconciliation_selected.clear()
                        include_opening_balance.value = False
                        reconciliation_note.value = ""
                        difference_explanation.value = ""
                        ui.notify(
                            "Conciliation enregistrée : "
                            f"{result['transaction_count']} transaction(s).",
                            type="positive",
                        )
                        refresh_reconciliation_screen()

                        method = reconciliation_method_rows.get(int(selected_payment_id or 0), {})
                        if program_payment and method.get("method_type") == "credit_card":
                            proposed = result.get("statement_balance")
                            if proposed is None:
                                proposed = result.get("expected_balance")
                            proposed = abs(Decimal(proposed or 0))
                            # Le rafraîchissement global est volontairement différé :
                            # il détruisait le contexte NiceGUI avant l'ouverture du
                            # dialogue de paiement. L'enregistrement du paiement appelle
                            # refresh_all via le callback transmis au dialogue.
                            _card_payment_dialog(
                                user_id,
                                refresh_all,
                                prefill={
                                    "destination_payment_method_id": int(selected_payment_id),
                                    "amount": float(proposed) if proposed > 0 else None,
                                    "payment_date": due_date_value or date.today().isoformat(),
                                    "status": "planned",
                                    "bank_programmed": False,
                                    "description": (
                                        "Paiement de carte — relevé du "
                                        + date.fromisoformat(statement_date_value).strftime("%d/%m/%Y")
                                        if statement_date_value
                                        else "Paiement de carte"
                                    ),
                                },
                            )
                        else:
                            refresh_all()

                    def request_finalize(program_payment=False):
                        if (
                            not reconciliation_selected
                            and not include_opening_balance.value
                        ):
                            ui.notify(
                                "Sélectionnez au moins une transaction.",
                                type="warning",
                            )
                            return

                        if (
                            difference is not None
                            and abs(difference) >= Decimal(".01")
                        ):
                            with ui.dialog() as warning_dialog:
                                with ui.card().classes(
                                    "w-full max-w-lg p-4"
                                ):
                                    ui.label(
                                        "La conciliation ne balance pas"
                                    ).classes("text-xl font-bold")
                                    ui.label(
                                        "Différence : "
                                        + _balance_money(difference)
                                    ).classes(
                                        "text-lg font-bold text-negative"
                                    )
                                    ui.label(
                                        "Clore comme écart justifié utilise le solde réel de ce relevé comme nouvelle référence : la différence ne reviendra pas au relevé suivant. Reporter l’écart conserve plutôt le solde attendu comme référence."
                                    ).classes("text-sm jf-muted")
                                    explanation_dialog = ui.textarea(
                                        label="Explication de l’écart",
                                        value=(
                                            difference_explanation.value or ""
                                        ),
                                    ).props(
                                        "dense outlined autogrow maxlength=1000"
                                    ).classes("w-full mt-2")

                                    def close_justified():
                                        explanation = str(
                                            explanation_dialog.value or ""
                                        ).strip()
                                        if not explanation:
                                            ui.notify(
                                                "Inscrivez une explication de l’écart avant de le clore comme justifié.",
                                                type="warning",
                                            )
                                            return
                                        difference_explanation.value = explanation
                                        warning_dialog.close()
                                        finalize_now("justified", False)

                                    def close_and_program_payment():
                                        explanation = str(
                                            explanation_dialog.value or ""
                                        ).strip()
                                        if not explanation:
                                            ui.notify(
                                                "Inscrivez une explication de l’écart avant de clore et programmer le paiement.",
                                                type="warning",
                                            )
                                            return
                                        difference_explanation.value = explanation
                                        warning_dialog.close()
                                        finalize_now("justified", True)

                                    def carry_difference():
                                        warning_dialog.close()
                                        finalize_now("carry", False)

                                    with ui.column().classes(
                                        "w-full gap-2 mt-2"
                                    ):
                                        ui.button(
                                            "Clore comme écart justifié",
                                            icon="done_all",
                                            on_click=close_justified,
                                        ).props("color=primary").classes(
                                            "w-full"
                                        )
                                        if reconciliation_method_rows.get(
                                            int(reconciliation_payment.value or 0), {}
                                        ).get("method_type") == "credit_card":
                                            ui.button(
                                                "Clore et programmer le paiement",
                                                icon="credit_card",
                                                on_click=close_and_program_payment,
                                            ).props("outline color=primary").classes("w-full")
                                        ui.button(
                                            "Reporter l’écart",
                                            icon="redo",
                                            on_click=carry_difference,
                                        ).props(
                                            "outline color=warning"
                                        ).classes("w-full")
                                        ui.button(
                                            "Retourner à la conciliation",
                                            on_click=warning_dialog.close,
                                        ).props("flat").classes("w-full")
                            warning_dialog.open()
                            return

                        finalize_now("balanced", program_payment)

                    with ui.row().classes("w-full gap-2 mt-2 flex-wrap"):
                        ui.button(
                            "Enregistrer le travail en cours",
                            icon="save",
                            on_click=save_current_reconciliation_draft,
                        ).props("outline color=secondary").classes("grow")
                        ui.button(
                            "Finaliser la conciliation",
                            icon="fact_check",
                            on_click=lambda: request_finalize(False),
                        ).props("color=primary").classes("grow")
                        if reconciliation_method_rows.get(
                            int(selected_id or 0), {}
                        ).get("method_type") == "credit_card":
                            ui.button(
                                "Clore et programmer le paiement",
                                icon="credit_card",
                                on_click=lambda: request_finalize(True),
                            ).props("outline color=primary").classes("grow")

        statement_balance.on_value_change(
            lambda event: (
                render_reconciliation_selection.refresh()
            )
        )
        include_opening_balance.on_value_change(
            lambda event: (
                render_reconciliation_selection.refresh()
            )
        )

        with ui.expansion(
            "Transactions sans mode de paiement",
            icon="playlist_add_check",
        ).classes("w-full mt-2"):
            with ui.card().classes("w-full p-3"):
                unassigned_target = ui.select(
                    payment_options,
                    value=first_payment_id,
                    label="Attribuer au mode",
                ).props(
                    "dense outlined options-dense"
                ).classes("w-full")
                unassigned_search = ui.input(
                    label="Rechercher",
                ).props(
                    "dense outlined clearable"
                ).classes("w-full")
                unassigned_box = ui.column().classes(
                    "w-full gap-1 mt-2"
                )

                def toggle_unassigned(transaction_id, value):
                    transaction_id = int(transaction_id)
                    if value:
                        unassigned_selected.add(transaction_id)
                    else:
                        unassigned_selected.discard(transaction_id)

                @ui.refreshable
                def render_unassigned():
                    unassigned_box.clear()
                    rows = list_unassigned_transactions(
                        user_id,
                        query=unassigned_search.value or None,
                        limit=500,
                    )
                    valid_ids = {int(row["id"]) for row in rows}
                    unassigned_selected.intersection_update(valid_ids)

                    with unassigned_box:
                        if not rows:
                            ui.label(
                                "Aucune transaction confirmée sans mode."
                            ).classes("text-sm jf-muted")
                            return

                        ui.label(
                            f"{len(rows)} transaction(s) sans mode"
                        ).classes("text-xs jf-muted")

                        for row in rows:
                            transaction_id = int(row["id"])
                            with ui.element("div").classes(
                                "jf-finance-reconcile-row"
                            ):
                                ui.checkbox(
                                    value=(
                                        transaction_id
                                        in unassigned_selected
                                    ),
                                    on_change=(
                                        lambda event,
                                        selected=transaction_id:
                                        toggle_unassigned(
                                            selected,
                                            event.value,
                                        )
                                    ),
                                ).props("dense")
                                ui.label(
                                    row["transaction_date"].strftime(
                                        "%d/%m/%Y"
                                    )
                                ).classes(
                                    "jf-finance-reconcile-date"
                                )
                                ui.label(
                                    row["description"]
                                ).classes(
                                    "jf-finance-reconcile-description"
                                )
                                ui.label(
                                    _signed(
                                        row["amount"],
                                        row["transaction_type"],
                                    )
                                ).classes(
                                    "jf-finance-reconcile-amount"
                                )

                        def assign_selected():
                            try:
                                count = bulk_assign_payment_method(
                                    user_id,
                                    list(unassigned_selected),
                                    unassigned_target.value,
                                )
                            except Exception as error:
                                ui.notify(
                                    str(error),
                                    type="warning",
                                )
                                return

                            unassigned_selected.clear()
                            ui.notify(
                                f"{count} transaction(s) classée(s).",
                                type="positive",
                            )
                            refresh_reconciliation_screen()
                            refresh_all()

                        ui.button(
                            "Attribuer la sélection",
                            icon="playlist_add_check",
                            on_click=assign_selected,
                        ).props(
                            "outline color=primary"
                        ).classes("w-full mt-2")

                unassigned_search.on_value_change(
                    lambda event: render_unassigned.refresh()
                )
                render_unassigned()

        ui.label("Historique des conciliations").classes(
            "text-lg font-bold mt-2"
        )
        sessions_box = ui.column().classes("w-full gap-2")

        def session_detail_dialog(session_id):
            try:
                details = get_reconciliation_session(
                    user_id,
                    session_id,
                )
            except Exception as error:
                ui.notify(str(error), type="warning")
                return

            session = details["session"]
            transactions = details["transactions"]

            with ui.dialog() as dialog:
                with ui.card().classes(
                    "w-full max-w-3xl p-4"
                ):
                    with ui.row().classes(
                        "w-full items-start justify-between gap-2"
                    ):
                        with ui.column().classes("gap-0"):
                            ui.label(
                                session["payment_method_name"]
                            ).classes("text-xl font-bold")
                            ui.label(
                                "Relevé du "
                                + session["statement_date"].strftime(
                                    "%d/%m/%Y"
                                )
                            ).classes("text-sm jf-muted")
                        ui.label(
                            RECONCILIATION_SESSION_STATUSES.get(
                                session["status"],
                                session["status"],
                            )
                        ).classes(
                            "jf-finance-reconciliation-chip"
                        )

                    with ui.element("div").classes(
                        "jf-finance-summary-grid mt-2"
                    ):
                        for label, value in (
                            ("Solde précédent", session.get("reference_balance")),
                            ("Mouvements conciliés", session["selected_total"]),
                            ("Solde attendu", session.get("expected_balance")),
                            ("Solde du relevé", session["statement_balance"]),
                            ("Différence", session["difference"]),
                        ):
                            with ui.element("div").classes(
                                "jf-finance-summary"
                            ):
                                ui.label(label).classes(
                                    "jf-finance-summary-label"
                                )
                                ui.label(
                                    _balance_money(value)
                                    if value is not None
                                    else "—"
                                ).classes(
                                    "jf-finance-summary-value"
                                )

                    resolution_label = {
                        "balanced": "Conciliation équilibrée",
                        "justified": "Écart justifié — fermé",
                        "carry": "Écart reporté",
                        "legacy": "Ancienne méthode de conciliation",
                    }.get(
                        session.get("difference_resolution"),
                        str(session.get("difference_resolution") or ""),
                    )
                    if resolution_label:
                        ui.label(resolution_label).classes(
                            "text-sm font-semibold"
                        )
                    if session.get("difference_explanation"):
                        ui.label(
                            "Explication : "
                            + session["difference_explanation"]
                        ).classes("text-sm jf-muted")

                    if session["due_date"]:
                        ui.label(
                            "Paiement prévu : "
                            + session["due_date"].strftime("%d/%m/%Y")
                        ).classes("text-sm")
                    if session["note"]:
                        ui.label(session["note"]).classes(
                            "text-sm jf-muted"
                        )
                    if session["included_opening_balance"]:
                        ui.label(
                            "Ajustement initial inclus : "
                            + _balance_money(session["opening_balance_amount"])
                        ).classes("text-sm")

                    ui.label("Transactions").classes(
                        "font-bold mt-2"
                    )
                    with ui.column().classes("w-full gap-1"):
                        for transaction in transactions:
                            row_class = (
                                "jf-finance-reconcile-row"
                                if transaction["is_active"]
                                else (
                                    "jf-finance-reconcile-row "
                                    "opacity-50"
                                )
                            )
                            with ui.element("div").classes(row_class):
                                ui.icon(
                                    "check_circle"
                                    if transaction["is_active"]
                                    else "remove_circle_outline"
                                ).classes(
                                    "text-positive"
                                    if transaction["is_active"]
                                    else "text-gray-400"
                                )
                                ui.label(
                                    transaction[
                                        "transaction_date"
                                    ].strftime("%d/%m/%Y")
                                ).classes(
                                    "jf-finance-reconcile-date"
                                )
                                ui.label(
                                    transaction["description"]
                                ).classes(
                                    "jf-finance-reconcile-description"
                                )
                                with ui.row().classes(
                                    "items-center justify-end gap-1"
                                ):
                                    ui.label(
                                        _payment_effect(
                                            transaction["amount"],
                                            transaction[
                                                "transaction_type"
                                            ],
                                        )
                                    ).classes(
                                        "jf-finance-reconcile-amount"
                                    )
                                    if (
                                        transaction["is_active"]
                                        and session["status"] == "completed"
                                    ):
                                        def remove_one(
                                            transaction_id=transaction["id"],
                                        ):
                                            try:
                                                remove_transaction_from_reconciliation_session(
                                                    user_id,
                                                    session_id,
                                                    transaction_id,
                                                )
                                            except Exception as error:
                                                ui.notify(
                                                    str(error),
                                                    type="warning",
                                                )
                                                return
                                            dialog.close()
                                            ui.notify(
                                                "Transaction retirée "
                                                "de la conciliation.",
                                                type="positive",
                                            )
                                            refresh_reconciliation_screen()
                                            refresh_all()

                                        ui.button(
                                            icon="undo",
                                            on_click=remove_one,
                                        ).props(
                                            "flat dense round "
                                            "size=sm color=negative"
                                        ).tooltip(
                                            "Retirer de la conciliation"
                                        )

                    def cancel_session_now():
                        try:
                            cancel_reconciliation_session(
                                user_id,
                                session_id,
                            )
                        except Exception as error:
                            ui.notify(
                                str(error),
                                type="warning",
                            )
                            return
                        dialog.close()
                        ui.notify(
                            "Conciliation annulée.",
                            type="positive",
                        )
                        refresh_reconciliation_screen()
                        refresh_all()

                    with ui.row().classes(
                        "w-full justify-end gap-2 mt-2"
                    ):
                        if session["status"] == "completed":
                            ui.button(
                                "Annuler la conciliation",
                                icon="undo",
                                on_click=cancel_session_now,
                            ).props(
                                "outline color=negative"
                            )
                        ui.button(
                            "Fermer",
                            on_click=dialog.close,
                        ).props("color=primary")
            dialog.open()

        @ui.refreshable
        def render_sessions():
            sessions_box.clear()
            selected_id = reconciliation_payment.value
            rows = list_reconciliation_sessions(
                user_id,
                payment_method_id=selected_id,
                include_cancelled=True,
                limit=100,
            )
            with sessions_box:
                if not rows:
                    ui.label(
                        "Aucune conciliation enregistrée."
                    ).classes("text-sm jf-muted")
                    return

                for row in rows:
                    card_class = "jf-finance-session-card"
                    if row["status"] == "cancelled":
                        card_class += " jf-finance-session-cancelled"

                    with ui.element("div").classes(card_class):
                        with ui.row().classes(
                            "w-full items-center justify-between gap-2"
                        ):
                            with ui.column().classes("gap-0 min-w-0"):
                                ui.label(
                                    "Relevé du "
                                    + row["statement_date"].strftime(
                                        "%d/%m/%Y"
                                    )
                                ).classes("text-sm font-bold")
                                ui.label(
                                    f"{row['active_transaction_count']} "
                                    "transaction(s) — "
                                    + _money(row["selected_total"])
                                ).classes("text-xs jf-muted")
                                if row["difference"] is not None:
                                    ui.label(
                                        "Différence : "
                                        + _balance_money(row["difference"])
                                    ).classes(
                                        (
                                            "text-xs text-positive"
                                            if abs(
                                                Decimal(row["difference"])
                                            ) < Decimal(".01")
                                            else "text-xs text-negative"
                                        )
                                    )

                            with ui.row().classes("gap-1 shrink-0"):
                                ui.label(
                                    RECONCILIATION_SESSION_STATUSES.get(
                                        row["status"],
                                        row["status"],
                                    )
                                ).classes(
                                    "jf-finance-reconciliation-chip"
                                )
                                ui.button(
                                    "Voir",
                                    icon="visibility",
                                    on_click=(
                                        lambda _event=None,
                                        selected=row["id"]:
                                        session_detail_dialog(selected)
                                    ),
                                ).props(
                                    "flat dense color=primary"
                                )

        def refresh_reconciliation_screen(reset_selection=False):
            if reset_selection:
                reconciliation_selected.clear()
            render_reconciliation_draft.refresh()
            render_reconciliation_balance.refresh()
            render_planned_transactions.refresh()
            render_reconciliation_transactions.refresh()
            render_reconciliation_selection.refresh()
            render_sessions.refresh()
            render_unassigned.refresh()

        def change_reconciliation_payment(_event=None):
            # Changer volontairement de carte ouvre une nouvelle séance.
            refresh_reconciliation_screen(reset_selection=True)

        reconciliation_payment.on_value_change(
            change_reconciliation_payment
        )
        reconciliation_start.on_value_change(
            lambda event: render_reconciliation_transactions.refresh()
        )
        reconciliation_end.on_value_change(
            lambda event: render_reconciliation_transactions.refresh()
        )
        reconciliation_query.on_value_change(
            lambda event: render_reconciliation_transactions.refresh()
        )
        reconciliation_sort.on_value_change(
            lambda event: render_reconciliation_transactions.refresh()
        )

        render_reconciliation_draft()
        render_reconciliation_balance()
        render_planned_transactions()
        render_reconciliation_transactions()
        render_reconciliation_selection()
        render_sessions()

    def reload_options():
        reconciliation_payment.options = _payment_options(
            user_id,
            include_none=False,
        )
        if (
            reconciliation_payment.value
            not in reconciliation_payment.options
        ):
            reconciliation_payment.value = (
                next(iter(reconciliation_payment.options))
                if reconciliation_payment.options
                else None
            )
        reconciliation_payment.update()

        unassigned_target.options = _payment_options(
            user_id,
            include_none=False,
        )
        if unassigned_target.value not in unassigned_target.options:
            unassigned_target.value = (
                next(iter(unassigned_target.options))
                if unassigned_target.options
                else None
            )
        unassigned_target.update()

    return ReconciliationPanelHandle(
        on_refresh=lambda: refresh_reconciliation_screen(),
        on_reload_options=reload_options,
    )
