from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _normalize_date(value) -> date:
    if isinstance(value, date):
        return value

    return date.fromisoformat(
        str(value)
    )


def _iter_dates(
    start_date,
    end_date,
):
    current_date = _normalize_date(
        start_date
    )
    final_date = _normalize_date(
        end_date
    )

    while current_date <= final_date:
        yield current_date
        current_date += timedelta(
            days=1
        )


def _format_date(value) -> str:
    normalized = _normalize_date(
        value
    )
    return normalized.strftime(
        "%d/%m/%Y"
    )


def _format_time(value) -> str:
    if hasattr(value, "strftime"):
        return value.strftime(
            "%H:%M"
        )

    text = str(value or "")
    return text[:5]


def _period_text(value) -> str:
    time_text = _format_time(value)

    try:
        hour = int(time_text[:2])
    except (TypeError, ValueError):
        return ""

    return (
        "Matin"
        if hour < 12
        else "Soir"
    )


def _display_time_text(
    value,
    time_display_mode,
) -> str:
    if time_display_mode == "period":
        return _period_text(value)

    return _format_time(value)


def _measurement_text(
    reading,
    time_display_mode,
) -> str:
    return (
        f"{_display_time_text(reading['measured_time'], time_display_mode)}"
        f"  |  {reading['systolic']}/"
        f"{reading['diastolic']}"
        f"  |  Pouls {reading['pulse']}"
    )


def _note_text(
    readings,
    time_display_mode,
) -> str:
    notes = []

    for reading in readings:
        note = str(
            reading.get("note")
            or ""
        ).strip()

        if note:
            notes.append(
                (
                    f"<b>{escape(_display_time_text(reading['measured_time'], time_display_mode))}"
                    f"</b> : {escape(note)}"
                )
            )

    return "<br/>".join(
        notes
    )


