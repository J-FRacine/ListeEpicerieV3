from nicegui import ui
from db import get_categories

def ensure_family_selected(current_family_id):
    print("DEBUG utils.ensure_family_selected() → entrée")
    print(f"DEBUG utils.ensure_family_selected() → current_family_id = {current_family_id}")

    if current_family_id is None:
        print("DEBUG utils.ensure_family_selected() → AUCUNE famille sélectionnée")
        ui.notify("DEBUG: aucune famille sélectionnée")
        ui.label("⚠️ Aucune famille sélectionnée. Choisissez-en une dans l’onglet Familles.")
        return False

    print("DEBUG utils.ensure_family_selected() → famille OK")
    return True


def ensure_categories_exist():
    print("DEBUG utils.ensure_categories_exist() → entrée")

    categories = get_categories()
    print(f"DEBUG utils.ensure_categories_exist() → catégories = {categories}")

    if not categories:
        print("DEBUG utils.ensure_categories_exist() → AUCUNE catégorie")
        ui.notify("DEBUG: aucune catégorie disponible")
        ui.label("⚠️ Aucune catégorie disponible. Ajoutez-en dans l’onglet Catégories.")
        return False

    print("DEBUG utils.ensure_categories_exist() → catégories OK")
    return True


def apply_theme():
    print("DEBUG utils.apply_theme() → entrée")

    # IMPORTANT :
    # On n'utilise plus app.storage.user ici,
    # car cela provoquait un crash avant ui.run().
    # On laisse simplement le thème par défaut.

    print("DEBUG utils.apply_theme() → thème = light (fixé par défaut)")
    ui.dark_mode().disable()
