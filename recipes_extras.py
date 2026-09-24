from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation


NUTRITION_FIELDS = (
    ("calories_kcal", "Calories", "kcal"),
    ("protein_g", "Protéines", "g"),
    ("carbohydrates_g", "Glucides", "g"),
    ("sugars_g", "Sucres", "g"),
    ("fiber_g", "Fibres", "g"),
    ("fat_g", "Lipides", "g"),
    ("saturated_fat_g", "Gras saturés", "g"),
    ("sodium_mg", "Sodium", "mg"),
    ("cholesterol_mg", "Cholestérol", "mg"),
)

BASIS_LABELS = {
    "per_serving": "Par portion",
    "whole_recipe": "Recette complète",
}


def _db():
    import db
    return db


def _clean_text(value, limit=500):
    return str(value or "").strip()[:limit]


def _nonnegative_int(value, label):
    if value in (None, ""):
        return None
    try:
        number = int(float(value))
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} doit être un nombre entier.") from error
    if number < 0:
        raise ValueError(f"{label} ne peut pas être négatif.")
    return number


def _clean_tags(value):
    if value is None:
        return []
    if isinstance(value, str):
        values = re_split_tags(value)
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        raise ValueError("Les étiquettes de recette sont invalides.")

    result = []
    seen = set()
    for raw in values:
        tag = _clean_text(raw, 60)
        if not tag:
            continue
        key = tag.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(tag)
        if len(result) >= 20:
            break
    return result


def re_split_tags(value):
    import re
    return [
        part.strip()
        for part in re.split(r"[,;\n]+", str(value or ""))
        if part.strip()
    ]


def _number(value, label):
    if value in (None, ""):
        return None
    try:
        number = Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"{label} doit être un nombre.") from error
    if number < 0:
        raise ValueError(f"{label} ne peut pas être négatif.")
    if number > Decimal("1000000"):
        raise ValueError(f"{label} est trop élevé.")
    return float(number)


def normalize_nutrition(value):
    if value in (None, ""):
        return None
    if not isinstance(value, dict):
        raise ValueError("Le tableau nutritionnel est invalide.")

    basis = str(value.get("basis") or "per_serving").strip()
    aliases = {
        "per_serving": "per_serving",
        "par_portion": "per_serving",
        "portion": "per_serving",
        "whole_recipe": "whole_recipe",
        "recette_complete": "whole_recipe",
        "total": "whole_recipe",
    }
    basis = aliases.get(basis.casefold(), basis)
    if basis not in BASIS_LABELS:
        raise ValueError(
            "La base nutritionnelle doit être « per_serving » "
            "ou « whole_recipe »."
        )

    result = {
        "basis": basis,
        "estimated": bool(value.get("estimated", True)),
    }
    any_value = False
    for key, label, _unit in NUTRITION_FIELDS:
        aliases_for_key = {
            "calories_kcal": ("calories_kcal", "calories", "kcal"),
            "protein_g": ("protein_g", "protein", "proteines_g", "protéines_g"),
            "carbohydrates_g": (
                "carbohydrates_g", "carbs_g", "glucides_g", "carbohydrates",
            ),
            "sugars_g": ("sugars_g", "sugar_g", "sucres_g"),
            "fiber_g": ("fiber_g", "fibre_g", "fibres_g"),
            "fat_g": ("fat_g", "lipides_g", "fats_g"),
            "saturated_fat_g": (
                "saturated_fat_g", "saturated_g", "gras_satures_g",
                "gras_saturés_g",
            ),
            "sodium_mg": ("sodium_mg", "sodium"),
            "cholesterol_mg": ("cholesterol_mg", "cholesterol"),
        }[key]
        raw = None
        for alias in aliases_for_key:
            if alias in value:
                raw = value.get(alias)
                break
        number = _number(raw, label) if raw not in (None, "") else None
        result[key] = number
        if number is not None:
            any_value = True

    return result if any_value else None


def default_recipe_extra():
    return {
        "prep_time_minutes": None,
        "cook_time_minutes": None,
        "tags": [],
        "source": {"name": "", "url": ""},
        "nutrition": None,
    }


def normalize_recipe_extra(value):
    result = default_recipe_extra()
    if isinstance(value, dict):
        result.update(
            {
                "prep_time_minutes": value.get("prep_time_minutes"),
                "cook_time_minutes": value.get("cook_time_minutes"),
                "tags": value.get("tags", []),
                "source": value.get("source") or {},
                "nutrition": value.get("nutrition"),
            }
        )

    result["prep_time_minutes"] = _nonnegative_int(
        result.get("prep_time_minutes"),
        "Le temps de préparation",
    )
    result["cook_time_minutes"] = _nonnegative_int(
        result.get("cook_time_minutes"),
        "Le temps de cuisson",
    )
    result["tags"] = _clean_tags(result.get("tags"))

    source = result.get("source")
    if isinstance(source, str):
        source = {"name": source, "url": ""}
    if not isinstance(source, dict):
        source = {}
    result["source"] = {
        "name": _clean_text(source.get("name"), 200),
        "url": _clean_text(source.get("url"), 1000),
    }
    result["nutrition"] = normalize_nutrition(result.get("nutrition"))
    return result


