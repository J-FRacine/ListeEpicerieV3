from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import io
import json
import re
import traceback
import zipfile

from nicegui import ui

from app_access import get_user_app_access
from blood_pressure_data import (
    import_blood_pressure_rows,
    prepare_blood_pressure_import,
)
from db import get_accessible_families, get_connection, import_family_backup
from finances_data import (
    import_finance_rows,
    prepare_finance_import,
    restore_finance_supplement,
)


GLOBAL_BACKUP_FORMAT = "jf-apps-global-backup"
SUPPORTED_BACKUP_VERSIONS = {1, 2}
MAX_ARCHIVE_BYTES = 40 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 120 * 1024 * 1024
MAX_MEMBER_BYTES = 30 * 1024 * 1024
MAX_MEMBER_COUNT = 250

APP_LABELS = {
    "grocery": "Liste d’épicerie",
    "finances": "Finances",
    "blood_pressure": "Journal de pression",
    "rpg": "Personnages JDR",
    "feedback": "Commentaires et suggestions",
}

APP_PATHS = {
    "finances": "finances/finances.json",
    "blood_pressure": "journal_pression/sauvegarde.json",
    "rpg": "personnages_jdr/sauvegarde.json",
    "feedback": "portail/commentaires.json",
}


@dataclass(frozen=True)
class ArchiveInfo:
    content: bytes
    manifest: dict
    members: tuple[str, ...]


def _json_member(archive: zipfile.ZipFile, name: str):
    try:
        raw = archive.read(name)
    except KeyError as error:
        raise ValueError(f"Le fichier {name} est absent de la sauvegarde.") from error
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise ValueError(f"Le fichier {name} n’est pas encodé en UTF-8.") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Le fichier {name} contient un JSON invalide.") from error


def _text_member(archive: zipfile.ZipFile, name: str) -> str:
    try:
        raw = archive.read(name)
    except KeyError as error:
        raise ValueError(f"Le fichier {name} est absent de la sauvegarde.") from error
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"Le fichier {name} n’est pas encodé en UTF-8.") from error


def _validated_archive(content: bytes) -> ArchiveInfo:
    if not isinstance(content, (bytes, bytearray)) or not content:
        raise ValueError("La sauvegarde est vide.")
    if len(content) > MAX_ARCHIVE_BYTES:
        raise ValueError("La sauvegarde dépasse la taille maximale acceptée (40 Mo).")

    try:
        archive = zipfile.ZipFile(io.BytesIO(content), "r")
    except zipfile.BadZipFile as error:
        raise ValueError("Le fichier choisi n’est pas une archive ZIP valide.") from error

    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_MEMBER_COUNT:
            raise ValueError("La sauvegarde contient trop de fichiers.")

        total = 0
        members = []
        for info in infos:
            name = str(info.filename or "").replace("\\", "/")
            if not name or name.startswith("/"):
                raise ValueError("La sauvegarde contient un chemin de fichier invalide.")
            parts = [part for part in name.split("/") if part]
            if any(part in {".", ".."} for part in parts):
                raise ValueError("La sauvegarde contient un chemin de fichier non sécuritaire.")
            if info.file_size > MAX_MEMBER_BYTES:
                raise ValueError(f"Le fichier {name} est trop volumineux.")
            total += int(info.file_size)
            if total > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("Le contenu décompressé de la sauvegarde est trop volumineux.")
            members.append(name)

        if "manifest.json" not in members:
            raise ValueError("Cette archive ne contient pas de manifest.json JF Apps.")

        manifest = _json_member(archive, "manifest.json")

    if not isinstance(manifest, dict):
        raise ValueError("Le manifest de la sauvegarde est invalide.")
    if manifest.get("format") != GLOBAL_BACKUP_FORMAT:
        raise ValueError("Cette archive n’est pas une sauvegarde globale JF Apps reconnue.")
    try:
        version = int(manifest.get("version") or 0)
    except (TypeError, ValueError):
        version = 0
    if version not in SUPPORTED_BACKUP_VERSIONS:
        raise ValueError(
            "Cette version de sauvegarde globale n’est pas prise en charge par ce Portail."
        )

    return ArchiveInfo(bytes(content), manifest, tuple(members))


