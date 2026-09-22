from __future__ import annotations


def instruction_steps(value):
    """Découpe une préparation en étapes lisibles sans réécrire le texte."""
    lines = [str(line).strip() for line in str(value or "").splitlines()]
    return [line for line in lines if line]


def recipe_matches(recipe, ingredients, query):
    text = str(query or "").strip().casefold()
    if not text:
        return True

    haystack = [
        str(recipe.get("name") or ""),
        str(recipe.get("description") or ""),
        str(recipe.get("instructions") or ""),
    ]
    for ingredient in ingredients or []:
        haystack.extend(
            [
                str(ingredient.get("name") or ""),
                str(ingredient.get("category") or ""),
                str(ingredient.get("note") or ""),
            ]
        )
    return text in " ".join(haystack).casefold()


def ingredient_label(ingredient):
    name = str(ingredient.get("name") or "Ingrédient").strip()
    quantity = ingredient.get("quantity", 1)
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 1
    return f"{name} ({quantity})" if quantity != 1 else name


def build_recipe_reader(
    *,
    ui,
    recipe,
    ingredients,
    on_add_to_needs,
    summary_message,
):
    """Ouvre une lecture adaptée au téléphone/tablette et un mode cuisine."""
    steps = instruction_steps(recipe.get("instructions"))

    async def request_wake_lock():
        try:
            await ui.run_javascript(
                """
                (async () => {
                    try {
                        if ('wakeLock' in navigator) {
                            if (window.jfRecipeWakeLock) {
                                try { await window.jfRecipeWakeLock.release(); } catch (e) {}
                            }
                            window.jfRecipeWakeLock = await navigator.wakeLock.request('screen');
                            return true;
                        }
                    } catch (e) {}
                    return false;
                })()
                """
            )
        except Exception:
            pass

    async def release_wake_lock():
        try:
            await ui.run_javascript(
                """
                (async () => {
                    try {
                        if (window.jfRecipeWakeLock) {
                            await window.jfRecipeWakeLock.release();
                            window.jfRecipeWakeLock = null;
                        }
                    } catch (e) {}
                })()
                """
            )
        except Exception:
            pass

    def add_to_needs():
        try:
            result = on_add_to_needs()
        except (ValueError, PermissionError) as error:
            ui.notify(str(error), type="warning")
            return
        ui.notify(summary_message(result), type="positive", timeout=5000)

    with ui.dialog().props("maximized persistent") as cooking_dialog:
        with ui.card().classes("w-full min-h-screen p-4 sm:p-6"):
            with ui.row().classes(
                "w-full items-start justify-between gap-3 flex-nowrap sticky top-0 bg-white z-10 py-2"
            ):
                with ui.column().classes("gap-0 min-w-0 grow"):
                    ui.label(recipe["name"]).classes(
                        "text-2xl sm:text-3xl font-bold whitespace-normal"
                    ).style("overflow-wrap:anywhere;")
                    ui.label(
                        "1 portion" if recipe["servings"] == 1 else f"{recipe['servings']} portions"
                    ).classes("text-sm text-gray-500")
                async def close_cooking():
                    await release_wake_lock()
                    cooking_dialog.close()
                ui.button(icon="close", on_click=close_cooking).props(
                    "flat round color=primary"
                ).tooltip("Quitter le mode cuisine")

            with ui.element("div").classes(
                "w-full grid grid-cols-1 lg:grid-cols-2 gap-5 mt-3"
            ):
                with ui.card().classes("w-full p-4 shadow-none bg-blue-50"):
                    ui.label("Ingrédients").classes("text-xl font-bold")
                    if ingredients:
                        for ingredient in ingredients:
                            with ui.row().classes("w-full gap-3 flex-nowrap py-2"):
                                ui.icon("check_box_outline_blank").classes(
                                    "text-2xl text-primary shrink-0 mt-0.5"
                                )
                                with ui.column().classes("gap-0 min-w-0 grow"):
                                    ui.label(ingredient_label(ingredient)).classes(
                                        "text-lg font-semibold whitespace-normal"
                                    ).style("overflow-wrap:anywhere;")
                                    if ingredient.get("note"):
                                        ui.label(str(ingredient["note"])).classes(
                                            "text-base text-gray-600 whitespace-normal"
                                        ).style("overflow-wrap:anywhere;")
                    else:
                        ui.label("Aucun ingrédient.").classes("text-gray-500")

                with ui.card().classes("w-full p-4 shadow-none"):
                    ui.label("Préparation").classes("text-xl font-bold")
                    if steps:
                        for index, step in enumerate(steps, start=1):
                            with ui.row().classes("w-full gap-3 flex-nowrap py-2"):
                                ui.badge(str(index)).props("color=primary").classes(
                                    "shrink-0 mt-1"
                                )
                                ui.label(step).classes(
                                    "text-lg leading-relaxed whitespace-normal"
                                ).style("overflow-wrap:anywhere;")
                    else:
                        ui.label("Aucune étape de préparation.").classes("text-gray-500")

            ui.button(
                "Ajouter à la liste d’épicerie",
                icon="playlist_add",
                on_click=add_to_needs,
            ).props("color=positive size=lg").classes("w-full sm:w-auto mt-4")

    async def open_cooking_mode():
        cooking_dialog.open()
        await request_wake_lock()

    with ui.dialog() as reader_dialog:
        with ui.card().classes("w-full max-w-5xl p-4 sm:p-6"):
            with ui.row().classes("w-full items-start justify-between gap-3 flex-nowrap"):
                with ui.column().classes("gap-1 min-w-0 grow"):
                    ui.label(recipe["name"]).classes(
                        "text-2xl font-bold whitespace-normal"
                    ).style("overflow-wrap:anywhere;")
                    ui.label(
                        "1 portion" if recipe["servings"] == 1 else f"{recipe['servings']} portions"
                    ).classes("text-sm text-gray-500")
                    if recipe.get("description"):
                        ui.label(recipe["description"]).classes(
                            "text-sm text-gray-600 whitespace-normal"
                        ).style("overflow-wrap:anywhere;")
                ui.button(icon="close", on_click=reader_dialog.close).props("flat round")

            with ui.element("div").classes(
                "w-full grid grid-cols-1 md:grid-cols-2 gap-5 mt-3"
            ):
                with ui.card().classes("w-full p-4 shadow-none bg-blue-50"):
                    ui.label("Ingrédients").classes("text-lg font-bold")
                    if ingredients:
                        for ingredient in ingredients:
                            with ui.row().classes("w-full gap-2 flex-nowrap py-1"):
                                ui.icon("circle").classes("text-xs text-primary shrink-0 mt-2")
                                with ui.column().classes("gap-0 min-w-0 grow"):
                                    ui.label(ingredient_label(ingredient)).classes(
                                        "font-semibold whitespace-normal"
                                    ).style("overflow-wrap:anywhere;")
                                    if ingredient.get("note"):
                                        ui.label(str(ingredient["note"])).classes(
                                            "text-sm text-gray-600 whitespace-normal"
                                        ).style("overflow-wrap:anywhere;")
                    else:
                        ui.label("Aucun ingrédient.").classes("text-gray-500")

                with ui.card().classes("w-full p-4 shadow-none"):
                    ui.label("Préparation").classes("text-lg font-bold")
                    if steps:
                        for index, step in enumerate(steps, start=1):
                            with ui.row().classes("w-full gap-2 flex-nowrap py-1"):
                                ui.badge(str(index)).props("outline color=primary").classes("shrink-0")
                                ui.label(step).classes(
                                    "text-sm leading-relaxed whitespace-normal"
                                ).style("overflow-wrap:anywhere;")
                    else:
                        ui.label("Aucune étape de préparation.").classes("text-gray-500")

            with ui.row().classes("w-full justify-end gap-2 mt-4 flex-wrap"):
                ui.button(
                    "Ajouter à la liste d’épicerie",
                    icon="playlist_add",
                    on_click=add_to_needs,
                ).props("outline color=positive")
                ui.button(
                    "Mode cuisine",
                    icon="restaurant",
                    on_click=open_cooking_mode,
                ).props("color=primary")

    reader_dialog.open()
