from __future__ import annotations

import inspect
import json

from nicegui import ui

from recipes_chatgpt_import import (
    example_import_payload,
    import_recipe_candidate,
    parse_recipe_import,
    preview_recipe_import,
)
from recipes_extras import nutrition_rows


async def _read_result(value):
    if inspect.isawaitable(value):
        value = await value
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, bytes):
        return value
    raise ValueError("Le fichier JSON téléversé est invalide.")


async def _read_upload_event(event):
    current_file = getattr(event, "file", None)
    if current_file is not None:
        reader = getattr(current_file, "read", None)
        if not callable(reader):
            raise ValueError("Le fichier JSON ne peut pas être lu.")
        return await _read_result(reader())

    legacy_content = getattr(event, "content", None)
    reader = getattr(legacy_content, "read", None)
    if not callable(reader):
        raise ValueError("Le fichier JSON ne peut pas être lu.")
    return await _read_result(reader())


def _result_message(result):
    parts = [
        f"« {result['name']} » importée",
        f"{result['ingredients_linked']} ingrédient(s) relié(s)",
    ]
    if result["items_created"]:
        parts.append(f"{result['items_created']} item(s) créé(s)")
    if result["items_reused"]:
        parts.append(f"{result['items_reused']} item(s) réutilisé(s)")
    if result["ingredients_skipped"]:
        parts.append(
            f"{result['ingredients_skipped']} ingrédient(s) ignoré(s)"
        )
    if result["nutrition_imported"]:
        parts.append("tableau nutritionnel importé")
    return " · ".join(parts) + "."


