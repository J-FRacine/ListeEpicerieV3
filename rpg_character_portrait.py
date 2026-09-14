"""Bloc Portrait affiché dans la bannière d'un personnage JDR.

Aucun import direct de NiceGUI ou de la base : les dépendances sont injectées.
"""
from __future__ import annotations


def build_portrait_block(
    *,
    ui,
    user_id,
    character,
    get_rpg_portrait,
    save_rpg_portrait,
    delete_rpg_portrait,
    normalize_portrait,
    portrait_to_data_url,
    read_upload_event,
    notify_error,
):
    try:
        portrait = get_rpg_portrait(
            user_id,
            character["id"],
        )
    except Exception as error:
        notify_error(
            error,
            "Le portrait n’a pas pu être chargé.",
        )
        portrait = None

    data_url = portrait_to_data_url(portrait)

    def open_large_preview():
        if not data_url:
            return

        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-3xl p-3"):
                with ui.row().classes(
                    "w-full items-center justify-between gap-2"
                ):
                    ui.label(
                        character["character_name"]
                    ).classes("text-xl font-bold")
                    ui.button(
                        icon="close",
                        on_click=dialog.close,
                    ).props("flat round")

                ui.image(data_url).classes(
                    "w-full max-h-[75vh] rounded-xl"
                ).props("fit=contain")
        dialog.open()

    def open_manager():
        with ui.dialog() as manager:
            with ui.card().classes("w-full max-w-xl p-5"):
                with ui.row().classes(
                    "w-full items-start justify-between gap-3"
                ):
                    with ui.column().classes("gap-0"):
                        ui.label(
                            "Portrait du personnage"
                        ).classes("text-xl font-bold")
                        ui.label(
                            "JPEG, PNG ou WEBP. "
                            "La photo est redimensionnée et enregistrée "
                            "dans les données privées du personnage."
                        ).classes("text-sm jf-muted")
                    ui.button(
                        icon="close",
                        on_click=manager.close,
                    ).props("flat round")

                if data_url:
                    ui.image(data_url).classes(
                        "w-52 h-64 rounded-xl mx-auto mt-3"
                    ).props("fit=cover")
                else:
                    with ui.card().classes(
                        "w-52 h-64 mx-auto mt-3 "
                        "items-center justify-center bg-white/10"
                    ):
                        ui.icon("person").classes(
                            "text-7xl text-gray-400"
                        )
                        ui.label("Aucun portrait").classes(
                            "text-sm jf-muted"
                        )

                async def on_upload(event):
                    try:
                        uploaded = await read_upload_event(event)
                        normalized = normalize_portrait(
                            uploaded["data"],
                            content_type=uploaded["content_type"],
                            file_name=uploaded["file_name"],
                        )
                        save_rpg_portrait(
                            user_id,
                            character["id"],
                            normalized,
                        )
                    except Exception as error:
                        notify_error(
                            error,
                            "La photo n’a pas pu être enregistrée.",
                        )
                        return

                    manager.close()
                    ui.notify(
                        "Portrait enregistré.",
                        type="positive",
                    )
                    ui.navigate.reload()

                def on_rejected(_event=None):
                    ui.notify(
                        "Photo refusée. Utilisez un JPEG, PNG ou WEBP "
                        "de 8 Mo ou moins.",
                        type="warning",
                    )

                uploader = ui.upload(
                    label=(
                        "Remplacer la photo"
                        if data_url
                        else "Choisir une photo"
                    ),
                    on_upload=on_upload,
                    on_rejected=on_rejected,
                    auto_upload=True,
                    max_file_size=8_000_000,
                    max_files=1,
                ).classes("w-full mt-4")
                uploader.props(
                    'accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"'
                )

                ui.label(
                    "L’image est automatiquement orientée, "
                    "réduite à 1000 px maximum et convertie en JPEG."
                ).classes("text-xs jf-muted")

                if data_url:
                    def ask_delete():
                        with ui.dialog() as confirm:
                            with ui.card().classes(
                                "w-full max-w-md p-4"
                            ):
                                ui.label(
                                    "Supprimer le portrait?"
                                ).classes("text-xl font-bold")
                                ui.label(
                                    "Le personnage sera conservé. "
                                    "Seule sa photo sera supprimée."
                                ).classes("text-sm")

                                def remove():
                                    try:
                                        delete_rpg_portrait(
                                            user_id,
                                            character["id"],
                                        )
                                    except Exception as error:
                                        notify_error(
                                            error,
                                            "Le portrait n’a pas pu "
                                            "être supprimé.",
                                        )
                                        return

                                    confirm.close()
                                    manager.close()
                                    ui.notify(
                                        "Portrait supprimé.",
                                        type="positive",
                                    )
                                    ui.navigate.reload()

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
        manager.open()

    with ui.column().classes("gap-1 items-center shrink-0"):
        if data_url:
            portrait_image = ui.image(data_url).classes(
                "w-24 h-28 rounded-xl cursor-pointer "
                "border border-white/30 shadow-md"
            ).props("fit=cover")
            portrait_image.on(
                "click",
                lambda _event=None: open_large_preview(),
            )
            portrait_image.tooltip("Agrandir le portrait")
        else:
            with ui.card().classes(
                "w-24 h-28 items-center justify-center "
                "bg-white/10 border border-white/30"
            ):
                ui.icon("person").classes(
                    "text-5xl text-white/70"
                )

        ui.button(
            "Photo",
            icon="photo_camera",
            on_click=open_manager,
        ).props(
            "flat dense color=white no-caps"
        ).classes("text-xs")
