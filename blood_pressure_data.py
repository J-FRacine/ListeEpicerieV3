from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import date, datetime, time
from pathlib import Path

from db import get_connection


MAX_NOTE_LENGTH = 1000


def init_blood_pressure_schema():
    """Crée la table privée du journal de pression."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                blood_pressure_readings (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,
                    measured_date DATE NOT NULL,
                    measured_time TIME NOT NULL,
                    systolic SMALLINT NOT NULL
                        CHECK (
                            systolic BETWEEN 1 AND 400
                        ),
                    diastolic SMALLINT NOT NULL
                        CHECK (
                            diastolic BETWEEN 1 AND 300
                        ),
                    pulse SMALLINT NOT NULL
                        CHECK (
                            pulse BETWEEN 1 AND 300
                        ),
                    note TEXT,
                    created_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),
                    CHECK (
                        note IS NULL
                        OR CHAR_LENGTH(note)
                           <= 1000
                    )
                );
                """
            )

            cur.execute(
                """
                ALTER TABLE blood_pressure_readings
                ADD COLUMN IF NOT EXISTS import_source TEXT;
                """
            )
            cur.execute(
                """
                ALTER TABLE blood_pressure_readings
                ADD COLUMN IF NOT EXISTS import_key TEXT;
                """
            )
            cur.execute(
                """
                ALTER TABLE blood_pressure_readings
                ADD COLUMN IF NOT EXISTS imported_at TIMESTAMPTZ;
                """
            )
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                blood_pressure_user_import_key_idx
                ON blood_pressure_readings (
                    user_id,
                    import_key
                )
                WHERE import_key IS NOT NULL;
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                blood_pressure_user_date_idx
                ON blood_pressure_readings (
                    user_id,
                    measured_date DESC,
                    measured_time DESC,
                    id DESC
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                blood_pressure_reminder_settings (
                    user_id INTEGER PRIMARY KEY
                        REFERENCES users(id)
                        ON DELETE CASCADE,
                    enabled BOOLEAN NOT NULL
                        DEFAULT FALSE,
                    target_per_day SMALLINT NOT NULL
                        DEFAULT 2
                        CHECK (
                            target_per_day
                            BETWEEN 1 AND 10
                        ),
                    start_date DATE,
                    end_date DATE,
                    created_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),
                    CHECK (
                        start_date IS NULL
                        OR end_date IS NULL
                        OR end_date >= start_date
                    )
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                blood_pressure_reminder_slots (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,
                    label TEXT NOT NULL,
                    start_time TIME NOT NULL,
                    end_time TIME NOT NULL,
                    sort_order SMALLINT NOT NULL
                        CHECK (
                            sort_order BETWEEN 1 AND 10
                        ),
                    created_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),
                    UNIQUE (
                        user_id,
                        sort_order
                    ),
                    CHECK (
                        CHAR_LENGTH(label)
                        BETWEEN 1 AND 60
                    ),
                    CHECK (
                        end_time > start_time
                    )
                );
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                blood_pressure_reminder_slots_user_idx
                ON blood_pressure_reminder_slots (
                    user_id,
                    sort_order
                );
                """
            )

            conn.commit()


def _normalize_date(value) -> date:
    if isinstance(value, date):
        return value

    text = str(value or "").strip()

    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise ValueError(
            "La date est invalide."
        ) from error


def _normalize_time(value) -> time:
    if isinstance(value, time):
        return value.replace(
            second=0,
            microsecond=0,
        )

    text = str(value or "").strip()

    if len(text) >= 5:
        text = text[:5]

    try:
        return time.fromisoformat(text)
    except ValueError as error:
        raise ValueError(
            "L’heure est invalide."
        ) from error


def _normalize_integer(
    value,
    *,
    label,
    minimum,
    maximum,
) -> int:
    try:
        integer_value = int(value)
    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            f"{label} doit être un nombre entier."
        ) from error

    if not (
        minimum
        <= integer_value
        <= maximum
    ):
        raise ValueError(
            f"{label} doit être compris entre "
            f"{minimum} et {maximum}."
        )

    return integer_value


def _normalize_note(value) -> str | None:
    note = str(value or "").strip()

    if not note:
        return None

    if len(note) > MAX_NOTE_LENGTH:
        raise ValueError(
            "La note ne peut pas dépasser "
            f"{MAX_NOTE_LENGTH} caractères."
        )

    return note


def validate_reading_values(
    measured_date,
    measured_time,
    systolic,
    diastolic,
    pulse,
    note,
):
    return {
        "measured_date": _normalize_date(
            measured_date
        ),
        "measured_time": _normalize_time(
            measured_time
        ),
        "systolic": _normalize_integer(
            systolic,
            label="La pression systolique",
            minimum=1,
            maximum=400,
        ),
        "diastolic": _normalize_integer(
            diastolic,
            label="La pression diastolique",
            minimum=1,
            maximum=300,
        ),
        "pulse": _normalize_integer(
            pulse,
            label="Le pouls",
            minimum=1,
            maximum=300,
        ),
        "note": _normalize_note(
            note
        ),
    }


def create_blood_pressure_reading(
    user_id,
    measured_date,
    measured_time,
    systolic,
    diastolic,
    pulse,
    note=None,
):
    values = validate_reading_values(
        measured_date,
        measured_time,
        systolic,
        diastolic,
        pulse,
        note,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO blood_pressure_readings (
                    user_id,
                    measured_date,
                    measured_time,
                    systolic,
                    diastolic,
                    pulse,
                    note
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                RETURNING id;
                """,
                (
                    user_id,
                    values["measured_date"],
                    values["measured_time"],
                    values["systolic"],
                    values["diastolic"],
                    values["pulse"],
                    values["note"],
                ),
            )

            reading_id = cur.fetchone()[
                "id"
            ]

            conn.commit()
            return reading_id


