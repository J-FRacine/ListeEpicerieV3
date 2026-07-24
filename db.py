import os

import psycopg
from psycopg import sql
from psycopg.rows import dict_row


VALID_FAMILY_ROLES = {"owner", "admin", "member"}


def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "La variable d’environnement DATABASE_URL n’est pas définie."
        )

    return psycopg.connect(
        database_url,
        row_factory=dict_row,
    )


# ---------------------------------------------------------
# INITIALISATION ET MIGRATION DES CATÉGORIES
# ---------------------------------------------------------


def _categories_have_family_id(cur):
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'categories'
              AND column_name = 'family_id'
        ) AS exists;
        """
    )
    return cur.fetchone()["exists"]


def _add_categories_family_column(cur):
    if not _categories_have_family_id(cur):
        cur.execute(
            """
            ALTER TABLE categories
            ADD COLUMN family_id INTEGER;
            """
        )

    cur.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'categories_family_id_fkey'
                  AND conrelid = 'categories'::regclass
            ) THEN
                ALTER TABLE categories
                ADD CONSTRAINT categories_family_id_fkey
                FOREIGN KEY (family_id)
                REFERENCES families(id)
                ON DELETE CASCADE;
            END IF;
        END
        $$;
        """
    )


def _drop_legacy_category_name_uniqueness(cur):
    cur.execute(
        """
        ALTER TABLE categories
        DROP CONSTRAINT IF EXISTS categories_name_key;
        """
    )

    cur.execute(
        """
        SELECT table_constraint.constraint_name
        FROM information_schema.table_constraints AS table_constraint
        JOIN information_schema.constraint_column_usage AS column_usage
          ON column_usage.constraint_schema = table_constraint.constraint_schema
         AND column_usage.constraint_name = table_constraint.constraint_name
         AND column_usage.table_schema = table_constraint.table_schema
         AND column_usage.table_name = table_constraint.table_name
        WHERE table_constraint.table_schema = 'public'
          AND table_constraint.table_name = 'categories'
          AND table_constraint.constraint_type = 'UNIQUE'
        GROUP BY table_constraint.constraint_name
        HAVING COUNT(*) = 1
           AND MIN(column_usage.column_name) = 'name';
        """
    )

    for row in cur.fetchall():
        cur.execute(
            sql.SQL(
                """
                ALTER TABLE categories
                DROP CONSTRAINT IF EXISTS {};
                """
            ).format(sql.Identifier(row["constraint_name"]))
        )

    cur.execute(
        """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = 'categories'
          AND indexdef ILIKE 'CREATE UNIQUE INDEX%%'
          AND indexdef ILIKE '%%name%%'
          AND indexdef NOT ILIKE '%%family_id%%';
        """
    )

    for row in cur.fetchall():
        cur.execute(
            sql.SQL("DROP INDEX IF EXISTS public.{};").format(
                sql.Identifier(row["indexname"])
            )
        )


def _remove_duplicate_family_categories(cur):
    cur.execute(
        """
        WITH category_groups AS (
            SELECT
                id,
                MIN(id) OVER (
                    PARTITION BY
                        family_id,
                        LOWER(
                            COALESCE(
                                NULLIF(BTRIM(name), ''),
                                'Sans catégorie'
                            )
                        )
                ) AS keeper_id
            FROM categories
            WHERE family_id IS NOT NULL
        )
        UPDATE items AS item
        SET category_id = category_groups.keeper_id
        FROM category_groups
        WHERE item.category_id = category_groups.id
          AND category_groups.id <> category_groups.keeper_id;
        """
    )

    cur.execute(
        """
        WITH category_groups AS (
            SELECT
                id,
                MIN(id) OVER (
                    PARTITION BY
                        family_id,
                        LOWER(
                            COALESCE(
                                NULLIF(BTRIM(name), ''),
                                'Sans catégorie'
                            )
                        )
                ) AS keeper_id
            FROM categories
            WHERE family_id IS NOT NULL
        )
        DELETE FROM categories AS category
        USING category_groups
        WHERE category.id = category_groups.id
          AND category_groups.id <> category_groups.keeper_id;
        """
    )


def _copy_legacy_categories_to_all_families(cur):
    cur.execute(
        """
        WITH legacy_categories AS (
            SELECT DISTINCT ON (
                LOWER(
                    COALESCE(
                        NULLIF(BTRIM(name), ''),
                        'Sans catégorie'
                    )
                )
            )
                COALESCE(
                    NULLIF(BTRIM(name), ''),
                    'Sans catégorie'
                ) AS category_name,
                LOWER(
                    COALESCE(
                        NULLIF(BTRIM(name), ''),
                        'Sans catégorie'
                    )
                ) AS normalized_name
            FROM categories
            WHERE family_id IS NULL
            ORDER BY normalized_name, id
        )
        INSERT INTO categories (family_id, name)
        SELECT family.id, legacy_category.category_name
        FROM families AS family
        CROSS JOIN legacy_categories AS legacy_category
        WHERE NOT EXISTS (
            SELECT 1
            FROM categories AS existing_category
            WHERE existing_category.family_id = family.id
              AND LOWER(
                    COALESCE(
                        NULLIF(BTRIM(existing_category.name), ''),
                        'Sans catégorie'
                    )
                  ) = legacy_category.normalized_name
        );
        """
    )


