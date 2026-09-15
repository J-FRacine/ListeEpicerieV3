"""Données des objets magiques JDR — Phase 14."""
from __future__ import annotations

from decimal import Decimal

from db import get_connection
from rpg_character_equipment_schema import ensure_equipment_schema
from rpg_character_magic_schema import ensure_magic_item_schema

MAGIC_KINDS = {"passive", "charges", "activatable", "container", "other"}


def _ensure():
    ensure_equipment_schema(get_connection=get_connection)
    ensure_magic_item_schema(get_connection=get_connection)


def _int(value, *, label, minimum=0, maximum=100000, optional=False):
    if value in (None, ""):
        if optional:
            return None
        return minimum
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} doit être un nombre entier.") from error
    if result < minimum or result > maximum:
        raise ValueError(
            f"{label} doit être compris entre {minimum} et {maximum}."
        )
    return result


def _decimal(value, *, label, minimum=0, maximum=100000, optional=False):
    if value in (None, ""):
        if optional:
            return None
        return Decimal(str(minimum))
    try:
        result = Decimal(str(value))
    except Exception as error:
        raise ValueError(f"{label} doit être un nombre.") from error
    if result < Decimal(str(minimum)) or result > Decimal(str(maximum)):
        raise ValueError(
            f"{label} doit être compris entre {minimum} et {maximum}."
        )
    return result


def _text(value, *, label, maximum):
    text = str(value or "").strip()
    if len(text) > maximum:
        raise ValueError(
            f"{label} ne peut pas dépasser {maximum} caractères."
        )
    return text or None


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


