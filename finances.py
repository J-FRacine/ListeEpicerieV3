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
    TRANSACTION_STATUSES,
    TRANSACTION_TYPES,
    dashboard_summary,
    delete_transaction,
    ensure_default_finance_categories,
    export_finances,
    generate_due_recurrences,
    get_transaction,
    goal_progress,
    list_categories,
    list_goals,
    list_recurrences,
    list_tags,
    list_transactions,
    save_category,
    save_goal,
    save_recurrence,
    save_tag,
    save_transaction,
    set_transaction_status,
    toggle_category,
    toggle_goal,
    toggle_recurrence,
    toggle_tag,
)


FINANCE_CSS = r"""
.jf-finance-summary-grid {
    display:grid;
    grid-template-columns:repeat(3,minmax(0,1fr));
    gap:.4rem;
    width:100%;
}
.jf-finance-summary {
    padding:.55rem .5rem;
    border:1px solid var(--jf-border);
    border-radius:11px;
    background:var(--jf-surface);
}
.jf-finance-summary-label {color:var(--jf-muted);font-size:.66rem;}
.jf-finance-summary-value {
    color:var(--jf-navy);
    font-size:1rem;
    font-weight:850;
    white-space:nowrap;
}
.body--dark .jf-finance-summary-value {color:#dceaf6;}
.jf-finance-form-grid {
    display:grid;
    grid-template-columns:minmax(7rem,.7fr) minmax(8rem,.8fr) minmax(12rem,1.5fr);
    gap:.5rem;
    width:100%;
}
.jf-finance-field .q-field__control {min-height:40px;height:40px;}
.jf-finance-list {display:flex;flex-direction:column;gap:.3rem;width:100%;}
.jf-finance-day {
    padding:.25rem .5rem;
    border-left:4px solid var(--jf-blue);
    border-radius:8px;
    background:var(--jf-blue-soft);
    font-size:.76rem;
    font-weight:800;
}
.jf-finance-row {
    display:grid;
    grid-template-columns:minmax(0,1fr) auto auto;
    grid-template-areas:"main amount actions" "meta amount actions";
    align-items:center;
    gap:.05rem .4rem;
    min-height:44px;
    padding:.3rem .4rem;
    border:1px solid var(--jf-border);
    border-radius:9px;
    background:var(--jf-surface);
}
.jf-finance-main {
    grid-area:main;
    min-width:0;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
    font-size:.84rem;
    font-weight:800;
}
.jf-finance-meta {
    grid-area:meta;
    min-width:0;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
    color:var(--jf-muted);
    font-size:.67rem;
}
.jf-finance-amount {
    grid-area:amount;
    justify-self:end;
    font-size:.9rem;
    font-weight:850;
    white-space:nowrap;
}
.jf-finance-actions {grid-area:actions;display:flex;gap:0;}
.jf-finance-expense {color:#a33b46;}
.jf-finance-income {color:#187148;}
.jf-finance-card {
    width:100%;
    padding:.55rem .65rem;
    border:1px solid var(--jf-border);
    border-radius:10px;
    background:var(--jf-surface);
}
.jf-finance-progress {
    width:100%;
    height:7px;
    overflow:hidden;
    border-radius:99px;
    background:rgba(120,130,145,.18);
}
.jf-finance-progress > div {
    height:100%;
    border-radius:99px;
    background:var(--jf-blue);
}
@media(max-width:680px){
    .jf-finance-form-grid {grid-template-columns:1fr 1fr;}
    .jf-finance-description {grid-column:1/-1;}
    .jf-finance-summary-value {font-size:.86rem;}
}
@media(max-width:430px){
    .jf-finance-summary-label {font-size:.59rem;}
    .jf-finance-summary-value {font-size:.76rem;}
    .jf-finance-row {
        grid-template-columns:minmax(0,1fr) auto;
        grid-template-areas:"main amount" "meta actions";
    }
}
"""

ui.add_css(FINANCE_CSS, shared=True)


def _money(value):
    amount = Decimal(value or 0)
    return f"{abs(amount):,.2f}".replace(",", " ").replace(".", ",") + " $"


