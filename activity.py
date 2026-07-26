from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from nicegui import ui

from auth import get_current_user_id
from db import (
    get_accessible_families,
    get_activity_history,
    get_deleted_categories,
    get_deleted_items,
    get_deleted_stores,
    permanently_delete_category,
    permanently_delete_item,
    permanently_delete_store,
    purge_expired_trash,
    restore_category,
    restore_item,
    restore_store,
)
from state import (
    get_current_family_id,
    set_current_family_id,
)
from utils import ensure_family_selected


try:
    QUEBEC_TIME = ZoneInfo("America/Toronto")
except ZoneInfoNotFoundError:
    QUEBEC_TIME = timezone.utc

ACTION_TEXT = {
    "item_created": "a créé l’item",
    "item_updated": "a modifié l’item",
    "item_needed_added": "a ajouté aux besoins",
    "item_needed_removed": "a retiré des besoins",
    "item_deleted": "a placé dans la corbeille",
    "item_restored": "a restauré",
    "item_deleted_permanently": (
        "a supprimé définitivement"
    ),
    "category_created": "a créé la catégorie",
    "category_renamed": "a renommé la catégorie",
    "category_moved": "a déplacé la catégorie",
    "category_merged": "a fusionné la catégorie",
    "category_deleted": (
        "a placé la catégorie dans la corbeille"
    ),
    "category_restored": "a restauré la catégorie",
    "category_deleted_permanently": (
        "a supprimé définitivement la catégorie"
    ),
    "store_created": "a créé le magasin",
    "store_renamed": "a renommé le magasin",
    "store_moved": "a déplacé le magasin",
    "store_deleted": (
        "a placé le magasin dans la corbeille"
    ),
    "store_restored": "a restauré le magasin",
    "store_deleted_permanently": (
        "a supprimé définitivement le magasin"
    ),
    "backup_imported": "a importé une sauvegarde",
    "template_created": "a créé la liste modèle",
    "template_updated": "a modifié la liste modèle",
    "template_deleted": "a supprimé la liste modèle",
    "template_applied": "a ajouté aux besoins la liste modèle",
    "recipe_created": "a créé la recette",
    "recipe_updated": "a modifié la recette",
    "recipe_deleted": "a supprimé la recette",
    "recipe_applied": "a ajouté aux besoins la recette",
    "template_published": "a publié la liste modèle",
    "template_unpublished": "a retiré de la bibliothèque la liste modèle",
    "template_public_updated": "a mis à jour la publication de la liste modèle",
    "template_copied_from_library": "a copié depuis la bibliothèque la liste modèle",
    "recipe_published": "a publié la recette",
    "recipe_unpublished": "a retiré de la bibliothèque la recette",
    "recipe_public_updated": "a mis à jour la publication de la recette",
    "recipe_copied_from_library": "a copié depuis la bibliothèque la recette",
}


def _format_time(value):
    if not isinstance(value, datetime):
        return ""

    return value.astimezone(
        QUEBEC_TIME
    ).strftime("%Y-%m-%d à %H h %M")


def activity_panel():
    user_id = get_current_user_id()
    family_id = get_current_family_id()

    if user_id is None or not ensure_family_selected(family_id):
        return

    purge_expired_trash(
        user_id,
        family_id,
    )

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
            ui.navigate.to("/?tab=activite"),
        ),
    ).classes("w-full")

    ui.label("Activité et corbeille").classes(
        "text-2xl font-bold"
    )
    ui.label(
        "Les éléments de la corbeille sont supprimés "
        "automatiquement après 30 jours."
    ).classes("text-sm text-gray-500")

    with ui.tabs().classes("w-full") as tabs:
        history_tab = ui.tab(
            "Historique",
            icon="history",
        )
        trash_tab = ui.tab(
            "Corbeille",
            icon="delete_sweep",
        )

    with ui.tab_panels(
        tabs,
        value=history_tab,
    ).classes(
        "w-full bg-transparent p-0"
    ):
        with ui.tab_panel(
            history_tab
        ).classes("p-0"):
            _history_section(
                user_id,
                family_id,
            )

        with ui.tab_panel(
            trash_tab
        ).classes("p-0"):
            _trash_section(
                user_id,
                family_id,
            )


def _history_section(user_id, family_id):
    rows = get_activity_history(
        user_id,
        family_id,
        limit=100,
    )

    if not rows:
        ui.label(
            "Aucune activité enregistrée pour le moment."
        ).classes("text-gray-500")
        return

    for row in rows:
        action = ACTION_TEXT.get(
            row["action_type"],
            row["action_type"],
        )

        with ui.card().classes(
            "w-full px-4 py-3 mt-2"
        ):
            with ui.row().classes(
                "w-full items-start gap-3 flex-nowrap"
            ):
                ui.icon("history").classes(
                    "text-2xl text-primary shrink-0"
                )

                with ui.column().classes(
                    "gap-0 grow min-w-0"
                ):
                    ui.label(
                        f"{row['actor_name']} {action} "
                        f"« {row['entity_name']} »"
                    ).classes(
                        "font-bold whitespace-normal"
                    ).style("overflow-wrap:anywhere;")

                    ui.label(
                        _format_time(row["created_at"])
                    ).classes("text-xs text-gray-500")


