import db as _db

from grocery_common import log_activity, move_ordered_entry, next_sort_order


# ---------------------------------------------------------
# CATÉGORIES
# ---------------------------------------------------------


def get_categories(user_id, family_id):
    if family_id is None:
        return []

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT id, name, sort_order
                FROM categories
                WHERE family_id = %s
                  AND deleted_at IS NULL
                ORDER BY sort_order, LOWER(name), name, id;
                """,
                (family_id,),
            )
            return cur.fetchall()


def get_categories_with_counts(user_id, family_id):
    if family_id is None:
        return []

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT
                    category.id,
                    category.name,
                    category.sort_order,
                    COUNT(item.id) FILTER (
                        WHERE item.deleted_at IS NULL
                    )::INTEGER AS item_count,
                    COUNT(item.id) FILTER (
                        WHERE item.deleted_at IS NOT NULL
                    )::INTEGER AS deleted_item_count,
                    COUNT(item.id)::INTEGER AS total_item_count
                FROM categories AS category
                LEFT JOIN items AS item
                  ON item.category_id = category.id
                 AND item.family_id = %s
                WHERE category.family_id = %s
                  AND category.deleted_at IS NULL
                GROUP BY category.id, category.name, category.sort_order
                ORDER BY category.sort_order, LOWER(category.name), category.id;
                """,
                (family_id, family_id),
            )
            return cur.fetchall()


def _category_name_exists(cur, family_id, name, exclude_id=None):
    params = [family_id, name]
    exclusion = ""
    if exclude_id is not None:
        exclusion = "AND id <> %s"
        params.append(exclude_id)

    cur.execute(
        f"""
        SELECT 1
        FROM categories
        WHERE family_id = %s
          AND deleted_at IS NULL
          AND LOWER(BTRIM(name)) = LOWER(BTRIM(%s))
          {exclusion}
        LIMIT 1;
        """,
        tuple(params),
    )
    return cur.fetchone() is not None


def create_category(user_id, family_id, name):
    clean_name = str(name or "").strip()
    if not clean_name:
        raise ValueError("Le nom de la catégorie est obligatoire.")

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            if _category_name_exists(cur, family_id, clean_name):
                raise ValueError(f"La catégorie « {clean_name} » existe déjà.")

            cur.execute(
                """
                INSERT INTO categories (family_id, name, sort_order)
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (
                    family_id,
                    clean_name,
                    next_sort_order(cur, "categories", family_id),
                ),
            )
            category_id = cur.fetchone()["id"]
            log_activity(
                cur,
                family_id,
                user_id,
                "category_created",
                "category",
                category_id,
                clean_name,
            )
            conn.commit()
            return category_id


def rename_category(user_id, family_id, category_id, new_name):
    clean_name = str(new_name or "").strip()
    if not clean_name:
        raise ValueError("Le nom de la catégorie est obligatoire.")

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT name
                FROM categories
                WHERE id = %s
                  AND family_id = %s
                  AND deleted_at IS NULL;
                """,
                (category_id, family_id),
            )
            current = cur.fetchone()
            if current is None:
                raise ValueError("Cette catégorie n’existe plus.")

            if _category_name_exists(
                cur,
                family_id,
                clean_name,
                exclude_id=category_id,
            ):
                raise ValueError(f"La catégorie « {clean_name} » existe déjà.")

            cur.execute(
                "UPDATE categories SET name = %s WHERE id = %s;",
                (clean_name, category_id),
            )
            log_activity(
                cur,
                family_id,
                user_id,
                "category_renamed",
                "category",
                category_id,
                clean_name,
                {"old_name": current["name"]},
            )
            conn.commit()


