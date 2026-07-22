import sqlite3

def initialize_database(db_path="items.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Activer les clés étrangères (important pour ON DELETE CASCADE)
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.executescript("""
        -- ============================
        -- TABLE DES FAMILLES
        -- ============================
        CREATE TABLE IF NOT EXISTS families (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            is_master INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- ============================
        -- TABLE DES UTILISATEURS
        -- ============================
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE
        );

        -- ============================
        -- TABLE DES CATÉGORIES GLOBALES
        -- ============================
        CREATE TABLE IF NOT EXISTS global_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- ============================
        -- TABLE DES CATÉGORIES LOCALES
        -- ============================
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            color TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE
        );

        -- ============================
        -- TABLE DES ITEMS
        -- ============================
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER NOT NULL,
            user_id INTEGER,
            category_id INTEGER,
            global_category_id INTEGER,
            name TEXT NOT NULL,
            quantity REAL DEFAULT 1,
            unit TEXT,
            notes TEXT,
            is_done INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
            FOREIGN KEY (global_category_id) REFERENCES global_categories(id) ON DELETE SET NULL
        );

        -- ============================
        -- TABLE DES BESOINS
        -- ============================
        CREATE TABLE IF NOT EXISTS needs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER NOT NULL,
            user_id INTEGER,
            category_id INTEGER,
            global_category_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            priority INTEGER DEFAULT 0,
            status TEXT DEFAULT 'open',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
            FOREIGN KEY (global_category_id) REFERENCES global_categories(id) ON DELETE SET NULL
        );

        -- ============================
        -- TABLE DES PARTAGES ENTRE FAMILLES
        -- ============================
        CREATE TABLE IF NOT EXISTS family_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_family_id INTEGER NOT NULL,
            target_family_id INTEGER NOT NULL,
            mode TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_family_id) REFERENCES families(id) ON DELETE CASCADE,
            FOREIGN KEY (target_family_id) REFERENCES families(id) ON DELETE CASCADE
        );

        -- ============================
        -- INDEXES POUR PERFORMANCE
        -- ============================
        CREATE INDEX IF NOT EXISTS idx_items_family ON items(family_id);
        CREATE INDEX IF NOT EXISTS idx_items_category ON items(category_id);
        CREATE INDEX IF NOT EXISTS idx_items_global_category ON items(global_category_id);
        CREATE INDEX IF NOT EXISTS idx_items_user ON items(user_id);

        CREATE INDEX IF NOT EXISTS idx_categories_family ON categories(family_id);

        CREATE INDEX IF NOT EXISTS idx_users_family ON users(family_id);

        CREATE INDEX IF NOT EXISTS idx_needs_family ON needs(family_id);
        CREATE INDEX IF NOT EXISTS idx_needs_user ON needs(user_id);
        CREATE INDEX IF NOT EXISTS idx_needs_category ON needs(category_id);
        CREATE INDEX IF NOT EXISTS idx_needs_global_category ON needs(global_category_id);
    """)

    conn.commit()
    conn.close()
