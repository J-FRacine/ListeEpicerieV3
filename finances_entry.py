"""Panneau Saisie rapide avec services injectés et rechargement des options."""
from dataclasses import dataclass
from datetime import date
from typing import Callable


@dataclass
class EntryPanelHandle:
    on_reload_options: Callable[[], None]

    def reload_options(self) -> None:
        self.on_reload_options()


def build_entry_panel(
    *,
    ui,
    user_id,
    entry_tab,
    TRANSACTION_TYPES,
    TRANSACTION_STATUSES,
    ADD_CATEGORY_OPTION,
    ADD_TAG_OPTION,
    _quick_category_options,
    _quick_tag_options,
    _payment_options,
    list_categories,
    get_or_create_finance_category,
    get_or_create_finance_tag,
    save_transaction,
    _card_payment_dialog,
    refresh_all,
    refresh_dashboard,
) -> EntryPanelHandle:
    # SAISIE
    with ui.tab_panel(
        entry_tab
    ).classes(
        "px-0"
    ):
        with ui.card().classes(
            "w-full max-w-2xl p-4"
        ):
            with ui.row().classes("w-full items-center justify-between gap-2 flex-wrap"):
                ui.label(
                    "Saisie rapide"
                ).classes(
                    "text-xl font-bold"
                )
                ui.button(
                    "Paiement de carte",
                    icon="credit_card",
                    on_click=lambda: _card_payment_dialog(user_id, refresh_all),
                ).props("outline color=primary dense")

            kind = ui.toggle(
                TRANSACTION_TYPES,
                value="expense",
            ).props(
                "dense spread no-caps"
            ).classes(
                "w-full"
            )

            with ui.element(
                "div"
            ).classes(
                "jf-finance-form-grid"
            ):
                amount = ui.number(
                    label="Montant",
                    min=.01,
                    step=.01,
                ).props(
                    "dense outlined"
                ).classes(
                    "jf-finance-field"
                )
                when = ui.input(
                    label="Date",
                    value=(
                        date.today().isoformat()
                    ),
                ).props(
                    "type=date dense outlined"
                ).classes(
                    "jf-finance-field"
                )
                description = ui.input(
                    label="Description"
                ).props(
                    "dense outlined maxlength=160"
                ).classes(
                    "jf-finance-field "
                    "jf-finance-description"
                )

            with ui.row().classes(
                "w-full gap-2 flex-wrap"
            ):
                category = ui.select(
                    _quick_category_options(
                        user_id
                    ),
                    label=(
                        "Catégorie ou "
                        "sous-catégorie"
                    ),
                ).props(
                    "dense outlined clearable "
                    "options-dense"
                ).classes(
                    "min-w-56 grow"
                )
                payment_method = ui.select(
                    _payment_options(
                        user_id
                    ),
                    label="Mode de paiement",
                ).props(
                    "dense outlined clearable "
                    "options-dense"
                ).classes(
                    "min-w-48 grow"
                )

            tags = ui.select(
                _quick_tag_options(
                    user_id
                ),
                label="Étiquettes",
                multiple=True,
            ).props(
                "dense outlined use-chips "
                "clearable options-dense"
            ).classes(
                "w-full"
            )

            def quick_parent_options():
                options = {
                    None: "Catégorie principale",
                }
                current_type = kind.value or "expense"
                for row in list_categories(user_id):
                    if row.get("parent_id") is not None:
                        continue
                    if row.get("category_type") not in (
                        "both",
                        current_type,
                    ):
                        continue
                    options[int(row["id"])] = row["name"]
                return options

            def open_quick_category_dialog():
                with ui.dialog() as dialog:
                    with ui.card().classes(
                        "w-full max-w-lg p-4"
                    ):
                        ui.label(
                            "Ajouter une catégorie"
                        ).classes(
                            "text-xl font-bold"
                        )
                        ui.label(
                            "La nouvelle catégorie sera créée "
                            "et sélectionnée pour la transaction en cours."
                        ).classes(
                            "text-sm jf-muted"
                        )

                        new_name = ui.input(
                            label="Nom de la catégorie",
                            placeholder="Ex. Pharmacie",
                        ).props(
                            "dense outlined maxlength=100 autofocus"
                        ).classes(
                            "w-full mt-2"
                        )

                        parent = ui.select(
                            quick_parent_options(),
                            value=None,
                            label=(
                                "Sous-catégorie de "
                                "(facultatif)"
                            ),
                        ).props(
                            "dense outlined clearable options-dense"
                        ).classes(
                            "w-full"
                        )

                        ui.label(
                            "Les différences de majuscules, "
                            "d’accents et d’espaces sont reconnues "
                            "afin d’éviter les doublons évidents."
                        ).classes(
                            "text-xs jf-muted"
                        )

                        def save_new_category():
                            try:
                                result = (
                                    get_or_create_finance_category(
                                        user_id,
                                        new_name.value,
                                        parent_id=parent.value,
                                        category_type=(
                                            kind.value
                                            or "expense"
                                        ),
                                    )
                                )
                            except Exception as error:
                                ui.notify(
                                    str(error),
                                    type="warning",
                                )
                                return

                            category.options = (
                                _quick_category_options(
                                    user_id
                                )
                            )
                            category.value = result["id"]
                            category.update()
                            dialog.close()

                            ui.notify(
                                (
                                    "Catégorie créée et sélectionnée."
                                    if result["created"]
                                    else (
                                        "Cette catégorie existait déjà; "
                                        "elle a été sélectionnée."
                                    )
                                ),
                                type=(
                                    "positive"
                                    if result["created"]
                                    else "info"
                                ),
                            )
                            refresh_dashboard()

                        with ui.row().classes(
                            "w-full justify-end gap-2 mt-2"
                        ):
                            ui.button(
                                "Annuler",
                                on_click=dialog.close,
                            ).props("flat")
                            ui.button(
                                "Ajouter",
                                icon="add",
                                on_click=save_new_category,
                            ).props(
                                "color=primary"
                            )

                dialog.open()

            def category_quick_changed(event):
                if event.value != ADD_CATEGORY_OPTION:
                    return
                category.value = None
                category.update()
                open_quick_category_dialog()

            category.on_value_change(
                category_quick_changed
            )

            def open_quick_tag_dialog(
                selected_before,
            ):
                with ui.dialog() as dialog:
                    with ui.card().classes(
                        "w-full max-w-lg p-4"
                    ):
                        ui.label(
                            "Ajouter une étiquette"
                        ).classes(
                            "text-xl font-bold"
                        )
                        ui.label(
                            "Les étiquettes déjà sélectionnées "
                            "seront conservées."
                        ).classes(
                            "text-sm jf-muted"
                        )

                        new_name = ui.input(
                            label="Nom de l’étiquette",
                            placeholder="Ex. Vacances 2026",
                        ).props(
                            "dense outlined maxlength=80 autofocus"
                        ).classes(
                            "w-full mt-2"
                        )

                        ui.label(
                            "Les différences de majuscules, "
                            "d’accents et d’espaces sont reconnues "
                            "afin d’éviter les doublons évidents."
                        ).classes(
                            "text-xs jf-muted"
                        )

                        def save_new_tag():
                            try:
                                result = get_or_create_finance_tag(
                                    user_id,
                                    new_name.value,
                                )
                            except Exception as error:
                                ui.notify(
                                    str(error),
                                    type="warning",
                                )
                                return

                            selected = [
                                int(value)
                                for value in selected_before
                                if value not in (
                                    None,
                                    ADD_TAG_OPTION,
                                )
                            ]
                            if result["id"] not in selected:
                                selected.append(
                                    result["id"]
                                )

                            tags.options = (
                                _quick_tag_options(
                                    user_id
                                )
                            )
                            tags.value = selected
                            tags.update()
                            dialog.close()

                            ui.notify(
                                (
                                    "Étiquette créée et sélectionnée."
                                    if result["created"]
                                    else (
                                        "Cette étiquette existait déjà; "
                                        "elle a été sélectionnée."
                                    )
                                ),
                                type=(
                                    "positive"
                                    if result["created"]
                                    else "info"
                                ),
                            )
                            refresh_dashboard()

                        with ui.row().classes(
                            "w-full justify-end gap-2 mt-2"
                        ):
                            ui.button(
                                "Annuler",
                                on_click=dialog.close,
                            ).props("flat")
                            ui.button(
                                "Ajouter",
                                icon="add",
                                on_click=save_new_tag,
                            ).props(
                                "color=primary"
                            )

                dialog.open()

            def tags_quick_changed(event):
                selected = list(event.value or [])
                if ADD_TAG_OPTION not in selected:
                    return
                selected = [
                    value
                    for value in selected
                    if value != ADD_TAG_OPTION
                ]
                tags.value = selected
                tags.update()
                open_quick_tag_dialog(
                    selected
                )

            tags.on_value_change(
                tags_quick_changed
            )

            with ui.expansion(
                "Note, statut, rappel, budget et conciliation",
                icon="tune",
            ).classes(
                "w-full"
            ):
                budget_excluded_quick = ui.checkbox(
                    "Hors budget — transfert, paiement de carte ou déplacement d’épargne", value=False
                )
                ui.label("Le mouvement reste visible dans le Compte bancaire mais est exclu du budget et des KPI.").classes("text-xs jf-muted")
                status = ui.select(
                    TRANSACTION_STATUSES,
                    value="confirmed",
                    label="Statut de transaction",
                ).props(
                    "dense outlined options-dense"
                ).classes(
                    "w-full"
                )
                bank_programmed_quick = ui.checkbox(
                    "Programmée dans le compte bancaire",
                    value=False,
                )
                reminder_enabled_quick = ui.checkbox(
                    "Me rappeler cette transaction le jour prévu",
                    value=False,
                )
                reminder_time_quick = ui.input(
                    label="Heure du rappel", value="09:00"
                ).props("type=time dense outlined").classes("w-full")
                reconciled = ui.checkbox(
                    "Transaction conciliée",
                    value=False,
                )
                reconciliation_date = ui.input(
                    label=(
                        "Date de conciliation "
                        "(facultative)"
                    ),
                ).props(
                    "type=date dense outlined"
                ).classes(
                    "w-full"
                )
                note = ui.textarea(
                    label="Note facultative"
                ).props(
                    "dense outlined autogrow "
                    "maxlength=1000"
                ).classes(
                    "w-full"
                )

            def save_quick():
                try:
                    save_transaction(
                        user_id=user_id,
                        transaction_date=(
                            when.value
                        ),
                        transaction_type=(
                            kind.value
                        ),
                        amount=amount.value,
                        description=(
                            description.value
                        ),
                        category_id=(
                            None
                            if category.value
                            in (
                                None,
                                ADD_CATEGORY_OPTION,
                            )
                            else category.value
                        ),
                        tag_ids=(
                            [
                                value
                                for value
                                in (tags.value or [])
                                if value != ADD_TAG_OPTION
                            ]
                        ),
                        payment_method_id=(
                            payment_method.value
                        ),
                        note=note.value,
                        status=status.value,
                        reconciliation_status=(
                            "reconciled"
                            if reconciled.value
                            else "unreconciled"
                        ),
                        reconciliation_date=(
                            reconciliation_date.value
                            or None
                        ),
                        budget_excluded=budget_excluded_quick.value,
                        bank_programmed=bank_programmed_quick.value,
                        reminder_enabled=reminder_enabled_quick.value,
                        reminder_time=reminder_time_quick.value or "09:00",
                    )
                except Exception as error:
                    ui.notify(
                        str(error),
                        type="warning",
                    )
                    return

                amount.value = None
                description.value = ""
                note.value = ""
                tags.value = []
                reconciled.value = False
                reconciliation_date.value = ""
                budget_excluded_quick.value = False
                bank_programmed_quick.value = False
                reminder_enabled_quick.value = False
                reminder_time_quick.value = "09:00"

                ui.notify(
                    "Transaction enregistrée.",
                    type="positive",
                )
                refresh_all()

            ui.button(
                "Enregistrer",
                icon="save",
                on_click=save_quick,
            ).props(
                "color=primary"
            ).classes(
                "mt-2"
            )


    def reload_options():
        category.options = (
            _quick_category_options(
                user_id
            )
        )
        category.update()

        tags.options = _quick_tag_options(
            user_id
        )
        tags.update()

        payment_method.options = (
            _payment_options(
                user_id
            )
        )
        payment_method.update()

    return EntryPanelHandle(on_reload_options=reload_options)