def _signed(value, transaction_type):
    return ("-" if transaction_type == "expense" else "+") + _money(value)


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


def _transaction_dialog(user_id, on_saved, transaction=None):
    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-2xl p-4"):
            ui.label(
                "Modifier la transaction" if transaction else "Nouvelle transaction"
            ).classes("text-xl font-bold")

            kind = ui.toggle(
                TRANSACTION_TYPES,
                value=transaction["transaction_type"] if transaction else "expense",
            ).props("dense spread no-caps").classes("w-full")

            with ui.element("div").classes("jf-finance-form-grid"):
                amount = ui.number(
                    label="Montant",
                    value=transaction["amount"] if transaction else None,
                    min=.01,
                    step=.01,
                ).props("dense outlined").classes("jf-finance-field")
                when = ui.input(
                    label="Date",
                    value=(
                        transaction["transaction_date"].isoformat()
                        if transaction else date.today().isoformat()
                    ),
                ).props("type=date dense outlined").classes("jf-finance-field")
                description = ui.input(
                    label="Description",
                    value=transaction["description"] if transaction else "",
                ).props("dense outlined maxlength=160").classes(
                    "jf-finance-field jf-finance-description"
                )

            category = ui.select(
                {None: "Aucune", **_category_options(user_id)},
                value=transaction["category_id"] if transaction else None,
                label="Catégorie ou sous-catégorie",
            ).props("dense outlined clearable options-dense").classes("w-full")

            tags = ui.select(
                _tag_options(user_id),
                value=list(transaction["tag_ids"]) if transaction else [],
                label="Étiquettes",
                multiple=True,
            ).props("dense outlined use-chips clearable options-dense").classes(
                "w-full"
            )

            with ui.expansion("Plus d’options", icon="tune").classes("w-full"):
                status = ui.select(
                    TRANSACTION_STATUSES,
                    value=transaction["status"] if transaction else "confirmed",
                    label="Statut",
                ).props("dense outlined options-dense").classes("w-full")
                note = ui.textarea(
                    label="Note facultative",
                    value=transaction["note"] if transaction else "",
                ).props("dense outlined autogrow maxlength=1000").classes("w-full")

            def save():
                try:
                    save_transaction(
                        user_id=user_id,
                        transaction_id=transaction["id"] if transaction else None,
                        transaction_date=when.value,
                        transaction_type=kind.value,
                        amount=amount.value,
                        description=description.value,
                        category_id=category.value,
                        tag_ids=tags.value or [],
                        note=note.value,
                        status=status.value,
                    )
                except Exception as error:
                    ui.notify(str(error), type="warning")
                    return
                dialog.close()
                ui.notify("Transaction enregistrée.", type="positive")
                on_saved()

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Annuler", on_click=dialog.close).props("flat dense")
                ui.button("Enregistrer", icon="save", on_click=save).props(
                    "color=primary"
                )
    dialog.open()


