from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
import csv
import hashlib
import io
import json
import re
import unicodedata
from zoneinfo import ZoneInfo

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
RECONCILIATION_STATUSES = {
    "unreconciled": "À concilier",
    "reconciled": "Conciliée",
}
DEFAULT_PAYMENT_METHODS = (
    "MC Canadian Tire",
    "MC PC",
    "Visa Desjardins",
    "Direct",
)

DEFAULT_PAYMENT_METHOD_TYPES = {
    "MC Canadian Tire": "credit_card",
    "MC PC": "credit_card",
    "Visa Desjardins": "credit_card",
    "Direct": "bank",
}

PAYMENT_METHOD_TYPES = {
    "credit_card": "Carte de crédit",
    "bank": "Compte bancaire",
    "credit_line": "Marge de crédit",
    "cash": "Argent comptant",
    "other": "Autre",
}

RECONCILIATION_SESSION_STATUSES = {
    "completed": "Complétée",
    "cancelled": "Annulée",
}

BUDGET_INPUT_FREQUENCIES = {
    "monthly": "Mensuel",
    "biweekly": "Aux 2 semaines",
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


def _decimal_value(value, label, allow_blank=False):
    if value in (None, ""):
        if allow_blank:
            return None
        return Decimal("0.00")
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{label} est invalide.")


def _text(value, label, maximum, required=False):
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{label} est obligatoire.")
    if len(text) > maximum:
        raise ValueError(f"{label} ne peut pas dépasser {maximum} caractères.")
    return text or None


def _normalize_reminder_time(value):
    text = str(value or "09:00").strip()[:5]
    try:
        parsed = datetime.strptime(text, "%H:%M").time()
    except ValueError as error:
        raise ValueError("L’heure du rappel est invalide.") from error
    return parsed


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
                ALTER TABLE finance_categories
                ADD COLUMN IF NOT EXISTS dashboard_visible BOOLEAN
                NOT NULL DEFAULT TRUE;
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
                ALTER TABLE finance_tags
                ADD COLUMN IF NOT EXISTS dashboard_visible BOOLEAN
                NOT NULL DEFAULT TRUE;
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS finance_payment_methods (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CHECK (CHAR_LENGTH(name) BETWEEN 1 AND 100)
                );
            """)
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                finance_payment_methods_name_uq
                ON finance_payment_methods (user_id, LOWER(name));
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS
                finance_payment_methods_order_idx
                ON finance_payment_methods (
                    user_id, is_active DESC, sort_order, name
                );
            """)
            cur.execute("""
                ALTER TABLE finance_payment_methods
                ADD COLUMN IF NOT EXISTS method_type TEXT
                NOT NULL DEFAULT 'credit_card';
            """)
            cur.execute("""
                ALTER TABLE finance_payment_methods
                ADD COLUMN IF NOT EXISTS statement_day SMALLINT;
            """)
            cur.execute("""
                ALTER TABLE finance_payment_methods
                ADD COLUMN IF NOT EXISTS payment_day SMALLINT;
            """)
            cur.execute("""
                ALTER TABLE finance_payment_methods
                ADD COLUMN IF NOT EXISTS opening_balance NUMERIC(14,2)
                NOT NULL DEFAULT 0;
            """)
            cur.execute("""
                ALTER TABLE finance_payment_methods
                ADD COLUMN IF NOT EXISTS opening_balance_date DATE;
            """)
            cur.execute("""
                ALTER TABLE finance_payment_methods
                ADD COLUMN IF NOT EXISTS opening_balance_reconciled BOOLEAN
                NOT NULL DEFAULT FALSE;
            """)
            cur.execute("""
                ALTER TABLE finance_payment_methods
                ADD COLUMN IF NOT EXISTS note TEXT;
            """)
            cur.execute("""
                ALTER TABLE finance_payment_methods
                ADD COLUMN IF NOT EXISTS credit_limit NUMERIC(14,2);
            """)
            cur.execute("""
                DO $$
                DECLARE
                    current_definition TEXT;
                BEGIN
                    SELECT pg_get_constraintdef(oid)
                    INTO current_definition
                    FROM pg_constraint
                    WHERE conname = 'finance_payment_methods_type_ck'
                      AND conrelid = 'finance_payment_methods'::regclass;

                    IF current_definition IS NOT NULL
                       AND POSITION('credit_line' IN current_definition) = 0 THEN
                        ALTER TABLE finance_payment_methods
                        DROP CONSTRAINT finance_payment_methods_type_ck;
                        current_definition := NULL;
                    END IF;

                    IF current_definition IS NULL THEN
                        ALTER TABLE finance_payment_methods
                        ADD CONSTRAINT finance_payment_methods_type_ck
                        CHECK (
                            method_type IN (
                                'credit_card',
                                'bank',
                                'credit_line',
                                'cash',
                                'other'
                            )
                        );
                    END IF;
                END $$;
            """)
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'finance_payment_methods_statement_day_ck'
                    ) THEN
                        ALTER TABLE finance_payment_methods
                        ADD CONSTRAINT finance_payment_methods_statement_day_ck
                        CHECK (
                            statement_day IS NULL
                            OR statement_day BETWEEN 1 AND 31
                        );
                    END IF;
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'finance_payment_methods_payment_day_ck'
                    ) THEN
                        ALTER TABLE finance_payment_methods
                        ADD CONSTRAINT finance_payment_methods_payment_day_ck
                        CHECK (
                            payment_day IS NULL
                            OR payment_day BETWEEN 1 AND 31
                        );
                    END IF;
                END
                $$;
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
                ALTER TABLE finance_recurrences
                ADD COLUMN IF NOT EXISTS payment_method_id BIGINT;
            """)
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname =
                            'finance_recurrences_payment_method_fk'
                    ) THEN
                        ALTER TABLE finance_recurrences
                        ADD CONSTRAINT
                            finance_recurrences_payment_method_fk
                        FOREIGN KEY (payment_method_id)
                        REFERENCES finance_payment_methods(id)
                        ON DELETE SET NULL;
                    END IF;
                END
                $$;
            """)

            cur.execute("""
                ALTER TABLE finance_recurrences
                ADD COLUMN IF NOT EXISTS budget_excluded BOOLEAN
                NOT NULL DEFAULT FALSE;
            """)
            cur.execute("""
                ALTER TABLE finance_recurrences
                ADD COLUMN IF NOT EXISTS bank_programmed BOOLEAN
                NOT NULL DEFAULT FALSE;
            """)
            cur.execute("""
                ALTER TABLE finance_recurrences
                ADD COLUMN IF NOT EXISTS reminder_enabled BOOLEAN
                NOT NULL DEFAULT FALSE;
            """)
            cur.execute("""
                ALTER TABLE finance_recurrences
                ADD COLUMN IF NOT EXISTS reminder_time TIME
                NOT NULL DEFAULT '09:00';
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
                ALTER TABLE finance_transactions
                ADD COLUMN IF NOT EXISTS import_source TEXT;
            """)
            cur.execute("""
                ALTER TABLE finance_transactions
                ADD COLUMN IF NOT EXISTS import_key TEXT;
            """)
            cur.execute("""
                ALTER TABLE finance_transactions
                ADD COLUMN IF NOT EXISTS imported_at TIMESTAMPTZ;
            """)
            cur.execute("""
                ALTER TABLE finance_transactions
                ADD COLUMN IF NOT EXISTS payment_method_id BIGINT;
            """)
            cur.execute("""
                ALTER TABLE finance_transactions
                ADD COLUMN IF NOT EXISTS reconciliation_status TEXT
                NOT NULL DEFAULT 'unreconciled';
            """)
            cur.execute("""
                ALTER TABLE finance_transactions
                ADD COLUMN IF NOT EXISTS reconciliation_date DATE;
            """)
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname =
                            'finance_transactions_payment_method_fk'
                    ) THEN
                        ALTER TABLE finance_transactions
                        ADD CONSTRAINT
                            finance_transactions_payment_method_fk
                        FOREIGN KEY (payment_method_id)
                        REFERENCES finance_payment_methods(id)
                        ON DELETE SET NULL;
                    END IF;
                END
                $$;
            """)
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname =
                            'finance_transactions_reconciliation_status_ck'
                    ) THEN
                        ALTER TABLE finance_transactions
                        ADD CONSTRAINT
                            finance_transactions_reconciliation_status_ck
                        CHECK (
                            reconciliation_status IN (
                                'unreconciled',
                                'reconciled'
                            )
                        );
                    END IF;
                END
                $$;
            """)
            cur.execute("""
                ALTER TABLE finance_transactions
                ADD COLUMN IF NOT EXISTS budget_excluded BOOLEAN
                NOT NULL DEFAULT FALSE;
            """)
            cur.execute("""
                ALTER TABLE finance_transactions
                ADD COLUMN IF NOT EXISTS bank_programmed BOOLEAN
                NOT NULL DEFAULT FALSE;
            """)
            cur.execute("""
                ALTER TABLE finance_transactions
                ADD COLUMN IF NOT EXISTS reminder_enabled BOOLEAN
                NOT NULL DEFAULT FALSE;
            """)
            cur.execute("""
                ALTER TABLE finance_transactions
                ADD COLUMN IF NOT EXISTS reminder_time TIME
                NOT NULL DEFAULT '09:00';
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS
                finance_transactions_reconciliation_idx
                ON finance_transactions (
                    user_id,
                    payment_method_id,
                    reconciliation_status,
                    transaction_date DESC
                );
            """)

            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                finance_transactions_import_key_uq
                ON finance_transactions (user_id, import_source, import_key)
                WHERE import_source IS NOT NULL
                  AND import_key IS NOT NULL;
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
                CREATE TABLE IF NOT EXISTS finance_reconciliation_sessions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id) ON DELETE CASCADE,
                    payment_method_id BIGINT NOT NULL
                        REFERENCES finance_payment_methods(id)
                        ON DELETE RESTRICT,
                    statement_date DATE NOT NULL,
                    statement_balance NUMERIC(14,2),
                    due_date DATE,
                    reconciliation_date DATE NOT NULL,
                    note TEXT,
                    selected_total NUMERIC(14,2) NOT NULL DEFAULT 0,
                    difference NUMERIC(14,2),
                    included_opening_balance BOOLEAN
                        NOT NULL DEFAULT FALSE,
                    opening_balance_amount NUMERIC(14,2)
                        NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'completed'
                        CHECK (status IN ('completed', 'cancelled')),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    cancelled_at TIMESTAMPTZ,
                    CHECK (note IS NULL OR CHAR_LENGTH(note) <= 1000)
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS
                finance_reconciliation_sessions_user_idx
                ON finance_reconciliation_sessions (
                    user_id,
                    payment_method_id,
                    statement_date DESC,
                    id DESC
                );
            """)
            cur.execute("""
                ALTER TABLE finance_transactions
                ADD COLUMN IF NOT EXISTS reconciliation_session_id BIGINT;
            """)
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname =
                            'finance_transactions_reconciliation_session_fk'
                    ) THEN
                        ALTER TABLE finance_transactions
                        ADD CONSTRAINT
                            finance_transactions_reconciliation_session_fk
                        FOREIGN KEY (reconciliation_session_id)
                        REFERENCES finance_reconciliation_sessions(id)
                        ON DELETE SET NULL;
                    END IF;
                END
                $$;
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS
                finance_reconciliation_session_transactions (
                    session_id BIGINT NOT NULL
                        REFERENCES finance_reconciliation_sessions(id)
                        ON DELETE CASCADE,
                    transaction_id BIGINT NOT NULL
                        REFERENCES finance_transactions(id)
                        ON DELETE CASCADE,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    removed_at TIMESTAMPTZ,
                    PRIMARY KEY (session_id, transaction_id)
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS
                finance_reconciliation_session_transactions_active_idx
                ON finance_reconciliation_session_transactions (
                    transaction_id,
                    is_active
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS finance_budget_items (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id) ON DELETE CASCADE,
                    item_type TEXT NOT NULL
                        CHECK (item_type IN ('expense', 'income')),
                    description TEXT NOT NULL,
                    input_frequency TEXT NOT NULL DEFAULT 'monthly'
                        CHECK (input_frequency IN ('monthly', 'biweekly')),
                    input_amount NUMERIC(14,2) NOT NULL
                        CHECK (input_amount > 0),
                    biweekly_override NUMERIC(14,2),
                    note TEXT,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CHECK (biweekly_override IS NULL OR biweekly_override > 0),
                    CHECK (CHAR_LENGTH(description) BETWEEN 1 AND 160),
                    CHECK (note IS NULL OR CHAR_LENGTH(note) <= 1000)
                );
            """)
            cur.execute("""
                ALTER TABLE finance_budget_items
                ADD COLUMN IF NOT EXISTS recurrence_id BIGINT;
            """)
            cur.execute("""
                ALTER TABLE finance_budget_items
                ADD COLUMN IF NOT EXISTS sync_from_recurrence BOOLEAN
                NOT NULL DEFAULT TRUE;
            """)
            # Le lien Budget -> Récurrence est volontairement validé par
            # l’application plutôt que par une nouvelle contrainte au démarrage.
            # Cela rend la mise à niveau sûre même sur une base déjà utilisée.
            cur.execute("""
                CREATE INDEX IF NOT EXISTS finance_budget_items_order_idx
                ON finance_budget_items (
                    user_id, is_active DESC, item_type, sort_order, id
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


def set_category_dashboard_visible(user_id, category_id, is_visible):
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


def ensure_default_finance_payment_methods(user_id):
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


def _validate_payment_method(
    cur,
    user_id,
    payment_method_id,
):
    if payment_method_id in (
        None,
        "",
    ):
        return None

    normalized_id = int(
        payment_method_id
    )

    cur.execute(
        """
        SELECT id
        FROM finance_payment_methods
        WHERE id = %s
          AND user_id = %s;
        """,
        (
            normalized_id,
            user_id,
        ),
    )
    if not cur.fetchone():
        raise ValueError(
            "Le mode de paiement sélectionné est invalide."
        )

    return normalized_id



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
    payment_method_id=None,
    reconciliation_status="unreconciled",
    reconciliation_date=None,
    budget_excluded=False,
    bank_programmed=False,
    reminder_enabled=False,
    reminder_time=None,
    transaction_id=None,
):
    if transaction_type not in TRANSACTION_TYPES:
        raise ValueError("Type invalide.")
    if status not in TRANSACTION_STATUSES:
        raise ValueError("Statut invalide.")
    if reconciliation_status not in RECONCILIATION_STATUSES:
        raise ValueError("Statut de conciliation invalide.")

    parsed_date = (
        transaction_date
        if isinstance(transaction_date, date)
        else date.fromisoformat(str(transaction_date))
    )
    parsed_reconciliation_date = (
        reconciliation_date
        if isinstance(reconciliation_date, date)
        else (
            date.fromisoformat(str(reconciliation_date))
            if reconciliation_date
            else None
        )
    )
    if status == "planned":
        reconciliation_status = "unreconciled"
        parsed_reconciliation_date = None
    elif reconciliation_status == "unreconciled":
        parsed_reconciliation_date = None

    normalized_reminder_time = _normalize_reminder_time(reminder_time)
    bank_programmed = bool(bank_programmed) if status == "planned" else False
    reminder_enabled = bool(reminder_enabled) if status == "planned" else False

    amount = _money(amount)
    description = _text(
        description,
        "La description",
        160,
        True,
    )
    note = _text(
        note,
        "La note",
        1000,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            tags = _validate_links(
                cur,
                user_id,
                category_id,
                tag_ids,
            )
            validated_payment_method = (
                _validate_payment_method(
                    cur,
                    user_id,
                    payment_method_id,
                )
            )

            if transaction_id:
                cur.execute(
                    """
                    SELECT reconciliation_status
                    FROM finance_transactions
                    WHERE id = %s AND user_id = %s
                    FOR UPDATE;
                    """,
                    (transaction_id, user_id),
                )
                current_transaction = cur.fetchone()
                if not current_transaction:
                    raise ValueError("Transaction introuvable.")
                if (
                    current_transaction["reconciliation_status"]
                    == "reconciled"
                ):
                    raise ValueError(
                        "Retirez d’abord la conciliation avant de "
                        "modifier cette transaction."
                    )

                cur.execute(
                    """
                    UPDATE finance_transactions
                    SET
                        transaction_date = %s,
                        transaction_type = %s,
                        amount = %s,
                        description = %s,
                        category_id = %s,
                        note = %s,
                        status = %s,
                        payment_method_id = %s,
                        reconciliation_status = %s,
                        reconciliation_date = %s,
                        budget_excluded = %s,
                        bank_programmed = %s,
                        reminder_enabled = %s,
                        reminder_time = %s,
                        updated_at = NOW()
                    WHERE id = %s
                      AND user_id = %s;
                    """,
                    (
                        parsed_date,
                        transaction_type,
                        amount,
                        description,
                        category_id,
                        note,
                        status,
                        validated_payment_method,
                        reconciliation_status,
                        parsed_reconciliation_date,
                        bool(budget_excluded),
                        bank_programmed,
                        reminder_enabled,
                        normalized_reminder_time,
                        transaction_id,
                        user_id,
                    ),
                )
                if cur.rowcount == 0:
                    raise ValueError(
                        "Transaction introuvable."
                    )

                saved_id = int(
                    transaction_id
                )
                cur.execute(
                    """
                    DELETE FROM finance_transaction_tags
                    WHERE transaction_id = %s;
                    """,
                    (saved_id,),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO finance_transactions (
                        user_id,
                        transaction_date,
                        transaction_type,
                        amount,
                        description,
                        category_id,
                        note,
                        status,
                        payment_method_id,
                        reconciliation_status,
                        reconciliation_date,
                        budget_excluded,
                        bank_programmed,
                        reminder_enabled,
                        reminder_time
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s
                    )
                    RETURNING id;
                    """,
                    (
                        user_id,
                        parsed_date,
                        transaction_type,
                        amount,
                        description,
                        category_id,
                        note,
                        status,
                        validated_payment_method,
                        reconciliation_status,
                        parsed_reconciliation_date,
                        bool(budget_excluded),
                        bank_programmed,
                        reminder_enabled,
                        normalized_reminder_time,
                    ),
                )
                saved_id = int(
                    cur.fetchone()["id"]
                )

            for tag_id in tags:
                cur.execute(
                    """
                    INSERT INTO finance_transaction_tags (
                        transaction_id,
                        tag_id
                    )
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (
                        saved_id,
                        tag_id,
                    ),
                )

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
    payment_method_id=None,
    reconciliation_status=None,
    query=None,
    transaction_id=None,
    limit=1000,
):
    conditions = [
        "t.user_id = %s",
    ]
    params = [
        user_id,
    ]

    for sql, value in (
        (
            "t.id = %s",
            transaction_id,
        ),
        (
            "t.transaction_date >= %s",
            start_date,
        ),
        (
            "t.transaction_date <= %s",
            end_date,
        ),
        (
            "t.transaction_type = %s",
            transaction_type,
        ),
        (
            "t.category_id = %s",
            category_id,
        ),
        (
            "t.status = %s",
            status,
        ),
        (
            "t.payment_method_id = %s",
            payment_method_id,
        ),
        (
            "t.reconciliation_status = %s",
            reconciliation_status,
        ),
    ):
        if value not in (
            None,
            "",
        ):
            conditions.append(
                sql
            )
            params.append(
                value
            )

    if tag_id:
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM finance_transaction_tags AS selected_tag
                WHERE selected_tag.transaction_id = t.id
                  AND selected_tag.tag_id = %s
            )
            """
        )
        params.append(
            tag_id
        )

    if query:
        conditions.append(
            """
            (
                LOWER(t.description) LIKE LOWER(%s)
                OR LOWER(
                    COALESCE(
                        t.note,
                        ''
                    )
                ) LIKE LOWER(%s)
                OR LOWER(
                    COALESCE(
                        payment_method.name,
                        ''
                    )
                ) LIKE LOWER(%s)
            )
            """
        )
        pattern = (
            f"%{str(query).strip()}%"
        )
        params.extend(
            [
                pattern,
                pattern,
                pattern,
            ]
        )

    params.append(
        int(limit)
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    t.*,
                    payment_method.name
                        AS payment_method_name,
                    CASE
                        WHEN parent.id IS NULL
                        THEN category.name
                        ELSE parent.name
                             || ' › '
                             || category.name
                    END AS category_full_name,
                    COALESCE(
                        ARRAY_AGG(
                            tag.id
                            ORDER BY tag.name
                        )
                        FILTER (
                            WHERE tag.id IS NOT NULL
                        ),
                        ARRAY[]::BIGINT[]
                    ) AS tag_ids,
                    COALESCE(
                        ARRAY_AGG(
                            tag.name
                            ORDER BY tag.name
                        )
                        FILTER (
                            WHERE tag.id IS NOT NULL
                        ),
                        ARRAY[]::TEXT[]
                    ) AS tag_names
                FROM finance_transactions AS t
                LEFT JOIN finance_categories AS category
                    ON category.id = t.category_id
                LEFT JOIN finance_categories AS parent
                    ON parent.id = category.parent_id
                LEFT JOIN finance_payment_methods AS payment_method
                    ON payment_method.id = t.payment_method_id
                LEFT JOIN finance_transaction_tags AS transaction_tag
                    ON transaction_tag.transaction_id = t.id
                LEFT JOIN finance_tags AS tag
                    ON tag.id = transaction_tag.tag_id
                WHERE {" AND ".join(conditions)}
                GROUP BY
                    t.id,
                    category.id,
                    parent.id,
                    parent.name,
                    payment_method.id,
                    payment_method.name
                ORDER BY
                    t.transaction_date DESC,
                    t.id DESC
                LIMIT %s;
                """,
                params,
            )
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
                """
                SELECT reconciliation_status
                FROM finance_transactions
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
                """,
                (transaction_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Transaction introuvable.")
            if row["reconciliation_status"] == "reconciled":
                raise ValueError(
                    "Retirez d’abord la conciliation avant de "
                    "supprimer cette transaction."
                )

            cur.execute(
                """
                DELETE FROM finance_transactions
                WHERE id = %s AND user_id = %s;
                """,
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

def _refresh_reconciliation_session_totals(
    cur,
    session_id,
):
    cur.execute(
        """
        SELECT
            session.statement_balance,
            session.opening_balance_amount,
            COALESCE(
                SUM(
                    CASE
                        WHEN transaction.transaction_type = 'expense'
                        THEN transaction.amount
                        ELSE -transaction.amount
                    END
                ) FILTER (WHERE link.is_active = TRUE),
                0
            ) AS transaction_total
        FROM finance_reconciliation_sessions AS session
        LEFT JOIN finance_reconciliation_session_transactions AS link
            ON link.session_id = session.id
        LEFT JOIN finance_transactions AS transaction
            ON transaction.id = link.transaction_id
        WHERE session.id = %s
        GROUP BY session.id;
        """,
        (session_id,),
    )
    row = cur.fetchone()
    if not row:
        return

    selected_total = (
        Decimal(row["transaction_total"])
        + Decimal(row["opening_balance_amount"])
    )
    statement_balance = row["statement_balance"]
    difference = (
        Decimal(statement_balance) - selected_total
        if statement_balance is not None
        else None
    )
    cur.execute(
        """
        UPDATE finance_reconciliation_sessions
        SET selected_total = %s,
            difference = %s
        WHERE id = %s;
        """,
        (selected_total, difference, session_id),
    )


def set_transaction_reconciliation(
    user_id,
    transaction_id,
    reconciliation_status,
    reconciliation_date=None,
):
    if reconciliation_status not in RECONCILIATION_STATUSES:
        raise ValueError("Statut de conciliation invalide.")

    parsed_date = (
        reconciliation_date
        if isinstance(reconciliation_date, date)
        else (
            date.fromisoformat(str(reconciliation_date))
            if reconciliation_date
            else None
        )
    )
    if reconciliation_status == "unreconciled":
        parsed_date = None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT reconciliation_session_id
                FROM finance_transactions
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
                """,
                (transaction_id, user_id),
            )
            current = cur.fetchone()
            if not current:
                raise ValueError("Transaction introuvable.")

            session_id = current["reconciliation_session_id"]

            if reconciliation_status == "unreconciled" and session_id:
                cur.execute(
                    """
                    UPDATE finance_reconciliation_session_transactions
                    SET is_active = FALSE,
                        removed_at = NOW()
                    WHERE session_id = %s
                      AND transaction_id = %s
                      AND is_active = TRUE;
                    """,
                    (session_id, transaction_id),
                )

            cur.execute(
                """
                UPDATE finance_transactions
                SET reconciliation_status = %s,
                    reconciliation_date = %s,
                    reconciliation_session_id = %s,
                    updated_at = NOW()
                WHERE id = %s AND user_id = %s;
                """,
                (
                    reconciliation_status,
                    parsed_date,
                    (
                        None
                        if reconciliation_status == "unreconciled"
                        else session_id
                    ),
                    transaction_id,
                    user_id,
                ),
            )

            if session_id:
                _refresh_reconciliation_session_totals(
                    cur,
                    session_id,
                )

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
                WHERE user_id=%s AND transaction_date>=%s AND transaction_date<%s
                  AND COALESCE(budget_excluded, FALSE) = FALSE;
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

