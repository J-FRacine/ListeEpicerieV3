import db as _db

from grocery_common import log_activity


def _item_select_sql(extra_where="", order_by="item.id"):
    return f"""
        SELECT
            item.id,
            item.category_id,
            item.store_id,
            item.name,
            item.note,
            item.quantity,
            item.needed,
            item.times_needed,
            item.last_needed_at,
            category.name AS category,
            category.sort_order AS category_order,
            COALESCE(store.name, 'Sans magasin') AS store,
            COALESCE(store.sort_order, 999999) AS store_order
        FROM items AS item
        JOIN categories AS category
          ON category.id = item.category_id
         AND category.deleted_at IS NULL
        LEFT JOIN stores AS store
          ON store.id = item.store_id
        WHERE item.family_id = %s
          AND item.deleted_at IS NULL
          {extra_where}
        ORDER BY {order_by};
    """


def get_items(user_id, family_id):
    if family_id is None:
        return []

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(_item_select_sql(), (family_id,))
            return cur.fetchall()


def get_frequent_items(user_id, family_id, limit=8):
    safe_limit = max(1, min(int(limit or 8), 20))

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                _item_select_sql(
                    extra_where=(
                        "AND item.needed = 0 "
                        "AND item.times_needed > 0"
                    ),
                    order_by=(
                        "item.times_needed DESC, "
                        "item.last_needed_at DESC NULLS LAST, "
                        "LOWER(item.name), item.id "
                        f"LIMIT {safe_limit}"
                    ),
                ),
                (family_id,),
            )
            return cur.fetchall()


def _category_belongs(cur, family_id, category_id):
    cur.execute(
        """
        SELECT 1
        FROM categories
        WHERE id = %s
          AND family_id = %s
          AND deleted_at IS NULL
        LIMIT 1;
        """,
        (category_id, family_id),
    )
    return cur.fetchone() is not None


def _store_belongs(cur, family_id, store_id):
    if store_id is None:
        return True

    cur.execute(
        """
        SELECT 1
        FROM stores
        WHERE id = %s
          AND family_id = %s
          AND deleted_at IS NULL
        LIMIT 1;
        """,
        (store_id, family_id),
    )
    return cur.fetchone() is not None


def _default_store_id(cur, family_id):
    cur.execute(
        """
        SELECT id
        FROM stores
        WHERE family_id = %s
          AND deleted_at IS NULL
        ORDER BY sort_order, LOWER(name), id
        LIMIT 1;
        """,
        (family_id,),
    )
    row = cur.fetchone()
    return row["id"] if row else None


def add_item(
    user_id,
    family_id,
    category_id,
    name,
    quantity,
    needed,
    note="",
    store_id=None,
):
    item_name = str(name or "").strip()
    item_note = str(note or "").strip()
    item_quantity = int(quantity or 1)
    item_needed = 1 if needed else 0

    if not item_name:
        raise ValueError("Le nom de l’item est obligatoire.")
    if item_quantity < 1:
        raise ValueError("La quantité doit être d’au moins 1.")

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            if not _category_belongs(cur, family_id, category_id):
                raise ValueError("La catégorie choisie est invalide.")

            if store_id is None:
                store_id = _default_store_id(cur, family_id)
            if not _store_belongs(cur, family_id, store_id):
                raise ValueError("Le magasin choisi est invalide.")

            cur.execute(
                """
                INSERT INTO items (
                    family_id,
                    category_id,
                    store_id,
                    name,
                    note,
                    quantity,
                    needed,
                    times_needed,
                    last_needed_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    CASE WHEN %s = 1 THEN 1 ELSE 0 END,
                    CASE WHEN %s = 1 THEN NOW() ELSE NULL END
                )
                RETURNING id;
                """,
                (
                    family_id,
                    category_id,
                    store_id,
                    item_name,
                    item_note,
                    item_quantity,
                    item_needed,
                    item_needed,
                    item_needed,
                ),
            )
            item_id = cur.fetchone()["id"]
            log_activity(
                cur,
                family_id,
                user_id,
                "item_created",
                "item",
                item_id,
                item_name,
                {"needed": bool(item_needed)},
            )
            conn.commit()
            return item_id


