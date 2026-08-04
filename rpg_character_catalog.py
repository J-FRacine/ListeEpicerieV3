from __future__ import annotations

import unicodedata
from copy import deepcopy


RACE_PROFILES = {
    "human": {
        "label": "Humain",
        "creature_type": "Humanoïde",
        "subtypes": "humain",
        "size_key": "medium",
        "base_speed": 30,
        "vision": "Vision normale",
        "languages": "Commun",
        "ability_adjustments": "+2 à une caractéristique au choix",
        "carrying_capacity_multiplier": 1,
        "is_quadruped": False,
        "ignore_armor_speed": False,
        "ignore_encumbrance_speed": False,
        "standard_traits": "Don supplémentaire; Talentueux",
    },
    "dwarf": {
        "label": "Nain",
        "creature_type": "Humanoïde",
        "subtypes": "nain",
        "size_key": "medium",
        "base_speed": 20,
        "vision": "Vision dans le noir 60 pi",
        "languages": "Commun, nain",
        "ability_adjustments": "+2 CON, +2 SAG, −2 CHA",
        "carrying_capacity_multiplier": 1,
        "is_quadruped": False,
        "ignore_armor_speed": True,
        "ignore_encumbrance_speed": True,
        "standard_traits": "Lent et stable; Robustesse; Connaissance de la pierre",
    },
    "elf": {
        "label": "Elfe",
        "creature_type": "Humanoïde",
        "subtypes": "elfe",
        "size_key": "medium",
        "base_speed": 30,
        "vision": "Vision nocturne",
        "languages": "Commun, elfique",
        "ability_adjustments": "+2 DEX, +2 INT, −2 CON",
        "carrying_capacity_multiplier": 1,
        "is_quadruped": False,
        "ignore_armor_speed": False,
        "ignore_encumbrance_speed": False,
        "standard_traits": "Immunités elfiques; Magie elfique; Sens aiguisés",
    },
    "gnome": {
        "label": "Gnome",
        "creature_type": "Humanoïde",
        "subtypes": "gnome",
        "size_key": "small",
        "base_speed": 20,
        "vision": "Vision nocturne",
        "languages": "Commun, gnome, sylvestre",
        "ability_adjustments": "+2 CON, +2 CHA, −2 FOR",
        "carrying_capacity_multiplier": 1,
        "is_quadruped": False,
        "ignore_armor_speed": False,
        "ignore_encumbrance_speed": False,
        "standard_traits": "Entraînement défensif; Magie gnome; Sens aiguisés",
    },
    "half_elf": {
        "label": "Demi-elfe",
        "creature_type": "Humanoïde",
        "subtypes": "elfe, humain",
        "size_key": "medium",
        "base_speed": 30,
        "vision": "Vision nocturne",
        "languages": "Commun, elfique",
        "ability_adjustments": "+2 à une caractéristique au choix",
        "carrying_capacity_multiplier": 1,
        "is_quadruped": False,
        "ignore_armor_speed": False,
        "ignore_encumbrance_speed": False,
        "standard_traits": "Adaptabilité; Sang elfe; Immunités elfiques; Multitalent",
    },
    "half_orc": {
        "label": "Demi-orque",
        "creature_type": "Humanoïde",
        "subtypes": "humain, orque",
        "size_key": "medium",
        "base_speed": 30,
        "vision": "Vision dans le noir 60 pi",
        "languages": "Commun, orque",
        "ability_adjustments": "+2 à une caractéristique au choix",
        "carrying_capacity_multiplier": 1,
        "is_quadruped": False,
        "ignore_armor_speed": False,
        "ignore_encumbrance_speed": False,
        "standard_traits": "Intimidant; Sang orque; Férocité orque",
    },
    "halfling": {
        "label": "Halfelin",
        "creature_type": "Humanoïde",
        "subtypes": "halfelin",
        "size_key": "small",
        "base_speed": 20,
        "vision": "Vision normale",
        "languages": "Commun, halfelin",
        "ability_adjustments": "+2 DEX, +2 CHA, −2 FOR",
        "carrying_capacity_multiplier": 1,
        "is_quadruped": False,
        "ignore_armor_speed": False,
        "ignore_encumbrance_speed": False,
        "standard_traits": "Intrépide; Chance des halfelins; Pied sûr",
    },
    "custom": {
        "label": "Autre / personnalisée",
        "creature_type": "Humanoïde",
        "subtypes": "",
        "size_key": "medium",
        "base_speed": 30,
        "vision": "Vision normale",
        "languages": "Commun",
        "ability_adjustments": "Personnalisé",
        "carrying_capacity_multiplier": 1,
        "is_quadruped": False,
        "ignore_armor_speed": False,
        "ignore_encumbrance_speed": False,
        "standard_traits": "",
    },
}

RACE_LABELS = {
    key: profile["label"]
    for key, profile in RACE_PROFILES.items()
}

EQUIPMENT_TYPE_LABELS = {
    "armor": "Armure",
    "shield": "Bouclier",
    "weapon": "Arme",
    "gear": "Objet / possession",
}

ARMOR_CATEGORY_LABELS = {
    "none": "Sans catégorie",
    "light": "Légère",
    "medium": "Intermédiaire",
    "heavy": "Lourde",
}


def _normalized_text(value):
    text = str(value or "").strip().casefold()
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(character)
    )


def infer_race_key(value):
    normalized = _normalized_text(value).replace("_", " ").replace("-", " ")
    aliases = {
        "humain": "human",
        "human": "human",
        "nain": "dwarf",
        "dwarf": "dwarf",
        "elfe": "elf",
        "elf": "elf",
        "gnome": "gnome",
        "demi elfe": "half_elf",
        "half elf": "half_elf",
        "demi orque": "half_orc",
        "demi orc": "half_orc",
        "half orc": "half_orc",
        "halfelin": "halfling",
        "halfling": "halfling",
    }
    return aliases.get(normalized, "custom")


def get_race_profile(race_key):
    key = str(race_key or "custom").strip()
    return deepcopy(RACE_PROFILES.get(key, RACE_PROFILES["custom"]))
