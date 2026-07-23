from nicegui import ui
from nicegui import app
from db import get_categories

def ensure_family_selected(current_family_id):
    """Affiche un message si aucune famille n'est sélectionnée."""
    if current_family_id is None:
        ui.label("⚠️ Aucune famille sélectionnée. Choisissez-en une dans l’onglet Familles.")
        return False
    return True

def ensure_categories_exist():
    """Affiche un message si aucune catégorie n'existe."""
    categories = get_categories()
    if not categories:
        ui.label("⚠️ Aucune catégorie disponible. Ajoutez-en dans l’onglet Catégories.")
        return False
    return True

def apply_theme():
    """Applique le thème clair/sombre selon la préférence stockée."""
    theme = app.storage.user.get('theme', 'light')
    if theme == 'dark':
        ui.dark_mode().enable()
    else:
        ui.dark_mode().disable()
