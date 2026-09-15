"""Règles de préparation des sorts — Clerc Pathfinder 1e.

Phase 15A : emplacements, DD, sorts bonus de Sagesse et créneau de domaine.
Les fonctions sont pures afin d'être testables sans NiceGUI ni PostgreSQL.
"""
from __future__ import annotations

from math import floor


# Emplacements de base du Clerc, créneau de domaine exclu.
# La table officielle indique « +1 » pour le créneau de domaine de chaque
# niveau de sort accessible à partir du niveau 1.
CLERIC_BASE_SLOTS = {
    1:  {0: 3, 1: 1},
    2:  {0: 4, 1: 2},
    3:  {0: 4, 1: 2, 2: 1},
    4:  {0: 4, 1: 3, 2: 2},
    5:  {0: 4, 1: 3, 2: 2, 3: 1},
    6:  {0: 4, 1: 3, 2: 3, 3: 2},
    7:  {0: 4, 1: 4, 2: 3, 3: 2, 4: 1},
    8:  {0: 4, 1: 4, 2: 3, 3: 3, 4: 2},
    9:  {0: 4, 1: 4, 2: 4, 3: 3, 4: 2, 5: 1},
    10: {0: 4, 1: 4, 2: 4, 3: 3, 4: 3, 5: 2},
    11: {0: 4, 1: 4, 2: 4, 3: 4, 4: 3, 5: 2, 6: 1},
    12: {0: 4, 1: 4, 2: 4, 3: 4, 4: 3, 5: 3, 6: 2},
    13: {0: 4, 1: 4, 2: 4, 3: 4, 4: 4, 5: 3, 6: 2, 7: 1},
    14: {0: 4, 1: 4, 2: 4, 3: 4, 4: 4, 5: 3, 6: 3, 7: 2},
    15: {0: 4, 1: 4, 2: 4, 3: 4, 4: 4, 5: 4, 6: 3, 7: 2, 8: 1},
    16: {0: 4, 1: 4, 2: 4, 3: 4, 4: 4, 5: 4, 6: 3, 7: 3, 8: 2},
    17: {0: 4, 1: 4, 2: 4, 3: 4, 4: 4, 5: 4, 6: 4, 7: 3, 8: 2, 9: 1},
    18: {0: 4, 1: 4, 2: 4, 3: 4, 4: 4, 5: 4, 6: 4, 7: 3, 8: 3, 9: 2},
    19: {0: 4, 1: 4, 2: 4, 3: 4, 4: 4, 5: 4, 6: 4, 7: 4, 8: 3, 9: 3},
    20: {0: 4, 1: 4, 2: 4, 3: 4, 4: 4, 5: 4, 6: 4, 7: 4, 8: 4, 9: 4},
}

ABILITY_LABELS = {
    "str": "FOR",
    "dex": "DEX",
    "con": "CON",
    "int": "INT",
    "wis": "SAG",
    "cha": "CHA",
}


class SpellRuleError(ValueError):
    """Erreur métier de préparation des sorts."""


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def effective_ability_score(character, ability_key="wis"):
    key = str(ability_key or "wis").strip().lower()
    if key not in ABILITY_LABELS:
        key = "wis"
    temporary = character.get(f"{key}_temp_score")
    if temporary not in (None, ""):
        return _int(temporary, 10)
    return _int(character.get(f"{key}_score"), 10)


def ability_modifier_from_score(score):
    return floor((_int(score, 10) - 10) / 2)


