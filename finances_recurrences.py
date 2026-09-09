"""Panneau Récurrences et dialogue partagé, avec services injectés."""
from dataclasses import dataclass
from datetime import date
from typing import Callable


@dataclass
class RecurrencesPanelHandle:
    on_refresh: Callable[[], None]
    on_open_dialog: Callable[..., None]

    def refresh(self) -> None:
        self.on_refresh()

    def open_dialog(self, *args, **kwargs) -> None:
        self.on_open_dialog(*args, **kwargs)


def build_recurrences_panel(
    *,
    ui,
    user_id,
    recurring_tab,
    TRANSACTION_TYPES,
    FREQUENCY_UNITS,
    CONFIRMATION_MODES,
    delete_recurrence,
    save_recurrence,
    generate_due_recurrences,
    list_recurrences,
    toggle_recurrence,
    _category_options,
    _payment_options,
    _tag_options,
    _signed,
    refresh_all,
) -> RecurrencesPanelHandle:
    # RÉCURRENCES
    with ui.tab_panel(recurring_tab).classes("px-0"):
        recurrence_box = ui.column().classes("w-full gap-2")

        def delete_recurrence_dialog(row):
            with ui.dialog() as delete_dialog:
                with ui.card().classes("w-full max-w-xl p-4"):
                    ui.label("Supprimer la récurrence").classes(
                        "text-xl font-bold"
                    )
                    ui.label(row["description"]).classes("font-semibold")
                    ui.label(
                        "Les transactions déjà confirmées resteront toujours dans l’historique. "
                        "Choisis seulement ce qui doit arriver aux occurrences encore prévues."
                    ).classes("text-sm jf-muted")

                    def remove_recurrence(delete_planned):
                        try:
                            delete_recurrence(
                                user_id,
                                row["id"],
                                delete_planned=delete_planned,
                            )
                        except Exception as error:
                            ui.notify(str(error), type="warning")
                            return
                        delete_dialog.close()
                        ui.notify("Récurrence supprimée.", type="positive")
                        refresh_all()

                    with ui.column().classes("w-full gap-2 mt-2"):
                        ui.button(
                            "Supprimer aussi les transactions prévues non confirmées",
                            icon="delete_sweep",
                            on_click=lambda: remove_recurrence(True),
                        ).props("color=negative").classes("w-full")
                        ui.button(
                            "Conserver les transactions prévues comme transactions indépendantes",
                            icon="keep",
                            on_click=lambda: remove_recurrence(False),
                        ).props("outline color=primary").classes("w-full")
                    with ui.row().classes("w-full justify-end"):
                        ui.button("Annuler", on_click=delete_dialog.close).props("flat")
            delete_dialog.open()

        def recurrence_dialog(row=None):
            with ui.dialog() as dialog:
                with ui.card().classes("w-full max-w-2xl p-4"):
                    ui.label(
                        "Modifier la récurrence" if row else "Nouvelle récurrence"
                    ).classes("text-xl font-bold")
                    kind = ui.toggle(
                        TRANSACTION_TYPES,
                        value=row["transaction_type"] if row else "expense",
                    ).props("dense spread no-caps").classes("w-full")
                    with ui.element("div").classes("jf-finance-form-grid"):
                        amount = ui.number(
                            label="Montant",
                            value=row["amount"] if row else None,
                            min=.01,
                            step=.01,
                        ).props("dense outlined").classes("jf-finance-field")
                        start_date = ui.input(
                            label="Début",
                            value=(
                                row["start_date"].isoformat()
                                if row else date.today().isoformat()
                            ),
                        ).props("type=date dense outlined").classes(
                            "jf-finance-field"
                        )
                        description = ui.input(
                            label="Description",
                            value=row["description"] if row else "",
                        ).props("dense outlined maxlength=160").classes(
                            "jf-finance-field jf-finance-description"
                        )
                    with ui.row().classes("w-full gap-2 flex-wrap"):
                        interval = ui.number(
                            label="Tous les",
                            value=row["frequency_interval"] if row else 1,
                            min=1,
                            max=365,
                            step=1,
                        ).props("dense outlined").classes("w-28")
                        unit = ui.select(
                            FREQUENCY_UNITS,
                            value=row["frequency_unit"] if row else "month",
                            label="Unité",
                        ).props("dense outlined options-dense").classes(
                            "grow min-w-36"
                        )
                        end_date = ui.input(
                            label="Fin facultative",
                            value=(
                                row["end_date"].isoformat()
                                if row and row["end_date"] else ""
                            ),
                        ).props("type=date dense outlined").classes(
                            "grow min-w-40"
                        )
                    with ui.row().classes(
                        "w-full gap-2 flex-wrap"
                    ):
                        category = ui.select(
                            {
                                None: "Aucune",
                                **_category_options(
                                    user_id
                                ),
                            },
                            value=(
                                row[
                                    "category_id"
                                ]
                                if row
                                else None
                            ),
                            label="Catégorie",
                        ).props(
                            "dense outlined clearable "
                            "options-dense"
                        ).classes(
                            "min-w-52 grow"
                        )
                        payment_method = ui.select(
                            _payment_options(
                                user_id
                            ),
                            value=(
                                row.get(
                                    "payment_method_id"
                                )
                                if row
                                else None
                            ),
                            label=(
                                "Mode de paiement "
                                "par défaut"
                            ),
                        ).props(
                            "dense outlined clearable "
                            "options-dense"
                        ).classes(
                            "min-w-48 grow"
                        )
                    tags = ui.select(
                        _tag_options(user_id),
                        value=list(row["tag_ids"]) if row else [],
                        label="Étiquettes",
                        multiple=True,
                    ).props(
                        "dense outlined use-chips clearable options-dense"
                    ).classes("w-full")
                    budget_excluded_rec = ui.checkbox(
                        "Hors budget — transfert, paiement de carte ou déplacement d’épargne",
                        value=bool(row.get("budget_excluded")) if row else False,
                    )
                    ui.label("Les occurrences sont exclues du budget, mais continuent d’affecter le solde du compte si un compte bancaire est choisi.").classes("text-xs jf-muted")
                    bank_programmed_rec = ui.checkbox(
                        "Programmée dans le compte bancaire",
                        value=bool(row.get("bank_programmed")) if row else False,
                    )
                    reminder_enabled_rec = ui.checkbox(
                        "Me rappeler chaque occurrence le jour prévu",
                        value=bool(row.get("reminder_enabled")) if row else False,
                    )
                    reminder_time_rec = ui.input(
                        label="Heure du rappel",
                        value=str(row.get("reminder_time") or "09:00")[:5] if row else "09:00",
                    ).props("type=time dense outlined").classes("w-full")
                    ui.label(
                        "Le rappel d’une récurrence est envoyé même si l’occurrence n’a pas encore été matérialisée dans l’Historique."
                    ).classes("text-xs jf-muted")
                    if row:
                        ui.label(
                            "Si tu modifies la date, le montant ou la fréquence, les occurrences prévues non confirmées sont recalculées automatiquement. Les transactions confirmées restent intactes. Une occurrence rétroactive créée par la correction reste À confirmer."
                        ).classes("text-xs jf-muted")
                    mode = ui.select(
                        CONFIRMATION_MODES,
                        value=row["confirmation_mode"] if row else "confirm",
                        label="Création des occurrences",
                    ).props("dense outlined options-dense").classes("w-full")
                    note = ui.textarea(
                        label="Note facultative",
                        value=row["note"] if row else "",
                    ).props("dense outlined autogrow maxlength=1000").classes(
                        "w-full"
                    )

                    def save_rec():
                        try:
                            save_recurrence(
                                user_id=user_id,
                                recurrence_id=row["id"] if row else None,
                                transaction_type=kind.value,
                                description=description.value,
                                amount=amount.value,
                                category_id=category.value,
                                tag_ids=tags.value or [],
                                payment_method_id=(
                                    payment_method.value
                                ),
                                note=note.value,
                                frequency_unit=unit.value,
                                frequency_interval=interval.value,
                                start_date=start_date.value,
                                end_date=end_date.value or None,
                                confirmation_mode=mode.value,
                                budget_excluded=budget_excluded_rec.value,
                                bank_programmed=bank_programmed_rec.value,
                                reminder_enabled=reminder_enabled_rec.value,
                                reminder_time=reminder_time_rec.value or "09:00",
                            )
                            generate_due_recurrences(
                                user_id,
                                force_planned=bool(row),
                            )
                        except Exception as error:
                            ui.notify(str(error), type="warning")
                            return
                        dialog.close()
                        ui.notify("Récurrence enregistrée.", type="positive")
                        refresh_all()

                    with ui.row().classes("w-full justify-end gap-2"):
                        ui.button(
                            "Annuler", on_click=dialog.close
                        ).props("flat")
                        ui.button(
                            "Enregistrer", icon="save", on_click=save_rec
                        ).props("color=primary")
            dialog.open()

        @ui.refreshable
        def render_recurrences():
            recurrence_box.clear()
            rows = list_recurrences(user_id)
            with recurrence_box:
                with ui.row().classes(
                    "w-full items-center justify-between"
                ):
                    ui.label("Transactions récurrentes").classes(
                        "text-xl font-bold"
                    )
                    ui.button(
                        "Ajouter",
                        icon="add",
                        on_click=lambda: recurrence_dialog(),
                    ).props("color=primary dense")
                if not rows:
                    ui.label("Aucune récurrence.").classes(
                        "text-sm jf-muted"
                    )
                for row in rows:
                    with ui.element("div").classes("jf-finance-card"):
                        with ui.row().classes(
                            "w-full items-center justify-between gap-2"
                        ):
                            with ui.column().classes("gap-0 min-w-0"):
                                ui.label(row["description"]).classes(
                                    "text-sm font-bold"
                                )
                                ui.label(
                                    f"{_signed(row['amount'], row['transaction_type'])} "
                                    f"— tous les {row['frequency_interval']} "
                                    f"{FREQUENCY_UNITS[row['frequency_unit']].lower()}(s)"
                                ).classes("text-xs jf-muted")
                                details = [
                                    (
                                        "Prochaine : "
                                        f"{row['next_date'].strftime('%d/%m/%Y')}"
                                    ),
                                    CONFIRMATION_MODES[
                                        row[
                                            "confirmation_mode"
                                        ]
                                    ],
                                ]
                                if row.get(
                                    "payment_method_name"
                                ):
                                    details.append(
                                        row[
                                            "payment_method_name"
                                        ]
                                    )
                                if row.get("budget_excluded"):
                                    details.append("Hors budget")
                                if row.get("bank_programmed"):
                                    details.append("Programmée à la banque")
                                if row.get("reminder_enabled"):
                                    details.append("Rappel " + str(row.get("reminder_time") or "09:00")[:5])
                                ui.label(
                                    " — ".join(
                                        details
                                    )
                                ).classes(
                                    "text-xs jf-muted"
                                )
                            with ui.row().classes("gap-1 shrink-0"):
                                ui.switch(
                                    value=row["is_active"],
                                    on_change=(
                                        lambda event,
                                        selected=row["id"]:
                                        change_recurrence_state(
                                            selected, event.value
                                        )
                                    ),
                                ).props("dense")
                                ui.button(
                                    icon="edit",
                                    on_click=(
                                        lambda _event=None,
                                        selected=row:
                                        recurrence_dialog(selected)
                                    ),
                                ).props(
                                    "flat dense round size=sm color=primary"
                                )
                                ui.button(
                                    icon="delete",
                                    on_click=(
                                        lambda _event=None,
                                        selected=row:
                                        delete_recurrence_dialog(selected)
                                    ),
                                ).props(
                                    "flat dense round size=sm color=negative"
                                ).tooltip("Supprimer")

        def change_recurrence_state(recurrence_id, value):
            toggle_recurrence(user_id, recurrence_id, value)
            render_recurrences.refresh()

        render_recurrences()

    return RecurrencesPanelHandle(
        on_refresh=lambda: render_recurrences.refresh(),
        on_open_dialog=lambda *args, **kwargs: recurrence_dialog(*args, **kwargs),
    )
