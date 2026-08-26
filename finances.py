from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import json
import tempfile

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
    budget_summary,
    budget_capacity_summary,
    bulk_assign_payment_method,
    cancel_reconciliation_session,
    count_unassigned_confirmed_transactions,
    create_reconciliation_session,
    dashboard_month_projection,
    dashboard_summary,
    delete_recurrence,
    delete_installment_plan,
    delete_transaction,
    ensure_default_finance_categories,
    ensure_default_finance_payment_methods,
    export_finances,
    generate_due_recurrences,
    get_or_create_finance_category,
    get_or_create_finance_tag,
    get_card_payment_transfer,
    get_installment_plan,
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
    list_payment_methods,
    list_reconciliation_sessions,
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
    save_card_payment_transfer,
    save_category,
    save_goal,
    save_installment_plan,
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


FINANCE_CSS = r"""
.jf-finance-main-tabs {
    width: 100%;
    overflow: hidden;
    border-bottom: 1px solid var(--jf-border);
}
.jf-finance-main-tabs .q-tabs__content {
    display: flex;
    flex-wrap: nowrap;
    justify-content: flex-start;
    overflow-x: auto;
    overflow-y: hidden;
    scroll-behavior: smooth;
    scrollbar-width: thin;
    scrollbar-color:
        color-mix(in srgb, var(--jf-blue) 36%, transparent)
        transparent;
}
.jf-finance-main-tabs .q-tabs__content::-webkit-scrollbar {
    height: 4px;
}
.jf-finance-main-tabs .q-tabs__content::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: color-mix(
        in srgb,
        var(--jf-blue) 36%,
        transparent
    );
}
.jf-finance-main-tabs .q-tab {
    flex: 0 0 auto;
    min-width: max-content;
    padding-inline: .72rem;
}
.jf-finance-main-tabs .q-tab__content {
    min-width: max-content;
}
.jf-finance-main-tabs .q-tab__label {
    overflow: visible;
    white-space: nowrap;
    text-overflow: clip;
}
.jf-finance-main-tabs .q-tabs__arrow {
    color: var(--jf-navy);
}
.body--dark .jf-finance-main-tabs .q-tabs__arrow {
    color: #dceaf6;
}

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
.jf-finance-kpi-link {
    justify-self: start;
    min-width: 0;
    max-width: 100%;
    padding: 0;
    min-height: 1.8rem;
    color: var(--jf-blue);
    font-size: .75rem;
    font-weight: 800;
    text-decoration: underline;
    text-decoration-thickness: 1px;
    text-underline-offset: 2px;
}
.jf-finance-kpi-link .q-btn__content {
    min-width: 0;
    max-width: 100%;
    justify-content: flex-start;
}
.jf-finance-kpi-link .block {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.jf-finance-kpi-detail-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: .45rem;
    width: 100%;
}
.jf-finance-kpi-detail-list {
    display: flex;
    flex-direction: column;
    gap: .35rem;
    width: 100%;
}
.jf-finance-kpi-detail-row {
    display: grid;
    grid-template-columns: 5.2rem minmax(0, 1fr) auto auto;
    align-items: center;
    gap: .45rem;
    width: 100%;
    padding: .42rem .48rem;
    border: 1px solid var(--jf-border);
    border-radius: 9px;
    background: var(--jf-surface);
}
.jf-finance-kpi-detail-date {
    color: var(--jf-muted);
    font-size: .68rem;
    white-space: nowrap;
}
.jf-finance-kpi-detail-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: .78rem;
    font-weight: 780;
}
.jf-finance-kpi-detail-meta {
    color: var(--jf-muted);
    font-size: .62rem;
}
.jf-finance-kpi-detail-amount {
    min-width: 6rem;
    font-size: .78rem;
    font-weight: 850;
    text-align: right;
    white-space: nowrap;
}
@media (max-width: 560px) {
    .jf-finance-kpi-detail-summary {
        grid-template-columns: 1fr;
    }
    .jf-finance-kpi-detail-row {
        grid-template-columns: 4.7rem minmax(0, 1fr) auto;
        grid-template-areas:
            "date name amount"
            "date meta actions";
        gap: .15rem .35rem;
    }
    .jf-finance-kpi-detail-date {grid-area: date;}
    .jf-finance-kpi-detail-name {grid-area: name;}
    .jf-finance-kpi-detail-meta {grid-area: meta;}
    .jf-finance-kpi-detail-amount {grid-area: amount;}
    .jf-finance-kpi-detail-actions {grid-area: actions; justify-self: end;}
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
    .jf-finance-main-tabs {
        margin-top: .15rem;
    }
    .jf-finance-main-tabs .q-tabs__content {
        padding-bottom: .12rem;
    }
    .jf-finance-main-tabs .q-tab {
        min-height: 3rem;
        padding-inline: .65rem;
    }
    .jf-finance-main-tabs .q-tab__content {
        flex-direction: row;
        gap: .35rem;
    }
    .jf-finance-main-tabs .q-tab__icon {
        margin-bottom: 0;
        font-size: 1.2rem;
    }
    .jf-finance-main-tabs .q-tab__label {
        font-size: .72rem;
        line-height: 1;
    }

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
    .jf-finance-main-tabs .q-tab {
        min-height: 2.85rem;
        padding-inline: .58rem;
    }
    .jf-finance-main-tabs .q-tab__label {
        font-size: .68rem;
    }

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
        grid-template-columns:auto 5.4rem minmax(0,1fr) 7.5rem auto;
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
            grid-template-columns:auto 4.5rem minmax(0,1fr) 6.5rem auto;
            gap:.3rem;
            padding-inline:.25rem;
        }
        .jf-finance-reconcile-description {font-size:.74rem;}
        .jf-finance-reconcile-amount {font-size:.75rem;}
    }
    """,
    shared=True,
)