def dashboard_expense_kpis(
    user_id,
    month_value,
    limit=8,
):
    month = _month_start(
        month_value
    )
    next_month = _add_months(
        month,
        1,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    CASE
                        WHEN parent.id IS NULL
                        THEN category.name
                        ELSE parent.name
                             || ' › '
                             || category.name
                    END AS name,
                    SUM(transaction.amount) AS total,
                    COUNT(*) AS transaction_count
                FROM finance_transactions AS transaction
                JOIN finance_categories AS category
                    ON category.id =
                        transaction.category_id
                LEFT JOIN finance_categories AS parent
                    ON parent.id =
                        category.parent_id
                WHERE transaction.user_id = %s
                  AND transaction.transaction_type = 'expense'
                  AND transaction.status = 'confirmed'
                  AND COALESCE(transaction.budget_excluded, FALSE) = FALSE
                  AND transaction.transaction_date >= %s
                  AND transaction.transaction_date < %s
                GROUP BY
                    category.id,
                    parent.id,
                    parent.name
                ORDER BY
                    total DESC,
                    name
                LIMIT %s;
                """,
                (
                    user_id,
                    month,
                    next_month,
                    int(limit),
                ),
            )
            categories = cur.fetchall()

            cur.execute(
                """
                SELECT
                    tag.name,
                    SUM(transaction.amount) AS total,
                    COUNT(
                        DISTINCT transaction.id
                    ) AS transaction_count
                FROM finance_transactions AS transaction
                JOIN finance_transaction_tags AS transaction_tag
                    ON transaction_tag.transaction_id =
                        transaction.id
                JOIN finance_tags AS tag
                    ON tag.id =
                        transaction_tag.tag_id
                WHERE transaction.user_id = %s
                  AND transaction.transaction_type = 'expense'
                  AND transaction.status = 'confirmed'
                  AND COALESCE(transaction.budget_excluded, FALSE) = FALSE
                  AND transaction.transaction_date >= %s
                  AND transaction.transaction_date < %s
                GROUP BY
                    tag.id,
                    tag.name
                ORDER BY
                    total DESC,
                    tag.name
                LIMIT %s;
                """,
                (
                    user_id,
                    month,
                    next_month,
                    int(limit),
                ),
            )
            tags = cur.fetchall()

    return {
        "month": month,
        "categories": categories,
        "tags": tags,
    }



def _projection_row(
    *,
    transaction_date,
    transaction_type,
    amount,
    description,
    category_id=None,
    category_full_name=None,
    tag_ids=None,
    tag_names=None,
    payment_method_id=None,
    payment_method_name=None,
    recurrence_id=None,
    occurrence_date=None,
    status="planned",
    projected=False,
    budget_excluded=False,
    bank_programmed=False,
    reminder_enabled=False,
    reminder_time=None,
):
    return {
        "id": None,
        "transaction_date": transaction_date,
        "transaction_type": transaction_type,
        "amount": Decimal(amount),
        "description": description,
        "category_id": category_id,
        "category_full_name": category_full_name,
        "tag_ids": list(tag_ids or []),
        "tag_names": list(tag_names or []),
        "payment_method_id": payment_method_id,
        "payment_method_name": payment_method_name,
        "recurrence_id": recurrence_id,
        "occurrence_date": occurrence_date,
        "status": status,
        "projected": bool(projected),
        "budget_excluded": bool(budget_excluded),
        "bank_programmed": bool(bank_programmed),
        "reminder_enabled": bool(reminder_enabled),
        "reminder_time": reminder_time,
    }


def _projection_kpis(
    rows,
    transaction_type,
    limit=12,
    visible_category_ids=None,
    visible_tag_ids=None,
):
    category_values = {}
    tag_values = {}

    for row in rows:
        if row["transaction_type"] != transaction_type:
            continue
        if bool(row.get("budget_excluded")):
            continue

        amount = Decimal(row["amount"])
        bucket = (
            "upcoming"
            if row.get("projection_bucket") == "upcoming"
            else "realized"
        )

        category_id = row.get("category_id")
        category_name = (
            row.get("category_full_name")
            or "Sans catégorie"
        )
        category_key = (
            int(category_id)
            if category_id is not None
            else None
        )
        category_is_visible = (
            category_key is None
            or visible_category_ids is None
            or category_key in visible_category_ids
        )
        if category_is_visible:
            category = category_values.setdefault(
                category_key,
                {
                    "id": category_key,
                    "name": category_name,
                    "realized": Decimal("0.00"),
                    "upcoming": Decimal("0.00"),
                    "transaction_count": 0,
                },
            )
            category[bucket] += amount
            category["transaction_count"] += 1

        tag_ids = list(row.get("tag_ids") or [])
        tag_names = list(row.get("tag_names") or [])
        for index, tag_name in enumerate(tag_names):
            tag_id = (
                int(tag_ids[index])
                if index < len(tag_ids)
                and tag_ids[index] is not None
                else None
            )
            if (
                tag_id is not None
                and visible_tag_ids is not None
                and tag_id not in visible_tag_ids
            ):
                continue
            tag_key = (
                ("id", tag_id)
                if tag_id is not None
                else ("name", str(tag_name).casefold())
            )
            tag = tag_values.setdefault(
                tag_key,
                {
                    "id": tag_id,
                    "name": tag_name,
                    "realized": Decimal("0.00"),
                    "upcoming": Decimal("0.00"),
                    "transaction_count": 0,
                },
            )
            tag[bucket] += amount
            tag["transaction_count"] += 1

    def finalize(values):
        rows_out = []
        for row in values.values():
            row = dict(row)
            row["total"] = (
                Decimal(row["realized"])
                + Decimal(row["upcoming"])
            )
            rows_out.append(row)

        rows_out.sort(
            key=lambda row: (
                -row["total"],
                str(row["name"]).casefold(),
            )
        )
        return rows_out[: int(limit)]

    return {
        "categories": finalize(category_values),
        "tags": finalize(tag_values),
    }


def dashboard_month_projection(
    user_id,
    month_value,
    *,
    today_value=None,
    kpi_limit=12,
):
    """Prépare le réalisé, l'à venir et les récurrences projetées du mois."""

    month = _month_start(month_value)
    next_month = _add_months(month, 1)
    month_end = next_month - timedelta(days=1)
    today = (
        today_value
        if isinstance(today_value, date)
        else (
            date.fromisoformat(str(today_value))
            if today_value
            else date.today()
        )
    )

    existing = [
        dict(row)
        for row in list_transactions(
            user_id,
            start_date=month,
            end_date=month_end,
            limit=100000,
        )
    ]

    existing_occurrences = {
        (
            int(row["recurrence_id"]),
            row.get("occurrence_date")
            or row["transaction_date"],
        )
        for row in existing
        if row.get("recurrence_id")
    }

    projected = []
    if month_end >= today:
        for recurrence in list_recurrences(user_id):
            if not recurrence["is_active"]:
                continue

            occurrence = recurrence["next_date"]
            if not occurrence:
                occurrence = recurrence["start_date"]

            if recurrence["end_date"] and recurrence["end_date"] < month:
                continue

            while occurrence < month:
                occurrence = _next_date(
                    occurrence,
                    recurrence["frequency_unit"],
                    recurrence["frequency_interval"],
                )

            while occurrence <= month_end:
                if (
                    recurrence["end_date"]
                    and occurrence > recurrence["end_date"]
                ):
                    break

                occurrence_key = (
                    int(recurrence["id"]),
                    occurrence,
                )
                if occurrence_key not in existing_occurrences:
                    projected.append(
                        _projection_row(
                            transaction_date=occurrence,
                            transaction_type=recurrence[
                                "transaction_type"
                            ],
                            amount=recurrence["amount"],
                            description=recurrence["description"],
                            category_id=recurrence["category_id"],
                            category_full_name=recurrence[
                                "category_full_name"
                            ],
                            tag_ids=recurrence["tag_ids"],
                            tag_names=recurrence["tag_names"],
                            payment_method_id=recurrence[
                                "payment_method_id"
                            ],
                            payment_method_name=recurrence[
                                "payment_method_name"
                            ],
                            recurrence_id=recurrence["id"],
                            occurrence_date=occurrence,
                            status="planned",
                            projected=True,
                            budget_excluded=bool(
                                recurrence.get("budget_excluded")
                            ),
                            bank_programmed=bool(recurrence.get("bank_programmed")),
                            reminder_enabled=bool(recurrence.get("reminder_enabled")),
                            reminder_time=recurrence.get("reminder_time"),
                        )
                    )

                occurrence = _next_date(
                    occurrence,
                    recurrence["frequency_unit"],
                    recurrence["frequency_interval"],
                )

    combined = []
    for row in existing:
        row["projected"] = False
        is_upcoming = (
            row["status"] == "planned"
            or row["transaction_date"] > today
        )
        row["projection_bucket"] = (
            "upcoming"
            if is_upcoming
            else "realized"
        )
        combined.append(row)

    for row in projected:
        row["projection_bucket"] = "upcoming"
        combined.append(row)

    realized_expenses = sum(
        (
            Decimal(row["amount"])
            for row in combined
            if row["projection_bucket"] == "realized"
            and row["transaction_type"] == "expense"
            and not bool(row.get("budget_excluded"))
        ),
        Decimal("0.00"),
    )
    realized_incomes = sum(
        (
            Decimal(row["amount"])
            for row in combined
            if row["projection_bucket"] == "realized"
            and row["transaction_type"] == "income"
            and not bool(row.get("budget_excluded"))
        ),
        Decimal("0.00"),
    )
    upcoming_expenses = sum(
        (
            Decimal(row["amount"])
            for row in combined
            if row["projection_bucket"] == "upcoming"
            and row["transaction_type"] == "expense"
            and not bool(row.get("budget_excluded"))
        ),
        Decimal("0.00"),
    )
    upcoming_incomes = sum(
        (
            Decimal(row["amount"])
            for row in combined
            if row["projection_bucket"] == "upcoming"
            and row["transaction_type"] == "income"
            and not bool(row.get("budget_excluded"))
        ),
        Decimal("0.00"),
    )

    upcoming_rows = sorted(
        (
            row
            for row in combined
            if row["projection_bucket"] == "upcoming"
        ),
        key=lambda row: (
            row["transaction_date"],
            0 if row["transaction_type"] == "income" else 1,
            str(row["description"]).casefold(),
        ),
    )

    visible_category_ids = {
        int(row["id"])
        for row in list_categories(user_id, include_inactive=True)
        if bool(row.get("dashboard_visible", True))
    }
    visible_tag_ids = {
        int(row["id"])
        for row in list_tags(user_id, include_inactive=True)
        if bool(row.get("dashboard_visible", True))
    }

    return {
        "month": month,
        "month_end": month_end,
        "realized": {
            "expenses": realized_expenses,
            "incomes": realized_incomes,
            "difference": (
                realized_incomes
                - realized_expenses
            ),
        },
        "upcoming": {
            "expenses": upcoming_expenses,
            "incomes": upcoming_incomes,
            "difference": (
                upcoming_incomes
                - upcoming_expenses
            ),
            "count": len(upcoming_rows),
        },
        "total": {
            "expenses": (
                realized_expenses
                + upcoming_expenses
            ),
            "incomes": (
                realized_incomes
                + upcoming_incomes
            ),
            "difference": (
                realized_incomes
                + upcoming_incomes
                - realized_expenses
                - upcoming_expenses
            ),
        },
        "upcoming_transactions": upcoming_rows,
        "transactions": combined,
        "kpis": {
            "expense": _projection_kpis(
                combined,
                "expense",
                limit=kpi_limit,
                visible_category_ids=visible_category_ids,
                visible_tag_ids=visible_tag_ids,
            ),
            "income": _projection_kpis(
                combined,
                "income",
                limit=kpi_limit,
                visible_category_ids=visible_category_ids,
                visible_tag_ids=visible_tag_ids,
            ),
        },
    }


def payment_reconciliation_summary(
    user_id,
    month_value,
):
    month = _month_start(
        month_value
    )
    next_month = _add_months(
        month,
        1,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    payment_method.id
                        AS payment_method_id,
                    COALESCE(
                        payment_method.name,
                        'Sans mode de paiement'
                    ) AS payment_method_name,
                    payment_method.sort_order,
                    COALESCE(
                        SUM(transaction.amount)
                        FILTER (
                            WHERE transaction.transaction_type = 'expense'
                              AND transaction.status = 'confirmed'
                        ),
                        0
                    ) AS expense_total,
                    COALESCE(
                        SUM(transaction.amount)
                        FILTER (
                            WHERE transaction.transaction_type = 'income'
                              AND transaction.status = 'confirmed'
                        ),
                        0
                    ) AS income_total,
                    COALESCE(
                        SUM(transaction.amount)
                        FILTER (
                            WHERE transaction.reconciliation_status =
                                'unreconciled'
                              AND transaction.transaction_type =
                                'expense'
                              AND transaction.status = 'confirmed'
                        ),
                        0
                    ) AS unreconciled_expense_total,
                    COALESCE(
                        SUM(transaction.amount)
                        FILTER (
                            WHERE transaction.reconciliation_status =
                                'unreconciled'
                              AND transaction.transaction_type =
                                'income'
                              AND transaction.status = 'confirmed'
                        ),
                        0
                    ) AS unreconciled_income_total,
                    COUNT(*)
                    FILTER (
                        WHERE transaction.reconciliation_status =
                            'unreconciled'
                          AND transaction.status = 'confirmed'
                    ) AS unreconciled_count,
                    COUNT(*)
                    FILTER (
                        WHERE transaction.reconciliation_status =
                            'reconciled'
                          AND transaction.status = 'confirmed'
                    ) AS reconciled_count
                FROM finance_transactions AS transaction
                LEFT JOIN finance_payment_methods AS payment_method
                    ON payment_method.id =
                        transaction.payment_method_id
                WHERE transaction.user_id = %s
                  AND transaction.status = 'confirmed'
                  AND transaction.transaction_date >= %s
                  AND transaction.transaction_date < %s
                GROUP BY
                    payment_method.id,
                    payment_method.name,
                    payment_method.sort_order
                ORDER BY
                    payment_method.sort_order NULLS LAST,
                    payment_method.name NULLS LAST;
                """,
                (
                    user_id,
                    month,
                    next_month,
                ),
            )
            rows = cur.fetchall()

    return rows



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
    payment_method_id=None,
    note=None,
    end_date=None,
    confirmation_mode="confirm",
    budget_excluded=False,
    bank_programmed=False,
    reminder_enabled=False,
    reminder_time=None,
    recurrence_id=None,
):
    if transaction_type not in TRANSACTION_TYPES:
        raise ValueError("Type invalide.")
    if frequency_unit not in FREQUENCY_UNITS:
        raise ValueError("Fréquence invalide.")
    if confirmation_mode not in CONFIRMATION_MODES:
        raise ValueError("Mode invalide.")

    interval = int(
        frequency_interval
        or 1
    )
    if interval < 1 or interval > 365:
        raise ValueError(
            "L’intervalle doit être compris entre 1 et 365."
        )

    parsed_start = date.fromisoformat(
        str(start_date)
    )
    parsed_end = (
        date.fromisoformat(
            str(end_date)
        )
        if end_date
        else None
    )
    if (
        parsed_end
        and parsed_end < parsed_start
    ):
        raise ValueError(
            "La date de fin précède la date de début."
        )

    amount = _money(
        amount
    )
    description = _text(
        description,
        "La description",
        160,
        True,
    )
    note = _text(
        note,
        "La note",
        1000,
    )
    normalized_reminder_time = _normalize_reminder_time(reminder_time)

    with get_connection() as conn:
        with conn.cursor() as cur:
            tags = _validate_links(
                cur,
                user_id,
                category_id,
                tag_ids,
            )
            validated_payment_method = (
                _validate_payment_method(
                    cur,
                    user_id,
                    payment_method_id,
                )
            )

            if recurrence_id:
                # Les occurrences prévues sont des projections de la règle.
                # Lorsqu'on modifie la récurrence, elles sont reconstruites à
                # partir des nouvelles valeurs. Les transactions confirmées
                # restent intactes afin de préserver l'historique réel.
                cur.execute(
                    """
                    DELETE FROM finance_transactions
                    WHERE user_id=%s
                      AND recurrence_id=%s
                      AND status='planned';
                    """,
                    (user_id, recurrence_id),
                )
                cur.execute(
                    """
                    UPDATE finance_recurrences
                    SET
                        transaction_type = %s,
                        description = %s,
                        amount = %s,
                        category_id = %s,
                        payment_method_id = %s,
                        note = %s,
                        frequency_unit = %s,
                        frequency_interval = %s,
                        start_date = %s,
                        end_date = %s,
                        next_date = %s,
                        confirmation_mode = %s,
                        budget_excluded = %s,
                        bank_programmed = %s,
                        reminder_enabled = %s,
                        reminder_time = %s,
                        is_active = TRUE,
                        updated_at = NOW()
                    WHERE id = %s
                      AND user_id = %s;
                    """,
                    (
                        transaction_type,
                        description,
                        amount,
                        category_id,
                        validated_payment_method,
                        note,
                        frequency_unit,
                        interval,
                        parsed_start,
                        parsed_end,
                        parsed_start,
                        confirmation_mode,
                        bool(budget_excluded),
                        bool(bank_programmed),
                        bool(reminder_enabled),
                        normalized_reminder_time,
                        recurrence_id,
                        user_id,
                    ),
                )
                if cur.rowcount == 0:
                    raise ValueError(
                        "Récurrence introuvable."
                    )

                saved_id = int(
                    recurrence_id
                )
                cur.execute(
                    """
                    DELETE FROM finance_recurrence_tags
                    WHERE recurrence_id = %s;
                    """,
                    (saved_id,),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO finance_recurrences (
                        user_id,
                        transaction_type,
                        description,
                        amount,
                        category_id,
                        payment_method_id,
                        note,
                        frequency_unit,
                        frequency_interval,
                        start_date,
                        end_date,
                        next_date,
                        confirmation_mode,
                        budget_excluded,
                        bank_programmed,
                        reminder_enabled,
                        reminder_time
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s
                    )
                    RETURNING id;
                    """,
                    (
                        user_id,
                        transaction_type,
                        description,
                        amount,
                        category_id,
                        validated_payment_method,
                        note,
                        frequency_unit,
                        interval,
                        parsed_start,
                        parsed_end,
                        parsed_start,
                        confirmation_mode,
                        bool(budget_excluded),
                        bool(bank_programmed),
                        bool(reminder_enabled),
                        normalized_reminder_time,
                    ),
                )
                saved_id = int(
                    cur.fetchone()["id"]
                )

            for tag_id in tags:
                cur.execute(
                    """
                    INSERT INTO finance_recurrence_tags (
                        recurrence_id,
                        tag_id
                    )
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (
                        saved_id,
                        tag_id,
                    ),
                )

            _sync_budget_items_from_recurrence_cursor(
                cur, user_id, saved_id
            )
            conn.commit()
            return saved_id


def list_recurrences(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    recurrence.*,
                    payment_method.name
                        AS payment_method_name,
                    CASE
                        WHEN parent.id IS NULL
                        THEN category.name
                        ELSE parent.name
                             || ' › '
                             || category.name
                    END AS category_full_name,
                    COALESCE(
                        ARRAY_AGG(
                            tag.id
                            ORDER BY tag.name
                        )
                        FILTER (
                            WHERE tag.id IS NOT NULL
                        ),
                        ARRAY[]::BIGINT[]
                    ) AS tag_ids,
                    COALESCE(
                        ARRAY_AGG(
                            tag.name
                            ORDER BY tag.name
                        )
                        FILTER (
                            WHERE tag.id IS NOT NULL
                        ),
                        ARRAY[]::TEXT[]
                    ) AS tag_names
                FROM finance_recurrences AS recurrence
                LEFT JOIN finance_categories AS category
                    ON category.id =
                        recurrence.category_id
                LEFT JOIN finance_categories AS parent
                    ON parent.id =
                        category.parent_id
                LEFT JOIN finance_payment_methods AS payment_method
                    ON payment_method.id =
                        recurrence.payment_method_id
                LEFT JOIN finance_recurrence_tags AS recurrence_tag
                    ON recurrence_tag.recurrence_id =
                        recurrence.id
                LEFT JOIN finance_tags AS tag
                    ON tag.id =
                        recurrence_tag.tag_id
                WHERE recurrence.user_id = %s
                GROUP BY
                    recurrence.id,
                    category.id,
                    parent.id,
                    parent.name,
                    payment_method.id,
                    payment_method.name
                ORDER BY
                    recurrence.is_active DESC,
                    recurrence.next_date,
                    recurrence.description;
                """,
                (user_id,),
            )
            return cur.fetchall()


def toggle_recurrence(user_id, recurrence_id, is_active):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE finance_recurrences SET is_active=%s,updated_at=NOW()
                WHERE id=%s AND user_id=%s;
            """, (bool(is_active), recurrence_id, user_id))
            conn.commit()


def delete_recurrence(
    user_id,
    recurrence_id,
    *,
    delete_planned=True,
):
    """Supprime une règle sans réécrire l'historique confirmé."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM finance_recurrences
                WHERE id=%s AND user_id=%s
                FOR UPDATE;
                """,
                (recurrence_id, user_id),
            )
            if not cur.fetchone():
                raise ValueError("Récurrence introuvable.")

            if delete_planned:
                cur.execute(
                    """
                    DELETE FROM finance_transactions
                    WHERE user_id=%s
                      AND recurrence_id=%s
                      AND status='planned';
                    """,
                    (user_id, recurrence_id),
                )

            # Un poste Budget lié devient indépendant plutôt que d'être supprimé.
            cur.execute(
                """
                UPDATE finance_budget_items
                SET recurrence_id=NULL,
                    sync_from_recurrence=FALSE,
                    updated_at=NOW()
                WHERE user_id=%s AND recurrence_id=%s;
                """,
                (user_id, recurrence_id),
            )

            # La FK des transactions confirmées est ON DELETE SET NULL :
            # elles restent donc dans l'historique avec leur date et montant.
            cur.execute(
                """
                DELETE FROM finance_recurrences
                WHERE id=%s AND user_id=%s;
                """,
                (recurrence_id, user_id),
            )
            conn.commit()


def generate_due_recurrences(
    user_id,
    through_date=None,
    *,
    force_planned=False,
):
    through = (
        through_date
        or date.today()
    )
    created = 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM finance_recurrences
                WHERE user_id = %s
                  AND is_active = TRUE
                  AND next_date <= %s
                FOR UPDATE;
                """,
                (
                    user_id,
                    through,
                ),
            )
            rows = cur.fetchall()

            for recurrence in rows:
                cur.execute(
                    """
                    SELECT tag_id
                    FROM finance_recurrence_tags
                    WHERE recurrence_id = %s;
                    """,
                    (recurrence["id"],),
                )
                tags = [
                    row["tag_id"]
                    for row in cur.fetchall()
                ]
                occurrence = recurrence[
                    "next_date"
                ]

                while occurrence <= through:
                    if (
                        recurrence["end_date"]
                        and occurrence
                        > recurrence["end_date"]
                    ):
                        break

                    status = (
                        "planned"
                        if force_planned
                        else (
                            "confirmed"
                            if recurrence[
                                "confirmation_mode"
                            ]
                            == "automatic"
                            else "planned"
                        )
                    )

                    cur.execute(
                        """
                        INSERT INTO finance_transactions (
                            user_id,
                            transaction_date,
                            transaction_type,
                            amount,
                            description,
                            category_id,
                            payment_method_id,
                            note,
                            status,
                            reconciliation_status,
                            recurrence_id,
                            occurrence_date,
                            budget_excluded,
                            bank_programmed,
                            reminder_enabled,
                            reminder_time
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, 'unreconciled',
                            %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (
                            recurrence_id,
                            occurrence_date
                        )
                        DO NOTHING
                        RETURNING id;
                        """,
                        (
                            user_id,
                            occurrence,
                            recurrence[
                                "transaction_type"
                            ],
                            recurrence["amount"],
                            recurrence[
                                "description"
                            ],
                            recurrence[
                                "category_id"
                            ],
                            recurrence.get(
                                "payment_method_id"
                            ),
                            recurrence["note"],
                            status,
                            recurrence["id"],
                            occurrence,
                            bool(recurrence.get("budget_excluded")),
                            bool(recurrence.get("bank_programmed")),
                            bool(recurrence.get("reminder_enabled")),
                            recurrence.get("reminder_time") or _normalize_reminder_time(None),
                        ),
                    )
                    inserted = cur.fetchone()

                    if inserted:
                        created += 1
                        for tag_id in tags:
                            cur.execute(
                                """
                                INSERT INTO finance_transaction_tags (
                                    transaction_id,
                                    tag_id
                                )
                                VALUES (%s, %s)
                                ON CONFLICT DO NOTHING;
                                """,
                                (
                                    inserted["id"],
                                    tag_id,
                                ),
                            )

                    occurrence = _next_date(
                        occurrence,
                        recurrence[
                            "frequency_unit"
                        ],
                        recurrence[
                            "frequency_interval"
                        ],
                    )

                still_active = not (
                    recurrence["end_date"]
                    and occurrence
                    > recurrence["end_date"]
                )

                cur.execute(
                    """
                    UPDATE finance_recurrences
                    SET
                        next_date = %s,
                        is_active = %s,
                        updated_at = NOW()
                    WHERE id = %s;
                    """,
                    (
                        occurrence,
                        still_active,
                        recurrence["id"],
                    ),
                )

            conn.commit()

    return created



