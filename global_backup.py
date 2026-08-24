from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
import io
import json
import re
import tempfile
import traceback
import zipfile

from nicegui import ui

from app_access import get_user_app_access
from app_versions import get_app_version
from blood_pressure_data import export_blood_pressure_data
from db import export_family_backup, get_accessible_families, get_connection
from finances_data import export_finances


GLOBAL_BACKUP_FORMAT = "jf-apps-global-backup"
GLOBAL_BACKUP_VERSION = 1


def _json_value(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (set, tuple)):
        return list(value)
    # UUID et autres types PostgreSQL rares restent lisibles dans le snapshot.
    return str(value)


def _json_bytes(payload):
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        default=_json_value,
    ).encode("utf-8")


def _safe_filename(value):
    cleaned = re.sub(r"[^A-Za-z0-9À-ÿ_-]+", "_", str(value or "").strip())
    return cleaned.strip("_") or "donnees"


def _safe_identifier(value):
    text = str(value or "")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", text):
        raise ValueError("Identifiant SQL inattendu.")
    return text


def _public_table_columns(cur, table_name):
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        ORDER BY ordinal_position;
        """,
        (table_name,),
    )
    return [row["column_name"] for row in cur.fetchall()]


def _export_user_scoped_prefix(user_id, prefix):
    """Exporte les tables privées d'un module sans exposer les autres comptes.

    Une table racine avec user_id est filtrée directement. Pour Personnages JDR,
    les tables enfants contenant character_id sont limitées aux personnages du
    compte courant.
    """
    result = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public'
                  AND table_type='BASE TABLE'
                  AND table_name LIKE %s
                ORDER BY table_name;
                """,
                (prefix + "%",),
            )
            tables = [row["table_name"] for row in cur.fetchall()]

            for table_name in tables:
                safe_table = _safe_identifier(table_name)
                columns = _public_table_columns(cur, table_name)
                if "user_id" in columns:
                    cur.execute(
                        f'SELECT * FROM "{safe_table}" WHERE user_id=%s ORDER BY 1;',
                        (user_id,),
                    )
                elif prefix == "rpg_" and "character_id" in columns:
                    cur.execute(
                        f'''SELECT child.*
                            FROM "{safe_table}" AS child
                            JOIN rpg_characters AS character
                              ON character.id=child.character_id
                            WHERE character.user_id=%s
                            ORDER BY 1;''',
                        (user_id,),
                    )
                else:
                    # Une table sans portée utilisateur démontrable est ignorée.
                    continue
                result[table_name] = [dict(row) for row in cur.fetchall()]
    return result


def _export_feedback(user_id):
    payload = {"user_feedback": [], "user_feedback_events": []}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM user_feedback WHERE user_id=%s ORDER BY id;",
                (user_id,),
            )
            payload["user_feedback"] = [dict(row) for row in cur.fetchall()]
            cur.execute(
                """
                SELECT event.*
                FROM user_feedback_events AS event
                JOIN user_feedback AS feedback ON feedback.id=event.feedback_id
                WHERE feedback.user_id=%s
                ORDER BY event.id;
                """,
                (user_id,),
            )
            payload["user_feedback_events"] = [dict(row) for row in cur.fetchall()]
    return payload


def _export_grocery_preferences(family_ids):
    if not family_ids:
        return []
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM grocery_family_preferences
                    WHERE family_id = ANY(%s)
                    ORDER BY family_id;
                    """,
                    (list(family_ids),),
                )
                return [dict(row) for row in cur.fetchall()]
    except Exception:
        # Le fichier doit rester exportable même si une installation plus
        # ancienne ne possède pas encore cette table facultative.
        return []



def _export_family_scoped_tables(family_ids):
    """Snapshot complémentaire des tables directement rattachées aux familles.

    Ce snapshot conserve notamment les réglages, éléments supprimés et métadonnées
    qui ne font pas nécessairement partie de l'export utilisateur simplifié.
    Les tables d'adhésion/comptes sont volontairement exclues.
    """
    if not family_ids:
        return {}
    excluded = {"family_members", "users", "user_app_access"}
    payload = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND column_name='family_id'
                ORDER BY table_name;
                """
            )
            for row in cur.fetchall():
                table_name = row["table_name"]
                if table_name in excluded:
                    continue
                safe_table = _safe_identifier(table_name)
                cur.execute(
                    f'SELECT * FROM "{safe_table}" WHERE family_id = ANY(%s) ORDER BY 1;',
                    (list(family_ids),),
                )
                payload[table_name] = [dict(item) for item in cur.fetchall()]
    return payload

