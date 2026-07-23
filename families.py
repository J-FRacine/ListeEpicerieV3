from nicegui import ui

from db import get_families, create_family, delete_family
from state import current_family_id
from utils import ensure_family_selected


def families_panel():
    print("DEBUG families_panel() → entrée")
    print(f"DEBUG families_panel() → current_family_id = {current_family_id}")

    families = get_families()
    print(f"DEBUG families_panel() → familles = {families}")

    # Sélection automatique si aucune famille
    if current_family_id is None and families:
        globals()['current_family_id'] = families[0]['id']
        print(f"DEBUG families_panel() → auto-select = {current_family_id}")
        ui.notify(f"Famille auto-sélectionnée dans families_panel: {current_family_id}")

    ensure_family_selected(current_family_id)

    ui.label("Gestion des familles").classes("text-xl font-bold")

    family_dict = {f['name']: f['id'] for f in families}

    if families:
        ui.label("Famille active")

        def set_active_family(e):
            globals()['current_family_id'] = family_dict[e.value]
            print(f"DEBUG families_panel() → famille changée = {current_family_id}")
            ui.navigate.to('/?tab=families')

        ui.select(
            list(family_dict.keys()),
            value=[name for name, fid in family_dict.items() if fid == current_family_id][0],
            on_change=set_active_family
        ).classes("w-full")
    else:
        ui.label("⚠️ Aucune famille. Créez-en une ci-dessous.")

    ui.separator()

    ui.label("Familles existantes").classes("text-lg font-bold mt-2")

    if not families:
        ui.label("Aucune famille trouvée.")
    else:
        for f in families:
            with ui.row().classes("items-center justify-between mt-1"):
                ui.label(f['name']).classes("font-bold")

                with ui.row().classes("gap-2"):

                    ui.button(
                        "Activer",
                        on_click=lambda fid=f['id']: (
                            globals().__setitem__('current_family_id', fid),
                            print(f"DEBUG families_panel() → famille activée = {fid}"),
                            ui.navigate.to('/?tab=families')
                        )
                    ).props("flat color=white")

                    def open_delete_dialog(fid=f['id'], fname=f['name']):
                        print(f"DEBUG families_panel() → demande suppression famille {fname}")
                        with ui.dialog() as dialog:
                            with ui.card().classes("p-4"):
                                ui.label(f"Supprimer la famille '{fname}' ?").classes("text-lg font-bold")
                                ui.label("Cette action est irréversible.")

                                with ui.row().classes("justify-end gap-2 mt-4"):
                                    ui.button("Annuler", on_click=dialog.close)
                                    ui.button(
                                        "Supprimer",
                                        on_click=lambda: (
                                            delete_family(fid),
                                            print(f"DEBUG families_panel() → famille supprimée = {fid}"),
                                            dialog.close(),
                                            ui.notify(f"Famille '{fname}' supprimée."),
                                            ui.navigate.to('/?tab=families')
                                        )
                                    ).props("color=red")

                        dialog.open()

                    ui.button("🗑️", on_click=open_delete_dialog).props("flat color=red")

    ui.separator()

    new_name = ui.input("Nouvelle famille").classes("w-full")
    ui.button(
        "Créer",
        on_click=lambda: (
            create_family(new_name.value),
            print(f"DEBUG families_panel() → famille créée = {new_name.value}"),
            ui.navigate.to('/?tab=families')
        )
    ).classes("w-full mt-2")
