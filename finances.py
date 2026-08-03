from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile

from nicegui import ui

from app_versions import version_label
from finances_data import (
    CARRY_POLICIES,
    CONFIRMATION_MODES,
    FREQUENCY_UNITS,
    PAYMENT_METHOD_TYPES,
    RECONCILIATION_SESSION_STATUSES,
    RECONCILIATION_STATUSES,
    TRANSACTION_STATUSES,
    TRANSACTION_TYPES,
    bulk_assign_payment_method,
    cancel_reconciliation_session,
    count_unassigned_confirmed_transactions,
    create_reconciliation_session,
    dashboard_month_projection,
    dashboard_summary,
    delete_transaction,
    ensure_default_finance_categories,
    ensure_default_finance_payment_methods,
    export_finances,
    generate_due_recurrences,
    get_reconciliation_session,
    get_transaction,
    goal_progress,
    import_finance_rows,
    list_categories,
    list_goals,
    list_payment_methods,
    list_reconciliation_sessions,
    list_recurrences,
    list_tags,
    list_transactions,
    list_unassigned_transactions,
    list_unreconciled_transactions,
    move_payment_method,
    payment_predicted_balance_summary,
    prepare_finance_import,
    remove_transaction_from_reconciliation_session,
    save_category,
    save_goal,
    save_payment_method,
    save_recurrence,
    save_tag,
    save_transaction,
    set_transaction_reconciliation,
    set_transaction_status,
    toggle_category,
    toggle_goal,
    toggle_payment_method,
    toggle_recurrence,
    toggle_tag,
)


FINANCE_CSS = r"""
.jf-finance-summary-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: .45rem;
    width: 100%;
}
.jf-finance-summary {
    min-width: 0;
    padding: .58rem .58rem;
    border: 1px solid var(--jf-border);
    border-radius: 11px;
    background: var(--jf-surface);
}
.jf-finance-summary-label {
    color: var(--jf-muted);
    font-size: .66rem;
}
.jf-finance-summary-value {
    width: 100%;
    color: var(--jf-navy);
    font-size: 1rem;
    font-weight: 850;
    text-align: right;
    white-space: nowrap;
}
.body--dark .jf-finance-summary-value {
    color: #dceaf6;
}
.jf-finance-form-grid {
    display: grid;
    grid-template-columns:
        minmax(7rem, .7fr)
        minmax(8rem, .8fr)
        minmax(12rem, 1.5fr);
    gap: .5rem;
    width: 100%;
}
.jf-finance-field .q-field__control {
    min-height: 40px;
    height: 40px;
}
.jf-finance-card {
    width: 100%;
    padding: .55rem .65rem;
    border: 1px solid var(--jf-border);
    border-radius: 10px;
    background: var(--jf-surface);
}
.jf-finance-expense {
    color: #a33b46;
}
.jf-finance-income {
    color: #187148;
}
.jf-finance-progress {
    width: 100%;
    height: 7px;
    overflow: hidden;
    border-radius: 99px;
    background: rgba(120, 130, 145, .18);
}
.jf-finance-progress > div {
    height: 100%;
    border-radius: 99px;
    background: var(--jf-blue);
}
.jf-finance-kpi-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: .55rem;
    width: 100%;
}
.jf-finance-kpi-list {
    display: flex;
    flex-direction: column;
    gap: 0;
    width: 100%;
}
.jf-finance-kpi-header,
.jf-finance-kpi-row {
    display: grid;
    grid-template-columns:
        minmax(0, 1.35fr)
        minmax(5.4rem, .72fr)
        minmax(5.4rem, .72fr)
        minmax(5.8rem, .78fr);
    align-items: center;
    gap: .42rem;
    width: 100%;
}
.jf-finance-kpi-header {
    padding: .25rem 0 .35rem;
    color: var(--jf-muted);
    font-size: .62rem;
    font-weight: 800;
    text-transform: uppercase;
}
.jf-finance-kpi-row {
    padding: .34rem 0;
    border-bottom: 1px solid var(--jf-border);
}
.jf-finance-kpi-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: .75rem;
}
.jf-finance-kpi-value {
    justify-self: end;
    min-width: 0;
    font-size: .74rem;
    font-weight: 760;
    text-align: right;
    white-space: nowrap;
}
.jf-finance-kpi-total {
    font-weight: 900;
}
.jf-finance-upcoming-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: .55rem;
    width: 100%;
}
.jf-finance-upcoming-row {
    display: grid;
    grid-template-columns: 4.6rem minmax(0, 1fr) auto;
    align-items: center;
    gap: .45rem;
    width: 100%;
    padding: .35rem 0;
    border-bottom: 1px solid var(--jf-border);
}
.jf-finance-upcoming-date {
    color: var(--jf-muted);
    font-size: .68rem;
    white-space: nowrap;
}
.jf-finance-upcoming-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: .76rem;
    font-weight: 760;
}
.jf-finance-upcoming-meta {
    min-width: 0;
    overflow: hidden;
    color: var(--jf-muted);
    font-size: .62rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.jf-finance-upcoming-amount {
    min-width: 6rem;
    font-size: .76rem;
    font-weight: 850;
    text-align: right;
    white-space: nowrap;
}
.jf-finance-reconciliation-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: .5rem;
    width: 100%;
}
.jf-finance-reconciliation-card {
    width: 100%;
    padding: .5rem .6rem;
    border: 1px solid var(--jf-border);
    border-radius: 10px;
    background: var(--jf-surface);
}
.jf-finance-reconciliation-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: .45rem;
    width: 100%;
    font-size: .72rem;
}
.jf-finance-reconciliation-value {
    justify-self: end;
    min-width: 6.4rem;
    font-weight: 800;
    text-align: right;
    white-space: nowrap;
}
.jf-finance-history-list {
    display: flex;
    flex-direction: column;
    gap: .55rem;
    width: 100%;
}
.jf-finance-history-day {
    width: 100%;
    overflow: hidden;
    border: 1px solid var(--jf-border);
    border-radius: 12px;
    background: var(--jf-surface);
}
.jf-finance-day {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .5rem;
    width: 100%;
    padding: .3rem .55rem;
    border-left: 4px solid var(--jf-blue);
    background: var(--jf-blue-soft);
    font-size: .76rem;
    font-weight: 800;
}
.jf-finance-history-columns {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0;
    width: 100%;
}
.jf-finance-history-column {
    min-width: 0;
    padding: .4rem;
}
.jf-finance-history-column + .jf-finance-history-column {
    border-left: 1px solid var(--jf-border);
}
.jf-finance-history-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .4rem;
    padding: 0 .15rem .3rem;
    color: var(--jf-muted);
    font-size: .66rem;
    font-weight: 800;
    text-transform: uppercase;
}
.jf-finance-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto auto;
    grid-template-areas:
        "main amount actions"
        "meta amount actions";
    align-items: center;
    gap: .05rem .38rem;
    width: 100%;
    min-height: 43px;
    padding: .28rem .35rem;
    border: 1px solid var(--jf-border);
    border-radius: 9px;
    background: var(--jf-surface);
}
.jf-finance-row + .jf-finance-row {
    margin-top: .28rem;
}
.jf-finance-main {
    grid-area: main;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: .82rem;
    font-weight: 800;
}
.jf-finance-meta {
    grid-area: meta;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--jf-muted);
    font-size: .65rem;
}
.jf-finance-amount {
    grid-area: amount;
    justify-self: end;
    min-width: 6.6rem;
    font-size: .86rem;
    font-variant-numeric: tabular-nums;
    font-weight: 850;
    text-align: right;
    white-space: nowrap;
}
.jf-finance-actions {
    grid-area: actions;
    display: flex;
    gap: 0;
    justify-self: end;
}
.jf-finance-payment-chip,
.jf-finance-reconciliation-chip {
    display: inline-flex;
    align-items: center;
    width: fit-content;
    padding: .08rem .32rem;
    border-radius: 999px;
    font-size: .58rem;
    font-weight: 800;
}
.jf-finance-payment-chip {
    color: var(--jf-blue);
    background: var(--jf-blue-soft);
}
.jf-finance-reconciliation-chip {
    color: #73500f;
    background: rgba(199, 151, 65, .17);
}
.jf-finance-reconciled-chip {
    color: #176848;
    background: rgba(33, 145, 92, .15);
}
.jf-finance-empty-column {
    padding: .55rem .25rem;
    color: var(--jf-muted);
    font-size: .7rem;
    text-align: center;
}
.jf-finance-payment-row {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: .35rem;
    width: 100%;
}
.jf-finance-payment-order {
    display: flex;
    gap: 0;
}
@media (max-width: 760px) {
    .jf-finance-form-grid {
        grid-template-columns: 1fr 1fr;
    }
    .jf-finance-description {
        grid-column: 1 / -1;
    }
    .jf-finance-summary-value {
        font-size: .86rem;
    }
    .jf-finance-kpi-grid,
    .jf-finance-upcoming-grid,
    .jf-finance-reconciliation-grid,
    .jf-finance-history-columns {
        grid-template-columns: 1fr;
    }
    .jf-finance-history-column + .jf-finance-history-column {
        border-left: 0;
        border-top: 1px solid var(--jf-border);
    }
}
@media (max-width: 430px) {
    .jf-finance-summary-label {
        font-size: .59rem;
    }
    .jf-finance-summary-value {
        font-size: .76rem;
    }
    .jf-finance-row {
        grid-template-columns: minmax(0, 1fr) auto;
        grid-template-areas:
            "main amount"
            "meta actions";
    }
    .jf-finance-amount {
        min-width: 5.8rem;
    }
    .jf-finance-kpi-header,
    .jf-finance-kpi-row {
        grid-template-columns:
            minmax(0, 1fr)
            4.45rem
            4.45rem
            4.75rem;
        gap: .25rem;
    }
    .jf-finance-kpi-header {
        font-size: .52rem;
    }
    .jf-finance-kpi-name,
    .jf-finance-kpi-value {
        font-size: .65rem;
    }
}
"""

