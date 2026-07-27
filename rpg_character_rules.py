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


def armor_class_total(
    character,
) -> int:
    dex_modifier = (
        ability_modifier_for_character(
            character,
            "dex",
        )
    )

    return (
        10
        + as_int(
            character.get(
                "armor_bonus"
            )
        )
        + as_int(
            character.get(
                "shield_bonus"
            )
        )
        + dex_modifier
        + ac_size_modifier(
            character.get(
                "size_key"
            )
        )
        + as_int(
            character.get(
                "natural_armor_bonus"
            )
        )
        + as_int(
            character.get(
                "deflection_bonus"
            )
        )
        + as_int(
            character.get(
                "misc_ac_modifier"
            )
        )
    )


def touch_armor_class(
    character,
) -> int:
    dex_modifier = (
        ability_modifier_for_character(
            character,
            "dex",
        )
    )

    return (
        10
        + dex_modifier
        + ac_size_modifier(
            character.get(
                "size_key"
            )
        )
        + as_int(
            character.get(
                "deflection_bonus"
            )
        )
        + as_int(
            character.get(
                "misc_ac_modifier"
            )
        )
    )


def flat_footed_armor_class(
    character,
) -> int:
    dex_modifier = (
        ability_modifier_for_character(
            character,
            "dex",
        )
    )

    return (
        10
        + as_int(
            character.get(
                "armor_bonus"
            )
        )
        + as_int(
            character.get(
                "shield_bonus"
            )
        )
        + min(
            dex_modifier,
            0,
        )
        + ac_size_modifier(
            character.get(
                "size_key"
            )
        )
        + as_int(
            character.get(
                "natural_armor_bonus"
            )
        )
        + as_int(
            character.get(
                "deflection_bonus"
            )
        )
        + as_int(
            character.get(
                "misc_ac_modifier"
            )
        )
    )


def initiative_total(
    character,
) -> int:
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


def cmb_total(
    character,
) -> int:
    """Bonus de manœuvre offensive / Combat Maneuver Bonus."""

    size_key = str(
        character.get(
            "size_key"
        )
        or "medium"
    )

    ability_key = (
        "dex"
        if size_key
        in TINY_OR_SMALLER_SIZE_KEYS
        else "str"
    )

    return (
        as_int(
            character.get(
                "base_attack_bonus"
            )
        )
        + ability_modifier_for_character(
            character,
            ability_key,
        )
        + combat_maneuver_size_modifier(
            size_key
        )
        + as_int(
            character.get(
                "cmb_misc_modifier"
            )
        )
    )


def cmd_total(
    character,
) -> int:
    """Degré de manœuvre défensive / Combat Maneuver Defense."""

    misc_ac_modifier = as_int(
        character.get(
            "misc_ac_modifier"
        )
    )

    # Toutes les pénalités à la CA s’appliquent au DMD/CMD.
    automatic_ac_penalty = min(
        misc_ac_modifier,
        0,
    )

    return (
        10
        + as_int(
            character.get(
                "base_attack_bonus"
            )
        )
        + ability_modifier_for_character(
            character,
            "str",
        )
        + ability_modifier_for_character(
            character,
            "dex",
        )
        + combat_maneuver_size_modifier(
            character.get(
                "size_key"
            )
        )
        + as_int(
            character.get(
                "deflection_bonus"
            )
        )
        + automatic_ac_penalty
        + as_int(
            character.get(
                "cmd_misc_modifier"
            )
        )
    )


def grapple_total(
    character,
) -> int:
    """Ancien nom conservé pour compatibilité : correspond au BMO/CMB."""

    return cmb_total(
        character
    )


def save_total(
    character,
    save_row,
) -> int:
    definition = SAVE_DEFINITIONS[
        save_row["save_key"]
    ]

    return (
        as_int(
            save_row.get(
                "base_save"
            )
        )
        + ability_modifier_for_character(
            character,
            definition[
                "ability_key"
            ],
        )
        + as_int(
            save_row.get(
                "magic_modifier"
            )
        )
        + as_int(
            save_row.get(
                "misc_modifier"
            )
        )
        + as_int(
            save_row.get(
                "temporary_modifier"
            )
        )
    )


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


def skill_total(
    character,
    skill_row,
):
    ability_mod = (
        ability_modifier_for_character(
            character,
            skill_row.get(
                "ability_key"
            ),
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

    return (
        as_decimal(
            skill_row.get(
                "ranks"
            )
        )
        + Decimal(
            ability_mod
        )
        + Decimal(
            as_int(
                skill_row.get(
                    "misc_modifier"
                )
            )
        )
        + Decimal(
            armor_penalty
        )
        + Decimal(
            skill_class_bonus(
                skill_row
            )
        )
    )


def attack_total(
    character,
    attack_row,
) -> int:
    return (
        as_int(
            character.get(
                "base_attack_bonus"
            )
        )
        + ability_modifier_for_character(
            character,
            attack_row.get(
                "ability_key"
            )
            or "str",
        )
        + ac_size_modifier(
            character.get(
                "size_key"
            )
        )
        + as_int(
            attack_row.get(
                "magic_bonus"
            )
        )
        + as_int(
            attack_row.get(
                "misc_bonus"
            )
        )
    )