def update_blood_pressure_reading(
    user_id,
    reading_id,
    measured_date,
    measured_time,
    systolic,
    diastolic,
    pulse,
    note=None,
):
    values = validate_reading_values(
        measured_date,
        measured_time,
        systolic,
        diastolic,
        pulse,
        note,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE blood_pressure_readings
                SET
                    measured_date = %s,
                    measured_time = %s,
                    systolic = %s,
                    diastolic = %s,
                    pulse = %s,
                    note = %s,
                    updated_at = NOW()
                WHERE id = %s
                  AND user_id = %s
                RETURNING id;
                """,
                (
                    values["measured_date"],
                    values["measured_time"],
                    values["systolic"],
                    values["diastolic"],
                    values["pulse"],
                    values["note"],
                    reading_id,
                    user_id,
                ),
            )

            if cur.fetchone() is None:
                raise ValueError(
                    "Cette mesure n’existe plus "
                    "ou ne vous appartient pas."
                )

            conn.commit()


def delete_blood_pressure_reading(
    user_id,
    reading_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM blood_pressure_readings
                WHERE id = %s
                  AND user_id = %s
                RETURNING id;
                """,
                (
                    reading_id,
                    user_id,
                ),
            )

            if cur.fetchone() is None:
                raise ValueError(
                    "Cette mesure n’existe plus "
                    "ou ne vous appartient pas."
                )

            conn.commit()


def list_blood_pressure_readings(
    user_id,
    start_date=None,
    end_date=None,
):
    parameters = [
        user_id,
    ]
    conditions = [
        "user_id = %s",
    ]

    if start_date is not None:
        conditions.append(
            "measured_date >= %s"
        )
        parameters.append(
            _normalize_date(
                start_date
            )
        )

    if end_date is not None:
        conditions.append(
            "measured_date <= %s"
        )
        parameters.append(
            _normalize_date(
                end_date
            )
        )

    where_clause = " AND ".join(
        conditions
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    id,
                    measured_date,
                    measured_time,
                    systolic,
                    diastolic,
                    pulse,
                    note,
                    import_source,
                    import_key,
                    imported_at,
                    created_at,
                    updated_at
                FROM blood_pressure_readings
                WHERE {where_clause}
                ORDER BY
                    measured_date DESC,
                    measured_time DESC,
                    id DESC;
                """,
                parameters,
            )

            return cur.fetchall()


def count_blood_pressure_readings_on_date(
    user_id,
    measured_date,
) -> int:
    normalized_date = _normalize_date(
        measured_date
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS total
                FROM blood_pressure_readings
                WHERE user_id = %s
                  AND measured_date = %s;
                """,
                (
                    user_id,
                    normalized_date,
                ),
            )

            return int(
                cur.fetchone()["total"]
            )



CSV_COLUMNS = (
    "Date",
    "Heure",
    "Systolique",
    "Diastolique",
    "Pouls",
    "Note",
)

