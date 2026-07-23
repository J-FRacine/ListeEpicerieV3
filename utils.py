from nicegui import ui
from db import get_families, get_categories

def ensure_family_selected(current_family_id):
    families = get_families()
    if not families:
        ui.label("⚠️ Aucune famille trouvée. Allez dans l’onglet 'Familles' pour en créer une.")
        return None
    return current_family_id or families[0]['id']

def ensure_categories_exist():
    categories = get_categories()
    if not categories:
        ui.label("⚠️ Aucune catégorie trouvée. Allez dans l’onglet 'Catégories' pour en créer une.")
        return False
    return True
