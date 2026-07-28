from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import csv
import io
import json

from db import get_connection


TRANSACTION_TYPES = {"expense": "Dépense", "income": "Revenu"}
TRANSACTION_STATUSES = {"confirmed": "Confirmée", "planned": "Prévue"}
FREQUENCY_UNITS = {
    "day": "Jour",
    "week": "Semaine",
    "month": "Mois",
    "year": "Année",
}
CONFIRMATION_MODES = {
    "confirm": "À confirmer",
    "automatic": "Création automatique",
}
CARRY_POLICIES = {
    "none": "Aucun report",
    "unused": "Reporter le montant inutilisé",
    "overspend": "Reporter le dépassement",
    "both": "Reporter les deux",
}


def _money(value, allow_zero=False):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Le montant est invalide.")
    if allow_zero:
        if amount < 0:
            raise ValueError("Le montant ne peut pas être négatif.")
    elif amount <= 0:
        raise ValueError("Le montant doit être supérieur à zéro.")
    return amount


def _text(value, label, maximum, required=False):
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{label} est obligatoire.")
    if len(text) > maximum:
        raise ValueError(f"{label} ne peut pas dépasser {maximum} caractères.")
    return text or None


def _month_start(value):
    if isinstance(value, date):
        return value.replace(day=1)
    text = str(value or "")
    if len(text) == 7:
        text += "-01"
    return date.fromisoformat(text).replace(day=1)


def _add_months(value, months):
    absolute = value.year * 12 + value.month - 1 + months
    year, month_index = divmod(absolute, 12)
    month = month_index + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _next_date(current, unit, interval):
    if unit == "day":
        return current + timedelta(days=interval)
    if unit == "week":
        return current + timedelta(weeks=interval)
    if unit == "month":
        return _add_months(current, interval)
    if unit == "year":
        return _add_months(current, interval * 12)
    raise ValueError("Fréquence invalide.")


