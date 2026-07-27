from nicegui import app, ui

from auth import get_current_user
from db import (
    get_accessible_families,
    get_categories,
    get_items,
    get_recipes,
    get_stores,
    get_templates,
)
from state import (
    get_current_family_id,
    set_current_family_id,
)


ONBOARDING_CSS = r"""
.jf-guide-card {
    width: 100%;
    padding: 1.15rem;
}

.jf-flow-main {
    display: grid;
    grid-template-columns:
        minmax(8.4rem, 1fr)
        auto
        minmax(8.4rem, 1fr)
        auto
        minmax(8.4rem, 1fr)
        auto
        minmax(8.4rem, 1fr)
        auto
        minmax(8.4rem, 1fr);
    align-items: stretch;
    gap: 0.55rem;
    width: 100%;
}

.jf-flow-step {
    min-width: 0;
    padding: 0.85rem;
    border: 1px solid var(--jf-border);
    border-radius: 15px;
    background: var(--jf-surface);
}

.jf-flow-step-number {
    width: 1.8rem;
    height: 1.8rem;
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    border-radius: 999px;
    color: white;
    background: var(--jf-navy);
    font-weight: 800;
}

.jf-flow-step-icon {
    width: 2.45rem;
    height: 2.45rem;
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    border-radius: 12px;
    color: var(--jf-navy);
    background: var(--jf-blue-soft);
}

.jf-flow-arrow {
    display: grid;
    place-items: center;
    align-self: center;
    color: var(--jf-blue);
}

.jf-flow-branches {
    display: grid;
    grid-template-columns:
        repeat(3, minmax(0, 1fr));
    gap: 0.75rem;
    width: 100%;
}

.jf-flow-branch {
    min-width: 0;
    padding: 0.9rem;
    border: 1px solid var(--jf-border);
    border-radius: 15px;
    background: var(--jf-surface);
}

.jf-flow-note {
    width: 100%;
    padding: 0.8rem 0.95rem;
    border-left: 4px solid var(--jf-gold);
    border-radius: 12px;
    background: rgba(189, 149, 85, 0.10);
}

.jf-checklist-grid {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(min(100%, 18rem), 1fr));
    gap: 0.75rem;
    width: 100%;
}

.jf-checklist-item {
    width: 100%;
    min-height: 9rem;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 0.75rem;
    border: 1px solid var(--jf-border);
    border-radius: 16px;
    background: var(--jf-surface);
}

.jf-checklist-item-done {
    border-color: rgba(33, 145, 92, 0.38);
    background: rgba(33, 145, 92, 0.07);
}

.jf-checklist-status {
    width: 2rem;
    height: 2rem;
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    border-radius: 999px;
}

.jf-checklist-status-done {
    color: #167449;
    background: rgba(33, 145, 92, 0.14);
}

.jf-checklist-status-todo {
    color: var(--jf-navy);
    background: var(--jf-blue-soft);
}

@media (max-width: 860px) {
    .jf-flow-main {
        grid-template-columns: 1fr;
    }

    .jf-flow-arrow {
        transform: rotate(90deg);
        min-height: 1.3rem;
    }

    .jf-flow-branches {
        grid-template-columns: 1fr;
    }
}
"""

ui.add_css(
    ONBOARDING_CSS,
    shared=True,
)


def _flow_step(
    *,
    number,
    icon,
    title,
    description,
):
    with ui.element("div").classes(
        "jf-flow-step"
    ):
        with ui.row().classes(
            "w-full items-start gap-2 flex-nowrap"
        ):
            with ui.element("div").classes(
                "jf-flow-step-number"
            ):
                ui.label(str(number))

            with ui.element("div").classes(
                "jf-flow-step-icon"
            ):
                ui.icon(icon).classes("text-xl")

        ui.label(title).classes(
            "font-bold mt-2"
        )
        ui.label(description).classes(
            "text-sm jf-muted"
        )


def _flow_arrow():
    with ui.element("div").classes(
        "jf-flow-arrow"
    ):
        ui.icon(
            "arrow_forward"
        ).classes(
            "text-2xl"
        )


