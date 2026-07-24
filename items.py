from nicegui import app, ui

from auth import get_current_user_id
from db import (
    add_item,
    delete_item,
    get_accessible_families,
    get_categories,
    get_items,
    toggle_needed,
    update_item,
)
from state import (
    get_current_family_id,
    get_tri_mode_items,
    set_current_family_id,
    set_tri_mode_items,
)
from utils import (
    ensure_categories_exist,
    ensure_family_selected,
)


def items_panel():
    user_id = get_current_user_id()
    current_family_id = get_current_family_id()

    if (
        user_id is None
        or not ensure_family_selected(
            current_family_id
        )
    ):
        return

    families = get_accessible_families(user_id)

    if not families:
        ui.label(
            "Aucune famille accessible."
        ).classes("text-orange-700")
        return

    family_dict = {
        family["name"]: family["id"]
        for family in families
    }

    current_family_name = next(
        (
            name
            for name, family_id
            in family_dict.items()
            if family_id == current_family_id
        ),
        list(family_dict.keys())[0],
    )

    ui.select(
        list(family_dict.keys()),
        value=current_family_name,
        label="Famille",
        on_change=lambda event: (
            set_current_family_id(
                family_dict[event.value]
            ),
            ui.navigate.to("/?tab=items"),
        ),
    ).classes("w-full")

    if not ensure_categories_exist(
        user_id,
        current_family_id,
    ):
        return

    categories = get_categories(
        user_id,
        current_family_id,
    )

    category_dict = {
        category["name"]: category["id"]
        for category in categories
    }
    category_names = list(
        category_dict.keys()
    )

    # ---------------------------------------------------------
    # AJOUTER UN ITEM
    # ---------------------------------------------------------

    ui.separator()
    ui.label("Ajouter un item").classes(
        "text-xl font-bold"
    )

    with ui.card().classes("w-full p-4"):
        with ui.row().classes(
            "w-full items-end gap-3 flex-wrap"
        ):
            name_input = ui.input(
                label="Nom",
            ).props(
                "autocomplete=off"
            ).classes(
                "grow min-w-[210px]"
            )

            quantity_input = ui.number(
                label="Quantité",
                value=1,
                min=1,
                step=1,
            ).classes("w-28")

            category_input = ui.select(
                category_names,
                value=category_names[0],
                label="Catégorie",
            ).classes(
                "grow min-w-[170px]"
            )

            def add_new_item():
                item_name = (
                    name_input.value or ""
                ).strip()
                quantity = int(
                    quantity_input.value or 1
                )

                try:
                    add_item(
                        user_id,
                        current_family_id,
                        category_dict[
                            category_input.value
                        ],
                        item_name,
                        quantity,
                        0,
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

                name_input.value = ""
                quantity_input.value = 1
                name_input.update()
                quantity_input.update()
                render_items.refresh()
                name_input.run_method("focus")

                ui.notify(
                    f"« {item_name} » ajouté.",
                    type="positive",
                )

            name_input.on(
                "keydown.enter",
                add_new_item,
            )

            ui.button(
                "Ajouter",
                icon="add",
                on_click=add_new_item,
            ).props(
                "flat color=green"
            ).classes("mb-1")

    # ---------------------------------------------------------
    # RECHERCHE ET TRI
    # ---------------------------------------------------------

    ui.separator()

    search_storage_key = (
        f"items_search_{current_family_id}"
    )

    search_state = {
        "value": app.storage.user.get(
            search_storage_key,
            "",
        )
    }

    with ui.row().classes(
        "w-full items-center justify-between "
        "gap-3 flex-wrap"
    ):
        ui.label("Tous les items").classes(
            "text-xl font-bold"
        )

        with ui.row().classes(
            "items-center gap-1"
        ):
            ui.icon("sort").classes(
                "text-gray-500"
            )

            sort_input = ui.select(
                [
                    "Alphabétique",
                    "Ordre d’ajout",
                    "Catégorie",
                ],
                value=get_tri_mode_items(),
            ).props(
                "dense borderless options-dense"
            ).classes("w-40 text-sm")

    search_input = ui.input(
        label="Rechercher un item",
        value=search_state["value"],
        placeholder=(
            "Nom ou catégorie"
        ),
    ).props(
        "clearable debounce=150 "
        "autocomplete=off"
    ).classes("w-full")

    with search_input.add_slot("prepend"):
        ui.icon("search")

    # ---------------------------------------------------------
    # MODIFIER UN ITEM
    # ---------------------------------------------------------

    def open_edit_dialog(item):
        with ui.dialog() as dialog:
            with ui.card().classes(
                "w-full max-w-md p-5"
            ):
                ui.label(
                    "Modifier l’item"
                ).classes("text-xl font-bold")

                edit_name = ui.input(
                    label="Nom",
                    value=item["name"],
                ).classes("w-full")

                edit_quantity = ui.number(
                    label="Quantité",
                    value=item["quantity"],
                    min=1,
                    step=1,
                ).classes("w-full")

                edit_category = ui.select(
                    category_names,
                    value=item["category"],
                    label="Catégorie",
                ).classes("w-full")

                edit_needed = ui.checkbox(
                    "Présent dans la liste "
                    "des besoins",
                    value=item["needed"] == 1,
                )

                def save_item():
                    try:
                        update_item(
                            user_id,
                            item["id"],
                            category_dict[
                                edit_category.value
                            ],
                            (
                                edit_name.value
                                or ""
                            ).strip(),
                            int(
                                edit_quantity.value
                                or 1
                            ),
                            (
                                1
                                if edit_needed.value
                                else 0
                            ),
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

                    dialog.close()
                    render_items.refresh()

                    ui.notify(
                        "Item modifié.",
                        type="positive",
                    )

                with ui.row().classes(
                    "w-full justify-end "
                    "gap-2 mt-4"
                ):
                    ui.button(
                        "Annuler",
                        on_click=dialog.close,
                    ).props("flat")

                    ui.button(
                        "Enregistrer",
                        icon="save",
                        on_click=save_item,
                    ).props("color=primary")

        dialog.open()

    # ---------------------------------------------------------
    # LISTE FILTRÉE ET TACTILE
    # ---------------------------------------------------------

    @ui.refreshable
    def render_items():
        items = get_items(
            user_id,
            current_family_id,
        )

        tri_mode = get_tri_mode_items()

        if tri_mode == "Alphabétique":
            items = sorted(
                items,
                key=lambda item: (
                    item["name"]
                    .strip()
                    .casefold()
                ),
            )
        elif tri_mode == "Catégorie":
            items = sorted(
                items,
                key=lambda item: (
                    (
                        item["category"]
                        or ""
                    ).casefold(),
                    item["name"]
                    .strip()
                    .casefold(),
                ),
            )

        search_query = (
            search_state["value"]
            .strip()
            .casefold()
        )

        if search_query:
            visible_items = [
                item
                for item in items
                if (
                    search_query
                    in item["name"]
                    .strip()
                    .casefold()
                    or search_query
                    in (
                        item["category"]
                        or ""
                    ).casefold()
                )
            ]
        else:
            visible_items = items

        with ui.row().classes(
            "w-full items-center "
            "justify-between gap-2"
        ):
            ui.label(
                (
                    f"{len(visible_items)} "
                    f"sur {len(items)} items"
                )
                if search_query
                else (
                    f"{len(items)} item"
                    if len(items) == 1
                    else f"{len(items)} items"
                )
            ).classes(
                "text-sm text-gray-500"
            )

            if search_query:
                ui.button(
                    "Effacer",
                    icon="close",
                    on_click=lambda: (
                        search_state.update(
                            {"value": ""}
                        ),
                        app.storage.user.pop(
                            search_storage_key,
                            None,
                        ),
                        setattr(
                            search_input,
                            "value",
                            "",
                        ),
                        search_input.update(),
                        render_items.refresh(),
                    ),
                ).props(
                    "flat dense color=primary"
                )

        if not visible_items:
            with ui.card().classes(
                "w-full p-6 "
                "items-center text-center mt-2"
            ):
                ui.icon("search_off").classes(
                    "text-4xl text-gray-400"
                )
                ui.label(
                    "Aucun item trouvé"
                ).classes(
                    "text-lg font-bold"
                )
                ui.label(
                    "Modifiez la recherche "
                    "ou effacez le filtre."
                ).classes(
                    "text-gray-500"
                )
            return

        for item in visible_items:
            def change_needed(
                item_id=item["id"],
            ):
                try:
                    toggle_needed(
                        user_id,
                        item_id,
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

                # Le rechargement met aussi à jour le compteur
                # dans la barre de navigation.
                ui.navigate.to("/?tab=items")

            def remove_item(
                item_id=item["id"],
                item_name=item["name"],
            ):
                try:
                    delete_item(
                        user_id,
                        item_id,
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

                render_items.refresh()

                ui.notify(
                    f"« {item_name} » supprimé.",
                    type="positive",
                )

            with ui.card().classes(
                "w-full p-0 mt-2 overflow-hidden"
            ):
                with ui.row().classes(
                    "w-full items-stretch "
                    "flex-nowrap gap-0"
                ):
                    touch_area = ui.row().classes(
                        "grow min-w-0 items-center "
                        "justify-between gap-3 "
                        "px-4 py-3 cursor-pointer "
                        "hover:bg-blue-50"
                    )

                    touch_area.on(
                        "click",
                        change_needed,
                    )

                    with touch_area:
                        with ui.column().classes(
                            "gap-0 min-w-0 grow"
                        ):
                            ui.label(
                                (
                                    f"{item['name']} "
                                    f"({item['quantity']})"
                                )
                            ).classes(
                                "font-bold leading-snug "
                                "whitespace-normal "
                                "break-words"
                            ).style(
                                "overflow-wrap: anywhere;"
                            )

                            ui.label(
                                item["category"]
                                or "Sans catégorie"
                            ).classes(
                                "text-sm text-gray-500"
                            )

                        ui.icon(
                            (
                                "check_circle"
                                if item["needed"]
                                else "radio_button_unchecked"
                            )
                        ).classes(
                            (
                                "text-2xl text-green-600 "
                                "shrink-0"
                            )
                            if item["needed"]
                            else (
                                "text-2xl text-gray-400 "
                                "shrink-0"
                            )
                        )

                    with ui.row().classes(
                        "items-center gap-0 "
                        "shrink-0 pr-1"
                    ):
                        ui.button(
                            icon="edit",
                            on_click=lambda
                            item_data=item: (
                                open_edit_dialog(
                                    item_data
                                )
                            ),
                        ).props(
                            "flat round color=primary"
                        ).tooltip(
                            "Modifier cet item"
                        )

                        ui.button(
                            icon="delete",
                            on_click=remove_item,
                        ).props(
                            "flat round color=red"
                        ).tooltip(
                            "Supprimer l’item"
                        )

    def search_changed(event):
        search_state["value"] = (
            event.value or ""
        )
        app.storage.user[
            search_storage_key
        ] = search_state["value"]
        render_items.refresh()

    def sort_changed(event):
        set_tri_mode_items(event.value)
        render_items.refresh()

    search_input.on_value_change(
        search_changed
    )
    sort_input.on_value_change(
        sort_changed
    )

    render_items()

    ui.label(
        "Astuce : touchez le nom d’un item "
        "pour l’ajouter ou le retirer des besoins."
    ).classes(
        "text-xs text-gray-500 mt-2"
    )
