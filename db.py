import os

import psycopg
from psycopg import sql
from psycopg.rows import dict_row


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
# INITIALISATION ET MIGRATION
# ---------------------------------------------------------

def _categories_have_family_id(cur):
    cur.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'categories'
              AND column_name = 'family_id'
        ) AS exists;
    """)
    return cur.fetchone()["exists"]


def _add_categories_family_column(cur):
    if not _categories_have_family_id(cur):
        cur.execute("""
            ALTER TABLE categories
            ADD COLUMN family_id INTEGER;
        """)

    cur.execute("""
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
    """)


def _drop_legacy_category_name_uniqueness(cur):
    """Retire l'ancienne unicité globale sur categories.name.

    L'ancien modèle interdisait deux catégories portant le même nom.
    Le nouveau modèle doit permettre, par exemple, une catégorie
    « Épicerie » dans chacune des familles.
    """

    # Cas normal de l'ancien schéma: name TEXT UNIQUE.
    cur.execute("""
        ALTER TABLE categories
        DROP CONSTRAINT IF EXISTS categories_name_key;
    """)

    # Protection supplémentaire: retire toute autre contrainte UNIQUE
    # portant uniquement sur la colonne name.
    cur.execute("""
        SELECT
            table_constraint.constraint_name
        FROM information_schema.table_constraints AS table_constraint
        JOIN information_schema.constraint_column_usage AS column_usage
          ON column_usage.constraint_schema =
             table_constraint.constraint_schema
         AND column_usage.constraint_name =
             table_constraint.constraint_name
         AND column_usage.table_schema =
             table_constraint.table_schema
         AND column_usage.table_name =
             table_constraint.table_name
        WHERE table_constraint.table_schema = 'public'
          AND table_constraint.table_name = 'categories'
          AND table_constraint.constraint_type = 'UNIQUE'
        GROUP BY table_constraint.constraint_name
        HAVING COUNT(*) = 1
           AND MIN(column_usage.column_name) = 'name';
    """)

    for row in cur.fetchall():
        cur.execute(
            sql.SQL("""
                ALTER TABLE categories
                DROP CONSTRAINT IF EXISTS {};
            """).format(
                sql.Identifier(row["constraint_name"])
            )
        )

    # Protection supplémentaire contre un ancien index unique créé
    # directement, sans contrainte SQL.
    cur.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = 'categories'
          AND indexdef ILIKE 'CREATE UNIQUE INDEX%%'
          AND indexdef ILIKE '%%name%%'
          AND indexdef NOT ILIKE '%%family_id%%';
    """)

    for row in cur.fetchall():
        cur.execute(
            sql.SQL("DROP INDEX IF EXISTS public.{};").format(
                sql.Identifier(row["indexname"])
            )
        )


def _remove_duplicate_family_categories(cur):
    """Fusionne d’éventuels doublons locaux avant l’index unique."""

    cur.execute("""
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
    """)

    cur.execute("""
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
    """)


def _copy_legacy_categories_to_all_families(cur):
    """Copie toutes les anciennes catégories dans toutes les familles."""

    cur.execute("""
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
            ORDER BY
                normalized_name,
                id
        )
        INSERT INTO categories (family_id, name)
        SELECT
            family.id,
            legacy_category.category_name
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
    """)


def _ensure_local_category_for_each_item(cur):
    """Crée au besoin une catégorie locale correspondant à chaque item."""

    cur.execute("""
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
        SELECT
            item_category.family_id,
            item_category.category_name
        FROM item_category_names AS item_category
        WHERE NOT EXISTS (
            SELECT 1
            FROM categories AS existing_category
            WHERE existing_category.family_id =
                  item_category.family_id
              AND LOWER(
                    COALESCE(
                        NULLIF(BTRIM(existing_category.name), ''),
                        'Sans catégorie'
                    )
                  ) = item_category.normalized_name
        );
    """)


