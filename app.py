import os
from nicegui import ui, app
from db import (
    init_db,
    get_families,
    get_categories,
    get_items,
    add_item,
    delete_item,
)

init_db()


# -----------------------------
#  PAGE DE SÉLECTION DE FAMILLE
# -----------------------------

@ui.page('/select_family')
def select_family_page():
    ui.label('Choisir une famille').classes('text-2xl font-bold mb-4')

    families = get_families()

    family_select = ui.select(
        {f['id']: f['name'] for f in families},
        label='Famille'
    )

    async def go():
        if not family_select.value:
            ui.notify('Choisir une famille', color='red')
            return
        ui.navigate.to(f'/items?family_id={family_select.value}')

    ui.button('Continuer', on_click=go).classes('mt-4')


# -----------------------------
#  PAGE ITEMS
# -----------------------------

@ui.page('/items')
def items_page(family_id: int):
    ui.label('Liste d’épicerie').classes('text-2xl font-bold mb-4')

    categories = get_categories()

    item_name = ui.input('Nom de l’item')
    item_qty = ui.number('Quantité', value=1)
    item_cat = ui.select({c['id']: c['name'] for c in categories}, label='Catégorie')

    async def add_item_handler():
        if not item_name.value or not item_cat.value:
            ui.notify('Nom et catégorie requis', color='red')
            return
        add_item(family_id, item_cat.value, item_name.value, int(item_qty.value or 1))
        ui.notify('Item ajouté')
        ui.navigate.to(f'/items?family_id={family_id}')

    ui.button('Ajouter', on_click=add_item_handler)

    ui.separator()
    ui.label('Items :').classes('text-xl mt-4')

    items = get_items(family_id)

    for it in items:
        async def delete_handler(it_id=it['id']):
            delete_item(it_id, family_id)
            ui.notify('Item supprimé')
            ui.navigate.to(f'/items?family_id={family_id}')

        with ui.row().classes('items-center'):
            ui.label(f"{it['name']} ({it['quantity']}) — {it['category']}")
            ui.button('Supprimer', color='red', on_click=delete_handler)

    ui.button('Changer de famille', on_click=lambda: ui.navigate.to('/select_family')).classes('mt-6')


# -----------------------------
#  PAGE RACINE
# -----------------------------

@ui.page('/')
def index_page():
    ui.navigate.to('/select_family')


# -----------------------------
#  RUN
# -----------------------------

port = int(os.getenv('PORT', 8080))
ui.run(host='0.0.0.0', port=port)
