from __future__ import annotations

import json
import re
import unicodedata

from recipes_extras import normalize_nutrition, normalize_recipe_extra


IMPORT_FORMAT = "jf_apps_recipe_import"
IMPORT_VERSION = 1


def _fold(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text.casefold()).strip()


def normalize_name(value):
    text = _fold(value)
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value, limit):
    return str(value or "").strip()[:limit]


def _positive_int(value, label, default):
    if value in (None, ""):
        return default
    try:
        number = int(float(value))
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} doit être un nombre entier.") from error
    if number < 1:
        raise ValueError(f"{label} doit être d’au moins 1.")
    return number


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


def _ingredient_note(entry):
    amount = _clean_text(
        entry.get("quantity", entry.get("amount", "")),
        60,
    )
    unit = _clean_text(entry.get("unit"), 60)
    note = _clean_text(
        entry.get("note", entry.get("precision", "")),
        500,
    )
    first = " ".join(part for part in (amount, unit) if part).strip()
    if first and note:
        return f"{first} — {note}"
    return first or note


def _ingredient_kind(entry):
    if not isinstance(entry, dict):
        return "auto"

    if "grocery_item" in entry:
        raw = entry.get("grocery_item")
        if isinstance(raw, str):
            enabled = raw.strip().casefold() not in {
                "",
                "0",
                "false",
                "faux",
                "no",
                "non",
            }
        else:
            enabled = bool(raw)
        return "grocery" if enabled else "free"

    raw = str(
        entry.get(
            "kind",
            entry.get(
                "ingredient_type",
                entry.get("type", ""),
            ),
        )
        or ""
    ).strip().casefold()

    aliases = {
        "free": "free",
        "generic": "free",
        "générique": "free",
        "generique": "free",
        "libre": "free",
        "recipe_only": "free",
        "grocery": "grocery",
        "grocery_item": "grocery",
        "item": "grocery",
        "epicerie": "grocery",
        "épicerie": "grocery",
        "auto": "auto",
        "": "auto",
    }
    return aliases.get(raw, "auto")


def _normalize_ingredients(value):
    if not isinstance(value, list):
        raise ValueError("La liste des ingrédients est invalide.")

    rows = []
    for index, entry in enumerate(value, start=1):
        if isinstance(entry, str):
            name = _clean_text(entry, 180)
            if not name:
                continue
            rows.append(
                {
                    "name": name,
                    "quantity": "",
                    "unit": "",
                    "note": "",
                    "order": index,
                    "display_note": "",
                    "kind": "auto",
                }
            )
            continue

        if not isinstance(entry, dict):
            raise ValueError(
                f"L’ingrédient no {index} est invalide."
            )

        name = _clean_text(
            entry.get("name", entry.get("item_name")),
            180,
        )
        if not name:
            raise ValueError(
                f"L’ingrédient no {index} n’a pas de nom."
            )
        try:
            order = int(entry.get("order", index) or index)
        except (TypeError, ValueError):
            order = index

        quantity = _clean_text(
            entry.get("quantity", entry.get("amount", "")),
            60,
        )
        unit = _clean_text(entry.get("unit"), 60)
        note = _clean_text(
            entry.get("note", entry.get("precision", "")),
            500,
        )

        rows.append(
            {
                "name": name,
                "quantity": quantity,
                "unit": unit,
                "note": note,
                "order": order,
                "display_note": _ingredient_note(entry),
                "kind": _ingredient_kind(entry),
            }
        )

    rows.sort(key=lambda row: (row["order"], normalize_name(row["name"])))
    return rows


def _normalize_steps(value):
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError("La liste des étapes est invalide.")

    rows = []
    for index, entry in enumerate(value, start=1):
        if isinstance(entry, str):
            text = _clean_text(entry, 3000)
            order = index
        elif isinstance(entry, dict):
            text = _clean_text(
                entry.get("text", entry.get("instruction")),
                3000,
            )
            try:
                order = int(entry.get("order", index) or index)
            except (TypeError, ValueError):
                order = index
        else:
            raise ValueError(f"L’étape no {index} est invalide.")

        if text:
            rows.append({"order": order, "text": text})

    rows.sort(key=lambda row: row["order"])
    return rows


def _normalize_tags(value):
    if value in (None, ""):
        return []
    if isinstance(value, str):
        values = re.split(r"[,;\n]+", value)
    elif isinstance(value, list):
        values = value
    else:
        raise ValueError("Les étiquettes sont invalides.")

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


