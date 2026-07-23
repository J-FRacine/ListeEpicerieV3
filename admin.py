# ---------------------------------------------------------
#  PANNEAU : ADMIN
# ---------------------------------------------------------

from nicegui import ui

from db import (
    get_items,
    get_families,
    get_categories,
    create_category,
    add_item,
)
from state import current_family_id


def admin_panel():
    ui.label("Administration").classes("text-xl font-bold")

    ui.separator()

    # ---------- EXPORT ----------
    ui.label("Exporter les données").classes("text-lg font-bold mt-2")

    def export_csv():
        import csv
        from datetime import datetime

        items = get_items(current_family_id)
        families = get_families()
        family_name = next(f['name'] for f in families if f['id'] == current_family_id)

        filename = f"items_export_{datetime.now().strftime('%Y-%m-%d_%Hh%M')}.csv"

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Nom', 'Catégorie', 'Besoin', 'Famille'])
            for it in items:
                writer.writerow([
                    it['id'],
                    it['name'],
                    it['category'],
                    it['needed'],
                    family_name
                ])

        ui.download(filename)

    ui.button("Exporter CSV", on_click=export_csv).classes("w-full mt-2")

    ui.separator()

    # ---------- IMPORT ----------
    ui.label("Importer un fichier CSV").classes("text-lg font-bold mt-2")

    async def import_csv(event):
        import csv
        import io

        raw = await event.file.read()
        content = raw.decode('utf-8')
        f = io.StringIO(content)

        reader = csv.DictReader(f)

        for row in reader:
            name = row['Nom']
            category = row['Catégorie']
            needed = int(row['Besoin'])

            categories = get_categories()
            cat_dict = {c['name']: c['id'] for c in categories}

            if category not in cat_dict:
                create_category(category)
                categories = get_categories()
                cat_dict = {c['name']: c['id'] for c in categories}

            cat_id = cat_dict[category]

            add_item(current_family_id, cat_id, name, 1, needed)

        ui.notify("Importation terminée !")
        ui.navigate.to('/?tab=admin')

    ui.upload(
        label="Importer CSV",
        on_upload=import_csv,
        multiple=False
    ).classes("w-full mt-2")

    ui.separator()

    # ---------- COPIE FAMILLE -> FAMILLE ----------
    ui.label("Copier les items d'une famille à une autre").classes("text-lg font-bold mt-2")

    families = get_families()
    if not families:
        ui.label("Aucune famille disponible pour la copie.")
        return

    family_dict = {f['name']: f['id'] for f in families}

    source = ui.select(list(family_dict.keys()), label="Source").classes("w-full")
    dest = ui.select(list(family_dict.keys()), label="Destination").classes("w-full")

    def copy_family():
        if not source.value or not dest.value:
            ui.notify("Sélectionnez une source et une destination.")
            return

        src_id = family_dict[source.value]
        dst_id = family_dict[dest.value]

        if src_id == dst_id:
            ui.notify("Impossible de copier dans la même famille.")
            return

        items = get_items(src_id)

        categories = get_categories()
        cat_dict = {c['name']: c['id'] for c in categories}

        for it in items:
            cat_name = it['category']
            if cat_name not in cat_dict:
                create_category(cat_name)
                categories = get_categories()
                cat_dict = {c['name']: c['id'] for c in categories}

            cat_id = cat_dict[cat_name]

            add_item(dst_id, cat_id, it['name'], it['quantity'], it['needed'])

        ui.notify("Copie terminée !")
        ui.navigate.to('/?tab=admin')

    ui.button("Copier", on_click=copy_family).classes("w-full mt-2")

    ui.separator()

    # ---------- MODE CLAIR / SOMBRE ----------
    ui.label("Apparence").classes("text-lg font-bold mt-4")

    ui.button(
        "🌗 Basculer mode clair / sombre",
        on_click=lambda: ui.dark_mode().toggle()
    ).classes("w-full mt-2")

    ui.separator()

    # ---------- RETOUR AU MENU DES APPLICATIONS ----------
    ui.button(
        "⬅ Retour au menu des applications",
        on_click=lambda: ui.navigate.to('/apps')
    ).classes("w-full mt-4")