CSV_ALIASES = {
    "date": "measured_date",
    "measured_date": "measured_date",
    "date_mesure": "measured_date",
    "heure": "measured_time",
    "time": "measured_time",
    "measured_time": "measured_time",
    "heure_mesure": "measured_time",
    "systolique": "systolic",
    "systolic": "systolic",
    "sys": "systolic",
    "diastolique": "diastolic",
    "diastolic": "diastolic",
    "dia": "diastolic",
    "pouls": "pulse",
    "pulse": "pulse",
    "note": "note",
    "notes": "note",
}


def _serializable(value):
    if isinstance(value, (date, time, datetime)):
        return value.isoformat()
    return value


def _normalized_header(value):
    text = str(value or "").strip().casefold()
    replacements = str.maketrans(
        "àâäéèêëîïôöùûüç",
        "aaaeeeeiioouuuc",
    )
    return (
        text.translate(replacements)
        .replace(" ", "_")
        .replace("-", "_")
    )


def _reading_import_key(values):
    payload = "|".join(
        (
            values["measured_date"].isoformat(),
            values["measured_time"].strftime("%H:%M"),
            str(values["systolic"]),
            str(values["diastolic"]),
            str(values["pulse"]),
            values["note"] or "",
        )
    )
    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def _reading_exact_key(values):
    return (
        values["measured_date"],
        values["measured_time"],
        values["systolic"],
        values["diastolic"],
        values["pulse"],
        values["note"] or "",
    )


def _reading_slot_key(values):
    return (
        values["measured_date"],
        values["measured_time"],
    )


def _existing_reading_keys(user_id):
    readings = list_blood_pressure_readings(user_id)
    exact = set()
    slots = set()
    import_keys = set()

    for row in readings:
        values = {
            "measured_date": row["measured_date"],
            "measured_time": row["measured_time"].replace(
                second=0,
                microsecond=0,
            ),
            "systolic": int(row["systolic"]),
            "diastolic": int(row["diastolic"]),
            "pulse": int(row["pulse"]),
            "note": row.get("note") or "",
        }
        exact.add(_reading_exact_key(values))
        slots.add(_reading_slot_key(values))
        if row.get("import_key"):
            import_keys.add(row["import_key"])

    return exact, slots, import_keys