def _ensure_local_category_for_each_item(cur):
    cur.execute(
        """
        WITH item_category_names AS (
            SELECT DISTINCT
                item.family_id,
                COALESCE(
                    NULLIF(BTRIM(category.name), ''),
                    'Sans catégorie'
                ) AS category_name,
                LOWER(
                    COALESCE(
                        NULLIF(BTRIM(category.name), ''),
                        'Sans catégorie'
                    )
                ) AS normalized_name
            FROM items AS item
            JOIN categories AS category
              ON category.id = item.category_id
        )
        INSERT INTO categories (family_id, name)
        SELECT item_category.family_id, item_category.category_name
        FROM item_category_names AS item_category
        WHERE NOT EXISTS (
            SELECT 1
            FROM categories AS existing_category
            WHERE existing_category.family_id = item_category.family_id
              AND LOWER(
                    COALESCE(
                        NULLIF(BTRIM(existing_category.name), ''),
                        'Sans catégorie'
                    )
                  ) = item_category.normalized_name
        );
        """
    )


def _move_items_to_their_family_categories(cur):
    cur.execute(
        """
        UPDATE items AS item
        SET category_id = local_category.id
        FROM categories AS current_category,
             categories AS local_category
        WHERE current_category.id = item.category_id
          AND local_category.family_id = item.family_id
          AND LOWER(
                COALESCE(
                    NULLIF(BTRIM(local_category.name), ''),
                    'Sans catégorie'
                )
              ) = LOWER(
                COALESCE(
                    NULLIF(BTRIM(current_category.name), ''),
                    'Sans catégorie'
                )
              )
          AND current_category.family_id IS DISTINCT FROM item.family_id;
        """
    )


def _migrate_categories_to_families(cur):
    _add_categories_family_column(cur)
    _drop_legacy_category_name_uniqueness(cur)
    _remove_duplicate_family_categories(cur)

    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS categories_family_name_unique
        ON categories (
            family_id,
            LOWER(
                COALESCE(
                    NULLIF(BTRIM(name), ''),
                    'Sans catégorie'
                )
            )
        )
        WHERE family_id IS NOT NULL;
        """
    )

    _copy_legacy_categories_to_all_families(cur)
    _ensure_local_category_for_each_item(cur)
    _move_items_to_their_family_categories(cur)


# ---------------------------------------------------------
# INITIALISATION GÉNÉRALE
# ---------------------------------------------------------


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS families (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    family_id INTEGER
                        REFERENCES families(id)
                        ON DELETE CASCADE,
                    name TEXT NOT NULL
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    family_id INTEGER NOT NULL
                        REFERENCES families(id),
                    category_id INTEGER NOT NULL
                        REFERENCES categories(id),
                    name TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    needed INTEGER NOT NULL DEFAULT 0
                );
                """
            )

            _migrate_categories_to_families(cur)

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_unique
                ON users (LOWER(BTRIM(email)));
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS family_members (
                    family_id INTEGER NOT NULL
                        REFERENCES families(id)
                        ON DELETE CASCADE,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,
                    role TEXT NOT NULL DEFAULT 'member'
                        CHECK (role IN ('owner', 'admin', 'member')),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (family_id, user_id)
                );
                """
            )

            conn.commit()


# ---------------------------------------------------------
# OUTILS D'AUTORISATION
# ---------------------------------------------------------


def _get_active_user(cur, user_id):
    cur.execute(
        """
        SELECT
            id,
            display_name,
            email,
            password_hash,
            is_admin,
            is_active,
            created_at
        FROM users
        WHERE id = %s;
        """,
        (user_id,),
    )
    user = cur.fetchone()

    if user is None or not user["is_active"]:
        raise PermissionError("La session utilisateur n’est plus valide.")

    return user


def _require_global_admin(cur, user_id):
    user = _get_active_user(cur, user_id)

    if not user["is_admin"]:
        raise PermissionError("Cette action est réservée à l’administrateur.")

    return user


def _get_family_role(cur, user_id, family_id):
    user = _get_active_user(cur, user_id)

    if user["is_admin"]:
        return "admin"

    cur.execute(
        """
        SELECT role
        FROM family_members
        WHERE user_id = %s
          AND family_id = %s;
        """,
        (user_id, family_id),
    )
    row = cur.fetchone()
    return row["role"] if row else None


def _require_family_access(cur, user_id, family_id, manage=False):
    role = _get_family_role(cur, user_id, family_id)

    if role is None:
        raise PermissionError("Vous n’avez pas accès à cette famille.")

    if manage and role not in {"owner", "admin"}:
        raise PermissionError("Vous ne pouvez pas administrer cette famille.")

    return role


# ---------------------------------------------------------
# UTILISATEURS ET AUTHENTIFICATION
# ---------------------------------------------------------


def count_users():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*)::INTEGER AS user_count FROM users;")
            return cur.fetchone()["user_count"]


def needs_initial_admin_setup():
    """Indique si le portail doit afficher la configuration initiale.

    En plus d'une base sans utilisateur, cette fonction reconnaît le
    compte provisoire historique admin@local comme non configuré.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*)::INTEGER AS user_count,
                    MIN(LOWER(BTRIM(email))) AS only_email
                FROM users;
                """
            )
            row = cur.fetchone()

            return (
                row["user_count"] == 0
                or (
                    row["user_count"] == 1
                    and row["only_email"] == "admin@local"
                )
            )


def get_user_by_email(email):
    normalized_email = (email or "").strip()

    if not normalized_email:
        return None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    display_name,
                    email,
                    password_hash,
                    is_admin,
                    is_active,
                    created_at
                FROM users
                WHERE LOWER(BTRIM(email)) = LOWER(BTRIM(%s));
                """,
                (normalized_email,),
            )
            return cur.fetchone()


