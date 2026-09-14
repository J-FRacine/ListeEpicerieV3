"""Règles pures des armes détaillées et attaques liées."""
from __future__ import annotations

def _as_int(value, default=0):
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def weapon_attack_bonus(weapon) -> int:
    enhancement = max(
        0, _as_int(weapon.get("weapon_enhancement_bonus"))
    )
    masterwork = bool(weapon.get("weapon_masterwork"))
    return max(enhancement, 1 if masterwork else 0)

def merge_equipment_with_weapon_details(
    equipment_rows, detail_map, linked_attack_map
):
    result = []
    for raw in equipment_rows or ():
        row = dict(raw)
        equipment_id = int(row["id"])
        detail = dict(detail_map.get(equipment_id) or {})
        defaults = {
            "weapon_template_key": None,
            "weapon_damage": None,
            "weapon_critical": None,
            "weapon_damage_type": None,
            "weapon_range": None,
            "weapon_handedness": "one_handed",
            "weapon_masterwork": False,
            "weapon_enhancement_bonus": 0,
            "weapon_ammunition_type": None,
            "weapon_ammunition_current": None,
            "weapon_ammunition_max": None,
            "weapon_proficiency_required": None,
        }
        defaults.update(detail)
        row.update(defaults)
        if row.get("item_type") == "weapon":
            row["proficiency_required"] = (
                row.get("weapon_proficiency_required")
                or row.get("proficiency_required")
            )
        row["linked_attacks"] = list(
            linked_attack_map.get(equipment_id) or ()
        )
        row["weapon_attack_bonus"] = (
            weapon_attack_bonus(row)
            if row.get("item_type") == "weapon"
            else 0
        )
        result.append(row)
    return result

def merge_attacks_with_weapons(attack_rows, link_map):
    result = []
    for raw in attack_rows or ():
        row = dict(raw)
        attack_id = int(row["id"])
        link = dict(link_map.get(attack_id) or {})
        row["manual_magic_bonus"] = _as_int(row.get("magic_bonus"))
        row["stored_damage"] = row.get("damage")
        row["stored_critical"] = row.get("critical")
        row["stored_attack_range"] = row.get("attack_range")
        row["stored_attack_type"] = row.get("attack_type")
        row["stored_ammunition_current"] = row.get("ammunition_current")
        row["stored_ammunition_max"] = row.get("ammunition_max")
        if not link:
            row.update({
                "linked_equipment_id": None,
                "linked_equipment_name": None,
                "grip_mode": "default",
                "weapon_attack_bonus": 0,
                "weapon_damage_bonus": 0,
                "weapon_masterwork": False,
                "weapon_enhancement_bonus": 0,
            })
            result.append(row)
            continue
        row.update(link)
        attack_bonus = weapon_attack_bonus(link)
        row["weapon_attack_bonus"] = attack_bonus
        row["weapon_damage_bonus"] = max(
            0, _as_int(link.get("weapon_enhancement_bonus"))
        )
        row["magic_bonus"] = attack_bonus

        if not str(row.get("damage") or "").strip():
            row["damage"] = link.get("weapon_damage")
            row["damage_inherited"] = True
        else:
            row["damage_inherited"] = False
        if not str(row.get("critical") or "").strip():
            row["critical"] = link.get("weapon_critical")
            row["critical_inherited"] = True
        else:
            row["critical_inherited"] = False
        if not str(row.get("attack_range") or "").strip():
            row["attack_range"] = link.get("weapon_range")
            row["range_inherited"] = True
        else:
            row["range_inherited"] = False
        if not str(row.get("attack_type") or "").strip():
            row["attack_type"] = link.get("weapon_damage_type")
            row["type_inherited"] = True
        else:
            row["type_inherited"] = False

        if link.get("weapon_ammunition_current") is not None:
            row["ammunition_current"] = link.get("weapon_ammunition_current")
        if link.get("weapon_ammunition_max") is not None:
            row["ammunition_max"] = link.get("weapon_ammunition_max")
        result.append(row)
    return result

def attack_defaults_from_weapon(weapon):
    handedness = str(weapon.get("weapon_handedness") or "")
    grip_mode = "two_handed" if handedness == "two_handed" else "default"
    return {
        "attack_name": weapon.get("item_name") or "Attaque",
        "ability_key": "str",
        "magic_bonus": 0,
        "misc_bonus": 0,
        "damage": weapon.get("weapon_damage"),
        "critical": weapon.get("weapon_critical"),
        "attack_range": weapon.get("weapon_range"),
        "attack_type": weapon.get("weapon_damage_type"),
        "notes": None,
        "ammunition_current": None,
        "ammunition_max": None,
        "linked_equipment_id": weapon.get("id"),
        "grip_mode": grip_mode,
    }
