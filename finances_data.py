from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_HALF_UP
import csv
import hashlib
import io
import json
import re
import unicodedata
from zoneinfo import ZoneInfo

from db import get_connection
from finances_shared_loans_data import (
    SHARED_LOAN_PERMISSIONS,
    SHARED_LOAN_ROLES,
    add_shared_loan_event,
    get_shared_loan,
    list_available_loan_participants,
    list_shared_loans,
    save_shared_loan,
    shared_loan_amortization_preview,
)
from finances_validation import (
    decimal_value as _decimal_value,
    money as _money,
    optional_date as _optional_date_value,
    text_value as _text,
)
from finances_calculations import (
    add_months as _add_months,
    analyze_installment_progress,
    automatic_installment_amount as _automatic_installment_amount,
    month_start as _month_start,
    next_date as _next_date,
    periods_per_year as _periods_per_year,
    recurrence_dates_between as _recurrence_dates_between,
)


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








def _normalize_reminder_time(value):
    text = str(value or "09:00").strip()[:5]
    try:
        parsed = datetime.strptime(text, "%H:%M").time()
    except ValueError as error:
        raise ValueError("L’heure du rappel est invalide.") from error
    return parsed








def _init_finances_schema_v190():
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
                CREATE TABLE IF NOT EXISTS finance_linked_transfers (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id) ON DELETE CASCADE,
                    transfer_type TEXT NOT NULL DEFAULT 'credit_card_payment'
                        CHECK (transfer_type IN ('credit_card_payment')),
                    source_payment_method_id BIGINT NOT NULL
                        REFERENCES finance_payment_methods(id) ON DELETE RESTRICT,
                    destination_payment_method_id BIGINT NOT NULL
                        REFERENCES finance_payment_methods(id) ON DELETE RESTRICT,
                    amount NUMERIC(14,2) NOT NULL CHECK (amount > 0),
                    source_date DATE NOT NULL,
                    destination_date DATE NOT NULL,
                    description TEXT NOT NULL,
                    note TEXT,
                    status TEXT NOT NULL DEFAULT 'planned'
                        CHECK (status IN ('confirmed', 'planned')),
                    bank_programmed BOOLEAN NOT NULL DEFAULT FALSE,
                    reminder_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                    reminder_time TIME NOT NULL DEFAULT '09:00',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CHECK (source_payment_method_id <> destination_payment_method_id)
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS finance_linked_transfers_user_date_idx
                ON finance_linked_transfers (
                    user_id, source_date DESC, id DESC
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
                ALTER TABLE finance_transactions
                ADD COLUMN IF NOT EXISTS linked_transfer_id BIGINT;
            """)
            cur.execute("""
                ALTER TABLE finance_transactions
                ADD COLUMN IF NOT EXISTS linked_transfer_role TEXT;
            """)
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname =
                            'finance_transactions_linked_transfer_fk'
                    ) THEN
                        ALTER TABLE finance_transactions
                        ADD CONSTRAINT
                            finance_transactions_linked_transfer_fk
                        FOREIGN KEY (linked_transfer_id)
                        REFERENCES finance_linked_transfers(id)
                        ON DELETE CASCADE;
                    END IF;
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname =
                            'finance_transactions_linked_transfer_role_ck'
                    ) THEN
                        ALTER TABLE finance_transactions
                        ADD CONSTRAINT
                            finance_transactions_linked_transfer_role_ck
                        CHECK (
                            linked_transfer_role IS NULL
                            OR linked_transfer_role IN ('source', 'destination')
                        );
                    END IF;
                END
                $$;
            """)
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                finance_transactions_linked_transfer_role_uq
                ON finance_transactions (
                    linked_transfer_id, linked_transfer_role
                )
                WHERE linked_transfer_id IS NOT NULL
                  AND linked_transfer_role IS NOT NULL;
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
            # V1.9.0 — référence de relevé et traitement explicite des écarts.
            # Les ALTER sont idempotents pour les bases déjà en production.
            cur.execute("""
                ALTER TABLE finance_reconciliation_sessions
                ADD COLUMN IF NOT EXISTS reference_balance NUMERIC(14,2);
            """)
            cur.execute("""
                ALTER TABLE finance_reconciliation_sessions
                ADD COLUMN IF NOT EXISTS reference_date DATE;
            """)
            cur.execute("""
                ALTER TABLE finance_reconciliation_sessions
                ADD COLUMN IF NOT EXISTS expected_balance NUMERIC(14,2);
            """)
            cur.execute("""
                ALTER TABLE finance_reconciliation_sessions
                ADD COLUMN IF NOT EXISTS closing_reference_balance NUMERIC(14,2);
            """)
            cur.execute("""
                ALTER TABLE finance_reconciliation_sessions
                ADD COLUMN IF NOT EXISTS difference_resolution TEXT
                    NOT NULL DEFAULT 'legacy';
            """)
            cur.execute("""
                ALTER TABLE finance_reconciliation_sessions
                ADD COLUMN IF NOT EXISTS difference_explanation TEXT;
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



def _validate_card_payment_methods(
    cur,
    user_id,
    source_payment_method_id,
    destination_payment_method_id,
):
    source_id = _validate_payment_method(
        cur,
        user_id,
        source_payment_method_id,
    )
    destination_id = _validate_payment_method(
        cur,
        user_id,
        destination_payment_method_id,
    )
    if source_id is None:
        raise ValueError("Choisissez le compte bancaire de départ.")
    if destination_id is None:
        raise ValueError("Choisissez la carte de crédit à payer.")
    if source_id == destination_id:
        raise ValueError("Le compte de départ et la carte doivent être différents.")

    cur.execute(
        """
        SELECT id, name, method_type
        FROM finance_payment_methods
        WHERE user_id = %s
          AND id = ANY(%s);
        """,
        (user_id, [source_id, destination_id]),
    )
    methods = {
        int(row["id"]): dict(row)
        for row in cur.fetchall()
    }
    source = methods.get(source_id)
    destination = methods.get(destination_id)
    if not source or source.get("method_type") != "bank":
        raise ValueError(
            "Le compte de départ doit être un mode de paiement de type Compte bancaire."
        )
    if not destination or destination.get("method_type") != "credit_card":
        raise ValueError(
            "Le compte destinataire doit être un mode de paiement de type Carte de crédit."
        )
    return source, destination


def get_card_payment_transfer(user_id, transfer_id):
    if not transfer_id:
        return None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    transfer.*,
                    source.name AS source_payment_method_name,
                    destination.name AS destination_payment_method_name,
                    source_transaction.id AS source_transaction_id,
                    source_transaction.reconciliation_status
                        AS source_reconciliation_status,
                    destination_transaction.id AS destination_transaction_id,
                    destination_transaction.reconciliation_status
                        AS destination_reconciliation_status
                FROM finance_linked_transfers AS transfer
                JOIN finance_payment_methods AS source
                    ON source.id = transfer.source_payment_method_id
                JOIN finance_payment_methods AS destination
                    ON destination.id = transfer.destination_payment_method_id
                LEFT JOIN finance_transactions AS source_transaction
                    ON source_transaction.linked_transfer_id = transfer.id
                   AND source_transaction.linked_transfer_role = 'source'
                LEFT JOIN finance_transactions AS destination_transaction
                    ON destination_transaction.linked_transfer_id = transfer.id
                   AND destination_transaction.linked_transfer_role = 'destination'
                WHERE transfer.id = %s
                  AND transfer.user_id = %s
                  AND transfer.transfer_type = 'credit_card_payment';
                """,
                (transfer_id, user_id),
            )
            row = cur.fetchone()
    return dict(row) if row else None