def bonus_spells_for_modifier(modifier, spell_level):
    """Retourne les emplacements bonus de caractéristique pour un niveau.

    Pathfinder 1e : aucun bonus de niveau 0; pour les niveaux 1+, un
    modificateur au moins égal au niveau donne 1 emplacement, puis un autre
    tous les +4 de modificateur.
    """
    level = _int(spell_level)
    mod = _int(modifier)
    if level <= 0 or mod < level:
        return 0
    return 1 + ((mod - level) // 4)


def cleric_slot_table(cleric_level, ability_score):
    """Construit les emplacements journaliers du Clerc accessibles.

    Le créneau de domaine est séparé des emplacements normaux. Les oraisons
    (niveau 0) n'ont pas de créneau de domaine et ne sont pas dépensées.
    """
    level = max(1, min(20, _int(cleric_level, 1)))
    score = _int(ability_score, 10)
    modifier = ability_modifier_from_score(score)
    base = CLERIC_BASE_SLOTS[level]
    rows = []
    for spell_level in sorted(base):
        base_slots = int(base[spell_level])
        bonus_slots = bonus_spells_for_modifier(modifier, spell_level)
        domain_slots = 0 if spell_level == 0 else 1
        rows.append(
            {
                "spell_level": spell_level,
                "base_slots": base_slots,
                "bonus_slots": bonus_slots,
                "normal_slots": base_slots + bonus_slots,
                "domain_slots": domain_slots,
                "total_slots": base_slots + bonus_slots + domain_slots,
                "save_dc": 10 + spell_level + modifier,
                "required_ability_score": 10 + spell_level,
                "can_cast": score >= 10 + spell_level,
                "orison": spell_level == 0,
            }
        )
    return rows


def max_cleric_spell_level(cleric_level):
    rows = cleric_slot_table(cleric_level, 10)
    return max(row["spell_level"] for row in rows)


def spell_save_dc(character, spell_level, ability_key="wis"):
    score = effective_ability_score(character, ability_key)
    return 10 + _int(spell_level) + ability_modifier_from_score(score)


def prepared_usage_summary(slot_rows, prepared_rows):
    """Fusionne capacité et préparation/utilisation pour l'affichage."""
    by_level = {int(row["spell_level"]): dict(row) for row in slot_rows}
    for row in by_level.values():
        row.update(
            {
                "normal_prepared": 0,
                "normal_used": 0,
                "normal_available": 0,
                "domain_prepared": 0,
                "domain_used": 0,
                "domain_available": 0,
            }
        )

    for prepared in prepared_rows or ():
        level = _int(prepared.get("spell_level"), -1)
        if level not in by_level:
            continue
        count = max(0, _int(prepared.get("prepared_count"), 0))
        used = max(0, min(count, _int(prepared.get("used_count"), 0)))
        if level == 0:
            used = 0
        kind = str(prepared.get("slot_kind") or "normal").strip().lower()
        if kind == "domain":
            by_level[level]["domain_prepared"] += count
            by_level[level]["domain_used"] += used
        else:
            by_level[level]["normal_prepared"] += count
            by_level[level]["normal_used"] += used

    result = []
    for level in sorted(by_level):
        row = by_level[level]
        row["normal_available"] = max(
            0, row["normal_prepared"] - row["normal_used"]
        )
        row["domain_available"] = max(
            0, row["domain_prepared"] - row["domain_used"]
        )
        row["normal_open"] = max(
            0, int(row["normal_slots"]) - row["normal_prepared"]
        )
        row["domain_open"] = max(
            0, int(row["domain_slots"]) - row["domain_prepared"]
        )
        result.append(row)
    return result


def validate_preparation_capacity(
    *,
    slot_rows,
    existing_rows,
    spell_level,
    slot_kind,
    prepared_count,
    exclude_preparation_id=None,
):
    """Valide qu'une ligne préparée tient dans les emplacements disponibles."""
    level = _int(spell_level, -1)
    kind = str(slot_kind or "normal").strip().lower()
    if kind not in {"normal", "domain"}:
        raise SpellRuleError("Le type d’emplacement est invalide.")
    if level == 0 and kind == "domain":
        raise SpellRuleError("Les oraisons n’utilisent pas d’emplacement de domaine.")

    slot = next(
        (row for row in slot_rows if int(row["spell_level"]) == level),
        None,
    )
    if slot is None:
        raise SpellRuleError(
            "Ce niveau de sort n’est pas accessible avec le niveau de Clerc actuel."
        )
    if not slot.get("can_cast", True):
        raise SpellRuleError(
            f"La caractéristique de lancement doit être au moins "
            f"{slot['required_ability_score']} pour préparer un sort de niveau {level}."
        )

    count = max(1, _int(prepared_count, 1))
    already = 0
    for row in existing_rows or ():
        if exclude_preparation_id is not None and str(row.get("id")) == str(
            exclude_preparation_id
        ):
            continue
        if _int(row.get("spell_level"), -1) != level:
            continue
        row_kind = str(row.get("slot_kind") or "normal").strip().lower()
        if row_kind != kind:
            continue
        already += max(0, _int(row.get("prepared_count"), 0))

    limit = int(slot["domain_slots"] if kind == "domain" else slot["normal_slots"])
    if already + count > limit:
        label = "de domaine" if kind == "domain" else "normaux"
        raise SpellRuleError(
            f"Trop d’emplacements {label} préparés au niveau {level} : "
            f"{already + count} pour {limit} disponible(s)."
        )
    return True
