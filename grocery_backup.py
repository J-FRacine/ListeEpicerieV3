import db as _db

from grocery_common import log_activity


def export_family_backup(user_id, family_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                "SELECT id, name FROM families WHERE id = %s;",
                (family_id,),
            )
            family = cur.fetchone()
            if family is None:
                raise ValueError("Cette famille n’existe plus.")

            cur.execute(
                """
                SELECT name, sort_order
                FROM categories
                WHERE family_id = %s
                  AND deleted_at IS NULL
                ORDER BY sort_order, LOWER(name), id;
                """,
                (family_id,),
            )
            categories = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT name, sort_order
                FROM stores
                WHERE family_id = %s
                  AND deleted_at IS NULL
                ORDER BY sort_order, LOWER(name), id;
                """,
                (family_id,),
            )
            stores = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT
                    item.name,
                    item.note,
                    item.quantity,
                    item.needed,
                    item.times_needed,
                    item.last_needed_at,
                    category.name AS category,
                    COALESCE(store.name, 'Épicerie') AS store
                FROM items AS item
                JOIN categories AS category
                  ON category.id = item.category_id
                 AND category.deleted_at IS NULL
                LEFT JOIN stores AS store
                  ON store.id = item.store_id
                WHERE item.family_id = %s
                  AND item.deleted_at IS NULL
                ORDER BY
                    COALESCE(store.sort_order, 999999),
                    category.sort_order,
                    LOWER(item.name),
                    item.id;
                """,
                (family_id,),
            )
            items = []
            for row in cur.fetchall():
                items.append(
                    {
                        "name": row["name"],
                        "note": row["note"],
                        "quantity": row["quantity"],
                        "needed": bool(row["needed"]),
                        "times_needed": row["times_needed"],
                        "last_needed_at": (
                            row["last_needed_at"].isoformat()
                            if row["last_needed_at"]
                            else None
                        ),
                        "category": row["category"],
                        "store": row["store"],
                    }
                )

            return {
                "family": {"name": family["name"]},
                "categories": categories,
                "stores": stores,
                "items": items,
            }


def _named_ordered_entry(entry, entry_type):
    if isinstance(entry, str):
        name = entry
        sort_order = 0
    elif isinstance(entry, dict):
        name = entry.get("name")
        sort_order = entry.get("sort_order", 0)
    else:
        raise ValueError(f"Le fichier contient un {entry_type} invalide.")

    clean_name = str(name or "").strip()
    if not clean_name:
        raise ValueError(f"Le fichier contient un {entry_type} sans nom.")

    try:
        clean_order = int(sort_order or 0)
    except (TypeError, ValueError):
        clean_order = 0

    return clean_name, clean_order


def _item_values(item):
    if not isinstance(item, dict):
        raise ValueError("Le fichier contient un item invalide.")

    name = str(item.get("name") or "").strip()
    note = str(item.get("note") or "").strip()
    category = str(item.get("category") or "Sans catégorie").strip()
    store = str(item.get("store") or "Épicerie").strip()

    if not name:
        raise ValueError("Le fichier contient un item sans nom.")

    try:
        quantity = int(item.get("quantity", 1) or 1)
    except (TypeError, ValueError) as error:
        raise ValueError(f"La quantité de « {name} » est invalide.") from error

    if quantity < 1:
        raise ValueError(f"La quantité de « {name} » doit être d’au moins 1.")

    raw_needed = item.get("needed", False)
    if isinstance(raw_needed, str):
        needed = raw_needed.strip().lower() in {
            "1",
            "true",
            "vrai",
            "yes",
            "oui",
        }
    else:
        needed = bool(raw_needed)

    try:
        times_needed = max(
            0,
            int(
                item.get(
                    "times_needed",
                    1 if needed else 0,
                )
                or 0
            ),
        )
    except (TypeError, ValueError):
        times_needed = 1 if needed else 0

    last_needed_at = item.get("last_needed_at")
    if last_needed_at is not None:
        last_needed_at = str(last_needed_at).strip() or None

    return {
        "name": name,
        "note": note,
        "category": category or "Sans catégorie",
        "store": store or "Épicerie",
        "quantity": quantity,
        "needed": needed,
        "times_needed": times_needed,
        "last_needed_at": last_needed_at,
    }


