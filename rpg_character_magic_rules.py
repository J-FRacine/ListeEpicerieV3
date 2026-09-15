"""Règles pures des objets magiques JDR — Phase 14."""
from __future__ import annotations

from decimal import Decimal

NORMAL_SAVE_KEYS = {"fortitude", "reflex", "will"}


def _decimal(value, default="0"):
    try:
        return Decimal(str(value if value not in (None, "") else default))
    except Exception:
        return Decimal(default)


def _integer(value, default=0):
    try:
        return int(value if value not in (None, "") else default)
    except (TypeError, ValueError):
        return default


def item_total_weight(row):
    return (
        _decimal(row.get("weight_each"))
        * max(0, _integer(row.get("quantity"), 1))
    )


def merge_equipment_with_magic_details(
    equipment_rows,
    details_by_equipment=None,
    containment_by_equipment=None,
):
    details = details_by_equipment or {}
    containment = containment_by_equipment or {}
    merged = []

    defaults = {
        "magic_template_key": None,
        "magic_kind": None,
        "magic_requires_equipped": False,
        "magic_resistance_bonus": 0,
        "magic_charges_current": None,
        "magic_charges_max": None,
        "magic_contained_spell_name": None,
        "magic_caster_level": None,
        "magic_activation_text": None,
        "magic_capacity_weight": None,
        "is_magic_item": False,
        "container_equipment_id": None,
        "container_equipment_name": None,
    }

    for source in equipment_rows or ():
        row = dict(source)
        row.update(defaults)
        equipment_id = int(row["id"])

        detail = details.get(equipment_id)
        if detail:
            detail = dict(detail)
            row.update({
                "magic_template_key": detail.get("magic_template_key"),
                "magic_kind": detail.get("magic_kind") or "other",
                "magic_requires_equipped": bool(
                    detail.get("requires_equipped")
                ),
                "magic_resistance_bonus": _integer(
                    detail.get("resistance_bonus")
                ),
                "magic_charges_current": detail.get("charges_current"),
                "magic_charges_max": detail.get("charges_max"),
                "magic_contained_spell_name": detail.get(
                    "contained_spell_name"
                ),
                "magic_caster_level": detail.get("caster_level"),
                "magic_activation_text": detail.get("activation_text"),
                "magic_capacity_weight": detail.get("capacity_weight"),
                "is_magic_item": True,
            })

        link = containment.get(equipment_id)
        if link:
            row["container_equipment_id"] = link.get(
                "container_equipment_id"
            )
            row["container_equipment_name"] = link.get(
                "container_equipment_name"
            )

        merged.append(row)

    loads = container_loads(merged)
    for row in merged:
        if row.get("magic_kind") == "container":
            row["magic_container_load"] = loads.get(
                int(row["id"]), Decimal("0")
            )
        else:
            row["magic_container_load"] = None

    return merged


def _magic_item_active(row):
    if not row.get("is_magic_item"):
        return False
    if not bool(row.get("carried", True)):
        return False
    if row.get("magic_requires_equipped") and not bool(row.get("equipped")):
        return False
    return True


def magic_resistance_bonus(equipment_rows):
    bonuses = [
        max(0, _integer(row.get("magic_resistance_bonus")))
        for row in equipment_rows or ()
        if _magic_item_active(row)
    ]
    return max(bonuses, default=0)


def add_magic_save_bonuses(save_rows, equipment_rows):
    bonus = magic_resistance_bonus(equipment_rows)
    result = []
    for source in save_rows or ():
        row = dict(source)
        row["magic_item_bonus"] = (
            bonus if row.get("save_key") in NORMAL_SAVE_KEYS else 0
        )
        result.append(row)
    return result


def container_loads(equipment_rows):
    rows = [dict(row) for row in (equipment_rows or ())]
    result = {}
    for row in rows:
        container_id = row.get("container_equipment_id")
        if container_id in (None, ""):
            continue
        try:
            key = int(container_id)
        except (TypeError, ValueError):
            continue
        result[key] = result.get(key, Decimal("0")) + item_total_weight(row)
    return result


