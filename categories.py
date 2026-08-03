from nicegui import app, ui

from auth import get_current_user_id
from db import (
    create_category,
    create_store,
    delete_category,
    delete_store,
    get_accessible_families,
    get_categories_with_counts,
    get_stores_with_counts,
    merge_categories,
    move_category,
    move_store,
    rename_category,
    rename_store,
)
from state import (
    get_current_family_id,
    set_current_family_id,
)
from grocery_preferences import (
    categories_are_enabled,
    get_or_create_default_category_id,
    set_categories_enabled,
)
from utils import ensure_family_selected


def _section_storage_key(family_id):
    return (
        f"categories_active_section_{family_id}"
    )


def _remember_section(
    family_id,
    section,
):
    normalized_section = (
        "stores"
        if section == "stores"
        else "categories"
    )

    app.storage.user[
        _section_storage_key(family_id)
    ] = normalized_section


def _reload_categories(
    family_id,
    section,
):
    _remember_section(
        family_id,
        section,
    )
    ui.navigate.to("/?tab=categories")


def categories_panel():
    user_id = get_current_user_id()
    family_id = get_current_family_id()

    if user_id is None or not ensure_family_selected(family_id):
        return

    active_section = app.storage.user.get(
        _section_storage_key(family_id),
        "categories",
    )

    if active_section not in {
        "categories",
        "stores",
    }:
        active_section = "categories"

    families = get_accessible_families(user_id)
    if not families:
        ui.label(
            "Aucune famille accessible."
        ).classes("text-orange-700")
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
            set_current_family_id(
                family_by_name[event.value]
            ),
            _reload_categories(
                family_by_name[event.value],
                active_section,
            ),
        ),
    ).classes("w-full")

    categories_enabled = categories_are_enabled(
        user_id,
        family_id,
    )
    if not categories_enabled:
        active_section = "stores"

    categories = get_categories_with_counts(
        user_id,
        family_id,
    )
    stores = get_stores_with_counts(
        user_id,
        family_id,
    )

    ui.label("Organisation").classes(
        "text-2xl font-bold"
    )

    with ui.card().classes(
        "w-full p-4 border-l-4 border-primary"
    ):
        with ui.row().classes(
            "w-full items-center justify-between gap-3 flex-wrap"
        ):
            with ui.column().classes("gap-0 grow min-w-0"):
                ui.label(
                    "Utiliser les catégories"
                ).classes("text-lg font-bold")
                ui.label(
                    "Ce choix s’applique à toute la famille. "
                    "Les catégories existantes sont conservées "
                    "lorsqu’elles sont masquées."
                ).classes("text-sm text-gray-500")

            category_switch = ui.switch(
                value=categories_enabled,
            ).props("color=primary")

        def category_preference_changed(event):
            enabled = bool(event.value)
            try:
                set_categories_enabled(
                    user_id,
                    family_id,
                    enabled,
                )
                if not enabled:
                    get_or_create_default_category_id(
                        user_id,
                        family_id,
                    )
            except (
                ValueError,
                PermissionError,
            ) as error:
                ui.notify(
                    str(error),
                    type="warning",
                )
                category_switch.value = not enabled
                category_switch.update()
                return

            ui.notify(
                (
                    "Les catégories sont maintenant utilisées."
                    if enabled
                    else (
                        "Les catégories sont maintenant masquées. "
                        "Les données existantes sont conservées."
                    )
                ),
                type="positive",
            )
            _reload_categories(
                family_id,
                (
                    "categories"
                    if enabled
                    else "stores"
                ),
            )

        category_switch.on_value_change(
            category_preference_changed
        )

    ui.label(
        (
            "Les flèches déterminent l’ordre utilisé "
            "dans Besoins et Mode courses."
            if categories_enabled
            else (
                "Les items sont maintenant organisés uniquement "
                "par magasin. Réactivez les catégories ici au besoin."
            )
        )
    ).classes("text-sm text-gray-500")

    def section_changed(event):
        _remember_section(
            family_id,
            event.value,
        )

    with ui.tabs(
        value=active_section,
        on_change=section_changed,
    ).classes("w-full") as tabs:
        if categories_enabled:
            ui.tab(
                "categories",
                label="Catégories",
                icon="category",
            )
        ui.tab(
            "stores",
            label="Magasins",
            icon="storefront",
        )

    with ui.tab_panels(
        tabs,
        value=active_section,
    ).classes(
        "w-full bg-transparent p-0"
    ):
        if categories_enabled:
            with ui.tab_panel(
                "categories"
            ).classes("p-0 gap-3"):
                _category_section(
                    user_id,
                    family_id,
                    categories,
                )

        with ui.tab_panel(
            "stores"
        ).classes("p-0 gap-3"):
            _store_section(
                user_id,
                family_id,
                stores,
            )


