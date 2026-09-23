from __future__ import annotations


def _db():
    import db
    return db


def _log_activity():
    from grocery_common import log_activity
    return log_activity


def _clean_name(value):
    return str(value or "").strip()


def category_path(row):
    if not row:
        return ""
    parent = _clean_name(row.get("parent_name"))
    name = _clean_name(row.get("name") or row.get("category_name"))
    if parent and name:
        return f"{parent} › {name}"
    return name or parent


def recipe_category_options(rows, *, include_all=False, main_only=False):
    options = {}
    if include_all:
        options[0] = "Toutes les catégories"
    for row in rows or []:
        if main_only and row.get("parent_id") is not None:
            continue
        options[int(row["id"])] = category_path(row)
    return options


def category_matches_filter(assigned_category_id, selected_category_id, rows):
    try:
        selected = int(selected_category_id or 0)
    except (TypeError, ValueError):
        selected = 0
    if selected <= 0:
        return True
    if assigned_category_id is None:
        return False
    try:
        assigned = int(assigned_category_id)
    except (TypeError, ValueError):
        return False
    if assigned == selected:
        return True
    by_id = {int(row["id"]): row for row in (rows or [])}
    current = by_id.get(assigned)
    return bool(current and current.get("parent_id") == selected)


def list_recipe_categories(user_id, family_id):
    if family_id is None:
        return []
    db = _db()
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT
                    category.id,
                    category.family_id,
                    category.parent_id,
                    category.name,
                    category.sort_order,
                    parent.name AS parent_name,
                    COUNT(recipe.id)::INTEGER AS direct_recipe_count,
                    (
                        SELECT COUNT(*)::INTEGER
                        FROM grocery_recipe_categories AS child
                        WHERE child.parent_id = category.id
                    ) AS child_count
                FROM grocery_recipe_categories AS category
                LEFT JOIN grocery_recipe_categories AS parent
                  ON parent.id = category.parent_id
                LEFT JOIN grocery_recipes AS recipe
                  ON recipe.recipe_category_id = category.id
                WHERE category.family_id = %s
                GROUP BY
                    category.id,
                    category.family_id,
                    category.parent_id,
                    category.name,
                    category.sort_order,
                    parent.name,
                    parent.sort_order
                ORDER BY
                    CASE WHEN category.parent_id IS NULL THEN 0 ELSE 1 END,
                    COALESCE(parent.sort_order, category.sort_order),
                    COALESCE(LOWER(parent.name), LOWER(category.name)),
                    category.sort_order,
                    LOWER(category.name),
                    category.id;
                """,
                (family_id,),
            )
            rows = [dict(row) for row in cur.fetchall()]
            for row in rows:
                row["category_path"] = category_path(row)
            return rows


def get_recipe_category_assignments(user_id, family_id):
    if family_id is None:
        return {}
    db = _db()
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT
                    recipe.id AS recipe_id,
                    category.id AS category_id,
                    category.name AS category_name,
                    category.parent_id,
                    parent.name AS parent_name
                FROM grocery_recipes AS recipe
                LEFT JOIN grocery_recipe_categories AS category
                  ON category.id = recipe.recipe_category_id
                LEFT JOIN grocery_recipe_categories AS parent
                  ON parent.id = category.parent_id
                WHERE recipe.family_id = %s;
                """,
                (family_id,),
            )
            result = {}
            for row in cur.fetchall():
                entry = dict(row)
                entry["category_path"] = (
                    f"{entry['parent_name']} › {entry['category_name']}"
                    if entry.get("parent_name") and entry.get("category_name")
                    else (entry.get("category_name") or "")
                )
                result[int(entry["recipe_id"])] = entry
            return result