def parse_recipe_import(value):
    if isinstance(value, (bytes, bytearray, memoryview)):
        value = bytes(value).decode("utf-8-sig", errors="strict")
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise ValueError("Collez ou choisissez un fichier JSON.")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Le JSON est invalide près de la ligne {error.lineno}."
            ) from error
    elif isinstance(value, dict):
        data = value
    else:
        raise ValueError("Le contenu d’import est invalide.")

    if not isinstance(data, dict):
        raise ValueError("Le fichier JSON doit contenir un objet.")

    format_name = str(
        data.get("format", data.get("schema", ""))
    ).strip()
    version = data.get("version")

    if format_name != IMPORT_FORMAT:
        raise ValueError(
            f"Format attendu : {IMPORT_FORMAT}."
        )
    try:
        version = int(version)
    except (TypeError, ValueError) as error:
        raise ValueError("La version du format est invalide.") from error
    if version != IMPORT_VERSION:
        raise ValueError(
            f"Version {version} non prise en charge. "
            f"La version attendue est {IMPORT_VERSION}."
        )

    recipe = data.get("recipe")
    if not isinstance(recipe, dict):
        raise ValueError("La clé « recipe » est absente ou invalide.")

    name = _clean_text(recipe.get("name"), 180)
    if not name:
        raise ValueError("Le nom de la recette est obligatoire.")

    servings = _positive_int(
        recipe.get("servings"),
        "Le nombre de portions",
        4,
    )
    description = _clean_text(recipe.get("description"), 3000)
    category = _clean_text(recipe.get("category"), 120)
    subcategory = _clean_text(recipe.get("subcategory"), 120)
    tags = _normalize_tags(recipe.get("tags", []))
    prep_time = _nonnegative_int(
        recipe.get("prep_time_minutes"),
        "Le temps de préparation",
    )
    cook_time = _nonnegative_int(
        recipe.get("cook_time_minutes"),
        "Le temps de cuisson",
    )

    source = recipe.get("source") or {}
    if isinstance(source, str):
        source = {"name": source, "url": ""}
    if not isinstance(source, dict):
        raise ValueError("La source de la recette est invalide.")

    source_name = (
        source.get("name")
        or source.get("label")
        or (
            "ChatGPT"
            if str(source.get("type") or "").strip().casefold() == "chatgpt"
            else ""
        )
    )
    source = {
        "name": _clean_text(source_name, 200),
        "url": _clean_text(source.get("url"), 1000),
    }

    ingredients = _normalize_ingredients(recipe.get("ingredients", []))
    steps = _normalize_steps(
        recipe.get("steps", recipe.get("instructions", []))
    )

    if not ingredients:
        raise ValueError(
            "La recette importée doit contenir au moins un ingrédient."
        )
    if not steps:
        raise ValueError(
            "La recette importée doit contenir au moins une étape."
        )

    nutrition = normalize_nutrition(recipe.get("nutrition"))

    extra = normalize_recipe_extra(
        {
            "prep_time_minutes": prep_time,
            "cook_time_minutes": cook_time,
            "tags": tags,
            "source": source,
            "nutrition": nutrition,
        }
    )

    return {
        "format": IMPORT_FORMAT,
        "version": IMPORT_VERSION,
        "name": name,
        "description": description,
        "servings": servings,
        "category": category,
        "subcategory": subcategory,
        "ingredients": ingredients,
        "steps": steps,
        "instructions": "\n".join(
            row["text"] for row in steps
        ),
        "extra": extra,
    }


def preview_recipe_import(candidate, existing_items, existing_recipes):
    item_keys = {
        normalize_name(row.get("name"))
        for row in existing_items or []
    }
    recipe_keys = {
        normalize_name(row.get("name"))
        for row in existing_recipes or []
    }

    missing = []
    free_ingredients = []
    matched = 0

    for ingredient in candidate.get("ingredients") or []:
        if ingredient.get("kind") == "free":
            free_ingredients.append(
                ingredient.get("name") or "Ingrédient"
            )
            continue

        key = normalize_name(ingredient.get("name"))
        if key and key in item_keys:
            matched += 1
        else:
            missing.append(ingredient.get("name") or "Ingrédient")

    result = dict(candidate)
    result["duplicate"] = (
        normalize_name(candidate.get("name")) in recipe_keys
    )
    result["matched_ingredients"] = matched
    result["free_ingredients"] = free_ingredients
    result["missing_ingredients"] = missing
    return result