def _budget_amounts_from_values(
    input_frequency,
    input_amount,
    biweekly_override=None,
):
    amount = Decimal(input_amount).quantize(Decimal("0.01"))
    override = (
        Decimal(biweekly_override).quantize(Decimal("0.01"))
        if biweekly_override not in (None, "")
        else None
    )
    if input_frequency == "biweekly":
        biweekly = amount
        monthly = (amount * Decimal("26") / Decimal("12")).quantize(
            Decimal("0.01")
        )
    else:
        monthly = amount
        biweekly = (
            override
            if override is not None
            else (amount * Decimal("12") / Decimal("26")).quantize(
                Decimal("0.01")
            )
        )
    return monthly, biweekly


def _budget_values_from_recurrence(row):
    amount = Decimal(row["amount"]).quantize(Decimal("0.01"))
    unit = row["frequency_unit"]
    interval = int(row["frequency_interval"] or 1)
    if unit == "month" and interval == 1:
        return "monthly", amount
    if unit == "week" and interval == 2:
        return "biweekly", amount
    annual_factor = {
        "day": Decimal("365"),
        "week": Decimal("52"),
        "month": Decimal("12"),
        "year": Decimal("1"),
    }[unit] / Decimal(interval)
    monthly = (amount * annual_factor / Decimal("12")).quantize(Decimal("0.01"))
    return "monthly", monthly


