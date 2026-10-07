"""Conversion des mesures et estimation nutritionnelle des recettes."""
from __future__ import annotations

from fractions import Fraction
import re
import unicodedata

from recipes_food_catalog import get_food, match_food


NUTRIENT_KEYS = (
    "calories_kcal",
    "protein_g",
    "carbohydrates_g",
    "sugars_g",
    "fiber_g",
    "fat_g",
    "saturated_fat_g",
    "sodium_mg",
    "cholesterol_mg",
)

VOLUME_ML = {
    "ml": 1.0,
    "millilitre": 1.0,
    "millilitres": 1.0,
    "l": 1000.0,
    "litre": 1000.0,
    "litres": 1000.0,
    "tasse": 236.588,
    "tasses": 236.588,
    "cup": 236.588,
    "cups": 236.588,
    "c a soupe": 14.7868,
    "c soupe": 14.7868,
    "cuillere a soupe": 14.7868,
    "cuilleres a soupe": 14.7868,
    "tbsp": 14.7868,
    "c a table": 14.7868,
    "c table": 14.7868,
    "c a the": 4.92892,
    "c the": 4.92892,
    "cuillere a the": 4.92892,
    "cuilleres a the": 4.92892,
    "tsp": 4.92892,
}

MASS_G = {
    "g": 1.0,
    "gr": 1.0,
    "gramme": 1.0,
    "grammes": 1.0,
    "kg": 1000.0,
    "kilogramme": 1000.0,
    "kilogrammes": 1000.0,
    "mg": 0.001,
    "oz": 28.3495,
    "once": 28.3495,
    "onces": 28.3495,
    "lb": 453.592,
    "lbs": 453.592,
    "livre": 453.592,
    "livres": 453.592,
}

UNICODE_FRACTIONS = {
    "½": "1/2",
    "⅓": "1/3",
    "⅔": "2/3",
    "¼": "1/4",
    "¾": "3/4",
    "⅕": "1/5",
    "⅖": "2/5",
    "⅗": "3/5",
    "⅘": "4/5",
    "⅛": "1/8",
    "⅜": "3/8",
    "⅝": "5/8",
    "⅞": "7/8",
}


