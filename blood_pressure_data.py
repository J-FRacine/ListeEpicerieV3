from __future__ import annotations

from datetime import date, time

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