def export_blood_pressure_data(user_id):
    readings = list_blood_pressure_readings(user_id)
    settings = get_blood_pressure_reminder_settings(user_id)

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(CSV_COLUMNS)

    for row in reversed(readings):
        writer.writerow(
            (
                row["measured_date"].isoformat(),
                row["measured_time"].strftime("%H:%M"),
                row["systolic"],
                row["diastolic"],
                row["pulse"],
                row.get("note") or "",
            )
        )

    json_payload = {
        "application": "JF Apps",
        "module": "Journal de pression",
        "version": "1.1.0",
        "exported_at": datetime.now().astimezone().isoformat(),
        "readings": [
            {
                "measured_date": row["measured_date"].isoformat(),
                "measured_time": row["measured_time"].strftime("%H:%M"),
                "systolic": int(row["systolic"]),
                "diastolic": int(row["diastolic"]),
                "pulse": int(row["pulse"]),
                "note": row.get("note"),
                "import_source": row.get("import_source"),
                "import_key": row.get("import_key"),
            }
            for row in reversed(readings)
        ],
        "reminder_settings": {
            "configured": bool(settings.get("configured")),
            "enabled": bool(settings.get("enabled")),
            "target_per_day": int(settings.get("target_per_day") or 2),
            "start_date": _serializable(settings.get("start_date")),
            "end_date": _serializable(settings.get("end_date")),
            "slots": [
                {
                    "label": slot["label"],
                    "start_time": _serializable(slot["start_time"]),
                    "end_time": _serializable(slot["end_time"]),
                    "sort_order": int(slot.get("sort_order") or index),
                }
                for index, slot in enumerate(
                    settings.get("slots") or [],
                    start=1,
                )
            ],
        },
    }

    return (
        csv_buffer.getvalue().encode("utf-8-sig"),
        json.dumps(
            json_payload,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
    )


def _parse_csv_import(text):
    csv_text = str(text or "").lstrip("\ufeff")
    sample = csv_text[:4096]
    try:
        dialect = csv.Sniffer().sniff(
            sample,
            delimiters=",;\t",
        )
    except csv.Error:
        dialect = csv.excel

    stream = io.StringIO(csv_text)
    reader = csv.DictReader(
        stream,
        dialect=dialect,
    )
    if not reader.fieldnames:
        raise ValueError("Le fichier CSV ne contient pas d’en-têtes.")

    mapping = {}
    for header in reader.fieldnames:
        normalized = _normalized_header(header)
        destination = CSV_ALIASES.get(normalized)
        if destination:
            mapping[header] = destination

    required = {
        "measured_date",
        "measured_time",
        "systolic",
        "diastolic",
        "pulse",
    }
    if not required.issubset(set(mapping.values())):
        raise ValueError(
            "Le CSV doit contenir Date, Heure, Systolique, "
            "Diastolique et Pouls."
        )

    rows = []
    for line_number, source_row in enumerate(reader, start=2):
        row = {
            destination: source_row.get(source_header)
            for source_header, destination in mapping.items()
        }
        row["_line_number"] = line_number
        rows.append(row)

    return rows, None, "CSV JF Apps"


def _parse_json_import(text):
    try:
        payload = json.loads(str(text or ""))
    except json.JSONDecodeError as error:
        raise ValueError("Le fichier JSON est invalide.") from error

    reminder_settings = None
    if isinstance(payload, list):
        source_rows = payload
    elif isinstance(payload, dict):
        source_rows = payload.get("readings")
        reminder_settings = payload.get("reminder_settings")
    else:
        source_rows = None

    if not isinstance(source_rows, list):
        raise ValueError(
            "La sauvegarde JSON ne contient pas de liste de mesures."
        )

    rows = []
    for index, source_row in enumerate(source_rows, start=1):
        if not isinstance(source_row, dict):
            rows.append(
                {
                    "_line_number": index,
                    "_invalid": "La mesure JSON n’est pas un objet.",
                }
            )
            continue
        rows.append(
            {
                "measured_date": (
                    source_row.get("measured_date")
                    or source_row.get("date")
                ),
                "measured_time": (
                    source_row.get("measured_time")
                    or source_row.get("time")
                    or source_row.get("heure")
                ),
                "systolic": (
                    source_row.get("systolic")
                    or source_row.get("systolique")
                ),
                "diastolic": (
                    source_row.get("diastolic")
                    or source_row.get("diastolique")
                ),
                "pulse": (
                    source_row.get("pulse")
                    or source_row.get("pouls")
                ),
                "note": source_row.get("note"),
                "import_key": source_row.get("import_key"),
                "_line_number": index,
            }
        )

    return rows, reminder_settings, "JSON JF Apps"


def prepare_blood_pressure_import(user_id, filename, text):
    suffix = Path(str(filename or "")).suffix.lower()

    if suffix == ".json":
        raw_rows, reminder_settings, source_format = _parse_json_import(text)
    elif suffix == ".csv":
        raw_rows, reminder_settings, source_format = _parse_csv_import(text)
    else:
        raise ValueError(
            "Choisissez un fichier CSV ou JSON produit par JF Apps."
        )

    existing_exact, existing_slots, existing_import_keys = (
        _existing_reading_keys(user_id)
    )

    rows = []
    errors = []
    exact_duplicates = 0
    possible_conflicts = 0
    seen_exact = set()
    seen_slots = set()

    for raw_row in raw_rows:
        line_number = raw_row.get("_line_number", "?")
        if raw_row.get("_invalid"):
            errors.append(
                f"Ligne {line_number} : {raw_row['_invalid']}"
            )
            continue

        try:
            values = validate_reading_values(
                raw_row.get("measured_date"),
                raw_row.get("measured_time"),
                raw_row.get("systolic"),
                raw_row.get("diastolic"),
                raw_row.get("pulse"),
                raw_row.get("note"),
            )
        except ValueError as error:
            errors.append(f"Ligne {line_number} : {error}")
            continue

        import_key = (
            str(raw_row.get("import_key") or "").strip()
            or _reading_import_key(values)
        )
        exact_key = _reading_exact_key(values)
        slot_key = _reading_slot_key(values)

        duplicate_reason = None
        if import_key in existing_import_keys or exact_key in existing_exact:
            duplicate_reason = "exact"
            exact_duplicates += 1
        elif exact_key in seen_exact:
            duplicate_reason = "file_exact"
            exact_duplicates += 1
        elif slot_key in existing_slots or slot_key in seen_slots:
            duplicate_reason = "same_slot"
            possible_conflicts += 1

        rows.append(
            {
                **values,
                "import_key": import_key,
                "duplicate_reason": duplicate_reason,
                "line_number": line_number,
            }
        )
        seen_exact.add(exact_key)
        seen_slots.add(slot_key)

    valid_rows = sum(
        1
        for row in rows
        if row["duplicate_reason"] not in {"exact", "file_exact"}
    )

    reminder_preview = None
    if isinstance(reminder_settings, dict):
        try:
            slots = reminder_settings.get("slots") or []
            normalized_slots = (
                _normalize_reminder_slots(slots)
                if slots
                else []
            )
            reminder_preview = {
                "enabled": bool(reminder_settings.get("enabled")),
                "start_date": (
                    _normalize_date(reminder_settings.get("start_date"))
                    if reminder_settings.get("start_date")
                    else None
                ),
                "end_date": (
                    _normalize_date(reminder_settings.get("end_date"))
                    if reminder_settings.get("end_date")
                    else None
                ),
                "slots": normalized_slots,
            }
            if (
                reminder_preview["start_date"]
                and reminder_preview["end_date"]
                and reminder_preview["end_date"]
                < reminder_preview["start_date"]
            ):
                raise ValueError(
                    "La date de fin du rappel précède sa date de début."
                )
        except ValueError as error:
            errors.append(f"Réglages de rappel : {error}")
            reminder_preview = None

    return {
        "format": source_format,
        "rows": rows,
        "errors": errors,
        "total_rows": len(raw_rows),
        "valid_rows": valid_rows,
        "exact_duplicates": exact_duplicates,
        "possible_conflicts": possible_conflicts,
        "reminder_settings": reminder_preview,
    }


def import_blood_pressure_rows(
    user_id,
    rows,
    *,
    import_source="JF Apps",
    include_same_slot=False,
    reminder_settings=None,
    import_reminders=False,
):
    imported = 0
    skipped = 0
    failures = []

    with get_connection() as conn:
        with conn.cursor() as cur:
            for row in rows:
                reason = row.get("duplicate_reason")
                if reason in {"exact", "file_exact"}:
                    skipped += 1
                    continue
                if reason == "same_slot" and not include_same_slot:
                    skipped += 1
                    continue

                try:
                    values = validate_reading_values(
                        row.get("measured_date"),
                        row.get("measured_time"),
                        row.get("systolic"),
                        row.get("diastolic"),
                        row.get("pulse"),
                        row.get("note"),
                    )
                    import_key = (
                        row.get("import_key")
                        or _reading_import_key(values)
                    )

                    cur.execute(
                        """
                        INSERT INTO blood_pressure_readings (
                            user_id,
                            measured_date,
                            measured_time,
                            systolic,
                            diastolic,
                            pulse,
                            note,
                            import_source,
                            import_key,
                            imported_at
                        )
                        VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, NOW()
                        )
                        ON CONFLICT DO NOTHING
                        RETURNING id;
                        """,
                        (
                            user_id,
                            values["measured_date"],
                            values["measured_time"],
                            values["systolic"],
                            values["diastolic"],
                            values["pulse"],
                            values["note"],
                            str(import_source or "JF Apps")[:100],
                            import_key,
                        ),
                    )
                    if cur.fetchone():
                        imported += 1
                    else:
                        skipped += 1
                except Exception as error:
                    failures.append(
                        f"Ligne {row.get('line_number', '?')} : {error}"
                    )

            if (
                import_reminders
                and reminder_settings
                and reminder_settings.get("start_date")
                and reminder_settings.get("end_date")
                and reminder_settings.get("slots")
            ):
                normalized_slots = _normalize_reminder_slots(
                    reminder_settings["slots"]
                )
                cur.execute(
                    """
                    INSERT INTO blood_pressure_reminder_settings (
                        user_id,
                        enabled,
                        target_per_day,
                        start_date,
                        end_date
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        enabled = EXCLUDED.enabled,
                        target_per_day = EXCLUDED.target_per_day,
                        start_date = EXCLUDED.start_date,
                        end_date = EXCLUDED.end_date,
                        updated_at = NOW();
                    """,
                    (
                        user_id,
                        bool(reminder_settings.get("enabled")),
                        len(normalized_slots),
                        reminder_settings["start_date"],
                        reminder_settings["end_date"],
                    ),
                )
                cur.execute(
                    """
                    DELETE FROM blood_pressure_reminder_slots
                    WHERE user_id = %s;
                    """,
                    (user_id,),
                )
                _insert_reminder_slots(
                    cur,
                    user_id,
                    normalized_slots,
                )

            conn.commit()

    return {
        "imported": imported,
        "skipped": skipped,
        "failures": failures,
        "reminders_imported": bool(
            import_reminders
            and reminder_settings
            and reminder_settings.get("slots")
        ),
    }



MAX_REMINDER_SLOTS = 10


def _normalize_target_per_day(
    value,
) -> int:
    return _normalize_integer(
        value,
        label=(
            "Le nombre de prises "
            "par jour"
        ),
        minimum=1,
        maximum=MAX_REMINDER_SLOTS,
    )


def _minutes_from_time(
    value,
) -> int:
    normalized = _normalize_time(
        value
    )

    return (
        normalized.hour * 60
        + normalized.minute
    )


def _default_reminder_slots(
    target_per_day,
):
    """Crée des horaires de départ pour les anciens réglages."""

    target = _normalize_target_per_day(
        target_per_day
    )

    if target == 1:
        return [
            {
                "label": "Prise quotidienne",
                "start_time": time(
                    hour=6,
                    minute=0,
                ),
                "end_time": time(
                    hour=22,
                    minute=0,
                ),
                "sort_order": 1,
            }
        ]

    if target == 2:
        return [
            {
                "label": "Matin",
                "start_time": time(
                    hour=6,
                    minute=0,
                ),
                "end_time": time(
                    hour=11,
                    minute=0,
                ),
                "sort_order": 1,
            },
            {
                "label": "Soir",
                "start_time": time(
                    hour=17,
                    minute=0,
                ),
                "end_time": time(
                    hour=22,
                    minute=0,
                ),
                "sort_order": 2,
            },
        ]

    if target == 3:
        return [
            {
                "label": "Matin",
                "start_time": time(
                    hour=6,
                    minute=0,
                ),
                "end_time": time(
                    hour=10,
                    minute=0,
                ),
                "sort_order": 1,
            },
            {
                "label": "Après-midi",
                "start_time": time(
                    hour=12,
                    minute=0,
                ),
                "end_time": time(
                    hour=16,
                    minute=0,
                ),
                "sort_order": 2,
            },
            {
                "label": "Soir",
                "start_time": time(
                    hour=18,
                    minute=0,
                ),
                "end_time": time(
                    hour=22,
                    minute=0,
                ),
                "sort_order": 3,
            },
        ]

    day_start = 6 * 60
    day_end = 22 * 60
    segment = max(
        (day_end - day_start)
        // target,
        30,
    )
    slots = []

    for index in range(target):
        start_minutes = (
            day_start
            + index * segment
        )
        end_minutes = (
            day_end
            if index == target - 1
            else (
                day_start
                + (index + 1) * segment
                - 1
            )
        )

        slots.append(
            {
                "label": (
                    f"Prise {index + 1}"
                ),
                "start_time": time(
                    hour=(
                        start_minutes // 60
                    ),
                    minute=(
                        start_minutes % 60
                    ),
                ),
                "end_time": time(
                    hour=(
                        end_minutes // 60
                    ),
                    minute=(
                        end_minutes % 60
                    ),
                ),
                "sort_order": (
                    index + 1
                ),
            }
        )

    return slots


def _fetch_reminder_slots(
    cur,
    user_id,
):
    cur.execute(
        """
        SELECT
            id,
            label,
            start_time,
            end_time,
            sort_order,
            created_at,
            updated_at
        FROM blood_pressure_reminder_slots
        WHERE user_id = %s
        ORDER BY
            sort_order,
            start_time,
            id;
        """,
        (user_id,),
    )

    return cur.fetchall()


def _insert_reminder_slots(
    cur,
    user_id,
    slots,
):
    cur.executemany(
        """
        INSERT INTO blood_pressure_reminder_slots (
            user_id,
            label,
            start_time,
            end_time,
            sort_order
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s
        );
        """,
        [
            (
                user_id,
                slot["label"],
                slot["start_time"],
                slot["end_time"],
                slot["sort_order"],
            )
            for slot in slots
        ],
    )


def _ensure_reminder_slots(
    cur,
    user_id,
    target_per_day,
):
    slots = _fetch_reminder_slots(
        cur,
        user_id,
    )

    if slots:
        return slots

    default_slots = (
        _default_reminder_slots(
            target_per_day
        )
    )

    _insert_reminder_slots(
        cur,
        user_id,
        default_slots,
    )

    return _fetch_reminder_slots(
        cur,
        user_id,
    )


def _normalize_reminder_slots(
    slots,
):
    if not slots:
        raise ValueError(
            "Ajoutez au moins une prise quotidienne."
        )

    if len(slots) > MAX_REMINDER_SLOTS:
        raise ValueError(
            "Un maximum de 10 prises quotidiennes "
            "peut être configuré."
        )

    normalized = []

    for index, slot in enumerate(
        slots,
        start=1,
    ):
        label = str(
            slot.get("label")
            or ""
        ).strip()

        if not label:
            label = (
                f"Prise {index}"
            )

        if len(label) > 60:
            raise ValueError(
                "Le nom d’une prise ne peut pas "
                "dépasser 60 caractères."
            )

        start_time = _normalize_time(
            slot.get("start_time")
        )
        end_time = _normalize_time(
            slot.get("end_time")
        )

        if end_time <= start_time:
            raise ValueError(
                f"La plage « {label} » doit se terminer "
                "après son heure de début."
            )

        normalized.append(
            {
                "label": label,
                "start_time": start_time,
                "end_time": end_time,
            }
        )

    normalized.sort(
        key=lambda slot: (
            slot["start_time"],
            slot["end_time"],
            slot["label"].lower(),
        )
    )

    previous = None

    for index, slot in enumerate(
        normalized,
        start=1,
    ):
        if (
            previous is not None
            and slot["start_time"]
            <= previous["end_time"]
        ):
            raise ValueError(
                (
                    f"Les plages « {previous['label']} » "
                    f"et « {slot['label']} » se chevauchent. "
                    "Laissez au moins une minute entre elles."
                )
            )

        slot["sort_order"] = index
        previous = slot

    return normalized


def get_blood_pressure_reminder_settings(
    user_id,
):
    """Retourne la période et les plages horaires privées."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    enabled,
                    target_per_day,
                    start_date,
                    end_date,
                    created_at,
                    updated_at
                FROM blood_pressure_reminder_settings
                WHERE user_id = %s;
                """,
                (user_id,),
            )

            settings = cur.fetchone()

            if settings is None:
                return {
                    "configured": False,
                    "enabled": False,
                    "target_per_day": 2,
                    "start_date": None,
                    "end_date": None,
                    "created_at": None,
                    "updated_at": None,
                    "slots": (
                        _default_reminder_slots(
                            2
                        )
                    ),
                }

            slots = _ensure_reminder_slots(
                cur,
                user_id,
                settings[
                    "target_per_day"
                ],
            )

            conn.commit()

            return {
                **settings,
                "configured": True,
                "slots": slots,
            }


