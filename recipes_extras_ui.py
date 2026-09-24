from __future__ import annotations

from nicegui import ui

from recipes_extras import (
    BASIS_LABELS,
    NUTRITION_FIELDS,
    delete_recipe_nutrition,
    get_recipe_extras,
    nutrition_rows,
    save_recipe_nutrition,
)


def _render_rows(nutrition, servings):
    rows = nutrition_rows(nutrition, servings)
    if not rows:
        ui.label("Aucune valeur nutritive enregistrée.").classes(
            "text-sm text-gray-500"
        )
        return

    with ui.card().classes("w-full p-3 shadow-none bg-gray-50"):
        with ui.row().classes(
            "w-full font-bold text-sm items-center gap-2"
        ):
            ui.label("Nutriment").classes("grow")
            ui.label("Par portion").classes("w-32 text-right")
            ui.label("Recette complète").classes("w-36 text-right")
        ui.separator()
        for row in rows:
            with ui.row().classes(
                "w-full text-sm items-center gap-2 py-1"
            ):
                ui.label(row["label"]).classes("grow")
                ui.label(row["per_serving_text"]).classes(
                    "w-32 text-right"
                )
                ui.label(row["whole_recipe_text"]).classes(
                    "w-36 text-right"
                )


def open_nutrition_dialog(*, user_id, recipe, on_saved=None):
    extras = get_recipe_extras(user_id, recipe["id"])
    current = extras.get("nutrition") or {
        "basis": "per_serving",
        "estimated": True,
    }

    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-3xl p-5"):
            ui.label("Valeurs nutritives").classes("text-xl font-bold")
            ui.label(recipe["name"]).classes("text-sm text-gray-600")
            ui.label(
                "Les valeurs peuvent être saisies manuellement ou importées "
                "avec une recette ChatGPT. Lorsque « Estimation » est cochée, "
                "elles sont présentées comme approximatives."
            ).classes("text-xs text-gray-500")

            with ui.row().classes("w-full gap-3 flex-wrap"):
                basis = ui.select(
                    {
                        "per_serving": "Valeurs saisies par portion",
                        "whole_recipe": "Valeurs saisies pour la recette complète",
                    },
                    value=current.get("basis") or "per_serving",
                    label="Base de calcul",
                ).props("outlined").classes("grow min-w-[260px]")
                estimated = ui.checkbox(
                    "Estimation",
                    value=bool(current.get("estimated", True)),
                )

            inputs = {}
            with ui.element("div").classes(
                "w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"
            ):
                for key, label, unit in NUTRITION_FIELDS:
                    inputs[key] = ui.number(
                        label=f"{label} ({unit})",
                        value=current.get(key),
                        min=0,
                        step=0.1 if unit == "g" else 1,
                    ).classes("w-full")

            preview = ui.column().classes("w-full gap-2")

            def refresh_preview():
                candidate = dict(current)
                candidate.pop("per_serving_values", None)
                candidate.pop("whole_recipe_values", None)
                candidate.update(
                    {
                        "basis": basis.value,
                        "estimated": estimated.value,
                    }
                )
                for key, _label, _unit in NUTRITION_FIELDS:
                    candidate[key] = inputs[key].value
                preview.clear()
                with preview:
                    _render_rows(candidate, recipe["servings"])

            ui.button(
                "Aperçu",
                icon="visibility",
                on_click=refresh_preview,
            ).props("flat color=primary")

            def save():
                nutrition = dict(current)
                nutrition.pop("per_serving_values", None)
                nutrition.pop("whole_recipe_values", None)
                nutrition.update(
                    {
                        "basis": basis.value,
                        "estimated": bool(estimated.value),
                    }
                )
                for key, _label, _unit in NUTRITION_FIELDS:
                    nutrition[key] = inputs[key].value
                try:
                    save_recipe_nutrition(
                        user_id,
                        recipe["id"],
                        nutrition,
                    )
                except (ValueError, PermissionError) as error:
                    ui.notify(str(error), type="warning")
                    return
                dialog.close()
                if on_saved:
                    on_saved()
                ui.notify(
                    "Valeurs nutritives enregistrées.",
                    type="positive",
                )

            def clear():
                try:
                    delete_recipe_nutrition(
                        user_id,
                        recipe["id"],
                    )
                except (ValueError, PermissionError) as error:
                    ui.notify(str(error), type="warning")
                    return
                dialog.close()
                if on_saved:
                    on_saved()
                ui.notify(
                    "Tableau nutritionnel retiré.",
                    type="positive",
                )

            with ui.row().classes(
                "w-full justify-between gap-2 mt-3 flex-wrap"
            ):
                ui.button(
                    "Retirer le tableau",
                    icon="delete_outline",
                    on_click=clear,
                ).props("flat color=negative")
                with ui.row().classes("gap-2"):
                    ui.button(
                        "Annuler",
                        on_click=dialog.close,
                    ).props("flat")
                    ui.button(
                        "Enregistrer",
                        icon="save",
                        on_click=save,
                    ).props("color=primary")
    dialog.open()