def _sync_budget_items_from_recurrence_cursor(cur, user_id, recurrence_id):
    cur.execute(
        """
        SELECT id, transaction_type, amount, frequency_unit, frequency_interval
        FROM finance_recurrences
        WHERE id=%s AND user_id=%s;
        """,
        (recurrence_id, user_id),
    )
    recurrence = cur.fetchone()
    if not recurrence:
        return
    frequency, amount = _budget_values_from_recurrence(recurrence)
    cur.execute(
        """
        UPDATE finance_budget_items
        SET item_type=%s, input_frequency=%s, input_amount=%s,
            biweekly_override=CASE
                WHEN %s='biweekly' THEN NULL
                ELSE biweekly_override
            END,
            updated_at=NOW()
        WHERE user_id=%s AND recurrence_id=%s
          AND sync_from_recurrence=TRUE;
        """,
        (
            recurrence["transaction_type"], frequency, amount,
            frequency, user_id, recurrence_id,
        ),
    )


def save_budget_item(
    user_id,
    item_type,
    description,
    input_frequency,
    input_amount,
    biweekly_override=None,
    note=None,
    recurrence_id=None,
    sync_from_recurrence=True,
    budget_item_id=None,
):
    if item_type not in TRANSACTION_TYPES:
        raise ValueError("Type de poste budgétaire invalide.")
    if input_frequency not in BUDGET_INPUT_FREQUENCIES:
        raise ValueError("Fréquence budgétaire invalide.")
    description = _text(description, "La description", 160, True)
    amount = _money(input_amount)
    override = (
        _money(biweekly_override)
        if biweekly_override not in (None, "")
        else None
    )
    note = _text(note, "La note", 1000)
    if input_frequency == "biweekly":
        override = None

    normalized_recurrence_id = (
        int(recurrence_id)
        if recurrence_id not in (None, "")
        else None
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            if normalized_recurrence_id is not None:
                cur.execute(
                    """
                    SELECT id, transaction_type, amount, frequency_unit, frequency_interval
                    FROM finance_recurrences
                    WHERE id=%s AND user_id=%s;
                    """,
                    (normalized_recurrence_id, user_id),
                )
                linked = cur.fetchone()
                if not linked:
                    raise ValueError("La récurrence sélectionnée est invalide.")
                if sync_from_recurrence:
                    item_type = linked["transaction_type"]
                    input_frequency, amount = _budget_values_from_recurrence(linked)
                    if input_frequency == "biweekly":
                        override = None
                cur.execute(
                    """
                    SELECT id
                    FROM finance_budget_items
                    WHERE user_id=%s AND recurrence_id=%s
                      AND (%s IS NULL OR id<>%s)
                    LIMIT 1;
                    """,
                    (
                        user_id, normalized_recurrence_id,
                        budget_item_id, budget_item_id,
                    ),
                )
                if cur.fetchone():
                    raise ValueError(
                        "Cette récurrence est déjà liée à un autre poste du Budget."
                    )

            if budget_item_id:
                cur.execute(
                    """
                    UPDATE finance_budget_items
                    SET item_type=%s, description=%s, input_frequency=%s,
                        input_amount=%s, biweekly_override=%s, note=%s,
                        recurrence_id=%s, sync_from_recurrence=%s,
                        is_active=TRUE, updated_at=NOW()
                    WHERE id=%s AND user_id=%s;
                    """,
                    (
                        item_type, description, input_frequency, amount,
                        override, note, normalized_recurrence_id,
                        bool(sync_from_recurrence), budget_item_id, user_id,
                    ),
                )
                if cur.rowcount == 0:
                    raise ValueError("Poste budgétaire introuvable.")
            else:
                cur.execute(
                    """
                    SELECT COALESCE(MAX(sort_order),0)+1 AS next_order
                    FROM finance_budget_items
                    WHERE user_id=%s AND item_type=%s;
                    """,
                    (user_id, item_type),
                )
                next_order = int(cur.fetchone()["next_order"])
                cur.execute(
                    """
                    INSERT INTO finance_budget_items (
                        user_id, item_type, description, input_frequency,
                        input_amount, biweekly_override, note, sort_order,
                        recurrence_id, sync_from_recurrence
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
                    """,
                    (
                        user_id, item_type, description, input_frequency,
                        amount, override, note, next_order,
                        normalized_recurrence_id, bool(sync_from_recurrence),
                    ),
                )
            conn.commit()


def list_budget_items(user_id, include_inactive=False):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    budget.*,
                    recurrence.description AS recurrence_description,
                    recurrence.amount AS recurrence_amount,
                    recurrence.frequency_unit AS recurrence_frequency_unit,
                    recurrence.frequency_interval AS recurrence_frequency_interval,
                    recurrence.is_active AS recurrence_is_active
                FROM finance_budget_items AS budget
                LEFT JOIN finance_recurrences AS recurrence
                    ON recurrence.id=budget.recurrence_id
                   AND recurrence.user_id=budget.user_id
                WHERE budget.user_id=%s
                  AND (%s OR budget.is_active=TRUE)
                ORDER BY
                    CASE WHEN budget.item_type='income' THEN 0 ELSE 1 END,
                    budget.sort_order, LOWER(budget.description), budget.id;
                """,
                (user_id, include_inactive),
            )
            rows = []
            for raw in cur.fetchall():
                row = dict(raw)
                monthly, biweekly = _budget_amounts_from_values(
                    row["input_frequency"],
                    row["input_amount"],
                    row.get("biweekly_override"),
                )
                row["monthly_amount"] = monthly
                row["biweekly_amount"] = biweekly
                row["biweekly_is_override"] = (
                    row["input_frequency"] == "monthly"
                    and row.get("biweekly_override") is not None
                )
                rows.append(row)
            return rows


def toggle_budget_item(user_id, budget_item_id, is_active):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE finance_budget_items
                SET is_active=%s, updated_at=NOW()
                WHERE id=%s AND user_id=%s;
                """,
                (bool(is_active), budget_item_id, user_id),
            )
            if cur.rowcount == 0:
                raise ValueError("Poste budgétaire introuvable.")
            conn.commit()


