from nicegui import ui

from db import (
    get_needs,
    add_need,
    delete_need,
    toggle_need_done,
    get_categories,
    get_families,
)

from state import (
    get_current_family_id,
    set_current_family_id,
    get_tri_mode_needs,
    set_tri_mode_needs,
)

from utils import ensure_family_selected, ensure_categories_exist


def needs_panel():
    print("DEBUG needs_panel() → entrée")

    current_family_id = get_current_family_id()
    print(f"DEBUG needs_panel() → current_family_id = {current_family_id}")

    if not ensure_family_selected(current_family_id):
        print("DEBUG needs_panel() → STOP: famille non sélectionnée")
        return

    families = get_families()
    print(f"DEBUG needs_panel() → familles = {families}")

    family_dict = {f['name']: f['id'] for f in families}

    # Sélecteur de famille
    ui.select(
        list(family_dict.keys()),
        value=[name for name, fid in family_dict.items() if fid == current_family_id][0],
        label="Famille",
        on_change=lambda e: (
            print(f"DEBUG needs_panel() → famille changée = {family_dict[e.value]}"),
            set_current_family_id(family_dict[e.value]),
            ui.navigate.to('/?tab=besoins')
        )
    ).classes("w-full")

    ui.separator()

    ui.label("Besoins").classes("text-xl font-bold")

    tri_mode = get_tri_mode_needs()

    ui.select(
        ["Alphabétique", "Ordre d’ajout", "Catégorie"],
        value=tri_mode,
        label="Trier par",
        on_change=lambda e: (
            print(f"DEBUG needs_panel() → tri changé = {e.value}"),
            set_tri_mode_needs(e.value),
            ui.navigate.to('/?tab=besoins')
        )
    ).classes("w-full")

    if not ensure_categories_exist():
        print("DEBUG needs_panel() → STOP: aucune catégorie")
        return

    categories = get_categories()
    print(f"DEBUG needs_panel() → catégories = {categories}")

    cat_dict = {c['name']: c['id'] for c in categories}
    cat_names = list(cat_dict.keys())

    needs = get_needs(current_family_id)
    print(f"DEBUG needs_panel() → besoins = {needs}")

    # Tri
    if tri_mode == "Alphabétique":
        needs = sorted(needs, key=lambda x: x['name'].strip().lower())
    elif tri_mode == "Catégorie":
        needs = sorted(needs, key=lambda x: (x['category'] or '').lower())

    # Affichage des besoins
    for need in needs:
        with ui.row().classes("items-center justify-between bg-gray-100 rounded-lg px-3 py-2 mt-2 gap-2"):

            with ui.row().classes("items-center gap-2"):
                ui.label(f"{need['name']}").classes("font-bold")
                ui.button(
                    "✔️" if need['done'] else "❌",
                    on_click=lambda nid=need['id']: (
                        print(f"DEBUG needs_panel() → toggle besoin {nid}"),
                        toggle_need_done(nid),
                        ui.navigate.to('/?tab=besoins')
                    )
                ).props("flat color=white")

            with ui.row().classes("items-center gap-2"):
                ui.select(
                    cat_names,
                    value=need['category'],
                    on_change=lambda e, nid=need['id']: (
                        print(f"DEBUG needs_panel() → changement catégorie besoin {nid} → {e.value}"),
                        add_need(current_family_id, cat_dict[e.value], need['name'], need['done']),
                        delete_need(nid),
                        ui.navigate.to('/?tab=besoins')
                    )
                ).classes("w-32")

                ui.button(
                    "🗑️",
                    on_click=lambda nid=need['id']: (
                        print(f"DEBUG needs_panel() → suppression besoin {nid}"),
                        delete_need(nid),
                        ui.navigate.to('/?tab=besoins')
                    )
                ).props("flat color=red")
