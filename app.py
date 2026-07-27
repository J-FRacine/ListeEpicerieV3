from __future__ import annotations

import os
import traceback
from pathlib import Path

from nicegui import app, run, ui

from activity import activity_panel
from app_access import (
    get_user_app_access,
    init_app_access_schema,
    user_has_app_access,
)
from auth import (
    authenticate,
    clear_session,
    get_current_user,
    hash_password,
    normalize_email,
    set_authenticated_user,
)
from backup import backup_panel
from blood_pressure import (
    blood_pressure_panel,
    blood_pressure_portal_reminder,
)
from blood_pressure_data import (
    init_blood_pressure_schema,
)
from categories import categories_panel
from db import (
    create_first_admin,
    get_accessible_families,
    get_items,
    init_db,
    needs_initial_admin_setup,
)
from families import families_panel
from feedback import feedback_panel
from feedback_data import (
    count_feedback_attention,
    count_user_unread_feedback,
    init_feedback_schema,
)
from items import items_panel
from maintenance import maintenance_panel
from manual import manual_panel
from needs import needs_panel
from onboarding import getting_started_panel
from recipes import recipes_panel
from rpg_character import rpg_character_panel
from rpg_character_data import (
    init_rpg_character_schema,
)
from shared_library import shared_library_panel
from pwa import (
    configure_pwa,
    request_pwa_install,
)
from shopping import shopping_panel
from templates import templates_panel
from state import (
    get_current_family_id,
    set_current_family_id,
    set_current_tab,
)
from users import account_panel, users_panel
from utils import apply_theme


VALID_APP_TABS = {
    "items",
    "besoins",
    "categories",
    "modeles",
    "recettes",
    "bibliotheque",
    "activite",
    "donnees",
    "courses",
}
PORTAL_TABS = {"portail", "portal", "apps"}
FAMILY_TABS = {"familles", "families"}
USER_TABS = {"utilisateurs", "users"}
ACCOUNT_TABS = {"compte", "account"}
ACTIVITY_TABS = {
    "activite",
    "activité",
    "activity",
    "corbeille",
    "historique",
}
MAINTENANCE_TABS = {
    "maintenance",
    "entretien",
    "diagnostic",
}
MANUAL_TABS = {
    "manuel",
    "aide",
    "help",
    "guide",
}
GETTING_STARTED_TABS = {
    "demarrage",
    "démarrage",
    "commencer",
    "onboarding",
    "premiers-pas",
    "premiers_pas",
}
LIBRARY_TABS = {
    "bibliotheque",
    "bibliothèque",
    "library",
    "partage",
    "public",
}
TEMPLATE_TABS = {
    "modeles",
    "modèles",
    "modele",
    "modèle",
    "templates",
    "listes-modeles",
    "listes_modèles",
}
RECIPE_TABS = {
    "recettes",
    "recette",
    "recipes",
}
BACKUP_TABS = {
    "donnees",
    "sauvegarde",
    "backup",
    "admin",
}
SHOPPING_TABS = {
    "courses",
    "course",
    "magasin",
    "shopping",
}
BLOOD_PRESSURE_TABS = {
    "pression",
    "journal-pression",
    "journal_pression",
    "blood-pressure",
    "blood_pressure",
}
RPG_TABS = {
    "jdr",
    "personnages",
    "personnage",
    "characters",
    "character",
    "rpg",
    "ravenloft",
}
FEEDBACK_TABS = {
    "commentaires",
    "commentaire",
    "suggestions",
    "suggestion",
    "feedback",
    "avis",
}

BASE_DIR = Path(__file__).resolve().parent
LOGO_FILE = BASE_DIR / "logo_jf.png"
LOGO_URL = "/assets/logo_jf.png"

if LOGO_FILE.exists():
    app.add_static_file(
        url_path=LOGO_URL,
        local_file=str(LOGO_FILE),
        max_cache_age=3600,
    )

configure_pwa(BASE_DIR)