def move_category(user_id, family_id, category_id, direction):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT name
                FROM categories
                WHERE id = %s
                  AND family_id = %s
                  AND deleted_at IS NULL;
                """,
                (category_id, family_id),
            )
            category = cur.fetchone()
            if category is None:
                raise ValueError("Cette catégorie n’existe plus.")

            moved = move_ordered_entry(
                cur,
                "categories",
                family_id,
                category_id,
                direction,
            )
            if moved:
                log_activity(
                    cur,
                    family_id,
                    user_id,
                    "category_moved",
                    "category",
                    category_id,
                    category["name"],
                    {"direction": int(direction)},
                )
            conn.commit()
            return moved


def merge_categories(
    user_id,
    family_id,
    source_category_id,
    destination_category_id,
):
    if source_category_id == destination_category_id:
        raise ValueError("La catégorie de destination doit être différente.")

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT id, name
                FROM categories
                WHERE family_id = %s
                  AND deleted_at IS NULL
                  AND id IN (%s, %s);
                """,
                (family_id, source_category_id, destination_category_id),
            )
            rows = cur.fetchall()
            if len(rows) != 2:
                raise ValueError("Les deux catégories doivent être actives.")

            names = {row["id"]: row["name"] for row in rows}
            cur.execute(
                """
                UPDATE items
                SET category_id = %s
                WHERE family_id = %s
                  AND category_id = %s;
                """,
                (destination_category_id, family_id, source_category_id),
            )
            moved_count = cur.rowcount
            cur.execute(
                """
                UPDATE categories
                SET deleted_at = NOW(), deleted_by_user_id = %s
                WHERE id = %s;
                """,
                (user_id, source_category_id),
            )
            log_activity(
                cur,
                family_id,
                user_id,
                "category_merged",
                "category",
                source_category_id,
                names[source_category_id],
                {
                    "destination_name": names[destination_category_id],
                    "moved_items": moved_count,
                },
            )
            conn.commit()
            return moved_count


def delete_category(user_id, family_id, category_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT name
                FROM categories
                WHERE id = %s
                  AND family_id = %s
                  AND deleted_at IS NULL;
                """,
                (category_id, family_id),
            )
            category = cur.fetchone()
            if category is None:
                raise ValueError("Cette catégorie n’existe plus.")

            cur.execute(
                "SELECT COUNT(*)::INTEGER AS count FROM items WHERE category_id = %s;",
                (category_id,),
            )
            count = cur.fetchone()["count"]
            if count:
                raise ValueError(
                    f"Cette catégorie est encore liée à {count} item(s), "
                    "incluant la corbeille. Fusionnez-la d’abord."
                )

            cur.execute(
                """
                UPDATE categories
                SET deleted_at = NOW(), deleted_by_user_id = %s
                WHERE id = %s;
                """,
                (user_id, category_id),
            )
            log_activity(
                cur,
                family_id,
                user_id,
                "category_deleted",
                "category",
                category_id,
                category["name"],
            )
            conn.commit()


def get_deleted_categories(user_id, family_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT id, name, deleted_at
                FROM categories
                WHERE family_id = %s
                  AND deleted_at IS NOT NULL
                ORDER BY deleted_at DESC, LOWER(name);
                """,
                (family_id,),
            )
            return cur.fetchall()


def restore_category(user_id, family_id, category_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT name
                FROM categories
                WHERE id = %s
                  AND family_id = %s
                  AND deleted_at IS NOT NULL;
                """,
                (category_id, family_id),
            )
            category = cur.fetchone()
            if category is None:
                raise ValueError("Cette catégorie n’est plus dans la corbeille.")
            if _category_name_exists(cur, family_id, category["name"]):
                raise ValueError("Une catégorie active porte déjà ce nom.")

            cur.execute(
                """
                UPDATE categories
                SET deleted_at = NULL,
                    deleted_by_user_id = NULL,
                    sort_order = %s
                WHERE id = %s;
                """,
                (
                    next_sort_order(cur, "categories", family_id),
                    category_id,
                ),
            )
            log_activity(
                cur,
                family_id,
                user_id,
                "category_restored",
                "category",
                category_id,
                category["name"],
            )
            conn.commit()


def permanently_delete_category(user_id, family_id, category_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT name
                FROM categories
                WHERE id = %s
                  AND family_id = %s
                  AND deleted_at IS NOT NULL;
                """,
                (category_id, family_id),
            )
            category = cur.fetchone()
            if category is None:
                raise ValueError("Cette catégorie n’est plus dans la corbeille.")

            cur.execute(
                "SELECT COUNT(*)::INTEGER AS count FROM items WHERE category_id = %s;",
                (category_id,),
            )
            if cur.fetchone()["count"]:
                raise ValueError("Cette catégorie est encore liée à des items.")

            cur.execute("DELETE FROM categories WHERE id = %s;", (category_id,))
            log_activity(
                cur,
                family_id,
                user_id,
                "category_deleted_permanently",
                "category",
                category_id,
                category["name"],
            )
            conn.commit()


