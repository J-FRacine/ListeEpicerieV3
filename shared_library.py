from nicegui import ui

from auth import get_current_user_id
from db import (
    copy_shared_content_to_family,
    get_accessible_families,
    get_shared_content,
    get_shared_library,
)
from state import (
    get_current_family_id,
    set_current_family_id,
)


def _content_label(content_type):
    return "Liste modèle" if content_type == "template" else "Recette"


def _line_count_text(content_type, count):
    if content_type == "template":
        return f"{count} item" if count == 1 else f"{count} items"
    return f"{count} ingrédient" if count == 1 else f"{count} ingrédients"


def _copy_result_message(result):
    message = f"« {result['name']} » a été copiée dans votre famille."
    details = []
    if result["items_reused"]:
        details.append(
            "1 item réutilisé"
            if result["items_reused"] == 1
            else f"{result['items_reused']} items réutilisés"
        )
    if result["items_created"]:
        details.append(
            f"{result['items_created']} item créé"
            if result["items_created"] == 1
            else f"{result['items_created']} items créés"
        )
    if result["ambiguous_matches"]:
        details.append(
            f"{result['ambiguous_matches']} correspondance multiple"
            if result["ambiguous_matches"] == 1
            else f"{result['ambiguous_matches']} correspondances multiples"
        )
    if result.get("duplicate_lines_merged"):
        details.append(
            "1 ligne semblable fusionnée"
            if result["duplicate_lines_merged"] == 1
            else (
                f"{result['duplicate_lines_merged']} "
                "lignes semblables fusionnées"
            )
        )
    if details:
        message += " " + ", ".join(details) + "."
    return message