def import_family_backup(
    user_id,
    family_id,
    backup_data,
    replace_existing=False,
):
    if not isinstance(backup_data, dict):
        raise ValueError("Le contenu de la sauvegarde est invalide.")

    categories_data = backup_data.get("categories", [])
    stores_data = backup_data.get("stores", [])
    items_data = backup_data.get("items", [])

    if not isinstance(categories_data, list):
        raise ValueError("La liste des catégories est invalide.")
    if not isinstance(stores_data, list):
        raise ValueError("La liste des magasins est invalide.")
    if not isinstance(items_data, list):
        raise ValueError("La liste des items est invalide.")

    categories = [
        _named_ordered_entry(entry, "catégorie")
        for entry in categories_data
    ]
    stores = [
        _named_ordered_entry(entry, "magasin")
        for entry in stores_data
    ]
    items = [_item_values(item) for item in items_data]

    # Compatibilité avec les sauvegardes version 1.
    if not stores:
        stores = [("Épicerie", 10)]

    category_names = {name.casefold() for name, _ in categories}
    store_names = {name.casefold() for name, _ in stores}

    for item in items:
        category_key = item["category"].casefold()
        store_key = item["store"].casefold()
        if category_key not in category_names:
            categories.append((item["category"], 0))
            category_names.add(category_key)
        if store_key not in store_names:
            stores.append((item["store"], 0))
            store_names.add(store_key)

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)

            if replace_existing:
                cur.execute(
                    "DELETE FROM items WHERE family_id = %s;",
                    (family_id,),
                )
                cur.execute(
                    "DELETE FROM categories WHERE family_id = %s;",
                    (family_id,),
                )
                cur.execute(
                    "DELETE FROM stores WHERE family_id = %s;",
                    (family_id,),
                )

            cur.execute(
                """
                SELECT id, name
                FROM categories
                WHERE family_id = %s
                  AND deleted_at IS NULL;
                """,
                (family_id,),
            )
            category_ids = {
                row["name"].strip().casefold(): row["id"]
                for row in cur.fetchall()
            }

            cur.execute(
                """
                SELECT id, name
                FROM stores
                WHERE family_id = %s
                  AND deleted_at IS NULL;
                """,
                (family_id,),
            )
            store_ids = {
                row["name"].strip().casefold(): row["id"]
                for row in cur.fetchall()
            }

            categories_created = 0
            for position, (name, requested_order) in enumerate(
                categories,
                start=1,
            ):
                key = name.casefold()
                if key in category_ids:
                    continue
                cur.execute(
                    """
                    INSERT INTO categories (family_id, name, sort_order)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        family_id,
                        name,
                        requested_order or position * 10,
                    ),
                )
                category_ids[key] = cur.fetchone()["id"]
                categories_created += 1

            stores_created = 0
            for position, (name, requested_order) in enumerate(
                stores,
                start=1,
            ):
                key = name.casefold()
                if key in store_ids:
                    continue
                cur.execute(
                    """
                    INSERT INTO stores (family_id, name, sort_order)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        family_id,
                        name,
                        requested_order or position * 10,
                    ),
                )
                store_ids[key] = cur.fetchone()["id"]
                stores_created += 1

            existing = {}
            if not replace_existing:
                cur.execute(
                    """
                    SELECT id, name, category_id, store_id
                    FROM items
                    WHERE family_id = %s
                      AND deleted_at IS NULL
                    ORDER BY id;
                    """,
                    (family_id,),
                )
                for row in cur.fetchall():
                    key = (
                        row["category_id"],
                        row["store_id"],
                        row["name"].strip().casefold(),
                    )
                    existing.setdefault(key, row["id"])

            items_created = 0
            items_updated = 0

            for item in items:
                category_id = category_ids[item["category"].casefold()]
                store_id = store_ids[item["store"].casefold()]
                key = (
                    category_id,
                    store_id,
                    item["name"].casefold(),
                )
                needed = 1 if item["needed"] else 0

                if key in existing:
                    cur.execute(
                        """
                        UPDATE items
                        SET note = %s,
                            quantity = %s,
                            needed = %s,
                            times_needed = GREATEST(times_needed, %s),
                            last_needed_at = COALESCE(
                                %s::timestamptz,
                                last_needed_at
                            )
                        WHERE id = %s;
                        """,
                        (
                            item["note"],
                            item["quantity"],
                            needed,
                            item["times_needed"],
                            item["last_needed_at"],
                            existing[key],
                        ),
                    )
                    items_updated += 1
                else:
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
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s::timestamptz
                        );
                        """,
                        (
                            family_id,
                            category_id,
                            store_id,
                            item["name"],
                            item["note"],
                            item["quantity"],
                            needed,
                            item["times_needed"],
                            item["last_needed_at"],
                        ),
                    )
                    items_created += 1

            log_activity(
                cur,
                family_id,
                user_id,
                "backup_imported",
                "backup",
                None,
                "Sauvegarde",
                {
                    "replace_existing": bool(replace_existing),
                    "categories_created": categories_created,
                    "stores_created": stores_created,
                    "items_created": items_created,
                    "items_updated": items_updated,
                },
            )
            conn.commit()
            return {
                "categories_created": categories_created,
                "stores_created": stores_created,
                "items_created": items_created,
                "items_updated": items_updated,
            }