def build_blood_pressure_pdf(
    *,
    full_name,
    start_date,
    end_date,
    readings,
    output_path,
    time_display_mode="exact",
):
    """Crée le rapport PDF du journal de pression."""

    normalized_name = str(
        full_name or ""
    ).strip()

    if not normalized_name:
        raise ValueError(
            "Le nom complet est obligatoire."
        )

    normalized_start = _normalize_date(
        start_date
    )
    normalized_end = _normalize_date(
        end_date
    )

    if normalized_end < normalized_start:
        raise ValueError(
            "La date de fin doit être "
            "égale ou postérieure à "
            "la date de début."
        )

    normalized_time_display_mode = (
        "period"
        if str(time_display_mode or "").strip().lower() == "period"
        else "exact"
    )

    output = Path(
        output_path
    )
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    grouped = defaultdict(list)

    for reading in readings:
        measured_date = _normalize_date(
            reading["measured_date"]
        )

        if (
            normalized_start
            <= measured_date
            <= normalized_end
        ):
            grouped[
                measured_date
            ].append(
                reading
            )

    for day_readings in grouped.values():
        day_readings.sort(
            key=lambda item: (
                _format_time(
                    item["measured_time"]
                ),
                int(
                    item.get("id")
                    or 0
                ),
            )
        )

    page_width, page_height = landscape(
        letter
    )

    document = SimpleDocTemplate(
        str(output),
        pagesize=(
            page_width,
            page_height,
        ),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=11 * mm,
        title=(
            "Journal de pression artérielle"
        ),
        author="JF Apps",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        alignment=TA_CENTER,
        spaceAfter=5,
    )

    header_style = ParagraphStyle(
        "ReportHeader",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
        alignment=TA_CENTER,
    )

    header_cell_style = ParagraphStyle(
        "ReportHeaderCell",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.4,
        leading=10.3,
        textColor=colors.white,
    )

    cell_style = ParagraphStyle(
        "ReportCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.4,
        leading=10.3,
    )

    small_style = ParagraphStyle(
        "ReportSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=9.4,
    )

    story = [
        Paragraph(
            "Journal de pression artérielle",
            title_style,
        ),
        Paragraph(
            (
                f"<b>Nom :</b> "
                f"{escape(normalized_name)}"
            ),
            header_style,
        ),
        Paragraph(
            (
                f"<b>Période :</b> "
                f"du {_format_date(normalized_start)} "
                f"au {_format_date(normalized_end)}"
            ),
            header_style,
        ),
    ]

    if normalized_time_display_mode == "period":
        story.append(
            Paragraph(
                "<b>Affichage des prises :</b> Matin / Soir",
                header_style,
            )
        )

    story.append(
        Spacer(
            1,
            6 * mm,
        )
    )

    time_column_label = (
        "Période"
        if normalized_time_display_mode == "period"
        else "Heure"
    )

    rows = [
        [
            Paragraph(
                "<b>Date</b>",
                header_cell_style,
            ),
            Paragraph(
                "Mesure 1<br/>"
                f"{time_column_label} | SYS/DIA | Pouls",
                header_cell_style,
            ),
            Paragraph(
                "Mesure 2<br/>"
                f"{time_column_label} | SYS/DIA | Pouls",
                header_cell_style,
            ),
            Paragraph(
                "Notes",
                header_cell_style,
            ),
        ]
    ]

    no_data_rows = []

    for current_date in _iter_dates(
        normalized_start,
        normalized_end,
    ):
        day_readings = grouped.get(
            current_date,
            [],
        )

        if not day_readings:
            rows.append(
                [
                    Paragraph(
                        _format_date(
                            current_date
                        ),
                        cell_style,
                    ),
                    Paragraph(
                        "<i>Aucune donnée pour ce jour</i>",
                        cell_style,
                    ),
                    "",
                    "",
                ]
            )
            no_data_rows.append(
                len(rows) - 1
            )
            continue

        for pair_index in range(
            0,
            len(day_readings),
            2,
        ):
            pair = day_readings[
                pair_index:
                pair_index + 2
            ]

            date_label = _format_date(
                current_date
            )

            if pair_index > 0:
                date_label += " (suite)"

            first = pair[0]
            second = (
                pair[1]
                if len(pair) > 1
                else None
            )

            rows.append(
                [
                    Paragraph(
                        date_label,
                        cell_style,
                    ),
                    Paragraph(
                        escape(
                            _measurement_text(
                                first,
                                normalized_time_display_mode,
                            )
                        ),
                        small_style,
                    ),
                    (
                        Paragraph(
                            escape(
                                _measurement_text(
                                    second,
                                    normalized_time_display_mode,
                                )
                            ),
                            small_style,
                        )
                        if second
                        else ""
                    ),
                    Paragraph(
                        _note_text(
                            pair,
                            normalized_time_display_mode,
                        ),
                        small_style,
                    ),
                ]
            )

    table = Table(
        rows,
        colWidths=[
            27 * mm,
            56 * mm,
            56 * mm,
            120 * mm,
        ],
        repeatRows=1,
        hAlign="LEFT",
    )

    table_style = [
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor(
                "#173553"
            ),
        ),
        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 0),
            colors.white,
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "TOP",
        ),
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.45,
            colors.HexColor(
                "#A8B4BF"
            ),
        ),
        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            5,
        ),
        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            5,
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            5,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            5,
        ),
    ]

    for row_index in range(
        1,
        len(rows),
    ):
        if row_index % 2 == 0:
            table_style.append(
                (
                    "BACKGROUND",
                    (0, row_index),
                    (-1, row_index),
                    colors.HexColor(
                        "#F3F6F8"
                    ),
                )
            )

    for row_index in no_data_rows:
        table_style.extend(
            [
                (
                    "SPAN",
                    (1, row_index),
                    (3, row_index),
                ),
                (
                    "BACKGROUND",
                    (0, row_index),
                    (-1, row_index),
                    colors.HexColor(
                        "#FFF8E8"
                    ),
                ),
            ]
        )

    table.setStyle(
        TableStyle(
            table_style
        )
    )

    story.append(table)
    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )
    story.append(
        Paragraph(
            (
                "Rapport produit à partir des données privées "
                "de l’utilisateur dans JF Apps. "
                "Aucune moyenne ni interprétation médicale "
                "n’est calculée."
            ),
            small_style,
        )
    )

    def add_page_number(
        canvas,
        document_template,
    ):
        canvas.saveState()
        canvas.setFont(
            "Helvetica",
            7.5,
        )
        canvas.setFillColor(
            colors.HexColor(
                "#647484"
            )
        )
        canvas.drawRightString(
            page_width - 10 * mm,
            6 * mm,
            (
                f"Page "
                f"{document_template.page}"
            ),
        )
        canvas.restoreState()

    document.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )

    return output
