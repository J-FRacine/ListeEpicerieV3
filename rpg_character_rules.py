from __future__ import annotations

from decimal import Decimal
from math import floor


ABILITY_LABELS = {
    "str": "FOR",
    "dex": "DEX",
    "con": "CON",
    "int": "INT",
    "wis": "SAG",
    "cha": "CHA",
}

ABILITY_LONG_LABELS = {
    "str": "Force",
    "dex": "Dextérité",
    "con": "Constitution",
    "int": "Intelligence",
    "wis": "Sagesse",
    "cha": "Charisme",
}

SIZE_LABELS = {
    "fine": "Infime",
    "diminutive": "Minuscule",
    "tiny": "Très petite",
    "small": "Petite",
    "medium": "Moyenne",
    "large": "Grande",
    "huge": "Très grande",
    "gargantuan": "Gigantesque",
    "colossal": "Colossale",
}

SIZE_AC_MODIFIERS = {
    "fine": 8,
    "diminutive": 4,
    "tiny": 2,
    "small": 1,
    "medium": 0,
    "large": -1,
    "huge": -2,
    "gargantuan": -4,
    "colossal": -8,
}

# Pathfinder 1re édition :
# modificateur spécial de taille pour le BMO/CMB et le DMD/CMD.
SIZE_COMBAT_MANEUVER_MODIFIERS = {
    "fine": -8,
    "diminutive": -4,
    "tiny": -2,
    "small": -1,
    "medium": 0,
    "large": 1,
    "huge": 2,
    "gargantuan": 4,
    "colossal": 8,
}

TINY_OR_SMALLER_SIZE_KEYS = {
    "fine",
    "diminutive",
    "tiny",
}

SAVE_DEFINITIONS = {
    "fortitude": {
        "label": "Vigueur",
        "ability_key": "con",
        "ravenloft": False,
    },
    "reflex": {
        "label": "Réflexes",
        "ability_key": "dex",
        "ravenloft": False,
    },
    "will": {
        "label": "Volonté",
        "ability_key": "wis",
        "ravenloft": False,
    },
    "fear": {
        "label": "Peur",
        "ability_key": "wis",
        "ravenloft": True,
    },
    "horror": {
        "label": "Horreur",
        "ability_key": "wis",
        "ravenloft": True,
    },
    "madness": {
        "label": "Folie",
        "ability_key": "wis",
        "ravenloft": True,
    },
}

# Format :
# clé, nom, caractéristique, pénalité d’armure,
# formation requise, pénalité d’armure doublée.
#
# Liste Pathfinder 1re édition. Les variantes numérotées permettent
# de conserver plusieurs artisanats, représentations et professions.
STANDARD_SKILLS = [
    ("acrobatics", "Acrobaties", "dex", True, False, False),
    ("appraise", "Estimation", "int", False, False, False),
    ("bluff", "Bluff", "cha", False, False, False),
    ("climb", "Escalade", "str", True, False, False),
    ("craft_1", "Artisanat (1)", "int", False, False, False),
    ("craft_2", "Artisanat (2)", "int", False, False, False),
    ("craft_3", "Artisanat (3)", "int", False, False, False),
    ("diplomacy", "Diplomatie", "cha", False, False, False),
    ("disable_device", "Sabotage", "dex", True, True, False),
    ("disguise", "Déguisement", "cha", False, False, False),
    ("escape_artist", "Évasion", "dex", True, False, False),
    ("fly", "Vol", "dex", True, False, False),
    ("handle_animal", "Dressage", "cha", False, True, False),
    ("heal", "Premiers secours", "wis", False, False, False),
    ("intimidate", "Intimidation", "cha", False, False, False),
    (
        "knowledge_arcana",
        "Connaissances (mystères)",
        "int",
        False,
        True,
        False,
    ),
    (
        "knowledge_dungeoneering",
        "Connaissances (exploration souterraine)",
        "int",
        False,
        True,
        False,
    ),
    (
        "knowledge_engineering",
        "Connaissances (ingénierie)",
        "int",
        False,
        True,
        False,
    ),
    (
        "knowledge_geography",
        "Connaissances (géographie)",
        "int",
        False,
        True,
        False,
    ),
    (
        "knowledge_history",
        "Connaissances (histoire)",
        "int",
        False,
        True,
        False,
    ),
    (
        "knowledge_local",
        "Connaissances (folklore local)",
        "int",
        False,
        True,
        False,
    ),
    (
        "knowledge_nature",
        "Connaissances (nature)",
        "int",
        False,
        True,
        False,
    ),
    (
        "knowledge_nobility",
        "Connaissances (noblesse)",
        "int",
        False,
        True,
        False,
    ),
    (
        "knowledge_religion",
        "Connaissances (religion)",
        "int",
        False,
        True,
        False,
    ),
    (
        "knowledge_planes",
        "Connaissances (plans)",
        "int",
        False,
        True,
        False,
    ),
    ("linguistics", "Linguistique", "int", False, True, False),
    ("perception", "Perception", "wis", False, False, False),
    (
        "perform_1",
        "Représentation (1)",
        "cha",
        False,
        False,
        False,
    ),
    (
        "perform_2",
        "Représentation (2)",
        "cha",
        False,
        False,
        False,
    ),
    (
        "perform_3",
        "Représentation (3)",
        "cha",
        False,
        False,
        False,
    ),
    (
        "profession_1",
        "Profession (1)",
        "wis",
        False,
        True,
        False,
    ),
    (
        "profession_2",
        "Profession (2)",
        "wis",
        False,
        True,
        False,
    ),
    ("ride", "Équitation", "dex", True, False, False),
    ("sense_motive", "Psychologie", "wis", False, False, False),
    (
        "sleight_of_hand",
        "Escamotage",
        "dex",
        True,
        True,
        False,
    ),
    (
        "spellcraft",
        "Art de la magie",
        "int",
        False,
        True,
        False,
    ),
    ("stealth", "Discrétion", "dex", True, False, False),
    ("survival", "Survie", "wis", False, False, False),
    ("swim", "Natation", "str", True, False, False),
    (
        "use_magic_device",
        "Utilisation d’objets magiques",
        "cha",
        False,
        True,
        False,
    ),
]

