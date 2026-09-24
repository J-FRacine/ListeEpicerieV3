"""Persistance de la photo principale des recettes."""
from __future__ import annotations

import db as _db


def _require_recipe(cur, user_id, recipe_id):
    cur.execute(
        """
        SELECT id, family_id, name
        FROM grocery_recipes
        WHERE id = %s;
        """,
        (recipe_id,),
    )
    recipe = cur.fetchone()
    if recipe is None:
        raise ValueError("Cette recette n’existe plus.")
    _db._require_family_access(cur, user_id, recipe["family_id"])
    return recipe


def get_recipe_photo(user_id, recipe_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _require_recipe(cur, user_id, recipe_id)
            cur.execute(
                """
                SELECT
                    recipe_id,
                    file_name,
                    mime_type,
                    image_data,
                    image_width,
                    image_height,
                    image_size,
                    thumbnail_data,
                    thumbnail_width,
                    thumbnail_height,
                    thumbnail_size,
                    created_at,
                    updated_at
                FROM grocery_recipe_photos
                WHERE recipe_id = %s;
                """,
                (recipe_id,),
            )
            return cur.fetchone()


def get_recipe_photo_thumbnails(user_id, family_id):
    if family_id is None:
        return {}

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT
                    photo.recipe_id,
                    'image/jpeg'::TEXT AS mime_type,
                    photo.thumbnail_data AS image_data,
                    photo.thumbnail_width AS image_width,
                    photo.thumbnail_height AS image_height,
                    photo.thumbnail_size AS image_size
                FROM grocery_recipe_photos AS photo
                JOIN grocery_recipes AS recipe
                  ON recipe.id = photo.recipe_id
                WHERE recipe.family_id = %s;
                """,
                (family_id,),
            )
            return {
                int(row["recipe_id"]): dict(row)
                for row in cur.fetchall()
            }


def save_recipe_photo(user_id, recipe_id, photo):
    image_data = photo.get("image_data")
    thumbnail_data = photo.get("thumbnail_data")

    if isinstance(image_data, memoryview):
        image_data = image_data.tobytes()
    if isinstance(thumbnail_data, memoryview):
        thumbnail_data = thumbnail_data.tobytes()

    if not isinstance(image_data, (bytes, bytearray)) or not image_data:
        raise ValueError("La photo normalisée est invalide.")
    if not isinstance(thumbnail_data, (bytes, bytearray)) or not thumbnail_data:
        raise ValueError("La vignette normalisée est invalide.")

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _require_recipe(cur, user_id, recipe_id)
            cur.execute(
                """
                INSERT INTO grocery_recipe_photos (
                    recipe_id,
                    file_name,
                    mime_type,
                    image_data,
                    image_width,
                    image_height,
                    image_size,
                    thumbnail_data,
                    thumbnail_width,
                    thumbnail_height,
                    thumbnail_size
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (recipe_id)
                DO UPDATE SET
                    file_name = EXCLUDED.file_name,
                    mime_type = EXCLUDED.mime_type,
                    image_data = EXCLUDED.image_data,
                    image_width = EXCLUDED.image_width,
                    image_height = EXCLUDED.image_height,
                    image_size = EXCLUDED.image_size,
                    thumbnail_data = EXCLUDED.thumbnail_data,
                    thumbnail_width = EXCLUDED.thumbnail_width,
                    thumbnail_height = EXCLUDED.thumbnail_height,
                    thumbnail_size = EXCLUDED.thumbnail_size,
                    updated_at = NOW();
                """,
                (
                    recipe_id,
                    photo.get("file_name"),
                    photo.get("mime_type") or "image/jpeg",
                    bytes(image_data),
                    photo.get("width"),
                    photo.get("height"),
                    photo.get("image_size") or len(image_data),
                    bytes(thumbnail_data),
                    photo.get("thumbnail_width"),
                    photo.get("thumbnail_height"),
                    photo.get("thumbnail_size") or len(thumbnail_data),
                ),
            )
            conn.commit()


def delete_recipe_photo(user_id, recipe_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _require_recipe(cur, user_id, recipe_id)
            cur.execute(
                """
                DELETE FROM grocery_recipe_photos
                WHERE recipe_id = %s;
                """,
                (recipe_id,),
            )
            conn.commit()
