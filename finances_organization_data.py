from __future__ import annotations

from datetime import date
import unicodedata

def ensure_default_finance_categories(user_id, *, get_connection):
    defaults = [
        ("Alimentation", "expense"),
        ("Transport", "expense"),
        ("Maison", "expense"),
        ("Santé", "expense"),
        ("Loisirs", "expense"),
        ("Autres dépenses", "expense"),
        ("Salaire", "income"),
        ("Remboursement", "income"),
        ("Autres revenus", "income"),
    ]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS total FROM finance_categories WHERE user_id=%s;",
                (user_id,),
            )
            if int(cur.fetchone()["total"]) == 0:
                for name, category_type in defaults:
                    cur.execute("""
                        INSERT INTO finance_categories (user_id, name, category_type)
                        VALUES (%s, %s, %s);
                    """, (user_id, name, category_type))
                conn.commit()


def list_categories(user_id, include_inactive=False, *, get_connection):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    child.*,
                    parent.name AS parent_name,
                    CASE WHEN parent.id IS NULL
                         THEN child.name
                         ELSE parent.name || ' › ' || child.name
                    END AS full_name
                FROM finance_categories child
                LEFT JOIN finance_categories parent ON parent.id=child.parent_id
                WHERE child.user_id=%s
                  AND (%s OR child.is_active=TRUE)
                ORDER BY COALESCE(parent.name, child.name),
                         CASE WHEN parent.id IS NULL THEN 0 ELSE 1 END,
                         child.name;
            """, (user_id, include_inactive))
            return cur.fetchall()


def save_category(user_id, name, parent_id=None, category_type="both", category_id=None, *, get_connection, _text):
    name = _text(name, "Le nom", 100, True)
    if category_type not in {"expense", "income", "both"}:
        raise ValueError("Type de catégorie invalide.")
    with get_connection() as conn:
        with conn.cursor() as cur:
            if parent_id:
                cur.execute(
                    "SELECT id,parent_id FROM finance_categories WHERE id=%s AND user_id=%s;",
                    (parent_id, user_id),
                )
                parent = cur.fetchone()
                if not parent or parent["parent_id"] is not None:
                    raise ValueError("La catégorie parente est invalide.")
            if category_id:
                cur.execute("""
                    UPDATE finance_categories
                    SET name=%s,parent_id=%s,category_type=%s,updated_at=NOW()
                    WHERE id=%s AND user_id=%s;
                """, (name, parent_id, category_type, category_id, user_id))
            else:
                cur.execute("""
                    INSERT INTO finance_categories
                        (user_id,parent_id,name,category_type)
                    VALUES (%s,%s,%s,%s);
                """, (user_id, parent_id, name, category_type))
            conn.commit()


def toggle_category(user_id, category_id, is_active, *, get_connection):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE finance_categories SET is_active=%s,updated_at=NOW()
                WHERE id=%s AND user_id=%s;
            """, (bool(is_active), category_id, user_id))
            conn.commit()


def set_category_dashboard_visible(user_id, category_id, is_visible, *, get_connection):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE finance_categories
                SET dashboard_visible=%s, updated_at=NOW()
                WHERE id=%s AND user_id=%s;
                """,
                (bool(is_visible), category_id, user_id),
            )
            if cur.rowcount == 0:
                raise ValueError("Catégorie introuvable.")
            conn.commit()


def list_tags(user_id, include_inactive=False, *, get_connection):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM finance_tags
                WHERE user_id=%s AND (%s OR is_active=TRUE)
                ORDER BY name;
            """, (user_id, include_inactive))
            return cur.fetchall()


def save_tag(user_id, name, tag_id=None, *, get_connection, _text):
    name = _text(name, "Le nom", 80, True)
    with get_connection() as conn:
        with conn.cursor() as cur:
            if tag_id:
                cur.execute("""
                    UPDATE finance_tags SET name=%s,updated_at=NOW()
                    WHERE id=%s AND user_id=%s;
                """, (name, tag_id, user_id))
            else:
                cur.execute(
                    "INSERT INTO finance_tags (user_id,name) VALUES (%s,%s);",
                    (user_id, name),
                )
            conn.commit()




