"""Façade publique de l'application Personnages JDR."""
from __future__ import annotations

import rpg_character_catalog as _catalog
import rpg_character_data as _data
import rpg_character_rules as _rules
import rpg_character_ui as _impl
from rpg_character_attacks import build_attacks_panel
from rpg_character_deities_catalog import DEITY_PROFILES
from rpg_character_combat import build_combat_panel
from rpg_character_equipment import build_equipment_panel
from rpg_character_equipment_dialogs import (
    open_delete_equipment_dialog,
    open_equipment_dialog,
)
from rpg_character_equipment_schema import ensure_equipment_schema
from rpg_character_feats import build_feats_panel
from rpg_character_feats_catalog import (
    FEAT_KIND_LABELS,
    FEAT_TEMPLATES,
    SAVE_TARGET_LABELS,
)
from rpg_character_feats_data import (
    create_rpg_feat,
    delete_rpg_feat,
    list_rpg_feats,
    update_rpg_feat,
)
from rpg_character_faith import build_faith_panel
from rpg_character_faith_data import (
    get_rpg_faith,
    update_rpg_faith,
)
from rpg_character_identity import build_identity_panel
from rpg_character_portrait import build_portrait_block
from rpg_character_portrait_data import (
    delete_rpg_portrait,
    get_rpg_portrait,
    save_rpg_portrait,
)
from rpg_character_portrait_images import (
    normalize_portrait,
    portrait_to_data_url,
    read_upload_event,
)
from rpg_character_progression import build_progression_panel
from rpg_character_rules_dialog import open_calculation_rules_dialog
from rpg_character_saves import build_saves_panel
from rpg_character_skill_dialogs import (
    open_skill_dialog,
    skill_breakdown_text,
    skill_display_name,
)
from rpg_character_skills import build_skills_panel
from rpg_character_weapon_catalog import (
    ATTACK_GRIP_LABELS,
    WEAPON_HANDEDNESS_LABELS,
    WEAPON_TEMPLATES,
    weapon_template_values,
)
from rpg_character_weapon_data import (
    attack_weapon_links,
    clear_weapon_details,
    linked_attacks_by_equipment,
    save_weapon_details,
    set_attack_weapon_link,
    weapon_details_by_equipment,
)
from rpg_character_weapon_rules import (
    attack_defaults_from_weapon,
    merge_attacks_with_weapons,
    merge_equipment_with_weapon_details,
)
from rpg_character_weapon_schema import ensure_weapon_schema


def _as_number(value, default=0):
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _ensure_equipment_schema():
    ensure_equipment_schema(
        get_connection=_data.get_connection
    )


def _ensure_weapon_schema():
    _ensure_equipment_schema()
    ensure_weapon_schema(
        get_connection=_data.get_connection
    )


def _list_rpg_equipment(user_id, character_id):
    _ensure_weapon_schema()
    return merge_equipment_with_weapon_details(
        _data.list_rpg_equipment(
            user_id,
            character_id,
        ),
        weapon_details_by_equipment(
            user_id,
            character_id,
        ),
        linked_attacks_by_equipment(
            user_id,
            character_id,
        ),
    )


def _list_rpg_attacks(user_id, character_id):
    _ensure_weapon_schema()
    return merge_attacks_with_weapons(
        _data.list_rpg_attacks(
            user_id,
            character_id,
        ),
        attack_weapon_links(
            user_id,
            character_id,
        ),
    )


def _save_rpg_equipment(
    user_id,
    character_id,
    values,
    equipment_id=None,
):
    _ensure_weapon_schema()
    payload = dict(values or {})
    item_type = str(
        payload.get("item_type") or "gear"
    ).strip()
    wanted_equipped = bool(
        payload.get("equipped")
    )

    # Évite le vieux cas NULL non typé lors de la création
    # d'une nouvelle armure ou d'un nouveau bouclier déjà équipé.
    deferred_equip = (
        equipment_id is None
        and wanted_equipped
        and item_type in {"armor", "shield"}
    )
    if deferred_equip:
        payload["equipped"] = False

    saved_id = _data.save_rpg_equipment(
        user_id,
        character_id,
        payload,
        equipment_id=equipment_id,
    )

    if deferred_equip:
        _data.update_rpg_equipment_state(
            user_id,
            character_id,
            saved_id,
            carried=bool(
                values.get("carried", True)
            ),
            equipped=True,
        )

    if item_type == "weapon":
        save_weapon_details(
            user_id,
            character_id,
            saved_id,
            values,
        )
    else:
        clear_weapon_details(
            user_id,
            character_id,
            saved_id,
        )

    return saved_id


