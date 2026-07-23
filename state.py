from nicegui import app

# On stocke l’état dans app.storage.user pour qu’il survive aux reloads NiceGUI

# --- Famille active ---
if 'current_family_id' not in app.storage.user:
    app.storage.user['current_family_id'] = None

def get_current_family_id():
    return app.storage.user['current_family_id']

def set_current_family_id(fid):
    app.storage.user['current_family_id'] = fid


# --- Onglet actif ---
if 'current_tab' not in app.storage.user:
    app.storage.user['current_tab'] = 'items'

def get_current_tab():
    return app.storage.user['current_tab']

def set_current_tab(tab):
    app.storage.user['current_tab'] = tab


# --- Tri des items ---
if 'tri_mode_items' not in app.storage.user:
    app.storage.user['tri_mode_items'] = 'Alphabétique'

def get_tri_mode_items():
    return app.storage.user['tri_mode_items']

def set_tri_mode_items(mode):
    app.storage.user['tri_mode_items'] = mode


# --- Tri des besoins ---
if 'tri_mode_needs' not in app.storage.user:
    app.storage.user['tri_mode_needs'] = 'Alphabétique'

def get_tri_mode_needs():
    return app.storage.user['tri_mode_needs']

def set_tri_mode_needs(mode):
    app.storage.user['tri_mode_needs'] = mode