def _normalized_lookup_name(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )
    return " ".join(text.casefold().split())


def get_or_create_finance_category(
    user_id,
    name,
    *,
    parent_id=None,
    category_type="both",
    _text,
    _normalized_lookup_name,
    list_categories,
    toggle_category,
    save_category,
):
    """Crée une catégorie depuis la saisie rapide ou réutilise un doublon évident."""

    normalized_name = _normalized_lookup_name(
        _text(name, "Le nom", 100, True)
    )
    normalized_parent = (
        int(parent_id)
        if parent_id not in (None, "")
        else None
    )

    for row in list_categories(
        user_id,
        include_inactive=True,
    ):
        row_parent = (
            int(row["parent_id"])
            if row.get("parent_id") is not None
            else None
        )
        if (
            row_parent == normalized_parent
            and _normalized_lookup_name(row["name"])
            == normalized_name
        ):
            category_id = int(row["id"])
            if not row.get("is_active", True):
                toggle_category(
                    user_id,
                    category_id,
                    True,
                )
            return {
                "id": category_id,
                "created": False,
                "name": row["name"],
                "full_name": row["full_name"],
            }

    save_category(
        user_id,
        name,
        parent_id=normalized_parent,
        category_type=category_type,
    )

    for row in list_categories(
        user_id,
        include_inactive=True,
    ):
        row_parent = (
            int(row["parent_id"])
            if row.get("parent_id") is not None
            else None
        )
        if (
            row_parent == normalized_parent
            and _normalized_lookup_name(row["name"])
            == normalized_name
        ):
            return {
                "id": int(row["id"]),
                "created": True,
                "name": row["name"],
                "full_name": row["full_name"],
            }

    raise RuntimeError(
        "La catégorie a été créée, mais elle n’a pas pu être relue."
    )


def get_or_create_finance_tag(
    user_id,
    name,
    *,
    _text,
    _normalized_lookup_name,
    list_tags,
    toggle_tag,
    save_tag,
):
    """Crée une étiquette depuis la saisie rapide ou réutilise un doublon évident."""

    normalized_name = _normalized_lookup_name(
        _text(name, "Le nom", 80, True)
    )

    for row in list_tags(
        user_id,
        include_inactive=True,
    ):
        if (
            _normalized_lookup_name(row["name"])
            == normalized_name
        ):
            tag_id = int(row["id"])
            if not row.get("is_active", True):
                toggle_tag(
                    user_id,
                    tag_id,
                    True,
                )
            return {
                "id": tag_id,
                "created": False,
                "name": row["name"],
            }

    save_tag(
        user_id,
        name,
    )

    for row in list_tags(
        user_id,
        include_inactive=True,
    ):
        if (
            _normalized_lookup_name(row["name"])
            == normalized_name
        ):
            return {
                "id": int(row["id"]),
                "created": True,
                "name": row["name"],
            }

    raise RuntimeError(
        "L’étiquette a été créée, mais elle n’a pas pu être relue."
    )


def toggle_tag(user_id, tag_id, is_active):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE finance_tags SET is_active=%s,updated_at=NOW()
                WHERE id=%s AND user_id=%s;
            """, (bool(is_active), tag_id, user_id))
            conn.commit()


def set_tag_dashboard_visible(user_id, tag_id, is_visible):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE finance_tags
                SET dashboard_visible=%s, updated_at=NOW()
                WHERE id=%s AND user_id=%s;
                """,
                (bool(is_visible), tag_id, user_id),
            )
            if cur.rowcount == 0:
                raise ValueError("Étiquette introuvable.")
            conn.commit()


