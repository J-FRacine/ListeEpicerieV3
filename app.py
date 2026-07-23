from nicegui import ui, app

from db import init_db
from state import (
    get_current_tab,
    set_current_tab,
    get_current_family_id,
    set_current_family_id,
)
from items import items_panel
from needs import needs_panel
from families import families_panel
from categories import categories_panel
from utils import apply_theme


# ---------------------------------------------------------
# PORTAIL (login simple)
# ---------------------------------------------------------

def portal_page():
    ui.label("Bienvenue").classes("text-2xl font-bold mt-8")

    ui.button(
        "Entrer",
        on_click=lambda: (
            print("DEBUG portal_page() → authentification"),
            app.storage.user.update({'auth': True}),
            ui.navigate.to('/')
        )
    ).classes("mt-4")


# ---------------------------------------------------------
# PAGE PRINCIPALE
# ---------------------------------------------------------

def main_page():
    print("==============================")
    print("DEBUG: entrée dans main_page()")
    print("==============================")

    # Vérification authentification
    if not app.storage.user.get('auth'):
        print("DEBUG: utilisateur non authentifié → redirection")
        ui.navigate.to('/portal')
        return

    # Appliquer le thème
    apply_theme()

    # Lire l’onglet dans l’URL
    tab = ui.context.request.query_params.get('tab')
    print(f"DEBUG: tab dans URL = {tab}")

    if tab:
        set_current_tab(tab)

    current_tab = get_current_tab()
    print(f"DEBUG: current_tab utilisé = {current_tab}")

    # Auto-sélection famille si aucune
    current_family_id = get_current_family_id()
    print(f"DEBUG: current_family_id AVANT auto-select = {current_family_id}")

    if current_family_id is None:
        set_current_family_id(1)
        current_family_id = 1
        print(f"DEBUG: current_family_id APRÈS auto-select = {current_family_id}")

    # Rendu du panneau
    print(f"DEBUG: rendu panneau → {current_tab}")

    if current_tab == 'items':
        print("DEBUG: rendu items_panel()")
        items_panel()

    elif current_tab == 'besoins':
        print("DEBUG: rendu needs_panel()")
        needs_panel()

    elif current_tab == 'familles':
        print("DEBUG: rendu families_panel()")
        families_panel()

    elif current_tab == 'categories':
        print("DEBUG: rendu categories_panel()")
        categories_panel()

    # Barre de navigation
    print("DEBUG: rendu bottom_nav()")

    with ui.footer().classes("bg-gray-200 p-2"):
        with ui.row().classes("justify-around w-full"):
            ui.button("Items", on_click=lambda: ui.navigate.to('/?tab=items'))
            ui.button("Besoins", on_click=lambda: ui.navigate.to('/?tab=besoins'))
            ui.button("Familles", on_click=lambda: ui.navigate.to('/?tab=familles'))
            ui.button("Catégories", on_click=lambda: ui.navigate.to('/?tab=categories'))


# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

@ui.page('/portal')
def portal():
    portal_page()

@ui.page('/')
def index():
    main_page()


# ---------------------------------------------------------
# LANCEMENT
# ---------------------------------------------------------

init_db()
ui.run()
