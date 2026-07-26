from nicegui import app, ui

from auth import get_current_user_id
from db import (
    add_recipe_ingredient,
    apply_recipe_to_needs,
    create_recipe,
    delete_recipe,
    get_accessible_families,
    get_items,
    get_recipe_ingredients,
    get_recipes,
    move_recipe_ingredient,
    remove_recipe_ingredient,
    update_recipe,
    update_recipe_ingredient,
)
from state import (
    get_current_family_id,
    set_current_family_id,
)
from utils import ensure_family_selected


def _item_options(items):
    return {
        item["id"]: (
            f"{item['name']} — {item['store']} / {item['category']}"
        )
        for item in items
    }


def _recipe_caption(servings, ingredient_count):
    serving_text = (
        "1 portion"
        if servings == 1
        else f"{servings} portions"
    )
    ingredient_text = (
        "1 ingrédient"
        if ingredient_count == 1
        else f"{ingredient_count} ingrédients"
    )
    return f"{serving_text} · {ingredient_text}"


def _summary_message(result):
    total = result["items_total"]
    added = result["items_added"]
    quantities = result["quantities_updated"]

    message = (
        f"{total} ingrédient traité"
        if total == 1
        else f"{total} ingrédients traités"
    )
    message += (
        f", {added} ajouté aux besoins"
        if added == 1
        else f", {added} ajoutés aux besoins"
    )

    if quantities:
        message += (
            f", {quantities} quantité augmentée"
            if quantities == 1
            else f", {quantities} quantités augmentées"
        )

    return message + "."


