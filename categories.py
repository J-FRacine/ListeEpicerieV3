# ---------------------------------------------------------
#  PANNEAU : CATÉGORIES
# ---------------------------------------------------------

from nicegui import ui

from db import (
    get_categories,
    create_category,
    delete_category,
    get_connection,
)
from state import current_family_id
from utils import ensure_family_selected


def categories_panel():

    # Vérifier famille sélectionnée (si nécessaire dans ton app)
    ensure_family_selected(current_family_id)

    ui.label("Gestion des catégories").classes("text-xl font-bold")

    # --- Ajouter une catégorie ---
    new_cat = ui.input("Nouvelle catégorie").classes("w-full")
    ui.button(
        "Ajouter",
        on_click=lambda: (
            create_category(new_cat.value),
            ui.navigate.to('/?tab=categories')
        )
    ).classes("w-full mt-2")

    ui.separator()

    # --- Liste des catégories existantes ---
    categories = get_categories()
    if not categories:
        ui.label("⚠️ Aucune catégorie. Ajoutez-en une ci-dessus.")
        return

    for cat in categories:
        with ui.row().classes("items-center justify-between mt-1"):
            ui.label(cat['name'])
            ui.button(
                "🗑️",
                on_click=lambda cid=cat['id']: (
                    delete_category(cid),
                    ui.navigate.to('/?tab=categories')
                )
            ).props("flat color=red")

    # ---------------------------------------------------------
    #  GESTION AVANCÉE : RENOMMER + FUSIONNER
    # ---------------------------------------------------------

    ui.separator()
    ui.label("Gestion avancée des catégories").classes("text-lg font-bold mt-2")

    categories = get_categories()
    cat_dict = {c['name']: c['id'] for c in categories}
    cat_names = list(cat_dict.keys())

    # --- Sélection de la catégorie source ---
    source_cat = ui.select(cat_names, label="Catégorie de départ").classes("w-full mt-2")

    ui.separator()

    # ---------------------------------------------------------
    #  RENOMMER LA CATÉGORIE
    # ---------------------------------------------------------

    ui.label("Renommer la catégorie").classes("text-md font-bold mt-2")
    new_cat_name = ui.input("Nouveau nom").classes("w-full")

    def rename_category():
        if not source_cat.value or not new_cat_name.value:
            ui.notify("Sélectionnez une catégorie et entrez un nouveau nom.")
            return

        cat_id = cat_dict[source_cat.value]

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE categories SET name = %s WHERE id = %s", (new_cat_name.value, cat_id))
        conn.commit()
        cur.close()
        conn.close()

        ui.notify(f"Catégorie renommée en '{new_cat_name.value}' !")
        ui.navigate.to('/?tab=categories')

    ui.button("Renommer", on_click=rename_category).classes("w-full mt-2")

    ui.separator()

    # ---------------------------------------------------------
    #  FUSIONNER DANS UNE AUTRE CATÉGORIE
    # ---------------------------------------------------------

    ui.label("Fusionner dans une autre catégorie").classes("text-md font-bold mt-2")

    # Liste des catégories destination (sans la source)
    def get_dest_list():
        return [c for c in cat_names if c != source_cat.value]

    dest_cat = ui.select(get_dest_list(), label="Catégorie destination").classes("w-full")

    def merge_categories():
        if not source_cat.value or not dest_cat.value:
            ui.notify("Sélectionnez la catégorie de départ et la catégorie de destination.")
            return

        src_id = cat_dict[source_cat.value]
        dst_id = cat_dict[dest_cat.value]

        conn = get_connection()
        cur = conn.cursor()

        # Déplacer les items vers la catégorie destination
        cur.execute("UPDATE items SET category_id = %s WHERE category_id = %s", (dst_id, src_id))
        conn.commit()

        # Supprimer la catégorie source
        cur.execute("DELETE FROM categories WHERE id = %s", (src_id,))
        conn.commit()

        cur.close()
        conn.close()

        ui.notify(f"Catégorie '{source_cat.value}' fusionnée dans '{dest_cat.value}' !")
        ui.navigate.to('/?tab=categories')

    ui.button("Fusionner", on_click=merge_categories).classes("w-full mt-2")
