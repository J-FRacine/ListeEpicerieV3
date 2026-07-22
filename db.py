import os
import psycopg
from psycopg.rows import dict_row

# Connexion à la base Canner
def get_connection():
    return psycopg.connect(
        os.getenv("DATABASE_URL"),   # <-- CORRECTION ICI
        row_factory=dict_row
    )

# Initialisation (optionnelle)
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
                    quantity INTEGER NOT NULL DEFAULT 1
                );
            """)

            conn.commit()

# -----------------------------
# FAMILLES
# -----------------------------

def get_families():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM families ORDER BY name;")
            return cur.fetchall()

# -----------------------------
# CATÉGORIES
# -----------------------------

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

# -----------------------------
# ITEMS
# -----------------------------

def get_items(family_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT items.id, items.name, items.quantity, categories.name AS category
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

def delete_item(item_id, family_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM items
                WHERE id = %s AND family_id = %s;
            """, (item_id, family_id))
            conn.commit()