def _allowed_app_keys(user_id: int) -> set[str]:
    allowed = set(get_user_app_access(user_id))
    # Les commentaires sont des données privées du Portail, pas une application
    # optionnelle attribuée par user_app_access.
    allowed.add("feedback")
    return allowed


def _grocery_entries(info: ArchiveInfo) -> list[dict]:
    manifest_app = (info.manifest.get("applications") or {}).get("grocery") or {}
    declared = manifest_app.get("families") or []
    result = []

    if declared and isinstance(declared, list) and all(isinstance(item, dict) for item in declared):
        for index, item in enumerate(declared):
            name = str(item.get("name") or f"Famille {index + 1}").strip()
            path = str(item.get("file") or "").strip()
            if not path:
                continue
            result.append(
                {
                    "key": f"grocery_{index}",
                    "name": name,
                    "path": path,
                    "original_id": item.get("original_id"),
                }
            )
        if result:
            return result

    # Compatibilité avec les archives V1 : le manifest ne contenait que les noms.
    json_paths = sorted(
        name
        for name in info.members
        if name.startswith("liste_epicerie/")
        and name.endswith(".json")
        and name not in {
            "liste_epicerie/reglages_familles.json",
            "liste_epicerie/snapshot_familles.json",
        }
    )
    with zipfile.ZipFile(io.BytesIO(info.content), "r") as archive:
        for index, path in enumerate(json_paths):
            try:
                document = _json_member(archive, path)
                data = document.get("data") if isinstance(document, dict) else None
                family_name = (
                    ((data or {}).get("family") or {}).get("name")
                    if isinstance(data, dict)
                    else None
                )
            except Exception:
                family_name = None
            result.append(
                {
                    "key": f"grocery_{index}",
                    "name": str(family_name or path.rsplit("/", 1)[-1].rsplit(".", 1)[0]),
                    "path": path,
                    "original_id": None,
                }
            )
    return result


def inspect_global_backup(content: bytes, user: dict) -> dict:
    """Valide l'archive et produit une prévisualisation sans aucune écriture."""
    info = _validated_archive(content)
    user_id = int(user["id"])
    allowed = _allowed_app_keys(user_id)
    manifest_apps = info.manifest.get("applications") or {}
    if not isinstance(manifest_apps, dict):
        raise ValueError("La liste des applications du manifest est invalide.")

    available = []
    blocked = []
    with zipfile.ZipFile(io.BytesIO(info.content), "r") as archive:
        for key, app_data in manifest_apps.items():
            if key not in APP_LABELS:
                continue
            label = APP_LABELS[key]
            if key not in allowed:
                blocked.append(label)
                continue
            details = {"key": key, "label": label, "version": (app_data or {}).get("version")}
            if key != "grocery":
                required_path = APP_PATHS.get(key)
                if required_path and required_path not in info.members:
                    raise ValueError(
                        f"La sauvegarde déclare « {label} », mais le fichier {required_path} est absent."
                    )
            if key == "grocery":
                families = _grocery_entries(info)
                details["families"] = families
                details["count"] = len(families)
            elif key == "finances" and APP_PATHS[key] in info.members:
                text = _text_member(archive, APP_PATHS[key])
                preview = prepare_finance_import(user_id, "finances.json", text)
                payload = json.loads(text)
                details.update(
                    {
                        "transactions": preview.get("valid_rows", 0),
                        "already_imported": preview.get("already_imported", 0),
                        "possible_duplicates": preview.get("possible_duplicates", 0),
                        "budget_items": len(preview.get("budget_items") or []),
                        "installment_plans": len(payload.get("installment_plans") or []),
                        "financing_groups": len(payload.get("financing_budget_groups") or []),
                        "shared_loans": len(payload.get("shared_loans") or []),
                    }
                )
            elif key == "blood_pressure" and APP_PATHS[key] in info.members:
                text = _text_member(archive, APP_PATHS[key])
                preview = prepare_blood_pressure_import(user_id, "sauvegarde.json", text)
                details.update(
                    {
                        "readings": preview.get("total_rows", 0),
                        "valid_readings": preview.get("valid_rows", 0),
                        "duplicates": preview.get("exact_duplicates", 0),
                        "conflicts": preview.get("possible_conflicts", 0),
                        "has_reminders": bool(preview.get("reminder_settings")),
                    }
                )
            elif key == "rpg" and APP_PATHS[key] in info.members:
                payload = _json_member(archive, APP_PATHS[key])
                details.update(
                    {
                        "characters": len((payload or {}).get("rpg_characters") or []),
                        "related_rows": sum(
                            len(rows)
                            for table, rows in (payload or {}).items()
                            if table != "rpg_characters" and isinstance(rows, list)
                        ),
                    }
                )
            elif key == "feedback" and APP_PATHS[key] in info.members:
                payload = _json_member(archive, APP_PATHS[key])
                details.update(
                    {
                        "feedback": len((payload or {}).get("user_feedback") or []),
                        "events": len((payload or {}).get("user_feedback_events") or []),
                    }
                )
            available.append(details)

    exported_at = info.manifest.get("exported_at")
    return {
        "archive": info,
        "manifest": info.manifest,
        "available": available,
        "blocked": blocked,
        "exported_at": exported_at,
        "version": info.manifest.get("version"),
    }