def list_card_payment_transfers(user_id, limit=10000):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    transfer.*,
                    source.name AS source_payment_method_name,
                    destination.name AS destination_payment_method_name,
                    source_transaction.id AS source_transaction_id,
                    source_transaction.reconciliation_status
                        AS source_reconciliation_status,
                    destination_transaction.id AS destination_transaction_id,
                    destination_transaction.reconciliation_status
                        AS destination_reconciliation_status
                FROM finance_linked_transfers AS transfer
                JOIN finance_payment_methods AS source
                    ON source.id = transfer.source_payment_method_id
                JOIN finance_payment_methods AS destination
                    ON destination.id = transfer.destination_payment_method_id
                LEFT JOIN finance_transactions AS source_transaction
                    ON source_transaction.linked_transfer_id = transfer.id
                   AND source_transaction.linked_transfer_role = 'source'
                LEFT JOIN finance_transactions AS destination_transaction
                    ON destination_transaction.linked_transfer_id = transfer.id
                   AND destination_transaction.linked_transfer_role = 'destination'
                WHERE transfer.user_id = %s
                  AND transfer.transfer_type = 'credit_card_payment'
                ORDER BY transfer.source_date DESC, transfer.id DESC
                LIMIT %s;
                """,
                (user_id, int(limit)),
            )
            return [dict(row) for row in cur.fetchall()]


def save_card_payment_transfer(
    user_id,
    source_payment_method_id,
    destination_payment_method_id,
    amount,
    source_date,
    destination_date=None,
    description=None,
    note=None,
    status="planned",
    bank_programmed=False,
    reminder_enabled=False,
    reminder_time=None,
    transfer_id=None,
):
    if status not in TRANSACTION_STATUSES:
        raise ValueError("Statut invalide.")
    parsed_source_date = (
        source_date
        if isinstance(source_date, date)
        else date.fromisoformat(str(source_date))
    )
    parsed_destination_date = (
        destination_date
        if isinstance(destination_date, date)
        else (
            date.fromisoformat(str(destination_date))
            if destination_date
            else parsed_source_date
        )
    )
    amount = _money(amount)
    note = _text(note, "La note", 1000)
    normalized_reminder_time = _normalize_reminder_time(reminder_time)
    bank_programmed = bool(bank_programmed) if status == "planned" else False
    reminder_enabled = bool(reminder_enabled) if status == "planned" else False

    with get_connection() as conn:
        with conn.cursor() as cur:
            source, destination = _validate_card_payment_methods(
                cur,
                user_id,
                source_payment_method_id,
                destination_payment_method_id,
            )
            normalized_description = _text(
                description or f"Paiement {destination['name']}",
                "La description",
                160,
                True,
            )

            if transfer_id:
                cur.execute(
                    """
                    SELECT id
                    FROM finance_linked_transfers
                    WHERE id = %s AND user_id = %s
                    FOR UPDATE;
                    """,
                    (transfer_id, user_id),
                )
                if not cur.fetchone():
                    raise ValueError("Paiement de carte introuvable.")
                cur.execute(
                    """
                    SELECT reconciliation_status
                    FROM finance_transactions
                    WHERE user_id = %s
                      AND linked_transfer_id = %s
                    FOR UPDATE;
                    """,
                    (user_id, transfer_id),
                )
                linked_rows = cur.fetchall()
                if any(
                    row["reconciliation_status"] == "reconciled"
                    for row in linked_rows
                ):
                    raise ValueError(
                        "Retirez d’abord la conciliation du paiement de carte avant de le modifier."
                    )
                cur.execute(
                    """
                    UPDATE finance_linked_transfers
                    SET source_payment_method_id = %s,
                        destination_payment_method_id = %s,
                        amount = %s,
                        source_date = %s,
                        destination_date = %s,
                        description = %s,
                        note = %s,
                        status = %s,
                        bank_programmed = %s,
                        reminder_enabled = %s,
                        reminder_time = %s,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s;
                    """,
                    (
                        source["id"],
                        destination["id"],
                        amount,
                        parsed_source_date,
                        parsed_destination_date,
                        normalized_description,
                        note,
                        status,
                        bank_programmed,
                        reminder_enabled,
                        normalized_reminder_time,
                        transfer_id,
                        user_id,
                    ),
                )
                linked_id = int(transfer_id)
            else:
                cur.execute(
                    """
                    INSERT INTO finance_linked_transfers (
                        user_id,
                        transfer_type,
                        source_payment_method_id,
                        destination_payment_method_id,
                        amount,
                        source_date,
                        destination_date,
                        description,
                        note,
                        status,
                        bank_programmed,
                        reminder_enabled,
                        reminder_time
                    )
                    VALUES (
                        %s, 'credit_card_payment', %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING id;
                    """,
                    (
                        user_id,
                        source["id"],
                        destination["id"],
                        amount,
                        parsed_source_date,
                        parsed_destination_date,
                        normalized_description,
                        note,
                        status,
                        bank_programmed,
                        reminder_enabled,
                        normalized_reminder_time,
                    ),
                )
                linked_id = int(cur.fetchone()["id"])

            cur.execute(
                """
                SELECT id, linked_transfer_role
                FROM finance_transactions
                WHERE user_id = %s
                  AND linked_transfer_id = %s;
                """,
                (user_id, linked_id),
            )
            existing = {
                row["linked_transfer_role"]: int(row["id"])
                for row in cur.fetchall()
            }

            transaction_values = (
                (
                    "source",
                    parsed_source_date,
                    "expense",
                    source["id"],
                    bank_programmed,
                    reminder_enabled,
                    normalized_reminder_time,
                ),
                (
                    "destination",
                    parsed_destination_date,
                    "income",
                    destination["id"],
                    False,
                    False,
                    normalized_reminder_time,
                ),
            )
            for (
                role,
                transaction_date_value,
                transaction_type,
                payment_method_id,
                transaction_bank_programmed,
                transaction_reminder_enabled,
                transaction_reminder_time,
            ) in transaction_values:
                existing_id = existing.get(role)
                if existing_id:
                    cur.execute(
                        """
                        UPDATE finance_transactions
                        SET transaction_date = %s,
                            transaction_type = %s,
                            amount = %s,
                            description = %s,
                            category_id = NULL,
                            note = %s,
                            status = %s,
                            recurrence_id = NULL,
                            occurrence_date = NULL,
                            payment_method_id = %s,
                            reconciliation_status = 'unreconciled',
                            reconciliation_date = NULL,
                            reconciliation_session_id = NULL,
                            budget_excluded = TRUE,
                            bank_programmed = %s,
                            reminder_enabled = %s,
                            reminder_time = %s,
                            linked_transfer_role = %s,
                            updated_at = NOW()
                        WHERE id = %s AND user_id = %s;
                        """,
                        (
                            transaction_date_value,
                            transaction_type,
                            amount,
                            normalized_description,
                            note,
                            status,
                            payment_method_id,
                            transaction_bank_programmed,
                            transaction_reminder_enabled,
                            transaction_reminder_time,
                            role,
                            existing_id,
                            user_id,
                        ),
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
                            recurrence_id,
                            occurrence_date,
                            payment_method_id,
                            reconciliation_status,
                            reconciliation_date,
                            budget_excluded,
                            bank_programmed,
                            reminder_enabled,
                            reminder_time,
                            linked_transfer_id,
                            linked_transfer_role
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, NULL, %s, %s,
                            NULL, NULL, %s, 'unreconciled', NULL,
                            TRUE, %s, %s, %s, %s, %s
                        );
                        """,
                        (
                            user_id,
                            transaction_date_value,
                            transaction_type,
                            amount,
                            normalized_description,
                            note,
                            status,
                            payment_method_id,
                            transaction_bank_programmed,
                            transaction_reminder_enabled,
                            transaction_reminder_time,
                            linked_id,
                            role,
                        ),
                    )

            conn.commit()
            return linked_id


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
                    SELECT reconciliation_status, linked_transfer_id
                    FROM finance_transactions
                    WHERE id = %s AND user_id = %s
                    FOR UPDATE;
                    """,
                    (transaction_id, user_id),
                )
                current_transaction = cur.fetchone()
                if not current_transaction:
                    raise ValueError("Transaction introuvable.")
                if current_transaction.get("linked_transfer_id"):
                    raise ValueError(
                        "Ce paiement est lié à deux comptes. Utilisez « Modifier le paiement de carte » pour le changer."
                    )
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
    include_linked_transfer_destinations=True,
    amount_exact=None,
    amount_min=None,
    amount_max=None,
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

    if not include_linked_transfer_destinations:
        conditions.append(
            "(t.linked_transfer_role IS NULL OR t.linked_transfer_role <> 'destination')"
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

    def _amount_filter_value(value, label):
        if value in (None, ""):
            return None
        text = str(value).strip().replace(" ", "").replace(",", ".")
        try:
            parsed = Decimal(text).copy_abs().quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError, TypeError) as error:
            raise ValueError(f"{label} est invalide.") from error
        return parsed

    exact_value = _amount_filter_value(amount_exact, "Le montant")
    min_value = _amount_filter_value(amount_min, "Le montant minimum")
    max_value = _amount_filter_value(amount_max, "Le montant maximum")
    if min_value is not None and max_value is not None and min_value > max_value:
        raise ValueError("Le montant minimum ne peut pas dépasser le montant maximum.")
    if exact_value is not None:
        conditions.append("ABS(t.amount) = %s")
        params.append(exact_value)
    else:
        if min_value is not None:
            conditions.append("ABS(t.amount) >= %s")
            params.append(min_value)
        if max_value is not None:
            conditions.append("ABS(t.amount) <= %s")
            params.append(max_value)

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
                    payment_method.method_type
                        AS payment_method_type,
                    linked_transfer.transfer_type
                        AS linked_transfer_type,
                    linked_transfer.source_payment_method_id
                        AS linked_transfer_source_payment_method_id,
                    linked_transfer.destination_payment_method_id
                        AS linked_transfer_destination_payment_method_id,
                    linked_transfer.source_date
                        AS linked_transfer_source_date,
                    linked_transfer.destination_date
                        AS linked_transfer_destination_date,
                    source_method.name
                        AS linked_transfer_source_name,
                    destination_method.name
                        AS linked_transfer_destination_name,
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
                LEFT JOIN finance_linked_transfers AS linked_transfer
                    ON linked_transfer.id = t.linked_transfer_id
                LEFT JOIN finance_payment_methods AS source_method
                    ON source_method.id = linked_transfer.source_payment_method_id
                LEFT JOIN finance_payment_methods AS destination_method
                    ON destination_method.id = linked_transfer.destination_payment_method_id
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
                    payment_method.name,
                    payment_method.method_type,
                    linked_transfer.id,
                    linked_transfer.transfer_type,
                    linked_transfer.source_payment_method_id,
                    linked_transfer.destination_payment_method_id,
                    linked_transfer.source_date,
                    linked_transfer.destination_date,
                    source_method.id,
                    source_method.name,
                    destination_method.id,
                    destination_method.name
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
                SELECT reconciliation_status, linked_transfer_id
                FROM finance_transactions
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
                """,
                (transaction_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Transaction introuvable.")

            linked_transfer_id = row.get("linked_transfer_id")
            if linked_transfer_id:
                cur.execute(
                    """
                    SELECT reconciliation_status
                    FROM finance_transactions
                    WHERE user_id = %s
                      AND linked_transfer_id = %s
                    FOR UPDATE;
                    """,
                    (user_id, linked_transfer_id),
                )
                linked_rows = cur.fetchall()
                if any(
                    linked_row["reconciliation_status"] == "reconciled"
                    for linked_row in linked_rows
                ):
                    raise ValueError(
                        "Retirez d’abord la conciliation du paiement de carte avant de le supprimer."
                    )
                cur.execute(
                    """
                    DELETE FROM finance_linked_transfers
                    WHERE id = %s AND user_id = %s;
                    """,
                    (linked_transfer_id, user_id),
                )
                conn.commit()
                return

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
            cur.execute(
                """
                SELECT linked_transfer_id
                FROM finance_transactions
                WHERE id = %s AND user_id = %s
                FOR UPDATE;
                """,
                (transaction_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Transaction introuvable.")
            linked_transfer_id = row.get("linked_transfer_id")
            if linked_transfer_id:
                cur.execute(
                    """
                    UPDATE finance_linked_transfers
                    SET status = %s,
                        bank_programmed = CASE
                            WHEN %s = 'planned' THEN bank_programmed
                            ELSE FALSE
                        END,
                        reminder_enabled = CASE
                            WHEN %s = 'planned' THEN reminder_enabled
                            ELSE FALSE
                        END,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s;
                    """,
                    (
                        status,
                        status,
                        status,
                        linked_transfer_id,
                        user_id,
                    ),
                )
                cur.execute(
                    """
                    UPDATE finance_transactions
                    SET status = %s,
                        bank_programmed = CASE
                            WHEN %s = 'planned'
                                 AND linked_transfer_role = 'source'
                            THEN bank_programmed
                            ELSE FALSE
                        END,
                        reminder_enabled = CASE
                            WHEN %s = 'planned'
                                 AND linked_transfer_role = 'source'
                            THEN reminder_enabled
                            ELSE FALSE
                        END,
                        updated_at = NOW()
                    WHERE user_id = %s
                      AND linked_transfer_id = %s;
                    """,
                    (
                        status,
                        status,
                        status,
                        user_id,
                        linked_transfer_id,
                    ),
                )
            else:
                cur.execute(
                    """
                    UPDATE finance_transactions
                    SET status=%s,
                        bank_programmed = CASE
                            WHEN %s = 'planned' THEN bank_programmed
                            ELSE FALSE
                        END,
                        reminder_enabled = CASE
                            WHEN %s = 'planned' THEN reminder_enabled
                            ELSE FALSE
                        END,
                        updated_at=NOW()
                    WHERE id=%s AND user_id=%s;
                    """,
                    (status, status, status, transaction_id, user_id),
                )
            conn.commit()


def _refresh_reconciliation_session_totals(
    cur,
    session_id,
):
    """Recalcule une séance après le retrait d'une transaction.

    Les séances V1.9 utilisent un solde de référence + les mouvements nets.
    Les anciennes séances sans reference_balance conservent leur calcul historique.
    """
    cur.execute(
        """
        SELECT
            session.statement_balance,
            session.opening_balance_amount,
            session.reference_balance,
            session.expected_balance,
            session.difference_resolution,
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

    transaction_total = Decimal(row["transaction_total"])
    statement_balance = row["statement_balance"]
    resolution = str(row.get("difference_resolution") or "legacy")

    if row.get("reference_balance") is None:
        # Compatibilité avec les séances créées avant V1.9.0.
        selected_total = (
            transaction_total
            + Decimal(row.get("opening_balance_amount") or 0)
        )
        expected_balance = selected_total
    else:
        selected_total = transaction_total
        expected_balance = (
            Decimal(row["reference_balance"]) + transaction_total
        )

    difference = (
        Decimal(statement_balance) - expected_balance
        if statement_balance is not None
        else None
    )

    if resolution == "carry":
        closing_reference_balance = expected_balance
    elif statement_balance is not None:
        closing_reference_balance = Decimal(statement_balance)
    else:
        closing_reference_balance = expected_balance

    cur.execute(
        """
        UPDATE finance_reconciliation_sessions
        SET selected_total = %s,
            expected_balance = %s,
            difference = %s,
            closing_reference_balance = %s
        WHERE id = %s;
        """,
        (
            selected_total,
            expected_balance,
            difference,
            closing_reference_balance,
            session_id,
        ),
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


def set_bank_transaction_seen(
    user_id,
    transaction_id,
    seen,
    reconciliation_date=None,
):
    """Conciliation rapide pour un compte bancaire.

    Cocher confirme au besoin une transaction prévue et la concilie.
    Décocher retire seulement la conciliation; la transaction reste confirmée.
    """
    parsed_date = (
        reconciliation_date
        if isinstance(reconciliation_date, date)
        else (
            date.fromisoformat(str(reconciliation_date))
            if reconciliation_date
            else date.today()
        )
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    transaction.id,
                    transaction.status,
                    transaction.reconciliation_session_id,
                    method.method_type
                FROM finance_transactions AS transaction
                LEFT JOIN finance_payment_methods AS method
                    ON method.id = transaction.payment_method_id
                WHERE transaction.id = %s
                  AND transaction.user_id = %s
                FOR UPDATE OF transaction;
                """,
                (transaction_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Transaction introuvable.")
            if row.get("method_type") != "bank":
                raise ValueError(
                    "La conciliation rapide s’applique seulement aux comptes bancaires."
                )

            session_id = row.get("reconciliation_session_id")

            if seen:
                cur.execute(
                    """
                    UPDATE finance_transactions
                    SET status = 'confirmed',
                        reconciliation_status = 'reconciled',
                        reconciliation_date = %s,
                        bank_programmed = FALSE,
                        reminder_enabled = FALSE,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s;
                    """,
                    (parsed_date, transaction_id, user_id),
                )
            else:
                if session_id:
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
                    SET reconciliation_status = 'unreconciled',
                        reconciliation_date = NULL,
                        reconciliation_session_id = NULL,
                        updated_at = NOW()
                    WHERE id = %s AND user_id = %s;
                    """,
                    (transaction_id, user_id),
                )

            if session_id:
                _refresh_reconciliation_session_totals(cur, session_id)
            conn.commit()


def reconciliation_reference_summary(
    user_id,
    payment_method_id,
):
    """Retourne le point de départ du prochain relevé de carte.

    Un écart justifié est absorbé parce que le solde réel du relevé devient
    la nouvelle référence. Un écart reporté conserve le solde attendu comme
    référence afin que l'écart demeure visible au prochain relevé.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            payment_method_id = _validate_payment_method(
                cur, user_id, payment_method_id
            )
            cur.execute(
                """
                SELECT
                    id, name, method_type, opening_balance, opening_balance_date
                FROM finance_payment_methods
                WHERE id = %s AND user_id = %s;
                """,
                (payment_method_id, user_id),
            )
            method = cur.fetchone()
            if not method:
                raise ValueError("Mode de paiement introuvable.")

            cur.execute(
                """
                SELECT
                    id, statement_date, statement_balance, expected_balance,
                    closing_reference_balance, difference, difference_resolution
                FROM finance_reconciliation_sessions
                WHERE user_id = %s
                  AND payment_method_id = %s
                  AND status = 'completed'
                ORDER BY statement_date DESC, id DESC
                LIMIT 1;
                """,
                (user_id, payment_method_id),
            )
            previous = cur.fetchone()

    if previous:
        balance = previous.get("closing_reference_balance")
        if balance is None:
            balance = previous.get("statement_balance")
        if balance is None:
            balance = previous.get("expected_balance")
        if balance is None:
            balance = Decimal("0.00")
        return {
            "payment_method_id": payment_method_id,
            "payment_method_name": method["name"],
            "reference_balance": Decimal(balance),
            "reference_date": previous.get("statement_date"),
            "source": "previous_statement",
            "previous_session_id": previous.get("id"),
            "previous_difference": previous.get("difference"),
            "previous_difference_resolution": previous.get("difference_resolution"),
        }

    return {
        "payment_method_id": payment_method_id,
        "payment_method_name": method["name"],
        "reference_balance": Decimal(method.get("opening_balance") or 0),
        "reference_date": method.get("opening_balance_date"),
        "source": "opening_balance",
        "previous_session_id": None,
        "previous_difference": None,
        "previous_difference_resolution": None,
    }



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


def _dashboard_month_projection_v190(
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
            include_linked_transfer_destinations=False,
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
                "effective_start": _optional_date_value(
                    item.get("effective_start"), "La date de début"
                ),
                "effective_end": _optional_date_value(
                    item.get("effective_end"), "La date de fin"
                ),
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
                                sort_order=%s,is_active=%s,effective_start=%s,effective_end=%s,
                                updated_at=NOW()
                            WHERE id=%s AND user_id=%s;
                            """,
                            (
                                item["input_frequency"], item["input_amount"],
                                item.get("biweekly_override"), item.get("note"),
                                bool(item.get("sync_from_recurrence", True)),
                                item.get("sort_order") or 0, bool(item.get("is_active", True)),
                                item.get("effective_start"), item.get("effective_end"),
                                existing["id"], user_id,
                            ),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO finance_budget_items (
                                user_id,item_type,description,input_frequency,input_amount,
                                biweekly_override,note,sort_order,is_active,
                                recurrence_id,sync_from_recurrence,effective_start,effective_end
                            )
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,%s,%s,%s);
                            """,
                            (
                                user_id,item["item_type"],item["description"],
                                item["input_frequency"],item["input_amount"],
                                item.get("biweekly_override"),item.get("note"),
                                item.get("sort_order") or 0,bool(item.get("is_active", True)),
                                bool(item.get("sync_from_recurrence", True)),
                                item.get("effective_start"), item.get("effective_end"),
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
    difference_resolution="balanced",
    difference_explanation=None,
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
        else (date.fromisoformat(str(due_date)) if due_date else None)
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
        statement_balance, "Le solde du relevé", allow_blank=True
    )
    cleaned_note = _text(note, "La note", 1000)
    cleaned_explanation = _text(
        difference_explanation, "L’explication de l’écart", 1000
    )
    resolution = str(difference_resolution or "balanced").strip().lower()
    if resolution not in {"balanced", "justified", "carry"}:
        raise ValueError("Traitement de la différence invalide.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            payment_method_id = _validate_payment_method(
                cur, user_id, payment_method_id
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

            # Le dernier relevé finalisé devient la référence du suivant.
            cur.execute(
                """
                SELECT
                    id, statement_date, statement_balance, expected_balance,
                    closing_reference_balance
                FROM finance_reconciliation_sessions
                WHERE user_id = %s
                  AND payment_method_id = %s
                  AND status = 'completed'
                ORDER BY statement_date DESC, id DESC
                LIMIT 1
                FOR UPDATE;
                """,
                (user_id, payment_method_id),
            )
            previous = cur.fetchone()
            if previous:
                reference_balance = previous.get("closing_reference_balance")
                if reference_balance is None:
                    reference_balance = previous.get("statement_balance")
                if reference_balance is None:
                    reference_balance = previous.get("expected_balance")
                reference_balance = Decimal(reference_balance or 0)
                reference_date = previous.get("statement_date")
            else:
                reference_balance = Decimal(method.get("opening_balance") or 0)
                reference_date = method.get("opening_balance_date")

            opening_amount = Decimal("0.00")
            # Dès la première séance V1.9, le solde initial devient le point
            # de référence du relevé et ne doit plus rester artificiellement
            # dans le solde « à concilier » des mois suivants.
            if (
                previous is None
                and not method["opening_balance_reconciled"]
                and Decimal(method["opening_balance"] or 0) != 0
            ):
                include_opening_balance = True

            if include_opening_balance:
                if method["opening_balance_reconciled"]:
                    raise ValueError("Le solde initial est déjà concilié.")
                opening_amount = Decimal(method["opening_balance"] or 0)
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
                    "Sélectionnez au moins une transaction ou le solde initial."
                )

            selected_total = transaction_total
            expected_balance = reference_balance + transaction_total
            difference = (
                parsed_statement_balance - expected_balance
                if parsed_statement_balance is not None
                else None
            )

            if difference is None or abs(difference) < Decimal(".01"):
                resolution = "balanced"
                cleaned_explanation = None
            elif resolution == "justified":
                if not cleaned_explanation:
                    raise ValueError(
                        "Expliquez la différence avant de la clore comme écart justifié."
                    )
            elif resolution == "balanced":
                raise ValueError(
                    "La conciliation ne balance pas. Choisissez de justifier ou de reporter l’écart."
                )

            if resolution == "carry":
                closing_reference_balance = expected_balance
            elif parsed_statement_balance is not None:
                closing_reference_balance = parsed_statement_balance
            else:
                closing_reference_balance = expected_balance

            cur.execute(
                """
                INSERT INTO finance_reconciliation_sessions (
                    user_id, payment_method_id, statement_date,
                    statement_balance, due_date, reconciliation_date, note,
                    selected_total, difference, included_opening_balance,
                    opening_balance_amount, reference_balance, reference_date,
                    expected_balance, closing_reference_balance,
                    difference_resolution, difference_explanation
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id;
                """,
                (
                    user_id, payment_method_id, parsed_statement_date,
                    parsed_statement_balance, parsed_due_date,
                    parsed_reconciliation_date, cleaned_note, selected_total,
                    difference, bool(include_opening_balance), opening_amount,
                    reference_balance, reference_date, expected_balance,
                    closing_reference_balance, resolution, cleaned_explanation,
                ),
            )
            session_id = int(cur.fetchone()["id"])

            for transaction_id in ids:
                cur.execute(
                    """
                    INSERT INTO finance_reconciliation_session_transactions (
                        session_id, transaction_id
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
                        parsed_reconciliation_date, session_id, user_id, ids,
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

            # Une finalisation réussie remplace le brouillon éventuel de la carte.
            cur.execute(
                """
                DELETE FROM finance_reconciliation_drafts
                WHERE user_id=%s AND payment_method_id=%s;
                """,
                (user_id, payment_method_id),
            )

            conn.commit()

    return {
        "session_id": session_id,
        "selected_total": selected_total,
        "reference_balance": reference_balance,
        "expected_balance": expected_balance,
        "statement_balance": parsed_statement_balance,
        "difference": difference,
        "difference_resolution": resolution,
        "closing_reference_balance": closing_reference_balance,
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


def _export_finances_v190(user_id):
    transactions = list_transactions(
        user_id,
        include_linked_transfer_destinations=False,
        limit=100000,
    )
    json_transactions = list_transactions(
        user_id,
        include_linked_transfer_destinations=True,
        limit=100000,
    )
    linked_transfers = list_card_payment_transfers(
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
            "Paiement de carte lié",
            "Compte de départ",
            "Carte destinataire",
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
                (
                    "Oui"
                    if row.get("linked_transfer_id")
                    else "Non"
                ),
                row.get("linked_transfer_source_name") or "",
                row.get("linked_transfer_destination_name") or "",
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
        "version": "1.9.0",
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
            for row in json_transactions
        ],
        "linked_transfers": [
            serial(dict(row))
            for row in linked_transfers
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

# =========================================================
# ARCHITECTURE V1.13.0 — IMPLÉMENTATIONS HISTORIQUES EXPLICITES
# Les fonctions remplacées au fil des versions portent désormais un nom
# versionné (_..._v190, _..._v1100, etc.) plutôt que d’être redéfinies
# plusieurs fois sous le même nom. Les fonctions publiques restent celles
# de la version courante; le comportement et les migrations sont inchangés.
# =========================================================

# =========================================================
# FINANCES V1.10.0 — BUDGET PÉRIODÉ, CAPACITÉ VARIABLE ET
# PLANS DE FINANCEMENT / VERSEMENTS SUR CARTE
# =========================================================








INSTALLMENT_PLAN_TYPES = {
    "merchant": "Financement magasin",
    "credit_card": "Versements sur carte de crédit",
}




def _init_finances_schema_v1100():
    """Mise à niveau V1.10.0, idempotente et sans SQL manuel."""

    _init_finances_schema_v190()

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Périodes d'effet du Budget.
            cur.execute(
                """
                ALTER TABLE finance_budget_items
                ADD COLUMN IF NOT EXISTS effective_start DATE;
                """
            )
            cur.execute(
                """
                ALTER TABLE finance_budget_items
                ADD COLUMN IF NOT EXISTS effective_end DATE;
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS finance_budget_items_effective_idx
                ON finance_budget_items (
                    user_id,
                    is_active,
                    effective_start,
                    effective_end
                );
                """
            )

            # Plans de financement. Ils ne créent jamais une dépense pour le
            # montant initial complet : seuls les versements deviennent des
            # transactions budgétaires.
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS finance_installment_plans (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id) ON DELETE CASCADE,
                    plan_type TEXT NOT NULL
                        CHECK (plan_type IN ('merchant', 'credit_card')),
                    provider_name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    original_amount NUMERIC(14,2) NOT NULL
                        CHECK (original_amount > 0),
                    purchase_date DATE,
                    total_installments INTEGER NOT NULL
                        CHECK (total_installments BETWEEN 1 AND 1200),
                    completed_installments INTEGER NOT NULL DEFAULT 0
                        CHECK (completed_installments >= 0),
                    remaining_balance NUMERIC(14,2) NOT NULL DEFAULT 0
                        CHECK (remaining_balance >= 0),
                    installment_amount NUMERIC(14,2) NOT NULL
                        CHECK (installment_amount > 0),
                    annual_interest_rate NUMERIC(8,4) NOT NULL DEFAULT 0
                        CHECK (annual_interest_rate >= 0),
                    fees_total NUMERIC(14,2) NOT NULL DEFAULT 0
                        CHECK (fees_total >= 0),
                    frequency_unit TEXT NOT NULL DEFAULT 'month'
                        CHECK (frequency_unit IN ('day','week','month','year')),
                    frequency_interval INTEGER NOT NULL DEFAULT 1
                        CHECK (frequency_interval BETWEEN 1 AND 365),
                    next_due_date DATE,
                    payment_method_id BIGINT
                        REFERENCES finance_payment_methods(id)
                        ON DELETE SET NULL,
                    category_id BIGINT
                        REFERENCES finance_categories(id)
                        ON DELETE SET NULL,
                    budget_excluded BOOLEAN NOT NULL DEFAULT FALSE,
                    note TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CHECK (completed_installments <= total_installments),
                    CHECK (CHAR_LENGTH(provider_name) BETWEEN 1 AND 120),
                    CHECK (CHAR_LENGTH(description) BETWEEN 1 AND 160),
                    CHECK (note IS NULL OR CHAR_LENGTH(note) <= 1000)
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS finance_installment_plans_user_idx
                ON finance_installment_plans (
                    user_id,
                    is_active DESC,
                    next_due_date,
                    id
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS finance_installment_plan_tags (
                    plan_id BIGINT NOT NULL
                        REFERENCES finance_installment_plans(id)
                        ON DELETE CASCADE,
                    tag_id BIGINT NOT NULL
                        REFERENCES finance_tags(id)
                        ON DELETE CASCADE,
                    PRIMARY KEY (plan_id, tag_id)
                );
                """
            )

            cur.execute(
                """
                ALTER TABLE finance_transactions
                ADD COLUMN IF NOT EXISTS installment_plan_id BIGINT;
                """
            )
            cur.execute(
                """
                ALTER TABLE finance_transactions
                ADD COLUMN IF NOT EXISTS installment_number INTEGER;
                """
            )
            cur.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname =
                            'finance_transactions_installment_plan_fk'
                    ) THEN
                        ALTER TABLE finance_transactions
                        ADD CONSTRAINT
                            finance_transactions_installment_plan_fk
                        FOREIGN KEY (installment_plan_id)
                        REFERENCES finance_installment_plans(id)
                        ON DELETE SET NULL;
                    END IF;
                END
                $$;
                """
            )
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                finance_transactions_installment_number_uq
                ON finance_transactions (
                    installment_plan_id,
                    installment_number
                )
                WHERE installment_plan_id IS NOT NULL
                  AND installment_number IS NOT NULL;
                """
            )

            conn.commit()


def _periods_overlap(start_a, end_a, start_b, end_b):
    floor = date(1, 1, 1)
    ceiling = date(9999, 12, 31)
    a_start = start_a or floor
    a_end = end_a or ceiling
    b_start = start_b or floor
    b_end = end_b or ceiling
    return a_start <= b_end and b_start <= a_end




def _list_budget_items_v111(
    user_id,
    include_inactive=False,
    month_value=None,
    effective_only=False,
):
    month = _month_start(month_value) if month_value else None
    month_end = (
        _add_months(month, 1) - timedelta(days=1)
        if month
        else None
    )

    conditions = ["budget.user_id=%s", "(%s OR budget.is_active=TRUE)"]
    params = [user_id, include_inactive]
    if effective_only and month:
        conditions.extend(
            [
                "(budget.effective_start IS NULL OR budget.effective_start <= %s)",
                "(budget.effective_end IS NULL OR budget.effective_end >= %s)",
            ]
        )
        params.extend([month_end, month])

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    budget.*,
                    recurrence.description AS recurrence_description,
                    recurrence.amount AS recurrence_amount,
                    recurrence.frequency_unit AS recurrence_frequency_unit,
                    recurrence.frequency_interval AS recurrence_frequency_interval,
                    recurrence.start_date AS recurrence_start_date,
                    recurrence.end_date AS recurrence_end_date,
                    recurrence.next_date AS recurrence_next_date,
                    recurrence.is_active AS recurrence_is_active
                FROM finance_budget_items AS budget
                LEFT JOIN finance_recurrences AS recurrence
                    ON recurrence.id=budget.recurrence_id
                   AND recurrence.user_id=budget.user_id
                WHERE {' AND '.join(conditions)}
                ORDER BY
                    CASE WHEN budget.item_type='income' THEN 0 ELSE 1 END,
                    budget.sort_order,
                    LOWER(budget.description),
                    budget.id;
                """,
                params,
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
                if month:
                    row["effective_for_month"] = _periods_overlap(
                        row.get("effective_start"),
                        row.get("effective_end"),
                        month,
                        month_end,
                    )
                else:
                    row["effective_for_month"] = True
                rows.append(row)
            return rows


def budget_summary(user_id, month_value=None):
    month = _month_start(month_value or date.today())
    rows = list_budget_items(
        user_id,
        include_inactive=False,
        month_value=month,
        effective_only=True,
    )
    totals = {
        "month": month,
        "monthly_income": Decimal("0.00"),
        "monthly_expense": Decimal("0.00"),
        "biweekly_income": Decimal("0.00"),
        "biweekly_expense": Decimal("0.00"),
    }
    for row in rows:
        key = "income" if row["item_type"] == "income" else "expense"
        totals[f"monthly_{key}"] += Decimal(row["monthly_amount"])
        totals[f"biweekly_{key}"] += Decimal(row["biweekly_amount"])
    totals["monthly_remaining"] = (
        totals["monthly_income"] - totals["monthly_expense"]
    )
    totals["biweekly_remaining"] = (
        totals["biweekly_income"] - totals["biweekly_expense"]
    )
    totals["rows"] = rows
    return totals





def _budget_capacity_summary_v110(user_id, month_value):
    """Capacité disponible pour les dépenses variables du mois affiché."""

    month = _month_start(month_value)
    month_end = _add_months(month, 1) - timedelta(days=1)
    summary = budget_summary(user_id, month)
    active_rows = summary["rows"]
    income_rows = [
        row for row in active_rows
        if row["item_type"] == "income"
    ]

    recurrence_by_id = {
        int(row["id"]): dict(row)
        for row in list_recurrences(user_id)
    }

    linked_income_rows = [
        row for row in income_rows
        if row.get("recurrence_id")
        and int(row["recurrence_id"]) in recurrence_by_id
    ]

    pay_dates = []
    source = "budget"
    if linked_income_rows:
        # Le poste de revenu principal est celui qui représente le plus gros
        # montant par paie. Cela évite qu'un remboursement ponctuel soit compté
        # comme une paie supplémentaire.
        primary_income = max(
            linked_income_rows,
            key=lambda row: Decimal(row["biweekly_amount"]),
        )
        recurrence = recurrence_by_id[int(primary_income["recurrence_id"])]
        pay_dates = _recurrence_dates_between(
            recurrence,
            month,
            month_end,
        )
        source = "recurrence"
    else:
        has_biweekly_income = any(
            row["input_frequency"] == "biweekly"
            for row in income_rows
        )
        if has_biweekly_income:
            # Si le poste Budget n'est pas lié explicitement, chercher une
            # récurrence de revenu active aux deux semaines. On privilégie
            # celle dont le montant est le plus proche du principal revenu
            # bihebdomadaire du Budget. Cela permet de détecter les mois à
            # trois paies sans exiger une liaison parfaite des anciennes données.
            target_amount = max(
                (Decimal(row["biweekly_amount"]) for row in income_rows),
                default=Decimal("0.00"),
            )
            candidates = [
                row for row in recurrence_by_id.values()
                if row.get("transaction_type") == "income"
                and row.get("is_active")
                and row.get("frequency_unit") == "week"
                and int(row.get("frequency_interval") or 1) == 2
            ]
            if candidates:
                recurrence = min(
                    candidates,
                    key=lambda row: (
                        abs(Decimal(row.get("amount") or 0) - target_amount),
                        -Decimal(row.get("amount") or 0),
                    ),
                )
                pay_dates = _recurrence_dates_between(
                    recurrence,
                    month,
                    month_end,
                )
                source = "recurrence_detected"
            else:
                # Sans aucun ancrage de calendrier fiable, conserver le repli
                # prudent de deux paies.
                pay_dates = [month, month]
                source = "fallback_2"

    if pay_dates:
        pay_count = len(pay_dates)
        available_month = (
            Decimal(summary["biweekly_remaining"])
            * Decimal(pay_count)
        )
    else:
        pay_count = 1 if income_rows else 0
        available_month = Decimal(summary["monthly_remaining"])
        source = "monthly"

    return {
        **summary,
        "pay_count": pay_count,
        "pay_dates": pay_dates,
        "pay_count_source": source,
        "remaining_per_pay": Decimal(summary["biweekly_remaining"]),
        "available_month": available_month,
    }


def _fixed_budget_recurrence_ids(user_id, month_value):
    rows = list_budget_items(
        user_id,
        month_value=month_value,
        effective_only=True,
    )
    return {
        int(row["recurrence_id"])
        for row in rows
        if row["item_type"] == "expense"
        and row.get("recurrence_id")
    }








def _plan_transaction_note(plan, installment_number):
    pieces = [
        f"Versement {installment_number}/{plan['total_installments']}",
        str(plan.get("provider_name") or "").strip(),
    ]
    if plan.get("note"):
        pieces.append(str(plan["note"]).strip())
    return " — ".join(piece for piece in pieces if piece)[:1000]


def _rebuild_installment_transactions(cur, user_id, plan_id):
    cur.execute(
        """
        SELECT *
        FROM finance_installment_plans
        WHERE id=%s AND user_id=%s
        FOR UPDATE;
        """,
        (plan_id, user_id),
    )
    plan = cur.fetchone()
    if not plan:
        raise ValueError("Plan de financement introuvable.")

    # Les versements déjà confirmés font partie de l'historique réel et ne sont
    # jamais reconstruits. Les prévisions, elles, sont régénérées.
    cur.execute(
        """
        SELECT installment_number, amount
        FROM finance_transactions
        WHERE user_id=%s
          AND installment_plan_id=%s
          AND status='confirmed';
        """,
        (user_id, plan_id),
    )
    confirmed_rows = cur.fetchall()
    confirmed_numbers = {
        int(row["installment_number"])
        for row in confirmed_rows
        if row.get("installment_number") is not None
    }
    confirmed_amount = sum(
        (Decimal(row["amount"]) for row in confirmed_rows),
        Decimal("0.00"),
    )

    cur.execute(
        """
        DELETE FROM finance_transactions
        WHERE user_id=%s
          AND installment_plan_id=%s
          AND status='planned'
          AND reconciliation_status='unreconciled';
        """,
        (user_id, plan_id),
    )

    if not plan["is_active"]:
        return

    total = int(plan["total_installments"])
    baseline_completed = int(plan["completed_installments"])
    if baseline_completed >= total or not plan.get("next_due_date"):
        return

    cur.execute(
        """
        SELECT tag_id
        FROM finance_installment_plan_tags
        WHERE plan_id=%s
        ORDER BY tag_id;
        """,
        (plan_id,),
    )
    tag_ids = [int(row["tag_id"]) for row in cur.fetchall()]

    remaining_numbers = [
        number
        for number in range(baseline_completed + 1, total + 1)
        if number not in confirmed_numbers
    ]
    if not remaining_numbers:
        return

    base_due = plan["next_due_date"]
    standard_amount = Decimal(plan["installment_amount"])
    zero_cost = (
        Decimal(plan["annual_interest_rate"]) == 0
        and Decimal(plan["fees_total"]) == 0
    )
    balance_after_confirmed = max(
        Decimal("0.00"),
        Decimal(plan["remaining_balance"]) - confirmed_amount,
    )

    for position, installment_number in enumerate(remaining_numbers):
        offset = installment_number - (baseline_completed + 1)
        due = base_due
        for _ in range(offset):
            due = _next_date(
                due,
                plan["frequency_unit"],
                int(plan["frequency_interval"]),
            )

        amount = standard_amount
        if zero_cost and position == len(remaining_numbers) - 1:
            previous_count = max(0, len(remaining_numbers) - 1)
            adjusted = (
                balance_after_confirmed
                - standard_amount * Decimal(previous_count)
            )
            if adjusted > 0:
                amount = adjusted.quantize(Decimal("0.01"))

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
                budget_excluded,
                bank_programmed,
                reminder_enabled,
                reminder_time,
                installment_plan_id,
                installment_number
            )
            VALUES (
                %s,%s,'expense',%s,%s,%s,%s,'planned',%s,
                'unreconciled',%s,FALSE,FALSE,'09:00',%s,%s
            )
            RETURNING id;
            """,
            (
                user_id,
                due,
                amount,
                plan["description"],
                plan.get("category_id"),
                _plan_transaction_note(plan, installment_number),
                plan.get("payment_method_id"),
                bool(plan.get("budget_excluded")),
                plan_id,
                installment_number,
            ),
        )
        transaction_id = int(cur.fetchone()["id"])
        for tag_id in tag_ids:
            cur.execute(
                """
                INSERT INTO finance_transaction_tags (
                    transaction_id,
                    tag_id
                )
                VALUES (%s,%s)
                ON CONFLICT DO NOTHING;
                """,
                (transaction_id, tag_id),
            )


def _save_installment_plan_v111(
    user_id,
    *,
    plan_type,
    provider_name,
    description,
    original_amount,
    total_installments,
    next_due_date,
    payment_method_id,
    category_id=None,
    tag_ids=None,
    purchase_date=None,
    completed_installments=0,
    remaining_balance=None,
    installment_amount=None,
    annual_interest_rate=0,
    fees_total=0,
    frequency_unit="month",
    frequency_interval=1,
    budget_excluded=False,
    note=None,
    plan_id=None,
):
    if plan_type not in INSTALLMENT_PLAN_TYPES:
        raise ValueError("Type de financement invalide.")
    provider_name = _text(
        provider_name,
        "Le commerçant ou programme",
        120,
        True,
    )
    description = _text(description, "La description", 160, True)
    original = _money(original_amount)
    try:
        total_count = int(total_installments)
    except (TypeError, ValueError) as error:
        raise ValueError("Le nombre total de versements est invalide.") from error
    if total_count < 1 or total_count > 1200:
        raise ValueError("Le nombre total de versements doit être entre 1 et 1200.")

    purchase = _optional_date_value(purchase_date, "La date d’achat")
    next_due = _optional_date_value(
        next_due_date,
        "La prochaine échéance",
    )

    interest_rate = _decimal_value(
        annual_interest_rate,
        "Le taux d’intérêt",
        allow_blank=True,
    ) or Decimal("0.00")
    if interest_rate < 0:
        raise ValueError("Le taux d’intérêt ne peut pas être négatif.")
    fees = _decimal_value(
        fees_total,
        "Les frais",
        allow_blank=True,
    ) or Decimal("0.00")
    if fees < 0:
        raise ValueError("Les frais ne peuvent pas être négatifs.")

    if frequency_unit not in FREQUENCY_UNITS:
        raise ValueError("Fréquence invalide.")
    try:
        interval = int(frequency_interval or 1)
    except (TypeError, ValueError) as error:
        raise ValueError("L’intervalle de fréquence est invalide.") from error
    if interval < 1 or interval > 365:
        raise ValueError("L’intervalle de fréquence est invalide.")

    supplied_completed = completed_installments not in (None, "")
    completed_count = None
    if supplied_completed:
        try:
            completed_count = int(completed_installments)
        except (TypeError, ValueError) as error:
            raise ValueError("Le nombre de versements déjà effectués est invalide.") from error
        if completed_count < 0 or completed_count > total_count:
            raise ValueError("Le nombre de versements déjà effectués est invalide.")

    provisional_remaining = (
        _money(remaining_balance, allow_zero=True)
        if remaining_balance not in (None, "")
        else None
    )
    provisional_payment = (
        _money(installment_amount)
        if installment_amount not in (None, "")
        else None
    )

    # Si le nombre déjà effectué est inconnu mais que le solde et le versement
    # sont disponibles, on estime la progression avant de générer l’échéancier.
    progress = analyze_installment_progress(
        original_amount=original,
        remaining_balance=provisional_remaining,
        installment_amount=provisional_payment,
        total_installments=total_count,
        completed_installments=completed_count if supplied_completed else None,
    )
    completed_estimated = (not supplied_completed and provisional_remaining is not None)
    if completed_count is None:
        completed_count = int(progress["estimated_completed_installments"] or 0)

    remaining_count = total_count - completed_count
    if remaining_count > 0 and next_due is None:
        raise ValueError("Indiquez la date du prochain versement.")

    if provisional_remaining is None:
        if completed_count == 0:
            remaining = original
        else:
            remaining = max(
                Decimal("0.00"),
                (original - (Decimal(completed_count) * (provisional_payment or (original / Decimal(total_count))))).quantize(Decimal("0.01")),
            )
    else:
        remaining = provisional_remaining

    if remaining_count == 0:
        remaining = Decimal("0.00")

    if provisional_payment is None:
        payment = _automatic_installment_amount(
            remaining,
            remaining_count,
            interest_rate,
            fees,
            frequency_unit,
            interval,
        )
        if payment <= 0 and remaining_count:
            raise ValueError("Le montant du versement ne peut pas être calculé.")
    else:
        payment = provisional_payment

    note = _text(note, "La note", 1000)

    with get_connection() as conn:
        with conn.cursor() as cur:
            tags = _validate_links(cur, user_id, category_id, tag_ids)
            method_id = _validate_payment_method(
                cur,
                user_id,
                payment_method_id,
            )
            if method_id is None:
                raise ValueError("Choisissez le mode de paiement des versements.")
            cur.execute(
                """
                SELECT method_type
                FROM finance_payment_methods
                WHERE id=%s AND user_id=%s;
                """,
                (method_id, user_id),
            )
            method = cur.fetchone()
            if plan_type == "credit_card" and (
                not method or method["method_type"] != "credit_card"
            ):
                raise ValueError(
                    "Un plan de versements sur carte doit être associé à une carte de crédit."
                )

            is_active = completed_count < total_count
            if plan_id:
                cur.execute(
                    """
                    UPDATE finance_installment_plans
                    SET plan_type=%s,
                        provider_name=%s,
                        description=%s,
                        original_amount=%s,
                        purchase_date=%s,
                        total_installments=%s,
                        completed_installments=%s,
                        completed_installments_estimated=%s,
                        remaining_balance=%s,
                        installment_amount=%s,
                        annual_interest_rate=%s,
                        fees_total=%s,
                        frequency_unit=%s,
                        frequency_interval=%s,
                        next_due_date=%s,
                        payment_method_id=%s,
                        category_id=%s,
                        budget_excluded=%s,
                        note=%s,
                        is_active=%s,
                        updated_at=NOW()
                    WHERE id=%s AND user_id=%s;
                    """,
                    (
                        plan_type,
                        provider_name,
                        description,
                        original,
                        purchase,
                        total_count,
                        completed_count,
                        completed_estimated,
                        remaining,
                        payment,
                        interest_rate,
                        fees,
                        frequency_unit,
                        interval,
                        next_due,
                        method_id,
                        category_id,
                        bool(budget_excluded),
                        note,
                        is_active,
                        plan_id,
                        user_id,
                    ),
                )
                if cur.rowcount == 0:
                    raise ValueError("Plan de financement introuvable.")
                saved_id = int(plan_id)
            else:
                cur.execute(
                    """
                    INSERT INTO finance_installment_plans (
                        user_id,
                        plan_type,
                        provider_name,
                        description,
                        original_amount,
                        purchase_date,
                        total_installments,
                        completed_installments,
                        completed_installments_estimated,
                        remaining_balance,
                        installment_amount,
                        annual_interest_rate,
                        fees_total,
                        frequency_unit,
                        frequency_interval,
                        next_due_date,
                        payment_method_id,
                        category_id,
                        budget_excluded,
                        note,
                        is_active
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                    )
                    RETURNING id;
                    """,
                    (
                        user_id,
                        plan_type,
                        provider_name,
                        description,
                        original,
                        purchase,
                        total_count,
                        completed_count,
                        completed_estimated,
                        remaining,
                        payment,
                        interest_rate,
                        fees,
                        frequency_unit,
                        interval,
                        next_due,
                        method_id,
                        category_id,
                        bool(budget_excluded),
                        note,
                        is_active,
                    ),
                )
                saved_id = int(cur.fetchone()["id"])

            cur.execute(
                "DELETE FROM finance_installment_plan_tags WHERE plan_id=%s;",
                (saved_id,),
            )
            for tag_id in tags:
                cur.execute(
                    """
                    INSERT INTO finance_installment_plan_tags (plan_id, tag_id)
                    VALUES (%s,%s);
                    """,
                    (saved_id, tag_id),
                )

            _rebuild_installment_transactions(cur, user_id, saved_id)
            conn.commit()
            return saved_id


def _list_installment_plans_v111(user_id, include_inactive=True):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    plan.*,
                    payment_method.name AS payment_method_name,
                    payment_method.method_type AS payment_method_type,
                    CASE
                        WHEN parent.id IS NULL THEN category.name
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
                    ) AS tag_names,
                    (
                        SELECT COUNT(*)
                        FROM finance_transactions AS tx
                        WHERE tx.installment_plan_id=plan.id
                          AND tx.status='confirmed'
                    ) AS confirmed_tracked_count,
                    (
                        SELECT COUNT(*)
                        FROM finance_transactions AS tx
                        WHERE tx.installment_plan_id=plan.id
                          AND tx.status='planned'
                    ) AS planned_count,
                    COALESCE((
                        SELECT SUM(tx.amount)
                        FROM finance_transactions AS tx
                        WHERE tx.installment_plan_id=plan.id
                          AND tx.status='confirmed'
                    ), 0) AS confirmed_tracked_amount
,
                    (
                        SELECT MIN(tx.transaction_date)
                        FROM finance_transactions AS tx
                        WHERE tx.installment_plan_id=plan.id
                          AND tx.status='planned'
                    ) AS next_planned_date
                FROM finance_installment_plans AS plan
                LEFT JOIN finance_payment_methods AS payment_method
                    ON payment_method.id=plan.payment_method_id
                LEFT JOIN finance_categories AS category
                    ON category.id=plan.category_id
                LEFT JOIN finance_categories AS parent
                    ON parent.id=category.parent_id
                LEFT JOIN finance_installment_plan_tags AS plan_tag
                    ON plan_tag.plan_id=plan.id
                LEFT JOIN finance_tags AS tag
                    ON tag.id=plan_tag.tag_id
                WHERE plan.user_id=%s
                  AND (%s OR plan.is_active=TRUE)
                GROUP BY
                    plan.id,
                    payment_method.id,
                    payment_method.name,
                    payment_method.method_type,
                    category.id,
                    parent.id,
                    parent.name
                ORDER BY
                    plan.is_active DESC,
                    plan.next_due_date NULLS LAST,
                    LOWER(plan.provider_name),
                    LOWER(plan.description),
                    plan.id;
                """,
                (user_id, include_inactive),
            )
            result = []
            for raw in cur.fetchall():
                row = dict(raw)
                confirmed_count = int(row.get("confirmed_tracked_count") or 0)
                completed = min(
                    int(row["total_installments"]),
                    int(row["completed_installments"]) + confirmed_count,
                )
                row["display_completed_installments"] = completed
                row["display_remaining_installments"] = max(
                    0,
                    int(row["total_installments"]) - completed,
                )
                confirmed_amount = Decimal(
                    row.get("confirmed_tracked_amount") or 0
                )
                if (
                    Decimal(row["annual_interest_rate"]) == 0
                    and Decimal(row["fees_total"]) == 0
                ):
                    row["estimated_remaining_balance"] = max(
                        Decimal("0.00"),
                        Decimal(row["remaining_balance"]) - confirmed_amount,
                    )
                else:
                    # Avec intérêts/frais, le capital restant réel dépend du
                    # relevé du fournisseur; on conserve donc le solde saisi.
                    row["estimated_remaining_balance"] = Decimal(
                        row["remaining_balance"]
                    )
                effective_next = row.get("next_planned_date") or row.get("next_due_date")
                row["display_next_due_date"] = effective_next
                remaining_display = int(row.get("display_remaining_installments") or 0)
                if effective_next and remaining_display > 0:
                    end_date = effective_next
                    for _ in range(max(0, remaining_display - 1)):
                        end_date = _next_date(
                            end_date,
                            row["frequency_unit"],
                            int(row["frequency_interval"] or 1),
                        )
                    row["estimated_end_date"] = end_date
                else:
                    row["estimated_end_date"] = None
                unit_key = row.get("frequency_unit")
                interval = int(row.get("frequency_interval") or 1)
                if interval == 1:
                    row["payment_terms_label"] = {
                        "day": "Quotidien",
                        "week": "Hebdomadaire",
                        "month": "Mensuel",
                        "year": "Annuel",
                    }.get(unit_key, FREQUENCY_UNITS.get(unit_key, str(unit_key or "")))
                else:
                    plural_unit = {
                        "day": "jours",
                        "week": "semaines",
                        "month": "mois",
                        "year": "ans",
                    }.get(unit_key, str(FREQUENCY_UNITS.get(unit_key, unit_key or "")).lower())
                    row["payment_terms_label"] = f"Tous les {interval} {plural_unit}"
                row["progress_estimated"] = bool(
                    row.get("completed_installments_estimated", False)
                )
                result.append(row)
            return result


def get_installment_plan(user_id, plan_id):
    rows = list_installment_plans(user_id, include_inactive=True)
    for row in rows:
        if int(row["id"]) == int(plan_id):
            return row
    raise ValueError("Plan de financement introuvable.")


def toggle_installment_plan(user_id, plan_id, is_active):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE finance_installment_plans
                SET is_active=%s, updated_at=NOW()
                WHERE id=%s AND user_id=%s;
                """,
                (bool(is_active), plan_id, user_id),
            )
            if cur.rowcount == 0:
                raise ValueError("Plan de financement introuvable.")
            if is_active:
                _rebuild_installment_transactions(cur, user_id, plan_id)
            else:
                cur.execute(
                    """
                    DELETE FROM finance_transactions
                    WHERE user_id=%s
                      AND installment_plan_id=%s
                      AND status='planned'
                      AND reconciliation_status='unreconciled';
                    """,
                    (user_id, plan_id),
                )
            conn.commit()