APP_CSS = r'''
:root {
    --jf-navy: #173553;
    --jf-navy-deep: #10263d;
    --jf-blue: #587b9e;
    --jf-blue-soft: #eaf1f7;
    --jf-gold: #bd9555;
    --jf-surface: rgba(255, 255, 255, 0.94);
    --jf-border: rgba(23, 53, 83, 0.12);
    --jf-text: #17212b;
    --jf-muted: #647484;
    --jf-shadow:
        0 16px 42px rgba(23, 53, 83, 0.10),
        0 2px 8px rgba(23, 53, 83, 0.06);
    --nicegui-default-padding: 1rem;
    --nicegui-default-gap: 1rem;
}

body {
    min-height: 100vh;
    color: var(--jf-text);
    background:
        radial-gradient(
            circle at 12% 0%,
            rgba(88, 123, 158, 0.16),
            transparent 32rem
        ),
        radial-gradient(
            circle at 95% 10%,
            rgba(189, 149, 85, 0.10),
            transparent 26rem
        ),
        linear-gradient(180deg, #f8fafc 0%, #eef3f7 100%);
    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

body.body--dark {
    --jf-surface: rgba(23, 33, 43, 0.94);
    --jf-border: rgba(255, 255, 255, 0.10);
    --jf-text: #eef4f8;
    --jf-muted: #a8b5c0;
    --jf-blue-soft: rgba(88, 123, 158, 0.18);
    background:
        radial-gradient(
            circle at 15% 0%,
            rgba(88, 123, 158, 0.20),
            transparent 32rem
        ),
        linear-gradient(180deg, #111b25 0%, #0d151d 100%);
    color: var(--jf-text);
}

.q-card {
    border: 1px solid var(--jf-border);
    border-radius: 18px;
    background: var(--jf-surface);
    box-shadow: var(--jf-shadow);
}

.q-btn {
    border-radius: 12px;
    font-weight: 650;
    letter-spacing: 0;
    text-transform: none;
}

.q-field__control {
    border-radius: 12px 12px 4px 4px;
}

.jf-page {
    width: 100%;
    max-width: 64rem;
    margin: 0 auto;
    padding: 1.25rem 1rem 6.5rem;
}

.jf-auth-page {
    position: fixed;
    inset: 0;
    z-index: 1;
    width: 100vw;
    min-height: 100vh;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow-y: auto;
    padding: 1.5rem 1rem;
}

.jf-auth-card {
    width: 100%;
    max-width: 30rem;
    padding: 1.5rem;
    overflow: hidden;
}

.jf-auth-logo {
    width: min(100%, 23rem);
    margin: 0 auto 0.25rem;
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid var(--jf-border);
}

.jf-auth-title {
    color: var(--jf-navy);
    font-size: 2rem;
    line-height: 1.1;
    font-weight: 800;
    text-align: center;
}

.body--dark .jf-auth-title {
    color: #dceaf5;
}

.jf-auth-subtitle {
    color: var(--jf-muted);
    text-align: center;
    line-height: 1.5;
}

.jf-brand-mark {
    width: 2.65rem;
    height: 2.65rem;
    flex: 0 0 auto;
    display: grid;
    place-items: center;
    border-radius: 50%;
    color: white;
    background:
        linear-gradient(
            145deg,
            var(--jf-navy) 0%,
            var(--jf-blue) 100%
        );
    box-shadow: 0 7px 18px rgba(23, 53, 83, 0.24);
    font-weight: 800;
    letter-spacing: -0.05em;
}

.jf-hero-card {
    padding: clamp(1.25rem, 3vw, 2rem);
    overflow: hidden;
    position: relative;
}

.jf-hero-card::after {
    content: "";
    position: absolute;
    width: 17rem;
    height: 17rem;
    right: -7rem;
    top: -9rem;
    border-radius: 50%;
    background: rgba(189, 149, 85, 0.10);
    pointer-events: none;
}

.jf-hero-logo {
    width: min(100%, 22rem);
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid var(--jf-border);
    box-shadow: 0 12px 28px rgba(23, 53, 83, 0.10);
}

.jf-eyebrow {
    color: var(--jf-gold);
    font-size: 0.76rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.jf-hero-title {
    color: var(--jf-navy);
    font-size: clamp(1.8rem, 5vw, 2.65rem);
    line-height: 1.1;
    font-weight: 850;
    letter-spacing: -0.035em;
}

.body--dark .jf-hero-title {
    color: #e2edf6;
}

.jf-muted {
    color: var(--jf-muted);
}

.jf-section-title {
    margin-top: 0.35rem;
    color: var(--jf-navy);
    font-size: 1.15rem;
    font-weight: 800;
}

.body--dark .jf-section-title {
    color: #dceaf5;
}

.jf-card-grid {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(min(100%, 15rem), 1fr));
    gap: 1rem;
    width: 100%;
}

.jf-action-card {
    width: 100%;
    min-height: 12rem;
    padding: 1.2rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition:
        transform 160ms ease,
        box-shadow 160ms ease,
        border-color 160ms ease;
}

.jf-action-card:hover {
    transform: translateY(-3px);
    border-color: rgba(23, 53, 83, 0.25);
    box-shadow:
        0 20px 46px rgba(23, 53, 83, 0.14),
        0 4px 10px rgba(23, 53, 83, 0.07);
}

.jf-action-icon {
    width: 3rem;
    height: 3rem;
    display: grid;
    place-items: center;
    border-radius: 14px;
    color: var(--jf-navy);
    background: var(--jf-blue-soft);
}

.jf-action-title {
    color: var(--jf-navy);
    font-size: 1.12rem;
    font-weight: 800;
}

.jf-action-card-disabled {
    opacity: 0.78;
}

.jf-action-card-disabled:hover {
    transform: none;
    border-color: var(--jf-border);
    box-shadow: var(--jf-shadow);
}

.jf-card-badge {
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    color: var(--jf-navy);
    background: var(--jf-blue-soft);
    font-size: 0.72rem;
    font-weight: 800;
}

.jf-section-description {
    margin-top: -0.55rem;
    color: var(--jf-muted);
    font-size: 0.88rem;
}

.body--dark .jf-action-title {
    color: #e2edf6;
}

.jf-topbar {
    width: 100%;
    padding: 0.75rem 0.9rem;
    border-radius: 16px;
}

.jf-topbar-title {
    color: var(--jf-navy);
    font-size: 1.2rem;
    font-weight: 800;
}

.body--dark .jf-topbar-title {
    color: #e2edf6;
}

.jf-app-header {
    width: 100%;
    padding: 0.85rem 1rem;
    border: 1px solid var(--jf-border);
    border-radius: 17px;
    background: var(--jf-surface);
    box-shadow: 0 8px 24px rgba(23, 53, 83, 0.07);
}

.jf-app-title {
    color: var(--jf-navy);
    font-size: 1.35rem;
    line-height: 1.1;
    font-weight: 850;
}

.body--dark .jf-app-title {
    color: #e2edf6;
}

.jf-footer {
    padding: 0.45rem max(0.35rem, env(safe-area-inset-right))
        calc(0.45rem + env(safe-area-inset-bottom))
        max(0.35rem, env(safe-area-inset-left));
    border-top: 1px solid var(--jf-border);
    background: rgba(248, 250, 252, 0.94);
    backdrop-filter: blur(14px);
    box-shadow: 0 -6px 22px rgba(23, 53, 83, 0.07);
}

.body--dark .jf-footer {
    background: rgba(17, 27, 37, 0.94);
}

.jf-nav-button {
    min-width: 5rem;
    padding: 0.35rem 0.5rem;
    color: var(--jf-muted);
}

.jf-nav-active {
    color: white !important;
    background: var(--jf-navy) !important;
    box-shadow: 0 7px 16px rgba(23, 53, 83, 0.20);
}

.jf-nav-active .q-btn__content,
.jf-nav-active .q-icon,
.jf-nav-active .block {
    color: white !important;
}

.jf-status-chip {
    display: inline-flex;
    width: fit-content;
    align-items: center;
    gap: 0.35rem;
    padding: 0.35rem 0.65rem;
    color: var(--jf-navy);
    background: var(--jf-blue-soft);
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 700;
}

.body--dark .jf-status-chip {
    color: #dceaf5;
}

@media (max-width: 640px) {
    .jf-page {
        padding-top: 0.75rem;
    }

    .jf-auth-page {
        align-items: flex-start;
        padding-top: 1rem;
    }

    .jf-auth-card {
        padding: 1.15rem;
    }

    .jf-hero-card {
        text-align: center;
    }

    .jf-hero-logo {
        margin: 0 auto;
    }

    .jf-action-card {
        min-height: 10.5rem;
    }

    .jf-footer .q-btn__content {
        gap: 0.15rem;
    }

    .jf-nav-button {
        min-width: auto;
        font-size: 0.75rem;
    }
}
'''