def _safe_identifier(value: str) -> str:
    text = str(value or "")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", text):
        raise ValueError("Identifiant SQL inattendu dans la restauration.")
    return text


def _table_columns(cur, table_name: str) -> set[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s;
        """,
        (table_name,),
    )
    return {str(row["column_name"]) for row in cur.fetchall()}


def _insert_intersection(cur, table_name: str, raw: dict, overrides=None, exclude=None):
    safe_table = _safe_identifier(table_name)
    columns = _table_columns(cur, safe_table)
    values = dict(raw or {})
    values.update(overrides or {})
    excluded = set(exclude or ()) | {"id"}
    keys = [key for key in values if key in columns and key not in excluded]
    if not keys:
        raise ValueError(f"Aucune colonne restaurable dans {safe_table}.")
    col_sql = ", ".join(f'"{_safe_identifier(key)}"' for key in keys)
    placeholders = ", ".join(["%s"] * len(keys))
    if "id" in columns:
        cur.execute(
            f'INSERT INTO "{safe_table}" ({col_sql}) VALUES ({placeholders}) '
            "ON CONFLICT DO NOTHING RETURNING id;",
            tuple(values[key] for key in keys),
        )
        row = cur.fetchone()
        return int(row["id"]) if row and "id" in row else None

    cur.execute(
        f'INSERT INTO "{safe_table}" ({col_sql}) VALUES ({placeholders}) '
        "ON CONFLICT DO NOTHING;",
        tuple(values[key] for key in keys),
    )
    return True if getattr(cur, "rowcount", 0) else None


def _restore_rpg(user_id: int, payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("La sauvegarde Personnages JDR est invalide.")
    roots = payload.get("rpg_characters") or []
    imported = 0
    skipped = 0
    related = 0
    id_map = {}
    new_old_ids = set()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, LOWER(TRIM(character_name)) AS name_key FROM rpg_characters WHERE user_id=%s;",
                (user_id,),
            )
            existing = {str(row["name_key"]): int(row["id"]) for row in cur.fetchall()}
            for raw in roots:
                if not isinstance(raw, dict):
                    continue
                old_id = raw.get("id")
                name = str(raw.get("character_name") or "").strip()
                if not name:
                    continue
                key = name.casefold()
                if key in existing:
                    if old_id is not None:
                        id_map[int(old_id)] = existing[key]
                    skipped += 1
                    continue
                new_id = _insert_intersection(
                    cur,
                    "rpg_characters",
                    raw,
                    overrides={"user_id": user_id},
                    exclude={"manager_user_id"},
                )
                if new_id is None:
                    skipped += 1
                    continue
                existing[key] = new_id
                if old_id is not None:
                    id_map[int(old_id)] = new_id
                    new_old_ids.add(int(old_id))
                imported += 1

            for table_name, rows in payload.items():
                if table_name == "rpg_characters" or not str(table_name).startswith("rpg_"):
                    continue
                if not isinstance(rows, list):
                    continue
                safe_table = _safe_identifier(table_name)
                columns = _table_columns(cur, safe_table)
                if "character_id" not in columns:
                    continue
                for raw in rows:
                    if not isinstance(raw, dict):
                        continue
                    try:
                        old_character_id = int(raw.get("character_id"))
                    except (TypeError, ValueError):
                        continue
                    # Ne fusionne pas silencieusement les lignes enfants dans un
                    # personnage qui existait déjà : seuls les nouveaux personnages
                    # reçoivent leurs données enfants.
                    if old_character_id not in new_old_ids:
                        continue
                    new_character_id = id_map.get(old_character_id)
                    if not new_character_id:
                        continue
                    overrides = {"character_id": new_character_id}
                    if "user_id" in columns:
                        overrides["user_id"] = user_id
                    inserted = _insert_intersection(
                        cur,
                        safe_table,
                        raw,
                        overrides=overrides,
                    )
                    if inserted:
                        related += 1
            conn.commit()

    return {"characters_imported": imported, "characters_skipped": skipped, "related_rows": related}


def _restore_feedback(user_id: int, payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("La sauvegarde des commentaires est invalide.")
    roots = payload.get("user_feedback") or []
    events = payload.get("user_feedback_events") or []
    imported = 0
    skipped = 0
    event_count = 0
    id_map = {}
    original_owner_ids = set()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, LOWER(TRIM(app_key)) AS app_key, LOWER(TRIM(subject)) AS subject,
                       LOWER(TRIM(detail)) AS detail
                FROM user_feedback WHERE user_id=%s;
                """,
                (user_id,),
            )
            existing = {
                (str(row["app_key"]), str(row["subject"]), str(row["detail"])): int(row["id"])
                for row in cur.fetchall()
            }
            new_old_ids = set()
            for raw in roots:
                if not isinstance(raw, dict):
                    continue
                old_id = raw.get("id")
                old_owner = raw.get("user_id")
                if old_owner is not None:
                    try:
                        original_owner_ids.add(int(old_owner))
                    except (TypeError, ValueError):
                        pass
                key = (
                    str(raw.get("app_key") or "").strip().casefold(),
                    str(raw.get("subject") or "").strip().casefold(),
                    str(raw.get("detail") or "").strip().casefold(),
                )
                if not all(key):
                    continue
                if key in existing:
                    if old_id is not None:
                        id_map[int(old_id)] = existing[key]
                    skipped += 1
                    continue
                new_id = _insert_intersection(
                    cur,
                    "user_feedback",
                    raw,
                    overrides={"user_id": user_id, "manager_user_id": None},
                )
                if new_id is None:
                    skipped += 1
                    continue
                existing[key] = new_id
                if old_id is not None:
                    id_map[int(old_id)] = new_id
                    new_old_ids.add(int(old_id))
                imported += 1

            for raw in events:
                if not isinstance(raw, dict):
                    continue
                try:
                    old_feedback_id = int(raw.get("feedback_id"))
                except (TypeError, ValueError):
                    continue
                if old_feedback_id not in new_old_ids:
                    continue
                new_feedback_id = id_map.get(old_feedback_id)
                actor = raw.get("actor_user_id")
                try:
                    actor_value = int(actor) if actor is not None else None
                except (TypeError, ValueError):
                    actor_value = None
                mapped_actor = user_id if actor_value in original_owner_ids else None
                _insert_intersection(
                    cur,
                    "user_feedback_events",
                    raw,
                    overrides={"feedback_id": new_feedback_id, "actor_user_id": mapped_actor},
                )
                event_count += 1
            conn.commit()

    return {"feedback_imported": imported, "feedback_skipped": skipped, "events_imported": event_count}


