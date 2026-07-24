from __future__ import annotations

import os

from nicegui import ui

from auth import (
    authenticate,
    clear_session,
    get_current_user,
    hash_password,
    normalize_email,
    set_authenticated_user,
)
from backup import backup_panel
from categories import categories_panel
from db import (
    create_first_admin,
    get_accessible_families,
    init_db,
    needs_initial_admin_setup,
)
from families import families_panel
from items import items_panel
from needs import needs_panel
from state import (
    get_current_family_id,
    set_current_family_id,
    set_current_tab,
)
from users import account_panel, users_panel
from utils import apply_theme


VALID_APP_TABS = {"items", "besoins", "categories", "donnees"}
PORTAL_TABS = {"portail", "portal", "apps"}
FAMILY_TABS = {"familles", "families"}
USER_TABS = {"utilisateurs", "users"}
ACCOUNT_TABS = {"compte", "account"}
BACKUP_TABS = {"donnees", "sauvegarde", "backup", "admin"}


def page_container():
    return ui.column().classes(
        "w-full max-w-3xl mx-auto px-4 pt-4 pb-24 gap-4"
    )


def logout():
    clear_session()
    ui.navigate.to("/")


def show_first_admin_setup():
    apply_theme()

    with ui.column().classes(
        "w-full max-w-md mx-auto px-4 py-8 gap-4"
    ):
        with ui.card().classes("w-full p-6"):
            ui.label("Configuration initiale").classes(
                "text-2xl font-bold"
            )
            ui.label(
                "Créez le premier administrateur du portail. "
                "Toutes les familles existantes lui seront attribuées."
            ).classes("text-gray-600")

            name_input = ui.input(label="Votre nom").classes("w-full")
            email_input = ui.input(
                label="Adresse courriel"
            ).props(
                "type=email autocomplete=username"
            ).classes("w-full")
            password_input = ui.input(
                label="Mot de passe",
                password=True,
                password_toggle_button=True,
            ).props(
                "autocomplete=new-password"
            ).classes("w-full")
            confirmation_input = ui.input(
                label="Confirmer le mot de passe",
                password=True,
                password_toggle_button=True,
            ).props(
                "autocomplete=new-password"
            ).classes("w-full")

            ui.label(
                "Le mot de passe doit contenir au moins 10 caractères."
            ).classes("text-xs text-gray-500")

            def create_admin():
                if password_input.value != confirmation_input.value:
                    ui.notify(
                        "Les deux mots de passe ne correspondent pas.",
                        type="warning",
                    )
                    return

                email = normalize_email(email_input.value)

                if "@" not in email:
                    ui.notify(
                        "L’adresse courriel semble invalide.",
                        type="warning",
                    )
                    return

                try:
                    password_hash = hash_password(password_input.value or "")
                    user = create_first_admin(
                        name_input.value,
                        email,
                        password_hash,
                    )
                except ValueError as error:
                    ui.notify(str(error), type="warning")
                    return

                set_authenticated_user(user["id"])
                ui.notify(
                    "Administrateur créé. Bienvenue dans JF Apps.",
                    type="positive",
                )
                ui.navigate.to("/?tab=portail")

            confirmation_input.on("keydown.enter", create_admin)
            ui.button(
                "Créer l’administrateur",
                icon="admin_panel_settings",
                on_click=create_admin,
            ).props("color=primary").classes("w-full mt-2")


def show_login():
    apply_theme()

    with ui.column().classes(
        "w-full max-w-md mx-auto px-4 py-8 gap-4"
    ):
        with ui.card().classes("w-full p-6"):
            ui.label("JF Apps").classes("text-3xl font-bold text-center")
            ui.label(
                "Portail de mes applications personnelles"
            ).classes("text-center text-gray-600")

            email_input = ui.input(
                label="Adresse courriel"
            ).props(
                "type=email autofocus autocomplete=username"
            ).classes("w-full mt-4")
            password_input = ui.input(
                label="Mot de passe",
                password=True,
                password_toggle_button=True,
            ).props(
                "autocomplete=current-password"
            ).classes("w-full")

            login_error = ui.label("").classes(
                "text-sm text-negative min-h-[20px]"
            )

            def try_login():
                login_error.set_text("")

                user = authenticate(
                    email_input.value,
                    password_input.value,
                )

                if user is None:
                    message = (
                        "Adresse courriel ou mot de passe incorrect."
                    )
                    login_error.set_text(message)
                    ui.notify(message, type="negative")
                    password_input.value = ""
                    password_input.update()
                    return

                ui.navigate.to("/?tab=portail")

            email_input.on(
                "keydown.enter",
                lambda: password_input.run_method("focus"),
            )
            password_input.on("keydown.enter", try_login)
            ui.button(
                "Se connecter",
                icon="login",
                on_click=try_login,
            ).props("color=primary").classes("w-full mt-2")


