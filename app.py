from nicegui import ui, app
import os

from db import init_db, get_families
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
    print("==============================")
    print("DEBUG: entrée dans portal_page()")
    print("==============================")

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
    try:
        auth = app.storage.user.get('auth')
        print(f"DEBUG: auth = {auth}")
    except Exception as e:
        print(f"DEBUG: ERREUR storage.user → {e}")
        ui.navigate.to('/portal')
        return

    if not auth:
        print("DEBUG: utilisateur non authentifié → redirection vers /portal")
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
        familles = get_families()
        print(f"DEBUG: familles trouvées = {familles}")

        if familles:
            set_current_family_id(familles[0]['id'])
            current_family_id = familles[0]['id']
            print(f"DEBUG: current_family_id APRÈS auto-select = {current_family_id}")
        else:
            print("DEBUG: AUCUNE famille → affichage message")
            ui.label("⚠️ Aucune famille trouvée. Ajoutez-en dans l’onglet Familles.")
            return

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

print("DEBUG: initialisation DB…")
init_db()
print("DEBUG: DB initialisée")

ui.run(
    host='0.0.0.0',
    port=int(os.getenv("PORT", 8080)),
    storage_secret=os.getenv("STORAGE_SECRET", "dev-secret")
)
