import os
from nicegui import ui

ui.label('Hello from Canner!')

port = int(os.getenv('PORT', 8080))
ui.run(host='0.0.0.0', port=port)
