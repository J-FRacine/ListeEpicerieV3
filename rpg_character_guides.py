from __future__ import annotations

"""Repères purs pour la création JDR Pathfinder 1e.

Le module ne dépend ni de NiceGUI ni de PostgreSQL. Il sert d'aide à la saisie
sans imposer silencieusement des choix au personnage.
"""

from copy import deepcopy
from math import floor
from typing import Any, Mapping
import unicodedata


FIGHTER_ALIASES = {
    "fighter",
    "guerrier",
}

FIGHTER_CLASS_SKILL_KEYS = {
    "climb",
    "craft_1",
    "craft_2",
    "craft_3",
    "handle_animal",
    "intimidate",
    "knowledge_dungeoneering",
    "knowledge_engineering",
    "profession_1",
    "profession_2",
    "ride",
    "survival",
    "swim",
}

FIGHTER_CLASS_SKILL_LABELS = (
    "Escalade",
    "Artisanat",
    "Dressage",
    "Intimidation",
    "Connaissances (exploration souterraine)",
    "Connaissances (ingénierie)",
    "Profession",
    "Équitation",
    "Survie",
    "Natation",
)

FIGHTER_PROFICIENCIES = (
    "Armes simples et de guerre; armures légères, intermédiaires et lourdes; "
    "boucliers, incluant le pavois."
)

FIGHTER_LEVELS: dict[int, dict[str, Any]] = {
    1: {
        "bab": 1,
        "fortitude": 2,
        "reflex": 0,
        "will": 0,
        "specials": ("Don de combat bonus",),
        "general_notes": ("Don général de niveau 1",),
    },
    2: {
        "bab": 2,
        "fortitude": 3,
        "reflex": 0,
        "will": 0,
        "specials": ("Don de combat bonus", "Bravoure +1"),
        "general_notes": (),
    },
    3: {
        "bab": 3,
        "fortitude": 3,
        "reflex": 1,
        "will": 1,
        "specials": ("Entraînement aux armures 1",),
        "general_notes": ("Don général de niveau 3",),
    },
    4: {
        "bab": 4,
        "fortitude": 4,
        "reflex": 1,
        "will": 1,
        "specials": ("Don de combat bonus",),
        "general_notes": ("Augmentation générale de caractéristique +1",),
    },
}

RACE_COMPARISON: dict[str, dict[str, Any]] = {
    "human": {
        "label": "Humain standard",
        "ability_adjustments": "+2 à une caractéristique au choix",
        "combat": "Très flexible; le don racial supplémentaire est particulièrement utile à un Fighter.",
        "skills": "+1 rang de compétence par niveau avec le trait racial Skilled.",
        "magic": (
            "Aucun sort racial. Le +2 flexible peut être placé en INT si une future "
            "orientation magique est prévue."
        ),
        "fighter_note": (
            "Au niveau 4, un Fighter humain standard peut normalement avoir 6 dons au total : "
            "2 dons généraux, 3 dons bonus de Fighter et 1 don racial humain."
        ),
    },
    "elf": {
        "label": "Elfe standard",
        "ability_adjustments": "+2 DEX, +2 INT, −2 CON",
        "combat": (
            "DEX et INT favorisent un profil agile/intelligent, mais le −2 CON réduit la robustesse."
        ),
        "skills": "+2 racial en Perception; l’INT plus élevée peut aussi donner davantage de rangs.",
        "magic": (
            "Elven Magic aide à vaincre la résistance aux sorts et à identifier les objets magiques; "
            "cela ne donne toutefois aucun sort ni niveau de lanceur de sorts."
        ),
        "fighter_note": (
            "La familiarité elfique avec certaines armes apporte peu à un Fighter, qui maîtrise déjà "
            "les armes simples et de guerre; l’intérêt principal ici est surtout DEX/INT et Elven Magic."
        ),
    },
}


