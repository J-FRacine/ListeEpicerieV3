"""Styles partagés de la fiche Personnage JDR."""
from __future__ import annotations

RPG_CSS = r"""
.jf-rpg-private {
    width: 100%;
    padding: 0.85rem 1rem;
    border-left: 5px solid #65508f;
    border-radius: 14px;
    background: rgba(101, 80, 143, 0.10);
}

.jf-rpg-grid {
    display: grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(
                min(100%, 13rem),
                1fr
            )
        );
    gap: 0.8rem;
    width: 100%;
}

.jf-rpg-ability-grid {
    display: grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(
                min(100%, 12rem),
                1fr
            )
        );
    gap: 0.75rem;
    width: 100%;
}

.jf-rpg-ability-card,
.jf-rpg-save-card,
.jf-rpg-skill-card,
.jf-rpg-attack-card {
    width: 100%;
    padding: 0.95rem;
    border: 1px solid var(--jf-border);
    border-radius: 16px;
    background: var(--jf-surface);
}

.jf-rpg-stat-value {
    color: var(--jf-navy);
    font-size: 1.55rem;
    font-weight: 800;
}

.body--dark .jf-rpg-stat-value {
    color: #dceaf6;
}

.jf-rpg-summary {
    width: 100%;
    padding: 0.85rem 1rem;
    border-left: 5px solid var(--jf-blue);
    border-radius: 14px;
    background: var(--jf-blue-soft);
}

.jf-rpg-ravenloft {
    border-left: 5px solid #65508f;
}

.jf-rpg-audit {
    width: 100%;
    padding: .75rem .85rem;
    border: 1px solid var(--jf-border);
    border-left: 4px solid var(--jf-blue);
    border-radius: 12px;
    background: var(--jf-blue-soft);
}
.jf-rpg-audit-warning {
    border-left-color: #bf7812;
    background: rgba(191, 120, 18, .09);
}
.jf-rpg-audit-row {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: start;
    gap: .45rem;
    width: 100%;
    padding: .32rem 0;
    border-bottom: 1px solid var(--jf-border);
}
.jf-rpg-reference-row {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: .45rem;
    width: 100%;
    padding: .35rem 0;
    border-bottom: 1px solid var(--jf-border);
}
.jf-rpg-reference-formula {
    color: var(--jf-muted);
    font-size: .7rem;
}
.jf-rpg-skill-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    width: 100%;
}

.jf-rpg-skill-badge {
    display: inline-flex;
    align-items: center;
    width: fit-content;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--jf-navy);
    background: var(--jf-blue-soft);
}

.jf-rpg-skill-badge-owned {
    color: #156c47;
    background: rgba(33, 145, 92, 0.13);
}

.jf-rpg-skill-badge-class {
    color: #65420e;
    background: rgba(189, 149, 85, 0.17);
}

.jf-rpg-skill-filter-summary {
    width: 100%;
    padding: 0.7rem 0.85rem;
    border-radius: 12px;
    background: rgba(34, 70, 122, 0.07);
}

.jf-rpg-help {
    width: 100%;
    padding: 0.8rem 0.95rem;
    border-left: 4px solid var(--jf-gold);
    border-radius: 12px;
    background: rgba(189, 149, 85, 0.10);
}

.jf-rpg-character-banner {
    width: 100%;
    padding: 1rem;
    border-radius: 16px;
    color: white;
    background:
        linear-gradient(
            135deg,
            #1b2836 0%,
            #35485d 62%,
            #65508f 100%
        );
}

.jf-rpg-skill-total {
    min-width: 3rem;
    padding: 0.2rem 0.58rem;
    border-radius: 999px;
    text-align: center;
    color: white;
    background: var(--jf-navy);
    font-size: 0.95rem;
    font-weight: 800;
}

.jf-rpg-skill-card {
    padding: 0.58rem 0.7rem;
    border-radius: 13px;
}

.jf-rpg-skill-header {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    width: 100%;
    min-width: 0;
}

.jf-rpg-skill-name {
    min-width: 0;
    overflow-wrap: anywhere;
    color: var(--jf-navy);
    font-size: 0.98rem;
    font-weight: 800;
}

.body--dark .jf-rpg-skill-name {
    color: #dceaf6;
}

.jf-rpg-skill-edit-button {
    flex: 0 0 auto;
}

.jf-rpg-skill-badges-compact {
    display: flex;
    flex: 1 1 auto;
    flex-wrap: wrap;
    gap: 0.25rem;
    min-width: 0;
}

.jf-rpg-skill-badges-compact .jf-rpg-skill-badge {
    padding: 0.12rem 0.42rem;
    font-size: 0.66rem;
}

.jf-rpg-skill-controls {
    display: grid;
    grid-template-columns:
        minmax(6.5rem, 8.5rem)
        minmax(4.6rem, 5.7rem)
        minmax(4.6rem, 5.7rem)
        max-content
        max-content
        max-content
        max-content;
    align-items: center;
    gap: 0.25rem 0.55rem;
    width: 100%;
    margin-top: 0.35rem;
}

.jf-rpg-skill-control .q-field__control {
    min-height: 36px;
    height: 36px;
}

.jf-rpg-skill-control .q-field__native,
.jf-rpg-skill-control .q-field__input,
.jf-rpg-skill-control .q-field__label {
    font-size: 0.78rem;
}

.jf-rpg-skill-check {
    margin: 0;
    white-space: nowrap;
}

.jf-rpg-skill-check .q-checkbox__label {
    font-size: 0.74rem;
}

.jf-rpg-skill-check .q-checkbox__inner {
    font-size: 32px;
}

.jf-rpg-skill-calculation {
    width: 100%;
    margin-top: 0.3rem;
    padding: 0.28rem 0.5rem;
    border-radius: 9px;
    color: var(--jf-muted);
    background: rgba(34, 70, 122, 0.055);
    font-size: 0.72rem;
}

.jf-rpg-skill-warning {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.45rem;
    width: 100%;
    margin-top: 0.28rem;
    padding: 0.28rem 0.5rem;
    border-radius: 9px;
    color: #75500f;
    background: rgba(189, 149, 85, 0.16);
    font-size: 0.72rem;
}

@media (max-width: 980px) {
    .jf-rpg-skill-controls {
        grid-template-columns:
            minmax(6.5rem, 1.2fr)
            minmax(4.6rem, 0.7fr)
            minmax(4.6rem, 0.7fr)
            repeat(2, max-content);
    }
}

@media (max-width: 680px) {
    .jf-rpg-skill-header {
        align-items: flex-start;
        flex-wrap: wrap;
    }

    .jf-rpg-skill-badges-compact {
        flex-basis: 100%;
    }

    .jf-rpg-skill-controls {
        grid-template-columns:
            minmax(6rem, 1fr)
            minmax(4.4rem, 0.65fr)
            minmax(4.4rem, 0.65fr)
            repeat(2, max-content);
    }

    .jf-rpg-skill-check .q-checkbox__label {
        font-size: 0.7rem;
    }
}

@media (max-width: 470px) {
    .jf-rpg-skill-controls {
        grid-template-columns:
            minmax(5.8rem, 1fr)
            minmax(4.2rem, 0.75fr)
            minmax(4.2rem, 0.75fr);
    }
}

.jf-rpg-main-tabs {
    width: 100%;
    overflow: hidden;
    border-bottom: 1px solid var(--jf-border);
}
.jf-rpg-main-tabs .q-tabs__content {
    display: flex;
    flex-wrap: nowrap;
    justify-content: flex-start;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: thin;
}
.jf-rpg-main-tabs .q-tab {
    flex: 0 0 auto;
    min-width: max-content;
    padding-inline: .72rem;
}
.jf-rpg-main-tabs .q-tab__content {
    min-width: max-content;
}
.jf-rpg-main-tabs .q-tab__label {
    overflow: visible;
    white-space: nowrap;
    text-overflow: clip;
}
.jf-rpg-race-profile {
    width: 100%;
    padding: .8rem .9rem;
    border: 1px solid var(--jf-border);
    border-left: 4px solid #65508f;
    border-radius: 13px;
    background: rgba(101, 80, 143, .07);
}
.jf-rpg-race-preview-row {
    display: grid;
    grid-template-columns: minmax(7rem, .8fr) minmax(0, 1fr) minmax(0, 1fr);
    gap: .45rem;
    width: 100%;
    padding: .34rem 0;
    border-bottom: 1px solid var(--jf-border);
    font-size: .76rem;
}
.jf-rpg-combat-value .q-field__native,
.jf-rpg-combat-value .q-field__input {
    color: var(--jf-navy);
    font-size: 1.1rem;
    font-weight: 820;
}
.body--dark .jf-rpg-combat-value .q-field__native,
.body--dark .jf-rpg-combat-value .q-field__input {
    color: #e2edf6;
}
.jf-rpg-equipment-summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(9.5rem, 1fr));
    gap: .55rem;
    width: 100%;
}
.jf-rpg-equipment-stat {
    padding: .65rem .72rem;
    border: 1px solid var(--jf-border);
    border-radius: 11px;
    background: var(--jf-surface);
}
.jf-rpg-equipment-stat-value {
    color: var(--jf-navy);
    font-size: 1.18rem;
    font-weight: 850;
}
.body--dark .jf-rpg-equipment-stat-value {
    color: #dceaf6;
}
.jf-rpg-equipment-card {
    width: 100%;
    padding: .72rem .8rem;
    border: 1px solid var(--jf-border);
    border-radius: 13px;
    background: var(--jf-surface);
}
.jf-rpg-equipment-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
    gap: .55rem;
    width: 100%;
}
.jf-rpg-equipment-name {
    min-width: 0;
    overflow-wrap: anywhere;
    font-size: .9rem;
    font-weight: 820;
}
.jf-rpg-equipment-meta {
    color: var(--jf-muted);
    font-size: .7rem;
}
.jf-rpg-equipment-breakdown {
    width: 100%;
    padding: .7rem .8rem;
    border-left: 4px solid var(--jf-blue);
    border-radius: 11px;
    background: var(--jf-blue-soft);
    font-size: .75rem;
}

@media (max-width: 680px) {
    .jf-rpg-main-tabs .q-tab {
        min-height: 3rem;
        padding-inline: .62rem;
    }
    .jf-rpg-main-tabs .q-tab__content {
        flex-direction: row;
        gap: .3rem;
    }
    .jf-rpg-main-tabs .q-tab__icon {
        margin-bottom: 0;
        font-size: 1.15rem;
    }
    .jf-rpg-main-tabs .q-tab__label {
        font-size: .7rem;
    }
    .jf-rpg-race-preview-row {
        grid-template-columns: minmax(6rem, .8fr) minmax(0, 1fr);
    }
    .jf-rpg-race-preview-row > :nth-child(2) {
        display: none;
    }
}

.jf-rpg-ability-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 0.5rem;
}

.jf-rpg-ability-card {
    padding: 0.58rem 0.65rem;
    border-radius: 13px;
}

.jf-rpg-ability-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.35rem;
    width: 100%;
}

.jf-rpg-ability-title {
    min-width: 0;
    font-size: 0.82rem;
    font-weight: 800;
}

.jf-rpg-ability-modifier {
    flex: 0 0 auto;
    min-width: 2.45rem;
    padding: 0.12rem 0.42rem;
    border-radius: 999px;
    text-align: center;
    color: white;
    background: var(--jf-navy);
    font-size: 0.92rem;
    font-weight: 800;
}

.jf-rpg-ability-fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.35rem;
    width: 100%;
    margin-top: 0.35rem;
}

.jf-rpg-compact-field .q-field__control {
    min-height: 38px;
    height: 38px;
}

.jf-rpg-compact-field .q-field__native,
.jf-rpg-compact-field .q-field__input,
.jf-rpg-compact-field .q-field__label {
    font-size: 0.78rem;
}

.jf-rpg-combat-grid {
    display: grid;
    grid-template-columns: repeat(8, minmax(7.25rem, 1fr));
    gap: 0.45rem 0.55rem;
    width: 100%;
}

.jf-rpg-result-grid {
    display: grid;
    grid-template-columns: repeat(6, minmax(6.5rem, 1fr));
    gap: 0.55rem;
    width: 100%;
}

.jf-rpg-result-item {
    padding: 0.45rem 0.55rem;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.52);
}

.body--dark .jf-rpg-result-item {
    background: rgba(0, 0, 0, 0.12);
}

.jf-rpg-rules-formula {
    width: 100%;
    margin-top: 0.3rem;
    padding: 0.55rem 0.65rem;
    border-radius: 10px;
    background: var(--jf-blue-soft);
    font-size: 0.82rem;
    font-weight: 700;
}

.jf-rpg-rules-example {
    width: 100%;
    margin-top: 0.35rem;
    padding: 0.55rem 0.65rem;
    border-left: 4px solid var(--jf-gold);
    border-radius: 9px;
    background: rgba(189, 149, 85, 0.09);
    font-size: 0.8rem;
}

@media (max-width: 1180px) {
    .jf-rpg-ability-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .jf-rpg-combat-grid {
        grid-template-columns: repeat(5, minmax(7rem, 1fr));
    }

    .jf-rpg-result-grid {
        grid-template-columns: repeat(3, minmax(6.5rem, 1fr));
    }
}

@media (max-width: 760px) {
    .jf-rpg-ability-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .jf-rpg-combat-grid {
        grid-template-columns: repeat(3, minmax(6.5rem, 1fr));
    }
}

@media (max-width: 480px) {
    .jf-rpg-ability-grid {
        grid-template-columns: 1fr;
    }

    .jf-rpg-combat-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .jf-rpg-result-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

.jf-rpg-section-actions {
    position: sticky;
    bottom: 0.75rem;
    z-index: 3;
    width: fit-content;
    margin-left: auto;
    padding: 0.4rem;
    border: 1px solid var(--jf-border);
    border-radius: 14px;
    background: var(--jf-surface);
    box-shadow: var(--jf-shadow);
}

@media (max-width: 680px) {
    .jf-rpg-section-actions {
        width: 100%;
    }

    .jf-rpg-section-actions .q-btn {
        width: 100%;
    }
}
"""


def install_rpg_styles(ui):
    ui.add_css(RPG_CSS, shared=True)
