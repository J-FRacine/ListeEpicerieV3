import time
from collections import defaultdict
from datetime import datetime

from nicegui import app, ui

from auth import get_current_user_id
from db import (
    get_accessible_families,
    get_items,
    toggle_needed,
)
from state import get_current_family_id
from utils import ensure_family_selected


AUTO_REFRESH_SECONDS = 5
UNDO_SECONDS = 10


def _session_key(family_id):
    return f"shopping_session_{family_id}"


def _undo_key(family_id):
    return f"shopping_pending_undo_{family_id}"


def _open_categories_key(family_id):
    return f"shopping_open_categories_{family_id}"


def has_active_shopping_session(family_id):
    if family_id is None:
        return False

    return bool(
        app.storage.user.get(
            _session_key(family_id)
        )
    )


def start_shopping_session(
    user_id,
    family_id,
):
    """Démarre ou redémarre le suivi des courses."""

    items = get_items(
        user_id,
        family_id,
    )

    needed_item_ids = [
        item["id"]
        for item in items
        if item["needed"] == 1
    ]

    if not needed_item_ids:
        raise ValueError(
            "La liste des besoins est vide."
        )

    app.storage.user[
        _session_key(family_id)
    ] = {
        "item_ids": needed_item_ids,
        "started_at": time.time(),
    }

    app.storage.user.pop(
        _undo_key(family_id),
        None,
    )


def _ensure_session(
    user_id,
    family_id,
    current_needs,
):
    session_key = _session_key(family_id)
    session = app.storage.user.get(
        session_key
    )

    current_ids = {
        item["id"]
        for item in current_needs
    }

    if not session:
        session = {
            "item_ids": sorted(
                current_ids
            ),
            "started_at": time.time(),
        }
    else:
        observed_ids = {
            int(item_id)
            for item_id in session.get(
                "item_ids",
                [],
            )
        }
        observed_ids.update(current_ids)
        session["item_ids"] = sorted(
            observed_ids
        )

    app.storage.user[
        session_key
    ] = session

    return session


def _clear_shopping_session(family_id):
    for key in (
        _session_key(family_id),
        _undo_key(family_id),
        _open_categories_key(family_id),
    ):
        app.storage.user.pop(
            key,
            None,
        )


