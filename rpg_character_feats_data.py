"""Persistance des dons structurés de Personnages JDR."""
from __future__ import annotations

from db import get_connection


_SCHEMA_READY = False
FEAT_KINDS = {"passive", "active", "info"}
SAVE_KEYS = {
    "",
    "all",
    "fortitude",
    "reflex",
    "will",
    "fear",
    "horror",
    "madness",
}


def _text(value, *, label, maximum, required=False):
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{label} est obligatoire.")
    if len(text) > maximum:
        raise ValueError(
            f"{label} ne peut pas dépasser {maximum} caractères."
        )
    return text or None


def _integer(value, *, label, minimum=-100, maximum=100):
    if value in (None, ""):
        return 0
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} doit être un nombre entier.") from error
    if result < minimum or result > maximum:
        raise ValueError(
            f"{label} doit être compris entre {minimum} et {maximum}."
        )
    return result


def ensure_rpg_feat_schema():
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rpg_character_feats (
                    id BIGSERIAL PRIMARY KEY,
                    character_id BIGINT NOT NULL
                        REFERENCES rpg_characters(id)
                        ON DELETE CASCADE,
                    feat_name TEXT NOT NULL,
                    english_name TEXT,
                    feat_kind TEXT NOT NULL DEFAULT 'info'
                        CHECK (feat_kind IN ('passive', 'active', 'info')),
                    catalog_key TEXT,
                    source_text TEXT,
                    prerequisites TEXT,
                    summary TEXT,
                    effects TEXT,
                    notes TEXT,
                    linked_attack_id BIGINT
                        REFERENCES rpg_character_attacks(id)
                        ON DELETE SET NULL,
                    attack_modifier INTEGER NOT NULL DEFAULT 0,
                    damage_note TEXT,
                    initiative_modifier INTEGER NOT NULL DEFAULT 0,
                    cmb_modifier INTEGER NOT NULL DEFAULT 0,
                    cmd_modifier INTEGER NOT NULL DEFAULT 0,
                    save_key TEXT,
                    save_modifier INTEGER NOT NULL DEFAULT 0,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CHECK (
                        save_key IS NULL
                        OR save_key IN (
                            'all', 'fortitude', 'reflex', 'will',
                            'fear', 'horror', 'madness'
                        )
                    )
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS
                rpg_character_feats_character_idx
                ON rpg_character_feats (
                    character_id,
                    sort_order,
                    feat_name,
                    id
                );
                """
            )
            conn.commit()

    _SCHEMA_READY = True


def _require_character(cur, user_id, character_id):
    cur.execute(
        """
        SELECT id
        FROM rpg_characters
        WHERE id = %s
          AND user_id = %s;
        """,
        (character_id, user_id),
    )
    if cur.fetchone() is None:
        raise ValueError(
            "Ce personnage n’existe plus ou ne vous appartient pas."
        )


def _linked_attack(cur, character_id, value):
    if value in (None, ""):
        return None
    try:
        attack_id = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("L’attaque liée est invalide.") from error

    cur.execute(
        """
        SELECT id
        FROM rpg_character_attacks
        WHERE id = %s
          AND character_id = %s;
        """,
        (attack_id, character_id),
    )
    if cur.fetchone() is None:
        raise ValueError(
            "L’attaque liée n’appartient pas à ce personnage."
        )
    return attack_id


def _normalized(values):
    kind = str(values.get("feat_kind") or "info").strip().lower()
    if kind not in FEAT_KINDS:
        raise ValueError("Le type de don est invalide.")

    save_key = str(values.get("save_key") or "").strip().lower()
    if save_key not in SAVE_KEYS:
        raise ValueError("Le jet de sauvegarde ciblé est invalide.")

    return {
        "feat_name": _text(
            values.get("feat_name"),
            label="Le nom du don",
            maximum=160,
            required=True,
        ),
        "english_name": _text(
            values.get("english_name"),
            label="Le nom anglais",
            maximum=160,
        ),
        "feat_kind": kind,
        "catalog_key": _text(
            values.get("catalog_key"),
            label="La clé du catalogue",
            maximum=120,
        ),
        "source_text": _text(
            values.get("source_text"),
            label="La source",
            maximum=300,
        ),
        "prerequisites": _text(
            values.get("prerequisites"),
            label="Les prérequis",
            maximum=2000,
        ),
        "summary": _text(
            values.get("summary"),
            label="Le résumé",
            maximum=4000,
        ),
        "effects": _text(
            values.get("effects"),
            label="Les effets",
            maximum=6000,
        ),
        "notes": _text(
            values.get("notes"),
            label="Les notes",
            maximum=4000,
        ),
        "attack_modifier": _integer(
            values.get("attack_modifier"),
            label="Le modificateur d’attaque",
        ),
        "damage_note": _text(
            values.get("damage_note"),
            label="La note de dégâts",
            maximum=1000,
        ),
        "initiative_modifier": _integer(
            values.get("initiative_modifier"),
            label="Le modificateur d’initiative",
        ),
        "cmb_modifier": _integer(
            values.get("cmb_modifier"),
            label="Le modificateur BMO/CMB",
        ),
        "cmd_modifier": _integer(
            values.get("cmd_modifier"),
            label="Le modificateur DMD/CMD",
        ),
        "save_key": save_key or None,
        "save_modifier": _integer(
            values.get("save_modifier"),
            label="Le modificateur de sauvegarde",
        ),
        "sort_order": _integer(
            values.get("sort_order"),
            label="L’ordre",
            minimum=-100000,
            maximum=100000,
        ),
    }


def list_rpg_feats(user_id, character_id):
    ensure_rpg_feat_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                SELECT
                    f.*,
                    a.attack_name AS linked_attack_name
                FROM rpg_character_feats f
                LEFT JOIN rpg_character_attacks a
                    ON a.id = f.linked_attack_id
                WHERE f.character_id = %s
                ORDER BY
                    CASE f.feat_kind
                        WHEN 'active' THEN 1
                        WHEN 'passive' THEN 2
                        ELSE 3
                    END,
                    f.sort_order,
                    LOWER(f.feat_name),
                    f.id;
                """,
                (character_id,),
            )
            return cur.fetchall()


