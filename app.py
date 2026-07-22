import os
from nicegui import ui
from db import (
    init_db,
    get_families,
    create_family,
    get_categories,
    create_category,
    delete_category,
    get_items,
    add_item,
    delete_item,
    toggle_needed,
)

# ---------------------------------------------------------
#  INITIALISATION BD POSTGRES
# ---------------------------------------------------------
init_db()

# ---------------------------------------------------------
#  ÉTAT GLOBAL
# ---------------------------------------------------------
current_family_id = None
current_tab = 'items'
tri_mode_items = 'Ordre d’ajout'
tri_mode_needs = 'Ordre d’ajout'


# ---------------------------------------------------------
#  UTILITAIRES
# ---------------------------------------------------------

def ensure_default_family():
    """Crée une famille par défaut si la BD est vide."""
    global current_family_id
    families = get_families()
    if not families:
        create_family("Famille 1")
        families = get_families()
    if current_family_id is None:
        current_family_id = families[0]['id']


# ---------------------------------------------------------
#  PANNEAU : FAMILLES
# ---------------------------------------------------------

def families_panel():
    ui.label("Gestion des familles").classes("text-xl font-bold")

    families = get_families()
    family_dict = {f['name']: f['id'] for f in families}

    ui.label("Famille active")
    ui.select(
        list(family_dict.keys()),
        value=[name for name, fid in family_dict.items() if fid == current_family_id][0],
        on_change=lambda e: (
            globals().__setitem__('current_family_id', family_dict[e.value]),
            ui.open('/')
        )
    ).classes("w-full")

    ui.separator()

    new_name = ui.input("Nouvelle famille").classes("w-full")
    ui.button("Créer", on_click=lambda: (
        create_family(new_name.value),
        ui.open('/')
    )).classes("w-full mt-2")


# ---------------------------------------------------------
#  PANNEAU : CATÉGORIES
# ---------------------------------------------------------

def categories_panel():
    ui.label("Gestion des catégories").classes("text-xl font-bold")

    new_cat = ui.input("Nouvelle catégorie").classes("w-full")
    ui.button("Ajouter", on_click=lambda: (
        create_category(new_cat.value),
        ui.open('/')
    )).classes("w-full mt-2")

    ui.separator()

    categories = get_categories()
    for cat in categories:
        with ui.row().classes("items-center justify-between mt-1"):
            ui.label(cat['name'])
            ui.button("🗑️", on_click=lambda cid=cat['id']: (
                delete_category(cid),
                ui.open('/')
            )).props("flat color=red")


# ---------------------------------------------------------
#  PANNEAU : AJOUT ITEM
# ---------------------------------------------------------

def add_item_panel():
    ui.label("Ajouter un item").classes("text-xl font-bold")

    categories = get_categories()
    cat_dict = {c['name']: c['id'] for c in categories}
    cat_names = list(cat_dict.keys())

    default_cat = cat_names[0] if cat_names else None

    item_name = ui.input("Nom de l’item").classes("w-full")
    item_cat = ui.select(cat_names, value=default_cat, label="Catégorie").classes("w-full")
    item_qty = ui.number("Quantité", value=1).classes("w-full")
    item_needed = ui.checkbox("J’en ai besoin")

    ui.button("Ajouter", on_click=lambda: (
        add_item(current_family_id, cat_dict[item_cat.value], item_name.value, int(item_qty.value)),
        ui.open('/')
    )).classes("w-full mt-2")


# ---------------------------------------------------------
#  PANNEAU : ITEMS
# ---------------------------------------------------------

def items_panel():
    global tri_mode_items

    families = get_families()
    family_dict = {f['name']: f['id'] for f in families}

    ui.select(
        list(family_dict.keys()),
        value=[name for name, fid in family_dict.items() if fid == current_family_id][0],
        label="Famille",
        on_change=lambda e: (
            globals().__setitem__('current_family_id', family_dict[e.value]),
            ui.open('/')
        )
    ).classes("w-full")

    ui.separator()

    ui.label("Tous les items").classes("text-xl font-bold")

    ui.select(
        ["Alphabétique", "Ordre d’ajout", "Catégorie", "Besoin"],
        value=tri_mode_items,
        label="Trier par",
        on_change=lambda e: (
            globals().__setitem__('tri_mode_items', e.value),
            ui.open('/')
        )
    ).classes("w-full")

    categories = get_categories()
    cat_dict = {c['name']: c['id'] for c in categories}
    cat_names = list(cat_dict.keys())

    items = get_items(current_family_id)

    # Tri
    if tri_mode_items == "Alphabétique":
        items = sorted(items, key=lambda x: x['name'].lower())
    elif tri_mode_items == "Catégorie":
        items = sorted(items, key=lambda x: (x['category'] or '').lower())
    elif tri_mode_items == "Besoin":
        items = sorted(items, key=lambda x: x['needed'], reverse=True)

    for it in items:
        with ui.row().classes("items-center justify-between bg-gray-100 rounded-lg px-3 py-2 mt-2 gap-2"):

            with ui.row().classes("items-center gap-2"):
                ui.label(f"{it['name']} ({it['quantity']})").classes("font-bold")
                ui.button("✔️" if it['needed'] else "❌",
                          on_click=lambda iid=it['id']: (
                              toggle_needed(iid),
                              ui.open('/')
                          )).props("flat color=white")

            with ui.row().classes("items-center gap-2"):
                ui.select(
                    cat_names,
                    value=it['category'],
                    on_change=lambda e, iid=it['id']: (
                        # update category
                        add_item(current_family_id, cat_dict[e.value], it['name'], it['quantity']),
                        delete_item(iid),
                        ui.open('/')
                    )
                ).classes("w-32")

                ui.button("🗑️",
                          on_click=lambda iid=it['id']: (
                              delete_item(iid),
                              ui.open('/')
                          )).props("flat color=red")


