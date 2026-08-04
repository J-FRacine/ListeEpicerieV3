from __future__ import annotations

from decimal import Decimal
from math import floor
import re


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



CARRYING_CAPACITY_BASE = {
    1: (3, 6, 10),
    2: (6, 13, 20),
    3: (10, 20, 30),
    4: (13, 26, 40),
    5: (16, 33, 50),
    6: (20, 40, 60),
    7: (23, 46, 70),
    8: (26, 53, 80),
    9: (30, 60, 90),
    10: (33, 66, 100),
    11: (38, 76, 115),
    12: (43, 86, 130),
    13: (50, 100, 150),
    14: (58, 116, 175),
    15: (66, 133, 200),
    16: (76, 153, 230),
    17: (86, 173, 260),
    18: (100, 200, 300),
    19: (116, 233, 350),
    20: (133, 266, 400),
    21: (153, 306, 460),
    22: (173, 346, 520),
    23: (200, 400, 600),
    24: (233, 466, 700),
    25: (266, 533, 800),
    26: (306, 613, 920),
    27: (346, 693, 1040),
    28: (400, 800, 1200),
    29: (466, 933, 1400),
}

BIPED_SIZE_LOAD_MULTIPLIERS = {
    "fine": Decimal("0.125"),
    "diminutive": Decimal("0.25"),
    "tiny": Decimal("0.5"),
    "small": Decimal("0.75"),
    "medium": Decimal("1"),
    "large": Decimal("2"),
    "huge": Decimal("4"),
    "gargantuan": Decimal("8"),
    "colossal": Decimal("16"),
}

QUADRUPED_SIZE_LOAD_MULTIPLIERS = {
    "fine": Decimal("0.25"),
    "diminutive": Decimal("0.5"),
    "tiny": Decimal("0.75"),
    "small": Decimal("1"),
    "medium": Decimal("1.5"),
    "large": Decimal("3"),
    "huge": Decimal("6"),
    "gargantuan": Decimal("12"),
    "colossal": Decimal("24"),
}

LOAD_LABELS = {
    "light": "Légère",
    "medium": "Moyenne",
    "heavy": "Lourde",
    "overloaded": "Surcharge",
    "immovable": "Impossible à soulever",
}


def effective_ability_score(character, ability_key):
    temporary = character.get(f"{ability_key}_temp_score")
    if temporary not in (None, ""):
        return as_int(temporary, 10)
    return as_int(character.get(f"{ability_key}_score"), 10)


def _base_carrying_capacity(strength_score):
    strength = max(1, as_int(strength_score, 10))
    if strength <= 29:
        return tuple(
            Decimal(str(value))
            for value in CARRYING_CAPACITY_BASE[strength]
        )

    reference_strength = 20 + (strength % 10)
    decades = (strength - reference_strength) // 10
    multiplier = Decimal(4) ** decades
    return tuple(
        Decimal(str(value)) * multiplier
        for value in CARRYING_CAPACITY_BASE[reference_strength]
    )


def carrying_capacity(character):
    strength = effective_ability_score(character, "str")
    light, medium, heavy = _base_carrying_capacity(strength)
    size_key = str(character.get("size_key") or "medium")
    quadruped = bool(character.get("is_quadruped"))
    size_multipliers = (
        QUADRUPED_SIZE_LOAD_MULTIPLIERS
        if quadruped
        else BIPED_SIZE_LOAD_MULTIPLIERS
    )
    size_multiplier = size_multipliers.get(
        size_key,
        Decimal("1"),
    )
    try:
        racial_multiplier = Decimal(
            str(character.get("carrying_capacity_multiplier") or 1)
        )
    except Exception:
        racial_multiplier = Decimal("1")
    if racial_multiplier <= 0:
        racial_multiplier = Decimal("1")

    multiplier = size_multiplier * racial_multiplier
    return {
        "strength": strength,
        "size_key": size_key,
        "quadruped": quadruped,
        "size_multiplier": size_multiplier,
        "racial_multiplier": racial_multiplier,
        "total_multiplier": multiplier,
        "light_max": light * multiplier,
        "medium_max": medium * multiplier,
        "heavy_max": heavy * multiplier,
        "lift_off_ground_max": heavy * multiplier * 2,
        "push_drag_max": heavy * multiplier * 5,
    }


