"""Panneau Budget construit avec ses dépendances explicitement injectées."""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Callable


@dataclass
class BudgetPanelHandle:
    """Point de liaison utilisé par le parent pour actualiser Budget."""

    on_refresh: Callable[[], None]

    def refresh(self) -> None:
        self.on_refresh()


def build_budget_panel(
    *, ui, user_id, budget_tab, month_state,
    budget_capacity_summary, list_budget_items, budget_forecast,
    list_installment_plans, save_budget_item, save_financing_budget_group,
    delete_financing_budget_group, toggle_budget_item, move_budget_item,
    generate_due_recurrences, _recurrence_options, _category_options,
    _payment_options, _tag_options, _money, _balance_money, _month_label,
    _shift_month, TRANSACTION_TYPES, BUDGET_INPUT_FREQUENCIES,
    FREQUENCY_UNITS, CONFIRMATION_MODES, CREATE_RECURRENCE_OPTION,
    BUDGET_SORT_FIELDS, BUDGET_SORT_DIRECTIONS, refresh_all,
) -> BudgetPanelHandle:
    """Construit l'interface Budget avec le curseur mensuel partagé."""
    with ui.tab_panel(budget_tab).classes("px-0"):
        with ui.row().classes(
            "w-full items-center justify-center gap-2 py-2"
        ) as budget_loading:
            ui.spinner(size="sm")
            ui.label("Calcul du mois et des prévisions…").classes(
                "text-sm jf-muted"
            )
        budget_loading.set_visibility(False)

        async def change_budget_month(offset, reset=False):
            if reset:
                month_state.reset()
            else:
                month_state.shift(offset)

            budget_loading.set_visibility(True)
            try:
                # Laisser le navigateur afficher le sablier avant les calculs.
                await ui.run_javascript(
                    "await new Promise(requestAnimationFrame); return true;"
                )
                render_budget.refresh()
            finally:
                budget_loading.set_visibility(False)

        budget_sort_state = {
            "field": "monthly_amount",
            "direction": "desc",
        }

        def sorted_budget_rows(section_rows, section_type):
            rows_to_sort = list(section_rows)
            if section_type != "expense":
                return rows_to_sort

            field = budget_sort_state["field"]
            direction = budget_sort_state["direction"]
            reverse = direction == "desc"

            # Critère secondaire stable : libellé alphabétique A → Z.
            rows_to_sort.sort(
                key=lambda item: str(item.get("description") or "").casefold()
            )

            if field == "description":
                rows_to_sort.sort(
                    key=lambda item: str(item.get("description") or "").casefold(),
                    reverse=reverse,
                )
            elif field == "monthly_amount":
                rows_to_sort.sort(
                    key=lambda item: Decimal(item.get("monthly_amount") or 0),
                    reverse=reverse,
                )
            elif field == "biweekly_amount":
                rows_to_sort.sort(
                    key=lambda item: Decimal(item.get("biweekly_amount") or 0),
                    reverse=reverse,
                )
            elif field == "effective_start":
                missing_date = date.min if reverse else date.max
                rows_to_sort.sort(
                    key=lambda item: item.get("effective_start") or missing_date,
                    reverse=reverse,
                )
            elif field == "custom":
                rows_to_sort.sort(
                    key=lambda item: int(item.get("sort_order") or 0),
                    reverse=reverse,
                )
            return rows_to_sort

        def budget_item_dialog(row=None, clone_period=False):
            source_row = dict(row) if row else None
            edit_id = None if clone_period else (row["id"] if row else None)
            suggested_start = ""
            if clone_period and source_row and source_row.get("effective_end"):
                suggested_start = (
                    source_row["effective_end"] + timedelta(days=1)
                ).isoformat()

            recurrence_options = _recurrence_options(user_id)
            recurrence_options[CREATE_RECURRENCE_OPTION] = (
                "+ Créer une nouvelle récurrence"
            )

            with ui.dialog() as dialog:
                with ui.card().classes("w-full max-w-2xl p-4"):
                    ui.label(
                        "Nouvelle période budgétaire" if clone_period else (
                            "Modifier le poste" if row else "Nouveau poste budgétaire"
                        )
                    ).classes("text-xl font-bold")
                    kind_budget = ui.toggle(
                        TRANSACTION_TYPES,
                        value=source_row["item_type"] if source_row else "expense",
                    ).props("dense spread no-caps").classes("w-full")
                    description_budget = ui.input(
                        label="Description",
                        value=source_row["description"] if source_row else "",
                    ).props("dense outlined maxlength=160").classes("w-full")
                    with ui.row().classes("w-full gap-2 flex-wrap"):
                        frequency_budget = ui.select(
                            BUDGET_INPUT_FREQUENCIES,
                            value=(
                                source_row["input_frequency"]
                                if source_row else "monthly"
                            ),
                            label="Montant saisi en",
                        ).props(
                            "dense outlined options-dense"
                        ).classes("grow min-w-44")
                        amount_budget = ui.number(
                            label="Montant",
                            value=(
                                source_row["input_amount"]
                                if source_row else None
                            ),
                            min=.01,
                            step=.01,
                        ).props("dense outlined").classes("grow min-w-36")
                    biweekly_override = ui.number(
                        label="Montant par paie personnalisé — facultatif",
                        value=(
                            source_row.get("biweekly_override")
                            if source_row else None
                        ),
                        min=.01,
                        step=.01,
                    ).props("dense outlined clearable").classes("w-full")
                    ui.label(
                        "Le Budget représente les revenus et dépenses fixes. "
                        "Le reste calculé alimente automatiquement la capacité "
                        "disponible du Tableau."
                    ).classes("text-xs jf-muted")
                    with ui.row().classes("w-full gap-2 flex-wrap"):
                        effective_start = ui.input(
                            label="Début — facultatif",
                            value=(
                                suggested_start
                                or (
                                    source_row.get("effective_start").isoformat()
                                    if source_row
                                    and source_row.get("effective_start")
                                    else ""
                                )
                            ),
                        ).props(
                            "type=date dense outlined clearable"
                        ).classes("grow min-w-44")
                        effective_end = ui.input(
                            label="Fin — facultatif",
                            value=(
                                ""
                                if clone_period
                                else (
                                    source_row.get("effective_end").isoformat()
                                    if source_row
                                    and source_row.get("effective_end")
                                    else ""
                                )
                            ),
                        ).props(
                            "type=date dense outlined clearable"
                        ).classes("grow min-w-44")
                    ui.label(
                        "Exemple : ancien loyer jusqu’au 30 juin, nouveau loyer "
                        "à partir du 1er juillet. Les mois passés conservent ainsi "
                        "leur budget historique."
                    ).classes("text-xs jf-muted")

                    recurrence_budget = ui.select(
                        recurrence_options,
                        value=(
                            source_row.get("recurrence_id")
                            if source_row else None
                        ),
                        label="Récurrence associée — facultatif",
                    ).props(
                        "dense outlined clearable options-dense"
                    ).classes("w-full")

                    with ui.column().classes(
                        "w-full gap-2 p-3 rounded-borders bg-grey-1"
                    ) as new_recurrence_box:
                        ui.label(
                            "Nouvelle récurrence liée"
                        ).classes("font-bold text-primary")
                        ui.label(
                            "Les valeurs sont proposées à partir du poste Budget. "
                            "La récurrence et le poste seront enregistrés ensemble : "
                            "si l’un échoue, aucun des deux n’est conservé."
                        ).classes("text-xs jf-muted")
                        recurrence_description = ui.input(
                            label="Description de la récurrence",
                            value="",
                        ).props(
                            "dense outlined maxlength=160"
                        ).classes("w-full")
                        with ui.row().classes("w-full gap-2 flex-wrap"):
                            recurrence_amount = ui.number(
                                label="Montant de la récurrence",
                                value=None,
                                min=.01,
                                step=.01,
                            ).props("dense outlined").classes("grow min-w-36")
                            recurrence_interval = ui.number(
                                label="Tous les",
                                value=1,
                                min=1,
                                max=365,
                                step=1,
                            ).props("dense outlined").classes("w-28")
                            recurrence_unit = ui.select(
                                FREQUENCY_UNITS,
                                value="month",
                                label="Unité",
                            ).props(
                                "dense outlined options-dense"
                            ).classes("grow min-w-36")
                        with ui.row().classes("w-full gap-2 flex-wrap"):
                            recurrence_start = ui.input(
                                label="Début de la récurrence",
                                value=date.today().isoformat(),
                            ).props(
                                "type=date dense outlined"
                            ).classes("grow min-w-44")
                            recurrence_end = ui.input(
                                label="Fin de la récurrence — facultatif",
                                value="",
                            ).props(
                                "type=date dense outlined clearable"
                            ).classes("grow min-w-44")
                        with ui.row().classes("w-full gap-2 flex-wrap"):
                            recurrence_category = ui.select(
                                {None: "Aucune", **_category_options(user_id)},
                                value=None,
                                label="Catégorie — facultatif",
                            ).props(
                                "dense outlined clearable options-dense"
                            ).classes("grow min-w-52")
                            recurrence_payment = ui.select(
                                _payment_options(user_id),
                                value=None,
                                label="Mode de paiement — facultatif",
                            ).props(
                                "dense outlined clearable options-dense"
                            ).classes("grow min-w-52")
                        recurrence_tags = ui.select(
                            _tag_options(user_id),
                            value=[],
                            label="Étiquettes — facultatif",
                            multiple=True,
                        ).props(
                            "dense outlined use-chips clearable options-dense"
                        ).classes("w-full")
                        recurrence_mode = ui.select(
                            CONFIRMATION_MODES,
                            value="confirm",
                            label="Création des occurrences",
                        ).props(
                            "dense outlined options-dense"
                        ).classes("w-full")
                        recurrence_bank_programmed = ui.checkbox(
                            "Programmée dans le compte bancaire",
                            value=False,
                        )
                        recurrence_reminder = ui.checkbox(
                            "Me rappeler chaque occurrence le jour prévu",
                            value=False,
                        )
                        recurrence_reminder_time = ui.input(
                            label="Heure du rappel",
                            value="09:00",
                        ).props(
                            "type=time dense outlined"
                        ).classes("w-full")

                    sync_budget_recurrence = ui.checkbox(
                        "Synchroniser le montant et la date de fin avec la récurrence",
                        value=(
                            bool(source_row.get("sync_from_recurrence", True))
                            if source_row else True
                        ),
                    )
                    ui.label(
                        "Avec la synchronisation active, le montant du poste suit "
                        "la récurrence et la date de fin du poste est appliquée à "
                        "la récurrence. Les transactions confirmées ne sont jamais "
                        "supprimées."
                    ).classes("text-xs jf-muted")
                    allow_overlap = ui.checkbox(
                        "Autoriser volontairement un chevauchement avec une autre période identique",
                        value=False,
                    ).classes("text-sm")
                    note_budget = ui.textarea(
                        label="Note facultative",
                        value=source_row.get("note") if source_row else "",
                    ).props(
                        "dense outlined autogrow maxlength=1000"
                    ).classes("w-full")

                    def sync_override_visibility(_event=None):
                        biweekly_override.visible = (
                            frequency_budget.value == "monthly"
                        )

                    def update_new_recurrence_visibility(_event=None):
                        creating = (
                            recurrence_budget.value
                            == CREATE_RECURRENCE_OPTION
                        )
                        new_recurrence_box.visible = creating
                        if not creating:
                            return
                        recurrence_description.value = (
                            description_budget.value or ""
                        )
                        recurrence_amount.value = amount_budget.value
                        if frequency_budget.value == "biweekly":
                            recurrence_unit.value = "week"
                            recurrence_interval.value = 2
                        else:
                            recurrence_unit.value = "month"
                            recurrence_interval.value = 1
                        recurrence_start.value = (
                            effective_start.value
                            or date.today().isoformat()
                        )
                        recurrence_end.value = effective_end.value or ""

                    frequency_budget.on_value_change(
                        sync_override_visibility
                    )
                    recurrence_budget.on_value_change(
                        update_new_recurrence_visibility
                    )
                    sync_override_visibility()
                    update_new_recurrence_visibility()

                    def save_budget_now():
                        creating_recurrence = (
                            recurrence_budget.value
                            == CREATE_RECURRENCE_OPTION
                        )
                        new_recurrence = None
                        selected_recurrence = recurrence_budget.value
                        if creating_recurrence:
                            selected_recurrence = None
                            new_recurrence = {
                                "description": (
                                    recurrence_description.value
                                    or description_budget.value
                                ),
                                "amount": (
                                    recurrence_amount.value
                                    if recurrence_amount.value not in (None, "")
                                    else amount_budget.value
                                ),
                                "frequency_unit": recurrence_unit.value,
                                "frequency_interval": recurrence_interval.value,
                                "start_date": (
                                    recurrence_start.value
                                    or effective_start.value
                                    or date.today().isoformat()
                                ),
                                "end_date": (
                                    recurrence_end.value
                                    or effective_end.value
                                    or None
                                ),
                                "category_id": recurrence_category.value,
                                "tag_ids": recurrence_tags.value or [],
                                "payment_method_id": recurrence_payment.value,
                                "confirmation_mode": recurrence_mode.value,
                                "bank_programmed": recurrence_bank_programmed.value,
                                "reminder_enabled": recurrence_reminder.value,
                                "reminder_time": (
                                    recurrence_reminder_time.value or "09:00"
                                ),
                                "note": note_budget.value,
                            }

                        try:
                            # Lorsqu'on crée une nouvelle période à partir d'un
                            # poste existant, l'ancienne période est fermée la
                            # veille et sa récurrence est détachée. La nouvelle
                            # période peut ainsi reprendre la même récurrence.
                            if clone_period and source_row:
                                if not effective_start.value:
                                    raise ValueError(
                                        "Indiquez la date de début de la nouvelle période."
                                    )
                                new_start = date.fromisoformat(
                                    effective_start.value
                                )
                                old_start = source_row.get("effective_start")
                                if old_start and new_start <= old_start:
                                    raise ValueError(
                                        "La nouvelle période doit commencer après l’ancienne."
                                    )
                                old_end = source_row.get("effective_end")
                                if old_end is None or old_end >= new_start:
                                    old_end = new_start - timedelta(days=1)
                                save_budget_item(
                                    user_id=user_id,
                                    budget_item_id=source_row["id"],
                                    item_type=source_row["item_type"],
                                    description=source_row["description"],
                                    input_frequency=source_row["input_frequency"],
                                    input_amount=source_row["input_amount"],
                                    biweekly_override=source_row.get(
                                        "biweekly_override"
                                    ),
                                    note=source_row.get("note"),
                                    recurrence_id=None,
                                    sync_from_recurrence=False,
                                    effective_start=source_row.get(
                                        "effective_start"
                                    ),
                                    effective_end=old_end,
                                    allow_overlap=True,
                                )

                            save_budget_item(
                                user_id=user_id,
                                budget_item_id=edit_id,
                                item_type=kind_budget.value,
                                description=description_budget.value,
                                input_frequency=frequency_budget.value,
                                input_amount=amount_budget.value,
                                biweekly_override=(
                                    biweekly_override.value
                                    if frequency_budget.value == "monthly"
                                    else None
                                ),
                                note=note_budget.value,
                                recurrence_id=selected_recurrence,
                                sync_from_recurrence=(
                                    sync_budget_recurrence.value
                                ),
                                effective_start=(
                                    effective_start.value or None
                                ),
                                effective_end=(
                                    effective_end.value or None
                                ),
                                allow_overlap=allow_overlap.value,
                                new_recurrence=new_recurrence,
                            )
                            if creating_recurrence:
                                generate_due_recurrences(user_id)
                        except Exception as error:
                            ui.notify(str(error), type="warning")
                            return
                        dialog.close()
                        ui.notify(
                            (
                                "Poste budgétaire et récurrence enregistrés."
                                if creating_recurrence
                                else "Poste budgétaire enregistré."
                            ),
                            type="positive",
                        )
                        refresh_all()

                    with ui.row().classes("w-full justify-end gap-2"):
                        ui.button(
                            "Annuler", on_click=dialog.close
                        ).props("flat")
                        ui.button(
                            "Enregistrer",
                            icon="save",
                            on_click=save_budget_now,
                        ).props("color=primary")
            dialog.open()

        def financing_budget_group_dialog(row=None):
            current = dict(row or {})
            plans = list_installment_plans(user_id, include_inactive=True)
            options = {
                int(plan["id"]): (
                    str(plan.get("provider_name") or "") + " — " + str(plan.get("description") or "")
                ).strip(" —")
                for plan in plans
            }
            with ui.dialog() as dialog:
                with ui.card().classes("w-full max-w-3xl p-4"):
                    ui.label(
                        "Modifier le groupe de financements" if current else "Nouveau groupe de financements"
                    ).classes("text-xl font-bold")
                    ui.label(
                        "Ce poste devient une dépense fixe du Budget. Ses versements restent visibles dans l’Historique et la conciliation, mais ne sont pas recomptés comme dépenses variables du Tableau."
                    ).classes("text-xs jf-muted")
                    group_name = ui.input(
                        label="Nom du poste",
                        value=current.get("description", ""),
                        placeholder="Ex. Financement MC CDN TIRE",
                    ).props("dense outlined maxlength=160").classes("w-full")
                    selected_plans = ui.select(
                        options,
                        value=current.get("financing_plan_ids") or [],
                        label="Financements associés",
                        multiple=True,
                    ).props("dense outlined use-chips clearable options-dense").classes("w-full")
                    ui.label(
                        "Un financement ne peut appartenir qu’à un seul groupe Budget à la fois."
                    ).classes("text-xs jf-muted")
                    with ui.row().classes("w-full gap-2 flex-wrap"):
                        start_group = ui.input(
                            label="Début — facultatif",
                            value=current.get("effective_start").isoformat() if current.get("effective_start") else "",
                        ).props("type=date dense outlined clearable").classes("grow min-w-44")
                        end_group = ui.input(
                            label="Fin — facultatif",
                            value=current.get("effective_end").isoformat() if current.get("effective_end") else "",
                        ).props("type=date dense outlined clearable").classes("grow min-w-44")
                    note_group = ui.textarea(
                        label="Note facultative", value=current.get("note") or ""
                    ).props("dense outlined autogrow maxlength=1000").classes("w-full")

                    def save_group_now():
                        try:
                            save_financing_budget_group(
                                user_id,
                                budget_item_id=current.get("id"),
                                description=group_name.value,
                                plan_ids=selected_plans.value or [],
                                effective_start=start_group.value or None,
                                effective_end=end_group.value or None,
                                note=note_group.value,
                            )
                        except Exception as error:
                            ui.notify(str(error), type="warning")
                            return
                        dialog.close()
                        ui.notify("Groupe de financements enregistré.", type="positive")
                        refresh_all()

                    def delete_group_now():
                        try:
                            delete_financing_budget_group(user_id, current["id"])
                        except Exception as error:
                            ui.notify(str(error), type="warning")
                            return
                        dialog.close()
                        ui.notify("Groupe de financements supprimé.", type="positive")
                        refresh_all()

                    with ui.row().classes("w-full justify-between gap-2 mt-2"):
                        if current:
                            ui.button(
                                "Supprimer le groupe", icon="delete", on_click=delete_group_now
                            ).props("flat color=negative")
                        else:
                            ui.element("span")
                        with ui.row().classes("gap-2"):
                            ui.button("Annuler", on_click=dialog.close).props("flat")
                            ui.button("Enregistrer", icon="save", on_click=save_group_now).props("color=primary")
            dialog.open()

        def change_budget_state(item_id, value):
            try:
                toggle_budget_item(user_id, item_id, value)
            except Exception as error:
                ui.notify(str(error), type="warning")
            refresh_all()

        def change_budget_order(item_id, direction):
            try:
                move_budget_item(user_id, item_id, direction)
            except Exception as error:
                ui.notify(str(error), type="warning")
            render_budget.refresh()

        @ui.refreshable
        def render_budget():
            capacity_budget = budget_capacity_summary(user_id, month_state.value)
            # budget_capacity_summary contient déjà le résumé du mois; ne
            # pas relancer budget_summary évite une lecture DB complète.
            summary_budget = capacity_budget
            rows = list_budget_items(
                user_id, include_inactive=True, month_value=month_state.value
            )
            with ui.row().classes("w-full items-start justify-between gap-2 flex-wrap"):
                with ui.column().classes("gap-0"):
                    ui.label("Budget — structure fixe").classes("text-xl font-bold")
                    ui.label(
                        "Revenus et dépenses fixes applicables à "
                        + _month_label(month_state.value)
                        + ". Le résultat détermine la portion disponible pour les dépenses variables."
                    ).classes("text-xs jf-muted")
                with ui.row().classes("gap-1 flex-wrap"):
                    ui.button(
                        icon="chevron_left",
                        on_click=lambda: change_budget_month(-1),
                    ).props("flat round dense")
                    ui.button(
                        _month_label(month_state.value),
                        on_click=lambda: change_budget_month(0, reset=True),
                    ).props("flat dense")
                    ui.button(
                        icon="chevron_right",
                        on_click=lambda: change_budget_month(1),
                    ).props("flat round dense")
                    ui.button(
                        "Ajouter un poste", icon="add",
                        on_click=lambda: budget_item_dialog(),
                    ).props("color=primary dense")
                    ui.button(
                        "Groupe de financements", icon="payments",
                        on_click=lambda: financing_budget_group_dialog(),
                    ).props("outline color=primary dense")

            with ui.element("div").classes("jf-finance-summary-grid"):
                for label, value, css in (
                    ("Revenus fixes mensuels", summary_budget["monthly_income"], "jf-finance-income"),
                    ("Dépenses fixes mensuelles", summary_budget["monthly_expense"], "jf-finance-expense"),
                    ("Reste mensuel moyen", summary_budget["monthly_remaining"], "jf-finance-income" if summary_budget["monthly_remaining"] >= 0 else "jf-finance-expense"),
                    ("Reste par paie", summary_budget["biweekly_remaining"], "jf-finance-income" if summary_budget["biweekly_remaining"] >= 0 else "jf-finance-expense"),
                    (f"Disponible ce mois — {capacity_budget.get('pay_count', 0)} paie(s)", capacity_budget.get("available_month_base", capacity_budget.get("available_month", 0)), "jf-finance-income" if Decimal(capacity_budget.get("available_month_base", capacity_budget.get("available_month", 0))) >= 0 else "jf-finance-expense"),
                ):
                    with ui.element("div").classes("jf-finance-summary"):
                        ui.label(label).classes("jf-finance-summary-label")
                        ui.label(_balance_money(value)).classes("jf-finance-summary-value " + css)

            def render_budget_rows_card(section_rows, section_type, *, empty="Aucun poste."):
                ordered_rows = sorted_budget_rows(section_rows, section_type)
                with ui.card().classes("w-full p-0 overflow-hidden"):
                    if not ordered_rows:
                        ui.label(empty).classes("p-4 text-sm jf-muted")
                    for row in ordered_rows:
                        active_month = bool(row.get("effective_for_month", True))
                        row_class = "jf-finance-budget-row" + (" opacity-50" if not row.get("is_active", True) else "")
                        with ui.element("div").classes(row_class):
                            with ui.column().classes("gap-0 min-w-0"):
                                ui.label(row["description"]).classes("font-semibold truncate").tooltip(row["description"])
                                if row.get("budget_financing_group"):
                                    detail = "Groupe de financements"
                                else:
                                    detail = BUDGET_INPUT_FREQUENCIES.get(row["input_frequency"], row["input_frequency"])
                                if row.get("biweekly_is_override"):
                                    detail += " • montant par paie personnalisé"
                                if not row.get("is_active", True):
                                    detail += " • désactivé"
                                ui.label(detail).classes("text-xs jf-muted")
                                start_value = row.get("effective_start")
                                end_value = row.get("effective_end")
                                if start_value or end_value:
                                    if start_value and end_value:
                                        period_text = f"Du {start_value.strftime('%d/%m/%Y')} au {end_value.strftime('%d/%m/%Y')}"
                                    elif start_value:
                                        period_text = f"Depuis le {start_value.strftime('%d/%m/%Y')}"
                                    else:
                                        period_text = f"Jusqu’au {end_value.strftime('%d/%m/%Y')}"
                                    ui.label(period_text).classes("text-xs text-primary")
                                if row.get("budget_financing_group"):
                                    names = row.get("financing_plan_names") or []
                                    ui.label(
                                        f"{len(names)} financement(s) : " + ", ".join(names)
                                    ).classes("text-xs text-primary").tooltip(", ".join(names))
                                elif row.get("recurrence_id"):
                                    link_text = "Lié à « " + str(row.get("recurrence_description") or "récurrence") + " »"
                                    if row.get("sync_from_recurrence"):
                                        link_text += " • synchronisé"
                                    ui.label(link_text).classes("text-xs text-primary")
                            ui.label(_money(row["monthly_amount"]) + " / mois").classes("jf-finance-budget-money")
                            ui.label(_money(row["biweekly_amount"]) + " / paie").classes("jf-finance-budget-money")
                            with ui.row().classes("gap-0 shrink-0"):
                                if section_type == "income" or budget_sort_state["field"] == "custom":
                                    ui.button(icon="keyboard_arrow_up", on_click=lambda _event=None, selected=row["id"]: change_budget_order(selected, "up")).props("flat dense round size=sm")
                                    ui.button(icon="keyboard_arrow_down", on_click=lambda _event=None, selected=row["id"]: change_budget_order(selected, "down")).props("flat dense round size=sm")
                                ui.switch(value=row["is_active"], on_change=lambda event, selected=row["id"]: change_budget_state(selected, event.value)).props("dense")
                                if row.get("budget_financing_group"):
                                    ui.button(icon="edit", on_click=lambda _event=None, selected=row: financing_budget_group_dialog(selected)).props("flat dense round size=sm color=primary")
                                else:
                                    ui.button(icon="event_repeat", on_click=lambda _event=None, selected=row: budget_item_dialog(selected, clone_period=True)).props("flat dense round size=sm color=secondary").tooltip("Créer une nouvelle période")
                                    ui.button(icon="edit", on_click=lambda _event=None, selected=row: budget_item_dialog(selected)).props("flat dense round size=sm color=primary")
                    if ordered_rows:
                        total_month = sum((Decimal(row.get("monthly_amount") or 0) for row in ordered_rows), Decimal("0.00"))
                        total_pay = sum((Decimal(row.get("biweekly_amount") or 0) for row in ordered_rows), Decimal("0.00"))
                        with ui.element("div").classes("jf-finance-budget-row font-bold bg-grey-1"):
                            ui.label("Total de la section").classes("font-bold")
                            ui.label(_money(total_month) + " / mois").classes("jf-finance-budget-money")
                            ui.label(_money(total_pay) + " / paie").classes("jf-finance-budget-money")
                            ui.element("span")

            # Revenus : même présentation compacte, uniquement selon la période consultée.
            income_rows = [row for row in rows if row["item_type"] == "income"]
            ui.label("Revenus fixes").classes("text-lg font-bold mt-2")
            render_budget_rows_card(income_rows, "income")

            with ui.row().classes("w-full items-end justify-between gap-2 flex-wrap mt-2"):
                ui.label("Dépenses fixes actives").classes("text-lg font-bold")
                with ui.row().classes("items-end gap-2 flex-wrap"):
                    budget_sort_field = ui.select(
                        BUDGET_SORT_FIELDS, value=budget_sort_state["field"], label="Trier par"
                    ).props("dense outlined options-dense").classes("min-w-44")
                    budget_sort_direction = ui.select(
                        BUDGET_SORT_DIRECTIONS, value=budget_sort_state["direction"], label="Sens"
                    ).props("dense outlined options-dense").classes("min-w-32")
                    def change_budget_sort(_event=None):
                        budget_sort_state["field"] = budget_sort_field.value or "monthly_amount"
                        budget_sort_state["direction"] = budget_sort_direction.value or "desc"
                        render_budget.refresh()
                    budget_sort_field.on_value_change(change_budget_sort)
                    budget_sort_direction.on_value_change(change_budget_sort)

            displayed_month = month_state.value
            displayed_end = _shift_month(displayed_month, 1) - timedelta(days=1)
            expense_rows = [row for row in rows if row["item_type"] == "expense"]
            active_expenses = []
            future_expenses = []
            archived_expenses = []
            for row in expense_rows:
                start_value = row.get("effective_start")
                end_value = row.get("effective_end")
                if end_value and end_value < displayed_month:
                    archived_expenses.append(row)
                elif start_value and start_value > displayed_end:
                    future_expenses.append(row)
                else:
                    active_expenses.append(row)

            render_budget_rows_card(active_expenses, "expense", empty="Aucune dépense fixe active pour ce mois.")

            if future_expenses:
                with ui.expansion(
                    f"À venir ({len(future_expenses)})", icon="event_upcoming", value=True
                ).classes("w-full mt-2"):
                    ui.label(
                        "Ces postes ne réduisent pas le disponible du mois affiché tant que leur période n’a pas commencé."
                    ).classes("text-xs jf-muted mb-1")
                    render_budget_rows_card(future_expenses, "expense")

            if archived_expenses:
                with ui.expansion(
                    f"Archives ({len(archived_expenses)})", icon="inventory_2", value=False
                ).classes("w-full mt-2"):
                    ui.label(
                        "Ces postes sont conservés pour l’historique et ne sont pas inclus dans le Budget du mois affiché."
                    ).classes("text-xs jf-muted mb-1")
                    render_budget_rows_card(archived_expenses, "expense")

            ui.label("Prévisions").classes("text-lg font-bold mt-3")
            ui.label(
                "Solde variable de fin de mois = disponible de base + report précédent − dépenses variables prévues/réalisées."
            ).classes("text-xs jf-muted")
            forecast_rows = budget_forecast(
                user_id,
                month_state.value,
                months=6,
                initial_capacity=capacity_budget,
            )
            with ui.card().classes("w-full p-0 overflow-hidden"):
                with ui.element("div").classes("jf-finance-cashflow-head").style(
                    "display:grid;grid-template-columns:minmax(8rem,1fr) 7rem 7rem 7rem 8rem;gap:.5rem;"
                ):
                    ui.label("Mois")
                    ui.label("Disponible").classes("text-right")
                    ui.label("Report").classes("text-right")
                    ui.label("Variables").classes("text-right")
                    ui.label("Solde fin").classes("text-right")
                for forecast in forecast_rows:
                    with ui.element("div").classes("jf-finance-cashflow-row").style(
                        "display:grid;grid-template-columns:minmax(8rem,1fr) 7rem 7rem 7rem 8rem;gap:.5rem;"
                    ):
                        ui.label(_month_label(forecast["month"]) + f" · {forecast['pay_count']} paie(s)")
                        ui.label(_balance_money(forecast["available_base"])).classes("text-right")
                        ui.label(_balance_money(forecast["carry_in"])).classes("text-right")
                        ui.label(_money(forecast["variable_expenses"])).classes("text-right")
                        css = "jf-finance-income" if forecast["ending_balance"] >= 0 else "jf-finance-expense"
                        ui.label(_balance_money(forecast["ending_balance"])).classes("text-right font-bold " + css)
        render_budget()
        return BudgetPanelHandle(
            on_refresh=lambda: render_budget.refresh(),
        )
