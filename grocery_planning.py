import db as _db

from grocery_common import log_activity


# ---------------------------------------------------------
# OUTILS INTERNES
# ---------------------------------------------------------


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


def _parent_table(kind):
    if kind == "template":
        return "grocery_templates"
    if kind == "recipe":
        return "grocery_recipes"
    raise ValueError("Type de contenu invalide.")


def _line_table(kind):
    if kind == "template":
        return "grocery_template_items"
    if kind == "recipe":
        return "grocery_recipe_ingredients"
    raise ValueError("Type de contenu invalide.")


def _line_parent_column(kind):
    if kind == "template":
        return "template_id"
    if kind == "recipe":
        return "recipe_id"
    raise ValueError("Type de contenu invalide.")


def _load_parent(cur, user_id, kind, parent_id):
    table = _parent_table(kind)

    cur.execute(
        f"""
        SELECT id, family_id, name
        FROM {table}
        WHERE id = %s;
        """,
        (parent_id,),
    )
    row = cur.fetchone()

    if row is None:
        label = "Cette liste modèle" if kind == "template" else "Cette recette"
        raise ValueError(f"{label} n’existe plus.")

    _db._require_family_access(
        cur,
        user_id,
        row["family_id"],
    )
    return row


def _require_item(cur, family_id, item_id):
    cur.execute(
        """
        SELECT id, family_id, name
        FROM items
        WHERE id = %s
          AND family_id = %s
          AND deleted_at IS NULL;
        """,
        (item_id, family_id),
    )
    item = cur.fetchone()

    if item is None:
        raise ValueError(
            "L’item choisi n’existe plus ou n’appartient pas à cette famille."
        )

    return item


def _name_exists(cur, kind, family_id, name, exclude_id=None):
    table = _parent_table(kind)
    params = [family_id, name]
    exclusion = ""

    if exclude_id is not None:
        exclusion = "AND id <> %s"
        params.append(exclude_id)

    cur.execute(
        f"""
        SELECT 1
        FROM {table}
        WHERE family_id = %s
          AND LOWER(BTRIM(name)) = LOWER(BTRIM(%s))
          {exclusion}
        LIMIT 1;
        """,
        tuple(params),
    )
    return cur.fetchone() is not None


def _next_line_order(cur, kind, parent_id):
    table = _line_table(kind)
    parent_column = _line_parent_column(kind)

    cur.execute(
        f"""
        SELECT COALESCE(MAX(sort_order), 0) + 10 AS next_order
        FROM {table}
        WHERE {parent_column} = %s;
        """,
        (parent_id,),
    )
    return cur.fetchone()["next_order"]


def _move_line(cur, kind, parent_id, line_id, direction):
    direction = int(direction)
    if direction not in {-1, 1}:
        raise ValueError("Direction de déplacement invalide.")

    table = _line_table(kind)
    parent_column = _line_parent_column(kind)

    cur.execute(
        f"""
        SELECT id
        FROM {table}
        WHERE {parent_column} = %s
        ORDER BY sort_order, id;
        """,
        (parent_id,),
    )
    rows = cur.fetchall()
    identifiers = [row["id"] for row in rows]

    if line_id not in identifiers:
        raise ValueError("Cet élément n’existe plus.")

    position = identifiers.index(line_id)
    destination = position + direction

    if destination < 0 or destination >= len(rows):
        return False

    for index, row in enumerate(rows, start=1):
        cur.execute(
            f"UPDATE {table} SET sort_order = %s WHERE id = %s;",
            (index * 10, row["id"]),
        )

    other_id = rows[destination]["id"]
    cur.execute(
        f"UPDATE {table} SET sort_order = %s WHERE id = %s;",
        ((destination + 1) * 10, line_id),
    )
    cur.execute(
        f"UPDATE {table} SET sort_order = %s WHERE id = %s;",
        ((position + 1) * 10, other_id),
    )
    return True


