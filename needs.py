from collections import defaultdict

from nicegui import app, ui

from auth import get_current_user_id
from db import (
    get_accessible_families,
    get_items,
    toggle_needed,
)
from state import (
    get_current_family_id,
    set_current_family_id,
)
from utils import ensure_family_selected


def needs_panel():
    user_id = get_current_user_id()
    current_family_id = get_current_family_id()

    if (
        user_id is None
        or not ensure_family_selected(current_family_id)
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
            set_current_family_id(
                family_dict[event.value]
            ),
            ui.navigate.to("/?tab=besoins"),
        ),
    ).classes("w-full")

    ui.separator()

    # ---------------------------------------------------------
    # RÉCUPÉRATION ET REGROUPEMENT DES BESOINS
    # ---------------------------------------------------------

    items = get_items(
        user_id,
        current_family_id,
    )

    needs = [
        item
        for item in items
        if item["needed"] == 1
    ]

    if not needs:
        ui.label("Besoins").classes(
            "text-xl font-bold"
        )
        ui.label(
            "Aucun item n’est actuellement "
            "marqué comme besoin."
        ).classes("text-gray-500 mt-3")
        return

    needs_by_category = defaultdict(list)

    for item in needs:
        category_name = (
            item["category"].strip()
            if item.get("category")
            else "Sans catégorie"
        )
        needs_by_category[category_name].append(item)

    category_names = sorted(
        needs_by_category.keys(),
        key=lambda category: category.casefold(),
    )

    # L’état ouvert/fermé est conservé séparément pour chaque
    # utilisateur et pour chaque famille.
    storage_key = (
        f"needs_open_categories_{current_family_id}"
    )

    stored_open_categories = app.storage.user.get(
        storage_key
    )

    if stored_open_categories is None:
        open_categories = set(category_names)
    else:
        open_categories = {
            category_name
            for category_name in stored_open_categories
            if category_name in category_names
        }

    def save_category_state(
        category_name,
        is_open,
    ):
        stored_categories = app.storage.user.get(
            storage_key
        )

        if stored_categories is None:
            current_open_categories = set(
                category_names
            )
        else:
            current_open_categories = set(
                stored_categories
            )

        if is_open:
            current_open_categories.add(
                category_name
            )
        else:
            current_open_categories.discard(
                category_name
            )

        app.storage.user[storage_key] = sorted(
            current_open_categories,
            key=lambda name: name.casefold(),
        )

    def open_all_categories():
        app.storage.user[storage_key] = list(
            category_names
        )
        ui.navigate.to("/?tab=besoins")

    def close_all_categories():
        app.storage.user[storage_key] = []
        ui.navigate.to("/?tab=besoins")

    # ---------------------------------------------------------
    # EN-TÊTE ET ACTIONS
    # ---------------------------------------------------------

    total_needs = len(needs)
    open_count = len(open_categories)

    with ui.row().classes(
        "w-full items-center justify-between "
        "gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Besoins").classes(
                "text-xl font-bold"
            )
            ui.label(
                f"{total_needs} item"
                if total_needs == 1
                else f"{total_needs} items"
            ).classes("text-sm text-gray-500")

        with ui.row().classes(
            "items-center gap-1 flex-wrap"
        ):
            ui.button(
                icon="unfold_more",
                on_click=open_all_categories,
            ).props(
                "flat round color=primary"
            ).tooltip("Ouvrir toutes les catégories")

            ui.button(
                icon="unfold_less",
                on_click=close_all_categories,
            ).props(
                "flat round color=primary"
            ).tooltip("Fermer toutes les catégories")

    ui.label(
        f"{open_count} catégorie"
        if open_count == 1
        else f"{open_count} catégories ouvertes"
    ).classes("text-xs text-gray-500")

    # ---------------------------------------------------------
    # CATÉGORIES REPLIABLES
    # ---------------------------------------------------------

    for category_name in category_names:
        category_items = sorted(
            needs_by_category[category_name],
            key=lambda item: (
                item["name"].strip().casefold()
            ),
        )

        item_count = len(category_items)

        def category_state_changed(
            event,
            selected_category=category_name,
        ):
            save_category_state(
                selected_category,
                bool(event.value),
            )

        with ui.expansion(
            text=category_name,
            caption=(
                f"{item_count} item"
                if item_count == 1
                else f"{item_count} items"
            ),
            icon="category",
            value=category_name in open_categories,
            on_value_change=category_state_changed,
        ).props(
            "expand-separator"
        ).classes(
            "w-full bg-white rounded-xl "
            "shadow-sm border border-gray-200 "
            "overflow-hidden mt-2"
        ):
            with ui.column().classes(
                "w-full gap-1 px-1 pb-2"
            ):
                for item in category_items:
                    with ui.row().classes(
                        "w-full items-center "
                        "justify-between "
                        "bg-gray-100 rounded-lg "
                        "px-3 py-2 gap-2"
                    ):
                        quantity = item.get(
                            "quantity",
                            1,
                        )

                        item_text = (
                            f"{item['name']} "
                            f"({quantity})"
                            if quantity
                            and quantity != 1
                            else item["name"]
                        )

                        ui.label(item_text).classes(
                            "font-bold"
                        )

                        def remove_need(
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

                            ui.navigate.to(
                                "/?tab=besoins"
                            )

                        ui.button(
                            icon="check",
                            on_click=remove_need,
                        ).props(
                            "flat round color=green"
                        ).tooltip(
                            "Retirer de la liste "
                            "des besoins"
                        )
