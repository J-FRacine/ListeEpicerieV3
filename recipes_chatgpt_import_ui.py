from __future__ import annotations

import inspect
import json

from nicegui import ui

from recipes_batch_import import (
    batch_summary,
    mark_batch_duplicates,
    parse_recipe_upload,
)
from recipes_chatgpt_import import (
    example_import_payload,
    import_recipe_candidate,
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
    raise ValueError("Le fichier téléversé est invalide.")


async def _read_upload_event(event):
    current_file = getattr(event, "file", None)
    if current_file is not None:
        reader = getattr(current_file, "read", None)
        if not callable(reader):
            raise ValueError("Le fichier ne peut pas être lu.")
        content = await _read_result(reader())
        filename = (
            getattr(current_file, "name", None)
            or getattr(event, "name", None)
            or "recette.json"
        )
        return str(filename), content

    legacy_content = getattr(event, "content", None)
    reader = getattr(legacy_content, "read", None)
    if not callable(reader):
        raise ValueError("Le fichier ne peut pas être lu.")
    content = await _read_result(reader())
    filename = getattr(event, "name", None) or "recette.json"
    return str(filename), content


def _result_message(result):
    parts = [
        f"« {result['name']} » importée",
        f"{result['ingredients_linked']} ingrédient(s) relié(s)",
    ]
    if result["items_created"]:
        parts.append(f"{result['items_created']} item(s) créé(s)")
    if result["items_reused"]:
        parts.append(f"{result['items_reused']} item(s) réutilisé(s)")
    if result.get("free_ingredients"):
        parts.append(
            f"{result['free_ingredients']} ingrédient(s) libre(s)"
        )
    if result["ingredients_skipped"]:
        parts.append(
            f"{result['ingredients_skipped']} ingrédient(s) ignoré(s)"
        )
    if result["nutrition_imported"]:
        parts.append("tableau nutritionnel importé")
    return " · ".join(parts) + "."


def _entry_status(row):
    if row.get("imported"):
        return "Importée", "positive"
    if row.get("import_error"):
        return "Erreur d’import", "negative"
    if row.get("error"):
        return "Fichier invalide", "negative"
    if row.get("duplicate_existing"):
        return "Déjà dans JF Apps", "grey"
    if row.get("duplicate_batch"):
        return "Doublon dans le lot", "orange"
    return "Prête", "positive"


def open_chatgpt_recipe_import_dialog(
    *,
    user_id,
    family_id,
    on_imported,
    allow_grocery_integration=True,
):
    from db import (
        get_categories,
        get_items,
        get_recipes,
        get_stores,
    )

    categories = (
        get_categories(user_id, family_id)
        if allow_grocery_integration
        else []
    )
    stores = (
        get_stores(user_id, family_id)
        if allow_grocery_integration
        else []
    )
    existing_items = (
        get_items(user_id, family_id)
        if allow_grocery_integration
        else []
    )
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

    state = {
        "raw_entries": [],
        "entries": [],
    }

    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-6xl p-5"):
            ui.label("Importer des recettes JSON").classes(
                "text-xl font-bold"
            )
            ui.label(
                "Sélectionnez un ou plusieurs fichiers JSON, ou un ZIP "
                "contenant des JSON. JF Apps analyse tout le lot avant "
                "l’import et ignore les doublons déjà présents."
            ).classes("text-sm text-gray-600")

            with ui.expansion(
                "Coller du JSON ou voir le JSON source",
                icon="code",
                value=False,
            ).classes("w-full") as json_source_expansion:
                json_input = ui.textarea(
                    label="JSON de la recette",
                    placeholder=(
                        '{"format":"jf_apps_recipe_import",'
                        '"version":1,...}'
                    ),
                ).props("autogrow").classes("w-full font-mono")
                ui.button(
                    "Ajouter ce JSON au lot",
                    icon="add",
                    on_click=lambda: add_pasted_json(),
                ).props("outline color=primary")

            ui.upload(
                label="Choisir des JSON ou un ZIP",
                on_upload=lambda event: on_upload(event),
                auto_upload=True,
                max_file_size=12_000_000,
                max_files=50,
            ).props(
                'accept=".json,.zip,application/json,application/zip" '
                "multiple"
            ).classes("w-full")

            ui.label(
                "Vous pouvez sélectionner plusieurs fichiers .json en une "
                "seule fois. Un ZIP peut contenir jusqu’à 100 JSON."
            ).classes("text-xs text-gray-500")

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

            create_missing = None
            category_select = None
            store_select = None

            if allow_grocery_integration:
                with ui.row().classes(
                    "w-full gap-3 items-end flex-wrap"
                ):
                    create_missing = ui.checkbox(
                        "Créer les ingrédients non reconnus comme items d’épicerie",
                        value=False,
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
                        "La création automatique d’items est désactivée."
                    ).classes("text-xs text-orange-700")
            else:
                ui.label(
                    "Ce compte a accès à Recettes sans accès à la Liste "
                    "d’épicerie. Les ingrédients importés resteront propres "
                    "aux recettes et aucun item d’épicerie ne sera créé ou relié."
                ).classes(
                    "text-sm bg-blue-50 border border-blue-200 "
                    "rounded-lg p-3"
                )

            summary_box = ui.row().classes(
                "w-full gap-2 items-center flex-wrap"
            )
            entries_box = ui.column().classes("w-full gap-2")

            def rebuild_entries():
                rows = mark_batch_duplicates(
                    state["raw_entries"],
                    existing_recipes,
                )
                for row in rows:
                    if row.get("candidate") and not row.get("error"):
                        row["preview"] = preview_recipe_import(
                            row["candidate"],
                            existing_items,
                            existing_recipes,
                        )
                state["entries"] = rows
                render_entries()

            def render_entries():
                summary_box.clear()
                entries_box.clear()
                info = batch_summary(state["entries"])

                with summary_box:
                    if not state["entries"]:
                        ui.label(
                            "Aucun fichier chargé."
                        ).classes("text-sm text-gray-500")
                    else:
                        ui.badge(
                            f"{info['total']} fichier(s)/recette(s)"
                        ).props("outline color=primary")
                        ui.badge(
                            f"{info['selected']} sélectionnée(s)"
                        ).props("color=primary")
                        if info["duplicates"]:
                            ui.badge(
                                f"{info['duplicates']} doublon(s)"
                            ).props("color=grey")
                        if info["invalid"]:
                            ui.badge(
                                f"{info['invalid']} invalide(s)"
                            ).props("color=negative")

                with entries_box:
                    if not state["entries"]:
                        return

                    with ui.row().classes(
                        "w-full gap-2 flex-wrap"
                    ):
                        ui.button(
                            "Tout sélectionner",
                            icon="done_all",
                            on_click=lambda: select_all(True),
                        ).props("flat dense color=primary")
                        ui.button(
                            "Tout désélectionner",
                            icon="remove_done",
                            on_click=lambda: select_all(False),
                        ).props("flat dense")
                        ui.button(
                            "Effacer le lot",
                            icon="delete_sweep",
                            on_click=clear_batch,
                        ).props("flat dense color=negative")

                    for row in state["entries"]:
                        status_label, status_color = _entry_status(row)
                        candidate = row.get("candidate")
                        disabled = bool(
                            row.get("error")
                            or row.get("duplicate_existing")
                            or row.get("duplicate_batch")
                            or row.get("imported")
                        )

                        with ui.card().classes(
                            "w-full p-3 shadow-none border border-gray-200"
                        ):
                            with ui.row().classes(
                                "w-full items-start gap-3 flex-nowrap"
                            ):
                                checkbox = ui.checkbox(
                                    value=bool(row.get("selected")),
                                    on_change=(
                                        lambda event, entry=row:
                                        set_selected(
                                            entry["entry_id"],
                                            bool(event.value),
                                        )
                                    ),
                                )
                                checkbox.set_enabled(not disabled)

                                with ui.column().classes(
                                    "gap-0 grow min-w-0"
                                ):
                                    ui.label(
                                        (
                                            candidate["name"]
                                            if candidate
                                            else row["source_name"]
                                        )
                                    ).classes(
                                        "font-bold whitespace-normal"
                                    )
                                    ui.label(
                                        row["source_name"]
                                    ).classes(
                                        "text-xs text-gray-500 "
                                        "whitespace-normal"
                                    )

                                    if candidate:
                                        category = (
                                            candidate.get("category") or ""
                                        )
                                        if candidate.get("subcategory"):
                                            category = (
                                                category
                                                + " › "
                                                + candidate["subcategory"]
                                            ).strip(" ›")
                                        summary = (
                                            f"{candidate['servings']} portion(s) · "
                                            f"{len(candidate['ingredients'])} ingrédient(s) · "
                                            f"{len(candidate['steps'])} étape(s)"
                                        )
                                        if category:
                                            summary += f" · {category}"
                                        ui.label(summary).classes(
                                            "text-sm text-gray-600 "
                                            "whitespace-normal"
                                        )

                                        preview = row.get("preview") or {}
                                        ui.label(
                                            f"{preview.get('matched_ingredients', 0)} item(s) reconnu(s) · "
                                            f"{len(preview.get('free_ingredients') or [])} libre(s) · "
                                            f"{len(preview.get('missing_ingredients') or [])} non reconnu(s)"
                                        ).classes(
                                            "text-xs text-gray-500"
                                        )

                                    if row.get("error"):
                                        ui.label(row["error"]).classes(
                                            "text-xs text-negative "
                                            "whitespace-normal"
                                        )
                                    if row.get("import_error"):
                                        ui.label(
                                            row["import_error"]
                                        ).classes(
                                            "text-xs text-negative "
                                            "whitespace-normal"
                                        )

                                ui.badge(status_label).props(
                                    f"color={status_color}"
                                )

            def set_selected(entry_id, selected):
                for row in state["entries"]:
                    if int(row["entry_id"]) == int(entry_id):
                        row["selected"] = bool(selected)
                        break
                render_entries()

            def select_all(selected):
                for row in state["entries"]:
                    row["selected"] = bool(
                        selected
                        and row.get("candidate")
                        and not row.get("error")
                        and not row.get("duplicate_existing")
                        and not row.get("duplicate_batch")
                        and not row.get("imported")
                    )
                render_entries()

            def clear_batch():
                state["raw_entries"] = []
                state["entries"] = []
                render_entries()

            async def on_upload(event):
                try:
                    filename, content = await _read_upload_event(event)
                    state["raw_entries"].extend(
                        parse_recipe_upload(filename, content)
                    )
                    rebuild_entries()
                except Exception as error:
                    ui.notify(
                        str(error),
                        type="warning",
                        timeout=8000,
                    )

            def add_pasted_json():
                text = str(json_input.value or "").strip()
                if not text:
                    ui.notify(
                        "Collez d’abord un JSON.",
                        type="warning",
                    )
                    return
                state["raw_entries"].extend(
                    parse_recipe_upload(
                        "JSON collé.json",
                        text.encode("utf-8"),
                    )
                )
                json_input.value = ""
                json_input.update()
                json_source_expansion.value = False
                json_source_expansion.update()
                rebuild_entries()

            def import_selected():
                selected = [
                    row
                    for row in state["entries"]
                    if row.get("selected")
                    and row.get("candidate")
                ]
                if not selected:
                    ui.notify(
                        "Sélectionnez au moins une recette prête.",
                        type="warning",
                    )
                    return

                create_items = bool(
                    create_missing.value
                    if create_missing is not None
                    else False
                )
                if (
                    allow_grocery_integration
                    and create_items
                    and (
                        category_select is None
                        or category_select.value is None
                    )
                ):
                    ui.notify(
                        "Choisissez une catégorie pour les nouveaux items.",
                        type="warning",
                    )
                    return

                imported_count = 0
                failed_count = 0
                result_messages = []

                for row in selected:
                    try:
                        result = import_recipe_candidate(
                            user_id,
                            family_id,
                            row["candidate"],
                            category_id=(
                                category_select.value
                                if category_select is not None
                                else None
                            ),
                            store_id=(
                                store_select.value
                                if store_select is not None
                                else None
                            ),
                            create_missing_items=create_items,
                            reuse_existing_items=bool(
                                allow_grocery_integration
                            ),
                        )
                    except Exception as error:
                        row["import_error"] = str(error)
                        row["selected"] = False
                        failed_count += 1
                        continue

                    row["imported"] = True
                    row["selected"] = False
                    imported_count += 1
                    result_messages.append(
                        _result_message(result)
                    )
                    existing_recipes.append({
                        "name": result["name"]
                    })

                if imported_count:
                    on_imported()

                render_entries()

                if imported_count:
                    message = (
                        f"{imported_count} recette(s) importée(s)"
                    )
                    if failed_count:
                        message += f" · {failed_count} échec(s)"
                    ui.notify(
                        message + ".",
                        type=(
                            "warning"
                            if failed_count
                            else "positive"
                        ),
                        timeout=9000,
                        close_button=True,
                    )
                elif failed_count:
                    ui.notify(
                        "Aucune recette importée. "
                        f"{failed_count} import(s) ont échoué.",
                        type="warning",
                        timeout=9000,
                        close_button=True,
                    )

            render_entries()

            with ui.row().classes(
                "w-full justify-end gap-2 mt-3 flex-wrap"
            ):
                ui.button(
                    "Fermer",
                    on_click=dialog.close,
                ).props("flat")
                ui.button(
                    "Importer la sélection",
                    icon="download",
                    on_click=import_selected,
                ).props("color=positive")

    dialog.open()
