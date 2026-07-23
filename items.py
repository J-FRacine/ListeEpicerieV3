from nicegui import ui

from db import (
    get_items,
    add_item,
    delete_item,
    toggle_needed,
    get_categories,
    get_families,
)

from state import (
    get_current_family_id,
    set_current_family_id,
    get_tri_mode_items,
    set_tri_mode_items,
)

from utils import ensure_family_selected, ensure_categories_exist


def items_panel():
    print("DEBUG items_panel() → entrée")

    current_family_id = get_current_family_id()
    print(f"DEBUG items_panel() → current_family_id = {current_family_id}")

    if not ensure_family_selected(current_family_id):
        print("DEBUG items_panel() → STOP: famille non sélectionnée")
        return

    families = get_families()
    print(f"DEBUG items_panel() → familles = {families}")

    family_dict = {f['name']: f['id'] for f in families}

    # Sélecteur de famille
    ui.select(
        list(family_dict.keys()),
        value=[name for name, fid in family_dict.items() if fid == current_family_id][0],
        label="Famille",
        on_change=lambda e: (
            print(f"DEBUG items_panel() → famille changée = {family_dict[e.value]}"),
            set_current_family_id(family_dict[e.value]),
            ui.navigate.to('/?tab=items')
        )
    ).classes("w-full")

    ui.separator()

    ui.label("Tous les items").classes("text-xl font-bold")

    tri_mode = get_tri_mode_items()

    ui.select(
        ["Alphabétique", "Ordre d’ajout", "Catégorie"],
        value=tri_mode,
        label="Trier par",
        on_change=lambda e: (
            print(f"DEBUG items_panel() → tri changé = {e.value}"),
            set_tri_mode_items(e.value),
            ui.navigate.to('/?tab=items')
        )
    ).classes("w-full")

    if not ensure_categories_exist():
        print("DEBUG items_panel() → STOP: aucune catégorie")
        return

    categories = get_categories()
    print(f"DEBUG items_panel() → catégories = {categories}")

    cat_dict = {c['name']: c['id'] for c in categories}
    cat_names = list(cat_dict.keys())

    items = get_items(current_family_id)
    print(f"DEBUG items_panel() → items = {items}")

    # Tri
    if tri_mode == "Alphabétique":
        items = sorted(items, key=lambda x: x['name'].strip().lower())
    elif tri_mode == "Catégorie":
        items = sorted(items, key=lambda x: (x['category'] or '').lower())

    # Affichage des items
    for item in items:
        with ui.row().classes("items-center justify-between bg-gray-100 rounded-lg px-3 py-2 mt-2 gap-2"):

            with ui.row().classes("items-center gap-2"):
                ui.label(f"{item['name']} ({item['quantity']})").classes("font-bold")

                ui.button(
                    "✔️" if item['needed'] else "❌",
                    on_click=lambda iid=item['id']: (
                        print(f"DEBUG items_panel() → toggle item {iid}"),
                        toggle_needed(iid),
                        ui.navigate.to('/?tab=items')
                    )
                ).props("flat color=white")

            with ui.row().classes("items-center gap-2"):
                ui.select(
                    cat_names,
                    value=item['category'],
                    on_change=lambda e, iid=item['id']: (
                        print(f"DEBUG items_panel() → changement catégorie item {iid} → {e.value}"),
                        # Ici tu peux ajouter une fonction pour changer la catégorie si tu veux
                        ui.navigate.to('/?tab=items')
                    )
                ).classes("w-32")

                ui.button(
                    "🗑️",
                    on_click=lambda iid=item['id']: (
                        print(f"DEBUG items_panel() → suppression item {iid}"),
                        delete_item(iid),
                        ui.navigate.to('/?tab=items')
                    )
                ).props("flat color=red")

    ui.separator()

    # Ajout d'un nouvel item
    ui.label("Ajouter un item").classes("text-lg font-bold")

    with ui.row().classes("items-center gap-2 mt-2"):
        name_input = ui.input(label="Nom")
        quantity_input = ui.number(label="Quantité", value=1)
        category_input = ui.select(cat_names, label="Catégorie")

        ui.button(
            "Ajouter",
            on_click=lambda: (
                print(f"DEBUG items_panel() → ajout item {name_input.value}"),
                add_item(
                    current_family_id,
                    cat_dict[category_input.value],
                    name_input.value,
                    quantity_input.value,
                    0  # needed = 0 par défaut
                ),
                ui.navigate.to('/?tab=items')
            )
        ).props("flat color=green")