# ---------------------------------------------------------
#  PANNEAU : BESOINS
# ---------------------------------------------------------

def needs_panel():
    global tri_mode_needs

    families = get_families()
    family_dict = {f['name']: f['id'] for f in families}

    ui.select(
        list(family_dict.keys()),
        value=[name for name, fid in family_dict.items() if fid == current_family_id][0],
        label="Famille",
        on_change=lambda e: (
            globals().__setitem__('current_family_id', family_dict[e.value]),
            ui.open('/')
        )
    ).classes("w-full")

    ui.separator()

    ui.label("Besoins").classes("text-xl font-bold")

    ui.select(
        ["Alphabétique", "Ordre d’ajout"],
        value=tri_mode_needs,
        label="Trier par",
        on_change=lambda e: (
            globals().__setitem__('tri_mode_needs', e.value),
            ui.open('/')
        )
    ).classes("w-full")

    items = get_items(current_family_id)
    needed_items = [it for it in items if it['needed'] == 1]

    grouped = {}
    for it in needed_items:
        grouped.setdefault(it['category'] or "Sans catégorie", []).append(it)

    if not grouped:
        ui.label("Aucun item marqué comme besoin.")
        return

    for cat, its in grouped.items():
        ui.label(f"📂 {cat}").classes("text-lg font-bold mt-3")

        if tri_mode_needs == "Alphabétique":
            its = sorted(its, key=lambda x: x['name'])

        for it in its:
            with ui.row().classes("items-center gap-3 mt-1"):
                ui.button("❌",
                          on_click=lambda iid=it['id']: (
                              toggle_needed(iid),
                              ui.open('/')
                          )).props("flat color=red")
                ui.label(it['name']).classes("font-bold")


# ---------------------------------------------------------
#  NAVIGATION BAS
# ---------------------------------------------------------

def bottom_nav():
    global current_tab

    with ui.row().classes(
        "fixed bottom-0 left-0 w-full justify-around bg-gray-800/90 text-white py-2 border-t border-gray-700 backdrop-blur"
    ):
        ui.button("📝 Items", on_click=lambda: (
            globals().__setitem__('current_tab', 'items'),
            ui.open('/')
        )).props("flat color=white")

        ui.button("❤️ Besoins", on_click=lambda: (
            globals().__setitem__('current_tab', 'besoins'),
            ui.open('/')
        )).props("flat color=white")

        ui.button("📂 Catégories", on_click=lambda: (
            globals().__setitem__('current_tab', 'categories'),
            ui.open('/')
        )).props("flat color=white")

        ui.button("👨‍👩‍👧 Familles", on_click=lambda: (
            globals().__setitem__('current_tab', 'families'),
            ui.open('/')
        )).props("flat color=white")


# ---------------------------------------------------------
#  PAGE PRINCIPALE
# ---------------------------------------------------------

@ui.page('/')
def main_page():

    ensure_default_family()

    with ui.row().classes("w-full justify-center mt-4"):
        with ui.column().classes(
            "w-full max-w-md bg-white text-black p-4 rounded-lg shadow-md "
            "h-[calc(100vh-80px)] overflow-y-auto pb-24"
        ):
            if current_tab == 'items':
                add_item_panel()
                ui.separator()
                items_panel()
            elif current_tab == 'besoins':
                needs_panel()
            elif current_tab == 'categories':
                categories_panel()
            elif current_tab == 'families':
                families_panel()

    bottom_nav()


# ---------------------------------------------------------
#  LANCEMENT CANNER
# ---------------------------------------------------------

ui.run(
    title="Liste d’achats",
    reload=False,
    host="0.0.0.0",
    port=int(os.getenv("PORT", 8080)),
)