def delete_installment_plan(user_id, plan_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM finance_installment_plans
                WHERE id=%s AND user_id=%s
                FOR UPDATE;
                """,
                (plan_id, user_id),
            )
            if not cur.fetchone():
                raise ValueError("Plan de financement introuvable.")
            cur.execute(
                """
                DELETE FROM finance_transactions
                WHERE user_id=%s
                  AND installment_plan_id=%s
                  AND status='planned'
                  AND reconciliation_status='unreconciled';
                """,
                (user_id, plan_id),
            )
            # Les versements déjà confirmés sont conservés dans l'historique.
            cur.execute(
                """
                UPDATE finance_transactions
                SET installment_plan_id=NULL,
                    installment_number=NULL,
                    updated_at=NOW()
                WHERE user_id=%s
                  AND installment_plan_id=%s
                  AND status='confirmed';
                """,
                (user_id, plan_id),
            )
            cur.execute(
                """
                DELETE FROM finance_installment_plans
                WHERE id=%s AND user_id=%s;
                """,
                (plan_id, user_id),
            )
            conn.commit()


def _export_finances_v1100(user_id):
    csv_bytes, json_bytes = _export_finances_v190(user_id)
    try:
        payload = json.loads(json_bytes.decode("utf-8"))
    except Exception:
        return csv_bytes, json_bytes

    def serial(value):
        if isinstance(value, (date, datetime, time, Decimal)):
            return str(value)
        if isinstance(value, list):
            return [serial(item) for item in value]
        if isinstance(value, dict):
            return {key: serial(item) for key, item in value.items()}
        return value

    payload["version"] = "1.10.0"
    payload["installment_plans"] = [
        serial(dict(row))
        for row in list_installment_plans(user_id, include_inactive=True)
    ]
    payload["budget_items"] = [
        serial(dict(row))
        for row in list_budget_items(user_id, include_inactive=True)
    ]
    return (
        csv_bytes,
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
    )


# =========================================================
# FINANCES V1.10.1 — CORRECTIFS BUDGET, REPORT MENSUEL
# ET SYNCHRONISATION BUDGET ↔ RÉCURRENCE
# =========================================================






def _init_finances_schema_v1101():
    """Mise à niveau V1.10.1, idempotente et sans SQL manuel."""

    _init_finances_schema_v1100()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS finance_user_settings (
                    user_id INTEGER PRIMARY KEY
                        REFERENCES users(id) ON DELETE CASCADE,
                    carry_month_balance BOOLEAN NOT NULL DEFAULT FALSE,
                    carry_start_month DATE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                ALTER TABLE finance_user_settings
                ADD COLUMN IF NOT EXISTS carry_month_balance BOOLEAN
                NOT NULL DEFAULT FALSE;
                """
            )
            cur.execute(
                """
                ALTER TABLE finance_user_settings
                ADD COLUMN IF NOT EXISTS carry_start_month DATE;
                """
            )
            conn.commit()