def finances_panel(current_user, initial_section=None):
    user_id = current_user["id"]
    ensure_default_finance_categories(user_id)

    try:
        generate_due_recurrences(user_id)
    except Exception:
        pass

    month_state = {"value": date.today().replace(day=1)}

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

    with ui.tabs().classes("w-full") as tabs:
        dashboard_tab = ui.tab("Tableau", icon="dashboard")
        entry_tab = ui.tab("Saisie", icon="add_circle")
        history_tab = ui.tab("Historique", icon="history")
        recurring_tab = ui.tab("Récurrences", icon="repeat")
        goals_tab = ui.tab("Objectifs", icon="track_changes")
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
        "exporter": export_tab,
    }

    with ui.tab_panels(
        tabs,
        value=tab_map.get(str(initial_section or "tableau").lower(), dashboard_tab),
    ).classes("w-full bg-transparent"):

        # TABLEAU
        with ui.tab_panel(dashboard_tab).classes("px-0"):
            dashboard_box = ui.column().classes("w-full gap-2")

            @ui.refreshable
            def render_dashboard():
                dashboard_box.clear()
                summary = dashboard_summary(user_id, month_state["value"])
                goals = goal_progress(user_id, month_state["value"])
                with dashboard_box:
                    with ui.row().classes(
                        "w-full items-center justify-center gap-1"
                    ):
                        ui.button(
                            icon="chevron_left",
                            on_click=lambda: change_month(-1),
                        ).props("flat dense round")
                        ui.label(_month_label(month_state["value"])).classes(
                            "font-bold min-w-40 text-center"
                        )
                        ui.button(
                            icon="chevron_right",
                            on_click=lambda: change_month(1),
                        ).props("flat dense round")

                    with ui.element("div").classes("jf-finance-summary-grid"):
                        values = (
                            ("Dépenses", summary["expenses"], "jf-finance-expense"),
                            ("Revenus", summary["incomes"], "jf-finance-income"),
                            (
                                "Différence",
                                summary["difference"],
                                "jf-finance-income"
                                if summary["difference"] >= 0
                                else "jf-finance-expense",
                            ),
                        )
                        for label, value, css in values:
                            with ui.element("div").classes("jf-finance-summary"):
                                ui.label(label).classes("jf-finance-summary-label")
                                ui.label(_money(value)).classes(
                                    f"jf-finance-summary-value {css}"
                                )

                    if summary["planned_count"]:
                        with ui.element("div").classes("jf-finance-card"):
                            ui.label(
                                f"{summary['planned_count']} transaction(s) à confirmer"
                            ).classes("text-sm font-bold")

                    if goals:
                        ui.label("Objectifs du mois").classes(
                            "text-lg font-bold mt-1"
                        )
                        for goal in goals:
                            percent = max(0, min(100, goal["percentage"]))
                            with ui.element("div").classes("jf-finance-card"):
                                with ui.row().classes(
                                    "w-full justify-between gap-2"
                                ):
                                    ui.label(goal["target_name"]).classes(
                                        "text-sm font-bold"
                                    )
                                    ui.label(
                                        f"{_money(goal['spent'])} / "
                                        f"{_money(goal['available'])}"
                                    ).classes("text-xs font-bold")
                                with ui.element("div").classes(
                                    "jf-finance-progress mt-1"
                                ):
                                    ui.element("div").style(
                                        f"width:{percent:.1f}%"
                                    )
                                with ui.row().classes(
                                    "w-full justify-between gap-2"
                                ):
                                    ui.label(
                                        f"Reste : {_money(goal['remaining'])}"
                                    ).classes("text-xs jf-muted")
                                    if goal["carry_in"]:
                                        ui.label(
                                            f"Report : {_money(goal['carry_in'])}"
                                        ).classes("text-xs jf-muted")

            def change_month(offset):
                month_state["value"] = _shift_month(
                    month_state["value"], offset
                )
                render_dashboard.refresh()

            render_dashboard()

        # SAISIE
        with ui.tab_panel(entry_tab).classes("px-0"):
            with ui.card().classes("w-full max-w-2xl p-4"):
                ui.label("Saisie rapide").classes("text-xl font-bold")
                kind = ui.toggle(
                    TRANSACTION_TYPES, value="expense"
                ).props("dense spread no-caps").classes("w-full")
                with ui.element("div").classes("jf-finance-form-grid"):
                    amount = ui.number(
                        label="Montant", min=.01, step=.01, format="%.2f"
                    ).props("dense outlined").classes("jf-finance-field")
                    when = ui.input(
                        label="Date", value=date.today().isoformat()
                    ).props("type=date dense outlined").classes("jf-finance-field")
                    description = ui.input(
                        label="Description"
                    ).props("dense outlined maxlength=160").classes(
                        "jf-finance-field jf-finance-description"
                    )
                category = ui.select(
                    {None: "Aucune", **_category_options(user_id)},
                    label="Catégorie ou sous-catégorie",
                ).props("dense outlined clearable options-dense").classes("w-full")
                tags = ui.select(
                    _tag_options(user_id),
                    label="Étiquettes",
                    multiple=True,
                ).props("dense outlined use-chips clearable options-dense").classes(
                    "w-full"
                )
                with ui.expansion("Note et statut", icon="tune").classes("w-full"):
                    status = ui.select(
                        TRANSACTION_STATUSES,
                        value="confirmed",
                        label="Statut",
                    ).props("dense outlined options-dense").classes("w-full")
                    note = ui.textarea(
                        label="Note facultative"
                    ).props("dense outlined autogrow maxlength=1000").classes(
                        "w-full"
                    )

                def save_quick():
                    try:
                        save_transaction(
                            user_id=user_id,
                            transaction_date=when.value,
                            transaction_type=kind.value,
                            amount=amount.value,
                            description=description.value,
                            category_id=category.value,
                            tag_ids=tags.value or [],
                            note=note.value,
                            status=status.value,
                        )
                    except Exception as error:
                        ui.notify(str(error), type="warning")
                        return
                    amount.value = None
                    description.value = ""
                    note.value = ""
                    tags.value = []
                    ui.notify("Transaction enregistrée.", type="positive")
                    refresh_all()

                ui.button(
                    "Enregistrer", icon="save", on_click=save_quick
                ).props("color=primary").classes("mt-2")

        # HISTORIQUE
        with ui.tab_panel(history_tab).classes("px-0"):
            with ui.card().classes("w-full p-3"):
                ui.label("Historique compact").classes("text-lg font-bold")
                with ui.expansion("Filtres", icon="filter_alt").classes("w-full"):
                    with ui.element("div").classes("jf-finance-form-grid"):
                        start = ui.input(
                            label="Du",
                            value=month_state["value"].isoformat(),
                        ).props("type=date dense outlined").classes(
                            "jf-finance-field"
                        )
                        end = ui.input(
                            label="Au", value=date.today().isoformat()
                        ).props("type=date dense outlined").classes(
                            "jf-finance-field"
                        )
                        query = ui.input(
                            label="Recherche"
                        ).props("dense outlined clearable").classes(
                            "jf-finance-field jf-finance-description"
                        )
                    history_type = ui.select(
                        {"": "Tous", **TRANSACTION_TYPES},
                        value="",
                        label="Type",
                    ).props("dense outlined options-dense").classes("w-full")
                    history_status = ui.select(
                        {"": "Tous", **TRANSACTION_STATUSES},
                        value="",
                        label="Statut",
                    ).props("dense outlined options-dense").classes("w-full")
                    history_category = ui.select(
                        {None: "Toutes", **_category_options(user_id)},
                        value=None,
                        label="Catégorie",
                    ).props("dense outlined clearable options-dense").classes(
                        "w-full"
                    )
                    history_tag = ui.select(
                        {None: "Toutes", **_tag_options(user_id)},
                        value=None,
                        label="Étiquette",
                    ).props("dense outlined clearable options-dense").classes(
                        "w-full"
                    )
                    ui.button(
                        "Appliquer",
                        icon="filter_alt",
                        on_click=lambda: render_history.refresh(),
                    ).props("outline dense color=primary")

            history_box = ui.column().classes("jf-finance-list mt-2")

            def remove_dialog(row):
                with ui.dialog() as dialog:
                    with ui.card().classes("w-full max-w-md p-4"):
                        ui.label("Supprimer cette transaction?").classes(
                            "text-lg font-bold"
                        )
                        ui.label(
                            f"{row['description']} — "
                            f"{_signed(row['amount'], row['transaction_type'])}"
                        )
                        def remove():
                            delete_transaction(user_id, row["id"])
                            dialog.close()
                            ui.notify("Transaction supprimée.", type="positive")
                            refresh_all()
                        with ui.row().classes("w-full justify-end gap-2"):
                            ui.button(
                                "Annuler", on_click=dialog.close
                            ).props("flat")
                            ui.button(
                                "Supprimer", icon="delete", on_click=remove
                            ).props("color=negative")
                dialog.open()

            @ui.refreshable
            def render_history():
                history_box.clear()
                rows = list_transactions(
                    user_id,
                    start_date=start.value or None,
                    end_date=end.value or None,
                    transaction_type=history_type.value or None,
                    category_id=history_category.value or None,
                    tag_id=history_tag.value or None,
                    status=history_status.value or None,
                    query=query.value or None,
                )
                grouped = defaultdict(list)
                for row in rows:
                    grouped[row["transaction_date"]].append(row)
                with history_box:
                    if not rows:
                        ui.label("Aucune transaction.").classes(
                            "text-sm jf-muted p-3"
                        )
                    for day in sorted(grouped, reverse=True):
                        ui.label(day.strftime("%d/%m/%Y")).classes(
                            "jf-finance-day"
                        )
                        for row in grouped[day]:
                            with ui.element("div").classes("jf-finance-row"):
                                ui.label(row["description"]).classes(
                                    "jf-finance-main"
                                )
                                meta = []
                                if row["category_full_name"]:
                                    meta.append(row["category_full_name"])
                                if row["tag_names"]:
                                    meta.append(" • ".join(row["tag_names"]))
                                if row["status"] == "planned":
                                    meta.append("À confirmer")
                                ui.label(" — ".join(meta) or "Sans catégorie").classes(
                                    "jf-finance-meta"
                                )
                                amount_css = (
                                    "jf-finance-expense"
                                    if row["transaction_type"] == "expense"
                                    else "jf-finance-income"
                                )
                                ui.label(
                                    _signed(row["amount"], row["transaction_type"])
                                ).classes(
                                    f"jf-finance-amount {amount_css}"
                                )
                                with ui.element("div").classes(
                                    "jf-finance-actions"
                                ):
                                    if row["status"] == "planned":
                                        ui.button(
                                            icon="check",
                                            on_click=(
                                                lambda _event=None,
                                                selected=row["id"]:
                                                confirm_transaction(selected)
                                            ),
                                        ).props(
                                            "flat dense round size=sm color=positive"
                                        )
                                    ui.button(
                                        icon="edit",
                                        on_click=(
                                            lambda _event=None,
                                            selected=row["id"]:
                                            _transaction_dialog(
                                                user_id,
                                                refresh_all,
                                                get_transaction(user_id, selected),
                                            )
                                        ),
                                    ).props(
                                        "flat dense round size=sm color=primary"
                                    )
                                    ui.button(
                                        icon="delete",
                                        on_click=(
                                            lambda _event=None,
                                            selected=row:
                                            remove_dialog(selected)
                                        ),
                                    ).props(
                                        "flat dense round size=sm color=negative"
                                    )

            def confirm_transaction(transaction_id):
                set_transaction_status(
                    user_id, transaction_id, "confirmed"
                )
                ui.notify("Transaction confirmée.", type="positive")
                refresh_all()

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
                        category = ui.select(
                            {None: "Aucune", **_category_options(user_id)},
                            value=row["category_id"] if row else None,
                            label="Catégorie",
                        ).props("dense outlined clearable options-dense").classes(
                            "w-full"
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
                                    ui.label(
                                        f"Prochaine : {row['next_date'].strftime('%d/%m/%Y')} "
                                        f"— {CONFIRMATION_MODES[row['confirmation_mode']]}"
                                    ).classes("text-xs jf-muted")
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

        # ORGANISATION
        with ui.tab_panel(organization_tab).classes("px-0"):
            with ui.tabs().classes("w-full") as organization_tabs:
                categories_tab = ui.tab("Catégories")
                tags_tab = ui.tab("Étiquettes")

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

        # EXPORTER
        with ui.tab_panel(export_tab).classes("px-0"):
            with ui.card().classes("w-full max-w-2xl p-4"):
                ui.label("Exporter les données").classes("text-xl font-bold")
                ui.label(
                    "Le CSV convient à Excel. Le JSON constitue "
                    "une sauvegarde complète de sécurité."
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
        render_dashboard.refresh()
        render_history.refresh()
        render_recurrences.refresh()
        render_goals.refresh()
        render_categories.refresh()
        render_tags.refresh()