def _ensure_recipe_category(cur, family_id, name, parent_id=None):
    clean = _clean_text(name, 120)
    if not clean:
        return None

    cur.execute(
        """
        SELECT id, name
        FROM grocery_recipe_categories
        WHERE family_id = %s
          AND parent_id IS NOT DISTINCT FROM %s
        ORDER BY id;
        """,
        (family_id, parent_id),
    )
    target = normalize_name(clean)
    for row in cur.fetchall():
        if normalize_name(row["name"]) == target:
            return int(row["id"])

    cur.execute(
        """
        SELECT COALESCE(MAX(sort_order), 0) + 10 AS next_order
        FROM grocery_recipe_categories
        WHERE family_id = %s
          AND parent_id IS NOT DISTINCT FROM %s;
        """,
        (family_id, parent_id),
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
        (family_id, parent_id, clean, sort_order),
    )
    return int(cur.fetchone()["id"])


def _recipe_category_id(cur, family_id, candidate):
    category = candidate.get("category") or ""
    subcategory = candidate.get("subcategory") or ""
    if not category:
        return None
    parent_id = _ensure_recipe_category(
        cur,
        family_id,
        category,
        None,
    )
    if subcategory:
        return _ensure_recipe_category(
            cur,
            family_id,
            subcategory,
            parent_id,
        )
    return parent_id


