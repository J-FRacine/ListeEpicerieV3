from collections import defaultdict

from nicegui import ui

from db import get_families, get_items, toggle_needed
from state import get_current_family_id, set_current_family_id
from utils import ensure_family_selected


def needs_panel():
    print("DEBUG needs_panel() → entrée")

    current_family_id = get_current_family_id()
    print(f"DEBUG needs_panel() → current_family_id = {current_family_id}")

    if not ensure_family_selected(current_family_id):
        print("DEBUG needs_panel() → STOP: famille non sélectionnée")
        return

    families = get_families()
    print(f"DEBUG needs_panel() → familles = {families}")

    if not families:
        ui.label(
            "⚠️ Aucune famille disponible."
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
            print(
                "DEBUG needs_panel() → famille changée = "
                f"{family_dict[event.value]}"
            ),
            set_current_family_id(family_dict[event.value]),
            ui.navigate.to("/?tab=besoins"),
        ),
    ).classes("w-full")

    ui.separator()

    ui.label("Besoins").classes("text-xl font-bold")

    # ---------------------------------------------------------
    # RÉCUPÉRATION DES BESOINS
    # ---------------------------------------------------------

    items = get_items(current_family_id)
    needs = [
        item
        for item in items
        if item["needed"] == 1
    ]

    print(f"DEBUG needs_panel() → besoins = {needs}")

    if not needs:
        ui.label(
            "Aucun item n’est actuellement marqué comme besoin."
        ).classes("text-gray-500 mt-3")
        return

    # ---------------------------------------------------------
    # REGROUPEMENT PAR CATÉGORIE
    # ---------------------------------------------------------

    needs_by_category = defaultdict(list)

    for item in needs:
        category_name = (
            item["category"].strip()
            if item.get("category")
            else "Sans catégorie"
        )
        needs_by_category[category_name].append(item)

    # Les catégories sont affichées en ordre alphabétique.
    sorted_categories = sorted(
        needs_by_category.keys(),
        key=lambda category: category.casefold(),
    )

    # ---------------------------------------------------------
    # AFFICHAGE
    # Les items sont triés alphabétiquement à l'intérieur
    # de chacune des catégories.
    # ---------------------------------------------------------

    for category_name in sorted_categories:
        category_items = sorted(
            needs_by_category[category_name],
            key=lambda item: item["name"].strip().casefold(),
        )

        with ui.column().classes("w-full gap-1 mt-4"):
            ui.label(category_name).classes(
                "text-lg font-bold border-b border-gray-300 "
                "pb-1 w-full"
            )

            for item in category_items:
                with ui.row().classes(
                    "w-full items-center justify-between "
                    "bg-gray-100 rounded-lg px-3 py-2 mt-1 gap-2"
                ):
                    with ui.row().classes("items-center gap-2"):
                        quantity = item.get("quantity", 1)

                        if quantity and quantity != 1:
                            item_text = f"{item['name']} ({quantity})"
                        else:
                            item_text = item["name"]

                        ui.label(item_text).classes("font-bold")

                    ui.button(
                        icon="check",
                        on_click=lambda item_id=item["id"]: (
                            print(
                                "DEBUG needs_panel() → "
                                f"retrait du besoin {item_id}"
                            ),
                            toggle_needed(item_id),
                            ui.navigate.to("/?tab=besoins"),
                        ),
                    ).props(
                        "flat round color=green"
                    ).tooltip(
                        "Retirer de la liste des besoins"
                    )
