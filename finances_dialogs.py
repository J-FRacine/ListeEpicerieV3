"""Dialogues partagés de transaction et paiement de carte, avec services injectés."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_CEILING
from typing import Callable


@dataclass
class FinanceDialogsHandle:
    on_transaction: Callable[..., None]
    on_card_payment: Callable[..., None]

    def transaction(self, user_id, on_saved, transaction=None, default_payment_method_id=None):
        return self.on_transaction(user_id, on_saved, transaction, default_payment_method_id)

    def card_payment(self, user_id, on_saved, transfer=None, prefill=None):
        return self.on_card_payment(user_id, on_saved, transfer, prefill)


def build_finance_dialogs(
    *,
    ui,
    TRANSACTION_TYPES,
    TRANSACTION_STATUSES,
    _category_options,
    _tag_options,
    _payment_options,
    list_payment_methods,
    save_transaction,
    save_card_payment_transfer,
) -> FinanceDialogsHandle:
    def _bank_payment_source_options(user_id, include_inactive=False):
        return {
            int(row["id"]): (
                row["name"] + (" — désactivé" if not row.get("is_active") else "")
            )
            for row in list_payment_methods(
                user_id,
                include_inactive=include_inactive,
            )
            if row.get("method_type") == "bank"
        }


    def _credit_card_options(user_id, include_inactive=False):
        return {
            int(row["id"]): (
                row["name"] + (" — désactivée" if not row.get("is_active") else "")
            )
            for row in list_payment_methods(
                user_id,
                include_inactive=include_inactive,
            )
            if row.get("method_type") == "credit_card"
        }


    def _card_payment_dialog(
        user_id,
        on_saved,
        transfer=None,
        prefill=None,
    ):
        prefill = dict(prefill or {})
        source_options = _bank_payment_source_options(
            user_id,
            include_inactive=bool(transfer),
        )
        card_options = _credit_card_options(
            user_id,
            include_inactive=bool(transfer),
        )
        source_default = (
            int(transfer["source_payment_method_id"])
            if transfer
            else (
                int(prefill["source_payment_method_id"])
                if prefill.get("source_payment_method_id") in source_options
                else (None if prefill else next(iter(source_options), None))
            )
        )
        card_default = (
            int(transfer["destination_payment_method_id"])
            if transfer
            else (
                int(prefill["destination_payment_method_id"])
                if prefill.get("destination_payment_method_id") in card_options
                else next(iter(card_options), None)
            )
        )
        default_date = str(prefill.get("payment_date") or date.today().isoformat())

        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-2xl p-4"):
                ui.label(
                    "Modifier le paiement de carte"
                    if transfer
                    else "Paiement de carte"
                ).classes("text-xl font-bold")
                ui.label(
                    "Un seul paiement est créé, avec deux effets liés : sortie du compte bancaire et crédit appliqué sur la carte. Le mouvement est automatiquement Hors budget."
                ).classes("text-sm jf-muted")

                if not source_options or not card_options:
                    missing = []
                    if not source_options:
                        missing.append("un Compte bancaire")
                    if not card_options:
                        missing.append("une Carte de crédit")
                    ui.label(
                        "Configurez d’abord " + " et ".join(missing)
                        + " dans Organisation > Modes de paiement."
                    ).classes("text-sm text-negative")
                    with ui.row().classes("w-full justify-end"):
                        ui.button("Fermer", on_click=dialog.close).props("flat")
                    dialog.open()
                    return

                with ui.element("div").classes("jf-finance-form-grid"):
                    source_method = ui.select(
                        source_options,
                        value=source_default,
                        label="Compte bancaire de départ",
                    ).props("dense outlined options-dense").classes("jf-finance-field")
                    destination_method = ui.select(
                        card_options,
                        value=card_default,
                        label="Carte de crédit à payer",
                    ).props("dense outlined options-dense").classes("jf-finance-field")
                    amount = ui.number(
                        label="Montant du paiement",
                        value=(
                            transfer.get("amount")
                            if transfer
                            else prefill.get("amount")
                        ),
                        min=.01,
                        step=.01,
                    ).props("dense outlined").classes("jf-finance-field")
                    source_date = ui.input(
                        label="Date du débit bancaire",
                        value=(
                            transfer["source_date"].isoformat()
                            if transfer
                            else default_date
                        ),
                    ).props("type=date dense outlined").classes("jf-finance-field")
                    destination_date = ui.input(
                        label="Date de réception sur la carte",
                        value=(
                            transfer["destination_date"].isoformat()
                            if transfer
                            else default_date
                        ),
                    ).props("type=date dense outlined").classes("jf-finance-field")
                    description = ui.input(
                        label="Description",
                        value=(
                            transfer.get("description")
                            if transfer
                            else prefill.get("description", "Paiement de carte")
                        ),
                    ).props("dense outlined maxlength=160").classes(
                        "jf-finance-field jf-finance-description"
                    )

                status = ui.select(
                    TRANSACTION_STATUSES,
                    value=(
                        transfer.get("status")
                        if transfer
                        else prefill.get("status", "planned")
                    ),
                    label="Statut",
                ).props("dense outlined options-dense").classes("w-full")
                bank_programmed = ui.checkbox(
                    "Déjà programmé auprès de la banque",
                    value=(
                        bool(transfer.get("bank_programmed"))
                        if transfer
                        else bool(prefill.get("bank_programmed", False))
                    ),
                )
                reminder_enabled = ui.checkbox(
                    "Me rappeler ce paiement le jour du débit",
                    value=bool(transfer.get("reminder_enabled")) if transfer else False,
                )
                reminder_time = ui.input(
                    label="Heure du rappel",
                    value=(
                        str(transfer.get("reminder_time") or "09:00")[:5]
                        if transfer
                        else "09:00"
                    ),
                ).props("type=time dense outlined").classes("w-full")
                note = ui.textarea(
                    label="Note facultative",
                    value=(
                        transfer.get("note") or ""
                        if transfer
                        else str(prefill.get("note") or "")
                    ),
                ).props("dense outlined autogrow maxlength=1000").classes("w-full")

                def round_payment_up():
                    if amount.value in (None, ""):
                        ui.notify("Indiquez d’abord un montant.", type="warning")
                        return
                    try:
                        rounded = Decimal(str(amount.value)).quantize(
                            Decimal("1"), rounding=ROUND_CEILING
                        )
                    except Exception:
                        ui.notify("Le montant est invalide.", type="warning")
                        return
                    amount.value = float(rounded)
                    amount.update()

                ui.button(
                    "Arrondir au dollar supérieur",
                    icon="north_east",
                    on_click=round_payment_up,
                ).props("outline dense color=secondary").classes("self-start")

                if prefill and not transfer:
                    ui.label(
                        "Les valeurs proviennent de la conciliation. Vérifiez le compte source, le montant, les dates et le statut avant d’enregistrer."
                    ).classes("text-xs text-primary")

                ui.label(
                    "Quand le paiement est confirmé, son côté carte apparaît dans Conciliation comme un crédit qui réduit le solde dû. Les deux côtés restent liés lors d’une modification ou d’une suppression."
                ).classes("text-xs jf-muted")

                def save():
                    try:
                        save_card_payment_transfer(
                            user_id=user_id,
                            transfer_id=transfer.get("id") if transfer else None,
                            source_payment_method_id=source_method.value,
                            destination_payment_method_id=destination_method.value,
                            amount=amount.value,
                            source_date=source_date.value,
                            destination_date=destination_date.value or source_date.value,
                            description=description.value,
                            note=note.value,
                            status=status.value,
                            bank_programmed=bank_programmed.value,
                            reminder_enabled=reminder_enabled.value,
                            reminder_time=reminder_time.value or "09:00",
                        )
                    except Exception as error:
                        ui.notify(str(error), type="warning")
                        return
                    dialog.close()
                    ui.notify(
                        "Paiement de carte enregistré.",
                        type="positive",
                    )
                    on_saved()

                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button("Annuler", on_click=dialog.close).props("flat dense")
                    ui.button(
                        "Enregistrer le paiement",
                        icon="credit_card",
                        on_click=save,
                    ).props("color=primary")

        dialog.open()


    def _transaction_dialog(
        user_id,
        on_saved,
        transaction=None,
        default_payment_method_id=None,
    ):
        payment_options = _payment_options(
            user_id
        )

        with ui.dialog() as dialog:
            with ui.card().classes(
                "w-full max-w-2xl p-4"
            ):
                ui.label(
                    (
                        "Modifier la transaction"
                        if transaction
                        else "Nouvelle transaction"
                    )
                ).classes(
                    "text-xl font-bold"
                )

                kind = ui.toggle(
                    TRANSACTION_TYPES,
                    value=(
                        transaction[
                            "transaction_type"
                        ]
                        if transaction
                        else "expense"
                    ),
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
                        value=(
                            transaction["amount"]
                            if transaction
                            else None
                        ),
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
                            transaction[
                                "transaction_date"
                            ].isoformat()
                            if transaction
                            else date.today().isoformat()
                        ),
                    ).props(
                        "type=date dense outlined"
                    ).classes(
                        "jf-finance-field"
                    )

                    description = ui.input(
                        label="Description",
                        value=(
                            transaction[
                                "description"
                            ]
                            if transaction
                            else ""
                        ),
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
                        {
                            None: "Aucune",
                            **_category_options(
                                user_id
                            ),
                        },
                        value=(
                            transaction[
                                "category_id"
                            ]
                            if transaction
                            else None
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
                        payment_options,
                        value=(
                            transaction.get(
                                "payment_method_id"
                            )
                            if transaction
                            else default_payment_method_id
                        ),
                        label="Mode de paiement",
                    ).props(
                        "dense outlined clearable "
                        "options-dense"
                    ).classes(
                        "min-w-48 grow"
                    )

                tags = ui.select(
                    _tag_options(
                        user_id
                    ),
                    value=(
                        list(
                            transaction[
                                "tag_ids"
                            ]
                        )
                        if transaction
                        else []
                    ),
                    label="Étiquettes",
                    multiple=True,
                ).props(
                    "dense outlined use-chips "
                    "clearable options-dense"
                ).classes(
                    "w-full"
                )

                with ui.expansion(
                    "Plus d’options",
                    icon="tune",
                ).classes(
                    "w-full"
                ):
                    budget_excluded = ui.checkbox(
                        "Hors budget — transfert, paiement de carte ou déplacement d’épargne",
                        value=bool(transaction.get("budget_excluded")) if transaction else False,
                    )
                    ui.label(
                        "La transaction affecte toujours le solde du compte, mais elle n’est pas comptée dans les dépenses, revenus, KPI ou objectifs du budget. Pour payer une carte depuis un compte bancaire, privilégiez le bouton « Paiement carte » afin de lier les deux côtés."
                    ).classes("text-xs jf-muted")
                    status = ui.select(
                        TRANSACTION_STATUSES,
                        value=(
                            transaction["status"]
                            if transaction
                            else "confirmed"
                        ),
                        label="Statut de transaction",
                    ).props(
                        "dense outlined options-dense"
                    ).classes(
                        "w-full"
                    )

                    bank_programmed = ui.checkbox(
                        "Programmée dans le compte bancaire",
                        value=bool(transaction.get("bank_programmed")) if transaction else False,
                    )
                    ui.label(
                        "Indique qu’une transaction prévue a déjà été programmée auprès de la banque. Elle reste visible comme Prévue jusqu’à sa confirmation dans JF Apps."
                    ).classes("text-xs jf-muted")

                    reminder_enabled = ui.checkbox(
                        "Me rappeler cette transaction le jour prévu",
                        value=bool(transaction.get("reminder_enabled")) if transaction else False,
                    )
                    reminder_time = ui.input(
                        label="Heure du rappel",
                        value=(
                            str(transaction.get("reminder_time") or "09:00")[:5]
                            if transaction
                            else "09:00"
                        ),
                    ).props("type=time dense outlined").classes("w-full")
                    ui.label(
                        "Le rappel Web Push est envoyé le jour de la transaction si elle est encore Prévue. Active les notifications sur l’appareil dans l’onglet Compte."
                    ).classes("text-xs jf-muted")

                    reconciled = ui.checkbox(
                        "Transaction conciliée",
                        value=(
                            (
                                transaction.get(
                                    "reconciliation_status"
                                )
                                == "reconciled"
                            )
                            if transaction
                            else False
                        ),
                    )

                    reconciliation_date = ui.input(
                        label=(
                            "Date de conciliation "
                            "(facultative)"
                        ),
                        value=(
                            transaction[
                                "reconciliation_date"
                            ].isoformat()
                            if (
                                transaction
                                and transaction.get(
                                    "reconciliation_date"
                                )
                            )
                            else ""
                        ),
                    ).props(
                        "type=date dense outlined"
                    ).classes(
                        "w-full"
                    )

                    note = ui.textarea(
                        label="Note facultative",
                        value=(
                            transaction["note"]
                            if transaction
                            else ""
                        ),
                    ).props(
                        "dense outlined autogrow "
                        "maxlength=1000"
                    ).classes(
                        "w-full"
                    )

                def save():
                    try:
                        save_transaction(
                            user_id=user_id,
                            transaction_id=(
                                transaction["id"]
                                if transaction
                                else None
                            ),
                            transaction_date=when.value,
                            transaction_type=kind.value,
                            amount=amount.value,
                            description=description.value,
                            category_id=category.value,
                            tag_ids=tags.value or [],
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
                            budget_excluded=budget_excluded.value,
                            bank_programmed=bank_programmed.value,
                            reminder_enabled=reminder_enabled.value,
                            reminder_time=reminder_time.value or "09:00",
                        )
                    except Exception as error:
                        ui.notify(
                            str(error),
                            type="warning",
                        )
                        return

                    dialog.close()
                    ui.notify(
                        "Transaction enregistrée.",
                        type="positive",
                    )
                    on_saved()

                with ui.row().classes(
                    "w-full justify-end gap-2"
                ):
                    ui.button(
                        "Annuler",
                        on_click=dialog.close,
                    ).props(
                        "flat dense"
                    )
                    ui.button(
                        "Enregistrer",
                        icon="save",
                        on_click=save,
                    ).props(
                        "color=primary"
                    )

        dialog.open()


    return FinanceDialogsHandle(
        on_transaction=_transaction_dialog,
        on_card_payment=_card_payment_dialog,
    )