PATHFINDER_SKILL_KEYS = {
    definition[0]
    for definition in STANDARD_SKILLS
}

SKILL_ENGLISH_NAMES = {
    "acrobatics": "Acrobatics",
    "appraise": "Appraise",
    "bluff": "Bluff",
    "climb": "Climb",
    "craft_1": "Craft (1)",
    "craft_2": "Craft (2)",
    "craft_3": "Craft (3)",
    "diplomacy": "Diplomacy",
    "disable_device": "Disable Device",
    "disguise": "Disguise",
    "escape_artist": "Escape Artist",
    "fly": "Fly",
    "handle_animal": "Handle Animal",
    "heal": "Heal",
    "intimidate": "Intimidate",
    "knowledge_arcana": "Knowledge (arcana)",
    "knowledge_dungeoneering": (
        "Knowledge (dungeoneering)"
    ),
    "knowledge_engineering": (
        "Knowledge (engineering)"
    ),
    "knowledge_geography": (
        "Knowledge (geography)"
    ),
    "knowledge_history": "Knowledge (history)",
    "knowledge_local": "Knowledge (local)",
    "knowledge_nature": "Knowledge (nature)",
    "knowledge_nobility": (
        "Knowledge (nobility)"
    ),
    "knowledge_religion": (
        "Knowledge (religion)"
    ),
    "knowledge_planes": "Knowledge (planes)",
    "linguistics": "Linguistics",
    "perception": "Perception",
    "perform_1": "Perform (1)",
    "perform_2": "Perform (2)",
    "perform_3": "Perform (3)",
    "profession_1": "Profession (1)",
    "profession_2": "Profession (2)",
    "ride": "Ride",
    "sense_motive": "Sense Motive",
    "sleight_of_hand": "Sleight of Hand",
    "spellcraft": "Spellcraft",
    "stealth": "Stealth",
    "survival": "Survival",
    "swim": "Swim",
    "use_magic_device": "Use Magic Device",
}


def as_int(value, default=0) -> int:
    if value in (None, ""):
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_decimal(
    value,
    default=Decimal("0"),
) -> Decimal:
    if value in (None, ""):
        return default

    try:
        return Decimal(
            str(value)
        )
    except Exception:
        return default


def format_modifier(value) -> str:
    number = as_int(value)

    if number >= 0:
        return f"+{number}"

    return str(number)


def format_number(value) -> str:
    number = as_decimal(value)

    if (
        number
        == number.to_integral()
    ):
        return str(
            int(number)
        )

    return format(
        number.normalize(),
        "f",
    )


def ability_modifier(
    score,
    temporary_score=None,
) -> int:
    effective = (
        temporary_score
        if temporary_score
        not in (
            None,
            "",
        )
        else score
    )
    normalized = as_int(
        effective,
        10,
    )
    return floor(
        (
            normalized
            - 10
        )
        / 2
    )


def ability_modifier_for_character(
    character,
    ability_key,
) -> int:
    score = character.get(
        f"{ability_key}_score",
        10,
    )
    temporary_score = (
        character.get(
            f"{ability_key}_temp_score"
        )
    )
    return ability_modifier(
        score,
        temporary_score,
    )


