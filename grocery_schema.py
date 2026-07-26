from psycopg import sql


def _initialize_sort_orders(cur, table_name):
    if table_name not in {"categories", "stores"}:
        raise ValueError("Table de classement invalide.")

    table = sql.Identifier(table_name)
    cur.execute(
        sql.SQL(
            """
            WITH family_state AS (
                SELECT
                    family_id,
                    COUNT(DISTINCT sort_order) AS distinct_orders
                FROM {}
                WHERE deleted_at IS NULL
                GROUP BY family_id
            ),
            ranked AS (
                SELECT
                    entry.id,
                    ROW_NUMBER() OVER (
                        PARTITION BY entry.family_id
                        ORDER BY LOWER(entry.name), entry.name, entry.id
                    ) * 10 AS new_order
                FROM {} AS entry
                JOIN family_state AS state
                  ON state.family_id = entry.family_id
                WHERE entry.deleted_at IS NULL
                  AND state.distinct_orders <= 1
            )
            UPDATE {} AS entry
            SET sort_order = ranked.new_order
            FROM ranked
            WHERE entry.id = ranked.id;
            """
        ).format(table, table, table)
    )


def migrate_grocery_schema(get_connection):
    """Ajoute les nouvelles structures sans supprimer les données existantes."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS stores (
                    id SERIAL PRIMARY KEY,
                    family_id INTEGER NOT NULL
                        REFERENCES families(id)
                        ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    deleted_at TIMESTAMPTZ,
                    deleted_by_user_id INTEGER
                );
                """
            )

            cur.execute(
                """
                ALTER TABLE categories
                ADD COLUMN IF NOT EXISTS sort_order INTEGER;
                ALTER TABLE categories
                ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
                ALTER TABLE categories
                ADD COLUMN IF NOT EXISTS deleted_by_user_id INTEGER;

                UPDATE categories
                SET sort_order = 0
                WHERE sort_order IS NULL;

                ALTER TABLE categories
                ALTER COLUMN sort_order SET DEFAULT 0;
                ALTER TABLE categories
                ALTER COLUMN sort_order SET NOT NULL;
                """
            )

            cur.execute(
                """
                ALTER TABLE items
                ADD COLUMN IF NOT EXISTS note TEXT;
                ALTER TABLE items
                ADD COLUMN IF NOT EXISTS store_id INTEGER;
                ALTER TABLE items
                ADD COLUMN IF NOT EXISTS times_needed INTEGER;
                ALTER TABLE items
                ADD COLUMN IF NOT EXISTS last_needed_at TIMESTAMPTZ;
                ALTER TABLE items
                ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
                ALTER TABLE items
                ADD COLUMN IF NOT EXISTS deleted_by_user_id INTEGER;

                UPDATE items
                SET note = ''
                WHERE note IS NULL;

                UPDATE items
                SET times_needed = CASE
                    WHEN needed = 1 THEN 1
                    ELSE 0
                END
                WHERE times_needed IS NULL;

                ALTER TABLE items
                ALTER COLUMN note SET DEFAULT '';
                ALTER TABLE items
                ALTER COLUMN note SET NOT NULL;
                ALTER TABLE items
                ALTER COLUMN times_needed SET DEFAULT 0;
                ALTER TABLE items
                ALTER COLUMN times_needed SET NOT NULL;
                """
            )

            cur.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'items_store_id_fkey'
                          AND conrelid = 'items'::regclass
                    ) THEN
                        ALTER TABLE items
                        ADD CONSTRAINT items_store_id_fkey
                        FOREIGN KEY (store_id)
                        REFERENCES stores(id)
                        ON DELETE SET NULL;
                    END IF;
                END
                $$;
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_log (
                    id BIGSERIAL PRIMARY KEY,
                    family_id INTEGER NOT NULL
                        REFERENCES families(id)
                        ON DELETE CASCADE,
                    user_id INTEGER
                        REFERENCES users(id)
                        ON DELETE SET NULL,
                    action_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id INTEGER,
                    entity_name TEXT NOT NULL DEFAULT '',
                    details JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS grocery_templates (
                    id SERIAL PRIMARY KEY,
                    family_id INTEGER NOT NULL
                        REFERENCES families(id)
                        ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_by_user_id INTEGER
                        REFERENCES users(id)
                        ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS grocery_template_items (
                    id BIGSERIAL PRIMARY KEY,
                    template_id INTEGER NOT NULL
                        REFERENCES grocery_templates(id)
                        ON DELETE CASCADE,
                    item_id INTEGER NOT NULL
                        REFERENCES items(id)
                        ON DELETE CASCADE,
                    quantity INTEGER NOT NULL DEFAULT 1
                        CHECK (quantity >= 1),
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (template_id, item_id)
                );

                CREATE TABLE IF NOT EXISTS grocery_recipes (
                    id SERIAL PRIMARY KEY,
                    family_id INTEGER NOT NULL
                        REFERENCES families(id)
                        ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    instructions TEXT NOT NULL DEFAULT '',
                    servings INTEGER NOT NULL DEFAULT 4
                        CHECK (servings >= 1),
                    created_by_user_id INTEGER
                        REFERENCES users(id)
                        ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS grocery_recipe_ingredients (
                    id BIGSERIAL PRIMARY KEY,
                    recipe_id INTEGER NOT NULL
                        REFERENCES grocery_recipes(id)
                        ON DELETE CASCADE,
                    item_id INTEGER NOT NULL
                        REFERENCES items(id)
                        ON DELETE CASCADE,
                    quantity INTEGER NOT NULL DEFAULT 1
                        CHECK (quantity >= 1),
                    note TEXT NOT NULL DEFAULT '',
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (recipe_id, item_id)
                );
                """
            )

            cur.execute(
                """
                DROP INDEX IF EXISTS categories_family_name_unique;

                CREATE UNIQUE INDEX IF NOT EXISTS
                    categories_family_active_name_unique
                ON categories (
                    family_id,
                    LOWER(BTRIM(name))
                )
                WHERE family_id IS NOT NULL
                  AND deleted_at IS NULL;

                CREATE UNIQUE INDEX IF NOT EXISTS
                    stores_family_active_name_unique
                ON stores (
                    family_id,
                    LOWER(BTRIM(name))
                )
                WHERE deleted_at IS NULL;

                CREATE INDEX IF NOT EXISTS items_family_active_idx
                ON items (family_id, deleted_at);

                CREATE INDEX IF NOT EXISTS items_family_needed_idx
                ON items (family_id, needed)
                WHERE deleted_at IS NULL;

                CREATE INDEX IF NOT EXISTS activity_log_family_created_idx
                ON activity_log (family_id, created_at DESC);

                CREATE UNIQUE INDEX IF NOT EXISTS
                    grocery_templates_family_name_unique
                ON grocery_templates (
                    family_id,
                    LOWER(BTRIM(name))
                );

                CREATE INDEX IF NOT EXISTS
                    grocery_template_items_template_order_idx
                ON grocery_template_items (
                    template_id,
                    sort_order,
                    id
                );

                CREATE UNIQUE INDEX IF NOT EXISTS
                    grocery_recipes_family_name_unique
                ON grocery_recipes (
                    family_id,
                    LOWER(BTRIM(name))
                );

                CREATE INDEX IF NOT EXISTS
                    grocery_recipe_ingredients_recipe_order_idx
                ON grocery_recipe_ingredients (
                    recipe_id,
                    sort_order,
                    id
                );
                """
            )

            # Chaque famille reçoit un magasin initial. Les anciens items y sont liés.
            cur.execute(
                """
                INSERT INTO stores (family_id, name, sort_order)
                SELECT family.id, 'Épicerie', 10
                FROM families AS family
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM stores AS store
                    WHERE store.family_id = family.id
                      AND store.deleted_at IS NULL
                );
                """
            )

            cur.execute(
                """
                UPDATE items AS item
                SET store_id = (
                    SELECT store.id
                    FROM stores AS store
                    WHERE store.family_id = item.family_id
                      AND store.deleted_at IS NULL
                    ORDER BY store.sort_order, LOWER(store.name), store.id
                    LIMIT 1
                )
                WHERE item.store_id IS NULL;
                """
            )

            _initialize_sort_orders(cur, "categories")
            _initialize_sort_orders(cur, "stores")

            # Conservation de 30 jours dans la corbeille.
            cur.execute(
                """
                DELETE FROM items
                WHERE deleted_at IS NOT NULL
                  AND deleted_at < NOW() - INTERVAL '30 days';

                DELETE FROM categories AS category
                WHERE category.deleted_at IS NOT NULL
                  AND category.deleted_at < NOW() - INTERVAL '30 days'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM items AS item
                      WHERE item.category_id = category.id
                  );

                DELETE FROM stores AS store
                WHERE store.deleted_at IS NOT NULL
                  AND store.deleted_at < NOW() - INTERVAL '30 days'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM items AS item
                      WHERE item.store_id = store.id
                  );
                """
            )

            conn.commit()
