# ---------------------------------------------------------
#  PANNEAU : FAMILLES
# ---------------------------------------------------------
from nicegui import ui

def families_panel():
    ui.label("Gestion des familles").classes("text-xl font-bold")

    families = get_families()
    family_dict = {f['name']: f['id'] for f in families}

    # Sélecteur de famille active
    if families:
        ui.label("Famille active")
        ui.select(
            list(family_dict.keys()),
            value=[name for name, fid in family_dict.items() if fid == current_family_id][0]
            if current_family_id in family_dict.values() else list(family_dict.keys())[0],
            on_change=lambda e: (
                globals().__setitem__('current_family_id', family_dict[e.value]),
                ui.navigate.to('/')
            )
        ).classes("w-full")
    else:
        ui.label("⚠️ Aucune famille. Créez-en une ci-dessous.")

    ui.separator()

    # Liste de toutes les familles
    ui.label("Familles existantes").classes("text-lg font-bold mt-2")

    if not families:
        ui.label("Aucune famille trouvée.")
    else:
        for f in families:
            with ui.row().classes("items-center justify-between mt-1"):
                ui.label(f['name']).classes("font-bold")

                with ui.row().classes("gap-2"):
                    # Activer
                    ui.button(
                        "Activer",
                        on_click=lambda fid=f['id']: (
                            globals().__setitem__('current_family_id', fid),
                            ui.navigate.to('/')
                        )
                    ).props("flat color=white")

                    # Supprimer (dialogue NiceGUI 1.x)
                    def open_delete_dialog(fid=f['id'], fname=f['name']):
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
                                            dialog.close(),
                                            ui.notify(f"Famille '{fname}' supprimée."),
                                            ui.navigate.to('/')
                                        )
                                    ).props("color=red")

                        dialog.open()

                    ui.button("🗑️", on_click=open_delete_dialog).props("flat color=red")

    ui.separator()

    # Création d’une nouvelle famille
    new_name = ui.input("Nouvelle famille").classes("w-full")
    ui.button("Créer", on_click=lambda: (
        create_family(new_name.value),
        ui.navigate.to('/')
    )).classes("w-full mt-2")