def shared_library_panel():
    user_id = get_current_user_id()
    family_id = get_current_family_id()

    if user_id is None:
        return

    families = get_accessible_families(user_id)
    valid_family_ids = {
        family["id"]
        for family in families
    }

    if families and family_id not in valid_family_ids:
        family_id = families[0]["id"]
        set_current_family_id(family_id)

    if not families:
        with ui.card().classes("w-full p-6"):
            ui.icon("groups").classes("text-4xl text-primary")
            ui.label("Créez d’abord votre famille").classes(
                "text-xl font-bold"
            )
            ui.label(
                "Une famille est nécessaire pour recevoir une copie "
                "privée d’une recette ou d’une liste modèle."
            ).classes("text-gray-600")
            with ui.row().classes("gap-2 flex-wrap mt-2"):
                ui.button(
                    "Créer ma famille",
                    icon="group_add",
                    on_click=lambda: ui.navigate.to("/?tab=familles"),
                ).props("color=primary")
                ui.button(
                    "Voir le guide de démarrage",
                    icon="help_outline",
                    on_click=lambda: ui.navigate.to("/?tab=manuel"),
                ).props("outline color=primary")
        return

    family_id = get_current_family_id()
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
        label="Copier dans la famille",
        on_change=lambda event: (
            set_current_family_id(family_by_name[event.value]),
            ui.navigate.to("/?tab=bibliotheque"),
        ),
    ).classes("w-full")

    with ui.row().classes(
        "w-full items-start justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Bibliothèque partagée").classes(
                "text-2xl font-bold"
            )
            ui.label(
                "Consultez les recettes et listes modèles publiées, "
                "puis créez une copie indépendante dans votre famille."
            ).classes("text-sm text-gray-500")
        ui.icon("public").classes("text-4xl text-primary")

    with ui.card().classes("w-full p-4 border-l-4 border-primary"):
        ui.label("Confidentialité").classes("font-bold")
        ui.label(
            "La bibliothèque ne montre que les données génériques publiées. "
            "Les magasins, notes privées, prix, besoins et identifiants "
            "internes des familles ne sont jamais affichés."
        ).classes("text-sm text-gray-600")

    with ui.row().classes("w-full gap-2 flex-wrap"):
        ui.button(
            "Mes listes modèles",
            icon="checklist",
            on_click=lambda: ui.navigate.to("/?tab=modeles"),
        ).props("flat color=primary")
        ui.button(
            "Mes recettes",
            icon="restaurant_menu",
            on_click=lambda: ui.navigate.to("/?tab=recettes"),
        ).props("flat color=primary")

    filter_state = {"type": "", "search": ""}

    type_toggle = ui.toggle(
        {
            "all": "Tout",
            "recipe": "Recettes",
            "template": "Listes modèles",
        },
        value="all",
    ).props("no-caps").classes("w-full sm:w-auto")

    search_input = ui.input(
        label="Rechercher dans la bibliothèque",
        placeholder="Nom, ingrédient, item ou catégorie",
    ).props(
        "clearable debounce=150 autocomplete=off"
    ).classes("w-full")
    with search_input.add_slot("prepend"):
        ui.icon("search")

    def open_preview(summary):
        try:
            content = get_shared_content(
                user_id,
                summary["id"],
            )
        except (ValueError, PermissionError) as error:
            ui.notify(str(error), type="warning")
            render_library.refresh()
            return

        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-2xl p-5"):
                with ui.row().classes(
                    "w-full items-start justify-between gap-3"
                ):
                    with ui.column().classes("gap-0 min-w-0 grow"):
                        ui.label(content["name"]).classes(
                            "text-2xl font-bold whitespace-normal"
                        ).style("overflow-wrap:anywhere;")
                        ui.label(
                            _content_label(content["content_type"])
                        ).classes("text-sm text-primary font-bold")
                    ui.button(
                        icon="close",
                        on_click=dialog.close,
                    ).props("flat round")

                if content["description"]:
                    ui.label(content["description"]).classes(
                        "text-sm text-gray-600 whitespace-normal"
                    ).style("overflow-wrap:anywhere;")

                if content["content_type"] == "recipe":
                    ui.label(
                        f"{content['servings']} portion"
                        if content["servings"] == 1
                        else f"{content['servings']} portions"
                    ).classes("text-sm text-gray-500")

                ui.separator()
                ui.label(
                    "Items" if content["content_type"] == "template" else "Ingrédients"
                ).classes("text-lg font-bold")

                for line in content["lines"]:
                    with ui.row().classes(
                        "w-full items-start flex-nowrap gap-3 py-2"
                    ):
                        ui.icon("check_circle_outline").classes(
                            "text-primary text-xl shrink-0"
                        )
                        with ui.column().classes("gap-0 grow min-w-0"):
                            label = (
                                f"{line['item_name']} ({line['quantity']})"
                                if line["quantity"] != 1
                                else line["item_name"]
                            )
                            ui.label(label).classes(
                                "font-bold whitespace-normal"
                            ).style("overflow-wrap:anywhere;")
                            if line["category_name"]:
                                ui.label(
                                    f"Catégorie suggérée : {line['category_name']}"
                                ).classes("text-xs text-gray-500")
                            if line["note"]:
                                ui.label(line["note"]).classes(
                                    "text-xs text-gray-600 whitespace-normal"
                                ).style("overflow-wrap:anywhere;")

                if content["content_type"] == "recipe" and content["instructions"]:
                    ui.separator()
                    ui.label("Préparation").classes("text-lg font-bold")
                    ui.label(content["instructions"]).classes(
                        "text-sm whitespace-pre-wrap text-gray-700"
                    ).style("overflow-wrap:anywhere;")

                def copy_content():
                    try:
                        result = copy_shared_content_to_family(
                            user_id,
                            content["id"],
                            get_current_family_id(),
                        )
                    except (ValueError, PermissionError) as error:
                        ui.notify(str(error), type="warning")
                        return

                    dialog.close()
                    ui.notify(
                        _copy_result_message(result),
                        type="positive",
                        timeout=8000,
                        close_button=True,
                    )

                with ui.row().classes(
                    "w-full justify-end gap-2 mt-3 flex-wrap"
                ):
                    ui.button("Fermer", on_click=dialog.close).props("flat")
                    ui.button(
                        "Copier dans ma famille",
                        icon="content_copy",
                        on_click=copy_content,
                    ).props("color=primary")

        dialog.open()

    @ui.refreshable
    def render_library():
        try:
            rows = get_shared_library(
                user_id,
                filter_state["type"],
                filter_state["search"],
            )
        except (ValueError, PermissionError) as error:
            ui.label(str(error)).classes("text-negative")
            return

        ui.label(
            f"{len(rows)} publication"
            if len(rows) == 1
            else f"{len(rows)} publications"
        ).classes("text-sm text-gray-500")

        if not rows:
            with ui.card().classes("w-full p-7 items-center text-center"):
                ui.icon("library_books").classes("text-5xl text-primary")
                ui.label("Aucun résultat").classes("text-xl font-bold")
                ui.label(
                    "Aucun contenu publié ne correspond aux critères actuels."
                ).classes("text-gray-500")
            return

        for row in rows:
            with ui.card().classes("w-full p-4"):
                with ui.row().classes(
                    "w-full items-start justify-between gap-3 flex-nowrap"
                ):
                    with ui.column().classes("gap-1 grow min-w-0"):
                        ui.badge(
                            _content_label(row["content_type"])
                        ).props("outline color=primary")
                        ui.label(row["name"]).classes(
                            "text-lg font-bold whitespace-normal"
                        ).style("overflow-wrap:anywhere;")
                        if row["description"]:
                            ui.label(row["description"]).classes(
                                "text-sm text-gray-600 whitespace-normal"
                            ).style("overflow-wrap:anywhere;")
                        details = _line_count_text(
                            row["content_type"],
                            row["line_count"],
                        )
                        if row["content_type"] == "recipe":
                            portions = (
                                f"{row['servings']} portion"
                                if row["servings"] == 1
                                else f"{row['servings']} portions"
                            )
                            details = f"{portions} · {details}"
                        ui.label(details).classes("text-xs text-gray-500")

                    ui.button(
                        icon="visibility",
                        on_click=lambda selected=row: open_preview(selected),
                    ).props("flat round color=primary").tooltip("Consulter")

                ui.button(
                    "Consulter et copier",
                    icon="content_copy",
                    on_click=lambda selected=row: open_preview(selected),
                ).props("outline color=primary").classes("mt-2")

    def type_changed(event):
        filter_state["type"] = (
            ""
            if event.value == "all"
            else event.value or ""
        )
        render_library.refresh()

    def search_changed(event):
        filter_state["search"] = event.value or ""
        render_library.refresh()

    type_toggle.on_value_change(type_changed)
    search_input.on_value_change(search_changed)
    render_library()
