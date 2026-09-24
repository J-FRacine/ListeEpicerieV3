from __future__ import annotations

from nicegui import ui

from recipes_photo_data import (
    delete_recipe_photo,
    get_recipe_photo,
    save_recipe_photo,
)
from recipes_photo_images import (
    MAX_STORED_BYTES,
    MAX_UPLOAD_BYTES,
    normalize_recipe_photo,
    read_recipe_photo_upload,
    recipe_photo_to_data_url,
)


def _kb(value):
    try:
        return max(0, int(value or 0)) / 1024
    except (TypeError, ValueError):
        return 0.0


def open_recipe_photo_dialog(
    *,
    user_id,
    recipe,
    on_saved=None,
):
    try:
        current = get_recipe_photo(user_id, recipe["id"])
    except Exception as error:
        ui.notify(
            f"La photo n’a pas pu être chargée : {error}",
            type="warning",
        )
        current = None

    current_url = recipe_photo_to_data_url(current)

    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-xl p-5"):
            with ui.row().classes(
                "w-full items-start justify-between gap-3"
            ):
                with ui.column().classes("gap-0"):
                    ui.label("Photo de la recette").classes(
                        "text-xl font-bold"
                    )
                    ui.label(recipe["name"]).classes(
                        "text-sm text-gray-600"
                    )
                ui.button(
                    icon="close",
                    on_click=dialog.close,
                ).props("flat round")

            if current_url:
                ui.image(current_url).classes(
                    "w-full max-h-[420px] rounded-xl mt-3"
                ).props("fit=contain")
                ui.label(
                    (
                        f"{current.get('image_width') or '?'} × "
                        f"{current.get('image_height') or '?'} px · "
                        f"{_kb(current.get('image_size')):.0f} Ko stockés"
                    )
                ).classes(
                    "text-xs text-gray-500 text-center w-full"
                )
            else:
                with ui.card().classes(
                    "w-full h-48 items-center justify-center "
                    "bg-gray-50 shadow-none mt-3"
                ):
                    ui.icon("image").classes(
                        "text-6xl text-gray-300"
                    )
                    ui.label("Aucune photo").classes(
                        "text-sm text-gray-500"
                    )

            async def on_upload(event):
                try:
                    uploaded = await read_recipe_photo_upload(event)
                    normalized = normalize_recipe_photo(
                        uploaded["data"],
                        content_type=uploaded["content_type"],
                        file_name=uploaded["file_name"],
                    )
                    save_recipe_photo(
                        user_id,
                        recipe["id"],
                        normalized,
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
                if on_saved:
                    on_saved()
                ui.notify(
                    (
                        "Photo enregistrée et optimisée "
                        f"à environ {_kb(normalized['image_size']):.0f} Ko."
                    ),
                    type="positive",
                    timeout=6000,
                )

            def on_rejected(_event=None):
                ui.notify(
                    "Photo refusée. Utilisez un JPEG, PNG ou WEBP "
                    f"de {MAX_UPLOAD_BYTES // 1_000_000} Mo ou moins.",
                    type="warning",
                )

            uploader = ui.upload(
                label=(
                    "Remplacer la photo"
                    if current_url
                    else "Choisir une photo"
                ),
                on_upload=on_upload,
                on_rejected=on_rejected,
                auto_upload=True,
                max_file_size=MAX_UPLOAD_BYTES,
                max_files=1,
            ).classes("w-full mt-4")
            uploader.props(
                'accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"'
            )

            ui.label(
                "La photo est automatiquement orientée, réduite à "
                "1200 px maximum, convertie en JPEG et compressée "
                f"pour viser moins de {MAX_STORED_BYTES // 1000} Ko. "
                "Une petite vignette séparée est utilisée dans la liste."
            ).classes("text-xs text-gray-500")

            if current_url:
                def ask_delete():
                    with ui.dialog() as confirm:
                        with ui.card().classes(
                            "w-full max-w-md p-4"
                        ):
                            ui.label(
                                "Supprimer la photo?"
                            ).classes("text-xl font-bold")
                            ui.label(
                                "La recette sera conservée. "
                                "Seule sa photo sera supprimée."
                            ).classes("text-sm text-gray-600")

                            def remove():
                                try:
                                    delete_recipe_photo(
                                        user_id,
                                        recipe["id"],
                                    )
                                except Exception as error:
                                    ui.notify(
                                        str(error),
                                        type="warning",
                                    )
                                    return

                                confirm.close()
                                dialog.close()
                                if on_saved:
                                    on_saved()
                                ui.notify(
                                    "Photo supprimée.",
                                    type="positive",
                                )

                            with ui.row().classes(
                                "w-full justify-end gap-2 mt-3"
                            ):
                                ui.button(
                                    "Annuler",
                                    on_click=confirm.close,
                                ).props("flat")
                                ui.button(
                                    "Supprimer",
                                    icon="delete",
                                    on_click=remove,
                                ).props("color=negative")
                    confirm.open()

                with ui.row().classes(
                    "w-full justify-end mt-2"
                ):
                    ui.button(
                        "Supprimer la photo",
                        icon="delete",
                        on_click=ask_delete,
                    ).props("flat color=negative")
    dialog.open()