def _move_items_to_their_family_categories(cur):
    """Relie chaque item à la catégorie de sa propre famille."""

    cur.execute("""
        UPDATE items AS item
        SET category_id = local_category.id
        FROM
            categories AS current_category,
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
          AND current_category.family_id
              IS DISTINCT FROM item.family_id;
    """)


def _migrate_categories_to_families(cur):
    """Migration des catégories globales vers des catégories familiales."""

    _add_categories_family_column(cur)

    # IMPORTANT: cette étape doit arriver avant la création des copies.
    # Elle corrige précisément l'erreur categories_name_key.
    _drop_legacy_category_name_uniqueness(cur)

    _remove_duplicate_family_categories(cur)

    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
            categories_family_name_unique
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
    """)

    _copy_legacy_categories_to_all_families(cur)
    _ensure_local_category_for_each_item(cur)
    _move_items_to_their_family_categories(cur)


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS families (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    family_id INTEGER
                        REFERENCES families(id)
                        ON DELETE CASCADE,
                    name TEXT NOT NULL
                );
            """)

            cur.execute("""
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
            """)

            _migrate_categories_to_families(cur)
            conn.commit()


# ---------------------------------------------------------
# FAMILLES
# ---------------------------------------------------------

def get_families():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name
                FROM families
                ORDER BY LOWER(name), name;
            """)
            return cur.fetchall()


def create_family(name):
    family_name = (name or "").strip()

    if not family_name:
        raise ValueError("Le nom de la famille est obligatoire.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO families (name)
                VALUES (%s)
                RETURNING id;
            """, (family_name,))
            family_id = cur.fetchone()["id"]

            # Une nouvelle famille reçoit aussi les catégories
            # provenant de l'ancien modèle global.
            cur.execute("""
                INSERT INTO categories (family_id, name)
                SELECT
                    %s,
                    legacy_category.name
                FROM categories AS legacy_category
                WHERE legacy_category.family_id IS NULL
                ON CONFLICT DO NOTHING;
            """, (family_id,))

            conn.commit()
            return family_id


def delete_family(family_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM items WHERE family_id = %s;",
                (family_id,),
            )
            cur.execute(
                "DELETE FROM families WHERE id = %s;",
                (family_id,),
            )
            conn.commit()


# ---------------------------------------------------------
# CATÉGORIES PROPRES À UNE FAMILLE
# ---------------------------------------------------------

def get_categories(family_id):
    if family_id is None:
        return []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name
                FROM categories
                WHERE family_id = %s
                ORDER BY LOWER(name), name;
            """, (family_id,))
            return cur.fetchall()


def get_categories_with_counts(family_id):
    if family_id is None:
        return []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
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
            """, (family_id, family_id))
            return cur.fetchall()


def _category_name_exists(
    cur,
    family_id,
    name,
    exclude_category_id=None,
):
    if exclude_category_id is None:
        cur.execute("""
            SELECT 1
            FROM categories
            WHERE family_id = %s
              AND LOWER(BTRIM(name)) = LOWER(BTRIM(%s))
            LIMIT 1;
        """, (family_id, name))
    else:
        cur.execute("""
            SELECT 1
            FROM categories
            WHERE family_id = %s
              AND LOWER(BTRIM(name)) = LOWER(BTRIM(%s))
              AND id <> %s
            LIMIT 1;
        """, (
            family_id,
            name,
            exclude_category_id,
        ))

    return cur.fetchone() is not None


def create_category(family_id, name):
    category_name = (name or "").strip()

    if family_id is None:
        raise ValueError("Aucune famille n’est sélectionnée.")

    if not category_name:
        raise ValueError("Le nom de la catégorie est obligatoire.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            if _category_name_exists(
                cur,
                family_id,
                category_name,
            ):
                raise ValueError(
                    f"La catégorie « {category_name} » existe déjà "
                    "dans cette famille."
                )

            cur.execute("""
                INSERT INTO categories (family_id, name)
                VALUES (%s, %s)
                RETURNING id;
            """, (
                family_id,
                category_name,
            ))
            category_id = cur.fetchone()["id"]
            conn.commit()
            return category_id