def move_budget_item(user_id, budget_item_id, direction):
    if direction not in {"up", "down"}:
        raise ValueError("Direction invalide.")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, item_type, sort_order
                FROM finance_budget_items
                WHERE user_id=%s
                ORDER BY item_type, sort_order, id
                FOR UPDATE;
                """,
                (user_id,),
            )
            rows = cur.fetchall()
            current = next(
                (row for row in rows if int(row["id"]) == int(budget_item_id)),
                None,
            )
            if not current:
                raise ValueError("Poste budgétaire introuvable.")
            same_type = [row for row in rows if row["item_type"] == current["item_type"]]
            ids = [int(row["id"]) for row in same_type]
            index = ids.index(int(budget_item_id))
            target_index = index - 1 if direction == "up" else index + 1
            if target_index < 0 or target_index >= len(same_type):
                return
            target = same_type[target_index]
            current_order = int(current["sort_order"])
            target_order = int(target["sort_order"])
            if current_order == target_order:
                current_order = index + 1
                target_order = target_index + 1
            cur.execute(
                "UPDATE finance_budget_items SET sort_order=%s,updated_at=NOW() WHERE id=%s;",
                (target_order, current["id"]),
            )
            cur.execute(
                "UPDATE finance_budget_items SET sort_order=%s,updated_at=NOW() WHERE id=%s;",
                (current_order, target["id"]),
            )
            conn.commit()


def budget_summary(user_id):
    rows = list_budget_items(user_id)
    totals = {
        "monthly_income": Decimal("0.00"),
        "monthly_expense": Decimal("0.00"),
        "biweekly_income": Decimal("0.00"),
        "biweekly_expense": Decimal("0.00"),
    }
    for row in rows:
        key = "income" if row["item_type"] == "income" else "expense"
        totals[f"monthly_{key}"] += Decimal(row["monthly_amount"])
        totals[f"biweekly_{key}"] += Decimal(row["biweekly_amount"])
    totals["monthly_remaining"] = totals["monthly_income"] - totals["monthly_expense"]
    totals["biweekly_remaining"] = totals["biweekly_income"] - totals["biweekly_expense"]
    totals["rows"] = rows
    return totals


def list_bank_accounts(user_id, include_inactive=False):
    """Retourne les comptes suivis dans la vue Compte : banque et marge de crédit."""
    return [
        row for row in list_payment_methods(user_id, include_inactive=include_inactive)
        if row.get("method_type") in {"bank", "credit_line"}
    ]


def _bank_effective_rows(user_id, payment_method_id, end_date, today_value=None):
    today = (
        today_value if isinstance(today_value, date)
        else date.fromisoformat(str(today_value)) if today_value
        else date.today()
    )
    accounts = list_bank_accounts(user_id, include_inactive=True)
    account = next(
        (row for row in accounts if int(row["id"]) == int(payment_method_id)),
        None,
    )
    if not account:
        raise ValueError("Compte bancaire ou marge de crédit introuvable.")
    opening_date = account.get("opening_balance_date")
    if not opening_date:
        return account, [], None
    if opening_date > end_date:
        return account, [], opening_date

    existing = [
        dict(row)
        for row in list_transactions(
            user_id,
            start_date=opening_date,
            end_date=end_date,
            payment_method_id=payment_method_id,
            limit=100000,
        )
    ]
    existing_occurrences = {
        (int(row["recurrence_id"]), row.get("occurrence_date") or row["transaction_date"])
        for row in existing if row.get("recurrence_id")
    }
    rows = []
    for row in existing:
        # Les transactions prévues dont la date est passée demeurent visibles.
        # Elles représentent un mouvement encore attendu, mais ne sont pas
        # incluses dans le solde ACTUEL tant qu'elles ne sont pas confirmées.
        row["projected"] = False
        rows.append(row)

    if end_date > today:
        for recurrence in list_recurrences(user_id):
            if not recurrence["is_active"]:
                continue
            if int(recurrence.get("payment_method_id") or 0) != int(payment_method_id):
                continue
            occurrence = recurrence.get("next_date") or recurrence["start_date"]
            while occurrence <= today:
                occurrence = _next_date(
                    occurrence,
                    recurrence["frequency_unit"],
                    recurrence["frequency_interval"],
                )
            while occurrence <= end_date:
                if recurrence.get("end_date") and occurrence > recurrence["end_date"]:
                    break
                key = (int(recurrence["id"]), occurrence)
                if key not in existing_occurrences and occurrence >= opening_date:
                    rows.append(
                        _projection_row(
                            transaction_date=occurrence,
                            transaction_type=recurrence["transaction_type"],
                            amount=recurrence["amount"],
                            description=recurrence["description"],
                            category_id=recurrence.get("category_id"),
                            category_full_name=recurrence.get("category_full_name"),
                            tag_ids=recurrence.get("tag_ids"),
                            tag_names=recurrence.get("tag_names"),
                            payment_method_id=payment_method_id,
                            payment_method_name=account["name"],
                            recurrence_id=recurrence["id"],
                            occurrence_date=occurrence,
                            status="planned",
                            projected=True,
                            budget_excluded=bool(recurrence.get("budget_excluded")),
                            bank_programmed=bool(recurrence.get("bank_programmed")),
                            reminder_enabled=bool(recurrence.get("reminder_enabled")),
                            reminder_time=recurrence.get("reminder_time"),
                        )
                    )
                occurrence = _next_date(
                    occurrence,
                    recurrence["frequency_unit"],
                    recurrence["frequency_interval"],
                )
    rows.sort(
        key=lambda row: (
            row["transaction_date"],
            0 if row["transaction_type"] == "income" else 1,
            int(row.get("id") or 0),
            str(row["description"]).casefold(),
        )
    )
    return account, rows, opening_date


def _signed_transaction_amount(row, method_type="bank"):
    amount = Decimal(row["amount"])
    if method_type == "credit_line":
        # Sur une marge, une dépense augmente la dette et un revenu/remboursement
        # la réduit. Le solde affiché représente donc le montant utilisé.
        return amount if row["transaction_type"] == "expense" else -amount
    return amount if row["transaction_type"] == "income" else -amount


def bank_cashflow_month(user_id, payment_method_id, month_value, today_value=None):
    month = _month_start(month_value)
    next_month = _add_months(month, 1)
    month_end = next_month - timedelta(days=1)
    today = (
        today_value if isinstance(today_value, date)
        else date.fromisoformat(str(today_value)) if today_value
        else date.today()
    )
    account, rows, opening_date = _bank_effective_rows(
        user_id, payment_method_id, month_end, today_value=today
    )
    if not opening_date or opening_date > month_end:
        return {
            "account": account, "month": month, "month_end": month_end,
            "available": False, "opening_date": opening_date, "rows": [],
        }

    method_type = account.get("method_type") or "bank"
    opening_balance = Decimal(account.get("opening_balance") or 0)
    balance = opening_balance

    # Solde actuel = uniquement les mouvements confirmés jusqu'à aujourd'hui.
    current_balance = opening_balance if opening_date <= today else None
    if current_balance is not None:
        for row in rows:
            tx_date = row["transaction_date"]
            if tx_date > today:
                break
            if row.get("status") == "confirmed" and not row.get("projected"):
                current_balance += _signed_transaction_amount(row, method_type)

    start_balance = balance
    display_rows = []
    minimum_balance = None
    maximum_balance = None

    for row in rows:
        tx_date = row["transaction_date"]
        if tx_date < month:
            balance += _signed_transaction_amount(row, method_type)
            start_balance = balance
            continue
        if tx_date > month_end:
            continue
        balance += _signed_transaction_amount(row, method_type)
        display = dict(row)
        display["running_balance"] = balance
        display_rows.append(display)
        if minimum_balance is None or balance < minimum_balance:
            minimum_balance = balance
        if maximum_balance is None or balance > maximum_balance:
            maximum_balance = balance

    if minimum_balance is None:
        minimum_balance = start_balance
    else:
        minimum_balance = min(start_balance, minimum_balance)
    if maximum_balance is None:
        maximum_balance = start_balance
    else:
        maximum_balance = max(start_balance, maximum_balance)

    result = {
        "account": account,
        "month": month,
        "month_end": month_end,
        "available": True,
        "opening_date": opening_date,
        "start_balance": start_balance,
        "current_balance": current_balance,
        "minimum_balance": minimum_balance,
        "maximum_balance": maximum_balance,
        "end_balance": balance,
        "rows": display_rows,
        "is_credit_line": method_type == "credit_line",
    }
    if method_type == "credit_line":
        limit = account.get("credit_limit")
        limit = Decimal(limit) if limit is not None else None
        result["credit_limit"] = limit
        result["current_available_credit"] = (
            limit - current_balance
            if limit is not None and current_balance is not None
            else None
        )
        result["minimum_available_credit"] = (
            limit - maximum_balance if limit is not None else None
        )
        result["end_available_credit"] = (
            limit - balance if limit is not None else None
        )
    return result


def bank_cashflow_year_summary(user_id, payment_method_id, year, today_value=None):
    year = int(year)
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    today = (
        today_value if isinstance(today_value, date)
        else date.fromisoformat(str(today_value)) if today_value
        else date.today()
    )
    account, rows, opening_date = _bank_effective_rows(
        user_id, payment_method_id, end, today_value=today
    )
    if not opening_date or opening_date > end:
        return {"account": account, "year": year, "available": False, "months": []}
    method_type = account.get("method_type") or "bank"
    balance = Decimal(account.get("opening_balance") or 0)
    for row in rows:
        if row["transaction_date"] < start:
            balance += _signed_transaction_amount(row, method_type)
    by_month = defaultdict(list)
    for row in rows:
        if start <= row["transaction_date"] <= end:
            by_month[row["transaction_date"].month].append(row)
    months = []
    for month_number in range(1, 13):
        month_start = date(year, month_number, 1)
        month_end = date(year, month_number, monthrange(year, month_number)[1])
        if month_end < opening_date:
            months.append({
                "month": month_start,
                "month_end": month_end,
                "available": False,
                "start_balance": None,
                "minimum_balance": None,
                "maximum_balance": None,
                "end_balance": None,
            })
            continue
        start_balance = balance
        minimum = balance
        maximum = balance
        for row in by_month.get(month_number, []):
            balance += _signed_transaction_amount(row, method_type)
            minimum = min(minimum, balance)
            maximum = max(maximum, balance)
        month_row = {
            "month": month_start,
            "month_end": month_end,
            "available": True,
            "start_balance": start_balance,
            "minimum_balance": minimum,
            "maximum_balance": maximum,
            "end_balance": balance,
        }
        if method_type == "credit_line" and account.get("credit_limit") is not None:
            limit = Decimal(account["credit_limit"])
            month_row["end_available_credit"] = limit - balance
            month_row["minimum_available_credit"] = limit - maximum
        months.append(month_row)
    return {
        "account": account,
        "year": year,
        "available": True,
        "months": months,
        "is_credit_line": method_type == "credit_line",
    }

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
    realized_end = min(
        next_month,
        date.today() + timedelta(days=1),
    )

    if realized_end <= month:
        return Decimal("0.00")

    if goal["goal_type"] == "tag":
        cur.execute("""
            SELECT COALESCE(SUM(t.amount),0) AS total
            FROM finance_transactions t
            JOIN finance_transaction_tags tt ON tt.transaction_id=t.id
            WHERE t.user_id=%s AND t.transaction_type='expense'
              AND t.status='confirmed'
              AND COALESCE(t.budget_excluded, FALSE) = FALSE
              AND t.transaction_date>=%s AND t.transaction_date<%s
              AND tt.tag_id=%s;
        """, (
            goal["user_id"],
            month,
            realized_end,
            goal["tag_id"],
        ))
    else:
        cur.execute("""
            SELECT COALESCE(SUM(t.amount),0) AS total
            FROM finance_transactions t
            LEFT JOIN finance_categories c ON c.id=t.category_id
            WHERE t.user_id=%s AND t.transaction_type='expense'
              AND t.status='confirmed'
              AND COALESCE(t.budget_excluded, FALSE) = FALSE
              AND t.transaction_date>=%s AND t.transaction_date<%s
              AND (t.category_id=%s OR c.parent_id=%s);
        """, (
            goal["user_id"],
            month,
            realized_end,
            goal["category_id"],
            goal["category_id"],
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



def _normalized_header(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _row_lookup(row):
    return {_normalized_header(key): value for key, value in row.items()}


def _pick(row, *names):
    lookup = _row_lookup(row)
    for name in names:
        key = _normalized_header(name)
        if key in lookup:
            return lookup[key]
    return None


def _parse_import_amount(value):
    text = str(value or "").strip().replace("\u00a0", "").replace(" ", "")
    if not text:
        raise ValueError("Montant absent.")
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    try:
        amount = abs(Decimal(text)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Le montant est invalide.")
    if amount <= 0:
        raise ValueError("Le montant doit être supérieur à zéro.")
    return amount


def _parse_import_type(value):
    normalized = _normalized_header(value)
    if normalized in {"expense", "depense", "depenses"}:
        return "expense"
    if normalized in {"income", "revenu", "revenus"}:
        return "income"
    raise ValueError(f"Type de transaction inconnu : {value}")


def _parse_import_status(value):
    normalized = _normalized_header(value)
    if not normalized or normalized in {"confirmed", "confirmee", "confirme"}:
        return "confirmed"
    if normalized in {"planned", "prevue", "prevu", "a confirmer"}:
        return "planned"
    raise ValueError(f"Statut inconnu : {value}")

def _parse_reconciliation_status(value):
    normalized = _normalized_header(value)
    if not normalized or normalized in {
        "unreconciled",
        "a concilier",
        "non conciliee",
        "non concilie",
    }:
        return "unreconciled"
    if normalized in {
        "reconciled",
        "conciliee",
        "concilie",
    }:
        return "reconciled"
    raise ValueError(
        f"Statut de conciliation inconnu : {value}"
    )



def _parse_import_bool(value):
    if isinstance(value, bool):
        return value
    normalized = _normalized_header(value)
    return normalized in {
        "1", "true", "vrai", "oui", "yes", "hors budget", "exclue", "exclu"
    }


def _split_import_tags(value):
    if isinstance(value, list):
        candidates = value
    else:
        candidates = re.split(r"\s*[|;,]\s*", str(value or "").strip())
    result = []
    seen = set()
    for candidate in candidates:
        name = str(candidate or "").strip()
        key = name.casefold()
        if name and key not in seen:
            seen.add(key)
            result.append(name[:80])
    return result


def _stable_import_key(source, payload, occurrence):
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{digest}:{occurrence}"


def _parse_spendee_rows(rows):
    normalized_rows = []
    errors = []
    occurrence_counts = {}
    timezone = ZoneInfo("America/Toronto")

    for row_number, row in enumerate(rows, start=2):
        try:
            currency = str(_pick(row, "Currency") or "CAD").strip().upper()
            if currency and currency != "CAD":
                raise ValueError(
                    f"La devise {currency} n’est pas prise en charge par cette V1."
                )

            original_timestamp = str(_pick(row, "Date") or "").strip()
            timestamp = datetime.fromisoformat(original_timestamp.replace("Z", "+00:00"))
            if timestamp.tzinfo is not None:
                transaction_date = timestamp.astimezone(timezone).date()
            else:
                transaction_date = timestamp.date()

            category_name = str(_pick(row, "Category name") or "").strip()
            original_note = str(_pick(row, "Note") or "").strip()
            description = original_note or category_name or "Transaction importée"
            tag_names = _split_import_tags(_pick(row, "Labels"))
            transaction_type = _parse_import_type(_pick(row, "Type"))
            amount = _parse_import_amount(_pick(row, "Amount"))

            payload = {
                "date": original_timestamp,
                "wallet": str(_pick(row, "Wallet") or "").strip(),
                "type": transaction_type,
                "category": category_name,
                "amount": str(amount),
                "currency": currency,
                "note": original_note,
                "tags": tag_names,
                "author": str(_pick(row, "Author") or "").strip(),
            }
            base = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
            occurrence_counts[base] = occurrence_counts.get(base, 0) + 1

            normalized_rows.append(
                {
                    "transaction_date": transaction_date,
                    "transaction_type": transaction_type,
                    "amount": amount,
                    "description": description[:160],
                    "category_name": category_name[:100] or None,
                    "tag_names": tag_names,
                    "note": None,
                    "status": "confirmed",
                    "payment_method_name": None,
                    "reconciliation_status": "unreconciled",
                    "reconciliation_date": None,
                    "budget_excluded": False,
                    "import_source": "spendee",
                    "import_key": _stable_import_key(
                        "spendee", payload, occurrence_counts[base]
                    ),
                    "original_row": row_number,
                }
            )
        except Exception as error:
            errors.append(f"Ligne {row_number} : {error}")

    return normalized_rows, errors, "Spendee CSV"


def _parse_jf_csv_rows(rows):
    normalized_rows = []
    errors = []
    occurrence_counts = {}

    for row_number, row in enumerate(
        rows,
        start=2,
    ):
        try:
            raw_date = str(
                _pick(
                    row,
                    "Date",
                    "transaction_date",
                )
                or ""
            ).strip()

            if "T" in raw_date:
                transaction_date = (
                    datetime.fromisoformat(
                        raw_date.replace(
                            "Z",
                            "+00:00",
                        )
                    ).date()
                )
            else:
                transaction_date = (
                    date.fromisoformat(
                        raw_date
                    )
                )

            transaction_type = (
                _parse_import_type(
                    _pick(
                        row,
                        "Type",
                        "transaction_type",
                    )
                )
            )
            amount = _parse_import_amount(
                _pick(
                    row,
                    "Montant",
                    "Amount",
                    "amount",
                )
            )
            category_name = str(
                _pick(
                    row,
                    "Catégorie",
                    "Categorie",
                    "Category",
                    "category_full_name",
                )
                or ""
            ).strip()
            tag_names = _split_import_tags(
                _pick(
                    row,
                    "Étiquettes",
                    "Etiquettes",
                    "Tags",
                    "tag_names",
                )
            )
            description = str(
                _pick(
                    row,
                    "Description",
                    "description",
                )
                or category_name
                or "Transaction importée"
            ).strip()
            note = (
                str(
                    _pick(
                        row,
                        "Note",
                        "note",
                    )
                    or ""
                ).strip()
                or None
            )
            status = _parse_import_status(
                _pick(
                    row,
                    "Statut",
                    "status",
                )
            )
            payment_method_name = (
                str(
                    _pick(
                        row,
                        "Mode de paiement",
                        "Mode paiement",
                        "Payment method",
                        "payment_method_name",
                    )
                    or ""
                ).strip()
                or None
            )
            reconciliation_status = (
                _parse_reconciliation_status(
                    _pick(
                        row,
                        "Conciliation",
                        "Statut de conciliation",
                        "reconciliation_status",
                    )
                )
            )
            raw_reconciliation_date = str(
                _pick(
                    row,
                    "Date de conciliation",
                    "reconciliation_date",
                )
                or ""
            ).strip()
            reconciliation_date = (
                date.fromisoformat(
                    raw_reconciliation_date
                )
                if raw_reconciliation_date
                else None
            )
            if reconciliation_status == "unreconciled":
                reconciliation_date = None

            budget_excluded = _parse_import_bool(
                _pick(
                    row,
                    "Hors budget",
                    "Exclue du budget",
                    "Exclu du budget",
                    "budget_excluded",
                )
            )
            bank_programmed = _parse_import_bool(
                _pick(
                    row,
                    "Programmée à la banque",
                    "Programmee a la banque",
                    "bank_programmed",
                )
            )
            reminder_enabled = _parse_import_bool(
                _pick(
                    row,
                    "Rappel actif",
                    "reminder_enabled",
                )
            )
            reminder_time = _normalize_reminder_time(
                _pick(
                    row,
                    "Heure du rappel",
                    "reminder_time",
                )
                or "09:00"
            )

            source = str(
                _pick(
                    row,
                    "Source importation",
                    "import_source",
                )
                or "jf_apps_csv"
            ).strip()[:80]
            supplied_key = str(
                _pick(
                    row,
                    "Clé importation",
                    "Cle importation",
                    "import_key",
                )
                or ""
            ).strip()

            payload = {
                "date": transaction_date.isoformat(),
                "type": transaction_type,
                "amount": str(amount),
                "description": description,
                "category": category_name,
                "tags": tag_names,
                "note": note,
                "status": status,
                "payment_method": payment_method_name,
                "reconciliation_status": reconciliation_status,
                "reconciliation_date": (
                    reconciliation_date.isoformat()
                    if reconciliation_date
                    else None
                ),
            }
            base = json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
            occurrence_counts[base] = (
                occurrence_counts.get(
                    base,
                    0,
                )
                + 1
            )
            import_key = (
                supplied_key
                or _stable_import_key(
                    source,
                    payload,
                    occurrence_counts[base],
                )
            )

            normalized_rows.append(
                {
                    "transaction_date": transaction_date,
                    "transaction_type": transaction_type,
                    "amount": amount,
                    "description": description[:160],
                    "category_name": (
                        category_name[:100]
                        or None
                    ),
                    "tag_names": tag_names,
                    "note": note,
                    "status": status,
                    "payment_method_name": (
                        payment_method_name[:100]
                        if payment_method_name
                        else None
                    ),
                    "reconciliation_status": reconciliation_status,
                    "reconciliation_date": reconciliation_date,
                    "budget_excluded": budget_excluded,
                    "bank_programmed": bank_programmed,
                    "reminder_enabled": reminder_enabled,
                    "reminder_time": reminder_time,
                    "import_source": source,
                    "import_key": import_key[:180],
                    "original_row": row_number,
                }
            )
        except Exception as error:
            errors.append(
                f"Ligne {row_number} : {error}"
            )

    return (
        normalized_rows,
        errors,
        "JF Apps CSV",
    )


def _parse_jf_json(document):
    if not isinstance(document, dict) or not isinstance(document.get("transactions"), list):
        raise ValueError("Le fichier JSON ne contient pas une sauvegarde Finances reconnue.")
    rows = []
    for item in document["transactions"]:
        if isinstance(item, dict):
            rows.append(item)
    parsed, errors, _ = _parse_jf_csv_rows(rows)

    budget_items = []
    for index, item in enumerate(document.get("budget_items") or [], start=1):
        if not isinstance(item, dict):
            continue
        try:
            item_type = str(item.get("item_type") or "").strip()
            if item_type not in TRANSACTION_TYPES:
                raise ValueError("type invalide")
            input_frequency = str(item.get("input_frequency") or "monthly").strip()
            if input_frequency not in BUDGET_INPUT_FREQUENCIES:
                raise ValueError("fréquence invalide")
            budget_items.append({
                "item_type": item_type,
                "description": _text(item.get("description"), "La description", 160, True),
                "input_frequency": input_frequency,
                "input_amount": _money(item.get("input_amount")),
                "biweekly_override": (
                    _money(item.get("biweekly_override"))
                    if item.get("biweekly_override") not in (None, "")
                    else None
                ),
                "note": _text(item.get("note"), "La note", 1000),
                "sync_from_recurrence": bool(item.get("sync_from_recurrence", True)),
                "sort_order": int(item.get("sort_order") or index),
                "is_active": bool(item.get("is_active", True)),
            })
        except Exception as error:
            errors.append(f"Budget {index} : {error}")
    return parsed, errors, "JF Apps JSON", budget_items


def _csv_rows(text):
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return list(csv.DictReader(io.StringIO(text), dialect=dialect))


def _existing_import_state(user_id, rows):
    if not rows:
        return set(), set()

    keys = [row["import_key"] for row in rows if row.get("import_key")]
    sources = [row["import_source"] for row in rows if row.get("import_source")]
    start_date = min(row["transaction_date"] for row in rows)
    end_date = max(row["transaction_date"] for row in rows)

    imported = set()
    exact = set()
    with get_connection() as conn:
        with conn.cursor() as cur:
            if keys:
                cur.execute(
                    """
                    SELECT import_source, import_key
                    FROM finance_transactions
                    WHERE user_id = %s
                      AND import_key = ANY(%s)
                      AND import_source = ANY(%s);
                    """,
                    (user_id, keys, sources),
                )
                imported = {
                    (str(row["import_source"]), str(row["import_key"]))
                    for row in cur.fetchall()
                }

            cur.execute(
                """
                SELECT
                    transaction.transaction_date,
                    transaction.transaction_type,
                    transaction.amount,
                    LOWER(TRIM(transaction.description)) AS description_key,
                    LOWER(TRIM(COALESCE(
                        CASE
                            WHEN parent.id IS NULL THEN category.name
                            ELSE parent.name || ' › ' || category.name
                        END,
                        ''
                    ))) AS category_key
                FROM finance_transactions AS transaction
                LEFT JOIN finance_categories AS category
                    ON category.id = transaction.category_id
                LEFT JOIN finance_categories AS parent
                    ON parent.id = category.parent_id
                WHERE transaction.user_id = %s
                  AND transaction.transaction_date BETWEEN %s AND %s;
                """,
                (user_id, start_date, end_date),
            )
            exact = {
                (
                    row["transaction_date"],
                    row["transaction_type"],
                    Decimal(row["amount"]),
                    row["description_key"],
                    row["category_key"],
                )
                for row in cur.fetchall()
            }
    return imported, exact


def prepare_finance_import(user_id, filename, text):
    if not str(text or "").strip():
        raise ValueError("Le fichier est vide.")

    lower_name = str(filename or "").lower()
    budget_items = []
    if lower_name.endswith(".json") or str(text).lstrip().startswith("{"):
        rows, errors, format_name, budget_items = _parse_jf_json(json.loads(text))
    else:
        csv_rows = _csv_rows(text)
        if not csv_rows:
            raise ValueError("Le fichier CSV ne contient aucune transaction.")
        headers = {_normalized_header(key) for key in csv_rows[0].keys()}
        if {"wallet", "category name", "currency", "labels"}.issubset(headers):
            rows, errors, format_name = _parse_spendee_rows(csv_rows)
        else:
            rows, errors, format_name = _parse_jf_csv_rows(csv_rows)

    imported_keys, exact_keys = _existing_import_state(user_id, rows)
    already_imported = 0
    possible_duplicates = 0

    for row in rows:
        source_key = (row["import_source"], row["import_key"])
        exact_key = (
            row["transaction_date"],
            row["transaction_type"],
            Decimal(row["amount"]),
            row["description"].strip().lower(),
            str(row.get("category_name") or "").strip().lower(),
        )
        if source_key in imported_keys:
            row["duplicate_reason"] = "already_imported"
            already_imported += 1
        elif exact_key in exact_keys:
            row["duplicate_reason"] = "possible_duplicate"
            possible_duplicates += 1
        else:
            row["duplicate_reason"] = None

    return {
        "format": format_name,
        "rows": rows,
        "errors": errors,
        "total_rows": len(rows) + len(errors),
        "valid_rows": len(rows),
        "already_imported": already_imported,
        "possible_duplicates": possible_duplicates,
        "categories": sorted(
            {row["category_name"] for row in rows if row.get("category_name")},
            key=str.casefold,
        ),
        "tags": sorted(
            {
                tag
                for row in rows
                for tag in row.get(
                    "tag_names",
                    [],
                )
            },
            key=str.casefold,
        ),
        "payment_methods": sorted(
            {
                row["payment_method_name"]
                for row in rows
                if row.get(
                    "payment_method_name"
                )
            },
            key=str.casefold,
        ),
        "budget_items": budget_items,
    }


def _get_or_create_category_for_import(cur, user_id, path, transaction_type):
    if not path:
        return None, 0

    parts = [part.strip() for part in re.split(r"\s*(?:›|>)\s*", path) if part.strip()]
    parts = parts[:2]
    parent_id = None
    created = 0

    for index, name in enumerate(parts):
        cur.execute(
            """
            SELECT id, category_type
            FROM finance_categories
            WHERE user_id = %s
              AND parent_id IS NOT DISTINCT FROM %s
              AND LOWER(name) = LOWER(%s)
            LIMIT 1;
            """,
            (user_id, parent_id, name),
        )
        category = cur.fetchone()
        if category:
            category_id = int(category["id"])
            if category["category_type"] not in {transaction_type, "both"}:
                cur.execute(
                    """
                    UPDATE finance_categories
                    SET category_type = 'both', is_active = TRUE, updated_at = NOW()
                    WHERE id = %s;
                    """,
                    (category_id,),
                )
            else:
                cur.execute(
                    "UPDATE finance_categories SET is_active=TRUE WHERE id=%s;",
                    (category_id,),
                )
        else:
            cur.execute(
                """
                INSERT INTO finance_categories (
                    user_id, parent_id, name, category_type
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (user_id, parent_id, name[:100], transaction_type),
            )
            category_id = int(cur.fetchone()["id"])
            created += 1
        parent_id = category_id

    return parent_id, created


