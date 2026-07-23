from nicegui import ui
from nicegui import app

def apply_theme():
    theme = app.storage.user.get('theme', 'light')
    if theme == 'dark':
        ui.dark_mode().enable()
    else:
        ui.dark_mode().disable()
