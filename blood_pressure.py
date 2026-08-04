from __future__ import annotations

import asyncio
import json
import re
import tempfile
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from nicegui import run, ui

from blood_pressure_data import (
    count_blood_pressure_readings_on_date,
    create_blood_pressure_reading,
    delete_blood_pressure_reading,
    export_blood_pressure_data,
    get_blood_pressure_reminder_settings,
    get_blood_pressure_reminder_status,
    import_blood_pressure_rows,
    list_blood_pressure_readings,
    prepare_blood_pressure_import,
    save_blood_pressure_reminder_schedule,
    update_blood_pressure_reading,
)
from blood_pressure_pdf import (
    build_blood_pressure_pdf,
)


REPORT_DIRECTORY = (
    Path(
        tempfile.gettempdir()
    )
    / "jf_apps_pressure_reports"
)

EXPORT_DIRECTORY = (
    Path(
        tempfile.gettempdir()
    )
    / "jf_apps_pressure_exports"
)

_BACKGROUND_TASKS = set()


def _start_background_task(coroutine):
    task = asyncio.create_task(coroutine)
    _BACKGROUND_TASKS.add(task)

    def finish(done_task):
        _BACKGROUND_TASKS.discard(done_task)
        try:
            done_task.result()
        except asyncio.CancelledError:
            pass
        except Exception as error:
            print(
                "Tâche du Journal de pression interrompue :",
                error,
            )

    task.add_done_callback(finish)
    return task


BLOOD_PRESSURE_CSS = r"""
.jf-pressure-main-tabs {
    width: 100%;
    overflow: hidden;
    border-bottom: 1px solid var(--jf-border);
}
.jf-pressure-main-tabs .q-tabs__content {
    display: flex;
    flex-wrap: nowrap;
    justify-content: flex-start;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: thin;
}
.jf-pressure-main-tabs .q-tab {
    flex: 0 0 auto;
    min-width: max-content;
    padding-inline: .75rem;
}
.jf-pressure-main-tabs .q-tab__content {
    min-width: max-content;
}
.jf-pressure-main-tabs .q-tab__label {
    overflow: visible;
    white-space: nowrap;
    text-overflow: clip;
}
.jf-pressure-import-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
    gap: .55rem;
    width: 100%;
}
.jf-pressure-import-stat {
    padding: .65rem .75rem;
    border: 1px solid var(--jf-border);
    border-radius: 11px;
    background: var(--jf-surface);
}
.jf-pressure-import-row {
    display: grid;
    grid-template-columns: 5.2rem minmax(0, 1fr) 6.5rem;
    align-items: center;
    gap: .45rem;
    width: 100%;
    padding: .38rem .45rem;
    border: 1px solid var(--jf-border);
    border-radius: 9px;
    background: var(--jf-surface);
}
.jf-pressure-import-date {
    color: var(--jf-muted);
    font-size: .7rem;
    white-space: nowrap;
}
.jf-pressure-import-values {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: .78rem;
    font-weight: 760;
}
.jf-pressure-import-status {
    justify-self: end;
    font-size: .66rem;
    font-weight: 800;
    text-align: right;
}
@media (max-width: 650px) {
    .jf-pressure-main-tabs .q-tab {
        min-height: 3rem;
        padding-inline: .62rem;
    }
    .jf-pressure-main-tabs .q-tab__content {
        flex-direction: row;
        gap: .3rem;
    }
    .jf-pressure-main-tabs .q-tab__icon {
        margin-bottom: 0;
        font-size: 1.15rem;
    }
    .jf-pressure-main-tabs .q-tab__label {
        font-size: .7rem;
    }
}

.jf-pressure-grid {
    display: grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(
                min(100%, 13rem),
                1fr
            )
        );
    gap: 0.75rem;
    width: 100%;
}

.jf-pressure-reading-card {
    width: 100%;
    padding: 0.9rem;
    border: 1px solid var(--jf-border);
    border-radius: 15px;
    background: var(--jf-surface);
}

.jf-pressure-value {
    color: var(--jf-navy);
    font-size: 1.35rem;
    font-weight: 800;
}

.jf-pressure-day {
    width: 100%;
    padding: 0.75rem 0.9rem;
    border-left: 4px solid var(--jf-blue);
    border-radius: 12px;
    background: var(--jf-blue-soft);
}

.jf-pressure-history-filter-card {
    padding: 0.85rem 1rem;
}

.jf-pressure-history-filter-row {
    display: grid;
    grid-template-columns:
        minmax(10rem, 13rem)
        minmax(10rem, 13rem)
        auto;
    align-items: end;
    gap: 0.65rem;
    width: 100%;
    margin-top: 0.55rem;
}

.jf-pressure-history-date .q-field__control {
    min-height: 38px;
    height: 38px;
}

.jf-pressure-history-date .q-field__native,
.jf-pressure-history-date .q-field__input,
.jf-pressure-history-date .q-field__label {
    font-size: 0.82rem;
}

.jf-pressure-history-list {
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
    width: 100%;
    margin-top: 0.65rem;
}

.jf-pressure-history-day-card {
    width: 100%;
    overflow: hidden;
    border: 1px solid var(--jf-border);
    border-radius: 13px;
    background: var(--jf-surface);
}

.jf-pressure-history-day-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    width: 100%;
    padding: 0.42rem 0.7rem;
    border-left: 4px solid var(--jf-blue);
    background: var(--jf-blue-soft);
    font-size: 0.82rem;
}

.jf-pressure-history-row {
    display: grid;
    grid-template-columns:
        4.5rem
        6.2rem
        5.8rem
        minmax(0, 1fr)
        auto;
    grid-template-areas:
        "time pressure pulse note actions";
    align-items: center;
    gap: 0.45rem;
    min-height: 43px;
    padding: 0.32rem 0.55rem;
    border-top: 1px solid var(--jf-border);
}

.jf-pressure-history-time {
    grid-area: time;
    color: var(--jf-blue);
    font-size: 0.82rem;
    font-weight: 800;
}

.jf-pressure-history-pressure {
    grid-area: pressure;
    color: var(--jf-navy);
    font-size: 1.05rem;
    font-weight: 850;
}

.body--dark .jf-pressure-history-pressure {
    color: #dceaf6;
}

.jf-pressure-history-pulse {
    grid-area: pulse;
    font-size: 0.8rem;
}

.jf-pressure-history-note {
    grid-area: note;
    min-width: 0;
    overflow-wrap: anywhere;
    color: var(--jf-muted);
    font-size: 0.76rem;
}

.jf-pressure-history-actions {
    grid-area: actions;
    display: flex;
    gap: 0;
    justify-self: end;
}

@media (max-width: 650px) {
    .jf-pressure-history-filter-row {
        grid-template-columns: 1fr 1fr;
    }

    .jf-pressure-history-filter-button {
        grid-column: 1 / -1;
        justify-self: start;
    }

    .jf-pressure-history-row {
        grid-template-columns:
            4rem 5.8rem 1fr auto;
        grid-template-areas:
            "time pressure pulse actions"
            "note note note note";
        row-gap: 0.1rem;
    }

    .jf-pressure-history-note:empty {
        display: none;
    }
}

@media (max-width: 420px) {
    .jf-pressure-history-filter-row {
        grid-template-columns: 1fr;
    }

    .jf-pressure-history-filter-button {
        grid-column: auto;
    }

    .jf-pressure-history-row {
        grid-template-columns:
            3.7rem 5.4rem 1fr auto;
        padding-inline: 0.4rem;
    }
}

.jf-pressure-private {
    width: 100%;
    padding: 0.85rem 1rem;
    border-left: 4px solid #218f5c;
    border-radius: 12px;
    background: rgba(33, 143, 92, 0.08);
}

.jf-pressure-report-note {
    width: 100%;
    padding: 0.8rem 0.95rem;
    border-left: 4px solid var(--jf-gold);
    border-radius: 12px;
    background: rgba(189, 149, 85, 0.10);
}

.jf-pressure-portal-placeholder {
    width: 100%;
}

.jf-pressure-portal-alert {
    width: 100%;
    margin-top: 0.45rem;
    padding: 0.8rem 0.95rem;
    border: 1px solid rgba(191, 120, 18, 0.30);
    border-left: 5px solid #bf7812;
    border-radius: 14px;
    background: rgba(255, 244, 219, 0.92);
}

.body--dark .jf-pressure-portal-alert {
    background: rgba(111, 72, 18, 0.34);
}

.jf-pressure-reminder-preview {
    width: 100%;
    padding: 0.9rem 1rem;
    border: 1px solid var(--jf-border);
    border-radius: 14px;
    background: var(--jf-surface);
}

.jf-pressure-slot-card {
    width: 100%;
    padding: 0.95rem;
    border: 1px solid var(--jf-border);
    border-radius: 15px;
    background: var(--jf-surface);
}

.jf-pressure-slot-status {
    width: 100%;
    padding: 0.7rem 0.8rem;
    border-radius: 12px;
    background: rgba(34, 70, 122, 0.07);
}

.jf-pressure-quick-entry {
    width: 100%;
    padding: 0.85rem 1rem;
    border-left: 5px solid var(--jf-blue);
    border-radius: 13px;
    background: var(--jf-blue-soft);
}

.jf-pressure-alert-due {
    border-color: rgba(191, 120, 18, 0.30);
    border-left-color: #bf7812;
    background: rgba(255, 244, 219, 0.92);
}

.jf-pressure-alert-upcoming {
    border-color: rgba(34, 70, 122, 0.25);
    border-left-color: var(--jf-blue);
    background: rgba(231, 240, 250, 0.94);
}

.body--dark .jf-pressure-alert-upcoming {
    background: rgba(30, 58, 92, 0.42);
}
"""