def get_recipe_extras(user_id, recipe_id):
    db = _db()
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT family_id, recipe_extra
                FROM grocery_recipes
                WHERE id = %s;
                """,
                (recipe_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("Cette recette n’existe plus.")
            db._require_family_access(cur, user_id, row["family_id"])
            return normalize_recipe_extra(row.get("recipe_extra") or {})


def _save_extra(user_id, recipe_id, extra):
    db = _db()
    normalized = normalize_recipe_extra(extra)
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT family_id
                FROM grocery_recipes
                WHERE id = %s;
                """,
                (recipe_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("Cette recette n’existe plus.")
            db._require_family_access(cur, user_id, row["family_id"])
            cur.execute(
                """
                UPDATE grocery_recipes
                SET recipe_extra = %s::jsonb,
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (
                    __import__("json").dumps(
                        normalized,
                        ensure_ascii=False,
                    ),
                    recipe_id,
                ),
            )
            conn.commit()
    return normalized


def save_recipe_metadata(
    user_id,
    recipe_id,
    *,
    prep_time_minutes=None,
    cook_time_minutes=None,
    tags=None,
    source_name="",
    source_url="",
):
    current = get_recipe_extras(user_id, recipe_id)
    current["prep_time_minutes"] = prep_time_minutes
    current["cook_time_minutes"] = cook_time_minutes
    current["tags"] = _clean_tags(tags)
    current["source"] = {
        "name": _clean_text(source_name, 200),
        "url": _clean_text(source_url, 1000),
    }
    return _save_extra(user_id, recipe_id, current)


def save_recipe_nutrition(user_id, recipe_id, nutrition):
    current = get_recipe_extras(user_id, recipe_id)
    current["nutrition"] = normalize_nutrition(nutrition)
    return _save_extra(user_id, recipe_id, current)


def delete_recipe_nutrition(user_id, recipe_id):
    current = get_recipe_extras(user_id, recipe_id)
    current["nutrition"] = None
    return _save_extra(user_id, recipe_id, current)


def recipe_extra_search_text(extra):
    value = normalize_recipe_extra(extra)
    source = value.get("source") or {}
    parts = [
        " ".join(value.get("tags") or []),
        str(source.get("name") or ""),
        str(source.get("url") or ""),
    ]
    return " ".join(parts).casefold()


def recipe_time_label(extra):
    value = normalize_recipe_extra(extra)
    prep = value.get("prep_time_minutes")
    cook = value.get("cook_time_minutes")
    parts = []
    if prep is not None:
        parts.append(f"Préparation {prep} min")
    if cook is not None:
        parts.append(f"Cuisson {cook} min")
    return " · ".join(parts)


def _format_number(value):
    if value is None:
        return "—"
    number = float(value)
    if abs(number - round(number)) < 0.05:
        return str(int(round(number)))
    return f"{number:.1f}".replace(".", ",")


def nutrition_rows(nutrition, servings):
    normalized = normalize_nutrition(nutrition)
    if not normalized:
        return []

    try:
        servings = max(1, int(servings or 1))
    except (TypeError, ValueError):
        servings = 1

    rows = []
    for key, label, unit in NUTRITION_FIELDS:
        value = normalized.get(key)
        if value is None:
            continue
        if normalized["basis"] == "per_serving":
            per_serving = float(value)
            whole = float(value) * servings
        else:
            whole = float(value)
            per_serving = float(value) / servings

        rows.append(
            {
                "key": key,
                "label": label,
                "unit": unit,
                "per_serving": per_serving,
                "whole_recipe": whole,
                "per_serving_text": (
                    f"{_format_number(per_serving)} {unit}"
                    if unit != "kcal"
                    else f"{_format_number(per_serving)} kcal"
                ),
                "whole_recipe_text": (
                    f"{_format_number(whole)} {unit}"
                    if unit != "kcal"
                    else f"{_format_number(whole)} kcal"
                ),
            }
        )
    return rows


def nutrition_short_label(nutrition, servings):
    rows = nutrition_rows(nutrition, servings)
    calories = next(
        (row for row in rows if row["key"] == "calories_kcal"),
        None,
    )
    if calories:
        return f"{calories['per_serving_text']} / portion"
    return "Tableau nutritionnel"
