"""Façade publique de l'application Personnages JDR.

L'implémentation NiceGUI principale reste dans ``rpg_character_ui.py``.
Les panneaux déjà extraits sont raccordés ici sans changer le point d'import
historique ``rpg_character_panel``.

Diagnostic temporaire Phase 7 :
les erreurs techniques non prévues sont également écrites dans la sortie
standard afin d'apparaître dans le journal Canner.
"""
from __future__ import annotations

import traceback

import rpg_character_data as _data
import rpg_character_ui as _impl
from rpg_character_attacks import build_attacks_panel
from rpg_character_combat import build_combat_panel
from rpg_character_equipment import build_equipment_panel
from rpg_character_equipment_schema import ensure_equipment_schema
from rpg_character_identity import build_identity_panel
from rpg_character_progression import build_progression_panel
from rpg_character_saves import build_saves_panel
from rpg_character_skills import build_skills_panel


_ORIGINAL_SAFE_NOTIFY_ERROR = _impl._safe_notify_error


def _safe_notify_error(error, fallback):
    """Conserve l'affichage actuel et journalise les erreurs inattendues."""
    if not isinstance(error, (ValueError, PermissionError)):
        print(
            "[JDR] ERREUR TECHNIQUE NON GÉRÉE",
            f"{type(error).__name__}: {error}",
            flush=True,
        )
        traceback.print_exception(
            type(error),
            error,
            error.__traceback__,
        )

    return _ORIGINAL_SAFE_NOTIFY_ERROR(error, fallback)


def _ensure_equipment_schema():
    ensure_equipment_schema(get_connection=_data.get_connection)


def _get_rpg_character(user_id, character_id):
    # La fiche lit l'équipement avant même d'afficher l'onglet Équipement.
    # La migration doit donc être faite avant le chargement du personnage.
    _ensure_equipment_schema()
    return _data.get_rpg_character(user_id, character_id)


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


def _combat_panel(user_id, character):
    _ensure_equipment_schema()
    return build_combat_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        list_rpg_equipment=_impl.list_rpg_equipment,
        ability_labels=_impl.ABILITY_LABELS,
        ability_long_labels=_impl.ABILITY_LONG_LABELS,
        ability_modifier=_impl.ability_modifier,
        format_modifier=_impl.format_modifier,
        apply_equipment_effects=_impl.apply_equipment_effects,
        armor_class_total=_impl.armor_class_total,
        touch_armor_class=_impl.touch_armor_class,
        flat_footed_armor_class=_impl.flat_footed_armor_class,
        initiative_total=_impl.initiative_total,
        cmb_total=_impl.cmb_total,
        cmd_total=_impl.cmd_total,
        format_number=_impl.format_number,
        update_rpg_character_combat=_impl.update_rpg_character_combat,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
        calculation_rules_dialog=_impl._calculation_rules_dialog,
    )


def _equipment_panel(user_id, character):
    _ensure_equipment_schema()
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


def _skills_panel(user_id, character):
    return build_skills_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        list_rpg_skills=_impl.list_rpg_skills,
        character_sheet_audit=_impl.character_sheet_audit,
        create_custom_rpg_skill=_impl.create_custom_rpg_skill,
        delete_custom_rpg_skill=_impl.delete_custom_rpg_skill,
        update_rpg_skills=_impl.update_rpg_skills,
        skill_total=_impl.skill_total,
        skill_breakdown=_impl.skill_breakdown,
        format_number=_impl.format_number,
        ability_labels=_impl.ABILITY_LABELS,
        skill_dialog=_impl._skill_dialog,
        skill_display_name=_impl._skill_display_name,
        skill_breakdown_text=_impl._skill_breakdown_text,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
        calculation_rules_dialog=_impl._calculation_rules_dialog,
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


# Le diagnostic est branché d'abord afin que les anciens dialogues encore
# présents dans rpg_character_ui.py l'utilisent aussi.
_impl._safe_notify_error = _safe_notify_error
_impl.get_rpg_character = _get_rpg_character
_impl._identity_panel = _identity_panel
_impl._combat_panel = _combat_panel
_impl._equipment_panel = _equipment_panel
_impl._saves_panel = _saves_panel
_impl._progression_panel = _progression_panel
_impl._skills_panel = _skills_panel
_impl._attacks_panel = _attacks_panel

rpg_character_panel = _impl.rpg_character_panel

__all__ = ["rpg_character_panel"]


def __getattr__(name):
    return getattr(_impl, name)


def __dir__():
    return sorted(set(globals()) | set(dir(_impl)))