def update_item(
    user_id,
    item_id,
    category_id,
    name,
    quantity,
    needed,
    note="",
    store_id=None,
):
    item_name = str(name or "").strip()
    item_note = str(note or "").strip()
    item_quantity = int(quantity or 1)
    item_needed = 1 if needed else 0

    if not item_name:
        raise ValueError("Le nom de l’item est obligatoire.")
    if item_quantity < 1:
        raise ValueError("La quantité doit être d’au moins 1.")

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT family_id, name, needed
                FROM items
                WHERE id = %s
                  AND deleted_at IS NULL;
                """,
                (item_id,),
            )
            current = cur.fetchone()
            if current is None:
                raise ValueError("Cet item n’existe plus.")

            family_id = current["family_id"]
            _db._require_family_access(cur, user_id, family_id)
            if not _category_belongs(cur, family_id, category_id):
                raise ValueError("La catégorie choisie est invalide.")

            if store_id is None:
                store_id = _default_store_id(cur, family_id)
            if not _store_belongs(cur, family_id, store_id):
                raise ValueError("Le magasin choisi est invalide.")

            added_to_needs = current["needed"] == 0 and item_needed == 1
            cur.execute(
                """
                UPDATE items
                SET
                    category_id = %s,
                    store_id = %s,
                    name = %s,
                    note = %s,
                    quantity = %s,
                    needed = %s,
                    times_needed = times_needed + %s,
                    last_needed_at = CASE
                        WHEN %s = 1 THEN NOW()
                        ELSE last_needed_at
                    END
                WHERE id = %s;
                """,
                (
                    category_id,
                    store_id,
                    item_name,
                    item_note,
                    item_quantity,
                    item_needed,
                    1 if added_to_needs else 0,
                    1 if added_to_needs else 0,
                    item_id,
                ),
            )
            log_activity(
                cur,
                family_id,
                user_id,
                "item_updated",
                "item",
                item_id,
                item_name,
                {"old_name": current["name"]},
            )

            if current["needed"] != item_needed:
                log_activity(
                    cur,
                    family_id,
                    user_id,
                    (
                        "item_needed_added"
                        if item_needed
                        else "item_needed_removed"
                    ),
                    "item",
                    item_id,
                    item_name,
                )
            conn.commit()


def _set_needed(cur, user_id, item_id, needed):
    cur.execute(
        """
        SELECT family_id, name, needed
        FROM items
        WHERE id = %s
          AND deleted_at IS NULL;
        """,
        (item_id,),
    )
    item = cur.fetchone()
    if item is None:
        raise ValueError("Cet item n’existe plus.")

    _db._require_family_access(cur, user_id, item["family_id"])
    new_value = 1 if needed else 0
    if item["needed"] == new_value:
        return new_value

    cur.execute(
        """
        UPDATE items
        SET
            needed = %s,
            times_needed = times_needed + %s,
            last_needed_at = CASE
                WHEN %s = 1 THEN NOW()
                ELSE last_needed_at
            END
        WHERE id = %s;
        """,
        (
            new_value,
            1 if new_value else 0,
            new_value,
            item_id,
        ),
    )
    log_activity(
        cur,
        item["family_id"],
        user_id,
        "item_needed_added" if new_value else "item_needed_removed",
        "item",
        item_id,
        item["name"],
    )
    return new_value


def set_item_needed(user_id, item_id, needed):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            result = _set_needed(cur, user_id, item_id, needed)
            conn.commit()
            return result


def toggle_needed(user_id, item_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT needed
                FROM items
                WHERE id = %s
                  AND deleted_at IS NULL;
                """,
                (item_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("Cet item n’existe plus.")

            result = _set_needed(
                cur,
                user_id,
                item_id,
                row["needed"] == 0,
            )
            conn.commit()
            return result


def delete_item(user_id, item_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT family_id, name
                FROM items
                WHERE id = %s
                  AND deleted_at IS NULL;
                """,
                (item_id,),
            )
            item = cur.fetchone()
            if item is None:
                raise ValueError("Cet item n’existe plus.")

            _db._require_family_access(cur, user_id, item["family_id"])
            cur.execute(
                """
                UPDATE items
                SET deleted_at = NOW(), deleted_by_user_id = %s
                WHERE id = %s;
                """,
                (user_id, item_id),
            )
            log_activity(
                cur,
                item["family_id"],
                user_id,
                "item_deleted",
                "item",
                item_id,
                item["name"],
            )
            conn.commit()


def get_deleted_items(user_id, family_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT
                    item.id,
                    item.name,
                    item.note,
                    item.quantity,
                    item.needed,
                    item.deleted_at,
                    category.name AS category,
                    COALESCE(store.name, 'Sans magasin') AS store
                FROM items AS item
                LEFT JOIN categories AS category
                  ON category.id = item.category_id
                LEFT JOIN stores AS store
                  ON store.id = item.store_id
                WHERE item.family_id = %s
                  AND item.deleted_at IS NOT NULL
                ORDER BY item.deleted_at DESC, LOWER(item.name);
                """,
                (family_id,),
            )
            return cur.fetchall()


def restore_item(user_id, family_id, item_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT name
                FROM items
                WHERE id = %s
                  AND family_id = %s
                  AND deleted_at IS NOT NULL;
                """,
                (item_id, family_id),
            )
            item = cur.fetchone()
            if item is None:
                raise ValueError("Cet item n’est plus dans la corbeille.")

            cur.execute(
                """
                UPDATE items
                SET deleted_at = NULL, deleted_by_user_id = NULL
                WHERE id = %s;
                """,
                (item_id,),
            )
            log_activity(
                cur,
                family_id,
                user_id,
                "item_restored",
                "item",
                item_id,
                item["name"],
            )
            conn.commit()


def permanently_delete_item(user_id, family_id, item_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT name
                FROM items
                WHERE id = %s
                  AND family_id = %s
                  AND deleted_at IS NOT NULL;
                """,
                (item_id, family_id),
            )
            item = cur.fetchone()
            if item is None:
                raise ValueError("Cet item n’est plus dans la corbeille.")

            cur.execute("DELETE FROM items WHERE id = %s;", (item_id,))
            log_activity(
                cur,
                family_id,
                user_id,
                "item_deleted_permanently",
                "item",
                item_id,
                item["name"],
            )
            conn.commit()
