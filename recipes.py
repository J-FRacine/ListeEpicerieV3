from nicegui import app, ui

from auth import get_current_user_id
from app_access import user_has_app_access
from db import (
    add_recipe_free_ingredient,
    add_recipe_ingredient,
    apply_recipe_to_needs,
    create_recipe,
    delete_recipe,
    get_accessible_families,
    get_items,
    get_recipe_ingredients,
    get_recipes,
    link_recipe_free_ingredient_to_item,
    move_recipe_ingredient,
    refresh_public_recipe,
    remove_recipe_ingredient,
    set_recipe_public,
    update_recipe,
    update_recipe_ingredient,
)
from recipes_categories import (
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
from recipes_navigation import (
    breadcrumb_parts,
    build_category_navigation,
    recent_recipe_ids,
    recipe_ids_for_navigation,
)
from recipes_chatgpt_import_ui import open_chatgpt_recipe_import_dialog
from recipes_extras import (
    get_recipe_extras,
    nutrition_short_label,
    recipe_extra_search_text,
    recipe_time_label,
    save_recipe_metadata,
)
from recipes_extras_ui import open_nutrition_dialog
from recipes_export_ui import open_recipe_export_dialog
from recipes_ingredient_tools_ui import open_measurement_converter_dialog
from recipes_photo_data import (
    get_recipe_photo,
    get_recipe_photo_thumbnails,
)
from recipes_photo_images import recipe_photo_to_data_url
from recipes_photo_ui import open_recipe_photo_dialog
from recipes_reader import build_recipe_reader, recipe_matches
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
    total = int(result.get("items_total") or 0)
    added = int(result.get("items_added") or 0)
    quantities = int(result.get("quantities_updated") or 0)
    free_skipped = int(result.get("free_ingredients_skipped") or 0)

    if total == 0 and free_skipped:
        return (
            "Aucun ingrédient relié à l’épicerie à ajouter. "
            f"{free_skipped} ingrédient"
            + ("" if free_skipped == 1 else "s")
            + " libre"
            + ("" if free_skipped == 1 else "s")
            + " reste"
            + ("" if free_skipped == 1 else "nt")
            + " seulement dans la recette."
        )

    message = (
        f"{total} ingrédient relié traité"
        if total == 1
        else f"{total} ingrédients reliés traités"
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

    if free_skipped:
        message += (
            f", {free_skipped} ingrédient libre non ajouté"
            if free_skipped == 1
            else f", {free_skipped} ingrédients libres non ajoutés"
        )

    return message + "."


def recipes_panel():
    user_id = get_current_user_id()
    family_id = get_current_family_id()
    has_grocery_access = user_has_app_access(
        user_id,
        "grocery",
    ) if user_id is not None else False
    open_storage_key = f"open_grocery_recipes_{family_id}"
    search_state = {
        "text": "",
        "view": "home",
        "main_category_id": None,
        "subcategory_id": None,
    }

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
                (
                    "Créez, consultez et partagez vos recettes, puis "
                    "envoyez leurs ingrédients dans la liste d’épicerie."
                    if has_grocery_access
                    else
                    "Créez, consultez et partagez vos recettes. "
                    "L’intégration à la Liste d’épicerie n’est pas "
                    "activée pour ce compte."
                )
            ).classes("text-sm text-gray-500")
        ui.icon("restaurant_menu").classes("text-4xl text-primary")

    def recipe_form(title, recipe=None):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-3xl p-5"):
                ui.label(title).classes("text-xl font-bold")
                ui.label(
                    "Sur ordinateur, utilisez cet écran pour préparer le contenu. Sur téléphone ou tablette, le bouton Consulter offre une lecture plus simple."
                ).classes("text-xs text-gray-500")

                extras = (
                    get_recipe_extras(user_id, recipe["id"])
                    if recipe
                    else {}
                )
                source = extras.get("source") or {}

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

                with ui.row().classes("w-full gap-3 flex-wrap"):
                    prep_time_input = ui.number(
                        label="Préparation (minutes)",
                        value=extras.get("prep_time_minutes"),
                        min=0,
                        step=1,
                    ).classes("grow min-w-[170px]")
                    cook_time_input = ui.number(
                        label="Cuisson (minutes)",
                        value=extras.get("cook_time_minutes"),
                        min=0,
                        step=1,
                    ).classes("grow min-w-[170px]")

                tags_input = ui.input(
                    label="Étiquettes facultatives",
                    value=", ".join(extras.get("tags") or []),
                    placeholder="Ex. rapide, congélation, végétarien",
                ).classes("w-full")

                with ui.row().classes("w-full gap-3 flex-wrap"):
                    source_name_input = ui.input(
                        label="Source facultative",
                        value=source.get("name") or "",
                        placeholder="Ex. ChatGPT, Ricardo, recette familiale",
                    ).classes("grow min-w-[220px]")
                    source_url_input = ui.input(
                        label="Lien source facultatif",
                        value=source.get("url") or "",
                        placeholder="https://...",
                    ).classes("grow min-w-[280px]")

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
                        save_recipe_metadata(
                            user_id,
                            saved_recipe_id,
                            prep_time_minutes=prep_time_input.value,
                            cook_time_minutes=cook_time_input.value,
                            tags=tags_input.value,
                            source_name=source_name_input.value,
                            source_url=source_url_input.value,
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
            "Importer depuis ChatGPT",
            icon="data_object",
            on_click=lambda: open_chatgpt_recipe_import_dialog(
                user_id=user_id,
                family_id=family_id,
                on_imported=render_recipes.refresh,
                allow_grocery_integration=has_grocery_access,
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

        if has_grocery_access:
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

    with ui.column().classes("w-full gap-1 mt-2"):
        search_input = ui.input(
            label="Rechercher une recette",
            placeholder=(
                "Nom, description, préparation, ingrédient, "
                "catégorie ou étiquette"
            ),
        ).props("clearable debounce=180 autocomplete=off").classes(
            "w-full"
        )
        with search_input.add_slot("prepend"):
            ui.icon("search")
        ui.label(
            "La recherche couvre toutes les catégories."
        ).classes("text-xs text-gray-500")

    def search_changed(event):
        search_state["text"] = str(event.value or "")
        render_recipes.refresh()

    search_input.on_value_change(search_changed)

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
                is_free = bool(ingredient.get("is_free"))
                ui.label(
                    "Modifier l’ingrédient libre"
                    if is_free
                    else ingredient["name"]
                ).classes("text-xl font-bold")

                name_input = None
                link_checkbox = None
                item_select = None
                item_link_box = None

                if is_free:
                    name_input = ui.input(
                        label="Nom",
                        value=ingredient["name"],
                        placeholder="Ex. légumes au choix, fines herbes...",
                    ).classes("w-full")
                    ui.label(
                        "Cet ingrédient appartient seulement à la recette "
                        "et ne sera pas ajouté automatiquement à l’épicerie."
                    ).classes("text-xs text-gray-500")

                    if has_grocery_access:
                        available_items = get_items(
                            user_id,
                            family_id,
                        )
                        link_options = _item_options(
                            available_items
                        )
                        if link_options:
                            link_checkbox = ui.checkbox(
                                "Relier à un item de la liste d’épicerie",
                                value=False,
                            )
                            item_link_box = ui.column().classes(
                                "w-full gap-1"
                            )
                            item_link_box.set_visibility(False)
                            with item_link_box:
                                item_select = ui.select(
                                    options=link_options,
                                    label="Item d’épicerie",
                                    with_input=True,
                                ).props(
                                    "clearable use-input input-debounce=0"
                                ).classes("w-full")
                                ui.label(
                                    "Le nom de l’item remplacera le nom libre. "
                                    "La quantité, la précision et la position "
                                    "dans la recette seront conservées."
                                ).classes("text-xs text-gray-500")

                            def toggle_item_link(event):
                                item_link_box.set_visibility(
                                    bool(event.value)
                                )

                            link_checkbox.on_value_change(
                                toggle_item_link
                            )

                quantity_input = ui.number(
                    label="Quantité",
                    value=ingredient["quantity"],
                    min=1,
                    step=1,
                ).classes("w-full")
                note_input = ui.input(
                    label="Précision facultative",
                    value=ingredient["note"],
                    placeholder="Ex. au goût, assez pour couvrir...",
                ).classes("w-full")

                def save():
                    try:
                        if (
                            is_free
                            and link_checkbox is not None
                            and bool(link_checkbox.value)
                        ):
                            if (
                                item_select is None
                                or item_select.value is None
                            ):
                                ui.notify(
                                    "Choisissez l’item d’épicerie à relier.",
                                    type="warning",
                                )
                                return
                            link_recipe_free_ingredient_to_item(
                                user_id,
                                ingredient["id"],
                                int(item_select.value),
                                quantity=quantity_input.value,
                                note=note_input.value,
                            )
                        else:
                            update_recipe_ingredient(
                                user_id,
                                ingredient["id"],
                                quantity_input.value,
                                note_input.value,
                                name=(
                                    name_input.value
                                    if name_input is not None
                                    else None
                                ),
                            )
                    except (ValueError, PermissionError) as error:
                        ui.notify(str(error), type="warning")
                        return
                    dialog.close()
                    render_recipes.refresh()
                    ui.notify(
                        (
                            "Ingrédient relié à l’épicerie."
                            if (
                                is_free
                                and link_checkbox is not None
                                and bool(link_checkbox.value)
                            )
                            else "Ingrédient modifié."
                        ),
                        type="positive",
                    )

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

    def navigate_recipes(
        view,
        *,
        main_category_id=None,
        subcategory_id=None,
    ):
        search_state["view"] = str(view or "home")
        search_state["main_category_id"] = (
            int(main_category_id)
            if main_category_id not in (None, "")
            else None
        )
        search_state["subcategory_id"] = (
            int(subcategory_id)
            if subcategory_id not in (None, "")
            else None
        )
        render_recipes.refresh()

    def render_navigation_card(
        title,
        count,
        *,
        icon,
        on_click,
        caption="",
    ):
        with ui.card().classes(
            "w-full p-4 cursor-pointer shadow-sm "
            "border border-gray-200 hover:shadow-md"
        ) as card:
            card.on("click", on_click)
            with ui.row().classes(
                "w-full items-center gap-3 flex-nowrap"
            ):
                ui.icon(icon).classes(
                    "text-3xl text-primary shrink-0"
                )
                with ui.column().classes("gap-0 grow min-w-0"):
                    ui.label(title).classes(
                        "font-bold text-base whitespace-normal"
                    )
                    if caption:
                        ui.label(caption).classes(
                            "text-xs text-gray-500 whitespace-normal"
                        )
                ui.badge(str(int(count or 0))).props(
                    "outline color=primary"
                )

    @ui.refreshable
    def render_recipes():
        recipe_rows = get_recipes(user_id, family_id)
        current_category_rows = list_recipe_categories(
            user_id,
            family_id,
        )
        category_assignments = get_recipe_category_assignments(
            user_id,
            family_id,
        )
        navigation = build_category_navigation(
            recipe_rows,
            current_category_rows,
            category_assignments,
        )

        valid_recipe_ids = {
            int(recipe["id"])
            for recipe in recipe_rows
        }
        open_recipe_ids = get_open_recipe_ids() & valid_recipe_ids
        app.storage.user[open_storage_key] = sorted(open_recipe_ids)

        if not recipe_rows:
            with ui.card().classes(
                "w-full p-7 items-center text-center mt-3"
            ):
                ui.icon("menu_book").classes(
                    "text-5xl text-primary"
                )
                ui.label("Aucune recette").classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "Créez votre première recette, puis associez "
                    "ses ingrédients aux items de la famille."
                ).classes("text-gray-500")
            return

        query = str(
            search_state["text"] or ""
        ).strip().casefold()

        if not query and search_state["view"] == "home":
            with ui.row().classes(
                "w-full items-center justify-between "
                "gap-2 flex-wrap mt-2"
            ):
                with ui.column().classes("gap-0"):
                    ui.label(
                        "Parcourir par catégorie"
                    ).classes("text-xl font-bold")
                    ui.label(
                        "Choisissez une catégorie pour afficher "
                        "seulement les recettes qui vous intéressent."
                    ).classes("text-sm text-gray-500")
                ui.label(
                    f"{navigation['total_count']} recettes"
                ).classes("text-sm text-gray-500")

            with ui.element("div").classes(
                "w-full grid grid-cols-1 sm:grid-cols-2 "
                "lg:grid-cols-3 xl:grid-cols-4 gap-3 mt-2"
            ):
                render_navigation_card(
                    "Toutes les recettes",
                    navigation["total_count"],
                    icon="menu_book",
                    caption="Afficher le catalogue complet",
                    on_click=lambda _event: navigate_recipes("all"),
                )
                render_navigation_card(
                    "Récentes",
                    min(10, navigation["total_count"]),
                    icon="history",
                    caption="Les 10 dernières modifiées",
                    on_click=lambda _event: navigate_recipes("recent"),
                )

                for main_category in navigation["main_categories"]:
                    main_id = int(main_category["id"])
                    render_navigation_card(
                        main_category["name"],
                        main_category["count"],
                        icon="folder",
                        caption=(
                            f"{len(main_category['children'])} "
                            "sous-catégorie(s)"
                            if main_category["children"]
                            else "Catégorie"
                        ),
                        on_click=(
                            lambda _event, category_id=main_id:
                            navigate_recipes(
                                "main",
                                main_category_id=category_id,
                            )
                        ),
                    )

                if navigation["uncategorized_count"]:
                    render_navigation_card(
                        "Sans catégorie",
                        navigation["uncategorized_count"],
                        icon="folder_off",
                        caption="Recettes à classer",
                        on_click=lambda _event: navigate_recipes(
                            "uncategorized"
                        ),
                    )
            return

        if query:
            candidate_recipe_ids = valid_recipe_ids
            with ui.row().classes(
                "w-full items-center gap-2 flex-wrap mt-2"
            ):
                ui.button(
                    "Catégories",
                    icon="arrow_back",
                    on_click=lambda: (
                        search_input.set_value(""),
                        navigate_recipes("home"),
                    ),
                ).props("flat dense color=primary")
                ui.icon("chevron_right").classes("text-gray-400")
                ui.label(
                    "Résultats de recherche"
                ).classes("font-semibold")
        else:
            view = search_state["view"]
            candidate_recipe_ids = recipe_ids_for_navigation(
                recipe_rows,
                current_category_rows,
                category_assignments,
                view=view,
                main_category_id=search_state["main_category_id"],
                subcategory_id=search_state["subcategory_id"],
            )

            with ui.row().classes(
                "w-full items-center gap-1 flex-wrap mt-2"
            ):
                ui.button(
                    "Catégories",
                    icon="home",
                    on_click=lambda: navigate_recipes("home"),
                ).props("flat dense color=primary")

                for part in breadcrumb_parts(
                    current_category_rows,
                    view=view,
                    main_category_id=search_state["main_category_id"],
                    subcategory_id=search_state["subcategory_id"],
                ):
                    ui.icon("chevron_right").classes(
                        "text-gray-400"
                    )
                    ui.label(part).classes("font-semibold")

            if view in {"main", "subcategory"}:
                selected_main = next(
                    (
                        row
                        for row in navigation["main_categories"]
                        if int(row["id"])
                        == int(search_state["main_category_id"])
                    ),
                    None,
                )
                if selected_main and selected_main["children"]:
                    with ui.row().classes(
                        "w-full gap-2 flex-wrap mt-1"
                    ):
                        all_button = ui.button(
                            f"Toutes ({selected_main['count']})",
                            on_click=lambda category_id=selected_main["id"]:
                            navigate_recipes(
                                "main",
                                main_category_id=category_id,
                            ),
                        ).props("dense no-caps")
                        if view == "main":
                            all_button.props("color=primary")
                        else:
                            all_button.props("outline color=primary")

                        for child in selected_main["children"]:
                            child_id = int(child["id"])
                            child_button = ui.button(
                                f"{child['name']} ({child['count']})",
                                on_click=(
                                    lambda category_id=selected_main["id"],
                                    sub_id=child_id:
                                    navigate_recipes(
                                        "subcategory",
                                        main_category_id=category_id,
                                        subcategory_id=sub_id,
                                    )
                                ),
                            ).props("dense no-caps")
                            if (
                                view == "subcategory"
                                and int(
                                    search_state["subcategory_id"]
                                    or 0
                                ) == child_id
                            ):
                                child_button.props("color=primary")
                            else:
                                child_button.props(
                                    "outline color=primary"
                                )

        candidate_rows = [
            recipe
            for recipe in recipe_rows
            if int(recipe["id"]) in candidate_recipe_ids
        ]

        if not query and search_state["view"] == "recent":
            recent_ids = recent_recipe_ids(
                candidate_rows,
                limit=10,
            )
            recent_position = {
                recipe_id: index
                for index, recipe_id in enumerate(recent_ids)
            }
            candidate_rows = [
                recipe
                for recipe in candidate_rows
                if int(recipe["id"]) in recent_position
            ]
            candidate_rows.sort(
                key=lambda recipe: recent_position[int(recipe["id"])]
            )

        if has_grocery_access:
            items = get_items(user_id, family_id)
        else:
            items = []
        options = _item_options(items)
        photo_thumbnails = get_recipe_photo_thumbnails(
            user_id,
            family_id,
        )

        details = []
        for recipe in candidate_rows:
            ingredients = get_recipe_ingredients(
                user_id,
                recipe["id"],
            )
            assignment = category_assignments.get(
                int(recipe["id"]),
                {},
            )
            extras = get_recipe_extras(
                user_id,
                recipe["id"],
            )
            category_text = str(
                assignment.get("category_path") or ""
            )

            if query:
                text_matches = recipe_matches(
                    recipe,
                    ingredients,
                    search_state["text"],
                ) or (
                    query in category_text.casefold()
                ) or (
                    query in recipe_extra_search_text(extras)
                )
                if not text_matches:
                    continue

            details.append(
                (
                    recipe,
                    ingredients,
                    assignment,
                    extras,
                )
            )

        ui.label(
            f"{len(details)} recette"
            if len(details) == 1
            else f"{len(details)} recettes"
        ).classes("text-sm text-gray-500 mt-1")

        if not details:
            with ui.card().classes(
                "w-full p-6 items-center text-center mt-2"
            ):
                ui.icon("search_off").classes(
                    "text-4xl text-gray-400"
                )
                ui.label(
                    "Aucune recette trouvée"
                ).classes("text-lg font-bold")
                ui.label(
                    (
                        "Modifiez ou effacez la recherche pour "
                        "voir d’autres recettes."
                        if query
                        else "Cette catégorie ne contient aucune recette."
                    )
                ).classes("text-sm text-gray-500")
            return

        for recipe, ingredients, category_assignment, recipe_extras in details:
            recipe_id = recipe["id"]
            ingredient_count = len(ingredients)
            category_text = str(
                category_assignment.get("category_path") or ""
            )

            recipe_thumbnail = photo_thumbnails.get(
                int(recipe_id)
            )
            recipe_thumbnail_url = recipe_photo_to_data_url(
                recipe_thumbnail
            )

            def consult_selected(
                selected_recipe=recipe,
                selected_ingredients=ingredients,
                selected_extras=recipe_extras,
            ):
                try:
                    full_photo = get_recipe_photo(
                        user_id,
                        selected_recipe["id"],
                    )
                except Exception as error:
                    ui.notify(
                        f"La photo n’a pas pu être chargée : {error}",
                        type="warning",
                    )
                    full_photo = None

                build_recipe_reader(
                    ui=ui,
                    recipe=selected_recipe,
                    ingredients=selected_ingredients,
                    extras=selected_extras,
                    photo_data_url=recipe_photo_to_data_url(
                        full_photo
                    ),
                    on_add_to_needs=(
                        (
                            lambda selected_id=selected_recipe["id"]:
                            apply_recipe_to_needs(
                                user_id,
                                selected_id,
                            )
                        )
                        if has_grocery_access
                        else None
                    ),
                    summary_message=(
                        _summary_message
                        if has_grocery_access
                        else None
                    ),
                    on_export=(
                        lambda selected=selected_recipe:
                        open_recipe_export_dialog(
                            user_id=user_id,
                            recipe=selected,
                        )
                    ),
                )

            details_context = {
                "open": recipe_id in open_recipe_ids,
                "container": None,
            }

            def toggle_recipe_details(
                selected_recipe_id=recipe_id,
                context=details_context,
            ):
                new_value = not context["open"]
                context["open"] = new_value
                save_recipe_open_state(
                    selected_recipe_id,
                    new_value,
                )

                container = context.get("container")
                if container is not None:
                    container.set_visibility(
                        new_value
                    )

            with ui.card().classes(
                "w-full p-0 bg-white rounded-xl shadow-sm "
                "border border-gray-200 overflow-hidden mt-3"
            ):
                with ui.row().classes(
                    "w-full items-center gap-3 flex-nowrap px-3 py-3"
                ):
                    ui.button(
                        "Consulter",
                        icon="menu_book",
                        on_click=consult_selected,
                    ).props(
                        "color=primary dense no-caps"
                    ).classes("shrink-0")

                    if recipe_thumbnail_url:
                        ui.image(
                            recipe_thumbnail_url
                        ).classes(
                            "w-14 h-14 rounded-lg shrink-0"
                        ).props("fit=cover")
                    else:
                        ui.icon("restaurant").classes(
                            "text-2xl text-primary shrink-0"
                        )

                    with ui.column().classes(
                        "gap-0 min-w-0 grow"
                    ):
                        ui.label(
                            recipe["name"]
                        ).classes(
                            "text-base font-medium whitespace-normal"
                        ).style(
                            "overflow-wrap:anywhere;"
                        )
                        ui.label(
                            _recipe_caption(
                                recipe["servings"],
                                ingredient_count,
                                category_text,
                            )
                        ).classes(
                            "text-sm text-gray-500 whitespace-normal"
                        )

                    ui.button(
                        icon="unfold_more",
                        on_click=toggle_recipe_details,
                    ).props(
                        "flat round dense color=primary"
                    ).classes("shrink-0").tooltip(
                        "Afficher ou masquer les détails"
                    )

                details_container = ui.column().classes(
                    "w-full gap-3 px-4 pb-4"
                )
                details_context["container"] = details_container
                details_container.set_visibility(
                    details_context["open"]
                )

                with details_container:
                    if recipe["description"]:
                        ui.label(recipe["description"]).classes(
                            "text-sm text-gray-600 whitespace-normal"
                        ).style("overflow-wrap:anywhere;")

                    time_label = recipe_time_label(recipe_extras)
                    tags = recipe_extras.get("tags") or []
                    source = recipe_extras.get("source") or {}
                    nutrition = recipe_extras.get("nutrition")

                    with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                        if time_label:
                            ui.badge(time_label).props("outline color=primary")
                        for tag in tags:
                            ui.badge(tag).props("outline color=secondary")
                        if nutrition:
                            ui.badge(
                                nutrition_short_label(
                                    nutrition,
                                    recipe["servings"],
                                )
                            ).props("outline color=positive")

                    if source.get("name") or source.get("url"):
                        with ui.row().classes("w-full gap-2 items-center flex-wrap"):
                            if source.get("name"):
                                ui.label(
                                    "Source : " + source["name"]
                                ).classes("text-xs text-gray-500")
                            if source.get("url"):
                                ui.link(
                                    "Ouvrir la source",
                                    source["url"],
                                    new_tab=True,
                                ).classes("text-xs")

                    with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                        def add_selected_to_needs(selected=recipe):
                            try:
                                result = apply_recipe_to_needs(user_id, selected["id"])
                            except (ValueError, PermissionError) as error:
                                ui.notify(str(error), type="warning")
                                return
                            ui.notify(
                                _summary_message(result), type="positive", timeout=5000
                            )

                        if has_grocery_access:
                            ui.button(
                                "Ajouter à l’épicerie",
                                icon="playlist_add",
                                on_click=add_selected_to_needs,
                            ).props("outline color=positive")

                        ui.button(
                            "Photo",
                            icon="photo_camera",
                            on_click=lambda selected=recipe: open_recipe_photo_dialog(
                                user_id=user_id,
                                recipe=selected,
                                on_saved=render_recipes.refresh,
                            ),
                        ).props("flat color=primary")

                        ui.button(
                            "Valeurs nutritives",
                            icon="monitor_weight",
                            on_click=lambda selected=recipe: open_nutrition_dialog(
                                user_id=user_id,
                                recipe=selected,
                                on_saved=render_recipes.refresh,
                            ),
                        ).props("flat color=primary")

                        ui.button(
                            "Mesures",
                            icon="scale",
                            on_click=lambda selected=recipe: open_measurement_converter_dialog(
                                user_id=user_id,
                                recipe=selected,
                                on_saved=render_recipes.refresh,
                            ),
                        ).props("flat color=primary")

                        ui.button(
                            "PDF / courriel",
                            icon="picture_as_pdf",
                            on_click=lambda selected=recipe: open_recipe_export_dialog(
                                user_id=user_id,
                                recipe=selected,
                            ),
                        ).props("flat color=primary")

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
                                        if ingredient.get("is_free"):
                                            ui.label(
                                                "Ingrédient libre · "
                                                "non ajouté automatiquement à l’épicerie"
                                            ).classes(
                                                "text-xs text-orange-700"
                                            )
                                        else:
                                            ui.label(
                                                f"{ingredient['store']} · "
                                                f"{ingredient['category']}"
                                            ).classes(
                                                "text-xs text-gray-500"
                                            )
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

                    ui.separator()
                    ui.label("Ajouter un ingrédient").classes("font-bold")
                    ui.label(
                        "Choisissez un item d’épicerie existant ou ajoutez "
                        "un ingrédient libre qui restera propre à la recette."
                    ).classes("text-xs text-gray-500")

                    if has_grocery_access and options:
                        ui.label(
                            "Item d’épicerie existant"
                        ).classes("text-sm font-semibold mt-1")
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
                                render_recipes.refresh()
                                ui.notify(
                                    "Item d’épicerie ajouté à la recette.",
                                    type="positive",
                                )

                            ui.button(
                                "Ajouter l’item",
                                icon="add",
                                on_click=add_selected,
                            ).props("color=primary")
                    elif has_grocery_access:
                        ui.label(
                            "Aucun item d’épicerie disponible. "
                            "Vous pouvez quand même ajouter des ingrédients libres."
                        ).classes("text-sm text-orange-700")
                    else:
                        ui.label(
                            "Les ingrédients sont ajoutés comme ingrédients "
                            "libres parce que ce compte n’a pas accès à "
                            "la Liste d’épicerie."
                        ).classes("text-sm text-gray-500")

                    ui.label(
                        "Ingrédient libre"
                    ).classes("text-sm font-semibold mt-2")
                    with ui.row().classes("w-full items-end gap-2 flex-wrap"):
                        free_name_input = ui.input(
                            label="Nom",
                            placeholder=(
                                "Ex. légumes au choix, champignons, "
                                "fines herbes..."
                            ),
                        ).classes("grow min-w-[230px]")
                        free_quantity_input = ui.number(
                            label="Quantité",
                            value=1,
                            min=1,
                            step=1,
                        ).classes("w-28")
                        free_note_input = ui.input(
                            label="Précision",
                            placeholder="Ex. au goût, assez pour couvrir...",
                        ).classes("grow min-w-[190px]")

                        def add_free(
                            selected_recipe_id=recipe_id,
                            name_field=free_name_input,
                            quantity_field=free_quantity_input,
                            note_field=free_note_input,
                        ):
                            try:
                                add_recipe_free_ingredient(
                                    user_id,
                                    selected_recipe_id,
                                    name_field.value,
                                    quantity_field.value,
                                    note_field.value,
                                )
                            except (
                                ValueError,
                                PermissionError,
                            ) as error:
                                ui.notify(str(error), type="warning")
                                return

                            save_recipe_open_state(selected_recipe_id, True)
                            render_recipes.refresh()
                            ui.notify(
                                "Ingrédient libre ajouté à la recette.",
                                type="positive",
                            )

                        ui.button(
                            "Ajouter libre",
                            icon="post_add",
                            on_click=add_free,
                        ).props("outline color=primary")

                    if recipe["instructions"]:
                        ui.separator()
                        ui.label("Préparation").classes("text-lg font-bold")
                        ui.label(recipe["instructions"]).classes(
                            "text-sm whitespace-pre-wrap text-gray-700"
                        ).style("overflow-wrap:anywhere;")

    render_recipes()