# ---------------------------------------------------------
# MAGASINS
# ---------------------------------------------------------


def get_stores(user_id, family_id):
    if family_id is None:
        return []

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT id, name, sort_order
                FROM stores
                WHERE family_id = %s
                  AND deleted_at IS NULL
                ORDER BY sort_order, LOWER(name), name, id;
                """,
                (family_id,),
            )
            return cur.fetchall()


def get_stores_with_counts(user_id, family_id):
    if family_id is None:
        return []

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT
                    store.id,
                    store.name,
                    store.sort_order,
                    COUNT(item.id) FILTER (
                        WHERE item.deleted_at IS NULL
                    )::INTEGER AS item_count,
                    COUNT(item.id) FILTER (
                        WHERE item.deleted_at IS NOT NULL
                    )::INTEGER AS deleted_item_count,
                    COUNT(item.id)::INTEGER AS total_item_count
                FROM stores AS store
                LEFT JOIN items AS item
                  ON item.store_id = store.id
                 AND item.family_id = %s
                WHERE store.family_id = %s
                  AND store.deleted_at IS NULL
                GROUP BY store.id, store.name, store.sort_order
                ORDER BY store.sort_order, LOWER(store.name), store.id;
                """,
                (family_id, family_id),
            )
            return cur.fetchall()


def _store_name_exists(cur, family_id, name, exclude_id=None):
    params = [family_id, name]
    exclusion = ""
    if exclude_id is not None:
        exclusion = "AND id <> %s"
        params.append(exclude_id)

    cur.execute(
        f"""
        SELECT 1
        FROM stores
        WHERE family_id = %s
          AND deleted_at IS NULL
          AND LOWER(BTRIM(name)) = LOWER(BTRIM(%s))
          {exclusion}
        LIMIT 1;
        """,
        tuple(params),
    )
    return cur.fetchone() is not None


def create_store(user_id, family_id, name):
    clean_name = str(name or "").strip()
    if not clean_name:
        raise ValueError("Le nom du magasin est obligatoire.")

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            if _store_name_exists(cur, family_id, clean_name):
                raise ValueError(f"Le magasin « {clean_name} » existe déjà.")

            cur.execute(
                """
                INSERT INTO stores (family_id, name, sort_order)
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (
                    family_id,
                    clean_name,
                    next_sort_order(cur, "stores", family_id),
                ),
            )
            store_id = cur.fetchone()["id"]
            log_activity(
                cur,
                family_id,
                user_id,
                "store_created",
                "store",
                store_id,
                clean_name,
            )
            conn.commit()
            return store_id


def rename_store(user_id, family_id, store_id, new_name):
    clean_name = str(new_name or "").strip()
    if not clean_name:
        raise ValueError("Le nom du magasin est obligatoire.")

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT name
                FROM stores
                WHERE id = %s
                  AND family_id = %s
                  AND deleted_at IS NULL;
                """,
                (store_id, family_id),
            )
            current = cur.fetchone()
            if current is None:
                raise ValueError("Ce magasin n’existe plus.")
            if _store_name_exists(cur, family_id, clean_name, store_id):
                raise ValueError(f"Le magasin « {clean_name} » existe déjà.")

            cur.execute(
                "UPDATE stores SET name = %s WHERE id = %s;",
                (clean_name, store_id),
            )
            log_activity(
                cur,
                family_id,
                user_id,
                "store_renamed",
                "store",
                store_id,
                clean_name,
                {"old_name": current["name"]},
            )
            conn.commit()


