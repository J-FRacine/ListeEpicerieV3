from __future__ import annotations

from datetime import datetime

from psycopg import sql

import db as _db


TABLES_FOR_SIZE = (
    "families",
    "family_members",
    "users",
    "categories",
    "stores",
    "items",
    "activity_log",
)


def _scope_clause(alias, family_id):
    if family_id is None:
        return sql.SQL("TRUE"), []

    return (
        sql.SQL("{}.family_id = %s").format(
            sql.Identifier(alias)
        ),
        [int(family_id)],
    )


def _count_rows(
    cur,
    table_name,
    family_id=None,
    extra_where="TRUE",
):
    if table_name not in {
        "items",
        "categories",
        "stores",
        "activity_log",
    }:
        raise ValueError("Table de diagnostic invalide.")

    scope, params = _scope_clause(
        "entry",
        family_id,
    )

    query = sql.SQL(
        """
        SELECT COUNT(*) AS total
        FROM {} AS entry
        WHERE {}
          AND {};
        """
    ).format(
        sql.Identifier(table_name),
        scope,
        sql.SQL(extra_where),
    )

    cur.execute(query, params)
    return int(cur.fetchone()["total"])


def _get_global_counts(cur):
    cur.execute(
        """
        SELECT
            COUNT(*) AS users_total,
            COUNT(*) FILTER (
                WHERE is_active
            ) AS users_active,
            COUNT(*) FILTER (
                WHERE NOT is_active
            ) AS users_inactive,
            COUNT(*) FILTER (
                WHERE is_admin
                  AND is_active
            ) AS administrators_active
        FROM users;
        """
    )
    users = dict(cur.fetchone())

    cur.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM families) AS families_total,
            (SELECT COUNT(*) FROM family_members) AS memberships_total;
        """
    )
    structure = dict(cur.fetchone())

    return {
        **users,
        **structure,
    }


def _get_family_options(cur):
    cur.execute(
        """
        SELECT
            family.id,
            family.name,
            COUNT(member.user_id) AS members_total,
            COUNT(member.user_id) FILTER (
                WHERE user_account.is_active
            ) AS active_members,
            COUNT(member.user_id) FILTER (
                WHERE member.role = 'owner'
                  AND user_account.is_active
            ) AS active_owners
        FROM families AS family
        LEFT JOIN family_members AS member
          ON member.family_id = family.id
        LEFT JOIN users AS user_account
          ON user_account.id = member.user_id
        GROUP BY family.id, family.name
        ORDER BY LOWER(family.name), family.name, family.id;
        """
    )
    return cur.fetchall()


def _get_scope_counts(cur, family_id):
    return {
        "items_active": _count_rows(
            cur,
            "items",
            family_id,
            "entry.deleted_at IS NULL",
        ),
        "items_needed": _count_rows(
            cur,
            "items",
            family_id,
            (
                "entry.deleted_at IS NULL "
                "AND entry.needed = 1"
            ),
        ),
        "items_deleted": _count_rows(
            cur,
            "items",
            family_id,
            "entry.deleted_at IS NOT NULL",
        ),
        "categories_active": _count_rows(
            cur,
            "categories",
            family_id,
            "entry.deleted_at IS NULL",
        ),
        "categories_deleted": _count_rows(
            cur,
            "categories",
            family_id,
            "entry.deleted_at IS NOT NULL",
        ),
        "stores_active": _count_rows(
            cur,
            "stores",
            family_id,
            "entry.deleted_at IS NULL",
        ),
        "stores_deleted": _count_rows(
            cur,
            "stores",
            family_id,
            "entry.deleted_at IS NOT NULL",
        ),
        "activity_entries": _count_rows(
            cur,
            "activity_log",
            family_id,
        ),
    }


def _get_invalid_items(cur, family_id):
    scope, params = _scope_clause(
        "item",
        family_id,
    )

    cur.execute(
        sql.SQL(
            """
            SELECT
                item.id,
                family.id AS family_id,
                family.name AS family_name,
                item.name,
                item.quantity,
                item.needed,
                item.category_id,
                item.store_id,
                category.name AS category_name,
                category.family_id AS category_family_id,
                category.deleted_at AS category_deleted_at,
                store.name AS store_name,
                store.family_id AS store_family_id,
                store.deleted_at AS store_deleted_at,
                (category.id IS NULL) AS category_missing,
                (
                    category.id IS NOT NULL
                    AND category.family_id <> item.family_id
                ) AS category_wrong_family,
                (
                    category.id IS NOT NULL
                    AND category.deleted_at IS NOT NULL
                ) AS category_deleted,
                (item.store_id IS NULL) AS store_not_assigned,
                (
                    item.store_id IS NOT NULL
                    AND store.id IS NULL
                ) AS store_missing,
                (
                    store.id IS NOT NULL
                    AND store.family_id <> item.family_id
                ) AS store_wrong_family,
                (
                    store.id IS NOT NULL
                    AND store.deleted_at IS NOT NULL
                ) AS store_deleted,
                (BTRIM(COALESCE(item.name, '')) = '') AS blank_name,
                (item.quantity < 1) AS invalid_quantity,
                (item.needed NOT IN (0, 1)) AS invalid_needed
            FROM items AS item
            JOIN families AS family
              ON family.id = item.family_id
            LEFT JOIN categories AS category
              ON category.id = item.category_id
            LEFT JOIN stores AS store
              ON store.id = item.store_id
            WHERE item.deleted_at IS NULL
              AND {}
              AND (
                    category.id IS NULL
                 OR category.family_id <> item.family_id
                 OR category.deleted_at IS NOT NULL
                 OR item.store_id IS NULL
                 OR store.id IS NULL
                 OR store.family_id <> item.family_id
                 OR store.deleted_at IS NOT NULL
                 OR BTRIM(COALESCE(item.name, '')) = ''
                 OR item.quantity < 1
                 OR item.needed NOT IN (0, 1)
              )
            ORDER BY
                LOWER(family.name),
                LOWER(COALESCE(item.name, '')),
                item.id;
            """
        ).format(scope),
        params,
    )

    rows = []
    for row in cur.fetchall():
        issue_labels = []

        checks = (
            ("category_missing", "catégorie introuvable"),
            (
                "category_wrong_family",
                "catégorie liée à une autre famille",
            ),
            (
                "category_deleted",
                "catégorie placée dans la corbeille",
            ),
            (
                "store_not_assigned",
                "aucun magasin attribué",
            ),
            ("store_missing", "magasin introuvable"),
            (
                "store_wrong_family",
                "magasin lié à une autre famille",
            ),
            (
                "store_deleted",
                "magasin placé dans la corbeille",
            ),
            ("blank_name", "nom vide"),
            (
                "invalid_quantity",
                "quantité inférieure à 1",
            ),
            (
                "invalid_needed",
                "statut de besoin invalide",
            ),
        )

        for key, label in checks:
            if row[key]:
                issue_labels.append(label)

        data = dict(row)
        data["issues"] = issue_labels
        rows.append(data)

    return rows


def _get_duplicate_items(cur, family_id):
    scope, params = _scope_clause(
        "item",
        family_id,
    )

    cur.execute(
        sql.SQL(
            """
            SELECT
                family.name AS family_name,
                COALESCE(store.name, 'Sans magasin') AS store_name,
                category.name AS category_name,
                LOWER(BTRIM(item.name)) AS normalized_name,
                COUNT(*) AS item_count,
                STRING_AGG(
                    item.name || ' (#' || item.id::TEXT || ')',
                    ', '
                    ORDER BY item.id
                ) AS entries
            FROM items AS item
            JOIN families AS family
              ON family.id = item.family_id
            JOIN categories AS category
              ON category.id = item.category_id
            LEFT JOIN stores AS store
              ON store.id = item.store_id
            WHERE item.deleted_at IS NULL
              AND category.deleted_at IS NULL
              AND (
                    store.id IS NULL
                    OR store.deleted_at IS NULL
              )
              AND {}
            GROUP BY
                family.name,
                item.family_id,
                item.category_id,
                item.store_id,
                store.name,
                category.name,
                LOWER(BTRIM(item.name))
            HAVING COUNT(*) > 1
            ORDER BY
                COUNT(*) DESC,
                LOWER(family.name),
                LOWER(COALESCE(store.name, '')),
                LOWER(category.name),
                LOWER(BTRIM(item.name));
            """
        ).format(scope),
        params,
    )
    exact = cur.fetchall()

    cur.execute(
        sql.SQL(
            """
            WITH candidate AS (
                SELECT
                    item.id,
                    item.family_id,
                    item.category_id,
                    item.store_id,
                    item.name,
                    LOWER(BTRIM(item.name)) AS normalized_name,
                    REGEXP_REPLACE(
                        LOWER(BTRIM(item.name)),
                        '[^[:alnum:]]+',
                        '',
                        'g'
                    ) AS compact_name
                FROM items AS item
                WHERE item.deleted_at IS NULL
                  AND {}
            )
            SELECT
                family.name AS family_name,
                COALESCE(store.name, 'Sans magasin') AS store_name,
                category.name AS category_name,
                candidate.compact_name,
                COUNT(*) AS item_count,
                STRING_AGG(
                    candidate.name || ' (#' || candidate.id::TEXT || ')',
                    ', '
                    ORDER BY candidate.id
                ) AS entries
            FROM candidate
            JOIN families AS family
              ON family.id = candidate.family_id
            JOIN categories AS category
              ON category.id = candidate.category_id
             AND category.deleted_at IS NULL
            LEFT JOIN stores AS store
              ON store.id = candidate.store_id
            WHERE candidate.compact_name <> ''
              AND (
                    store.id IS NULL
                    OR store.deleted_at IS NULL
              )
            GROUP BY
                family.name,
                candidate.family_id,
                candidate.category_id,
                candidate.store_id,
                store.name,
                category.name,
                candidate.compact_name
            HAVING COUNT(*) > 1
               AND COUNT(
                    DISTINCT candidate.normalized_name
               ) > 1
            ORDER BY
                COUNT(*) DESC,
                LOWER(family.name),
                LOWER(COALESCE(store.name, '')),
                LOWER(category.name),
                candidate.compact_name;
            """
        ).format(scope),
        params,
    )
    probable = cur.fetchall()

    cur.execute(
        sql.SQL(
            """
            SELECT
                family.name AS family_name,
                LOWER(BTRIM(item.name)) AS normalized_name,
                COUNT(*) AS item_count,
                COUNT(
                    DISTINCT ROW(
                        item.category_id,
                        item.store_id
                    )
                ) AS location_count,
                STRING_AGG(
                    DISTINCT (
                        COALESCE(store.name, 'Sans magasin')
                        || ' · '
                        || category.name
                    ),
                    ', '
                ) AS locations
            FROM items AS item
            JOIN families AS family
              ON family.id = item.family_id
            JOIN categories AS category
              ON category.id = item.category_id
             AND category.deleted_at IS NULL
            LEFT JOIN stores AS store
              ON store.id = item.store_id
            WHERE item.deleted_at IS NULL
              AND (
                    store.id IS NULL
                    OR store.deleted_at IS NULL
              )
              AND {}
            GROUP BY
                family.name,
                item.family_id,
                LOWER(BTRIM(item.name))
            HAVING COUNT(*) > 1
               AND COUNT(
                    DISTINCT ROW(
                        item.category_id,
                        item.store_id
                    )
               ) > 1
            ORDER BY
                COUNT(*) DESC,
                LOWER(family.name),
                LOWER(BTRIM(item.name));
            """
        ).format(scope),
        params,
    )
    cross_location = cur.fetchall()

    return {
        "exact": exact,
        "probable": probable,
        "cross_location": cross_location,
    }


def _get_unused_entries(cur, family_id):
    category_scope, category_params = _scope_clause(
        "category",
        family_id,
    )

    cur.execute(
        sql.SQL(
            """
            SELECT
                category.id,
                family.name AS family_name,
                category.name,
                category.sort_order
            FROM categories AS category
            JOIN families AS family
              ON family.id = category.family_id
            WHERE category.deleted_at IS NULL
              AND {}
              AND NOT EXISTS (
                    SELECT 1
                    FROM items AS item
                    WHERE item.category_id = category.id
                      AND item.deleted_at IS NULL
              )
            ORDER BY
                LOWER(family.name),
                category.sort_order,
                LOWER(category.name),
                category.id;
            """
        ).format(category_scope),
        category_params,
    )
    categories = cur.fetchall()

    store_scope, store_params = _scope_clause(
        "store",
        family_id,
    )

    cur.execute(
        sql.SQL(
            """
            SELECT
                store.id,
                family.name AS family_name,
                store.name,
                store.sort_order
            FROM stores AS store
            JOIN families AS family
              ON family.id = store.family_id
            WHERE store.deleted_at IS NULL
              AND {}
              AND NOT EXISTS (
                    SELECT 1
                    FROM items AS item
                    WHERE item.store_id = store.id
                      AND item.deleted_at IS NULL
              )
            ORDER BY
                LOWER(family.name),
                store.sort_order,
                LOWER(store.name),
                store.id;
            """
        ).format(store_scope),
        store_params,
    )
    stores = cur.fetchall()

    return {
        "categories": categories,
        "stores": stores,
    }


def _get_naming_issues(cur, family_id):
    results = []

    for table_name, entity_label in (
        ("items", "Item"),
        ("categories", "Catégorie"),
        ("stores", "Magasin"),
    ):
        scope, params = _scope_clause(
            "entry",
            family_id,
        )

        cur.execute(
            sql.SQL(
                """
                SELECT
                    entry.id,
                    family.name AS family_name,
                    entry.name,
                    %s AS entity_type,
                    (entry.name <> BTRIM(entry.name)) AS outer_spaces,
                    (entry.name ~ '[[:space:]]{2,}') AS repeated_spaces,
                    (BTRIM(COALESCE(entry.name, '')) = '') AS blank_name
                FROM {} AS entry
                JOIN families AS family
                  ON family.id = entry.family_id
                WHERE entry.deleted_at IS NULL
                  AND {}
                  AND (
                        entry.name <> BTRIM(entry.name)
                     OR entry.name ~ '[[:space:]]{2,}'
                     OR BTRIM(COALESCE(entry.name, '')) = ''
                  )
                ORDER BY
                    LOWER(family.name),
                    LOWER(COALESCE(entry.name, '')),
                    entry.id;
                """
            ).format(
                sql.Identifier(table_name),
                scope,
            ),
            [entity_label, *params],
        )

        for row in cur.fetchall():
            issues = []
            if row["outer_spaces"]:
                issues.append(
                    "espaces au début ou à la fin"
                )
            if row["repeated_spaces"]:
                issues.append(
                    "espaces répétés"
                )
            if row["blank_name"]:
                issues.append("nom vide")

            data = dict(row)
            data["issues"] = issues
            results.append(data)

    return results


def _get_duplicate_reference_names(cur, family_id):
    results = {}

    for table_name, key in (
        ("categories", "categories"),
        ("stores", "stores"),
    ):
        scope, params = _scope_clause(
            "entry",
            family_id,
        )

        cur.execute(
            sql.SQL(
                """
                SELECT
                    family.name AS family_name,
                    LOWER(BTRIM(entry.name)) AS normalized_name,
                    COUNT(*) AS entry_count,
                    STRING_AGG(
                        entry.name || ' (#' || entry.id::TEXT || ')',
                        ', '
                        ORDER BY entry.id
                    ) AS entries
                FROM {} AS entry
                JOIN families AS family
                  ON family.id = entry.family_id
                WHERE entry.deleted_at IS NULL
                  AND {}
                GROUP BY
                    family.name,
                    entry.family_id,
                    LOWER(BTRIM(entry.name))
                HAVING COUNT(*) > 1
                ORDER BY
                    COUNT(*) DESC,
                    LOWER(family.name),
                    LOWER(BTRIM(entry.name));
                """
            ).format(
                sql.Identifier(table_name),
                scope,
            ),
            params,
        )
        results[key] = cur.fetchall()

    return results


def _get_expired_trash(cur, family_id):
    results = []

    for table_name, entity_label in (
        ("items", "Item"),
        ("categories", "Catégorie"),
        ("stores", "Magasin"),
    ):
        scope, params = _scope_clause(
            "entry",
            family_id,
        )

        cur.execute(
            sql.SQL(
                """
                SELECT
                    entry.id,
                    family.name AS family_name,
                    entry.name,
                    entry.deleted_at,
                    %s AS entity_type
                FROM {} AS entry
                JOIN families AS family
                  ON family.id = entry.family_id
                WHERE entry.deleted_at IS NOT NULL
                  AND entry.deleted_at
                      < NOW() - INTERVAL '30 days'
                  AND {}
                ORDER BY
                    entry.deleted_at,
                    LOWER(family.name),
                    LOWER(entry.name),
                    entry.id;
                """
            ).format(
                sql.Identifier(table_name),
                scope,
            ),
            [entity_label, *params],
        )
        results.extend(cur.fetchall())

    return results


def _get_family_access_issues(cur, family_id):
    params = []
    family_condition = sql.SQL("TRUE")

    if family_id is not None:
        family_condition = sql.SQL(
            "family.id = %s"
        )
        params.append(int(family_id))

    cur.execute(
        sql.SQL(
            """
            SELECT
                family.id,
                family.name,
                COUNT(member.user_id) AS members_total,
                COUNT(member.user_id) FILTER (
                    WHERE user_account.is_active
                ) AS active_members,
                COUNT(member.user_id) FILTER (
                    WHERE member.role = 'owner'
                      AND user_account.is_active
                ) AS active_owners,
                COUNT(member.user_id) FILTER (
                    WHERE NOT user_account.is_active
                ) AS inactive_members
            FROM families AS family
            LEFT JOIN family_members AS member
              ON member.family_id = family.id
            LEFT JOIN users AS user_account
              ON user_account.id = member.user_id
            WHERE {}
            GROUP BY family.id, family.name
            HAVING
                   COUNT(member.user_id) FILTER (
                       WHERE user_account.is_active
                   ) = 0
                OR COUNT(member.user_id) FILTER (
                       WHERE member.role = 'owner'
                         AND user_account.is_active
                   ) = 0
                OR COUNT(member.user_id) FILTER (
                       WHERE NOT user_account.is_active
                   ) > 0
            ORDER BY LOWER(family.name), family.name, family.id;
            """
        ).format(family_condition),
        params,
    )

    rows = []
    for row in cur.fetchall():
        issues = []

        if row["active_members"] == 0:
            issues.append(
                "aucun membre actif"
            )
        if row["active_owners"] == 0:
            issues.append(
                "aucun propriétaire actif"
            )
        if row["inactive_members"] > 0:
            issues.append(
                f"{row['inactive_members']} accès attribué(s) "
                "à un compte inactif"
            )

        data = dict(row)
        data["issues"] = issues
        rows.append(data)

    return rows


def _get_database_sizes(cur):
    cur.execute(
        """
        SELECT pg_database_size(
            current_database()
        ) AS database_bytes;
        """
    )
    database_bytes = int(
        cur.fetchone()["database_bytes"] or 0
    )

    table_sizes = []
    for table_name in TABLES_FOR_SIZE:
        cur.execute(
            """
            SELECT COALESCE(
                pg_total_relation_size(
                    to_regclass(%s)
                ),
                0
            ) AS total_bytes;
            """,
            (f"public.{table_name}",),
        )
        table_sizes.append(
            {
                "table_name": table_name,
                "total_bytes": int(
                    cur.fetchone()["total_bytes"]
                    or 0
                ),
            }
        )

    table_sizes.sort(
        key=lambda entry: entry["total_bytes"],
        reverse=True,
    )

    return {
        "database_bytes": database_bytes,
        "tables": table_sizes,
    }


def get_maintenance_families(actor_user_id):
    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_global_admin(
                cur,
                actor_user_id,
            )
            return _get_family_options(cur)


def get_maintenance_report(
    actor_user_id,
    family_id=None,
):
    selected_family_id = (
        int(family_id)
        if family_id is not None
        else None
    )

    with _db.get_connection() as conn:
        with conn.cursor() as cur:
            _db._require_global_admin(
                cur,
                actor_user_id,
            )

            family_options = _get_family_options(cur)
            valid_ids = {
                row["id"]
                for row in family_options
            }

            if (
                selected_family_id is not None
                and selected_family_id not in valid_ids
            ):
                raise ValueError(
                    "La famille sélectionnée n’existe plus."
                )

            global_counts = _get_global_counts(cur)
            scope_counts = _get_scope_counts(
                cur,
                selected_family_id,
            )
            invalid_items = _get_invalid_items(
                cur,
                selected_family_id,
            )
            duplicate_items = _get_duplicate_items(
                cur,
                selected_family_id,
            )
            unused_entries = _get_unused_entries(
                cur,
                selected_family_id,
            )
            naming_issues = _get_naming_issues(
                cur,
                selected_family_id,
            )
            duplicate_reference_names = (
                _get_duplicate_reference_names(
                    cur,
                    selected_family_id,
                )
            )
            expired_trash = _get_expired_trash(
                cur,
                selected_family_id,
            )
            family_access_issues = (
                _get_family_access_issues(
                    cur,
                    selected_family_id,
                )
            )
            database_sizes = _get_database_sizes(cur)

    critical_count = (
        len(invalid_items)
        + len(
            duplicate_reference_names[
                "categories"
            ]
        )
        + len(
            duplicate_reference_names[
                "stores"
            ]
        )
        + sum(
            1
            for family in family_access_issues
            if family["active_members"] == 0
        )
    )

    warning_count = (
        len(duplicate_items["exact"])
        + len(duplicate_items["probable"])
        + len(unused_entries["categories"])
        + len(unused_entries["stores"])
        + len(naming_issues)
        + len(expired_trash)
        + len(family_access_issues)
    )

    selected_family_name = None
    if selected_family_id is not None:
        selected_family_name = next(
            (
                row["name"]
                for row in family_options
                if row["id"]
                == selected_family_id
            ),
            None,
        )

    return {
        "generated_at": datetime.now().astimezone(),
        "selected_family_id": selected_family_id,
        "selected_family_name": selected_family_name,
        "family_options": family_options,
        "global_counts": global_counts,
        "scope_counts": scope_counts,
        "invalid_items": invalid_items,
        "duplicate_items": duplicate_items,
        "unused_entries": unused_entries,
        "naming_issues": naming_issues,
        "duplicate_reference_names": (
            duplicate_reference_names
        ),
        "expired_trash": expired_trash,
        "family_access_issues": (
            family_access_issues
        ),
        "database_sizes": database_sizes,
        "critical_count": critical_count,
        "warning_count": warning_count,
    }
