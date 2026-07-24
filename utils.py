from nicegui import app, ui

from db import get_categories


def ensure_family_selected(current_family_id):
    if current_family_id is None:
        ui.notify(
            "Aucune famille sélectionnée.",
            type="warning",
        )
        ui.label(
            "⚠️ Choisissez ou créez une famille "
            "dans le portail."
        )
        return False

    return True


def ensure_categories_exist(user_id, family_id):
    categories = get_categories(
        user_id,
        family_id,
    )

    if not categories:
        ui.label(
            "⚠️ Cette famille ne contient encore "
            "aucune catégorie."
        ).classes("text-orange-700")

        ui.button(
            "Créer une catégorie",
            icon="add",
            on_click=lambda: ui.navigate.to(
                "/?tab=categories"
            ),
        ).props("flat color=primary")

        return False

    return True


def apply_theme():
    ui.colors(
        primary="#173553",
        secondary="#587b9e",
        accent="#bd9555",
        dark="#17212b",
        dark_page="#0d151d",
        positive="#2e7d5b",
        negative="#b54750",
        info="#3c7aa6",
        warning="#d18a32",
    )

    theme = app.storage.user.get(
        "theme",
        "light",
    )

    if theme == "dark":
        ui.dark_mode().enable()
    else:
        ui.dark_mode().disable()
