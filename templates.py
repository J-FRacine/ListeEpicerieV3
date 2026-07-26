from nicegui import ui

from auth import get_current_user_id
from db import (
    add_template_item,
    apply_template_to_needs,
    create_template,
    create_template_from_needs,
    delete_template,
    get_accessible_families,
    get_items,
    get_template_items,
    get_templates,
    move_template_item,
    remove_template_item,
    update_template,
    update_template_item,
)
from state import (
    get_current_family_id,
    set_current_family_id,
)
from utils import ensure_family_selected


def _item_options(items):
    return {
        item["id"]: (
            f"{item['name']} — {item['store']} / {item['category']}"
        )
        for item in items
    }


def _summary_message(result):
    total = result["items_total"]
    added = result["items_added"]
    quantities = result["quantities_updated"]

    message = (
        f"{total} item traité" if total == 1 else f"{total} items traités"
    )
    message += (
        f", {added} ajouté aux besoins"
        if added == 1
        else f", {added} ajoutés aux besoins"
    )

    if quantities:
        message += (
            f", {quantities} quantité augmentée"
            if quantities == 1
            else f", {quantities} quantités augmentées"
        )

    return message + "."


def templates_panel():
    user_id = get_current_user_id()
    family_id = get_current_family_id()

    if user_id is None or not ensure_family_selected(family_id):
        return

    families = get_accessible_families(user_id)
    if not families:
        ui.label("Aucune famille accessible.").classes("text-orange-700")
        return

    family_by_name = {
        family["name"]: family["id"]
        for family in families
    }
    current_name = next(
        (
            name
            for name, accessible_id in family_by_name.items()
            if accessible_id == family_id
        ),
        list(family_by_name)[0],
    )

    ui.select(
        list(family_by_name),
        value=current_name,
        label="Famille",
        on_change=lambda event: (
            set_current_family_id(family_by_name[event.value]),
            ui.navigate.to("/?tab=modeles"),
        ),
    ).classes("w-full")

    with ui.row().classes(
        "w-full items-start justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Listes modèles").classes("text-2xl font-bold")
            ui.label(
                "Préparez des listes réutilisables et ajoutez-les "
                "aux besoins en une seule opération."
            ).classes("text-sm text-gray-500")

        ui.icon("playlist_add_check").classes("text-4xl text-primary")

    def open_create_dialog(from_needs=False):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-lg p-5"):
                ui.label(
                    "Créer depuis les besoins"
                    if from_needs
                    else "Nouvelle liste modèle"
                ).classes("text-xl font-bold")

                if from_needs:
                    ui.label(
                        "Tous les besoins actuels seront copiés dans "
                        "la nouvelle liste modèle."
                    ).classes("text-sm text-gray-500")

                name_input = ui.input(
                    label="Nom",
                    placeholder="Ex. Costco mensuel",
                ).classes("w-full")
                description_input = ui.textarea(
                    label="Description facultative",
                    placeholder="Ex. Produits achetés environ une fois par mois",
                ).props("autogrow").classes("w-full")

                def save():
                    try:
                        if from_needs:
                            create_template_from_needs(
                                user_id,
                                family_id,
                                name_input.value,
                                description_input.value,
                            )
                        else:
                            create_template(
                                user_id,
                                family_id,
                                name_input.value,
                                description_input.value,
                            )
                    except (ValueError, PermissionError) as error:
                        ui.notify(str(error), type="warning")
                        return

                    dialog.close()
                    render_templates.refresh()
                    ui.notify("Liste modèle créée.", type="positive")

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button(
                        "Créer",
                        icon="add",
                        on_click=save,
                    ).props("color=primary")

        dialog.open()

    with ui.row().classes("w-full gap-2 flex-wrap"):
        ui.button(
            "Nouvelle liste modèle",
            icon="add",
            on_click=lambda: open_create_dialog(False),
        ).props("color=primary")

        ui.button(
            "Créer depuis les besoins",
            icon="content_copy",
            on_click=lambda: open_create_dialog(True),
        ).props("outline color=primary")

        ui.button(
            "Recettes",
            icon="restaurant_menu",
            on_click=lambda: ui.navigate.to("/?tab=recettes"),
        ).props("flat color=primary")

    def open_edit_template(template):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-lg p-5"):
                ui.label("Modifier la liste modèle").classes(
                    "text-xl font-bold"
                )
                name_input = ui.input(
                    label="Nom",
                    value=template["name"],
                ).classes("w-full")
                description_input = ui.textarea(
                    label="Description facultative",
                    value=template["description"],
                ).props("autogrow").classes("w-full")

                def save():
                    try:
                        update_template(
                            user_id,
                            template["id"],
                            name_input.value,
                            description_input.value,
                        )
                    except (ValueError, PermissionError) as error:
                        ui.notify(str(error), type="warning")
                        return

                    dialog.close()
                    render_templates.refresh()
                    ui.notify("Liste modèle modifiée.", type="positive")

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button(
                        "Enregistrer",
                        icon="save",
                        on_click=save,
                    ).props("color=primary")

        dialog.open()

    def confirm_delete(template):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-md p-5"):
                ui.label("Supprimer la liste modèle?").classes(
                    "text-xl font-bold"
                )
                ui.label(
                    f"« {template['name']} » sera supprimée. "
                    "Les items eux-mêmes resteront dans l’application."
                ).classes("text-gray-600")

                def perform_delete():
                    try:
                        delete_template(user_id, template["id"])
                    except (ValueError, PermissionError) as error:
                        ui.notify(str(error), type="warning")
                        return

                    dialog.close()
                    render_templates.refresh()
                    ui.notify("Liste modèle supprimée.", type="positive")

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button(
                        "Supprimer",
                        icon="delete",
                        on_click=perform_delete,
                    ).props("color=negative")

        dialog.open()

    def open_quantity_dialog(line):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-sm p-5"):
                ui.label(line["name"]).classes("text-xl font-bold")
                quantity_input = ui.number(
                    label="Quantité dans la liste modèle",
                    value=line["quantity"],
                    min=1,
                    step=1,
                ).classes("w-full")

                def save():
                    try:
                        update_template_item(
                            user_id,
                            line["id"],
                            quantity_input.value,
                        )
                    except (ValueError, PermissionError) as error:
                        ui.notify(str(error), type="warning")
                        return

                    dialog.close()
                    render_templates.refresh()

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button(
                        "Enregistrer",
                        icon="save",
                        on_click=save,
                    ).props("color=primary")

        dialog.open()

    def move_line(line_id, direction):
        try:
            move_template_item(user_id, line_id, direction)
        except (ValueError, PermissionError) as error:
            ui.notify(str(error), type="warning")
            return
        render_templates.refresh()

    @ui.refreshable
    def render_templates():
        templates = get_templates(user_id, family_id)
        items = get_items(user_id, family_id)
        options = _item_options(items)

        if not templates:
            with ui.card().classes("w-full p-7 items-center text-center mt-3"):
                ui.icon("playlist_add").classes("text-5xl text-primary")
                ui.label("Aucune liste modèle").classes("text-xl font-bold")
                ui.label(
                    "Créez une liste vide ou copiez les besoins actuels."
                ).classes("text-gray-500")
            return

        for template in templates:
            template_id = template["id"]
            lines = get_template_items(user_id, template_id)
            item_count = len(lines)

            with ui.expansion(
                text=template["name"],
                caption=(
                    f"{item_count} item"
                    if item_count == 1
                    else f"{item_count} items"
                ),
                icon="checklist",
                value=False,
            ).props("expand-separator").classes(
                "w-full bg-white rounded-xl shadow-sm "
                "border border-gray-200 overflow-hidden mt-3"
            ):
                with ui.column().classes("w-full gap-3 px-2 pb-3"):
                    if template["description"]:
                        ui.label(template["description"]).classes(
                            "text-sm text-gray-600 whitespace-normal"
                        ).style("overflow-wrap:anywhere;")

                    with ui.row().classes(
                        "w-full items-center gap-1 flex-wrap"
                    ):
                        def apply_selected(selected=template):
                            try:
                                result = apply_template_to_needs(
                                    user_id,
                                    selected["id"],
                                )
                            except (ValueError, PermissionError) as error:
                                ui.notify(str(error), type="warning")
                                return

                            ui.notify(
                                _summary_message(result),
                                type="positive",
                                timeout=5000,
                            )

                        ui.button(
                            "Ajouter aux besoins",
                            icon="playlist_add_check",
                            on_click=apply_selected,
                        ).props("color=positive")

                        ui.button(
                            icon="edit",
                            on_click=lambda selected=template: (
                                open_edit_template(selected)
                            ),
                        ).props("flat round color=primary").tooltip(
                            "Modifier la liste modèle"
                        )

                        ui.button(
                            icon="delete",
                            on_click=lambda selected=template: (
                                confirm_delete(selected)
                            ),
                        ).props("flat round color=negative").tooltip(
                            "Supprimer la liste modèle"
                        )

                    if lines:
                        for index, line in enumerate(lines):
                            with ui.card().classes("w-full p-3 shadow-none"):
                                with ui.row().classes(
                                    "w-full items-center gap-2 flex-nowrap"
                                ):
                                    with ui.column().classes(
                                        "gap-0 grow min-w-0"
                                    ):
                                        ui.label(
                                            f"{line['name']} ({line['quantity']})"
                                            if line["quantity"] != 1
                                            else line["name"]
                                        ).classes(
                                            "font-bold whitespace-normal"
                                        ).style("overflow-wrap:anywhere;")

                                        ui.label(
                                            f"{line['store']} · {line['category']}"
                                        ).classes("text-xs text-gray-500")

                                        if line["note"]:
                                            ui.label(line["note"]).classes(
                                                "text-xs text-gray-600 "
                                                "whitespace-normal"
                                            ).style("overflow-wrap:anywhere;")

                                    with ui.row().classes(
                                        "items-center gap-0 shrink-0"
                                    ):
                                        ui.button(
                                            icon="arrow_upward",
                                            on_click=lambda line_id=line["id"]: (
                                                move_line(line_id, -1)
                                            ),
                                        ).props(
                                            "flat round dense"
                                        ).set_enabled(index > 0)

                                        ui.button(
                                            icon="arrow_downward",
                                            on_click=lambda line_id=line["id"]: (
                                                move_line(line_id, 1)
                                            ),
                                        ).props(
                                            "flat round dense"
                                        ).set_enabled(index < item_count - 1)

                                        ui.button(
                                            icon="edit",
                                            on_click=lambda selected=line: (
                                                open_quantity_dialog(selected)
                                            ),
                                        ).props(
                                            "flat round dense color=primary"
                                        ).tooltip("Modifier la quantité")

                                        def remove_selected(line_id=line["id"]):
                                            try:
                                                remove_template_item(
                                                    user_id,
                                                    line_id,
                                                )
                                            except (
                                                ValueError,
                                                PermissionError,
                                            ) as error:
                                                ui.notify(
                                                    str(error),
                                                    type="warning",
                                                )
                                                return
                                            render_templates.refresh()

                                        ui.button(
                                            icon="close",
                                            on_click=remove_selected,
                                        ).props(
                                            "flat round dense color=negative"
                                        ).tooltip("Retirer de la liste modèle")
                    else:
                        ui.label(
                            "Cette liste modèle ne contient encore aucun item."
                        ).classes("text-sm text-gray-500")

                    if options:
                        ui.separator()
                        ui.label("Ajouter un item existant").classes(
                            "font-bold"
                        )
                        with ui.row().classes(
                            "w-full items-end gap-2 flex-wrap"
                        ):
                            item_input = ui.select(
                                options=options,
                                label="Item",
                                with_input=True,
                            ).props(
                                "clearable use-input input-debounce=0"
                            ).classes("grow min-w-[230px]")

                            quantity_input = ui.number(
                                label="Quantité",
                                value=1,
                                min=1,
                                step=1,
                            ).classes("w-28")

                            def add_selected(
                                selected_template_id=template_id,
                                selected_item_input=item_input,
                                selected_quantity_input=quantity_input,
                            ):
                                if selected_item_input.value is None:
                                    ui.notify(
                                        "Choisissez un item.",
                                        type="warning",
                                    )
                                    return

                                try:
                                    add_template_item(
                                        user_id,
                                        selected_template_id,
                                        int(selected_item_input.value),
                                        selected_quantity_input.value,
                                    )
                                except (
                                    ValueError,
                                    PermissionError,
                                ) as error:
                                    ui.notify(str(error), type="warning")
                                    return

                                render_templates.refresh()

                            ui.button(
                                "Ajouter",
                                icon="add",
                                on_click=add_selected,
                            ).props("color=primary")
                    else:
                        ui.label(
                            "Créez d’abord des items dans la page Items."
                        ).classes("text-sm text-orange-700")

    render_templates()
