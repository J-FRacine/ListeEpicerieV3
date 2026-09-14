"""Catalogue léger d'armes pour la fiche JDR."""
from __future__ import annotations

WEAPON_HANDEDNESS_LABELS = {
    "light": "Légère",
    "one_handed": "Une main",
    "two_handed": "Deux mains",
    "ranged": "À distance",
    "other": "Autre",
}

ATTACK_GRIP_LABELS = {
    "default": "Selon l’arme / normal",
    "one_handed": "Utilisée à une main",
    "two_handed": "Utilisée à deux mains",
}

WEAPON_TEMPLATES = {
    "": {"label": "Saisie libre"},
    "iomedae_longsword": {
        "label": "Épée longue — Longsword (Iomedae)",
        "item_name": "Épée longue",
        "item_type": "weapon",
        "quantity": 1,
        "weight_each": 4,
        "value_text": "15 po",
        "proficiency_required": "Armes de guerre",
        "weapon_damage_by_size": {
            "small": "1d6",
            "medium": "1d8",
        },
        "weapon_critical": "19-20/x2",
        "weapon_damage_type": "Tranchant",
        "weapon_range": "",
        "weapon_handedness": "one_handed",
        "weapon_masterwork": False,
        "weapon_enhancement_bonus": 0,
        "weapon_ammunition_type": "",
        "weapon_ammunition_current": None,
        "weapon_ammunition_max": None,
    },
}

def weapon_template_values(template_key, size_key="medium"):
    template = dict(WEAPON_TEMPLATES.get(template_key) or {})
    if not template_key or not template:
        return {}
    damage_by_size = dict(
        template.pop("weapon_damage_by_size", {}) or {}
    )
    template["weapon_damage"] = damage_by_size.get(
        str(size_key or "medium").strip().lower(),
        "",
    )
    template["weapon_template_key"] = template_key
    return template
