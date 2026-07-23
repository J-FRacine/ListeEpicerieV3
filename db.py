import os
import psycopg
from psycopg.rows import dict_row

def get_connection():
    return psycopg.connect(
        os.getenv("DATABASE_URL"),
        row_factory=dict_row
    )

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
                    name TEXT NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    family_id INTEGER NOT NULL REFERENCES families(id),
                    category_id INTEGER NOT NULL REFERENCES categories(id),
                    name TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    needed INTEGER NOT NULL DEFAULT 0
                );
            """)

            conn.commit()

def get_families():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM families ORDER BY name;")
            return cur.fetchall()

def create_family(name):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO families (name) VALUES (%s);", (name,))
            conn.commit()

def get_categories():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM categories ORDER BY name;")
            return cur.fetchall()

def create_category(name):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO categories (name) VALUES (%s);", (name,))
            conn.commit()

def delete_category(cat_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM items WHERE category_id = %s;", (cat_id,))
            cur.execute("DELETE FROM categories WHERE id = %s;", (cat_id,))
            conn.commit()

def get_items(family_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT items.id, items.name, items.quantity, items.needed,
                       categories.name AS category
                FROM items
                JOIN categories ON items.category_id = categories.id
                WHERE items.family_id = %s
                ORDER BY items.id;
            """, (family_id,))
            return cur.fetchall()

def add_item(family_id, category_id, name, quantity, needed):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO items (family_id, category_id, name, quantity, needed)
                VALUES (%s, %s, %s, %s, %s);
            """, (family_id, category_id, name, quantity, needed))
            conn.commit()

def toggle_needed(item_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT needed FROM items WHERE id = %s;", (item_id,))
            row = cur.fetchone()
            new_val = 0 if row["needed"] == 1 else 1
            cur.execute("UPDATE items SET needed = %s WHERE id = %s;", (new_val, item_id))
            conn.commit()

def delete_item(item_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM items WHERE id = %s;", (item_id,))
            conn.commit()

def delete_family(family_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM items WHERE family_id = %s", (family_id,))
    cur.execute("DELETE FROM families WHERE id = %s", (family_id,))
    conn.commit()
    cur.close()
    conn.close()
    # ---------------------------------------------------------
#  BESOIN (NEEDS)
# ---------------------------------------------------------

def get_needs(family_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, category, done
        FROM needs
        WHERE family_id = %s
        ORDER BY id ASC
    """, (family_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            'id': r[0],
            'name': r[1],
            'category': r[2],
            'done': r[3],
        }
        for r in rows
    ]


def add_need(family_id, category_id, name, done):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO needs (family_id, category, name, done)
        VALUES (%s, %s, %s, %s)
    """, (family_id, category_id, name, done))

    conn.commit()
    cur.close()
    conn.close()


def delete_need(need_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM needs WHERE id = %s", (need_id,))

    conn.commit()
    cur.close()
    conn.close()


def toggle_need_done(need_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE needs
        SET done = CASE WHEN done = 1 THEN 0 ELSE 1 END
        WHERE id = %s
    """, (need_id,))

    conn.commit()
    cur.close()
    conn.close()