ui.add_css(
    BLOOD_PRESSURE_CSS,
    shared=True,
)


def _date_text(value) -> str:
    if isinstance(value, date):
        normalized = value
    else:
        normalized = date.fromisoformat(
            str(value)
        )

    return normalized.strftime(
        "%d/%m/%Y"
    )


def _time_text(value) -> str:
    if hasattr(value, "strftime"):
        return value.strftime(
            "%H:%M"
        )

    return str(value or "")[:5]


def _cleanup_old_reports():
    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    cutoff = time.time() - (
        2 * 60 * 60
    )

    for path in REPORT_DIRECTORY.glob(
        "*.pdf"
    ):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink(
                    missing_ok=True
                )
        except OSError:
            pass


def _safe_filename_part(value) -> str:
    normalized = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        str(value or "").strip(),
    ).strip("_")

    return (
        normalized[:45]
        or "rapport"
    )


async def device_date_time():
    try:
        result = await ui.run_javascript(
            """
            const now = new Date();
            const pad = value =>
                String(value).padStart(2, '0');

            return {
                date:
                    now.getFullYear()
                    + '-'
                    + pad(now.getMonth() + 1)
                    + '-'
                    + pad(now.getDate()),
                time:
                    pad(now.getHours())
                    + ':'
                    + pad(now.getMinutes()),
            };
            """,
            timeout=8.0,
        )

        if (
            isinstance(result, dict)
            and result.get("date")
            and result.get("time")
        ):
            return (
                result["date"],
                result["time"],
            )
    except Exception:
        pass

    now = datetime.now()

    return (
        now.date().isoformat(),
        now.strftime("%H:%M"),
    )




def _hour_range_text(
    start_time,
    end_time,
) -> str:
    return (
        f"{_time_text(start_time)} "
        f"à {_time_text(end_time)}"
    )


def _reminder_state_text(
    status,
):
    next_slot = status.get(
        "next_slot"
    )
    remaining = int(
        status.get(
            "remaining_count"
        )
        or 0
    )

    if not next_slot:
        return (
            "",
            "",
            "upcoming",
        )

    label = next_slot["label"]
    hour_range = _hour_range_text(
        next_slot["start_time"],
        next_slot["end_time"],
    )

    if status["state"] == "due":
        main_text = (
            f"La prise « {label} » reste à faire aujourd’hui."
        )
        detail_text = (
            f"Plage suggérée : {hour_range}. "
            "Une prise faite en dehors de cette plage "
            "compte quand même."
        )
        visual_state = "due"
    else:
        main_text = (
            f"Il reste {remaining} prise(s) "
            "de pression aujourd’hui."
        )
        detail_text = (
            f"Prochaine prise suggérée : « {label} », "
            f"de {hour_range}."
        )
        visual_state = "upcoming"

    return (
        main_text,
        detail_text,
        visual_state,
    )


def _default_new_slot(
    current_slots,
):
    index = len(
        current_slots
    ) + 1

    defaults = [
        (
            "Matin",
            "06:00",
            "11:00",
        ),
        (
            "Soir",
            "17:00",
            "22:00",
        ),
        (
            "Après-midi",
            "12:00",
            "16:00",
        ),
    ]

    if index <= len(defaults):
        label, start_time, end_time = (
            defaults[
                index - 1
            ]
        )
    else:
        label = f"Prise {index}"
        start_time = "12:00"
        end_time = "13:00"

    return {
        "label": label,
        "start_time": start_time,
        "end_time": end_time,
    }


def blood_pressure_portal_reminder(
    user_id,
):
    """Affiche l’avis détaillé selon l’heure de l’appareil."""

    placeholder = ui.column().classes(
        "jf-pressure-portal-placeholder gap-0"
    )

    async def load_status():
        try:
            (
                device_date,
                device_time,
            ) = await device_date_time()

            status = (
                get_blood_pressure_reminder_status(
                    user_id,
                    device_date,
                    device_time,
                )
            )
        except Exception:
            return

        placeholder.clear()

        if (
            not status["active"]
            or status["remaining_count"] <= 0
        ):
            return

        (
            main_text,
            detail_text,
            visual_state,
        ) = _reminder_state_text(
            status
        )

        completed = status[
            "completed_count"
        ]
        target = status[
            "target_per_day"
        ]

        alert_class = (
            "jf-pressure-portal-alert "
            f"jf-pressure-alert-{visual_state}"
        )

        with placeholder:
            with ui.element("div").classes(
                alert_class
            ):
                with ui.row().classes(
                    "w-full items-center "
                    "justify-between gap-3 flex-wrap"
                ):
                    with ui.row().classes(
                        "items-start gap-3 flex-nowrap "
                        "grow min-w-0"
                    ):
                        ui.icon(
                            (
                                "notifications_active"
                                if visual_state
                                == "due"
                                else "schedule"
                            )
                        ).classes(
                            "text-3xl text-warning shrink-0"
                        )

                        with ui.column().classes(
                            "gap-0 grow min-w-0"
                        ):
                            ui.label(
                                "Journal de pression"
                            ).classes(
                                "font-bold"
                            )
                            ui.label(
                                main_text
                            ).classes(
                                "text-sm font-bold"
                            )
                            ui.label(
                                detail_text
                            ).classes(
                                "text-xs"
                            )
                            ui.label(
                                (
                                    f"{completed} sur {target} "
                                    "prise(s) complétée(s) "
                                    "aujourd’hui."
                                )
                            ).classes(
                                "text-xs jf-muted"
                            )

                    ui.button(
                        "Saisir maintenant",
                        icon="add_circle",
                        on_click=lambda: ui.navigate.to(
                            "/?tab=pression"
                            "&section=saisie"
                            "&quick=1"
                        ),
                    ).props(
                        "outline color=warning"
                    )

    status_guard = ui.element("span").classes("hidden")

    async def load_status_after_mount():
        await asyncio.sleep(0.15)
        if status_guard.is_deleted:
            return
        try:
            load_status()
        except RuntimeError:
            return

    _start_background_task(
        load_status_after_mount()
    )