def open_chatgpt_recipe_import_dialog(
    *,
    user_id,
    family_id,
    on_imported,
):
    from db import (
        get_categories,
        get_items,
        get_recipes,
        get_stores,
    )

    categories = get_categories(user_id, family_id)
    stores = get_stores(user_id, family_id)
    existing_items = get_items(user_id, family_id)
    existing_recipes = get_recipes(user_id, family_id)

    category_options = {
        row["id"]: row["name"]
        for row in categories
    }
    store_options = {
        row["id"]: row["name"]
        for row in stores
    }
    default_category = categories[0]["id"] if categories else None
    default_store = stores[0]["id"] if stores else None

    state = {"candidate": None, "preview": None}

    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-5xl p-5"):
            ui.label("Importer une recette ChatGPT").classes(
                "text-xl font-bold"
            )
            ui.label(
                "Collez le JSON que ChatGPT vous a fourni ou choisissez "
                "un fichier .json. JF Apps vérifie la recette et affiche "
                "un aperçu avant toute écriture."
            ).classes("text-sm text-gray-600")

            json_input = ui.textarea(
                label="JSON de la recette",
                placeholder='{"format":"jf_apps_recipe_import","version":1,...}',
            ).props("autogrow").classes("w-full font-mono")

            async def on_upload(event):
                try:
                    data = await _read_upload_event(event)
                    json_input.value = data.decode(
                        "utf-8-sig",
                        errors="strict",
                    )
                    json_input.update()
                    ui.notify(
                        "Fichier JSON chargé. Cliquez sur Analyser.",
                        type="positive",
                    )
                except Exception as error:
                    ui.notify(str(error), type="warning")

            ui.upload(
                label="Choisir un fichier JSON",
                on_upload=on_upload,
                auto_upload=True,
                max_file_size=2_000_000,
                max_files=1,
            ).props('accept=".json,application/json"').classes("w-full")

            with ui.expansion(
                "Voir un exemple du format accepté",
                icon="data_object",
            ).classes("w-full"):
                ui.code(
                    json.dumps(
                        example_import_payload(),
                        ensure_ascii=False,
                        indent=2,
                    )
                ).classes("w-full text-xs")

            with ui.row().classes(
                "w-full gap-3 items-end flex-wrap"
            ):
                create_missing = ui.checkbox(
                    "Créer les items d’épicerie manquants",
                    value=bool(categories),
                )
                category_select = ui.select(
                    category_options,
                    value=default_category,
                    label="Catégorie des nouveaux items",
                ).props("outlined dense").classes(
                    "grow min-w-[220px]"
                )
                store_select = ui.select(
                    store_options,
                    value=default_store,
                    label="Magasin des nouveaux items",
                ).props("outlined dense clearable").classes(
                    "grow min-w-[220px]"
                )

            if not categories:
                create_missing.value = False
                create_missing.disable()
                ui.label(
                    "Aucune catégorie d’épicerie n’est disponible. "
                    "Créez-en une avant d’autoriser la création "
                    "automatique d’items."
                ).classes("text-xs text-orange-700")

            preview_box = ui.column().classes("w-full gap-2")

            def analyze():
                try:
                    candidate = parse_recipe_import(
                        json_input.value or ""
                    )
                    preview = preview_recipe_import(
                        candidate,
                        existing_items,
                        existing_recipes,
                    )
                except Exception as error:
                    state["candidate"] = None
                    state["preview"] = None
                    preview_box.clear()
                    with preview_box:
                        ui.label(str(error)).classes("text-negative")
                    return

                state["candidate"] = candidate
                state["preview"] = preview
                preview_box.clear()

                extra = candidate.get("extra") or {}
                nutrition = extra.get("nutrition")
                with preview_box:
                    with ui.card().classes(
                        "w-full p-4 shadow-none bg-blue-50"
                    ):
                        with ui.row().classes(
                            "w-full items-center gap-2 flex-wrap"
                        ):
                            ui.label(candidate["name"]).classes(
                                "text-lg font-bold"
                            )
                            if preview["duplicate"]:
                                ui.badge(
                                    "Déjà dans JF Apps"
                                ).props("color=grey")
                            if candidate.get("category"):
                                category = candidate["category"]
                                if candidate.get("subcategory"):
                                    category += (
                                        " › "
                                        + candidate["subcategory"]
                                    )
                                ui.badge(category).props(
                                    "outline color=primary"
                                )

                        ui.label(
                            f"{candidate['servings']} portion(s) · "
                            f"{len(candidate['ingredients'])} ingrédient(s) · "
                            f"{len(candidate['steps'])} étape(s)"
                        ).classes("text-sm text-gray-600")

                        tags = extra.get("tags") or []
                        if tags:
                            ui.label(
                                "Étiquettes : " + ", ".join(tags)
                            ).classes("text-sm text-gray-600")

                        ui.label(
                            f"{preview['matched_ingredients']} item(s) reconnu(s) · "
                            f"{len(preview['missing_ingredients'])} à créer ou vérifier"
                        ).classes("text-sm text-gray-600")

                        if preview["missing_ingredients"]:
                            ui.label(
                                "Manquants : "
                                + ", ".join(
                                    preview["missing_ingredients"][:10]
                                )
                                + (
                                    "…"
                                    if len(
                                        preview["missing_ingredients"]
                                    ) > 10
                                    else ""
                                )
                            ).classes(
                                "text-xs text-orange-700 whitespace-normal"
                            )

                    if nutrition:
                        ui.label("Tableau nutritionnel").classes(
                            "font-bold mt-2"
                        )
                        rows = nutrition_rows(
                            nutrition,
                            candidate["servings"],
                        )
                        for row in rows:
                            with ui.row().classes(
                                "w-full text-sm gap-2 items-center"
                            ):
                                ui.label(row["label"]).classes("grow")
                                ui.label(
                                    row["per_serving_text"]
                                    + " / portion"
                                ).classes("text-right")
                        if nutrition.get("estimated"):
                            ui.badge("Estimation").props(
                                "outline color=orange"
                            )
                        if nutrition.get("serving_size"):
                            ui.label(
                                "Portion : " + nutrition["serving_size"]
                            ).classes("text-xs text-gray-600")
                        if nutrition.get("basis_note"):
                            ui.label(
                                nutrition["basis_note"]
                            ).classes(
                                "text-xs text-gray-600 whitespace-normal"
                            )
                        for nutrition_note in nutrition.get("notes") or []:
                            ui.label(
                                "• " + nutrition_note
                            ).classes(
                                "text-xs text-gray-600 whitespace-normal"
                            )

            def import_selected():
                candidate = state.get("candidate")
                preview = state.get("preview")
                if not candidate or not preview:
                    ui.notify(
                        "Analysez d’abord le JSON.",
                        type="warning",
                    )
                    return
                if preview.get("duplicate"):
                    ui.notify(
                        "Une recette du même nom existe déjà. "
                        "Elle ne sera pas écrasée.",
                        type="warning",
                    )
                    return
                if (
                    create_missing.value
                    and category_select.value is None
                ):
                    ui.notify(
                        "Choisissez une catégorie pour les nouveaux items.",
                        type="warning",
                    )
                    return

                try:
                    result = import_recipe_candidate(
                        user_id,
                        family_id,
                        candidate,
                        category_id=category_select.value,
                        store_id=store_select.value,
                        create_missing_items=bool(
                            create_missing.value
                        ),
                    )
                except Exception as error:
                    ui.notify(
                        str(error),
                        type="warning",
                        timeout=9000,
                        close_button=True,
                    )
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
                "w-full justify-between gap-2 mt-3 flex-wrap"
            ):
                ui.button(
                    "Analyser",
                    icon="fact_check",
                    on_click=analyze,
                ).props("outline color=primary")
                with ui.row().classes("gap-2"):
                    ui.button(
                        "Fermer",
                        on_click=dialog.close,
                    ).props("flat")
                    ui.button(
                        "Importer",
                        icon="download",
                        on_click=import_selected,
                    ).props("color=positive")
    dialog.open()
