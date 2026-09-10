"""Styles de Finances, installés avec une interface injectée."""

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
        minmax(5.8rem, .78fr)
        minmax(4.2rem, .50fr);
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
            4.1rem
            4.1rem
            4.45rem
            3.65rem;
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

_FINANCE_LAYOUT_CSS = r"""
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
    """

_FINANCE_ACCOUNT_CSS = r"""
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
    .jf-finance-cashflow-start {
        background:color-mix(in srgb,var(--jf-blue-soft) 55%,var(--jf-surface));
        font-weight:700;
    }
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
    """

def install_finance_styles(ui):
    ui.add_css(FINANCE_CSS, shared=True)
    ui.add_css(_FINANCE_LAYOUT_CSS, shared=True)
    ui.add_css(_FINANCE_ACCOUNT_CSS, shared=True)
