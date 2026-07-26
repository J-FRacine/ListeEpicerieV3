import db as _db

from grocery_common import log_activity


CONTENT_TYPES = {"template", "recipe"}


def _clean_text(value):
    return str(value or "").strip()


def _positive_int(value, label="La quantité"):
    raw_value = 1 if value is None or value == "" else value
    try:
        number = int(raw_value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} est invalide.") from error
    if number < 1:
        raise ValueError(f"{label} doit être d’au moins 1.")
    return number


def _source_column(content_type):
    if content_type == "template":
        return "source_template_id"
    if content_type == "recipe":
        return "source_recipe_id"
    raise ValueError("Type de contenu partagé invalide.")


def _source_label(content_type):
    return "liste modèle" if content_type == "template" else "recette"


def _load_source(cur, user_id, content_type, source_id):
    if content_type == "template":
        cur.execute(
            """
            SELECT
                id,
                family_id,
                name,
                description,
                ''::TEXT AS instructions,
                NULL::INTEGER AS servings,
                updated_at
            FROM grocery_templates
            WHERE id = %s;
            """,
            (source_id,),
        )
    elif content_type == "recipe":
        cur.execute(
            """
            SELECT
                id,
                family_id,
                name,
                description,
                instructions,
                servings,
                updated_at
            FROM grocery_recipes
            WHERE id = %s;
            """,
            (source_id,),
        )
    else:
        raise ValueError("Type de contenu partagé invalide.")

    source = cur.fetchone()
    if source is None:
        raise ValueError(
            f"Cette {_source_label(content_type)} n’existe plus."
        )

    _db._require_family_access(
        cur,
        user_id,
        source["family_id"],
    )
    return source


def _load_source_lines(cur, content_type, source_id, family_id):
    if content_type == "template":
        cur.execute(
            """
            SELECT
                item.name AS item_name,
                line.quantity,
                ''::TEXT AS note,
                category.name AS category_name,
                line.sort_order
            FROM grocery_template_items AS line
            JOIN items AS item
              ON item.id = line.item_id
             AND item.family_id = %s
             AND item.deleted_at IS NULL
            JOIN categories AS category
              ON category.id = item.category_id
             AND category.deleted_at IS NULL
            WHERE line.template_id = %s
            ORDER BY line.sort_order, line.id;
            """,
            (family_id, source_id),
        )
    else:
        cur.execute(
            """
            SELECT
                item.name AS item_name,
                ingredient.quantity,
                ingredient.note,
                category.name AS category_name,
                ingredient.sort_order
            FROM grocery_recipe_ingredients AS ingredient
            JOIN items AS item
              ON item.id = ingredient.item_id
             AND item.family_id = %s
             AND item.deleted_at IS NULL
            JOIN categories AS category
              ON category.id = item.category_id
             AND category.deleted_at IS NULL
            WHERE ingredient.recipe_id = %s
            ORDER BY ingredient.sort_order, ingredient.id;
            """,
            (family_id, source_id),
        )

    return cur.fetchall()


def _existing_publication(cur, content_type, source_id):
    source_column = _source_column(content_type)
    cur.execute(
        f"""
        SELECT id
        FROM shared_grocery_content
        WHERE {source_column} = %s;
        """,
        (source_id,),
    )
    return cur.fetchone()


def _publish_source(
    cur,
    *,
    user_id,
    content_type,
    source_id,
    require_existing=False,
):
    source = _load_source(
        cur,
        user_id,
        content_type,
        source_id,
    )
    lines = _load_source_lines(
        cur,
        content_type,
        source_id,
        source["family_id"],
    )

    if not lines:
        noun = "La liste modèle" if content_type == "template" else "La recette"
        raise ValueError(
            f"{noun} doit contenir au moins un élément actif avant d’être publiée."
        )

    existing = _existing_publication(
        cur,
        content_type,
        source_id,
    )

    if require_existing and existing is None:
        raise ValueError(
            f"Cette {_source_label(content_type)} n’est pas publiée."
        )

    if existing is None:
        cur.execute(
            """
            INSERT INTO shared_grocery_content (
                content_type,
                source_family_id,
                source_template_id,
                source_recipe_id,
                name,
                description,
                instructions,
                servings,
                published_by_user_id,
                source_updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id;
            """,
            (
                content_type,
                source["family_id"],
                source_id if content_type == "template" else None,
                source_id if content_type == "recipe" else None,
                source["name"],
                source["description"],
                source["instructions"],
                source["servings"],
                user_id,
                source["updated_at"],
            ),
        )
        public_id = cur.fetchone()["id"]
    else:
        public_id = existing["id"]
        cur.execute(
            """
            UPDATE shared_grocery_content
            SET
                name = %s,
                description = %s,
                instructions = %s,
                servings = %s,
                source_updated_at = %s,
                updated_at = NOW()
            WHERE id = %s;
            """,
            (
                source["name"],
                source["description"],
                source["instructions"],
                source["servings"],
                source["updated_at"],
                public_id,
            ),
        )
        cur.execute(
            """
            DELETE FROM shared_grocery_content_lines
            WHERE content_id = %s;
            """,
            (public_id,),
        )

    for position, line in enumerate(lines, start=1):
        cur.execute(
            """
            INSERT INTO shared_grocery_content_lines (
                content_id,
                item_name,
                quantity,
                note,
                category_name,
                sort_order
            )
            VALUES (%s, %s, %s, %s, %s, %s);
            """,
            (
                public_id,
                _clean_text(line["item_name"]),
                _positive_int(line["quantity"]),
                _clean_text(line["note"]),
                _clean_text(line["category_name"]),
                position * 10,
            ),
        )

    return source, public_id, existing is not None


