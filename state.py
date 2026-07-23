# IMPORTANT :
# On NE DOIT PAS accéder à app.storage.user ici,
# car NiceGUI n'est pas encore démarré au moment de l'import.

# On utilise des variables globales simples.
# Elles seront remplacées plus tard par app.storage.user
# mais seulement APRÈS le démarrage de NiceGUI.

current_family_id = None
current_tab = 'items'
tri_mode_items = 'Alphabétique'
tri_mode_needs = 'Alphabétique'

# Fonctions d'accès (compatibles avec le reste du code)

def get_current_family_id():
    return current_family_id

def set_current_family_id(fid):
    global current_family_id
    current_family_id = fid

def get_current_tab():
    return current_tab

def set_current_tab(tab):
    global current_tab
    current_tab = tab

def get_tri_mode_items():
    return tri_mode_items

def set_tri_mode_items(mode):
    global tri_mode_items
    tri_mode_items = mode

def get_tri_mode_needs():
    return tri_mode_needs

def set_tri_mode_needs(mode):
    global tri_mode_needs
    tri_mode_needs = mode