def get_recipe_category_assignment(user_id, recipe_id):
    db = _db()
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    recipe.family_id,
                    category.id AS category_id,
                    category.name AS category_name,
                    category.parent_id,
                    parent.name AS parent_name
                FROM grocery_recipes AS recipe
                LEFT JOIN grocery_recipe_categories AS category
                  ON category.id = recipe.recipe_category_id
                LEFT JOIN grocery_recipe_categories AS parent
                  ON parent.id = category.parent_id
                WHERE recipe.id = %s;
                """,
                (recipe_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("Cette recette n’existe plus.")
            db._require_family_access(cur, user_id, row["family_id"])
            entry = dict(row)
            entry["category_path"] = (
                f"{entry['parent_name']} › {entry['category_name']}"
                if entry.get("parent_name") and entry.get("category_name")
                else (entry.get("category_name") or "")
            )
            return entry


def _validate_parent(cur, family_id, parent_id):
    if parent_id in (None, "", 0, "0"):
        return None
    parent_id = int(parent_id)
    cur.execute(
        """
        SELECT id, parent_id
        FROM grocery_recipe_categories
        WHERE id = %s
          AND family_id = %s;
        """,
        (parent_id, family_id),
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError("La catégorie principale choisie est invalide.")
    if row["parent_id"] is not None:
        raise ValueError("Une sous-catégorie ne peut pas contenir une autre sous-catégorie.")
    return parent_id


def _name_exists(cur, family_id, name, parent_id, exclude_id=None):
    params = [family_id, name, parent_id]
    exclusion = ""
    if exclude_id is not None:
        exclusion = "AND id <> %s"
        params.append(int(exclude_id))
    cur.execute(
        f"""
        SELECT 1
        FROM grocery_recipe_categories
        WHERE family_id = %s
          AND LOWER(BTRIM(name)) = LOWER(BTRIM(%s))
          AND parent_id IS NOT DISTINCT FROM %s
          {exclusion}
        LIMIT 1;
        """,
        tuple(params),
    )
    return cur.fetchone() is not None


def create_recipe_category(user_id, family_id, name, parent_id=None):
    clean = _clean_name(name)
    if not clean:
        raise ValueError("Le nom de la catégorie est obligatoire.")
    db = _db()
    log_activity = _log_activity()
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            db._require_family_access(cur, user_id, family_id)
            clean_parent = _validate_parent(cur, family_id, parent_id)
            if _name_exists(cur, family_id, clean, clean_parent):
                raise ValueError(f"La catégorie « {clean} » existe déjà à cet endroit.")
            cur.execute(
                """
                SELECT COALESCE(MAX(sort_order), 0) + 10 AS next_order
                FROM grocery_recipe_categories
                WHERE family_id = %s
                  AND parent_id IS NOT DISTINCT FROM %s;
                """,
                (family_id, clean_parent),
            )
            sort_order = int(cur.fetchone()["next_order"] or 10)
            cur.execute(
                """
                INSERT INTO grocery_recipe_categories (
                    family_id, parent_id, name, sort_order
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (family_id, clean_parent, clean, sort_order),
            )
            category_id = int(cur.fetchone()["id"])
            log_activity(
                cur,
                family_id,
                user_id,
                "recipe_category_created",
                "recipe_category",
                category_id,
                clean,
                {"parent_id": clean_parent},
            )
            conn.commit()
            return category_id


def rename_recipe_category(user_id, category_id, new_name):
    clean = _clean_name(new_name)
    if not clean:
        raise ValueError("Le nom de la catégorie est obligatoire.")
    db = _db()
    log_activity = _log_activity()
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, family_id, parent_id, name
                FROM grocery_recipe_categories
                WHERE id = %s;
                """,
                (category_id,),
            )
            current = cur.fetchone()
            if current is None:
                raise ValueError("Cette catégorie n’existe plus.")
            db._require_family_access(cur, user_id, current["family_id"])
            if _name_exists(
                cur,
                current["family_id"],
                clean,
                current["parent_id"],
                exclude_id=category_id,
            ):
                raise ValueError(f"La catégorie « {clean} » existe déjà à cet endroit.")
            cur.execute(
                """
                UPDATE grocery_recipe_categories
                SET name = %s,
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (clean, category_id),
            )
            log_activity(
                cur,
                current["family_id"],
                user_id,
                "recipe_category_renamed",
                "recipe_category",
                category_id,
                clean,
                {"old_name": current["name"]},
            )
            conn.commit()


