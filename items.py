from nicegui import ui

from db import (
    get_items,
    add_item,
    delete_item,
    toggle_needed,
    get_categories,
    get_families,
)

from state import current_family_id, tri_mode_items
from utils import ensure_family_selected, ensure_categories_exist


# ---------------------------------------------------------
#  PANNEAU : AJOUT ITEM
# ---------------------------------------------------------

def add_item_panel():
    print("DEBUG add_item_panel() → entrée")
    print(f"DEBUG add_item_panel() → current_family_id = {current_family_id}")

    ui.label("Ajouter un item").classes("text-xl font-bold")

    if not ensure_family_selected(current_family_id):
        print("DEBUG add_item_panel() → STOP: famille non sélectionnée")
        return

    if not ensure_categories_exist():
        print("DEBUG add_item_panel() → STOP: aucune catégorie")
        return

    categories = get_categories()
    print(f"DEBUG add_item_panel() → catégories = {categories}")

    cat_dict = {c['name']: c['id'] for c in categories}
    cat_names = list(cat_dict.keys())

    item_name = ui.input("Nom de l’item").classes("w-full")
    item_cat = ui.select(cat_names, value=cat_names[0], label="Catégorie").classes("w-full")
    item_qty = ui.number("Quantité", value=1).classes("w-full")
    item_needed = ui.checkbox("J’en ai besoin")

    ui.button(
        "Ajouter",
        on_click=lambda: (
            print("DEBUG add_item_panel() → ajout item"),
            add_item(
                current_family_id,
                cat_dict[item_cat.value],
                item_name.value,
                int(item_qty.value),
                1 if item_needed.value else 0
            ),
            ui.navigate.to('/?tab=items')
        )
    ).classes("w-full mt-2")


# ---------------------------------------------------------
#  PANNEAU : ITEMS
# ---------------------------------------------------------

def items_panel():
    print("DEBUG items_panel() → entrée")
    print(f"DEBUG items_panel() → current_family_id = {current_family_id}")

    if not ensure_family_selected(current_family_id):
        print("DEBUG items_panel() → STOP: famille non sélectionnée")
        return

    families = get_families()
    print(f"DEBUG items_panel() → familles = {families}")

    family_dict = {f['name']: f['id'] for f in families}

    ui.select(
        list(family_dict.keys()),
        value=[name for name, fid in family_dict.items() if fid == current_family_id][0],
        label="Famille",
        on_change=lambda e: (
            print(f"DEBUG items_panel() → famille changée = {family_dict[e.value]}"),
            globals().__setitem__('current_family_id', family_dict[e.value]),
            ui.navigate.to('/?tab=items')
        )
    ).classes("w-full")

    ui.separator()

    ui.label("Tous les items").classes("text-xl font-bold")

    ui.select(
        ["Alphabétique", "Ordre d’ajout", "Catégorie", "Besoin"],
        value=tri_mode_items,
        label="Trier par",
        on_change=lambda e: (
            print(f"DEBUG items_panel() → tri changé = {e.value}"),
            globals().__setitem__('tri_mode_items', e.value),
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

    if tri_mode_items == "Alphabétique":
        items = sorted(items, key=lambda x: x['name'].strip().lower())
    elif tri_mode_items == "Catégorie":
        items = sorted(items, key=lambda x: (x['category'] or '').lower())
    elif tri_mode_items == "Besoin":
        items = sorted(items, key=lambda x: x['needed'], reverse=True)

    for it in items:
        with ui.row().classes("items-center justify-between bg-gray-100 rounded-lg px-3 py-2 mt-2 gap-2"):

            with ui.row().classes("items-center gap-2"):
                ui.label(f"{it['name']} ({it['quantity']})").classes("font-bold")
                ui.button(
                    "✔️" if it['needed'] else "❌",
                    on_click=lambda iid=it['id']: (
                        print(f"DEBUG items_panel() → toggle besoin item {iid}"),
                        toggle_needed(iid),
                        ui.navigate.to('/?tab=items')
                    )
                ).props("flat color=white")

            with ui.row().classes("items-center gap-2"):
                ui.select(
                    cat_names,
                    value=it['category'],
                    on_change=lambda e, iid=it['id']: (
                        print(f"DEBUG items_panel() → changement catégorie item {iid} → {e.value}"),
                        add_item(current_family_id, cat_dict[e.value], it['name'], it['quantity'], it['needed']),
                        delete_item(iid),
                        ui.navigate.to('/?tab=items')
                    )
                ).classes("w-32")

                ui.button(
                    "🗑️",
                    on_click=lambda iid=it['id']: (
                        print(f"DEBUG items_panel() → suppression item {iid}"),
                        delete_item(iid),
                        ui.navigate.to('/?tab=items')
                    )
                ).props("flat color=red")
