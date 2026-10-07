from __future__ import annotations

from nicegui import ui

from recipes_extras import (
    get_recipe_extras,
    save_recipe_ingredient_metrics,
    save_recipe_nutrition,
)
from recipes_food_catalog import food_options
from recipes_ingredient_analysis import (
    analyze_recipe_ingredients,
    build_nutrition_estimate,
    grams_from_measurement,
    serialize_metrics,
)


def open_measurement_converter_dialog(*, user_id, recipe, on_saved=None):
    from db import get_recipe_ingredients

    ingredients = get_recipe_ingredients(user_id, recipe["id"])
    extras = get_recipe_extras(user_id, recipe["id"])
    saved_metrics = extras.get("ingredient_metrics") or {}
    analysis = analyze_recipe_ingredients(ingredients, saved_metrics)
    options = food_options()

    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-5xl p-5"):
            ui.label("Mesures en grammes").classes("text-xl font-bold")
            ui.label(recipe["name"]).classes("text-sm text-gray-600")
            ui.label(
                "JF Apps tente de reconnaître l’ingrédient et sa mesure. "
                "Les poids issus de tasses, cuillères ou unités sont des "
                "estimations propres à l’ingrédient. Vous pouvez toujours "
                "corriger le poids avant de l’enregistrer."
            ).classes("text-xs text-gray-500 whitespace-normal")

            if not ingredients:
                ui.label("Cette recette ne contient aucun ingrédient.").classes(
                    "text-sm text-orange-700"
                )
                ui.button("Fermer", on_click=dialog.close).props("flat")
                dialog.open()
                return

            controls = {}

            with ui.column().classes("w-full gap-3 mt-2"):
                for row in analysis:
                    ingredient_id = int(row["ingredient_id"])
                    with ui.card().classes(
                        "w-full p-3 shadow-none border border-gray-200"
                    ):
                        with ui.row().classes(
                            "w-full items-start gap-3 flex-wrap"
                        ):
                            with ui.column().classes("gap-0 grow min-w-[220px]"):
                                ui.label(row["name"]).classes(
                                    "font-bold whitespace-normal"
                                )
                                original = row["note"] or (
                                    str(row["measurement"].get("amount") or "")
                                    + " "
                                    + str(row["measurement"].get("unit") or "")
                                ).strip()
                                ui.label(
                                    "Mesure originale : " + (original or "non précisée")
                                ).classes("text-xs text-gray-500 whitespace-normal")
                                if row.get("source"):
                                    ui.label(row["source"]).classes(
                                        "text-xs text-blue-700"
                                    )

                            food_select = ui.select(
                                options,
                                value=row.get("food_key") or None,
                                label="Aliment de référence",
                                with_input=True,
                            ).props(
                                "clearable use-input input-debounce=0 outlined dense"
                            ).classes("grow min-w-[250px]")

                            grams_input = ui.number(
                                label="Poids (g)",
                                value=row.get("grams"),
                                min=0,
                                step=0.1,
                            ).props("outlined dense").classes("w-36")

                            controls[ingredient_id] = {
                                "row": row,
                                "food": food_select,
                                "grams": grams_input,
                            }

                            def recalculate(
                                event,
                                ingredient_key=ingredient_id,
                            ):
                                control = controls[ingredient_key]
                                food_key = event.value
                                control["row"]["food_key"] = food_key
                                grams, _source = grams_from_measurement(
                                    control["row"]["measurement"],
                                    food_key,
                                )
                                control["grams"].value = grams
                                control["grams"].update()

                            food_select.on_value_change(recalculate)

            def rows_from_controls():
                rows = []
                for ingredient_id, control in controls.items():
                    row = dict(control["row"])
                    row["ingredient_id"] = ingredient_id
                    row["food_key"] = control["food"].value or ""
                    row["grams"] = control["grams"].value
                    # Un poids modifié par l’utilisateur devient une valeur manuelle.
                    row["metric_source"] = "manual"
                    rows.append(row)
                return rows

            def save_metrics_only():
                try:
                    metrics = serialize_metrics(rows_from_controls())
                    save_recipe_ingredient_metrics(
                        user_id,
                        recipe["id"],
                        metrics,
                    )
                except (ValueError, PermissionError) as error:
                    ui.notify(str(error), type="warning")
                    return
                dialog.close()
                if on_saved:
                    on_saved()
                ui.notify(
                    "Conversions en grammes enregistrées.",
                    type="positive",
                )

            def calculate_nutrition():
                rows = rows_from_controls()
                result = build_nutrition_estimate(
                    rows,
                    recipe.get("servings"),
                )
                if result["used_count"] <= 0:
                    ui.notify(
                        "Aucun ingrédient n’a pu être utilisé dans le calcul. "
                        "Choisissez un aliment de référence et un poids en grammes.",
                        type="warning",
                        timeout=8000,
                    )
                    return
                try:
                    save_recipe_ingredient_metrics(
                        user_id,
                        recipe["id"],
                        serialize_metrics(rows),
                    )
                    save_recipe_nutrition(
                        user_id,
                        recipe["id"],
                        result["nutrition"],
                    )
                except (ValueError, PermissionError) as error:
                    ui.notify(str(error), type="warning")
                    return

                dialog.close()
                if on_saved:
                    on_saved()
                message = (
                    f"Valeurs nutritives estimées avec "
                    f"{result['used_count']} ingrédient(s)."
                )
                if result["skipped_count"]:
                    message += (
                        f" {result['skipped_count']} ingrédient(s) "
                        "n’ont pas été inclus."
                    )
                ui.notify(
                    message,
                    type=(
                        "warning"
                        if result["skipped_count"]
                        else "positive"
                    ),
                    timeout=9000,
                    close_button=True,
                )

            with ui.row().classes(
                "w-full justify-between gap-2 mt-3 flex-wrap"
            ):
                ui.label(
                    "Les conversions enregistrées sont affichées comme ≈ grammes; "
                    "la mesure originale reste intacte."
                ).classes("text-xs text-gray-500 grow")
                with ui.row().classes("gap-2 flex-wrap"):
                    ui.button(
                        "Annuler",
                        on_click=dialog.close,
                    ).props("flat")
                    ui.button(
                        "Enregistrer les grammes",
                        icon="scale",
                        on_click=save_metrics_only,
                    ).props("outline color=primary")
                    ui.button(
                        "Calculer la nutrition",
                        icon="monitor_weight",
                        on_click=calculate_nutrition,
                    ).props("color=primary")

    dialog.open()