def rename_category(
    family_id,
    category_id,
    new_name,
):
    category_name = (new_name or "").strip()

    if not category_name:
        raise ValueError("Le nom de la catégorie est obligatoire.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            if _category_name_exists(
                cur,
                family_id,
                category_name,
                exclude_category_id=category_id,
            ):
                raise ValueError(
                    f"La catégorie « {category_name} » existe déjà "
                    "dans cette famille."
                )

            cur.execute("""
                UPDATE categories
                SET name = %s
                WHERE id = %s
                  AND family_id = %s;
            """, (
                category_name,
                category_id,
                family_id,
            ))

            if cur.rowcount == 0:
                raise ValueError(
                    "Cette catégorie n’existe pas "
                    "dans la famille active."
                )

            conn.commit()


def merge_categories(
    family_id,
    source_category_id,
    destination_category_id,
):
    if source_category_id == destination_category_id:
        raise ValueError(
            "La catégorie de destination doit être différente."
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id
                FROM categories
                WHERE family_id = %s
                  AND id IN (%s, %s);
            """, (
                family_id,
                source_category_id,
                destination_category_id,
            ))
            found_categories = cur.fetchall()

            if len(found_categories) != 2:
                raise ValueError(
                    "Les deux catégories doivent appartenir "
                    "à la famille active."
                )

            cur.execute("""
                UPDATE items
                SET category_id = %s
                WHERE family_id = %s
                  AND category_id = %s;
            """, (
                destination_category_id,
                family_id,
                source_category_id,
            ))
            moved_item_count = cur.rowcount

            cur.execute("""
                DELETE FROM categories
                WHERE id = %s
                  AND family_id = %s;
            """, (
                source_category_id,
                family_id,
            ))

            conn.commit()
            return moved_item_count


def delete_category(family_id, category_id):
    """Supprime une catégorie vide sans effacer ses items."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)::INTEGER AS item_count
                FROM items
                WHERE family_id = %s
                  AND category_id = %s;
            """, (
                family_id,
                category_id,
            ))
            item_count = cur.fetchone()["item_count"]

            if item_count > 0:
                raise ValueError(
                    "Cette catégorie contient encore "
                    f"{item_count} item(s). Fusionnez-la d’abord."
                )

            cur.execute("""
                DELETE FROM categories
                WHERE id = %s
                  AND family_id = %s;
            """, (
                category_id,
                family_id,
            ))

            if cur.rowcount == 0:
                raise ValueError(
                    "Cette catégorie n’existe pas "
                    "dans la famille active."
                )

            conn.commit()


# ---------------------------------------------------------
# ITEMS
# ---------------------------------------------------------

def get_items(family_id):
    if family_id is None:
        return []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
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
            """, (family_id,))
            return cur.fetchall()


def _category_belongs_to_family(
    cur,
    family_id,
    category_id,
):
    cur.execute("""
        SELECT 1
        FROM categories
        WHERE id = %s
          AND family_id = %s
        LIMIT 1;
    """, (
        category_id,
        family_id,
    ))
    return cur.fetchone() is not None


def add_item(
    family_id,
    category_id,
    name,
    quantity,
    needed,
):
    item_name = (name or "").strip()
    item_quantity = int(quantity or 1)
    item_needed = 1 if needed else 0

    if family_id is None:
        raise ValueError("Aucune famille n’est sélectionnée.")

    if not item_name:
        raise ValueError("Le nom de l’item est obligatoire.")

    if item_quantity < 1:
        raise ValueError("La quantité doit être d’au moins 1.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            if not _category_belongs_to_family(
                cur,
                family_id,
                category_id,
            ):
                raise ValueError(
                    "La catégorie choisie n’appartient pas "
                    "à la famille active."
                )

            cur.execute("""
                INSERT INTO items (
                    family_id,
                    category_id,
                    name,
                    quantity,
                    needed
                )
                VALUES (%s, %s, %s, %s, %s);
            """, (
                family_id,
                category_id,
                item_name,
                item_quantity,
                item_needed,
            ))
            conn.commit()


