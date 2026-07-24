import json

from psycopg import sql

import db as _db


def log_activity(
    cur,
    family_id,
    user_id,
    action_type,
    entity_type,
    entity_id,
    entity_name,
    details=None,
):
    cur.execute(
        """
        INSERT INTO activity_log (
            family_id,
            user_id,
            action_type,
            entity_type,
            entity_id,
            entity_name,
            details
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb);
        """,
        (
            family_id,
            user_id,
            action_type,
            entity_type,
            entity_id,
            str(entity_name or ""),
            json.dumps(details or {}, ensure_ascii=False),
        ),
    )


def next_sort_order(cur, table_name, family_id):
    if table_name not in {"categories", "stores"}:
        raise ValueError("Table de classement invalide.")

    cur.execute(
        sql.SQL(
            """
            SELECT COALESCE(MAX(sort_order), 0) + 10 AS next_order
            FROM {}
            WHERE family_id = %s
              AND deleted_at IS NULL;
            """
        ).format(sql.Identifier(table_name)),
        (family_id,),
    )
    return cur.fetchone()["next_order"]


def move_ordered_entry(
    cur,
    table_name,
    family_id,
    entry_id,
    direction,
):
    if table_name not in {"categories", "stores"}:
        raise ValueError("Table de classement invalide.")

    direction = int(direction)
    if direction not in {-1, 1}:
        raise ValueError("Direction de déplacement invalide.")

    table = sql.Identifier(table_name)
    cur.execute(
        sql.SQL(
            """
            SELECT id, name
            FROM {}
            WHERE family_id = %s
              AND deleted_at IS NULL
            ORDER BY sort_order, LOWER(name), name, id;
            """
        ).format(table),
        (family_id,),
    )
    rows = cur.fetchall()
    identifiers = [row["id"] for row in rows]

    if entry_id not in identifiers:
        raise ValueError("Cet élément n’existe plus.")

    position = identifiers.index(entry_id)
    destination = position + direction

    if destination < 0 or destination >= len(rows):
        return False

    # Renumérotation stable, puis échange des deux positions.
    for index, row in enumerate(rows, start=1):
        cur.execute(
            sql.SQL(
                "UPDATE {} SET sort_order = %s WHERE id = %s;"
            ).format(table),
            (index * 10, row["id"]),
        )

    other = rows[destination]
    cur.execute(
        sql.SQL(
            "UPDATE {} SET sort_order = %s WHERE id = %s;"
        ).format(table),
        ((destination + 1) * 10, entry_id),
    )
    cur.execute(
        sql.SQL(
            "UPDATE {} SET sort_order = %s WHERE id = %s;"
        ).format(table),
        ((position + 1) * 10, other["id"]),
    )
    return True


def get_activity_history(user_id, family_id, limit=100):
    safe_limit = max(1, min(int(limit or 100), 500))

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                f"""
                SELECT
                    activity.id,
                    activity.action_type,
                    activity.entity_type,
                    activity.entity_id,
                    activity.entity_name,
                    activity.details,
                    activity.created_at,
                    COALESCE(
                        user_account.display_name,
                        'Utilisateur supprimé'
                    ) AS actor_name
                FROM activity_log AS activity
                LEFT JOIN users AS user_account
                  ON user_account.id = activity.user_id
                WHERE activity.family_id = %s
                ORDER BY activity.created_at DESC, activity.id DESC
                LIMIT {safe_limit};
                """,
                (family_id,),
            )
            return cur.fetchall()


def purge_expired_trash(user_id, family_id):
    """Supprime les éléments conservés dans la corbeille depuis 30 jours."""

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)

            cur.execute(
                """
                DELETE FROM items
                WHERE family_id = %s
                  AND deleted_at IS NOT NULL
                  AND deleted_at < NOW() - INTERVAL '30 days';
                """,
                (family_id,),
            )

            cur.execute(
                """
                DELETE FROM categories AS category
                WHERE category.family_id = %s
                  AND category.deleted_at IS NOT NULL
                  AND category.deleted_at < NOW() - INTERVAL '30 days'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM items AS item
                      WHERE item.category_id = category.id
                  );
                """,
                (family_id,),
            )

            cur.execute(
                """
                DELETE FROM stores AS store
                WHERE store.family_id = %s
                  AND store.deleted_at IS NOT NULL
                  AND store.deleted_at < NOW() - INTERVAL '30 days'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM items AS item
                      WHERE item.store_id = store.id
                  );
                """,
                (family_id,),
            )

            conn.commit()
