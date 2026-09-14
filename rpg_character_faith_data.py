"""Persistance Foi / Domaines pour Personnages JDR.

La divinité reste stockée dans la colonne historique ``rpg_characters.deity``.
Les domaines et sous-domaines sont ajoutés automatiquement à la même table.
"""
from __future__ import annotations

from db import get_connection


_SCHEMA_READY = False


def _text(value, *, label, maximum):
    text = str(value or "").strip()
    if len(text) > maximum:
        raise ValueError(
            f"{label} ne peut pas dépasser {maximum} caractères."
        )
    return text or None


def ensure_rpg_faith_schema():
    """Ajoute les champs Foi sans SQL manuel et sans supprimer de données."""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return

    definitions = (
        "domain_1 TEXT",
        "subdomain_1 TEXT",
        "domain_2 TEXT",
        "subdomain_2 TEXT",
        "faith_notes TEXT",
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            for definition in definitions:
                cur.execute(
                    f"""
                    ALTER TABLE rpg_characters
                    ADD COLUMN IF NOT EXISTS {definition};
                    """
                )
            conn.commit()

    _SCHEMA_READY = True


def get_rpg_faith(user_id, character_id):
    ensure_rpg_faith_schema()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    deity,
                    domain_1,
                    subdomain_1,
                    domain_2,
                    subdomain_2,
                    faith_notes
                FROM rpg_characters
                WHERE id = %s
                  AND user_id = %s;
                """,
                (character_id, user_id),
            )
            row = cur.fetchone()

    if row is None:
        raise ValueError(
            "Ce personnage n’existe plus ou ne vous appartient pas."
        )

    return row


def update_rpg_faith(user_id, character_id, values):
    """Enregistre la divinité et les deux emplacements de domaine."""
    ensure_rpg_faith_schema()

    normalized = {
        "deity": _text(
            values.get("deity"),
            label="La divinité",
            maximum=160,
        ),
        "domain_1": _text(
            values.get("domain_1"),
            label="Le domaine 1",
            maximum=160,
        ),
        "subdomain_1": _text(
            values.get("subdomain_1"),
            label="Le sous-domaine 1",
            maximum=160,
        ),
        "domain_2": _text(
            values.get("domain_2"),
            label="Le domaine 2",
            maximum=160,
        ),
        "subdomain_2": _text(
            values.get("subdomain_2"),
            label="Le sous-domaine 2",
            maximum=160,
        ),
        "faith_notes": _text(
            values.get("faith_notes"),
            label="Les notes de foi",
            maximum=5000,
        ),
    }

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE rpg_characters
                SET
                    deity = %s,
                    domain_1 = %s,
                    subdomain_1 = %s,
                    domain_2 = %s,
                    subdomain_2 = %s,
                    faith_notes = %s,
                    updated_at = NOW()
                WHERE id = %s
                  AND user_id = %s
                RETURNING id;
                """,
                (
                    normalized["deity"],
                    normalized["domain_1"],
                    normalized["subdomain_1"],
                    normalized["domain_2"],
                    normalized["subdomain_2"],
                    normalized["faith_notes"],
                    character_id,
                    user_id,
                ),
            )
            if cur.fetchone() is None:
                raise ValueError(
                    "Ce personnage n’existe plus "
                    "ou ne vous appartient pas."
                )
            conn.commit()
