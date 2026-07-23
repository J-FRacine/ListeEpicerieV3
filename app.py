import os
from nicegui import ui, app
from fastapi import Request

# --- Import des modules séparés ---
from header import jf_header
from navigation import bottom_nav

from admin import admin_panel
from items import items_panel, add_item_panel
from needs import needs_panel
from categories import categories_panel
from families import families_panel

from state import current_tab, current_family_id
from utils import ensure_family_selected
from utils import apply_theme


from db import init_db

# ---------------------------------------------------------
#  INITIALISATION BD
# ---------------------------------------------------------
init_db()

# ---------------------------------------------------------
#  PORTAIL
# ---------------------------------------------------------

VALID_CODE = "1234"
VALID_PASSWORD = "jf2024"

@app.get('/logout')
def logout():
    app.storage.user.clear()
    ui.navigate.to('/portal')

@ui.page('/portal')
def portal_page():
    jf_header()

    with ui.column().classes("w-full max-w-md mx-auto mt-10 p-6 bg-white dark:bg-gray-800 rounded-lg shadow"):
        ui.label("Portail des applications de J‑François").classes("text-2xl font-bold mb-4")

        code = ui.input("Code d’accès").classes("w-full")
        password = ui.input("Mot de passe", password=True).classes("w-full")

        def login():
            if code.value == VALID_CODE and password.value == VALID_PASSWORD:
                app.storage.user['auth'] = True
                ui.navigate.to('/apps')
            else:
                ui.notify("Code ou mot de passe incorrect", color="red")

        ui.button("Connexion", on_click=login).classes("w-full mt-4")

# ---------------------------------------------------------
#  MENU DES APPS
# ---------------------------------------------------------

@ui.page('/apps')
def apps_page():
    if not app.storage.user.get('auth'):
        ui.navigate.to('/portal')
        return

    jf_header()

    with ui.column().classes("w-full max-w-md mx-auto mt-10 p-6 bg-white dark:bg-gray-800 rounded-lg shadow"):
        ui.label("Applications disponibles").classes("text-2xl font-bold mb-4")

        ui.button("Liste d’achats", on_click=lambda: ui.navigate.to('/')).classes("w-full mb-2")
        ui.button("Admin", on_click=lambda: ui.navigate.to('/admin')).classes("w-full mb-2")
        ui.button("Déconnexion", on_click=lambda: ui.navigate.to('/logout')).classes("w-full mt-4")

# ---------------------------------------------------------
#  PAGE PRINCIPALE
# ---------------------------------------------------------

@ui.page('/')
def main_page(request: Request):
    if not app.storage.user.get('auth'):
        ui.navigate.to('/portal')
        return

    # --- LIRE L’ONGLET DEPUIS L’URL ---
    tab = request.query_params.get('tab')
    if tab:
        globals()['current_tab'] = tab

    with ui.row().classes("w-full justify-center mt-4"):
        with ui.column().classes(
            "w-full max-w-md bg-white text-black p-4 rounded-lg shadow-md "
            "h-[calc(100vh-80px)] overflow-y-auto pb-24"
        ):

            if current_tab == 'items':
                add_item_panel()
                ui.separator()
                items_panel()
                ui.button("⬅ Retour au menu des applications",
                    on_click=lambda: ui.navigate.to('/apps')
                ).classes("w-full mt-4")

            elif current_tab == 'besoins':
                needs_panel()

            elif current_tab == 'categories':
                categories_panel()

            elif current_tab == 'families':
                families_panel()

            elif current_tab == 'admin':
                admin_panel()

    bottom_nav()

# ---------------------------------------------------------
#  LANCEMENT CANNER
# ---------------------------------------------------------

ui.run(
    title="JF Apps — Liste d’achats",
    favicon="logo_jf.png",
    reload=False,
    host="0.0.0.0",
    port=int(os.getenv("PORT", 8080)),
    storage_secret="jf-secret-key",
)
