from __future__ import annotations

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
    list_blood_pressure_readings,
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


BLOOD_PRESSURE_CSS = r"""
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


async def _device_date_time():
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


def blood_pressure_panel(
    current_user,
):
    user_id = current_user["id"]
    today_server = date.today()
    default_start = (
        today_server
        - timedelta(
            days=30
        )
    )

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

    with ui.tabs().classes(
        "w-full"
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

    with ui.tab_panels(
        tabs,
        value=entry_tab,
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
                        "inputmode=numeric"
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
                    ) = await _device_date_time()

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

                async def save_reading():
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

                    clear_measure_values()
                    await use_device_now()
                    render_history.refresh()

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

                    ui.button(
                        "Date et heure actuelles",
                        icon="schedule",
                        on_click=use_device_now,
                    ).props(
                        "outline color=primary"
                    )

                ui.timer(
                    0.15,
                    use_device_now,
                    once=True,
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
                "w-full p-5"
            ):
                ui.label(
                    "Historique"
                ).classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "Filtrez, modifiez ou supprimez "
                    "vos propres mesures."
                ).classes(
                    "text-sm jf-muted"
                )

                with ui.row().classes(
                    "w-full gap-3 flex-wrap mt-2"
                ):
                    history_start_input = ui.input(
                        label="Du",
                        value=default_start.isoformat(),
                    ).props(
                        "type=date"
                    ).classes(
                        "grow min-w-[180px]"
                    )

                    history_end_input = ui.input(
                        label="Au",
                        value=today_server.isoformat(),
                    ).props(
                        "type=date"
                    ).classes(
                        "grow min-w-[180px]"
                    )

                    ui.button(
                        "Appliquer",
                        icon="filter_alt",
                        on_click=lambda: (
                            render_history.refresh()
                        ),
                    ).props(
                        "outline color=primary"
                    ).classes(
                        "self-end"
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
                            "text-negative"
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
                        "text-negative"
                    )
                    return
                except Exception:
                    ui.label(
                        "L’historique n’a pas pu "
                        "être chargé."
                    ).classes(
                        "text-negative"
                    )
                    return

                if not readings:
                    with ui.card().classes(
                        "w-full p-6 items-center "
                        "text-center mt-3"
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

                grouped = defaultdict(list)

                for reading in readings:
                    grouped[
                        reading[
                            "measured_date"
                        ]
                    ].append(
                        reading
                    )

                for day in sorted(
                    grouped,
                    reverse=True,
                ):
                    with ui.element(
                        "div"
                    ).classes(
                        "jf-pressure-day mt-3"
                    ):
                        with ui.row().classes(
                            "w-full items-center "
                            "justify-between gap-2"
                        ):
                            ui.label(
                                _date_text(day)
                            ).classes(
                                "font-bold"
                            )
                            ui.label(
                                (
                                    "1 mesure"
                                    if len(grouped[day]) == 1
                                    else (
                                        f"{len(grouped[day])} "
                                        "mesures"
                                    )
                                )
                            ).classes(
                                "text-xs jf-muted"
                            )

                    with ui.element(
                        "div"
                    ).classes(
                        "jf-pressure-grid mt-2"
                    ):
                        for reading in sorted(
                            grouped[day],
                            key=lambda item: (
                                item[
                                    "measured_time"
                                ],
                                item["id"],
                            ),
                        ):
                            with ui.element(
                                "div"
                            ).classes(
                                "jf-pressure-reading-card"
                            ):
                                with ui.row().classes(
                                    "w-full items-start "
                                    "justify-between gap-2"
                                ):
                                    with ui.column().classes(
                                        "gap-0"
                                    ):
                                        ui.label(
                                            _time_text(
                                                reading[
                                                    "measured_time"
                                                ]
                                            )
                                        ).classes(
                                            "font-bold text-primary"
                                        )
                                        ui.label(
                                            (
                                                f"{reading['systolic']}/"
                                                f"{reading['diastolic']}"
                                            )
                                        ).classes(
                                            "jf-pressure-value"
                                        )
                                        ui.label(
                                            (
                                                f"Pouls : "
                                                f"{reading['pulse']}"
                                            )
                                        ).classes(
                                            "text-sm"
                                        )

                                    with ui.row().classes(
                                        "gap-0"
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
                                            "flat round color=primary"
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
                                            "flat round color=negative"
                                        ).tooltip(
                                            "Supprimer"
                                        )

                                if reading["note"]:
                                    ui.separator().classes(
                                        "my-2"
                                    )
                                    ui.label(
                                        reading["note"]
                                    ).classes(
                                        "text-sm jf-muted"
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
