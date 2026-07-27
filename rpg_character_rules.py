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

SIZE_GRAPPLE_MODIFIERS = {
    "fine": -16,
    "diminutive": -12,
    "tiny": -8,
    "small": -4,
    "medium": 0,
    "large": 4,
    "huge": 8,
    "gargantuan": 12,
    "colossal": 16,
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

STANDARD_SKILLS = [
    ("appraise", "Appraise", "int", False, False, False),
    ("balance", "Balance", "dex", True, False, False),
    ("bluff", "Bluff", "cha", False, False, False),
    ("climb", "Climb", "str", True, False, False),
    ("concentration", "Concentration", "con", False, False, False),
    ("craft_1", "Craft (1)", "int", False, False, False),
    ("craft_2", "Craft (2)", "int", False, False, False),
    ("craft_3", "Craft (3)", "int", False, False, False),
    ("decipher_script", "Decipher Script", "int", False, True, False),
    ("diplomacy", "Diplomacy", "cha", False, False, False),
    ("disable_device", "Disable Device", "int", False, True, False),
    ("disguise", "Disguise", "cha", False, False, False),
    ("escape_artist", "Escape Artist", "dex", True, False, False),
    ("forgery", "Forgery", "int", False, False, False),
    ("gather_information", "Gather Information", "cha", False, False, False),
    ("handle_animal", "Handle Animal", "cha", False, True, False),
    ("heal", "Heal", "wis", False, False, False),
    ("hide", "Hide", "dex", True, False, False),
    ("hypnosis", "Hypnosis", "cha", False, True, False),
    ("intimidate", "Intimidate", "cha", False, False, False),
    ("jump", "Jump", "str", True, False, False),
    ("knowledge_1", "Knowledge (1)", "int", False, True, False),
    ("knowledge_2", "Knowledge (2)", "int", False, True, False),
    ("knowledge_3", "Knowledge (3)", "int", False, True, False),
    ("knowledge_4", "Knowledge (4)", "int", False, True, False),
    ("knowledge_5", "Knowledge (5)", "int", False, True, False),
    ("listen", "Listen", "wis", False, False, False),
    ("move_silently", "Move Silently", "dex", True, False, False),
    ("open_lock", "Open Lock", "dex", False, True, False),
    ("perform_1", "Perform (1)", "cha", False, False, False),
    ("perform_2", "Perform (2)", "cha", False, False, False),
    ("perform_3", "Perform (3)", "cha", False, False, False),
    ("profession_1", "Profession (1)", "wis", False, True, False),
    ("profession_2", "Profession (2)", "wis", False, True, False),
    ("ride", "Ride", "dex", False, False, False),
    ("search", "Search", "int", False, False, False),
    ("sense_motive", "Sense Motive", "wis", False, False, False),
    ("sleight_of_hand", "Sleight of Hand", "dex", True, True, False),
    ("spellcraft", "Spellcraft", "int", False, True, False),
    ("spot", "Spot", "wis", False, False, False),
    ("survival", "Survival", "wis", False, False, False),
    ("swim", "Swim", "str", True, False, True),
    ("tumble", "Tumble", "dex", True, True, False),
    ("use_magic_device", "Use Magic Device", "cha", False, True, False),
    ("use_rope", "Use Rope", "dex", False, False, False),
]


def as_int(value, default=0) -> int:
    if value in (None, ""):
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_decimal(value, default=Decimal("0")) -> Decimal:
    if value in (None, ""):
        return default

    try:
        return Decimal(str(value))
    except Exception:
        return default


def format_modifier(value) -> str:
    number = as_int(value)

    if number >= 0:
        return f"+{number}"

    return str(number)


def format_number(value) -> str:
    number = as_decimal(value)

    if number == number.to_integral():
        return str(int(number))

    return format(number.normalize(), "f")


def ability_modifier(score, temporary_score=None) -> int:
    effective = (
        temporary_score
        if temporary_score not in (None, "")
        else score
    )
    normalized = as_int(effective, 10)
    return floor((normalized - 10) / 2)


def ability_modifier_for_character(character, ability_key) -> int:
    score = character.get(f"{ability_key}_score", 10)
    temporary_score = character.get(f"{ability_key}_temp_score")
    return ability_modifier(score, temporary_score)


def ac_size_modifier(size_key) -> int:
    return SIZE_AC_MODIFIERS.get(
        str(size_key or "medium"),
        0,
    )


def grapple_size_modifier(size_key) -> int:
    return SIZE_GRAPPLE_MODIFIERS.get(
        str(size_key or "medium"),
        0,
    )


def armor_class_total(character) -> int:
    dex_modifier = ability_modifier_for_character(
        character,
        "dex",
    )

    return (
        10
        + as_int(character.get("armor_bonus"))
        + as_int(character.get("shield_bonus"))
        + dex_modifier
        + ac_size_modifier(character.get("size_key"))
        + as_int(character.get("natural_armor_bonus"))
        + as_int(character.get("deflection_bonus"))
        + as_int(character.get("misc_ac_modifier"))
    )


def touch_armor_class(character) -> int:
    dex_modifier = ability_modifier_for_character(
        character,
        "dex",
    )

    return (
        10
        + dex_modifier
        + ac_size_modifier(character.get("size_key"))
        + as_int(character.get("deflection_bonus"))
        + as_int(character.get("misc_ac_modifier"))
    )


def flat_footed_armor_class(character) -> int:
    dex_modifier = ability_modifier_for_character(
        character,
        "dex",
    )

    return (
        10
        + as_int(character.get("armor_bonus"))
        + as_int(character.get("shield_bonus"))
        + min(dex_modifier, 0)
        + ac_size_modifier(character.get("size_key"))
        + as_int(character.get("natural_armor_bonus"))
        + as_int(character.get("deflection_bonus"))
        + as_int(character.get("misc_ac_modifier"))
    )


def initiative_total(character) -> int:
    return (
        ability_modifier_for_character(
            character,
            "dex",
        )
        + as_int(
            character.get(
                "initiative_misc_modifier"
            )
        )
    )


def grapple_total(character) -> int:
    return (
        as_int(character.get("base_attack_bonus"))
        + ability_modifier_for_character(
            character,
            "str",
        )
        + grapple_size_modifier(
            character.get("size_key")
        )
        + as_int(
            character.get(
                "grapple_misc_modifier"
            )
        )
    )


def save_total(character, save_row) -> int:
    definition = SAVE_DEFINITIONS[
        save_row["save_key"]
    ]

    return (
        as_int(save_row.get("base_save"))
        + ability_modifier_for_character(
            character,
            definition["ability_key"],
        )
        + as_int(save_row.get("magic_modifier"))
        + as_int(save_row.get("misc_modifier"))
        + as_int(save_row.get("temporary_modifier"))
    )


def skill_total(character, skill_row):
    ability_mod = ability_modifier_for_character(
        character,
        skill_row.get("ability_key"),
    )

    armor_penalty = 0

    if skill_row.get("armor_check_applies"):
        armor_penalty = as_int(
            character.get("armor_check_penalty")
        )

        if skill_row.get("double_armor_penalty"):
            armor_penalty *= 2

    return (
        as_decimal(skill_row.get("ranks"))
        + Decimal(ability_mod)
        + Decimal(
            as_int(
                skill_row.get("misc_modifier")
            )
        )
        + Decimal(armor_penalty)
    )


def attack_total(character, attack_row) -> int:
    return (
        as_int(character.get("base_attack_bonus"))
        + ability_modifier_for_character(
            character,
            attack_row.get("ability_key")
            or "str",
        )
        + ac_size_modifier(
            character.get("size_key")
        )
        + as_int(attack_row.get("magic_bonus"))
        + as_int(attack_row.get("misc_bonus"))
    )
