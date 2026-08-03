from __future__ import annotations

import unicodedata

from db import (
    create_category,
    get_accessible_families,
    get_categories,
    get_connection,
)


DEFAULT_CATEGORY_NAME = "Sans catégorie"


def normalized_text(value):
    """Clé de tri et de recherche insensible à la casse et aux accents."""

    text = str(value or "").strip().casefold()
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(character)
    )


def init_grocery_preferences_schema():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS grocery_family_preferences (
                    family_id INTEGER PRIMARY KEY
                        REFERENCES families(id)
                        ON DELETE CASCADE,
                    categories_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            conn.commit()


def _require_family_access(user_id, family_id):
    if user_id is None or family_id is None:
        raise PermissionError("La famille active est invalide.")

    accessible_ids = {
        int(row["id"])
        for row in get_accessible_families(user_id)
    }
    if int(family_id) not in accessible_ids:
        raise PermissionError(
            "Vous n’avez pas accès à cette famille."
        )


def categories_are_enabled(user_id, family_id):
    _require_family_access(user_id, family_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT categories_enabled
                FROM grocery_family_preferences
                WHERE family_id = %s;
                """,
                (family_id,),
            )
            row = cur.fetchone()

            if row is None:
                cur.execute(
                    """
                    INSERT INTO grocery_family_preferences (
                        family_id,
                        categories_enabled
                    )
                    VALUES (%s, TRUE)
                    ON CONFLICT (family_id) DO NOTHING;
                    """,
                    (family_id,),
                )
                conn.commit()
                return True

            return bool(row["categories_enabled"])


def set_categories_enabled(user_id, family_id, enabled):
    _require_family_access(user_id, family_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO grocery_family_preferences (
                    family_id,
                    categories_enabled
                )
                VALUES (%s, %s)
                ON CONFLICT (family_id)
                DO UPDATE SET
                    categories_enabled = EXCLUDED.categories_enabled,
                    updated_at = NOW();
                """,
                (family_id, bool(enabled)),
            )
            conn.commit()


def get_or_create_default_category_id(user_id, family_id):
    """Retourne une catégorie technique utilisée quand les catégories sont masquées."""

    _require_family_access(user_id, family_id)
    categories = get_categories(user_id, family_id)

    for category in categories:
        if normalized_text(category["name"]) == normalized_text(
            DEFAULT_CATEGORY_NAME
        ):
            return int(category["id"])

    try:
        return int(
            create_category(
                user_id,
                family_id,
                DEFAULT_CATEGORY_NAME,
            )
        )
    except ValueError:
        # Une autre requête a pu la créer entre-temps.
        categories = get_categories(user_id, family_id)
        for category in categories:
            if normalized_text(category["name"]) == normalized_text(
                DEFAULT_CATEGORY_NAME
            ):
                return int(category["id"])
        raise