def save_blood_pressure_reminder_schedule(
    user_id,
    *,
    enabled,
    start_date,
    end_date,
    slots,
):
    """Enregistre la période et les plages choisies par l’utilisateur."""

    normalized_start = (
        _normalize_date(
            start_date
        )
        if start_date
        else None
    )
    normalized_end = (
        _normalize_date(
            end_date
        )
        if end_date
        else None
    )

    if normalized_start is None:
        raise ValueError(
            "La date de début est obligatoire."
        )

    if normalized_end is None:
        raise ValueError(
            "La date de fin est obligatoire."
        )

    if normalized_end < normalized_start:
        raise ValueError(
            "La date de fin doit être "
            "égale ou postérieure à "
            "la date de début."
        )

    normalized_slots = (
        _normalize_reminder_slots(
            slots
        )
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO
                blood_pressure_reminder_settings (
                    user_id,
                    enabled,
                    target_per_day,
                    start_date,
                    end_date,
                    updated_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW()
                )
                ON CONFLICT (user_id)
                DO UPDATE SET
                    enabled = EXCLUDED.enabled,
                    target_per_day =
                        EXCLUDED.target_per_day,
                    start_date =
                        EXCLUDED.start_date,
                    end_date =
                        EXCLUDED.end_date,
                    updated_at = NOW();
                """,
                (
                    user_id,
                    bool(enabled),
                    len(
                        normalized_slots
                    ),
                    normalized_start,
                    normalized_end,
                ),
            )

            cur.execute(
                """
                DELETE FROM
                blood_pressure_reminder_slots
                WHERE user_id = %s;
                """,
                (user_id,),
            )

            _insert_reminder_slots(
                cur,
                user_id,
                normalized_slots,
            )

            conn.commit()


def save_blood_pressure_reminder_settings(
    user_id,
    *,
    enabled,
    target_per_day,
    start_date,
    end_date,
):
    """Compatibilité avec l’ancien réglage par simple quantité."""

    save_blood_pressure_reminder_schedule(
        user_id,
        enabled=enabled,
        start_date=start_date,
        end_date=end_date,
        slots=_default_reminder_slots(
            target_per_day
        ),
    )


def get_blood_pressure_reminder_status(
    user_id,
    on_date,
    current_time=None,
):
    """Calcule les prises complétées sans notion de retard.

    Les plages servent de repères pour l’avis.
    Toute mesure faite dans la journée compte,
    même si son heure est hors de la plage prévue.
    """

    normalized_date = _normalize_date(
        on_date
    )
    normalized_current_time = (
        _normalize_time(
            current_time
        )
        if current_time is not None
        else time(
            hour=12,
            minute=0,
        )
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    enabled,
                    target_per_day,
                    start_date,
                    end_date
                FROM blood_pressure_reminder_settings
                WHERE user_id = %s;
                """,
                (user_id,),
            )

            settings = cur.fetchone()

            if settings is None:
                return {
                    "configured": False,
                    "enabled": False,
                    "active": False,
                    "date": normalized_date,
                    "current_time": (
                        normalized_current_time
                    ),
                    "target_per_day": 2,
                    "completed_count": 0,
                    "remaining_count": 0,
                    "total_readings_count": 0,
                    "start_date": None,
                    "end_date": None,
                    "state": "not_configured",
                    "slots": [],
                    "next_slot": None,
                }

            slots = _ensure_reminder_slots(
                cur,
                user_id,
                settings[
                    "target_per_day"
                ],
            )

            cur.execute(
                """
                SELECT
                    id,
                    measured_time
                FROM blood_pressure_readings
                WHERE user_id = %s
                  AND measured_date = %s
                ORDER BY
                    measured_time,
                    id;
                """,
                (
                    user_id,
                    normalized_date,
                ),
            )

            readings = cur.fetchall()
            conn.commit()

    active = bool(
        settings["enabled"]
        and settings["start_date"]
        and settings["end_date"]
        and (
            settings["start_date"]
            <= normalized_date
            <= settings["end_date"]
        )
    )

    reading_times = [
        reading["measured_time"]
        for reading in readings
    ]

    slot_statuses = []

    for index, slot in enumerate(
        slots
    ):
        completed_time = (
            reading_times[index]
            if index < len(
                reading_times
            )
            else None
        )

        completed = (
            completed_time is not None
        )

        if completed:
            status = "completed"
        elif (
            normalized_current_time
            >= slot["start_time"]
        ):
            status = "due"
        else:
            status = "upcoming"

        slot_statuses.append(
            {
                "id": slot["id"],
                "label": slot["label"],
                "start_time": (
                    slot["start_time"]
                ),
                "end_time": (
                    slot["end_time"]
                ),
                "sort_order": (
                    slot["sort_order"]
                ),
                "completed": completed,
                "completed_time": (
                    completed_time
                ),
                "status": status,
            }
        )

    completed_count = min(
        len(readings),
        len(slot_statuses),
    )
    remaining_count = (
        max(
            len(slot_statuses)
            - completed_count,
            0,
        )
        if active
        else 0
    )

    pending_slots = [
        slot
        for slot in slot_statuses
        if not slot["completed"]
    ]

    due_slots = [
        slot
        for slot in pending_slots
        if slot["status"]
        == "due"
    ]
    upcoming_slots = [
        slot
        for slot in pending_slots
        if slot["status"]
        == "upcoming"
    ]

    if not active:
        state = "inactive"
        next_slot = None
    elif remaining_count == 0:
        state = "complete"
        next_slot = None
    elif due_slots:
        state = "due"
        next_slot = due_slots[0]
    else:
        state = "upcoming"
        next_slot = (
            upcoming_slots[0]
            if upcoming_slots
            else pending_slots[0]
        )

    return {
        "configured": True,
        "enabled": bool(
            settings["enabled"]
        ),
        "active": active,
        "date": normalized_date,
        "current_time": (
            normalized_current_time
        ),
        "target_per_day": len(
            slot_statuses
        ),
        "completed_count": (
            completed_count
        ),
        "remaining_count": (
            remaining_count
        ),
        "total_readings_count": len(
            readings
        ),
        "start_date": (
            settings["start_date"]
        ),
        "end_date": (
            settings["end_date"]
        ),
        "state": state,
        "slots": slot_statuses,
        "next_slot": next_slot,
    }
