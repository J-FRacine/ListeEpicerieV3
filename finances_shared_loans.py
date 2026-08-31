from __future__ import annotations

from datetime import date
from decimal import Decimal

from nicegui import ui

from finances_data import (
    FREQUENCY_UNITS,
    SHARED_LOAN_PERMISSIONS,
    SHARED_LOAN_ROLES,
    add_shared_loan_event,
    get_shared_loan,
    list_available_loan_participants,
    list_shared_loans,
    save_shared_loan,
    shared_loan_amortization_preview,
)


def _money(value):
    amount = Decimal(value or 0)
    sign = "-" if amount < 0 else ""
    return sign + f"{abs(amount):,.2f}".replace(",", " ").replace(".", ",") + " $"


def shared_loans_panel(user, refresh_parent=None):
    """Module isolé : seul le prêt explicitement partagé devient visible."""

    user_id = int(user["id"])
    box = ui.column().classes("w-full gap-2")

    def refresh_all():
        render_loans.refresh()
        if refresh_parent:
            try:
                refresh_parent()
            except Exception:
                pass

    def loan_dialog(loan=None):
        current = dict(loan or {})
        full = get_shared_loan(user_id, current["id"]) if current.get("id") else current
        if current.get("id") and not full.get("is_owner"):
            ui.notify("Seul le propriétaire peut modifier la fiche du prêt.", type="warning")
            return

        candidates = list_available_loan_participants(user_id)
        candidate_options = {
            int(row["id"]): f"{row['display_name']} — {row['email']}"
            for row in candidates
        }
        existing_members = {int(row["user_id"]): dict(row) for row in full.get("members", [])}

        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-4xl p-4"):
                ui.label("Modifier le prêt partagé" if current else "Nouveau prêt partagé").classes("text-xl font-bold")
                ui.label(
                    "Le partage porte uniquement sur ce prêt. Les participants n’obtiennent aucun accès "
                    "à vos comptes, cartes, budgets, transactions ou autres prêts."
                ).classes("text-xs text-gray-500")
                with ui.element("div").classes("jf-finance-form-grid"):
                    title = ui.input("Nom du prêt", value=full.get("title", "")).props("dense outlined maxlength=160").classes("jf-finance-field jf-finance-description")
                    lender = ui.input("Prêteur", value=full.get("lender_name", "")).props("dense outlined maxlength=160").classes("jf-finance-field")
                    borrower = ui.input("Emprunteur", value=full.get("borrower_name", "")).props("dense outlined maxlength=160").classes("jf-finance-field")
                    original = ui.number("Montant initial", value=full.get("original_balance"), min=0, step=.01).props("dense outlined").classes("jf-finance-field")
                    balance = ui.number("Solde actuel", value=full.get("current_balance"), min=0, step=.01).props("dense outlined").classes("jf-finance-field")
                    rate = ui.number("Taux annuel %", value=full.get("annual_interest_rate", 0), min=0, step=.01).props("dense outlined").classes("jf-finance-field")
                    payment = ui.number("Versement prévu", value=full.get("payment_amount"), min=.01, step=.01).props("dense outlined clearable").classes("jf-finance-field")
                    frequency = ui.select(FREQUENCY_UNITS, value=full.get("frequency_unit", "month"), label="Fréquence").props("dense outlined options-dense").classes("jf-finance-field")
                    interval = ui.number("Tous les…", value=full.get("frequency_interval", 1), min=1, step=1).props("dense outlined").classes("jf-finance-field")
                    start = ui.input("Date de début", value=full.get("start_date").isoformat() if full.get("start_date") else "").props("type=date dense outlined clearable").classes("jf-finance-field")
                    next_due = ui.input("Prochaine échéance", value=full.get("next_due_date").isoformat() if full.get("next_due_date") else "").props("type=date dense outlined clearable").classes("jf-finance-field")
                    end = ui.input("Fin prévue — facultative", value=full.get("end_date").isoformat() if full.get("end_date") else "").props("type=date dense outlined clearable").classes("jf-finance-field")
                    status = ui.select(
                        {"active": "Actif", "paused": "En pause", "completed": "Terminé"},
                        value=full.get("status", "active"),
                        label="Statut",
                    ).props("dense outlined options-dense").classes("jf-finance-field")
                note = ui.textarea("Note", value=full.get("note") or "").props("dense outlined autogrow maxlength=2000").classes("w-full")

                ui.separator()
                ui.label("Partager ce prêt").classes("font-bold")
                selected_users = ui.select(
                    candidate_options,
                    value=list(existing_members),
                    label="Utilisateurs autorisés",
                    multiple=True,
                ).props("dense outlined use-chips clearable options-dense").classes("w-full")
                ui.label(
                    "Les personnes choisies voient uniquement la fiche, le solde et l’historique de ce prêt. "
                    "Le rôle et la permission sont propres à ce prêt."
                ).classes("text-xs text-gray-500")

                member_state = {
                    int(member_id): {
                        "role": row.get("role", "observer"),
                        "permission": row.get("permission", "view"),
                    }
                    for member_id, row in existing_members.items()
                }
                member_controls = {}

                @ui.refreshable
                def render_member_permissions():
                    member_controls.clear()
                    selected = [int(value) for value in (selected_users.value or [])]
                    if not selected:
                        ui.label("Aucun autre utilisateur n’a accès à ce prêt.").classes(
                            "text-xs text-gray-500"
                        )
                        return
                    with ui.column().classes("w-full gap-1 mt-1"):
                        for member_id in selected:
                            state = member_state.setdefault(
                                member_id,
                                {"role": "observer", "permission": "view"},
                            )
                            with ui.card().classes("w-full p-2"):
                                ui.label(candidate_options.get(member_id, str(member_id))).classes(
                                    "text-sm font-semibold"
                                )
                                with ui.row().classes("w-full gap-2 items-end flex-wrap"):
                                    role_control = ui.select(
                                        SHARED_LOAN_ROLES,
                                        value=state["role"],
                                        label="Rôle dans ce prêt",
                                    ).props("dense outlined options-dense").classes("min-w-44 grow")
                                    permission_control = ui.select(
                                        SHARED_LOAN_PERMISSIONS,
                                        value=state["permission"],
                                        label="Permission",
                                    ).props("dense outlined options-dense").classes("min-w-52 grow")

                                    def remember_role(event, selected_id=member_id):
                                        member_state[selected_id]["role"] = event.value or "observer"

                                    def remember_permission(event, selected_id=member_id):
                                        member_state[selected_id]["permission"] = event.value or "view"

                                    role_control.on_value_change(remember_role)
                                    permission_control.on_value_change(remember_permission)
                                    member_controls[member_id] = (
                                        role_control,
                                        permission_control,
                                    )

                def selected_users_changed(_event=None):
                    selected = {int(value) for value in (selected_users.value or [])}
                    for member_id in selected:
                        member_state.setdefault(
                            member_id,
                            {"role": "observer", "permission": "view"},
                        )
                    render_member_permissions.refresh()

                selected_users.on_value_change(selected_users_changed)
                render_member_permissions()

                def save_now():
                    members = []
                    for member_id in selected_users.value or []:
                        member_id = int(member_id)
                        controls = member_controls.get(member_id)
                        if controls:
                            role_value = controls[0].value or "observer"
                            permission_value = controls[1].value or "view"
                        else:
                            state = member_state.get(member_id, {})
                            role_value = state.get("role", "observer")
                            permission_value = state.get("permission", "view")
                        members.append(
                            {
                                "user_id": member_id,
                                "role": role_value,
                                "permission": permission_value,
                            }
                        )
                    try:
                        save_shared_loan(
                            user_id,
                            loan_id=full.get("id"),
                            title=title.value,
                            lender_name=lender.value,
                            borrower_name=borrower.value,
                            original_balance=original.value or 0,
                            current_balance=balance.value,
                            annual_interest_rate=rate.value or 0,
                            payment_amount=payment.value,
                            frequency_unit=frequency.value,
                            frequency_interval=int(interval.value or 1),
                            start_date=start.value or None,
                            next_due_date=next_due.value or None,
                            end_date=end.value or None,
                            note=note.value,
                            status=status.value,
                            members=members,
                        )
                    except Exception as error:
                        ui.notify(str(error), type="warning")
                        return
                    dialog.close()
                    ui.notify("Prêt partagé enregistré.", type="positive")
                    refresh_all()

                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button("Enregistrer", icon="save", on_click=save_now).props("color=primary")
        dialog.open()

    def event_dialog(loan_id):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-lg p-4"):
                ui.label("Ajouter à l’historique du prêt").classes("text-xl font-bold")
                event_type = ui.select(
                    {
                        "payment": "Versement",
                        "principal_addition": "Ajout au capital",
                        "adjustment": "Ajustement du solde (+ ou -)",
                        "note": "Note seulement",
                    },
                    value="payment",
                    label="Type",
                ).props("dense outlined options-dense").classes("w-full")
                amount = ui.number("Montant", value=None, step=.01).props("dense outlined clearable").classes("w-full")
                event_date = ui.input("Date", value=date.today().isoformat()).props("type=date dense outlined").classes("w-full")
                note = ui.textarea("Note", value="").props("dense outlined autogrow maxlength=1000").classes("w-full")

                def save_event():
                    try:
                        result = add_shared_loan_event(
                            user_id,
                            loan_id,
                            event_type=event_type.value,
                            amount=amount.value or 0,
                            event_date=event_date.value,
                            note=note.value,
                        )
                    except Exception as error:
                        ui.notify(str(error), type="warning")
                        return
                    dialog.close()
                    ui.notify(
                        "Historique mis à jour — nouveau solde : " + _money(result["balance_after"]),
                        type="positive",
                    )
                    refresh_all()

                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button("Enregistrer", icon="save", on_click=save_event).props("color=primary")
        dialog.open()

    def detail_dialog(loan_id):
        loan = get_shared_loan(user_id, loan_id)
        schedule = shared_loan_amortization_preview(user_id, loan_id, max_rows=36)
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-5xl p-4"):
                with ui.row().classes("w-full items-start justify-between gap-2"):
                    with ui.column().classes("gap-0"):
                        ui.label(loan["title"]).classes("text-xl font-bold")
                        ui.label(
                            f"{loan.get('lender_name') or 'Prêteur non précisé'} → "
                            f"{loan.get('borrower_name') or 'Emprunteur non précisé'}"
                        ).classes("text-sm text-gray-500")
                    ui.button(icon="close", on_click=dialog.close).props("flat round dense")
                with ui.element("div").classes("jf-finance-summary-grid"):
                    for label, value in (
                        ("Montant initial", loan["original_balance"]),
                        ("Solde actuel", loan["current_balance"]),
                        ("Versement", loan.get("payment_amount") or 0),
                    ):
                        with ui.element("div").classes("jf-finance-summary"):
                            ui.label(label).classes("jf-finance-summary-label")
                            ui.label(_money(value)).classes("jf-finance-summary-value")
                if loan.get("members"):
                    ui.label(
                        "Partagé avec : " + ", ".join(row["display_name"] for row in loan["members"])
                    ).classes("text-xs text-primary")

                ui.label("Historique").classes("font-bold mt-2")
                if not loan.get("events"):
                    ui.label("Aucun mouvement enregistré.").classes("text-xs text-gray-500")
                for event in loan.get("events", [])[:30]:
                    with ui.row().classes("w-full items-center gap-2 py-1 border-b"):
                        ui.label(event["event_date"].strftime("%d/%m/%Y")).classes("w-24 text-xs")
                        ui.label(str(event["event_type"]).replace("_", " ")).classes("grow text-xs")
                        ui.label(_money(event["amount"])).classes("text-xs font-bold")
                        ui.label("→ " + _money(event["balance_after"])).classes("text-xs text-gray-500")

                ui.label("Projection d’amortissement").classes("font-bold mt-2")
                if not schedule:
                    ui.label("Indiquez un versement prévu pour obtenir une projection.").classes("text-xs text-gray-500")
                else:
                    with ui.element("div").classes("w-full overflow-x-auto"):
                        with ui.element("div").classes("min-w-[650px]"):
                            with ui.row().classes("w-full font-bold text-xs border-b py-1"):
                                for text, cls in (("#", "w-10"),("Date", "w-24"),("Versement", "w-28 text-right"),("Intérêts", "w-28 text-right"),("Capital", "w-28 text-right"),("Solde", "grow text-right")):
                                    ui.label(text).classes(cls)
                            for row in schedule:
                                with ui.row().classes("w-full text-xs border-b py-1"):
                                    ui.label(str(row["number"])).classes("w-10")
                                    ui.label(row["date"].strftime("%d/%m/%Y")).classes("w-24")
                                    ui.label(_money(row["payment"])).classes("w-28 text-right")
                                    ui.label(_money(row["interest"])).classes("w-28 text-right")
                                    ui.label(_money(row["principal"])).classes("w-28 text-right")
                                    ui.label(_money(row["remaining"])).classes("grow text-right")
        dialog.open()

    @ui.refreshable
    def render_loans():
        box.clear()
        loans = list_shared_loans(user_id)
        with box:
            with ui.row().classes("w-full items-start justify-between gap-2 flex-wrap"):
                with ui.column().classes("gap-0"):
                    ui.label("Prêts partagés").classes("text-xl font-bold")
                    ui.label(
                        "Chaque prêt possède ses propres permissions; aucune autre donnée Finances n’est partagée."
                    ).classes("text-xs text-gray-500")
                ui.button("Ajouter un prêt", icon="add", on_click=lambda: loan_dialog()).props("color=primary dense")
            if not loans:
                with ui.card().classes("w-full p-4"):
                    ui.label("Aucun prêt partagé.").classes("text-sm text-gray-500")
                return
            with ui.element("div").classes("jf-finance-balance-grid"):
                for loan in loans:
                    with ui.element("section").classes("jf-finance-balance-card"):
                        with ui.row().classes("w-full items-start justify-between gap-2"):
                            with ui.column().classes("gap-0 min-w-0"):
                                ui.label(loan["title"]).classes("font-bold truncate").tooltip(loan["title"])
                                role = "Propriétaire" if loan.get("is_owner") else SHARED_LOAN_ROLES.get(loan.get("my_role"), "Partagé")
                                ui.label(role + (f" · {loan.get('shared_count', 0)} partage(s)" if loan.get("is_owner") else "")).classes("text-xs text-gray-500")
                            if loan.get("is_owner"):
                                ui.button(icon="edit", on_click=lambda _e=None, row=loan: loan_dialog(row)).props("flat dense round size=sm color=primary")
                        ui.label(_money(loan["current_balance"])).classes("jf-finance-balance-main mt-1")
                        ui.label("Solde restant").classes("text-xs text-gray-500 text-right")
                        if loan.get("payment_amount"):
                            ui.label("Versement prévu : " + _money(loan["payment_amount"])).classes("text-xs")
                        if loan.get("next_due_date"):
                            ui.label("Prochaine échéance : " + loan["next_due_date"].strftime("%d/%m/%Y")).classes("text-xs text-primary")
                        with ui.row().classes("w-full justify-end gap-1 mt-2"):
                            ui.button("Voir", icon="visibility", on_click=lambda _e=None, loan_id=loan["id"]: detail_dialog(loan_id)).props("flat dense color=primary")
                            if loan.get("is_owner") or loan.get("my_permission") == "edit":
                                ui.button("Ajouter un mouvement", icon="add", on_click=lambda _e=None, loan_id=loan["id"]: event_dialog(loan_id)).props("outline dense color=primary")

    render_loans()
