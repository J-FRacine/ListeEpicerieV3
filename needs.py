from collections import defaultdict

from nicegui import ui

from auth import get_current_user_id
from db import get_accessible_families, get_items, toggle_needed
from state import get_current_family_id, set_current_family_id
from utils import ensure_family_selected


def needs_panel():
    user_id = get_current_user_id()
    current_family_id = get_current_family_id()

    if user_id is None or not ensure_family_selected(current_family_id):
        return

    families = get_accessible_families(user_id)

    if not families:
        ui.label("Aucune famille accessible.").classes("text-orange-700")
        return

    family_dict = {family["name"]: family["id"] for family in families}
    current_family_name = next(
        (
            name
            for name, family_id in family_dict.items()
            if family_id == current_family_id
        ),
        list(family_dict.keys())[0],
    )

    ui.select(
        list(family_dict.keys()),
        value=current_family_name,
        label="Famille",
        on_change=lambda event: (
            set_current_family_id(family_dict[event.value]),
            ui.navigate.to("/?tab=besoins"),
        ),
    ).classes("w-full")

    ui.separator()
    ui.label("Besoins").classes("text-xl font-bold")

    items = get_items(user_id, current_family_id)
    needs = [item for item in items if item["needed"] == 1]

    if not needs:
        ui.label(
            "Aucun item n’est actuellement marqué comme besoin."
        ).classes("text-gray-500 mt-3")
        return

    needs_by_category = defaultdict(list)

    for item in needs:
        category_name = (
            item["category"].strip()
            if item.get("category")
            else "Sans catégorie"
        )
        needs_by_category[category_name].append(item)

    for category_name in sorted(
        needs_by_category.keys(),
        key=lambda category: category.casefold(),
    ):
        category_items = sorted(
            needs_by_category[category_name],
            key=lambda item: item["name"].strip().casefold(),
        )

        with ui.column().classes("w-full gap-1 mt-4"):
            ui.label(category_name).classes(
                "text-lg font-bold border-b border-gray-300 pb-1 w-full"
            )

            for item in category_items:
                with ui.row().classes(
                    "w-full items-center justify-between "
                    "bg-gray-100 rounded-lg px-3 py-2 mt-1 gap-2"
                ):
                    quantity = item.get("quantity", 1)
                    item_text = (
                        f"{item['name']} ({quantity})"
                        if quantity and quantity != 1
                        else item["name"]
                    )
                    ui.label(item_text).classes("font-bold")

                    def remove_need(item_id=item["id"]):
                        try:
                            toggle_needed(user_id, item_id)
                        except (ValueError, PermissionError) as error:
                            ui.notify(str(error), type="warning")
                            return
                        ui.navigate.to("/?tab=besoins")

                    ui.button(
                        icon="check",
                        on_click=remove_need,
                    ).props("flat round color=green").tooltip(
                        "Retirer de la liste des besoins"
                    )