def _create_rpg_attack(
    user_id,
    character_id,
    values,
):
    _ensure_weapon_schema()
    payload = dict(values or {})
    linked_equipment_id = payload.pop(
        "linked_equipment_id",
        None,
    )
    grip_mode = payload.pop(
        "grip_mode",
        "default",
    )
    attack_id = _data.create_rpg_attack(
        user_id,
        character_id,
        payload,
    )
    try:
        set_attack_weapon_link(
            user_id,
            character_id,
            attack_id,
            linked_equipment_id,
            grip_mode=grip_mode,
        )
    except Exception:
        _data.delete_rpg_attack(
            user_id,
            character_id,
            attack_id,
        )
        raise
    return attack_id


def _update_rpg_attack(
    user_id,
    character_id,
    attack_id,
    values,
):
    _ensure_weapon_schema()
    payload = dict(values or {})
    linked_equipment_id = payload.pop(
        "linked_equipment_id",
        None,
    )
    grip_mode = payload.pop(
        "grip_mode",
        "default",
    )
    _data.update_rpg_attack(
        user_id,
        character_id,
        attack_id,
        payload,
    )
    set_attack_weapon_link(
        user_id,
        character_id,
        attack_id,
        linked_equipment_id,
        grip_mode=grip_mode,
    )


def _create_attack_from_weapon(
    user_id,
    character,
    equipment_row,
):
    _ensure_weapon_schema()
    equipment = _list_rpg_equipment(
        user_id,
        character["id"],
    )
    try:
        weapon = next(
            row
            for row in equipment
            if int(row["id"])
            == int(equipment_row["id"])
            and row.get("item_type") == "weapon"
        )
    except StopIteration as error:
        raise ValueError(
            "Cette arme n’existe plus."
        ) from error

    linked = list(
        weapon.get("linked_attacks") or ()
    )
    if linked:
        return int(
            linked[0]["attack_id"]
        ), False

    attack_id = _create_rpg_attack(
        user_id,
        character["id"],
        attack_defaults_from_weapon(
            weapon
        ),
    )
    return attack_id, True


def _get_rpg_character(user_id, character_id):
    _ensure_weapon_schema()
    return _data.get_rpg_character(
        user_id,
        character_id,
    )


def _skill_display_name(
    french_name,
    english_name,
):
    return skill_display_name(
        french_name,
        english_name,
    )


def _skill_breakdown_text(breakdown):
    return skill_breakdown_text(
        breakdown,
        ability_labels=_rules.ABILITY_LABELS,
        format_modifier=_rules.format_modifier,
    )


def _skill_dialog(
    user_id,
    character,
    on_saved,
):
    return open_skill_dialog(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        on_saved=on_saved,
        ability_labels=_rules.ABILITY_LABELS,
        ability_long_labels=_rules.ABILITY_LONG_LABELS,
        create_custom_rpg_skill=_data.create_custom_rpg_skill,
        notify_error=_impl._safe_notify_error,
    )


def _equipment_dialog(
    user_id,
    character,
    row=None,
    preset_key=None,
):
    _ensure_weapon_schema()
    return open_equipment_dialog(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        row=row,
        preset_key=preset_key,
        equipment_type_labels=_catalog.EQUIPMENT_TYPE_LABELS,
        armor_category_labels=_catalog.ARMOR_CATEGORY_LABELS,
        weapon_handedness_labels=WEAPON_HANDEDNESS_LABELS,
        weapon_templates=WEAPON_TEMPLATES,
        weapon_template_values=weapon_template_values,
        save_rpg_equipment=_save_rpg_equipment,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
    )


def _delete_equipment_dialog(
    user_id,
    character,
    row,
):
    return open_delete_equipment_dialog(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        row=row,
        delete_rpg_equipment=_data.delete_rpg_equipment,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
    )


