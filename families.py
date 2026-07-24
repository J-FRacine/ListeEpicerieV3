from nicegui import ui

from auth import get_current_user_id
from db import (
    create_family_for_user,
    delete_family_for_user,
    get_accessible_families_with_stats,
    rename_family_for_user,
)
from state import get_current_family_id, set_current_family_id


def families_panel():
    user_id = get_current_user_id()

    if user_id is None:
        return

    families = get_accessible_families_with_stats(user_id)
    current_family_id = get_current_family_id()
    valid_family_ids = {family["id"] for family in families}

    if current_family_id not in valid_family_ids:
        current_family_id = families[0]["id"] if families else None
        set_current_family_id(current_family_id)

    family_options = {
        family["id"]: family["name"]
        for family in families
    }

    with ui.row().classes(
        "w-full items-start justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Familles").classes("text-2xl font-bold")
            ui.label(
                "Créez vos espaces et choisissez celui utilisé par les applications."
            ).classes("text-sm text-gray-500")

        family_count = len(families)
        ui.label(
            f"{family_count} famille"
            if family_count == 1
            else f"{family_count} familles"
        ).classes("text-sm bg-gray-100 rounded-full px-3 py-1")

    with ui.card().classes("w-full p-4"):
        ui.label("Créer une famille").classes("text-lg font-bold")

        with ui.row().classes("w-full items-end gap-2 flex-wrap"):
            new_family_input = ui.input(
                label="Nom de la nouvelle famille",
                placeholder="Ex. Maison ou Chalet",
            ).classes("grow min-w-[220px]")

            def add_family():
                try:
                    new_family_id = create_family_for_user(
                        user_id,
                        new_family_input.value,
                    )
                except (ValueError, PermissionError) as error:
                    ui.notify(str(error), type="warning")
                    return

                set_current_family_id(new_family_id)
                ui.notify("Famille créée et activée.", type="positive")
                ui.navigate.to("/?tab=familles")

            new_family_input.on("keydown.enter", add_family)
            ui.button(
                "Créer",
                icon="add",
                on_click=add_family,
            ).props("color=primary").classes("min-w-[120px]")

    if not families:
        with ui.card().classes("w-full p-6 items-center text-center"):
            ui.icon("groups").classes("text-4xl text-gray-400")
            ui.label("Aucune famille").classes("text-lg font-bold")
            ui.label("Créez votre première famille ci-dessus.").classes(
                "text-gray-500"
            )
        return

    with ui.card().classes("w-full p-4"):
        with ui.row().classes("w-full items-center gap-3"):
            ui.icon("check_circle").classes("text-3xl text-positive")
            with ui.column().classes("gap-0 grow"):
                ui.label("Famille active").classes("text-lg font-bold")
                ui.label(
                    "Cette famille sera utilisée par la liste d’épicerie."
                ).classes("text-sm text-gray-500")

        with ui.row().classes("w-full items-end gap-2 flex-wrap mt-2"):
            active_family_input = ui.select(
                family_options,
                value=current_family_id,
                label="Choisir la famille active",
            ).classes("grow min-w-[220px]")

            def activate_selected_family():
                if active_family_input.value is None:
                    ui.notify("Choisissez une famille.", type="warning")
                    return

                set_current_family_id(int(active_family_input.value))
                ui.notify("Famille active modifiée.", type="positive")
                ui.navigate.to("/?tab=familles")

            ui.button(
                "Activer",
                icon="check",
                on_click=activate_selected_family,
            ).props("color=positive").classes("min-w-[120px]")

        ui.button(
            "Ouvrir la liste d’épicerie",
            icon="shopping_cart",
            on_click=lambda: ui.navigate.to("/?tab=items"),
        ).props("flat color=primary").classes("mt-2")

    def open_rename_dialog(family):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-md p-5"):
                ui.label("Renommer la famille").classes("text-xl font-bold")
                family_name_input = ui.input(
                    label="Nom",
                    value=family["name"],
                ).classes("w-full")

                def save_family_name():
                    try:
                        rename_family_for_user(
                            user_id,
                            family["id"],
                            family_name_input.value,
                        )
                    except (ValueError, PermissionError) as error:
                        ui.notify(str(error), type="warning")
                        return

                    dialog.close()
                    ui.notify("Famille renommée.", type="positive")
                    ui.navigate.to("/?tab=familles")

                family_name_input.on("keydown.enter", save_family_name)

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button(
                        "Enregistrer",
                        icon="save",
                        on_click=save_family_name,
                    ).props("color=primary")

        dialog.open()

    def open_delete_dialog(family):
        remaining_family_ids = [
            other_family["id"]
            for other_family in families
            if other_family["id"] != family["id"]
        ]
        contains_data = (
            family["item_count"] > 0
            or family["category_count"] > 0
        )

        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-md p-5"):
                ui.label("Supprimer la famille").classes("text-xl font-bold")
                ui.label(
                    f"Supprimer définitivement « {family['name']} » ?"
                ).classes("font-bold")
                ui.label(
                    f"{family['category_count']} catégorie(s), "
                    f"{family['item_count']} item(s), dont "
                    f"{family['needed_count']} besoin(s), seront supprimés."
                ).classes("text-gray-600")

                confirmation = None

                if contains_data:
                    confirmation = ui.checkbox(
                        "Je comprends que les données de cette famille "
                        "seront supprimées."
                    ).classes("mt-2")

                def confirm_delete():
                    if confirmation is not None and not confirmation.value:
                        ui.notify(
                            "Cochez la confirmation avant de supprimer.",
                            type="warning",
                        )
                        return

                    try:
                        delete_family_for_user(user_id, family["id"])
                    except (ValueError, PermissionError) as error:
                        ui.notify(str(error), type="warning")
                        return

                    if get_current_family_id() == family["id"]:
                        set_current_family_id(
                            remaining_family_ids[0]
                            if remaining_family_ids
                            else None
                        )

                    dialog.close()
                    ui.notify("Famille supprimée.", type="positive")
                    ui.navigate.to("/?tab=familles")

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button(
                        "Supprimer",
                        icon="delete",
                        on_click=confirm_delete,
                    ).props("color=negative")

        dialog.open()

    ui.label("Familles accessibles").classes("text-lg font-bold mt-1")

    with ui.column().classes("w-full gap-2"):
        for family in families:
            is_active = family["id"] == current_family_id

            with ui.card().classes("w-full px-4 py-3"):
                with ui.row().classes(
                    "w-full items-center justify-between gap-3 flex-wrap"
                ):
                    with ui.row().classes(
                        "items-center gap-3 grow min-w-[190px]"
                    ):
                        ui.icon("group").classes("text-2xl text-primary")

                        with ui.column().classes("gap-1"):
                            with ui.row().classes("items-center gap-2"):
                                ui.label(family["name"]).classes(
                                    "font-bold text-base"
                                )
                                if is_active:
                                    ui.badge("Active").props("color=positive")

                            with ui.row().classes(
                                "items-center gap-2 flex-wrap"
                            ):
                                ui.label(
                                    f"{family['item_count']} item"
                                    if family["item_count"] == 1
                                    else f"{family['item_count']} items"
                                ).classes("text-sm text-gray-500")
                                ui.label("•").classes("text-gray-400")
                                ui.label(
                                    f"{family['needed_count']} besoin"
                                    if family["needed_count"] == 1
                                    else f"{family['needed_count']} besoins"
                                ).classes("text-sm text-gray-500")
                                ui.label("•").classes("text-gray-400")
                                ui.label(
                                    f"{family['member_count']} membre"
                                    if family["member_count"] == 1
                                    else f"{family['member_count']} membres"
                                ).classes("text-sm text-gray-500")

                    with ui.row().classes("items-center gap-0"):
                        if not is_active:
                            ui.button(
                                icon="check_circle",
                                on_click=lambda selected_id=family["id"]: (
                                    set_current_family_id(selected_id),
                                    ui.navigate.to("/?tab=familles"),
                                ),
                            ).props("flat round color=positive").tooltip(
                                "Activer"
                            )

                        if family["can_manage"]:
                            ui.button(
                                icon="edit",
                                on_click=lambda selected=family: (
                                    open_rename_dialog(selected)
                                ),
                            ).props("flat round color=primary").tooltip(
                                "Renommer"
                            )
                            ui.button(
                                icon="delete",
                                on_click=lambda selected=family: (
                                    open_delete_dialog(selected)
                                ),
                            ).props("flat round color=negative").tooltip(
                                "Supprimer"
                            )