ui.add_css(APP_CSS, shared=True)


def page_container():
    return ui.column().classes("jf-page gap-4")


def brand_mark():
    with ui.element("div").classes("jf-brand-mark"):
        ui.label("JF")


def brand_logo(classes=""):
    if LOGO_FILE.exists():
        return ui.image(LOGO_URL).props(
            'fit="contain" alt="Logo Jean-François"'
        ).classes(classes)

    with ui.element("div").classes(
        f"jf-brand-mark {classes}"
    ):
        ui.label("JF")

    return None


def logout():
    clear_session()
    ui.navigate.to("/")


def _create_first_admin_blocking(
    display_name,
    email,
    password,
):
    password_hash = hash_password(password)
    return create_first_admin(
        display_name,
        email,
        password_hash,
    )


def auth_brand():
    with ui.column().classes(
        "w-full items-center gap-2"
    ):
        brand_logo("jf-auth-logo")
        ui.label("JF Apps").classes("jf-auth-title")
        ui.label(
            "Un portail personnel, simple et partagé."
        ).classes("jf-auth-subtitle")


def show_first_admin_setup():
    apply_theme()

    with ui.element("div").classes("jf-auth-page"):
        with ui.card().classes("jf-auth-card"):
            auth_brand()

            ui.separator().classes("my-3")

            ui.label("Configuration initiale").classes(
                "text-2xl font-bold"
            )
            ui.label(
                "Créez le premier administrateur du portail. "
                "Toutes les familles existantes lui seront attribuées."
            ).classes("jf-muted")

            name_input = ui.input(
                label="Votre nom"
            ).props(
                "autofocus autocomplete=name"
            ).classes("w-full mt-2")

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
                "Le mot de passe doit contenir au moins "
                "10 caractères."
            ).classes("text-xs jf-muted")

            status_label = ui.label("").classes(
                "text-sm min-h-[22px]"
            )

            create_button = None

            async def create_admin():
                nonlocal create_button

                status_label.set_text("")
                status_label.classes(
                    replace=(
                        "text-sm min-h-[22px] "
                        "text-gray-600"
                    )
                )

                display_name = (
                    name_input.value or ""
                ).strip()
                email = normalize_email(
                    email_input.value
                )
                password = password_input.value or ""
                confirmation = (
                    confirmation_input.value or ""
                )

                if not display_name:
                    status_label.set_text(
                        "Votre nom est obligatoire."
                    )
                    status_label.classes(
                        replace=(
                            "text-sm min-h-[22px] "
                            "text-negative"
                        )
                    )
                    name_input.run_method("focus")
                    return

                if (
                    "@" not in email
                    or email.startswith("@")
                    or email.endswith("@")
                ):
                    status_label.set_text(
                        "L’adresse courriel semble invalide."
                    )
                    status_label.classes(
                        replace=(
                            "text-sm min-h-[22px] "
                            "text-negative"
                        )
                    )
                    email_input.run_method("focus")
                    return

                if password != confirmation:
                    status_label.set_text(
                        "Les deux mots de passe "
                        "ne correspondent pas."
                    )
                    status_label.classes(
                        replace=(
                            "text-sm min-h-[22px] "
                            "text-negative"
                        )
                    )
                    confirmation_input.run_method(
                        "focus"
                    )
                    return

                if len(password) < 10:
                    status_label.set_text(
                        "Le mot de passe doit contenir "
                        "au moins 10 caractères."
                    )
                    status_label.classes(
                        replace=(
                            "text-sm min-h-[22px] "
                            "text-negative"
                        )
                    )
                    password_input.run_method("focus")
                    return

                if create_button is not None:
                    create_button.disable()

                status_label.set_text(
                    "Création de l’administrateur "
                    "en cours…"
                )
                status_label.classes(
                    replace=(
                        "text-sm min-h-[22px] "
                        "text-primary"
                    )
                )

                try:
                    user = await run.io_bound(
                        _create_first_admin_blocking,
                        display_name,
                        email,
                        password,
                    )

                    set_authenticated_user(user["id"])

                    status_label.set_text(
                        "Administrateur créé. "
                        "Ouverture du portail…"
                    )
                    status_label.classes(
                        replace=(
                            "text-sm min-h-[22px] "
                            "text-positive"
                        )
                    )

                    ui.notify(
                        "Administrateur créé. "
                        "Bienvenue dans JF Apps.",
                        type="positive",
                    )
                    ui.navigate.to("/?tab=portail")

                except ValueError as error:
                    status_label.set_text(str(error))
                    status_label.classes(
                        replace=(
                            "text-sm min-h-[22px] "
                            "text-negative"
                        )
                    )
                    ui.notify(
                        str(error),
                        type="negative",
                    )

                except Exception as error:
                    traceback.print_exc()
                    message = (
                        "La création a échoué : "
                        f"{type(error).__name__}: {error}"
                    )
                    status_label.set_text(message)
                    status_label.classes(
                        replace=(
                            "text-sm min-h-[22px] "
                            "text-negative"
                        )
                    )
                    ui.notify(
                        "La création a échoué. "
                        "Le détail est affiché sous "
                        "le formulaire et dans Canner.",
                        type="negative",
                        timeout=8000,
                    )

                finally:
                    if create_button is not None:
                        create_button.enable()

            confirmation_input.on(
                "keydown.enter",
                create_admin,
            )

            create_button = ui.button(
                "Créer l’administrateur",
                icon="admin_panel_settings",
                on_click=create_admin,
            ).props(
                "color=primary size=lg"
            ).classes("w-full mt-2")