def get_user_by_id(user_id):
    if user_id is None:
        return None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    display_name,
                    email,
                    password_hash,
                    is_admin,
                    is_active,
                    created_at
                FROM users
                WHERE id = %s;
                """,
                (user_id,),
            )
            return cur.fetchone()


def create_first_admin(display_name, email, password_hash):
    """Crée le premier administrateur ou réclame admin@local.

    Le compte admin@local provenait d'une ancienne étape provisoire du
    projet. S'il est le seul compte présent, on le transforme en vrai
    compte administrateur au lieu de bloquer la configuration initiale.
    """

    name = (display_name or "").strip()
    normalized_email = (email or "").strip().lower()

    if not name:
        raise ValueError("Le nom est obligatoire.")

    if not normalized_email:
        raise ValueError("L’adresse courriel est obligatoire.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("LOCK TABLE users IN EXCLUSIVE MODE;")
            cur.execute(
                """
                SELECT
                    id,
                    LOWER(BTRIM(email)) AS normalized_email
                FROM users
                ORDER BY id;
                """
            )
            existing_users = cur.fetchall()

            if not existing_users:
                cur.execute(
                    """
                    INSERT INTO users (
                        display_name,
                        email,
                        password_hash,
                        is_admin,
                        is_active
                    )
                    VALUES (%s, %s, %s, TRUE, TRUE)
                    RETURNING
                        id,
                        display_name,
                        email,
                        is_admin,
                        is_active;
                    """,
                    (name, normalized_email, password_hash),
                )
                user = cur.fetchone()

            elif (
                len(existing_users) == 1
                and existing_users[0]["normalized_email"]
                == "admin@local"
            ):
                cur.execute(
                    """
                    UPDATE users
                    SET
                        display_name = %s,
                        email = %s,
                        password_hash = %s,
                        is_admin = TRUE,
                        is_active = TRUE
                    WHERE id = %s
                    RETURNING
                        id,
                        display_name,
                        email,
                        is_admin,
                        is_active;
                    """,
                    (
                        name,
                        normalized_email,
                        password_hash,
                        existing_users[0]["id"],
                    ),
                )
                user = cur.fetchone()

            else:
                raise ValueError(
                    "Le premier administrateur existe déjà."
                )

            cur.execute(
                """
                INSERT INTO family_members (family_id, user_id, role)
                SELECT id, %s, 'owner'
                FROM families
                ON CONFLICT (family_id, user_id) DO UPDATE
                SET role = EXCLUDED.role;
                """,
                (user["id"],),
            )

            conn.commit()
            return user


def list_users_for_admin(actor_user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_global_admin(cur, actor_user_id)

            cur.execute(
                """
                SELECT
                    user_account.id,
                    user_account.display_name,
                    user_account.email,
                    user_account.is_admin,
                    user_account.is_active,
                    user_account.created_at,
                    COALESCE(
                        ARRAY_AGG(member.family_id ORDER BY member.family_id)
                        FILTER (WHERE member.family_id IS NOT NULL),
                        ARRAY[]::INTEGER[]
                    ) AS family_ids,
                    COALESCE(
                        ARRAY_AGG(family.name ORDER BY LOWER(family.name))
                        FILTER (WHERE family.id IS NOT NULL),
                        ARRAY[]::TEXT[]
                    ) AS family_names
                FROM users AS user_account
                LEFT JOIN family_members AS member
                  ON member.user_id = user_account.id
                LEFT JOIN families AS family
                  ON family.id = member.family_id
                GROUP BY user_account.id
                ORDER BY LOWER(user_account.display_name), user_account.id;
                """
            )
            return cur.fetchall()


def create_user_for_admin(
    actor_user_id,
    display_name,
    email,
    password_hash,
    family_ids,
    is_admin=False,
):
    name = (display_name or "").strip()
    normalized_email = (email or "").strip().lower()

    if not name:
        raise ValueError("Le nom est obligatoire.")

    if not normalized_email:
        raise ValueError("L’adresse courriel est obligatoire.")

    family_ids = sorted({int(family_id) for family_id in (family_ids or [])})

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_global_admin(cur, actor_user_id)

            cur.execute(
                """
                SELECT 1
                FROM users
                WHERE LOWER(BTRIM(email)) = LOWER(BTRIM(%s))
                LIMIT 1;
                """,
                (normalized_email,),
            )

            if cur.fetchone() is not None:
                raise ValueError("Un compte utilise déjà cette adresse courriel.")

            cur.execute(
                """
                INSERT INTO users (
                    display_name,
                    email,
                    password_hash,
                    is_admin,
                    is_active
                )
                VALUES (%s, %s, %s, %s, TRUE)
                RETURNING id;
                """,
                (name, normalized_email, password_hash, bool(is_admin)),
            )
            user_id = cur.fetchone()["id"]

            if family_ids:
                cur.execute(
                    """
                    INSERT INTO family_members (family_id, user_id, role)
                    SELECT family.id, %s, 'member'
                    FROM families AS family
                    WHERE family.id = ANY(%s)
                    ON CONFLICT (family_id, user_id) DO NOTHING;
                    """,
                    (user_id, family_ids),
                )

            conn.commit()
            return user_id


def set_user_memberships_for_admin(actor_user_id, target_user_id, family_ids):
    family_ids = sorted({int(family_id) for family_id in (family_ids or [])})

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_global_admin(cur, actor_user_id)
            _get_active_user(cur, target_user_id)

            cur.execute(
                """
                DELETE FROM family_members
                WHERE user_id = %s
                  AND role = 'member';
                """,
                (target_user_id,),
            )

            if family_ids:
                cur.execute(
                    """
                    INSERT INTO family_members (family_id, user_id, role)
                    SELECT family.id, %s, 'member'
                    FROM families AS family
                    WHERE family.id = ANY(%s)
                    ON CONFLICT (family_id, user_id) DO UPDATE
                    SET role = CASE
                        WHEN family_members.role IN ('owner', 'admin')
                            THEN family_members.role
                        ELSE 'member'
                    END;
                    """,
                    (target_user_id, family_ids),
                )

            conn.commit()


def set_user_active_for_admin(actor_user_id, target_user_id, is_active):
    if int(actor_user_id) == int(target_user_id) and not is_active:
        raise ValueError("Vous ne pouvez pas désactiver votre propre compte.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_global_admin(cur, actor_user_id)

            cur.execute(
                """
                UPDATE users
                SET is_active = %s
                WHERE id = %s;
                """,
                (bool(is_active), target_user_id),
            )

            if cur.rowcount == 0:
                raise ValueError("Ce compte n’existe plus.")

            conn.commit()


def reset_user_password_for_admin(actor_user_id, target_user_id, password_hash):
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_global_admin(cur, actor_user_id)

            cur.execute(
                """
                UPDATE users
                SET password_hash = %s
                WHERE id = %s;
                """,
                (password_hash, target_user_id),
            )

            if cur.rowcount == 0:
                raise ValueError("Ce compte n’existe plus.")

            conn.commit()


def update_own_profile(user_id, display_name):
    name = (display_name or "").strip()

    if not name:
        raise ValueError("Le nom est obligatoire.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            _get_active_user(cur, user_id)
            cur.execute(
                """
                UPDATE users
                SET display_name = %s
                WHERE id = %s;
                """,
                (name, user_id),
            )
            conn.commit()


def update_own_password_hash(user_id, password_hash):
    with get_connection() as conn:
        with conn.cursor() as cur:
            _get_active_user(cur, user_id)
            cur.execute(
                """
                UPDATE users
                SET password_hash = %s
                WHERE id = %s;
                """,
                (password_hash, user_id),
            )
            conn.commit()


# ---------------------------------------------------------
# FAMILLES ET ACCÈS
# ---------------------------------------------------------


def get_accessible_families(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            user = _get_active_user(cur, user_id)

            if user["is_admin"]:
                cur.execute(
                    """
                    SELECT id, name, 'admin'::TEXT AS role, TRUE AS can_manage
                    FROM families
                    ORDER BY LOWER(name), name;
                    """
                )
            else:
                cur.execute(
                    """
                    SELECT
                        family.id,
                        family.name,
                        member.role,
                        member.role IN ('owner', 'admin') AS can_manage
                    FROM families AS family
                    JOIN family_members AS member
                      ON member.family_id = family.id
                    WHERE member.user_id = %s
                    ORDER BY LOWER(family.name), family.name;
                    """,
                    (user_id,),
                )

            return cur.fetchall()


def get_accessible_families_with_stats(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            user = _get_active_user(cur, user_id)

            if user["is_admin"]:
                access_join = ""
                access_where = ""
                params = ()
                role_expression = "'admin'::TEXT"
                manage_expression = "TRUE"
            else:
                access_join = (
                    "JOIN family_members AS access_member "
                    "ON access_member.family_id = family.id"
                )
                access_where = "WHERE access_member.user_id = %s"
                params = (user_id,)
                role_expression = "access_member.role"
                manage_expression = "access_member.role IN ('owner', 'admin')"

            query = f"""
                SELECT
                    family.id,
                    family.name,
                    {role_expression} AS role,
                    {manage_expression} AS can_manage,
                    (
                        SELECT COUNT(*)::INTEGER
                        FROM categories AS category
                        WHERE category.family_id = family.id
                    ) AS category_count,
                    (
                        SELECT COUNT(*)::INTEGER
                        FROM items AS item
                        WHERE item.family_id = family.id
                    ) AS item_count,
                    (
                        SELECT COUNT(*)::INTEGER
                        FROM items AS item
                        WHERE item.family_id = family.id
                          AND item.needed = 1
                    ) AS needed_count,
                    (
                        SELECT COUNT(*)::INTEGER
                        FROM family_members AS member_count
                        WHERE member_count.family_id = family.id
                    ) AS member_count
                FROM families AS family
                {access_join}
                {access_where}
                ORDER BY LOWER(family.name), family.name;
            """
            cur.execute(query, params)
            return cur.fetchall()


def create_family_for_user(user_id, name):
    family_name = (name or "").strip()

    if not family_name:
        raise ValueError("Le nom de la famille est obligatoire.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            _get_active_user(cur, user_id)

            cur.execute(
                """
                SELECT 1
                FROM families
                WHERE LOWER(BTRIM(name)) = LOWER(BTRIM(%s))
                LIMIT 1;
                """,
                (family_name,),
            )

            if cur.fetchone() is not None:
                raise ValueError(f"La famille « {family_name} » existe déjà.")

            cur.execute(
                """
                INSERT INTO families (name)
                VALUES (%s)
                RETURNING id;
                """,
                (family_name,),
            )
            family_id = cur.fetchone()["id"]

            cur.execute(
                """
                INSERT INTO family_members (family_id, user_id, role)
                VALUES (%s, %s, 'owner');
                """,
                (family_id, user_id),
            )

            cur.execute(
                """
                INSERT INTO categories (family_id, name)
                SELECT %s, legacy_category.name
                FROM categories AS legacy_category
                WHERE legacy_category.family_id IS NULL
                ON CONFLICT DO NOTHING;
                """,
                (family_id,),
            )

            conn.commit()
            return family_id


def rename_family_for_user(user_id, family_id, new_name):
    family_name = (new_name or "").strip()

    if not family_name:
        raise ValueError("Le nom de la famille est obligatoire.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_family_access(cur, user_id, family_id, manage=True)

            cur.execute(
                """
                SELECT 1
                FROM families
                WHERE LOWER(BTRIM(name)) = LOWER(BTRIM(%s))
                  AND id <> %s
                LIMIT 1;
                """,
                (family_name, family_id),
            )

            if cur.fetchone() is not None:
                raise ValueError(f"La famille « {family_name} » existe déjà.")

            cur.execute(
                """
                UPDATE families
                SET name = %s
                WHERE id = %s;
                """,
                (family_name, family_id),
            )

            if cur.rowcount == 0:
                raise ValueError("Cette famille n’existe plus.")

            conn.commit()


def delete_family_for_user(user_id, family_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_family_access(cur, user_id, family_id, manage=True)

            cur.execute("DELETE FROM items WHERE family_id = %s;", (family_id,))
            cur.execute("DELETE FROM families WHERE id = %s;", (family_id,))

            if cur.rowcount == 0:
                raise ValueError("Cette famille n’existe plus.")

            conn.commit()


# ---------------------------------------------------------
# CATÉGORIES PROPRES À UNE FAMILLE
# ---------------------------------------------------------


def get_categories(user_id, family_id):
    if family_id is None:
        return []

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT id, name
                FROM categories
                WHERE family_id = %s
                ORDER BY LOWER(name), name;
                """,
                (family_id,),
            )
            return cur.fetchall()


