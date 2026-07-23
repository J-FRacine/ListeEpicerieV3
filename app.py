import os
from nicegui import ui, app
from fastapi import Request

# --- Import des modules ---
from header import jf_header
from navigation import bottom_nav

from admin import admin_panel
from items import items_panel, add_item_panel
from needs import needs_panel
from categories import categories_panel
from families import families_panel

from state import current_tab, current_family_id
from utils import apply_theme
from db import init_db, get_families

# ---------------------------------------------------------
#  INITIALISATION BD
# ---------------------------------------------------------
print("DEBUG: init_db() lancé")
init_db()
print("DEBUG: init_db() terminé")

# ---------------------------------------------------------
#  PORTAIL
# ---------------------------------------------------------

VALID_CODE = "1234"
VALID_PASSWORD = "jf2024"

@app.get('/logout')
def logout():
    print("DEBUG: logout() → suppression session utilisateur")
    app.storage.user.clear()
    ui.navigate.to('/portal')

@ui.page('/portal')
def portal_page():
    print("DEBUG: entrée dans portal_page()")
    apply_theme()
    jf_header()

    with ui.column().classes(
        "w-full max-w-md mx-auto mt-10 p-6 bg-white dark:bg-gray-800 rounded-lg shadow"
    ):
        ui.label("Portail des applications de J‑François").classes("text-2xl font-bold mb-4")

        code = ui.input("Code d’accès").classes("w-full")
        password = ui.input("Mot de passe", password=True).classes("w-full")

        def login():
            print(f"DEBUG: tentative login → code={code.value}, mdp={password.value}")
            if code.value == VALID_CODE and password.value == VALID_PASSWORD:
                print("DEBUG: login réussi")
                app.storage.user['auth'] = True
                ui.navigate.to('/apps')
            else:
                print("DEBUG: login échoué")
                ui.notify("Code ou mot de passe incorrect", color="red")

        ui.button("Connexion", on_click=login).classes("w-full mt-4")

# ---------------------------------------------------------
#  MENU DES APPS
# ---------------------------------------------------------

@ui.page('/apps')
def apps_page():
    print("DEBUG: entrée dans apps_page()")
    apply_theme()

    if not app.storage.user.get('auth'):
        print("DEBUG: utilisateur non authentifié → redirection")
        ui.navigate.to('/portal')
        return

    jf_header()

    with ui.column().classes(
        "w-full max-w-md mx-auto mt-10 p-6 bg-white dark:bg-gray-800 rounded-lg shadow"
    ):
        ui.label("Applications disponibles").classes("text-2xl font-bold mb-4")

        ui.button("Liste d’achats", on_click=lambda: ui.navigate.to('/')).classes("w-full mb-2")
        ui.button("Admin", on_click=lambda: ui.navigate.to('/?tab=admin')).classes("w-full mb-2")
        ui.button("Déconnexion", on_click=lambda: ui.navigate.to('/logout')).classes("w-full mt-4")

# ---------------------------------------------------------
#  PAGE PRINCIPALE
# ---------------------------------------------------------

@ui.page('/')
def main_page(request: Request):
    print("\n\n==============================")
    print("DEBUG: entrée dans main_page()")
    print("==============================")

    # --- Sélection automatique de la première famille (DOIT être en premier) ---
    print(f"DEBUG: current_family_id AVANT auto-select = {current_family_id}")
    if current_family_id is None:
        families = get_families()
        print(f"DEBUG: familles trouvées = {families}")
        if families:
            globals()['current_family_id'] = families[0]['id']
            print(f"DEBUG: current_family_id APRÈS auto-select = {current_family_id}")
            ui.notify(f"Famille auto-sélectionnée: {current_family_id}")
        else:
            print("DEBUG: Aucune famille dans la BD !")
            ui.notify("Aucune famille dans la BD !")

    apply_theme()

    if not app.storage.user.get('auth'):
        print("DEBUG: utilisateur non authentifié → redirection")
        ui.navigate.to('/portal')
        return

    # --- LIRE L’ONGLET DEPUIS L’URL ---
    tab = request.query_params.get('tab')
    print(f"DEBUG: tab dans URL = {tab}")
    if tab:
        globals()['current_tab'] = tab

    print(f"DEBUG: current_tab utilisé = {current_tab}")

    with ui.row().classes("w-full justify-center mt-4"):
        with ui.column().classes(
            "w-full max-w-md bg-white dark:bg-gray-900 text-black dark:text-white "
            "p-4 rounded-lg shadow-md h-[calc(100vh-80px)] overflow-y-auto pb-24"
        ):

            print(f"DEBUG: rendu panneau → {current_tab}")

            if current_tab == 'items':
                print("DEBUG: rendu add_item_panel()")
                add_item_panel()
                ui.separator()
                print("DEBUG: rendu items_panel()")
                items_panel()
                ui.button("⬅ Retour au menu des applications",
                          on_click=lambda: ui.navigate.to('/apps')
                ).classes("w-full mt-4")

            elif current_tab == 'besoins':
                print("DEBUG: rendu needs_panel()")
                needs_panel()

            elif current_tab == 'categories':
                print("DEBUG: rendu categories_panel()")
                categories_panel()

            elif current_tab == 'families':
                print("DEBUG: rendu families_panel()")
                families_panel()

            elif current_tab == 'admin':
                print("DEBUG: rendu admin_panel()")
                admin_panel()

    print("DEBUG: rendu bottom_nav()")
    bottom_nav()

# ---------------------------------------------------------
#  LANCEMENT CANNER
# ---------------------------------------------------------

print("DEBUG: lancement ui.run()")
ui.run(
    title="JF Apps — Liste d’achats",
    favicon="logo_jf.png",
    reload=False,
    host="0.0.0.0",
    port=int(os.getenv("PORT", 8080)),
    storage_secret="jf-secret-key",
)