GEAR_PRESETS: dict[str, dict[str, Any]] = {
    "chain_shirt": {
        "label": "Chemise de mailles",
        "category": "armor",
        "equipment": {
            "item_type": "armor",
            "armor_category": "light",
            "armor_bonus": 4,
            "shield_bonus": 0,
            "enhancement_bonus": 0,
            "max_dex_bonus": 4,
            "armor_check_penalty": -2,
            "arcane_spell_failure": 20,
            "speed_reduction_applies": False,
            "weight_each": 25,
            "value_text": "100 po",
            "proficiency_required": "Armures légères",
        },
        "notes": "Bonne option légère; l’échec des sorts profanes reste de 20 %.",
    },
    "breastplate": {
        "label": "Cuirasse",
        "category": "armor",
        "equipment": {
            "item_type": "armor",
            "armor_category": "medium",
            "armor_bonus": 6,
            "shield_bonus": 0,
            "enhancement_bonus": 0,
            "max_dex_bonus": 3,
            "armor_check_penalty": -4,
            "arcane_spell_failure": 25,
            "speed_reduction_applies": True,
            "weight_each": 30,
            "value_text": "200 po",
            "proficiency_required": "Armures intermédiaires",
        },
        "notes": (
            "Très solide au niveau 4. Un Fighter standard possède Entraînement aux armures 1 dès le "
            "niveau 3, mais l’app le présente comme rappel et ne modifie pas silencieusement les stats de l’objet."
        ),
    },
    "chainmail": {
        "label": "Cotte de mailles",
        "category": "armor",
        "equipment": {
            "item_type": "armor",
            "armor_category": "medium",
            "armor_bonus": 6,
            "shield_bonus": 0,
            "enhancement_bonus": 0,
            "max_dex_bonus": 2,
            "armor_check_penalty": -5,
            "arcane_spell_failure": 30,
            "speed_reduction_applies": True,
            "weight_each": 40,
            "value_text": "150 po",
            "proficiency_required": "Armures intermédiaires",
        },
        "notes": "Protection +6, mais plus lourde et moins favorable à une future magie profane.",
    },
    "full_plate": {
        "label": "Harnois complet",
        "category": "armor",
        "equipment": {
            "item_type": "armor",
            "armor_category": "heavy",
            "armor_bonus": 9,
            "shield_bonus": 0,
            "enhancement_bonus": 0,
            "max_dex_bonus": 1,
            "armor_check_penalty": -6,
            "arcane_spell_failure": 35,
            "speed_reduction_applies": True,
            "weight_each": 50,
            "value_text": "1 500 po",
            "proficiency_required": "Armures lourdes",
        },
        "notes": "Protection maximale courante, mais lourde et peu compatible avec une magie profane classique.",
    },
    "heavy_steel_shield": {
        "label": "Bouclier lourd en acier",
        "category": "shield",
        "equipment": {
            "item_type": "shield",
            "armor_category": "none",
            "armor_bonus": 0,
            "shield_bonus": 2,
            "enhancement_bonus": 0,
            "max_dex_bonus": None,
            "armor_check_penalty": -2,
            "arcane_spell_failure": 15,
            "speed_reduction_applies": False,
            "weight_each": 15,
            "value_text": "20 po",
            "proficiency_required": "Boucliers",
        },
        "notes": "Ajoute +2 de bouclier à la CA lorsqu’il est marqué Équipé.",
    },
    "longsword": {
        "label": "Épée longue",
        "category": "weapon",
        "equipment": {
            "item_type": "weapon",
            "weight_each": 4,
            "value_text": "15 po",
            "proficiency_required": "Armes de guerre",
        },
        "attack": {
            "ability_key": "str",
            "damage": "1d8",
            "critical": "19-20/x2",
            "attack_range": "—",
            "attack_type": "Tranchant",
            "magic_bonus": 0,
            "misc_bonus": 0,
        },
        "notes": "Arme de guerre à une main; le champ Dégâts peut recevoir ensuite le modificateur approprié, ex. 1d8+3.",
    },
    "rapier": {
        "label": "Rapière",
        "category": "weapon",
        "equipment": {
            "item_type": "weapon",
            "weight_each": 2,
            "value_text": "20 po",
            "proficiency_required": "Armes de guerre",
        },
        "attack": {
            "ability_key": "str",
            "damage": "1d6",
            "critical": "18-20/x2",
            "attack_range": "—",
            "attack_type": "Perforant",
            "magic_bonus": 0,
            "misc_bonus": 0,
        },
        "notes": (
            "Base de dégâts 1d6. Une construction DEX peut utiliser des règles/dons qui changent la caractéristique d’attaque; "
            "ne pas les supposer automatiquement."
        ),
    },
    "greatsword": {
        "label": "Épée à deux mains",
        "category": "weapon",
        "equipment": {
            "item_type": "weapon",
            "weight_each": 8,
            "value_text": "50 po",
            "proficiency_required": "Armes de guerre",
        },
        "attack": {
            "ability_key": "str",
            "damage": "2d6",
            "critical": "19-20/x2",
            "attack_range": "—",
            "attack_type": "Tranchant",
            "magic_bonus": 0,
            "misc_bonus": 0,
        },
        "notes": "Arme de guerre à deux mains; l’ajustement de Force aux dégâts reste à inscrire selon la feuille réelle.",
    },
    "longbow": {
        "label": "Arc long",
        "category": "weapon",
        "equipment": {
            "item_type": "weapon",
            "weight_each": 3,
            "value_text": "75 po",
            "proficiency_required": "Armes de guerre",
        },
        "attack": {
            "ability_key": "dex",
            "damage": "1d8",
            "critical": "x3",
            "attack_range": "100 pi",
            "attack_type": "Perforant",
            "magic_bonus": 0,
            "misc_bonus": 0,
        },
        "notes": "Utilise normalement la DEX pour le jet d’attaque; l’arc long standard n’ajoute pas un bonus de FOR positif aux dégâts.",
    },
}


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().replace("-", " ").split())


