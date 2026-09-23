from __future__ import annotations

from nicegui import run, ui

from recipes_site_import import (
    DEFAULT_SITE_URL,
    crawl_google_site,
    import_recipe_candidates,
    preview_recipe_matches,
)


def _result_message(result):
    return (
        f"{result.get('recipes_imported', 0)} recette(s) importée(s), "
        f"{result.get('duplicates_skipped', 0)} doublon(s) ignoré(s), "
        f"{result.get('recipe_categories_created', 0)} catégorie(s) de recette créée(s), "
        f"{result.get('items_created', 0)} nouvel/nouveaux item(s), "
        f"{result.get('ingredients_linked', 0)} ingrédient(s) relié(s)."
    )


def _source_category_label(recipe):
    primary = str(recipe.get("source_category") or "").strip()
    secondary = str(recipe.get("source_subcategory") or "").strip()
    if primary and secondary:
        return f"{primary} › {secondary}"
    return primary


def open_recipe_site_import_dialog(*, user_id, family_id, on_imported):
    # Import tardif pour que les tests du parseur n'aient aucune dépendance PostgreSQL.
    from db import get_categories, get_items, get_recipes, get_stores

    categories = get_categories(user_id, family_id)
    stores = get_stores(user_id, family_id)
    existing_items = get_items(user_id, family_id)
    existing_recipes = get_recipes(user_id, family_id)

    category_options = {row["id"]: row["name"] for row in categories}
    store_options = {row["id"]: row["name"] for row in stores}
    default_category = categories[0]["id"] if categories else None
    default_store = stores[0]["id"] if stores else None
    state = {"preview": [], "checkboxes": []}

    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-5xl p-5"):
            ui.label("Importer depuis Recettes de l’Ours").classes("text-xl font-bold")
            ui.label(
                "JF Apps parcourt les pages publiques de votre ancien Google Sites. "
                "Les pages de catégories et sous-catégories servent uniquement à découvrir "
                "les vraies pages de recettes."
            ).classes("text-sm text-gray-600")

            url_input = ui.input(
                label="Adresse de départ",
                value=DEFAULT_SITE_URL,
            ).props("outlined").classes("w-full")

            with ui.card().classes("w-full p-3 shadow-none bg-blue-50"):
                ui.label("Import contrôlé").classes("font-bold")
                ui.label(
                    "Les recettes portant déjà le même nom sont ignorées. "
                    "Les catégories de recettes sont déduites de l’arborescence du site "
                    "(ex. Entrées, Les bases › Pain). Les ingrédients sont ensuite rapprochés "
                    "des items existants."
                ).classes("text-xs text-gray-600")

            with ui.row().classes("w-full gap-3 items-end flex-wrap"):
                create_missing = ui.checkbox(
                    "Créer les items manquants",
                    value=bool(categories),
                )
                category_select = ui.select(
                    category_options,
                    value=default_category,
                    label="Catégorie des nouveaux items d’épicerie",
                ).props("outlined dense").classes("grow min-w-[220px]")
                store_select = ui.select(
                    store_options,
                    value=default_store,
                    label="Magasin des nouveaux items",
                ).props("outlined dense clearable").classes("grow min-w-[220px]")

            if not categories:
                ui.label(
                    "Aucune catégorie d’épicerie n’est disponible. Créez-en au moins une "
                    "avant de permettre la création d’items manquants."
                ).classes("text-sm text-orange-700")
                create_missing.value = False
                create_missing.disable()

            preview_box = ui.column().classes("w-full gap-2")

            async def analyze():
                scan_button.disable()
                preview_box.clear()
                with preview_box:
                    with ui.row().classes("items-center gap-2"):
                        ui.spinner(size="sm")
                        ui.label("Analyse du site en cours…").classes(
                            "text-sm text-gray-600"
                        )
                try:
                    scan = await run.io_bound(
                        crawl_google_site,
                        url_input.value or DEFAULT_SITE_URL,
                    )
                    preview = preview_recipe_matches(
                        scan.get("recipes") or [],
                        existing_items,
                        existing_recipes,
                    )
                    state["preview"] = preview
                except Exception as error:
                    preview_box.clear()
                    with preview_box:
                        ui.label(str(error)).classes("text-negative")
                    scan_button.enable()
                    return

                preview_box.clear()
                state["checkboxes"] = []
                with preview_box:
                    with ui.row().classes(
                        "w-full gap-2 flex-wrap items-center"
                    ):
                        ui.badge(
                            f"{scan.get('pages_scanned', 0)} page(s) analysée(s)"
                        )
                        ui.badge(
                            f"{len(preview)} recette(s) reconnue(s)"
                        ).props("color=primary")
                        ui.badge(
                            f"{scan.get('sections_ignored', 0)} section(s) ignorée(s)"
                        ).props("color=grey")
                        if scan.get("pages_unrecognized"):
                            ui.badge(
                                f"{scan['pages_unrecognized']} page(s) à vérifier"
                            ).props("color=orange")
                        if scan.get("truncated"):
                            ui.badge(
                                "Analyse limitée aux premières pages"
                            ).props("color=orange")
                        if scan.get("errors"):
                            ui.badge(
                                f"{len(scan['errors'])} page(s) non lue(s)"
                            ).props("color=orange")

                    if not preview:
                        ui.label(
                            "Aucune vraie page de recette n’a été reconnue. "
                            "Les pages de navigation sont volontairement exclues."
                        ).classes("text-sm text-orange-700")

                    for index, recipe in enumerate(preview):
                        with ui.card().classes("w-full p-3 shadow-none"):
                            with ui.row().classes(
                                "w-full items-start gap-3 flex-nowrap"
                            ):
                                checkbox = ui.checkbox(
                                    value=not recipe.get("duplicate")
                                )
                                checkbox.set_enabled(
                                    not recipe.get("duplicate")
                                )
                                state["checkboxes"].append(
                                    (index, checkbox)
                                )
                                with ui.column().classes(
                                    "gap-1 grow min-w-0"
                                ):
                                    with ui.row().classes(
                                        "items-center gap-2 flex-wrap"
                                    ):
                                        ui.label(recipe["name"]).classes(
                                            "font-bold whitespace-normal"
                                        )
                                        if recipe.get("duplicate"):
                                            ui.badge(
                                                "Déjà dans JF Apps"
                                            ).props("color=grey")
                                        else:
                                            ui.badge(
                                                "1 portion"
                                                if recipe.get("servings") == 1
                                                else f"{recipe.get('servings', 4)} portions"
                                            ).props(
                                                "outline color=primary"
                                            )
                                        source_category = _source_category_label(
                                            recipe
                                        )
                                        if source_category:
                                            ui.badge(
                                                source_category
                                            ).props(
                                                "outline color=secondary"
                                            )

                                    total = len(
                                        recipe.get("ingredients") or []
                                    )
                                    missing = (
                                        recipe.get("missing_ingredients")
                                        or []
                                    )
                                    matched = recipe.get(
                                        "matched_ingredients", 0
                                    )
                                    ui.label(
                                        f"{total} ingrédient(s) · "
                                        f"{matched} item(s) déjà reconnu(s) · "
                                        f"{len(missing)} à créer ou vérifier"
                                    ).classes("text-xs text-gray-600")
                                    if missing:
                                        shown = ", ".join(
                                            str(name)
                                            for name in missing[:6]
                                        )
                                        suffix = (
                                            "…" if len(missing) > 6 else ""
                                        )
                                        ui.label(
                                            "Manquants : "
                                            + shown
                                            + suffix
                                        ).classes(
                                            "text-xs text-orange-700 whitespace-normal"
                                        )
                                    ui.link(
                                        "Voir la page source",
                                        recipe["source_url"],
                                        new_tab=True,
                                    ).classes("text-xs")
                scan_button.enable()

            async def import_selected():
                selected = [
                    state["preview"][index]
                    for index, checkbox in state["checkboxes"]
                    if checkbox.value
                ]
                if not selected:
                    ui.notify(
                        "Sélectionnez au moins une recette à importer.",
                        type="warning",
                    )
                    return
                if (
                    create_missing.value
                    and category_select.value is None
                ):
                    ui.notify(
                        "Choisissez la catégorie d’épicerie qui recevra les nouveaux items.",
                        type="warning",
                    )
                    return

                import_button.disable()
                try:
                    result = await run.io_bound(
                        import_recipe_candidates,
                        user_id,
                        family_id,
                        selected,
                        category_select.value,
                        store_select.value,
                        bool(create_missing.value),
                    )
                except Exception as error:
                    ui.notify(
                        str(error),
                        type="warning",
                        timeout=9000,
                        close_button=True,
                    )
                    import_button.enable()
                    return

                dialog.close()
                on_imported()
                ui.notify(
                    _result_message(result),
                    type="positive",
                    timeout=9000,
                    close_button=True,
                )

            with ui.row().classes(
                "w-full justify-between gap-2 mt-2 flex-wrap"
            ):
                scan_button = ui.button(
                    "Analyser le site",
                    icon="travel_explore",
                    on_click=analyze,
                ).props("outline color=primary")
                with ui.row().classes("gap-2"):
                    ui.button(
                        "Fermer",
                        on_click=dialog.close,
                    ).props("flat")
                    import_button = ui.button(
                        "Importer la sélection",
                        icon="download",
                        on_click=import_selected,
                    ).props("color=positive")

    dialog.open()