def show_login():
    apply_theme()

    with ui.element("div").classes("jf-auth-page"):
        with ui.card().classes("jf-auth-card"):
            auth_brand()

            ui.separator().classes("my-3")

            ui.label("Connexion").classes(
                "text-2xl font-bold text-center"
            )
            ui.label(
                "Retrouvez vos applications et "
                "vos listes partagées."
            ).classes("jf-auth-subtitle")

            email_input = ui.input(
                label="Adresse courriel"
            ).props(
                "type=email autofocus "
                "autocomplete=username"
            ).classes("w-full mt-3")

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
                        "Adresse courriel ou "
                        "mot de passe incorrect."
                    )
                    login_error.set_text(message)
                    ui.notify(
                        message,
                        type="negative",
                    )
                    password_input.value = ""
                    password_input.update()
                    return

                ui.navigate.to("/?tab=portail")

            email_input.on(
                "keydown.enter",
                lambda: password_input.run_method(
                    "focus"
                ),
            )
            password_input.on(
                "keydown.enter",
                try_login,
            )

            ui.button(
                "Se connecter",
                icon="login",
                on_click=try_login,
            ).props(
                "color=primary size=lg"
            ).classes("w-full mt-2")


def portal_action_card(
    *,
    title,
    description,
    icon,
    action_label,
    on_click=None,
    color="primary",
    badge=None,
    enabled=True,
):
    card_classes = (
        "jf-action-card"
        if enabled
        else (
            "jf-action-card "
            "jf-action-card-disabled"
        )
    )

    with ui.card().classes(card_classes):
        with ui.column().classes("gap-3"):
            with ui.row().classes(
                "w-full items-start "
                "justify-between gap-2"
            ):
                with ui.element("div").classes(
                    "jf-action-icon"
                ):
                    ui.icon(icon).classes(
                        "text-2xl"
                    )

                if badge:
                    ui.label(
                        badge
                    ).classes(
                        "jf-card-badge"
                    )

            with ui.column().classes("gap-1"):
                ui.label(title).classes(
                    "jf-action-title"
                )
                ui.label(description).classes(
                    "text-sm jf-muted"
                )

        if enabled:
            ui.button(
                action_label,
                icon="arrow_forward",
                on_click=on_click,
            ).props(
                f"flat color={color}"
            ).classes("self-start")
        else:
            ui.button(
                action_label,
                icon="schedule",
            ).props(
                "flat disable"
            ).classes("self-start")


def portal_section(
    title,
    description,
):
    ui.label(title).classes(
        "jf-section-title"
    )
    ui.label(description).classes(
        "jf-section-description"
    )


