from nicegui import ui

def bottom_nav():
    with ui.footer().classes(
        "fixed bottom-0 w-full bg-gray-100 dark:bg-gray-800 p-2 flex justify-around shadow-inner"
    ):
        ui.button("Items", on_click=lambda: ui.navigate.to('/?tab=items'))
        ui.button("Besoins", on_click=lambda: ui.navigate.to('/?tab=besoins'))
        ui.button("Catégories", on_click=lambda: ui.navigate.to('/?tab=categories'))
        ui.button("Familles", on_click=lambda: ui.navigate.to('/?tab=families'))
        ui.button("Admin", on_click=lambda: ui.navigate.to('/?tab=admin'))
