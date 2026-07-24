from nicegui import app


DEFAULT_TAB = "items"
DEFAULT_ITEM_SORT = "Alphabétique"
DEFAULT_NEEDS_SORT = "Alphabétique"


def get_current_family_id():
    value = app.storage.user.get("current_family_id")

    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def set_current_family_id(family_id):
    if family_id is None:
        app.storage.user.pop("current_family_id", None)
    else:
        app.storage.user["current_family_id"] = int(family_id)


def get_current_tab():
    return app.storage.user.get("current_tab", DEFAULT_TAB)


def set_current_tab(tab):
    app.storage.user["current_tab"] = tab or DEFAULT_TAB


def get_tri_mode_items():
    return app.storage.user.get("tri_mode_items", DEFAULT_ITEM_SORT)


def set_tri_mode_items(mode):
    app.storage.user["tri_mode_items"] = mode or DEFAULT_ITEM_SORT


def get_tri_mode_needs():
    return app.storage.user.get("tri_mode_needs", DEFAULT_NEEDS_SORT)


def set_tri_mode_needs(mode):
    app.storage.user["tri_mode_needs"] = mode or DEFAULT_NEEDS_SORT
