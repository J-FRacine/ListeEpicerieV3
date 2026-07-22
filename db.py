import os
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL")

# Connexion globale
conn = psycopg.connect(DATABASE_URL)

def init_db():
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL
            );
        """)
        conn.commit()