def _set_source_public(user_id, content_type, source_id, is_public):
    desired_state = bool(is_public)

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            source = _load_source(
                cur,
                user_id,
                content_type,
                source_id,
            )
            existing = _existing_publication(
                cur,
                content_type,
                source_id,
            )

            if desired_state:
                source, _, was_existing = _publish_source(
                    cur,
                    user_id=user_id,
                    content_type=content_type,
                    source_id=source_id,
                )
                action = (
                    f"{content_type}_public_updated"
                    if was_existing
                    else f"{content_type}_published"
                )
            else:
                if existing is None:
                    return False
                cur.execute(
                    """
                    DELETE FROM shared_grocery_content
                    WHERE id = %s;
                    """,
                    (existing["id"],),
                )
                action = f"{content_type}_unpublished"

            log_activity(
                cur,
                source["family_id"],
                user_id,
                action,
                content_type,
                source_id,
                source["name"],
            )
            conn.commit()
            return True


def set_template_public(user_id, template_id, is_public):
    return _set_source_public(
        user_id,
        "template",
        template_id,
        is_public,
    )


def set_recipe_public(user_id, recipe_id, is_public):
    return _set_source_public(
        user_id,
        "recipe",
        recipe_id,
        is_public,
    )


def refresh_public_template(user_id, template_id):
    return _refresh_public_source(
        user_id,
        "template",
        template_id,
    )


def refresh_public_recipe(user_id, recipe_id):
    return _refresh_public_source(
        user_id,
        "recipe",
        recipe_id,
    )