def ensure_default_finance_payment_methods(
    user_id,
    *,
    get_connection,
    DEFAULT_PAYMENT_METHODS,
    DEFAULT_PAYMENT_METHOD_TYPES,
):
    """Crée les modes de paiement initiaux pour un nouvel utilisateur."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS total
                FROM finance_payment_methods
                WHERE user_id = %s;
                """,
                (user_id,),
            )
            if int(cur.fetchone()["total"]) > 0:
                return

            for sort_order, name in enumerate(
                DEFAULT_PAYMENT_METHODS,
                start=1,
            ):
                cur.execute(
                    """
                    INSERT INTO finance_payment_methods (
                        user_id,
                        name,
                        sort_order,
                        method_type
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (
                        user_id,
                        name,
                        sort_order,
                        DEFAULT_PAYMENT_METHOD_TYPES.get(
                            name,
                            "other",
                        ),
                    ),
                )

            conn.commit()


def _optional_day(value, label):
    if value in (None, ""):
        return None
    day = int(value)
    if day < 1 or day > 31:
        raise ValueError(f"{label} doit être entre 1 et 31.")
    return day


def list_payment_methods(
    user_id,
    include_inactive=False,
    *,
    get_connection,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    method.id,
                    method.name,
                    method.sort_order,
                    method.is_active,
                    method.method_type,
                    method.statement_day,
                    method.payment_day,
                    method.opening_balance,
                    method.opening_balance_date,
                    method.opening_balance_reconciled,
                    method.credit_limit,
                    method.note,
                    COUNT(transaction.id) AS transaction_count
                FROM finance_payment_methods AS method
                LEFT JOIN finance_transactions AS transaction
                    ON transaction.payment_method_id = method.id
                   AND transaction.user_id = method.user_id
                WHERE method.user_id = %s
                  AND (%s OR method.is_active = TRUE)
                GROUP BY method.id
                ORDER BY
                    method.is_active DESC,
                    method.sort_order,
                    LOWER(method.name),
                    method.id;
                """,
                (user_id, include_inactive),
            )
            return cur.fetchall()