def _calculation_rules_dialog(user_id, character):
    return open_calculation_rules_dialog(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        list_rpg_saves=_data.list_rpg_saves,
        list_rpg_skills=_data.list_rpg_skills,
        list_rpg_attacks=_list_rpg_attacks,
        armor_class_breakdown=_rules.armor_class_breakdown,
        initiative_breakdown=_rules.initiative_breakdown,
        cmb_breakdown=_rules.cmb_breakdown,
        cmd_breakdown=_rules.cmd_breakdown,
        equipment_effects=_rules.equipment_effects,
        format_number=_rules.format_number,
        format_modifier=_rules.format_modifier,
        ability_labels=_rules.ABILITY_LABELS,
        ability_modifier_for_character=
            _rules.ability_modifier_for_character,
        save_breakdown=_rules.save_breakdown,
        save_definitions=_rules.SAVE_DEFINITIONS,
        pathfinder_reference_checks=
            _rules.pathfinder_reference_checks,
        skill_breakdown=_rules.skill_breakdown,
        attack_breakdown=_rules.attack_breakdown,
        skill_display_name=_skill_display_name,
    )


def _portrait_block(user_id, character):
    return build_portrait_block(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        get_rpg_portrait=get_rpg_portrait,
        save_rpg_portrait=save_rpg_portrait,
        delete_rpg_portrait=delete_rpg_portrait,
        normalize_portrait=normalize_portrait,
        portrait_to_data_url=portrait_to_data_url,
        read_upload_event=read_upload_event,
        notify_error=_impl._safe_notify_error,
    )


def _identity_panel(user_id, character):
    return build_identity_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        race_labels=_catalog.RACE_LABELS,
        size_labels=_rules.SIZE_LABELS,
        infer_race_key=_catalog.infer_race_key,
        get_race_profile=_catalog.get_race_profile,
        update_rpg_character_identity=
            _data.update_rpg_character_identity,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
    )


def _faith_panel(user_id, character):
    return build_faith_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        get_rpg_faith=get_rpg_faith,
        update_rpg_faith=update_rpg_faith,
        deity_profiles=DEITY_PROFILES,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
    )


def _progression_panel(user_id, character):
    return build_progression_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        list_rpg_skills=_data.list_rpg_skills,
        list_rpg_level_history=_data.list_rpg_level_history,
        format_modifier=_rules.format_modifier,
        format_number=_rules.format_number,
        ability_labels=_rules.ABILITY_LABELS,
        ability_long_labels=_rules.ABILITY_LONG_LABELS,
        skill_display_name=_skill_display_name,
        apply_rpg_level_up=_data.apply_rpg_level_up,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
    )


def _feats_panel(user_id, character):
    return build_feats_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        list_rpg_feats=list_rpg_feats,
        list_rpg_attacks=_list_rpg_attacks,
        create_rpg_feat=create_rpg_feat,
        update_rpg_feat=update_rpg_feat,
        delete_rpg_feat=delete_rpg_feat,
        feat_kind_labels=FEAT_KIND_LABELS,
        save_target_labels=SAVE_TARGET_LABELS,
        feat_templates=FEAT_TEMPLATES,
        format_modifier=_rules.format_modifier,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
    )


def _combat_panel(user_id, character):
    _ensure_weapon_schema()
    return build_combat_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        list_rpg_equipment=_list_rpg_equipment,
        ability_labels=_rules.ABILITY_LABELS,
        ability_long_labels=_rules.ABILITY_LONG_LABELS,
        ability_modifier=_rules.ability_modifier,
        format_modifier=_rules.format_modifier,
        apply_equipment_effects=_rules.apply_equipment_effects,
        armor_class_total=_rules.armor_class_total,
        touch_armor_class=_rules.touch_armor_class,
        flat_footed_armor_class=_rules.flat_footed_armor_class,
        initiative_total=_rules.initiative_total,
        cmb_total=_rules.cmb_total,
        cmd_total=_rules.cmd_total,
        format_number=_rules.format_number,
        update_rpg_character_combat=
            _data.update_rpg_character_combat,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
        calculation_rules_dialog=_calculation_rules_dialog,
    )