def delete_recipe_category(user_id, category_id):
    db = _db()
    log_activity = _log_activity()
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, family_id, name
                FROM grocery_recipe_categories
                WHERE id = %s;
                """,
                (category_id,),
            )
            current = cur.fetchone()
            if current is None:
                raise ValueError("Cette catégorie n’existe plus.")
            db._require_family_access(cur, user_id, current["family_id"])
            cur.execute(
                """
                SELECT COUNT(*)::INTEGER AS total
                FROM grocery_recipe_categories
                WHERE parent_id = %s;
                """,
                (category_id,),
            )
            if int(cur.fetchone()["total"] or 0):
                raise ValueError(
                    "Supprimez ou déplacez d’abord les sous-catégories de cette catégorie."
                )
            cur.execute(
                "DELETE FROM grocery_recipe_categories WHERE id = %s;",
                (category_id,),
            )
            log_activity(
                cur,
                current["family_id"],
                user_id,
                "recipe_category_deleted",
                "recipe_category",
                category_id,
                current["name"],
            )
            conn.commit()


def set_recipe_category(user_id, recipe_id, category_id):
    db = _db()
    log_activity = _log_activity()
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, family_id, name, recipe_category_id
                FROM grocery_recipes
                WHERE id = %s;
                """,
                (recipe_id,),
            )
            recipe = cur.fetchone()
            if recipe is None:
                raise ValueError("Cette recette n’existe plus.")
            db._require_family_access(cur, user_id, recipe["family_id"])
            clean_category_id = None
            if category_id not in (None, "", 0, "0"):
                clean_category_id = int(category_id)
                cur.execute(
                    """
                    SELECT id
                    FROM grocery_recipe_categories
                    WHERE id = %s
                      AND family_id = %s;
                    """,
                    (clean_category_id, recipe["family_id"]),
                )
                if cur.fetchone() is None:
                    raise ValueError("La catégorie de recette choisie est invalide.")
            if recipe["recipe_category_id"] == clean_category_id:
                return
            cur.execute(
                """
                UPDATE grocery_recipes
                SET recipe_category_id = %s,
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (clean_category_id, recipe_id),
            )
            log_activity(
                cur,
                recipe["family_id"],
                user_id,
                "recipe_category_assigned",
                "recipe",
                recipe_id,
                recipe["name"],
                {"recipe_category_id": clean_category_id},
            )
            conn.commit()


def delete_recipes_bulk(user_id, family_id, recipe_ids):
    selected = sorted({int(value) for value in (recipe_ids or [])})
    if not selected:
        raise ValueError("Sélectionnez au moins une recette.")
    db = _db()
    log_activity = _log_activity()
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            db._require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT id, name
                FROM grocery_recipes
                WHERE family_id = %s
                  AND id = ANY(%s)
                ORDER BY id;
                """,
                (family_id, selected),
            )
            rows = cur.fetchall()
            if len(rows) != len(selected):
                raise ValueError(
                    "Une des recettes sélectionnées n’existe plus ou n’appartient pas à cette famille."
                )
            for row in rows:
                log_activity(
                    cur,
                    family_id,
                    user_id,
                    "recipe_deleted",
                    "recipe",
                    row["id"],
                    row["name"],
                    {"bulk": True},
                )
            cur.execute(
                """
                DELETE FROM grocery_recipes
                WHERE family_id = %s
                  AND id = ANY(%s);
                """,
                (family_id, selected),
            )
            deleted = int(cur.rowcount or 0)
            conn.commit()
            return deleted
