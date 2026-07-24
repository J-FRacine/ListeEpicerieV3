from nicegui import app, ui

from db import get_categories


def ensure_family_selected(current_family_id):
    if current_family_id is None:
        ui.notify(
            "Aucune famille sélectionnée.",
            type="warning",
        )
        ui.label(
            "⚠️ Choisissez ou créez une famille dans le portail."
        )
        return False

    return True


def ensure_categories_exist(user_id, family_id):
    categories = get_categories(user_id, family_id)

    if not categories:
        ui.label(
            "⚠️ Cette famille ne contient encore aucune catégorie."
        ).classes("text-orange-700")

        ui.button(
            "Créer une catégorie",
            icon="add",
            on_click=lambda: ui.navigate.to("/?tab=categories"),
        ).props("flat color=primary")

        return False

    return True


def apply_theme():
    theme = app.storage.user.get("theme", "light")

    if theme == "dark":
        ui.dark_mode().enable()
    else:
        ui.dark_mode().disable()