def _apply_lines_to_needs(
    cur,
    *,
    user_id,
    family_id,
    kind,
    parent_id,
    entity_name,
):
    table = _line_table(kind)
    parent_column = _line_parent_column(kind)

    cur.execute(
        f"""
        SELECT
            line.item_id,
            line.quantity AS requested_quantity,
            item.name,
            item.quantity AS current_quantity,
            item.needed
        FROM {table} AS line
        JOIN items AS item
          ON item.id = line.item_id
         AND item.family_id = %s
         AND item.deleted_at IS NULL
        WHERE line.{parent_column} = %s
        ORDER BY line.sort_order, line.id;
        """,
        (family_id, parent_id),
    )
    rows = cur.fetchall()

    if not rows:
        noun = "La liste modèle" if kind == "template" else "La recette"
        raise ValueError(f"{noun} ne contient aucun item actif.")

    added = 0
    quantities_updated = 0

    for row in rows:
        new_quantity = max(
            int(row["current_quantity"] or 1),
            int(row["requested_quantity"] or 1),
        )
        was_needed = bool(row["needed"])

        if not was_needed:
            added += 1

        if new_quantity != int(row["current_quantity"] or 1):
            quantities_updated += 1

        cur.execute(
            """
            UPDATE items
            SET
                quantity = %s,
                needed = 1,
                times_needed = times_needed + %s,
                last_needed_at = CASE
                    WHEN %s = 1 THEN NOW()
                    ELSE last_needed_at
                END
            WHERE id = %s;
            """,
            (
                new_quantity,
                0 if was_needed else 1,
                0 if was_needed else 1,
                row["item_id"],
            ),
        )

    action_type = (
        "template_applied"
        if kind == "template"
        else "recipe_applied"
    )
    entity_type = "template" if kind == "template" else "recipe"

    log_activity(
        cur,
        family_id,
        user_id,
        action_type,
        entity_type,
        parent_id,
        entity_name,
        {
            "items_total": len(rows),
            "items_added": added,
            "quantities_updated": quantities_updated,
        },
    )

    return {
        "items_total": len(rows),
        "items_added": added,
        "quantities_updated": quantities_updated,
    }


# ---------------------------------------------------------
# LISTES MODÈLES
# ---------------------------------------------------------