def build_global_backup(user):
    """Construit une archive privée contenant toutes les apps accessibles."""
    user_id = int(user["id"])
    allowed = set(get_user_app_access(user_id))
    exported_at = datetime.now().astimezone()
    manifest = {
        "format": GLOBAL_BACKUP_FORMAT,
        "version": GLOBAL_BACKUP_VERSION,
        "exported_at": exported_at.isoformat(),
        "user": {
            "display_name": user.get("display_name") or "",
        },
        "applications": {},
        "restore": {
            "global_restore_available": False,
            "note": (
                "Cette version fournit la sauvegarde globale. "
                "La restauration globale contrôlée sera ajoutée séparément."
            ),
        },
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if "grocery" in allowed:
            families = get_accessible_families(user_id)
            family_ids = [int(row["id"]) for row in families]
            exported_families = []
            for family in families:
                family_data = export_family_backup(user_id, int(family["id"]))
                family_name = _safe_filename(family.get("name") or f"famille_{family['id']}")
                archive.writestr(
                    f"liste_epicerie/{family_name}.json",
                    _json_bytes({
                        "format": "jf-apps-liste-epicerie",
                        "version": 3,
                        "exported_at": exported_at.isoformat(),
                        "data": family_data,
                    }),
                )
                exported_families.append(family.get("name") or family_name)
            archive.writestr(
                "liste_epicerie/reglages_familles.json",
                _json_bytes(_export_grocery_preferences(family_ids)),
            )
            archive.writestr(
                "liste_epicerie/snapshot_familles.json",
                _json_bytes(_export_family_scoped_tables(family_ids)),
            )
            manifest["applications"]["grocery"] = {
                "label": "Liste d’épicerie",
                "version": get_app_version("grocery"),
                "families": exported_families,
            }

        if "finances" in allowed:
            csv_bytes, json_bytes = export_finances(user_id)
            archive.writestr("finances/finances.csv", csv_bytes)
            archive.writestr("finances/finances.json", json_bytes)
            manifest["applications"]["finances"] = {
                "label": "Finances",
                "version": get_app_version("finances"),
            }

        if "blood_pressure" in allowed:
            csv_bytes, json_bytes = export_blood_pressure_data(user_id)
            archive.writestr("journal_pression/mesures.csv", csv_bytes)
            archive.writestr("journal_pression/sauvegarde.json", json_bytes)
            manifest["applications"]["blood_pressure"] = {
                "label": "Journal de pression",
                "version": get_app_version("blood_pressure"),
            }

        if "rpg" in allowed:
            rpg_data = _export_user_scoped_prefix(user_id, "rpg_")
            archive.writestr("personnages_jdr/sauvegarde.json", _json_bytes(rpg_data))
            manifest["applications"]["rpg"] = {
                "label": "Personnages JDR",
                "version": get_app_version("rpg"),
                "tables": sorted(rpg_data),
            }

        try:
            feedback_data = _export_feedback(user_id)
            archive.writestr("portail/commentaires.json", _json_bytes(feedback_data))
            manifest["applications"]["feedback"] = {
                "label": "Commentaires et suggestions",
                "version": get_app_version("feedback"),
            }
        except Exception:
            # Les commentaires ne doivent pas faire échouer la sauvegarde des
            # applications principales si le module n'est pas installé.
            pass

        archive.writestr("manifest.json", _json_bytes(manifest))
        archive.writestr(
            "LIRE_MOI.txt",
            (
                "JF Apps — sauvegarde globale\n"
                "===========================\n\n"
                f"Créée le {exported_at.strftime('%Y-%m-%d %H:%M:%S %z')}\n\n"
                "Cette archive contient uniquement les données auxquelles le compte "
                "avait accès au moment de la sauvegarde. Les dossiers sont séparés par "
                "application. Le fichier manifest.json indique les versions.\n\n"
                "La restauration globale n'est pas encore activée dans cette version; "
                "conservez cette archive comme copie de sécurité.\n"
            ).encode("utf-8"),
        )

    filename = "jf_apps_sauvegarde_complete_" + exported_at.strftime("%Y%m%d_%H%M%S") + ".zip"
    return buffer.getvalue(), filename, manifest


def download_global_backup(user):
    """Action Portail : prépare puis télécharge la sauvegarde en une action."""
    try:
        content, filename, _manifest = build_global_backup(user)
        path = Path(tempfile.gettempdir()) / f"{user['id']}_{filename}"
        path.write_bytes(content)
        ui.download(str(path), filename=filename)
        ui.notify("Sauvegarde complète créée.", type="positive")
    except Exception as error:
        traceback.print_exc()
        ui.notify(
            f"La sauvegarde globale a échoué : {error}",
            type="negative",
            timeout=10000,
        )
