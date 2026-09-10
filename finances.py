from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
import json

from nicegui import ui

from app_versions import version_label
from blood_pressure_push import (
    count_active_push_subscriptions,
    get_vapid_public_key,
    save_push_subscription,
    set_push_channel_enabled,
)
from finances_data import (
    BUDGET_INPUT_FREQUENCIES,
    INSTALLMENT_PLAN_TYPES,
    CARRY_POLICIES,
    CONFIRMATION_MODES,
    FREQUENCY_UNITS,
    PAYMENT_METHOD_TYPES,
    RECONCILIATION_SESSION_STATUSES,
    RECONCILIATION_STATUSES,
    TRANSACTION_STATUSES,
    TRANSACTION_TYPES,
    bank_cashflow_month,
    bank_cashflow_year_summary,
    analyze_installment_progress,
    budget_summary,
    budget_capacity_summary,
    budget_forecast,
    bulk_assign_payment_method,
    calculate_installment_payment,
    cancel_reconciliation_session,
    count_unassigned_confirmed_transactions,
    create_reconciliation_session,
    dashboard_month_projection,
    dashboard_summary,
    delete_recurrence,
    delete_installment_plan,
    delete_financing_budget_group,
    delete_reconciliation_draft,
    delete_transaction,
    ensure_default_finance_categories,
    ensure_default_finance_payment_methods,
    export_finances,
    find_potential_duplicate_transactions,
    financing_month_summary,
    generate_due_recurrences,
    get_or_create_finance_category,
    get_or_create_finance_tag,
    get_card_payment_transfer,
    get_installment_plan,
    get_reconciliation_draft,
    get_finance_settings,
    get_reconciliation_session,
    get_transaction,
    goal_progress,
    import_finance_rows,
    init_finances_schema,
    list_bank_accounts,
    list_budget_items,
    list_card_payment_transfers,
    list_categories,
    list_goals,
    list_installment_plans,
    list_financing_budget_groups,
    list_month_unreconciled_transactions,
    list_payment_methods,
    list_reconciliation_sessions,
    list_reconciliation_drafts,
    list_recurrences,
    list_tags,
    list_transactions,
    list_unassigned_transactions,
    list_unreconciled_transactions,
    move_budget_item,
    move_payment_method,
    payment_predicted_balance_summary,
    reconciliation_reference_summary,
    prepare_finance_import,
    remove_transaction_from_reconciliation_session,
    save_budget_item,
    save_financing_budget_group,
    save_card_payment_transfer,
    save_category,
    save_goal,
    save_installment_plan,
    save_reconciliation_draft,
    save_payment_method,
    save_recurrence,
    save_tag,
    save_transaction,
    set_bank_transaction_seen,
    set_month_carryover,
    set_category_dashboard_visible,
    set_tag_dashboard_visible,
    set_transaction_reconciliation,
    set_transaction_status,
    toggle_budget_item,
    toggle_category,
    toggle_goal,
    toggle_installment_plan,
    toggle_payment_method,
    toggle_recurrence,
    toggle_tag,
)
from finances_dialogs import build_finance_dialogs
from finances_entry import build_entry_panel
from finances_import_export import build_import_export_panel
from finances_goals import build_goals_panel
from finances_recurrences import build_recurrences_panel
from finances_dashboard import build_dashboard_panel
from finances_account import build_account_panel
from finances_budget import build_budget_panel
from finances_financing import build_financing_panel
from finances_reconciliation import build_reconciliation_panel
from finances_shared_loans import shared_loans_panel
from finances_ui_state import MonthCursor, month_label as _month_label, shift_month as _shift_month


ADD_CATEGORY_OPTION = "__jf_add_category__"
ADD_TAG_OPTION = "__jf_add_tag__"
CREATE_RECURRENCE_OPTION = "__jf_create_recurrence__"

BUDGET_SORT_FIELDS = {
    "custom": "Ordre personnalisé",
    "description": "Alphabétique",
    "monthly_amount": "Montant par mois",
    "biweekly_amount": "Montant par paie",
    "effective_start": "Date de début",
}
BUDGET_SORT_DIRECTIONS = {
    "asc": "Croissant",
    "desc": "Décroissant",
}


