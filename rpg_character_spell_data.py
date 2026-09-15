"""Persistance de la préparation des sorts JDR — Phase 15A."""
from __future__ import annotations

from db import get_connection
from rpg_character_spell_rules import (
    ABILITY_LABELS,
    cleric_slot_table,
    effective_ability_score,
    validate_preparation_capacity,
)
from rpg_character_spell_schema import ensure_spell_schema


PROFILE_MODES = {"cure", "inflict", "none"}
SLOT_KINDS = {"normal", "domain"}


def _ensure():
    ensure_spell_schema(get_connection=get_connection)


def _text(value, *, label, maximum, required=False):
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{label} est obligatoire.")
    if len(text) > maximum:
        raise ValueError(f"{label} ne peut pas dépasser {maximum} caractères.")
    return text or None


def _int(value, *, label, minimum, maximum, default=None):
    if value in (None, ""):
        if default is None:
            raise ValueError(f"{label} est obligatoire.")
        result = int(default)
    else:
        try:
            result = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label} doit être un nombre entier.") from error
    if result < minimum or result > maximum:
        raise ValueError(
            f"{label} doit être compris entre {minimum} et {maximum}."
        )
    return result


def _require_character(cur, user_id, character_id):
    cur.execute(
        """
        SELECT
            id,
            character_level,
            class_name,
            str_score, str_temp_score,
            dex_score, dex_temp_score,
            con_score, con_temp_score,
            int_score, int_temp_score,
            wis_score, wis_temp_score,
            cha_score, cha_temp_score
        FROM rpg_characters
        WHERE id = %s AND user_id = %s;
        """,
        (character_id, user_id),
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError(
            "Ce personnage n’existe plus ou ne vous appartient pas."
        )
    return dict(row)


def _default_profile(character):
    level = max(1, min(20, int(character.get("character_level") or 1)))
    return {
        "character_id": int(character["id"]),
        "class_key": "cleric",
        "class_level": level,
        "caster_level": level,
        "ability_key": "wis",
        "spontaneous_mode": "cure",
        "preparation_notes": None,
        "is_default": True,
    }


def _profile_from_cursor(cur, character):
    cur.execute(
        """
        SELECT *
        FROM rpg_character_spellcasting_profiles
        WHERE character_id = %s;
        """,
        (character["id"],),
    )
    row = cur.fetchone()
    if row is None:
        return _default_profile(character)
    result = dict(row)
    result["is_default"] = False
    return result


def get_spellcasting_profile(user_id, character_id):
    _ensure()
    with get_connection() as conn:
        with conn.cursor() as cur:
            character = _require_character(cur, user_id, character_id)
            return _profile_from_cursor(cur, character)


def save_spellcasting_profile(user_id, character_id, values):
    _ensure()
    class_key = str(values.get("class_key") or "cleric").strip().lower()
    if class_key != "cleric":
        raise ValueError("La Phase 15A prend actuellement en charge le Clerc.")
    class_level = _int(
        values.get("class_level"),
        label="Le niveau de Clerc",
        minimum=1,
        maximum=20,
        default=1,
    )
    caster_level = _int(
        values.get("caster_level"),
        label="Le niveau de lanceur de sorts",
        minimum=1,
        maximum=100,
        default=class_level,
    )
    ability_key = str(values.get("ability_key") or "wis").strip().lower()
    if ability_key not in ABILITY_LABELS:
        raise ValueError("La caractéristique de lancement est invalide.")
    spontaneous_mode = str(
        values.get("spontaneous_mode") or "cure"
    ).strip().lower()
    if spontaneous_mode not in PROFILE_MODES:
        raise ValueError("Le mode de conversion spontanée est invalide.")
    notes = _text(
        values.get("preparation_notes"),
        label="Les notes de préparation",
        maximum=5000,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            character = _require_character(cur, user_id, character_id)
            cur.execute(
                """
                SELECT *
                FROM rpg_character_prepared_spells
                WHERE character_id = %s
                ORDER BY spell_level, slot_kind, id;
                """,
                (character_id,),
            )
            existing_prepared = [dict(row) for row in cur.fetchall()]
            score = effective_ability_score(character, ability_key)
            slot_rows = cleric_slot_table(class_level, score)
            accepted = []
            for prepared in existing_prepared:
                try:
                    validate_preparation_capacity(
                        slot_rows=slot_rows,
                        existing_rows=accepted,
                        spell_level=prepared.get("spell_level"),
                        slot_kind=prepared.get("slot_kind"),
                        prepared_count=prepared.get("prepared_count"),
                    )
                except ValueError as error:
                    raise ValueError(
                        "La nouvelle configuration ne peut pas contenir la préparation actuelle : "
                        + str(error)
                    ) from error
                accepted.append(prepared)

            cur.execute(
                """
                INSERT INTO rpg_character_spellcasting_profiles (
                    character_id,
                    class_key,
                    class_level,
                    caster_level,
                    ability_key,
                    spontaneous_mode,
                    preparation_notes
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (character_id) DO UPDATE SET
                    class_key = EXCLUDED.class_key,
                    class_level = EXCLUDED.class_level,
                    caster_level = EXCLUDED.caster_level,
                    ability_key = EXCLUDED.ability_key,
                    spontaneous_mode = EXCLUDED.spontaneous_mode,
                    preparation_notes = EXCLUDED.preparation_notes,
                    updated_at = NOW();
                """,
                (
                    character_id,
                    class_key,
                    class_level,
                    caster_level,
                    ability_key,
                    spontaneous_mode,
                    notes,
                ),
            )
            conn.commit()


def list_prepared_spells(user_id, character_id):
    _ensure()
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                SELECT *
                FROM rpg_character_prepared_spells
                WHERE character_id = %s
                ORDER BY
                    spell_level,
                    CASE slot_kind WHEN 'normal' THEN 1 ELSE 2 END,
                    sort_order,
                    LOWER(spell_name),
                    id;
                """,
                (character_id,),
            )
            return [dict(row) for row in cur.fetchall()]


def _normalize_preparation(values):
    spell_level = _int(
        values.get("spell_level"),
        label="Le niveau du sort",
        minimum=0,
        maximum=9,
        default=0,
    )
    slot_kind = str(values.get("slot_kind") or "normal").strip().lower()
    if slot_kind not in SLOT_KINDS:
        raise ValueError("Le type d’emplacement est invalide.")
    if spell_level == 0 and slot_kind != "normal":
        raise ValueError("Une oraison n’utilise pas d’emplacement de domaine.")
    prepared_count = _int(
        values.get("prepared_count"),
        label="Le nombre préparé",
        minimum=1,
        maximum=100,
        default=1,
    )
    used_count = _int(
        values.get("used_count"),
        label="Le nombre utilisé",
        minimum=0,
        maximum=100,
        default=0,
    )
    if spell_level == 0:
        used_count = 0
    if used_count > prepared_count:
        raise ValueError("Le nombre utilisé ne peut pas dépasser le nombre préparé.")

    return {
        "catalog_key": _text(
            values.get("catalog_key"),
            label="La clé du catalogue",
            maximum=160,
        ),
        "spell_name": _text(
            values.get("spell_name"),
            label="Le nom du sort",
            maximum=200,
            required=True,
        ),
        "spell_level": spell_level,
        "slot_kind": slot_kind,
        "domain_source": _text(
            values.get("domain_source"),
            label="Le domaine",
            maximum=160,
        ),
        "prepared_count": prepared_count,
        "used_count": used_count,
        "school": _text(values.get("school"), label="L’école", maximum=160),
        "range_text": _text(values.get("range_text"), label="La portée", maximum=300),
        "summary": _text(values.get("summary"), label="Le résumé", maximum=4000),
        "source_text": _text(values.get("source_text"), label="La source", maximum=500),
        "notes": _text(values.get("notes"), label="Les notes", maximum=4000),
        "sort_order": _int(
            values.get("sort_order"),
            label="L’ordre",
            minimum=-100000,
            maximum=100000,
            default=0,
        ),
    }


def save_prepared_spell(
    user_id,
    character_id,
    values,
    preparation_id=None,
):
    _ensure()
    normalized = _normalize_preparation(values)

    with get_connection() as conn:
        with conn.cursor() as cur:
            character = _require_character(cur, user_id, character_id)
            profile = _profile_from_cursor(cur, character)
            cur.execute(
                """
                SELECT *
                FROM rpg_character_prepared_spells
                WHERE character_id = %s
                ORDER BY id;
                """,
                (character_id,),
            )
            existing = [dict(row) for row in cur.fetchall()]
            score = effective_ability_score(character, profile["ability_key"])
            slot_rows = cleric_slot_table(profile["class_level"], score)
            validate_preparation_capacity(
                slot_rows=slot_rows,
                existing_rows=existing,
                spell_level=normalized["spell_level"],
                slot_kind=normalized["slot_kind"],
                prepared_count=normalized["prepared_count"],
                exclude_preparation_id=preparation_id,
            )

            if preparation_id is None:
                cur.execute(
                    """
                    INSERT INTO rpg_character_prepared_spells (
                        character_id,
                        catalog_key,
                        spell_name,
                        spell_level,
                        slot_kind,
                        domain_source,
                        prepared_count,
                        used_count,
                        school,
                        range_text,
                        summary,
                        source_text,
                        notes,
                        sort_order
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id;
                    """,
                    (
                        character_id,
                        normalized["catalog_key"],
                        normalized["spell_name"],
                        normalized["spell_level"],
                        normalized["slot_kind"],
                        normalized["domain_source"],
                        normalized["prepared_count"],
                        normalized["used_count"],
                        normalized["school"],
                        normalized["range_text"],
                        normalized["summary"],
                        normalized["source_text"],
                        normalized["notes"],
                        normalized["sort_order"],
                    ),
                )
                saved_id = int(cur.fetchone()["id"])
            else:
                cur.execute(
                    """
                    UPDATE rpg_character_prepared_spells
                    SET catalog_key=%s,
                        spell_name=%s,
                        spell_level=%s,
                        slot_kind=%s,
                        domain_source=%s,
                        prepared_count=%s,
                        used_count=%s,
                        school=%s,
                        range_text=%s,
                        summary=%s,
                        source_text=%s,
                        notes=%s,
                        sort_order=%s,
                        updated_at=NOW()
                    WHERE id=%s AND character_id=%s;
                    """,
                    (
                        normalized["catalog_key"],
                        normalized["spell_name"],
                        normalized["spell_level"],
                        normalized["slot_kind"],
                        normalized["domain_source"],
                        normalized["prepared_count"],
                        normalized["used_count"],
                        normalized["school"],
                        normalized["range_text"],
                        normalized["summary"],
                        normalized["source_text"],
                        normalized["notes"],
                        normalized["sort_order"],
                        preparation_id,
                        character_id,
                    ),
                )
                if cur.rowcount == 0:
                    raise ValueError("Ce sort préparé n’existe plus.")
                saved_id = int(preparation_id)
            conn.commit()
            return saved_id


def delete_prepared_spell(user_id, character_id, preparation_id):
    _ensure()
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                DELETE FROM rpg_character_prepared_spells
                WHERE id=%s AND character_id=%s;
                """,
                (preparation_id, character_id),
            )
            if cur.rowcount == 0:
                raise ValueError("Ce sort préparé n’existe plus.")
            conn.commit()


def set_prepared_spell_used_count(
    user_id,
    character_id,
    preparation_id,
    used_count,
):
    _ensure()
    used = _int(
        used_count,
        label="Le nombre utilisé",
        minimum=0,
        maximum=100,
        default=0,
    )
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                SELECT id, spell_level, prepared_count
                FROM rpg_character_prepared_spells
                WHERE id=%s AND character_id=%s
                FOR UPDATE;
                """,
                (preparation_id, character_id),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("Ce sort préparé n’existe plus.")
            maximum = int(row["prepared_count"])
            if int(row["spell_level"]) == 0:
                used = 0
            if used > maximum:
                raise ValueError("Tous les exemplaires préparés sont déjà utilisés.")
            cur.execute(
                """
                UPDATE rpg_character_prepared_spells
                SET used_count=%s, updated_at=NOW()
                WHERE id=%s AND character_id=%s;
                """,
                (used, preparation_id, character_id),
            )
            conn.commit()
            return used


def reset_spell_usage(user_id, character_id):
    _ensure()
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                UPDATE rpg_character_prepared_spells
                SET used_count=0, updated_at=NOW()
                WHERE character_id=%s AND used_count<>0;
                """,
                (character_id,),
            )
            conn.commit()