def prepare_equipment_for_encumbrance(equipment_rows):
    rows = [dict(row) for row in (equipment_rows or ())]
    by_id = {
        int(row["id"]): row
        for row in rows
        if row.get("id") not in (None, "")
    }

    for row in rows:
        container_id = row.get("container_equipment_id")
        if container_id in (None, ""):
            continue
        try:
            container = by_id.get(int(container_id))
        except (TypeError, ValueError):
            container = None
        if not container or container.get("magic_kind") != "container":
            continue

        row["_actual_weight_each"] = row.get("weight_each")
        row["weight_each"] = 0

    return rows


def container_capacity_state(equipment_rows, container_id):
    try:
        wanted = int(container_id)
    except (TypeError, ValueError):
        return {
            "capacity": Decimal("0"),
            "load": Decimal("0"),
            "remaining": Decimal("0"),
            "over_capacity": False,
        }

    rows = [dict(row) for row in (equipment_rows or ())]
    container = next(
        (row for row in rows if int(row.get("id") or -1) == wanted),
        None,
    )
    if not container:
        return {
            "capacity": Decimal("0"),
            "load": Decimal("0"),
            "remaining": Decimal("0"),
            "over_capacity": False,
        }

    capacity = _decimal(container.get("magic_capacity_weight"))
    load = container_loads(rows).get(wanted, Decimal("0"))
    return {
        "capacity": capacity,
        "load": load,
        "remaining": max(Decimal("0"), capacity - load),
        "over_capacity": bool(capacity and load > capacity),
    }


def validate_container_preview(
    equipment_rows,
    proposed_values,
    *,
    equipment_id=None,
    container_equipment_id=None,
):
    if container_equipment_id in (None, ""):
        return

    try:
        container_id = int(container_equipment_id)
    except (TypeError, ValueError) as error:
        raise ValueError("Le conteneur choisi est invalide.") from error

    if equipment_id not in (None, ""):
        try:
            current_id = int(equipment_id)
        except (TypeError, ValueError):
            current_id = None
        if current_id == container_id:
            raise ValueError(
                "Un objet ne peut pas être rangé dans lui-même."
            )

    rows = [dict(row) for row in (equipment_rows or ())]
    container = next(
        (
            row for row in rows
            if int(row.get("id") or -1) == container_id
        ),
        None,
    )
    if not container or container.get("magic_kind") != "container":
        raise ValueError(
            "Le conteneur choisi n’est plus un conteneur magique."
        )

    proposed_kind = str(
        proposed_values.get("magic_kind") or ""
    ).strip()
    if bool(proposed_values.get("magic_enabled")) and proposed_kind == "container":
        raise ValueError(
            "Un conteneur magique ne peut pas être rangé "
            "dans un autre conteneur magique."
        )

    capacity = _decimal(container.get("magic_capacity_weight"))
    if capacity <= 0:
        raise ValueError(
            "Ce conteneur magique n’a aucune capacité configurée."
        )

    existing = Decimal("0")
    for row in rows:
        if row.get("container_equipment_id") in (None, ""):
            continue
        try:
            same_container = int(row["container_equipment_id"]) == container_id
        except (TypeError, ValueError):
            same_container = False
        if not same_container:
            continue
        if equipment_id not in (None, ""):
            try:
                if int(row.get("id")) == int(equipment_id):
                    continue
            except (TypeError, ValueError):
                pass
        existing += item_total_weight(row)

    proposed = (
        _decimal(proposed_values.get("weight_each"))
        * max(0, _integer(proposed_values.get("quantity"), 1))
    )
    if existing + proposed > capacity:
        raise ValueError(
            "La capacité du conteneur magique serait dépassée "
            f"({existing + proposed} lb sur {capacity} lb)."
        )


def magic_effect_text(row):
    if row.get("magic_kind") == "charges":
        current = row.get("magic_charges_current")
        maximum = row.get("magic_charges_max")
        spell = str(row.get("magic_contained_spell_name") or "").strip()
        pieces = []
        if spell:
            pieces.append(spell)
        if current is not None or maximum is not None:
            pieces.append(
                f"charges {int(current or 0)} / {int(maximum or 0)}"
            )
        return " — ".join(pieces)

    if row.get("magic_resistance_bonus"):
        return (
            "résistance "
            f"+{_integer(row.get('magic_resistance_bonus'))} "
            "aux sauvegardes"
        )

    if row.get("magic_kind") == "container":
        load = _decimal(row.get("magic_container_load"))
        capacity = _decimal(row.get("magic_capacity_weight"))
        return f"contenu {load} / {capacity} lb"

    return str(row.get("magic_activation_text") or "").strip()