def recipes_panel():
    user_id = get_current_user_id()
    family_id = get_current_family_id()
    open_storage_key = (
        f"open_grocery_recipes_{family_id}"
    )

    def get_open_recipe_ids():
        stored_ids = app.storage.user.get(
            open_storage_key,
            [],
        )
        result = set()

        for stored_id in stored_ids:
            try:
                result.add(int(stored_id))
            except (TypeError, ValueError):
                continue

        return result

    def save_recipe_open_state(
        recipe_id,
        is_open,
    ):
        open_ids = get_open_recipe_ids()

        if is_open:
            open_ids.add(int(recipe_id))
        else:
            open_ids.discard(int(recipe_id))

        app.storage.user[open_storage_key] = sorted(
            open_ids
        )

    if user_id is None or not ensure_family_selected(family_id):
        return

    families = get_accessible_families(user_id)
    if not families:
        ui.label("Aucune famille accessible.").classes("text-orange-700")
        return

    family_by_name = {
        family["name"]: family["id"]
        for family in families
    }
    current_name = next(
        (
            name
            for name, accessible_id in family_by_name.items()
            if accessible_id == family_id
        ),
        list(family_by_name)[0],
    )

    ui.select(
        list(family_by_name),
        value=current_name,
        label="Famille",
        on_change=lambda event: (
            set_current_family_id(family_by_name[event.value]),
            ui.navigate.to("/?tab=recettes"),
        ),
    ).classes("w-full")

    with ui.row().classes(
        "w-full items-start justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Recettes").classes("text-2xl font-bold")
            ui.label(
                "Associez vos recettes aux items existants, puis ajoutez "
                "leurs ingrédients aux besoins."
            ).classes("text-sm text-gray-500")

        ui.icon("restaurant_menu").classes("text-4xl text-primary")

    def recipe_form(title, recipe=None):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-2xl p-5"):
                ui.label(title).classes("text-xl font-bold")

                name_input = ui.input(
                    label="Nom",
                    value=recipe["name"] if recipe else "",
                    placeholder="Ex. Pâté chinois",
                ).classes("w-full")

                servings_input = ui.number(
                    label="Nombre de portions",
                    value=recipe["servings"] if recipe else 4,
                    min=1,
                    step=1,
                ).classes("w-40")

                description_input = ui.textarea(
                    label="Description facultative",
                    value=recipe["description"] if recipe else "",
                    placeholder="Ex. Repas familial simple et économique",
                ).props("autogrow").classes("w-full")

                instructions_input = ui.textarea(
                    label="Préparation facultative",
                    value=recipe["instructions"] if recipe else "",
                    placeholder=(
                        "Ex. Cuire la viande, ajouter le maïs, couvrir de purée..."
                    ),
                ).props("autogrow").classes("w-full")

                def save():
                    try:
                        if recipe:
                            update_recipe(
                                user_id,
                                recipe["id"],
                                name_input.value,
                                description_input.value,
                                instructions_input.value,
                                servings_input.value,
                            )
                        else:
                            create_recipe(
                                user_id,
                                family_id,
                                name_input.value,
                                description_input.value,
                                instructions_input.value,
                                servings_input.value,
                            )
                    except (ValueError, PermissionError) as error:
                        ui.notify(str(error), type="warning")
                        return

                    dialog.close()
                    render_recipes.refresh()
                    ui.notify(
                        "Recette modifiée." if recipe else "Recette créée.",
                        type="positive",
                    )

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button(
                        "Enregistrer" if recipe else "Créer",
                        icon="save" if recipe else "add",
                        on_click=save,
                    ).props("color=primary")

        dialog.open()

    with ui.row().classes("w-full gap-2 flex-wrap"):
        ui.button(
            "Nouvelle recette",
            icon="add",
            on_click=lambda: recipe_form("Nouvelle recette"),
        ).props("color=primary")

        ui.button(
            "Listes modèles",
            icon="checklist",
            on_click=lambda: ui.navigate.to("/?tab=modeles"),
        ).props("flat color=primary")

    def confirm_delete(recipe):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-md p-5"):
                ui.label("Supprimer la recette?").classes("text-xl font-bold")
                ui.label(
                    f"« {recipe['name']} » sera supprimée. "
                    "Les items eux-mêmes resteront dans l’application."
                ).classes("text-gray-600")

                def perform_delete():
                    try:
                        delete_recipe(user_id, recipe["id"])
                    except (ValueError, PermissionError) as error:
                        ui.notify(str(error), type="warning")
                        return

                    dialog.close()
                    render_recipes.refresh()
                    ui.notify("Recette supprimée.", type="positive")

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button(
                        "Supprimer",
                        icon="delete",
                        on_click=perform_delete,
                    ).props("color=negative")

        dialog.open()

    def edit_ingredient(ingredient):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-md p-5"):
                ui.label(ingredient["name"]).classes("text-xl font-bold")

                quantity_input = ui.number(
                    label="Quantité",
                    value=ingredient["quantity"],
                    min=1,
                    step=1,
                ).classes("w-full")

                note_input = ui.input(
                    label="Précision facultative",
                    value=ingredient["note"],
                    placeholder="Ex. boîtes de 398 ml, au goût...",
                ).classes("w-full")

                def save():
                    try:
                        update_recipe_ingredient(
                            user_id,
                            ingredient["id"],
                            quantity_input.value,
                            note_input.value,
                        )
                    except (ValueError, PermissionError) as error:
                        ui.notify(str(error), type="warning")
                        return

                    dialog.close()
                    render_recipes.refresh()

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button(
                        "Enregistrer",
                        icon="save",
                        on_click=save,
                    ).props("color=primary")

        dialog.open()

    def move_ingredient(ingredient_id, direction):
        try:
            move_recipe_ingredient(user_id, ingredient_id, direction)
        except (ValueError, PermissionError) as error:
            ui.notify(str(error), type="warning")
            return
        render_recipes.refresh()

    @ui.refreshable
    def render_recipes():
        recipes = get_recipes(user_id, family_id)
        items = get_items(user_id, family_id)
        options = _item_options(items)

        valid_recipe_ids = {
            int(recipe["id"])
            for recipe in recipes
        }
        open_recipe_ids = (
            get_open_recipe_ids()
            & valid_recipe_ids
        )

        app.storage.user[open_storage_key] = sorted(
            open_recipe_ids
        )

        if not recipes:
            with ui.card().classes("w-full p-7 items-center text-center mt-3"):
                ui.icon("menu_book").classes("text-5xl text-primary")
                ui.label("Aucune recette").classes("text-xl font-bold")
                ui.label(
                    "Créez une recette, puis choisissez ses ingrédients "
                    "parmi les items de la famille."
                ).classes("text-gray-500")
            return

        for recipe in recipes:
            recipe_id = recipe["id"]
            ingredients = get_recipe_ingredients(user_id, recipe_id)
            ingredient_count = len(ingredients)

            with ui.expansion(
                text=recipe["name"],
                caption=_recipe_caption(
                    recipe["servings"],
                    ingredient_count,
                ),
                icon="restaurant",
                value=recipe_id in open_recipe_ids,
                on_value_change=(
                    lambda event,
                    selected_recipe_id=recipe_id: (
                        save_recipe_open_state(
                            selected_recipe_id,
                            bool(event.value),
                        )
                    )
                ),
            ).props("expand-separator").classes(
                "w-full bg-white rounded-xl shadow-sm "
                "border border-gray-200 overflow-hidden mt-3"
            ):
                with ui.column().classes("w-full gap-3 px-2 pb-3"):
                    if recipe["description"]:
                        ui.label(recipe["description"]).classes(
                            "text-sm text-gray-600 whitespace-normal"
                        ).style("overflow-wrap:anywhere;")

                    with ui.row().classes(
                        "w-full items-center gap-1 flex-wrap"
                    ):
                        def apply_selected(selected=recipe):
                            try:
                                result = apply_recipe_to_needs(
                                    user_id,
                                    selected["id"],
                                )
                            except (ValueError, PermissionError) as error:
                                ui.notify(str(error), type="warning")
                                return

                            ui.notify(
                                _summary_message(result),
                                type="positive",
                                timeout=5000,
                            )

                        ui.button(
                            "Ajouter les ingrédients",
                            icon="playlist_add",
                            on_click=apply_selected,
                        ).props("color=positive")

                        ui.button(
                            icon="edit",
                            on_click=lambda selected=recipe: recipe_form(
                                "Modifier la recette",
                                selected,
                            ),
                        ).props("flat round color=primary").tooltip(
                            "Modifier la recette"
                        )

                        ui.button(
                            icon="delete",
                            on_click=lambda selected=recipe: (
                                confirm_delete(selected)
                            ),
                        ).props("flat round color=negative").tooltip(
                            "Supprimer la recette"
                        )

                    ui.label("Ingrédients").classes("text-lg font-bold")

                    if ingredients:
                        for index, ingredient in enumerate(ingredients):
                            with ui.card().classes("w-full p-3 shadow-none"):
                                with ui.row().classes(
                                    "w-full items-center gap-2 flex-nowrap"
                                ):
                                    with ui.column().classes(
                                        "gap-0 grow min-w-0"
                                    ):
                                        ui.label(
                                            (
                                                f"{ingredient['name']} "
                                                f"({ingredient['quantity']})"
                                                if ingredient["quantity"] != 1
                                                else ingredient["name"]
                                            )
                                        ).classes(
                                            "font-bold whitespace-normal"
                                        ).style("overflow-wrap:anywhere;")

                                        ui.label(
                                            f"{ingredient['store']} · "
                                            f"{ingredient['category']}"
                                        ).classes("text-xs text-gray-500")

                                        if ingredient["note"]:
                                            ui.label(ingredient["note"]).classes(
                                                "text-xs text-gray-600 "
                                                "whitespace-normal"
                                            ).style("overflow-wrap:anywhere;")

                                    with ui.row().classes(
                                        "items-center gap-0 shrink-0"
                                    ):
                                        ui.button(
                                            icon="arrow_upward",
                                            on_click=lambda ingredient_id=ingredient[
                                                "id"
                                            ]: move_ingredient(
                                                ingredient_id,
                                                -1,
                                            ),
                                        ).props(
                                            "flat round dense"
                                        ).set_enabled(index > 0)

                                        ui.button(
                                            icon="arrow_downward",
                                            on_click=lambda ingredient_id=ingredient[
                                                "id"
                                            ]: move_ingredient(
                                                ingredient_id,
                                                1,
                                            ),
                                        ).props(
                                            "flat round dense"
                                        ).set_enabled(
                                            index < ingredient_count - 1
                                        )

                                        ui.button(
                                            icon="edit",
                                            on_click=lambda selected=ingredient: (
                                                edit_ingredient(selected)
                                            ),
                                        ).props(
                                            "flat round dense color=primary"
                                        ).tooltip("Modifier l’ingrédient")

                                        def remove_selected(
                                            ingredient_id=ingredient["id"],
                                        ):
                                            try:
                                                remove_recipe_ingredient(
                                                    user_id,
                                                    ingredient_id,
                                                )
                                            except (
                                                ValueError,
                                                PermissionError,
                                            ) as error:
                                                ui.notify(
                                                    str(error),
                                                    type="warning",
                                                )
                                                return
                                            render_recipes.refresh()

                                        ui.button(
                                            icon="close",
                                            on_click=remove_selected,
                                        ).props(
                                            "flat round dense color=negative"
                                        ).tooltip("Retirer de la recette")
                    else:
                        ui.label(
                            "Cette recette ne contient encore aucun ingrédient."
                        ).classes("text-sm text-gray-500")

                    if options:
                        ui.separator()
                        ui.label("Ajouter un ingrédient existant").classes(
                            "font-bold"
                        )
                        with ui.row().classes(
                            "w-full items-end gap-2 flex-wrap"
                        ):
                            item_input = ui.select(
                                options=options,
                                label="Item",
                                with_input=True,
                            ).props(
                                "clearable use-input input-debounce=0"
                            ).classes("grow min-w-[230px]")

                            quantity_input = ui.number(
                                label="Quantité",
                                value=1,
                                min=1,
                                step=1,
                            ).classes("w-28")

                            note_input = ui.input(
                                label="Précision",
                                placeholder="Ex. boîtes de 398 ml",
                            ).classes("grow min-w-[190px]")

                            def add_selected(
                                selected_recipe_id=recipe_id,
                                selected_item_input=item_input,
                                selected_quantity_input=quantity_input,
                                selected_note_input=note_input,
                            ):
                                if selected_item_input.value is None:
                                    ui.notify(
                                        "Choisissez un item.",
                                        type="warning",
                                    )
                                    return

                                try:
                                    add_recipe_ingredient(
                                        user_id,
                                        selected_recipe_id,
                                        int(selected_item_input.value),
                                        selected_quantity_input.value,
                                        selected_note_input.value,
                                    )
                                except (
                                    ValueError,
                                    PermissionError,
                                ) as error:
                                    ui.notify(str(error), type="warning")
                                    return

                                save_recipe_open_state(
                                    selected_recipe_id,
                                    True,
                                )
                                selected_item_input.value = None
                                selected_quantity_input.value = 1
                                selected_note_input.value = ""
                                selected_item_input.update()
                                selected_quantity_input.update()
                                selected_note_input.update()
                                render_recipes.refresh()
                                ui.notify(
                                    "Ingrédient ajouté à la recette.",
                                    type="positive",
                                )

                            ui.button(
                                "Ajouter",
                                icon="add",
                                on_click=add_selected,
                            ).props("color=primary")
                    else:
                        ui.label(
                            "Créez d’abord des items dans la page Items."
                        ).classes("text-sm text-orange-700")

                    if recipe["instructions"]:
                        ui.separator()
                        ui.label("Préparation").classes("text-lg font-bold")
                        ui.label(recipe["instructions"]).classes(
                            "text-sm whitespace-pre-wrap text-gray-700"
                        ).style("overflow-wrap:anywhere;")

    render_recipes()