def organization_diagram(
    *,
    compact=False,
):
    """Affiche le schéma visuel de l'organisation des données."""

    with ui.card().classes(
        "jf-guide-card"
    ):
        with ui.row().classes(
            "w-full items-start justify-between "
            "gap-3 flex-wrap"
        ):
            with ui.column().classes("gap-0"):
                ui.label(
                    "Organisation des données"
                ).classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "L’ordre recommandé pour construire "
                    "votre liste d’épicerie."
                ).classes(
                    "text-sm jf-muted"
                )

            ui.icon(
                "account_tree"
            ).classes(
                "text-4xl text-primary"
            )

        with ui.element("div").classes(
            "jf-flow-main mt-3"
        ):
            _flow_step(
                number=1,
                icon="groups",
                title="Famille",
                description=(
                    "Votre espace privé, même si "
                    "vous utilisez l’app seul."
                ),
            )
            _flow_arrow()
            _flow_step(
                number=2,
                icon="storefront",
                title="Magasins",
                description=(
                    "Les endroits où vous faites "
                    "habituellement vos achats."
                ),
            )
            _flow_arrow()
            _flow_step(
                number=3,
                icon="category",
                title="Catégories",
                description=(
                    "Les rayons ou types de produits "
                    "qui organisent vos items."
                ),
            )
            _flow_arrow()
            _flow_step(
                number=4,
                icon="inventory_2",
                title="Items",
                description=(
                    "Votre catalogue familial. "
                    "C’est la base de tout le reste."
                ),
            )
            _flow_arrow()
            _flow_step(
                number=5,
                icon="shopping_cart",
                title="Utilisation",
                description=(
                    "Transformez vos items en besoins, "
                    "modèles et recettes."
                ),
            )

        if not compact:
            with ui.column().classes(
                "w-full items-center gap-1 mt-2"
            ):
                ui.icon(
                    "south"
                ).classes(
                    "text-2xl text-primary"
                )
                ui.label(
                    "À partir des items"
                ).classes(
                    "text-sm font-bold jf-muted"
                )

            with ui.element("div").classes(
                "jf-flow-branches"
            ):
                with ui.element("div").classes(
                    "jf-flow-branch"
                ):
                    with ui.row().classes(
                        "items-center gap-2"
                    ):
                        ui.icon(
                            "shopping_basket"
                        ).classes(
                            "text-2xl text-primary"
                        )
                        ui.label(
                            "Besoins"
                        ).classes(
                            "font-bold"
                        )
                    ui.label(
                        "La liste active de ce que vous "
                        "devez acheter."
                    ).classes(
                        "text-sm jf-muted"
                    )
                    ui.label(
                        "Puis : Mode courses"
                    ).classes(
                        "text-xs font-bold mt-2"
                    )

                with ui.element("div").classes(
                    "jf-flow-branch"
                ):
                    with ui.row().classes(
                        "items-center gap-2"
                    ):
                        ui.icon(
                            "checklist"
                        ).classes(
                            "text-2xl text-primary"
                        )
                        ui.label(
                            "Listes modèles"
                        ).classes(
                            "font-bold"
                        )
                    ui.label(
                        "Des listes réutilisables pour "
                        "les achats qui reviennent."
                    ).classes(
                        "text-sm jf-muted"
                    )

                with ui.element("div").classes(
                    "jf-flow-branch"
                ):
                    with ui.row().classes(
                        "items-center gap-2"
                    ):
                        ui.icon(
                            "restaurant_menu"
                        ).classes(
                            "text-2xl text-primary"
                        )
                        ui.label(
                            "Recettes"
                        ).classes(
                            "font-bold"
                        )
                    ui.label(
                        "Des ingrédients réutilisant "
                        "les items de votre famille."
                    ).classes(
                        "text-sm jf-muted"
                    )

            with ui.element("div").classes(
                "jf-flow-note mt-3"
            ):
                with ui.row().classes(
                    "items-start gap-2 flex-nowrap"
                ):
                    ui.icon(
                        "public"
                    ).classes(
                        "text-xl text-primary shrink-0"
                    )
                    ui.label(
                        "La Bibliothèque partagée permet de "
                        "copier des recettes et listes modèles "
                        "publiées par d’autres familles. La copie "
                        "devient ensuite indépendante dans votre famille."
                    ).classes(
                        "text-sm"
                    )