def show_portal(user):
    apply_theme()

    allowed_app_keys = (
        get_user_app_access(
            user["id"]
        )
    )

    try:
        unread_feedback_count = (
            count_user_unread_feedback(
                user["id"]
            )
        )
    except Exception:
        unread_feedback_count = 0

    try:
        feedback_attention_count = (
            count_feedback_attention()
            if user["is_admin"]
            else 0
        )
    except Exception:
        feedback_attention_count = 0

    with page_container():
        with ui.card().classes("jf-hero-card"):
            with ui.row().classes(
                "w-full items-center justify-between "
                "gap-6 flex-wrap"
            ):
                brand_logo("jf-hero-logo")

                with ui.column().classes(
                    "grow gap-2 min-w-[220px]"
                ):
                    ui.label(
                        "PORTAIL PERSONNEL"
                    ).classes("jf-eyebrow")

                    ui.label(
                        f"Bonjour {user['display_name']}"
                    ).classes("jf-hero-title")

                    ui.label(
                        "Vos applications, vos familles et "
                        "vos données au même endroit."
                    ).classes(
                        "text-base jf-muted max-w-xl"
                    )

                    with ui.row().classes(
                        "items-center gap-2 flex-wrap mt-1"
                    ):
                        with ui.element("div").classes(
                            "jf-status-chip"
                        ):
                            ui.icon(
                                "verified_user"
                            ).classes("text-base")
                            ui.label(
                                "Portail sécurisé"
                            )

                        if user["is_admin"]:
                            with ui.element(
                                "div"
                            ).classes(
                                "jf-status-chip"
                            ):
                                ui.icon(
                                    "admin_panel_settings"
                                ).classes("text-base")
                                ui.label(
                                    "Administrateur"
                                )

                    if (
                        "blood_pressure"
                        in allowed_app_keys
                    ):
                        blood_pressure_portal_reminder(
                            user["id"]
                        )

            with ui.row().classes(
                "w-full justify-end gap-1 mt-2 flex-wrap"
            ):
                ui.button(
                    "Installer JF Apps",
                    icon="install_mobile",
                    on_click=request_pwa_install,
                ).props("flat color=primary")

                ui.button(
                    "Mon compte",
                    icon="account_circle",
                    on_click=lambda: ui.navigate.to(
                        "/?tab=compte"
                    ),
                ).props("flat color=primary")

                ui.button(
                    icon="logout",
                    on_click=logout,
                ).props("flat round").tooltip(
                    "Déconnexion"
                )

        accessible_families = get_accessible_families(
            user["id"]
        )

        if (
            "grocery" in allowed_app_keys
            and not accessible_families
        ):
            with ui.card().classes(
                "w-full p-5 border-l-4 border-primary"
            ):
                with ui.row().classes(
                    "w-full items-start gap-3 flex-nowrap"
                ):
                    ui.icon("group_add").classes(
                        "text-4xl text-primary shrink-0"
                    )
                    with ui.column().classes("gap-1 grow min-w-0"):
                        ui.label(
                            "Première étape : créez votre famille"
                        ).classes("text-xl font-bold")
                        ui.label(
                            "La famille est votre espace de travail, même si "
                            "vous utilisez JF Apps seul. Elle doit être créée "
                            "avant d’ajouter des items, des besoins, des listes "
                            "modèles ou des recettes."
                        ).classes("text-sm jf-muted")
                        with ui.row().classes("gap-2 flex-wrap mt-2"):
                            ui.button(
                                "Créer ma première famille",
                                icon="groups",
                                on_click=lambda: ui.navigate.to(
                                    "/?tab=familles"
                                ),
                            ).props("color=primary")
                            ui.button(
                                "Voir le guide de démarrage",
                                icon="help_outline",
                                on_click=lambda: ui.navigate.to(
                                    "/?tab=demarrage"
                                ),
                            ).props("outline color=primary")

        portal_section(
            "Applications",
            (
                "Les grandes applications de JF Apps. "
                "Les outils propres à l’épicerie se trouvent "
                "maintenant à l’intérieur de cette application."
            ),
        )

        with ui.element("div").classes(
            "jf-card-grid"
        ):
            visible_app_count = 0

            if "grocery" in allowed_app_keys:
                visible_app_count += 1
                portal_action_card(
                    title="Liste d’épicerie",
                    description=(
                        "Gérez les items, besoins, magasins, "
                        "catégories, modèles et recettes."
                    ),
                    icon="shopping_cart",
                    action_label="Ouvrir",
                    on_click=lambda: ui.navigate.to(
                        "/?tab=items"
                    ),
                )

            if "blood_pressure" in allowed_app_keys:
                visible_app_count += 1
                portal_action_card(
                    title="Journal de pression",
                    description=(
                        "Consignez vos mesures privées "
                        "et produisez un rapport PDF."
                    ),
                    icon="monitor_heart",
                    action_label="Ouvrir",
                    badge="App 2",
                    on_click=lambda: ui.navigate.to(
                        "/?tab=pression"
                    ),
                )

            if "finances" in allowed_app_keys:
                visible_app_count += 1
                portal_action_card(
                    title="Finances",
                    description=(
                        "Suivez manuellement les revenus, "
                        "dépenses, budgets et transactions récurrentes."
                    ),
                    icon="account_balance_wallet",
                    action_label="Bientôt",
                    badge="App 3",
                    enabled=False,
                )

            if "rpg" in allowed_app_keys:
                visible_app_count += 1
                portal_action_card(
                    title="Personnages JDR",
                    description=(
                        "Créez et utilisez vos feuilles privées "
                        "Pathfinder dans l’univers Ravenloft."
                    ),
                    icon="casino",
                    action_label="Ouvrir",
                    badge="App 4",
                    on_click=lambda: ui.navigate.to(
                        "/?tab=jdr"
                    ),
                )

            if visible_app_count == 0:
                with ui.card().classes(
                    "jf-action-card"
                ):
                    with ui.element(
                        "div"
                    ).classes(
                        "jf-action-icon"
                    ):
                        ui.icon(
                            "apps_outage"
                        ).classes(
                            "text-2xl"
                        )

                    ui.label(
                        "Aucune application attribuée"
                    ).classes(
                        "jf-action-title"
                    )

                    ui.label(
                        "Un administrateur doit choisir "
                        "les applications auxquelles "
                        "votre compte peut accéder."
                    ).classes(
                        "text-sm jf-muted"
                    )

        portal_section(
            "Mon espace",
            (
                "Vos renseignements personnels, vos familles "
                "et les personnes avec qui vous collaborez."
            ),
        )

        with ui.element("div").classes(
            "jf-card-grid"
        ):
            portal_action_card(
                title="Mes familles",
                description=(
                    "Créez une famille, choisissez l’espace "
                    "actif et gérez les accès partagés."
                ),
                icon="groups",
                action_label="Gérer",
                on_click=lambda: ui.navigate.to(
                    "/?tab=familles"
                ),
            )

            portal_action_card(
                title="Mon compte",
                description=(
                    "Modifiez votre nom, votre courriel "
                    "et votre mot de passe."
                ),
                icon="account_circle",
                action_label="Ouvrir",
                on_click=lambda: ui.navigate.to(
                    "/?tab=compte"
                ),
            )

        portal_section(
            "Aide et démarrage",
            (
                "Comprenez l’organisation des données et "
                "retrouvez rapidement les instructions."
            ),
        )

        with ui.element("div").classes(
            "jf-card-grid"
        ):
            if "grocery" in allowed_app_keys:
                portal_action_card(
                    title="Commencer ici",
                    description=(
                        "Suivez le parcours visuel : famille, "
                        "magasins, catégories, items et utilisation."
                    ),
                    icon="rocket_launch",
                    action_label="Voir les étapes",
                    on_click=lambda: ui.navigate.to(
                        "/?tab=demarrage"
                    ),
                )

            if "blood_pressure" in allowed_app_keys:
                portal_action_card(
                    title="Démarrer le journal",
                    description=(
                        "Saisie, historique privé "
                        "et création du rapport PDF."
                    ),
                    icon="monitor_heart",
                    action_label="Ouvrir",
                    on_click=lambda: ui.navigate.to(
                        "/?tab=pression"
                    ),
                )

            portal_action_card(
                title="Commentaires et suggestions",
                description=(
                    "Signalez un problème, proposez une amélioration "
                    "et consultez les réponses reçues."
                ),
                icon="rate_review",
                action_label=(
                    "Voir mes commentaires"
                    if unread_feedback_count
                    else "Partager une idée"
                ),
                badge=(
                    (
                        f"{unread_feedback_count} "
                        + (
                            "réponse"
                            if unread_feedback_count == 1
                            else "réponses"
                        )
                    )
                    if unread_feedback_count
                    else None
                ),
                on_click=lambda: ui.navigate.to(
                    (
                        "/?tab=commentaires&section=mes"
                        if unread_feedback_count
                        else (
                            "/?tab=commentaires"
                            "&section=nouveau"
                        )
                    )
                ),
            )

            portal_action_card(
                title="Manuel d’utilisation",
                description=(
                    "Consultez les explications détaillées "
                    "pour toutes les fonctions disponibles."
                ),
                icon="help_center",
                action_label="Consulter",
                on_click=lambda: ui.navigate.to(
                    "/?tab=manuel"
                ),
            )

        if user["is_admin"]:
            portal_section(
                "Administration",
                (
                    "Fonctions réservées à la gestion "
                    "du portail et au diagnostic."
                ),
            )

            with ui.element("div").classes(
                "jf-card-grid"
            ):
                portal_action_card(
                    title="Utilisateurs",
                    description=(
                        "Créez les comptes et attribuez "
                        "les familles et applications."
                    ),
                    icon="manage_accounts",
                    action_label="Gérer",
                    on_click=lambda: ui.navigate.to(
                        "/?tab=utilisateurs"
                    ),
                )

                portal_action_card(
                    title="Commentaires reçus",
                    description=(
                        "Consultez les suggestions, répondez "
                        "aux utilisateurs et attribuez un statut."
                    ),
                    icon="mark_chat_unread",
                    action_label="Gérer",
                    badge=(
                        (
                            f"{feedback_attention_count} "
                            "à traiter"
                        )
                        if feedback_attention_count
                        else None
                    ),
                    on_click=lambda: ui.navigate.to(
                        "/?tab=commentaires"
                        "&section=gestion"
                    ),
                )

                portal_action_card(
                    title="Centre de maintenance",
                    description=(
                        "Diagnostiquez l’intégrité et "
                        "l’organisation de la base."
                    ),
                    icon="health_and_safety",
                    action_label="Diagnostiquer",
                    on_click=lambda: ui.navigate.to(
                        "/?tab=maintenance"
                    ),
                )


