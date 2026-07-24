import time
from collections import defaultdict

from nicegui import app, ui

from auth import get_current_user_id
from db import (
    get_accessible_families,
    get_items,
    toggle_needed,
)
from state import (
    get_current_family_id,
    set_current_family_id,
)
from shopping import (
    has_active_shopping_session,
    start_shopping_session,
)
from utils import ensure_family_selected


UNDO_SECONDS = 10


def needs_panel():
    user_id = get_current_user_id()
    current_family_id = get_current_family_id()

    if (
        user_id is None
        or not ensure_family_selected(
            current_family_id
        )
    ):
        return

    families = get_accessible_families(
        user_id
    )

    if not families:
        ui.label(
            "Aucune famille accessible."
        ).classes("text-orange-700")
        return

    family_dict = {
        family["name"]: family["id"]
        for family in families
    }

    current_family_name = next(
        (
            name
            for name, family_id
            in family_dict.items()
            if family_id
            == current_family_id
        ),
        list(family_dict.keys())[0],
    )

    ui.select(
        list(family_dict.keys()),
        value=current_family_name,
        label="Famille",
        on_change=lambda event: (
            set_current_family_id(
                family_dict[event.value]
            ),
            ui.navigate.to("/?tab=besoins"),
        ),
    ).classes("w-full")

    ui.separator()

    undo_storage_key = (
        f"needs_pending_undo_"
        f"{current_family_id}"
    )

    # ---------------------------------------------------------
    # ANNULER LE DERNIER RETRAIT
    # ---------------------------------------------------------

    pending_undo = app.storage.user.get(
        undo_storage_key
    )

    if pending_undo:
        expires_at = float(
            pending_undo.get(
                "expires_at",
                0,
            )
        )

        if expires_at <= time.time():
            app.storage.user.pop(
                undo_storage_key,
                None,
            )
            pending_undo = None

    if pending_undo:
        undo_card = ui.card().classes(
            "w-full p-3 border-l-4 "
            "border-primary"
        )

        with undo_card:
            with ui.row().classes(
                "w-full items-center "
                "justify-between gap-3"
            ):
                with ui.row().classes(
                    "items-center gap-2 "
                    "grow min-w-0"
                ):
                    ui.icon(
                        "undo"
                    ).classes(
                        "text-2xl text-primary "
                        "shrink-0"
                    )

                    ui.label(
                        f"« {pending_undo['name']} » "
                        "retiré des besoins."
                    ).classes(
                        "text-sm font-bold "
                        "whitespace-normal"
                    ).style(
                        "overflow-wrap: anywhere;"
                    )

                def undo_last_removal():
                    try:
                        toggle_needed(
                            user_id,
                            pending_undo[
                                "item_id"
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

                    app.storage.user.pop(
                        undo_storage_key,
                        None,
                    )
                    ui.navigate.to(
                        "/?tab=besoins"
                    )

                ui.button(
                    "Annuler",
                    icon="undo",
                    on_click=undo_last_removal,
                ).props(
                    "flat color=primary"
                ).classes("shrink-0")

        remaining_seconds = max(
            0.1,
            float(
                pending_undo["expires_at"]
            ) - time.time(),
        )

        def expire_undo():
            current_pending = (
                app.storage.user.get(
                    undo_storage_key
                )
            )

            if (
                current_pending
                and current_pending.get(
                    "token"
                )
                == pending_undo.get(
                    "token"
                )
            ):
                app.storage.user.pop(
                    undo_storage_key,
                    None,
                )

            undo_card.delete()

        ui.timer(
            remaining_seconds,
            expire_undo,
            once=True,
        )

    # ---------------------------------------------------------
    # RÉCUPÉRATION ET REGROUPEMENT
    # ---------------------------------------------------------

    items = get_items(
        user_id,
        current_family_id,
    )

    needs = [
        item
        for item in items
        if item["needed"] == 1
    ]

    if not needs:
        ui.label("Besoins").classes(
            "text-xl font-bold"
        )
        ui.label(
            "Aucun item n’est actuellement "
            "marqué comme besoin."
        ).classes(
            "text-gray-500 mt-3"
        )
        return

    needs_by_category = defaultdict(list)

    for item in needs:
        category_name = (
            item["category"].strip()
            if item.get("category")
            else "Sans catégorie"
        )
        needs_by_category[
            category_name
        ].append(item)

    category_names = sorted(
        needs_by_category.keys(),
        key=lambda category: (
            category.casefold()
        ),
    )

    storage_key = (
        f"needs_open_categories_"
        f"{current_family_id}"
    )

    stored_open_categories = (
        app.storage.user.get(storage_key)
    )

    if stored_open_categories is None:
        open_categories = set(
            category_names
        )
    else:
        open_categories = {
            category_name
            for category_name
            in stored_open_categories
            if category_name
            in category_names
        }

    def save_category_state(
        category_name,
        is_open,
    ):
        stored_categories = (
            app.storage.user.get(
                storage_key
            )
        )

        if stored_categories is None:
            current_open_categories = set(
                category_names
            )
        else:
            current_open_categories = set(
                stored_categories
            )

        if is_open:
            current_open_categories.add(
                category_name
            )
        else:
            current_open_categories.discard(
                category_name
            )

        app.storage.user[
            storage_key
        ] = sorted(
            current_open_categories,
            key=lambda name: (
                name.casefold()
            ),
        )

    def open_all_categories():
        app.storage.user[
            storage_key
        ] = list(category_names)
        ui.navigate.to("/?tab=besoins")

    def close_all_categories():
        app.storage.user[
            storage_key
        ] = []
        ui.navigate.to("/?tab=besoins")

    # ---------------------------------------------------------
    # EN-TÊTE
    # ---------------------------------------------------------

    total_needs = len(needs)
    open_count = len(
        open_categories
    )

    with ui.row().classes(
        "w-full items-center "
        "justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Besoins").classes(
                "text-xl font-bold"
            )
            ui.label(
                (
                    f"{total_needs} item"
                    if total_needs == 1
                    else (
                        f"{total_needs} "
                        "items"
                    )
                )
            ).classes(
                "text-sm text-gray-500"
            )

        with ui.row().classes(
            "items-center gap-1 flex-wrap"
        ):
            ui.button(
                icon="unfold_more",
                on_click=open_all_categories,
            ).props(
                "flat round color=primary"
            ).tooltip(
                "Ouvrir toutes les catégories"
            )

            ui.button(
                icon="unfold_less",
                on_click=close_all_categories,
            ).props(
                "flat round color=primary"
            ).tooltip(
                "Fermer toutes les catégories"
            )

    ui.label(
        (
            f"{open_count} catégorie"
            if open_count == 1
            else (
                f"{open_count} "
                "catégories ouvertes"
            )
        )
    ).classes(
        "text-xs text-gray-500"
    )

    shopping_is_active = (
        has_active_shopping_session(
            current_family_id
        )
    )

    def open_shopping_mode():
        if not shopping_is_active:
            try:
                start_shopping_session(
                    user_id,
                    current_family_id,
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

        ui.navigate.to(
            "/?tab=courses"
        )

    ui.button(
        (
            "Reprendre les courses"
            if shopping_is_active
            else "Commencer les courses"
        ),
        icon=(
            "play_arrow"
            if shopping_is_active
            else "shopping_cart_checkout"
        ),
        on_click=open_shopping_mode,
    ).props(
        "color=primary size=lg"
    ).classes(
        "w-full mt-3"
    )

    # ---------------------------------------------------------
    # CATÉGORIES ET LIGNES TACTILES
    # ---------------------------------------------------------

    for category_name in category_names:
        category_items = sorted(
            needs_by_category[
                category_name
            ],
            key=lambda item: (
                item["name"]
                .strip()
                .casefold()
            ),
        )

        item_count = len(
            category_items
        )

        def category_state_changed(
            event,
            selected_category=(
                category_name
            ),
        ):
            save_category_state(
                selected_category,
                bool(event.value),
            )

        with ui.expansion(
            text=category_name,
            caption=(
                f"{item_count} item"
                if item_count == 1
                else (
                    f"{item_count} items"
                )
            ),
            icon="category",
            value=(
                category_name
                in open_categories
            ),
            on_value_change=(
                category_state_changed
            ),
        ).props(
            "expand-separator"
        ).classes(
            "w-full bg-white rounded-xl "
            "shadow-sm border "
            "border-gray-200 "
            "overflow-hidden mt-2"
        ):
            with ui.column().classes(
                "w-full gap-1 px-1 pb-2"
            ):
                for item in category_items:
                    quantity = item.get(
                        "quantity",
                        1,
                    )

                    item_text = (
                        f"{item['name']} "
                        f"({quantity})"
                        if quantity
                        and quantity != 1
                        else item["name"]
                    )

                    def remove_need(
                        item_id=item["id"],
                        item_name=item["name"],
                    ):
                        token = (
                            f"{item_id}-"
                            f"{time.time()}"
                        )

                        try:
                            toggle_needed(
                                user_id,
                                item_id,
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

                        app.storage.user[
                            undo_storage_key
                        ] = {
                            "item_id": item_id,
                            "name": item_name,
                            "token": token,
                            "expires_at": (
                                time.time()
                                + UNDO_SECONDS
                            ),
                        }

                        # Le rechargement met aussi
                        # le compteur à jour.
                        ui.navigate.to(
                            "/?tab=besoins"
                        )

                    item_row = ui.row().classes(
                        "w-full items-center "
                        "flex-nowrap "
                        "bg-gray-100 rounded-lg "
                        "px-3 py-3 gap-2 "
                        "cursor-pointer "
                        "hover:bg-blue-50"
                    )

                    item_row.on(
                        "click",
                        remove_need,
                    )

                    with item_row:
                        ui.label(
                            item_text
                        ).classes(
                            "font-bold leading-snug "
                            "whitespace-normal "
                            "break-words pr-2"
                        ).style(
                            "flex: 1 1 0; "
                            "min-width: 0; "
                            "overflow-wrap: anywhere;"
                        )

                        ui.icon(
                            "check"
                        ).classes(
                            "text-3xl "
                            "text-green-600 "
                            "shrink-0 ml-auto"
                        )

    ui.label(
        "Astuce : touchez une ligne entière "
        "pour retirer l’item. Vous aurez "
        "10 secondes pour annuler."
    ).classes(
        "text-xs text-gray-500 mt-2"
    )
