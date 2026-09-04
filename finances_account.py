"""Panneau Compte : interface et contrat, avec dépendances injectées."""
import json
from datetime import date
from decimal import Decimal
from dataclasses import dataclass
from typing import Callable


@dataclass
class AccountPanelHandle:
    """Liaison minimale entre Finances et le panneau Compte.

    Le panneau fournit des callbacks sans argument, idéalement des lambdas
    résolvant leurs fonctions cibles à l'appel. Ils ne sont pas exécutés à la
    construction et peuvent être remplacés ensuite.

    Le parent appelle reload_options() puis refresh() lors d'une actualisation
    globale. La sélection et les widgets restent sous la responsabilité du
    panneau. reload_options() ne déclenche pas explicitement le rendu.
    """

    on_refresh: Callable[[], None]
    on_reload_options: Callable[[], None]

    def refresh(self) -> None:
        self.on_refresh()

    def reload_options(self) -> None:
        self.on_reload_options()


def build_account_panel(
    *,
    ui,
    user_id,
    account_tab,
    tabs,
    organization_tab,
    MonthCursor,
    list_bank_accounts,
    bank_cashflow_month,
    bank_cashflow_year_summary,
    list_recurrences,
    get_transaction,
    get_card_payment_transfer,
    set_bank_transaction_seen,
    count_active_push_subscriptions,
    get_vapid_public_key,
    save_push_subscription,
    set_push_channel_enabled,
    _bank_account_options,
    _money,
    _balance_money,
    _month_label,
    refresh_all,
    recurrence_dialog,
    _transaction_dialog,
    _card_payment_dialog,
) -> AccountPanelHandle:
    """Construit Compte et retourne uniquement son handle de rafraîchissement.

    ui, la navigation, l'état mensuel et les services sont fournis par le parent.
    Les callbacks partagés doivent être des relais différés : leurs fonctions
    cibles peuvent n'être définies qu'après la construction du panneau.
    Aucun accès direct aux modules historiques ou à PostgreSQL.
    """
    with ui.tab_panel(account_tab).classes("px-0"):
        account_month_state = MonthCursor()
        bank_rows = list_bank_accounts(user_id)
        bank_options = {int(row["id"]): row["name"] for row in bank_rows}
        selected_bank = next(
            (int(row["id"]) for row in bank_rows if row.get("method_type") == "bank"),
            next(iter(bank_options), None),
        )
        with ui.card().classes("w-full p-4"):
            with ui.row().classes("w-full items-end gap-2 flex-wrap"):
                account_selector = ui.select(bank_options, value=selected_bank, label="Compte bancaire / marge de crédit").props("dense outlined options-dense").classes("min-w-56 grow")
                ui.button("Configurer les comptes", icon="settings", on_click=lambda: tabs.set_value(organization_tab)).props("flat dense color=primary")
            ui.label("La vue Compte suit les comptes bancaires et les marges de crédit. Pour une marge, une dépense augmente la dette et un remboursement la réduit. Les mouvements Hors budget continuent d’affecter le solde ou la dette.").classes("text-xs jf-muted")
        with ui.card().classes("w-full p-4"):
            with ui.row().classes("w-full items-start justify-between gap-2 flex-wrap"):
                with ui.column().classes("gap-0 min-w-0"):
                    ui.label("Notifications de transactions").classes("font-bold")
                    ui.label(
                        "Les rappels sont envoyés sur les appareils autorisés pour une transaction ou une récurrence encore prévue."
                    ).classes("text-sm jf-muted")
                finance_push_count = ui.label(
                    f"{count_active_push_subscriptions(user_id, 'finance')} appareil(s) actif(s)"
                ).classes("text-primary")
            ui.label(
                "La notification reste discrète : « Finances — Une transaction prévue nécessite votre attention. »"
            ).classes("text-xs jf-muted")

            async def activate_finance_notifications():
                try:
                    public_key = get_vapid_public_key()
                    result = await ui.run_javascript(
                        f"""
                            const publicKey = {json.dumps(public_key)};
                            function jfUrlBase64ToUint8Array(base64String) {{
                                const padding = '='.repeat((4 - base64String.length % 4) % 4);
                                const base64 = base64String.replace(/-/g, '+').replace(/_/g, '/') + padding;
                                const rawData = window.atob(base64);
                                return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
                            }}
                            if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {{
                                return {{status: 'unsupported'}};
                            }}
                            const permission = await Notification.requestPermission();
                            if (permission !== 'granted') {{
                                return {{status: permission || 'denied'}};
                            }}
                            const registration = await navigator.serviceWorker.ready;
                            let subscription = await registration.pushManager.getSubscription();
                            if (!subscription) {{
                                subscription = await registration.pushManager.subscribe({{
                                    userVisibleOnly: true,
                                    applicationServerKey: jfUrlBase64ToUint8Array(publicKey),
                                }});
                            }}
                            return {{
                                status: 'subscribed',
                                subscription: subscription.toJSON(),
                                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
                                userAgent: navigator.userAgent || '',
                            }};
                            """,
                        timeout=45.0,
                    )
                except Exception as error:
                    ui.notify(f"L’activation des notifications a échoué : {error}", type="negative", timeout=10000)
                    return
                status_value = result.get("status") if isinstance(result, dict) else None
                if status_value == "subscribed":
                    try:
                        save_push_subscription(
                            user_id,
                            result.get("subscription") or {},
                            timezone_name=result.get("timezone") or "UTC",
                            user_agent=result.get("userAgent"),
                            channel="finance",
                        )
                    except Exception as error:
                        ui.notify(str(error), type="negative", timeout=10000)
                        return
                    finance_push_count.set_text(
                        f"{count_active_push_subscriptions(user_id, 'finance')} appareil(s) actif(s)"
                    )
                    ui.notify("Notifications activées sur cet appareil.", type="positive")
                    return
                messages = {
                    "denied": "Le navigateur a refusé l’autorisation de notification.",
                    "default": "L’autorisation de notification n’a pas été accordée.",
                    "unsupported": "Les notifications Web Push ne sont pas disponibles dans ce navigateur ou dans ce mode d’utilisation.",
                }
                ui.notify(messages.get(status_value, "Les notifications n’ont pas pu être activées."), type="warning", timeout=10000)

            async def deactivate_finance_notifications():
                try:
                    result = await ui.run_javascript(
                        """
                            if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
                                return {status: 'unsupported'};
                            }
                            const registration = await navigator.serviceWorker.ready;
                            const subscription = await registration.pushManager.getSubscription();
                            if (!subscription) { return {status: 'none'}; }
                            return {status: 'found', endpoint: subscription.endpoint};
                            """,
                        timeout=30.0,
                    )
                except Exception as error:
                    ui.notify(f"La désactivation des notifications a échoué : {error}", type="negative")
                    return
                status_value = result.get("status") if isinstance(result, dict) else None
                if status_value == "found" and result.get("endpoint"):
                    set_push_channel_enabled(
                        user_id, result["endpoint"], "finance", False
                    )
                    finance_push_count.set_text(
                        f"{count_active_push_subscriptions(user_id, 'finance')} appareil(s) actif(s)"
                    )
                    ui.notify(
                        "Rappels Finances désactivés sur cet appareil. Les autres notifications JF Apps restent inchangées.",
                        type="info",
                    )
                elif status_value == "none":
                    ui.notify("Aucun abonnement de notification n’était actif sur cet appareil.", type="info")
                else:
                    ui.notify("La désactivation n’a pas été confirmée.", type="warning")

            with ui.row().classes("gap-2 flex-wrap mt-2"):
                ui.button("Activer sur cet appareil", icon="notifications_active", on_click=activate_finance_notifications).props("color=primary dense")
                ui.button("Désactiver sur cet appareil", icon="notifications_off", on_click=deactivate_finance_notifications).props("flat dense")

        account_box = ui.column().classes("w-full gap-2")

        def change_account_month(offset):
            account_month_state.shift(offset)
            render_account.refresh()

        def open_account_row_editor(selected_row):
            row = dict(selected_row or {})

            if row.get("projected"):
                recurrence_id = row.get("recurrence_id")
                if not recurrence_id:
                    ui.notify(
                        "Cette ligne est une projection et ne peut pas être modifiée comme transaction.",
                        type="info",
                    )
                    return
                recurrence = next(
                    (
                        item
                        for item in list_recurrences(user_id)
                        if int(item["id"]) == int(recurrence_id)
                    ),
                    None,
                )
                if not recurrence:
                    ui.notify("Récurrence introuvable.", type="warning")
                    return
                recurrence_dialog(recurrence)
                return

            transaction_id = row.get("id")
            if not transaction_id:
                ui.notify("Transaction introuvable.", type="warning")
                return

            linked_transfer_id = row.get("linked_transfer_id")

            def open_real_editor():
                try:
                    if linked_transfer_id:
                        transfer = get_card_payment_transfer(
                            user_id, linked_transfer_id
                        )
                        if not transfer:
                            raise ValueError("Paiement de carte introuvable.")
                        if (
                            transfer.get("destination_reconciliation_status")
                            == "reconciled"
                        ):
                            ui.notify(
                                "Ce paiement est déjà concilié sur la carte de crédit. "
                                    "Retirez d’abord cette conciliation dans l’onglet Conciliation.",
                                type="warning",
                            )
                            return
                        _card_payment_dialog(
                            user_id, refresh_all, transfer=transfer
                        )
                    else:
                        transaction = get_transaction(
                            user_id, transaction_id
                        )
                        _transaction_dialog(
                            user_id, refresh_all, transaction=transaction
                        )
                except Exception as error:
                    ui.notify(str(error), type="warning")

            if row.get("reconciliation_status") != "reconciled":
                open_real_editor()
                return

            if linked_transfer_id:
                try:
                    transfer = get_card_payment_transfer(
                        user_id, linked_transfer_id
                    )
                except Exception as error:
                    ui.notify(str(error), type="warning")
                    return
                if (
                    transfer
                    and transfer.get("destination_reconciliation_status")
                    == "reconciled"
                ):
                    ui.notify(
                        "Ce paiement est aussi concilié sur la carte de crédit. "
                            "Retirez d’abord cette conciliation dans l’onglet Conciliation.",
                        type="warning",
                    )
                    return

            with ui.dialog() as confirm_dialog:
                with ui.card().classes("w-full max-w-lg p-4"):
                    ui.label("Transaction déjà conciliée").classes(
                        "text-lg font-bold"
                    )
                    ui.label(
                        "Pour la modifier, Finances doit d’abord retirer la conciliation "
                            "« Vu ». La transaction restera enregistrée et pourra être "
                            "conciliée de nouveau après la modification."
                    ).classes("text-sm jf-muted")

                    def remove_reconciliation_and_edit():
                        try:
                            set_bank_transaction_seen(
                                user_id,
                                transaction_id,
                                False,
                                date.today(),
                            )
                        except Exception as error:
                            ui.notify(str(error), type="warning")
                            return
                        confirm_dialog.close()
                        render_account.refresh()
                        open_real_editor()

                    with ui.row().classes("w-full justify-end gap-2"):
                        ui.button(
                            "Annuler", on_click=confirm_dialog.close
                        ).props("flat dense")
                        ui.button(
                            "Retirer la conciliation et modifier",
                            icon="edit",
                            on_click=remove_reconciliation_and_edit,
                        ).props("color=primary")
            confirm_dialog.open()

        @ui.refreshable
        def render_account():
            account_box.clear()
            with account_box:
                if not account_selector.value:
                    with ui.element("div").classes("jf-finance-report-note"):
                        ui.label("Aucun Compte bancaire ni aucune Marge de crédit n’est configuré. Crée-en un dans Organisation > Modes de paiement.").classes("text-sm")
                    return
                try:
                    month_data = bank_cashflow_month(user_id, account_selector.value, account_month_state.value)
                    year_data = bank_cashflow_year_summary(user_id, account_selector.value, account_month_state.value.year)
                except Exception as error:
                    ui.label(str(error)).classes("text-sm jf-finance-expense")
                    return
                with ui.row().classes("w-full items-center justify-center gap-1"):
                    ui.button(icon="chevron_left", on_click=lambda: change_account_month(-1)).props("flat dense round")
                    ui.label(_month_label(account_month_state.value)).classes("font-bold min-w-40 text-center")
                    ui.button(icon="chevron_right", on_click=lambda: change_account_month(1)).props("flat dense round")
                if not month_data.get("available"):
                    with ui.element("div").classes("jf-finance-report-note"):
                        ui.label("Pour calculer le suivi, indique un solde de référence et sa date dans Organisation > Modes de paiement.").classes("text-sm")
                    return
                is_credit_line = bool(month_data.get("is_credit_line"))
                with ui.element("div").classes("jf-finance-summary-grid"):
                    if is_credit_line:
                        current_debt = (
                            month_data.get("current_balance")
                            if month_data.get("current_balance") is not None
                            else month_data["start_balance"]
                        )
                        summary_values = [
                            ("Dette de départ", month_data["start_balance"]),
                            ("Dette actuelle", current_debt),
                            ("Plus haut prévu", month_data["maximum_balance"]),
                            ("Dette fin de mois", month_data["end_balance"]),
                        ]
                        if month_data.get("credit_limit") is not None:
                            summary_values.extend([
                                ("Limite de crédit", month_data["credit_limit"]),
                                ("Crédit disponible fin", month_data["end_available_credit"]),
                            ])
                    else:
                        summary_values = [
                            ("Solde actuel", month_data.get("current_balance") if month_data.get("current_balance") is not None else month_data["start_balance"]),
                            ("Plus bas prévu", month_data["minimum_balance"]),
                            ("Solde fin de mois", month_data["end_balance"]),
                        ]
                    for label, value in summary_values:
                        with ui.element("div").classes("jf-finance-summary"):
                            ui.label(label).classes("jf-finance-summary-label")
                            if is_credit_line and "Dette" in label:
                                css = "jf-finance-expense" if Decimal(value) > 0 else "jf-finance-income"
                            else:
                                css = "jf-finance-expense" if Decimal(value) < 0 else "jf-finance-income"
                            ui.label(_balance_money(value)).classes("jf-finance-summary-value " + css)
                with ui.card().classes("w-full p-0 overflow-hidden"):
                    bank_reconcile = not is_credit_line
                    head_classes = "jf-finance-cashflow-head" + (
                        " jf-finance-bank-reconcile" if bank_reconcile else ""
                    )
                    with ui.element("div").classes(head_classes):
                        headers = (
                            ("Date","Description","Utilisation","Remboursement","Dette")
                            if is_credit_line
                            else ("Vu","Date","Description","Sortie","Entrée","Solde")
                        )
                        for text in headers:
                            ui.label(text).classes(
                                "text-right"
                                if text not in {"Vu", "Date", "Description"}
                                else ""
                            )
                    if bank_reconcile:
                        start_value = Decimal(month_data["start_balance"])
                        start_css = (
                            "jf-finance-expense"
                            if start_value < 0
                            else "jf-finance-income"
                        )
                        with ui.element("div").classes(
                            "jf-finance-cashflow-row "
                                "jf-finance-bank-reconcile "
                                "jf-finance-cashflow-start"
                        ):
                            ui.label("")
                            ui.label(account_month_state.value.strftime("%d/%m"))
                            ui.label("Solde de départ").classes("font-bold")
                            ui.label("")
                            ui.label("")
                            ui.label(_balance_money(start_value)).classes(
                                "jf-finance-cashflow-money font-bold " + start_css
                            )
                    if month_data["rows"]:
                        for row in month_data["rows"]:
                            row_classes = "jf-finance-cashflow-row" + (
                                " jf-finance-bank-reconcile" if bank_reconcile else ""
                            )
                            with ui.element("div").classes(row_classes):
                                if bank_reconcile:
                                    transaction_id = row.get("id")
                                    projected = bool(row.get("projected"))
                                    reconciled_now = (
                                        row.get("reconciliation_status") == "reconciled"
                                    )

                                    def change_bank_seen(
                                        event,
                                        selected_id=transaction_id,
                                        selected_projected=projected,
                                    ):
                                        if selected_projected or not selected_id:
                                            ui.notify(
                                                "Cette ligne est encore une projection. Attendez qu’elle devienne une transaction prévue avant de la concilier.",
                                                type="info",
                                            )
                                            render_account.refresh()
                                            return
                                        try:
                                            set_bank_transaction_seen(
                                                user_id,
                                                selected_id,
                                                bool(event.value),
                                                date.today(),
                                            )
                                        except Exception as error:
                                            ui.notify(str(error), type="warning")
                                            render_account.refresh()
                                            return
                                        ui.notify(
                                            "Transaction conciliée."
                                            if event.value
                                            else "Conciliation retirée.",
                                            type="positive",
                                        )
                                        refresh_all()

                                    checkbox = ui.checkbox(
                                        value=reconciled_now,
                                        on_change=change_bank_seen,
                                    ).props("dense")
                                    if projected:
                                        checkbox.disable()
                                        checkbox.tooltip(
                                            "Projection seulement — elle n’est pas encore une transaction réelle."
                                        )
                                ui.label(row["transaction_date"].strftime("%d/%m"))
                                with ui.column().classes("gap-0 min-w-0"):
                                    with ui.row().classes(
                                        "w-full items-center gap-1 flex-nowrap min-w-0"
                                    ):
                                        ui.label(row["description"]).classes(
                                            "font-semibold truncate grow"
                                        ).tooltip(row["description"])
                                        edit_icon = (
                                            "event_repeat"
                                            if row.get("projected")
                                            else "edit"
                                        )
                                        edit_tip = (
                                            "Modifier la récurrence à l’origine de cette projection"
                                            if row.get("projected")
                                            else "Modifier cette transaction"
                                        )
                                        ui.button(
                                            icon=edit_icon,
                                            on_click=lambda _event=None, selected=dict(row): open_account_row_editor(selected),
                                        ).props(
                                            "flat dense round size=sm color=primary"
                                        ).tooltip(edit_tip)
                                    meta=[]
                                    if row.get("linked_transfer_id") and row.get("linked_transfer_destination_name"):
                                        meta.append("Vers " + str(row.get("linked_transfer_destination_name")))
                                    if row.get("projected"): meta.append("Récurrence projetée")
                                    elif row.get("status") == "planned": meta.append("Prévue")
                                    if row.get("reconciliation_status") == "reconciled" and bank_reconcile:
                                        meta.append("Conciliée")
                                    if row.get("budget_excluded"): meta.append("Hors budget")
                                    if row.get("bank_programmed"): meta.append("Programmé")
                                    if row.get("reminder_enabled"): meta.append("Rappel " + str(row.get("reminder_time") or "09:00")[:5])
                                    if meta: ui.label(" • ".join(meta)).classes("text-xs jf-muted")
                                ui.label(_money(row["amount"]) if row["transaction_type"] == "expense" else "").classes("jf-finance-cashflow-money jf-finance-expense")
                                ui.label(_money(row["amount"]) if row["transaction_type"] == "income" else "").classes("jf-finance-cashflow-money jf-finance-income")
                                running_value = Decimal(row["running_balance"])
                                running_css = (
                                    "jf-finance-expense"
                                    if (is_credit_line and running_value > 0)
                                    or (not is_credit_line and running_value < 0)
                                    else ""
                                )
                                ui.label(_balance_money(running_value)).classes("jf-finance-cashflow-money font-bold " + running_css)
                    else:
                        ui.label("Aucun mouvement pour ce mois.").classes("p-4 text-sm jf-muted")
                if not is_credit_line:
                    ui.label(
                        "Compte bancaire : cochez Vu lorsque le mouvement apparaît réellement à la banque. Une transaction Prévue est confirmée et conciliée en une seule opération; une projection pure reste non cochable."
                    ).classes("text-xs jf-muted px-1")
                if year_data.get("available"):
                    with ui.row().classes("w-full items-center justify-between mt-2"):
                        ui.label(f"Vue annuelle {account_month_state.value.year}").classes("text-lg font-bold")
                        ui.label(
                            "Dette utilisée prévue à la fin de chaque mois"
                            if is_credit_line
                            else "Solde prévu à la fin de chaque mois"
                        ).classes("text-xs jf-muted")
                    with ui.element("div").classes("jf-finance-year-grid"):
                        for month_row in year_data["months"]:
                            month_value = month_row["month"]
                            with ui.element("div").classes("jf-finance-year-card").on("click", lambda _event=None, selected=month_value: (account_month_state.set(selected), render_account.refresh())):
                                ui.label(_month_label(month_value).split()[0]).classes("text-xs jf-muted")
                                if not month_row.get("available", True):
                                    ui.label("—").classes("font-bold jf-muted")
                                    ui.label("avant le solde de référence").classes("text-xs jf-muted")
                                else:
                                    end_value = Decimal(month_row["end_balance"])
                                    if is_credit_line:
                                        ui.label(_balance_money(end_value)).classes(
                                            "font-bold " + ("jf-finance-expense" if end_value > 0 else "jf-finance-income")
                                        )
                                        ui.label(
                                            "max. " + _balance_money(month_row["maximum_balance"])
                                        ).classes("text-xs jf-muted")
                                        if month_row.get("end_available_credit") is not None:
                                            ui.label(
                                                "disp. " + _balance_money(month_row["end_available_credit"])
                                            ).classes("text-xs jf-muted")
                                    else:
                                        ui.label(_balance_money(end_value)).classes("font-bold " + ("jf-finance-expense" if end_value < 0 else "jf-finance-income"))
                                        ui.label("min. " + _balance_money(month_row["minimum_balance"])).classes("text-xs jf-muted")
        def reload_account_options():
            account_selector.options = _bank_account_options(user_id)
            if account_selector.value not in account_selector.options:
                account_selector.value = next(iter(account_selector.options), None)
            account_selector.update()

        account_panel = AccountPanelHandle(
            on_refresh=lambda: render_account.refresh(),
            on_reload_options=lambda: reload_account_options(),
        )
        account_selector.on_value_change(lambda _event: render_account.refresh())
        render_account()
    return account_panel