ui.add_css(FINANCE_CSS, shared=True)

ui.add_css(
    r"""
    .jf-finance-balance-grid {
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));
        gap:.55rem;
        width:100%;
    }
    .jf-finance-balance-card {
        width:100%;
        padding:.65rem .72rem;
        border:1px solid var(--jf-border);
        border-radius:12px;
        background:var(--jf-surface);
    }
    .jf-finance-balance-main {
        width:100%;
        color:var(--jf-navy);
        font-size:1.08rem;
        font-weight:850;
        text-align:right;
        white-space:nowrap;
    }
    .body--dark .jf-finance-balance-main {color:#dceaf6;}
    .jf-finance-balance-line {
        display:grid;
        grid-template-columns:minmax(0,1fr) auto;
        align-items:center;
        gap:.5rem;
        width:100%;
        font-size:.72rem;
    }
    .jf-finance-balance-line > :last-child {
        min-width:6.5rem;
        text-align:right;
        font-weight:750;
    }
    .jf-finance-reconcile-toolbar {
        display:grid;
        grid-template-columns:minmax(12rem,1.3fr) minmax(9rem,.8fr)
            minmax(9rem,.8fr) minmax(10rem,1fr);
        align-items:end;
        gap:.5rem;
        width:100%;
    }
    .jf-finance-reconcile-row {
        display:grid;
        grid-template-columns:auto 5.4rem minmax(0,1fr) 7.5rem;
        align-items:center;
        gap:.45rem;
        min-height:42px;
        padding:.28rem .4rem;
        border:1px solid var(--jf-border);
        border-radius:9px;
        background:var(--jf-surface);
    }
    .jf-finance-reconcile-date {
        color:var(--jf-muted);
        font-size:.7rem;
        white-space:nowrap;
    }
    .jf-finance-reconcile-description {
        min-width:0;
        overflow:hidden;
        text-overflow:ellipsis;
        white-space:nowrap;
        font-size:.8rem;
        font-weight:750;
    }
    .jf-finance-reconcile-amount {
        text-align:right;
        font-size:.82rem;
        font-weight:850;
        white-space:nowrap;
    }
    .jf-finance-selection-summary {
        position:sticky;
        bottom:.35rem;
        z-index:4;
        width:100%;
        padding:.65rem .75rem;
        border:1px solid var(--jf-border);
        border-radius:12px;
        box-shadow:0 3px 12px rgba(0,0,0,.12);
        background:var(--jf-surface);
    }
    .jf-finance-session-card {
        width:100%;
        padding:.6rem .7rem;
        border:1px solid var(--jf-border);
        border-radius:11px;
        background:var(--jf-surface);
    }
    .jf-finance-session-cancelled {opacity:.68;}
    .jf-finance-warning-card {
        width:100%;
        padding:.55rem .65rem;
        border-left:4px solid #c6861a;
        border-radius:10px;
        background:rgba(198,134,26,.10);
    }
    @media(max-width:760px){
        .jf-finance-reconcile-toolbar {
            grid-template-columns:1fr 1fr;
        }
        .jf-finance-reconcile-search {grid-column:1/-1;}
    }
    @media(max-width:520px){
        .jf-finance-reconcile-toolbar {grid-template-columns:1fr;}
        .jf-finance-reconcile-search {grid-column:auto;}
        .jf-finance-reconcile-row {
            grid-template-columns:auto 4.5rem minmax(0,1fr) 6.5rem;
            gap:.3rem;
            padding-inline:.25rem;
        }
        .jf-finance-reconcile-description {font-size:.74rem;}
        .jf-finance-reconcile-amount {font-size:.75rem;}
    }
    """,
    shared=True,
)


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


def _month_label(month):
    names = [
        "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
    ]
    return f"{names[month.month]} {month.year}"


def _shift_month(month, amount):
    absolute = month.year * 12 + month.month - 1 + amount
    year, month_index = divmod(absolute, 12)
    return date(year, month_index + 1, 1)


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



