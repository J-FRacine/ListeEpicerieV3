"""Catalogue des objets magiques JDR — Phase 14."""
from __future__ import annotations

from copy import deepcopy

MAGIC_KIND_LABELS = {
    "passive": "Passif",
    "charges": "À charges",
    "activatable": "Activable",
    "container": "Conteneur magique",
    "other": "Autre",
}

MAGIC_ITEM_TEMPLATES = {
    "cloak_resistance": {
        "label": "Cloak of Resistance",
        "values": {
            "item_name": "Cloak of Resistance +1",
            "item_type": "gear",
            "quantity": 1,
            "weight_each": 1,
            "value_text": "1 000 po",
            "carried": True,
            "equipped": True,
            "magic_enabled": True,
            "magic_kind": "passive",
            "magic_requires_equipped": True,
            "magic_resistance_bonus": 1,
            "magic_charges_current": None,
            "magic_charges_max": None,
            "magic_contained_spell_name": "",
            "magic_caster_level": None,
            "magic_capacity_weight": None,
            "magic_activation_text": (
                "Bonus de résistance sur Vigueur, Réflexes et Volonté."
            ),
        },
    },
    "wand_cure_light_wounds": {
        "label": "Wand of Cure Light Wounds",
        "values": {
            "item_name": "Wand of Cure Light Wounds",
            "item_type": "gear",
            "quantity": 1,
            "weight_each": 0,
            "value_text": "750 po",
            "carried": True,
            "equipped": False,
            "magic_enabled": True,
            "magic_kind": "charges",
            "magic_requires_equipped": False,
            "magic_resistance_bonus": 0,
            "magic_charges_current": 50,
            "magic_charges_max": 50,
            "magic_contained_spell_name": "Cure Light Wounds",
            "magic_caster_level": 1,
            "magic_capacity_weight": None,
            "magic_activation_text": (
                "1 charge par utilisation. Soins : 1d8+1 PV au NLS 1."
            ),
        },
    },
    "handy_haversack": {
        "label": "Handy Haversack",
        "values": {
            "item_name": "Handy Haversack",
            "item_type": "gear",
            "quantity": 1,
            "weight_each": 5,
            "value_text": "2 000 po",
            "carried": True,
            "equipped": False,
            "magic_enabled": True,
            "magic_kind": "container",
            "magic_requires_equipped": False,
            "magic_resistance_bonus": 0,
            "magic_charges_current": None,
            "magic_charges_max": None,
            "magic_contained_spell_name": "",
            "magic_caster_level": 9,
            "magic_capacity_weight": 120,
            "magic_activation_text": (
                "Capacité totale 120 lb. Le sac pèse toujours 5 lb. "
"Retirer un objet précis est une action de mouvement sans attaque d’opportunité."
            ),
        },
    },
}


def magic_template_values(template_key):
    template = MAGIC_ITEM_TEMPLATES.get(str(template_key or "").strip())
    if not template:
        return {}
    values = deepcopy(template["values"])
    values["magic_template_key"] = str(template_key)
    return values


def cure_light_wounds_effect(caster_level=1):
    try:
        level = max(1, int(caster_level or 1))
    except (TypeError, ValueError):
        level = 1
    bonus = min(level, 5)
    return f"1d8+{bonus} PV"
