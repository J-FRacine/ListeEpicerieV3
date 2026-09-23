from __future__ import annotations

from nicegui import ui

from recipes_categories import (
    create_recipe_category,
    delete_recipe_category,
    delete_recipes_bulk,
    list_recipe_categories,
    recipe_category_options,
    rename_recipe_category,
)


def open_recipe_categories_dialog(*, user_id, family_id, on_close_refresh=None):
    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-3xl p-5"):
            with ui.row().classes("w-full items-center justify-between gap-2"):
                with ui.column().classes("gap-0"):
                    ui.label("Catégories de recettes").classes("text-xl font-bold")
                    ui.label(
                        "Créez des catégories principales et, au besoin, une seule couche de sous-catégories."
                    ).classes("text-sm text-gray-600")
                ui.button(icon="close", on_click=dialog.close).props("flat round")

            @ui.refreshable
            def render_categories():
                rows = list_recipe_categories(user_id, family_id)
                main_options = {0: "Catégorie principale"}
                main_options.update(
                    recipe_category_options(rows, main_only=True)
                )

                with ui.card().classes("w-full p-3 shadow-none bg-blue-50"):
                    ui.label("Ajouter une catégorie").classes("font-bold")
                    with ui.row().classes("w-full gap-2 items-end flex-wrap"):
                        name_input = ui.input(
                            label="Nom",
                            placeholder="Ex. Entrées, Desserts, Pain...",
                        ).classes("grow min-w-[220px]")
                        parent_input = ui.select(
                            main_options,
                            value=0,
                            label="Niveau",
                        ).props("outlined dense").classes("grow min-w-[220px]")

                        def add_category():
                            try:
                                create_recipe_category(
                                    user_id,
                                    family_id,
                                    name_input.value,
                                    None if parent_input.value in (None, 0, "0") else parent_input.value,
                                )
                            except (ValueError, PermissionError) as error:
                                ui.notify(str(error), type="warning")
                                return
                            render_categories.refresh()
                            ui.notify("Catégorie créée.", type="positive")

                        ui.button(
                            "Ajouter",
                            icon="add",
                            on_click=add_category,
                        ).props("color=primary")

                if not rows:
                    ui.label(
                        "Aucune catégorie de recette pour cette famille."
                    ).classes("text-sm text-gray-500")
                else:
                    for row in rows:
                        with ui.card().classes("w-full p-3 shadow-none"):
                            with ui.row().classes(
                                "w-full items-center gap-2 flex-nowrap"
                            ):
                                if row.get("parent_id") is not None:
                                    ui.icon("subdirectory_arrow_right").classes(
                                        "text-primary shrink-0"
                                    )
                                else:
                                    ui.icon("folder").classes(
                                        "text-primary shrink-0"
                                    )
                                with ui.column().classes("gap-0 grow min-w-0"):
                                    ui.label(row["category_path"]).classes(
                                        "font-bold whitespace-normal"
                                    )
                                    details = []
                                    if row.get("direct_recipe_count"):
                                        details.append(
                                            f"{row['direct_recipe_count']} recette(s)"
                                        )
                                    if row.get("child_count"):
                                        details.append(
                                            f"{row['child_count']} sous-catégorie(s)"
                                        )
                                    if details:
                                        ui.label(" · ".join(details)).classes(
                                            "text-xs text-gray-500"
                                        )

                                def rename(selected=row):
                                    with ui.dialog() as rename_dialog:
                                        with ui.card().classes("w-full max-w-md p-4"):
                                            ui.label("Renommer la catégorie").classes(
                                                "text-lg font-bold"
                                            )
                                            field = ui.input(
                                                label="Nom",
                                                value=selected["name"],
                                            ).classes("w-full")

                                            def save():
                                                try:
                                                    rename_recipe_category(
                                                        user_id,
                                                        selected["id"],
                                                        field.value,
                                                    )
                                                except (ValueError, PermissionError) as error:
                                                    ui.notify(
                                                        str(error),
                                                        type="warning",
                                                    )
                                                    return
                                                rename_dialog.close()
                                                render_categories.refresh()

                                            with ui.row().classes(
                                                "w-full justify-end gap-2"
                                            ):
                                                ui.button(
                                                    "Annuler",
                                                    on_click=rename_dialog.close,
                                                ).props("flat")
                                                ui.button(
                                                    "Enregistrer",
                                                    icon="save",
                                                    on_click=save,
                                                ).props("color=primary")
                                    rename_dialog.open()

                                def remove(selected=row):
                                    with ui.dialog() as confirm:
                                        with ui.card().classes("w-full max-w-md p-4"):
                                            ui.label(
                                                "Supprimer cette catégorie?"
                                            ).classes("text-lg font-bold")
                                            ui.label(
                                                "Les recettes ne seront pas supprimées; elles deviendront sans catégorie. "
                                                "Une catégorie contenant des sous-catégories doit d’abord être vidée de celles-ci."
                                            ).classes("text-sm text-gray-600")

                                            def perform():
                                                try:
                                                    delete_recipe_category(
                                                        user_id,
                                                        selected["id"],
                                                    )
                                                except (ValueError, PermissionError) as error:
                                                    ui.notify(
                                                        str(error),
                                                        type="warning",
                                                    )
                                                    return
                                                confirm.close()
                                                render_categories.refresh()
                                                ui.notify(
                                                    "Catégorie supprimée.",
                                                    type="positive",
                                                )

                                            with ui.row().classes(
                                                "w-full justify-end gap-2"
                                            ):
                                                ui.button(
                                                    "Annuler",
                                                    on_click=confirm.close,
                                                ).props("flat")
                                                ui.button(
                                                    "Supprimer",
                                                    icon="delete",
                                                    on_click=perform,
                                                ).props("color=negative")
                                    confirm.open()

                                ui.button(
                                    icon="edit",
                                    on_click=rename,
                                ).props("flat round dense color=primary").tooltip(
                                    "Renommer"
                                )
                                ui.button(
                                    icon="delete",
                                    on_click=remove,
                                ).props("flat round dense color=negative").tooltip(
                                    "Supprimer"
                                )

            render_categories()

            def close_and_refresh():
                dialog.close()
                if on_close_refresh:
                    on_close_refresh()

            with ui.row().classes("w-full justify-end mt-3"):
                ui.button(
                    "Fermer et actualiser",
                    icon="refresh",
                    on_click=close_and_refresh,
                ).props("color=primary")

    dialog.open()


