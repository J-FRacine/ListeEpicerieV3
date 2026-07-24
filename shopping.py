import time
from collections import defaultdict
from datetime import datetime

from nicegui import app, ui

from auth import get_current_user_id
from db import (
    get_accessible_families,
    get_items,
    set_item_needed,
)
from state import get_current_family_id
from utils import ensure_family_selected


AUTO_REFRESH_SECONDS = 5
UNDO_SECONDS = 10


def _session_key(family_id):
    return f"shopping_session_{family_id}"


def _undo_key(family_id):
    return f"shopping_pending_undo_{family_id}"


def _open_key(family_id):
    return f"shopping_open_groups_{family_id}"


def has_active_shopping_session(family_id):
    return bool(
        family_id
        and app.storage.user.get(
            _session_key(family_id)
        )
    )


def start_shopping_session(user_id, family_id):
    items = [
        item
        for item in get_items(user_id, family_id)
        if item["needed"] == 1
    ]

    if not items:
        raise ValueError(
            "La liste des besoins est vide."
        )

    app.storage.user[
        _session_key(family_id)
    ] = {
        "item_ids": [
            item["id"]
            for item in items
        ],
        "started_at": time.time(),
    }
    app.storage.user.pop(
        _undo_key(family_id),
        None,
    )


def _ensure_session(family_id, current_needs):
    key = _session_key(family_id)
    session = app.storage.user.get(key) or {
        "item_ids": [],
        "started_at": time.time(),
    }

    observed = {
        int(value)
        for value in session.get(
            "item_ids",
            [],
        )
    }
    observed.update(
        item["id"]
        for item in current_needs
    )
    session["item_ids"] = sorted(observed)
    app.storage.user[key] = session
    return session


def _clear_session(family_id):
    for key in (
        _session_key(family_id),
        _undo_key(family_id),
        _open_key(family_id),
    ):
        app.storage.user.pop(key, None)


