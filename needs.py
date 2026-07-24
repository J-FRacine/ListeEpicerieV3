import time
from collections import defaultdict

from nicegui import app, ui

from auth import get_current_user_id
from db import (
    get_accessible_families,
    get_items,
    set_item_needed,
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
    family_id = get_current_family_id()

    if user_id is None or not ensure_family_selected(family_id):
        return

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
            ui.navigate.to("/?tab=besoins"),
        ),
    ).classes("w-full")

    ui.separator()

    # ---------------------------------------------------------
    # ANNULER LE DERNIER RETRAIT
    # ---------------------------------------------------------

    undo_key = f"needs_pending_undo_{family_id}"
    pending = app.storage.user.get(undo_key)

    if pending and float(
        pending.get("expires_at", 0)
    ) <= time.time():
        app.storage.user.pop(undo_key, None)
        pending = None

    if pending:
        undo_card = ui.card().classes(
            "w-full p-3 border-l-4 border-primary"
        )

        with undo_card:
            with ui.row().classes(
                "w-full items-center justify-between gap-3"
            ):
                ui.label(
                    f"« {pending['name']} » retiré des besoins."
                ).classes(
                    "text-sm font-bold grow min-w-0 "
                    "whitespace-normal"
                ).style("overflow-wrap:anywhere;")

                def undo_last():
                    try:
                        set_item_needed(
                            user_id,
                            pending["item_id"],
                            True,
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
                        undo_key,
                        None,
                    )
                    ui.navigate.to("/?tab=besoins")

                ui.button(
                    "Annuler",
                    icon="undo",
                    on_click=undo_last,
                ).props(
                    "flat color=primary"
                ).classes("shrink-0")

        remaining_seconds = max(
            0.1,
            float(pending["expires_at"]) - time.time(),
        )
        pending_item_id = pending["item_id"]

        def expire_undo():
            current_pending = app.storage.user.get(
                undo_key
            )
            if (
                current_pending
                and current_pending.get("item_id")
                == pending_item_id
            ):
                app.storage.user.pop(undo_key, None)
            undo_card.delete()

        ui.timer(
            remaining_seconds,
            expire_undo,
            once=True,
        )

    items = [
        item
        for item in get_items(user_id, family_id)
        if item["needed"] == 1
    ]

    if not items:
        ui.label("Besoins").classes(
            "text-xl font-bold"
        )
        ui.label(
            "Aucun item n’est actuellement marqué comme besoin."
        ).classes("text-gray-500 mt-3")
        return

    # ---------------------------------------------------------
    # GROUPEMENT MAGASIN > CATÉGORIE
    # ---------------------------------------------------------

    grouped = defaultdict(
        lambda: defaultdict(list)
    )
    store_order = {}
    category_order = {}

    for item in items:
        store = item["store"] or "Sans magasin"
        category = (
            item["category"]
            or "Sans catégorie"
        )
        grouped[store][category].append(item)
        store_order[store] = item["store_order"]
        category_order[
            (store, category)
        ] = item["category_order"]

    stores = sorted(
        grouped,
        key=lambda name: (
            store_order[name],
            name.casefold(),
        ),
    )

    open_key = f"needs_open_groups_{family_id}"
    all_group_keys = []

    for store in stores:
        all_group_keys.append(
            f"store::{store}"
        )
        for category in grouped[store]:
            all_group_keys.append(
                f"category::{store}::{category}"
            )

    stored_open = app.storage.user.get(open_key)
    open_groups = set(
        all_group_keys
        if stored_open is None
        else stored_open
    )

    def save_state(key, is_open):
        current = set(
            app.storage.user.get(
                open_key,
                all_group_keys,
            )
        )

        if is_open:
            current.add(key)
        else:
            current.discard(key)

        app.storage.user[
            open_key
        ] = sorted(current)

    # ---------------------------------------------------------
    # EN-TÊTE
    # ---------------------------------------------------------

    with ui.row().classes(
        "w-full items-center justify-between "
        "gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Besoins").classes(
                "text-xl font-bold"
            )
            ui.label(
                f"{len(items)} item"
                if len(items) == 1
                else f"{len(items)} items"
            ).classes("text-sm text-gray-500")

        with ui.row().classes(
            "items-center gap-1"
        ):
            ui.button(
                icon="unfold_more",
                on_click=lambda: (
                    app.storage.user.__setitem__(
                        open_key,
                        all_group_keys,
                    ),
                    ui.navigate.to(
                        "/?tab=besoins"
                    ),
                ),
            ).props(
                "flat round color=primary"
            ).tooltip("Tout ouvrir")

            ui.button(
                icon="unfold_less",
                on_click=lambda: (
                    app.storage.user.__setitem__(
                        open_key,
                        [],
                    ),
                    ui.navigate.to(
                        "/?tab=besoins"
                    ),
                ),
            ).props(
                "flat round color=primary"
            ).tooltip("Tout fermer")

    shopping_active = (
        has_active_shopping_session(
            family_id
        )
    )

    def open_shopping():
        if not shopping_active:
            try:
                start_shopping_session(
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
                return

        ui.navigate.to("/?tab=courses")

    ui.button(
        (
            "Reprendre les courses"
            if shopping_active
            else "Commencer les courses"
        ),
        icon=(
            "play_arrow"
            if shopping_active
            else "shopping_cart_checkout"
        ),
        on_click=open_shopping,
    ).props(
        "color=primary size=lg"
    ).classes("w-full mt-3")

    # ---------------------------------------------------------
    # GROUPES REPLIABLES
    # ---------------------------------------------------------

    for store in stores:
        store_key = f"store::{store}"
        store_count = sum(
            len(rows)
            for rows in grouped[store].values()
        )

        def store_changed(
            event,
            key=store_key,
        ):
            save_state(
                key,
                bool(event.value),
            )

        with ui.expansion(
            text=store,
            caption=(
                f"{store_count} item"
                if store_count == 1
                else f"{store_count} items"
            ),
            icon="storefront",
            value=store_key in open_groups,
            on_value_change=store_changed,
        ).props(
            "expand-separator"
        ).classes(
            "w-full bg-white rounded-xl "
            "shadow-sm border border-gray-200 "
            "overflow-hidden mt-2"
        ):
            categories = sorted(
                grouped[store],
                key=lambda name: (
                    category_order[
                        (store, name)
                    ],
                    name.casefold(),
                ),
            )

            for category in categories:
                category_key = (
                    f"category::{store}::{category}"
                )
                category_items = sorted(
                    grouped[store][category],
                    key=lambda row: (
                        row["name"].casefold()
                    ),
                )

                def category_changed(
                    event,
                    key=category_key,
                ):
                    save_state(
                        key,
                        bool(event.value),
                    )

                with ui.expansion(
                    text=category,
                    caption=(
                        f"{len(category_items)} item"
                        if len(category_items) == 1
                        else (
                            f"{len(category_items)} items"
                        )
                    ),
                    icon="category",
                    value=(
                        category_key in open_groups
                    ),
                    on_value_change=(
                        category_changed
                    ),
                ).props(
                    "dense expand-separator"
                ).classes(
                    "w-full bg-gray-50 rounded-lg "
                    "overflow-hidden mb-2"
                ):
                    with ui.column().classes(
                        "w-full gap-1 px-1 pb-2"
                    ):
                        for item in category_items:

                            def remove_need(
                                selected=item,
                            ):
                                try:
                                    set_item_needed(
                                        user_id,
                                        selected["id"],
                                        False,
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
                                    undo_key
                                ] = {
                                    "item_id": selected[
                                        "id"
                                    ],
                                    "name": selected[
                                        "name"
                                    ],
                                    "expires_at": (
                                        time.time()
                                        + UNDO_SECONDS
                                    ),
                                }
                                ui.navigate.to(
                                    "/?tab=besoins"
                                )

                            row = ui.row().classes(
                                "w-full items-center "
                                "flex-nowrap bg-white "
                                "rounded-lg px-3 py-3 "
                                "gap-2 cursor-pointer "
                                "hover:bg-blue-50"
                            )
                            row.on(
                                "click",
                                remove_need,
                            )

                            with row:
                                with ui.column().classes(
                                    "gap-0 grow min-w-0"
                                ):
                                    title = item["name"]
                                    if item["quantity"] != 1:
                                        title += (
                                            f" ({item['quantity']})"
                                        )

                                    ui.label(title).classes(
                                        "font-bold leading-snug "
                                        "whitespace-normal "
                                        "break-words"
                                    ).style(
                                        "overflow-wrap:anywhere;"
                                    )

                                    if item.get("note"):
                                        ui.label(
                                            item["note"]
                                        ).classes(
                                            "text-sm text-gray-500 "
                                            "whitespace-normal"
                                        ).style(
                                            "overflow-wrap:anywhere;"
                                        )

                                ui.icon("check").classes(
                                    "text-3xl text-green-600 "
                                    "shrink-0 ml-auto"
                                )

    ui.label(
        "Les magasins et les catégories suivent "
        "l’ordre défini dans Catégories."
    ).classes("text-xs text-gray-500 mt-2")