def _grocery_preferences_by_source_id(info: ArchiveInfo) -> dict[int, dict]:
    path = "liste_epicerie/reglages_familles.json"
    if path not in info.members:
        return {}
    try:
        with zipfile.ZipFile(io.BytesIO(info.content), "r") as archive:
            rows = _json_member(archive, path)
    except Exception:
        return {}
    result = {}
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        try:
            source_id = int(row.get("family_id"))
        except (TypeError, ValueError):
            continue
        result[source_id] = row
    return result


def _restore_grocery_preferences(target_family_id: int, raw: dict) -> bool:
    if not isinstance(raw, dict) or "categories_enabled" not in raw:
        return False
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO grocery_family_preferences (family_id, categories_enabled)
                VALUES (%s, %s)
                ON CONFLICT (family_id) DO UPDATE
                SET categories_enabled=EXCLUDED.categories_enabled, updated_at=NOW();
                """,
                (target_family_id, bool(raw.get("categories_enabled"))),
            )
            conn.commit()
    return True


def _restore_grocery(user_id: int, info: ArchiveInfo, family_selection: dict) -> dict:
    entries = {entry["key"]: entry for entry in _grocery_entries(info)}
    accessible = {int(row["id"]): row for row in get_accessible_families(user_id)}
    restored = []
    preferences = _grocery_preferences_by_source_id(info)
    with zipfile.ZipFile(io.BytesIO(info.content), "r") as archive:
        for entry_key, target_id in (family_selection or {}).items():
            entry = entries.get(entry_key)
            if not entry:
                continue
            target_id = int(target_id)
            if target_id not in accessible:
                raise PermissionError("Une famille de destination n’est plus accessible.")
            document = _json_member(archive, entry["path"])
            data = document.get("data") if isinstance(document, dict) else None
            if not isinstance(data, dict):
                raise ValueError(f"La sauvegarde de « {entry['name']} » est invalide.")
            result = import_family_backup(
                user_id,
                target_id,
                data,
                replace_existing=False,
            )
            preferences_restored = False
            try:
                source_id = int(entry.get("original_id")) if entry.get("original_id") is not None else None
            except (TypeError, ValueError):
                source_id = None
            if source_id is not None and source_id in preferences:
                preferences_restored = _restore_grocery_preferences(
                    target_id, preferences[source_id]
                )
            restored.append(
                {
                    "source": entry["name"],
                    "target": accessible[target_id].get("name") or str(target_id),
                    "preferences_restored": preferences_restored,
                    "result": result,
                }
            )
    return {"families": restored}


def restore_global_backup(
    content: bytes,
    user: dict,
    selected_apps: set[str],
    family_selection: dict | None = None,
) -> dict:
    """Restauration sélective, par fusion uniquement, jamais destructive."""
    preview = inspect_global_backup(content, user)
    info: ArchiveInfo = preview["archive"]
    user_id = int(user["id"])
    allowed = _allowed_app_keys(user_id)
    available = {item["key"] for item in preview["available"]}
    selected = set(selected_apps or ()) & available & allowed
    if not selected:
        raise ValueError("Sélectionnez au moins une application à restaurer.")

    results = {}
    with zipfile.ZipFile(io.BytesIO(info.content), "r") as archive:
        if "grocery" in selected:
            if not family_selection:
                raise ValueError("Choisissez au moins une famille à restaurer pour la Liste d’épicerie.")
            results["grocery"] = _restore_grocery(user_id, info, family_selection)

        if "finances" in selected:
            text = _text_member(archive, APP_PATHS["finances"])
            finance_preview = prepare_finance_import(user_id, "finances.json", text)
            finance_result = import_finance_rows(
                user_id,
                finance_preview.get("rows") or [],
                skip_possible_duplicates=True,
                budget_items=finance_preview.get("budget_items") or [],
            )
            supplement = restore_finance_supplement(user_id, json.loads(text))
            results["finances"] = {**finance_result, "supplement": supplement}

        if "blood_pressure" in selected:
            text = _text_member(archive, APP_PATHS["blood_pressure"])
            bp_preview = prepare_blood_pressure_import(user_id, "sauvegarde.json", text)
            results["blood_pressure"] = import_blood_pressure_rows(
                user_id,
                bp_preview.get("rows") or [],
                import_source="JF Apps — sauvegarde globale",
                include_same_slot=False,
                reminder_settings=bp_preview.get("reminder_settings"),
                import_reminders=bool(bp_preview.get("reminder_settings")),
            )

        if "rpg" in selected:
            results["rpg"] = _restore_rpg(user_id, _json_member(archive, APP_PATHS["rpg"]))

        if "feedback" in selected:
            results["feedback"] = _restore_feedback(
                user_id,
                _json_member(archive, APP_PATHS["feedback"]),
            )

    return results


def _preview_caption(item: dict) -> str:
    key = item["key"]
    if key == "grocery":
        return f"{item.get('count', 0)} famille(s) présente(s) dans l’archive."
    if key == "finances":
        return (
            f"{item.get('transactions', 0)} transaction(s), "
            f"{item.get('budget_items', 0)} poste(s) Budget, "
            f"{item.get('installment_plans', 0)} financement(s)."
        )
    if key == "blood_pressure":
        return (
            f"{item.get('readings', 0)} mesure(s), "
            f"{item.get('duplicates', 0)} doublon(s) exact(s) détecté(s)."
        )
    if key == "rpg":
        return f"{item.get('characters', 0)} personnage(s) et {item.get('related_rows', 0)} ligne(s) associée(s)."
    if key == "feedback":
        return f"{item.get('feedback', 0)} commentaire(s) et {item.get('events', 0)} événement(s)."
    return ""


def global_restore_panel(user: dict):
    """Interface du Centre de maintenance pour la restauration sélective."""
    state = {
        "content": None,
        "preview": None,
        "selected": set(),
        "family_targets": {},
        "family_enabled": {},
        "busy": False,
    }

    with ui.card().classes("w-full p-5"):
        with ui.row().classes("w-full items-start gap-3"):
            ui.icon("settings_backup_restore").classes("text-3xl text-primary")
            with ui.column().classes("gap-0 grow"):
                ui.label("Restaurer une sauvegarde globale").classes("text-xl font-bold")
                ui.label(
                    "Chargez une archive ZIP JF Apps, prévisualisez son contenu puis choisissez seulement les applications à fusionner."
                ).classes("text-sm text-gray-500")

        ui.label(
            "La restauration globale est non destructive : elle fusionne les données, ignore les doublons reconnus et ne supprime jamais vos données actuelles."
        ).classes("text-sm text-amber-800 bg-amber-50 rounded-lg px-3 py-2 w-full mt-2")

        status_label = ui.label("Aucune archive chargée.").classes("text-sm text-gray-500")

        @ui.refreshable
        def preview_panel():
            preview = state.get("preview")
            if not preview:
                return

            manifest = preview["manifest"]
            with ui.element("div").classes("w-full mt-3 rounded-xl border border-gray-200 p-4"):
                ui.label("Prévisualisation").classes("font-bold text-lg")
                exported_at = manifest.get("exported_at") or "date inconnue"
                ui.label(
                    f"Sauvegarde globale V{preview.get('version')} — créée le {exported_at}"
                ).classes("text-sm text-gray-500")
                if preview.get("blocked"):
                    ui.label(
                        "Non restaurable avec ce compte : " + ", ".join(preview["blocked"])
                    ).classes("text-xs text-orange-700")

                state["selected"].intersection_update(
                    {item["key"] for item in preview["available"]}
                )
                for item in preview["available"]:
                    key = item["key"]
                    checked = key in state["selected"]
                    checkbox = ui.checkbox(
                        item["label"],
                        value=checked,
                    ).classes("mt-2")

                    def set_selected(event, app_key=key):
                        if event.value:
                            state["selected"].add(app_key)
                        else:
                            state["selected"].discard(app_key)
                        preview_panel.refresh()

                    checkbox.on_value_change(set_selected)
                    ui.label(_preview_caption(item)).classes("text-xs text-gray-500 ml-8")

                    if key == "grocery" and checked:
                        accessible = get_accessible_families(int(user["id"]))
                        options = {
                            int(row["id"]): str(row.get("name") or f"Famille {row['id']}")
                            for row in accessible
                        }
                        if not options:
                            ui.label("Aucune famille accessible comme destination.").classes("text-xs text-negative ml-8")
                            continue
                        for family in item.get("families") or []:
                            family_key = family["key"]
                            if family_key not in state["family_targets"]:
                                same = next(
                                    (
                                        family_id
                                        for family_id, family_name in options.items()
                                        if family_name.strip().casefold() == family["name"].strip().casefold()
                                    ),
                                    next(iter(options)),
                                )
                                state["family_targets"][family_key] = same
                            state["family_enabled"].setdefault(family_key, True)
                            with ui.row().classes("w-full items-center gap-2 ml-8"):
                                enabled = ui.checkbox(
                                    family["name"],
                                    value=bool(state["family_enabled"][family_key]),
                                ).props("dense")
                                enabled.on_value_change(
                                    lambda event, fk=family_key: state["family_enabled"].__setitem__(fk, bool(event.value))
                                )
                                ui.label("→").classes("text-xs")
                                target = ui.select(
                                    options,
                                    value=state["family_targets"][family_key],
                                ).props("dense outlined").classes("min-w-52")
                                target.on_value_change(
                                    lambda event, fk=family_key: state["family_targets"].__setitem__(fk, int(event.value))
                                )

                with ui.row().classes("w-full justify-end gap-2 mt-4"):
                    async def run_restore():
                        if state["busy"]:
                            return
                        selected = set(state["selected"])
                        if not selected:
                            ui.notify("Sélectionnez au moins une application.", type="warning")
                            return
                        family_selection = {}
                        if "grocery" in selected:
                            grocery_item = next(
                                (item for item in preview["available"] if item["key"] == "grocery"),
                                None,
                            )
                            for family in (grocery_item or {}).get("families") or []:
                                if not state["family_enabled"].get(family["key"], True):
                                    continue
                                target_id = state["family_targets"].get(family["key"])
                                if target_id:
                                    family_selection[family["key"]] = target_id
                        state["busy"] = True
                        restore_button.disable()
                        try:
                            ui.notify("Restauration en cours…", type="info", timeout=3000)
                            result = restore_global_backup(
                                state["content"],
                                user,
                                selected,
                                family_selection=family_selection,
                            )
                            labels = [APP_LABELS[key] for key in selected if key in result]
                            ui.notify(
                                "Restauration terminée : " + ", ".join(labels) + ".",
                                type="positive",
                                timeout=8000,
                            )
                            status_label.set_text(
                                "Dernière restauration terminée le "
                                + datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
                            )
                        except (ValueError, PermissionError) as error:
                            ui.notify(str(error), type="negative", timeout=10000)
                        except Exception as error:
                            traceback.print_exc()
                            ui.notify(
                                f"La restauration a échoué : {error}",
                                type="negative",
                                timeout=10000,
                            )
                        finally:
                            state["busy"] = False
                            restore_button.enable()

                    restore_button = ui.button(
                        "Restaurer la sélection",
                        icon="restore",
                        on_click=run_restore,
                    ).props("color=primary")

        async def load_archive(event):
            try:
                content = await event.file.read()
                if isinstance(content, str):
                    content = content.encode("utf-8")
                preview = inspect_global_backup(bytes(content), user)
                state["content"] = bytes(content)
                state["preview"] = preview
                state["selected"] = {item["key"] for item in preview["available"]}
                state["family_targets"] = {}
                state["family_enabled"] = {}
                status_label.set_text(
                    f"Archive chargée : {getattr(event.file, 'name', 'sauvegarde.zip')}"
                )
                preview_panel.refresh()
            except (ValueError, PermissionError) as error:
                state["content"] = None
                state["preview"] = None
                status_label.set_text("Archive refusée.")
                preview_panel.refresh()
                ui.notify(str(error), type="negative", timeout=10000)
            except Exception as error:
                traceback.print_exc()
                state["content"] = None
                state["preview"] = None
                status_label.set_text("Impossible de lire l’archive.")
                preview_panel.refresh()
                ui.notify(
                    f"Impossible de lire la sauvegarde : {error}",
                    type="negative",
                    timeout=10000,
                )

        ui.upload(
            label="Choisir une sauvegarde globale ZIP",
            on_upload=load_archive,
            auto_upload=True,
            max_file_size=MAX_ARCHIVE_BYTES,
        ).props("accept=.zip").classes("w-full mt-3")

        preview_panel()
