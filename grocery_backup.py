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

            cur.execute(
                """
                SELECT id, name, description
                FROM grocery_templates
                WHERE family_id = %s
                ORDER BY LOWER(name), id;
                """,
                (family_id,),
            )
            templates = []
            for template in cur.fetchall():
                cur.execute(
                    """
                    SELECT
                        item.name,
                        category.name AS category,
                        COALESCE(store.name, 'Épicerie') AS store,
                        line.quantity,
                        line.sort_order
                    FROM grocery_template_items AS line
                    JOIN items AS item
                      ON item.id = line.item_id
                     AND item.deleted_at IS NULL
                    JOIN categories AS category
                      ON category.id = item.category_id
                    LEFT JOIN stores AS store
                      ON store.id = item.store_id
                    WHERE line.template_id = %s
                    ORDER BY line.sort_order, line.id;
                    """,
                    (template["id"],),
                )
                template_items = [dict(row) for row in cur.fetchall()]
                templates.append(
                    {
                        "name": template["name"],
                        "description": template["description"],
                        "items": template_items,
                    }
                )

            cur.execute(
                """
                SELECT
                    id,
                    name,
                    description,
                    instructions,
                    servings
                FROM grocery_recipes
                WHERE family_id = %s
                ORDER BY LOWER(name), id;
                """,
                (family_id,),
            )
            recipes = []
            for recipe in cur.fetchall():
                cur.execute(
                    """
                    SELECT
                        item.name,
                        category.name AS category,
                        COALESCE(store.name, 'Épicerie') AS store,
                        ingredient.quantity,
                        ingredient.note,
                        ingredient.sort_order
                    FROM grocery_recipe_ingredients AS ingredient
                    JOIN items AS item
                      ON item.id = ingredient.item_id
                     AND item.deleted_at IS NULL
                    JOIN categories AS category
                      ON category.id = item.category_id
                    LEFT JOIN stores AS store
                      ON store.id = item.store_id
                    WHERE ingredient.recipe_id = %s
                    ORDER BY ingredient.sort_order, ingredient.id;
                    """,
                    (recipe["id"],),
                )
                ingredients = [dict(row) for row in cur.fetchall()]
                recipes.append(
                    {
                        "name": recipe["name"],
                        "description": recipe["description"],
                        "instructions": recipe["instructions"],
                        "servings": recipe["servings"],
                        "ingredients": ingredients,
                    }
                )

            return {
                "family": {"name": family["name"]},
                "categories": categories,
                "stores": stores,
                "items": items,
                "templates": templates,
                "recipes": recipes,
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


def _line_item_reference(entry, label):
    if not isinstance(entry, dict):
        raise ValueError(f"Le fichier contient un {label} invalide.")

    name = str(entry.get("name") or "").strip()
    category = str(entry.get("category") or "Sans catégorie").strip()
    store = str(entry.get("store") or "Épicerie").strip()

    if not name:
        raise ValueError(f"Le fichier contient un {label} sans nom d’item.")

    try:
        quantity = int(entry.get("quantity", 1) or 1)
    except (TypeError, ValueError) as error:
        raise ValueError(f"La quantité de « {name} » est invalide.") from error

    if quantity < 1:
        raise ValueError(f"La quantité de « {name} » doit être d’au moins 1.")

    try:
        sort_order = int(entry.get("sort_order", 0) or 0)
    except (TypeError, ValueError):
        sort_order = 0

    return {
        "name": name,
        "category": category or "Sans catégorie",
        "store": store or "Épicerie",
        "quantity": quantity,
        "sort_order": sort_order,
        "note": str(entry.get("note") or "").strip(),
    }


def _template_values(template):
    if not isinstance(template, dict):
        raise ValueError("Le fichier contient une liste modèle invalide.")

    name = str(template.get("name") or "").strip()
    if not name:
        raise ValueError("Le fichier contient une liste modèle sans nom.")

    raw_items = template.get("items", [])
    if not isinstance(raw_items, list):
        raise ValueError(f"Les items de la liste modèle « {name} » sont invalides.")

    return {
        "name": name,
        "description": str(template.get("description") or "").strip(),
        "items": [
            _line_item_reference(entry, "item de liste modèle")
            for entry in raw_items
        ],
    }


def _recipe_values(recipe):
    if not isinstance(recipe, dict):
        raise ValueError("Le fichier contient une recette invalide.")

    name = str(recipe.get("name") or "").strip()
    if not name:
        raise ValueError("Le fichier contient une recette sans nom.")

    try:
        servings = int(recipe.get("servings", 4) or 4)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Le nombre de portions de « {name} » est invalide.") from error

    if servings < 1:
        raise ValueError(f"Le nombre de portions de « {name} » est invalide.")

    raw_ingredients = recipe.get("ingredients", [])
    if not isinstance(raw_ingredients, list):
        raise ValueError(f"Les ingrédients de la recette « {name} » sont invalides.")

    return {
        "name": name,
        "description": str(recipe.get("description") or "").strip(),
        "instructions": str(recipe.get("instructions") or "").strip(),
        "servings": servings,
        "ingredients": [
            _line_item_reference(entry, "ingrédient")
            for entry in raw_ingredients
        ],
    }


def _ensure_unique_names(entries, label):
    seen = set()
    for entry in entries:
        key = entry["name"].casefold()
        if key in seen:
            raise ValueError(
                f"Le fichier contient plusieurs {label} nommés « {entry['name']} »."
            )
        seen.add(key)


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
    templates_data = backup_data.get("templates", [])
    recipes_data = backup_data.get("recipes", [])

    if not isinstance(categories_data, list):
        raise ValueError("La liste des catégories est invalide.")
    if not isinstance(stores_data, list):
        raise ValueError("La liste des magasins est invalide.")
    if not isinstance(items_data, list):
        raise ValueError("La liste des items est invalide.")
    if not isinstance(templates_data, list):
        raise ValueError("La liste des listes modèles est invalide.")
    if not isinstance(recipes_data, list):
        raise ValueError("La liste des recettes est invalide.")

    categories = [
        _named_ordered_entry(entry, "catégorie")
        for entry in categories_data
    ]
    stores = [
        _named_ordered_entry(entry, "magasin")
        for entry in stores_data
    ]
    items = [_item_values(item) for item in items_data]
    templates = [_template_values(entry) for entry in templates_data]
    recipes = [_recipe_values(entry) for entry in recipes_data]

    _ensure_unique_names(templates, "listes modèles")
    _ensure_unique_names(recipes, "recettes")

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
                    "DELETE FROM grocery_templates WHERE family_id = %s;",
                    (family_id,),
                )
                cur.execute(
                    "DELETE FROM grocery_recipes WHERE family_id = %s;",
                    (family_id,),
                )
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
                        )
                        RETURNING id;
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
                    existing[key] = cur.fetchone()["id"]
                    items_created += 1

            # Recharge un dictionnaire stable pour les listes modèles et recettes.
            cur.execute(
                """
                SELECT
                    item.id,
                    item.name,
                    category.name AS category,
                    COALESCE(store.name, 'Épicerie') AS store
                FROM items AS item
                JOIN categories AS category
                  ON category.id = item.category_id
                LEFT JOIN stores AS store
                  ON store.id = item.store_id
                WHERE item.family_id = %s
                  AND item.deleted_at IS NULL
                ORDER BY item.id;
                """,
                (family_id,),
            )
            item_ids = {}
            for row in cur.fetchall():
                key = (
                    row["store"].strip().casefold(),
                    row["category"].strip().casefold(),
                    row["name"].strip().casefold(),
                )
                item_ids.setdefault(key, row["id"])

            templates_created = 0
            templates_updated = 0
            template_lines_skipped = 0

            cur.execute(
                """
                SELECT id, name
                FROM grocery_templates
                WHERE family_id = %s;
                """,
                (family_id,),
            )
            template_ids = {
                row["name"].strip().casefold(): row["id"]
                for row in cur.fetchall()
            }

            for template in templates:
                template_key = template["name"].casefold()
                template_id = template_ids.get(template_key)

                if template_id is None:
                    cur.execute(
                        """
                        INSERT INTO grocery_templates (
                            family_id,
                            name,
                            description,
                            created_by_user_id
                        )
                        VALUES (%s, %s, %s, %s)
                        RETURNING id;
                        """,
                        (
                            family_id,
                            template["name"],
                            template["description"],
                            user_id,
                        ),
                    )
                    template_id = cur.fetchone()["id"]
                    template_ids[template_key] = template_id
                    templates_created += 1
                else:
                    cur.execute(
                        """
                        UPDATE grocery_templates
                        SET description = %s,
                            updated_at = NOW()
                        WHERE id = %s;
                        """,
                        (template["description"], template_id),
                    )
                    templates_updated += 1

                cur.execute(
                    "DELETE FROM grocery_template_items WHERE template_id = %s;",
                    (template_id,),
                )

                for position, line in enumerate(template["items"], start=1):
                    item_key = (
                        line["store"].casefold(),
                        line["category"].casefold(),
                        line["name"].casefold(),
                    )
                    item_id = item_ids.get(item_key)
                    if item_id is None:
                        template_lines_skipped += 1
                        continue

                    cur.execute(
                        """
                        INSERT INTO grocery_template_items (
                            template_id,
                            item_id,
                            quantity,
                            sort_order
                        )
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (template_id, item_id)
                        DO UPDATE SET
                            quantity = EXCLUDED.quantity,
                            sort_order = EXCLUDED.sort_order;
                        """,
                        (
                            template_id,
                            item_id,
                            line["quantity"],
                            line["sort_order"] or position * 10,
                        ),
                    )

            recipes_created = 0
            recipes_updated = 0
            recipe_lines_skipped = 0

            cur.execute(
                """
                SELECT id, name
                FROM grocery_recipes
                WHERE family_id = %s;
                """,
                (family_id,),
            )
            recipe_ids = {
                row["name"].strip().casefold(): row["id"]
                for row in cur.fetchall()
            }

            for recipe in recipes:
                recipe_key = recipe["name"].casefold()
                recipe_id = recipe_ids.get(recipe_key)

                if recipe_id is None:
                    cur.execute(
                        """
                        INSERT INTO grocery_recipes (
                            family_id,
                            name,
                            description,
                            instructions,
                            servings,
                            created_by_user_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id;
                        """,
                        (
                            family_id,
                            recipe["name"],
                            recipe["description"],
                            recipe["instructions"],
                            recipe["servings"],
                            user_id,
                        ),
                    )
                    recipe_id = cur.fetchone()["id"]
                    recipe_ids[recipe_key] = recipe_id
                    recipes_created += 1
                else:
                    cur.execute(
                        """
                        UPDATE grocery_recipes
                        SET description = %s,
                            instructions = %s,
                            servings = %s,
                            updated_at = NOW()
                        WHERE id = %s;
                        """,
                        (
                            recipe["description"],
                            recipe["instructions"],
                            recipe["servings"],
                            recipe_id,
                        ),
                    )
                    recipes_updated += 1

                cur.execute(
                    """
                    DELETE FROM grocery_recipe_ingredients
                    WHERE recipe_id = %s;
                    """,
                    (recipe_id,),
                )

                for position, ingredient in enumerate(
                    recipe["ingredients"],
                    start=1,
                ):
                    item_key = (
                        ingredient["store"].casefold(),
                        ingredient["category"].casefold(),
                        ingredient["name"].casefold(),
                    )
                    item_id = item_ids.get(item_key)
                    if item_id is None:
                        recipe_lines_skipped += 1
                        continue

                    cur.execute(
                        """
                        INSERT INTO grocery_recipe_ingredients (
                            recipe_id,
                            item_id,
                            quantity,
                            note,
                            sort_order
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (recipe_id, item_id)
                        DO UPDATE SET
                            quantity = EXCLUDED.quantity,
                            note = EXCLUDED.note,
                            sort_order = EXCLUDED.sort_order;
                        """,
                        (
                            recipe_id,
                            item_id,
                            ingredient["quantity"],
                            ingredient["note"],
                            ingredient["sort_order"] or position * 10,
                        ),
                    )

            result = {
                "categories_created": categories_created,
                "stores_created": stores_created,
                "items_created": items_created,
                "items_updated": items_updated,
                "templates_created": templates_created,
                "templates_updated": templates_updated,
                "recipes_created": recipes_created,
                "recipes_updated": recipes_updated,
                "template_lines_skipped": template_lines_skipped,
                "recipe_lines_skipped": recipe_lines_skipped,
            }

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
                    **result,
                },
            )
            conn.commit()
            return result
