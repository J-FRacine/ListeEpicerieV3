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

# Initialisation DB
init_db()


# -----------------------------
#  PAGE DE SÉLECTION DE FAMILLE
# -----------------------------

@ui.page('/select_family')
def select_family_page():
    # Page centrée verticalement et horizontalement
    with ui.column().classes('items-center justify-center w-full h-screen gap-4'):
        ui.label('Choisir une famille').classes('text-3xl font-bold mb-4')

        families = get_families()

        # Carte moderne centrée
        with ui.card().classes('p-6 shadow-lg rounded-xl w-80 items-center'):
            family_select = ui.select(
                {f['id']: f['name'] for f in families},
                label='Famille'
            ).classes('w-full')

            ui.button(
                'Continuer',
                on_click=lambda: ui.navigate.to(
                    f'/items?family_id={family_select.value}'
                )
            ).classes('w-full mt-4 bg-blue-600 text-white')


# -----------------------------
#  PAGE ITEMS
# -----------------------------

@ui.page('/items')
def items_page(family_id: int):
    with ui.column().classes('items-center w-full h-full gap-4 p-4'):
        ui.label('Liste d’épicerie').classes('text-3xl font-bold mb-4')

        categories = get_categories()

        # Carte pour ajouter un item
        with ui.card().classes('p-6 shadow-lg rounded-xl w-full max-w-xl'):
            item_name = ui.input('Nom de l’item').classes('w-full')
            item_qty = ui.number('Quantité', value=1).classes('w-full')
            item_cat = ui.select(
                {c['id']: c['name'] for c in categories},
                label='Catégorie'
            ).classes('w-full')

            ui.button(
                'Ajouter',
                on_click=lambda: (
                    add_item(family_id, item_cat.value, item_name.value, int(item_qty.value or 1)),
                    ui.navigate.to(f'/items?family_id={family_id}')
                )
            ).classes('w-full mt-4 bg-green-600 text-white')

        ui.separator()
        ui.label('Items').classes('text-2xl font-semibold')

        items = get_items(family_id)

        # Liste des items
        with ui.column().classes('w-full max-w-xl gap-2'):
            for it in items:
                with ui.row().classes('w-full justify-between items-center p-2 border rounded-lg'):
                    ui.label(f"{it['name']} ({it['quantity']}) — {it['category']}")
                    ui.button(
                        'Supprimer',
                        color='red',
                        on_click=lambda it_id=it['id']: (
                            delete_item(it_id, family_id),
                            ui.navigate.to(f'/items?family_id={family_id}')
                        )
                    )

        ui.button(
            'Changer de famille',
            on_click=lambda: ui.navigate.to('/select_family')
        ).classes('mt-6 bg-gray-700 text-white')


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
