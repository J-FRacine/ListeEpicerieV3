import json
import re
from datetime import datetime, timezone

from nicegui import ui

from db import (
    export_family_backup,
    get_families,
    import_family_backup,
)
from state import get_current_family_id
from utils import ensure_family_selected


BACKUP_FORMAT = "jf-apps-liste-epicerie"
BACKUP_VERSION = 1


def _safe_filename(value):
    cleaned = re.sub(
        r"[^A-Za-z0-9À-ÿ_-]+",
        "_",
        value.strip(),
    )
    cleaned = cleaned.strip("_")
    return cleaned or "famille"


def _validate_backup_document(document):
    if not isinstance(document, dict):
        raise ValueError(
            "Le fichier JSON ne contient pas une sauvegarde valide."
        )

    if document.get("format") != BACKUP_FORMAT:
        raise ValueError(
            "Ce fichier n’est pas une sauvegarde de "
            "la liste d’épicerie JF Apps."
        )

    if document.get("version") != BACKUP_VERSION:
        raise ValueError(
            "La version de cette sauvegarde n’est pas prise "
            "en charge."
        )

    data = document.get("data")

    if not isinstance(data, dict):
        raise ValueError(
            "La section de données de la sauvegarde est absente."
        )

    if not isinstance(data.get("categories", []), list):
        raise ValueError(
            "La liste des catégories est invalide."
        )

    if not isinstance(data.get("items", []), list):
        raise ValueError(
            "La liste des items est invalide."
        )

    return data


def backup_panel():
    current_family_id = get_current_family_id()

    if not ensure_family_selected(current_family_id):
        return

    families = get_families()
    current_family = next(
        (
            family
            for family in families
            if family["id"] == current_family_id
        ),
        None,
    )

    if current_family is None:
        ui.label(
            "La famille active n’existe plus."
        ).classes("text-orange-700")
        return

    family_name = current_family["name"]

    with ui.row().classes(
        "w-full items-start justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Données et sauvegarde").classes(
                "text-2xl font-bold"
            )
            ui.label(
                f"Famille active : {family_name}"
            ).classes("text-sm text-gray-500")

        ui.icon("cloud_sync").classes(
            "text-3xl text-primary"
        )

    ui.label(
        "La sauvegarde contient les catégories, les items, "
        "les quantités et la liste des besoins de cette famille."
    ).classes("text-gray-600")

    # ---------------------------------------------------------
    # EXPORTATION
    # ---------------------------------------------------------

    with ui.card().classes("w-full p-5"):
        with ui.row().classes(
            "w-full items-center gap-3"
        ):
            ui.icon("download").classes(
                "text-3xl text-primary"
            )

            with ui.column().classes("gap-0 grow"):
                ui.label("Exporter").classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "Télécharger une sauvegarde JSON de "
                    "la famille active."
                ).classes("text-sm text-gray-500")

        def export_data():
            try:
                data = export_family_backup(
                    current_family_id
                )
            except ValueError as error:
                ui.notify(str(error), type="warning")
                return

            exported_at = datetime.now(
                timezone.utc
            ).isoformat()

            document = {
                "format": BACKUP_FORMAT,
                "version": BACKUP_VERSION,
                "exported_at": exported_at,
                "data": data,
            }

            json_content = json.dumps(
                document,
                ensure_ascii=False,
                indent=2,
            )

            date_text = datetime.now().strftime(
                "%Y-%m-%d_%Hh%M"
            )
            filename = (
                "sauvegarde_epicerie_"
                f"{_safe_filename(family_name)}_"
                f"{date_text}.json"
            )

            ui.download.content(
                json_content,
                filename=filename,
                media_type="application/json",
            )

            ui.notify(
                "La sauvegarde est prête.",
                type="positive",
            )

        ui.button(
            "Télécharger la sauvegarde",
            icon="download",
            on_click=export_data,
        ).props("color=primary").classes(
            "w-full mt-3"
        )

    # ---------------------------------------------------------
    # IMPORTATION
    # ---------------------------------------------------------

    with ui.card().classes("w-full p-5"):
        with ui.row().classes(
            "w-full items-center gap-3"
        ):
            ui.icon("upload_file").classes(
                "text-3xl text-primary"
            )

            with ui.column().classes("gap-0 grow"):
                ui.label("Importer").classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "Importer une sauvegarde dans "
                    "la famille active."
                ).classes("text-sm text-gray-500")

        import_mode = ui.radio(
            {
                "merge": (
                    "Fusionner — conserver les données actuelles "
                    "et mettre à jour les doublons"
                ),
                "replace": (
                    "Remplacer — effacer les données actuelles "
                    "de cette famille"
                ),
            },
            value="merge",
        ).classes("w-full mt-3")

        ui.label(
            "Un doublon est un item ayant le même nom dans "
            "la même catégorie."
        ).classes("text-xs text-gray-500")

        replacement_confirmation = ui.checkbox(
            "Je comprends que le mode Remplacer effacera "
            "les catégories et les items actuels de cette famille."
        ).classes("mt-2")

        async def import_data(event):
            replace_existing = (
                import_mode.value == "replace"
            )

            if (
                replace_existing
                and not replacement_confirmation.value
            ):
                ui.notify(
                    "Coche la confirmation avant d’utiliser "
                    "le mode Remplacer.",
                    type="warning",
                )
                return

            try:
                text = await event.file.text()
                document = json.loads(text)
                data = _validate_backup_document(document)

                result = import_family_backup(
                    current_family_id,
                    data,
                    replace_existing=replace_existing,
                )
            except UnicodeDecodeError:
                ui.notify(
                    "Le fichier ne peut pas être lu comme texte.",
                    type="negative",
                )
                return
            except json.JSONDecodeError:
                ui.notify(
                    "Le fichier choisi n’est pas un fichier "
                    "JSON valide.",
                    type="negative",
                )
                return
            except (ValueError, KeyError) as error:
                ui.notify(
                    str(error),
                    type="negative",
                )
                return
            except Exception as error:
                print(
                    "ERREUR importation sauvegarde :",
                    repr(error),
                )
                ui.notify(
                    "L’importation a échoué. Consulte le journal "
                    "de Canner pour le détail.",
                    type="negative",
                )
                return

            if result["replaced"]:
                message = (
                    "Importation terminée : "
                    f"{result['categories_created']} catégorie(s) "
                    f"et {result['items_created']} item(s) restauré(s)."
                )
            else:
                message = (
                    "Fusion terminée : "
                    f"{result['categories_created']} catégorie(s) créée(s), "
                    f"{result['items_created']} item(s) ajouté(s), "
                    f"{result['items_updated']} item(s) mis à jour."
                )

            ui.notify(
                message,
                type="positive",
                timeout=8000,
            )
            ui.navigate.to("/?tab=donnees")

        ui.upload(
            label="Choisir une sauvegarde JSON",
            on_upload=import_data,
            auto_upload=True,
            max_files=1,
        ).props(
            "accept=.json,application/json"
        ).classes("w-full mt-3")

        ui.label(
            "L’importation agit uniquement sur la famille "
            "affichée en haut de cette page."
        ).classes("text-xs text-gray-500 mt-2")