ui.add_css(
    r"""
    .jf-finance-bank-strip {
        width: 100%; padding: .85rem 1rem;
        border: 1px solid color-mix(in srgb, var(--jf-blue) 24%, var(--jf-border));
        border-radius: 16px;
        background: color-mix(in srgb, var(--jf-blue-soft) 70%, var(--jf-surface));
    }
    .jf-finance-cashflow-head,.jf-finance-cashflow-row {
        display:grid; grid-template-columns:5.5rem minmax(12rem,1fr) 7rem 7rem 8rem;
        gap:.6rem; align-items:center; width:100%;
    }
    .jf-finance-cashflow-head.jf-finance-bank-reconcile,
    .jf-finance-cashflow-row.jf-finance-bank-reconcile {
        grid-template-columns:2.5rem 5.5rem minmax(12rem,1fr) 7rem 7rem 8rem;
    }
    .jf-finance-cashflow-head {padding:.45rem .7rem;font-size:.72rem;font-weight:800;color:var(--jf-muted);}
    .jf-finance-cashflow-row {padding:.65rem .7rem;border-top:1px solid var(--jf-border);font-size:.82rem;}
    .jf-finance-cashflow-money {text-align:right;font-variant-numeric:tabular-nums;}
    .jf-finance-year-grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(9rem,1fr));gap:.55rem;width:100%;}
    .jf-finance-year-card {border:1px solid var(--jf-border);border-radius:12px;padding:.65rem .75rem;background:var(--jf-surface);cursor:pointer;}
    .jf-finance-year-card:hover {border-color:var(--jf-blue);}
    .jf-finance-budget-row {display:grid;grid-template-columns:minmax(12rem,1fr) 8.5rem 8.5rem auto;gap:.65rem;align-items:center;width:100%;padding:.7rem .8rem;border-top:1px solid var(--jf-border);}
    .jf-finance-budget-money {text-align:right;font-variant-numeric:tabular-nums;font-weight:700;}
    @media(max-width:700px){
        .jf-finance-cashflow-head{display:none;}
        .jf-finance-cashflow-row{grid-template-columns:4.5rem minmax(0,1fr) 7.3rem;gap:.35rem .55rem;}
        .jf-finance-cashflow-row>:nth-child(3),.jf-finance-cashflow-row>:nth-child(4){display:none;}
        .jf-finance-cashflow-row.jf-finance-bank-reconcile{grid-template-columns:2.2rem 4.5rem minmax(0,1fr) 7.3rem;}
        .jf-finance-cashflow-row.jf-finance-bank-reconcile>:nth-child(4),
        .jf-finance-cashflow-row.jf-finance-bank-reconcile>:nth-child(5){display:none;}
        .jf-finance-budget-row{grid-template-columns:minmax(0,1fr) 7.2rem auto;}
        .jf-finance-budget-row>:nth-child(3){display:none;}
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



def _card_payment_dialog(
    user_id,
    on_saved,
    transfer=None,
):
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
        else next(iter(source_options), None)
    )
    card_default = (
        int(transfer["destination_payment_method_id"])
        if transfer
        else next(iter(card_options), None)
    )
    default_date = date.today().isoformat()

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
                    value=transfer.get("amount") if transfer else None,
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
                        else "Paiement de carte"
                    ),
                ).props("dense outlined maxlength=160").classes(
                    "jf-finance-field jf-finance-description"
                )

            status = ui.select(
                TRANSACTION_STATUSES,
                value=transfer.get("status") if transfer else "planned",
                label="Statut",
            ).props("dense outlined options-dense").classes("w-full")
            bank_programmed = ui.checkbox(
                "Déjà programmé auprès de la banque",
                value=bool(transfer.get("bank_programmed")) if transfer else False,
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
                value=transfer.get("note") or "" if transfer else "",
            ).props("dense outlined autogrow maxlength=1000").classes("w-full")

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


def finances_panel(current_user, initial_section=None, show_heading=True):
    user_id = current_user["id"]

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
                    "Budget fixe, capacité disponible et dépenses variables."
                ).classes("text-sm jf-muted")

            with ui.row().classes("items-center gap-1"):
                ui.button(
                    "Paiement carte",
                    icon="credit_card",
                    on_click=lambda: _card_payment_dialog(user_id, refresh_all),
                ).props("outline color=primary dense")
                ui.button(
                    "Ajouter",
                    icon="add",
                    on_click=lambda: _transaction_dialog(user_id, refresh_all),
                ).props("color=primary dense")
    else:
        with ui.row().classes("w-full justify-end gap-1 flex-wrap"):
            ui.button(
                "Paiement de carte",
                icon="credit_card",
                on_click=lambda: _card_payment_dialog(user_id, refresh_all),
            ).props("outline color=primary dense")
            ui.button(
                "Ajouter une transaction",
                icon="add",
                on_click=lambda: _transaction_dialog(user_id, refresh_all),
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
                    "planned_count": projection["upcoming"]["count"],
                }
                capacity = projection.get("capacity") or budget_capacity_summary(
                    user_id, month_state["value"]
                )
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
                            user_id, int(primary_account["id"]), month_state["value"]
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
                                            f"{_month_label(month_state['value'])} — "
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
                                month_state["value"],
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

                                displayed_realized = sum(
                                    (Decimal(row["realized"]) for row in rows),
                                    Decimal("0.00"),
                                )
                                displayed_upcoming = sum(
                                    (Decimal(row["upcoming"]) for row in rows),
                                    Decimal("0.00"),
                                )
                                displayed_total = sum(
                                    (Decimal(row["total"]) for row in rows),
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

            def change_month(
                offset,
                reset=False,
            ):
                month_state["value"] = (
                    date.today().replace(day=1)
                    if reset
                    else _shift_month(month_state["value"], offset)
                )
                render_dashboard.refresh()
                try:
                    render_budget.refresh()
                except (NameError, UnboundLocalError):
                    pass

            render_dashboard()


        # COMPTE / TRÉSORERIE
        with ui.tab_panel(account_tab).classes("px-0"):
            account_state = {"month": date.today().replace(day=1)}
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
                account_state["month"] = _shift_month(account_state["month"], offset)
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
                        month_data = bank_cashflow_month(user_id, account_selector.value, account_state["month"])
                        year_data = bank_cashflow_year_summary(user_id, account_selector.value, account_state["month"].year)
                    except Exception as error:
                        ui.label(str(error)).classes("text-sm jf-finance-expense")
                        return
                    with ui.row().classes("w-full items-center justify-center gap-1"):
                        ui.button(icon="chevron_left", on_click=lambda: change_account_month(-1)).props("flat dense round")
                        ui.label(_month_label(account_state["month"])).classes("font-bold min-w-40 text-center")
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
                                ("Solde de départ", month_data["start_balance"]),
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
                            ui.label(f"Vue annuelle {account_state['month'].year}").classes("text-lg font-bold")
                            ui.label(
                                "Dette utilisée prévue à la fin de chaque mois"
                                if is_credit_line
                                else "Solde prévu à la fin de chaque mois"
                            ).classes("text-xs jf-muted")
                        with ui.element("div").classes("jf-finance-year-grid"):
                            for month_row in year_data["months"]:
                                month_value = month_row["month"]
                                with ui.element("div").classes("jf-finance-year-card").on("click", lambda _event=None, selected=month_value: (account_state.__setitem__("month", selected), render_account.refresh())):
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
            account_selector.on_value_change(lambda _event: render_account.refresh())
            render_account()

        # BUDGET GLOBAL
        with ui.tab_panel(budget_tab).classes("px-0"):
            budget_box = ui.column().classes("w-full gap-2")
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
                budget_box.clear()
                summary_budget = budget_summary(user_id, month_state["value"])
                capacity_budget = budget_capacity_summary(user_id, month_state["value"])
                rows = list_budget_items(
                    user_id, include_inactive=True, month_value=month_state["value"]
                )
                with budget_box:
                    with ui.row().classes("w-full items-start justify-between gap-2 flex-wrap"):
                        with ui.column().classes("gap-0"):
                            ui.label("Budget — structure fixe").classes("text-xl font-bold")
                            ui.label(
                                "Revenus et dépenses fixes applicables à "
                                + _month_label(month_state["value"])
                                + ". Le résultat détermine la portion disponible pour les dépenses variables."
                            ).classes("text-xs jf-muted")
                        with ui.row().classes("gap-1 flex-wrap"):
                            ui.button(
                                icon="chevron_left",
                                on_click=lambda: change_month(-1),
                            ).props("flat round dense")
                            ui.button(
                                "Mois courant",
                                on_click=lambda: change_month(0, reset=True),
                            ).props("flat dense")
                            ui.button(
                                icon="chevron_right",
                                on_click=lambda: change_month(1),
                            ).props("flat round dense")
                            ui.button(
                                "Ajouter un poste", icon="add",
                                on_click=lambda: budget_item_dialog(),
                            ).props("color=primary dense")

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

                    for section_type, section_label in (("income", "Revenus fixes"), ("expense", "Dépenses fixes")):
                        if section_type == "expense":
                            with ui.row().classes(
                                "w-full items-end justify-between gap-2 flex-wrap mt-2"
                            ):
                                ui.label(section_label).classes("text-lg font-bold")
                                with ui.row().classes("items-end gap-2 flex-wrap"):
                                    budget_sort_field = ui.select(
                                        BUDGET_SORT_FIELDS,
                                        value=budget_sort_state["field"],
                                        label="Trier par",
                                    ).props(
                                        "dense outlined options-dense"
                                    ).classes("min-w-44")
                                    budget_sort_direction = ui.select(
                                        BUDGET_SORT_DIRECTIONS,
                                        value=budget_sort_state["direction"],
                                        label="Sens",
                                    ).props(
                                        "dense outlined options-dense"
                                    ).classes("min-w-32")

                                    def change_budget_sort(_event=None):
                                        budget_sort_state["field"] = (
                                            budget_sort_field.value or "monthly_amount"
                                        )
                                        budget_sort_state["direction"] = (
                                            budget_sort_direction.value or "desc"
                                        )
                                        render_budget.refresh()

                                    budget_sort_field.on_value_change(
                                        change_budget_sort
                                    )
                                    budget_sort_direction.on_value_change(
                                        change_budget_sort
                                    )
                        else:
                            ui.label(section_label).classes("text-lg font-bold mt-2")

                        section_rows = sorted_budget_rows(
                            [row for row in rows if row["item_type"] == section_type],
                            section_type,
                        )
                        with ui.card().classes("w-full p-0 overflow-hidden"):
                            if not section_rows:
                                ui.label("Aucun poste.").classes("p-4 text-sm jf-muted")
                            for row in section_rows:
                                active_month = bool(row.get("effective_for_month", True))
                                row_class = "jf-finance-budget-row" + (" opacity-50" if not active_month else "")
                                with ui.element("div").classes(row_class):
                                    with ui.column().classes("gap-0 min-w-0"):
                                        ui.label(row["description"]).classes("font-semibold truncate").tooltip(row["description"])
                                        detail = BUDGET_INPUT_FREQUENCIES.get(row["input_frequency"], row["input_frequency"])
                                        if row.get("biweekly_is_override"):
                                            detail += " • montant par paie personnalisé"
                                        if not row["is_active"]:
                                            detail += " • désactivé"
                                        if not active_month:
                                            detail += " • hors période pour ce mois"
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
                                        if row.get("recurrence_id"):
                                            link_text = "Lié à « " + str(row.get("recurrence_description") or "récurrence") + " »"
                                            if row.get("sync_from_recurrence"):
                                                link_text += " • synchronisé"
                                            ui.label(link_text).classes("text-xs text-primary")
                                    ui.label(_money(row["monthly_amount"]) + " / mois").classes("jf-finance-budget-money")
                                    ui.label(_money(row["biweekly_amount"]) + " / paie").classes("jf-finance-budget-money")
                                    with ui.row().classes("gap-0 shrink-0"):
                                        if (
                                            section_type == "income"
                                            or budget_sort_state["field"] == "custom"
                                        ):
                                            ui.button(icon="keyboard_arrow_up", on_click=lambda _event=None, selected=row["id"]: change_budget_order(selected, "up")).props("flat dense round size=sm")
                                            ui.button(icon="keyboard_arrow_down", on_click=lambda _event=None, selected=row["id"]: change_budget_order(selected, "down")).props("flat dense round size=sm")
                                        ui.switch(value=row["is_active"], on_change=lambda event, selected=row["id"]: change_budget_state(selected, event.value)).props("dense")
                                        ui.button(icon="event_repeat", on_click=lambda _event=None, selected=row: budget_item_dialog(selected, clone_period=True)).props("flat dense round size=sm color=secondary").tooltip("Créer une nouvelle période")
                                        ui.button(icon="edit", on_click=lambda _event=None, selected=row: budget_item_dialog(selected)).props("flat dense round size=sm color=primary")
            render_budget()

        # FINANCEMENTS ET VERSEMENTS
        with ui.tab_panel(financing_tab).classes("px-0"):
            financing_box = ui.column().classes("w-full gap-2")

            def installment_plan_dialog(plan=None):
                current = dict(plan) if plan else {}
                with ui.dialog() as dialog:
                    with ui.card().classes("w-full max-w-3xl p-4"):
                        ui.label(
                            "Modifier le financement" if plan else "Nouveau financement"
                        ).classes("text-xl font-bold")
                        plan_type = ui.select(
                            INSTALLMENT_PLAN_TYPES,
                            value=current.get("plan_type", "merchant"),
                            label="Type de financement",
                        ).props("dense outlined options-dense").classes("w-full")
                        with ui.element("div").classes("jf-finance-form-grid"):
                            provider = ui.input(
                                label="Magasin / programme", value=current.get("provider_name", "")
                            ).props("dense outlined maxlength=160").classes("jf-finance-field")
                            description_plan = ui.input(
                                label="Achat / description", value=current.get("description", "")
                            ).props("dense outlined maxlength=200").classes("jf-finance-field jf-finance-description")
                            original_amount = ui.number(
                                label="Montant initial", value=current.get("original_amount"), min=.01, step=.01
                            ).props("dense outlined").classes("jf-finance-field")
                            purchase_date = ui.input(
                                label="Date d’achat — facultative",
                                value=current.get("purchase_date").isoformat() if current.get("purchase_date") else "",
                            ).props("type=date dense outlined clearable").classes("jf-finance-field")
                            total_installments = ui.number(
                                label="Nombre total de versements", value=current.get("total_installments", 18), min=1, step=1
                            ).props("dense outlined").classes("jf-finance-field")
                            completed_installments = ui.number(
                                label="Versements déjà effectués", value=current.get("completed_installments", 0), min=0, step=1
                            ).props("dense outlined").classes("jf-finance-field")
                            remaining_balance = ui.number(
                                label="Solde restant actuel — facultatif", value=current.get("remaining_balance"), min=0, step=.01
                            ).props("dense outlined clearable").classes("jf-finance-field")
                            installment_amount = ui.number(
                                label="Montant du versement — auto si vide", value=current.get("installment_amount"), min=.01, step=.01
                            ).props("dense outlined clearable").classes("jf-finance-field")
                            annual_interest_rate = ui.number(
                                label="Taux d’intérêt annuel %", value=current.get("annual_interest_rate", 0), min=0, step=.01
                            ).props("dense outlined").classes("jf-finance-field")
                            fees_total = ui.number(
                                label="Frais totaux", value=current.get("fees_total", 0), min=0, step=.01
                            ).props("dense outlined").classes("jf-finance-field")
                            frequency_unit = ui.select(
                                FREQUENCY_UNITS, value=current.get("frequency_unit", "month"), label="Fréquence"
                            ).props("dense outlined options-dense").classes("jf-finance-field")
                            frequency_interval = ui.number(
                                label="Tous les…", value=current.get("frequency_interval", 1), min=1, step=1
                            ).props("dense outlined").classes("jf-finance-field")
                            next_due_date = ui.input(
                                label="Prochaine échéance",
                                value=current.get("next_due_date").isoformat() if current.get("next_due_date") else date.today().isoformat(),
                            ).props("type=date dense outlined").classes("jf-finance-field")
                            payment_method_plan = ui.select(
                                _payment_options(user_id, include_none=False),
                                value=current.get("payment_method_id"),
                                label="Compte ou carte utilisé pour les versements",
                            ).props("dense outlined clearable options-dense").classes("jf-finance-field")
                            category_plan = ui.select(
                                _category_options(user_id),
                                value=current.get("category_id"),
                                label="Catégorie de dépense",
                            ).props("dense outlined clearable options-dense").classes("jf-finance-field")
                        tags_plan = ui.select(
                            _tag_options(user_id),
                            value=current.get("tag_ids") or [],
                            label="Étiquettes — facultatif", multiple=True,
                        ).props("dense outlined use-chips clearable options-dense").classes("w-full")
                        budget_excluded = ui.checkbox(
                            "Exclure exceptionnellement les versements du budget (Hors budget)",
                            value=bool(current.get("budget_excluded", False)),
                        )
                        note_plan = ui.textarea(
                            label="Note facultative", value=current.get("note") or ""
                        ).props("dense outlined autogrow maxlength=1000").classes("w-full")
                        ui.label(
                            "Seuls les versements futurs sont créés comme dépenses prévues. Le montant initial "
                            "n’est pas compté une seconde fois. Pour un plan déjà en cours, indiquez les versements "
                            "déjà effectués et le solde actuel; l’historique passé n’est pas recréé automatiquement."
                        ).classes("text-xs jf-muted")

                        def save_plan_now():
                            try:
                                save_installment_plan(
                                    user_id=user_id,
                                    plan_id=current.get("id"),
                                    plan_type=plan_type.value,
                                    provider_name=provider.value,
                                    description=description_plan.value,
                                    original_amount=original_amount.value,
                                    purchase_date=purchase_date.value or None,
                                    total_installments=int(total_installments.value or 0),
                                    completed_installments=int(completed_installments.value or 0),
                                    remaining_balance=remaining_balance.value,
                                    installment_amount=installment_amount.value,
                                    annual_interest_rate=annual_interest_rate.value or 0,
                                    fees_total=fees_total.value or 0,
                                    frequency_unit=frequency_unit.value,
                                    frequency_interval=int(frequency_interval.value or 1),
                                    next_due_date=next_due_date.value,
                                    payment_method_id=payment_method_plan.value,
                                    category_id=category_plan.value,
                                    tag_ids=tags_plan.value or [],
                                    budget_excluded=budget_excluded.value,
                                    note=note_plan.value,
                                )
                            except Exception as error:
                                ui.notify(str(error), type="warning")
                                return
                            dialog.close()
                            ui.notify("Financement enregistré et versements projetés.", type="positive")
                            refresh_all()

                        with ui.row().classes("w-full justify-end gap-2"):
                            ui.button("Annuler", on_click=dialog.close).props("flat")
                            ui.button("Enregistrer", icon="save", on_click=save_plan_now).props("color=primary")
                dialog.open()

            def remove_installment_plan(plan_id):
                with ui.dialog() as dialog:
                    with ui.card().classes("w-full max-w-md p-4"):
                        ui.label("Supprimer le financement ?").classes("text-xl font-bold")
                        ui.label(
                            "Les versements futurs non confirmés seront retirés. Les transactions déjà confirmées restent dans l’historique."
                        ).classes("text-sm jf-muted")
                        def remove_now():
                            try:
                                delete_installment_plan(user_id, plan_id)
                            except Exception as error:
                                ui.notify(str(error), type="warning")
                                return
                            dialog.close(); ui.notify("Financement supprimé.", type="positive"); refresh_all()
                        with ui.row().classes("w-full justify-end gap-2"):
                            ui.button("Annuler", on_click=dialog.close).props("flat")
                            ui.button("Supprimer", icon="delete", on_click=remove_now).props("color=negative")
                dialog.open()

            @ui.refreshable
            def render_financing():
                financing_box.clear()
                plans = list_installment_plans(user_id, include_inactive=True)
                with financing_box:
                    with ui.row().classes("w-full items-start justify-between gap-2 flex-wrap"):
                        with ui.column().classes("gap-0"):
                            ui.label("Financements et achats en versements").classes("text-xl font-bold")
                            ui.label(
                                "Magasins et plans de versements sur cartes. Chaque versement est une vraie dépense "
                                "dans les KPI selon sa catégorie, sauf exclusion explicite."
                            ).classes("text-xs jf-muted")
                        ui.button("Ajouter un financement", icon="add", on_click=lambda: installment_plan_dialog()).props("color=primary dense")
                    if not plans:
                        with ui.card().classes("w-full p-4"):
                            ui.label("Aucun financement enregistré.").classes("text-sm jf-muted")
                    with ui.element("div").classes("jf-finance-balance-grid"):
                        for plan in plans:
                            with ui.element("section").classes("jf-finance-balance-card"):
                                with ui.row().classes("w-full items-start justify-between gap-2"):
                                    with ui.column().classes("gap-0 min-w-0"):
                                        ui.label(plan["description"]).classes("font-bold truncate").tooltip(plan["description"])
                                        ui.label(
                                            INSTALLMENT_PLAN_TYPES.get(plan["plan_type"], plan["plan_type"])
                                            + (" — " + plan["provider_name"] if plan.get("provider_name") else "")
                                        ).classes("text-xs jf-muted")
                                    with ui.row().classes("gap-0"):
                                        ui.switch(
                                            value=plan["is_active"],
                                            on_change=lambda event, selected=plan["id"]: (toggle_installment_plan(user_id, selected, event.value), refresh_all()),
                                        ).props("dense")
                                        ui.button(icon="edit", on_click=lambda _event=None, selected=plan: installment_plan_dialog(selected)).props("flat dense round size=sm color=primary")
                                        ui.button(icon="delete", on_click=lambda _event=None, selected=plan["id"]: remove_installment_plan(selected)).props("flat dense round size=sm color=negative")
                                with ui.element("div").classes("jf-finance-summary-grid mt-2"):
                                    for label, value in (
                                        ("Montant initial", plan["original_amount"]),
                                        ("Payé / estimé", Decimal(plan.get("original_amount", 0)) - Decimal(plan.get("estimated_remaining_balance", 0))),
                                        ("Solde restant", plan.get("estimated_remaining_balance", plan.get("remaining_balance", 0))),
                                        ("Versement", plan["installment_amount"]),
                                    ):
                                        with ui.element("div").classes("jf-finance-summary"):
                                            ui.label(label).classes("jf-finance-summary-label")
                                            ui.label(_money(value)).classes("jf-finance-summary-value")
                                ui.label(
                                    f"{plan.get('display_completed_installments', plan.get('completed_installments', 0))}/{plan['total_installments']} versements effectués — "
                                    f"{plan.get('display_remaining_installments', 0)} restant(s)"
                                ).classes("text-xs jf-muted mt-1")
                                if plan.get("next_due_date"):
                                    ui.label(
                                        "Prochaine échéance : " + plan["next_due_date"].strftime("%d/%m/%Y")
                                    ).classes("text-xs text-primary")
                                if Decimal(plan.get("annual_interest_rate", 0)) or Decimal(plan.get("fees_total", 0)):
                                    ui.label(
                                        f"Intérêt : {plan.get('annual_interest_rate', 0)} % — Frais : {_money(plan.get('fees_total', 0))}"
                                    ).classes("text-xs jf-muted")
            render_financing()


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
                                render_dashboard.refresh()

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
                                render_dashboard.refresh()

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
                        if row.get("linked_transfer_id"):
                            ui.label(
                                "Ce paiement est lié au compte bancaire et à la carte de crédit. Les deux côtés seront supprimés ensemble."
                            ).classes("text-sm jf-muted")

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
                    if row.get("linked_transfer_id") and row.get("linked_transfer_role") == "source":
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
                    if row[
                        "status"
                    ] == "planned":
                        meta.append(
                            "À confirmer"
                        )
                    if row.get("budget_excluded"):
                        meta.append("Hors budget")
                    if row.get("bank_programmed"):
                        meta.append("Programmé")
                    if row.get("reminder_enabled"):
                        meta.append("Rappel " + str(row.get("reminder_time") or "09:00")[:5])
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

                        if row.get("linked_transfer_id"):
                            ui.button(
                                icon="edit",
                                on_click=(
                                    lambda _event=None,
                                    selected_transfer_id=row.get("linked_transfer_id"):
                                    _card_payment_dialog(
                                        user_id,
                                        refresh_all,
                                        get_card_payment_transfer(
                                            user_id,
                                            selected_transfer_id,
                                        ),
                                    )
                                ),
                            ).props(
                                "flat dense round size=sm color=primary"
                            ).tooltip(
                                "Modifier le paiement de carte"
                            )
                        else:
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
                        include_linked_transfer_destinations=False,
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

                        def finalize_now(resolution="balanced"):
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
                                    statement_balance=statement_balance.value,
                                    due_date=due_date.value or None,
                                    reconciliation_date=(
                                        reconciliation_date_input.value
                                    ),
                                    note=reconciliation_note.value,
                                    include_opening_balance=(
                                        include_opening_balance.value
                                    ),
                                    difference_resolution=resolution,
                                    difference_explanation=(
                                        difference_explanation.value or None
                                    ),
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
                                            finalize_now("justified")

                                        def carry_difference():
                                            warning_dialog.close()
                                            finalize_now("carry")

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

                            finalize_now("balanced")

                        ui.button(
                            "Finaliser la conciliation",
                            icon="fact_check",
                            on_click=request_finalize,
                        ).props("color=primary").classes("w-full mt-2")

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
                render_reconciliation_balance.refresh()
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

                    def change_category_dashboard(category_id, value):
                        try:
                            set_category_dashboard_visible(
                                user_id, category_id, value
                            )
                        except Exception as error:
                            ui.notify(str(error), type="warning")
                            return
                        render_dashboard.refresh()

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
                                with ui.column().classes("gap-0"):
                                    ui.label(
                                        "Catégories et sous-catégories"
                                    ).classes("text-xl font-bold")
                                    ui.label(
                                        "La case Tableau choisit les catégories affichées dans les KPI du Tableau de bord."
                                    ).classes("text-xs jf-muted")
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
                                        with ui.row().classes("gap-1 items-center"):
                                            ui.checkbox(
                                                "Tableau",
                                                value=bool(
                                                    row.get(
                                                        "dashboard_visible", True
                                                    )
                                                ),
                                                on_change=(
                                                    lambda event,
                                                    selected=row["id"]:
                                                    change_category_dashboard(
                                                        selected, event.value
                                                    )
                                                ),
                                            ).props("dense").tooltip(
                                                "Afficher cette catégorie dans les KPI du Tableau"
                                            )
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

                    def change_tag_dashboard(tag_id, value):
                        try:
                            set_tag_dashboard_visible(
                                user_id, tag_id, value
                            )
                        except Exception as error:
                            ui.notify(str(error), type="warning")
                            return
                        render_dashboard.refresh()

                    @ui.refreshable
                    def render_tags():
                        tag_box.clear()
                        rows = list_tags(user_id, include_inactive=True)
                        with tag_box:
                            with ui.row().classes(
                                "w-full items-center justify-between"
                            ):
                                with ui.column().classes("gap-0"):
                                    ui.label("Étiquettes").classes(
                                        "text-xl font-bold"
                                    )
                                    ui.label(
                                        "La case Tableau choisit les étiquettes affichées dans les KPI du Tableau de bord."
                                    ).classes("text-xs jf-muted")
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
                                        with ui.row().classes("gap-1 items-center"):
                                            ui.checkbox(
                                                "Tableau",
                                                value=bool(
                                                    row.get(
                                                        "dashboard_visible", True
                                                    )
                                                ),
                                                on_change=(
                                                    lambda event,
                                                    selected=row["id"]:
                                                    change_tag_dashboard(
                                                        selected, event.value
                                                    )
                                                ),
                                            ).props("dense").tooltip(
                                                "Afficher cette étiquette dans les KPI du Tableau"
                                            )
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

                                credit_limit = ui.number(
                                    label="Limite de crédit — facultative",
                                    value=(
                                        row.get("credit_limit")
                                        if row
                                        else None
                                    ),
                                    min=0,
                                    step=.01,
                                ).props(
                                    "dense outlined clearable"
                                ).classes("w-full")

                                payment_help = ui.label(
                                    "Pour une carte, le solde initial sert à la conciliation. Pour un Compte bancaire, il devient le solde de référence utilisé par l’onglet Compte et le Tableau; indique aussi la date de référence."
                                ).classes("text-xs jf-muted")

                                def update_payment_type_fields(_event=None):
                                    is_credit_line = method_type.value == "credit_line"
                                    credit_limit.visible = is_credit_line
                                    payment_help.set_text(
                                        (
                                            "Pour une Marge de crédit, le solde initial représente la dette utilisée à la date de référence. La limite permet de calculer le crédit disponible; une dépense augmente la dette et un remboursement la réduit."
                                            if is_credit_line
                                            else "Pour une carte, le solde initial sert à la conciliation. Pour un Compte bancaire, il devient le solde de référence utilisé par l’onglet Compte et le Tableau; indique aussi la date de référence."
                                        )
                                    )

                                method_type.on_value_change(update_payment_type_fields)
                                update_payment_type_fields()

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
                                            credit_limit=(
                                                credit_limit.value
                                                if method_type.value == "credit_line"
                                                else None
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
                                            if row.get("method_type") == "credit_line":
                                                used = Decimal(
                                                    row.get("opening_balance") or 0
                                                )
                                                limit = (
                                                    Decimal(row["credit_limit"])
                                                    if row.get("credit_limit") is not None
                                                    else None
                                                )
                                                text = "Solde utilisé de référence : " + _balance_money(used)
                                                if limit is not None:
                                                    text += (
                                                        " — limite "
                                                        + _balance_money(limit)
                                                        + " — disponible "
                                                        + _balance_money(limit - used)
                                                    )
                                                ui.label(text).classes(
                                                    "text-xs jf-muted"
                                                )
                                            elif Decimal(
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
                                    f"{len(preview['payment_methods'])} — "
                                    "Postes de budget détectés : "
                                    f"{len(preview.get('budget_items') or [])}"
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
                                        budget_items=preview.get("budget_items") or [],
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
                                    "mode(s) de paiement créé(s), "
                                    f"{result.get('budget_items_imported', 0)} "
                                    "poste(s) de budget restauré(s)."
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
                    "de paiement, les statuts de conciliation, l’indicateur Hors budget, "
                    "les postes du budget global et les clés d’importation sont conservés."
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
        account_selector.options = _bank_account_options(user_id)
        if account_selector.value not in account_selector.options:
            account_selector.value = next(iter(account_selector.options), None)
        account_selector.update()
        render_account.refresh()
        render_budget.refresh()
        render_financing.refresh()

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
