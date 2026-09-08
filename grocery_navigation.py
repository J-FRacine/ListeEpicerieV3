from __future__ import annotations

GROCERY_NAV_CSS = r"""
.jf-grocery-primary-nav {
    width: 100%;
    padding: .35rem .45rem;
    border: 1px solid var(--jf-border);
    border-radius: 13px;
    background: var(--jf-surface);
    background: color-mix(in srgb, var(--jf-surface) 92%, transparent);
}

.jf-grocery-primary-nav-row {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: .3rem;
}

.jf-grocery-primary-nav-button {
    width: 100%;
    min-width: 0;
    min-height: 2.45rem;
    padding: .35rem .45rem;
    border-radius: 10px;
    color: var(--jf-muted);
}

.jf-grocery-primary-nav-button .q-btn__content {
    flex-wrap: nowrap;
    gap: .25rem;
    white-space: nowrap;
}

.jf-grocery-primary-nav-active {
    color: white !important;
    background: var(--jf-navy) !important;
    box-shadow: 0 6px 15px rgba(23, 53, 83, .18);
}

.jf-grocery-primary-nav-active .q-btn__content,
.jf-grocery-primary-nav-active .q-icon,
.jf-grocery-primary-nav-active .block {
    color: white !important;
}

@media (max-width: 520px) {
    .jf-grocery-primary-nav {
        padding: .25rem;
    }

    .jf-grocery-primary-nav-row {
        gap: .2rem;
    }

    .jf-grocery-primary-nav-button {
        min-height: 2.35rem;
        padding: .3rem .15rem;
        font-size: .76rem;
    }

    .jf-grocery-primary-nav-button .q-icon {
        font-size: 1.05rem;
    }
}

@media (max-width: 380px) {
    .jf-grocery-primary-nav-button {
        font-size: .71rem;
    }

    .jf-grocery-primary-nav-button .q-btn__content {
        gap: .12rem;
    }
}
"""

def install_grocery_navigation_styles(ui):
    """Installe les styles de navigation dans l'interface NiceGUI fournie."""

    ui.add_css(GROCERY_NAV_CSS, shared=True)


def grocery_navigation_entries(
    active_tab,
    needs_count=0,
    *,
    categories_enabled=True,
):
    """Retourne les trois destinations principales de la Liste d'épicerie."""

    needs_label = (
        f"Besoins {needs_count}"
        if needs_count > 0
        else "Besoins"
    )
    organization_label = (
        "Catégories"
        if categories_enabled
        else "Magasins"
    )
    organization_icon = (
        "category"
        if categories_enabled
        else "storefront"
    )

    return (
        {
            "tab": "items",
            "label": "Items",
            "icon": "inventory_2",
            "target": "/?tab=items",
            "active": active_tab == "items",
        },
        {
            "tab": "besoins",
            "label": needs_label,
            "icon": "shopping_cart",
            "target": "/?tab=besoins",
            "active": active_tab == "besoins",
        },
        {
            "tab": "categories",
            "label": organization_label,
            "icon": organization_icon,
            "target": "/?tab=categories",
            "active": active_tab == "categories",
        },
    )


def grocery_primary_navigation(
    ui,
    active_tab,
    needs_count=0,
    *,
    categories_enabled=True,
):
    """Affiche la navigation principale de l'épicerie dans la partie haute."""

    entries = grocery_navigation_entries(
        active_tab,
        needs_count,
        categories_enabled=categories_enabled,
    )

    with ui.element("nav").classes(
        "jf-grocery-primary-nav"
    ).props(
        'aria-label="Navigation principale de la Liste d’épicerie"'
    ):
        with ui.element("div").classes(
            "jf-grocery-primary-nav-row"
        ):
            for entry in entries:
                button = ui.button(
                    entry["label"],
                    icon=entry["icon"],
                    on_click=(
                        lambda _event=None, target=entry["target"]:
                        ui.navigate.to(target)
                    ),
                ).props(
                    "flat dense no-caps"
                ).classes(
                    "jf-grocery-primary-nav-button"
                )

                if entry["active"]:
                    button.classes(
                        add="jf-grocery-primary-nav-active"
                    )