def move_store(user_id, family_id, store_id, direction):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT name
                FROM stores
                WHERE id = %s
                  AND family_id = %s
                  AND deleted_at IS NULL;
                """,
                (store_id, family_id),
            )
            store = cur.fetchone()
            if store is None:
                raise ValueError("Ce magasin n’existe plus.")

            moved = move_ordered_entry(
                cur,
                "stores",
                family_id,
                store_id,
                direction,
            )
            if moved:
                log_activity(
                    cur,
                    family_id,
                    user_id,
                    "store_moved",
                    "store",
                    store_id,
                    store["name"],
                    {"direction": int(direction)},
                )
            conn.commit()
            return moved


def delete_store(user_id, family_id, store_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT name
                FROM stores
                WHERE id = %s
                  AND family_id = %s
                  AND deleted_at IS NULL;
                """,
                (store_id, family_id),
            )
            store = cur.fetchone()
            if store is None:
                raise ValueError("Ce magasin n’existe plus.")

            cur.execute(
                "SELECT COUNT(*)::INTEGER AS count FROM items WHERE store_id = %s;",
                (store_id,),
            )
            count = cur.fetchone()["count"]
            if count:
                raise ValueError(
                    f"Ce magasin est encore lié à {count} item(s), "
                    "incluant la corbeille. Modifiez-les d’abord."
                )

            cur.execute(
                """
                UPDATE stores
                SET deleted_at = NOW(), deleted_by_user_id = %s
                WHERE id = %s;
                """,
                (user_id, store_id),
            )
            log_activity(
                cur,
                family_id,
                user_id,
                "store_deleted",
                "store",
                store_id,
                store["name"],
            )
            conn.commit()


def get_deleted_stores(user_id, family_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT id, name, deleted_at
                FROM stores
                WHERE family_id = %s
                  AND deleted_at IS NOT NULL
                ORDER BY deleted_at DESC, LOWER(name);
                """,
                (family_id,),
            )
            return cur.fetchall()


def restore_store(user_id, family_id, store_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT name
                FROM stores
                WHERE id = %s
                  AND family_id = %s
                  AND deleted_at IS NOT NULL;
                """,
                (store_id, family_id),
            )
            store = cur.fetchone()
            if store is None:
                raise ValueError("Ce magasin n’est plus dans la corbeille.")
            if _store_name_exists(cur, family_id, store["name"]):
                raise ValueError("Un magasin actif porte déjà ce nom.")

            cur.execute(
                """
                UPDATE stores
                SET deleted_at = NULL,
                    deleted_by_user_id = NULL,
                    sort_order = %s
                WHERE id = %s;
                """,
                (
                    next_sort_order(cur, "stores", family_id),
                    store_id,
                ),
            )
            log_activity(
                cur,
                family_id,
                user_id,
                "store_restored",
                "store",
                store_id,
                store["name"],
            )
            conn.commit()


def permanently_delete_store(user_id, family_id, store_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT name
                FROM stores
                WHERE id = %s
                  AND family_id = %s
                  AND deleted_at IS NOT NULL;
                """,
                (store_id, family_id),
            )
            store = cur.fetchone()
            if store is None:
                raise ValueError("Ce magasin n’est plus dans la corbeille.")

            cur.execute(
                "SELECT COUNT(*)::INTEGER AS count FROM items WHERE store_id = %s;",
                (store_id,),
            )
            if cur.fetchone()["count"]:
                raise ValueError("Ce magasin est encore lié à des items.")

            cur.execute("DELETE FROM stores WHERE id = %s;", (store_id,))
            log_activity(
                cur,
                family_id,
                user_id,
                "store_deleted_permanently",
                "store",
                store_id,
                store["name"],
            )
            conn.commit()
