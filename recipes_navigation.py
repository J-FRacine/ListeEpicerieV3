"""Navigation pure de la bibliothèque de recettes."""
from __future__ import annotations


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_category_navigation(recipe_rows, category_rows, category_assignments):
    rows = [dict(row) for row in (category_rows or [])]
    assignments = category_assignments or {}
    direct_counts = {
        _as_int(row.get("id")): 0
        for row in rows
        if _as_int(row.get("id")) is not None
    }
    uncategorized_count = 0

    for recipe in recipe_rows or []:
        recipe_id = _as_int(recipe.get("id"))
        assignment = assignments.get(recipe_id, {}) if recipe_id is not None else {}
        category_id = _as_int(assignment.get("category_id"))
        if category_id is None or category_id not in direct_counts:
            uncategorized_count += 1
        else:
            direct_counts[category_id] += 1

    children_by_parent = {}
    roots = []
    for row in rows:
        category_id = _as_int(row.get("id"))
        if category_id is None:
            continue
        parent_id = _as_int(row.get("parent_id"))
        entry = {
            "id": category_id,
            "name": str(row.get("name") or "").strip(),
            "parent_id": parent_id,
            "direct_count": int(direct_counts.get(category_id, 0)),
            "count": int(direct_counts.get(category_id, 0)),
            "children": [],
        }
        if parent_id is None:
            roots.append(entry)
        else:
            children_by_parent.setdefault(parent_id, []).append(entry)

    for root in roots:
        children = children_by_parent.get(root["id"], [])
        root["children"] = children
        root["count"] = root["direct_count"] + sum(
            child["direct_count"] for child in children
        )

    return {
        "total_count": len(recipe_rows or []),
        "uncategorized_count": uncategorized_count,
        "main_categories": roots,
    }


def recipe_ids_for_navigation(
    recipe_rows,
    category_rows,
    category_assignments,
    *,
    view,
    main_category_id=None,
    subcategory_id=None,
):
    rows = [dict(row) for row in (category_rows or [])]
    assignments = category_assignments or {}
    all_ids = [int(recipe["id"]) for recipe in (recipe_rows or [])]

    if view in {"all", "recent"}:
        return set(all_ids)

    if view == "uncategorized":
        return {
            recipe_id
            for recipe_id in all_ids
            if _as_int(assignments.get(recipe_id, {}).get("category_id")) is None
        }

    if view not in {"main", "subcategory"}:
        return set()

    main_id = _as_int(main_category_id)
    sub_id = _as_int(subcategory_id)
    if view == "subcategory" and sub_id is not None:
        allowed_categories = {sub_id}
    else:
        allowed_categories = {main_id} if main_id is not None else set()
        allowed_categories.update(
            _as_int(row.get("id"))
            for row in rows
            if _as_int(row.get("parent_id")) == main_id
        )
        allowed_categories.discard(None)

    return {
        recipe_id
        for recipe_id in all_ids
        if _as_int(assignments.get(recipe_id, {}).get("category_id"))
        in allowed_categories
    }


def recent_recipe_ids(recipe_rows, limit=10):
    rows = [dict(row) for row in (recipe_rows or [])]
    rows.sort(
        key=lambda row: str(
            row.get("updated_at") or row.get("created_at") or ""
        ),
        reverse=True,
    )
    return [int(row["id"]) for row in rows[: max(0, int(limit))]]


def breadcrumb_parts(
    category_rows,
    *,
    view,
    main_category_id=None,
    subcategory_id=None,
):
    names = {
        _as_int(row.get("id")): dict(row)
        for row in (category_rows or [])
        if _as_int(row.get("id")) is not None
    }

    if view == "all":
        return ["Toutes les recettes"]
    if view == "recent":
        return ["Récentes"]
    if view == "uncategorized":
        return ["Sans catégorie"]

    main_id = _as_int(main_category_id)
    sub_id = _as_int(subcategory_id)
    if view in {"main", "subcategory"} and main_id in names:
        parts = [str(names[main_id].get("name") or "").strip()]
        if view == "subcategory" and sub_id in names:
            parts.append(str(names[sub_id].get("name") or "").strip())
        return parts
    return []