def ac_size_modifier(
    size_key,
) -> int:
    return SIZE_AC_MODIFIERS.get(
        str(
            size_key
            or "medium"
        ),
        0,
    )


def combat_maneuver_size_modifier(
    size_key,
) -> int:
    return (
        SIZE_COMBAT_MANEUVER_MODIFIERS.get(
            str(
                size_key
                or "medium"
            ),
            0,
        )
    )


def armor_class_breakdown(
    character,
):
    """Décompose les trois formes de classe d’armure."""

    dex_modifier = ability_modifier_for_character(
        character,
        "dex",
    )
    size_modifier = ac_size_modifier(
        character.get("size_key")
    )
    armor_bonus = as_int(character.get("armor_bonus"))
    shield_bonus = as_int(character.get("shield_bonus"))
    natural_bonus = as_int(
        character.get("natural_armor_bonus")
    )
    deflection_bonus = as_int(
        character.get("deflection_bonus")
    )
    misc_modifier = as_int(
        character.get("misc_ac_modifier")
    )
    flat_footed_dex = min(dex_modifier, 0)

    total = (
        10
        + armor_bonus
        + shield_bonus
        + dex_modifier
        + size_modifier
        + natural_bonus
        + deflection_bonus
        + misc_modifier
    )
    touch = (
        10
        + dex_modifier
        + size_modifier
        + deflection_bonus
        + misc_modifier
    )
    flat_footed = (
        10
        + armor_bonus
        + shield_bonus
        + flat_footed_dex
        + size_modifier
        + natural_bonus
        + deflection_bonus
        + misc_modifier
    )

    return {
        "base": 10,
        "armor_bonus": armor_bonus,
        "shield_bonus": shield_bonus,
        "dex_modifier": dex_modifier,
        "flat_footed_dex_modifier": flat_footed_dex,
        "size_modifier": size_modifier,
        "natural_armor_bonus": natural_bonus,
        "deflection_bonus": deflection_bonus,
        "misc_modifier": misc_modifier,
        "total": total,
        "touch": touch,
        "flat_footed": flat_footed,
    }


def armor_class_total(
    character,
) -> int:
    return armor_class_breakdown(character)["total"]


def touch_armor_class(
    character,
) -> int:
    return armor_class_breakdown(character)["touch"]


def flat_footed_armor_class(
    character,
) -> int:
    return armor_class_breakdown(character)["flat_footed"]


def initiative_breakdown(
    character,
):
    dex_modifier = ability_modifier_for_character(
        character,
        "dex",
    )
    misc_modifier = as_int(
        character.get("initiative_misc_modifier")
    )

    return {
        "dex_modifier": dex_modifier,
        "misc_modifier": misc_modifier,
        "total": dex_modifier + misc_modifier,
    }


def initiative_total(
    character,
) -> int:
    return initiative_breakdown(character)["total"]


def cmb_breakdown(
    character,
):
    """Décompose le BMO/CMB de Pathfinder 1re édition."""

    size_key = str(
        character.get("size_key") or "medium"
    )
    ability_key = (
        "dex"
        if size_key in TINY_OR_SMALLER_SIZE_KEYS
        else "str"
    )
    base_attack_bonus = as_int(
        character.get("base_attack_bonus")
    )
    ability_mod = ability_modifier_for_character(
        character,
        ability_key,
    )
    size_modifier = combat_maneuver_size_modifier(
        size_key
    )
    misc_modifier = as_int(
        character.get("cmb_misc_modifier")
    )

    return {
        "ability_key": ability_key,
        "base_attack_bonus": base_attack_bonus,
        "ability_modifier": ability_mod,
        "size_modifier": size_modifier,
        "misc_modifier": misc_modifier,
        "total": (
            base_attack_bonus
            + ability_mod
            + size_modifier
            + misc_modifier
        ),
    }


def cmb_total(
    character,
) -> int:
    return cmb_breakdown(character)["total"]


def cmd_breakdown(
    character,
):
    """Décompose le DMD/CMD de Pathfinder 1re édition."""

    base_attack_bonus = as_int(
        character.get("base_attack_bonus")
    )
    strength_modifier = ability_modifier_for_character(
        character,
        "str",
    )
    dexterity_modifier = ability_modifier_for_character(
        character,
        "dex",
    )
    size_modifier = combat_maneuver_size_modifier(
        character.get("size_key")
    )
    deflection_bonus = as_int(
        character.get("deflection_bonus")
    )
    automatic_ac_penalty = min(
        as_int(character.get("misc_ac_modifier")),
        0,
    )
    misc_modifier = as_int(
        character.get("cmd_misc_modifier")
    )

    total = (
        10
        + base_attack_bonus
        + strength_modifier
        + dexterity_modifier
        + size_modifier
        + deflection_bonus
        + automatic_ac_penalty
        + misc_modifier
    )

    return {
        "base": 10,
        "base_attack_bonus": base_attack_bonus,
        "strength_modifier": strength_modifier,
        "dexterity_modifier": dexterity_modifier,
        "size_modifier": size_modifier,
        "deflection_bonus": deflection_bonus,
        "automatic_ac_penalty": automatic_ac_penalty,
        "misc_modifier": misc_modifier,
        "total": total,
    }