def _get_or_create_tag_for_import(cur, user_id, name):
    cur.execute(
        """
        SELECT id
        FROM finance_tags
        WHERE user_id = %s AND LOWER(name) = LOWER(%s)
        LIMIT 1;
        """,
        (user_id, name),
    )
    row = cur.fetchone()
    if row:
        tag_id = int(row["id"])
        cur.execute(
            "UPDATE finance_tags SET is_active=TRUE WHERE id=%s;",
            (tag_id,),
        )
        return tag_id, 0

    cur.execute(
        """
        INSERT INTO finance_tags (user_id, name)
        VALUES (%s, %s)
        RETURNING id;
        """,
        (user_id, name[:80]),
    )
    return int(cur.fetchone()["id"]), 1

def _get_or_create_payment_method_for_import(
    cur,
    user_id,
    name,
):
    if not name:
        return None, 0

    cur.execute(
        """
        SELECT id
        FROM finance_payment_methods
        WHERE user_id = %s
          AND LOWER(name) = LOWER(%s)
        LIMIT 1;
        """,
        (
            user_id,
            name,
        ),
    )
    row = cur.fetchone()

    if row:
        payment_method_id = int(
            row["id"]
        )
        cur.execute(
            """
            UPDATE finance_payment_methods
            SET
                is_active = TRUE,
                updated_at = NOW()
            WHERE id = %s;
            """,
            (payment_method_id,),
        )
        return payment_method_id, 0

    cur.execute(
        """
        SELECT COALESCE(
            MAX(sort_order),
            0
        ) + 1 AS next_order
        FROM finance_payment_methods
        WHERE user_id = %s;
        """,
        (user_id,),
    )
    next_order = int(
        cur.fetchone()["next_order"]
    )

    cur.execute(
        """
        INSERT INTO finance_payment_methods (
            user_id,
            name,
            sort_order
        )
        VALUES (%s, %s, %s)
        RETURNING id;
        """,
        (
            user_id,
            name[:100],
            next_order,
        ),
    )
    return (
        int(
            cur.fetchone()["id"]
        ),
        1,
    )