def get_finance_settings(user_id):
    """Réglages privés de Finances pour l'utilisateur connecté."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT carry_month_balance, carry_start_month
                FROM finance_user_settings
                WHERE user_id=%s;
                """,
                (user_id,),
            )
            row = cur.fetchone()
    if not row:
        return {
            "carry_month_balance": False,
            "carry_start_month": None,
        }
    return {
        "carry_month_balance": bool(row["carry_month_balance"]),
        "carry_start_month": row.get("carry_start_month"),
    }


def set_month_carryover(user_id, enabled, start_month=None):
    """Active/désactive le report du solde variable entre les mois.

    Lors de l'activation, le mois fourni devient le premier mois de calcul :
    aucun report entrant n'est appliqué à ce mois, mais son solde final est
    reporté au mois suivant. Cela évite de recalculer indéfiniment le passé.
    """

    enabled = bool(enabled)
    start_value = None
    if enabled:
        start_value = _month_start(start_month or date.today())

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO finance_user_settings (
                    user_id, carry_month_balance, carry_start_month
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET carry_month_balance=EXCLUDED.carry_month_balance,
                    carry_start_month=CASE
                        WHEN EXCLUDED.carry_month_balance
                        THEN COALESCE(
                            finance_user_settings.carry_start_month,
                            EXCLUDED.carry_start_month
                        )
                        ELSE NULL
                    END,
                    updated_at=NOW();
                """,
                (user_id, enabled, start_value),
            )
            conn.commit()
    return get_finance_settings(user_id)




def budget_capacity_summary(user_id, month_value):
    """Capacité variable avec report optionnel du solde mensuel."""

    month = _month_start(month_value)
    base = dict(_budget_capacity_summary_v110(user_id, month))
    base_available = Decimal(base["available_month"])
    settings = get_finance_settings(user_id)
    carry_enabled = bool(settings.get("carry_month_balance"))
    carry_start = settings.get("carry_start_month")
    carry_in = Decimal("0.00")

    if carry_enabled and carry_start:
        carry_start = _month_start(carry_start)
        if month > carry_start:
            cursor = carry_start
            safety = 0
            while cursor < month and safety < 600:
                cursor_base = _budget_capacity_summary_v110(
                    user_id,
                    cursor,
                )
                cursor_available = Decimal(cursor_base["available_month"])
                cursor_expenses = _variable_expense_total_for_month(
                    user_id,
                    cursor,
                )
                carry_in = (
                    cursor_available + carry_in - cursor_expenses
                ).quantize(Decimal("0.01"))
                cursor = _add_months(cursor, 1)
                safety += 1

    base["available_month_base"] = base_available
    base["carry_enabled"] = carry_enabled
    base["carry_start_month"] = carry_start
    base["carry_in"] = carry_in
    base["available_month"] = (
        base_available + carry_in
    ).quantize(Decimal("0.01"))
    return base


def _create_budget_recurrence_cursor(
    cur,
    user_id,
    *,
    transaction_type,
    fallback_description,
    fallback_amount,
    fallback_start,
    fallback_end,
    payload,
):
    """Crée une récurrence dans la transaction SQL du poste Budget."""

    payload = dict(payload or {})
    description = _text(
        payload.get("description") or fallback_description,
        "La description de la récurrence",
        160,
        True,
    )
    amount = _money(
        payload.get("amount")
        if payload.get("amount") not in (None, "")
        else fallback_amount
    )
    frequency_unit = payload.get("frequency_unit") or "month"
    if frequency_unit not in FREQUENCY_UNITS:
        raise ValueError("Fréquence de récurrence invalide.")
    interval = int(payload.get("frequency_interval") or 1)
    if interval < 1 or interval > 365:
        raise ValueError("L’intervalle de récurrence doit être compris entre 1 et 365.")

    start_source = payload.get("start_date") or fallback_start or date.today()
    parsed_start = _optional_date_value(
        start_source,
        "La date de début de la récurrence",
    )
    end_source = (
        payload.get("end_date")
        if payload.get("end_date") not in (None, "")
        else fallback_end
    )
    parsed_end = _optional_date_value(
        end_source,
        "La date de fin de la récurrence",
    )
    if parsed_end and parsed_end < parsed_start:
        raise ValueError("La date de fin de la récurrence précède sa date de début.")

    confirmation_mode = payload.get("confirmation_mode") or "confirm"
    if confirmation_mode not in CONFIRMATION_MODES:
        raise ValueError("Mode de confirmation de la récurrence invalide.")

    category_id = payload.get("category_id") or None
    tag_ids = payload.get("tag_ids") or []
    tags = _validate_links(cur, user_id, category_id, tag_ids)
    payment_method_id = _validate_payment_method(
        cur,
        user_id,
        payload.get("payment_method_id"),
    )
    recurrence_note = _text(
        payload.get("note"),
        "La note de la récurrence",
        1000,
    )
    reminder_time = _normalize_reminder_time(
        payload.get("reminder_time") or "09:00"
    )

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
            payment_method_id,
            recurrence_note,
            frequency_unit,
            interval,
            parsed_start,
            parsed_end,
            parsed_start,
            confirmation_mode,
            bool(payload.get("budget_excluded", False)),
            bool(payload.get("bank_programmed", False)),
            bool(payload.get("reminder_enabled", False)),
            reminder_time,
        ),
    )
    recurrence_id = int(cur.fetchone()["id"])
    for tag_id in tags:
        cur.execute(
            """
            INSERT INTO finance_recurrence_tags (recurrence_id, tag_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (recurrence_id, tag_id),
        )
    return recurrence_id


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
    effective_start=None,
    effective_end=None,
    allow_overlap=False,
    new_recurrence=None,
):
    """Enregistre un poste Budget V1.10.1.

    Corrige le NULL PostgreSQL des validations, permet la création atomique
    d'une récurrence et synchronise la date de fin vers la récurrence liée.
    """

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
    start_value = _optional_date_value(effective_start, "La date de début")
    end_value = _optional_date_value(effective_end, "La date de fin")
    if start_value and end_value and end_value < start_value:
        raise ValueError(
            "La date de fin doit être égale ou postérieure à la date de début."
        )
    if input_frequency == "biweekly":
        override = None

    normalized_recurrence_id = (
        int(recurrence_id)
        if recurrence_id not in (None, "")
        else None
    )
    if new_recurrence and normalized_recurrence_id is not None:
        raise ValueError(
            "Choisissez une récurrence existante ou créez-en une nouvelle, pas les deux."
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            if new_recurrence:
                normalized_recurrence_id = _create_budget_recurrence_cursor(
                    cur,
                    user_id,
                    transaction_type=item_type,
                    fallback_description=description,
                    fallback_amount=amount,
                    fallback_start=start_value,
                    fallback_end=end_value,
                    payload=new_recurrence,
                )

            linked = None
            if normalized_recurrence_id is not None:
                cur.execute(
                    """
                    SELECT id, transaction_type, amount,
                           frequency_unit, frequency_interval,
                           start_date, end_date
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
                    if end_value and end_value < linked["start_date"]:
                        raise ValueError(
                            "La date de fin du poste Budget précède le début de la récurrence."
                        )

                # Ne pas envoyer un NULL non typé dans « %s IS NULL » : pour
                # un nouveau poste, la condition d'exclusion n'est simplement
                # pas ajoutée à la requête.
                duplicate_sql = """
                    SELECT id
                    FROM finance_budget_items
                    WHERE user_id=%s AND recurrence_id=%s
                """
                duplicate_params = [user_id, normalized_recurrence_id]
                if budget_item_id is not None:
                    duplicate_sql += " AND id<>%s"
                    duplicate_params.append(int(budget_item_id))
                duplicate_sql += " LIMIT 1;"
                cur.execute(duplicate_sql, duplicate_params)
                if cur.fetchone():
                    raise ValueError(
                        "Cette récurrence est déjà liée à un autre poste du Budget."
                    )

            if not allow_overlap:
                overlap_sql = """
                    SELECT id, effective_start, effective_end
                    FROM finance_budget_items
                    WHERE user_id=%s
                      AND item_type=%s
                      AND LOWER(TRIM(description))=LOWER(TRIM(%s))
                """
                overlap_params = [user_id, item_type, description]
                if budget_item_id is not None:
                    overlap_sql += " AND id<>%s"
                    overlap_params.append(int(budget_item_id))
                overlap_sql += ";"
                cur.execute(overlap_sql, overlap_params)
                for other in cur.fetchall():
                    if _periods_overlap(
                        start_value,
                        end_value,
                        other.get("effective_start"),
                        other.get("effective_end"),
                    ):
                        raise ValueError(
                            "Une autre période de ce poste budgétaire se chevauche. "
                            "Ajustez les dates ou autorisez explicitement le chevauchement."
                        )

            if budget_item_id:
                cur.execute(
                    """
                    UPDATE finance_budget_items
                    SET item_type=%s,
                        description=%s,
                        input_frequency=%s,
                        input_amount=%s,
                        biweekly_override=%s,
                        note=%s,
                        recurrence_id=%s,
                        sync_from_recurrence=%s,
                        effective_start=%s,
                        effective_end=%s,
                        is_active=TRUE,
                        updated_at=NOW()
                    WHERE id=%s AND user_id=%s;
                    """,
                    (
                        item_type,
                        description,
                        input_frequency,
                        amount,
                        override,
                        note,
                        normalized_recurrence_id,
                        bool(sync_from_recurrence),
                        start_value,
                        end_value,
                        budget_item_id,
                        user_id,
                    ),
                )
                if cur.rowcount == 0:
                    raise ValueError("Poste budgétaire introuvable.")
                saved_id = int(budget_item_id)
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
                        user_id,
                        item_type,
                        description,
                        input_frequency,
                        input_amount,
                        biweekly_override,
                        note,
                        sort_order,
                        recurrence_id,
                        sync_from_recurrence,
                        effective_start,
                        effective_end
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id;
                    """,
                    (
                        user_id,
                        item_type,
                        description,
                        input_frequency,
                        amount,
                        override,
                        note,
                        next_order,
                        normalized_recurrence_id,
                        bool(sync_from_recurrence),
                        start_value,
                        end_value,
                    ),
                )
                saved_id = int(cur.fetchone()["id"])

            # Synchronisation explicite demandée : lorsque le lien est actif,
            # la date de fin du Budget devient aussi la date de fin de la règle.
            # Les transactions confirmées restent intactes; seules les
            # occurrences prévues postérieures sont retirées.
            if normalized_recurrence_id is not None and sync_from_recurrence:
                cur.execute(
                    """
                    UPDATE finance_recurrences
                    SET end_date=%s,
                        updated_at=NOW()
                    WHERE id=%s AND user_id=%s;
                    """,
                    (end_value, normalized_recurrence_id, user_id),
                )
                if end_value is not None:
                    cur.execute(
                        """
                        DELETE FROM finance_transactions
                        WHERE user_id=%s
                          AND recurrence_id=%s
                          AND status='planned'
                          AND transaction_date>%s;
                        """,
                        (user_id, normalized_recurrence_id, end_value),
                    )

            conn.commit()
            return saved_id


def _export_finances_v1102(user_id):
    """Export V1.10.2 incluant les réglages de report mensuel."""

    csv_bytes, json_bytes = _export_finances_v1100(user_id)
    try:
        payload = json.loads(json_bytes.decode("utf-8"))
    except Exception:
        return csv_bytes, json_bytes

    def serial(value):
        if isinstance(value, (date, datetime, time, Decimal)):
            return str(value)
        if isinstance(value, list):
            return [serial(item) for item in value]
        if isinstance(value, dict):
            return {key: serial(item) for key, item in value.items()}
        return value

    payload["version"] = "1.10.2"
    payload["finance_settings"] = serial(get_finance_settings(user_id))
    return (
        csv_bytes,
        json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
    )


# =========================================================
# FINANCES V1.11.0 — BROUILLONS DE CONCILIATION,
# CONTRÔLES D'HISTORIQUE ET FINANCEMENTS PLUS TOLÉRANTS
# =========================================================





def _init_finances_schema_v1110():
    """Mise à niveau V1.11.0, idempotente et sans SQL manuel."""

    _init_finances_schema_v1101()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE finance_installment_plans
                ADD COLUMN IF NOT EXISTS completed_installments_estimated BOOLEAN
                NOT NULL DEFAULT FALSE;
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS finance_reconciliation_drafts (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id) ON DELETE CASCADE,
                    payment_method_id BIGINT NOT NULL
                        REFERENCES finance_payment_methods(id) ON DELETE CASCADE,
                    statement_date DATE,
                    statement_balance NUMERIC(14,2),
                    due_date DATE,
                    reconciliation_date DATE,
                    note TEXT,
                    include_opening_balance BOOLEAN NOT NULL DEFAULT FALSE,
                    difference_explanation TEXT,
                    filter_start DATE,
                    filter_end DATE,
                    filter_query TEXT,
                    sort_direction TEXT NOT NULL DEFAULT 'asc'
                        CHECK (sort_direction IN ('asc', 'desc')),
                    selected_transaction_ids BIGINT[] NOT NULL DEFAULT ARRAY[]::BIGINT[],
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (user_id, payment_method_id),
                    CHECK (note IS NULL OR CHAR_LENGTH(note) <= 1000),
                    CHECK (
                        difference_explanation IS NULL
                        OR CHAR_LENGTH(difference_explanation) <= 1000
                    )
                );
                """
            )
            conn.commit()




def save_reconciliation_draft(
    user_id,
    payment_method_id,
    transaction_ids,
    *,
    statement_date=None,
    statement_balance=None,
    due_date=None,
    reconciliation_date=None,
    note=None,
    include_opening_balance=False,
    difference_explanation=None,
    filter_start=None,
    filter_end=None,
    filter_query=None,
    sort_direction="asc",
):
    """Sauvegarde le travail de conciliation sans concilier les transactions."""

    ids = sorted({int(value) for value in (transaction_ids or [])})
    statement = _optional_date_value(statement_date, "La date du relevé")
    due = _optional_date_value(due_date, "La date de paiement")
    reconciled_on = _optional_date_value(
        reconciliation_date, "La date de conciliation"
    )
    start = _optional_date_value(filter_start, "La date de début du filtre")
    end = _optional_date_value(filter_end, "La date de fin du filtre")
    balance = _decimal_value(
        statement_balance, "Le solde du relevé", allow_blank=True
    )
    cleaned_note = _text(note, "La note", 1000)
    cleaned_explanation = _text(
        difference_explanation, "L’explication de l’écart", 1000
    )
    cleaned_query = _text(filter_query, "La recherche", 300)
    sort_value = str(sort_direction or "asc").strip().lower()
    if sort_value not in {"asc", "desc"}:
        sort_value = "asc"

    with get_connection() as conn:
        with conn.cursor() as cur:
            method_id = _validate_payment_method(cur, user_id, payment_method_id)
            if method_id is None:
                raise ValueError("Choisissez un mode de paiement.")
            cur.execute(
                """
                INSERT INTO finance_reconciliation_drafts (
                    user_id, payment_method_id, statement_date,
                    statement_balance, due_date, reconciliation_date,
                    note, include_opening_balance, difference_explanation,
                    filter_start, filter_end, filter_query, sort_direction,
                    selected_transaction_ids
                )
                VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                ON CONFLICT (user_id, payment_method_id) DO UPDATE
                SET statement_date=EXCLUDED.statement_date,
                    statement_balance=EXCLUDED.statement_balance,
                    due_date=EXCLUDED.due_date,
                    reconciliation_date=EXCLUDED.reconciliation_date,
                    note=EXCLUDED.note,
                    include_opening_balance=EXCLUDED.include_opening_balance,
                    difference_explanation=EXCLUDED.difference_explanation,
                    filter_start=EXCLUDED.filter_start,
                    filter_end=EXCLUDED.filter_end,
                    filter_query=EXCLUDED.filter_query,
                    sort_direction=EXCLUDED.sort_direction,
                    selected_transaction_ids=EXCLUDED.selected_transaction_ids,
                    updated_at=NOW()
                RETURNING id;
                """,
                (
                    user_id,
                    method_id,
                    statement,
                    balance,
                    due,
                    reconciled_on,
                    cleaned_note,
                    bool(include_opening_balance),
                    cleaned_explanation,
                    start,
                    end,
                    cleaned_query,
                    sort_value,
                    ids,
                ),
            )
            draft_id = int(cur.fetchone()["id"])
            conn.commit()
    return draft_id


def get_reconciliation_draft(user_id, payment_method_id):
    if payment_method_id in (None, ""):
        return None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT draft.*, method.name AS payment_method_name
                FROM finance_reconciliation_drafts AS draft
                JOIN finance_payment_methods AS method
                  ON method.id=draft.payment_method_id
                WHERE draft.user_id=%s AND draft.payment_method_id=%s;
                """,
                (user_id, int(payment_method_id)),
            )
            row = cur.fetchone()
    return dict(row) if row else None


