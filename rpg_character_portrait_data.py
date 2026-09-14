"""Persistance du portrait d'un personnage JDR."""
from __future__ import annotations

from db import get_connection


_SCHEMA_READY = False


def ensure_rpg_portrait_schema():
    """Crée la table de portraits de façon idempotente et non destructive."""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rpg_character_portraits (
                    character_id BIGINT PRIMARY KEY
                        REFERENCES rpg_characters(id)
                        ON DELETE CASCADE,
                    file_name TEXT,
                    mime_type TEXT NOT NULL,
                    image_data BYTEA NOT NULL,
                    image_width INTEGER,
                    image_height INTEGER,
                    image_size INTEGER NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            conn.commit()

    _SCHEMA_READY = True


def _require_character(cur, user_id, character_id):
    cur.execute(
        """
        SELECT id
        FROM rpg_characters
        WHERE id = %s
          AND user_id = %s;
        """,
        (character_id, user_id),
    )
    if cur.fetchone() is None:
        raise ValueError(
            "Ce personnage n’existe plus ou ne vous appartient pas."
        )


def get_rpg_portrait(user_id, character_id):
    ensure_rpg_portrait_schema()

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                SELECT
                    character_id,
                    file_name,
                    mime_type,
                    image_data,
                    image_width,
                    image_height,
                    image_size,
                    created_at,
                    updated_at
                FROM rpg_character_portraits
                WHERE character_id = %s;
                """,
                (character_id,),
            )
            return cur.fetchone()


def save_rpg_portrait(user_id, character_id, portrait):
    ensure_rpg_portrait_schema()

    image_data = portrait.get("image_data")
    if isinstance(image_data, memoryview):
        image_data = image_data.tobytes()
    if not isinstance(image_data, (bytes, bytearray)) or not image_data:
        raise ValueError("La photo normalisée est invalide.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                INSERT INTO rpg_character_portraits (
                    character_id,
                    file_name,
                    mime_type,
                    image_data,
                    image_width,
                    image_height,
                    image_size
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (character_id)
                DO UPDATE SET
                    file_name = EXCLUDED.file_name,
                    mime_type = EXCLUDED.mime_type,
                    image_data = EXCLUDED.image_data,
                    image_width = EXCLUDED.image_width,
                    image_height = EXCLUDED.image_height,
                    image_size = EXCLUDED.image_size,
                    updated_at = NOW();
                """,
                (
                    character_id,
                    portrait.get("file_name"),
                    portrait.get("mime_type") or "image/jpeg",
                    bytes(image_data),
                    portrait.get("width"),
                    portrait.get("height"),
                    portrait.get("image_size") or len(image_data),
                ),
            )
            conn.commit()


def delete_rpg_portrait(user_id, character_id):
    ensure_rpg_portrait_schema()

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                DELETE FROM rpg_character_portraits
                WHERE character_id = %s;
                """,
                (character_id,),
            )
            conn.commit()