def ensure_valid_family(user_id):
    families = get_accessible_families(
        user_id
    )

    if not families:
        set_current_family_id(None)
        return False

    valid_ids = {
        family["id"]
        for family in families
    }

    current_family_id = (
        get_current_family_id()
    )

    if current_family_id not in valid_ids:
        set_current_family_id(
            families[0]["id"]
        )

    return True


def show_no_family_message():
    with ui.card().classes("w-full p-6"):
        ui.icon("group_off").classes(
            "text-4xl text-primary"
        )
        ui.label(
            "Aucune famille accessible"
        ).classes("text-xl font-bold")
        ui.label(
            "Créez une famille ou demandez à "
            "l’administrateur de vous donner accès."
        ).classes("jf-muted")
        with ui.row().classes("gap-2 flex-wrap mt-2"):
            ui.button(
                "Créer ou gérer les familles",
                icon="groups",
                on_click=lambda: ui.navigate.to(
                    "/?tab=familles"
                ),
            ).props("color=primary")
            ui.button(
                "Voir le guide de démarrage",
                icon="help_outline",
                on_click=lambda: ui.navigate.to(
                    "/?tab=demarrage"
                ),
            ).props("outline color=primary")


def show_app_access_denied(
    app_name,
):
    with ui.card().classes(
        "w-full p-6 border-l-4 border-negative"
    ):
        ui.icon(
            "lock"
        ).classes(
            "text-5xl text-negative"
        )
        ui.label(
            "Accès non autorisé"
        ).classes(
            "text-xl font-bold"
        )
        ui.label(
            f"Votre compte n’a pas accès à "
            f"l’application « {app_name} »."
        ).classes(
            "jf-muted"
        )
        ui.label(
            "Demandez à un administrateur du portail "
            "de modifier vos applications autorisées."
        ).classes(
            "text-sm jf-muted"
        )
        ui.button(
            "Retour au portail",
            icon="apps",
            on_click=lambda: ui.navigate.to(
                "/?tab=portail"
            ),
        ).props(
            "color=primary"
        ).classes(
            "mt-2"
        )