def list_reconciliation_drafts(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT draft.*, method.name AS payment_method_name
                FROM finance_reconciliation_drafts AS draft
                JOIN finance_payment_methods AS method
                  ON method.id=draft.payment_method_id
                WHERE draft.user_id=%s
                ORDER BY draft.updated_at DESC, draft.id DESC;
                """,
                (user_id,),
            )
            return cur.fetchall()


def delete_reconciliation_draft(user_id, payment_method_id):
    if payment_method_id in (None, ""):
        return 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM finance_reconciliation_drafts
                WHERE user_id=%s AND payment_method_id=%s;
                """,
                (user_id, int(payment_method_id)),
            )
            count = cur.rowcount
            conn.commit()
    return count


def find_potential_duplicate_transactions(
    user_id,
    *,
    start_date=None,
    end_date=None,
    same_type=True,
    window_days=2,
    limit=10000,
):
    """Retourne des groupes de doublons potentiels: montant exact + dates proches."""

    rows = list_transactions(
        user_id,
        start_date=start_date,
        end_date=end_date,
        include_linked_transfer_destinations=False,
        limit=limit,
    )
    buckets = defaultdict(list)
    for row in rows:
        key = (
            Decimal(row["amount"]).copy_abs().quantize(Decimal("0.01")),
            row["transaction_type"] if same_type else "*",
        )
        buckets[key].append(dict(row))

    groups = []
    delta_days = max(0, int(window_days))
    for (amount, tx_type), bucket in buckets.items():
        bucket.sort(key=lambda item: (item["transaction_date"], int(item["id"])))
        cluster = []
        for row in bucket:
            if not cluster:
                cluster = [row]
                continue
            if (
                row["transaction_date"] - cluster[0]["transaction_date"]
            ).days <= delta_days:
                cluster.append(row)
            else:
                if len(cluster) >= 2:
                    groups.append(
                        {
                            "amount": amount,
                            "transaction_type": tx_type,
                            "transactions": cluster,
                        }
                    )
                cluster = [row]
        if len(cluster) >= 2:
            groups.append(
                {
                    "amount": amount,
                    "transaction_type": tx_type,
                    "transactions": cluster,
                }
            )

    groups.sort(
        key=lambda group: (
            group["transactions"][-1]["transaction_date"],
            group["amount"],
        ),
        reverse=True,
    )
    return groups