def cmd_total(
    character,
) -> int:
    return cmd_breakdown(character)["total"]


def grapple_total(
    character,
) -> int:
    """Ancien nom conservé pour compatibilité : correspond au BMO/CMB."""

    return cmb_total(
        character
    )


def save_breakdown(
    character,
    save_row,
):
    definition = SAVE_DEFINITIONS[
        save_row["save_key"]
    ]
    ability_key = definition["ability_key"]
    base_save = as_int(save_row.get("base_save"))
    ability_mod = ability_modifier_for_character(
        character,
        ability_key,
    )
    magic_modifier = as_int(
        save_row.get("magic_modifier")
    )
    misc_modifier = as_int(
        save_row.get("misc_modifier")
    )
    temporary_modifier = as_int(
        save_row.get("temporary_modifier")
    )

    return {
        "ability_key": ability_key,
        "base_save": base_save,
        "ability_modifier": ability_mod,
        "magic_modifier": magic_modifier,
        "misc_modifier": misc_modifier,
        "temporary_modifier": temporary_modifier,
        "total": (
            base_save
            + ability_mod
            + magic_modifier
            + misc_modifier
            + temporary_modifier
        ),
    }


def save_total(
    character,
    save_row,
) -> int:
    return save_breakdown(character, save_row)["total"]


def skill_class_bonus(
    skill_row,
) -> int:
    ranks = as_decimal(
        skill_row.get(
            "ranks"
        )
    )

    if (
        ranks > 0
        and bool(
            skill_row.get(
                "class_skill"
            )
        )
    ):
        return 3

    return 0


def skill_breakdown(
    character,
    skill_row,
):
    """Retourne chaque composante du calcul Pathfinder."""

    ability_key = (
        skill_row.get(
            "ability_key"
        )
        or "int"
    )
    ability_mod = (
        ability_modifier_for_character(
            character,
            ability_key,
        )
    )
    ranks = as_decimal(
        skill_row.get(
            "ranks"
        )
    )
    misc_modifier = as_int(
        skill_row.get(
            "misc_modifier"
        )
    )
    class_bonus = (
        skill_class_bonus(
            skill_row
        )
    )

    armor_penalty = 0

    if skill_row.get(
        "armor_check_applies"
    ):
        armor_penalty = as_int(
            character.get(
                "armor_check_penalty"
            )
        )

        if skill_row.get(
            "double_armor_penalty"
        ):
            armor_penalty *= 2

    total = (
        ranks
        + Decimal(
            ability_mod
        )
        + Decimal(
            misc_modifier
        )
        + Decimal(
            armor_penalty
        )
        + Decimal(
            class_bonus
        )
    )

    return {
        "ability_key": ability_key,
        "ability_modifier": ability_mod,
        "ranks": ranks,
        "class_bonus": class_bonus,
        "misc_modifier": misc_modifier,
        "armor_penalty": armor_penalty,
        "total": total,
    }


def skill_total(
    character,
    skill_row,
):
    return skill_breakdown(
        character,
        skill_row,
    )["total"]


def attack_breakdown(
    character,
    attack_row,
):
    ability_key = attack_row.get("ability_key") or "str"
    base_attack_bonus = as_int(
        character.get("base_attack_bonus")
    )
    ability_mod = ability_modifier_for_character(
        character,
        ability_key,
    )
    size_modifier = ac_size_modifier(
        character.get("size_key")
    )
    magic_bonus = as_int(
        attack_row.get("magic_bonus")
    )
    misc_bonus = as_int(
        attack_row.get("misc_bonus")
    )

    return {
        "ability_key": ability_key,
        "base_attack_bonus": base_attack_bonus,
        "ability_modifier": ability_mod,
        "size_modifier": size_modifier,
        "magic_bonus": magic_bonus,
        "misc_bonus": misc_bonus,
        "total": (
            base_attack_bonus
            + ability_mod
            + size_modifier
            + magic_bonus
            + misc_bonus
        ),
    }


def attack_total(
    character,
    attack_row,
) -> int:
    return attack_breakdown(character, attack_row)["total"]

