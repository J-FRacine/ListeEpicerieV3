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

    raw_basis = str(value.get("basis") or "").strip()
    aliases = {
        "per_serving": "per_serving",
        "par_portion": "per_serving",
        "portion": "per_serving",
        "whole_recipe": "whole_recipe",
        "recette_complete": "whole_recipe",
        "total": "whole_recipe",
    }
    canonical_basis = aliases.get(raw_basis.casefold())

    per_serving = (
        value.get("per_serving")
        if isinstance(value.get("per_serving"), dict)
        else value.get("per_serving_values")
    )
    whole_recipe = (
        value.get("whole_recipe")
        if isinstance(value.get("whole_recipe"), dict)
        else value.get("whole_recipe_values")
    )

    if canonical_basis == "per_serving":
        numeric_source = per_serving if isinstance(per_serving, dict) else value
        basis = "per_serving"
    elif canonical_basis == "whole_recipe":
        numeric_source = whole_recipe if isinstance(whole_recipe, dict) else value
        basis = "whole_recipe"
    elif isinstance(per_serving, dict) and per_serving:
        numeric_source = per_serving
        basis = "per_serving"
    elif isinstance(whole_recipe, dict) and whole_recipe:
        numeric_source = whole_recipe
        basis = "whole_recipe"
    elif not raw_basis:
        numeric_source = value
        basis = "per_serving"
    else:
        raise ValueError(
            "La base nutritionnelle doit être « per_serving » ou "
            "« whole_recipe », ou le tableau doit fournir un bloc "
            "« per_serving » / « whole_recipe »."
        )

    notes_value = value.get("notes")
    if isinstance(notes_value, str):
        notes = [
            line.strip()
            for line in notes_value.splitlines()
            if line.strip()
        ]
    elif isinstance(notes_value, (list, tuple)):
        notes = [
            _clean_text(note, 500)
            for note in notes_value
            if _clean_text(note, 500)
        ][:20]
    else:
        notes = []

    result = {
        "basis": basis,
        "estimated": bool(value.get("estimated", True)),
        "serving_size": _clean_text(value.get("serving_size"), 200),
        "notes": notes,
        "basis_note": (
            _clean_text(raw_basis, 500)
            if raw_basis and canonical_basis is None
            else _clean_text(value.get("basis_note"), 500)
        ),
    }

    per_serving_values = {}
    whole_recipe_values = {}
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

        def source_number(source):
            if not isinstance(source, dict):
                return None
            for alias in aliases_for_key:
                if alias in source and source.get(alias) not in (None, ""):
                    return _number(source.get(alias), label)
            return None

        per_number = source_number(per_serving)
        whole_number = source_number(whole_recipe)
        if per_number is not None:
            per_serving_values[key] = per_number
        if whole_number is not None:
            whole_recipe_values[key] = whole_number

        number = source_number(numeric_source)
        if number is None and numeric_source is not value:
            number = source_number(value)

        result[key] = number
        if number is not None:
            any_value = True

    if per_serving_values:
        result["per_serving_values"] = per_serving_values
    if whole_recipe_values:
        result["whole_recipe_values"] = whole_recipe_values

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

    source_name = (
        source.get("name")
        or source.get("label")
        or (
            "ChatGPT"
            if str(source.get("type") or "").strip().casefold() == "chatgpt"
            else ""
        )
    )
    result["source"] = {
        "name": _clean_text(source_name, 200),
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

    explicit_per_serving = normalized.get("per_serving_values") or {}
    explicit_whole_recipe = normalized.get("whole_recipe_values") or {}

    rows = []
    for key, label, unit in NUTRITION_FIELDS:
        value = normalized.get(key)
        per_serving = explicit_per_serving.get(key)
        whole = explicit_whole_recipe.get(key)

        if per_serving is None and whole is None and value is None:
            continue

        if per_serving is None:
            if normalized["basis"] == "per_serving" and value is not None:
                per_serving = float(value)
            elif whole is not None:
                per_serving = float(whole) / servings
            elif value is not None:
                per_serving = float(value) / servings

        if whole is None:
            if normalized["basis"] == "whole_recipe" and value is not None:
                whole = float(value)
            elif per_serving is not None:
                whole = float(per_serving) * servings
            elif value is not None:
                whole = float(value) * servings

        rows.append(
            {
                "key": key,
                "label": label,
                "unit": unit,
                "per_serving": float(per_serving),
                "whole_recipe": float(whole),
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