def list_month_unreconciled_transactions(user_id, month_value):
    month = _month_start(month_value)
    month_end = _add_months(month, 1) - timedelta(days=1)
    return list_transactions(
        user_id,
        start_date=month,
        end_date=month_end,
        status="confirmed",
        reconciliation_status="unreconciled",
        include_linked_transfer_destinations=True,
        limit=10000,
    )


def _export_finances_v1110(user_id):
    """Export V1.11.0 incluant les nouveaux réglages de financement."""

    csv_bytes, json_bytes = _export_finances_v1102(user_id)
    try:
        payload = json.loads(json_bytes.decode("utf-8"))
    except Exception:
        return csv_bytes, json_bytes

    payload["version"] = "1.11.0"
    payload["reconciliation_drafts"] = [
        {
            key: (
                str(value)
                if isinstance(value, (date, datetime, time, Decimal))
                else value
            )
            for key, value in dict(row).items()
        }
        for row in list_reconciliation_drafts(user_id)
    ]
    return (
        csv_bytes,
        json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
    )

# =========================================================
# FINANCES V1.12.0 — PRÉVISIONS, GROUPES DE FINANCEMENTS,
# INTÉRÊTS ET PRÊTS PARTAGÉS
# =========================================================










def init_finances_schema():
    """Mise à niveau V1.12.0, idempotente et sans SQL manuel."""

    _init_finances_schema_v1110()
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Groupes de financements intégrés au Budget.
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS finance_budget_financing_groups (
                    budget_item_id BIGINT PRIMARY KEY
                        REFERENCES finance_budget_items(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS finance_budget_financing_group_plans (
                    budget_item_id BIGINT NOT NULL
                        REFERENCES finance_budget_financing_groups(budget_item_id)
                        ON DELETE CASCADE,
                    plan_id BIGINT NOT NULL
                        REFERENCES finance_installment_plans(id) ON DELETE CASCADE,
                    PRIMARY KEY (budget_item_id, plan_id),
                    UNIQUE (plan_id)
                );
                """
            )

            # Ventilation des versements avec intérêts.
            cur.execute(
                """
                ALTER TABLE finance_installment_plans
                ADD COLUMN IF NOT EXISTS payment_includes_interest BOOLEAN
                NOT NULL DEFAULT TRUE;
                """
            )
            cur.execute(
                """
                ALTER TABLE finance_installment_plans
                ADD COLUMN IF NOT EXISTS base_installment_amount NUMERIC(14,2);
                """
            )
            cur.execute(
                """
                ALTER TABLE finance_installment_plans
                ADD COLUMN IF NOT EXISTS calculated_installment_amount NUMERIC(14,2);
                """
            )

            # Prêts partagés : une entité isolée de toutes les autres finances.
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS finance_shared_loans (
                    id BIGSERIAL PRIMARY KEY,
                    owner_user_id INTEGER NOT NULL
                        REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    lender_name TEXT,
                    borrower_name TEXT,
                    original_balance NUMERIC(14,2) NOT NULL DEFAULT 0,
                    current_balance NUMERIC(14,2) NOT NULL DEFAULT 0,
                    annual_interest_rate NUMERIC(8,4) NOT NULL DEFAULT 0,
                    payment_amount NUMERIC(14,2),
                    frequency_unit TEXT NOT NULL DEFAULT 'month'
                        CHECK (frequency_unit IN ('day','week','month','year')),
                    frequency_interval INTEGER NOT NULL DEFAULT 1,
                    start_date DATE,
                    next_due_date DATE,
                    end_date DATE,
                    note TEXT,
                    status TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active','paused','completed')),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CHECK (CHAR_LENGTH(title) BETWEEN 1 AND 160),
                    CHECK (original_balance >= 0),
                    CHECK (current_balance >= 0),
                    CHECK (annual_interest_rate >= 0),
                    CHECK (payment_amount IS NULL OR payment_amount > 0)
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS finance_shared_loans_owner_idx
                ON finance_shared_loans (owner_user_id, status, id);
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS finance_shared_loan_members (
                    loan_id BIGINT NOT NULL
                        REFERENCES finance_shared_loans(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id) ON DELETE CASCADE,
                    role TEXT NOT NULL DEFAULT 'observer'
                        CHECK (role IN ('lender','borrower','observer')),
                    permission TEXT NOT NULL DEFAULT 'view'
                        CHECK (permission IN ('view','edit')),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (loan_id, user_id)
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS finance_shared_loan_members_user_idx
                ON finance_shared_loan_members (user_id, loan_id);
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS finance_shared_loan_events (
                    id BIGSERIAL PRIMARY KEY,
                    loan_id BIGINT NOT NULL
                        REFERENCES finance_shared_loans(id) ON DELETE CASCADE,
                    created_by_user_id INTEGER NOT NULL
                        REFERENCES users(id) ON DELETE RESTRICT,
                    event_date DATE NOT NULL,
                    event_type TEXT NOT NULL
                        CHECK (event_type IN ('payment','principal_addition','adjustment','note')),
                    amount NUMERIC(14,2) NOT NULL DEFAULT 0,
                    interest_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
                    principal_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
                    balance_after NUMERIC(14,2) NOT NULL DEFAULT 0,
                    note TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS finance_shared_loan_events_loan_idx
                ON finance_shared_loan_events (loan_id, event_date, id);
                """
            )
            conn.commit()





def _financing_group_plan_ids(cur, user_id, budget_item_id=None):
    conditions = ["group_row.user_id=%s"]
    params = [user_id]
    if budget_item_id is not None:
        conditions.append("group_row.budget_item_id=%s")
        params.append(int(budget_item_id))
    cur.execute(
        f"""
        SELECT link.budget_item_id, link.plan_id
        FROM finance_budget_financing_group_plans AS link
        JOIN finance_budget_financing_groups AS group_row
          ON group_row.budget_item_id=link.budget_item_id
        WHERE {' AND '.join(conditions)}
        ORDER BY link.budget_item_id, link.plan_id;
        """,
        params,
    )
    return cur.fetchall()


def _financing_group_amount_for_month(cur, user_id, plan_ids, month):
    if not plan_ids:
        return Decimal("0.00")
    month = _month_start(month)
    month_end = _add_months(month, 1) - timedelta(days=1)
    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM finance_transactions
        WHERE user_id=%s
          AND installment_plan_id=ANY(%s)
          AND transaction_type='expense'
          AND status IN ('planned','confirmed')
          AND transaction_date BETWEEN %s AND %s;
        """,
        (user_id, list(plan_ids), month, month_end),
    )
    return Decimal(cur.fetchone()["total"] or 0).quantize(Decimal("0.01"))


def list_budget_items(
    user_id,
    include_inactive=False,
    month_value=None,
    effective_only=False,
):
    rows = [
        dict(row)
        for row in _list_budget_items_v111(
            user_id,
            include_inactive=include_inactive,
            month_value=month_value,
            effective_only=effective_only,
        )
    ]
    if not rows:
        return rows

    month = _month_start(month_value or date.today())
    by_id = {int(row["id"]): row for row in rows}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT group_row.budget_item_id,
                       COALESCE(ARRAY_AGG(link.plan_id ORDER BY link.plan_id)
                           FILTER (WHERE link.plan_id IS NOT NULL), ARRAY[]::BIGINT[]) AS plan_ids,
                       COALESCE(ARRAY_AGG(plan.description ORDER BY plan.description)
                           FILTER (WHERE plan.id IS NOT NULL), ARRAY[]::TEXT[]) AS plan_names
                FROM finance_budget_financing_groups AS group_row
                LEFT JOIN finance_budget_financing_group_plans AS link
                  ON link.budget_item_id=group_row.budget_item_id
                LEFT JOIN finance_installment_plans AS plan
                  ON plan.id=link.plan_id
                WHERE group_row.user_id=%s
                  AND group_row.budget_item_id=ANY(%s)
                GROUP BY group_row.budget_item_id;
                """,
                (user_id, list(by_id)),
            )
            for group in cur.fetchall():
                item_id = int(group["budget_item_id"])
                row = by_id.get(item_id)
                if not row:
                    continue
                plan_ids = [int(value) for value in (group.get("plan_ids") or [])]
                dynamic_monthly = _financing_group_amount_for_month(
                    cur, user_id, plan_ids, month
                )
                dynamic_biweekly = (
                    dynamic_monthly * Decimal("12") / Decimal("26")
                ).quantize(Decimal("0.01"))
                row["budget_financing_group"] = True
                row["financing_plan_ids"] = plan_ids
                row["financing_plan_names"] = list(group.get("plan_names") or [])
                row["monthly_amount"] = dynamic_monthly
                row["biweekly_amount"] = dynamic_biweekly
                row["input_frequency"] = "monthly"
                row["input_amount"] = dynamic_monthly
                row["biweekly_override"] = None
                row["biweekly_is_override"] = False
    return rows