def shopping_panel():
    user_id = get_current_user_id()
    family_id = get_current_family_id()

    if (
        user_id is None
        or not ensure_family_selected(
            family_id
        )
    ):
        return

    families = get_accessible_families(
        user_id
    )

    current_family = next(
        (
            family
            for family in families
            if family["id"] == family_id
        ),
        None,
    )

    if current_family is None:
        ui.label(
            "Cette famille n'est plus accessible."
        ).classes("text-negative")
        return

    family_name = current_family["name"]

    # ---------------------------------------------------------
    # EN-TÊTE DU MODE COURSES
    # ---------------------------------------------------------

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
            ).props(
                "flat round"
            ).tooltip(
                "Retour aux besoins"
            )

            with ui.column().classes(
                "gap-0 grow min-w-0"
            ):
                ui.label(
                    "Mode courses"
                ).classes(
                    "text-xl font-bold"
                )
                ui.label(
                    family_name
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
            ).tooltip(
                "Actualiser maintenant"
            )

    # ---------------------------------------------------------
    # CONTENU ACTUALISABLE
    # ---------------------------------------------------------

    @ui.refreshable
    def render_shopping():
        try:
            all_items = get_items(
                user_id,
                family_id,
            )
        except (
            ValueError,
            PermissionError,
        ) as error:
            ui.label(
                str(error)
            ).classes("text-negative")
            return

        current_needs = [
            item
            for item in all_items
            if item["needed"] == 1
        ]

        session = _ensure_session(
            user_id,
            family_id,
            current_needs,
        )

        observed_ids = {
            int(item_id)
            for item_id in session.get(
                "item_ids",
                [],
            )
        }
        current_ids = {
            item["id"]
            for item in current_needs
        }

        total_count = len(
            observed_ids
        )
        remaining_count = len(
            current_ids
        )
        completed_count = max(
            total_count - remaining_count,
            0,
        )
        progress_value = (
            completed_count / total_count
            if total_count > 0
            else 1.0
        )

        # -----------------------------------------------------
        # PROGRESSION
        # -----------------------------------------------------

        with ui.card().classes(
            "w-full p-4"
        ):
            with ui.row().classes(
                "w-full items-center "
                "justify-between gap-3"
            ):
                with ui.column().classes(
                    "gap-0"
                ):
                    ui.label(
                        (
                            f"{completed_count} sur "
                            f"{total_count} article"
                            if total_count == 1
                            else (
                                f"{completed_count} sur "
                                f"{total_count} articles"
                            )
                        )
                    ).classes(
                        "text-lg font-bold"
                    )

                    ui.label(
                        (
                            f"{remaining_count} restant"
                            if remaining_count == 1
                            else (
                                f"{remaining_count} restants"
                            )
                        )
                    ).classes(
                        "text-sm text-gray-500"
                    )

                ui.label(
                    f"{round(progress_value * 100)} %"
                ).classes(
                    "text-lg font-bold text-primary"
                )

            ui.linear_progress(
                value=progress_value,
            ).props(
                "rounded size=14px "
                "color=positive "
                "track-color=grey-3"
            ).classes("w-full mt-3")

            ui.label(
                "Actualisation automatique toutes les "
                f"{AUTO_REFRESH_SECONDS} secondes."
            ).classes(
                "text-xs text-gray-500 mt-2"
            )

        # -----------------------------------------------------
        # ANNULER LE DERNIER ARTICLE
        # -----------------------------------------------------

        undo_key = _undo_key(
            family_id
        )
        pending_undo = (
            app.storage.user.get(
                undo_key
            )
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
                    undo_key,
                    None,
                )
                pending_undo = None

        if pending_undo:
            with ui.card().classes(
                "w-full p-3 border-l-4 "
                "border-positive"
            ):
                with ui.row().classes(
                    "w-full items-center "
                    "justify-between gap-3"
                ):
                    ui.label(
                        f"« {pending_undo['name']} » "
                        "coché comme acheté."
                    ).classes(
                        "text-sm font-bold "
                        "grow min-w-0 "
                        "whitespace-normal"
                    ).style(
                        "overflow-wrap: anywhere;"
                    )

                    def undo_purchase():
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
                            undo_key,
                            None,
                        )
                        render_shopping.refresh()

                    ui.button(
                        "Annuler",
                        icon="undo",
                        on_click=undo_purchase,
                    ).props(
                        "flat color=primary"
                    ).classes("shrink-0")

        # -----------------------------------------------------
        # COURSES TERMINÉES
        # -----------------------------------------------------

        if not current_needs:
            with ui.card().classes(
                "w-full p-7 items-center text-center"
            ):
                ui.icon(
                    "celebration"
                ).classes(
                    "text-6xl text-positive"
                )
                ui.label(
                    "Courses terminées!"
                ).classes(
                    "text-2xl font-bold"
                )
                ui.label(
                    "Tous les articles de la liste "
                    "ont été cochés."
                ).classes(
                    "text-gray-500"
                )

                def finish_completed_session():
                    _clear_shopping_session(
                        family_id
                    )
                    ui.navigate.to(
                        "/?tab=besoins"
                    )

                ui.button(
                    "Terminer et revenir",
                    icon="done_all",
                    on_click=(
                        finish_completed_session
                    ),
                ).props(
                    "color=positive size=lg"
                ).classes(
                    "w-full mt-3"
                )

            return

        # -----------------------------------------------------
        # REGROUPEMENT PAR CATÉGORIE
        # -----------------------------------------------------

        needs_by_category = defaultdict(
            list
        )

        for item in current_needs:
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
            key=lambda name: name.casefold(),
        )

        open_key = _open_categories_key(
            family_id
        )
        stored_open = (
            app.storage.user.get(
                open_key
            )
        )

        if stored_open is None:
            open_categories = set(
                category_names
            )
        else:
            open_categories = {
                name
                for name in stored_open
                if name in category_names
            }

        def save_open_state(
            category_name,
            is_open,
        ):
            stored = app.storage.user.get(
                open_key
            )

            if stored is None:
                opened = set(
                    category_names
                )
            else:
                opened = set(stored)

            if is_open:
                opened.add(
                    category_name
                )
            else:
                opened.discard(
                    category_name
                )

            app.storage.user[
                open_key
            ] = sorted(
                opened,
                key=lambda name: (
                    name.casefold()
                ),
            )

        ui.label(
            "Touchez un article lorsqu'il "
            "est placé dans le panier."
        ).classes(
            "text-sm text-gray-500"
        )

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

            def expansion_changed(
                event,
                selected_category=(
                    category_name
                ),
            ):
                save_open_state(
                    selected_category,
                    bool(event.value),
                )

            with ui.expansion(
                text=category_name,
                caption=(
                    f"{len(category_items)} item"
                    if len(category_items) == 1
                    else (
                        f"{len(category_items)} items"
                    )
                ),
                icon="storefront",
                value=(
                    category_name
                    in open_categories
                ),
                on_value_change=(
                    expansion_changed
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
                    "w-full gap-2 px-1 pb-2"
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

                        def mark_purchased(
                            item_id=item["id"],
                            item_name=item["name"],
                        ):
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
                                undo_key
                            ] = {
                                "item_id": item_id,
                                "name": item_name,
                                "expires_at": (
                                    time.time()
                                    + UNDO_SECONDS
                                ),
                            }

                            render_shopping.refresh()

                        item_row = (
                            ui.row()
                            .classes(
                                "w-full items-center "
                                "flex-nowrap "
                                "bg-gray-100 "
                                "rounded-xl "
                                "px-4 py-4 gap-3 "
                                "cursor-pointer "
                                "hover:bg-blue-50"
                            )
                        )

                        item_row.on(
                            "click",
                            mark_purchased,
                        )

                        with item_row:
                            ui.label(
                                item_text
                            ).classes(
                                "font-bold text-lg "
                                "leading-snug "
                                "whitespace-normal "
                                "break-words pr-2"
                            ).style(
                                "flex: 1 1 0; "
                                "min-width: 0; "
                                "overflow-wrap: anywhere;"
                            )

                            ui.icon(
                                "shopping_cart_checkout"
                            ).classes(
                                "text-3xl "
                                "text-primary "
                                "shrink-0 ml-auto"
                            )

        # -----------------------------------------------------
        # TERMINER AVANT LA FIN
        # -----------------------------------------------------

        def confirm_finish():
            with ui.dialog() as dialog:
                with ui.card().classes(
                    "w-full max-w-md p-5"
                ):
                    ui.label(
                        "Terminer les courses?"
                    ).classes(
                        "text-xl font-bold"
                    )
                    ui.label(
                        (
                            f"Il reste {remaining_count} article."
                            if remaining_count == 1
                            else (
                                f"Il reste {remaining_count} "
                                "articles."
                            )
                        )
                    ).classes(
                        "text-gray-600"
                    )
                    ui.label(
                        "Les articles restants demeureront "
                        "dans la liste des besoins."
                    ).classes(
                        "text-gray-600"
                    )

                    def finish_anyway():
                        _clear_shopping_session(
                            family_id
                        )
                        dialog.close()
                        ui.navigate.to(
                            "/?tab=besoins"
                        )

                    with ui.row().classes(
                        "w-full justify-end "
                        "gap-2 mt-3"
                    ):
                        ui.button(
                            "Continuer les courses",
                            on_click=dialog.close,
                        ).props("flat")

                        ui.button(
                            "Terminer",
                            icon="stop_circle",
                            on_click=finish_anyway,
                        ).props(
                            "color=primary"
                        )

            dialog.open()

        ui.button(
            "Terminer les courses",
            icon="flag",
            on_click=confirm_finish,
        ).props(
            "outline color=primary"
        ).classes(
            "w-full mt-4"
        )

        ui.label(
            "Dernière vérification : "
            f"{datetime.now().strftime('%H h %M')}"
        ).classes(
            "text-xs text-gray-500 "
            "text-center w-full"
        )

    render_shopping()

    # Permet de voir les ajouts ou retraits faits
    # par un autre utilisateur pendant les courses.
    ui.timer(
        AUTO_REFRESH_SECONDS,
        render_shopping.refresh,
    )
