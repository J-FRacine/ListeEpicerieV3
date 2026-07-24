from nicegui import ui

from db import (
    add_item,
    delete_item,
    get_categories,
    get_families,
    get_items,
    toggle_needed,
)
from state import (
    get_current_family_id,
    get_tri_mode_items,
    set_current_family_id,
    set_tri_mode_items,
)
from utils import ensure_categories_exist, ensure_family_selected


def items_panel():
    print("DEBUG items_panel() → entrée")

    current_family_id = get_current_family_id()
    print(f"DEBUG items_panel() → current_family_id = {current_family_id}")

    if not ensure_family_selected(current_family_id):
        print("DEBUG items_panel() → STOP: famille non sélectionnée")
        return

    families = get_families()
    print(f"DEBUG items_panel() → familles = {families}")

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
            print(
                "DEBUG items_panel() → famille changée = "
                f"{family_dict[event.value]}"
            ),
            set_current_family_id(family_dict[event.value]),
            ui.navigate.to("/?tab=items"),
        ),
    ).classes("w-full")

    if not ensure_categories_exist():
        print("DEBUG items_panel() → STOP: aucune catégorie")
        return

    categories = get_categories()
    print(f"DEBUG items_panel() → catégories = {categories}")

    category_dict = {
        category["name"]: category["id"]
        for category in categories
    }
    category_names = list(category_dict.keys())

    # ---------------------------------------------------------
    # AJOUTER UN ITEM
    # Placé immédiatement sous le sélecteur de famille
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

            if not category_input.value:
                ui.notify(
                    "Choisis une catégorie.",
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

            print(
                "DEBUG items_panel() → ajout item "
                f"{item_name}"
            )

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
    # LISTE DES ITEMS
    # ---------------------------------------------------------

    ui.separator()

    tri_mode = get_tri_mode_items()

    with ui.row().classes(
        "w-full items-center justify-between gap-3"
    ):
        ui.label("Tous les items").classes("text-xl font-bold")

        with ui.row().classes("items-center gap-1"):
            ui.icon("sort").classes("text-gray-500 text-lg")

            ui.select(
                [
                    "Alphabétique",
                    "Ordre d’ajout",
                    "Catégorie",
                ],
                value=tri_mode,
                on_change=lambda event: (
                    print(
                        "DEBUG items_panel() → tri changé = "
                        f"{event.value}"
                    ),
                    set_tri_mode_items(event.value),
                    ui.navigate.to("/?tab=items"),
                ),
            ).props(
                "dense borderless options-dense"
            ).classes("w-40 text-sm")

    items = get_items(current_family_id)
    print(f"DEBUG items_panel() → items = {items}")

    if tri_mode == "Alphabétique":
        items = sorted(
            items,
            key=lambda item: item["name"].strip().lower(),
        )
    elif tri_mode == "Catégorie":
        items = sorted(
            items,
            key=lambda item: (item["category"] or "").lower(),
        )

    if not items:
        ui.label(
            "Aucun item dans cette famille."
        ).classes("text-gray-500 mt-3")
        return

    for item in items:
        with ui.row().classes(
            "w-full items-center justify-between "
            "bg-gray-100 rounded-lg px-3 py-2 mt-2 gap-2"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.label(
                    f"{item['name']} ({item['quantity']})"
                ).classes("font-bold")

                ui.button(
                    "✔️" if item["needed"] else "❌",
                    on_click=lambda item_id=item["id"]: (
                        print(
                            "DEBUG items_panel() → "
                            f"toggle item {item_id}"
                        ),
                        toggle_needed(item_id),
                        ui.navigate.to("/?tab=items"),
                    ),
                ).props("flat color=white")

            with ui.row().classes("items-center gap-2"):
                ui.select(
                    category_names,
                    value=item["category"],
                    on_change=lambda event, item_id=item["id"]: (
                        print(
                            "DEBUG items_panel() → "
                            f"changement catégorie item "
                            f"{item_id} → {event.value}"
                        ),
                        ui.navigate.to("/?tab=items"),
                    ),
                ).classes("w-32")

                ui.button(
                    "🗑️",
                    on_click=lambda item_id=item["id"]: (
                        print(
                            "DEBUG items_panel() → "
                            f"suppression item {item_id}"
                        ),
                        delete_item(item_id),
                        ui.navigate.to("/?tab=items"),
                    ),
                ).props("flat color=red")