def list_financing_budget_groups(user_id, month_value=None):
    return [
        row for row in list_budget_items(
            user_id,
            include_inactive=True,
            month_value=month_value or date.today(),
        )
        if row.get("budget_financing_group")
    ]


def save_financing_budget_group(
    user_id,
    *,
    description,
    plan_ids,
    budget_item_id=None,
    effective_start=None,
    effective_end=None,
    note=None,
):
    description = _text(description, "Le nom du groupe", 160, True)
    selected = sorted({int(value) for value in (plan_ids or [])})
    if not selected:
        raise ValueError("Sélectionnez au moins un financement.")
    start_value = _optional_date_value(effective_start, "La date de début")
    end_value = _optional_date_value(effective_end, "La date de fin")
    if start_value and end_value and end_value < start_value:
        raise ValueError("La date de fin doit être après la date de début.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM finance_installment_plans
                WHERE user_id=%s AND id=ANY(%s);
                """,
                (user_id, selected),
            )
            valid = {int(row["id"]) for row in cur.fetchall()}
            if valid != set(selected):
                raise ValueError("Un financement sélectionné est introuvable.")

            cur.execute(
                """
                SELECT link.plan_id, budget.description
                FROM finance_budget_financing_group_plans AS link
                JOIN finance_budget_financing_groups AS group_row
                  ON group_row.budget_item_id=link.budget_item_id
                JOIN finance_budget_items AS budget
                  ON budget.id=link.budget_item_id
                WHERE group_row.user_id=%s
                  AND link.plan_id=ANY(%s)
                  AND (%s::BIGINT IS NULL OR link.budget_item_id<>%s::BIGINT);
                """,
                (user_id, selected, budget_item_id, budget_item_id),
            )
            conflicts = cur.fetchall()
            if conflicts:
                names = ", ".join(str(row["description"]) for row in conflicts)
                raise ValueError(
                    "Un financement est déjà associé à un autre groupe Budget : " + names
                )

            # Le montant stocké sert uniquement de valeur de repli; list_budget_items
            # le remplace dynamiquement selon les échéances du mois consulté.
            month = _month_start(start_value or date.today())
            fallback_amount = _financing_group_amount_for_month(
                cur, user_id, selected, month
            )
            if fallback_amount <= 0:
                fallback_amount = Decimal("0.01")

            if budget_item_id:
                cur.execute(
                    """
                    UPDATE finance_budget_items
                    SET description=%s, item_type='expense', input_frequency='monthly',
                        input_amount=%s, biweekly_override=NULL, note=%s,
                        recurrence_id=NULL, sync_from_recurrence=FALSE,
                        effective_start=%s, effective_end=%s,
                        is_active=TRUE, updated_at=NOW()
                    WHERE id=%s AND user_id=%s
                    RETURNING id;
                    """,
                    (
                        description,
                        fallback_amount,
                        _text(note, "La note", 1000),
                        start_value,
                        end_value,
                        int(budget_item_id),
                        user_id,
                    ),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("Groupe Budget introuvable.")
                saved_id = int(row["id"])
            else:
                cur.execute(
                    """
                    SELECT COALESCE(MAX(sort_order),0)+1 AS next_order
                    FROM finance_budget_items
                    WHERE user_id=%s AND item_type='expense';
                    """,
                    (user_id,),
                )
                next_order = int(cur.fetchone()["next_order"])
                cur.execute(
                    """
                    INSERT INTO finance_budget_items (
                        user_id,item_type,description,input_frequency,input_amount,
                        note,sort_order,effective_start,effective_end,is_active
                    )
                    VALUES (%s,'expense',%s,'monthly',%s,%s,%s,%s,%s,TRUE)
                    RETURNING id;
                    """,
                    (
                        user_id,
                        description,
                        fallback_amount,
                        _text(note, "La note", 1000),
                        next_order,
                        start_value,
                        end_value,
                    ),
                )
                saved_id = int(cur.fetchone()["id"])

            cur.execute(
                """
                INSERT INTO finance_budget_financing_groups (budget_item_id,user_id)
                VALUES (%s,%s)
                ON CONFLICT (budget_item_id) DO UPDATE SET
                    user_id=EXCLUDED.user_id, updated_at=NOW();
                """,
                (saved_id, user_id),
            )
            cur.execute(
                "DELETE FROM finance_budget_financing_group_plans WHERE budget_item_id=%s;",
                (saved_id,),
            )
            for plan_id in selected:
                cur.execute(
                    """
                    INSERT INTO finance_budget_financing_group_plans (budget_item_id,plan_id)
                    VALUES (%s,%s);
                    """,
                    (saved_id, plan_id),
                )
            conn.commit()
            return saved_id


def delete_financing_budget_group(user_id, budget_item_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM finance_budget_items
                WHERE id=%s AND user_id=%s
                  AND EXISTS (
                    SELECT 1 FROM finance_budget_financing_groups AS group_row
                    WHERE group_row.budget_item_id=finance_budget_items.id
                  );
                """,
                (int(budget_item_id), user_id),
            )
            count = cur.rowcount
            conn.commit()
            return count


def _fixed_budget_installment_plan_ids(user_id, month_value):
    month = _month_start(month_value)
    rows = list_budget_items(
        user_id,
        month_value=month,
        effective_only=True,
    )
    ids = set()
    for row in rows:
        if row.get("budget_financing_group") and row.get("effective_for_month", True):
            ids.update(int(value) for value in row.get("financing_plan_ids") or [])
    return ids


def dashboard_month_projection(
    user_id,
    month_value,
    *,
    today_value=None,
    kpi_limit=12,
):
    """Tableau : exclut des variables les récurrences ET financements fixes du Budget."""

    projection = _dashboard_month_projection_v190(
        user_id,
        month_value,
        today_value=today_value,
        kpi_limit=max(int(kpi_limit), 1000),
    )
    fixed_recurrence_ids = _fixed_budget_recurrence_ids(user_id, month_value)
    fixed_plan_ids = _fixed_budget_installment_plan_ids(user_id, month_value)

    all_rows = []
    variable_rows = []
    for original in projection["transactions"]:
        row = dict(original)
        recurrence_id = row.get("recurrence_id")
        plan_id = row.get("installment_plan_id")
        fixed_recurrence = bool(
            row["transaction_type"] == "expense"
            and recurrence_id
            and int(recurrence_id) in fixed_recurrence_ids
        )
        fixed_financing = bool(
            row["transaction_type"] == "expense"
            and plan_id
            and int(plan_id) in fixed_plan_ids
        )
        row["fixed_budget"] = fixed_recurrence or fixed_financing
        row["fixed_budget_recurrence"] = fixed_recurrence
        row["fixed_budget_financing"] = fixed_financing
        all_rows.append(row)
        if (
            row["transaction_type"] == "expense"
            and not bool(row.get("budget_excluded"))
            and not row["fixed_budget"]
        ):
            variable_rows.append(row)

    realized_expenses = sum(
        (Decimal(row["amount"]) for row in variable_rows
         if row.get("projection_bucket") == "realized"),
        Decimal("0.00"),
    )
    upcoming_expenses = sum(
        (Decimal(row["amount"]) for row in variable_rows
         if row.get("projection_bucket") == "upcoming"),
        Decimal("0.00"),
    )
    total_expenses = realized_expenses + upcoming_expenses
    fixed_realized = sum(
        (Decimal(row["amount"]) for row in all_rows
         if row.get("fixed_budget")
         and row.get("projection_bucket") == "realized"
         and not bool(row.get("budget_excluded"))),
        Decimal("0.00"),
    )
    fixed_upcoming = sum(
        (Decimal(row["amount"]) for row in all_rows
         if row.get("fixed_budget")
         and row.get("projection_bucket") == "upcoming"
         and not bool(row.get("budget_excluded"))),
        Decimal("0.00"),
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
    variable_upcoming = sorted(
        (row for row in variable_rows if row.get("projection_bucket") == "upcoming"),
        key=lambda row: (row["transaction_date"], str(row["description"]).casefold()),
    )
    capacity = budget_capacity_summary(user_id, month_value)
    remaining_available = Decimal(capacity["available_month"]) - total_expenses

    projection["transactions"] = all_rows
    projection["upcoming_transactions"] = variable_upcoming
    projection["realized"]["expenses"] = realized_expenses
    projection["upcoming"]["expenses"] = upcoming_expenses
    projection["upcoming"]["count"] = len(variable_upcoming)
    projection["total"]["expenses"] = total_expenses
    projection["kpis"]["expense"] = _projection_kpis(
        variable_rows,
        "expense",
        limit=kpi_limit,
        visible_category_ids=visible_category_ids,
        visible_tag_ids=visible_tag_ids,
    )
    projection["fixed_budget"] = {
        "realized": fixed_realized,
        "upcoming": fixed_upcoming,
        "total": fixed_realized + fixed_upcoming,
        "recurrence_ids": sorted(fixed_recurrence_ids),
        "installment_plan_ids": sorted(fixed_plan_ids),
    }
    projection["capacity"] = capacity
    projection["remaining_available"] = remaining_available
    return projection




def budget_forecast(user_id, start_month, months=6, initial_capacity=None):
    """Prévision légère de la capacité variable et du solde de fin de mois.

    Contrairement au Tableau, cette vue n'a besoin ni des KPI par catégorie/
    étiquette ni du détail de toutes les transactions. On évite donc de bâtir
    six fois ``dashboard_month_projection`` lors d'un simple changement de mois.
    Le report est propagé séquentiellement à partir du premier mois affiché.
    """

    start = _month_start(start_month)
    month_count = max(1, min(int(months or 6), 24))
    settings = get_finance_settings(user_id)
    carry_enabled = bool(settings.get("carry_month_balance"))
    carry_start = settings.get("carry_start_month")
    carry_start = _month_start(carry_start) if carry_start else None

    first_capacity = (
        dict(initial_capacity)
        if initial_capacity is not None
        else budget_capacity_summary(user_id, start)
    )
    carry = Decimal(first_capacity.get("carry_in", 0) or 0)
    result = []

    for offset in range(month_count):
        month = _add_months(start, offset)
        if offset == 0:
            capacity = first_capacity
        else:
            # Les mois suivants n'ont besoin que de la capacité de base.
            # Le report est déjà connu grâce au solde du mois précédent.
            capacity = _budget_capacity_summary_v110(user_id, month)
            if not (carry_enabled and carry_start and month > carry_start):
                carry = Decimal("0.00")

        base = Decimal(
            capacity.get("available_month_base", capacity["available_month"])
        )
        expenses = _variable_expense_total_for_month(user_id, month)
        ending = (base + carry - expenses).quantize(Decimal("0.01"))
        result.append(
            {
                "month": month,
                "available_base": base,
                "carry_in": carry,
                "variable_expenses": expenses,
                "ending_balance": ending,
                "pay_count": int(capacity.get("pay_count", 0)),
            }
        )

        # Le résultat d'un mois devient le report du mois suivant seulement à
        # partir du mois d'activation du report.
        if carry_enabled and carry_start and month >= carry_start:
            carry = ending
        else:
            carry = Decimal("0.00")

    return result


def _project_installment_plan_payments_for_month(plan, month_value):
    """Calcule les échéances d'un financement dans un mois si elles ne sont pas matérialisées.

    Les transactions planifiées/confirmées restent prioritaires. Ce calcul sert de
    filet de sécurité pour les anciens plans ou une projection qui n'aurait pas
    encore généré ses lignes finance_transactions.
    """

    if not plan.get("is_active"):
        return Decimal("0.00"), 0

    month = _month_start(month_value)
    month_end = _add_months(month, 1) - timedelta(days=1)
    due = plan.get("display_next_due_date") or plan.get("next_due_date")
    remaining = int(plan.get("display_remaining_installments") or 0)
    if not due or remaining <= 0:
        return Decimal("0.00"), 0

    amount = Decimal(plan.get("installment_amount") or 0)
    balance = Decimal(
        plan.get("estimated_remaining_balance", plan.get("remaining_balance", 0))
        or 0
    )
    zero_cost = (
        Decimal(plan.get("annual_interest_rate") or 0) == 0
        and Decimal(plan.get("fees_total") or 0) == 0
    )
    total = Decimal("0.00")
    count = 0

    for position in range(remaining):
        if due > month_end:
            break
        if due >= month:
            payment = amount
            if zero_cost and position == remaining - 1:
                previous = amount * Decimal(max(0, remaining - 1))
                final_amount = balance - previous
                if final_amount > 0:
                    payment = final_amount.quantize(Decimal("0.01"))
            total += payment
            count += 1
        due = _next_date(
            due,
            plan.get("frequency_unit") or "month",
            int(plan.get("frequency_interval") or 1),
        )

    return total.quantize(Decimal("0.01")), count


def financing_month_summary(user_id, month_value):
    month = _month_start(month_value)
    month_end = _add_months(month, 1) - timedelta(days=1)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tx.installment_plan_id,
                       COALESCE(SUM(tx.amount),0) AS payments,
                       COUNT(*)::INTEGER AS payment_count
                FROM finance_transactions AS tx
                JOIN finance_installment_plans AS plan
                  ON plan.id=tx.installment_plan_id
                WHERE tx.user_id=%s
                  AND tx.transaction_type='expense'
                  AND tx.status IN ('planned','confirmed')
                  AND tx.transaction_date BETWEEN %s AND %s
                GROUP BY tx.installment_plan_id;
                """,
                (user_id, month, month_end),
            )
            materialized = {
                int(row["installment_plan_id"]): {
                    "payments": Decimal(row["payments"] or 0),
                    "payment_count": int(row["payment_count"] or 0),
                }
                for row in cur.fetchall()
            }

    plans = list_installment_plans(user_id, include_inactive=False)
    payments = Decimal("0.00")
    payment_count = 0
    for plan in plans:
        actual = materialized.get(int(plan["id"]))
        if actual is not None:
            payments += actual["payments"]
            payment_count += actual["payment_count"]
            continue
        projected, projected_count = _project_installment_plan_payments_for_month(
            plan, month
        )
        payments += projected
        payment_count += projected_count

    # Les transactions historiques d'un plan devenu inactif restent comptées
    # dans le mois où elles existent réellement.
    active_ids = {int(plan["id"]) for plan in plans}
    for plan_id, actual in materialized.items():
        if plan_id not in active_ids:
            payments += actual["payments"]
            payment_count += actual["payment_count"]

    remaining = sum(
        (Decimal(row.get("estimated_remaining_balance", row.get("remaining_balance", 0)))
         for row in plans),
        Decimal("0.00"),
    )
    return {
        "month": month,
        "payments": payments.quantize(Decimal("0.01")),
        "payment_count": int(payment_count),
        "remaining_balances": remaining.quantize(Decimal("0.01")),
        "active_plan_count": len(plans),
    }


def save_installment_plan(
    user_id,
    *,
    plan_type,
    provider_name,
    description,
    original_amount,
    total_installments,
    next_due_date,
    payment_method_id,
    plan_id=None,
    purchase_date=None,
    completed_installments=0,
    remaining_balance=None,
    installment_amount=None,
    annual_interest_rate=0,
    fees_total=0,
    frequency_unit="month",
    frequency_interval=1,
    category_id=None,
    tag_ids=None,
    budget_excluded=False,
    note=None,
    payment_includes_interest=True,
):
    """Enregistre un financement; calcule le versement total si intérêts exclus."""

    rate = _decimal_value(annual_interest_rate, "Le taux d’intérêt", allow_blank=True) or Decimal("0.00")
    base_payment = (
        _money(installment_amount)
        if installment_amount not in (None, "")
        else None
    )
    includes = bool(payment_includes_interest) or rate <= 0
    calculated = None
    actual_payment = base_payment
    completed_for_save = completed_installments
    completed_was_estimated_here = False

    if rate > 0 and not includes:
        total_count = int(total_installments or 0)
        if completed_installments not in (None, ""):
            completed = int(completed_installments or 0)
        elif (
            base_payment is not None
            and remaining_balance not in (None, "")
            and total_count > 0
        ):
            progress = analyze_installment_progress(
                original_amount=original_amount,
                remaining_balance=remaining_balance,
                installment_amount=base_payment,
                total_installments=total_count,
                completed_installments=None,
            )
            completed = int(progress["estimated_completed_installments"])
            # Le calcul des intérêts doit utiliser la progression estimée avec le
            # montant de base saisi. On transmet donc cette progression au moteur
            # V1.11 afin qu'il ne la réestime pas avec le versement total calculé.
            completed_for_save = completed
            completed_was_estimated_here = True
        else:
            completed = 0
        remaining_count = max(1, total_count - completed)
        principal = (
            _money(remaining_balance, allow_zero=True)
            if remaining_balance not in (None, "")
            else _money(original_amount)
        )
        calculated = _automatic_installment_amount(
            principal,
            remaining_count,
            rate,
            _decimal_value(fees_total, "Les frais", allow_blank=True) or Decimal("0.00"),
            frequency_unit,
            int(frequency_interval or 1),
        )
        actual_payment = calculated

    saved_id = _save_installment_plan_v111(
        user_id,
        plan_type=plan_type,
        provider_name=provider_name,
        description=description,
        original_amount=original_amount,
        total_installments=total_installments,
        next_due_date=next_due_date,
        payment_method_id=payment_method_id,
        plan_id=plan_id,
        purchase_date=purchase_date,
        completed_installments=completed_for_save,
        remaining_balance=remaining_balance,
        installment_amount=actual_payment,
        annual_interest_rate=annual_interest_rate,
        fees_total=fees_total,
        frequency_unit=frequency_unit,
        frequency_interval=frequency_interval,
        category_id=category_id,
        tag_ids=tag_ids,
        budget_excluded=budget_excluded,
        note=note,
    )
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE finance_installment_plans
                SET payment_includes_interest=%s,
                    base_installment_amount=%s,
                    calculated_installment_amount=%s,
                    completed_installments_estimated=CASE
                        WHEN %s THEN TRUE
                        ELSE completed_installments_estimated
                    END,
                    updated_at=NOW()
                WHERE id=%s AND user_id=%s;
                """,
                (
                    includes,
                    base_payment if base_payment is not None else actual_payment,
                    calculated,
                    completed_was_estimated_here,
                    saved_id,
                    user_id,
                ),
            )
            conn.commit()
    return saved_id