def blood_pressure_panel(
    current_user,
    *,
    initial_section="saisie",
    quick_entry=False,
    show_heading=True,
):
    user_id = current_user["id"]
    today_server = date.today()
    default_start = (
        today_server
        - timedelta(
            days=30
        )
    )
    reminder_settings = (
        get_blood_pressure_reminder_settings(
            user_id
        )
    )
    reminder_default_start = (
        reminder_settings["start_date"]
        or today_server
    )
    reminder_default_end = (
        reminder_settings["end_date"]
        or (
            today_server
            + timedelta(
                days=13
            )
        )
    )

    if show_heading:
        with ui.row().classes(
            "w-full items-start justify-between "
            "gap-3 flex-wrap"
        ):
            with ui.column().classes(
                "gap-0"
            ):
                ui.label(
                    "Journal de pression"
                ).classes(
                    "text-2xl font-bold"
                )
                ui.label(
                    "Saisie privée de la pression "
                    "artérielle et du pouls."
                ).classes(
                    "text-sm jf-muted"
                )

            ui.icon(
                "monitor_heart"
            ).classes(
                "text-4xl text-primary"
            )

    with ui.element("div").classes(
        "jf-pressure-private"
    ):
        with ui.row().classes(
            "items-start gap-2 flex-nowrap"
        ):
            ui.icon(
                "lock"
            ).classes(
                "text-xl text-positive shrink-0"
            )
            ui.label(
                "Ces mesures appartiennent uniquement "
                "à votre compte. Elles ne sont jamais "
                "partagées avec une famille ou un autre utilisateur."
            ).classes(
                "text-sm"
            )

    with ui.tabs().props(
        "dense no-caps inline-label "
        "mobile-arrows outside-arrows align=left"
    ).classes(
        "jf-pressure-main-tabs"
    ) as tabs:
        entry_tab = ui.tab(
            "Saisie",
            icon="add_circle",
        )
        history_tab = ui.tab(
            "Historique",
            icon="history",
        )
        report_tab = ui.tab(
            "Rapport PDF",
            icon="picture_as_pdf",
        )
        reminder_tab = ui.tab(
            "Rappel",
            icon="notifications_active",
        )
        data_tab = ui.tab(
            "Données",
            icon="import_export",
        )

    normalized_section = str(
        initial_section
        or "saisie"
    ).strip().lower()

    initial_tab = {
        "saisie": entry_tab,
        "entry": entry_tab,
        "historique": history_tab,
        "history": history_tab,
        "rapport": report_tab,
        "pdf": report_tab,
        "rappel": reminder_tab,
        "reminder": reminder_tab,
        "donnees": data_tab,
        "données": data_tab,
        "data": data_tab,
        "import": data_tab,
        "export": data_tab,
    }.get(
        normalized_section,
        entry_tab,
    )

    with ui.tab_panels(
        tabs,
        value=initial_tab,
    ).classes(
        "w-full bg-transparent"
    ):
        # -------------------------------------------------
        # SAISIE
        # -------------------------------------------------
        with ui.tab_panel(
            entry_tab
        ).classes(
            "px-0"
        ):
            if quick_entry:
                with ui.element("div").classes(
                    "jf-pressure-quick-entry mb-3"
                ):
                    with ui.row().classes(
                        "items-start gap-2 flex-nowrap"
                    ):
                        ui.icon(
                            "bolt"
                        ).classes(
                            "text-2xl text-primary shrink-0"
                        )
                        with ui.column().classes(
                            "gap-0"
                        ):
                            ui.label(
                                "Saisie rapide depuis le Portail"
                            ).classes(
                                "font-bold"
                            )
                            ui.label(
                                "La date et l’heure de cet appareil "
                                "sont déjà proposées. Enregistrez la "
                                "mesure puis revenez directement au Portail."
                            ).classes(
                                "text-sm jf-muted"
                            )

            with ui.card().classes(
                "w-full p-5"
            ):
                with ui.row().classes(
                    "w-full items-start "
                    "justify-between gap-3 "
                    "flex-wrap"
                ):
                    with ui.column().classes(
                        "gap-0"
                    ):
                        ui.label(
                            "Nouvelle mesure"
                        ).classes(
                            "text-xl font-bold"
                        )
                        ui.label(
                            "La date et l’heure de "
                            "cet appareil sont proposées "
                            "automatiquement et restent modifiables."
                        ).classes(
                            "text-sm jf-muted"
                        )

                    today_count_label = ui.label(
                        ""
                    ).classes(
                        "text-sm bg-gray-100 "
                        "rounded-full px-3 py-1"
                    )

                with ui.element(
                    "div"
                ).classes(
                    "jf-pressure-grid mt-2"
                ):
                    measured_date_input = ui.input(
                        label="Date",
                    ).props(
                        "type=date"
                    ).classes(
                        "w-full"
                    )

                    measured_time_input = ui.input(
                        label="Heure",
                    ).props(
                        "type=time step=60"
                    ).classes(
                        "w-full"
                    )

                    systolic_input = ui.number(
                        label="Systolique",
                        min=1,
                        max=400,
                        step=1,
                    ).props(
                        (
                            "inputmode=numeric autofocus"
                            if quick_entry
                            else "inputmode=numeric"
                        )
                    ).classes(
                        "w-full"
                    )

                    diastolic_input = ui.number(
                        label="Diastolique",
                        min=1,
                        max=300,
                        step=1,
                    ).props(
                        "inputmode=numeric"
                    ).classes(
                        "w-full"
                    )

                    pulse_input = ui.number(
                        label="Pouls",
                        min=1,
                        max=300,
                        step=1,
                    ).props(
                        "inputmode=numeric"
                    ).classes(
                        "w-full"
                    )

                note_input = ui.textarea(
                    label="Note facultative",
                    placeholder=(
                        "Ex. avant le déjeuner, "
                        "après une marche, médicament…"
                    ),
                ).props(
                    "maxlength=1000 autogrow"
                ).classes(
                    "w-full"
                )

                ui.label(
                    "Les valeurs sont enregistrées telles "
                    "que vous les saisissez. Cette phase "
                    "ne calcule aucune moyenne et ne donne "
                    "aucune interprétation médicale."
                ).classes(
                    "text-xs jf-muted"
                )

                @ui.refreshable
                def refresh_today_count():
                    selected_date = (
                        measured_date_input.value
                        or date.today().isoformat()
                    )

                    try:
                        count = (
                            count_blood_pressure_readings_on_date(
                                user_id,
                                selected_date,
                            )
                        )
                    except ValueError:
                        count = 0

                    if count == 0:
                        text = (
                            "Aucune mesure à cette date"
                        )
                    elif count == 1:
                        text = (
                            "1 mesure à cette date"
                        )
                    else:
                        text = (
                            f"{count} mesures à cette date"
                        )

                    today_count_label.set_text(
                        text
                    )

                async def use_device_now():
                    (
                        device_date,
                        device_time,
                    ) = await device_date_time()

                    measured_date_input.value = (
                        device_date
                    )
                    measured_time_input.value = (
                        device_time
                    )
                    refresh_today_count.refresh()

                def clear_measure_values():
                    systolic_input.value = None
                    diastolic_input.value = None
                    pulse_input.value = None
                    note_input.value = ""

                async def save_reading(
                    *,
                    return_to_portal=False,
                ):
                    try:
                        create_blood_pressure_reading(
                            user_id,
                            measured_date_input.value,
                            measured_time_input.value,
                            systolic_input.value,
                            diastolic_input.value,
                            pulse_input.value,
                            note_input.value,
                        )
                    except ValueError as error:
                        ui.notify(
                            str(error),
                            type="warning",
                        )
                        return
                    except Exception:
                        ui.notify(
                            "La mesure n’a pas pu "
                            "être enregistrée.",
                            type="negative",
                        )
                        return

                    ui.notify(
                        "Mesure enregistrée.",
                        type="positive",
                    )

                    render_history.refresh()

                    if return_to_portal:
                        ui.navigate.to(
                            "/?tab=portail"
                        )
                        return

                    clear_measure_values()
                    await use_device_now()

                    if quick_entry:
                        try:
                            await ui.run_javascript(
                                """
                                setTimeout(() => {
                                    const field =
                                        document.querySelector(
                                            'input[autofocus]'
                                        );
                                    if (field) {
                                        field.focus();
                                    }
                                }, 120);
                                """,
                                timeout=3.0,
                            )
                        except Exception:
                            pass

                async def save_and_return():
                    await save_reading(
                        return_to_portal=True
                    )

                measured_date_input.on_value_change(
                    lambda event: (
                        refresh_today_count.refresh()
                    )
                )

                with ui.row().classes(
                    "w-full gap-2 flex-wrap mt-2"
                ):
                    ui.button(
                        "Enregistrer",
                        icon="save",
                        on_click=save_reading,
                    ).props(
                        "color=primary"
                    )

                    if quick_entry:
                        ui.button(
                            "Enregistrer et revenir au Portail",
                            icon="keyboard_return",
                            on_click=save_and_return,
                        ).props(
                            "outline color=primary"
                        )

                    ui.button(
                        "Date et heure actuelles",
                        icon="schedule",
                        on_click=use_device_now,
                    ).props(
                        "outline color=primary"
                    )

                entry_guard = ui.element("span").classes("hidden")

                async def use_device_after_mount():
                    await asyncio.sleep(0.15)
                    if entry_guard.is_deleted:
                        return
                    try:
                        await use_device_now()
                    except RuntimeError:
                        return

                _start_background_task(
                    use_device_after_mount()
                )

        # -------------------------------------------------
        # HISTORIQUE
        # -------------------------------------------------
        with ui.tab_panel(
            history_tab
        ).classes(
            "px-0"
        ):
            with ui.card().classes(
                "w-full jf-pressure-history-filter-card"
            ):
                with ui.row().classes(
                    "w-full items-start "
                    "justify-between gap-2 flex-wrap"
                ):
                    with ui.column().classes(
                        "gap-0"
                    ):
                        ui.label(
                            "Historique"
                        ).classes(
                            "text-lg font-bold"
                        )
                        ui.label(
                            "Filtrez, modifiez ou supprimez "
                            "vos propres mesures."
                        ).classes(
                            "text-xs jf-muted"
                        )

                with ui.element(
                    "div"
                ).classes(
                    "jf-pressure-history-filter-row"
                ):
                    history_start_input = ui.input(
                        label="Du",
                        value=default_start.isoformat(),
                    ).props(
                        "type=date dense outlined"
                    ).classes(
                        "jf-pressure-history-date"
                    )

                    history_end_input = ui.input(
                        label="Au",
                        value=today_server.isoformat(),
                    ).props(
                        "type=date dense outlined"
                    ).classes(
                        "jf-pressure-history-date"
                    )

                    ui.button(
                        "Appliquer",
                        icon="filter_alt",
                        on_click=lambda: (
                            render_history.refresh()
                        ),
                    ).props(
                        "outline dense color=primary"
                    ).classes(
                        "jf-pressure-history-filter-button"
                    )

            def open_edit_dialog(
                reading,
            ):
                with ui.dialog() as dialog:
                    with ui.card().classes(
                        "w-full max-w-2xl p-5"
                    ):
                        ui.label(
                            "Modifier la mesure"
                        ).classes(
                            "text-xl font-bold"
                        )

                        with ui.element(
                            "div"
                        ).classes(
                            "jf-pressure-grid"
                        ):
                            edit_date = ui.input(
                                label="Date",
                                value=reading[
                                    "measured_date"
                                ].isoformat(),
                            ).props(
                                "type=date"
                            ).classes(
                                "w-full"
                            )

                            edit_time = ui.input(
                                label="Heure",
                                value=_time_text(
                                    reading[
                                        "measured_time"
                                    ]
                                ),
                            ).props(
                                "type=time step=60"
                            ).classes(
                                "w-full"
                            )

                            edit_systolic = ui.number(
                                label="Systolique",
                                value=reading[
                                    "systolic"
                                ],
                                min=1,
                                max=400,
                                step=1,
                            ).classes(
                                "w-full"
                            )

                            edit_diastolic = ui.number(
                                label="Diastolique",
                                value=reading[
                                    "diastolic"
                                ],
                                min=1,
                                max=300,
                                step=1,
                            ).classes(
                                "w-full"
                            )

                            edit_pulse = ui.number(
                                label="Pouls",
                                value=reading[
                                    "pulse"
                                ],
                                min=1,
                                max=300,
                                step=1,
                            ).classes(
                                "w-full"
                            )

                        edit_note = ui.textarea(
                            label="Note facultative",
                            value=reading[
                                "note"
                            ] or "",
                        ).props(
                            "maxlength=1000 autogrow"
                        ).classes(
                            "w-full"
                        )

                        def save_edit():
                            try:
                                update_blood_pressure_reading(
                                    user_id,
                                    reading["id"],
                                    edit_date.value,
                                    edit_time.value,
                                    edit_systolic.value,
                                    edit_diastolic.value,
                                    edit_pulse.value,
                                    edit_note.value,
                                )
                            except ValueError as error:
                                ui.notify(
                                    str(error),
                                    type="warning",
                                )
                                return
                            except Exception:
                                ui.notify(
                                    "La modification "
                                    "a échoué.",
                                    type="negative",
                                )
                                return

                            dialog.close()
                            ui.notify(
                                "Mesure modifiée.",
                                type="positive",
                            )
                            render_history.refresh()
                            refresh_today_count.refresh()

                        with ui.row().classes(
                            "w-full justify-end "
                            "gap-2 mt-3"
                        ):
                            ui.button(
                                "Annuler",
                                on_click=dialog.close,
                            ).props(
                                "flat"
                            )
                            ui.button(
                                "Enregistrer",
                                icon="save",
                                on_click=save_edit,
                            ).props(
                                "color=primary"
                            )

                dialog.open()

            def confirm_delete(
                reading,
            ):
                with ui.dialog() as dialog:
                    with ui.card().classes(
                        "w-full max-w-md p-5"
                    ):
                        ui.label(
                            "Supprimer cette mesure?"
                        ).classes(
                            "text-xl font-bold"
                        )
                        ui.label(
                            (
                                f"{_date_text(reading['measured_date'])} "
                                f"à {_time_text(reading['measured_time'])} "
                                f"- {reading['systolic']}/"
                                f"{reading['diastolic']}, "
                                f"pouls {reading['pulse']}"
                            )
                        ).classes(
                            "text-sm jf-muted"
                        )
                        ui.label(
                            "Cette suppression est définitive."
                        ).classes(
                            "text-sm text-negative"
                        )

                        def delete_confirmed():
                            try:
                                delete_blood_pressure_reading(
                                    user_id,
                                    reading["id"],
                                )
                            except ValueError as error:
                                ui.notify(
                                    str(error),
                                    type="warning",
                                )
                                return
                            except Exception:
                                ui.notify(
                                    "La suppression "
                                    "a échoué.",
                                    type="negative",
                                )
                                return

                            dialog.close()
                            ui.notify(
                                "Mesure supprimée.",
                                type="positive",
                            )
                            render_history.refresh()
                            refresh_today_count.refresh()

                        with ui.row().classes(
                            "w-full justify-end "
                            "gap-2 mt-3"
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
                                on_click=delete_confirmed,
                            ).props(
                                "color=negative"
                            )

                dialog.open()

            @ui.refreshable
            def render_history():
                try:
                    start_value = (
                        history_start_input.value
                    )
                    end_value = (
                        history_end_input.value
                    )

                    if (
                        start_value
                        and end_value
                        and end_value < start_value
                    ):
                        ui.label(
                            "La date de fin doit être "
                            "égale ou postérieure "
                            "à la date de début."
                        ).classes(
                            "text-negative mt-2"
                        )
                        return

                    readings = (
                        list_blood_pressure_readings(
                            user_id,
                            start_value or None,
                            end_value or None,
                        )
                    )
                except ValueError as error:
                    ui.label(
                        str(error)
                    ).classes(
                        "text-negative mt-2"
                    )
                    return
                except Exception:
                    ui.label(
                        "L’historique n’a pas pu "
                        "être chargé."
                    ).classes(
                        "text-negative mt-2"
                    )
                    return

                if not readings:
                    with ui.card().classes(
                        "w-full p-5 items-center "
                        "text-center mt-2"
                    ):
                        ui.icon(
                            "monitor_heart"
                        ).classes(
                            "text-4xl text-gray-400"
                        )
                        ui.label(
                            "Aucune mesure "
                            "dans cet intervalle"
                        ).classes(
                            "text-lg font-bold"
                        )
                    return

                grouped = defaultdict(
                    list
                )

                for reading in readings:
                    grouped[
                        reading[
                            "measured_date"
                        ]
                    ].append(
                        reading
                    )

                with ui.element(
                    "div"
                ).classes(
                    "jf-pressure-history-list"
                ):
                    for day in sorted(
                        grouped,
                        reverse=True,
                    ):
                        with ui.element(
                            "section"
                        ).classes(
                            "jf-pressure-history-day-card"
                        ):
                            with ui.element(
                                "div"
                            ).classes(
                                "jf-pressure-history-day-header"
                            ):
                                ui.label(
                                    _date_text(
                                        day
                                    )
                                ).classes(
                                    "font-bold"
                                )
                                ui.label(
                                    (
                                        "1 mesure"
                                        if len(
                                            grouped[
                                                day
                                            ]
                                        ) == 1
                                        else (
                                            f"{len(grouped[day])} "
                                            "mesures"
                                        )
                                    )
                                ).classes(
                                    "text-xs jf-muted"
                                )

                            for reading in sorted(
                                grouped[
                                    day
                                ],
                                key=lambda item: (
                                    item[
                                        "measured_time"
                                    ],
                                    item[
                                        "id"
                                    ],
                                ),
                            ):
                                with ui.element(
                                    "div"
                                ).classes(
                                    "jf-pressure-history-row"
                                ):
                                    ui.label(
                                        _time_text(
                                            reading[
                                                "measured_time"
                                            ]
                                        )
                                    ).classes(
                                        "jf-pressure-history-time"
                                    )

                                    ui.label(
                                        (
                                            f"{reading['systolic']}/"
                                            f"{reading['diastolic']}"
                                        )
                                    ).classes(
                                        "jf-pressure-history-pressure"
                                    )

                                    ui.label(
                                        (
                                            f"Pouls {reading['pulse']}"
                                        )
                                    ).classes(
                                        "jf-pressure-history-pulse"
                                    )

                                    ui.label(
                                        reading[
                                            "note"
                                        ] or ""
                                    ).classes(
                                        "jf-pressure-history-note"
                                    )

                                    with ui.element(
                                        "div"
                                    ).classes(
                                        "jf-pressure-history-actions"
                                    ):
                                        ui.button(
                                            icon="edit",
                                            on_click=(
                                                lambda selected=reading:
                                                open_edit_dialog(
                                                    selected
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
                                                lambda selected=reading:
                                                confirm_delete(
                                                    selected
                                                )
                                            ),
                                        ).props(
                                            "flat dense round "
                                            "size=sm color=negative"
                                        ).tooltip(
                                            "Supprimer"
                                        )

            render_history()

        # -------------------------------------------------
        # RAPPORT PDF
        # -------------------------------------------------
        with ui.tab_panel(
            report_tab
        ).classes(
            "px-0"
        ):
            with ui.card().classes(
                "w-full p-5"
            ):
                ui.label(
                    "Rapport PDF"
                ).classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "Choisissez le nom à imprimer "
                    "et l’intervalle du rapport."
                ).classes(
                    "text-sm jf-muted"
                )

                report_name_input = ui.input(
                    label="Nom complet à imprimer",
                    value=current_user[
                        "display_name"
                    ],
                ).props(
                    "autocomplete=name"
                ).classes(
                    "w-full"
                )

                with ui.row().classes(
                    "w-full gap-3 flex-wrap"
                ):
                    report_start_input = ui.input(
                        label="Date de début",
                        value=default_start.isoformat(),
                    ).props(
                        "type=date"
                    ).classes(
                        "grow min-w-[180px]"
                    )

                    report_end_input = ui.input(
                        label="Date de fin",
                        value=today_server.isoformat(),
                    ).props(
                        "type=date"
                    ).classes(
                        "grow min-w-[180px]"
                    )

                recipient_input = ui.input(
                    label=(
                        "Courriel du destinataire "
                        "(facultatif)"
                    ),
                    placeholder=(
                        "Ex. clinique@exemple.ca"
                    ),
                ).props(
                    "type=email autocomplete=email"
                ).classes(
                    "w-full"
                )

                with ui.element(
                    "div"
                ).classes(
                    "jf-pressure-report-note"
                ):
                    ui.label(
                        "Chaque date de l’intervalle "
                        "apparaît dans le PDF. Lorsqu’il "
                        "n’existe aucune mesure, le rapport "
                        "indique « Aucune donnée pour ce jour »."
                    ).classes(
                        "text-sm"
                    )

                async def generate_report():
                    full_name = str(
                        report_name_input.value
                        or ""
                    ).strip()
                    start_value = (
                        report_start_input.value
                    )
                    end_value = (
                        report_end_input.value
                    )

                    if not full_name:
                        ui.notify(
                            "Inscrivez le nom complet "
                            "à imprimer.",
                            type="warning",
                        )
                        return

                    if (
                        not start_value
                        or not end_value
                    ):
                        ui.notify(
                            "Choisissez les deux dates "
                            "du rapport.",
                            type="warning",
                        )
                        return

                    if end_value < start_value:
                        ui.notify(
                            "La date de fin doit être "
                            "égale ou postérieure "
                            "à la date de début.",
                            type="warning",
                        )
                        return

                    try:
                        readings = (
                            list_blood_pressure_readings(
                                user_id,
                                start_value,
                                end_value,
                            )
                        )

                        _cleanup_old_reports()

                        filename = (
                            "journal_pression_"
                            f"{_safe_filename_part(full_name)}_"
                            f"{start_value}_"
                            f"{end_value}.pdf"
                        )

                        output_path = (
                            REPORT_DIRECTORY
                            / (
                                f"{user_id}_"
                                f"{int(time.time() * 1000)}_"
                                f"{filename}"
                            )
                        )

                        await run.io_bound(
                            build_blood_pressure_pdf,
                            full_name=full_name,
                            start_date=start_value,
                            end_date=end_value,
                            readings=readings,
                            output_path=output_path,
                        )

                        ui.download(
                            str(output_path),
                            filename=filename,
                        )

                        ui.notify(
                            "Le PDF est prêt.",
                            type="positive",
                        )
                    except ValueError as error:
                        ui.notify(
                            str(error),
                            type="warning",
                        )
                    except Exception:
                        ui.notify(
                            "Le PDF n’a pas pu "
                            "être produit.",
                            type="negative",
                        )

                async def prepare_email():
                    full_name = str(
                        report_name_input.value
                        or ""
                    ).strip()
                    start_value = (
                        report_start_input.value
                        or ""
                    )
                    end_value = (
                        report_end_input.value
                        or ""
                    )

                    subject = (
                        "Journal de pression artérielle"
                    )
                    try:
                        display_start = _date_text(
                            start_value
                        )
                        display_end = _date_text(
                            end_value
                        )
                    except ValueError:
                        display_start = start_value
                        display_end = end_value

                    body = (
                        "Bonjour,\n\n"
                        "Veuillez trouver mon journal "
                        "de pression artérielle pour la période "
                        f"du {display_start} au {display_end}.\n\n"
                        f"Nom : {full_name}\n\n"
                        "Le fichier PDF doit être joint "
                        "manuellement à ce courriel.\n"
                    )

                    recipient = str(
                        recipient_input.value
                        or ""
                    ).strip()

                    mailto_url = (
                        f"mailto:{quote(recipient)}"
                        f"?subject={quote(subject)}"
                        f"&body={quote(body)}"
                    )

                    await ui.run_javascript(
                        (
                            "window.location.href = "
                            + json.dumps(
                                mailto_url
                            )
                            + ";"
                        ),
                        timeout=5.0,
                    )

                with ui.row().classes(
                    "w-full gap-2 flex-wrap mt-2"
                ):
                    ui.button(
                        "Générer le PDF",
                        icon="picture_as_pdf",
                        on_click=generate_report,
                    ).props(
                        "color=primary"
                    )

                    ui.button(
                        "Préparer le courriel",
                        icon="email",
                        on_click=prepare_email,
                    ).props(
                        "outline color=primary"
                    )

                ui.label(
                    "Le navigateur ou l’appareil de courriel "
                    "ne permet pas toujours d’ajouter "
                    "automatiquement une pièce jointe. "
                    "Générez d’abord le PDF, puis joignez-le "
                    "au message préparé."
                ).classes(
                    "text-xs jf-muted"
                )

        # -------------------------------------------------
        # RAPPEL DU PORTAIL
        # -------------------------------------------------
        with ui.tab_panel(
            reminder_tab
        ).classes(
            "px-0"
        ):
            with ui.card().classes(
                "w-full p-5"
            ):
                ui.label(
                    "Horaires et rappel"
                ).classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "Choisissez vos propres plages horaires "
                    "pour chaque prise quotidienne."
                ).classes(
                    "text-sm jf-muted"
                )

                reminder_enabled_input = ui.checkbox(
                    (
                        "Afficher un avis sur le Portail "
                        "lorsqu’une prise reste à faire"
                    ),
                    value=bool(
                        reminder_settings[
                            "enabled"
                        ]
                    ),
                )

                with ui.row().classes(
                    "w-full gap-3 flex-wrap mt-2"
                ):
                    reminder_start_input = ui.input(
                        label="Date de début",
                        value=(
                            reminder_default_start
                            .isoformat()
                        ),
                    ).props(
                        "type=date"
                    ).classes(
                        "grow min-w-[180px]"
                    )

                    reminder_end_input = ui.input(
                        label="Date de fin",
                        value=(
                            reminder_default_end
                            .isoformat()
                        ),
                    ).props(
                        "type=date"
                    ).classes(
                        "grow min-w-[180px]"
                    )

                ui.label(
                    "Les plages servent de repères pour les avis. "
                    "Toute mesure enregistrée dans la journée "
                    "compte comme une prise, même hors plage."
                ).classes(
                    "text-xs jf-muted"
                )

                slot_models = [
                    {
                        "label": slot[
                            "label"
                        ],
                        "start_time": (
                            _time_text(
                                slot[
                                    "start_time"
                                ]
                            )
                        ),
                        "end_time": (
                            _time_text(
                                slot[
                                    "end_time"
                                ]
                            )
                        ),
                    }
                    for slot in reminder_settings[
                        "slots"
                    ]
                ]

                def update_slot(
                    index,
                    field,
                    value,
                ):
                    if (
                        0
                        <= index
                        < len(slot_models)
                    ):
                        slot_models[
                            index
                        ][field] = value

                def remove_slot(index):
                    if len(slot_models) <= 1:
                        ui.notify(
                            "Conservez au moins "
                            "une prise quotidienne.",
                            type="warning",
                        )
                        return

                    if (
                        0
                        <= index
                        < len(slot_models)
                    ):
                        slot_models.pop(
                            index
                        )
                        render_slots.refresh()

                def add_slot():
                    if len(slot_models) >= 10:
                        ui.notify(
                            "Un maximum de 10 prises "
                            "peut être configuré.",
                            type="warning",
                        )
                        return

                    slot_models.append(
                        _default_new_slot(
                            slot_models
                        )
                    )
                    render_slots.refresh()

                @ui.refreshable
                def render_slots():
                    ui.label(
                        (
                            "1 prise quotidienne"
                            if len(slot_models) == 1
                            else (
                                f"{len(slot_models)} "
                                "prises quotidiennes"
                            )
                        )
                    ).classes(
                        "text-lg font-bold mt-4"
                    )

                    with ui.column().classes(
                        "w-full gap-3 mt-1"
                    ):
                        for index, slot in enumerate(
                            slot_models
                        ):
                            with ui.element(
                                "div"
                            ).classes(
                                "jf-pressure-slot-card"
                            ):
                                with ui.row().classes(
                                    "w-full items-center "
                                    "justify-between gap-2"
                                ):
                                    ui.label(
                                        f"Prise {index + 1}"
                                    ).classes(
                                        "font-bold"
                                    )

                                    if len(
                                        slot_models
                                    ) > 1:
                                        ui.button(
                                            icon="delete",
                                            on_click=(
                                                lambda _=None,
                                                selected=index:
                                                remove_slot(
                                                    selected
                                                )
                                            ),
                                        ).props(
                                            "flat round color=negative"
                                        ).tooltip(
                                            "Retirer cette prise"
                                        )

                                with ui.element(
                                    "div"
                                ).classes(
                                    "jf-pressure-grid mt-2"
                                ):
                                    label_input = ui.input(
                                        label="Nom",
                                        value=slot[
                                            "label"
                                        ],
                                        placeholder=(
                                            "Ex. Matin"
                                        ),
                                    ).props(
                                        "maxlength=60"
                                    ).classes(
                                        "w-full"
                                    )

                                    start_input = ui.input(
                                        label="Début",
                                        value=slot[
                                            "start_time"
                                        ],
                                    ).props(
                                        "type=time step=60"
                                    ).classes(
                                        "w-full"
                                    )

                                    end_input = ui.input(
                                        label="Fin",
                                        value=slot[
                                            "end_time"
                                        ],
                                    ).props(
                                        "type=time step=60"
                                    ).classes(
                                        "w-full"
                                    )

                                    label_input.on_value_change(
                                        (
                                            lambda event,
                                            selected=index:
                                            update_slot(
                                                selected,
                                                "label",
                                                event.value,
                                            )
                                        )
                                    )
                                    start_input.on_value_change(
                                        (
                                            lambda event,
                                            selected=index:
                                            update_slot(
                                                selected,
                                                "start_time",
                                                event.value,
                                            )
                                        )
                                    )
                                    end_input.on_value_change(
                                        (
                                            lambda event,
                                            selected=index:
                                            update_slot(
                                                selected,
                                                "end_time",
                                                event.value,
                                            )
                                        )
                                    )

                render_slots()

                ui.button(
                    "Ajouter une prise",
                    icon="add",
                    on_click=add_slot,
                ).props(
                    "outline color=primary"
                ).classes(
                    "mt-2"
                )

                with ui.element(
                    "div"
                ).classes(
                    "jf-pressure-report-note mt-3"
                ):
                    ui.label(
                        "Les plages ne peuvent pas se chevaucher "
                        "et doivent commencer et finir dans la "
                        "même journée. Elles restent toutefois "
                        "indicatives : une prise faite plus tôt "
                        "ou plus tard compte quand même."
                    ).classes(
                        "text-sm"
                    )

                preview_container = ui.column().classes(
                    "w-full gap-2 mt-3"
                )

                async def refresh_reminder_preview():
                    try:
                        (
                            device_date,
                            device_time,
                        ) = await device_date_time()

                        status = (
                            get_blood_pressure_reminder_status(
                                user_id,
                                device_date,
                                device_time,
                            )
                        )
                    except Exception:
                        return

                    preview_container.clear()

                    with preview_container:
                        with ui.element(
                            "div"
                        ).classes(
                            "jf-pressure-reminder-preview"
                        ):
                            ui.label(
                                "État du rappel aujourd’hui"
                            ).classes(
                                "font-bold"
                            )

                            if not status[
                                "configured"
                            ]:
                                ui.label(
                                    "Enregistrez d’abord "
                                    "vos horaires."
                                ).classes(
                                    "text-sm jf-muted"
                                )
                            elif not status[
                                "enabled"
                            ]:
                                ui.label(
                                    "Le rappel est désactivé."
                                ).classes(
                                    "text-sm jf-muted"
                                )
                            elif not status[
                                "active"
                            ]:
                                ui.label(
                                    "La date d’aujourd’hui "
                                    "se trouve en dehors "
                                    "de la période configurée."
                                ).classes(
                                    "text-sm jf-muted"
                                )
                            elif status[
                                "remaining_count"
                            ] == 0:
                                ui.label(
                                    (
                                        "Toutes les prises "
                                        "prévues aujourd’hui "
                                        "sont complétées."
                                    )
                                ).classes(
                                    "text-sm text-positive"
                                )
                            else:
                                (
                                    main_text,
                                    detail_text,
                                    _,
                                ) = _reminder_state_text(
                                    status
                                )
                                ui.label(
                                    main_text
                                ).classes(
                                    (
                                        "text-sm text-warning"
                                        if status["state"]
                                        == "due"
                                        else "text-sm text-primary"
                                    )
                                )
                                ui.label(
                                    detail_text
                                ).classes(
                                    "text-xs jf-muted"
                                )

                        if status[
                            "configured"
                        ]:
                            for slot in status[
                                "slots"
                            ]:
                                with ui.element(
                                    "div"
                                ).classes(
                                    "jf-pressure-slot-status"
                                ):
                                    with ui.row().classes(
                                        "w-full items-center "
                                        "justify-between gap-2 "
                                        "flex-wrap"
                                    ):
                                        with ui.column().classes(
                                            "gap-0"
                                        ):
                                            ui.label(
                                                slot[
                                                    "label"
                                                ]
                                            ).classes(
                                                "font-bold"
                                            )
                                            ui.label(
                                                _hour_range_text(
                                                    slot[
                                                        "start_time"
                                                    ],
                                                    slot[
                                                        "end_time"
                                                    ],
                                                )
                                            ).classes(
                                                "text-xs jf-muted"
                                            )

                                        if slot[
                                            "status"
                                        ] == "completed":
                                            status_text = (
                                                "Complétée à "
                                                f"{_time_text(slot['completed_time'])}"
                                            )
                                            status_class = (
                                                "text-positive"
                                            )
                                        elif slot[
                                            "status"
                                        ] == "due":
                                            status_text = (
                                                "À prendre aujourd’hui"
                                            )
                                            status_class = (
                                                "text-warning"
                                            )
                                        else:
                                            status_text = (
                                                "À venir"
                                            )
                                            status_class = (
                                                "text-primary"
                                            )

                                        ui.label(
                                            status_text
                                        ).classes(
                                            f"text-sm {status_class}"
                                        )

                async def save_reminder():
                    try:
                        save_blood_pressure_reminder_schedule(
                            user_id,
                            enabled=(
                                reminder_enabled_input.value
                            ),
                            start_date=(
                                reminder_start_input.value
                            ),
                            end_date=(
                                reminder_end_input.value
                            ),
                            slots=slot_models,
                        )
                    except ValueError as error:
                        ui.notify(
                            str(error),
                            type="warning",
                        )
                        return
                    except Exception:
                        ui.notify(
                            "Les horaires n’ont pas pu "
                            "être enregistrés.",
                            type="negative",
                        )
                        return

                    ui.notify(
                        "Horaires et rappel enregistrés.",
                        type="positive",
                    )

                    await refresh_reminder_preview()

                with ui.row().classes(
                    "w-full gap-2 flex-wrap mt-3"
                ):
                    ui.button(
                        "Enregistrer les horaires",
                        icon="save",
                        on_click=save_reminder,
                    ).props(
                        "color=primary"
                    )

                    ui.button(
                        "Actualiser l’état",
                        icon="refresh",
                        on_click=(
                            refresh_reminder_preview
                        ),
                    ).props(
                        "outline color=primary"
                    )

                ui.label(
                    "L’avis est affiché dans la grande carte "
                    "de bienvenue du Portail. Il ne s’agit "
                    "pas d’une notification poussée."
                ).classes(
                    "text-xs jf-muted"
                )

                reminder_guard = ui.element("span").classes("hidden")

                async def refresh_reminder_after_mount():
                    await asyncio.sleep(0.15)
                    if reminder_guard.is_deleted:
                        return
                    try:
                        await refresh_reminder_preview()
                    except RuntimeError:
                        return

                _start_background_task(
                    refresh_reminder_after_mount()
                )


        # -------------------------------------------------
        # DONNÉES PRIVÉES
        # -------------------------------------------------
        with ui.tab_panel(
            data_tab
        ).classes(
            "px-0"
        ):
            with ui.card().classes(
                "w-full max-w-4xl p-5"
            ):
                ui.label(
                    "Importer une sauvegarde"
                ).classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "Formats reconnus : CSV et JSON produits "
                    "par JF Apps. Une prévisualisation est toujours "
                    "affichée avant l’importation."
                ).classes(
                    "text-sm jf-muted"
                )

                async def receive_import(event):
                    try:
                        text = await event.file.text()
                        filename = getattr(
                            event.file,
                            "name",
                            "journal_pression.csv",
                        )
                        preview = prepare_blood_pressure_import(
                            user_id,
                            filename,
                            text,
                        )
                    except Exception as error:
                        ui.notify(
                            str(error),
                            type="negative",
                        )
                        return

                    with ui.dialog() as dialog:
                        with ui.card().classes(
                            "w-full max-w-4xl p-4"
                        ):
                            ui.label(
                                "Prévisualisation de l’importation"
                            ).classes(
                                "text-xl font-bold"
                            )
                            ui.label(
                                f"Format reconnu : {preview['format']}"
                            ).classes(
                                "text-sm jf-muted"
                            )

                            with ui.element("div").classes(
                                "jf-pressure-import-summary mt-2"
                            ):
                                for label, value in (
                                    (
                                        "Mesures valides",
                                        preview["valid_rows"],
                                    ),
                                    (
                                        "Déjà présentes",
                                        preview["exact_duplicates"],
                                    ),
                                    (
                                        "Même date et heure",
                                        preview["possible_conflicts"],
                                    ),
                                    (
                                        "Erreurs",
                                        len(preview["errors"]),
                                    ),
                                ):
                                    with ui.element("div").classes(
                                        "jf-pressure-import-stat"
                                    ):
                                        ui.label(label).classes(
                                            "text-xs jf-muted"
                                        )
                                        ui.label(str(value)).classes(
                                            "text-xl font-bold"
                                        )

                            include_conflicts = ui.checkbox(
                                "Importer aussi les mesures différentes "
                                "ayant exactement la même date et la même heure",
                                value=False,
                            ).classes("mt-2")

                            import_reminders = None
                            if preview["reminder_settings"]:
                                import_reminders = ui.checkbox(
                                    "Remplacer aussi mes plages et réglages "
                                    "de rappel par ceux de la sauvegarde JSON",
                                    value=False,
                                )
                                ui.label(
                                    "Cette option remplace les horaires "
                                    "actuellement configurés."
                                ).classes(
                                    "text-xs jf-muted"
                                )

                            if preview["errors"]:
                                with ui.expansion(
                                    (
                                        "Lignes ignorées "
                                        f"({len(preview['errors'])})"
                                    ),
                                    icon="warning",
                                ).classes("w-full"):
                                    for message in preview["errors"][:40]:
                                        ui.label(message).classes(
                                            "text-xs text-negative"
                                        )

                            ui.label("Aperçu").classes(
                                "font-bold mt-2"
                            )
                            with ui.column().classes(
                                "w-full gap-1"
                            ):
                                visible_rows = [
                                    row
                                    for row in preview["rows"]
                                    if row.get("duplicate_reason")
                                    not in {"exact", "file_exact"}
                                ][:12]

                                if not visible_rows:
                                    ui.label(
                                        "Aucune nouvelle mesure à afficher."
                                    ).classes(
                                        "text-sm jf-muted"
                                    )

                                for row in visible_rows:
                                    reason = row.get(
                                        "duplicate_reason"
                                    )
                                    status = (
                                        "Même heure"
                                        if reason == "same_slot"
                                        else "Nouvelle"
                                    )
                                    status_class = (
                                        "text-warning"
                                        if reason == "same_slot"
                                        else "text-positive"
                                    )

                                    with ui.element("div").classes(
                                        "jf-pressure-import-row"
                                    ):
                                        ui.label(
                                            row["measured_date"].strftime(
                                                "%d/%m/%Y"
                                            )
                                            + " "
                                            + row["measured_time"].strftime(
                                                "%H:%M"
                                            )
                                        ).classes(
                                            "jf-pressure-import-date"
                                        )
                                        ui.label(
                                            (
                                                f"{row['systolic']}/"
                                                f"{row['diastolic']} — "
                                                f"pouls {row['pulse']}"
                                                + (
                                                    f" — {row['note']}"
                                                    if row.get("note")
                                                    else ""
                                                )
                                            )
                                        ).classes(
                                            "jf-pressure-import-values"
                                        ).tooltip(
                                            row.get("note") or ""
                                        )
                                        ui.label(status).classes(
                                            "jf-pressure-import-status "
                                            + status_class
                                        )

                            def confirm_import():
                                try:
                                    result = import_blood_pressure_rows(
                                        user_id,
                                        preview["rows"],
                                        include_same_slot=(
                                            include_conflicts.value
                                        ),
                                        reminder_settings=(
                                            preview["reminder_settings"]
                                        ),
                                        import_reminders=(
                                            bool(import_reminders.value)
                                            if import_reminders
                                            else False
                                        ),
                                    )
                                except Exception as error:
                                    ui.notify(
                                        str(error),
                                        type="negative",
                                    )
                                    return

                                dialog.close()
                                message = (
                                    "Importation terminée : "
                                    f"{result['imported']} ajoutée(s), "
                                    f"{result['skipped']} ignorée(s)."
                                )
                                if result["reminders_imported"]:
                                    message += (
                                        " Les réglages de rappel ont "
                                        "aussi été remplacés."
                                    )
                                ui.notify(
                                    message,
                                    type="positive",
                                    timeout=10000,
                                )
                                if result["failures"]:
                                    ui.notify(
                                        (
                                            f"{len(result['failures'])} "
                                            "mesure(s) n’ont pas pu "
                                            "être importées."
                                        ),
                                        type="warning",
                                        timeout=10000,
                                    )

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
                ).classes(
                    "w-full mt-3"
                )

            with ui.card().classes(
                "w-full max-w-4xl p-5 mt-3"
            ):
                ui.label(
                    "Exporter les données"
                ).classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "Le CSV convient à Excel. Le JSON constitue "
                    "la sauvegarde privée complète et conserve "
                    "également les plages de rappel."
                ).classes(
                    "text-sm jf-muted"
                )

                def do_export(kind):
                    try:
                        csv_bytes, json_bytes = (
                            export_blood_pressure_data(
                                user_id
                            )
                        )
                        data = (
                            csv_bytes
                            if kind == "csv"
                            else json_bytes
                        )
                        EXPORT_DIRECTORY.mkdir(
                            parents=True,
                            exist_ok=True,
                        )
                        filename = (
                            "journal_pression_"
                            f"{date.today().isoformat()}."
                            f"{kind}"
                        )
                        output_path = (
                            EXPORT_DIRECTORY
                            / f"{user_id}_{int(time.time() * 1000)}_{filename}"
                        )
                        output_path.write_bytes(data)
                        ui.download(
                            str(output_path),
                            filename=filename,
                        )
                    except Exception as error:
                        ui.notify(
                            str(error),
                            type="negative",
                        )

                with ui.row().classes(
                    "gap-2 flex-wrap mt-2"
                ):
                    ui.button(
                        "Exporter CSV",
                        icon="table_view",
                        on_click=lambda: do_export("csv"),
                    ).props(
                        "outline color=primary"
                    )
                    ui.button(
                        "Exporter JSON",
                        icon="data_object",
                        on_click=lambda: do_export("json"),
                    ).props(
                        "outline color=primary"
                    )

                ui.label(
                    "Les fichiers sont générés uniquement pour "
                    "votre compte. Conservez le JSON dans un "
                    "emplacement privé et sécurisé."
                ).classes(
                    "text-xs jf-muted mt-2"
                )
