from nicegui import ui

from db import (
    create_category,
    delete_category,
    get_categories_with_counts,
    merge_categories,
    rename_category,
)


def categories_panel():
    categories = get_categories_with_counts()

    # ---------------------------------------------------------
    # EN-TÊTE
    # ---------------------------------------------------------

    with ui.row().classes(
        "w-full items-start justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Catégories").classes("text-2xl font-bold")
            ui.label(
                "Classez les items et gardez la liste facile à parcourir."
            ).classes("text-sm text-gray-500")

        category_count = len(categories)
        ui.label(
            f"{category_count} catégorie"
            if category_count == 1
            else f"{category_count} catégories"
        ).classes(
            "text-sm bg-gray-100 rounded-full px-3 py-1"
        )

    # ---------------------------------------------------------
    # AJOUT RAPIDE
    # ---------------------------------------------------------

    with ui.card().classes("w-full p-4"):
        ui.label("Ajouter une catégorie").classes(
            "text-lg font-bold"
        )

        with ui.row().classes(
            "w-full items-end gap-2 flex-wrap"
        ):
            new_category_input = ui.input(
                label="Nom de la nouvelle catégorie",
                placeholder="Ex. Pharmacie",
            ).classes("grow min-w-[220px]")

            def add_category():
                try:
                    create_category(new_category_input.value)
                except ValueError as error:
                    ui.notify(str(error), type="warning")
                    return

                ui.notify("Catégorie ajoutée.", type="positive")
                ui.navigate.to("/?tab=categories")

            new_category_input.on(
                "keydown.enter",
                add_category,
            )

            ui.button(
                "Ajouter",
                icon="add",
                on_click=add_category,
            ).props("color=primary").classes("min-w-[120px]")

    # ---------------------------------------------------------
    # AUCUNE CATÉGORIE
    # ---------------------------------------------------------

    if not categories:
        with ui.card().classes(
            "w-full p-6 items-center text-center"
        ):
            ui.icon("category").classes(
                "text-4xl text-gray-400"
            )
            ui.label("Aucune catégorie").classes(
                "text-lg font-bold"
            )
            ui.label(
                "Ajoutez votre première catégorie ci-dessus."
            ).classes("text-gray-500")
        return

    # ---------------------------------------------------------
    # DIALOGUES
    # ---------------------------------------------------------

    def open_rename_dialog(category):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-md p-5"):
                ui.label("Renommer la catégorie").classes(
                    "text-xl font-bold"
                )

                name_input = ui.input(
                    label="Nom",
                    value=category["name"],
                ).classes("w-full")

                def save_name():
                    try:
                        rename_category(
                            category["id"],
                            name_input.value,
                        )
                    except ValueError as error:
                        ui.notify(str(error), type="warning")
                        return

                    dialog.close()
                    ui.notify(
                        "Catégorie renommée.",
                        type="positive",
                    )
                    ui.navigate.to("/?tab=categories")

                name_input.on("keydown.enter", save_name)

                with ui.row().classes(
                    "w-full justify-end gap-2 mt-3"
                ):
                    ui.button(
                        "Annuler",
                        on_click=dialog.close,
                    ).props("flat")

                    ui.button(
                        "Enregistrer",
                        icon="save",
                        on_click=save_name,
                    ).props("color=primary")

        dialog.open()

    def open_merge_dialog(category):
        destination_categories = {
            other_category["name"]: other_category["id"]
            for other_category in categories
            if other_category["id"] != category["id"]
        }

        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-md p-5"):
                ui.label("Fusionner la catégorie").classes(
                    "text-xl font-bold"
                )

                ui.label(
                    f"Les {category['item_count']} item(s) de "
                    f"« {category['name']} » seront déplacés."
                ).classes("text-gray-600")

                if not destination_categories:
                    ui.label(
                        "Créez d’abord une autre catégorie."
                    ).classes("text-orange-700")

                    with ui.row().classes(
                        "w-full justify-end mt-3"
                    ):
                        ui.button(
                            "Fermer",
                            on_click=dialog.close,
                        )
                else:
                    destination_input = ui.select(
                        list(destination_categories.keys()),
                        label="Déplacer vers",
                    ).classes("w-full")

                    def confirm_merge():
                        if not destination_input.value:
                            ui.notify(
                                "Choisissez une catégorie de destination.",
                                type="warning",
                            )
                            return

                        destination_name = destination_input.value
                        destination_id = destination_categories[
                            destination_name
                        ]

                        try:
                            moved_count = merge_categories(
                                category["id"],
                                destination_id,
                            )
                        except ValueError as error:
                            ui.notify(str(error), type="warning")
                            return

                        dialog.close()
                        ui.notify(
                            f"{moved_count} item(s) déplacé(s) vers "
                            f"« {destination_name} ».",
                            type="positive",
                        )
                        ui.navigate.to("/?tab=categories")

                    with ui.row().classes(
                        "w-full justify-end gap-2 mt-3"
                    ):
                        ui.button(
                            "Annuler",
                            on_click=dialog.close,
                        ).props("flat")

                        ui.button(
                            "Fusionner",
                            icon="merge_type",
                            on_click=confirm_merge,
                        ).props("color=primary")

        dialog.open()

    def open_delete_dialog(category):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-md p-5"):
                ui.label("Supprimer la catégorie").classes(
                    "text-xl font-bold"
                )

                if category["item_count"] > 0:
                    ui.label(
                        f"« {category['name']} » contient "
                        f"{category['item_count']} item(s)."
                    ).classes("font-bold")

                    ui.label(
                        "Pour protéger vos données, cette catégorie "
                        "ne peut pas être supprimée directement. "
                        "Utilisez le bouton Fusionner."
                    ).classes("text-gray-600")

                    with ui.row().classes(
                        "w-full justify-end mt-3"
                    ):
                        ui.button(
                            "Fermer",
                            on_click=dialog.close,
                        )
                else:
                    ui.label(
                        f"Supprimer définitivement "
                        f"« {category['name']} » ?"
                    )

                    with ui.row().classes(
                        "w-full justify-end gap-2 mt-3"
                    ):
                        ui.button(
                            "Annuler",
                            on_click=dialog.close,
                        ).props("flat")

                        def confirm_delete():
                            try:
                                delete_category(category["id"])
                            except ValueError as error:
                                ui.notify(
                                    str(error),
                                    type="warning",
                                )
                                return

                            dialog.close()
                            ui.notify(
                                "Catégorie supprimée.",
                                type="positive",
                            )
                            ui.navigate.to("/?tab=categories")

                        ui.button(
                            "Supprimer",
                            icon="delete",
                            on_click=confirm_delete,
                        ).props("color=negative")

        dialog.open()

    # ---------------------------------------------------------
    # LISTE DES CATÉGORIES
    # ---------------------------------------------------------

    ui.label("Catégories existantes").classes(
        "text-lg font-bold mt-1"
    )

    with ui.column().classes("w-full gap-2"):
        for category in categories:
            item_count = category["item_count"]

            with ui.card().classes(
                "w-full px-4 py-3"
            ):
                with ui.row().classes(
                    "w-full items-center justify-between gap-3"
                ):
                    with ui.row().classes(
                        "items-center gap-3 grow min-w-[180px]"
                    ):
                        ui.icon("folder").classes(
                            "text-2xl text-primary"
                        )

                        with ui.column().classes("gap-0"):
                            ui.label(category["name"]).classes(
                                "font-bold text-base"
                            )

                            ui.label(
                                f"{item_count} item"
                                if item_count == 1
                                else f"{item_count} items"
                            ).classes("text-sm text-gray-500")

                    with ui.row().classes(
                        "items-center gap-0"
                    ):
                        ui.button(
                            icon="edit",
                            on_click=lambda selected=category: (
                                open_rename_dialog(selected)
                            ),
                        ).props(
                            "flat round color=primary"
                        ).tooltip("Renommer")

                        ui.button(
                            icon="merge_type",
                            on_click=lambda selected=category: (
                                open_merge_dialog(selected)
                            ),
                        ).props(
                            "flat round color=primary"
                        ).tooltip("Fusionner")

                        ui.button(
                            icon="delete",
                            on_click=lambda selected=category: (
                                open_delete_dialog(selected)
                            ),
                        ).props(
                            "flat round color=negative"
                        ).tooltip("Supprimer")