def get_templates(user_id, family_id):
    if family_id is None:
        return []

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT
                    template.id,
                    template.name,
                    template.description,
                    template.created_at,
                    template.updated_at,
                    COUNT(item.id)::INTEGER AS item_count
                FROM grocery_templates AS template
                LEFT JOIN grocery_template_items AS line
                  ON line.template_id = template.id
                LEFT JOIN items AS item
                  ON item.id = line.item_id
                 AND item.deleted_at IS NULL
                WHERE template.family_id = %s
                GROUP BY template.id
                ORDER BY LOWER(template.name), template.name, template.id;
                """,
                (family_id,),
            )
            return cur.fetchall()


def get_template_items(user_id, template_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            template = _load_parent(
                cur,
                user_id,
                "template",
                template_id,
            )
            cur.execute(
                """
                SELECT
                    line.id,
                    line.item_id,
                    line.quantity,
                    line.sort_order,
                    item.name,
                    item.note,
                    item.needed,
                    category.name AS category,
                    COALESCE(store.name, 'Sans magasin') AS store
                FROM grocery_template_items AS line
                JOIN items AS item
                  ON item.id = line.item_id
                 AND item.family_id = %s
                 AND item.deleted_at IS NULL
                JOIN categories AS category
                  ON category.id = item.category_id
                LEFT JOIN stores AS store
                  ON store.id = item.store_id
                WHERE line.template_id = %s
                ORDER BY line.sort_order, line.id;
                """,
                (template["family_id"], template_id),
            )
            return cur.fetchall()


def create_template(user_id, family_id, name, description=""):
    clean_name = _clean_text(name)
    clean_description = _clean_text(description)

    if not clean_name:
        raise ValueError("Le nom de la liste modèle est obligatoire.")

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)

            if _name_exists(cur, "template", family_id, clean_name):
                raise ValueError(
                    f"La liste modèle « {clean_name} » existe déjà."
                )

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
                    clean_name,
                    clean_description,
                    user_id,
                ),
            )
            template_id = cur.fetchone()["id"]

            log_activity(
                cur,
                family_id,
                user_id,
                "template_created",
                "template",
                template_id,
                clean_name,
            )
            conn.commit()
            return template_id


def create_template_from_needs(
    user_id,
    family_id,
    name,
    description="",
):
    clean_name = _clean_text(name)
    clean_description = _clean_text(description)

    if not clean_name:
        raise ValueError("Le nom de la liste modèle est obligatoire.")

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)

            if _name_exists(cur, "template", family_id, clean_name):
                raise ValueError(
                    f"La liste modèle « {clean_name} » existe déjà."
                )

            cur.execute(
                """
                SELECT id, quantity
                FROM items
                WHERE family_id = %s
                  AND deleted_at IS NULL
                  AND needed = 1
                ORDER BY id;
                """,
                (family_id,),
            )
            needed_items = cur.fetchall()

            if not needed_items:
                raise ValueError(
                    "Aucun besoin actif ne peut être ajouté à la liste modèle."
                )

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
                    clean_name,
                    clean_description,
                    user_id,
                ),
            )
            template_id = cur.fetchone()["id"]

            for position, item in enumerate(needed_items, start=1):
                cur.execute(
                    """
                    INSERT INTO grocery_template_items (
                        template_id,
                        item_id,
                        quantity,
                        sort_order
                    )
                    VALUES (%s, %s, %s, %s);
                    """,
                    (
                        template_id,
                        item["id"],
                        max(1, int(item["quantity"] or 1)),
                        position * 10,
                    ),
                )

            log_activity(
                cur,
                family_id,
                user_id,
                "template_created",
                "template",
                template_id,
                clean_name,
                {"created_from_needs": True, "item_count": len(needed_items)},
            )
            conn.commit()
            return template_id


def update_template(user_id, template_id, name, description=""):
    clean_name = _clean_text(name)
    clean_description = _clean_text(description)

    if not clean_name:
        raise ValueError("Le nom de la liste modèle est obligatoire.")

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            template = _load_parent(
                cur,
                user_id,
                "template",
                template_id,
            )

            if _name_exists(
                cur,
                "template",
                template["family_id"],
                clean_name,
                exclude_id=template_id,
            ):
                raise ValueError(
                    f"La liste modèle « {clean_name} » existe déjà."
                )

            cur.execute(
                """
                UPDATE grocery_templates
                SET name = %s,
                    description = %s,
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (clean_name, clean_description, template_id),
            )

            log_activity(
                cur,
                template["family_id"],
                user_id,
                "template_updated",
                "template",
                template_id,
                clean_name,
                {"old_name": template["name"]},
            )
            conn.commit()