def import_finance_rows(
    user_id,
    rows,
    skip_possible_duplicates=True,
    budget_items=None,
):
    imported_count = 0
    skipped_count = 0
    categories_created = 0
    tags_created = 0
    payment_methods_created = 0
    budget_items_imported = 0
    failures = []

    with get_connection() as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    "SAVEPOINT finance_import_row;"
                )
                row_categories_created = 0
                row_tags_created = 0
                row_payment_methods_created = 0

                try:
                    if (
                        row.get(
                            "duplicate_reason"
                        )
                        == "already_imported"
                    ):
                        skipped_count += 1
                        cur.execute(
                            "RELEASE SAVEPOINT finance_import_row;"
                        )
                        continue

                    if (
                        skip_possible_duplicates
                        and row.get(
                            "duplicate_reason"
                        )
                        == "possible_duplicate"
                    ):
                        skipped_count += 1
                        cur.execute(
                            "RELEASE SAVEPOINT finance_import_row;"
                        )
                        continue

                    category_id, created = (
                        _get_or_create_category_for_import(
                            cur,
                            user_id,
                            row.get(
                                "category_name"
                            ),
                            row[
                                "transaction_type"
                            ],
                        )
                    )
                    row_categories_created += created

                    payment_method_id, created = (
                        _get_or_create_payment_method_for_import(
                            cur,
                            user_id,
                            row.get(
                                "payment_method_name"
                            ),
                        )
                    )
                    row_payment_methods_created += created

                    reconciliation_status = row.get(
                        "reconciliation_status"
                    ) or "unreconciled"
                    if (
                        reconciliation_status
                        not in RECONCILIATION_STATUSES
                    ):
                        reconciliation_status = "unreconciled"

                    reconciliation_date = row.get(
                        "reconciliation_date"
                    )
                    if row["status"] == "planned":
                        reconciliation_status = "unreconciled"
                        reconciliation_date = None
                    elif (
                        reconciliation_status
                        == "unreconciled"
                    ):
                        reconciliation_date = None

                    cur.execute(
                        """
                        INSERT INTO finance_transactions (
                            user_id,
                            transaction_date,
                            transaction_type,
                            amount,
                            description,
                            category_id,
                            payment_method_id,
                            note,
                            status,
                            reconciliation_status,
                            reconciliation_date,
                            budget_excluded,
                            bank_programmed,
                            reminder_enabled,
                            reminder_time,
                            import_source,
                            import_key,
                            imported_at
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                        )
                        ON CONFLICT DO NOTHING
                        RETURNING id;
                        """,
                        (
                            user_id,
                            row[
                                "transaction_date"
                            ],
                            row[
                                "transaction_type"
                            ],
                            row["amount"],
                            row[
                                "description"
                            ],
                            category_id,
                            payment_method_id,
                            row.get("note"),
                            row["status"],
                            reconciliation_status,
                            reconciliation_date,
                            bool(row.get("budget_excluded")),
                            bool(row.get("bank_programmed")) if row["status"] == "planned" else False,
                            bool(row.get("reminder_enabled")) if row["status"] == "planned" else False,
                            row.get("reminder_time") or _normalize_reminder_time(None),
                            row[
                                "import_source"
                            ],
                            row[
                                "import_key"
                            ],
                        ),
                    )
                    inserted = cur.fetchone()

                    if not inserted:
                        skipped_count += 1
                        cur.execute(
                            "ROLLBACK TO SAVEPOINT finance_import_row;"
                        )
                        cur.execute(
                            "RELEASE SAVEPOINT finance_import_row;"
                        )
                        continue

                    transaction_id = int(
                        inserted["id"]
                    )

                    for tag_name in row.get(
                        "tag_names",
                        [],
                    ):
                        tag_id, created = (
                            _get_or_create_tag_for_import(
                                cur,
                                user_id,
                                tag_name,
                            )
                        )
                        row_tags_created += created

                        cur.execute(
                            """
                            INSERT INTO finance_transaction_tags (
                                transaction_id,
                                tag_id
                            )
                            VALUES (%s, %s)
                            ON CONFLICT DO NOTHING;
                            """,
                            (
                                transaction_id,
                                tag_id,
                            ),
                        )

                    imported_count += 1
                    categories_created += (
                        row_categories_created
                    )
                    tags_created += (
                        row_tags_created
                    )
                    payment_methods_created += (
                        row_payment_methods_created
                    )

                    cur.execute(
                        "RELEASE SAVEPOINT finance_import_row;"
                    )
                except Exception as error:
                    cur.execute(
                        "ROLLBACK TO SAVEPOINT finance_import_row;"
                    )
                    cur.execute(
                        "RELEASE SAVEPOINT finance_import_row;"
                    )
                    failures.append(
                        (
                            "Ligne "
                            f"{row.get('original_row', '?')} "
                            f": {error}"
                        )
                    )
                    continue

            for item in budget_items or []:
                try:
                    cur.execute(
                        """
                        SELECT id
                        FROM finance_budget_items
                        WHERE user_id=%s
                          AND item_type=%s
                          AND LOWER(TRIM(description))=LOWER(TRIM(%s))
                        ORDER BY id
                        LIMIT 1;
                        """,
                        (user_id, item["item_type"], item["description"]),
                    )
                    existing = cur.fetchone()
                    if existing:
                        cur.execute(
                            """
                            UPDATE finance_budget_items
                            SET input_frequency=%s,input_amount=%s,biweekly_override=%s,
                                note=%s,recurrence_id=NULL,sync_from_recurrence=%s,
                                sort_order=%s,is_active=%s,updated_at=NOW()
                            WHERE id=%s AND user_id=%s;
                            """,
                            (
                                item["input_frequency"], item["input_amount"],
                                item.get("biweekly_override"), item.get("note"),
                                bool(item.get("sync_from_recurrence", True)),
                                item.get("sort_order") or 0, bool(item.get("is_active", True)),
                                existing["id"], user_id,
                            ),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO finance_budget_items (
                                user_id,item_type,description,input_frequency,input_amount,
                                biweekly_override,note,sort_order,is_active,
                                recurrence_id,sync_from_recurrence
                            )
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,%s);
                            """,
                            (
                                user_id,item["item_type"],item["description"],
                                item["input_frequency"],item["input_amount"],
                                item.get("biweekly_override"),item.get("note"),
                                item.get("sort_order") or 0,bool(item.get("is_active", True)),
                                bool(item.get("sync_from_recurrence", True)),
                            ),
                        )
                    budget_items_imported += 1
                except Exception as error:
                    failures.append(f"Budget : {item.get('description', '?')} : {error}")

            conn.commit()

    return {
        "imported": imported_count,
        "skipped": skipped_count,
        "categories_created": categories_created,
        "tags_created": tags_created,
        "payment_methods_created": payment_methods_created,
        "budget_items_imported": budget_items_imported,
        "failures": failures,
    }



def payment_predicted_balance_summary(user_id):
    """Soldes cumulatifs sans remise à zéro mensuelle."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    method.id AS payment_method_id,
                    method.name AS payment_method_name,
                    method.method_type,
                    method.statement_day,
                    method.payment_day,
                    method.opening_balance,
                    method.opening_balance_date,
                    method.opening_balance_reconciled,
                    method.is_active,
                    method.sort_order,
                    CASE
                        WHEN method.opening_balance_reconciled = FALSE
                        THEN method.opening_balance
                        ELSE 0
                    END AS opening_balance_pending,
                    COALESCE(
                        SUM(transaction.amount) FILTER (
                            WHERE transaction.reconciliation_status = 'unreconciled'
                              AND transaction.status = 'confirmed'
                              AND transaction.transaction_type = 'expense'
                        ),
                        0
                    ) AS confirmed_expenses,
                    COALESCE(
                        SUM(transaction.amount) FILTER (
                            WHERE transaction.reconciliation_status = 'unreconciled'
                              AND transaction.status = 'confirmed'
                              AND transaction.transaction_type = 'income'
                        ),
                        0
                    ) AS confirmed_incomes,
                    COALESCE(
                        SUM(transaction.amount) FILTER (
                            WHERE transaction.reconciliation_status = 'unreconciled'
                              AND transaction.status = 'planned'
                              AND transaction.transaction_type = 'expense'
                        ),
                        0
                    ) AS planned_expenses,
                    COALESCE(
                        SUM(transaction.amount) FILTER (
                            WHERE transaction.reconciliation_status = 'unreconciled'
                              AND transaction.status = 'planned'
                              AND transaction.transaction_type = 'income'
                        ),
                        0
                    ) AS planned_incomes,
                    COUNT(transaction.id) FILTER (
                        WHERE transaction.reconciliation_status = 'unreconciled'
                          AND transaction.status = 'confirmed'
                    ) AS confirmed_count,
                    COUNT(transaction.id) FILTER (
                        WHERE transaction.reconciliation_status = 'unreconciled'
                          AND transaction.status = 'planned'
                    ) AS planned_count,
                    MIN(transaction.transaction_date) FILTER (
                        WHERE transaction.reconciliation_status = 'unreconciled'
                          AND transaction.status = 'confirmed'
                    ) AS oldest_unreconciled_date,
                    (
                        SELECT MAX(session.reconciliation_date)
                        FROM finance_reconciliation_sessions AS session
                        WHERE session.user_id = method.user_id
                          AND session.payment_method_id = method.id
                          AND session.status = 'completed'
                    ) AS last_reconciliation_date
                FROM finance_payment_methods AS method
                LEFT JOIN finance_transactions AS transaction
                    ON transaction.user_id = method.user_id
                   AND transaction.payment_method_id = method.id
                WHERE method.user_id = %s
                GROUP BY method.id
                ORDER BY
                    method.is_active DESC,
                    method.sort_order,
                    LOWER(method.name),
                    method.id;
                """,
                (user_id,),
            )
            rows = cur.fetchall()

    result = []
    for row in rows:
        current_balance = (
            Decimal(row["opening_balance_pending"])
            + Decimal(row["confirmed_expenses"])
            - Decimal(row["confirmed_incomes"])
        )
        planned_impact = (
            Decimal(row["planned_expenses"])
            - Decimal(row["planned_incomes"])
        )
        result.append(
            {
                **dict(row),
                "current_balance": current_balance,
                "planned_impact": planned_impact,
                "predicted_balance": current_balance + planned_impact,
            }
        )
    return result


def count_unassigned_confirmed_transactions(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS total
                FROM finance_transactions
                WHERE user_id = %s
                  AND status = 'confirmed'
                  AND payment_method_id IS NULL;
                """,
                (user_id,),
            )
            return int(cur.fetchone()["total"])


def list_unreconciled_transactions(
    user_id,
    payment_method_id,
    start_date=None,
    end_date=None,
    query=None,
):
    return list_transactions(
        user_id,
        start_date=start_date,
        end_date=end_date,
        status="confirmed",
        payment_method_id=payment_method_id,
        reconciliation_status="unreconciled",
        query=query,
        limit=10000,
    )


def bulk_assign_payment_method(
    user_id,
    transaction_ids,
    payment_method_id,
):
    ids = sorted({int(value) for value in (transaction_ids or [])})
    if not ids:
        raise ValueError("Sélectionnez au moins une transaction.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            validated_method = _validate_payment_method(
                cur,
                user_id,
                payment_method_id,
            )
            cur.execute(
                """
                UPDATE finance_transactions
                SET payment_method_id = %s,
                    updated_at = NOW()
                WHERE user_id = %s
                  AND id = ANY(%s);
                """,
                (validated_method, user_id, ids),
            )
            if cur.rowcount != len(ids):
                raise ValueError(
                    "Certaines transactions sélectionnées sont introuvables."
                )
            conn.commit()
    return len(ids)