def create_rpg_feat(user_id, character_id, values):
    ensure_rpg_feat_schema()
    normalized = _normalized(values)

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            linked_attack_id = _linked_attack(
                cur,
                character_id,
                values.get("linked_attack_id"),
            )

            cur.execute(
                """
                INSERT INTO rpg_character_feats (
                    character_id,
                    feat_name,
                    english_name,
                    feat_kind,
                    catalog_key,
                    source_text,
                    prerequisites,
                    summary,
                    effects,
                    notes,
                    linked_attack_id,
                    attack_modifier,
                    damage_note,
                    initiative_modifier,
                    cmb_modifier,
                    cmd_modifier,
                    save_key,
                    save_modifier,
                    sort_order
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id;
                """,
                (
                    character_id,
                    normalized["feat_name"],
                    normalized["english_name"],
                    normalized["feat_kind"],
                    normalized["catalog_key"],
                    normalized["source_text"],
                    normalized["prerequisites"],
                    normalized["summary"],
                    normalized["effects"],
                    normalized["notes"],
                    linked_attack_id,
                    normalized["attack_modifier"],
                    normalized["damage_note"],
                    normalized["initiative_modifier"],
                    normalized["cmb_modifier"],
                    normalized["cmd_modifier"],
                    normalized["save_key"],
                    normalized["save_modifier"],
                    normalized["sort_order"],
                ),
            )
            feat_id = cur.fetchone()["id"]
            conn.commit()
            return feat_id


def update_rpg_feat(user_id, character_id, feat_id, values):
    ensure_rpg_feat_schema()
    normalized = _normalized(values)

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            linked_attack_id = _linked_attack(
                cur,
                character_id,
                values.get("linked_attack_id"),
            )

            cur.execute(
                """
                UPDATE rpg_character_feats
                SET
                    feat_name = %s,
                    english_name = %s,
                    feat_kind = %s,
                    catalog_key = %s,
                    source_text = %s,
                    prerequisites = %s,
                    summary = %s,
                    effects = %s,
                    notes = %s,
                    linked_attack_id = %s,
                    attack_modifier = %s,
                    damage_note = %s,
                    initiative_modifier = %s,
                    cmb_modifier = %s,
                    cmd_modifier = %s,
                    save_key = %s,
                    save_modifier = %s,
                    sort_order = %s,
                    updated_at = NOW()
                WHERE id = %s
                  AND character_id = %s
                RETURNING id;
                """,
                (
                    normalized["feat_name"],
                    normalized["english_name"],
                    normalized["feat_kind"],
                    normalized["catalog_key"],
                    normalized["source_text"],
                    normalized["prerequisites"],
                    normalized["summary"],
                    normalized["effects"],
                    normalized["notes"],
                    linked_attack_id,
                    normalized["attack_modifier"],
                    normalized["damage_note"],
                    normalized["initiative_modifier"],
                    normalized["cmb_modifier"],
                    normalized["cmd_modifier"],
                    normalized["save_key"],
                    normalized["save_modifier"],
                    normalized["sort_order"],
                    feat_id,
                    character_id,
                ),
            )
            if cur.fetchone() is None:
                raise ValueError("Ce don n’existe plus.")
            conn.commit()


def delete_rpg_feat(user_id, character_id, feat_id):
    ensure_rpg_feat_schema()
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                DELETE FROM rpg_character_feats
                WHERE id = %s
                  AND character_id = %s
                RETURNING id;
                """,
                (feat_id, character_id),
            )
            if cur.fetchone() is None:
                raise ValueError("Ce don n’existe plus.")
            conn.commit()