def delete_template(user_id, template_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            template = _load_parent(
                cur,
                user_id,
                "template",
                template_id,
            )
            cur.execute(
                "DELETE FROM grocery_templates WHERE id = %s;",
                (template_id,),
            )
            log_activity(
                cur,
                template["family_id"],
                user_id,
                "template_deleted",
                "template",
                template_id,
                template["name"],
            )
            conn.commit()


def add_template_item(user_id, template_id, item_id, quantity=1):
    clean_quantity = _positive_int(quantity)

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            template = _load_parent(
                cur,
                user_id,
                "template",
                template_id,
            )
            _require_item(
                cur,
                template["family_id"],
                item_id,
            )

            cur.execute(
                """
                SELECT 1
                FROM grocery_template_items
                WHERE template_id = %s
                  AND item_id = %s;
                """,
                (template_id, item_id),
            )
            if cur.fetchone() is not None:
                raise ValueError("Cet item est déjà dans la liste modèle.")

            cur.execute(
                """
                INSERT INTO grocery_template_items (
                    template_id,
                    item_id,
                    quantity,
                    sort_order
                )
                VALUES (%s, %s, %s, %s);
                """,
                (
                    template_id,
                    item_id,
                    clean_quantity,
                    _next_line_order(cur, "template", template_id),
                ),
            )
            cur.execute(
                """
                UPDATE grocery_templates
                SET updated_at = NOW()
                WHERE id = %s;
                """,
                (template_id,),
            )
            conn.commit()


def update_template_item(user_id, line_id, quantity):
    clean_quantity = _positive_int(quantity)

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT line.template_id
                FROM grocery_template_items AS line
                WHERE line.id = %s;
                """,
                (line_id,),
            )
            line = cur.fetchone()
            if line is None:
                raise ValueError("Cet item de la liste modèle n’existe plus.")

            template = _load_parent(
                cur,
                user_id,
                "template",
                line["template_id"],
            )
            cur.execute(
                """
                UPDATE grocery_template_items
                SET quantity = %s
                WHERE id = %s;
                """,
                (clean_quantity, line_id),
            )
            cur.execute(
                """
                UPDATE grocery_templates
                SET updated_at = NOW()
                WHERE id = %s;
                """,
                (template["id"],),
            )
            conn.commit()


def remove_template_item(user_id, line_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT template_id
                FROM grocery_template_items
                WHERE id = %s;
                """,
                (line_id,),
            )
            line = cur.fetchone()
            if line is None:
                raise ValueError("Cet item de la liste modèle n’existe plus.")

            template = _load_parent(
                cur,
                user_id,
                "template",
                line["template_id"],
            )
            cur.execute(
                "DELETE FROM grocery_template_items WHERE id = %s;",
                (line_id,),
            )
            cur.execute(
                """
                UPDATE grocery_templates
                SET updated_at = NOW()
                WHERE id = %s;
                """,
                (template["id"],),
            )
            conn.commit()


def move_template_item(user_id, line_id, direction):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT template_id
                FROM grocery_template_items
                WHERE id = %s;
                """,
                (line_id,),
            )
            line = cur.fetchone()
            if line is None:
                raise ValueError("Cet item de la liste modèle n’existe plus.")

            template = _load_parent(
                cur,
                user_id,
                "template",
                line["template_id"],
            )
            moved = _move_line(
                cur,
                "template",
                template["id"],
                line_id,
                direction,
            )
            if moved:
                cur.execute(
                    """
                    UPDATE grocery_templates
                    SET updated_at = NOW()
                    WHERE id = %s;
                    """,
                    (template["id"],),
                )
            conn.commit()
            return moved


def apply_template_to_needs(user_id, template_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            template = _load_parent(
                cur,
                user_id,
                "template",
                template_id,
            )
            result = _apply_lines_to_needs(
                cur,
                user_id=user_id,
                family_id=template["family_id"],
                kind="template",
                parent_id=template_id,
                entity_name=template["name"],
            )
            conn.commit()
            return result


# ---------------------------------------------------------
# RECETTES
# ---------------------------------------------------------


def get_recipes(user_id, family_id):
    if family_id is None:
        return []

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT
                    recipe.id,
                    recipe.name,
                    recipe.description,
                    recipe.instructions,
                    recipe.servings,
                    recipe.created_at,
                    recipe.updated_at,
                    COUNT(item.id)::INTEGER AS ingredient_count
                FROM grocery_recipes AS recipe
                LEFT JOIN grocery_recipe_ingredients AS ingredient
                  ON ingredient.recipe_id = recipe.id
                LEFT JOIN items AS item
                  ON item.id = ingredient.item_id
                 AND item.deleted_at IS NULL
                WHERE recipe.family_id = %s
                GROUP BY recipe.id
                ORDER BY LOWER(recipe.name), recipe.name, recipe.id;
                """,
                (family_id,),
            )
            return cur.fetchall()