def shopping_panel():
    user_id = get_current_user_id()
    family_id = get_current_family_id()

    if user_id is None or not ensure_family_selected(family_id):
        return

    family = next(
        (
            row
            for row in get_accessible_families(
                user_id
            )
            if row["id"] == family_id
        ),
        None,
    )

    if family is None:
        ui.label(
            "Cette famille n’est plus accessible."
        ).classes("text-negative")
        return

    with ui.card().classes(
        "w-full p-4 sticky top-2 z-20 "
        "border-l-4 border-primary"
    ):
        with ui.row().classes(
            "w-full items-center justify-between "
            "gap-3 flex-nowrap"
        ):
            ui.button(
                icon="arrow_back",
                on_click=lambda: ui.navigate.to(
                    "/?tab=besoins"
                ),
            ).props("flat round")

            with ui.column().classes(
                "gap-0 grow min-w-0"
            ):
                ui.label("Mode courses").classes(
                    "text-xl font-bold"
                )
                ui.label(
                    family["name"]
                ).classes(
                    "text-sm text-gray-500 truncate"
                )

            ui.button(
                icon="refresh",
                on_click=lambda: (
                    render_shopping.refresh()
                ),
            ).props(
                "flat round color=primary"
            )

    @ui.refreshable
    def render_shopping():
        current = [
            item
            for item in get_items(
                user_id,
                family_id,
            )
            if item["needed"] == 1
        ]

        session = _ensure_session(
            family_id,
            current,
        )
        observed_ids = {
            int(value)
            for value in session.get(
                "item_ids",
                [],
            )
        }
        current_ids = {
            item["id"]
            for item in current
        }

        total = len(observed_ids)
        remaining = len(current_ids)
        completed = max(
            total - remaining,
            0,
        )
        progress = (
            completed / total
            if total
            else 1.0
        )

        with ui.card().classes("w-full p-4"):
            with ui.row().classes(
                "w-full items-center justify-between gap-3"
            ):
                with ui.column().classes("gap-0"):
                    ui.label(
                        f"{completed} sur {total} articles"
                    ).classes("text-lg font-bold")
                    ui.label(
                        f"{remaining} restant"
                        if remaining == 1
                        else f"{remaining} restants"
                    ).classes("text-sm text-gray-500")

                ui.label(
                    f"{round(progress * 100)} %"
                ).classes(
                    "text-lg font-bold text-primary"
                )

            ui.linear_progress(
                value=progress
            ).props(
                "rounded size=14px color=positive "
                "track-color=grey-3"
            ).classes("w-full mt-3")

        undo_key = _undo_key(family_id)
        pending = app.storage.user.get(undo_key)

        if pending and float(
            pending.get("expires_at", 0)
        ) <= time.time():
            app.storage.user.pop(
                undo_key,
                None,
            )
            pending = None

        if pending:
            with ui.card().classes(
                "w-full p-3 border-l-4 border-positive"
            ):
                with ui.row().classes(
                    "w-full items-center justify-between gap-3"
                ):
                    ui.label(
                        f"« {pending['name']} » placé dans le panier."
                    ).classes(
                        "text-sm font-bold grow min-w-0 "
                        "whitespace-normal"
                    )

                    def undo_purchase():
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
                        render_shopping.refresh()

                    ui.button(
                        "Annuler",
                        icon="undo",
                        on_click=undo_purchase,
                    ).props("flat color=primary")

        if not current:
            with ui.card().classes(
                "w-full p-7 items-center text-center"
            ):
                ui.icon("celebration").classes(
                    "text-6xl text-positive"
                )
                ui.label(
                    "Courses terminées!"
                ).classes("text-2xl font-bold")
                ui.label(
                    "Tous les articles ont été cochés."
                ).classes("text-gray-500")

                def finish():
                    _clear_session(family_id)
                    ui.navigate.to("/?tab=besoins")

                ui.button(
                    "Terminer et revenir",
                    icon="done_all",
                    on_click=finish,
                ).props(
                    "color=positive size=lg"
                ).classes("w-full mt-3")
            return

        grouped = defaultdict(
            lambda: defaultdict(list)
        )
        store_order = {}
        category_order = {}

        for item in current:
            grouped[
                item["store"]
            ][item["category"]].append(item)
            store_order[
                item["store"]
            ] = item["store_order"]
            category_order[
                (
                    item["store"],
                    item["category"],
                )
            ] = item["category_order"]

        stores = sorted(
            grouped,
            key=lambda name: (
                store_order[name],
                name.casefold(),
            ),
        )

        open_storage_key = _open_key(family_id)
        all_keys = []

        for store in stores:
            all_keys.append(f"store::{store}")
            for category in grouped[store]:
                all_keys.append(
                    f"category::{store}::{category}"
                )

        open_groups = set(
            app.storage.user.get(
                open_storage_key,
                all_keys,
            )
        )

        def save_open(key, is_open):
            values = set(
                app.storage.user.get(
                    open_storage_key,
                    all_keys,
                )
            )
            if is_open:
                values.add(key)
            else:
                values.discard(key)

            app.storage.user[
                open_storage_key
            ] = sorted(values)

        ui.label(
            "Touchez un article lorsqu’il est dans le panier."
        ).classes("text-sm text-gray-500")

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
                save_open(
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
                "w-full bg-white rounded-xl shadow-sm "
                "border border-gray-200 overflow-hidden mt-2"
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
                    rows = sorted(
                        grouped[store][category],
                        key=lambda item: (
                            item["name"].casefold()
                        ),
                    )

                    def category_changed(
                        event,
                        key=category_key,
                    ):
                        save_open(
                            key,
                            bool(event.value),
                        )

                    with ui.expansion(
                        text=category,
                        caption=(
                            f"{len(rows)} item"
                            if len(rows) == 1
                            else f"{len(rows)} items"
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
                            "w-full gap-2 px-1 pb-2"
                        ):
                            for item in rows:

                                def purchase(
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
                                    render_shopping.refresh()

                                item_row = ui.row().classes(
                                    "w-full items-center flex-nowrap "
                                    "bg-white rounded-xl px-4 py-4 "
                                    "gap-3 cursor-pointer hover:bg-blue-50"
                                )
                                item_row.on(
                                    "click",
                                    purchase,
                                )

                                with item_row:
                                    with ui.column().classes(
                                        "gap-0 grow min-w-0"
                                    ):
                                        title = item["name"]
                                        if item["quantity"] != 1:
                                            title += (
                                                f" ({item['quantity']})"
                                            )

                                        ui.label(title).classes(
                                            "font-bold text-lg "
                                            "leading-snug whitespace-normal "
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

                                    ui.icon(
                                        "shopping_cart_checkout"
                                    ).classes(
                                        "text-3xl text-primary "
                                        "shrink-0 ml-auto"
                                    )

        def confirm_finish():
            with ui.dialog() as dialog:
                with ui.card().classes(
                    "w-full max-w-md p-5"
                ):
                    ui.label(
                        "Terminer les courses?"
                    ).classes("text-xl font-bold")
                    ui.label(
                        f"Il reste {remaining} article."
                        if remaining == 1
                        else (
                            f"Il reste {remaining} articles."
                        )
                    )
                    ui.label(
                        "Ils demeureront dans la liste des besoins."
                    ).classes("text-gray-600")

                    def finish_anyway():
                        _clear_session(family_id)
                        dialog.close()
                        ui.navigate.to(
                            "/?tab=besoins"
                        )

                    with ui.row().classes(
                        "w-full justify-end gap-2 mt-3"
                    ):
                        ui.button(
                            "Continuer",
                            on_click=dialog.close,
                        ).props("flat")
                        ui.button(
                            "Terminer",
                            icon="flag",
                            on_click=finish_anyway,
                        ).props("color=primary")

            dialog.open()

        ui.button(
            "Terminer les courses",
            icon="flag",
            on_click=confirm_finish,
        ).props(
            "outline color=primary"
        ).classes("w-full mt-4")

        ui.label(
            "Dernière vérification : "
            f"{datetime.now().strftime('%H h %M')}"
        ).classes(
            "text-xs text-gray-500 text-center w-full"
        )

    render_shopping()
    ui.timer(
        AUTO_REFRESH_SECONDS,
        render_shopping.refresh,
    )