def _category_section(
    user_id,
    family_id,
    categories,
):
    with ui.card().classes("w-full p-4"):
        ui.label(
            "Ajouter une catégorie"
        ).classes("text-lg font-bold")

        with ui.row().classes(
            "w-full items-end gap-2 flex-wrap"
        ):
            new_input = ui.input(
                label="Nom",
                placeholder="Ex. Fruits et légumes",
            ).classes("grow min-w-[220px]")

            def add():
                try:
                    create_category(
                        user_id,
                        family_id,
                        new_input.value,
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

                ui.notify(
                    "Catégorie ajoutée.",
                    type="positive",
                )
                _reload_categories(family_id, "categories")

            new_input.on("keydown.enter", add)
            ui.button(
                "Ajouter",
                icon="add",
                on_click=add,
            ).props("color=primary")

    if not categories:
        ui.label("Aucune catégorie.").classes(
            "text-gray-500"
        )
        return

    def rename_dialog(category):
        with ui.dialog() as dialog:
            with ui.card().classes(
                "w-full max-w-md p-5"
            ):
                ui.label(
                    "Renommer la catégorie"
                ).classes("text-xl font-bold")

                name_input = ui.input(
                    label="Nom",
                    value=category["name"],
                ).classes("w-full")

                def save():
                    try:
                        rename_category(
                            user_id,
                            family_id,
                            category["id"],
                            name_input.value,
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

                    dialog.close()
                    ui.notify(
                        "Catégorie renommée.",
                        type="positive",
                    )
                    _reload_categories(
                        family_id,
                        "categories",
                    )

                with ui.row().classes(
                    "w-full justify-end gap-2"
                ):
                    ui.button(
                        "Annuler",
                        on_click=dialog.close,
                    ).props("flat")
                    ui.button(
                        "Enregistrer",
                        icon="save",
                        on_click=save,
                    ).props("color=primary")

        dialog.open()

    def merge_dialog(category):
        destinations = {
            row["name"]: row["id"]
            for row in categories
            if row["id"] != category["id"]
        }

        with ui.dialog() as dialog:
            with ui.card().classes(
                "w-full max-w-md p-5"
            ):
                ui.label(
                    "Fusionner la catégorie"
                ).classes("text-xl font-bold")

                if not destinations:
                    ui.label(
                        "Créez d’abord une autre catégorie."
                    )
                    ui.button(
                        "Fermer",
                        on_click=dialog.close,
                    )
                else:
                    destination = ui.select(
                        list(destinations),
                        label="Déplacer vers",
                    ).classes("w-full")

                    def confirm():
                        if not destination.value:
                            ui.notify(
                                "Choisissez une destination.",
                                type="warning",
                            )
                            return

                        try:
                            count = merge_categories(
                                user_id,
                                family_id,
                                category["id"],
                                destinations[
                                    destination.value
                                ],
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

                        dialog.close()
                        ui.notify(
                            f"{count} item(s) déplacé(s).",
                            type="positive",
                        )
                        _reload_categories(
                            family_id,
                            "categories",
                        )

                    with ui.row().classes(
                        "w-full justify-end gap-2"
                    ):
                        ui.button(
                            "Annuler",
                            on_click=dialog.close,
                        ).props("flat")
                        ui.button(
                            "Fusionner",
                            icon="merge_type",
                            on_click=confirm,
                        ).props("color=primary")

        dialog.open()

    def delete_dialog(category):
        with ui.dialog() as dialog:
            with ui.card().classes(
                "w-full max-w-md p-5"
            ):
                ui.label(
                    "Mettre à la corbeille"
                ).classes("text-xl font-bold")

                if category["total_item_count"]:
                    ui.label(
                        "Cette catégorie est encore liée à "
                        f"{category['total_item_count']} item(s), "
                        "incluant les items supprimés. "
                        "Fusionnez-la d’abord."
                    ).classes("text-orange-700")
                    ui.button(
                        "Fermer",
                        on_click=dialog.close,
                    )
                else:
                    ui.label(
                        f"La catégorie « {category['name']} » "
                        "sera conservée 30 jours."
                    )

                    def confirm():
                        try:
                            delete_category(
                                user_id,
                                family_id,
                                category["id"],
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

                        dialog.close()
                        ui.notify(
                            "Catégorie déplacée dans la corbeille.",
                            type="positive",
                        )
                        _reload_categories(
                            family_id,
                            "categories",
                        )

                    with ui.row().classes(
                        "w-full justify-end gap-2"
                    ):
                        ui.button(
                            "Annuler",
                            on_click=dialog.close,
                        ).props("flat")
                        ui.button(
                            "Mettre à la corbeille",
                            icon="delete",
                            on_click=confirm,
                        ).props("color=negative")

        dialog.open()

    for index, category in enumerate(categories):
        with ui.card().classes(
            "w-full px-3 py-2"
        ):
            with ui.row().classes(
                "w-full items-center gap-2 flex-nowrap"
            ):
                with ui.column().classes(
                    "gap-0 grow min-w-0"
                ):
                    ui.label(
                        category["name"]
                    ).classes(
                        "font-bold whitespace-normal"
                    )

                    count_text = (
                        f"{category['item_count']} "
                        "item(s) actif(s)"
                    )
                    if category["deleted_item_count"]:
                        count_text += (
                            " · "
                            f"{category['deleted_item_count']} "
                            "dans la corbeille"
                        )

                    ui.label(count_text).classes(
                        "text-sm text-gray-500"
                    )

                up_button = ui.button(
                    icon="arrow_upward",
                    on_click=lambda selected=category: (
                        _move_and_reload(
                            move_category,
                            user_id,
                            family_id,
                            selected["id"],
                            -1,
                            "categories",
                        )
                    ),
                ).props("flat round dense")

                if index == 0:
                    up_button.disable()

                down_button = ui.button(
                    icon="arrow_downward",
                    on_click=lambda selected=category: (
                        _move_and_reload(
                            move_category,
                            user_id,
                            family_id,
                            selected["id"],
                            1,
                            "categories",
                        )
                    ),
                ).props("flat round dense")

                if index == len(categories) - 1:
                    down_button.disable()

                ui.button(
                    icon="edit",
                    on_click=lambda selected=category: (
                        rename_dialog(selected)
                    ),
                ).props("flat round color=primary")

                ui.button(
                    icon="merge_type",
                    on_click=lambda selected=category: (
                        merge_dialog(selected)
                    ),
                ).props("flat round color=primary")

                ui.button(
                    icon="delete",
                    on_click=lambda selected=category: (
                        delete_dialog(selected)
                    ),
                ).props("flat round color=negative")


def _store_section(
    user_id,
    family_id,
    stores,
):
    with ui.card().classes("w-full p-4"):
        ui.label("Ajouter un magasin").classes(
            "text-lg font-bold"
        )

        with ui.row().classes(
            "w-full items-end gap-2 flex-wrap"
        ):
            new_input = ui.input(
                label="Nom",
                placeholder="Ex. IGA, Costco",
            ).classes("grow min-w-[220px]")

            def add():
                try:
                    create_store(
                        user_id,
                        family_id,
                        new_input.value,
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

                ui.notify(
                    "Magasin ajouté.",
                    type="positive",
                )
                _reload_categories(family_id, "stores")

            new_input.on("keydown.enter", add)
            ui.button(
                "Ajouter",
                icon="add",
                on_click=add,
            ).props("color=primary")

    def rename_dialog(store):
        with ui.dialog() as dialog:
            with ui.card().classes(
                "w-full max-w-md p-5"
            ):
                ui.label(
                    "Renommer le magasin"
                ).classes("text-xl font-bold")

                name_input = ui.input(
                    label="Nom",
                    value=store["name"],
                ).classes("w-full")

                def save():
                    try:
                        rename_store(
                            user_id,
                            family_id,
                            store["id"],
                            name_input.value,
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

                    dialog.close()
                    ui.notify(
                        "Magasin renommé.",
                        type="positive",
                    )
                    _reload_categories(
                        family_id,
                        "stores",
                    )

                with ui.row().classes(
                    "w-full justify-end gap-2"
                ):
                    ui.button(
                        "Annuler",
                        on_click=dialog.close,
                    ).props("flat")
                    ui.button(
                        "Enregistrer",
                        icon="save",
                        on_click=save,
                    ).props("color=primary")

        dialog.open()

    def delete_dialog(store):
        with ui.dialog() as dialog:
            with ui.card().classes(
                "w-full max-w-md p-5"
            ):
                ui.label(
                    "Mettre à la corbeille"
                ).classes("text-xl font-bold")

                if store["total_item_count"]:
                    ui.label(
                        "Ce magasin est encore lié à "
                        f"{store['total_item_count']} item(s). "
                        "Modifiez les items d’abord."
                    ).classes("text-orange-700")
                    ui.button(
                        "Fermer",
                        on_click=dialog.close,
                    )
                else:
                    ui.label(
                        f"Le magasin « {store['name']} » "
                        "sera conservé 30 jours."
                    )

                    def confirm():
                        try:
                            delete_store(
                                user_id,
                                family_id,
                                store["id"],
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

                        dialog.close()
                        ui.notify(
                            "Magasin déplacé dans la corbeille.",
                            type="positive",
                        )
                        _reload_categories(
                            family_id,
                            "stores",
                        )

                    with ui.row().classes(
                        "w-full justify-end gap-2"
                    ):
                        ui.button(
                            "Annuler",
                            on_click=dialog.close,
                        ).props("flat")
                        ui.button(
                            "Mettre à la corbeille",
                            icon="delete",
                            on_click=confirm,
                        ).props("color=negative")

        dialog.open()

    for index, store in enumerate(stores):
        with ui.card().classes(
            "w-full px-3 py-2"
        ):
            with ui.row().classes(
                "w-full items-center gap-2 flex-nowrap"
            ):
                with ui.column().classes(
                    "gap-0 grow min-w-0"
                ):
                    ui.label(store["name"]).classes(
                        "font-bold whitespace-normal"
                    )

                    count_text = (
                        f"{store['item_count']} "
                        "item(s) actif(s)"
                    )
                    if store["deleted_item_count"]:
                        count_text += (
                            " · "
                            f"{store['deleted_item_count']} "
                            "dans la corbeille"
                        )

                    ui.label(count_text).classes(
                        "text-sm text-gray-500"
                    )

                up_button = ui.button(
                    icon="arrow_upward",
                    on_click=lambda selected=store: (
                        _move_and_reload(
                            move_store,
                            user_id,
                            family_id,
                            selected["id"],
                            -1,
                            "stores",
                        )
                    ),
                ).props("flat round dense")

                if index == 0:
                    up_button.disable()

                down_button = ui.button(
                    icon="arrow_downward",
                    on_click=lambda selected=store: (
                        _move_and_reload(
                            move_store,
                            user_id,
                            family_id,
                            selected["id"],
                            1,
                            "stores",
                        )
                    ),
                ).props("flat round dense")

                if index == len(stores) - 1:
                    down_button.disable()

                ui.button(
                    icon="edit",
                    on_click=lambda selected=store: (
                        rename_dialog(selected)
                    ),
                ).props("flat round color=primary")

                ui.button(
                    icon="delete",
                    on_click=lambda selected=store: (
                        delete_dialog(selected)
                    ),
                ).props("flat round color=negative")


def _move_and_reload(
    function,
    user_id,
    family_id,
    entry_id,
    direction,
    section,
):
    try:
        function(
            user_id,
            family_id,
            entry_id,
            direction,
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

    _reload_categories(
        family_id,
        section,
    )
