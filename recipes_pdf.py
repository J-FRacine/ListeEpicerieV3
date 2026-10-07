from __future__ import annotations

from io import BytesIO
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from recipes_extras import nutrition_rows, recipe_time_label
from recipes_ingredient_analysis import metric_label


def _safe(value):
    return escape(str(value or "").strip())


def _steps(value):
    return [
        str(line).strip()
        for line in str(value or "").splitlines()
        if str(line).strip()
    ]


def _photo_bytes(photo):
    if not photo:
        return None
    data = photo.get("image_data")
    if isinstance(data, memoryview):
        data = data.tobytes()
    if isinstance(data, bytearray):
        data = bytes(data)
    return data if isinstance(data, bytes) and data else None


def build_recipe_pdf(
    *,
    recipe,
    ingredients,
    extras,
    output_path,
    photo=None,
    include_photo=True,
    include_nutrition=True,
    include_metric=True,
):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "RecipeTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#173B5E"),
        spaceAfter=6,
    )
    h2 = ParagraphStyle(
        "RecipeH2",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#173B5E"),
        spaceBefore=6,
        spaceAfter=5,
    )
    body = ParagraphStyle(
        "RecipeBody",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=13,
        spaceAfter=3,
    )
    small = ParagraphStyle(
        "RecipeSmall",
        parent=body,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#667085"),
    )

    document = SimpleDocTemplate(
        str(output),
        pagesize=letter,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=str(recipe.get("name") or "Recette"),
    )

    story = [
        Paragraph(_safe(recipe.get("name") or "Recette"), title_style),
    ]

    summary_parts = []
    servings = int(recipe.get("servings") or 1)
    summary_parts.append(
        "1 portion" if servings == 1 else f"{servings} portions"
    )
    time_text = recipe_time_label(extras or {})
    if time_text:
        summary_parts.append(time_text)
    if summary_parts:
        story.append(
            Paragraph(" · ".join(map(_safe, summary_parts)), small)
        )

    description = str(recipe.get("description") or "").strip()
    if description:
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(_safe(description), body))

    source = (extras or {}).get("source") or {}
    if source.get("name") or source.get("url"):
        source_text = "Source : " + str(source.get("name") or "").strip()
        if source.get("url"):
            source_text += " — " + str(source["url"]).strip()
        story.append(Paragraph(_safe(source_text), small))

    photo_bytes = _photo_bytes(photo)
    if include_photo and photo_bytes:
        try:
            image = RLImage(BytesIO(photo_bytes))
            image._restrictSize(175 * mm, 70 * mm)
            story.extend([Spacer(1, 4 * mm), image, Spacer(1, 3 * mm)])
        except Exception:
            # Une photo problématique ne doit jamais empêcher le PDF texte.
            pass

    story.append(Paragraph("Ingrédients", h2))
    metrics = (extras or {}).get("ingredient_metrics") or {}
    if ingredients:
        rows = []
        for ingredient in ingredients:
            name = str(ingredient.get("name") or "Ingrédient").strip()
            quantity = ingredient.get("quantity", 1)
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                quantity = 1
            title = name if quantity == 1 else f"{name} ({quantity})"
            note = str(ingredient.get("note") or "").strip()
            metric = (
                metric_label(
                    metrics,
                    ingredient.get("id"),
                    ingredient.get("name"),
                )
                if include_metric
                else ""
            )
            detail = " · ".join(part for part in (note, metric) if part)
            rows.append([
                Paragraph("• " + _safe(title), body),
                Paragraph(_safe(detail), small),
            ])
        table = Table(rows, colWidths=[65 * mm, 110 * mm])
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 1),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("Aucun ingrédient.", body))

    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Préparation", h2))
    steps = _steps(recipe.get("instructions"))
    if steps:
        for index, step in enumerate(steps, start=1):
            story.append(
                Paragraph(f"<b>{index}.</b> {_safe(step)}", body)
            )
    else:
        story.append(Paragraph("Aucune étape de préparation.", body))

    nutrition = (extras or {}).get("nutrition")
    nutrition_table = nutrition_rows(nutrition, servings)
    if include_nutrition and nutrition_table:
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph("Valeurs nutritives", h2))
        if nutrition and nutrition.get("estimated"):
            story.append(Paragraph("Valeurs approximatives.", small))
        data = [[
            Paragraph("Nutriment", small),
            Paragraph("Par portion", small),
            Paragraph("Recette", small),
        ]]
        for row in nutrition_table:
            data.append([
                Paragraph(_safe(row["label"]), body),
                Paragraph(_safe(row["per_serving_text"]), body),
                Paragraph(_safe(row["whole_recipe_text"]), body),
            ])
        table = Table(data, colWidths=[70 * mm, 50 * mm, 50 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF2F8")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D0D5DD")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        for note in (nutrition or {}).get("notes") or []:
            story.append(Paragraph("• " + _safe(note), small))

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Généré par JF Apps — Recettes", small))
    document.build(story)
    return output