def _navigate_to_categories_section(
    family_id,
    section,
):
    app.storage.user[
        f"categories_active_section_{family_id}"
    ] = section

    ui.navigate.to(
        "/?tab=categories"
    )


def _checklist_card(
    *,
    number,
    title,
    description,
    done,
    action_label,
    icon,
    on_click,
):
    classes = (
        "jf-checklist-item "
        "jf-checklist-item-done"
        if done
        else "jf-checklist-item"
    )

    with ui.element("div").classes(
        classes
    ):
        with ui.row().classes(
            "w-full items-start gap-3 flex-nowrap"
        ):
            status_classes = (
                "jf-checklist-status "
                "jf-checklist-status-done"
                if done
                else (
                    "jf-checklist-status "
                    "jf-checklist-status-todo"
                )
            )

            with ui.element("div").classes(
                status_classes
            ):
                ui.icon(
                    "check"
                    if done
                    else icon
                ).classes(
                    "text-lg"
                )

            with ui.column().classes(
                "gap-0 grow min-w-0"
            ):
                ui.label(
                    f"{number}. {title}"
                ).classes(
                    "font-bold"
                )
                ui.label(
                    description
                ).classes(
                    "text-sm jf-muted"
                )

        ui.button(
            (
                "Vérifier"
                if done
                else action_label
            ),
            icon=(
                "check_circle"
                if done
                else "arrow_forward"
            ),
            on_click=on_click,
        ).props(
            (
                "flat color=positive"
                if done
                else "flat color=primary"
            )
        ).classes(
            "self-start"
        )


