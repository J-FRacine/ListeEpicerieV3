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