def open_bulk_delete_dialog(*, user_id, family_id, on_deleted=None):
    from db import get_recipes

    recipes = get_recipes(user_id, family_id)
    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-3xl p-5"):
            ui.label("Supprimer plusieurs recettes").classes("text-xl font-bold")
            ui.label(
                "Cochez seulement les recettes à supprimer. Les items de la Liste d’épicerie ne seront pas supprimés."
            ).classes("text-sm text-gray-600")

            checkboxes = []
            selected_label = ui.label("0 recette sélectionnée").classes(
                "text-sm font-semibold"
            )

            def update_count(*_):
                total = sum(1 for _, checkbox in checkboxes if checkbox.value)
                selected_label.text = (
                    "1 recette sélectionnée"
                    if total == 1
                    else f"{total} recettes sélectionnées"
                )

            with ui.row().classes("w-full gap-2 flex-wrap"):
                def select_all():
                    for _, checkbox in checkboxes:
                        checkbox.value = True
                        checkbox.update()
                    update_count()

                def clear_all():
                    for _, checkbox in checkboxes:
                        checkbox.value = False
                        checkbox.update()
                    update_count()

                ui.button("Tout sélectionner", on_click=select_all).props(
                    "flat color=primary"
                )
                ui.button("Tout désélectionner", on_click=clear_all).props(
                    "flat color=primary"
                )

            with ui.scroll_area().classes("w-full h-80 border rounded-lg p-2"):
                if not recipes:
                    ui.label("Aucune recette à supprimer.").classes(
                        "text-sm text-gray-500"
                    )
                for recipe in recipes:
                    checkbox = ui.checkbox(recipe["name"], value=False)
                    checkbox.on_value_change(update_count)
                    checkboxes.append((int(recipe["id"]), checkbox))

            def request_delete():
                selected = [
                    recipe_id
                    for recipe_id, checkbox in checkboxes
                    if checkbox.value
                ]
                if not selected:
                    ui.notify(
                        "Sélectionnez au moins une recette.",
                        type="warning",
                    )
                    return

                with ui.dialog() as confirm:
                    with ui.card().classes("w-full max-w-md p-5"):
                        ui.label("Confirmer la suppression").classes(
                            "text-xl font-bold"
                        )
                        ui.label(
                            f"{len(selected)} recette(s) seront supprimée(s). "
                            "Cette action ne supprime pas les items de l’épicerie."
                        ).classes("text-sm text-gray-600")

                        def perform():
                            try:
                                deleted = delete_recipes_bulk(
                                    user_id,
                                    family_id,
                                    selected,
                                )
                            except (ValueError, PermissionError) as error:
                                ui.notify(str(error), type="warning")
                                return
                            confirm.close()
                            dialog.close()
                            if on_deleted:
                                on_deleted()
                            ui.notify(
                                f"{deleted} recette(s) supprimée(s).",
                                type="positive",
                            )

                        with ui.row().classes("w-full justify-end gap-2"):
                            ui.button(
                                "Annuler",
                                on_click=confirm.close,
                            ).props("flat")
                            ui.button(
                                "Supprimer",
                                icon="delete_sweep",
                                on_click=perform,
                            ).props("color=negative")
                confirm.open()

            with ui.row().classes("w-full justify-end gap-2 mt-3"):
                ui.button("Fermer", on_click=dialog.close).props("flat")
                ui.button(
                    "Supprimer la sélection",
                    icon="delete_sweep",
                    on_click=request_delete,
                ).props("color=negative")

    dialog.open()
