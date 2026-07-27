from __future__ import annotations

from collections.abc import Iterable

from db import get_connection


APP_DEFINITIONS = {
    "grocery": {
        "label": "Liste d’épicerie",
        "short_label": "Épicerie",
        "icon": "shopping_cart",
        "description": (
            "Items, besoins, magasins, catégories, "
            "modèles et recettes."
        ),
        "available": True,
    },
    "blood_pressure": {
        "label": "Journal de pression",
        "short_label": "Pression",
        "icon": "monitor_heart",
        "description": (
            "Mesures privées de pression "
            "artérielle et du pouls."
        ),
        "available": True,
    },
    "finances": {
        "label": "Finances",
        "short_label": "Finances",
        "icon": "account_balance_wallet",
        "description": (
            "Revenus, dépenses, budgets "
            "et transactions récurrentes."
        ),
        "available": False,
    },
    "rpg": {
        "label": "Personnages JDR",
        "short_label": "JDR",
        "icon": "casino",
        "description": (
            "Feuilles de personnage interactives "
            "pour Donjons & Dragons et Ravenloft."
        ),
        "available": False,
    },
}

ALL_APP_KEYS = tuple(
    APP_DEFINITIONS.keys()
)

DEFAULT_APP_KEYS = (
    "grocery",
)


def _normalize_app_keys(
    app_keys: Iterable[str] | None,
) -> list[str]:
    normalized = []

    for app_key in app_keys or []:
        key = str(app_key).strip()

        if key not in APP_DEFINITIONS:
            raise ValueError(
                f"Application inconnue : {key}"
            )

        if key not in normalized:
            normalized.append(key)

    return normalized


def _get_user_row(
    cur,
    user_id,
):
    cur.execute(
        """
        SELECT
            id,
            is_admin,
            is_active
        FROM users
        WHERE id = %s;
        """,
        (user_id,),
    )

    user = cur.fetchone()

    if user is None:
        raise ValueError(
            "Cet utilisateur n’existe plus."
        )

    return user


def _require_active_user(
    cur,
    user_id,
):
    user = _get_user_row(
        cur,
        user_id,
    )

    if not user["is_active"]:
        raise PermissionError(
            "La session utilisateur "
            "n’est plus valide."
        )

    return user


def _require_global_admin(
    cur,
    user_id,
):
    user = _require_active_user(
        cur,
        user_id,
    )

    if not user["is_admin"]:
        raise PermissionError(
            "Cette action est réservée "
            "à l’administrateur."
        )

    return user


def _initialize_profile(
    cur,
    user_id,
):
    """Initialise un ancien compte avec l’accès Épicerie.

    La table de profil empêche de réaccorder automatiquement
    l’application lorsqu’un administrateur retire volontairement
    tous les accès d’un utilisateur.
    """

    cur.execute(
        """
        INSERT INTO user_app_access_profiles (
            user_id
        )
        VALUES (%s)
        ON CONFLICT (user_id) DO NOTHING
        RETURNING user_id;
        """,
        (user_id,),
    )

    created_profile = (
        cur.fetchone()
        is not None
    )

    if created_profile:
        cur.execute(
            """
            INSERT INTO user_app_access (
                user_id,
                app_key
            )
            VALUES (%s, 'grocery')
            ON CONFLICT (
                user_id,
                app_key
            ) DO NOTHING;
            """,
            (user_id,),
        )


def _initialize_all_profiles(
    cur,
):
    cur.execute(
        """
        WITH new_profiles AS (
            INSERT INTO user_app_access_profiles (
                user_id
            )
            SELECT user_account.id
            FROM users AS user_account
            LEFT JOIN user_app_access_profiles
              AS existing_profile
              ON existing_profile.user_id
                 = user_account.id
            WHERE existing_profile.user_id
                  IS NULL
            ON CONFLICT (user_id) DO NOTHING
            RETURNING user_id
        )
        INSERT INTO user_app_access (
            user_id,
            app_key
        )
        SELECT
            new_profile.user_id,
            'grocery'
        FROM new_profiles AS new_profile
        ON CONFLICT (
            user_id,
            app_key
        ) DO NOTHING;
        """
    )


