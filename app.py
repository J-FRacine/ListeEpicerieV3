from __future__ import annotations

import os

from nicegui import app, ui

from backup import backup_panel
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


VALID_APP_TABS = {
    "items",
    "besoins",
    "categories",
    "donnees",
}
FAMILY_TABS = {"familles", "families"}
PORTAL_TABS = {"portail", "portal", "apps"}
BACKUP_TABS = {
    "donnees",
    "sauvegarde",
    "backup",
    "admin",
}


# ---------------------------------------------------------
# OUTILS D'AFFICHAGE
# ---------------------------------------------------------

def page_container():
    """Retourne le conteneur principal utilisé par toutes les pages."""

    return ui.column().classes(
        "w-full max-w-3xl mx-auto px-4 pt-4 pb-24 gap-4"
    )


def show_portal(*, authenticated):
    """Affiche le portail central JF Apps."""

    apply_theme()

    with page_container():
        with ui.card().classes(
            "w-full p-6 items-center text-center"
        ):
            ui.label("JF Apps").classes(
                "text-3xl font-bold"
            )
            ui.label(
                "Portail de mes applications personnelles"
            ).classes(
                "text-base text-gray-600 "
                "dark:text-gray-300"
            )

            if not authenticated:
                ui.label(
                    "La connexion réelle sera ajoutée plus tard. "
                    "Pour l’instant, le bouton Entrer ouvre "
                    "simplement le portail."
                ).classes(
                    "mt-4 text-sm text-gray-500"
                )

                def enter_portal():
                    app.storage.user["auth"] = True
                    ui.navigate.to("/?tab=portail")

                ui.button(
                    "Entrer",
                    on_click=enter_portal,
                ).classes(
                    "mt-4 w-full max-w-xs"
                )
                return

            ui.separator().classes("my-2")

            ui.button(
                "Ouvrir la liste d’épicerie",
                icon="shopping_cart",
                on_click=lambda: ui.navigate.to(
                    "/?tab=items"
                ),
            ).classes("w-full max-w-sm")

            ui.button(
                "Gérer les familles",
                icon="groups",
                on_click=lambda: ui.navigate.to(
                    "/?tab=familles"
                ),
            ).classes("w-full max-w-sm")

            ui.button(
                "Déconnexion",
                icon="logout",
                on_click=logout,
            ).props("flat").classes("mt-2")


def logout():
    """Ferme la session provisoire."""

    app.storage.user.clear()
    ui.navigate.to("/")


def ensure_valid_family():
    """Sélectionne une famille valide."""

    families = get_families()

    if not families:
        set_current_family_id(None)
        return False

    valid_ids = {
        family["id"]
        for family in families
    }
    current_family_id = get_current_family_id()

    if current_family_id not in valid_ids:
        set_current_family_id(families[0]["id"])

    return True


def show_no_family_message():
    """Affiche un chemin clair pour créer la première famille."""

    with ui.card().classes("w-full p-6"):
        ui.label(
            "Aucune famille trouvée"
        ).classes("text-xl font-bold")
        ui.label(
            "Crée d’abord une famille dans le portail, "
            "puis reviens dans la liste d’épicerie."
        )
        ui.button(
            "Créer ou gérer une famille",
            icon="groups",
            on_click=lambda: ui.navigate.to(
                "/?tab=familles"
            ),
        ).classes("mt-2")


def application_header(active_tab):
    """En-tête de l’application avec accès aux sauvegardes."""

    with ui.row().classes(
        "w-full items-center justify-between gap-3"
    ):
        ui.label(
            "Liste d’épicerie"
        ).classes("text-2xl font-bold")

        ui.button(
            icon="settings",
            on_click=lambda: ui.navigate.to(
                "/?tab=donnees"
            ),
        ).props(
            "flat round color=primary"
            if active_tab == "donnees"
            else "flat round"
        ).tooltip("Données et sauvegarde")


def bottom_navigation(active_tab):
    """Navigation mobile de l’application d’épicerie."""

    with ui.footer().classes(
        "bg-gray-100 dark:bg-gray-900 border-t p-2"
    ):
        with ui.row().classes(
            "w-full justify-around gap-1"
        ):
            ui.button(
                "Items",
                icon="inventory_2",
                on_click=lambda: ui.navigate.to(
                    "/?tab=items"
                ),
            ).props(
                "flat color=primary"
                if active_tab == "items"
                else "flat"
            )

            ui.button(
                "Besoins",
                icon="shopping_cart",
                on_click=lambda: ui.navigate.to(
                    "/?tab=besoins"
                ),
            ).props(
                "flat color=primary"
                if active_tab == "besoins"
                else "flat"
            )

            ui.button(
                "Catégories",
                icon="category",
                on_click=lambda: ui.navigate.to(
                    "/?tab=categories"
                ),
            ).props(
                "flat color=primary"
                if active_tab == "categories"
                else "flat"
            )

            ui.button(
                "Portail",
                icon="apps",
                on_click=lambda: ui.navigate.to(
                    "/?tab=portail"
                ),
            ).props("flat")


# ---------------------------------------------------------
# ROUTE PRINCIPALE
# ---------------------------------------------------------

@ui.page("/", title="JF Apps")
def index(tab="portail"):
    """Affiche le portail ou une section de l’application."""

    apply_theme()

    authenticated = bool(
        app.storage.user.get("auth")
    )

    if not authenticated:
        show_portal(authenticated=False)
        return

    normalized_tab = (
        tab or "portail"
    ).strip().lower()

    if normalized_tab in PORTAL_TABS:
        show_portal(authenticated=True)
        return

    if normalized_tab in FAMILY_TABS:
        set_current_tab("familles")

        with page_container():
            ui.button(
                "Retour au portail",
                icon="arrow_back",
                on_click=lambda: ui.navigate.to(
                    "/?tab=portail"
                ),
            ).props("flat")

            families_panel()

        return

    if normalized_tab in BACKUP_TABS:
        normalized_tab = "donnees"

    if normalized_tab not in VALID_APP_TABS:
        normalized_tab = "items"

    set_current_tab(normalized_tab)

    with page_container():
        application_header(normalized_tab)

        if not ensure_valid_family():
            show_no_family_message()
        elif normalized_tab == "items":
            items_panel()
        elif normalized_tab == "besoins":
            needs_panel()
        elif normalized_tab == "categories":
            categories_panel()
        elif normalized_tab == "donnees":
            backup_panel()

    bottom_navigation(normalized_tab)


# ---------------------------------------------------------
# LANCEMENT
# ---------------------------------------------------------

init_db()

ui.run(
    host="0.0.0.0",
    port=int(os.getenv("PORT", "8080")),
    storage_secret=os.getenv(
        "STORAGE_SECRET",
        "dev-secret-change-me",
    ),
    reload=False,
)
