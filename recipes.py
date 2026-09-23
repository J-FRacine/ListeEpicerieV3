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
    refresh_public_recipe,
    remove_recipe_ingredient,
    set_recipe_public,
    update_recipe,
    update_recipe_ingredient,
)
from recipes_categories import (
    category_matches_filter,
    get_recipe_category_assignment,
    get_recipe_category_assignments,
    list_recipe_categories,
    recipe_category_options,
    set_recipe_category,
)
from recipes_management import (
    open_bulk_delete_dialog,
    open_recipe_categories_dialog,
)
from recipes_reader import build_recipe_reader, recipe_matches
from recipes_site_import_ui import open_recipe_site_import_dialog
from state import get_current_family_id, set_current_family_id
from utils import ensure_family_selected


def _item_options(items):
    return {
        item["id"]: f"{item['name']} — {item['store']} / {item['category']}"
        for item in items
    }


def _recipe_caption(servings, ingredient_count, category_path=""):
    serving_text = "1 portion" if servings == 1 else f"{servings} portions"
    ingredient_text = (
        "1 ingrédient" if ingredient_count == 1 else f"{ingredient_count} ingrédients"
    )
    caption = f"{serving_text} · {ingredient_text}"
    if category_path:
        caption += f" · {category_path}"
    return caption


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
    open_storage_key = f"open_grocery_recipes_{family_id}"
    search_state = {"text": "", "category_id": 0}

    def get_open_recipe_ids():
        stored_ids = app.storage.user.get(open_storage_key, [])
        result = set()
        for stored_id in stored_ids:
            try:
                result.add(int(stored_id))
            except (TypeError, ValueError):
                continue
        return result

    def save_recipe_open_state(recipe_id, is_open):
        open_ids = get_open_recipe_ids()
        if is_open:
            open_ids.add(int(recipe_id))
        else:
            open_ids.discard(int(recipe_id))
        app.storage.user[open_storage_key] = sorted(open_ids)

    if user_id is None or not ensure_family_selected(family_id):
        return

    families = get_accessible_families(user_id)
    if not families:
        ui.label("Aucune famille accessible.").classes("text-orange-700")
        return

    family_by_name = {family["name"]: family["id"] for family in families}
    current_name = next(
        (
            name
            for name, accessible_id in family_by_name.items()
            if accessible_id == family_id
        ),
        list(family_by_name)[0],
    )

    with ui.row().classes("w-full items-end gap-3 flex-wrap"):
        ui.select(
            list(family_by_name),
            value=current_name,
            label="Famille",
            on_change=lambda event: (
                set_current_family_id(family_by_name[event.value]),
                ui.navigate.to("/?tab=recettes"),
            ),
        ).classes("grow min-w-[220px]")

        ui.button(
            "Nouvelle recette",
            icon="add",
            on_click=lambda: recipe_form("Nouvelle recette"),
        ).props("color=primary")

    with ui.row().classes("w-full items-start justify-between gap-3 flex-wrap mt-2"):
        with ui.column().classes("gap-0"):
            ui.label("Mes recettes").classes("text-2xl font-bold")
            ui.label(
                "Créez, consultez et partagez vos recettes, puis envoyez leurs ingrédients dans la liste d’épicerie."
            ).classes("text-sm text-gray-500")
        ui.icon("restaurant_menu").classes("text-4xl text-primary")

    def recipe_form(title, recipe=None):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-3xl p-5"):
                ui.label(title).classes("text-xl font-bold")
                ui.label(
                    "Sur ordinateur, utilisez cet écran pour préparer le contenu. Sur téléphone ou tablette, le bouton Consulter offre une lecture plus simple."
                ).classes("text-xs text-gray-500")

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
                    label="Préparation — une étape par ligne de préférence",
                    value=recipe["instructions"] if recipe else "",
                    placeholder=(
                        "Ex.\nCuire la viande.\nAjouter le maïs.\nCouvrir de purée et cuire au four."
                    ),
                ).props("autogrow").classes("w-full")

                category_rows = list_recipe_categories(user_id, family_id)
                current_category = (
                    get_recipe_category_assignment(user_id, recipe["id"])
                    if recipe
                    else None
                )
                category_input = ui.select(
                    recipe_category_options(category_rows),
                    value=(
                        current_category.get("category_id")
                        if current_category
                        else None
                    ),
                    label="Catégorie de recette",
                ).props("outlined clearable").classes("w-full")
                if not category_rows:
                    ui.label(
                        "Aucune catégorie de recette. Utilisez le bouton Catégories "
                        "dans l’écran principal pour en créer."
                    ).classes("text-xs text-orange-700")

                def save():
                    try:
                        if recipe:
                            saved_recipe_id = recipe["id"]
                            update_recipe(
                                user_id,
                                saved_recipe_id,
                                name_input.value,
                                description_input.value,
                                instructions_input.value,
                                servings_input.value,
                            )
                        else:
                            saved_recipe_id = create_recipe(
                                user_id,
                                family_id,
                                name_input.value,
                                description_input.value,
                                instructions_input.value,
                                servings_input.value,
                            )
                        set_recipe_category(
                            user_id,
                            saved_recipe_id,
                            category_input.value,
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

    with ui.row().classes("w-full gap-2 flex-wrap mt-2"):
        ui.button(
            "Importer mon ancien site",
            icon="cloud_download",
            on_click=lambda: open_recipe_site_import_dialog(
                user_id=user_id,
                family_id=family_id,
                on_imported=render_recipes.refresh,
            ),
        ).props("outline color=primary")

        ui.button(
            "Catégories",
            icon="category",
            on_click=lambda: open_recipe_categories_dialog(
                user_id=user_id,
                family_id=family_id,
                on_close_refresh=lambda: ui.navigate.to("/?tab=recettes"),
            ),
        ).props("flat color=primary")

        ui.button(
            "Supprimer plusieurs",
            icon="delete_sweep",
            on_click=lambda: open_bulk_delete_dialog(
                user_id=user_id,
                family_id=family_id,
                on_deleted=render_recipes.refresh,
            ),
        ).props("flat color=negative")

        ui.button(
            "Listes modèles",
            icon="checklist",
            on_click=lambda: ui.navigate.to("/?tab=modeles"),
        ).props("flat color=primary")
        ui.button(
            "Bibliothèque partagée",
            icon="public",
            on_click=lambda: ui.navigate.to("/?tab=bibliotheque"),
        ).props("flat color=primary")

    category_filter_rows = list_recipe_categories(user_id, family_id)
    with ui.row().classes("w-full gap-2 items-end flex-wrap mt-2"):
        search_input = ui.input(
            label="Rechercher une recette",
            placeholder="Nom, description, préparation, ingrédient ou catégorie",
        ).props("clearable debounce=180 autocomplete=off").classes(
            "grow min-w-[260px]"
        )
        with search_input.add_slot("prepend"):
            ui.icon("search")

        category_filter = ui.select(
            recipe_category_options(
                category_filter_rows,
                include_all=True,
            ),
            value=0,
            label="Catégorie",
        ).props("outlined dense").classes("grow min-w-[220px]")

    def search_changed(event):
        search_state["text"] = str(event.value or "")
        render_recipes.refresh()

    def category_changed(event):
        try:
            search_state["category_id"] = int(event.value or 0)
        except (TypeError, ValueError):
            search_state["category_id"] = 0
        render_recipes.refresh()

    search_input.on_value_change(search_changed)
    category_filter.on_value_change(category_changed)

    def confirm_delete(recipe):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-md p-5"):
                ui.label("Supprimer la recette?").classes("text-xl font-bold")
                ui.label(
                    f"« {recipe['name']} » sera supprimée. Les items eux-mêmes resteront dans l’application."
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
                        "Supprimer", icon="delete", on_click=perform_delete
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
                    ui.button("Enregistrer", icon="save", on_click=save).props(
                        "color=primary"
                    )

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
        recipe_rows = get_recipes(user_id, family_id)
        items = get_items(user_id, family_id)
        options = _item_options(items)

        current_category_rows = list_recipe_categories(user_id, family_id)
        category_assignments = get_recipe_category_assignments(
            user_id,
            family_id,
        )
        details = []
        query = str(search_state["text"] or "").strip().casefold()
        for recipe in recipe_rows:
            ingredients = get_recipe_ingredients(user_id, recipe["id"])
            assignment = category_assignments.get(int(recipe["id"]), {})
            assigned_category_id = assignment.get("category_id")
            if not category_matches_filter(
                assigned_category_id,
                search_state["category_id"],
                current_category_rows,
            ):
                continue
            category_text = str(
                assignment.get("category_path") or ""
            )
            text_matches = recipe_matches(
                recipe,
                ingredients,
                search_state["text"],
            ) or (
                bool(query)
                and query in category_text.casefold()
            )
            if text_matches:
                details.append((recipe, ingredients, assignment))

        valid_recipe_ids = {int(recipe["id"]) for recipe in recipe_rows}
        open_recipe_ids = get_open_recipe_ids() & valid_recipe_ids
        app.storage.user[open_storage_key] = sorted(open_recipe_ids)

        if not recipe_rows:
            with ui.card().classes("w-full p-7 items-center text-center mt-3"):
                ui.icon("menu_book").classes("text-5xl text-primary")
                ui.label("Aucune recette").classes("text-xl font-bold")
                ui.label(
                    "Créez votre première recette, puis associez ses ingrédients aux items de la famille."
                ).classes("text-gray-500")
            return

        ui.label(
            f"{len(details)} recette" if len(details) == 1 else f"{len(details)} recettes"
        ).classes("text-sm text-gray-500 mt-1")

        if not details:
            with ui.card().classes("w-full p-6 items-center text-center mt-2"):
                ui.icon("search_off").classes("text-4xl text-gray-400")
                ui.label("Aucune recette trouvée").classes("text-lg font-bold")
                ui.label("Modifiez ou effacez la recherche pour voir d’autres recettes.").classes(
                    "text-sm text-gray-500"
                )
            return

        for recipe, ingredients, category_assignment in details:
            recipe_id = recipe["id"]
            ingredient_count = len(ingredients)
            category_text = str(
                category_assignment.get("category_path") or ""
            )

            with ui.expansion(
                text=recipe["name"],
                caption=_recipe_caption(
                    recipe["servings"],
                    ingredient_count,
                    category_text,
                ),
                icon="restaurant",
                value=recipe_id in open_recipe_ids,
                on_value_change=(
                    lambda event, selected_recipe_id=recipe_id: save_recipe_open_state(
                        selected_recipe_id, bool(event.value)
                    )
                ),
            ).props("expand-separator").classes(
                "w-full bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mt-3"
            ):
                with ui.column().classes("w-full gap-3 px-2 pb-3"):
                    if recipe["description"]:
                        ui.label(recipe["description"]).classes(
                            "text-sm text-gray-600 whitespace-normal"
                        ).style("overflow-wrap:anywhere;")

                    with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                        def apply_selected(selected=recipe):
                            return apply_recipe_to_needs(user_id, selected["id"])

                        ui.button(
                            "Consulter",
                            icon="menu_book",
                            on_click=lambda selected_recipe=recipe, selected_ingredients=ingredients: (
                                build_recipe_reader(
                                    ui=ui,
                                    recipe=selected_recipe,
                                    ingredients=selected_ingredients,
                                    on_add_to_needs=lambda selected_id=selected_recipe["id"]: apply_recipe_to_needs(
                                        user_id, selected_id
                                    ),
                                    summary_message=_summary_message,
                                )
                            ),
                        ).props("color=primary")

                        def add_selected_to_needs(selected=recipe):
                            try:
                                result = apply_recipe_to_needs(user_id, selected["id"])
                            except (ValueError, PermissionError) as error:
                                ui.notify(str(error), type="warning")
                                return
                            ui.notify(
                                _summary_message(result), type="positive", timeout=5000
                            )

                        ui.button(
                            "Ajouter à l’épicerie",
                            icon="playlist_add",
                            on_click=add_selected_to_needs,
                        ).props("outline color=positive")

                        ui.button(
                            icon="edit",
                            on_click=lambda selected=recipe: recipe_form(
                                "Modifier la recette", selected
                            ),
                        ).props("flat round color=primary").tooltip("Modifier la recette")

                        ui.button(
                            icon="delete",
                            on_click=lambda selected=recipe: confirm_delete(selected),
                        ).props("flat round color=negative").tooltip("Supprimer la recette")

                    with ui.card().classes("w-full p-3 shadow-none bg-blue-50"):
                        def change_public_state(event, selected_recipe=recipe):
                            save_recipe_open_state(selected_recipe["id"], True)
                            try:
                                set_recipe_public(
                                    user_id,
                                    selected_recipe["id"],
                                    bool(event.value),
                                )
                            except (ValueError, PermissionError) as error:
                                ui.notify(str(error), type="warning")
                                render_recipes.refresh()
                                return

                            ui.notify(
                                "Recette publiée dans la bibliothèque."
                                if event.value
                                else "Recette retirée de la bibliothèque.",
                                type="positive",
                            )
                            render_recipes.refresh()

                        ui.checkbox(
                            "Publier dans la bibliothèque partagée",
                            value=bool(recipe["is_public"]),
                            on_change=change_public_state,
                        )
                        ui.label(
                            "La publication contient seulement le nom, la description, les portions, la préparation et les ingrédients génériques autorisés."
                        ).classes("text-xs text-gray-600")

                        if recipe["is_public"]:
                            if recipe["public_update_available"]:
                                ui.badge("Modifications privées à publier").props(
                                    "color=orange"
                                )

                            def refresh_public(selected_recipe=recipe):
                                save_recipe_open_state(selected_recipe["id"], True)
                                try:
                                    refresh_public_recipe(user_id, selected_recipe["id"])
                                except (ValueError, PermissionError) as error:
                                    ui.notify(str(error), type="warning")
                                    return
                                ui.notify(
                                    "Version publiée mise à jour.", type="positive"
                                )
                                render_recipes.refresh()

                            ui.button(
                                "Mettre à jour la version publiée",
                                icon="sync",
                                on_click=refresh_public,
                            ).props("flat color=primary")

                    ui.label("Ingrédients").classes("text-lg font-bold")

                    if ingredients:
                        for index, ingredient in enumerate(ingredients):
                            with ui.card().classes("w-full p-3 shadow-none"):
                                with ui.row().classes(
                                    "w-full items-center gap-2 flex-nowrap"
                                ):
                                    with ui.column().classes("gap-0 grow min-w-0"):
                                        ui.label(
                                            (
                                                f"{ingredient['name']} ({ingredient['quantity']})"
                                                if ingredient["quantity"] != 1
                                                else ingredient["name"]
                                            )
                                        ).classes("font-bold whitespace-normal").style(
                                            "overflow-wrap:anywhere;"
                                        )
                                        ui.label(
                                            f"{ingredient['store']} · {ingredient['category']}"
                                        ).classes("text-xs text-gray-500")
                                        if ingredient["note"]:
                                            ui.label(ingredient["note"]).classes(
                                                "text-xs text-gray-600 whitespace-normal"
                                            ).style("overflow-wrap:anywhere;")

                                    with ui.row().classes("items-center gap-0 shrink-0"):
                                        ui.button(
                                            icon="arrow_upward",
                                            on_click=lambda ingredient_id=ingredient[
                                                "id"
                                            ]: move_ingredient(ingredient_id, -1),
                                        ).props("flat round dense").set_enabled(index > 0)
                                        ui.button(
                                            icon="arrow_downward",
                                            on_click=lambda ingredient_id=ingredient[
                                                "id"
                                            ]: move_ingredient(ingredient_id, 1),
                                        ).props("flat round dense").set_enabled(
                                            index < ingredient_count - 1
                                        )
                                        ui.button(
                                            icon="edit",
                                            on_click=lambda selected=ingredient: edit_ingredient(
                                                selected
                                            ),
                                        ).props("flat round dense color=primary").tooltip(
                                            "Modifier l’ingrédient"
                                        )

                                        def remove_selected(
                                            ingredient_id=ingredient["id"],
                                        ):
                                            try:
                                                remove_recipe_ingredient(
                                                    user_id, ingredient_id
                                                )
                                            except (
                                                ValueError,
                                                PermissionError,
                                            ) as error:
                                                ui.notify(str(error), type="warning")
                                                return
                                            render_recipes.refresh()

                                        ui.button(
                                            icon="close", on_click=remove_selected
                                        ).props("flat round dense color=negative").tooltip(
                                            "Retirer de la recette"
                                        )
                    else:
                        ui.label(
                            "Cette recette ne contient encore aucun ingrédient."
                        ).classes("text-sm text-gray-500")

                    if options:
                        ui.separator()
                        ui.label("Ajouter un ingrédient existant").classes("font-bold")
                        with ui.row().classes("w-full items-end gap-2 flex-wrap"):
                            item_input = ui.select(
                                options=options,
                                label="Item",
                                with_input=True,
                            ).props("clearable use-input input-debounce=0").classes(
                                "grow min-w-[230px]"
                            )
                            quantity_input = ui.number(
                                label="Quantité", value=1, min=1, step=1
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
                                    ui.notify("Choisissez un item.", type="warning")
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

                                save_recipe_open_state(selected_recipe_id, True)
                                selected_item_input.value = None
                                selected_quantity_input.value = 1
                                selected_note_input.value = ""
                                selected_item_input.update()
                                selected_quantity_input.update()
                                selected_note_input.update()
                                render_recipes.refresh()
                                ui.notify(
                                    "Ingrédient ajouté à la recette.", type="positive"
                                )

                            ui.button(
                                "Ajouter", icon="add", on_click=add_selected
                            ).props("color=primary")
                    else:
                        ui.label(
                            "Créez d’abord des items dans la Liste d’épicerie."
                        ).classes("text-sm text-orange-700")

                    if recipe["instructions"]:
                        ui.separator()
                        ui.label("Préparation").classes("text-lg font-bold")
                        ui.label(recipe["instructions"]).classes(
                            "text-sm whitespace-pre-wrap text-gray-700"
                        ).style("overflow-wrap:anywhere;")

    render_recipes()