def get_recipe_ingredients(user_id, recipe_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            recipe = _load_parent(
                cur,
                user_id,
                "recipe",
                recipe_id,
            )
            cur.execute(
                """
                SELECT
                    ingredient.id,
                    ingredient.item_id,
                    ingredient.quantity,
                    ingredient.note,
                    ingredient.sort_order,
                    item.name,
                    item.note AS item_note,
                    item.needed,
                    category.name AS category,
                    COALESCE(store.name, 'Sans magasin') AS store
                FROM grocery_recipe_ingredients AS ingredient
                JOIN items AS item
                  ON item.id = ingredient.item_id
                 AND item.family_id = %s
                 AND item.deleted_at IS NULL
                JOIN categories AS category
                  ON category.id = item.category_id
                LEFT JOIN stores AS store
                  ON store.id = item.store_id
                WHERE ingredient.recipe_id = %s
                ORDER BY ingredient.sort_order, ingredient.id;
                """,
                (recipe["family_id"], recipe_id),
            )
            return cur.fetchall()


def create_recipe(
    user_id,
    family_id,
    name,
    description="",
    instructions="",
    servings=4,
):
    clean_name = _clean_text(name)
    clean_description = _clean_text(description)
    clean_instructions = _clean_text(instructions)
    clean_servings = _positive_int(servings, "Le nombre de portions")

    if not clean_name:
        raise ValueError("Le nom de la recette est obligatoire.")

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)

            if _name_exists(cur, "recipe", family_id, clean_name):
                raise ValueError(f"La recette « {clean_name} » existe déjà.")

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
                    clean_name,
                    clean_description,
                    clean_instructions,
                    clean_servings,
                    user_id,
                ),
            )
            recipe_id = cur.fetchone()["id"]
            log_activity(
                cur,
                family_id,
                user_id,
                "recipe_created",
                "recipe",
                recipe_id,
                clean_name,
            )
            conn.commit()
            return recipe_id


def update_recipe(
    user_id,
    recipe_id,
    name,
    description="",
    instructions="",
    servings=4,
):
    clean_name = _clean_text(name)
    clean_description = _clean_text(description)
    clean_instructions = _clean_text(instructions)
    clean_servings = _positive_int(servings, "Le nombre de portions")

    if not clean_name:
        raise ValueError("Le nom de la recette est obligatoire.")

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            recipe = _load_parent(
                cur,
                user_id,
                "recipe",
                recipe_id,
            )

            if _name_exists(
                cur,
                "recipe",
                recipe["family_id"],
                clean_name,
                exclude_id=recipe_id,
            ):
                raise ValueError(f"La recette « {clean_name} » existe déjà.")

            cur.execute(
                """
                UPDATE grocery_recipes
                SET name = %s,
                    description = %s,
                    instructions = %s,
                    servings = %s,
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (
                    clean_name,
                    clean_description,
                    clean_instructions,
                    clean_servings,
                    recipe_id,
                ),
            )
            log_activity(
                cur,
                recipe["family_id"],
                user_id,
                "recipe_updated",
                "recipe",
                recipe_id,
                clean_name,
                {"old_name": recipe["name"]},
            )
            conn.commit()


def delete_recipe(user_id, recipe_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            recipe = _load_parent(
                cur,
                user_id,
                "recipe",
                recipe_id,
            )
            cur.execute(
                "DELETE FROM grocery_recipes WHERE id = %s;",
                (recipe_id,),
            )
            log_activity(
                cur,
                recipe["family_id"],
                user_id,
                "recipe_deleted",
                "recipe",
                recipe_id,
                recipe["name"],
            )
            conn.commit()


def add_recipe_ingredient(
    user_id,
    recipe_id,
    item_id,
    quantity=1,
    note="",
):
    clean_quantity = _positive_int(quantity)
    clean_note = _clean_text(note)

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            recipe = _load_parent(
                cur,
                user_id,
                "recipe",
                recipe_id,
            )
            _require_item(
                cur,
                recipe["family_id"],
                item_id,
            )

            cur.execute(
                """
                SELECT 1
                FROM grocery_recipe_ingredients
                WHERE recipe_id = %s
                  AND item_id = %s;
                """,
                (recipe_id, item_id),
            )
            if cur.fetchone() is not None:
                raise ValueError("Cet item est déjà dans la recette.")

            cur.execute(
                """
                INSERT INTO grocery_recipe_ingredients (
                    recipe_id,
                    item_id,
                    quantity,
                    note,
                    sort_order
                )
                VALUES (%s, %s, %s, %s, %s);
                """,
                (
                    recipe_id,
                    item_id,
                    clean_quantity,
                    clean_note,
                    _next_line_order(cur, "recipe", recipe_id),
                ),
            )
            cur.execute(
                """
                UPDATE grocery_recipes
                SET updated_at = NOW()
                WHERE id = %s;
                """,
                (recipe_id,),
            )
            conn.commit()


def update_recipe_ingredient(user_id, ingredient_id, quantity, note=""):
    clean_quantity = _positive_int(quantity)
    clean_note = _clean_text(note)

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT recipe_id
                FROM grocery_recipe_ingredients
                WHERE id = %s;
                """,
                (ingredient_id,),
            )
            ingredient = cur.fetchone()
            if ingredient is None:
                raise ValueError("Cet ingrédient n’existe plus.")

            recipe = _load_parent(
                cur,
                user_id,
                "recipe",
                ingredient["recipe_id"],
            )
            cur.execute(
                """
                UPDATE grocery_recipe_ingredients
                SET quantity = %s,
                    note = %s
                WHERE id = %s;
                """,
                (clean_quantity, clean_note, ingredient_id),
            )
            cur.execute(
                """
                UPDATE grocery_recipes
                SET updated_at = NOW()
                WHERE id = %s;
                """,
                (recipe["id"],),
            )
            conn.commit()