def _require_equipment(cur, character_id, equipment_id):
    cur.execute(
        """
        SELECT id, item_name, item_type, quantity, weight_each
        FROM rpg_character_equipment
        WHERE id = %s AND character_id = %s;
        """,
        (equipment_id, character_id),
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError("Cet équipement n’existe plus.")
    return dict(row)


def magic_details_by_equipment(user_id, character_id):
    _ensure()
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                SELECT d.*
                FROM rpg_character_magic_item_details d
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


def containment_by_equipment(user_id, character_id):
    _ensure()
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            cur.execute(
                """
                SELECT
                    c.equipment_id,
                    c.container_equipment_id,
                    container.item_name AS container_equipment_name
                FROM rpg_character_equipment_containment c
                JOIN rpg_character_equipment child
                  ON child.id = c.equipment_id
                JOIN rpg_character_equipment container
                  ON container.id = c.container_equipment_id
                WHERE child.character_id = %s
                  AND container.character_id = %s;
                """,
                (character_id, character_id),
            )
            return {
                int(row["equipment_id"]): dict(row)
                for row in cur.fetchall()
            }


def save_magic_details(user_id, character_id, equipment_id, values):
    _ensure()

    kind = str(values.get("magic_kind") or "other").strip()
    if kind not in MAGIC_KINDS:
        raise ValueError("Le type d’objet magique est invalide.")

    resistance = _int(
        values.get("magic_resistance_bonus"),
        label="Le bonus de résistance",
        minimum=0,
        maximum=20,
    )
    current = _int(
        values.get("magic_charges_current"),
        label="Les charges actuelles",
        minimum=0,
        maximum=100000,
        optional=True,
    )
    maximum = _int(
        values.get("magic_charges_max"),
        label="Les charges maximums",
        minimum=0,
        maximum=100000,
        optional=True,
    )
    if current is not None and maximum is not None and current > maximum:
        raise ValueError(
            "Les charges actuelles ne peuvent pas dépasser le maximum."
        )

    caster_level = _int(
        values.get("magic_caster_level"),
        label="Le niveau de lanceur de sorts",
        minimum=0,
        maximum=100,
        optional=True,
    )
    capacity = _decimal(
        values.get("magic_capacity_weight"),
        label="La capacité du conteneur",
        minimum=0,
        maximum=100000,
        optional=True,
    )

    normalized = {
        "magic_template_key": _text(
            values.get("magic_template_key"),
            label="Le modèle d’objet magique",
            maximum=120,
        ),
        "contained_spell_name": _text(
            values.get("magic_contained_spell_name"),
            label="Le sort contenu",
            maximum=200,
        ),
        "activation_text": _text(
            values.get("magic_activation_text"),
            label="Le texte d’activation",
            maximum=2000,
        ),
    }

    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            _require_equipment(cur, character_id, equipment_id)
            cur.execute(
                """
                INSERT INTO rpg_character_magic_item_details (
                    equipment_id,
                    magic_template_key,
                    magic_kind,
                    requires_equipped,
                    resistance_bonus,
                    charges_current,
                    charges_max,
                    contained_spell_name,
                    caster_level,
                    activation_text,
                    capacity_weight
                )
                VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                ON CONFLICT (equipment_id)
                DO UPDATE SET
                    magic_template_key = EXCLUDED.magic_template_key,
                    magic_kind = EXCLUDED.magic_kind,
                    requires_equipped = EXCLUDED.requires_equipped,
                    resistance_bonus = EXCLUDED.resistance_bonus,
                    charges_current = EXCLUDED.charges_current,
                    charges_max = EXCLUDED.charges_max,
                    contained_spell_name = EXCLUDED.contained_spell_name,
                    caster_level = EXCLUDED.caster_level,
                    activation_text = EXCLUDED.activation_text,
                    capacity_weight = EXCLUDED.capacity_weight,
                    updated_at = NOW();
                """,
                (
                    equipment_id,
                    normalized["magic_template_key"],
                    kind,
                    bool(values.get("magic_requires_equipped")),
                    resistance,
                    current,
                    maximum,
                    normalized["contained_spell_name"],
                    caster_level,
                    normalized["activation_text"],
                    capacity,
                ),
            )
            conn.commit()


def clear_magic_details(user_id, character_id, equipment_id):
    _ensure()
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            _require_equipment(cur, character_id, equipment_id)
            cur.execute(
                """
                DELETE FROM rpg_character_equipment_containment
                WHERE equipment_id = %s
                   OR container_equipment_id = %s;
                """,
                (equipment_id, equipment_id),
            )
            cur.execute(
                """
                DELETE FROM rpg_character_magic_item_details
                WHERE equipment_id = %s;
                """,
                (equipment_id,),
            )
            conn.commit()


def set_equipment_container(
    user_id,
    character_id,
    equipment_id,
    container_equipment_id,
):
    _ensure()
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            child = _require_equipment(cur, character_id, equipment_id)

            if container_equipment_id in (None, ""):
                cur.execute(
                    """
                    DELETE FROM rpg_character_equipment_containment
                    WHERE equipment_id = %s;
                    """,
                    (equipment_id,),
                )
                conn.commit()
                return

            try:
                container_id = int(container_equipment_id)
            except (TypeError, ValueError) as error:
                raise ValueError("Le conteneur choisi est invalide.") from error

            if int(equipment_id) == container_id:
                raise ValueError(
                    "Un objet ne peut pas être rangé dans lui-même."
                )

            container = _require_equipment(
                cur, character_id, container_id
            )
            cur.execute(
                """
                SELECT magic_kind, capacity_weight
                FROM rpg_character_magic_item_details
                WHERE equipment_id = %s;
                """,
                (container_id,),
            )
            detail = cur.fetchone()
            if not detail or detail["magic_kind"] != "container":
                raise ValueError(
                    "Le conteneur choisi n’est plus un conteneur magique."
                )

            cur.execute(
                """
                SELECT magic_kind
                FROM rpg_character_magic_item_details
                WHERE equipment_id = %s;
                """,
                (equipment_id,),
            )
            child_magic = cur.fetchone()
            if child_magic and child_magic["magic_kind"] == "container":
                raise ValueError(
                    "Un conteneur magique ne peut pas être rangé "
                    "dans un autre conteneur magique."
                )

            capacity = Decimal(str(detail["capacity_weight"] or 0))
            if capacity <= 0:
                raise ValueError(
                    "Ce conteneur magique n’a aucune capacité configurée."
                )

            cur.execute(
                """
                SELECT COALESCE(
                    SUM(e.weight_each * GREATEST(e.quantity, 0)),
                    0
                ) AS total_weight
                FROM rpg_character_equipment_containment c
                JOIN rpg_character_equipment e
                  ON e.id = c.equipment_id
                WHERE c.container_equipment_id = %s
                  AND c.equipment_id <> %s;
                """,
                (container_id, equipment_id),
            )
            existing = Decimal(
                str(cur.fetchone()["total_weight"] or 0)
            )
            child_weight = (
                Decimal(str(child["weight_each"] or 0))
                * max(0, int(child["quantity"] or 0))
            )
            if existing + child_weight > capacity:
                raise ValueError(
                    "La capacité du conteneur magique serait dépassée "
                    f"({existing + child_weight} lb sur {capacity} lb)."
                )

            cur.execute(
                """
                INSERT INTO rpg_character_equipment_containment (
                    equipment_id,
                    container_equipment_id
                )
                VALUES (%s, %s)
                ON CONFLICT (equipment_id)
                DO UPDATE SET
                    container_equipment_id =
                        EXCLUDED.container_equipment_id,
                    updated_at = NOW();
                """,
                (equipment_id, container_id),
            )
            conn.commit()


def use_magic_item_charge(
    user_id,
    character_id,
    equipment_id,
):
    _ensure()
    with get_connection() as conn:
        with conn.cursor() as cur:
            _require_character(cur, user_id, character_id)
            _require_equipment(cur, character_id, equipment_id)
            cur.execute(
                """
                SELECT
                    d.magic_kind,
                    d.charges_current,
                    d.charges_max
                FROM rpg_character_magic_item_details d
                WHERE d.equipment_id = %s
                FOR UPDATE;
                """,
                (equipment_id,),
            )
            detail = cur.fetchone()
            if detail is None or detail["magic_kind"] != "charges":
                raise ValueError(
                    "Cet objet n’est pas configuré comme objet à charges."
                )
            current = int(detail["charges_current"] or 0)
            if current <= 0:
                raise ValueError("Cet objet n’a plus de charge.")

            new_value = current - 1
            cur.execute(
                """
                UPDATE rpg_character_magic_item_details
                SET charges_current = %s,
                    updated_at = NOW()
                WHERE equipment_id = %s;
                """,
                (new_value, equipment_id),
            )
            conn.commit()
            return new_value
