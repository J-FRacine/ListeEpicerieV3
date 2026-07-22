import os
from nicegui import ui, app
from db import (
    init_db,
    authenticate,
    get_categories,
    create_category,
    get_items,
    add_item,
    delete_item,
)

# Initialisation de la base
init_db()

# -----------------------------
#  SESSIONS UTILISATEURS
# -----------------------------

app.storage.secret = os.getenv("SESSION_SECRET", "dev-secret")


def require_login():
    """Redirige vers /login si l'utilisateur n'est pas connecté."""
    if not ui.get_session().get('user'):
        ui.navigate.to('/login')


# -----------------------------
#  PAGE LOGIN
# -----------------------------

@ui.page('/login')
def login_page():
    ui.label('Connexion').classes('text-2xl font-bold mb-4')

    email = ui.input('Email')
    password = ui.input('Mot de passe', password=True)

    def do_login():
        user = authenticate(email.value, password.value)
        if not user:
            ui.notify('Identifiants invalides', color='red')
            return

        ui.get_session()['user'] = user
        ui.notify(f'Bienvenue {user["email"]} !')

        if user['role'] == 'superadmin':
            ui.navigate.to('/admin')
        else:
            ui.navigate.to('/items')

    ui.button('Se connecter', on_click=do_login).classes('mt-4')


# -----------------------------
#  PAGE ADMIN (SUPERADMIN)
# -----------------------------

@ui.page('/admin')
def admin_page():
    require_login()

    user = ui.get_session()['user']
    if user['role'] != 'superadmin':
        ui.label("Accès refusé").classes('text-red-500')
        return

    ui.label('Administration — Catégories globales').classes('text-2xl font-bold mb-4')

    categories = get_categories()

    with ui.row():
        new_cat = ui.input('Nouvelle catégorie')
        ui.button(
            'Ajouter',
            on_click=lambda: (
                create_category(new_cat.value),
                ui.notify('Catégorie ajoutée'),
                ui.navigate.to('/admin')
            )
        )

    ui.separator()

    ui.label('Catégories existantes :').classes('text-xl mt-4')

    for c in categories:
        ui.label(f"- {c['name']}")

    ui.button(
        'Déconnexion',
        on_click=lambda: (
            ui.get_session().clear(),
            ui.navigate.to('/login')
        )
    ).classes('mt-6')


# -----------------------------
#  PAGE ITEMS (FAMILLE)
# -----------------------------

@ui.page('/items')
def items_page():
    require_login()

    user = ui.get_session()['user']
    family_id = user['family_id']

    ui.label('Liste d’épicerie familiale').classes('text-2xl font-bold mb-4')

    categories = get_categories()

    # Formulaire d'ajout
    with ui.row():
        item_name = ui.input('Nom de l’item')
        item_qty = ui.number('Quantité', value=1)
        item_cat = ui.select(
            {c['id']: c['name'] for c in categories},
            label='Catégorie'
        )
        ui.button(
            'Ajouter',
            on_click=lambda: (
                add_item(family_id, item_cat.value, item_name.value, item_qty.value),
                ui.notify('Item ajouté'),
                ui.navigate.to('/items')
            )
        )

    ui.separator()

    # Liste des items
    ui.label('Items de la famille :').classes('text-xl mt-4')

    items = get_items(family_id)

    for it in items:
        with ui.row().classes('items-center'):
            ui.label(f"{it['name']} ({it['quantity']}) — {it['category']}")
            ui.button(
                'Supprimer',
                color='red',
                on_click=lambda it_id=it['id']: (
                    delete_item(it_id, family_id),
                    ui.notify('Item supprimé'),
                    ui.navigate.to('/items')
                )
            )

    ui.button(
        'Déconnexion',
        on_click=lambda: (
            ui.get_session().clear(),
            ui.navigate.to('/login')
        )
    ).classes('mt-6')


# -----------------------------
#  PAGE RACINE
# -----------------------------

@ui.page('/')
def index_page():
    ui.navigate.to('/login')


# -----------------------------
#  RUN
# -----------------------------

port = int(os.getenv('PORT', 8080))
ui.run(host='0.0.0.0', port=port)