def show_portal(user):
    apply_theme()

    with page_container():
        with ui.card().classes("w-full p-6"):
            with ui.row().classes(
                "w-full items-start justify-between gap-3 flex-wrap"
            ):
                with ui.column().classes("gap-0"):
                    ui.label("JF Apps").classes("text-3xl font-bold")
                    ui.label(
                        f"Bonjour {user['display_name']}"
                    ).classes("text-gray-600")

                ui.button(
                    icon="logout",
                    on_click=logout,
                ).props("flat round").tooltip("Déconnexion")

            ui.separator().classes("my-2")

            ui.label("Applications").classes("text-lg font-bold")
            ui.button(
                "Liste d’épicerie",
                icon="shopping_cart",
                on_click=lambda: ui.navigate.to("/?tab=items"),
            ).classes("w-full")

            ui.label("Portail").classes("text-lg font-bold mt-3")
            ui.button(
                "Familles",
                icon="groups",
                on_click=lambda: ui.navigate.to("/?tab=familles"),
            ).classes("w-full")
            ui.button(
                "Mon compte",
                icon="account_circle",
                on_click=lambda: ui.navigate.to("/?tab=compte"),
            ).props("outline").classes("w-full")

            if user["is_admin"]:
                ui.button(
                    "Utilisateurs",
                    icon="manage_accounts",
                    on_click=lambda: ui.navigate.to("/?tab=utilisateurs"),
                ).props("outline").classes("w-full")


def ensure_valid_family(user_id):
    families = get_accessible_families(user_id)

    if not families:
        set_current_family_id(None)
        return False

    valid_ids = {family["id"] for family in families}
    current_family_id = get_current_family_id()

    if current_family_id not in valid_ids:
        set_current_family_id(families[0]["id"])

    return True


def show_no_family_message():
    with ui.card().classes("w-full p-6"):
        ui.label("Aucune famille accessible").classes("text-xl font-bold")
        ui.label(
            "Créez une famille ou demandez à l’administrateur "
            "de vous donner accès à une famille."
        )
        ui.button(
            "Gérer les familles",
            icon="groups",
            on_click=lambda: ui.navigate.to("/?tab=familles"),
        ).classes("mt-2")


def portal_header(title):
    with ui.row().classes(
        "w-full items-center justify-between gap-3"
    ):
        ui.button(
            icon="arrow_back",
            on_click=lambda: ui.navigate.to("/?tab=portail"),
        ).props("flat round").tooltip("Retour au portail")
        ui.label(title).classes("text-xl font-bold")
        ui.button(
            icon="logout",
            on_click=logout,
        ).props("flat round").tooltip("Déconnexion")


def application_header(active_tab):
    with ui.row().classes(
        "w-full items-center justify-between gap-3"
    ):
        ui.label("Liste d’épicerie").classes("text-2xl font-bold")
        ui.button(
            icon="settings",
            on_click=lambda: ui.navigate.to("/?tab=donnees"),
        ).props(
            "flat round color=primary"
            if active_tab == "donnees"
            else "flat round"
        ).tooltip("Données et sauvegarde")


def bottom_navigation(active_tab):
    with ui.footer().classes(
        "bg-gray-100 dark:bg-gray-900 border-t p-2"
    ):
        with ui.row().classes("w-full justify-around gap-1"):
            ui.button(
                "Items",
                icon="inventory_2",
                on_click=lambda: ui.navigate.to("/?tab=items"),
            ).props(
                "flat color=primary" if active_tab == "items" else "flat"
            )
            ui.button(
                "Besoins",
                icon="shopping_cart",
                on_click=lambda: ui.navigate.to("/?tab=besoins"),
            ).props(
                "flat color=primary"
                if active_tab == "besoins"
                else "flat"
            )
            ui.button(
                "Catégories",
                icon="category",
                on_click=lambda: ui.navigate.to("/?tab=categories"),
            ).props(
                "flat color=primary"
                if active_tab == "categories"
                else "flat"
            )
            ui.button(
                "Portail",
                icon="apps",
                on_click=lambda: ui.navigate.to("/?tab=portail"),
            ).props("flat")


@ui.page("/", title="JF Apps")
def index(tab="portail"):
    apply_theme()

    if needs_initial_admin_setup():
        show_first_admin_setup()
        return

    user = get_current_user()

    if user is None:
        show_login()
        return

    normalized_tab = (tab or "portail").strip().lower()

    if normalized_tab in PORTAL_TABS:
        show_portal(user)
        return

    if normalized_tab in FAMILY_TABS:
        set_current_tab("familles")
        with page_container():
            portal_header("Familles")
            families_panel()
        return

    if normalized_tab in USER_TABS:
        if not user["is_admin"]:
            ui.navigate.to("/?tab=portail")
            return

        set_current_tab("utilisateurs")
        with page_container():
            portal_header("Utilisateurs")
            users_panel(user)
        return

    if normalized_tab in ACCOUNT_TABS:
        set_current_tab("compte")
        with page_container():
            portal_header("Mon compte")
            account_panel(user)
        return

    if normalized_tab in BACKUP_TABS:
        normalized_tab = "donnees"

    if normalized_tab not in VALID_APP_TABS:
        normalized_tab = "items"

    set_current_tab(normalized_tab)

    with page_container():
        application_header(normalized_tab)

        if not ensure_valid_family(user["id"]):
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


init_db()

storage_secret = os.getenv("STORAGE_SECRET")

if not storage_secret:
    raise RuntimeError(
        "La variable d’environnement STORAGE_SECRET est obligatoire."
    )

ui.run(
    host="0.0.0.0",
    port=int(os.getenv("PORT", "8080")),
    storage_secret=storage_secret,
    reload=False,
)