def portal_header(title):
    with ui.card().classes("jf-topbar"):
        with ui.row().classes(
            "w-full items-center justify-between "
            "gap-3"
        ):
            with ui.row().classes(
                "items-center gap-2 min-w-0"
            ):
                ui.button(
                    icon="arrow_back",
                    on_click=lambda: ui.navigate.to(
                        "/?tab=portail"
                    ),
                ).props("flat round").tooltip(
                    "Retour au portail"
                )

                brand_mark()

                ui.label(title).classes(
                    "jf-topbar-title truncate"
                )

            ui.button(
                icon="logout",
                on_click=logout,
            ).props("flat round").tooltip(
                "Déconnexion"
            )


def application_header(active_tab):
    with ui.element("div").classes(
        "jf-app-header"
    ):
        with ui.row().classes(
            "w-full items-center justify-between "
            "gap-3"
        ):
            with ui.row().classes(
                "items-center gap-3 min-w-0"
            ):
                brand_mark()

                with ui.column().classes(
                    "gap-0 min-w-0"
                ):
                    ui.label(
                        "Liste d’épicerie"
                    ).classes(
                        "jf-app-title truncate"
                    )
                    ui.label(
                        "Items et besoins partagés"
                    ).classes(
                        "text-xs jf-muted"
                    )

            with ui.row().classes(
                "items-center gap-0"
            ):
                planning_button = ui.button(
                    icon="menu_book",
                ).props(
                    "flat round color=primary"
                    if active_tab in {
                        "modeles",
                        "recettes",
                        "bibliotheque",
                    }
                    else "flat round"
                ).tooltip(
                    "Planification"
                )

                with planning_button:
                    with ui.menu().props(
                        "auto-close"
                    ):
                        ui.menu_item(
                            "Listes modèles",
                            lambda: ui.navigate.to(
                                "/?tab=modeles"
                            ),
                        )
                        ui.menu_item(
                            "Recettes",
                            lambda: ui.navigate.to(
                                "/?tab=recettes"
                            ),
                        )
                        ui.separator()
                        ui.menu_item(
                            "Bibliothèque partagée",
                            lambda: ui.navigate.to(
                                "/?tab=bibliotheque"
                            ),
                        )

                ui.button(
                    icon="history",
                    on_click=lambda: ui.navigate.to(
                        "/?tab=activite"
                    ),
                ).props(
                    "flat round color=primary"
                    if active_tab == "activite"
                    else "flat round"
                ).tooltip(
                    "Activité et corbeille"
                )

                ui.button(
                    icon="settings",
                    on_click=lambda: ui.navigate.to(
                        "/?tab=donnees"
                    ),
                ).props(
                    "flat round color=primary"
                    if active_tab == "donnees"
                    else "flat round"
                ).tooltip(
                    "Données et sauvegarde"
                )

                ui.button(
                    icon="help_outline",
                    on_click=lambda: ui.navigate.to(
                        "/?tab=manuel"
                    ),
                ).props("flat round").tooltip(
                    "Manuel d’utilisation"
                )

                ui.button(
                    icon="apps",
                    on_click=lambda: ui.navigate.to(
                        "/?tab=portail"
                    ),
                ).props("flat round").tooltip(
                    "Retour au portail"
                )


def bottom_navigation(
    active_tab,
    needs_count=0,
):
    needs_label = (
        f"Besoins {needs_count}"
        if needs_count > 0
        else "Besoins"
    )

    with ui.footer().classes("jf-footer"):
        with ui.row().classes(
            "w-full justify-around gap-1"
        ):
            items_button = ui.button(
                "Items",
                icon="inventory_2",
                on_click=lambda: ui.navigate.to(
                    "/?tab=items"
                ),
            ).props("flat").classes(
                "jf-nav-button"
            )

            needs_button = ui.button(
                needs_label,
                icon="shopping_cart",
                on_click=lambda: ui.navigate.to(
                    "/?tab=besoins"
                ),
            ).props("flat").classes(
                "jf-nav-button"
            )

            categories_button = ui.button(
                "Catégories",
                icon="category",
                on_click=lambda: ui.navigate.to(
                    "/?tab=categories"
                ),
            ).props("flat").classes(
                "jf-nav-button"
            )

            portal_button = ui.button(
                "Portail",
                icon="apps",
                on_click=lambda: ui.navigate.to(
                    "/?tab=portail"
                ),
            ).props("flat").classes(
                "jf-nav-button"
            )

            active_buttons = {
                "items": items_button,
                "besoins": needs_button,
                "categories": categories_button,
            }

            active_button = active_buttons.get(
                active_tab
            )

            if active_button is not None:
                active_button.classes(
                    add="jf-nav-active"
                )


