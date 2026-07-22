import os
import psycopg
import hashlib
from datetime import datetime

# Connexion Postgres via Canner
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg.connect(DATABASE_URL)


# -----------------------------
#  UTILITAIRES
# -----------------------------

def hash_password(password: str) -> str:
    """Hash simple SHA256 (à remplacer par bcrypt plus tard)."""
    return hashlib.sha256(password.encode()).hexdigest()


# -----------------------------
#  INITIALISATION DES TABLES
# -----------------------------

def init_db():
    with conn.cursor() as cur:

        # Table des familles
        cur.execute("""
            CREATE TABLE IF NOT EXISTS families (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """)

        # Table des utilisateurs
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                family_id INTEGER NOT NULL REFERENCES families(id),
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',  -- admin / member / superadmin
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """)

        # Table des catégories globales
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """)

        # Table des items
        cur.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id SERIAL PRIMARY KEY,
                family_id INTEGER NOT NULL REFERENCES families(id),
                category_id INTEGER NOT NULL REFERENCES categories(id),
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """)

        conn.commit()


# -----------------------------
#  FAMILLES
# -----------------------------

def create_family(name: str) -> int:
    """Crée une famille et retourne son ID."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO families (name) VALUES (%s) RETURNING id;",
            (name,)
        )
        family_id = cur.fetchone()[0]
        conn.commit()
        return family_id


# -----------------------------
#  UTILISATEURS
# -----------------------------

def create_user(family_id: int, email: str, password: str, role: str = "member") -> int:
    """Crée un utilisateur dans une famille."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (family_id, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (family_id, email, hash_password(password), role)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        return user_id


def authenticate(email: str, password: str):
    """Retourne l'utilisateur si email + mot de passe sont valides."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, family_id, email, password_hash, role FROM users WHERE email = %s;",
            (email,)
        )
        row = cur.fetchone()

        if not row:
            return None

        user_id, family_id, email, password_hash, role = row

        if hash_password(password) != password_hash:
            return None

        return {
            "id": user_id,
            "family_id": family_id,
            "email": email,
            "role": role
        }


# -----------------------------
#  CATÉGORIES GLOBALES
# -----------------------------

def create_category(name: str) -> int:
    """Crée une catégorie globale (super-admin seulement)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO categories (name) VALUES (%s) RETURNING id;",
            (name,)
        )
        category_id = cur.fetchone()[0]
        conn.commit()
        return category_id


def get_categories():
    """Retourne toutes les catégories globales."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM categories ORDER BY name ASC;")
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1]} for r in rows]


# -----------------------------
#  ITEMS
# -----------------------------

def add_item(family_id: int, category_id: int, name: str, quantity: int):
    """Ajoute un item dans la famille."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO items (family_id, category_id, name, quantity)
            VALUES (%s, %s, %s, %s);
            """,
            (family_id, category_id, name, quantity)
        )
        conn.commit()


def get_items(family_id: int):
    """Retourne tous les items d'une famille avec leur catégorie."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT items.id, items.name, items.quantity, categories.name
            FROM items
            JOIN categories ON items.category_id = categories.id
            WHERE items.family_id = %s
            ORDER BY items.id ASC;
            """,
            (family_id,)
        )
        rows = cur.fetchall()

        return [
            {
                "id": r[0],
                "name": r[1],
                "quantity": r[2],
                "category": r[3]
            }
            for r in rows
        ]


def delete_item(item_id: int, family_id: int):
    """Supprime un item si il appartient à la famille."""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM items WHERE id = %s AND family_id = %s;",
            (item_id, family_id)
        )
        conn.commit()
        
def get_user_by_id(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, family_id, email, role
                FROM users
                WHERE id = %s
            """, (user_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                'id': row[0],
                'family_id': row[1],
                'email': row[2],
                'role': row[3],
            }
