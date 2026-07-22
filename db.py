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
                ORDER BY categories.name, items.name;
            """, (family_id,))
            return cur.fetchall()

def add_item(family_id, category_id, name, quantity):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO items (family_id, category_id, name, quantity)
                VALUES (%s, %s, %s, %s);
            """, (family_id, category_id, name, quantity))
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