@ui.page(
    "/",
    title="JF Apps",
    language="fr",
)
def index(
    tab="portail",
    section=None,
    quick=None,
    character=None,
):
    apply_theme()

    if needs_initial_admin_setup():
        show_first_admin_setup()
        return

    user = get_current_user()

    if user is None:
        show_login()
        return

    normalized_tab = (
        tab or "portail"
    ).strip().lower()

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

    if normalized_tab in GETTING_STARTED_TABS:
        if not user_has_app_access(
            user["id"],
            "grocery",
        ):
            with page_container():
                portal_header(
                    "Accès non autorisé"
                )
                show_app_access_denied(
                    "Liste d’épicerie"
                )
            return

        set_current_tab("demarrage")

        with page_container():
            portal_header("Commencer ici")
            getting_started_panel()

        return

    if normalized_tab in BLOOD_PRESSURE_TABS:
        if not user_has_app_access(
            user["id"],
            "blood_pressure",
        ):
            with page_container():
                portal_header(
                    "Accès non autorisé"
                )
                show_app_access_denied(
                    "Journal de pression"
                )
            return

        set_current_tab("pression")

        with page_container():
            portal_header(
                "Journal de pression"
            )
            quick_entry = (
                str(
                    quick
                    or ""
                ).strip().lower()
                in {
                    "1",
                    "true",
                    "oui",
                    "yes",
                }
            )

            blood_pressure_panel(
                user,
                initial_section=(
                    section
                    or "saisie"
                ),
                quick_entry=(
                    quick_entry
                ),
            )

        return

    if normalized_tab in RPG_TABS:
        if not user_has_app_access(
            user["id"],
            "rpg",
        ):
            with page_container():
                portal_header(
                    "Accès non autorisé"
                )
                show_app_access_denied(
                    "Personnages JDR"
                )
            return

        set_current_tab("jdr")

        with page_container():
            portal_header(
                "Personnages JDR"
            )
            rpg_character_panel(
                user,
                selected_character_id=(
                    character
                ),
                initial_section=(
                    section
                    or "identite"
                ),
            )

        return

    if normalized_tab in FEEDBACK_TABS:
        set_current_tab("commentaires")

        with page_container():
            portal_header(
                "Commentaires et suggestions"
            )
            feedback_panel(
                user,
                initial_section=(
                    section
                    or "mes"
                ),
            )

        return

    if normalized_tab in MANUAL_TABS:
        set_current_tab("manuel")

        with page_container():
            portal_header("Manuel d’utilisation")
            manual_panel()

        return

    if normalized_tab in MAINTENANCE_TABS:
        if not user["is_admin"]:
            ui.navigate.to("/?tab=portail")
            return

        set_current_tab("maintenance")

        with page_container():
            portal_header("Centre de maintenance")
            maintenance_panel()

        return

    if normalized_tab in ACTIVITY_TABS:
        normalized_tab = "activite"

    if normalized_tab in LIBRARY_TABS:
        normalized_tab = "bibliotheque"

    if normalized_tab in BACKUP_TABS:
        normalized_tab = "donnees"

    if normalized_tab in TEMPLATE_TABS:
        normalized_tab = "modeles"

    if normalized_tab in RECIPE_TABS:
        normalized_tab = "recettes"

    if normalized_tab in SHOPPING_TABS:
        normalized_tab = "courses"

    if normalized_tab not in VALID_APP_TABS:
        ui.navigate.to(
            "/?tab=portail"
        )
        return

    if not user_has_app_access(
        user["id"],
        "grocery",
    ):
        with page_container():
            portal_header(
                "Accès non autorisé"
            )
            show_app_access_denied(
                "Liste d’épicerie"
            )
        return

    set_current_tab(normalized_tab)

    # Le mode courses utilise volontairement un écran simplifié,
    # sans l'en-tête et la navigation habituels.
    if normalized_tab == "courses":
        with page_container():
            if not ensure_valid_family(user["id"]):
                show_no_family_message()
            else:
                shopping_panel()
        return

    needs_count = 0

    with page_container():
        application_header(normalized_tab)

        if not ensure_valid_family(user["id"]):
            show_no_family_message()
        else:
            current_family_id = get_current_family_id()

            try:
                family_items = get_items(
                    user["id"],
                    current_family_id,
                )
                needs_count = sum(
                    1
                    for item in family_items
                    if item["needed"] == 1
                )
            except (ValueError, PermissionError):
                needs_count = 0

            if normalized_tab == "items":
                items_panel()
            elif normalized_tab == "besoins":
                needs_panel()
            elif normalized_tab == "categories":
                categories_panel()
            elif normalized_tab == "modeles":
                templates_panel()
            elif normalized_tab == "recettes":
                recipes_panel()
            elif normalized_tab == "bibliotheque":
                shared_library_panel()
            elif normalized_tab == "activite":
                activity_panel()
            elif normalized_tab == "donnees":
                backup_panel()

    bottom_navigation(
        normalized_tab,
        needs_count,
    )


init_db()
init_app_access_schema()
init_blood_pressure_schema()
init_rpg_character_schema()
init_feedback_schema()

storage_secret = os.getenv("STORAGE_SECRET")

if not storage_secret:
    raise RuntimeError(
        "La variable d’environnement "
        "STORAGE_SECRET est obligatoire."
    )

ui.run(
    host="0.0.0.0",
    port=int(os.getenv("PORT", "8080")),
    storage_secret=storage_secret,
    reload=False,
)
