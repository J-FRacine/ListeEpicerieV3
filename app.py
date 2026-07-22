import os
from nicegui import ui
from db import init_db

ui.label('Hello from Canner!')

# Initialiser la base
init_db()

port = int(os.getenv('PORT', 8080))
ui.run(host='0.0.0.0', port=port)
