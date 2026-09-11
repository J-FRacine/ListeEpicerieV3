"""Façade publique de l'application Personnages JDR.

L'implémentation NiceGUI principale est isolée dans ``rpg_character_ui.py``.
Cette façade conserve le point d'import historique ``rpg_character``.

Modularisation :
- Identité : ``rpg_character_identity.py``
- Équipement : ``rpg_character_equipment.py``
- Sauvegardes : ``rpg_character_saves.py``
- Progression : ``rpg_character_progression.py``
- Attaques : ``rpg_character_attacks.py``
"""
from __future__ import annotations

import rpg_character_ui as _impl
from rpg_character_attacks import build_attacks_panel
from rpg_character_equipment import build_equipment_panel
from rpg_character_identity import build_identity_panel
from rpg_character_progression import build_progression_panel
from rpg_character_saves import build_saves_panel


def _identity_panel(user_id, character):
    return build_identity_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        race_labels=_impl.RACE_LABELS,
        size_labels=_impl.SIZE_LABELS,
        infer_race_key=_impl.infer_race_key,
        get_race_profile=_impl.get_race_profile,
        update_rpg_character_identity=_impl.update_rpg_character_identity,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
    )


def _equipment_panel(user_id, character):
    return build_equipment_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        list_rpg_equipment=_impl.list_rpg_equipment,
        apply_equipment_effects=_impl.apply_equipment_effects,
        equipment_type_labels=_impl.EQUIPMENT_TYPE_LABELS,
        armor_category_labels=_impl.ARMOR_CATEGORY_LABELS,
        format_number=_impl.format_number,
        format_modifier=_impl.format_modifier,
        update_rpg_equipment_state=_impl.update_rpg_equipment_state,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
        equipment_dialog=_impl._equipment_dialog,
        delete_equipment_dialog=_impl._delete_equipment_dialog,
    )


def _saves_panel(user_id, character):
    return build_saves_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        list_rpg_saves=_impl.list_rpg_saves,
        save_definitions=_impl.SAVE_DEFINITIONS,
        ability_labels=_impl.ABILITY_LABELS,
        ability_modifier_for_character=_impl.ability_modifier_for_character,
        save_total=_impl.save_total,
        format_modifier=_impl.format_modifier,
        as_number=_impl._as_number,
        update_rpg_saves=_impl.update_rpg_saves,
        notify_error=_impl._safe_notify_error,
        calculation_rules_dialog=_impl._calculation_rules_dialog,
    )


def _progression_panel(user_id, character):
    return build_progression_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        list_rpg_skills=_impl.list_rpg_skills,
        list_rpg_level_history=_impl.list_rpg_level_history,
        format_modifier=_impl.format_modifier,
        format_number=_impl.format_number,
        ability_labels=_impl.ABILITY_LABELS,
        ability_long_labels=_impl.ABILITY_LONG_LABELS,
        skill_display_name=_impl._skill_display_name,
        apply_rpg_level_up=_impl.apply_rpg_level_up,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
    )


def _attacks_panel(user_id, character):
    return build_attacks_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        ability_labels=_impl.ABILITY_LABELS,
        attack_total=_impl.attack_total,
        format_modifier=_impl.format_modifier,
        list_rpg_attacks=_impl.list_rpg_attacks,
        create_rpg_attack=_impl.create_rpg_attack,
        update_rpg_attack=_impl.update_rpg_attack,
        delete_rpg_attack=_impl.delete_rpg_attack,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
    )


_impl._identity_panel = _identity_panel
_impl._equipment_panel = _equipment_panel
_impl._saves_panel = _saves_panel
_impl._progression_panel = _progression_panel
_impl._attacks_panel = _attacks_panel

rpg_character_panel = _impl.rpg_character_panel

__all__ = ["rpg_character_panel"]


def __getattr__(name):
    return getattr(_impl, name)


def __dir__():
    return sorted(set(globals()) | set(dir(_impl)))
