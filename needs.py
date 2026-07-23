# ---------------------------------------------------------
#  PANNEAU : BESOINS
# ---------------------------------------------------------

from nicegui import ui

from db import get_items, get_families, toggle_needed
from state import current_family_id, tri_mode_needs
from utils import ensure_family_selected


def needs_panel():
    global tri_mode_needs

    # Vérifier famille sélectionnée
    if not ensure_family_selected(current_family_id):
        return

    # Sélecteur de famille
    families = get_families()
    family_dict = {f['name']: f['id'] for f in families}

    ui.select(
        list(family_dict.keys()),
        value=[name for name, fid in family_dict.items() if fid == current_family_id][0]
        if current_family_id in family_dict.values() else list(family_dict.keys())[0],
        label="Famille",
        on_change=lambda e: (
            globals().__setitem__('current_family_id', family_dict[e.value]),
            ui.navigate.to('/?tab=besoins')
        )
    ).classes("w-full")

    ui.separator()

    ui.label("Besoins").classes("text-xl font-bold")

    # Tri
    ui.select(
        ["Alphabétique", "Ordre d’ajout"],
        value=tri_mode_needs,
        label="Trier par",
        on_change=lambda e: (
            globals().__setitem__('tri_mode_needs', e.value),
            ui.navigate.to('/?tab=besoins')
        )
    ).classes("w-full")

    # Items nécessaires
    items = get_items(current_family_id)
    needed_items = [it for it in items if it['needed'] == 1]

    # Groupement par catégorie
    grouped = {}
    for it in needed_items:
        grouped.setdefault(it['category'] or "Sans catégorie", []).append(it)

    if not grouped:
        ui.label("Aucun item marqué comme besoin.")
        return

    # Affichage
    for cat, its in grouped.items():
        ui.label(f"📂 {cat}").classes("text-lg font-bold mt-3")

        if tri_mode_needs == "Alphabétique":
            its = sorted(its, key=lambda x: x['name'].strip().lower())

        for it in its:
            with ui.row().classes("items-center gap-3 mt-1"):
                ui.button(
                    "❌",
                    on_click=lambda iid=it['id']: (
                        toggle_needed(iid),
                        ui.navigate.to('/?tab=besoins')
                    )
                ).props("flat color=red")

                ui.label(it['name']).classes("font-bold")
