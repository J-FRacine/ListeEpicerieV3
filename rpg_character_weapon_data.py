"""Données des armes détaillées et liens Équipement <-> Attaques."""
from __future__ import annotations

from db import get_connection
from rpg_character_weapon_schema import ensure_weapon_schema

HANDEDNESS = {"light", "one_handed", "two_handed", "ranged", "other"}
GRIP_MODES = {"default", "one_handed", "two_handed"}

def _ensure():
    ensure_weapon_schema(get_connection=get_connection)

def _text(value, *, label, maximum):
    text = str(value or "").strip()
    if len(text) > maximum:
        raise ValueError(
            f"{label} ne peut pas dépasser {maximum} caractères."
        )
    return text or None

def _optional_int(
    value, *, label, minimum=0, maximum=100000
):
    if value in (None, ""):
        return None
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{label} doit être un nombre entier."
        ) from error
    if result < minimum or result > maximum:
        raise ValueError(
            f"{label} doit être compris entre {minimum} et {maximum}."
        )
    return result

def _require_character(cur, user_id, character_id):
    cur.execute(
        """
        SELECT id
        FROM rpg_characters
        WHERE id = %s AND user_id = %s;
        """,
        (character_id, user_id),
    )
    if cur.fetchone() is None:
        raise ValueError(
            "Ce personnage n’existe plus ou ne vous appartient pas."
        )

def _require_weapon(cur, character_id, equipment_id):
    cur.execute(
        """
        SELECT id
        FROM rpg_character_equipment
        WHERE id = %s
          AND character_id = %s
          AND item_type = 'weapon';
        """,
        (equipment_id, character_id),
    )
    if cur.fetchone() is None:
        raise ValueError(
            "Cette arme n’existe plus dans l’Équipement."
        )

def weapon_details_by_equipment(user_id, character_id):
    _ensure()
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                SELECT d.*
                FROM rpg_character_weapon_details d
                JOIN rpg_character_equipment e
                  ON e.id = d.equipment_id
                WHERE e.character_id = %s;
                """,
                (character_id,),
            )
            return {
                int(row["equipment_id"]): dict(row)
                for row in cur.fetchall()
            }

def attack_weapon_links(user_id, character_id):
    _ensure()
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                SELECT
                    l.attack_id,
                    l.equipment_id AS linked_equipment_id,
                    l.grip_mode,
                    e.item_name AS linked_equipment_name,
                    e.equipped AS linked_equipment_equipped,
                    e.carried AS linked_equipment_carried,
                    d.weapon_template_key,
                    d.weapon_damage,
                    d.weapon_critical,
                    d.weapon_damage_type,
                    d.weapon_range,
                    d.weapon_handedness,
                    d.weapon_masterwork,
                    d.weapon_enhancement_bonus,
                    d.weapon_ammunition_type,
                    d.weapon_ammunition_current,
                    d.weapon_ammunition_max,
                    d.weapon_proficiency_required
                FROM rpg_character_attack_weapon_links l
                JOIN rpg_character_attacks a
                  ON a.id = l.attack_id
                JOIN rpg_character_equipment e
                  ON e.id = l.equipment_id
                LEFT JOIN rpg_character_weapon_details d
                  ON d.equipment_id = e.id
                WHERE a.character_id = %s
                  AND e.character_id = %s;
                """,
                (character_id, character_id),
            )
            return {
                int(row["attack_id"]): dict(row)
                for row in cur.fetchall()
            }