def getting_started_panel():
    user = get_current_user()

    if user is None:
        return

    families = get_accessible_families(
        user["id"]
    )

    current_family = None

    if families:
        current_family_id = (
            get_current_family_id()
        )

        current_family = next(
            (
                family
                for family in families
                if family["id"]
                == current_family_id
            ),
            families[0],
        )

        if (
            current_family_id
            != current_family["id"]
        ):
            set_current_family_id(
                current_family["id"]
            )

    family_id = (
        current_family["id"]
        if current_family
        else None
    )

    stores = []
    categories = []
    items = []
    templates = []
    recipes = []

    if family_id is not None:
        try:
            stores = get_stores(
                user["id"],
                family_id,
            )
            categories = get_categories(
                user["id"],
                family_id,
            )
            items = get_items(
                user["id"],
                family_id,
            )
            templates = get_templates(
                user["id"],
                family_id,
            )
            recipes = get_recipes(
                user["id"],
                family_id,
            )
        except (
            ValueError,
            PermissionError,
        ):
            stores = []
            categories = []
            items = []
            templates = []
            recipes = []

    required_statuses = [
        bool(families),
        bool(stores),
        bool(categories),
        bool(items),
    ]

    completed_required = sum(
        1
        for status in required_statuses
        if status
    )

    with ui.row().classes(
        "w-full items-start justify-between "
        "gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label(
                "Commencer ici"
            ).classes(
                "text-2xl font-bold"
            )
            ui.label(
                "Suivez ces étapes pour préparer "
                "rapidement votre liste d’épicerie."
            ).classes(
                "text-sm jf-muted"
            )

        ui.icon(
            "rocket_launch"
        ).classes(
            "text-4xl text-primary"
        )

    with ui.card().classes(
        "w-full p-4 border-l-4 border-primary"
    ):
        with ui.row().classes(
            "w-full items-center justify-between "
            "gap-3 flex-wrap"
        ):
            with ui.column().classes(
                "gap-0 grow min-w-0"
            ):
                ui.label(
                    (
                        f"{completed_required} étape"
                        if completed_required == 1
                        else (
                            f"{completed_required} étapes"
                        )
                    )
                    + " essentielles sur 4 terminées"
                ).classes(
                    "font-bold"
                )

                ui.label(
                    (
                        f"Famille active : "
                        f"{current_family['name']}"
                        if current_family
                        else (
                            "Commencez par créer votre famille. "
                            "Elle est obligatoire, même pour "
                            "une seule personne."
                        )
                    )
                ).classes(
                    "text-sm jf-muted"
                )

            ui.label(
                f"{round(completed_required / 4 * 100)} %"
            ).classes(
                "text-xl font-bold text-primary"
            )

        ui.linear_progress(
            value=completed_required / 4,
        ).props(
            "rounded size=13px color=positive "
            "track-color=grey-3"
        ).classes(
            "w-full mt-3"
        )

    organization_diagram()

    with ui.row().classes(
        "w-full items-center justify-between "
        "gap-2 flex-wrap"
    ):
        ui.label(
            "Votre parcours de démarrage"
        ).classes(
            "text-xl font-bold"
        )
        ui.label(
            "Les modèles et recettes sont facultatifs."
        ).classes(
            "text-sm jf-muted"
        )

    with ui.element("div").classes(
        "jf-checklist-grid"
    ):
        _checklist_card(
            number=1,
            title="Créer une famille",
            description=(
                "La famille contient toutes vos données. "
                "Elle est nécessaire même si vous êtes seul."
            ),
            done=bool(families),
            action_label="Créer ma famille",
            icon="groups",
            on_click=lambda: ui.navigate.to(
                "/?tab=familles"
            ),
        )

        _checklist_card(
            number=2,
            title="Ajouter vos magasins",
            description=(
                "Exemples : IGA, Costco, pharmacie "
                "ou quincaillerie."
            ),
            done=bool(stores),
            action_label="Ajouter un magasin",
            icon="storefront",
            on_click=(
                (
                    lambda: _navigate_to_categories_section(
                        family_id,
                        "stores",
                    )
                )
                if family_id is not None
                else (
                    lambda: ui.navigate.to(
                        "/?tab=familles"
                    )
                )
            ),
        )

        _checklist_card(
            number=3,
            title="Créer vos catégories",
            description=(
                "Exemples : Produits laitiers, "
                "Fruits et légumes, Entretien."
            ),
            done=bool(categories),
            action_label="Ajouter une catégorie",
            icon="category",
            on_click=(
                (
                    lambda: _navigate_to_categories_section(
                        family_id,
                        "categories",
                    )
                )
                if family_id is not None
                else (
                    lambda: ui.navigate.to(
                        "/?tab=familles"
                    )
                )
            ),
        )

        _checklist_card(
            number=4,
            title="Ajouter vos premiers items",
            description=(
                "Les items alimentent ensuite les besoins, "
                "les listes modèles et les recettes."
            ),
            done=bool(items),
            action_label="Ajouter un item",
            icon="inventory_2",
            on_click=(
                (
                    lambda: ui.navigate.to(
                        "/?tab=items"
                    )
                )
                if family_id is not None
                else (
                    lambda: ui.navigate.to(
                        "/?tab=familles"
                    )
                )
            ),
        )

        _checklist_card(
            number=5,
            title="Préparer une liste modèle",
            description=(
                "Facultatif : réutilisez une liste "
                "pour vos achats récurrents."
            ),
            done=bool(templates),
            action_label="Créer un modèle",
            icon="checklist",
            on_click=(
                (
                    lambda: ui.navigate.to(
                        "/?tab=modeles"
                    )
                )
                if family_id is not None
                else (
                    lambda: ui.navigate.to(
                        "/?tab=familles"
                    )
                )
            ),
        )

        _checklist_card(
            number=6,
            title="Créer une recette",
            description=(
                "Facultatif : ajoutez tous les ingrédients "
                "aux besoins en une opération."
            ),
            done=bool(recipes),
            action_label="Créer une recette",
            icon="restaurant_menu",
            on_click=(
                (
                    lambda: ui.navigate.to(
                        "/?tab=recettes"
                    )
                )
                if family_id is not None
                else (
                    lambda: ui.navigate.to(
                        "/?tab=familles"
                    )
                )
            ),
        )

    with ui.card().classes(
        "w-full p-4"
    ):
        with ui.row().classes(
            "w-full items-center justify-between "
            "gap-3 flex-wrap"
        ):
            with ui.column().classes("gap-0"):
                ui.label(
                    "Besoin de plus de détails?"
                ).classes(
                    "font-bold"
                )
                ui.label(
                    "Le manuel explique chaque écran "
                    "et chaque bouton."
                ).classes(
                    "text-sm jf-muted"
                )

            ui.button(
                "Ouvrir le manuel complet",
                icon="menu_book",
                on_click=lambda: ui.navigate.to(
                    "/?tab=manuel"
                ),
            ).props(
                "outline color=primary"
            )