def _fold(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().replace("œ", "oe")
    text = (
        text.replace("c. à soupe", "c a soupe")
        .replace("c. a soupe", "c a soupe")
        .replace("c à soupe", "c a soupe")
        .replace("c. à table", "c a table")
        .replace("c. a table", "c a table")
        .replace("c à table", "c a table")
        .replace("c. à thé", "c a the")
        .replace("c. a the", "c a the")
        .replace("c à thé", "c a the")
    )
    text = re.sub(r"[(),;]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_number(value):
    text = str(value or "").strip()
    if not text:
        return None
    for symbol, replacement in UNICODE_FRACTIONS.items():
        text = text.replace(symbol, " " + replacement)
    text = text.replace(",", ".")
    text = re.sub(r"\s+", " ", text).strip()

    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return float(text)
    if re.fullmatch(r"\d+\s+\d+/\d+", text):
        whole, fraction = text.split(" ", 1)
        return float(int(whole) + Fraction(fraction))
    if re.fullmatch(r"\d+/\d+", text):
        return float(Fraction(text))
    return None


def _number_pattern():
    return (
        r"(?:\d+(?:[.,]\d+)?\s+\d+/\d+|"
        r"\d+/\d+|\d+(?:[.,]\d+)?|"
        r"\d+\s*[½⅓⅔¼¾⅕⅖⅗⅘⅛⅜⅝⅞]|"
        r"[½⅓⅔¼¾⅕⅖⅗⅘⅛⅜⅝⅞])"
    )


def parse_measurement(note, fallback_quantity=1):
    """Extrait la quantité/unité culinaire conservée dans la note."""
    original = str(note or "").strip()
    folded = _fold(original)

    if not folded:
        try:
            quantity = float(fallback_quantity or 1)
        except (TypeError, ValueError):
            quantity = 1.0
        return {
            "original": original,
            "amount": quantity,
            "unit": "unite",
            "kind": "count",
        }

    explicit = re.search(
        rf"({_number_pattern()})\s*(kg|g|gr|grammes?|mg|oz|onces?|lbs?|livres?)\b",
        folded,
    )
    if explicit:
        amount = parse_number(explicit.group(1))
        unit = explicit.group(2)
        if amount is not None:
            return {
                "original": original,
                "amount": amount,
                "unit": unit,
                "kind": "mass",
            }

    match = re.match(rf"^\s*({_number_pattern()})\s*(.*)$", folded)
    if not match:
        return {
            "original": original,
            "amount": None,
            "unit": "",
            "kind": "unknown",
        }

    amount = parse_number(match.group(1))
    unit_text = match.group(2).strip()
    unit_text = re.split(r"\s+[—-]\s+", unit_text, maxsplit=1)[0]
    unit_text = re.sub(
        r"\b(environ|approx|approximativement)\b",
        "",
        unit_text,
    ).strip()

    known_units = sorted(
        set(MASS_G) | set(VOLUME_ML),
        key=len,
        reverse=True,
    )
    for unit in known_units:
        if unit_text == unit or unit_text.startswith(unit + " "):
            return {
                "original": original,
                "amount": amount,
                "unit": unit,
                "kind": "mass" if unit in MASS_G else "volume",
            }

    return {
        "original": original,
        "amount": amount,
        "unit": unit_text or "unite",
        "kind": "count",
    }


def grams_from_measurement(measurement, food_key):
    profile = get_food(food_key)
    if not profile:
        return None, "Aliment non reconnu"

    amount = measurement.get("amount")
    if amount is None:
        return None, "Quantité non reconnue"

    unit = str(measurement.get("unit") or "").strip()
    if unit in MASS_G:
        return round(float(amount) * MASS_G[unit], 1), "Poids indiqué"

    if unit in VOLUME_ML:
        density = profile.get("density_g_ml")
        if density is None:
            return None, "Densité non disponible"
        grams = float(amount) * VOLUME_ML[unit] * float(density)
        return round(grams, 1), "Conversion selon l’ingrédient"

    piece_g = profile.get("piece_g")
    if piece_g is not None:
        return (
            round(float(amount) * float(piece_g), 1),
            "Poids moyen par unité",
        )

    return None, "Mesure non convertible"


def analyze_ingredient(ingredient, saved=None):
    saved = saved or {}
    ingredient_id = int(ingredient.get("id") or 0)
    name = str(ingredient.get("name") or "").strip()
    note = str(ingredient.get("note") or "").strip()

    food_key = str(saved.get("food_key") or "").strip() or match_food(name)
    measurement = parse_measurement(
        note,
        fallback_quantity=ingredient.get("quantity", 1),
    )

    saved_grams = saved.get("grams")
    grams = None
    source = ""
    metric_source = str(saved.get("source") or "auto")

    if saved_grams not in (None, ""):
        try:
            grams = max(0.0, float(saved_grams))
            source = (
                "Poids enregistré"
                if metric_source == "manual"
                else "Conversion enregistrée"
            )
        except (TypeError, ValueError):
            grams = None

    if grams is None and food_key:
        grams, source = grams_from_measurement(measurement, food_key)

    return {
        "ingredient_id": ingredient_id,
        "name": name,
        "note": note,
        "measurement": measurement,
        "food_key": food_key,
        "grams": grams,
        "source": source,
        "metric_source": metric_source,
        "is_free": bool(ingredient.get("is_free")),
    }


def analyze_recipe_ingredients(ingredients, saved_metrics=None):
    saved_metrics = saved_metrics or {}
    by_name = {
        str(row.get("name_key") or ""): row
        for row in saved_metrics.values()
        if isinstance(row, dict) and row.get("name_key")
    }
    result = []
    for ingredient in ingredients or []:
        ingredient_id = str(int(ingredient.get("id") or 0))
        saved = saved_metrics.get(ingredient_id)
        if not saved:
            saved = by_name.get(_fold(ingredient.get("name"))) or {}
        result.append(analyze_ingredient(ingredient, saved))
    return result


def serialize_metrics(rows):
    result = {}
    for row in rows or []:
        ingredient_id = int(row.get("ingredient_id") or 0)
        grams = row.get("grams")
        food_key = str(row.get("food_key") or "").strip()
        if ingredient_id <= 0:
            continue
        if grams in (None, "") and not food_key:
            continue
        try:
            grams_value = (
                None
                if grams in (None, "")
                else round(max(0.0, float(grams)), 2)
            )
        except (TypeError, ValueError):
            grams_value = None
        result[str(ingredient_id)] = {
            "grams": grams_value,
            "food_key": food_key,
            "source": str(row.get("metric_source") or "auto"),
            "name_key": _fold(row.get("name")),
        }
    return result


def build_nutrition_estimate(rows, servings):
    totals = {key: 0.0 for key in NUTRIENT_KEYS}
    used = 0
    skipped = []

    for row in rows or []:
        food = get_food(row.get("food_key"))
        grams = row.get("grams")
        if not food or grams in (None, ""):
            skipped.append(str(row.get("name") or "Ingrédient"))
            continue
        try:
            grams = float(grams)
        except (TypeError, ValueError):
            skipped.append(str(row.get("name") or "Ingrédient"))
            continue
        if grams < 0:
            skipped.append(str(row.get("name") or "Ingrédient"))
            continue

        factor = grams / 100.0
        for key in NUTRIENT_KEYS:
            totals[key] += float(food["nutrition"].get(key) or 0) * factor
        used += 1

    try:
        portions = max(1, int(servings or 1))
    except (TypeError, ValueError):
        portions = 1

    nutrition = {
        "basis": "whole_recipe",
        "estimated": True,
        "serving_size": f"1 portion (1/{portions} de la recette)",
        "basis_note": (
            "Estimation JF Apps calculée à partir de poids convertis et "
            "de valeurs nutritionnelles génériques moyennes."
        ),
        "notes": [],
    }
    for key, value in totals.items():
        nutrition[key] = round(value, 2)

    if skipped:
        nutrition["notes"].append(
            f"{len(skipped)} ingrédient(s) non inclus dans le calcul : "
            + ", ".join(skipped[:8])
            + ("…" if len(skipped) > 8 else "")
        )

    nutrition["notes"].append(
        "Les marques, recettes commerciales, méthodes de cuisson et portions "
        "réelles peuvent modifier les valeurs."
    )

    return {
        "nutrition": nutrition,
        "used_count": used,
        "skipped_count": len(skipped),
        "skipped_names": skipped,
    }


def metric_label(metrics, ingredient_id, ingredient_name=""):
    metrics = metrics or {}
    row = metrics.get(str(int(ingredient_id or 0))) or {}
    if not row and ingredient_name:
        wanted = _fold(ingredient_name)
        row = next(
            (
                value
                for value in metrics.values()
                if isinstance(value, dict)
                and str(value.get("name_key") or "") == wanted
            ),
            {},
        )
    grams = row.get("grams")
    if grams in (None, ""):
        return ""
    try:
        value = float(grams)
    except (TypeError, ValueError):
        return ""
    if abs(value - round(value)) < 0.05:
        text = str(int(round(value)))
    else:
        text = f"{value:.1f}".replace(".", ",")
    return f"≈ {text} g"