def get_categories_with_counts(user_id, family_id):
    if family_id is None:
        return []

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT
                    category.id,
                    category.name,
                    COUNT(item.id)::INTEGER AS item_count
                FROM categories AS category
                LEFT JOIN items AS item
                  ON item.category_id = category.id
                 AND item.family_id = %s
                WHERE category.family_id = %s
                GROUP BY category.id, category.name
                ORDER BY LOWER(category.name), category.name;
                """,
                (family_id, family_id),
            )
            return cur.fetchall()


def _category_name_exists(cur, family_id, name, exclude_category_id=None):
    if exclude_category_id is None:
        cur.execute(
            """
            SELECT 1
            FROM categories
            WHERE family_id = %s
              AND LOWER(BTRIM(name)) = LOWER(BTRIM(%s))
            LIMIT 1;
            """,
            (family_id, name),
        )
    else:
        cur.execute(
            """
            SELECT 1
            FROM categories
            WHERE family_id = %s
              AND LOWER(BTRIM(name)) = LOWER(BTRIM(%s))
              AND id <> %s
            LIMIT 1;
            """,
            (family_id, name, exclude_category_id),
        )

    return cur.fetchone() is not None


def create_category(user_id, family_id, name):
    category_name = (name or "").strip()

    if not category_name:
        raise ValueError("Le nom de la catégorie est obligatoire.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_family_access(cur, user_id, family_id)

            if _category_name_exists(cur, family_id, category_name):
                raise ValueError(
                    f"La catégorie « {category_name} » existe déjà dans cette famille."
                )

            cur.execute(
                """
                INSERT INTO categories (family_id, name)
                VALUES (%s, %s)
                RETURNING id;
                """,
                (family_id, category_name),
            )
            category_id = cur.fetchone()["id"]
            conn.commit()
            return category_id


def rename_category(user_id, family_id, category_id, new_name):
    category_name = (new_name or "").strip()

    if not category_name:
        raise ValueError("Le nom de la catégorie est obligatoire.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_family_access(cur, user_id, family_id)

            if _category_name_exists(
                cur,
                family_id,
                category_name,
                exclude_category_id=category_id,
            ):
                raise ValueError(
                    f"La catégorie « {category_name} » existe déjà dans cette famille."
                )

            cur.execute(
                """
                UPDATE categories
                SET name = %s
                WHERE id = %s
                  AND family_id = %s;
                """,
                (category_name, category_id, family_id),
            )

            if cur.rowcount == 0:
                raise ValueError("Cette catégorie n’existe plus.")

            conn.commit()


def merge_categories(
    user_id,
    family_id,
    source_category_id,
    destination_category_id,
):
    if source_category_id == destination_category_id:
        raise ValueError("La catégorie de destination doit être différente.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_family_access(cur, user_id, family_id)

            cur.execute(
                """
                SELECT id
                FROM categories
                WHERE family_id = %s
                  AND id IN (%s, %s);
                """,
                (family_id, source_category_id, destination_category_id),
            )

            if len(cur.fetchall()) != 2:
                raise ValueError(
                    "Les deux catégories doivent appartenir à la famille active."
                )

            cur.execute(
                """
                UPDATE items
                SET category_id = %s
                WHERE family_id = %s
                  AND category_id = %s;
                """,
                (destination_category_id, family_id, source_category_id),
            )
            moved_item_count = cur.rowcount

            cur.execute(
                """
                DELETE FROM categories
                WHERE id = %s
                  AND family_id = %s;
                """,
                (source_category_id, family_id),
            )

            conn.commit()
            return moved_item_count


def delete_category(user_id, family_id, category_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_family_access(cur, user_id, family_id)

            cur.execute(
                """
                SELECT COUNT(*)::INTEGER AS item_count
                FROM items
                WHERE family_id = %s
                  AND category_id = %s;
                """,
                (family_id, category_id),
            )
            item_count = cur.fetchone()["item_count"]

            if item_count > 0:
                raise ValueError(
                    "Cette catégorie contient encore "
                    f"{item_count} item(s). Fusionnez-la d’abord."
                )

            cur.execute(
                """
                DELETE FROM categories
                WHERE id = %s
                  AND family_id = %s;
                """,
                (category_id, family_id),
            )

            if cur.rowcount == 0:
                raise ValueError("Cette catégorie n’existe plus.")

            conn.commit()


# ---------------------------------------------------------
# ITEMS
# ---------------------------------------------------------


def get_items(user_id, family_id):
    if family_id is None:
        return []

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_family_access(cur, user_id, family_id)
            cur.execute(
                """
                SELECT
                    item.id,
                    item.name,
                    item.quantity,
                    item.needed,
                    category.name AS category
                FROM items AS item
                JOIN categories AS category
                  ON category.id = item.category_id
                WHERE item.family_id = %s
                ORDER BY item.id;
                """,
                (family_id,),
            )
            return cur.fetchall()


def _category_belongs_to_family(cur, family_id, category_id):
    cur.execute(
        """
        SELECT 1
        FROM categories
        WHERE id = %s
          AND family_id = %s
        LIMIT 1;
        """,
        (category_id, family_id),
    )
    return cur.fetchone() is not None


def add_item(user_id, family_id, category_id, name, quantity, needed):
    item_name = (name or "").strip()
    item_quantity = int(quantity or 1)
    item_needed = 1 if needed else 0

    if not item_name:
        raise ValueError("Le nom de l’item est obligatoire.")

    if item_quantity < 1:
        raise ValueError("La quantité doit être d’au moins 1.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_family_access(cur, user_id, family_id)

            if not _category_belongs_to_family(cur, family_id, category_id):
                raise ValueError(
                    "La catégorie choisie n’appartient pas à la famille active."
                )

            cur.execute(
                """
                INSERT INTO items (
                    family_id,
                    category_id,
                    name,
                    quantity,
                    needed
                )
                VALUES (%s, %s, %s, %s, %s);
                """,
                (
                    family_id,
                    category_id,
                    item_name,
                    item_quantity,
                    item_needed,
                ),
            )
            conn.commit()


def update_item(user_id, item_id, category_id, name, quantity, needed):
    item_name = (name or "").strip()
    item_quantity = int(quantity or 1)
    item_needed = 1 if needed else 0

    if not item_name:
        raise ValueError("Le nom de l’item est obligatoire.")

    if item_quantity < 1:
        raise ValueError("La quantité doit être d’au moins 1.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT family_id FROM items WHERE id = %s;",
                (item_id,),
            )
            item = cur.fetchone()

            if item is None:
                raise ValueError("Cet item n’existe plus.")

            family_id = item["family_id"]
            _require_family_access(cur, user_id, family_id)

            if not _category_belongs_to_family(cur, family_id, category_id):
                raise ValueError(
                    "La catégorie choisie n’appartient pas à la famille de cet item."
                )

            cur.execute(
                """
                UPDATE items
                SET
                    category_id = %s,
                    name = %s,
                    quantity = %s,
                    needed = %s
                WHERE id = %s;
                """,
                (
                    category_id,
                    item_name,
                    item_quantity,
                    item_needed,
                    item_id,
                ),
            )
            conn.commit()


def toggle_needed(user_id, item_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT family_id, needed FROM items WHERE id = %s;",
                (item_id,),
            )
            row = cur.fetchone()

            if row is None:
                raise ValueError("Cet item n’existe plus.")

            _require_family_access(cur, user_id, row["family_id"])
            new_value = 0 if row["needed"] == 1 else 1

            cur.execute(
                "UPDATE items SET needed = %s WHERE id = %s;",
                (new_value, item_id),
            )
            conn.commit()


def delete_item(user_id, item_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT family_id FROM items WHERE id = %s;",
                (item_id,),
            )
            row = cur.fetchone()

            if row is None:
                raise ValueError("Cet item n’existe plus.")

            _require_family_access(cur, user_id, row["family_id"])
            cur.execute("DELETE FROM items WHERE id = %s;", (item_id,))
            conn.commit()


# ---------------------------------------------------------
# IMPORTATION ET EXPORTATION
# ---------------------------------------------------------


def export_family_backup(user_id, family_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_family_access(cur, user_id, family_id)

            cur.execute(
                "SELECT id, name FROM families WHERE id = %s;",
                (family_id,),
            )
            family = cur.fetchone()

            if family is None:
                raise ValueError("Cette famille n’existe plus.")

            cur.execute(
                """
                SELECT name
                FROM categories
                WHERE family_id = %s
                ORDER BY LOWER(name), name;
                """,
                (family_id,),
            )
            categories = [{"name": row["name"]} for row in cur.fetchall()]

            cur.execute(
                """
                SELECT
                    item.name,
                    item.quantity,
                    item.needed,
                    category.name AS category
                FROM items AS item
                JOIN categories AS category
                  ON category.id = item.category_id
                WHERE item.family_id = %s
                ORDER BY LOWER(category.name), LOWER(item.name), item.id;
                """,
                (family_id,),
            )
            items = [
                {
                    "name": row["name"],
                    "quantity": row["quantity"],
                    "needed": bool(row["needed"]),
                    "category": row["category"],
                }
                for row in cur.fetchall()
            ]

            return {
                "family": {"name": family["name"]},
                "categories": categories,
                "items": items,
            }


def _backup_category_name(category):
    if isinstance(category, str):
        name = category
    elif isinstance(category, dict):
        name = category.get("name")
    else:
        name = None

    category_name = str(name or "").strip()

    if not category_name:
        raise ValueError("Le fichier contient une catégorie sans nom.")

    return category_name


def _backup_item_values(item):
    if not isinstance(item, dict):
        raise ValueError("Le fichier contient un item dans un format invalide.")

    item_name = str(item.get("name") or "").strip()
    category_name = str(item.get("category") or "Sans catégorie").strip()

    if not item_name:
        raise ValueError("Le fichier contient un item sans nom.")

    if not category_name:
        category_name = "Sans catégorie"

    try:
        quantity = int(item.get("quantity", 1) or 1)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"La quantité de « {item_name} » est invalide."
        ) from error

    if quantity < 1:
        raise ValueError(
            f"La quantité de « {item_name} » doit être d’au moins 1."
        )

    raw_needed = item.get("needed", False)

    if isinstance(raw_needed, str):
        needed = raw_needed.strip().lower() in {
            "1",
            "true",
            "vrai",
            "yes",
            "oui",
        }
    else:
        needed = bool(raw_needed)

    return item_name, category_name, quantity, needed


def import_family_backup(
    user_id,
    family_id,
    backup_data,
    replace_existing=False,
):
    if not isinstance(backup_data, dict):
        raise ValueError("Le contenu de la sauvegarde est invalide.")

    categories_data = backup_data.get("categories", [])
    items_data = backup_data.get("items", [])

    if not isinstance(categories_data, list):
        raise ValueError("La liste des catégories est invalide.")

    if not isinstance(items_data, list):
        raise ValueError("La liste des items est invalide.")

    category_names = [
        _backup_category_name(category)
        for category in categories_data
    ]
    parsed_items = [_backup_item_values(item) for item in items_data]

    known_category_names = {name.casefold() for name in category_names}

    for _, category_name, _, _ in parsed_items:
        if category_name.casefold() not in known_category_names:
            category_names.append(category_name)
            known_category_names.add(category_name.casefold())

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_family_access(cur, user_id, family_id)

            if replace_existing:
                cur.execute("DELETE FROM items WHERE family_id = %s;", (family_id,))
                cur.execute(
                    "DELETE FROM categories WHERE family_id = %s;",
                    (family_id,),
                )

            cur.execute(
                "SELECT id, name FROM categories WHERE family_id = %s;",
                (family_id,),
            )
            category_ids = {
                row["name"].strip().casefold(): row["id"]
                for row in cur.fetchall()
            }

            categories_created = 0

            for category_name in category_names:
                normalized_name = category_name.casefold()

                if normalized_name in category_ids:
                    continue

                cur.execute(
                    """
                    INSERT INTO categories (family_id, name)
                    VALUES (%s, %s)
                    RETURNING id;
                    """,
                    (family_id, category_name),
                )
                category_ids[normalized_name] = cur.fetchone()["id"]
                categories_created += 1

            existing_items = {}

            if not replace_existing:
                cur.execute(
                    """
                    SELECT id, name, category_id
                    FROM items
                    WHERE family_id = %s
                    ORDER BY id;
                    """,
                    (family_id,),
                )

                for row in cur.fetchall():
                    key = (row["category_id"], row["name"].strip().casefold())
                    existing_items.setdefault(key, row["id"])

            items_created = 0
            items_updated = 0

            for item_name, category_name, quantity, needed in parsed_items:
                category_id = category_ids[category_name.casefold()]
                needed_value = 1 if needed else 0
                item_key = (category_id, item_name.casefold())

                if not replace_existing and item_key in existing_items:
                    cur.execute(
                        """
                        UPDATE items
                        SET name = %s, quantity = %s, needed = %s
                        WHERE id = %s;
                        """,
                        (
                            item_name,
                            quantity,
                            needed_value,
                            existing_items[item_key],
                        ),
                    )
                    items_updated += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO items (
                            family_id,
                            category_id,
                            name,
                            quantity,
                            needed
                        )
                        VALUES (%s, %s, %s, %s, %s);
                        """,
                        (
                            family_id,
                            category_id,
                            item_name,
                            quantity,
                            needed_value,
                        ),
                    )
                    items_created += 1

            conn.commit()

            return {
                "categories_created": categories_created,
                "items_created": items_created,
                "items_updated": items_updated,
                "replaced": bool(replace_existing),
            }