def is_fighter(class_name: Any) -> bool:
    normalized = _normalize(class_name)
    return normalized in FIGHTER_ALIASES or normalized.startswith("fighter ") or normalized.startswith("guerrier ")


def fighter_reference(level: Any) -> dict[str, Any] | None:
    try:
        normalized = int(level)
    except (TypeError, ValueError):
        return None
    if normalized not in FIGHTER_LEVELS:
        return None
    result = deepcopy(FIGHTER_LEVELS[normalized])
    result["level"] = normalized
    result["hit_die"] = "d10"
    result["skill_ranks"] = "2 + mod. INT par niveau"
    result["proficiencies"] = FIGHTER_PROFICIENCIES
    return result


def fighter_cumulative_milestones(level: Any) -> list[str]:
    try:
        normalized = max(0, min(4, int(level)))
    except (TypeError, ValueError):
        return []
    lines: list[str] = []
    for current in range(1, normalized + 1):
        row = FIGHTER_LEVELS[current]
        pieces = list(row["specials"]) + list(row["general_notes"])
        lines.append(f"Niveau {current} : " + "; ".join(pieces))
    return lines


def fighter_feat_counts(level: Any, race_key: Any = None) -> dict[str, int]:
    try:
        normalized = max(0, int(level))
    except (TypeError, ValueError):
        normalized = 0
    general = sum(1 for feat_level in range(1, normalized + 1, 2))
    fighter_bonus = int(normalized >= 1) + max(0, normalized // 2)
    human_bonus = 1 if _normalize(race_key) in {"human", "humain"} and normalized >= 1 else 0
    return {
        "general": general,
        "fighter_bonus": fighter_bonus,
        "human_bonus": human_bonus,
        "total": general + fighter_bonus + human_bonus,
    }


def ability_modifier(score: Any) -> int:
    try:
        value = int(score)
    except (TypeError, ValueError):
        value = 10
    return floor((value - 10) / 2)


def fighter_skill_rank_budget(level: Any, int_score: Any, race_key: Any = None) -> dict[str, int]:
    try:
        normalized_level = max(0, int(level))
    except (TypeError, ValueError):
        normalized_level = 0
    per_level = max(1, 2 + ability_modifier(int_score))
    class_total = per_level * normalized_level
    human_bonus = normalized_level if _normalize(race_key) in {"human", "humain"} else 0
    return {
        "per_level": per_level,
        "fighter_total": class_total,
        "human_standard_bonus": human_bonus,
        "total_without_favored_class": class_total + human_bonus,
    }


def is_fighter_class_skill(skill: Mapping[str, Any]) -> bool:
    key = _normalize(skill.get("skill_key")).replace(" ", "_")
    if key in FIGHTER_CLASS_SKILL_KEYS:
        return True
    if key.startswith("craft_") or key.startswith("profession_"):
        return True

    name = _normalize(skill.get("skill_name"))
    english = _normalize(skill.get("english_name"))
    names = {name, english}
    exact = {
        "escalade",
        "climb",
        "dressage",
        "handle animal",
        "intimidation",
        "intimidate",
        "connaissances (exploration souterraine)",
        "knowledge (dungeoneering)",
        "connaissances (ingenierie)",
        "knowledge (engineering)",
        "equitation",
        "ride",
        "survie",
        "survival",
        "natation",
        "swim",
    }
    if names & exact:
        return True
    return any(
        value.startswith(prefix)
        for value in names
        for prefix in ("artisanat", "craft", "profession")
    )


def race_comparison(race_key: Any) -> dict[str, Any] | None:
    key = _normalize(race_key)
    aliases = {
        "human": "human",
        "humain": "human",
        "elf": "elf",
        "elfe": "elf",
    }
    resolved = aliases.get(key)
    if not resolved:
        return None
    result = deepcopy(RACE_COMPARISON[resolved])
    result["race_key"] = resolved
    return result


def gear_preset_options() -> dict[str, str]:
    return {key: value["label"] for key, value in GEAR_PRESETS.items()}


def gear_preset(key: Any) -> dict[str, Any] | None:
    preset = GEAR_PRESETS.get(str(key or ""))
    return deepcopy(preset) if preset else None


def gear_reference_lines(key: Any) -> list[str]:
    preset = gear_preset(key)
    if not preset:
        return []
    equipment = preset["equipment"]
    lines = [f"Objet : {preset['label']}"]
    if preset["category"] == "armor":
        lines.extend(
            [
                f"Équipement → type Armure, catégorie {equipment['armor_category']}, bonus CA +{equipment['armor_bonus']}",
                f"DEX max {equipment['max_dex_bonus']}; pénalité aux tests {equipment['armor_check_penalty']}; échec profane {equipment['arcane_spell_failure']} %",
                f"Poids {equipment['weight_each']} lb; valeur {equipment['value_text']}; maîtrise {equipment['proficiency_required']}",
            ]
        )
    elif preset["category"] == "shield":
        lines.extend(
            [
                f"Équipement → type Bouclier, bonus bouclier +{equipment['shield_bonus']}",
                f"Pénalité aux tests {equipment['armor_check_penalty']}; échec profane {equipment['arcane_spell_failure']} %",
                f"Poids {equipment['weight_each']} lb; valeur {equipment['value_text']}; maîtrise {equipment['proficiency_required']}",
            ]
        )
    else:
        attack = preset["attack"]
        lines.extend(
            [
                f"Équipement → type Arme; poids {equipment['weight_each']} lb; valeur {equipment['value_text']}; maîtrise {equipment['proficiency_required']}",
                f"Attaques → caractéristique {attack['ability_key'].upper()}; dégâts {attack['damage']}; critique {attack['critical']}",
                f"Portée {attack['attack_range']}; type {attack['attack_type']}; bonus magique/divers 0 par défaut",
            ]
        )
    if preset.get("notes"):
        lines.append("Note : " + str(preset["notes"]))
    return lines