def _equipment_panel(user_id, character):
    _ensure_weapon_schema()
    return build_equipment_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        list_rpg_equipment=_list_rpg_equipment,
        apply_equipment_effects=_rules.apply_equipment_effects,
        equipment_type_labels=_catalog.EQUIPMENT_TYPE_LABELS,
        armor_category_labels=_catalog.ARMOR_CATEGORY_LABELS,
        weapon_handedness_labels=WEAPON_HANDEDNESS_LABELS,
        format_number=_rules.format_number,
        format_modifier=_rules.format_modifier,
        update_rpg_equipment_state=_data.update_rpg_equipment_state,
        create_attack_from_weapon=_create_attack_from_weapon,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
        equipment_dialog=_equipment_dialog,
        delete_equipment_dialog=_delete_equipment_dialog,
    )


def _saves_panel(user_id, character):
    return build_saves_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        list_rpg_saves=_data.list_rpg_saves,
        save_definitions=_rules.SAVE_DEFINITIONS,
        ability_labels=_rules.ABILITY_LABELS,
        ability_modifier_for_character=
            _rules.ability_modifier_for_character,
        save_total=_rules.save_total,
        format_modifier=_rules.format_modifier,
        as_number=_as_number,
        update_rpg_saves=_data.update_rpg_saves,
        notify_error=_impl._safe_notify_error,
        calculation_rules_dialog=_calculation_rules_dialog,
    )


def _skills_panel(user_id, character):
    return build_skills_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        list_rpg_skills=_data.list_rpg_skills,
        character_sheet_audit=_rules.character_sheet_audit,
        create_custom_rpg_skill=_data.create_custom_rpg_skill,
        delete_custom_rpg_skill=_data.delete_custom_rpg_skill,
        update_rpg_skills=_data.update_rpg_skills,
        skill_total=_rules.skill_total,
        skill_breakdown=_rules.skill_breakdown,
        format_number=_rules.format_number,
        ability_labels=_rules.ABILITY_LABELS,
        skill_dialog=_skill_dialog,
        skill_display_name=_skill_display_name,
        skill_breakdown_text=_skill_breakdown_text,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
        calculation_rules_dialog=_calculation_rules_dialog,
    )


def _attacks_panel(user_id, character):
    _ensure_weapon_schema()
    return build_attacks_panel(
        ui=_impl.ui,
        user_id=user_id,
        character=character,
        ability_labels=_rules.ABILITY_LABELS,
        attack_total=_rules.attack_total,
        format_modifier=_rules.format_modifier,
        list_rpg_attacks=_list_rpg_attacks,
        list_rpg_equipment=_list_rpg_equipment,
        weapon_handedness_labels=WEAPON_HANDEDNESS_LABELS,
        attack_grip_labels=ATTACK_GRIP_LABELS,
        create_rpg_attack=_create_rpg_attack,
        update_rpg_attack=_update_rpg_attack,
        delete_rpg_attack=_data.delete_rpg_attack,
        notify_error=_impl._safe_notify_error,
        character_url=_impl._character_url,
    )


_impl.get_rpg_character = _get_rpg_character
# Combat rapide utilise ce nom global de rpg_character_ui à l'ouverture.
_impl.list_rpg_attacks = _list_rpg_attacks
_impl._skill_display_name = _skill_display_name
_impl._skill_breakdown_text = _skill_breakdown_text
_impl._skill_dialog = _skill_dialog
_impl._equipment_dialog = _equipment_dialog
_impl._delete_equipment_dialog = _delete_equipment_dialog
_impl._calculation_rules_dialog = _calculation_rules_dialog
_impl._portrait_block = _portrait_block
_impl._identity_panel = _identity_panel
_impl._faith_panel = _faith_panel
_impl._progression_panel = _progression_panel
_impl._feats_panel = _feats_panel
_impl._combat_panel = _combat_panel
_impl._equipment_panel = _equipment_panel
_impl._saves_panel = _saves_panel
_impl._skills_panel = _skills_panel
_impl._attacks_panel = _attacks_panel

rpg_character_panel = _impl.rpg_character_panel

__all__ = ["rpg_character_panel"]


def __getattr__(name):
    return getattr(_impl, name)


def __dir__():
    return sorted(set(globals()) | set(dir(_impl)))
