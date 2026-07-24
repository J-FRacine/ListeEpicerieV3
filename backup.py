import csv
import io
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


def _build_json_export(data):
    document = {
        "format": BACKUP_FORMAT,
        "version": BACKUP_VERSION,
        "exported_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "data": data,
    }

    return json.dumps(
        document,
        ensure_ascii=False,
        indent=2,
    )


def _build_csv_export(data):
    """Crée un CSV pratique à consulter dans Excel.

    Le JSON demeure le format recommandé pour une sauvegarde
    complète et réimportable. Le CSV contient la liste des items.
    """

    output = io.StringIO(newline="")
    writer = csv.writer(
        output,
        delimiter=";",
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\r\n",
    )

    writer.writerow([
        "Famille",
        "Catégorie",
        "Item",
        "Quantité",
        "Besoin",
    ])

    family_name = data["family"]["name"]

    for item in data.get("items", []):
        writer.writerow([
            family_name,
            item.get("category", ""),
            item.get("name", ""),
            item.get("quantity", 1),
            "Oui" if item.get("needed") else "Non",
        ])

    # Le BOM UTF-8 aide Excel à afficher correctement les accents.
    return "\ufeff" + output.getvalue()


def backup_panel():
    current_family_id = get_current_family_id()

    if not ensure_family_selected(current_family_id):
        return

    families = get_families()

    if not families:
        ui.label(
            "Aucune famille disponible."
        ).classes("text-orange-700")
        return

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

    current_family_name = current_family["name"]

    family_name_to_id = {
        family["name"]: family["id"]
        for family in families
    }

    with ui.row().classes(
        "w-full items-start justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Données et sauvegarde").classes(
                "text-2xl font-bold"
            )
            ui.label(
                f"Famille active pour l’importation : "
                f"{current_family_name}"
            ).classes("text-sm text-gray-500")

        ui.icon("cloud_sync").classes(
            "text-3xl text-primary"
        )

    ui.label(
        "L’exportation peut viser n’importe quelle famille. "
        "L’importation agit seulement sur la famille active."
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
                    "Choisir la famille et le format du fichier."
                ).classes("text-sm text-gray-500")

        with ui.row().classes(
            "w-full items-end gap-3 flex-wrap mt-3"
        ):
            export_family_input = ui.select(
                list(family_name_to_id.keys()),
                value=current_family_name,
                label="Famille à exporter",
            ).classes("grow min-w-[220px]")

            export_format_input = ui.select(
                ["JSON", "CSV"],
                value="JSON",
                label="Format",
            ).classes("w-40")

        format_explanation = ui.label(
            "JSON : sauvegarde complète et réimportable."
        ).classes("text-xs text-gray-500")

        def update_format_explanation():
            if export_format_input.value == "CSV":
                format_explanation.set_text(
                    "CSV : liste des items pour Excel; "
                    "utilise JSON pour une restauration complète."
                )
            else:
                format_explanation.set_text(
                    "JSON : sauvegarde complète et réimportable."
                )

        export_format_input.on(
            "update:model-value",
            lambda: update_format_explanation(),
        )

        def export_data():
            selected_family_name = (
                export_family_input.value
            )
            selected_format = (
                export_format_input.value or "JSON"
            ).upper()

            if selected_family_name not in family_name_to_id:
                ui.notify(
                    "Choisis une famille à exporter.",
                    type="warning",
                )
                return

            selected_family_id = family_name_to_id[
                selected_family_name
            ]

            try:
                data = export_family_backup(
                    selected_family_id
                )
            except ValueError as error:
                ui.notify(str(error), type="warning")
                return

            date_text = datetime.now().strftime(
                "%Y-%m-%d_%Hh%M"
            )
            base_filename = (
                "sauvegarde_epicerie_"
                f"{_safe_filename(selected_family_name)}_"
                f"{date_text}"
            )

            if selected_format == "CSV":
                file_content = _build_csv_export(data)
                filename = f"{base_filename}.csv"
                media_type = "text/csv; charset=utf-8"
            else:
                file_content = _build_json_export(data)
                filename = f"{base_filename}.json"
                media_type = "application/json"

            ui.download.content(
                file_content,
                filename=filename,
                media_type=media_type,
            )

            ui.notify(
                f"Exportation de « {selected_family_name} » "
                f"en {selected_format} prête.",
                type="positive",
            )

        ui.button(
            "Exporter",
            icon="download",
            on_click=export_data,
        ).props("color=primary").classes(
            "w-full mt-3"
        )

    # ---------------------------------------------------------
    # IMPORTATION JSON
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
                    "Importer une sauvegarde JSON dans "
                    f"la famille active « {current_family_name} »."
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
            "Le format CSV est destiné à la consultation dans Excel. "
            "L’importation accepte actuellement le format JSON seulement."
        ).classes("text-xs text-gray-500 mt-2")
