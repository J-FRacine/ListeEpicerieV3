from nicegui import app, ui

from auth import get_current_user_id
from db import (
    add_item,
    delete_item,
    get_accessible_families,
    get_categories,
    get_frequent_items,
    get_items,
    get_stores,
    set_item_needed,
    toggle_needed,
    update_item,
)
from state import (
    get_current_family_id,
    get_tri_mode_items,
    set_current_family_id,
    set_tri_mode_items,
)
from utils import ensure_categories_exist, ensure_family_selected


def items_panel():
    user_id = get_current_user_id()
    family_id = get_current_family_id()

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
            set_current_family_id(
                family_by_name[event.value]
            ),
            ui.navigate.to("/?tab=items"),
        ),
    ).classes("w-full")

    if not ensure_categories_exist(user_id, family_id):
        return

    categories = get_categories(user_id, family_id)
    stores = get_stores(user_id, family_id)

    if not stores:
        ui.label(
            "Créez d’abord un magasin dans Catégories et magasins."
        ).classes("text-orange-700")
        return

    category_by_name = {
        row["name"]: row["id"]
        for row in categories
    }
    store_by_name = {
        row["name"]: row["id"]
        for row in stores
    }

    # ---------------------------------------------------------
    # AJOUT
    # ---------------------------------------------------------

    ui.separator()
    ui.label("Ajouter un item").classes("text-xl font-bold")

    with ui.card().classes("w-full p-4"):
        with ui.row().classes(
            "w-full items-end gap-3 flex-wrap"
        ):
            name_input = ui.input(
                label="Nom"
            ).props(
                "autocomplete=off autofocus"
            ).classes("grow min-w-[210px]")

            quantity_input = ui.number(
                label="Quantité",
                value=1,
                min=1,
                step=1,
            ).classes("w-28")

            category_input = ui.select(
                list(category_by_name),
                value=list(category_by_name)[0],
                label="Catégorie",
            ).classes("grow min-w-[170px]")

            store_input = ui.select(
                list(store_by_name),
                value=list(store_by_name)[0],
                label="Magasin",
            ).classes("grow min-w-[170px]")

        note_input = ui.textarea(
            label="Note facultative",
            placeholder=(
                "Ex. Sans sel et sans sucre, idéalement IGA"
            ),
        ).props(
            "autogrow maxlength=500"
        ).classes("w-full")

        needed_input = ui.checkbox(
            "Ajouter directement aux besoins"
        )

        def add_new_item():
            item_name = (
                name_input.value or ""
            ).strip()

            try:
                add_item(
                    user_id,
                    family_id,
                    category_by_name[
                        category_input.value
                    ],
                    item_name,
                    int(quantity_input.value or 1),
                    bool(needed_input.value),
                    note=(
                        note_input.value or ""
                    ).strip(),
                    store_id=store_by_name[
                        store_input.value
                    ],
                )
            except (
                ValueError,
                PermissionError,
                KeyError,
            ) as error:
                ui.notify(
                    str(error),
                    type="warning",
                )
                return

            ui.notify(
                f"« {item_name} » ajouté.",
                type="positive",
            )
            ui.navigate.to("/?tab=items")

        name_input.on(
            "keydown.enter",
            add_new_item,
        )

        ui.button(
            "Ajouter",
            icon="add",
            on_click=add_new_item,
        ).props(
            "color=primary"
        ).classes("w-full mt-2")

    # ---------------------------------------------------------
    # ITEMS FRÉQUENTS
    # ---------------------------------------------------------

    frequent_items = get_frequent_items(
        user_id,
        family_id,
        limit=8,
    )

    if frequent_items:
        ui.label("Souvent ajoutés").classes(
            "text-lg font-bold mt-1"
        )
        ui.label(
            "Touchez un item pour le remettre immédiatement dans les besoins."
        ).classes("text-sm text-gray-500")

        with ui.row().classes(
            "w-full gap-2 flex-wrap"
        ):
            for frequent in frequent_items:

                def add_frequent(item=frequent):
                    try:
                        set_item_needed(
                            user_id,
                            item["id"],
                            True,
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

                    ui.notify(
                        f"« {item['name']} » ajouté aux besoins.",
                        type="positive",
                    )
                    ui.navigate.to("/?tab=items")

                ui.button(
                    frequent["name"],
                    icon="add_shopping_cart",
                    on_click=add_frequent,
                ).props(
                    "outline color=primary no-caps"
                ).tooltip(
                    "Ajouté "
                    f"{frequent['times_needed']} fois "
                    "aux besoins"
                )

    # ---------------------------------------------------------
    # RECHERCHE ET TRI
    # ---------------------------------------------------------

    ui.separator()

    search_key = f"items_search_{family_id}"
    search_state = {
        "value": app.storage.user.get(
            search_key,
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

        sort_input = ui.select(
            [
                "Alphabétique",
                "Ordre d’ajout",
                "Catégorie",
                "Magasin",
            ],
            value=get_tri_mode_items(),
            label="Trier",
        ).props(
            "dense options-dense"
        ).classes("w-44")

    search_input = ui.input(
        label="Rechercher un item",
        value=search_state["value"],
        placeholder=(
            "Nom, note, catégorie ou magasin"
        ),
    ).props(
        "clearable debounce=150 autocomplete=off"
    ).classes("w-full")

    with search_input.add_slot("prepend"):
        ui.icon("search")

    # ---------------------------------------------------------
    # MODIFICATION
    # ---------------------------------------------------------

    def open_edit_dialog(item):
        with ui.dialog() as dialog:
            with ui.card().classes(
                "w-full max-w-lg p-5"
            ):
                ui.label("Modifier l’item").classes(
                    "text-xl font-bold"
                )

                edit_name = ui.input(
                    label="Nom",
                    value=item["name"],
                ).classes("w-full")

                edit_note = ui.textarea(
                    label="Note facultative",
                    value=item.get("note") or "",
                ).props(
                    "autogrow maxlength=500"
                ).classes("w-full")

                edit_quantity = ui.number(
                    label="Quantité",
                    value=item["quantity"],
                    min=1,
                    step=1,
                ).classes("w-full")

                edit_category = ui.select(
                    list(category_by_name),
                    value=item["category"],
                    label="Catégorie",
                ).classes("w-full")

                edit_store = ui.select(
                    list(store_by_name),
                    value=item["store"],
                    label="Magasin",
                ).classes("w-full")

                edit_needed = ui.checkbox(
                    "Présent dans les besoins",
                    value=item["needed"] == 1,
                )

                def save_item():
                    try:
                        update_item(
                            user_id,
                            item["id"],
                            category_by_name[
                                edit_category.value
                            ],
                            (
                                edit_name.value or ""
                            ).strip(),
                            int(
                                edit_quantity.value or 1
                            ),
                            bool(edit_needed.value),
                            note=(
                                edit_note.value or ""
                            ).strip(),
                            store_id=store_by_name[
                                edit_store.value
                            ],
                        )
                    except (
                        ValueError,
                        PermissionError,
                        KeyError,
                    ) as error:
                        ui.notify(
                            str(error),
                            type="warning",
                        )
                        return

                    dialog.close()
                    ui.notify(
                        "Item modifié.",
                        type="positive",
                    )
                    ui.navigate.to("/?tab=items")

                with ui.row().classes(
                    "w-full justify-end gap-2 mt-3"
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
    # LISTE
    # ---------------------------------------------------------

    @ui.refreshable
    def render_items():
        all_items = get_items(
            user_id,
            family_id,
        )
        tri_mode = get_tri_mode_items()

        if tri_mode == "Alphabétique":
            all_items.sort(
                key=lambda item: item["name"]
                .strip()
                .casefold()
            )
        elif tri_mode == "Catégorie":
            all_items.sort(
                key=lambda item: (
                    item["category_order"],
                    item["category"].casefold(),
                    item["name"].casefold(),
                )
            )
        elif tri_mode == "Magasin":
            all_items.sort(
                key=lambda item: (
                    item["store_order"],
                    item["store"].casefold(),
                    item["category_order"],
                    item["name"].casefold(),
                )
            )

        query = search_state["value"].strip().casefold()
        visible = all_items

        if query:
            visible = [
                item
                for item in all_items
                if any(
                    query
                    in str(value or "").casefold()
                    for value in (
                        item["name"],
                        item.get("note"),
                        item["category"],
                        item["store"],
                    )
                )
            ]

        ui.label(
            (
                f"{len(visible)} sur "
                f"{len(all_items)} items"
            )
            if query
            else (
                f"{len(all_items)} item"
                if len(all_items) == 1
                else f"{len(all_items)} items"
            )
        ).classes("text-sm text-gray-500")

        if not visible:
            with ui.card().classes(
                "w-full p-6 items-center text-center"
            ):
                ui.icon("search_off").classes(
                    "text-4xl text-gray-400"
                )
                ui.label("Aucun item trouvé").classes(
                    "text-lg font-bold"
                )
            return

        for item in visible:

            def change_needed(selected=item):
                try:
                    toggle_needed(
                        user_id,
                        selected["id"],
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

                ui.navigate.to("/?tab=items")

            def move_to_trash(selected=item):
                try:
                    delete_item(
                        user_id,
                        selected["id"],
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

                ui.notify(
                    f"« {selected['name']} » déplacé dans la corbeille.",
                    type="positive",
                )
                ui.navigate.to("/?tab=items")

            with ui.card().classes(
                "w-full p-0 mt-2 overflow-hidden"
            ):
                with ui.row().classes(
                    "w-full items-stretch flex-nowrap gap-0"
                ):
                    touch_area = ui.row().classes(
                        "grow min-w-0 items-center "
                        "justify-between gap-3 px-4 py-3 "
                        "cursor-pointer hover:bg-blue-50"
                    )
                    touch_area.on(
                        "click",
                        change_needed,
                    )

                    with touch_area:
                        with ui.column().classes(
                            "gap-0 min-w-0 grow"
                        ):
                            title = item["name"]
                            if item["quantity"] != 1:
                                title += (
                                    f" ({item['quantity']})"
                                )

                            ui.label(title).classes(
                                "font-bold leading-snug "
                                "whitespace-normal break-words"
                            ).style(
                                "overflow-wrap:anywhere;"
                            )

                            ui.label(
                                f"{item['store']} · "
                                f"{item['category']}"
                            ).classes(
                                "text-sm text-primary"
                            )

                            if item.get("note"):
                                ui.label(
                                    item["note"]
                                ).classes(
                                    "text-sm text-gray-500 "
                                    "whitespace-normal"
                                ).style(
                                    "overflow-wrap:anywhere;"
                                )

                        ui.icon(
                            "check_circle"
                            if item["needed"]
                            else "radio_button_unchecked"
                        ).classes(
                            "text-2xl shrink-0 "
                            + (
                                "text-green-600"
                                if item["needed"]
                                else "text-gray-400"
                            )
                        )

                    with ui.row().classes(
                        "items-center gap-0 shrink-0 pr-1"
                    ):
                        ui.button(
                            icon="edit",
                            on_click=lambda selected=item: (
                                open_edit_dialog(selected)
                            ),
                        ).props(
                            "flat round color=primary"
                        ).tooltip("Modifier")

                        ui.button(
                            icon="delete",
                            on_click=move_to_trash,
                        ).props(
                            "flat round color=negative"
                        ).tooltip(
                            "Mettre à la corbeille"
                        )

    def search_changed(event):
        search_state["value"] = event.value or ""
        app.storage.user[
            search_key
        ] = search_state["value"]
        render_items.refresh()

    def sort_changed(event):
        set_tri_mode_items(event.value)
        render_items.refresh()

    search_input.on_value_change(search_changed)
    sort_input.on_value_change(sort_changed)
    render_items()

    ui.label(
        "Astuce : touchez la partie principale d’un item "
        "pour changer son état de besoin."
    ).classes("text-xs text-gray-500 mt-2")