def import_recipe_candidate(
    user_id,
    family_id,
    candidate,
    *,
    category_id,
    store_id=None,
    create_missing_items=True,
):
    import db as _db
    from grocery_common import log_activity

    if not isinstance(candidate, dict):
        raise ValueError("La recette analysée est invalide.")

    normalized = parse_recipe_import(
        {
            "format": IMPORT_FORMAT,
            "version": IMPORT_VERSION,
            "recipe": {
                "name": candidate.get("name"),
                "description": candidate.get("description"),
                "servings": candidate.get("servings"),
                "category": candidate.get("category"),
                "subcategory": candidate.get("subcategory"),
                "tags": (candidate.get("extra") or {}).get("tags", []),
                "prep_time_minutes": (
                    candidate.get("extra") or {}
                ).get("prep_time_minutes"),
                "cook_time_minutes": (
                    candidate.get("extra") or {}
                ).get("cook_time_minutes"),
                "source": (candidate.get("extra") or {}).get("source", {}),
                "nutrition": (
                    candidate.get("extra") or {}
                ).get("nutrition"),
                "ingredients": candidate.get("ingredients", []),
                "steps": candidate.get("steps", []),
            },
        }
    )

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)

            cur.execute(
                """
                SELECT id, name
                FROM grocery_recipes
                WHERE family_id = %s;
                """,
                (family_id,),
            )
            existing_recipe_names = {
                normalize_name(row["name"])
                for row in cur.fetchall()
            }
            if normalize_name(normalized["name"]) in existing_recipe_names:
                raise ValueError(
                    f"La recette « {normalized['name']} » existe déjà."
                )

            if create_missing_items:
                cur.execute(
                    """
                    SELECT id
                    FROM categories
                    WHERE id = %s
                      AND family_id = %s
                      AND deleted_at IS NULL;
                    """,
                    (category_id, family_id),
                )
                if cur.fetchone() is None:
                    raise ValueError(
                        "Choisissez une catégorie d’épicerie valide "
                        "pour les nouveaux items."
                    )

            if store_id is None:
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
                store = cur.fetchone()
                store_id = int(store["id"]) if store else None
            else:
                cur.execute(
                    """
                    SELECT id
                    FROM stores
                    WHERE id = %s
                      AND family_id = %s
                      AND deleted_at IS NULL;
                    """,
                    (store_id, family_id),
                )
                if cur.fetchone() is None:
                    raise ValueError(
                        "Choisissez un magasin d’épicerie valide."
                    )

            cur.execute(
                """
                SELECT id, name
                FROM items
                WHERE family_id = %s
                  AND deleted_at IS NULL;
                """,
                (family_id,),
            )
            item_map = {
                normalize_name(row["name"]): int(row["id"])
                for row in cur.fetchall()
            }

            recipe_category_id = _recipe_category_id(
                cur,
                family_id,
                normalized,
            )
            extra_json = json.dumps(
                normalized["extra"],
                ensure_ascii=False,
            )

            cur.execute(
                """
                INSERT INTO grocery_recipes (
                    family_id,
                    recipe_category_id,
                    name,
                    description,
                    instructions,
                    servings,
                    recipe_extra,
                    created_by_user_id
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s::jsonb, %s
                )
                RETURNING id;
                """,
                (
                    family_id,
                    recipe_category_id,
                    normalized["name"],
                    normalized["description"],
                    normalized["instructions"],
                    normalized["servings"],
                    extra_json,
                    user_id,
                ),
            )
            recipe_id = int(cur.fetchone()["id"])

            created_items = 0
            reused_items = 0
            skipped_ingredients = 0
            linked_ingredients = 0
            free_ingredients = 0
            seen_item_ids = set()

            for position, ingredient in enumerate(
                normalized["ingredients"],
                start=1,
            ):
                ingredient_kind = ingredient.get("kind") or "auto"
                key = normalize_name(ingredient["name"])
                item_id = (
                    None
                    if ingredient_kind == "free"
                    else item_map.get(key)
                )

                if (
                    item_id is None
                    and ingredient_kind != "free"
                    and create_missing_items
                ):
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
                            %s, %s, %s, %s, '', 1, 0, 0, NULL
                        )
                        RETURNING id;
                        """,
                        (
                            family_id,
                            category_id,
                            store_id,
                            ingredient["name"],
                        ),
                    )
                    item_id = int(cur.fetchone()["id"])
                    item_map[key] = item_id
                    created_items += 1
                elif item_id is not None:
                    reused_items += 1

                if item_id is None:
                    cur.execute(
                        """
                        INSERT INTO grocery_recipe_ingredients (
                            recipe_id,
                            item_id,
                            free_name,
                            quantity,
                            note,
                            sort_order
                        )
                        VALUES (%s, NULL, %s, 1, %s, %s);
                        """,
                        (
                            recipe_id,
                            ingredient["name"],
                            ingredient["display_note"],
                            position * 10,
                        ),
                    )
                    free_ingredients += 1
                    continue

                if item_id in seen_item_ids:
                    skipped_ingredients += 1
                    continue
                seen_item_ids.add(item_id)

                cur.execute(
                    """
                    INSERT INTO grocery_recipe_ingredients (
                        recipe_id,
                        item_id,
                        quantity,
                        note,
                        sort_order
                    )
                    VALUES (%s, %s, 1, %s, %s);
                    """,
                    (
                        recipe_id,
                        item_id,
                        ingredient["display_note"],
                        position * 10,
                    ),
                )
                linked_ingredients += 1

            log_activity(
                cur,
                family_id,
                user_id,
                "recipe_created",
                "recipe",
                recipe_id,
                normalized["name"],
                {
                    "source": "chatgpt_json_import",
                    "created_items": created_items,
                    "reused_items": reused_items,
                    "free_ingredients": free_ingredients,
                    "nutrition": bool(
                        normalized["extra"].get("nutrition")
                    ),
                },
            )
            conn.commit()

    return {
        "recipe_id": recipe_id,
        "name": normalized["name"],
        "items_created": created_items,
        "items_reused": reused_items,
        "ingredients_linked": linked_ingredients,
        "free_ingredients": free_ingredients,
        "ingredients_skipped": skipped_ingredients,
        "nutrition_imported": bool(
            normalized["extra"].get("nutrition")
        ),
    }


def example_import_payload():
    return {
        "format": IMPORT_FORMAT,
        "version": IMPORT_VERSION,
        "recipe": {
            "name": "Nom de la recette",
            "description": "Courte description",
            "servings": 4,
            "category": "Desserts",
            "subcategory": "",
            "tags": ["congélation", "dessert"],
            "prep_time_minutes": 20,
            "cook_time_minutes": 30,
            "ingredients": [
                {
                    "name": "Farine",
                    "quantity": 1.5,
                    "unit": "tasse",
                    "note": "",
                    "order": 1,
                    "kind": "grocery",
                },
                {
                    "name": "Fines herbes au choix",
                    "quantity": "",
                    "unit": "",
                    "note": "au goût",
                    "order": 2,
                    "kind": "free",
                },
            ],
            "steps": [
                {"order": 1, "text": "Préchauffer le four."}
            ],
            "source": {
                "name": "ChatGPT",
                "url": "",
            },
            "nutrition": {
                "basis": "per_serving",
                "estimated": True,
                "calories_kcal": 285,
                "protein_g": 8.5,
                "carbohydrates_g": 31.2,
                "sugars_g": 14.7,
                "fiber_g": 4.1,
                "fat_g": 15.3,
                "saturated_fat_g": 6.2,
                "sodium_mg": 210,
                "cholesterol_mg": 42,
            },
        },
    }
