from nicegui import ui

def jf_header():
    ui.dark_mode().auto()  # mode auto déplacé ici

    with ui.header().classes(
        "w-full bg-white dark:bg-gray-900 shadow-md p-3 flex flex-col items-center"
    ):
        ui.image('logo_jf.png').classes("w-12 h-12 mb-1")
        ui.label("JF Apps").classes("text-xl font-bold text-gray-800 dark:text-gray-200")
        ui.label("Liste d’achats — Portail sécurisé").classes(
            "text-sm text-gray-600 dark:text-gray-400"
        )