def _transaction_dialog(
    user_id,
    on_saved,
    transaction=None,
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
                        else None
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


def finances_panel(current_user, initial_section=None, show_heading=True):
    user_id = current_user["id"]
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

    month_state = {"value": date.today().replace(day=1)}

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
                    "Dépenses variables, revenus et objectifs mensuels."
                ).classes("text-sm jf-muted")

            ui.button(
                "Ajouter",
                icon="add",
                on_click=lambda: _transaction_dialog(user_id, refresh_all),
            ).props("color=primary dense")
    else:
        with ui.row().classes("w-full justify-end"):
            ui.button(
                "Ajouter une transaction",
                icon="add",
                on_click=lambda: _transaction_dialog(user_id, refresh_all),
            ).props("color=primary dense")

    with ui.tabs().classes("w-full") as tabs:
        dashboard_tab = ui.tab("Tableau", icon="dashboard")
        entry_tab = ui.tab("Saisie", icon="add_circle")
        history_tab = ui.tab("Historique", icon="history")
        recurring_tab = ui.tab("Récurrences", icon="repeat")
        goals_tab = ui.tab("Objectifs", icon="track_changes")
        reconciliation_tab = ui.tab("Conciliation", icon="fact_check")
        organization_tab = ui.tab("Organisation", icon="category")
        export_tab = ui.tab("Exporter", icon="download")

    tab_map = {
        "tableau": dashboard_tab,
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
                    month_state["value"],
                )
                summary = {
                    "expenses": projection["realized"]["expenses"],
                    "incomes": projection["realized"]["incomes"],
                    "difference": projection["realized"]["difference"],
                    "planned_count": projection["upcoming"]["count"],
                }
                goals = goal_progress(
                    user_id,
                    month_state["value"],
                )
                kpis = projection["kpis"]
                predicted_rows = payment_predicted_balance_summary(
                    user_id
                )
                unassigned_count = count_unassigned_confirmed_transactions(
                    user_id
                )

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
                                month_state[
                                    "value"
                                ]
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

                    with ui.element(
                        "div"
                    ).classes(
                        "jf-finance-summary-grid"
                    ):
                        values = (
                            (
                                "Dépenses réalisées",
                                summary[
                                    "expenses"
                                ],
                                "jf-finance-expense",
                            ),
                            (
                                "Revenus réalisés",
                                summary[
                                    "incomes"
                                ],
                                "jf-finance-income",
                            ),
                            (
                                "Différence réalisée",
                                summary[
                                    "difference"
                                ],
                                (
                                    "jf-finance-income"
                                    if summary[
                                        "difference"
                                    ] >= 0
                                    else (
                                        "jf-finance-expense"
                                    )
                                ),
                            ),
                        )

                        for (
                            label,
                            value,
                            css,
                        ) in values:
                            with ui.element(
                                "div"
                            ).classes(
                                "jf-finance-summary"
                            ):
                                ui.label(
                                    label
                                ).classes(
                                    "jf-finance-summary-label"
                                )
                                ui.label(
                                    _money(value)
                                ).classes(
                                    (
                                        "jf-finance-summary-value "
                                        f"{css}"
                                    )
                                )

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
                                    "Dépenses à venir",
                                    projection["upcoming"]["expenses"],
                                    "jf-finance-expense",
                                ),
                                (
                                    "Revenus à venir",
                                    projection["upcoming"]["incomes"],
                                    "jf-finance-income",
                                ),
                                (
                                    "Effet net prévu",
                                    projection["upcoming"]["difference"],
                                    (
                                        "jf-finance-income"
                                        if projection["upcoming"]["difference"] >= 0
                                        else "jf-finance-expense"
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
                                        _balance_money(value)
                                    ).classes(
                                        "jf-finance-summary-value "
                                        + css
                                    )

                        with ui.element("div").classes(
                            "jf-finance-upcoming-grid"
                        ):
                            for transaction_type, title, css in (
                                (
                                    "expense",
                                    "Dépenses prévues",
                                    "jf-finance-expense",
                                ),
                                (
                                    "income",
                                    "Revenus prévus",
                                    "jf-finance-income",
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

                                for row in rows:
                                    with ui.element("div").classes(
                                        "jf-finance-kpi-row"
                                    ):
                                        ui.label(
                                            row["name"]
                                        ).classes(
                                            "jf-finance-kpi-name"
                                        ).tooltip(
                                            row["name"]
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

                    for transaction_type, heading, color_class in (
                        (
                            "expense",
                            "KPI des dépenses",
                            "jf-finance-expense",
                        ),
                        (
                            "income",
                            "KPI des revenus",
                            "jf-finance-income",
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
                            )
                            render_kpi_table(
                                "Par étiquette",
                                type_kpis["tags"],
                                empty_message=(
                                    "Aucune transaction étiquetée."
                                ),
                                color_class=color_class,
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

            def change_month(
                offset,
            ):
                month_state[
                    "value"
                ] = _shift_month(
                    month_state[
                        "value"
                    ],
                    offset,
                )
                render_dashboard.refresh()

            render_dashboard()


        # SAISIE
        with ui.tab_panel(
            entry_tab
        ).classes(
            "px-0"
        ):
            with ui.card().classes(
                "w-full max-w-2xl p-4"
            ):
                ui.label(
                    "Saisie rapide"
                ).classes(
                    "text-xl font-bold"
                )

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
                        {
                            None: "Aucune",
                            **_category_options(
                                user_id
                            ),
                        },
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
                    _tag_options(
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

                with ui.expansion(
                    "Note, statut et conciliation",
                    icon="tune",
                ).classes(
                    "w-full"
                ):
                    status = ui.select(
                        TRANSACTION_STATUSES,
                        value="confirmed",
                        label="Statut de transaction",
                    ).props(
                        "dense outlined options-dense"
                    ).classes(
                        "w-full"
                    )
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
                                category.value
                            ),
                            tag_ids=(
                                tags.value
                                or []
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


        # HISTORIQUE
        with ui.tab_panel(
            history_tab
        ).classes(
            "px-0"
        ):
            with ui.card().classes(
                "w-full p-3"
            ):
                ui.label(
                    "Historique compact"
                ).classes(
                    "text-lg font-bold"
                )

                with ui.expansion(
                    "Filtres",
                    icon="filter_alt",
                ).classes(
                    "w-full"
                ):
                    with ui.element(
                        "div"
                    ).classes(
                        "jf-finance-form-grid"
                    ):
                        start = ui.input(
                            label="Du",
                            value=(
                                month_state[
                                    "value"
                                ].isoformat()
                            ),
                        ).props(
                            "type=date dense outlined"
                        ).classes(
                            "jf-finance-field"
                        )
                        end = ui.input(
                            label="Au",
                            value=(
                                date.today().isoformat()
                            ),
                        ).props(
                            "type=date dense outlined"
                        ).classes(
                            "jf-finance-field"
                        )
                        query = ui.input(
                            label="Recherche"
                        ).props(
                            "dense outlined clearable"
                        ).classes(
                            "jf-finance-field "
                            "jf-finance-description"
                        )

                    with ui.row().classes(
                        "w-full gap-2 flex-wrap"
                    ):
                        history_type = ui.select(
                            {
                                "": "Tous les types",
                                **TRANSACTION_TYPES,
                            },
                            value="",
                            label="Type",
                        ).props(
                            "dense outlined options-dense"
                        ).classes(
                            "min-w-40 grow"
                        )
                        history_status = ui.select(
                            {
                                "": "Tous les statuts",
                                **TRANSACTION_STATUSES,
                            },
                            value="",
                            label="Transaction",
                        ).props(
                            "dense outlined options-dense"
                        ).classes(
                            "min-w-40 grow"
                        )
                        history_reconciliation = ui.select(
                            {
                                "": "Toutes",
                                **RECONCILIATION_STATUSES,
                            },
                            value="",
                            label="Conciliation",
                        ).props(
                            "dense outlined options-dense"
                        ).classes(
                            "min-w-40 grow"
                        )

                    with ui.row().classes(
                        "w-full gap-2 flex-wrap"
                    ):
                        history_category = ui.select(
                            {
                                None: "Toutes",
                                **_category_options(
                                    user_id
                                ),
                            },
                            value=None,
                            label="Catégorie",
                        ).props(
                            "dense outlined clearable "
                            "options-dense"
                        ).classes(
                            "min-w-52 grow"
                        )
                        history_tag = ui.select(
                            {
                                None: "Toutes",
                                **_tag_options(
                                    user_id
                                ),
                            },
                            value=None,
                            label="Étiquette",
                        ).props(
                            "dense outlined clearable "
                            "options-dense"
                        ).classes(
                            "min-w-44 grow"
                        )
                        history_payment = ui.select(
                            {
                                None: "Tous",
                                **_payment_options(
                                    user_id,
                                    include_none=False,
                                ),
                            },
                            value=None,
                            label="Mode de paiement",
                        ).props(
                            "dense outlined clearable "
                            "options-dense"
                        ).classes(
                            "min-w-48 grow"
                        )

                    ui.button(
                        "Appliquer",
                        icon="filter_alt",
                        on_click=lambda: (
                            render_history.refresh()
                        ),
                    ).props(
                        "outline dense color=primary"
                    )

            history_box = ui.column().classes(
                "jf-finance-history-list mt-2"
            )

            def remove_dialog(
                row,
            ):
                with ui.dialog() as dialog:
                    with ui.card().classes(
                        "w-full max-w-md p-4"
                    ):
                        ui.label(
                            "Supprimer cette transaction?"
                        ).classes(
                            "text-lg font-bold"
                        )
                        ui.label(
                            (
                                f"{row['description']} — "
                                f"{_signed(row['amount'], row['transaction_type'])}"
                            )
                        )

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
                            ).props(
                                "flat"
                            )
                            ui.button(
                                "Supprimer",
                                icon="delete",
                                on_click=remove,
                            ).props(
                                "color=negative"
                            )

                dialog.open()

            def confirm_transaction(
                transaction_id,
            ):
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
                    if current_status
                    == "reconciled"
                    else "reconciled"
                )
                reconciliation_date = (
                    date.today()
                    if new_status
                    == "reconciled"
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
                        if new_status
                        == "reconciled"
                        else (
                            "Transaction remise "
                            "à concilier."
                        )
                    ),
                    type="positive",
                )
                refresh_all()

            def render_transaction_row(
                row,
            ):
                with ui.element(
                    "article"
                ).classes(
                    "jf-finance-row"
                ):
                    ui.label(
                        row["description"]
                    ).classes(
                        "jf-finance-main"
                    )

                    meta = []
                    if row[
                        "category_full_name"
                    ]:
                        meta.append(
                            row[
                                "category_full_name"
                            ]
                        )
                    if row[
                        "tag_names"
                    ]:
                        meta.append(
                            " • ".join(
                                row[
                                    "tag_names"
                                ]
                            )
                        )
                    if row.get(
                        "payment_method_name"
                    ):
                        meta.append(
                            row[
                                "payment_method_name"
                            ]
                        )
                    if row[
                        "status"
                    ] == "planned":
                        meta.append(
                            "À confirmer"
                        )
                    meta.append(
                        RECONCILIATION_STATUSES.get(
                            row.get(
                                "reconciliation_status"
                            )
                            or "unreconciled",
                            "À concilier",
                        )
                    )

                    ui.label(
                        " — ".join(
                            meta
                        )
                        or "Sans catégorie"
                    ).classes(
                        "jf-finance-meta"
                    )

                    amount_css = (
                        "jf-finance-expense"
                        if row[
                            "transaction_type"
                        ]
                        == "expense"
                        else "jf-finance-income"
                    )
                    ui.label(
                        _signed(
                            row[
                                "amount"
                            ],
                            row[
                                "transaction_type"
                            ],
                        )
                    ).classes(
                        (
                            "jf-finance-amount "
                            f"{amount_css}"
                        )
                    )

                    with ui.element(
                        "div"
                    ).classes(
                        "jf-finance-actions"
                    ):
                        if row[
                            "status"
                        ] == "planned":
                            ui.button(
                                icon="check",
                                on_click=(
                                    lambda _event=None,
                                    selected_id=row[
                                        "id"
                                    ]:
                                    confirm_transaction(
                                        selected_id
                                    )
                                ),
                            ).props(
                                "flat dense round "
                                "size=sm color=positive"
                            ).tooltip(
                                "Confirmer la transaction"
                            )

                        reconciliation_icon = (
                            "undo"
                            if row.get(
                                "reconciliation_status"
                            )
                            == "reconciled"
                            else "done_all"
                        )
                        reconciliation_tooltip = (
                            "Remettre à concilier"
                            if row.get(
                                "reconciliation_status"
                            )
                            == "reconciled"
                            else "Marquer conciliée"
                        )

                        ui.button(
                            icon=reconciliation_icon,
                            on_click=(
                                lambda _event=None,
                                selected_id=row[
                                    "id"
                                ],
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
                            "flat dense round "
                            "size=sm color=secondary"
                        ).tooltip(
                            reconciliation_tooltip
                        )

                        ui.button(
                            icon="edit",
                            on_click=(
                                lambda _event=None,
                                selected_id=row[
                                    "id"
                                ]:
                                _transaction_dialog(
                                    user_id,
                                    refresh_all,
                                    get_transaction(
                                        user_id,
                                        selected_id,
                                    ),
                                )
                            ),
                        ).props(
                            "flat dense round "
                            "size=sm color=primary"
                        ).tooltip(
                            "Modifier"
                        )

                        ui.button(
                            icon="delete",
                            on_click=(
                                lambda _event=None,
                                selected=row:
                                remove_dialog(
                                    selected
                                )
                            ),
                        ).props(
                            "flat dense round "
                            "size=sm color=negative"
                        ).tooltip(
                            "Supprimer"
                        )

            @ui.refreshable
            def render_history():
                history_box.clear()

                try:
                    rows = list_transactions(
                        user_id,
                        start_date=(
                            start.value
                            or None
                        ),
                        end_date=(
                            end.value
                            or None
                        ),
                        transaction_type=(
                            history_type.value
                            or None
                        ),
                        category_id=(
                            history_category.value
                            or None
                        ),
                        tag_id=(
                            history_tag.value
                            or None
                        ),
                        status=(
                            history_status.value
                            or None
                        ),
                        payment_method_id=(
                            history_payment.value
                            or None
                        ),
                        reconciliation_status=(
                            history_reconciliation.value
                            or None
                        ),
                        query=(
                            query.value
                            or None
                        ),
                    )
                except Exception as error:
                    with history_box:
                        ui.label(
                            str(error)
                        ).classes(
                            "text-negative"
                        )
                    return

                grouped = defaultdict(
                    list
                )
                for row in rows:
                    grouped[
                        row[
                            "transaction_date"
                        ]
                    ].append(
                        row
                    )

                with history_box:
                    if not rows:
                        ui.label(
                            "Aucune transaction."
                        ).classes(
                            "text-sm jf-muted p-3"
                        )
                        return

                    for day in sorted(
                        grouped,
                        reverse=True,
                    ):
                        day_rows = grouped[
                            day
                        ]
                        expenses = [
                            row
                            for row in day_rows
                            if row[
                                "transaction_type"
                            ]
                            == "expense"
                        ]
                        incomes = [
                            row
                            for row in day_rows
                            if row[
                                "transaction_type"
                            ]
                            == "income"
                        ]

                        with ui.element(
                            "section"
                        ).classes(
                            "jf-finance-history-day"
                        ):
                            with ui.element(
                                "div"
                            ).classes(
                                "jf-finance-day"
                            ):
                                ui.label(
                                    day.strftime(
                                        "%d/%m/%Y"
                                    )
                                )
                                ui.label(
                                    (
                                        f"{len(day_rows)} "
                                        "transaction(s)"
                                    )
                                ).classes(
                                    "text-xs jf-muted"
                                )

                            with ui.element(
                                "div"
                            ).classes(
                                "jf-finance-history-columns"
                            ):
                                with ui.element(
                                    "div"
                                ).classes(
                                    "jf-finance-history-column"
                                ):
                                    with ui.element(
                                        "div"
                                    ).classes(
                                        "jf-finance-history-heading"
                                    ):
                                        ui.label(
                                            "Dépenses"
                                        )
                                        ui.label(
                                            _money(
                                                sum(
                                                    Decimal(
                                                        row[
                                                            "amount"
                                                        ]
                                                    )
                                                    for row
                                                    in expenses
                                                )
                                            )
                                        ).classes(
                                            "text-right"
                                        )

                                    if expenses:
                                        for row in expenses:
                                            render_transaction_row(
                                                row
                                            )
                                    else:
                                        ui.label(
                                            "Aucune dépense"
                                        ).classes(
                                            "jf-finance-empty-column"
                                        )

                                with ui.element(
                                    "div"
                                ).classes(
                                    "jf-finance-history-column"
                                ):
                                    with ui.element(
                                        "div"
                                    ).classes(
                                        "jf-finance-history-heading"
                                    ):
                                        ui.label(
                                            "Revenus"
                                        )
                                        ui.label(
                                            _money(
                                                sum(
                                                    Decimal(
                                                        row[
                                                            "amount"
                                                        ]
                                                    )
                                                    for row
                                                    in incomes
                                                )
                                            )
                                        ).classes(
                                            "text-right"
                                        )

                                    if incomes:
                                        for row in incomes:
                                            render_transaction_row(
                                                row
                                            )
                                    else:
                                        ui.label(
                                            "Aucun revenu"
                                        ).classes(
                                            "jf-finance-empty-column"
                                        )

            render_history()


        # RÉCURRENCES
        with ui.tab_panel(recurring_tab).classes("px-0"):
            recurrence_box = ui.column().classes("w-full gap-2")

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
                                )
                                generate_due_recurrences(user_id)
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

            def change_recurrence_state(recurrence_id, value):
                toggle_recurrence(user_id, recurrence_id, value)
                render_recurrences.refresh()

            render_recurrences()

        # OBJECTIFS
        with ui.tab_panel(goals_tab).classes("px-0"):
            goals_box = ui.column().classes("w-full gap-2")

            def goal_dialog(row=None):
                categories = _category_options(user_id)
                tags = _tag_options(user_id)
                with ui.dialog() as dialog:
                    with ui.card().classes("w-full max-w-2xl p-4"):
                        ui.label(
                            "Modifier l’objectif" if row else "Nouvel objectif"
                        ).classes("text-xl font-bold")
                        kind = ui.toggle(
                            {"category": "Catégorie", "tag": "Étiquette"},
                            value=row["goal_type"] if row else "category",
                        ).props("dense spread no-caps").classes("w-full")
                        target = ui.select(
                            categories if not row or row["goal_type"] == "category" else tags,
                            value=(
                                row["category_id"]
                                if row and row["goal_type"] == "category"
                                else (row["tag_id"] if row else None)
                            ),
                            label="Cible",
                        ).props("dense outlined options-dense").classes("w-full")

                        def refresh_targets():
                            target.options = (
                                categories if kind.value == "category" else tags
                            )
                            target.value = None
                            target.update()

                        kind.on_value_change(lambda event: refresh_targets())

                        with ui.element("div").classes("jf-finance-form-grid"):
                            amount = ui.number(
                                label="Objectif mensuel",
                                value=row["monthly_amount"] if row else None,
                                min=.01,
                                step=.01,
                            ).props("dense outlined").classes("jf-finance-field")
                            start_month = ui.input(
                                label="Début",
                                value=(
                                    row["start_month"].strftime("%Y-%m")
                                    if row else date.today().strftime("%Y-%m")
                                ),
                            ).props("type=month dense outlined").classes(
                                "jf-finance-field"
                            )
                            end_month = ui.input(
                                label="Fin facultative",
                                value=(
                                    row["end_month"].strftime("%Y-%m")
                                    if row and row["end_month"] else ""
                                ),
                            ).props("type=month dense outlined").classes(
                                "jf-finance-field jf-finance-description"
                            )
                        carry = ui.select(
                            CARRY_POLICIES,
                            value=row["carry_policy"] if row else "none",
                            label="Report au mois suivant",
                        ).props("dense outlined options-dense").classes("w-full")
                        maximum = ui.number(
                            label="Plafond de report facultatif",
                            value=row["max_carry"] if row else None,
                            min=0,
                            step=.01,
                        ).props("dense outlined clearable").classes("w-full")
                        ui.label(
                            "Les mois déjà créés conservent leur historique."
                        ).classes("text-xs jf-muted")

                        def save_goal_now():
                            try:
                                save_goal(
                                    user_id=user_id,
                                    goal_id=row["id"] if row else None,
                                    goal_type=kind.value,
                                    target_id=target.value,
                                    monthly_amount=amount.value,
                                    carry_policy=carry.value,
                                    start_month=start_month.value,
                                    end_month=end_month.value or None,
                                    max_carry=maximum.value,
                                )
                            except Exception as error:
                                ui.notify(str(error), type="warning")
                                return
                            dialog.close()
                            ui.notify("Objectif enregistré.", type="positive")
                            refresh_all()

                        with ui.row().classes("w-full justify-end gap-2"):
                            ui.button(
                                "Annuler", on_click=dialog.close
                            ).props("flat")
                            ui.button(
                                "Enregistrer", icon="save", on_click=save_goal_now
                            ).props("color=primary")
                dialog.open()

            @ui.refreshable
            def render_goals():
                goals_box.clear()
                rows = list_goals(user_id)
                with goals_box:
                    with ui.row().classes(
                        "w-full items-center justify-between"
                    ):
                        ui.label("Objectifs mensuels").classes(
                            "text-xl font-bold"
                        )
                        ui.button(
                            "Ajouter",
                            icon="add",
                            on_click=lambda: goal_dialog(),
                        ).props("color=primary dense")
                    if not rows:
                        ui.label("Aucun objectif.").classes(
                            "text-sm jf-muted"
                        )
                    for row in rows:
                        with ui.element("div").classes("jf-finance-card"):
                            with ui.row().classes(
                                "w-full items-center justify-between gap-2"
                            ):
                                with ui.column().classes("gap-0 min-w-0"):
                                    ui.label(row["target_name"]).classes(
                                        "text-sm font-bold"
                                    )
                                    ui.label(
                                        f"{_money(row['monthly_amount'])} / mois "
                                        f"— {CARRY_POLICIES[row['carry_policy']]}"
                                    ).classes("text-xs jf-muted")
                                with ui.row().classes("gap-1"):
                                    ui.switch(
                                        value=row["is_active"],
                                        on_change=(
                                            lambda event,
                                            selected=row["id"]:
                                            change_goal_state(
                                                selected, event.value
                                            )
                                        ),
                                    ).props("dense")
                                    ui.button(
                                        icon="edit",
                                        on_click=(
                                            lambda _event=None,
                                            selected=row:
                                            goal_dialog(selected)
                                        ),
                                    ).props(
                                        "flat dense round size=sm color=primary"
                                    )

            def change_goal_state(goal_id, value):
                toggle_goal(user_id, goal_id, value)
                refresh_all()

            render_goals()

        # CONCILIATION
        with ui.tab_panel(reconciliation_tab).classes("px-0"):
            payment_options = _payment_options(
                user_id,
                include_none=False,
            )
            first_payment_id = (
                next(iter(payment_options))
                if payment_options
                else None
            )
            reconciliation_selected = set()
            reconciliation_rows_by_id = {}
            unassigned_selected = set()

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

                    ui.button(
                        "Actualiser",
                        icon="refresh",
                        on_click=lambda: (
                            refresh_reconciliation_screen()
                        ),
                    ).props("outline dense color=primary")

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

                include_opening_balance = ui.checkbox(
                    "Inclure l’ajustement initial",
                    value=False,
                ).classes("text-sm")
                opening_balance_label = ui.label("").classes(
                    "text-xs jf-muted"
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

                if include_opening_balance.value:
                    selected_method = int(
                        reconciliation_payment.value or 0
                    )
                    for summary_row in (
                        payment_predicted_balance_summary(user_id)
                    ):
                        if (
                            int(summary_row["payment_method_id"])
                            == selected_method
                        ):
                            total += Decimal(
                                summary_row["opening_balance_pending"]
                            )
                            break
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
                reconciliation_rows_by_id.clear()
                selected_id = reconciliation_payment.value

                with reconciliation_transactions_box:
                    if not selected_id:
                        ui.label(
                            "Aucun mode de paiement sélectionné."
                        ).classes("text-sm jf-muted")
                        return

                    try:
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

                    valid_ids = {
                        int(row["id"])
                        for row in rows
                    }
                    reconciliation_selected.intersection_update(
                        valid_ids
                    )

                    if not rows:
                        ui.label(
                            "Aucune transaction confirmée à concilier."
                        ).classes("text-sm jf-muted p-3")
                        return

                    with ui.row().classes(
                        "w-full items-center justify-between gap-2"
                    ):
                        ui.label(
                            f"{len(rows)} transaction(s)"
                        ).classes("text-xs jf-muted")

                        def select_all_rows():
                            reconciliation_selected.update(valid_ids)
                            render_reconciliation_transactions.refresh()
                            render_reconciliation_selection.refresh()

                        def clear_all_rows():
                            reconciliation_selected.clear()
                            render_reconciliation_transactions.refresh()
                            render_reconciliation_selection.refresh()

                        with ui.row().classes("gap-1"):
                            ui.button(
                                "Tout",
                                on_click=select_all_rows,
                            ).props("flat dense color=primary")
                            ui.button(
                                "Aucun",
                                on_click=clear_all_rows,
                            ).props("flat dense color=primary")

                    for row in rows:
                        transaction_id = int(row["id"])
                        reconciliation_rows_by_id[
                            transaction_id
                        ] = row

                        with ui.element("div").classes(
                            "jf-finance-reconcile-row"
                        ):
                            ui.checkbox(
                                value=(
                                    transaction_id
                                    in reconciliation_selected
                                ),
                                on_change=(
                                    lambda event,
                                    selected=transaction_id:
                                    toggle_reconciliation_selection(
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

                            with ui.column().classes(
                                "gap-0 min-w-0"
                            ):
                                ui.label(
                                    row["description"]
                                ).classes(
                                    "jf-finance-reconcile-description"
                                )
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
                                    row["amount"],
                                    row["transaction_type"],
                                )
                            ).classes(
                                "jf-finance-reconcile-amount "
                                + amount_class
                            )

            @ui.refreshable
            def render_reconciliation_selection():
                reconciliation_selection_box.clear()
                total = selected_reconciliation_total()
                current_balance = Decimal("0.00")
                selected_id = reconciliation_payment.value
                selected_summary = next(
                    (
                        row
                        for row in payment_predicted_balance_summary(
                            user_id
                        )
                        if int(row["payment_method_id"])
                        == int(selected_id or 0)
                    ),
                    None,
                )
                if selected_summary:
                    current_balance = Decimal(
                        selected_summary["current_balance"]
                    )

                remaining = current_balance - total
                statement_value = (
                    Decimal(str(statement_balance.value))
                    if statement_balance.value not in (None, "")
                    else None
                )
                difference = (
                    statement_value - total
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
                            ui.label("Total sélectionné")
                            ui.label(_balance_money(total))

                        with ui.element("div").classes(
                            "jf-finance-balance-line"
                        ):
                            ui.label("Solde non concilié restant")
                            ui.label(_balance_money(remaining))

                        if difference is not None:
                            with ui.element("div").classes(
                                "jf-finance-balance-line"
                            ):
                                ui.label("Différence avec le relevé")
                                ui.label(_balance_money(difference)).classes(
                                    (
                                        "text-positive"
                                        if abs(difference) < Decimal(".01")
                                        else "text-negative"
                                    )
                                )

                        def finalize_now():
                            try:
                                result = create_reconciliation_session(
                                    user_id=user_id,
                                    payment_method_id=(
                                        reconciliation_payment.value
                                    ),
                                    transaction_ids=list(
                                        reconciliation_selected
                                    ),
                                    statement_date=statement_date.value,
                                    statement_balance=(
                                        statement_balance.value
                                    ),
                                    due_date=due_date.value or None,
                                    reconciliation_date=(
                                        reconciliation_date_input.value
                                    ),
                                    note=reconciliation_note.value,
                                    include_opening_balance=(
                                        include_opening_balance.value
                                    ),
                                )
                            except Exception as error:
                                ui.notify(
                                    str(error),
                                    type="warning",
                                )
                                return

                            reconciliation_selected.clear()
                            include_opening_balance.value = False
                            reconciliation_note.value = ""
                            ui.notify(
                                (
                                    "Conciliation enregistrée : "
                                    f"{result['transaction_count']} "
                                    "transaction(s)."
                                ),
                                type="positive",
                            )
                            refresh_reconciliation_screen()
                            refresh_all()

                        def request_finalize():
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
                                        "w-full max-w-md p-4"
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
                                            "La différence sera conservée "
                                            "dans l’historique."
                                        ).classes("text-sm jf-muted")
                                        with ui.row().classes(
                                            "w-full justify-end gap-2"
                                        ):
                                            ui.button(
                                                "Annuler",
                                                on_click=(
                                                    warning_dialog.close
                                                ),
                                            ).props("flat")
                                            ui.button(
                                                "Continuer",
                                                icon="warning",
                                                on_click=lambda: (
                                                    warning_dialog.close(),
                                                    finalize_now(),
                                                ),
                                            ).props("color=negative")
                                warning_dialog.open()
                                return

                            finalize_now()

                        ui.button(
                            "Finaliser la conciliation",
                            icon="fact_check",
                            on_click=request_finalize,
                        ).props(
                            "color=primary"
                        ).classes("w-full mt-2")

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
                                ("Total concilié", session["selected_total"]),
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

            def refresh_reconciliation_screen():
                reconciliation_selected.clear()
                render_reconciliation_balance.refresh()
                render_reconciliation_transactions.refresh()
                render_reconciliation_selection.refresh()
                render_sessions.refresh()
                render_unassigned.refresh()

            reconciliation_payment.on_value_change(
                lambda event: refresh_reconciliation_screen()
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

            render_reconciliation_balance()
            render_reconciliation_transactions()
            render_reconciliation_selection()
            render_sessions()

        # ORGANISATION
        with ui.tab_panel(organization_tab).classes("px-0"):
            with ui.tabs().classes("w-full") as organization_tabs:
                categories_tab = ui.tab("Catégories")
                tags_tab = ui.tab("Étiquettes")
                payment_methods_tab = ui.tab(
                    "Modes de paiement"
                )

            with ui.tab_panels(
                organization_tabs,
                value=categories_tab,
            ).classes("w-full bg-transparent"):
                with ui.tab_panel(categories_tab).classes("px-0"):
                    category_box = ui.column().classes("w-full gap-2")

                    def category_dialog(row=None):
                        roots = {None: "Aucune — catégorie principale"}
                        for candidate in list_categories(user_id):
                            if candidate["parent_id"] is None and (
                                not row or candidate["id"] != row["id"]
                            ):
                                roots[int(candidate["id"])] = candidate["name"]

                        with ui.dialog() as dialog:
                            with ui.card().classes("w-full max-w-xl p-4"):
                                ui.label(
                                    "Modifier la catégorie"
                                    if row else "Nouvelle catégorie"
                                ).classes("text-xl font-bold")
                                name = ui.input(
                                    label="Nom",
                                    value=row["name"] if row else "",
                                ).props("dense outlined maxlength=100").classes(
                                    "w-full"
                                )
                                parent = ui.select(
                                    roots,
                                    value=row["parent_id"] if row else None,
                                    label="Catégorie parente",
                                ).props(
                                    "dense outlined clearable options-dense"
                                ).classes("w-full")
                                category_type = ui.select(
                                    {
                                        "expense": "Dépenses",
                                        "income": "Revenus",
                                        "both": "Dépenses et revenus",
                                    },
                                    value=row["category_type"] if row else "both",
                                    label="Utilisation",
                                ).props("dense outlined options-dense").classes(
                                    "w-full"
                                )

                                def save_category_now():
                                    try:
                                        save_category(
                                            user_id=user_id,
                                            category_id=row["id"] if row else None,
                                            name=name.value,
                                            parent_id=parent.value,
                                            category_type=category_type.value,
                                        )
                                    except Exception as error:
                                        ui.notify(str(error), type="warning")
                                        return
                                    dialog.close()
                                    ui.notify("Catégorie enregistrée.", type="positive")
                                    refresh_all()

                                with ui.row().classes(
                                    "w-full justify-end gap-2"
                                ):
                                    ui.button(
                                        "Annuler", on_click=dialog.close
                                    ).props("flat")
                                    ui.button(
                                        "Enregistrer",
                                        icon="save",
                                        on_click=save_category_now,
                                    ).props("color=primary")
                        dialog.open()

                    @ui.refreshable
                    def render_categories():
                        category_box.clear()
                        rows = list_categories(
                            user_id, include_inactive=True
                        )
                        with category_box:
                            with ui.row().classes(
                                "w-full items-center justify-between"
                            ):
                                ui.label(
                                    "Catégories et sous-catégories"
                                ).classes("text-xl font-bold")
                                ui.button(
                                    "Ajouter",
                                    icon="add",
                                    on_click=lambda: category_dialog(),
                                ).props("color=primary dense")
                            for row in rows:
                                with ui.element("div").classes("jf-finance-card"):
                                    with ui.row().classes(
                                        "w-full items-center justify-between gap-2"
                                    ):
                                        ui.label(row["full_name"]).classes(
                                            "text-sm font-bold"
                                        )
                                        with ui.row().classes("gap-1"):
                                            ui.switch(
                                                value=row["is_active"],
                                                on_change=(
                                                    lambda event,
                                                    selected=row["id"]:
                                                    change_category_state(
                                                        selected, event.value
                                                    )
                                                ),
                                            ).props("dense")
                                            ui.button(
                                                icon="edit",
                                                on_click=(
                                                    lambda _event=None,
                                                    selected=row:
                                                    category_dialog(selected)
                                                ),
                                            ).props(
                                                "flat dense round size=sm color=primary"
                                            )

                    def change_category_state(category_id, value):
                        toggle_category(user_id, category_id, value)
                        refresh_all()

                    render_categories()

                with ui.tab_panel(tags_tab).classes("px-0"):
                    tag_box = ui.column().classes("w-full gap-2")

                    def tag_dialog(row=None):
                        with ui.dialog() as dialog:
                            with ui.card().classes("w-full max-w-md p-4"):
                                ui.label(
                                    "Modifier l’étiquette"
                                    if row else "Nouvelle étiquette"
                                ).classes("text-xl font-bold")
                                name = ui.input(
                                    label="Nom",
                                    value=row["name"] if row else "",
                                ).props("dense outlined maxlength=80").classes(
                                    "w-full"
                                )

                                def save_tag_now():
                                    try:
                                        save_tag(
                                            user_id=user_id,
                                            tag_id=row["id"] if row else None,
                                            name=name.value,
                                        )
                                    except Exception as error:
                                        ui.notify(str(error), type="warning")
                                        return
                                    dialog.close()
                                    ui.notify("Étiquette enregistrée.", type="positive")
                                    refresh_all()

                                with ui.row().classes(
                                    "w-full justify-end gap-2"
                                ):
                                    ui.button(
                                        "Annuler", on_click=dialog.close
                                    ).props("flat")
                                    ui.button(
                                        "Enregistrer",
                                        icon="save",
                                        on_click=save_tag_now,
                                    ).props("color=primary")
                        dialog.open()

                    @ui.refreshable
                    def render_tags():
                        tag_box.clear()
                        rows = list_tags(user_id, include_inactive=True)
                        with tag_box:
                            with ui.row().classes(
                                "w-full items-center justify-between"
                            ):
                                ui.label("Étiquettes").classes(
                                    "text-xl font-bold"
                                )
                                ui.button(
                                    "Ajouter",
                                    icon="add",
                                    on_click=lambda: tag_dialog(),
                                ).props("color=primary dense")
                            for row in rows:
                                with ui.element("div").classes("jf-finance-card"):
                                    with ui.row().classes(
                                        "w-full items-center justify-between gap-2"
                                    ):
                                        ui.label(row["name"]).classes(
                                            "text-sm font-bold"
                                        )
                                        with ui.row().classes("gap-1"):
                                            ui.switch(
                                                value=row["is_active"],
                                                on_change=(
                                                    lambda event,
                                                    selected=row["id"]:
                                                    change_tag_state(
                                                        selected, event.value
                                                    )
                                                ),
                                            ).props("dense")
                                            ui.button(
                                                icon="edit",
                                                on_click=(
                                                    lambda _event=None,
                                                    selected=row:
                                                    tag_dialog(selected)
                                                ),
                                            ).props(
                                                "flat dense round size=sm color=primary"
                                            )

                    def change_tag_state(tag_id, value):
                        toggle_tag(user_id, tag_id, value)
                        refresh_all()

                    render_tags()

                with ui.tab_panel(
                    payment_methods_tab
                ).classes(
                    "px-0"
                ):
                    payment_box = ui.column().classes(
                        "w-full gap-2"
                    )

                    def payment_method_dialog(
                        row=None,
                    ):
                        with ui.dialog() as dialog:
                            with ui.card().classes(
                                "w-full max-w-2xl p-4"
                            ):
                                ui.label(
                                    (
                                        "Modifier le mode de paiement"
                                        if row
                                        else "Nouveau mode de paiement"
                                    )
                                ).classes("text-xl font-bold")

                                name = ui.input(
                                    label="Nom",
                                    value=row["name"] if row else "",
                                ).props(
                                    "dense outlined maxlength=100"
                                ).classes("w-full")

                                method_type = ui.select(
                                    PAYMENT_METHOD_TYPES,
                                    value=(
                                        row["method_type"]
                                        if row
                                        else "credit_card"
                                    ),
                                    label="Type",
                                ).props(
                                    "dense outlined options-dense"
                                ).classes("w-full")

                                with ui.element("div").classes(
                                    "jf-finance-form-grid"
                                ):
                                    statement_day = ui.number(
                                        label="Fermeture habituelle — jour",
                                        value=(
                                            row["statement_day"]
                                            if row
                                            else None
                                        ),
                                        min=1,
                                        max=31,
                                        step=1,
                                    ).props(
                                        "dense outlined clearable"
                                    ).classes("jf-finance-field")

                                    payment_day = ui.number(
                                        label="Paiement habituel — jour",
                                        value=(
                                            row["payment_day"]
                                            if row
                                            else None
                                        ),
                                        min=1,
                                        max=31,
                                        step=1,
                                    ).props(
                                        "dense outlined clearable"
                                    ).classes("jf-finance-field")

                                    opening_date = ui.input(
                                        label="Date du solde initial",
                                        value=(
                                            row[
                                                "opening_balance_date"
                                            ].isoformat()
                                            if row
                                            and row[
                                                "opening_balance_date"
                                            ]
                                            else ""
                                        ),
                                    ).props(
                                        "type=date dense outlined"
                                    ).classes(
                                        "jf-finance-field "
                                        "jf-finance-description"
                                    )

                                opening_balance = ui.number(
                                    label="Solde initial ou ajustement",
                                    value=(
                                        row["opening_balance"]
                                        if row
                                        else 0
                                    ),
                                    step=.01,
                                ).props(
                                    "dense outlined"
                                ).classes("w-full")

                                ui.label(
                                    "Le solde initial reste dans le solde "
                                    "prévu jusqu’à son inclusion dans une "
                                    "séance de conciliation."
                                ).classes("text-xs jf-muted")

                                note = ui.textarea(
                                    label="Note facultative",
                                    value=row["note"] if row else "",
                                ).props(
                                    "dense outlined autogrow maxlength=1000"
                                ).classes("w-full")

                                def save_payment_now():
                                    try:
                                        save_payment_method(
                                            user_id=user_id,
                                            payment_method_id=(
                                                row["id"]
                                                if row
                                                else None
                                            ),
                                            name=name.value,
                                            method_type=method_type.value,
                                            statement_day=(
                                                statement_day.value
                                            ),
                                            payment_day=payment_day.value,
                                            opening_balance=(
                                                opening_balance.value
                                            ),
                                            opening_balance_date=(
                                                opening_date.value or None
                                            ),
                                            note=note.value,
                                        )
                                    except Exception as error:
                                        ui.notify(
                                            str(error),
                                            type="warning",
                                        )
                                        return

                                    dialog.close()
                                    ui.notify(
                                        "Mode de paiement enregistré.",
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
                                        "Enregistrer",
                                        icon="save",
                                        on_click=save_payment_now,
                                    ).props("color=primary")

                        dialog.open()

                    def change_payment_state(
                        payment_method_id,
                        value,
                    ):
                        try:
                            toggle_payment_method(
                                user_id,
                                payment_method_id,
                                value,
                            )
                        except Exception as error:
                            ui.notify(
                                str(error),
                                type="warning",
                            )
                            return

                        refresh_all()

                    def change_payment_order(
                        payment_method_id,
                        direction,
                    ):
                        try:
                            move_payment_method(
                                user_id,
                                payment_method_id,
                                direction,
                            )
                        except Exception as error:
                            ui.notify(
                                str(error),
                                type="warning",
                            )
                            return

                        render_payment_methods.refresh()

                    @ui.refreshable
                    def render_payment_methods():
                        payment_box.clear()
                        rows = list_payment_methods(
                            user_id,
                            include_inactive=True,
                        )

                        with payment_box:
                            with ui.row().classes(
                                "w-full items-center "
                                "justify-between gap-2"
                            ):
                                with ui.column().classes(
                                    "gap-0"
                                ):
                                    ui.label(
                                        "Modes de paiement"
                                    ).classes(
                                        "text-xl font-bold"
                                    )
                                    ui.label(
                                        (
                                            "Une transaction utilise "
                                            "un seul mode de paiement."
                                        )
                                    ).classes(
                                        "text-xs jf-muted"
                                    )

                                ui.button(
                                    "Ajouter",
                                    icon="add",
                                    on_click=lambda: (
                                        payment_method_dialog()
                                    ),
                                ).props(
                                    "color=primary dense"
                                )

                            for row in rows:
                                with ui.element(
                                    "div"
                                ).classes(
                                    "jf-finance-card"
                                ):
                                    with ui.element(
                                        "div"
                                    ).classes(
                                        "jf-finance-payment-row"
                                    ):
                                        with ui.element(
                                            "div"
                                        ).classes(
                                            "jf-finance-payment-order"
                                        ):
                                            ui.button(
                                                icon="keyboard_arrow_up",
                                                on_click=(
                                                    lambda _event=None,
                                                    selected=row["id"]:
                                                    change_payment_order(
                                                        selected,
                                                        "up",
                                                    )
                                                ),
                                            ).props(
                                                "flat dense round "
                                                "size=sm color=primary"
                                            ).tooltip(
                                                "Monter"
                                            )
                                            ui.button(
                                                icon="keyboard_arrow_down",
                                                on_click=(
                                                    lambda _event=None,
                                                    selected=row["id"]:
                                                    change_payment_order(
                                                        selected,
                                                        "down",
                                                    )
                                                ),
                                            ).props(
                                                "flat dense round "
                                                "size=sm color=primary"
                                            ).tooltip(
                                                "Descendre"
                                            )

                                        with ui.column().classes(
                                            "gap-0 min-w-0"
                                        ):
                                            ui.label(
                                                row["name"]
                                            ).classes(
                                                "text-sm font-bold"
                                            )
                                            ui.label(
                                                (
                                                    PAYMENT_METHOD_TYPES.get(
                                                        row["method_type"],
                                                        "Autre",
                                                    )
                                                    + " — "
                                                    + f"{row['transaction_count']} "
                                                    "transaction(s)"
                                                )
                                            ).classes(
                                                "text-xs jf-muted"
                                            )
                                            schedule_parts = []
                                            if row["statement_day"]:
                                                schedule_parts.append(
                                                    "relevé vers le "
                                                    + str(row["statement_day"])
                                                )
                                            if row["payment_day"]:
                                                schedule_parts.append(
                                                    "paiement vers le "
                                                    + str(row["payment_day"])
                                                )
                                            if schedule_parts:
                                                ui.label(
                                                    " — ".join(
                                                        schedule_parts
                                                    )
                                                ).classes(
                                                    "text-xs jf-muted"
                                                )
                                            if Decimal(
                                                row["opening_balance"]
                                            ) != 0:
                                                ui.label(
                                                    "Solde initial : "
                                                    + _balance_money(
                                                        row[
                                                            "opening_balance"
                                                        ]
                                                    )
                                                    + (
                                                        " — concilié"
                                                        if row[
                                                            "opening_balance_reconciled"
                                                        ]
                                                        else " — à concilier"
                                                    )
                                                ).classes(
                                                    "text-xs jf-muted"
                                                )

                                        with ui.row().classes(
                                            "gap-1 shrink-0"
                                        ):
                                            ui.switch(
                                                value=row[
                                                    "is_active"
                                                ],
                                                on_change=(
                                                    lambda event,
                                                    selected=row["id"]:
                                                    change_payment_state(
                                                        selected,
                                                        event.value,
                                                    )
                                                ),
                                            ).props(
                                                "dense"
                                            )
                                            ui.button(
                                                icon="edit",
                                                on_click=(
                                                    lambda _event=None,
                                                    selected=row:
                                                    payment_method_dialog(
                                                        selected
                                                    )
                                                ),
                                            ).props(
                                                "flat dense round "
                                                "size=sm color=primary"
                                            ).tooltip(
                                                "Modifier"
                                            )

                    render_payment_methods()

        # IMPORTER ET EXPORTER
        with ui.tab_panel(export_tab).classes("px-0"):
            with ui.card().classes("w-full max-w-3xl p-4"):
                ui.label("Importer des transactions").classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "Formats reconnus : CSV de Spendee, CSV de JF Apps "
                    "et sauvegarde JSON de JF Apps. Une prévisualisation "
                    "est toujours affichée avant l’importation."
                ).classes("text-sm jf-muted")

                async def receive_import(event):
                    try:
                        text = await event.file.text()
                        filename = getattr(event.file, "name", "import.csv")
                        preview = prepare_finance_import(
                            user_id,
                            filename,
                            text,
                        )
                    except Exception as error:
                        ui.notify(str(error), type="negative")
                        return

                    with ui.dialog() as dialog:
                        with ui.card().classes("w-full max-w-4xl p-4"):
                            ui.label("Prévisualisation de l’importation").classes(
                                "text-xl font-bold"
                            )
                            ui.label(
                                f"Format reconnu : {preview['format']}"
                            ).classes("text-sm jf-muted")

                            with ui.element("div").classes(
                                "jf-finance-summary-grid mt-2"
                            ):
                                for label, value in (
                                    ("Valides", preview["valid_rows"]),
                                    ("Déjà importées", preview["already_imported"]),
                                    ("Doublons possibles", preview["possible_duplicates"]),
                                ):
                                    with ui.element("div").classes(
                                        "jf-finance-summary"
                                    ):
                                        ui.label(label).classes(
                                            "jf-finance-summary-label"
                                        )
                                        ui.label(str(value)).classes(
                                            "jf-finance-summary-value"
                                        )

                            ui.label(
                                (
                                    "Catégories détectées : "
                                    f"{len(preview['categories'])} — "
                                    "Étiquettes détectées : "
                                    f"{len(preview['tags'])} — "
                                    "Modes de paiement détectés : "
                                    f"{len(preview['payment_methods'])}"
                                )
                            ).classes(
                                "text-xs jf-muted"
                            )

                            skip_possible = ui.checkbox(
                                "Ignorer les transactions identiques déjà présentes",
                                value=True,
                            ).classes("mt-2")

                            if preview["errors"]:
                                with ui.expansion(
                                    f"Erreurs ignorées ({len(preview['errors'])})",
                                    icon="warning",
                                ).classes("w-full"):
                                    for message in preview["errors"][:30]:
                                        ui.label(message).classes(
                                            "text-xs text-negative"
                                        )

                            ui.label("Aperçu").classes("font-bold mt-2")
                            with ui.column().classes("w-full gap-1"):
                                visible_rows = [
                                    row for row in preview["rows"]
                                    if row.get("duplicate_reason") != "already_imported"
                                ][:8]
                                for row in visible_rows:
                                    with ui.element("div").classes(
                                        "jf-finance-card"
                                    ):
                                        with ui.row().classes(
                                            "w-full items-center justify-between gap-2"
                                        ):
                                            with ui.column().classes(
                                                "gap-0 min-w-0"
                                            ):
                                                ui.label(row["description"]).classes(
                                                    "text-sm font-bold"
                                                )
                                                details = [
                                                    row["transaction_date"].strftime("%d/%m/%Y"),
                                                    row.get("category_name") or "Sans catégorie",
                                                ]
                                                if row.get("tag_names"):
                                                    details.append(
                                                        " • ".join(row["tag_names"])
                                                    )
                                                if row.get(
                                                    "payment_method_name"
                                                ):
                                                    details.append(
                                                        row[
                                                            "payment_method_name"
                                                        ]
                                                    )
                                                ui.label(" — ".join(details)).classes(
                                                    "text-xs jf-muted"
                                                )
                                            css = (
                                                "jf-finance-expense"
                                                if row["transaction_type"] == "expense"
                                                else "jf-finance-income"
                                            )
                                            ui.label(
                                                _signed(
                                                    row["amount"],
                                                    row["transaction_type"],
                                                )
                                            ).classes(f"text-sm font-bold {css}")

                            def confirm_import():
                                try:
                                    result = import_finance_rows(
                                        user_id,
                                        preview["rows"],
                                        skip_possible_duplicates=(
                                            skip_possible.value
                                        ),
                                    )
                                except Exception as error:
                                    ui.notify(str(error), type="negative")
                                    return

                                dialog.close()
                                message = (
                                    f"Importation terminée : {result['imported']} ajoutée(s), "
                                    f"{result['skipped']} ignorée(s), "
                                    f"{result['categories_created']} catégorie(s) créée(s), "
                                    f"{result['tags_created']} étiquette(s) créée(s), "
                                    f"{result['payment_methods_created']} "
                                    "mode(s) de paiement créé(s)."
                                )
                                ui.notify(message, type="positive", timeout=10000)
                                if result["failures"]:
                                    ui.notify(
                                        f"{len(result['failures'])} ligne(s) n’ont pas pu être importées.",
                                        type="warning",
                                        timeout=10000,
                                    )
                                refresh_all()

                            with ui.row().classes(
                                "w-full justify-end gap-2 mt-3"
                            ):
                                ui.button(
                                    "Annuler",
                                    on_click=dialog.close,
                                ).props("flat")
                                ui.button(
                                    "Importer",
                                    icon="upload",
                                    on_click=confirm_import,
                                ).props("color=primary")
                    dialog.open()

                ui.upload(
                    label="Choisir un fichier CSV ou JSON",
                    on_upload=receive_import,
                    auto_upload=True,
                    max_files=1,
                ).props(
                    "accept=.csv,.json,text/csv,application/json"
                ).classes("w-full mt-3")

            with ui.card().classes("w-full max-w-3xl p-4 mt-3"):
                ui.label("Exporter les données").classes("text-xl font-bold")
                ui.label(
                    "Le CSV convient à Excel. Le JSON constitue "
                    "une sauvegarde complète de sécurité. Les modes "
                    "de paiement, les statuts de conciliation et les clés "
                    "d’importation sont conservés."
                ).classes("text-sm jf-muted")

                def do_export(kind):
                    try:
                        csv_bytes, json_bytes = export_finances(user_id)
                        content = csv_bytes if kind == "csv" else json_bytes
                        filename = f"finances_{date.today().isoformat()}.{kind}"
                        path = Path(tempfile.gettempdir()) / (
                            f"{user_id}_{filename}"
                        )
                        path.write_bytes(content)
                        ui.download(str(path), filename=filename)
                    except Exception as error:
                        ui.notify(str(error), type="negative")

                with ui.row().classes("gap-2 flex-wrap"):
                    ui.button(
                        "Exporter CSV",
                        icon="table_view",
                        on_click=lambda: do_export("csv"),
                    ).props("outline color=primary")
                    ui.button(
                        "Exporter JSON",
                        icon="data_object",
                        on_click=lambda: do_export("json"),
                    ).props("outline color=primary")

    def refresh_all():
        # Actualiser les listes déjà visibles après l’ajout ou
        # la modification d’une catégorie, d’une étiquette ou
        # d’un mode de paiement.
        category.options = {
            None: "Aucune",
            **_category_options(
                user_id
            ),
        }
        category.update()

        tags.options = _tag_options(
            user_id
        )
        tags.update()

        payment_method.options = (
            _payment_options(
                user_id
            )
        )
        payment_method.update()

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

        render_dashboard.refresh()
        render_history.refresh()
        render_recurrences.refresh()
        render_goals.refresh()
        render_categories.refresh()
        render_tags.refresh()
        render_payment_methods.refresh()

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

        refresh_reconciliation_screen()