from finances_styles import FINANCE_CSS, install_finance_styles

install_finance_styles(ui)

def _money(value):
    amount = Decimal(value or 0)
    return f"{abs(amount):,.2f}".replace(",", " ").replace(".", ",") + " $"


def _signed(value, transaction_type):
    return ("-" if transaction_type == "expense" else "+") + _money(value)



def _payment_effect(value, transaction_type):
    sign = "+" if transaction_type == "expense" else "-"
    return sign + _money(value)


def _balance_money(value):
    amount = Decimal(value or 0)
    sign = "-" if amount < 0 else ""
    return sign + _money(amount)


def _category_options(user_id):
    return {
        int(row["id"]): row["full_name"]
        for row in list_categories(user_id)
    }


def _tag_options(user_id):
    return {
        int(row["id"]): row["name"]
        for row in list_tags(user_id)
    }

def _quick_category_options(user_id):
    return {
        None: "Aucune",
        **_category_options(user_id),
        ADD_CATEGORY_OPTION: "+ Ajouter une catégorie…",
    }


def _quick_tag_options(user_id):
    return {
        **_tag_options(user_id),
        ADD_TAG_OPTION: "+ Ajouter une étiquette…",
    }


def _bank_account_options(user_id):
    return {
        int(row["id"]): row["name"]
        for row in list_bank_accounts(user_id)
    }


def _payment_options(
    user_id,
    include_none=True,
):
    options = {}

    if include_none:
        options[
            None
        ] = "Aucun"

    for row in list_payment_methods(
        user_id
    ):
        options[
            int(row["id"])
        ] = row["name"]

    return options




def _recurrence_options(user_id):
    options = {None: "Aucune récurrence"}
    for row in list_recurrences(user_id):
        unit = FREQUENCY_UNITS.get(
            row.get("frequency_unit"),
            str(row.get("frequency_unit") or ""),
        ).lower()
        interval = int(row.get("frequency_interval") or 1)
        rhythm = unit if interval == 1 else f"{interval} {unit}s"
        inactive = " — inactive" if not row.get("is_active") else ""
        options[int(row["id"])] = (
            f"{row['description']} — {_money(row['amount'])} / {rhythm}{inactive}"
        )
    return options