def remove_recipe_ingredient(user_id, ingredient_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT recipe_id
                FROM grocery_recipe_ingredients
                WHERE id = %s;
                """,
                (ingredient_id,),
            )
            ingredient = cur.fetchone()
            if ingredient is None:
                raise ValueError("Cet ingrédient n’existe plus.")

            recipe = _load_parent(
                cur,
                user_id,
                "recipe",
                ingredient["recipe_id"],
            )
            cur.execute(
                "DELETE FROM grocery_recipe_ingredients WHERE id = %s;",
                (ingredient_id,),
            )
            cur.execute(
                """
                UPDATE grocery_recipes
                SET updated_at = NOW()
                WHERE id = %s;
                """,
                (recipe["id"],),
            )
            conn.commit()


def move_recipe_ingredient(user_id, ingredient_id, direction):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT recipe_id
                FROM grocery_recipe_ingredients
                WHERE id = %s;
                """,
                (ingredient_id,),
            )
            ingredient = cur.fetchone()
            if ingredient is None:
                raise ValueError("Cet ingrédient n’existe plus.")

            recipe = _load_parent(
                cur,
                user_id,
                "recipe",
                ingredient["recipe_id"],
            )
            moved = _move_line(
                cur,
                "recipe",
                recipe["id"],
                ingredient_id,
                direction,
            )
            if moved:
                cur.execute(
                    """
                    UPDATE grocery_recipes
                    SET updated_at = NOW()
                    WHERE id = %s;
                    """,
                    (recipe["id"],),
                )
            conn.commit()
            return moved


def apply_recipe_to_needs(user_id, recipe_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            recipe = _load_parent(
                cur,
                user_id,
                "recipe",
                recipe_id,
            )
            result = _apply_lines_to_needs(
                cur,
                user_id=user_id,
                family_id=recipe["family_id"],
                kind="recipe",
                parent_id=recipe_id,
                entity_name=recipe["name"],
            )
            conn.commit()
            return result