def reduced_speed_for_base(base_speed):
    speed = max(0, as_int(base_speed, 30))
    if speed <= 5:
        return speed
    ranges = (
        (15, 10),
        (20, 15),
        (30, 20),
        (35, 25),
        (45, 30),
        (50, 35),
        (60, 40),
        (65, 45),
        (75, 50),
        (80, 55),
        (90, 60),
        (95, 65),
        (105, 70),
        (110, 75),
        (120, 80),
    )
    for maximum, reduced in ranges:
        if speed <= maximum:
            return reduced
    return max(5, int((speed * 2 / 3) // 5 * 5))


def _item_decimal(item, key, default="0"):
    try:
        return Decimal(str(item.get(key, default) or default))
    except Exception:
        return Decimal(default)


def _item_int(item, key, default=0):
    return as_int(item.get(key), default)


def equipment_effects(character, equipment_rows):
    equipment = [dict(row) for row in (equipment_rows or [])]
    carried = [row for row in equipment if bool(row.get("carried", True))]
    equipped = [row for row in equipment if bool(row.get("equipped"))]

    total_weight = sum(
        (
            _item_decimal(row, "weight_each")
            * max(0, _item_int(row, "quantity", 1))
            for row in carried
        ),
        Decimal("0"),
    )

    armors = [row for row in equipped if row.get("item_type") == "armor"]
    shields = [row for row in equipped if row.get("item_type") == "shield"]
    armor = armors[0] if armors else None
    shield = shields[0] if shields else None

    equipment_armor_bonus = 0
    if armor:
        equipment_armor_bonus = (
            _item_int(armor, "armor_bonus")
            + _item_int(armor, "enhancement_bonus")
        )

    equipment_shield_bonus = 0
    if shield:
        equipment_shield_bonus = (
            _item_int(shield, "shield_bonus")
            + _item_int(shield, "enhancement_bonus")
        )

    equipment_penalty = sum(
        _item_int(row, "armor_check_penalty")
        for row in equipped
        if row.get("item_type") in {"armor", "shield"}
    )

    max_dex_candidates = [
        _item_int(row, "max_dex_bonus")
        for row in equipped
        if row.get("item_type") in {"armor", "shield"}
        and row.get("max_dex_bonus") not in (None, "")
    ]

    capacity = carrying_capacity(character)
    if total_weight <= capacity["light_max"]:
        load_key = "light"
        load_max_dex = None
        load_penalty = 0
        load_speed = None
        load_run_multiplier = 4
        next_threshold = capacity["light_max"]
    elif total_weight <= capacity["medium_max"]:
        load_key = "medium"
        load_max_dex = 3
        load_penalty = -3
        load_speed = reduced_speed_for_base(character.get("base_speed", 30))
        load_run_multiplier = 4
        next_threshold = capacity["medium_max"]
    elif total_weight <= capacity["heavy_max"]:
        load_key = "heavy"
        load_max_dex = 1
        load_penalty = -6
        load_speed = reduced_speed_for_base(character.get("base_speed", 30))
        load_run_multiplier = 3
        next_threshold = capacity["heavy_max"]
    elif total_weight <= capacity["lift_off_ground_max"]:
        load_key = "overloaded"
        load_max_dex = 0
        load_penalty = -6
        load_speed = 5
        load_run_multiplier = 0
        next_threshold = capacity["lift_off_ground_max"]
    else:
        load_key = "immovable"
        load_max_dex = 0
        load_penalty = -6
        load_speed = 0
        load_run_multiplier = 0
        next_threshold = capacity["lift_off_ground_max"]

    if load_max_dex is not None:
        max_dex_candidates.append(load_max_dex)

    effective_max_dex = (
        min(max_dex_candidates)
        if max_dex_candidates
        else None
    )

    manual_armor = as_int(character.get("armor_bonus"))
    manual_shield = as_int(character.get("shield_bonus"))
    manual_penalty = as_int(character.get("armor_check_penalty"))
    effective_armor = max(manual_armor, equipment_armor_bonus)
    effective_shield = max(manual_shield, equipment_shield_bonus)
    effective_penalty = min(
        manual_penalty,
        equipment_penalty,
        load_penalty,
    )

    base_speed = max(0, as_int(character.get("base_speed"), 30))
    armor_speed = None
    armor_run_multiplier = 4
    speed_armor_item = None
    for row in equipped:
        if row.get("item_type") != "armor":
            continue
        category = str(row.get("armor_category") or "none")
        applies = bool(row.get("speed_reduction_applies")) or category in {
            "medium",
            "heavy",
        }
        if applies:
            custom_speed = row.get("reduced_speed_override")
            armor_speed = (
                _item_int(row, "reduced_speed_override")
                if custom_speed not in (None, "")
                else reduced_speed_for_base(base_speed)
            )
            speed_armor_item = row
        if category == "heavy":
            armor_run_multiplier = min(armor_run_multiplier, 3)

    ignore_armor_speed = bool(character.get("ignore_armor_speed"))
    ignore_load_speed = bool(character.get("ignore_encumbrance_speed"))
    speed_candidates = [base_speed]
    if armor_speed is not None and not ignore_armor_speed:
        speed_candidates.append(armor_speed)
    if load_speed is not None and not ignore_load_speed:
        speed_candidates.append(load_speed)
    final_speed = min(speed_candidates) if speed_candidates else base_speed

    run_multiplier = min(armor_run_multiplier, load_run_multiplier)
    remaining = max(Decimal("0"), next_threshold - total_weight)

    raw_dex_modifier = ability_modifier_for_character(character, "dex")
    effective_dex_modifier = (
        min(raw_dex_modifier, effective_max_dex)
        if effective_max_dex is not None
        else raw_dex_modifier
    )

    return {
        "equipment": equipment,
        "carried_weight": total_weight,
        "carrying_capacity": capacity,
        "load_key": load_key,
        "load_label": LOAD_LABELS[load_key],
        "remaining_before_next_threshold": remaining,
        "next_threshold": next_threshold,
        "equipped_armor": armor,
        "equipped_shield": shield,
        "equipment_armor_bonus": equipment_armor_bonus,
        "equipment_shield_bonus": equipment_shield_bonus,
        "equipment_armor_check_penalty": equipment_penalty,
        "manual_armor_bonus": manual_armor,
        "manual_shield_bonus": manual_shield,
        "manual_armor_check_penalty": manual_penalty,
        "effective_armor_bonus": effective_armor,
        "effective_shield_bonus": effective_shield,
        "effective_armor_check_penalty": effective_penalty,
        "effective_max_dex_bonus": effective_max_dex,
        "raw_dex_modifier": raw_dex_modifier,
        "effective_ac_dex_modifier": effective_dex_modifier,
        "base_speed": base_speed,
        "armor_speed": armor_speed,
        "load_speed": load_speed,
        "final_speed": final_speed,
        "run_multiplier": run_multiplier,
        "ignore_armor_speed": ignore_armor_speed,
        "ignore_encumbrance_speed": ignore_load_speed,
        "speed_armor_item": speed_armor_item,
    }


def apply_equipment_effects(character, equipment_rows):
    enriched = dict(character)
    effects = equipment_effects(enriched, equipment_rows)
    enriched["equipment_effects"] = effects
    for key in (
        "effective_armor_bonus",
        "effective_shield_bonus",
        "effective_armor_check_penalty",
        "effective_max_dex_bonus",
        "effective_ac_dex_modifier",
        "carried_weight",
        "load_key",
        "load_label",
        "base_speed",
        "final_speed",
        "run_multiplier",
    ):
        enriched[key] = effects[key]
    return enriched


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

    dex_modifier = as_int(
        character.get(
            "effective_ac_dex_modifier",
            ability_modifier_for_character(character, "dex"),
        )
    )
    size_modifier = ac_size_modifier(
        character.get("size_key")
    )
    armor_bonus = as_int(
        character.get(
            "effective_armor_bonus",
            character.get("armor_bonus"),
        )
    )
    shield_bonus = as_int(
        character.get(
            "effective_shield_bonus",
            character.get("shield_bonus"),
        )
    )
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
    dexterity_modifier = as_int(
        character.get(
            "effective_ac_dex_modifier",
            ability_modifier_for_character(character, "dex"),
        )
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
                "effective_armor_check_penalty",
                character.get("armor_check_penalty"),
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




def pathfinder_reference_checks():
    """Tests de référence lisibles utilisés par l’aide intégrée."""

    handle_animal_character = {
        "cha_score": 7,
        "armor_check_penalty": 0,
    }
    handle_animal_skill = {
        "ability_key": "cha",
        "ranks": Decimal("1"),
        "misc_modifier": 0,
        "class_skill": True,
        "armor_check_applies": False,
        "double_armor_penalty": False,
    }
    handle_animal = skill_breakdown(
        handle_animal_character,
        handle_animal_skill,
    )

    untrained_class_skill = skill_breakdown(
        handle_animal_character,
        {
            **handle_animal_skill,
            "ranks": Decimal("0"),
        },
    )

    tiny_cmb = cmb_breakdown(
        {
            "size_key": "tiny",
            "base_attack_bonus": 1,
            "str_score": 10,
            "dex_score": 14,
            "cmb_misc_modifier": 0,
        }
    )

    medium_cmd = cmd_breakdown(
        {
            "size_key": "medium",
            "base_attack_bonus": 3,
            "str_score": 14,
            "dex_score": 12,
            "deflection_bonus": 1,
            "misc_ac_modifier": 0,
            "cmd_misc_modifier": 0,
        }
    )

    checks = [
        {
            "key": "ability_modifier_7",
            "label": "Modificateur de caractéristique 7",
            "expected": -2,
            "actual": ability_modifier(7),
            "formula": "(7 − 10) ÷ 2, arrondi vers le bas = −2",
        },
        {
            "key": "handle_animal",
            "label": "Dressage — Handle Animal",
            "expected": Decimal("2"),
            "actual": handle_animal["total"],
            "formula": (
                "Charisme −2 + rangs 1 + compétence de classe 3 "
                "+ divers 0 = total +2"
            ),
        },
        {
            "key": "class_bonus_requires_rank",
            "label": "Bonus de compétence de classe sans rang",
            "expected": 0,
            "actual": untrained_class_skill["class_bonus"],
            "formula": "0 rang = aucun bonus automatique de +3",
        },
        {
            "key": "tiny_cmb_uses_dexterity",
            "label": "BMO/CMB d’une créature Très petite",
            "expected": 1,
            "actual": tiny_cmb["total"],
            "formula": "BBA 1 + DEX 2 + taille spéciale −2 = +1",
        },
        {
            "key": "medium_cmd",
            "label": "DMD/CMD de référence",
            "expected": 20,
            "actual": medium_cmd["total"],
            "formula": "10 + BBA 3 + FOR 2 + DEX 1 + taille 0 + déviation 1 = 17",
        },
    ]

    # La formule du dernier contrôle est construite explicitement ci-dessus.
    # L’attendu doit suivre le calcul réel de référence.
    checks[-1]["expected"] = Decimal("17")

    for check in checks:
        check["passed"] = (
            Decimal(str(check["actual"]))
            == Decimal(str(check["expected"]))
        )

    return checks


def character_sheet_audit(
    character,
    skills,
):
    """Retourne des avertissements de saisie sans modifier la feuille."""

    warnings = []

    armor_penalty = as_int(
        character.get(
            "effective_armor_check_penalty",
            character.get("armor_check_penalty"),
        )
    )
    if armor_penalty > 0:
        warnings.append(
            {
                "severity": "warning",
                "title": "Pénalité d’armure positive",
                "detail": (
                    "Une pénalité d’armure est normalement inscrite "
                    "avec un signe négatif."
                ),
            }
        )

    for skill in skills:
        breakdown = skill_breakdown(
            character,
            skill,
        )
        french_name = str(
            skill.get("skill_name") or ""
        ).strip()
        english_name = str(
            skill.get("english_name") or ""
        ).strip()
        display_name = (
            f"{french_name} — {english_name}"
            if french_name and english_name
            else french_name or english_name or "Compétence"
        )

        if (
            breakdown["class_bonus"] == 3
            and breakdown["misc_modifier"] == 3
        ):
            warnings.append(
                {
                    "severity": "warning",
                    "title": display_name,
                    "detail": (
                        "Le champ Divers vaut +3 alors que le bonus "
                        "automatique de compétence de classe vaut déjà +3."
                    ),
                }
            )

        if (
            bool(skill.get("trained_only"))
            and as_decimal(skill.get("ranks")) <= 0
        ):
            warnings.append(
                {
                    "severity": "info",
                    "title": display_name,
                    "detail": (
                        "Cette compétence exige une formation, mais "
                        "aucun rang n’est actuellement inscrit."
                    ),
                }
            )

        if (
            bool(skill.get("double_armor_penalty"))
            and not bool(skill.get("armor_check_applies"))
        ):
            warnings.append(
                {
                    "severity": "warning",
                    "title": display_name,
                    "detail": (
                        "La pénalité d’armure est réglée à ×2, mais "
                        "l’option Armure n’est pas activée."
                    ),
                }
            )

    reference_checks = pathfinder_reference_checks()
    failed_reference_checks = [
        check
        for check in reference_checks
        if not check["passed"]
    ]

    if failed_reference_checks:
        warnings.insert(
            0,
            {
                "severity": "error",
                "title": "Contrôle interne des règles",
                "detail": (
                    f"{len(failed_reference_checks)} test(s) de référence "
                    "ne donnent pas le résultat attendu."
                ),
            },
        )

    return {
        "warnings": warnings,
        "reference_checks": reference_checks,
        "reference_checks_passed": (
            len(reference_checks)
            - len(failed_reference_checks)
        ),
        "reference_checks_total": len(reference_checks),
    }