def save_payment_method(
    user_id,
    name,
    payment_method_id=None,
    method_type="credit_card",
    statement_day=None,
    payment_day=None,
    opening_balance=0,
    opening_balance_date=None,
    credit_limit=None,
    note=None,
    *,
    get_connection,
    _text,
    _decimal_value,
    _optional_day,
    PAYMENT_METHOD_TYPES,
):
    cleaned_name = _text(
        name,
        "Le nom du mode de paiement",
        100,
        True,
    )
    if method_type not in PAYMENT_METHOD_TYPES:
        raise ValueError("Le type de mode de paiement est invalide.")

    parsed_statement_day = _optional_day(
        statement_day,
        "Le jour de fermeture",
    )
    parsed_payment_day = _optional_day(
        payment_day,
        "Le jour de paiement",
    )
    parsed_opening_balance = _decimal_value(
        opening_balance,
        "Le solde initial",
    )
    parsed_opening_date = (
        opening_balance_date
        if isinstance(opening_balance_date, date)
        else (
            date.fromisoformat(str(opening_balance_date))
            if opening_balance_date
            else None
        )
    )
    parsed_credit_limit = _decimal_value(
        credit_limit,
        "La limite de crédit",
        allow_blank=True,
    )
    if parsed_credit_limit is not None and parsed_credit_limit < 0:
        raise ValueError("La limite de crédit ne peut pas être négative.")
    if method_type != "credit_line":
        parsed_credit_limit = None
    if method_type == "credit_line" and parsed_opening_balance < 0:
        raise ValueError("Le solde utilisé d’une marge ne peut pas être négatif.")
    cleaned_note = _text(
        note,
        "La note",
        1000,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            params = [user_id, cleaned_name]
            duplicate_sql = """
                SELECT id
                FROM finance_payment_methods
                WHERE user_id = %s
                  AND LOWER(name) = LOWER(%s)
            """
            if payment_method_id:
                duplicate_sql += " AND id <> %s"
                params.append(payment_method_id)
            duplicate_sql += " LIMIT 1;"
            cur.execute(duplicate_sql, params)
            if cur.fetchone():
                raise ValueError(
                    "Un mode de paiement porte déjà ce nom."
                )

            if payment_method_id:
                cur.execute(
                    """
                    UPDATE finance_payment_methods
                    SET
                        name = %s,
                        method_type = %s,
                        statement_day = %s,
                        payment_day = %s,
                        opening_balance_reconciled = CASE
                            WHEN opening_balance IS DISTINCT FROM %s
                              OR opening_balance_date IS DISTINCT FROM %s
                            THEN FALSE
                            ELSE opening_balance_reconciled
                        END,
                        opening_balance = %s,
                        opening_balance_date = %s,
                        credit_limit = %s,
                        note = %s,
                        updated_at = NOW()
                    WHERE id = %s
                      AND user_id = %s;
                    """,
                    (
                        cleaned_name,
                        method_type,
                        parsed_statement_day,
                        parsed_payment_day,
                        parsed_opening_balance,
                        parsed_opening_date,
                        parsed_opening_balance,
                        parsed_opening_date,
                        parsed_credit_limit,
                        cleaned_note,
                        payment_method_id,
                        user_id,
                    ),
                )
                if cur.rowcount == 0:
                    raise ValueError(
                        "Mode de paiement introuvable."
                    )
            else:
                cur.execute(
                    """
                    SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_order
                    FROM finance_payment_methods
                    WHERE user_id = %s;
                    """,
                    (user_id,),
                )
                next_order = int(cur.fetchone()["next_order"])
                cur.execute(
                    """
                    INSERT INTO finance_payment_methods (
                        user_id,
                        name,
                        sort_order,
                        method_type,
                        statement_day,
                        payment_day,
                        opening_balance,
                        opening_balance_date,
                        credit_limit,
                        note
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        user_id,
                        cleaned_name,
                        next_order,
                        method_type,
                        parsed_statement_day,
                        parsed_payment_day,
                        parsed_opening_balance,
                        parsed_opening_date,
                        parsed_credit_limit,
                        cleaned_note,
                    ),
                )
            conn.commit()


def toggle_payment_method(
    user_id,
    payment_method_id,
    is_active,
    *,
    get_connection,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE finance_payment_methods
                SET
                    is_active = %s,
                    updated_at = NOW()
                WHERE id = %s
                  AND user_id = %s;
                """,
                (
                    bool(is_active),
                    payment_method_id,
                    user_id,
                ),
            )
            if cur.rowcount == 0:
                raise ValueError(
                    "Mode de paiement introuvable."
                )
            conn.commit()


def move_payment_method(
    user_id,
    payment_method_id,
    direction,
    *,
    get_connection,
):
    if direction not in {
        "up",
        "down",
    }:
        raise ValueError(
            "Direction de déplacement invalide."
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    sort_order
                FROM finance_payment_methods
                WHERE user_id = %s
                ORDER BY
                    sort_order,
                    LOWER(name),
                    id
                FOR UPDATE;
                """,
                (user_id,),
            )
            rows = cur.fetchall()
            ids = [
                int(row["id"])
                for row in rows
            ]

            try:
                index = ids.index(
                    int(payment_method_id)
                )
            except ValueError:
                raise ValueError(
                    "Mode de paiement introuvable."
                )

            target_index = (
                index - 1
                if direction == "up"
                else index + 1
            )

            if (
                target_index < 0
                or target_index >= len(rows)
            ):
                return

            current = rows[index]
            target = rows[target_index]

            current_order = int(
                current["sort_order"]
            )
            target_order = int(
                target["sort_order"]
            )

            if current_order == target_order:
                current_order = index + 1
                target_order = target_index + 1

            cur.execute(
                """
                UPDATE finance_payment_methods
                SET sort_order = %s,
                    updated_at = NOW()
                WHERE id = %s
                  AND user_id = %s;
                """,
                (
                    target_order,
                    current["id"],
                    user_id,
                ),
            )
            cur.execute(
                """
                UPDATE finance_payment_methods
                SET sort_order = %s,
                    updated_at = NOW()
                WHERE id = %s
                  AND user_id = %s;
                """,
                (
                    current_order,
                    target["id"],
                    user_id,
                ),
            )

            conn.commit()