def init_finances_schema():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS finance_categories (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    parent_id BIGINT REFERENCES finance_categories(id) ON DELETE RESTRICT,
                    name TEXT NOT NULL,
                    category_type TEXT NOT NULL DEFAULT 'both'
                        CHECK (category_type IN ('expense', 'income', 'both')),
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CHECK (CHAR_LENGTH(name) BETWEEN 1 AND 100)
                );
            """)
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS finance_categories_root_uq
                ON finance_categories (user_id, LOWER(name))
                WHERE parent_id IS NULL;
            """)
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS finance_categories_child_uq
                ON finance_categories (user_id, parent_id, LOWER(name))
                WHERE parent_id IS NOT NULL;
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS finance_tags (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CHECK (CHAR_LENGTH(name) BETWEEN 1 AND 80),
                    UNIQUE (user_id, name)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS finance_recurrences (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    transaction_type TEXT NOT NULL
                        CHECK (transaction_type IN ('expense', 'income')),
                    description TEXT NOT NULL,
                    amount NUMERIC(14,2) NOT NULL CHECK (amount > 0),
                    category_id BIGINT REFERENCES finance_categories(id) ON DELETE SET NULL,
                    note TEXT,
                    frequency_unit TEXT NOT NULL
                        CHECK (frequency_unit IN ('day', 'week', 'month', 'year')),
                    frequency_interval INTEGER NOT NULL DEFAULT 1
                        CHECK (frequency_interval BETWEEN 1 AND 365),
                    start_date DATE NOT NULL,
                    end_date DATE,
                    next_date DATE NOT NULL,
                    confirmation_mode TEXT NOT NULL DEFAULT 'confirm'
                        CHECK (confirmation_mode IN ('confirm', 'automatic')),
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CHECK (end_date IS NULL OR end_date >= start_date)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS finance_recurrence_tags (
                    recurrence_id BIGINT NOT NULL
                        REFERENCES finance_recurrences(id) ON DELETE CASCADE,
                    tag_id BIGINT NOT NULL
                        REFERENCES finance_tags(id) ON DELETE CASCADE,
                    PRIMARY KEY (recurrence_id, tag_id)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS finance_transactions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    transaction_date DATE NOT NULL,
                    transaction_type TEXT NOT NULL
                        CHECK (transaction_type IN ('expense', 'income')),
                    amount NUMERIC(14,2) NOT NULL CHECK (amount > 0),
                    description TEXT NOT NULL,
                    category_id BIGINT REFERENCES finance_categories(id) ON DELETE SET NULL,
                    note TEXT,
                    status TEXT NOT NULL DEFAULT 'confirmed'
                        CHECK (status IN ('confirmed', 'planned')),
                    recurrence_id BIGINT REFERENCES finance_recurrences(id) ON DELETE SET NULL,
                    occurrence_date DATE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (recurrence_id, occurrence_date)
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS finance_transactions_user_date_idx
                ON finance_transactions (user_id, transaction_date DESC, id DESC);
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS finance_transaction_tags (
                    transaction_id BIGINT NOT NULL
                        REFERENCES finance_transactions(id) ON DELETE CASCADE,
                    tag_id BIGINT NOT NULL
                        REFERENCES finance_tags(id) ON DELETE CASCADE,
                    PRIMARY KEY (transaction_id, tag_id)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS finance_goals (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    goal_type TEXT NOT NULL CHECK (goal_type IN ('category', 'tag')),
                    category_id BIGINT REFERENCES finance_categories(id) ON DELETE RESTRICT,
                    tag_id BIGINT REFERENCES finance_tags(id) ON DELETE RESTRICT,
                    monthly_amount NUMERIC(14,2) NOT NULL CHECK (monthly_amount > 0),
                    carry_policy TEXT NOT NULL DEFAULT 'none'
                        CHECK (carry_policy IN ('none','unused','overspend','both')),
                    max_carry NUMERIC(14,2),
                    start_month DATE NOT NULL,
                    end_month DATE,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CHECK (
                        (goal_type='category' AND category_id IS NOT NULL AND tag_id IS NULL)
                        OR
                        (goal_type='tag' AND tag_id IS NOT NULL AND category_id IS NULL)
                    )
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS finance_goal_months (
                    id BIGSERIAL PRIMARY KEY,
                    goal_id BIGINT NOT NULL REFERENCES finance_goals(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    month_start DATE NOT NULL,
                    base_amount NUMERIC(14,2) NOT NULL,
                    carry_in NUMERIC(14,2) NOT NULL DEFAULT 0,
                    carry_policy TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (goal_id, month_start)
                );
            """)
            conn.commit()


def ensure_default_finance_categories(user_id):
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


def list_categories(user_id, include_inactive=False):
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


def save_category(user_id, name, parent_id=None, category_type="both", category_id=None):
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


def toggle_category(user_id, category_id, is_active):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE finance_categories SET is_active=%s,updated_at=NOW()
                WHERE id=%s AND user_id=%s;
            """, (bool(is_active), category_id, user_id))
            conn.commit()


def list_tags(user_id, include_inactive=False):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM finance_tags
                WHERE user_id=%s AND (%s OR is_active=TRUE)
                ORDER BY name;
            """, (user_id, include_inactive))
            return cur.fetchall()


def save_tag(user_id, name, tag_id=None):
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


def toggle_tag(user_id, tag_id, is_active):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE finance_tags SET is_active=%s,updated_at=NOW()
                WHERE id=%s AND user_id=%s;
            """, (bool(is_active), tag_id, user_id))
            conn.commit()


def _validate_links(cur, user_id, category_id, tag_ids):
    if category_id:
        cur.execute(
            "SELECT id FROM finance_categories WHERE id=%s AND user_id=%s;",
            (category_id, user_id),
        )
        if not cur.fetchone():
            raise ValueError("Catégorie invalide.")
    tags = sorted({int(value) for value in (tag_ids or [])})
    if tags:
        cur.execute(
            "SELECT id FROM finance_tags WHERE user_id=%s AND id=ANY(%s);",
            (user_id, tags),
        )
        found = {int(row["id"]) for row in cur.fetchall()}
        if found != set(tags):
            raise ValueError("Étiquette invalide.")
    return tags


def save_transaction(
    user_id,
    transaction_date,
    transaction_type,
    amount,
    description,
    category_id=None,
    tag_ids=None,
    note=None,
    status="confirmed",
    transaction_id=None,
):
    if transaction_type not in TRANSACTION_TYPES:
        raise ValueError("Type invalide.")
    if status not in TRANSACTION_STATUSES:
        raise ValueError("Statut invalide.")
    parsed_date = (
        transaction_date
        if isinstance(transaction_date, date)
        else date.fromisoformat(str(transaction_date))
    )
    amount = _money(amount)
    description = _text(description, "La description", 160, True)
    note = _text(note, "La note", 1000)

    with get_connection() as conn:
        with conn.cursor() as cur:
            tags = _validate_links(cur, user_id, category_id, tag_ids)
            if transaction_id:
                cur.execute("""
                    UPDATE finance_transactions
                    SET transaction_date=%s,transaction_type=%s,amount=%s,
                        description=%s,category_id=%s,note=%s,status=%s,
                        updated_at=NOW()
                    WHERE id=%s AND user_id=%s;
                """, (
                    parsed_date, transaction_type, amount, description,
                    category_id, note, status, transaction_id, user_id,
                ))
                saved_id = int(transaction_id)
                cur.execute(
                    "DELETE FROM finance_transaction_tags WHERE transaction_id=%s;",
                    (saved_id,),
                )
            else:
                cur.execute("""
                    INSERT INTO finance_transactions
                        (user_id,transaction_date,transaction_type,amount,
                         description,category_id,note,status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id;
                """, (
                    user_id, parsed_date, transaction_type, amount,
                    description, category_id, note, status,
                ))
                saved_id = int(cur.fetchone()["id"])
            for tag_id in tags:
                cur.execute("""
                    INSERT INTO finance_transaction_tags (transaction_id,tag_id)
                    VALUES (%s,%s) ON CONFLICT DO NOTHING;
                """, (saved_id, tag_id))
            conn.commit()
            return saved_id


def list_transactions(
    user_id,
    start_date=None,
    end_date=None,
    transaction_type=None,
    category_id=None,
    tag_id=None,
    status=None,
    query=None,
    transaction_id=None,
    limit=1000,
):
    conditions = ["t.user_id=%s"]
    params = [user_id]
    for sql, value in (
        ("t.id=%s", transaction_id),
        ("t.transaction_date>=%s", start_date),
        ("t.transaction_date<=%s", end_date),
        ("t.transaction_type=%s", transaction_type),
        ("t.category_id=%s", category_id),
        ("t.status=%s", status),
    ):
        if value not in (None, ""):
            conditions.append(sql)
            params.append(value)
    if tag_id:
        conditions.append("""
            EXISTS (
                SELECT 1 FROM finance_transaction_tags x
                WHERE x.transaction_id=t.id AND x.tag_id=%s
            )
        """)
        params.append(tag_id)
    if query:
        conditions.append("""
            (LOWER(t.description) LIKE LOWER(%s)
             OR LOWER(COALESCE(t.note,'')) LIKE LOWER(%s))
        """)
        pattern = f"%{str(query).strip()}%"
        params.extend([pattern, pattern])
    params.append(int(limit))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT
                    t.*,
                    CASE WHEN parent.id IS NULL THEN category.name
                         ELSE parent.name || ' › ' || category.name
                    END AS category_full_name,
                    COALESCE(
                        ARRAY_AGG(tag.id ORDER BY tag.name)
                            FILTER (WHERE tag.id IS NOT NULL),
                        ARRAY[]::BIGINT[]
                    ) AS tag_ids,
                    COALESCE(
                        ARRAY_AGG(tag.name ORDER BY tag.name)
                            FILTER (WHERE tag.id IS NOT NULL),
                        ARRAY[]::TEXT[]
                    ) AS tag_names
                FROM finance_transactions t
                LEFT JOIN finance_categories category ON category.id=t.category_id
                LEFT JOIN finance_categories parent ON parent.id=category.parent_id
                LEFT JOIN finance_transaction_tags tt ON tt.transaction_id=t.id
                LEFT JOIN finance_tags tag ON tag.id=tt.tag_id
                WHERE {" AND ".join(conditions)}
                GROUP BY t.id,category.id,parent.id,parent.name
                ORDER BY t.transaction_date DESC,t.id DESC
                LIMIT %s;
            """, params)
            return cur.fetchall()


def get_transaction(user_id, transaction_id):
    rows = list_transactions(user_id, transaction_id=transaction_id)
    if not rows:
        raise ValueError("Transaction introuvable.")
    return rows[0]


def delete_transaction(user_id, transaction_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM finance_transactions WHERE id=%s AND user_id=%s;",
                (transaction_id, user_id),
            )
            conn.commit()


def set_transaction_status(user_id, transaction_id, status):
    if status not in TRANSACTION_STATUSES:
        raise ValueError("Statut invalide.")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE finance_transactions SET status=%s,updated_at=NOW()
                WHERE id=%s AND user_id=%s;
            """, (status, transaction_id, user_id))
            conn.commit()


def dashboard_summary(user_id, month_value):
    month = _month_start(month_value)
    next_month = _add_months(month, 1)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(SUM(amount) FILTER (
                        WHERE transaction_type='expense' AND status='confirmed'
                    ),0) AS expenses,
                    COALESCE(SUM(amount) FILTER (
                        WHERE transaction_type='income' AND status='confirmed'
                    ),0) AS incomes,
                    COUNT(*) FILTER (WHERE status='planned') AS planned_count
                FROM finance_transactions
                WHERE user_id=%s AND transaction_date>=%s AND transaction_date<%s;
            """, (user_id, month, next_month))
            row = cur.fetchone()
    expenses = Decimal(row["expenses"])
    incomes = Decimal(row["incomes"])
    return {
        "month": month,
        "expenses": expenses,
        "incomes": incomes,
        "difference": incomes - expenses,
        "planned_count": int(row["planned_count"]),
    }


def save_recurrence(
    user_id,
    transaction_type,
    description,
    amount,
    frequency_unit,
    frequency_interval,
    start_date,
    category_id=None,
    tag_ids=None,
    note=None,
    end_date=None,
    confirmation_mode="confirm",
    recurrence_id=None,
):
    if transaction_type not in TRANSACTION_TYPES:
        raise ValueError("Type invalide.")
    if frequency_unit not in FREQUENCY_UNITS:
        raise ValueError("Fréquence invalide.")
    if confirmation_mode not in CONFIRMATION_MODES:
        raise ValueError("Mode invalide.")
    interval = int(frequency_interval or 1)
    parsed_start = date.fromisoformat(str(start_date))
    parsed_end = date.fromisoformat(str(end_date)) if end_date else None
    amount = _money(amount)
    description = _text(description, "La description", 160, True)
    note = _text(note, "La note", 1000)

    with get_connection() as conn:
        with conn.cursor() as cur:
            tags = _validate_links(cur, user_id, category_id, tag_ids)
            if recurrence_id:
                cur.execute("""
                    UPDATE finance_recurrences
                    SET transaction_type=%s,description=%s,amount=%s,
                        category_id=%s,note=%s,frequency_unit=%s,
                        frequency_interval=%s,start_date=%s,end_date=%s,
                        confirmation_mode=%s,is_active=TRUE,updated_at=NOW()
                    WHERE id=%s AND user_id=%s;
                """, (
                    transaction_type, description, amount, category_id, note,
                    frequency_unit, interval, parsed_start, parsed_end,
                    confirmation_mode, recurrence_id, user_id,
                ))
                saved_id = int(recurrence_id)
                cur.execute(
                    "DELETE FROM finance_recurrence_tags WHERE recurrence_id=%s;",
                    (saved_id,),
                )
            else:
                cur.execute("""
                    INSERT INTO finance_recurrences
                        (user_id,transaction_type,description,amount,category_id,
                         note,frequency_unit,frequency_interval,start_date,end_date,
                         next_date,confirmation_mode)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id;
                """, (
                    user_id, transaction_type, description, amount, category_id,
                    note, frequency_unit, interval, parsed_start, parsed_end,
                    parsed_start, confirmation_mode,
                ))
                saved_id = int(cur.fetchone()["id"])
            for tag_id in tags:
                cur.execute("""
                    INSERT INTO finance_recurrence_tags (recurrence_id,tag_id)
                    VALUES (%s,%s) ON CONFLICT DO NOTHING;
                """, (saved_id, tag_id))
            conn.commit()


def list_recurrences(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    r.*,
                    CASE WHEN parent.id IS NULL THEN category.name
                         ELSE parent.name || ' › ' || category.name
                    END AS category_full_name,
                    COALESCE(
                        ARRAY_AGG(tag.id ORDER BY tag.name)
                            FILTER (WHERE tag.id IS NOT NULL),
                        ARRAY[]::BIGINT[]
                    ) AS tag_ids,
                    COALESCE(
                        ARRAY_AGG(tag.name ORDER BY tag.name)
                            FILTER (WHERE tag.id IS NOT NULL),
                        ARRAY[]::TEXT[]
                    ) AS tag_names
                FROM finance_recurrences r
                LEFT JOIN finance_categories category ON category.id=r.category_id
                LEFT JOIN finance_categories parent ON parent.id=category.parent_id
                LEFT JOIN finance_recurrence_tags rt ON rt.recurrence_id=r.id
                LEFT JOIN finance_tags tag ON tag.id=rt.tag_id
                WHERE r.user_id=%s
                GROUP BY r.id,category.id,parent.id,parent.name
                ORDER BY r.is_active DESC,r.next_date,r.description;
            """, (user_id,))
            return cur.fetchall()


def toggle_recurrence(user_id, recurrence_id, is_active):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE finance_recurrences SET is_active=%s,updated_at=NOW()
                WHERE id=%s AND user_id=%s;
            """, (bool(is_active), recurrence_id, user_id))
            conn.commit()


def generate_due_recurrences(user_id, through_date=None):
    through = through_date or date.today()
    created = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM finance_recurrences
                WHERE user_id=%s AND is_active=TRUE AND next_date<=%s
                FOR UPDATE;
            """, (user_id, through))
            rows = cur.fetchall()
            for recurrence in rows:
                cur.execute(
                    "SELECT tag_id FROM finance_recurrence_tags WHERE recurrence_id=%s;",
                    (recurrence["id"],),
                )
                tags = [row["tag_id"] for row in cur.fetchall()]
                occurrence = recurrence["next_date"]
                while occurrence <= through:
                    if recurrence["end_date"] and occurrence > recurrence["end_date"]:
                        break
                    status = (
                        "confirmed"
                        if recurrence["confirmation_mode"] == "automatic"
                        else "planned"
                    )
                    cur.execute("""
                        INSERT INTO finance_transactions
                            (user_id,transaction_date,transaction_type,amount,
                             description,category_id,note,status,recurrence_id,
                             occurrence_date)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (recurrence_id,occurrence_date) DO NOTHING
                        RETURNING id;
                    """, (
                        user_id, occurrence, recurrence["transaction_type"],
                        recurrence["amount"], recurrence["description"],
                        recurrence["category_id"], recurrence["note"], status,
                        recurrence["id"], occurrence,
                    ))
                    inserted = cur.fetchone()
                    if inserted:
                        created += 1
                        for tag_id in tags:
                            cur.execute("""
                                INSERT INTO finance_transaction_tags
                                    (transaction_id,tag_id)
                                VALUES (%s,%s) ON CONFLICT DO NOTHING;
                            """, (inserted["id"], tag_id))
                    occurrence = _next_date(
                        occurrence,
                        recurrence["frequency_unit"],
                        recurrence["frequency_interval"],
                    )
                still_active = not (
                    recurrence["end_date"]
                    and occurrence > recurrence["end_date"]
                )
                cur.execute("""
                    UPDATE finance_recurrences
                    SET next_date=%s,is_active=%s,updated_at=NOW()
                    WHERE id=%s;
                """, (occurrence, still_active, recurrence["id"]))
            conn.commit()
    return created


def save_goal(
    user_id,
    goal_type,
    target_id,
    monthly_amount,
    carry_policy,
    start_month,
    end_month=None,
    max_carry=None,
    goal_id=None,
):
    if goal_type not in {"category", "tag"}:
        raise ValueError("Type d’objectif invalide.")
    if carry_policy not in CARRY_POLICIES:
        raise ValueError("Politique de report invalide.")
    amount = _money(monthly_amount)
    start = _month_start(start_month)
    end = _month_start(end_month) if end_month else None
    max_value = (
        _money(max_carry, allow_zero=True)
        if max_carry not in (None, "")
        else None
    )
    category_id = int(target_id) if goal_type == "category" else None
    tag_id = int(target_id) if goal_type == "tag" else None

    with get_connection() as conn:
        with conn.cursor() as cur:
            _validate_links(
                cur,
                user_id,
                category_id,
                [tag_id] if tag_id else [],
            )
            if goal_id:
                cur.execute("""
                    UPDATE finance_goals
                    SET goal_type=%s,category_id=%s,tag_id=%s,
                        monthly_amount=%s,carry_policy=%s,max_carry=%s,
                        start_month=%s,end_month=%s,is_active=TRUE,updated_at=NOW()
                    WHERE id=%s AND user_id=%s;
                """, (
                    goal_type, category_id, tag_id, amount, carry_policy,
                    max_value, start, end, goal_id, user_id,
                ))
            else:
                cur.execute("""
                    INSERT INTO finance_goals
                        (user_id,goal_type,category_id,tag_id,monthly_amount,
                         carry_policy,max_carry,start_month,end_month)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s);
                """, (
                    user_id, goal_type, category_id, tag_id, amount,
                    carry_policy, max_value, start, end,
                ))
            conn.commit()


def list_goals(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    g.*,
                    CASE WHEN g.goal_type='tag' THEN tag.name
                         WHEN parent.id IS NULL THEN category.name
                         ELSE parent.name || ' › ' || category.name
                    END AS target_name
                FROM finance_goals g
                LEFT JOIN finance_categories category ON category.id=g.category_id
                LEFT JOIN finance_categories parent ON parent.id=category.parent_id
                LEFT JOIN finance_tags tag ON tag.id=g.tag_id
                WHERE g.user_id=%s
                ORDER BY g.is_active DESC,target_name;
            """, (user_id,))
            return cur.fetchall()


def toggle_goal(user_id, goal_id, is_active):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE finance_goals SET is_active=%s,updated_at=NOW()
                WHERE id=%s AND user_id=%s;
            """, (bool(is_active), goal_id, user_id))
            conn.commit()


def _goal_spent(cur, goal, month):
    next_month = _add_months(month, 1)
    if goal["goal_type"] == "tag":
        cur.execute("""
            SELECT COALESCE(SUM(t.amount),0) AS total
            FROM finance_transactions t
            JOIN finance_transaction_tags tt ON tt.transaction_id=t.id
            WHERE t.user_id=%s AND t.transaction_type='expense'
              AND t.status='confirmed'
              AND t.transaction_date>=%s AND t.transaction_date<%s
              AND tt.tag_id=%s;
        """, (goal["user_id"], month, next_month, goal["tag_id"]))
    else:
        cur.execute("""
            SELECT COALESCE(SUM(t.amount),0) AS total
            FROM finance_transactions t
            LEFT JOIN finance_categories c ON c.id=t.category_id
            WHERE t.user_id=%s AND t.transaction_type='expense'
              AND t.status='confirmed'
              AND t.transaction_date>=%s AND t.transaction_date<%s
              AND (t.category_id=%s OR c.parent_id=%s);
        """, (
            goal["user_id"], month, next_month,
            goal["category_id"], goal["category_id"],
        ))
    return Decimal(cur.fetchone()["total"])


def goal_progress(user_id, month_value):
    month = _month_start(month_value)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    g.*,
                    CASE WHEN g.goal_type='tag' THEN tag.name
                         WHEN parent.id IS NULL THEN category.name
                         ELSE parent.name || ' › ' || category.name
                    END AS target_name
                FROM finance_goals g
                LEFT JOIN finance_categories category ON category.id=g.category_id
                LEFT JOIN finance_categories parent ON parent.id=category.parent_id
                LEFT JOIN finance_tags tag ON tag.id=g.tag_id
                WHERE g.user_id=%s AND g.is_active=TRUE
                  AND g.start_month<=%s
                  AND (g.end_month IS NULL OR g.end_month>=%s)
                ORDER BY target_name;
            """, (user_id, month, month))
            goals = cur.fetchall()
            results = []
            for goal in goals:
                cur.execute("""
                    SELECT * FROM finance_goal_months
                    WHERE goal_id=%s AND month_start=%s;
                """, (goal["id"], month))
                snapshot = cur.fetchone()
                if not snapshot:
                    carry_in = Decimal("0.00")
                    previous_month = _add_months(month, -1)
                    if previous_month >= goal["start_month"]:
                        previous = next(
                            (
                                item for item in goal_progress(user_id, previous_month)
                                if item["goal_id"] == goal["id"]
                            ),
                            None,
                        )
                        if previous:
                            carry_in = previous["carry_out"]
                    if goal["max_carry"] is not None:
                        limit = Decimal(goal["max_carry"])
                        carry_in = max(-limit, min(limit, carry_in))
                    cur.execute("""
                        INSERT INTO finance_goal_months
                            (goal_id,user_id,month_start,base_amount,carry_in,carry_policy)
                        VALUES (%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (goal_id,month_start) DO NOTHING;
                    """, (
                        goal["id"], user_id, month, goal["monthly_amount"],
                        carry_in, goal["carry_policy"],
                    ))
                    conn.commit()
                    snapshot = {
                        "base_amount": goal["monthly_amount"],
                        "carry_in": carry_in,
                        "carry_policy": goal["carry_policy"],
                    }
                spent = _goal_spent(cur, goal, month)
                available = (
                    Decimal(snapshot["base_amount"])
                    + Decimal(snapshot["carry_in"])
                )
                difference = available - spent
                policy = snapshot["carry_policy"]
                carry_out = Decimal("0.00")
                if difference > 0 and policy in {"unused", "both"}:
                    carry_out = difference
                elif difference < 0 and policy in {"overspend", "both"}:
                    carry_out = difference
                if goal["max_carry"] is not None:
                    limit = Decimal(goal["max_carry"])
                    carry_out = max(-limit, min(limit, carry_out))
                percentage = float(spent / available * 100) if available > 0 else 0
                results.append({
                    "goal_id": int(goal["id"]),
                    "target_name": goal["target_name"],
                    "base_amount": Decimal(snapshot["base_amount"]),
                    "carry_in": Decimal(snapshot["carry_in"]),
                    "available": available,
                    "spent": spent,
                    "remaining": available - spent,
                    "carry_out": carry_out,
                    "percentage": percentage,
                    "carry_policy": policy,
                })
            return results


def export_finances(user_id):
    transactions = list_transactions(user_id, limit=100000)
    categories = list_categories(user_id, include_inactive=True)
    tags = list_tags(user_id, include_inactive=True)
    recurrences = list_recurrences(user_id)
    goals = list_goals(user_id)

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow([
        "Date", "Type", "Description", "Montant", "Catégorie",
        "Étiquettes", "Note", "Statut", "Récurrence",
    ])
    for row in reversed(transactions):
        writer.writerow([
            row["transaction_date"].isoformat(),
            TRANSACTION_TYPES[row["transaction_type"]],
            row["description"],
            str(row["amount"]),
            row["category_full_name"] or "",
            " | ".join(row["tag_names"] or []),
            row["note"] or "",
            TRANSACTION_STATUSES[row["status"]],
            "Oui" if row["recurrence_id"] else "Non",
        ])

    def serial(value):
        if isinstance(value, (date, Decimal)):
            return str(value)
        if isinstance(value, list):
            return [serial(item) for item in value]
        if isinstance(value, dict):
            return {key: serial(item) for key, item in value.items()}
        return value

    payload = {
        "format": "JF Apps Finances",
        "version": "1.0.0",
        "categories": [serial(dict(row)) for row in categories],
        "tags": [serial(dict(row)) for row in tags],
        "transactions": [serial(dict(row)) for row in transactions],
        "recurrences": [serial(dict(row)) for row in recurrences],
        "goals": [serial(dict(row)) for row in goals],
    }
    return (
        csv_buffer.getvalue().encode("utf-8-sig"),
        json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
    )
