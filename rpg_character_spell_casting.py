"""Règles pures de lancement guidé des sorts — JDR Phase 15B.

Ce module ne dépend ni de NiceGUI ni de PostgreSQL. Il prépare les informations
utiles au lancement et la conversion spontanée du Clerc sans appliquer
automatiquement de dégâts, soins ou états à une cible.
"""
from __future__ import annotations

from rpg_character_spell_rules import (
    ability_modifier_from_score,
    effective_ability_score,
)


class SpellCastError(ValueError):
    """Erreur métier lors d'un lancement de sort."""


# Un Clerc peut sacrifier un sort préparé normal de niveau suffisant pour lancer
# un sort Cure/Inflict. Les sorts de domaine et les oraisons ne sont pas
# convertibles. Les niveaux 5 à 8 utilisent les variantes de masse.
_SPONTANEOUS = {
    "cure": (
        {
            "key": "cure_light_wounds",
            "name": "Cure Light Wounds",
            "spell_level": 1,
            "summary": "Soigne 1d8 + 1/niveau de lanceur (max +5).",
            "range_text": "Touch",
            "target_text": "Créature touchée",
            "roll_text": "1d8 + min(niveau de lanceur, 5)",
        },
        {
            "key": "cure_moderate_wounds",
            "name": "Cure Moderate Wounds",
            "spell_level": 2,
            "summary": "Soigne 2d8 + 1/niveau de lanceur (max +10).",
            "range_text": "Touch",
            "target_text": "Créature touchée",
            "roll_text": "2d8 + min(niveau de lanceur, 10)",
        },
        {
            "key": "cure_serious_wounds",
            "name": "Cure Serious Wounds",
            "spell_level": 3,
            "summary": "Soigne 3d8 + 1/niveau de lanceur (max +15).",
            "range_text": "Touch",
            "target_text": "Créature touchée",
            "roll_text": "3d8 + min(niveau de lanceur, 15)",
        },
        {
            "key": "cure_critical_wounds",
            "name": "Cure Critical Wounds",
            "spell_level": 4,
            "summary": "Soigne 4d8 + 1/niveau de lanceur (max +20).",
            "range_text": "Touch",
            "target_text": "Créature touchée",
            "roll_text": "4d8 + min(niveau de lanceur, 20)",
        },
        {
            "key": "mass_cure_light_wounds",
            "name": "Mass Cure Light Wounds",
            "spell_level": 5,
            "summary": "Soigne plusieurs créatures avec l'effet de Cure Light Wounds.",
            "target_text": "Plusieurs créatures",
        },
        {
            "key": "mass_cure_moderate_wounds",
            "name": "Mass Cure Moderate Wounds",
            "spell_level": 6,
            "summary": "Soigne plusieurs créatures avec l'effet de Cure Moderate Wounds.",
            "target_text": "Plusieurs créatures",
        },
        {
            "key": "mass_cure_serious_wounds",
            "name": "Mass Cure Serious Wounds",
            "spell_level": 7,
            "summary": "Soigne plusieurs créatures avec l'effet de Cure Serious Wounds.",
            "target_text": "Plusieurs créatures",
        },
        {
            "key": "mass_cure_critical_wounds",
            "name": "Mass Cure Critical Wounds",
            "spell_level": 8,
            "summary": "Soigne plusieurs créatures avec l'effet de Cure Critical Wounds.",
            "target_text": "Plusieurs créatures",
        },
    ),
    "inflict": (
        {
            "key": "inflict_light_wounds",
            "name": "Inflict Light Wounds",
            "spell_level": 1,
            "summary": "Inflige 1d8 + 1/niveau de lanceur (max +5).",
            "range_text": "Touch",
            "target_text": "Créature touchée",
            "roll_text": "1d8 + min(niveau de lanceur, 5)",
        },
        {
            "key": "inflict_moderate_wounds",
            "name": "Inflict Moderate Wounds",
            "spell_level": 2,
            "summary": "Inflige 2d8 + 1/niveau de lanceur (max +10).",
            "range_text": "Touch",
            "target_text": "Créature touchée",
            "roll_text": "2d8 + min(niveau de lanceur, 10)",
        },
        {
            "key": "inflict_serious_wounds",
            "name": "Inflict Serious Wounds",
            "spell_level": 3,
            "summary": "Inflige 3d8 + 1/niveau de lanceur (max +15).",
            "range_text": "Touch",
            "target_text": "Créature touchée",
            "roll_text": "3d8 + min(niveau de lanceur, 15)",
        },
        {
            "key": "inflict_critical_wounds",
            "name": "Inflict Critical Wounds",
            "spell_level": 4,
            "summary": "Inflige 4d8 + 1/niveau de lanceur (max +20).",
            "range_text": "Touch",
            "target_text": "Créature touchée",
            "roll_text": "4d8 + min(niveau de lanceur, 20)",
        },
        {
            "key": "mass_inflict_light_wounds",
            "name": "Mass Inflict Light Wounds",
            "spell_level": 5,
            "summary": "Inflige l'effet d'Inflict Light Wounds à plusieurs créatures.",
            "target_text": "Plusieurs créatures",
        },
        {
            "key": "mass_inflict_moderate_wounds",
            "name": "Mass Inflict Moderate Wounds",
            "spell_level": 6,
            "summary": "Inflige l'effet d'Inflict Moderate Wounds à plusieurs créatures.",
            "target_text": "Plusieurs créatures",
        },
        {
            "key": "mass_inflict_serious_wounds",
            "name": "Mass Inflict Serious Wounds",
            "spell_level": 7,
            "summary": "Inflige l'effet d'Inflict Serious Wounds à plusieurs créatures.",
            "target_text": "Plusieurs créatures",
        },
        {
            "key": "mass_inflict_critical_wounds",
            "name": "Mass Inflict Critical Wounds",
            "spell_level": 8,
            "summary": "Inflige l'effet d'Inflict Critical Wounds à plusieurs créatures.",
            "target_text": "Plusieurs créatures",
        },
    ),
}


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def remaining_prepared_uses(row):
    """Nombre d'utilisations encore disponibles pour une préparation."""
    prepared = max(0, _int((row or {}).get("prepared_count"), 0))
    if _int((row or {}).get("spell_level"), 0) == 0:
        return prepared
    used = max(0, _int((row or {}).get("used_count"), 0))
    return max(0, prepared - min(prepared, used))