def _trash_section(user_id, family_id):
    deleted_items = get_deleted_items(
        user_id,
        family_id,
    )
    deleted_categories = get_deleted_categories(
        user_id,
        family_id,
    )
    deleted_stores = get_deleted_stores(
        user_id,
        family_id,
    )

    total = (
        len(deleted_items)
        + len(deleted_categories)
        + len(deleted_stores)
    )

    if total == 0:
        with ui.card().classes(
            "w-full p-6 items-center text-center"
        ):
            ui.icon("delete_outline").classes(
                "text-5xl text-gray-400"
            )
            ui.label("La corbeille est vide").classes(
                "text-xl font-bold"
            )
        return

    if deleted_items:
        ui.label("Items").classes(
            "text-lg font-bold mt-2"
        )

        for item in deleted_items:
            subtitle = (
                f"{item['store']} · "
                f"{item['category']} · "
                f"{_format_time(item['deleted_at'])}"
            )

            _trash_card(
                title=item["name"],
                subtitle=subtitle,
                note=item.get("note") or "",
                restore=lambda selected=item: (
                    _perform(
                        restore_item,
                        user_id,
                        family_id,
                        selected["id"],
                        "Item restauré.",
                    )
                ),
                delete=lambda selected=item: (
                    _confirm_permanent(
                        "item",
                        selected["name"],
                        lambda: _perform(
                            permanently_delete_item,
                            user_id,
                            family_id,
                            selected["id"],
                            (
                                "Item supprimé "
                                "définitivement."
                            ),
                        ),
                    )
                ),
            )

    if deleted_categories:
        ui.label("Catégories").classes(
            "text-lg font-bold mt-3"
        )

        for category in deleted_categories:
            _trash_card(
                title=category["name"],
                subtitle=_format_time(
                    category["deleted_at"]
                ),
                restore=lambda selected=category: (
                    _perform(
                        restore_category,
                        user_id,
                        family_id,
                        selected["id"],
                        "Catégorie restaurée.",
                    )
                ),
                delete=lambda selected=category: (
                    _confirm_permanent(
                        "catégorie",
                        selected["name"],
                        lambda: _perform(
                            permanently_delete_category,
                            user_id,
                            family_id,
                            selected["id"],
                            (
                                "Catégorie supprimée "
                                "définitivement."
                            ),
                        ),
                    )
                ),
            )

    if deleted_stores:
        ui.label("Magasins").classes(
            "text-lg font-bold mt-3"
        )

        for store in deleted_stores:
            _trash_card(
                title=store["name"],
                subtitle=_format_time(
                    store["deleted_at"]
                ),
                restore=lambda selected=store: (
                    _perform(
                        restore_store,
                        user_id,
                        family_id,
                        selected["id"],
                        "Magasin restauré.",
                    )
                ),
                delete=lambda selected=store: (
                    _confirm_permanent(
                        "magasin",
                        selected["name"],
                        lambda: _perform(
                            permanently_delete_store,
                            user_id,
                            family_id,
                            selected["id"],
                            (
                                "Magasin supprimé "
                                "définitivement."
                            ),
                        ),
                    )
                ),
            )


def _trash_card(
    title,
    subtitle,
    restore,
    delete,
    note="",
):
    with ui.card().classes(
        "w-full px-4 py-3 mt-2"
    ):
        with ui.row().classes(
            "w-full items-center gap-2 flex-nowrap"
        ):
            with ui.column().classes(
                "gap-0 grow min-w-0"
            ):
                ui.label(title).classes(
                    "font-bold whitespace-normal"
                ).style("overflow-wrap:anywhere;")

                ui.label(subtitle).classes(
                    "text-xs text-gray-500"
                )

                if note:
                    ui.label(note).classes(
                        "text-sm text-gray-500 "
                        "whitespace-normal"
                    )

            ui.button(
                icon="restore",
                on_click=restore,
            ).props(
                "flat round color=positive"
            ).tooltip("Restaurer")

            ui.button(
                icon="delete_forever",
                on_click=delete,
            ).props(
                "flat round color=negative"
            ).tooltip("Supprimer définitivement")


def _perform(
    function,
    user_id,
    family_id,
    entry_id,
    message,
):
    try:
        function(
            user_id,
            family_id,
            entry_id,
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
        message,
        type="positive",
    )
    ui.navigate.to("/?tab=activite")


def _confirm_permanent(
    entity_type,
    name,
    action,
):
    with ui.dialog() as dialog:
        with ui.card().classes(
            "w-full max-w-md p-5"
        ):
            ui.label(
                "Suppression définitive"
            ).classes("text-xl font-bold")

            ui.label(
                "Supprimer définitivement le "
                f"{entity_type} « {name} »? "
                "Cette action est irréversible."
            )

            def confirm():
                dialog.close()
                action()

            with ui.row().classes(
                "w-full justify-end gap-2 mt-3"
            ):
                ui.button(
                    "Annuler",
                    on_click=dialog.close,
                ).props("flat")
                ui.button(
                    "Supprimer",
                    icon="delete_forever",
                    on_click=confirm,
                ).props("color=negative")

    dialog.open()
