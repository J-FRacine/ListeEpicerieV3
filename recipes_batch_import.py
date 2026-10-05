"""Lecture sûre des imports groupés de recettes JSON / ZIP."""
from __future__ import annotations

import io
from pathlib import PurePosixPath
import zipfile

from recipes_chatgpt_import import normalize_name, parse_recipe_import


MAX_JSON_BYTES = 2_000_000
MAX_ZIP_BYTES = 12_000_000
MAX_ZIP_JSON_FILES = 100
MAX_ZIP_UNCOMPRESSED_BYTES = 25_000_000


def _clean_filename(value):
    name = str(value or "recette.json").replace("\\", "/")
    return PurePosixPath(name).name or "recette.json"


def _parse_json_bytes(filename, content):
    if len(content) > MAX_JSON_BYTES:
        raise ValueError(
            f"« {filename} » dépasse la limite de 2 Mo par fichier JSON."
        )
    try:
        text = bytes(content).decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError(
            f"« {filename} » n’est pas un fichier JSON UTF-8 valide."
        ) from error

    candidate = parse_recipe_import(text)
    return {
        "source_name": _clean_filename(filename),
        "candidate": candidate,
        "error": "",
    }


def parse_recipe_upload(filename, content):
    """Retourne une entrée par recette trouvée dans un JSON ou un ZIP."""
    safe_name = _clean_filename(filename)
    raw = bytes(content or b"")
    lower_name = safe_name.casefold()

    if lower_name.endswith(".json"):
        try:
            return [_parse_json_bytes(safe_name, raw)]
        except Exception as error:
            return [{
                "source_name": safe_name,
                "candidate": None,
                "error": str(error),
            }]

    if not lower_name.endswith(".zip"):
        return [{
            "source_name": safe_name,
            "candidate": None,
            "error": "Seuls les fichiers .json et .zip sont acceptés.",
        }]

    if len(raw) > MAX_ZIP_BYTES:
        return [{
            "source_name": safe_name,
            "candidate": None,
            "error": "L’archive ZIP dépasse la limite de 12 Mo.",
        }]

    try:
        archive = zipfile.ZipFile(io.BytesIO(raw), "r")
    except (zipfile.BadZipFile, OSError):
        return [{
            "source_name": safe_name,
            "candidate": None,
            "error": "L’archive ZIP est invalide.",
        }]

    entries = []
    total_uncompressed = 0
    json_count = 0

    with archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            member = str(info.filename or "")
            if "__MACOSX/" in member or member.startswith("__MACOSX"):
                continue
            if not member.casefold().endswith(".json"):
                continue

            json_count += 1
            if json_count > MAX_ZIP_JSON_FILES:
                entries.append({
                    "source_name": safe_name,
                    "candidate": None,
                    "error": (
                        "L’archive contient plus de 100 fichiers JSON; "
                        "séparez-la en plusieurs lots."
                    ),
                })
                break

            total_uncompressed += int(info.file_size or 0)
            if total_uncompressed > MAX_ZIP_UNCOMPRESSED_BYTES:
                entries.append({
                    "source_name": safe_name,
                    "candidate": None,
                    "error": (
                        "Le contenu décompressé de l’archive dépasse 25 Mo."
                    ),
                })
                break

            member_name = _clean_filename(member)
            if info.flag_bits & 0x1:
                entries.append({
                    "source_name": member_name,
                    "candidate": None,
                    "error": "Les fichiers ZIP chiffrés ne sont pas acceptés.",
                })
                continue

            try:
                member_bytes = archive.read(info)
                entries.append(
                    _parse_json_bytes(member_name, member_bytes)
                )
            except Exception as error:
                entries.append({
                    "source_name": member_name,
                    "candidate": None,
                    "error": str(error),
                })

    if not entries:
        entries.append({
            "source_name": safe_name,
            "candidate": None,
            "error": "Aucun fichier JSON n’a été trouvé dans l’archive.",
        })

    return entries


def mark_batch_duplicates(entries, existing_recipes):
    """Ajoute les indicateurs de doublon existant et doublon dans le lot."""
    existing_keys = {
        normalize_name(row.get("name"))
        for row in (existing_recipes or [])
    }
    seen = set()
    result = []

    for index, raw in enumerate(entries or []):
        row = dict(raw)
        candidate = row.get("candidate")
        name_key = normalize_name(
            candidate.get("name")
            if isinstance(candidate, dict)
            else ""
        )
        row["entry_id"] = index + 1
        row["duplicate_existing"] = bool(
            name_key and name_key in existing_keys
        )
        row["duplicate_batch"] = bool(
            name_key and name_key in seen
        )
        if name_key:
            seen.add(name_key)
        row["selected"] = bool(
            candidate
            and not row.get("error")
            and not row["duplicate_existing"]
            and not row["duplicate_batch"]
        )
        result.append(row)

    return result


def batch_summary(entries):
    rows = list(entries or [])
    return {
        "total": len(rows),
        "valid": sum(1 for row in rows if row.get("candidate")),
        "invalid": sum(1 for row in rows if row.get("error")),
        "duplicates": sum(
            1
            for row in rows
            if row.get("duplicate_existing") or row.get("duplicate_batch")
        ),
        "selected": sum(1 for row in rows if row.get("selected")),
    }