def finances_panel(current_user, initial_section=None, show_heading=True):
    user_id = current_user["id"]
    dialogs = build_finance_dialogs(
        ui=ui,
        TRANSACTION_TYPES=TRANSACTION_TYPES,
        TRANSACTION_STATUSES=TRANSACTION_STATUSES,
        _category_options=lambda *args, **kwargs: _category_options(*args, **kwargs),
        _tag_options=lambda *args, **kwargs: _tag_options(*args, **kwargs),
        _payment_options=lambda *args, **kwargs: _payment_options(*args, **kwargs),
        list_payment_methods=lambda *args, **kwargs: list_payment_methods(*args, **kwargs),
        save_transaction=lambda *args, **kwargs: save_transaction(*args, **kwargs),
        save_card_payment_transfer=lambda *args, **kwargs: save_card_payment_transfer(*args, **kwargs),
    )

    # Réessayer ici la mise à niveau du schéma. Au démarrage du Portail,
    # cette initialisation est maintenant non bloquante afin qu’un problème
    # de migration Finances ne puisse plus rendre toutes les applications
    # indisponibles.
    try:
        init_finances_schema()
    except Exception as error:
        with ui.card().classes("w-full max-w-3xl mx-auto jf-finance-card"):
            ui.label("Finances — mise à niveau de la base impossible").classes(
                "text-xl font-bold"
            )
            ui.label(
                "Le Portail peut continuer de fonctionner, mais Finances ne peut "
                "pas s’ouvrir tant que cette erreur n’est pas corrigée."
            ).classes("text-sm jf-muted")
            ui.label(
                f"{type(error).__name__}: {error}"
            ).classes("text-sm font-mono break-all")
        print("Finances — erreur d’initialisation du schéma :")
        import traceback as _traceback
        _traceback.print_exc()
        return
    ensure_default_finance_categories(
        user_id
    )
    ensure_default_finance_payment_methods(
        user_id
    )

    try:
        generate_due_recurrences(user_id)
    except Exception:
        pass

    month_state = MonthCursor()
    financing_month_state = MonthCursor()

    if show_heading:
        with ui.row().classes(
            "w-full items-center justify-between gap-2 flex-wrap"
        ):
            with ui.column().classes("gap-0"):
                with ui.row().classes("items-center gap-2"):
                    ui.label("Finances").classes("text-2xl font-bold")
                    ui.label(version_label("finances")).classes(
                        "text-xs font-bold px-2 py-1 rounded-full "
                        "bg-blue-100 text-blue-800"
                    )
                ui.label(
                    "Budget fixe, capacité disponible et dépenses variables."
                ).classes("text-sm jf-muted")

            with ui.row().classes("items-center gap-1"):
                ui.button(
                    "Paiement carte",
                    icon="credit_card",
                    on_click=lambda: dialogs.card_payment(user_id, refresh_all),
                ).props("outline color=primary dense")
                ui.button(
                    "Ajouter",
                    icon="add",
                    on_click=lambda: dialogs.transaction(user_id, refresh_all),
                ).props("color=primary dense")
    else:
        with ui.row().classes("w-full justify-end gap-1 flex-wrap"):
            ui.button(
                "Paiement de carte",
                icon="credit_card",
                on_click=lambda: dialogs.card_payment(user_id, refresh_all),
            ).props("outline color=primary dense")
            ui.button(
                "Ajouter une transaction",
                icon="add",
                on_click=lambda: dialogs.transaction(user_id, refresh_all),
            ).props("color=primary dense")

    with ui.tabs().props(
        "dense no-caps inline-label "
        "mobile-arrows outside-arrows align=left"
    ).classes(
        "jf-finance-main-tabs"
    ) as tabs:
        dashboard_tab = ui.tab("Tableau", icon="dashboard")
        account_tab = ui.tab("Compte", icon="account_balance")
        budget_tab = ui.tab("Budget", icon="savings")
        financing_tab = ui.tab("Financements", icon="payments")
        shared_loans_tab = ui.tab("Prêts partagés", icon="handshake")
        entry_tab = ui.tab("Saisie", icon="add_circle")
        history_tab = ui.tab("Historique", icon="history")
        recurring_tab = ui.tab("Récurrences", icon="repeat")
        goals_tab = ui.tab("Objectifs", icon="track_changes")
        reconciliation_tab = ui.tab("Conciliation", icon="fact_check")
        organization_tab = ui.tab("Organisation", icon="category")
        export_tab = ui.tab("Exporter", icon="download")

    tab_map = {
        "tableau": dashboard_tab,
        "compte": account_tab,
        "tresorerie": account_tab,
        "trésorerie": account_tab,
        "budget": budget_tab,
        "financements": financing_tab,
        "financement": financing_tab,
        "versements": financing_tab,
        "prets": shared_loans_tab,
        "prêts": shared_loans_tab,
        "prets-partages": shared_loans_tab,
        "prêts-partagés": shared_loans_tab,
        "saisie": entry_tab,
        "historique": history_tab,
        "recurrences": recurring_tab,
        "récurrences": recurring_tab,
        "objectifs": goals_tab,
        "organisation": organization_tab,
        "categories": organization_tab,
        "etiquettes": organization_tab,
        "étiquettes": organization_tab,
        "paiements": organization_tab,
        "conciliation": reconciliation_tab,
        "releve": reconciliation_tab,
        "relevé": reconciliation_tab,
        "exporter": export_tab,
    }

    with ui.tab_panels(
        tabs,
        value=tab_map.get(str(initial_section or "tableau").lower(), dashboard_tab),
    ).classes("w-full bg-transparent"):

        # TABLEAU
        dashboard_panel = build_dashboard_panel(
            ui=ui,
            user_id=user_id,
            dashboard_tab=dashboard_tab,
            month_state=month_state,
            tabs=tabs,
            account_tab=account_tab,
            reconciliation_tab=reconciliation_tab,
            PAYMENT_METHOD_TYPES=PAYMENT_METHOD_TYPES,
            dashboard_month_projection=lambda *args, **kwargs: dashboard_month_projection(*args, **kwargs),
            budget_capacity_summary=lambda *args, **kwargs: budget_capacity_summary(*args, **kwargs),
            goal_progress=lambda *args, **kwargs: goal_progress(*args, **kwargs),
            payment_predicted_balance_summary=lambda *args, **kwargs: payment_predicted_balance_summary(*args, **kwargs),
            count_unassigned_confirmed_transactions=lambda *args, **kwargs: count_unassigned_confirmed_transactions(*args, **kwargs),
            list_bank_accounts=lambda *args, **kwargs: list_bank_accounts(*args, **kwargs),
            bank_cashflow_month=lambda *args, **kwargs: bank_cashflow_month(*args, **kwargs),
            get_transaction=lambda *args, **kwargs: get_transaction(*args, **kwargs),
            set_month_carryover=lambda *args, **kwargs: set_month_carryover(*args, **kwargs),
            _money=lambda *args, **kwargs: _money(*args, **kwargs),
            _balance_money=lambda *args, **kwargs: _balance_money(*args, **kwargs),
            _month_label=lambda *args, **kwargs: _month_label(*args, **kwargs),
            _transaction_dialog=lambda *args, **kwargs: dialogs.transaction(*args, **kwargs),
            refresh_all=lambda *args, **kwargs: refresh_all(*args, **kwargs),
        )
        # COMPTE / TRÉSORERIE
        account_panel = build_account_panel(
            ui=ui,
            user_id=user_id,
            account_tab=account_tab,
            tabs=tabs,
            organization_tab=organization_tab,
            MonthCursor=lambda: MonthCursor(),
            list_bank_accounts=lambda *args, **kwargs: list_bank_accounts(*args, **kwargs),
            bank_cashflow_month=lambda *args, **kwargs: bank_cashflow_month(*args, **kwargs),
            bank_cashflow_year_summary=lambda *args, **kwargs: bank_cashflow_year_summary(*args, **kwargs),
            list_recurrences=lambda *args, **kwargs: list_recurrences(*args, **kwargs),
            get_transaction=lambda *args, **kwargs: get_transaction(*args, **kwargs),
            get_card_payment_transfer=lambda *args, **kwargs: get_card_payment_transfer(*args, **kwargs),
            set_bank_transaction_seen=lambda *args, **kwargs: set_bank_transaction_seen(*args, **kwargs),
            count_active_push_subscriptions=lambda *args, **kwargs: count_active_push_subscriptions(*args, **kwargs),
            get_vapid_public_key=lambda *args, **kwargs: get_vapid_public_key(*args, **kwargs),
            save_push_subscription=lambda *args, **kwargs: save_push_subscription(*args, **kwargs),
            set_push_channel_enabled=lambda *args, **kwargs: set_push_channel_enabled(*args, **kwargs),
            _bank_account_options=lambda *args, **kwargs: _bank_account_options(*args, **kwargs),
            _money=lambda *args, **kwargs: _money(*args, **kwargs),
            _balance_money=lambda *args, **kwargs: _balance_money(*args, **kwargs),
            _month_label=lambda *args, **kwargs: _month_label(*args, **kwargs),
            refresh_all=lambda *args, **kwargs: refresh_all(*args, **kwargs),
            recurrence_dialog=lambda *args, **kwargs: recurrences_panel.open_dialog(*args, **kwargs),
            _transaction_dialog=lambda *args, **kwargs: dialogs.transaction(*args, **kwargs),
            _card_payment_dialog=lambda *args, **kwargs: dialogs.card_payment(*args, **kwargs),
        )
        budget_panel = build_budget_panel(
            ui=ui,
            user_id=user_id,
            budget_tab=budget_tab,
            month_state=month_state,
            budget_capacity_summary=lambda *args, **kwargs: budget_capacity_summary(*args, **kwargs),
            list_budget_items=lambda *args, **kwargs: list_budget_items(*args, **kwargs),
            budget_forecast=lambda *args, **kwargs: budget_forecast(*args, **kwargs),
            list_installment_plans=lambda *args, **kwargs: list_installment_plans(*args, **kwargs),
            save_budget_item=lambda *args, **kwargs: save_budget_item(*args, **kwargs),
            save_financing_budget_group=lambda *args, **kwargs: save_financing_budget_group(*args, **kwargs),
            delete_financing_budget_group=lambda *args, **kwargs: delete_financing_budget_group(*args, **kwargs),
            toggle_budget_item=lambda *args, **kwargs: toggle_budget_item(*args, **kwargs),
            move_budget_item=lambda *args, **kwargs: move_budget_item(*args, **kwargs),
            generate_due_recurrences=lambda *args, **kwargs: generate_due_recurrences(*args, **kwargs),
            _recurrence_options=lambda *args, **kwargs: _recurrence_options(*args, **kwargs),
            _category_options=lambda *args, **kwargs: _category_options(*args, **kwargs),
            _payment_options=lambda *args, **kwargs: _payment_options(*args, **kwargs),
            _tag_options=lambda *args, **kwargs: _tag_options(*args, **kwargs),
            _money=lambda *args, **kwargs: _money(*args, **kwargs),
            _balance_money=lambda *args, **kwargs: _balance_money(*args, **kwargs),
            _month_label=lambda *args, **kwargs: _month_label(*args, **kwargs),
            _shift_month=lambda *args, **kwargs: _shift_month(*args, **kwargs),
            TRANSACTION_TYPES=TRANSACTION_TYPES,
            BUDGET_INPUT_FREQUENCIES=BUDGET_INPUT_FREQUENCIES,
            FREQUENCY_UNITS=FREQUENCY_UNITS,
            CONFIRMATION_MODES=CONFIRMATION_MODES,
            CREATE_RECURRENCE_OPTION=CREATE_RECURRENCE_OPTION,
            BUDGET_SORT_FIELDS=BUDGET_SORT_FIELDS,
            BUDGET_SORT_DIRECTIONS=BUDGET_SORT_DIRECTIONS,
            refresh_all=lambda *args, **kwargs: refresh_all(*args, **kwargs),
        )
        financing_panel = build_financing_panel(
            ui=ui,
            user_id=user_id,
            financing_tab=financing_tab,
            financing_month_state=financing_month_state,
            INSTALLMENT_PLAN_TYPES=INSTALLMENT_PLAN_TYPES,
            FREQUENCY_UNITS=FREQUENCY_UNITS,
            _payment_options=lambda *args, **kwargs: _payment_options(*args, **kwargs),
            _category_options=lambda *args, **kwargs: _category_options(*args, **kwargs),
            _tag_options=lambda *args, **kwargs: _tag_options(*args, **kwargs),
            list_installment_plans=lambda *args, **kwargs: list_installment_plans(*args, **kwargs),
            financing_month_summary=lambda *args, **kwargs: financing_month_summary(*args, **kwargs),
            save_installment_plan=lambda *args, **kwargs: save_installment_plan(*args, **kwargs),
            delete_installment_plan=lambda *args, **kwargs: delete_installment_plan(*args, **kwargs),
            toggle_installment_plan=lambda *args, **kwargs: toggle_installment_plan(*args, **kwargs),
            calculate_installment_payment=lambda *args, **kwargs: calculate_installment_payment(*args, **kwargs),
            analyze_installment_progress=lambda *args, **kwargs: analyze_installment_progress(*args, **kwargs),
            _money=lambda *args, **kwargs: _money(*args, **kwargs),
            _balance_money=lambda *args, **kwargs: _balance_money(*args, **kwargs),
            _month_label=lambda *args, **kwargs: _month_label(*args, **kwargs),
            refresh_all=lambda: refresh_all(),
        )

        # PRÊTS PARTAGÉS
        with ui.tab_panel(shared_loans_tab).classes("px-0"):
            # refresh_all est défini plus bas dans finances_panel.
            # Le passer directement ici l'évaluait pendant la construction
            # de la page et faisait échouer l'ouverture de Finances.
            # La lambda retarde sa résolution jusqu'au clic/rafraîchissement.
            shared_loans_panel(
                current_user,
                refresh_parent=lambda: refresh_all(),
            )


        # SAISIE
        entry_panel = build_entry_panel(
            ui=ui,
            user_id=user_id,
            entry_tab=entry_tab,
            TRANSACTION_TYPES=TRANSACTION_TYPES,
            TRANSACTION_STATUSES=TRANSACTION_STATUSES,
            ADD_CATEGORY_OPTION=ADD_CATEGORY_OPTION,
            ADD_TAG_OPTION=ADD_TAG_OPTION,
            _quick_category_options=lambda *args, **kwargs: _quick_category_options(*args, **kwargs),
            _quick_tag_options=lambda *args, **kwargs: _quick_tag_options(*args, **kwargs),
            _payment_options=lambda *args, **kwargs: _payment_options(*args, **kwargs),
            list_categories=lambda *args, **kwargs: list_categories(*args, **kwargs),
            get_or_create_finance_category=lambda *args, **kwargs: get_or_create_finance_category(*args, **kwargs),
            get_or_create_finance_tag=lambda *args, **kwargs: get_or_create_finance_tag(*args, **kwargs),
            save_transaction=lambda *args, **kwargs: save_transaction(*args, **kwargs),
            _card_payment_dialog=lambda *args, **kwargs: dialogs.card_payment(*args, **kwargs),
            refresh_all=lambda *args, **kwargs: refresh_all(*args, **kwargs),
            refresh_dashboard=lambda: dashboard_panel.refresh(),
        )
        # HISTORIQUE
        with ui.tab_panel(history_tab).classes("px-0"):
            import finances_history as _history_ui

            history_panel = _history_ui.build_history_panel(
                ui=ui,
                user_id=user_id,
                month_value=month_state.value,
                today_value=date.today(),
                TRANSACTION_TYPES=TRANSACTION_TYPES,
                TRANSACTION_STATUSES=TRANSACTION_STATUSES,
                RECONCILIATION_STATUSES=RECONCILIATION_STATUSES,
                category_options=lambda: _category_options(user_id),
                tag_options=lambda: _tag_options(user_id),
                payment_options=lambda: _payment_options(
                    user_id,
                    include_none=False,
                ),
                on_apply=lambda: render_history.refresh(),
                on_duplicate_search=lambda: duplicate_search_dialog(),
                on_monthly_unreconciled=lambda: monthly_unreconciled_dialog(),
            )

            # Alias conservés pour les raccords existants du parent.
            start = history_panel.start
            end = history_panel.end
            query = history_panel.query
            history_amount_exact = history_panel.amount_exact
            history_amount_min = history_panel.amount_min
            history_amount_max = history_panel.amount_max
            history_type = history_panel.transaction_type
            history_status = history_panel.status
            history_reconciliation = history_panel.reconciliation
            history_category = history_panel.category
            history_tag = history_panel.tag
            history_payment = history_panel.payment
            history_box = history_panel.history_box

            history_actions = _history_ui.build_history_actions(
                ui=ui,
                panel=history_panel,
                user_id=user_id,
                TRANSACTION_TYPES=TRANSACTION_TYPES,
                TRANSACTION_STATUSES=TRANSACTION_STATUSES,
                RECONCILIATION_STATUSES=RECONCILIATION_STATUSES,
                signed=_signed,
                money=_money,
                delete_transaction=delete_transaction,
                set_transaction_status=set_transaction_status,
                set_transaction_reconciliation=set_transaction_reconciliation,
                get_card_payment_transfer=get_card_payment_transfer,
                get_transaction=get_transaction,
                card_payment_dialog=lambda *args, **kwargs: dialogs.card_payment(*args, **kwargs),
                transaction_dialog=lambda *args, **kwargs: dialogs.transaction(*args, **kwargs),
                find_potential_duplicate_transactions=(
                    find_potential_duplicate_transactions
                ),
                list_month_unreconciled_transactions=(
                    list_month_unreconciled_transactions
                ),
                set_bank_transaction_seen=set_bank_transaction_seen,
                get_month_value=lambda: month_state.value,
                refresh_all=lambda: refresh_all(),
            )

            remove_dialog = history_actions.remove_dialog
            confirm_transaction = history_actions.confirm_transaction
            change_reconciliation = history_actions.change_reconciliation
            render_transaction_row = history_actions.render_transaction_row
            _open_history_row = history_actions.open_history_row
            duplicate_search_dialog = history_actions.duplicate_search_dialog
            monthly_unreconciled_dialog = (
                history_actions.monthly_unreconciled_dialog
            )
            _add_month_label_end = history_actions.add_month_label_end

            @ui.refreshable
            def render_history():
                _history_ui.render_history(
                    ui=ui,
                    panel=history_panel,
                    user_id=user_id,
                    list_transactions=list_transactions,
                    render_transaction_row=render_transaction_row,
                    money=_money,
                )

            render_history()


        # RÉCURRENCES
        recurrences_panel = build_recurrences_panel(
            ui=ui,
            user_id=user_id,
            recurring_tab=recurring_tab,
            TRANSACTION_TYPES=TRANSACTION_TYPES,
            FREQUENCY_UNITS=FREQUENCY_UNITS,
            CONFIRMATION_MODES=CONFIRMATION_MODES,
            delete_recurrence=lambda *args, **kwargs: delete_recurrence(*args, **kwargs),
            save_recurrence=lambda *args, **kwargs: save_recurrence(*args, **kwargs),
            generate_due_recurrences=lambda *args, **kwargs: generate_due_recurrences(*args, **kwargs),
            list_recurrences=lambda *args, **kwargs: list_recurrences(*args, **kwargs),
            toggle_recurrence=lambda *args, **kwargs: toggle_recurrence(*args, **kwargs),
            _category_options=lambda *args, **kwargs: _category_options(*args, **kwargs),
            _payment_options=lambda *args, **kwargs: _payment_options(*args, **kwargs),
            _tag_options=lambda *args, **kwargs: _tag_options(*args, **kwargs),
            _signed=lambda *args, **kwargs: _signed(*args, **kwargs),
            refresh_all=lambda *args, **kwargs: refresh_all(*args, **kwargs),
        )

        # OBJECTIFS
        goals_panel = build_goals_panel(
            ui=ui,
            user_id=user_id,
            goals_tab=goals_tab,
            CARRY_POLICIES=CARRY_POLICIES,
            _category_options=lambda *args, **kwargs: _category_options(*args, **kwargs),
            _tag_options=lambda *args, **kwargs: _tag_options(*args, **kwargs),
            _money=lambda *args, **kwargs: _money(*args, **kwargs),
            save_goal=lambda *args, **kwargs: save_goal(*args, **kwargs),
            list_goals=lambda *args, **kwargs: list_goals(*args, **kwargs),
            toggle_goal=lambda *args, **kwargs: toggle_goal(*args, **kwargs),
            refresh_all=lambda *args, **kwargs: refresh_all(*args, **kwargs),
        )

        # CONCILIATION
        reconciliation_panel = build_reconciliation_panel(
            RECONCILIATION_SESSION_STATUSES=RECONCILIATION_SESSION_STATUSES,
            _balance_money=lambda *args, **kwargs: _balance_money(*args, **kwargs),
            _card_payment_dialog=lambda *args, **kwargs: dialogs.card_payment(*args, **kwargs),
            _money=lambda *args, **kwargs: _money(*args, **kwargs),
            _payment_effect=lambda *args, **kwargs: _payment_effect(*args, **kwargs),
            _payment_options=lambda *args, **kwargs: _payment_options(*args, **kwargs),
            _signed=lambda *args, **kwargs: _signed(*args, **kwargs),
            _transaction_dialog=lambda *args, **kwargs: dialogs.transaction(*args, **kwargs),
            bulk_assign_payment_method=lambda *args, **kwargs: bulk_assign_payment_method(*args, **kwargs),
            cancel_reconciliation_session=lambda *args, **kwargs: cancel_reconciliation_session(*args, **kwargs),
            create_reconciliation_session=lambda *args, **kwargs: create_reconciliation_session(*args, **kwargs),
            delete_reconciliation_draft=lambda *args, **kwargs: delete_reconciliation_draft(*args, **kwargs),
            get_card_payment_transfer=lambda *args, **kwargs: get_card_payment_transfer(*args, **kwargs),
            get_reconciliation_draft=lambda *args, **kwargs: get_reconciliation_draft(*args, **kwargs),
            get_reconciliation_session=lambda *args, **kwargs: get_reconciliation_session(*args, **kwargs),
            list_payment_methods=lambda *args, **kwargs: list_payment_methods(*args, **kwargs),
            list_reconciliation_drafts=lambda *args, **kwargs: list_reconciliation_drafts(*args, **kwargs),
            list_reconciliation_sessions=lambda *args, **kwargs: list_reconciliation_sessions(*args, **kwargs),
            list_unassigned_transactions=lambda *args, **kwargs: list_unassigned_transactions(*args, **kwargs),
            list_unreconciled_transactions=lambda *args, **kwargs: list_unreconciled_transactions(*args, **kwargs),
            list_transactions=lambda *args, **kwargs: list_transactions(*args, **kwargs),
            payment_predicted_balance_summary=lambda *args, **kwargs: payment_predicted_balance_summary(*args, **kwargs),
            reconciliation_reference_summary=lambda *args, **kwargs: reconciliation_reference_summary(*args, **kwargs),
            reconciliation_tab=reconciliation_tab,
            refresh_all=lambda: refresh_all(),
            remove_transaction_from_reconciliation_session=lambda *args, **kwargs: remove_transaction_from_reconciliation_session(*args, **kwargs),
            save_reconciliation_draft=lambda *args, **kwargs: save_reconciliation_draft(*args, **kwargs),
            set_transaction_status=lambda *args, **kwargs: set_transaction_status(*args, **kwargs),
            ui=ui,
            user_id=user_id,
        )
        # ORGANISATION
        from finances_organization import build_organization_panel

        organization_panel = build_organization_panel(
            ui=ui,
            user_id=user_id,
            organization_tab=organization_tab,
            PAYMENT_METHOD_TYPES=PAYMENT_METHOD_TYPES,
            _balance_money=_balance_money,
            list_categories=list_categories,
            save_category=save_category,
            set_category_dashboard_visible=set_category_dashboard_visible,
            toggle_category=toggle_category,
            list_tags=list_tags,
            save_tag=save_tag,
            set_tag_dashboard_visible=set_tag_dashboard_visible,
            toggle_tag=toggle_tag,
            list_payment_methods=list_payment_methods,
            save_payment_method=save_payment_method,
            toggle_payment_method=toggle_payment_method,
            move_payment_method=move_payment_method,
            refresh_all=lambda: refresh_all(),
            render_dashboard=dashboard_panel,
        )

        # IMPORTER ET EXPORTER
        build_import_export_panel(
            ui=ui,
            user_id=user_id,
            export_tab=export_tab,
            prepare_finance_import=lambda *args, **kwargs: prepare_finance_import(*args, **kwargs),
            import_finance_rows=lambda *args, **kwargs: import_finance_rows(*args, **kwargs),
            export_finances=lambda *args, **kwargs: export_finances(*args, **kwargs),
            _signed=lambda *args, **kwargs: _signed(*args, **kwargs),
            refresh_all=lambda *args, **kwargs: refresh_all(*args, **kwargs),
        )

    def refresh_all():
        # Actualiser les listes déjà visibles après l’ajout ou
        # la modification d’une catégorie, d’une étiquette ou
        # d’un mode de paiement.
        entry_panel.reload_options()

        history_category.options = {
            None: "Toutes",
            **_category_options(
                user_id
            ),
        }
        history_category.update()

        history_tag.options = {
            None: "Toutes",
            **_tag_options(
                user_id
            ),
        }
        history_tag.update()

        history_payment.options = {
            None: "Tous",
            **_payment_options(
                user_id,
                include_none=False,
            ),
        }
        history_payment.update()

        dashboard_panel.refresh()
        render_history.refresh()
        recurrences_panel.refresh()
        goals_panel.refresh()
        organization_panel.refresh()
        account_panel.reload_options()
        account_panel.refresh()
        budget_panel.refresh()
        financing_panel.refresh()

        reconciliation_panel.reload_options()
        reconciliation_panel.refresh()
