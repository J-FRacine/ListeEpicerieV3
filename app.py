from __future__ import annotations

import os

from nicegui import app, ui

from categories import categories_panel
from db import get_families, init_db
from families import families_panel
from items import items_panel
from needs import needs_panel
from state import (
    get_current_family_id,
    set_current_family_id,
    set_current_tab,
)
from utils import apply_theme


VALID_APP_TABS = {'items', 'besoins', 'categories'}
FAMILY_TABS = {'familles', 'families'}
PORTAL_TABS = {'portail', 'portal', 'apps'}


# ---------------------------------------------------------
# OUTILS D'AFFICHAGE
# ---------------------------------------------------------

def page_container():
    """Retourne le conteneur principal utilisé par toutes les pages."""
    return ui.column().classes(
        'w-full max-w-3xl mx-auto px-4 pt-4 pb-24 gap-4'
    )


def show_portal(*, authenticated: bool) -> None:
    """Affiche le portail central JF Apps."""
    apply_theme()

    with page_container():
        with ui.card().classes('w-full p-6 items-center text-center'):
            ui.label('JF Apps').classes('text-3xl font-bold')
            ui.label('Portail de mes applications personnelles').classes(
                'text-base text-gray-600 dark:text-gray-300'
            )

            if not authenticated:
                ui.label(
                    "La connexion réelle sera ajoutée plus tard. Pour l'instant, "
                    "le bouton Entrer ouvre simplement le portail."
                ).classes('mt-4 text-sm text-gray-500')

                def enter_portal() -> None:
                    app.storage.user['auth'] = True
                    ui.navigate.to('/?tab=portail')

                ui.button('Entrer', on_click=enter_portal).classes('mt-4 w-full max-w-xs')
                return

            ui.separator().classes('my-2')

            ui.button(
                "Ouvrir la liste d'épicerie",
                icon='shopping_cart',
                on_click=lambda: ui.navigate.to('/?tab=items'),
            ).classes('w-full max-w-sm')

            ui.button(
                'Gérer les familles',
                icon='groups',
                on_click=lambda: ui.navigate.to('/?tab=familles'),
            ).classes('w-full max-w-sm')

            ui.button(
                'Déconnexion',
                icon='logout',
                on_click=logout,
            ).props('flat').classes('mt-2')


def logout() -> None:
    """Ferme la session provisoire et retourne au portail d'entrée."""
    app.storage.user.clear()
    ui.navigate.to('/')


def ensure_valid_family() -> bool:
    """Sélectionne une famille valide et retourne True si une famille existe."""
    families = get_families()
    if not families:
        set_current_family_id(None)
        return False

    valid_ids = {family['id'] for family in families}
    current_family_id = get_current_family_id()

    if current_family_id not in valid_ids:
        set_current_family_id(families[0]['id'])

    return True


def show_no_family_message() -> None:
    """Affiche un chemin clair pour créer la première famille."""
    with ui.card().classes('w-full p-6'):
        ui.label('Aucune famille trouvée').classes('text-xl font-bold')
        ui.label(
            "Crée d'abord une famille dans le portail, puis reviens dans la liste d'épicerie."
        )
        ui.button(
            'Créer ou gérer une famille',
            icon='groups',
            on_click=lambda: ui.navigate.to('/?tab=familles'),
        ).classes('mt-2')


def bottom_navigation(active_tab: str) -> None:
    """Navigation mobile de l'application d'épicerie."""
    with ui.footer().classes('bg-gray-100 dark:bg-gray-900 border-t p-2'):
        with ui.row().classes('w-full justify-around gap-1'):
            ui.button(
                'Items',
                icon='inventory_2',
                on_click=lambda: ui.navigate.to('/?tab=items'),
            ).props('flat' + (' color=primary' if active_tab == 'items' else ''))

            ui.button(
                'Besoins',
                icon='shopping_cart',
                on_click=lambda: ui.navigate.to('/?tab=besoins'),
            ).props('flat' + (' color=primary' if active_tab == 'besoins' else ''))

            ui.button(
                'Catégories',
                icon='category',
                on_click=lambda: ui.navigate.to('/?tab=categories'),
            ).props('flat' + (' color=primary' if active_tab == 'categories' else ''))

            ui.button(
                'Portail',
                icon='apps',
                on_click=lambda: ui.navigate.to('/?tab=portail'),
            ).props('flat')


# ---------------------------------------------------------
# ROUTE PRINCIPALE
# ---------------------------------------------------------

@ui.page('/', title='JF Apps')
def index(tab: str = 'portail') -> None:
    """Affiche le portail ou l'une des sections de l'application.

    NiceGUI transmet automatiquement le paramètre d'URL ``tab`` à cette
    fonction, par exemple ``/?tab=items``.
    """
    apply_theme()

    authenticated = bool(app.storage.user.get('auth'))
    if not authenticated:
        show_portal(authenticated=False)
        return

    normalized_tab = (tab or 'portail').strip().lower()

    if normalized_tab in PORTAL_TABS:
        show_portal(authenticated=True)
        return

    if normalized_tab in FAMILY_TABS:
        set_current_tab('familles')
        with page_container():
            ui.button(
                'Retour au portail',
                icon='arrow_back',
                on_click=lambda: ui.navigate.to('/?tab=portail'),
            ).props('flat')
            families_panel()
        return

    if normalized_tab not in VALID_APP_TABS:
        normalized_tab = 'items'

    set_current_tab(normalized_tab)

    with page_container():
        ui.label("Liste d'épicerie").classes('text-2xl font-bold')

        if not ensure_valid_family():
            show_no_family_message()
        elif normalized_tab == 'items':
            items_panel()
        elif normalized_tab == 'besoins':
            needs_panel()
        elif normalized_tab == 'categories':
            categories_panel()

    bottom_navigation(normalized_tab)


# ---------------------------------------------------------
# LANCEMENT
# ---------------------------------------------------------

init_db()

ui.run(
    host='0.0.0.0',
    port=int(os.getenv('PORT', '8080')),
    storage_secret=os.getenv('STORAGE_SECRET', 'dev-secret-change-me'),
    reload=False,
)