def list_installment_plans(user_id, include_inactive=True):
    rows = [dict(row) for row in _list_installment_plans_v111(user_id, include_inactive)]
    for row in rows:
        rate = Decimal(row.get("annual_interest_rate") or 0)
        row["payment_includes_interest"] = bool(row.get("payment_includes_interest", True))
        row["base_installment_amount"] = Decimal(
            row.get("base_installment_amount") or row.get("installment_amount") or 0
        )
        row["calculated_installment_amount"] = (
            Decimal(row["calculated_installment_amount"])
            if row.get("calculated_installment_amount") is not None
            else None
        )
        if rate > 0 and not row["payment_includes_interest"]:
            total_payment = Decimal(row.get("installment_amount") or 0)
            base = Decimal(row.get("base_installment_amount") or 0)
            row["estimated_interest_per_payment"] = max(
                Decimal("0.00"), total_payment - base
            ).quantize(Decimal("0.01"))
        else:
            row["estimated_interest_per_payment"] = None
    return rows
















def export_finances(user_id):
    csv_bytes, json_bytes = _export_finances_v1110(user_id)
    try:
        payload = json.loads(json_bytes.decode("utf-8"))
    except Exception:
        return csv_bytes, json_bytes

    def serial(value):
        if isinstance(value, (date, datetime, time, Decimal)):
            return str(value)
        if isinstance(value, list):
            return [serial(item) for item in value]
        if isinstance(value, dict):
            return {key: serial(item) for key, item in value.items()}
        return value

    payload["version"] = "1.12.0"
    payload["installment_plans"] = [
        serial(dict(row)) for row in list_installment_plans(user_id, include_inactive=True)
    ]
    payload["budget_items"] = [
        serial(dict(row)) for row in list_budget_items(user_id, include_inactive=True)
    ]
    payload["financing_budget_groups"] = [
        serial(dict(row)) for row in list_financing_budget_groups(user_id)
    ]
    payload["shared_loans"] = []
    for loan in list_shared_loans(user_id):
        if loan.get("is_owner"):
            payload["shared_loans"].append(serial(get_shared_loan(user_id, loan["id"])))
    return (
        csv_bytes,
        json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
    )

# Évite une récursion entre le calcul de report mensuel et le Tableau.
def _variable_expense_total_for_month(user_id, month_value):
    month = _month_start(month_value)
    projection = _dashboard_month_projection_v190(
        user_id,
        month,
        kpi_limit=1000,
    )
    # Une seule lecture des postes Budget suffit pour déterminer à la fois les
    # récurrences fixes et les financements regroupés à exclure des variables.
    fixed_rows = list_budget_items(
        user_id,
        month_value=month,
        effective_only=True,
    )
    fixed_recurrence_ids = {
        int(row["recurrence_id"])
        for row in fixed_rows
        if row.get("item_type") == "expense" and row.get("recurrence_id")
    }
    fixed_plan_ids = set()
    for row in fixed_rows:
        if row.get("budget_financing_group"):
            fixed_plan_ids.update(
                int(value) for value in (row.get("financing_plan_ids") or [])
            )
    return sum(
        (
            Decimal(row["amount"])
            for row in projection["transactions"]
            if row["transaction_type"] == "expense"
            and not bool(row.get("budget_excluded"))
            and not (
                row.get("recurrence_id")
                and int(row["recurrence_id"]) in fixed_recurrence_ids
            )
            and not (
                row.get("installment_plan_id")
                and int(row["installment_plan_id"]) in fixed_plan_ids
            )
        ),
        Decimal("0.00"),
    ).quantize(Decimal("0.01"))


def calculate_installment_payment(
    principal,
    remaining_count,
    annual_interest_rate,
    frequency_unit="month",
    frequency_interval=1,
    fees_total=0,
):
    """Calcul public utilisé par le formulaire pour prévisualiser un versement total."""
    principal_value = _money(principal, allow_zero=True)
    count = int(remaining_count or 0)
    rate = _decimal_value(
        annual_interest_rate,
        "Le taux d’intérêt",
        allow_blank=True,
    ) or Decimal("0.00")
    fees = _decimal_value(fees_total, "Les frais", allow_blank=True) or Decimal("0.00")
    if count <= 0:
        return Decimal("0.00")
    return _automatic_installment_amount(
        principal_value,
        count,
        rate,
        fees,
        frequency_unit,
        int(frequency_interval or 1),
    )


def restore_finance_supplement(user_id, payload):
    """Restaure les modules V1.12 absents de l'import transactionnel historique.

    La fusion est non destructive : un financement/groupe/prêt manifestement déjà
    présent est ignoré. Les identifiants de la sauvegarde ne sont jamais réutilisés.
    """
    if not isinstance(payload, dict):
        return {"installment_plans": 0, "financing_groups": 0, "shared_loans": 0}

    methods = {str(row["name"]).strip().casefold(): int(row["id"]) for row in list_payment_methods(user_id, include_inactive=True)}
    categories = {str(row["full_name"]).strip().casefold(): int(row["id"]) for row in list_categories(user_id, include_inactive=True)}
    tags = {str(row["name"]).strip().casefold(): int(row["id"]) for row in list_tags(user_id, include_inactive=True)}
    existing_plans = list_installment_plans(user_id, include_inactive=True)
    existing_plan_keys = {
        (
            str(row.get("provider_name") or "").strip().casefold(),
            str(row.get("description") or "").strip().casefold(),
            Decimal(row.get("original_amount") or 0).quantize(Decimal("0.01")),
        ): int(row["id"])
        for row in existing_plans
    }
    plan_map = {}
    imported_plans = 0

    for raw in payload.get("installment_plans") or []:
        try:
            old_id = int(raw.get("id")) if raw.get("id") is not None else None
            key = (
                str(raw.get("provider_name") or "").strip().casefold(),
                str(raw.get("description") or "").strip().casefold(),
                Decimal(str(raw.get("original_amount") or 0)).quantize(Decimal("0.01")),
            )
            if key in existing_plan_keys:
                if old_id is not None:
                    plan_map[old_id] = existing_plan_keys[key]
                continue
            method_name = str(raw.get("payment_method_name") or "").strip().casefold()
            method_id = methods.get(method_name)
            if method_id is None:
                # Un financement sans mode de paiement valide ne peut pas générer
                # ses versements de façon sécuritaire.
                continue
            category_id = categories.get(str(raw.get("category_full_name") or "").strip().casefold())
            tag_ids = [
                tags[name.strip().casefold()]
                for name in (raw.get("tag_names") or [])
                if name.strip().casefold() in tags
            ]
            saved = save_installment_plan(
                user_id,
                plan_type=raw.get("plan_type") or "merchant",
                provider_name=raw.get("provider_name") or "Financement",
                description=raw.get("description") or "Financement restauré",
                original_amount=raw.get("original_amount") or 0,
                purchase_date=raw.get("purchase_date"),
                total_installments=raw.get("total_installments") or 1,
                completed_installments=(
                    None if raw.get("completed_installments_estimated")
                    else raw.get("completed_installments")
                ),
                remaining_balance=raw.get("remaining_balance"),
                installment_amount=(
                    raw.get("base_installment_amount")
                    if raw.get("payment_includes_interest") is False
                    else raw.get("installment_amount")
                ),
                annual_interest_rate=raw.get("annual_interest_rate") or 0,
                fees_total=raw.get("fees_total") or 0,
                payment_includes_interest=raw.get("payment_includes_interest", True),
                frequency_unit=raw.get("frequency_unit") or "month",
                frequency_interval=raw.get("frequency_interval") or 1,
                next_due_date=raw.get("next_due_date"),
                payment_method_id=method_id,
                category_id=category_id,
                tag_ids=tag_ids,
                budget_excluded=bool(raw.get("budget_excluded", False)),
                note=raw.get("note"),
            )
            existing_plan_keys[key] = saved
            if old_id is not None:
                plan_map[old_id] = saved
            imported_plans += 1
        except Exception:
            continue

    imported_groups = 0
    existing_group_names = {
        str(row.get("description") or "").strip().casefold()
        for row in list_financing_budget_groups(user_id)
    }
    for raw in payload.get("financing_budget_groups") or []:
        try:
            name = str(raw.get("description") or "").strip()
            if not name or name.casefold() in existing_group_names:
                continue
            mapped = [
                plan_map[int(old_id)]
                for old_id in (raw.get("financing_plan_ids") or [])
                if int(old_id) in plan_map
            ]
            if not mapped:
                continue
            save_financing_budget_group(
                user_id,
                description=name,
                plan_ids=mapped,
                effective_start=raw.get("effective_start"),
                effective_end=raw.get("effective_end"),
                note=raw.get("note"),
            )
            existing_group_names.add(name.casefold())
            imported_groups += 1
        except Exception:
            continue

    imported_loans = 0
    owned_existing = {
        (
            str(row.get("title") or "").strip().casefold(),
            Decimal(row.get("original_balance") or 0).quantize(Decimal("0.01")),
        )
        for row in list_shared_loans(user_id)
        if row.get("is_owner")
    }
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id,email FROM users WHERE is_active=TRUE;")
            user_by_email = {
                str(row["email"]).strip().casefold(): int(row["id"])
                for row in cur.fetchall()
            }
    for raw in payload.get("shared_loans") or []:
        try:
            key = (
                str(raw.get("title") or "").strip().casefold(),
                Decimal(str(raw.get("original_balance") or 0)).quantize(Decimal("0.01")),
            )
            if key in owned_existing:
                continue
            members = []
            for member in raw.get("members") or []:
                member_id = user_by_email.get(str(member.get("email") or "").strip().casefold())
                if member_id and member_id != int(user_id):
                    members.append(
                        {
                            "user_id": member_id,
                            "role": member.get("role") or "observer",
                            "permission": member.get("permission") or "view",
                        }
                    )
            loan_id = save_shared_loan(
                user_id,
                title=raw.get("title") or "Prêt restauré",
                lender_name=raw.get("lender_name"),
                borrower_name=raw.get("borrower_name"),
                original_balance=raw.get("original_balance") or 0,
                current_balance=raw.get("current_balance"),
                annual_interest_rate=raw.get("annual_interest_rate") or 0,
                payment_amount=raw.get("payment_amount"),
                frequency_unit=raw.get("frequency_unit") or "month",
                frequency_interval=raw.get("frequency_interval") or 1,
                start_date=raw.get("start_date"),
                next_due_date=raw.get("next_due_date"),
                end_date=raw.get("end_date"),
                note=raw.get("note"),
                status=raw.get("status") or "active",
                members=members,
            )
            # L'historique d'un prêt restauré est volontairement reconstitué en
            # lecture seulement par une note synthétique; le solde actuel reste
            # celui du fichier et aucun ancien mouvement n'est rejoué deux fois.
            if raw.get("events"):
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        for event in reversed(raw.get("events") or []):
                            cur.execute(
                                """
                                INSERT INTO finance_shared_loan_events (
                                    loan_id,created_by_user_id,event_date,event_type,amount,
                                    interest_amount,principal_amount,balance_after,note,created_at
                                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,COALESCE(%s,NOW()));
                                """,
                                (
                                    loan_id,user_id,event.get("event_date") or date.today(),
                                    event.get("event_type") or "note",event.get("amount") or 0,
                                    event.get("interest_amount") or 0,event.get("principal_amount") or 0,
                                    event.get("balance_after") or raw.get("current_balance") or 0,
                                    event.get("note"),event.get("created_at"),
                                ),
                            )
                        conn.commit()
            owned_existing.add(key)
            imported_loans += 1
        except Exception:
            continue

    return {
        "installment_plans": imported_plans,
        "financing_groups": imported_groups,
        "shared_loans": imported_loans,
    }