def list_unassigned_transactions(
    user_id,
    query=None,
    limit=500,
):
    rows = list_transactions(
        user_id,
        status="confirmed",
        query=query,
        limit=max(int(limit) * 5, 1000),
    )
    return [
        row
        for row in rows
        if row["payment_method_id"] is None
    ][: int(limit)]


def create_reconciliation_session(
    user_id,
    payment_method_id,
    transaction_ids,
    statement_date,
    statement_balance=None,
    due_date=None,
    reconciliation_date=None,
    note=None,
    include_opening_balance=False,
):
    ids = sorted({int(value) for value in (transaction_ids or [])})
    parsed_statement_date = (
        statement_date
        if isinstance(statement_date, date)
        else date.fromisoformat(str(statement_date))
    )
    parsed_due_date = (
        due_date
        if isinstance(due_date, date)
        else (
            date.fromisoformat(str(due_date))
            if due_date
            else None
        )
    )
    parsed_reconciliation_date = (
        reconciliation_date
        if isinstance(reconciliation_date, date)
        else (
            date.fromisoformat(str(reconciliation_date))
            if reconciliation_date
            else date.today()
        )
    )
    parsed_statement_balance = _decimal_value(
        statement_balance,
        "Le solde du relevé",
        allow_blank=True,
    )
    cleaned_note = _text(note, "La note", 1000)

    with get_connection() as conn:
        with conn.cursor() as cur:
            payment_method_id = _validate_payment_method(
                cur,
                user_id,
                payment_method_id,
            )
            cur.execute(
                """
                SELECT *
                FROM finance_payment_methods
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
                """,
                (payment_method_id, user_id),
            )
            method = cur.fetchone()
            if not method:
                raise ValueError("Mode de paiement introuvable.")

            opening_amount = Decimal("0.00")
            if include_opening_balance:
                if method["opening_balance_reconciled"]:
                    raise ValueError(
                        "Le solde initial est déjà concilié."
                    )
                opening_amount = Decimal(method["opening_balance"])
                if opening_amount == 0:
                    include_opening_balance = False

            transaction_total = Decimal("0.00")
            if ids:
                cur.execute(
                    """
                    SELECT id, transaction_type, amount
                    FROM finance_transactions
                    WHERE user_id = %s
                      AND payment_method_id = %s
                      AND id = ANY(%s)
                      AND status = 'confirmed'
                      AND reconciliation_status = 'unreconciled'
                    FOR UPDATE;
                    """,
                    (user_id, payment_method_id, ids),
                )
                selected = cur.fetchall()
                if len(selected) != len(ids):
                    raise ValueError(
                        "Une transaction sélectionnée n’est plus disponible "
                        "pour cette conciliation."
                    )
                for row in selected:
                    transaction_total += (
                        Decimal(row["amount"])
                        if row["transaction_type"] == "expense"
                        else -Decimal(row["amount"])
                    )

            if not ids and not include_opening_balance:
                raise ValueError(
                    "Sélectionnez au moins une transaction "
                    "ou le solde initial."
                )

            selected_total = transaction_total + opening_amount
            difference = (
                parsed_statement_balance - selected_total
                if parsed_statement_balance is not None
                else None
            )

            cur.execute(
                """
                INSERT INTO finance_reconciliation_sessions (
                    user_id,
                    payment_method_id,
                    statement_date,
                    statement_balance,
                    due_date,
                    reconciliation_date,
                    note,
                    selected_total,
                    difference,
                    included_opening_balance,
                    opening_balance_amount
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                RETURNING id;
                """,
                (
                    user_id,
                    payment_method_id,
                    parsed_statement_date,
                    parsed_statement_balance,
                    parsed_due_date,
                    parsed_reconciliation_date,
                    cleaned_note,
                    selected_total,
                    difference,
                    bool(include_opening_balance),
                    opening_amount,
                ),
            )
            session_id = int(cur.fetchone()["id"])

            for transaction_id in ids:
                cur.execute(
                    """
                    INSERT INTO finance_reconciliation_session_transactions (
                        session_id,
                        transaction_id
                    )
                    VALUES (%s, %s);
                    """,
                    (session_id, transaction_id),
                )

            if ids:
                cur.execute(
                    """
                    UPDATE finance_transactions
                    SET reconciliation_status = 'reconciled',
                        reconciliation_date = %s,
                        reconciliation_session_id = %s,
                        updated_at = NOW()
                    WHERE user_id = %s
                      AND id = ANY(%s);
                    """,
                    (
                        parsed_reconciliation_date,
                        session_id,
                        user_id,
                        ids,
                    ),
                )

            if include_opening_balance:
                cur.execute(
                    """
                    UPDATE finance_payment_methods
                    SET opening_balance_reconciled = TRUE,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s;
                    """,
                    (payment_method_id, user_id),
                )

            conn.commit()

    return {
        "session_id": session_id,
        "selected_total": selected_total,
        "difference": difference,
        "transaction_count": len(ids),
    }


def list_reconciliation_sessions(
    user_id,
    payment_method_id=None,
    include_cancelled=True,
    limit=100,
):
    conditions = ["session.user_id = %s"]
    params = [user_id]
    if payment_method_id:
        conditions.append("session.payment_method_id = %s")
        params.append(payment_method_id)
    if not include_cancelled:
        conditions.append("session.status = 'completed'")
    params.append(int(limit))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    session.*,
                    method.name AS payment_method_name,
                    COUNT(link.transaction_id)
                        FILTER (WHERE link.is_active = TRUE)
                        AS active_transaction_count,
                    COUNT(link.transaction_id)
                        FILTER (WHERE link.is_active = FALSE)
                        AS removed_transaction_count
                FROM finance_reconciliation_sessions AS session
                JOIN finance_payment_methods AS method
                    ON method.id = session.payment_method_id
                LEFT JOIN finance_reconciliation_session_transactions AS link
                    ON link.session_id = session.id
                WHERE {" AND ".join(conditions)}
                GROUP BY session.id, method.id
                ORDER BY
                    session.statement_date DESC,
                    session.id DESC
                LIMIT %s;
                """,
                params,
            )
            return cur.fetchall()


def get_reconciliation_session(
    user_id,
    session_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    session.*,
                    method.name AS payment_method_name
                FROM finance_reconciliation_sessions AS session
                JOIN finance_payment_methods AS method
                    ON method.id = session.payment_method_id
                WHERE session.id = %s
                  AND session.user_id = %s;
                """,
                (session_id, user_id),
            )
            session = cur.fetchone()
            if not session:
                raise ValueError("Séance de conciliation introuvable.")

            cur.execute(
                """
                SELECT
                    transaction.id,
                    transaction.transaction_date,
                    transaction.transaction_type,
                    transaction.amount,
                    transaction.description,
                    transaction.reconciliation_date,
                    link.is_active,
                    link.removed_at
                FROM finance_reconciliation_session_transactions AS link
                JOIN finance_transactions AS transaction
                    ON transaction.id = link.transaction_id
                WHERE link.session_id = %s
                ORDER BY
                    transaction.transaction_date,
                    transaction.id;
                """,
                (session_id,),
            )
            transactions = cur.fetchall()

    return {
        "session": session,
        "transactions": transactions,
    }


def remove_transaction_from_reconciliation_session(
    user_id,
    session_id,
    transaction_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status
                FROM finance_reconciliation_sessions
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
                """,
                (session_id, user_id),
            )
            session = cur.fetchone()
            if not session:
                raise ValueError("Séance de conciliation introuvable.")
            if session["status"] != "completed":
                raise ValueError("Cette séance est déjà annulée.")

            cur.execute(
                """
                UPDATE finance_reconciliation_session_transactions
                SET is_active = FALSE,
                    removed_at = NOW()
                WHERE session_id = %s
                  AND transaction_id = %s
                  AND is_active = TRUE;
                """,
                (session_id, transaction_id),
            )
            if cur.rowcount == 0:
                raise ValueError(
                    "Cette transaction ne fait plus partie de la séance."
                )

            cur.execute(
                """
                UPDATE finance_transactions
                SET reconciliation_status = 'unreconciled',
                    reconciliation_date = NULL,
                    reconciliation_session_id = NULL,
                    updated_at = NOW()
                WHERE id = %s
                  AND user_id = %s;
                """,
                (transaction_id, user_id),
            )
            _refresh_reconciliation_session_totals(cur, session_id)
            conn.commit()


def cancel_reconciliation_session(
    user_id,
    session_id,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM finance_reconciliation_sessions
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
                """,
                (session_id, user_id),
            )
            session = cur.fetchone()
            if not session:
                raise ValueError("Séance de conciliation introuvable.")
            if session["status"] == "cancelled":
                raise ValueError("Cette séance est déjà annulée.")

            cur.execute(
                """
                SELECT transaction_id
                FROM finance_reconciliation_session_transactions
                WHERE session_id = %s
                  AND is_active = TRUE;
                """,
                (session_id,),
            )
            ids = [int(row["transaction_id"]) for row in cur.fetchall()]

            if ids:
                cur.execute(
                    """
                    UPDATE finance_transactions
                    SET reconciliation_status = 'unreconciled',
                        reconciliation_date = NULL,
                        reconciliation_session_id = NULL,
                        updated_at = NOW()
                    WHERE user_id = %s
                      AND id = ANY(%s);
                    """,
                    (user_id, ids),
                )
                cur.execute(
                    """
                    UPDATE finance_reconciliation_session_transactions
                    SET is_active = FALSE,
                        removed_at = NOW()
                    WHERE session_id = %s
                      AND is_active = TRUE;
                    """,
                    (session_id,),
                )

            if session["included_opening_balance"]:
                cur.execute(
                    """
                    UPDATE finance_payment_methods
                    SET opening_balance_reconciled = FALSE,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s;
                    """,
                    (session["payment_method_id"], user_id),
                )

            cur.execute(
                """
                UPDATE finance_reconciliation_sessions
                SET status = 'cancelled',
                    cancelled_at = NOW()
                WHERE id = %s;
                """,
                (session_id,),
            )
            conn.commit()


def list_reconciliation_session_links(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    link.*,
                    session.user_id
                FROM finance_reconciliation_session_transactions AS link
                JOIN finance_reconciliation_sessions AS session
                    ON session.id = link.session_id
                WHERE session.user_id = %s
                ORDER BY link.session_id, link.transaction_id;
                """,
                (user_id,),
            )
            return cur.fetchall()


def export_finances(user_id):
    transactions = list_transactions(
        user_id,
        limit=100000,
    )
    categories = list_categories(
        user_id,
        include_inactive=True,
    )
    tags = list_tags(
        user_id,
        include_inactive=True,
    )
    payment_methods = list_payment_methods(
        user_id,
        include_inactive=True,
    )
    recurrences = list_recurrences(
        user_id
    )
    goals = list_goals(
        user_id
    )
    budget_items = list_budget_items(
        user_id,
        include_inactive=True,
    )
    reconciliation_sessions = list_reconciliation_sessions(
        user_id,
        include_cancelled=True,
        limit=100000,
    )
    reconciliation_session_links = list_reconciliation_session_links(
        user_id
    )

    csv_buffer = io.StringIO()
    writer = csv.writer(
        csv_buffer
    )
    writer.writerow(
        [
            "Date",
            "Type",
            "Description",
            "Montant",
            "Catégorie",
            "Étiquettes",
            "Mode de paiement",
            "Note",
            "Statut",
            "Conciliation",
            "Date de conciliation",
            "Hors budget",
            "Programmée à la banque",
            "Rappel actif",
            "Heure du rappel",
            "Récurrence",
            "Source importation",
            "Clé importation",
            "Séance de conciliation",
        ]
    )

    for row in reversed(
        transactions
    ):
        writer.writerow(
            [
                row[
                    "transaction_date"
                ].isoformat(),
                TRANSACTION_TYPES[
                    row[
                        "transaction_type"
                    ]
                ],
                row["description"],
                str(row["amount"]),
                row[
                    "category_full_name"
                ]
                or "",
                " | ".join(
                    row[
                        "tag_names"
                    ]
                    or []
                ),
                row.get(
                    "payment_method_name"
                )
                or "",
                row["note"]
                or "",
                TRANSACTION_STATUSES[
                    row["status"]
                ],
                RECONCILIATION_STATUSES.get(
                    row.get(
                        "reconciliation_status"
                    )
                    or "unreconciled",
                    "À concilier",
                ),
                (
                    row[
                        "reconciliation_date"
                    ].isoformat()
                    if row.get(
                        "reconciliation_date"
                    )
                    else ""
                ),
                (
                    "Oui"
                    if row.get("budget_excluded")
                    else "Non"
                ),
                (
                    "Oui"
                    if row.get("bank_programmed")
                    else "Non"
                ),
                (
                    "Oui"
                    if row.get("reminder_enabled")
                    else "Non"
                ),
                str(row.get("reminder_time") or "")[:5],
                (
                    "Oui"
                    if row[
                        "recurrence_id"
                    ]
                    else "Non"
                ),
                row.get(
                    "import_source"
                )
                or "jf_apps",
                row.get(
                    "import_key"
                )
                or "",
                row.get(
                    "reconciliation_session_id"
                )
                or "",
            ]
        )

    def serial(value):
        if isinstance(
            value,
            (
                date,
                datetime,
                time,
                Decimal,
            ),
        ):
            return str(
                value
            )
        if isinstance(
            value,
            list,
        ):
            return [
                serial(item)
                for item in value
            ]
        if isinstance(
            value,
            dict,
        ):
            return {
                key: serial(item)
                for key, item
                in value.items()
            }
        return value

    payload = {
        "format": "JF Apps Finances",
        "version": "1.7.0",
        "categories": [
            serial(
                dict(row)
            )
            for row in categories
        ],
        "tags": [
            serial(
                dict(row)
            )
            for row in tags
        ],
        "payment_methods": [
            serial(
                dict(row)
            )
            for row in payment_methods
        ],
        "transactions": [
            serial(
                dict(row)
            )
            for row in transactions
        ],
        "recurrences": [
            serial(
                dict(row)
            )
            for row in recurrences
        ],
        "goals": [
            serial(
                dict(row)
            )
            for row in goals
        ],
        "budget_items": [
            serial(dict(row))
            for row in budget_items
        ],
        "reconciliation_sessions": [
            serial(dict(row))
            for row in reconciliation_sessions
        ],
        "reconciliation_session_transactions": [
            serial(dict(row))
            for row in reconciliation_session_links
        ],
    }

    return (
        csv_buffer.getvalue().encode(
            "utf-8-sig"
        ),
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ).encode(
            "utf-8"
        ),
    )