def linked_attacks_by_equipment(user_id, character_id):
    _ensure()
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                SELECT
                    l.equipment_id,
                    a.id AS attack_id,
                    a.attack_name,
                    l.grip_mode
                FROM rpg_character_attack_weapon_links l
                JOIN rpg_character_attacks a
                  ON a.id = l.attack_id
                JOIN rpg_character_equipment e
                  ON e.id = l.equipment_id
                WHERE a.character_id = %s
                  AND e.character_id = %s
                ORDER BY a.sort_order, a.id;
                """,
                (character_id, character_id),
            )
            result = {}
            for row in cur.fetchall():
                result.setdefault(
                    int(row["equipment_id"]), []
                ).append(dict(row))
            return result

def save_weapon_details(
    user_id, character_id, equipment_id, values
):
    _ensure()
    handedness = str(
        values.get("weapon_handedness") or "one_handed"
    ).strip()
    if handedness not in HANDEDNESS:
        raise ValueError(
            "La catégorie une/deux mains de l’arme est invalide."
        )

    enhancement = _optional_int(
        values.get("weapon_enhancement_bonus"),
        label="Le bonus magique de l’arme",
        minimum=0,
        maximum=20,
    ) or 0
    masterwork = bool(values.get("weapon_masterwork"))
    if enhancement > 0:
        masterwork = True

    normalized = {
        "weapon_template_key": _text(
            values.get("weapon_template_key"),
            label="Le modèle d’arme",
            maximum=120,
        ),
        "weapon_damage": _text(
            values.get("weapon_damage"),
            label="Les dégâts de l’arme",
            maximum=120,
        ),
        "weapon_critical": _text(
            values.get("weapon_critical"),
            label="Le critique de l’arme",
            maximum=80,
        ),
        "weapon_damage_type": _text(
            values.get("weapon_damage_type"),
            label="Le type de dégâts",
            maximum=120,
        ),
        "weapon_range": _text(
            values.get("weapon_range"),
            label="La portée de l’arme",
            maximum=80,
        ),
        "weapon_ammunition_type": _text(
            values.get("weapon_ammunition_type"),
            label="Le type de munitions",
            maximum=120,
        ),
        "weapon_ammunition_current": _optional_int(
            values.get("weapon_ammunition_current"),
            label="Les munitions actuelles",
        ),
        "weapon_ammunition_max": _optional_int(
            values.get("weapon_ammunition_max"),
            label="Les munitions maximums",
        ),
        "weapon_proficiency_required": _text(
            values.get("proficiency_required")
            or values.get("weapon_proficiency_required"),
            label="La maîtrise requise",
            maximum=160,
        ),
    }

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            _require_weapon(cur, character_id, equipment_id)
            cur.execute(
                """
                INSERT INTO rpg_character_weapon_details (
                    equipment_id,
                    weapon_template_key,
                    weapon_damage,
                    weapon_critical,
                    weapon_damage_type,
                    weapon_range,
                    weapon_handedness,
                    weapon_masterwork,
                    weapon_enhancement_bonus,
                    weapon_ammunition_type,
                    weapon_ammunition_current,
                    weapon_ammunition_max,
                    weapon_proficiency_required
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (equipment_id)
                DO UPDATE SET
                    weapon_template_key = EXCLUDED.weapon_template_key,
                    weapon_damage = EXCLUDED.weapon_damage,
                    weapon_critical = EXCLUDED.weapon_critical,
                    weapon_damage_type = EXCLUDED.weapon_damage_type,
                    weapon_range = EXCLUDED.weapon_range,
                    weapon_handedness = EXCLUDED.weapon_handedness,
                    weapon_masterwork = EXCLUDED.weapon_masterwork,
                    weapon_enhancement_bonus =
                        EXCLUDED.weapon_enhancement_bonus,
                    weapon_ammunition_type =
                        EXCLUDED.weapon_ammunition_type,
                    weapon_ammunition_current =
                        EXCLUDED.weapon_ammunition_current,
                    weapon_ammunition_max =
                        EXCLUDED.weapon_ammunition_max,
                    weapon_proficiency_required =
                        EXCLUDED.weapon_proficiency_required,
                    updated_at = NOW();
                """,
                (
                    equipment_id,
                    normalized["weapon_template_key"],
                    normalized["weapon_damage"],
                    normalized["weapon_critical"],
                    normalized["weapon_damage_type"],
                    normalized["weapon_range"],
                    handedness,
                    masterwork,
                    enhancement,
                    normalized["weapon_ammunition_type"],
                    normalized["weapon_ammunition_current"],
                    normalized["weapon_ammunition_max"],
                    normalized["weapon_proficiency_required"],
                ),
            )
            conn.commit()

def clear_weapon_details(
    user_id, character_id, equipment_id
):
    _ensure()
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                DELETE FROM rpg_character_attack_weapon_links
                WHERE equipment_id = %s;
                """,
                (equipment_id,),
            )
            cur.execute(
                """
                DELETE FROM rpg_character_weapon_details
                WHERE equipment_id = %s;
                """,
                (equipment_id,),
            )
            conn.commit()

def set_attack_weapon_link(
    user_id,
    character_id,
    attack_id,
    equipment_id,
    *,
    grip_mode="default",
):
    _ensure()
    grip = str(grip_mode or "default").strip()
    if grip not in GRIP_MODES:
        raise ValueError(
            "La prise de l’arme pour cette attaque est invalide."
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                SELECT id
                FROM rpg_character_attacks
                WHERE id = %s AND character_id = %s;
                """,
                (attack_id, character_id),
            )
            if cur.fetchone() is None:
                raise ValueError(
                    "Cette attaque n’existe plus."
                )

            if equipment_id in (None, ""):
                cur.execute(
                    """
                    DELETE FROM rpg_character_attack_weapon_links
                    WHERE attack_id = %s;
                    """,
                    (attack_id,),
                )
                conn.commit()
                return

            try:
                equipment_id = int(equipment_id)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "L’arme liée est invalide."
                ) from error

            _require_weapon(cur, character_id, equipment_id)
            cur.execute(
                """
                INSERT INTO rpg_character_attack_weapon_links (
                    attack_id,
                    equipment_id,
                    grip_mode
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (attack_id)
                DO UPDATE SET
                    equipment_id = EXCLUDED.equipment_id,
                    grip_mode = EXCLUDED.grip_mode,
                    updated_at = NOW();
                """,
                (attack_id, equipment_id, grip),
            )
            conn.commit()