def _refresh_public_source(user_id, content_type, source_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            source, _, _ = _publish_source(
                cur,
                user_id=user_id,
                content_type=content_type,
                source_id=source_id,
                require_existing=True,
            )
            log_activity(
                cur,
                source["family_id"],
                user_id,
                f"{content_type}_public_updated",
                content_type,
                source_id,
                source["name"],
            )
            conn.commit()
            return True


def get_shared_library(user_id, content_type=None, search_text=""):
    clean_type = _clean_text(content_type).lower()
    clean_search = _clean_text(search_text)

    if clean_type and clean_type not in CONTENT_TYPES:
        raise ValueError("Filtre de bibliothèque invalide.")

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._get_active_user(cur, user_id)

            where_parts = []
            params = []

            if clean_type:
                where_parts.append("content.content_type = %s")
                params.append(clean_type)

            if clean_search:
                where_parts.append(
                    """
                    (
                        content.name ILIKE %s
                        OR content.description ILIKE %s
                        OR EXISTS (
                            SELECT 1
                            FROM shared_grocery_content_lines AS line_search
                            WHERE line_search.content_id = content.id
                              AND (
                                  line_search.item_name ILIKE %s
                                  OR line_search.category_name ILIKE %s
                              )
                        )
                    )
                    """
                )
                pattern = f"%{clean_search}%"
                params.extend([pattern, pattern, pattern, pattern])

            where_sql = (
                "WHERE " + " AND ".join(where_parts)
                if where_parts
                else ""
            )

            cur.execute(
                f"""
                SELECT
                    content.id,
                    content.content_type,
                    content.name,
                    content.description,
                    content.instructions,
                    content.servings,
                    content.published_at,
                    content.updated_at,
                    COUNT(line.id)::INTEGER AS line_count
                FROM shared_grocery_content AS content
                LEFT JOIN shared_grocery_content_lines AS line
                  ON line.content_id = content.id
                {where_sql}
                GROUP BY content.id
                ORDER BY
                    content.updated_at DESC,
                    LOWER(content.name),
                    content.name,
                    content.id;
                """,
                tuple(params),
            )
            return cur.fetchall()


def get_shared_content(user_id, content_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._get_active_user(cur, user_id)
            cur.execute(
                """
                SELECT
                    id,
                    content_type,
                    name,
                    description,
                    instructions,
                    servings,
                    published_at,
                    updated_at
                FROM shared_grocery_content
                WHERE id = %s;
                """,
                (content_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError(
                    "Ce contenu n’est plus disponible dans la bibliothèque."
                )

            content = dict(row)
            cur.execute(
                """
                SELECT
                    id,
                    item_name,
                    quantity,
                    note,
                    category_name,
                    sort_order
                FROM shared_grocery_content_lines
                WHERE content_id = %s
                ORDER BY sort_order, id;
                """,
                (content_id,),
            )
            content["lines"] = cur.fetchall()
            return content


def _next_private_name(cur, content_type, family_id, public_name):
    table = (
        "grocery_templates"
        if content_type == "template"
        else "grocery_recipes"
    )
    base_name = _clean_text(public_name)
    candidate = base_name
    copy_number = 1

    while True:
        cur.execute(
            f"""
            SELECT 1
            FROM {table}
            WHERE family_id = %s
              AND LOWER(BTRIM(name)) = LOWER(BTRIM(%s))
            LIMIT 1;
            """,
            (family_id, candidate),
        )
        if cur.fetchone() is None:
            return candidate

        candidate = (
            f"{base_name} (copie)"
            if copy_number == 1
            else f"{base_name} (copie {copy_number})"
        )
        copy_number += 1


def _ensure_default_store(cur, family_id):
    cur.execute(
        """
        SELECT id
        FROM stores
        WHERE family_id = %s
          AND deleted_at IS NULL
        ORDER BY sort_order, LOWER(name), name, id
        LIMIT 1;
        """,
        (family_id,),
    )
    row = cur.fetchone()
    if row is not None:
        return row["id"]

    cur.execute(
        """
        INSERT INTO stores (family_id, name, sort_order)
        VALUES (%s, 'Épicerie', 10)
        RETURNING id;
        """,
        (family_id,),
    )
    return cur.fetchone()["id"]


def _ensure_category(cur, family_id, category_name):
    clean_name = _clean_text(category_name) or "À classer"
    cur.execute(
        """
        SELECT id
        FROM categories
        WHERE family_id = %s
          AND deleted_at IS NULL
          AND LOWER(BTRIM(name)) = LOWER(BTRIM(%s))
        ORDER BY id
        LIMIT 1;
        """,
        (family_id, clean_name),
    )
    row = cur.fetchone()
    if row is not None:
        return row["id"]

    cur.execute(
        """
        SELECT COALESCE(MAX(sort_order), 0) + 10 AS next_order
        FROM categories
        WHERE family_id = %s
          AND deleted_at IS NULL;
        """,
        (family_id,),
    )
    next_order = cur.fetchone()["next_order"]
    cur.execute(
        """
        INSERT INTO categories (family_id, name, sort_order)
        VALUES (%s, %s, %s)
        RETURNING id;
        """,
        (family_id, clean_name, next_order),
    )
    return cur.fetchone()["id"]


def _find_or_create_item(
    cur,
    *,
    family_id,
    item_name,
    category_name,
    default_store_id,
):
    clean_item_name = _clean_text(item_name)
    if not clean_item_name:
        raise ValueError("Un item public ne possède pas de nom valide.")

    clean_category = _clean_text(category_name)
    cur.execute(
        """
        SELECT
            item.id,
            category.name AS category_name
        FROM items AS item
        JOIN categories AS category
          ON category.id = item.category_id
        WHERE item.family_id = %s
          AND item.deleted_at IS NULL
          AND LOWER(BTRIM(item.name)) = LOWER(BTRIM(%s))
        ORDER BY
            CASE
                WHEN LOWER(BTRIM(category.name)) = LOWER(BTRIM(%s))
                    THEN 0
                ELSE 1
            END,
            item.id;
        """,
        (family_id, clean_item_name, clean_category),
    )
    matches = cur.fetchall()

    if matches:
        return matches[0]["id"], False, len(matches) > 1

    category_id = _ensure_category(
        cur,
        family_id,
        clean_category,
    )
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
        VALUES (%s, %s, %s, %s, '', 1, 0, 0, NULL)
        RETURNING id;
        """,
        (
            family_id,
            category_id,
            default_store_id,
            clean_item_name,
        ),
    )
    return cur.fetchone()["id"], True, False


def copy_shared_content_to_family(user_id, content_id, family_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(
                cur,
                user_id,
                family_id,
            )
            cur.execute(
                """
                SELECT
                    id,
                    content_type,
                    name,
                    description,
                    instructions,
                    servings
                FROM shared_grocery_content
                WHERE id = %s;
                """,
                (content_id,),
            )
            public = cur.fetchone()
            if public is None:
                raise ValueError(
                    "Ce contenu n’est plus disponible dans la bibliothèque."
                )

            cur.execute(
                """
                SELECT
                    item_name,
                    quantity,
                    note,
                    category_name,
                    sort_order
                FROM shared_grocery_content_lines
                WHERE content_id = %s
                ORDER BY sort_order, id;
                """,
                (content_id,),
            )
            lines = cur.fetchall()
            if not lines:
                raise ValueError(
                    "Ce contenu partagé ne contient aucun élément."
                )

            content_type = public["content_type"]
            private_name = _next_private_name(
                cur,
                content_type,
                family_id,
                public["name"],
            )

            if content_type == "template":
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
                        private_name,
                        public["description"],
                        user_id,
                    ),
                )
            else:
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
                        private_name,
                        public["description"],
                        public["instructions"],
                        _positive_int(
                            public["servings"],
                            "Le nombre de portions",
                        ),
                        user_id,
                    ),
                )

            new_parent_id = cur.fetchone()["id"]
            default_store_id = _ensure_default_store(
                cur,
                family_id,
            )

            items_created = 0
            items_reused = 0
            ambiguous_matches = 0
            duplicate_lines_merged = 0
            inserted_lines = {}

            for position, line in enumerate(lines, start=1):
                item_id, created, ambiguous = _find_or_create_item(
                    cur,
                    family_id=family_id,
                    item_name=line["item_name"],
                    category_name=line["category_name"],
                    default_store_id=default_store_id,
                )
                items_created += 1 if created else 0
                items_reused += 0 if created else 1
                ambiguous_matches += 1 if ambiguous else 0
                clean_quantity = _positive_int(line["quantity"])
                clean_note = _clean_text(line["note"])

                if item_id in inserted_lines:
                    duplicate_lines_merged += 1
                    existing_line_id = inserted_lines[item_id]
                    if content_type == "template":
                        cur.execute(
                            """
                            UPDATE grocery_template_items
                            SET quantity = GREATEST(quantity, %s)
                            WHERE id = %s;
                            """,
                            (clean_quantity, existing_line_id),
                        )
                    else:
                        cur.execute(
                            """
                            UPDATE grocery_recipe_ingredients
                            SET
                                quantity = GREATEST(quantity, %s),
                                note = CASE
                                    WHEN BTRIM(note) = '' THEN %s
                                    ELSE note
                                END
                            WHERE id = %s;
                            """,
                            (
                                clean_quantity,
                                clean_note,
                                existing_line_id,
                            ),
                        )
                    continue

                if content_type == "template":
                    cur.execute(
                        """
                        INSERT INTO grocery_template_items (
                            template_id,
                            item_id,
                            quantity,
                            sort_order
                        )
                        VALUES (%s, %s, %s, %s)
                        RETURNING id;
                        """,
                        (
                            new_parent_id,
                            item_id,
                            clean_quantity,
                            position * 10,
                        ),
                    )
                else:
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
                        RETURNING id;
                        """,
                        (
                            new_parent_id,
                            item_id,
                            clean_quantity,
                            clean_note,
                            position * 10,
                        ),
                    )

                inserted_lines[item_id] = cur.fetchone()["id"]

            action_type = f"{content_type}_copied_from_library"
            log_activity(
                cur,
                family_id,
                user_id,
                action_type,
                content_type,
                new_parent_id,
                private_name,
                {
                    "shared_content_id": int(content_id),
                    "items_created": items_created,
                    "items_reused": items_reused,
                    "ambiguous_matches": ambiguous_matches,
                    "duplicate_lines_merged": duplicate_lines_merged,
                },
            )
            conn.commit()

            return {
                "content_type": content_type,
                "new_id": new_parent_id,
                "name": private_name,
                "items_created": items_created,
                "items_reused": items_reused,
                "ambiguous_matches": ambiguous_matches,
                "duplicate_lines_merged": duplicate_lines_merged,
            }
