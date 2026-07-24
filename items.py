from nicegui import ui

from db import (
    add_item,
    delete_item,
    get_categories,
    get_families,
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
from utils import ensure_categories_exist, ensure_family_selected


def items_panel():
    current_family_id = get_current_family_id()

    if not ensure_family_selected(current_family_id):
        return

    families = get_families()

    if not families:
        ui.label("Aucune famille disponible.").classes("text-orange-700")
        return

    family_dict = {
        family["name"]: family["id"]
        for family in families
    }

    current_family_name = next(
        (
            name
            for name, family_id in family_dict.items()
            if family_id == current_family_id
        ),
        list(family_dict.keys())[0],
    )

    # ---------------------------------------------------------
    # FAMILLE ACTIVE
    # ---------------------------------------------------------

    ui.select(
        list(family_dict.keys()),
        value=current_family_name,
        label="Famille",
        on_change=lambda event: (
            set_current_family_id(family_dict[event.value]),
            ui.navigate.to("/?tab=items"),
        ),
    ).classes("w-full")

    if not ensure_categories_exist():
        return

    categories = get_categories()

    category_dict = {
        category["name"]: category["id"]
        for category in categories
    }
    category_names = list(category_dict.keys())

    # ---------------------------------------------------------
    # AJOUTER UN ITEM
    # ---------------------------------------------------------

    ui.separator()
    ui.label("Ajouter un item").classes("text-xl font-bold")

    with ui.row().classes("w-full items-end gap-3 flex-wrap"):
        name_input = ui.input(
            label="Nom",
        ).classes("grow min-w-[210px]")

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
        ).classes("grow min-w-[170px]")

        def add_new_item():
            item_name = (name_input.value or "").strip()

            if not item_name:
                ui.notify(
                    "Inscris le nom de l’item.",
                    type="warning",
                )
                return

            quantity = int(quantity_input.value or 1)

            if quantity < 1:
                ui.notify(
                    "La quantité doit être d’au moins 1.",
                    type="warning",
                )
                return

            add_item(
                current_family_id,
                category_dict[category_input.value],
                item_name,
                quantity,
                0,
            )

            ui.navigate.to("/?tab=items")

        ui.button(
            "Ajouter",
            on_click=add_new_item,
        ).props("flat color=green").classes("mb-1")

    # ---------------------------------------------------------
    # LISTE DES ITEMS ET TRI COMPACT
    # ---------------------------------------------------------

    ui.separator()

    tri_mode = get_tri_mode_items()

    with ui.row().classes(
        "w-full items-center justify-between gap-3 flex-wrap"
    ):
        ui.label("Tous les items").classes("text-xl font-bold")

        with ui.row().classes("items-center gap-1"):
            ui.icon("sort").classes("text-gray-500")

            ui.select(
                [
                    "Alphabétique",
                    "Ordre d’ajout",
                    "Catégorie",
                ],
                value=tri_mode,
                on_change=lambda event: (
                    set_tri_mode_items(event.value),
                    ui.navigate.to("/?tab=items"),
                ),
            ).props(
                "dense borderless options-dense"
            ).classes("w-40 text-sm")

    items = get_items(current_family_id)

    if tri_mode == "Alphabétique":
        items = sorted(
            items,
            key=lambda item: item["name"].strip().casefold(),
        )
    elif tri_mode == "Catégorie":
        items = sorted(
            items,
            key=lambda item: (
                (item["category"] or "").casefold(),
                item["name"].strip().casefold(),
            ),
        )

    if not items:
        ui.label(
            "Aucun item dans cette famille."
        ).classes("text-gray-500 mt-3")
        return

    # ---------------------------------------------------------
    # FENÊTRE DE MODIFICATION
    # ---------------------------------------------------------

    def open_edit_dialog(item):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-md p-5"):
                ui.label("Modifier l’item").classes(
                    "text-xl font-bold"
                )

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
                    "Présent dans la liste des besoins",
                    value=item["needed"] == 1,
                )

                def save_item():
                    item_name = (edit_name.value or "").strip()

                    if not item_name:
                        ui.notify(
                            "Le nom de l’item est obligatoire.",
                            type="warning",
                        )
                        return

                    quantity = int(edit_quantity.value or 1)

                    if quantity < 1:
                        ui.notify(
                            "La quantité doit être d’au moins 1.",
                            type="warning",
                        )
                        return

                    if not edit_category.value:
                        ui.notify(
                            "Choisis une catégorie.",
                            type="warning",
                        )
                        return

                    update_item(
                        item["id"],
                        category_dict[edit_category.value],
                        item_name,
                        quantity,
                        1 if edit_needed.value else 0,
                    )

                    dialog.close()
                    ui.navigate.to("/?tab=items")

                with ui.row().classes(
                    "w-full justify-end gap-2 mt-4"
                ):
                    ui.button(
                        "Annuler",
                        on_click=dialog.close,
                    ).props("flat")

                    ui.button(
                        "Enregistrer",
                        on_click=save_item,
                    ).props("color=primary")

        dialog.open()

    # ---------------------------------------------------------
    # AFFICHAGE DES ITEMS
    # ---------------------------------------------------------

    for item in items:
        with ui.row().classes(
            "w-full items-center justify-between "
            "bg-gray-100 rounded-lg px-3 py-2 mt-2 gap-2 "
            "flex-wrap"
        ):
            with ui.column().classes("gap-0 grow min-w-[170px]"):
                ui.label(
                    f"{item['name']} ({item['quantity']})"
                ).classes("font-bold")

                ui.label(
                    item["category"] or "Sans catégorie"
                ).classes("text-sm text-gray-500")

            with ui.row().classes(
                "items-center gap-1 flex-wrap justify-end"
            ):
                ui.button(
                    icon=(
                        "check_circle"
                        if item["needed"]
                        else "cancel"
                    ),
                    on_click=lambda item_id=item["id"]: (
                        toggle_needed(item_id),
                        ui.navigate.to("/?tab=items"),
                    ),
                ).props(
                    "flat round color=green"
                    if item["needed"]
                    else "flat round color=red"
                ).tooltip(
                    "Retirer des besoins"
                    if item["needed"]
                    else "Ajouter aux besoins"
                )

                ui.button(
                    icon="edit",
                    on_click=lambda item_data=item: (
                        open_edit_dialog(item_data)
                    ),
                ).props(
                    "flat round color=primary"
                ).tooltip("Modifier cet item")

                ui.button(
                    icon="delete",
                    on_click=lambda item_id=item["id"]: (
                        delete_item(item_id),
                        ui.navigate.to("/?tab=items"),
                    ),
                ).props(
                    "flat round color=red"
                ).tooltip("Supprimer l’item")
