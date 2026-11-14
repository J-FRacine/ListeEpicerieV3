"""Codes-barres UPC/EAN pour la Liste d'épicerie."""
from __future__ import annotations

import re
import db as _db


GTIN_LENGTHS = {8, 12, 13, 14}


def _valid_gtin_checksum(code):
    digits = [int(value) for value in str(code)]
    check = digits[-1]
    total = 0
    weight = 3
    for digit in reversed(digits[:-1]):
        total += digit * weight
        weight = 1 if weight == 3 else 3
    return (10 - (total % 10)) % 10 == check


def normalize_barcode(value):
    code = re.sub(r"\D", "", str(value or ""))
    if len(code) not in GTIN_LENGTHS:
        raise ValueError(
            "Le code doit contenir 8, 12, 13 ou 14 chiffres "
            "(EAN-8, UPC-A, EAN-13 ou GTIN-14)."
        )
    if not _valid_gtin_checksum(code):
        raise ValueError(
            "Le chiffre de contrôle du code-barres est invalide."
        )
    return code


def get_barcode_match(user_id, family_id, barcode):
    code = normalize_barcode(barcode)
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_family_access(cur, user_id, family_id)

            cur.execute(
                """
                SELECT
                    item.id,
                    item.name,
                    item.quantity,
                    item.needed,
                    item.note,
                    item.barcode,
                    category.name AS category,
                    COALESCE(store.name, 'Sans magasin') AS store
                FROM items AS item
                JOIN categories AS category
                  ON category.id = item.category_id
                 AND category.deleted_at IS NULL
                LEFT JOIN stores AS store
                  ON store.id = item.store_id
                WHERE item.family_id = %s
                  AND item.deleted_at IS NULL
                  AND item.barcode = %s
                ORDER BY item.id
                LIMIT 1;
                """,
                (family_id, code),
            )
            family_item = cur.fetchone()

            cur.execute(
                """
                SELECT
                    barcode,
                    generic_name,
                    brand,
                    format_text,
                    updated_at
                FROM grocery_barcode_catalog
                WHERE barcode = %s;
                """,
                (code,),
            )
            catalog = cur.fetchone()

    return {
        "barcode": code,
        "family_item": (
            dict(family_item)
            if family_item
            else None
        ),
        "catalog": dict(catalog) if catalog else None,
    }


def set_item_barcode(
    user_id,
    item_id,
    barcode,
    *,
    generic_name=None,
    brand=None,
    format_text=None,
):
    raw = str(barcode or "").strip()
    code = normalize_barcode(raw) if raw else None

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT family_id, name
                FROM items
                WHERE id = %s
                  AND deleted_at IS NULL;
                """,
                (item_id,),
            )
            item = cur.fetchone()
            if not item:
                raise ValueError("Cet item n’existe plus.")

            family_id = item["family_id"]
            _db._require_family_access(
                cur,
                user_id,
                family_id,
            )

            if code:
                cur.execute(
                    """
                    SELECT id, name
                    FROM items
                    WHERE family_id = %s
                      AND deleted_at IS NULL
                      AND barcode = %s
                      AND id <> %s
                    LIMIT 1;
                    """,
                    (family_id, code, item_id),
                )
                duplicate = cur.fetchone()
                if duplicate:
                    raise ValueError(
                        "Ce code-barres est déjà associé à "
                        f"« {duplicate['name']} » "
                        "dans cette famille."
                    )

            cur.execute(
                """
                UPDATE items
                SET barcode = %s
                WHERE id = %s;
                """,
                (code, item_id),
            )

            if (
                code
                and str(generic_name or "").strip()
            ):
                cur.execute(
                    """
                    INSERT INTO grocery_barcode_catalog (
                        barcode,
                        generic_name,
                        brand,
                        format_text,
                        contributed_by_user_id
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (barcode)
                    DO UPDATE SET
                        generic_name = CASE
                            WHEN BTRIM(EXCLUDED.generic_name) <> ''
                            THEN EXCLUDED.generic_name
                            ELSE grocery_barcode_catalog.generic_name
                        END,
                        brand = CASE
                            WHEN BTRIM(EXCLUDED.brand) <> ''
                            THEN EXCLUDED.brand
                            ELSE grocery_barcode_catalog.brand
                        END,
                        format_text = CASE
                            WHEN BTRIM(EXCLUDED.format_text) <> ''
                            THEN EXCLUDED.format_text
                            ELSE grocery_barcode_catalog.format_text
                        END,
                        updated_at = NOW();
                    """,
                    (
                        code,
                        str(generic_name or "").strip(),
                        str(brand or "").strip(),
                        str(format_text or "").strip(),
                        user_id,
                    ),
                )

            conn.commit()

    return code