def update_item(
    item_id,
    category_id,
    name,
    quantity,
    needed,
):
    item_name = (name or "").strip()
    item_quantity = int(quantity or 1)
    item_needed = 1 if needed else 0

    if not item_name:
        raise ValueError("Le nom de l’item est obligatoire.")

    if item_quantity < 1:
        raise ValueError("La quantité doit être d’au moins 1.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT family_id
                FROM items
                WHERE id = %s;
            """, (item_id,))
            item = cur.fetchone()

            if item is None:
                raise ValueError("Cet item n’existe plus.")

            family_id = item["family_id"]

            if not _category_belongs_to_family(
                cur,
                family_id,
                category_id,
            ):
                raise ValueError(
                    "La catégorie choisie n’appartient pas "
                    "à la famille de cet item."
                )

            cur.execute("""
                UPDATE items
                SET
                    category_id = %s,
                    name = %s,
                    quantity = %s,
                    needed = %s
                WHERE id = %s;
            """, (
                category_id,
                item_name,
                item_quantity,
                item_needed,
                item_id,
            ))
            conn.commit()


def toggle_needed(item_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT needed FROM items WHERE id = %s;",
                (item_id,),
            )
            row = cur.fetchone()

            if row is None:
                return

            new_value = 0 if row["needed"] == 1 else 1

            cur.execute(
                "UPDATE items SET needed = %s WHERE id = %s;",
                (
                    new_value,
                    item_id,
                ),
            )
            conn.commit()


def delete_item(item_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM items WHERE id = %s;",
                (item_id,),
            )
            conn.commit()


# ---------------------------------------------------------
# IMPORTATION ET EXPORTATION D'UNE FAMILLE
# ---------------------------------------------------------

def export_family_backup(family_id):
    """Retourne toutes les données d'épicerie de la famille active."""

    if family_id is None:
        raise ValueError("Aucune famille n’est sélectionnée.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name
                FROM families
                WHERE id = %s;
            """, (family_id,))
            family = cur.fetchone()

            if family is None:
                raise ValueError("Cette famille n’existe plus.")

            cur.execute("""
                SELECT name
                FROM categories
                WHERE family_id = %s
                ORDER BY LOWER(name), name;
            """, (family_id,))
            categories = [
                {"name": row["name"]}
                for row in cur.fetchall()
            ]

            cur.execute("""
                SELECT
                    item.name,
                    item.quantity,
                    item.needed,
                    category.name AS category
                FROM items AS item
                JOIN categories AS category
                  ON category.id = item.category_id
                WHERE item.family_id = %s
                ORDER BY
                    LOWER(category.name),
                    LOWER(item.name),
                    item.id;
            """, (family_id,))
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
                "family": {
                    "name": family["name"],
                },
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
        raise ValueError(
            "Le fichier contient une catégorie sans nom."
        )

    return category_name


def _backup_item_values(item):
    if not isinstance(item, dict):
        raise ValueError(
            "Le fichier contient un item dans un format invalide."
        )

    item_name = str(item.get("name") or "").strip()
    category_name = str(
        item.get("category") or "Sans catégorie"
    ).strip()

    if not item_name:
        raise ValueError(
            "Le fichier contient un item sans nom."
        )

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
            f"La quantité de « {item_name} » doit être "
            "d’au moins 1."
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
    family_id,
    backup_data,
    replace_existing=False,
):
    """Importe une sauvegarde dans la famille active.

    En mode fusion, un item portant le même nom dans la même catégorie
    est mis à jour plutôt que dupliqué.

    En mode remplacement, les catégories et items de la famille active
    sont supprimés, puis recréés à partir du fichier.
    """

    if family_id is None:
        raise ValueError("Aucune famille n’est sélectionnée.")

    if not isinstance(backup_data, dict):
        raise ValueError(
            "Le contenu de la sauvegarde est invalide."
        )

    categories_data = backup_data.get("categories", [])
    items_data = backup_data.get("items", [])

    if not isinstance(categories_data, list):
        raise ValueError(
            "La liste des catégories est invalide."
        )

    if not isinstance(items_data, list):
        raise ValueError(
            "La liste des items est invalide."
        )

    category_names = [
        _backup_category_name(category)
        for category in categories_data
    ]

    parsed_items = [
        _backup_item_values(item)
        for item in items_data
    ]

    # Une catégorie mentionnée par un item doit être importée,
    # même si elle manque par erreur dans la section categories.
    for _, category_name, _, _ in parsed_items:
        if category_name.casefold() not in {
            name.casefold()
            for name in category_names
        }:
            category_names.append(category_name)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id
                FROM families
                WHERE id = %s;
            """, (family_id,))

            if cur.fetchone() is None:
                raise ValueError("Cette famille n’existe plus.")

            if replace_existing:
                cur.execute(
                    "DELETE FROM items WHERE family_id = %s;",
                    (family_id,),
                )
                cur.execute(
                    "DELETE FROM categories WHERE family_id = %s;",
                    (family_id,),
                )

            cur.execute("""
                SELECT id, name
                FROM categories
                WHERE family_id = %s;
            """, (family_id,))

            category_ids = {
                row["name"].strip().casefold(): row["id"]
                for row in cur.fetchall()
            }

            categories_created = 0

            for category_name in category_names:
                normalized_name = category_name.casefold()

                if normalized_name in category_ids:
                    continue

                cur.execute("""
                    INSERT INTO categories (family_id, name)
                    VALUES (%s, %s)
                    RETURNING id;
                """, (
                    family_id,
                    category_name,
                ))
                category_ids[normalized_name] = (
                    cur.fetchone()["id"]
                )
                categories_created += 1

            existing_items = {}

            if not replace_existing:
                cur.execute("""
                    SELECT
                        item.id,
                        item.name,
                        item.category_id
                    FROM items AS item
                    WHERE item.family_id = %s
                    ORDER BY item.id;
                """, (family_id,))

                for row in cur.fetchall():
                    key = (
                        row["category_id"],
                        row["name"].strip().casefold(),
                    )
                    existing_items.setdefault(key, row["id"])

            items_created = 0
            items_updated = 0

            for (
                item_name,
                category_name,
                quantity,
                needed,
            ) in parsed_items:
                category_id = category_ids[
                    category_name.casefold()
                ]
                needed_value = 1 if needed else 0
                item_key = (
                    category_id,
                    item_name.casefold(),
                )

                if (
                    not replace_existing
                    and item_key in existing_items
                ):
                    cur.execute("""
                        UPDATE items
                        SET
                            name = %s,
                            quantity = %s,
                            needed = %s
                        WHERE id = %s;
                    """, (
                        item_name,
                        quantity,
                        needed_value,
                        existing_items[item_key],
                    ))
                    items_updated += 1
                else:
                    cur.execute("""
                        INSERT INTO items (
                            family_id,
                            category_id,
                            name,
                            quantity,
                            needed
                        )
                        VALUES (%s, %s, %s, %s, %s);
                    """, (
                        family_id,
                        category_id,
                        item_name,
                        quantity,
                        needed_value,
                    ))
                    items_created += 1

            conn.commit()

            return {
                "categories_created": categories_created,
                "items_created": items_created,
                "items_updated": items_updated,
                "replaced": bool(replace_existing),
            }