def available_prepared_spells(rows):
    """Retourne les sorts qui peuvent encore être lancés aujourd'hui."""
    return [
        dict(row)
        for row in (rows or ())
        if _int(row.get("spell_level"), 0) == 0
        or remaining_prepared_uses(row) > 0
    ]


def spontaneous_cast_options(profile, prepared_row):
    """Options Cure/Inflict pouvant remplacer le sort préparé sélectionné."""
    row = dict(prepared_row or {})
    source_level = _int(row.get("spell_level"), 0)
    if source_level <= 0 or str(row.get("slot_kind") or "normal") == "domain":
        return []

    mode = str((profile or {}).get("spontaneous_mode") or "none").strip().lower()
    if mode not in _SPONTANEOUS:
        return []

    return [
        dict(item)
        for item in _SPONTANEOUS[mode]
        if int(item["spell_level"]) <= source_level
    ]


def _spontaneous_by_key(profile, prepared_row, key):
    wanted = str(key or "").strip()
    for item in spontaneous_cast_options(profile, prepared_row):
        if item["key"] == wanted:
            return item
    raise SpellCastError("Cette conversion spontanée n’est pas permise avec cet emplacement.")


def build_cast_reference(
    *,
    character,
    profile,
    prepared_row,
    catalog_entry=None,
    spontaneous_key=None,
):
    """Construit le résumé affiché avant de confirmer un lancement."""
    row = dict(prepared_row or {})
    source_level = _int(row.get("spell_level"), 0)
    reusable = source_level == 0
    remaining = remaining_prepared_uses(row)
    if not reusable and remaining <= 0:
        raise SpellCastError("Tous les exemplaires préparés de ce sort sont déjà utilisés.")

    catalog = dict(catalog_entry or {})
    conversion = None
    if spontaneous_key:
        conversion = _spontaneous_by_key(profile, row, spontaneous_key)

    if conversion:
        spell = dict(conversion)
        is_spontaneous = True
    else:
        spell = {
            "key": row.get("catalog_key") or catalog.get("key"),
            "name": row.get("spell_name") or catalog.get("name") or "Sort",
            "spell_level": source_level,
            "summary": row.get("summary") or catalog.get("summary") or "",
            "range_text": row.get("range_text") or catalog.get("range_text") or "",
            "duration_text": catalog.get("duration_text") or "",
            "target_text": catalog.get("target_text") or "",
            "saving_throw_text": catalog.get("saving_throw_text") or "",
            "roll_text": catalog.get("roll_text") or "",
            "source_text": row.get("source_text") or catalog.get("source_text") or "",
        }
        is_spontaneous = False

    spell_level = _int(spell.get("spell_level"), source_level)
    ability_key = str((profile or {}).get("ability_key") or "wis")
    score = effective_ability_score(character or {}, ability_key)
    modifier = ability_modifier_from_score(score)
    caster_level = max(1, _int((profile or {}).get("caster_level"), 1))
    save_dc = 10 + spell_level + modifier

    return {
        "name": str(spell.get("name") or "Sort"),
        "spell_level": spell_level,
        "source_spell_name": str(row.get("spell_name") or "Sort préparé"),
        "source_spell_level": source_level,
        "slot_kind": str(row.get("slot_kind") or "normal"),
        "domain_source": row.get("domain_source"),
        "caster_level": caster_level,
        "ability_key": ability_key,
        "ability_score": score,
        "ability_modifier": modifier,
        "save_dc": save_dc,
        "summary": str(spell.get("summary") or ""),
        "range_text": str(spell.get("range_text") or ""),
        "duration_text": str(spell.get("duration_text") or ""),
        "target_text": str(spell.get("target_text") or ""),
        "saving_throw_text": str(spell.get("saving_throw_text") or ""),
        "roll_text": str(spell.get("roll_text") or ""),
        "source_text": str(spell.get("source_text") or row.get("source_text") or ""),
        "notes": str(row.get("notes") or ""),
        "reusable": reusable,
        "is_spontaneous": is_spontaneous,
        "remaining_before": remaining,
        "remaining_after": remaining if reusable else max(0, remaining - 1),
    }