def init_app_access_schema():
    """Crée les tables de permissions des applications."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                user_app_access_profiles (
                    user_id INTEGER PRIMARY KEY
                        REFERENCES users(id)
                        ON DELETE CASCADE,
                    configured_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW()
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                user_app_access (
                    user_id INTEGER NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,
                    app_key TEXT NOT NULL
                        CHECK (
                            app_key IN (
                                'grocery',
                                'blood_pressure',
                                'finances',
                                'rpg'
                            )
                        ),
                    granted_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (
                        user_id,
                        app_key
                    )
                );
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                user_app_access_app_key_idx
                ON user_app_access (
                    app_key,
                    user_id
                );
                """
            )

            _initialize_all_profiles(cur)

            conn.commit()


def get_user_app_access(
    user_id,
) -> set[str]:
    """Retourne les applications visibles et utilisables."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            user = _require_active_user(
                cur,
                user_id,
            )

            _initialize_profile(
                cur,
                user_id,
            )

            if user["is_admin"]:
                conn.commit()
                return set(
                    ALL_APP_KEYS
                )

            cur.execute(
                """
                SELECT app_key
                FROM user_app_access
                WHERE user_id = %s
                ORDER BY app_key;
                """,
                (user_id,),
            )

            result = {
                row["app_key"]
                for row in cur.fetchall()
                if row["app_key"]
                in APP_DEFINITIONS
            }

            conn.commit()
            return result


def user_has_app_access(
    user_id,
    app_key,
) -> bool:
    key = str(app_key).strip()

    if key not in APP_DEFINITIONS:
        return False

    return key in get_user_app_access(
        user_id
    )


def list_user_app_access_for_admin(
    actor_user_id,
) -> dict[int, set[str]]:
    """Retourne les permissions de tous les utilisateurs."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_global_admin(
                cur,
                actor_user_id,
            )

            _initialize_all_profiles(cur)

            cur.execute(
                """
                SELECT
                    user_account.id,
                    user_account.is_admin,
                    access.app_key
                FROM users AS user_account
                LEFT JOIN user_app_access AS access
                  ON access.user_id
                     = user_account.id
                ORDER BY
                    user_account.id,
                    access.app_key;
                """
            )

            result: dict[
                int,
                set[str],
            ] = {}

            for row in cur.fetchall():
                user_id = int(
                    row["id"]
                )

                result.setdefault(
                    user_id,
                    set(),
                )

                if row["is_admin"]:
                    result[user_id] = set(
                        ALL_APP_KEYS
                    )
                elif (
                    row["app_key"]
                    in APP_DEFINITIONS
                ):
                    result[user_id].add(
                        row["app_key"]
                    )

            conn.commit()
            return result


def set_user_app_access_for_admin(
    actor_user_id,
    target_user_id,
    app_keys,
):
    """Remplace les permissions d’applications d’un utilisateur."""

    normalized_keys = (
        _normalize_app_keys(
            app_keys
        )
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_global_admin(
                cur,
                actor_user_id,
            )

            target_user = _get_user_row(
                cur,
                target_user_id,
            )

            if target_user["is_admin"]:
                raise ValueError(
                    "Un administrateur du portail "
                    "a automatiquement accès à "
                    "toutes les applications."
                )

            cur.execute(
                """
                INSERT INTO user_app_access_profiles (
                    user_id,
                    configured_at
                )
                VALUES (
                    %s,
                    NOW()
                )
                ON CONFLICT (user_id)
                DO UPDATE SET
                    configured_at = NOW();
                """,
                (target_user_id,),
            )

            cur.execute(
                """
                DELETE FROM user_app_access
                WHERE user_id = %s;
                """,
                (target_user_id,),
            )

            if normalized_keys:
                cur.executemany(
                    """
                    INSERT INTO user_app_access (
                        user_id,
                        app_key
                    )
                    VALUES (%s, %s)
                    ON CONFLICT (
                        user_id,
                        app_key
                    ) DO NOTHING;
                    """,
                    [
                        (
                            target_user_id,
                            app_key,
                        )
                        for app_key
                        in normalized_keys
                    ],
                )

            conn.commit()


def app_labels(
    app_keys,
) -> list[str]:
    keys = set(
        app_keys or []
    )

    return [
        definition["label"]
        for key, definition
        in APP_DEFINITIONS.items()
        if key in keys
    ]
