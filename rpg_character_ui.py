"""Coquille NiceGUI principale de la fiche Personnage JDR.

Les panneaux fonctionnels sont dans des modules dédiés et sont raccordés par
``rpg_character.py``. Ce fichier conserve la structure générale de la fiche,
la création/suppression de personnage et Combat rapide.
"""
from __future__ import annotations

from nicegui import ui

from rpg_character_creation import (
    build_character_creation_panel,
    open_new_character_dialog,
)
from rpg_combat_session import build_combat_session
from rpg_character_catalog import (
    RACE_LABELS,
    get_race_profile,
)
from rpg_character_data import (
    create_rpg_character,
    delete_rpg_character,
    get_rpg_character,
    list_rpg_attacks,
    list_rpg_characters,
    list_rpg_equipment,
    list_rpg_saves,
    list_rpg_skills,
    update_rpg_character_combat,
    update_rpg_character_identity,
    update_rpg_saves,
    update_rpg_skills,
)
from rpg_character_feats_data import list_rpg_feats
from rpg_character_feats_rules import collect_feat_combat_effects
from rpg_character_spell_catalog import catalog_by_key as spell_catalog_by_key
from rpg_character_spell_data import (
    cast_prepared_spell,
    get_spellcasting_profile,
    list_prepared_spells,
)
from rpg_character_rules import (
    ABILITY_LABELS,
    ABILITY_LONG_LABELS,
    SAVE_DEFINITIONS,
    SIZE_LABELS,
    ability_modifier,
    apply_equipment_effects,
    armor_class_total,
    attack_total,
    character_sheet_audit,
    cmb_total,
    cmd_total,
    flat_footed_armor_class,
    format_modifier,
    initiative_total,
    save_total,
    touch_armor_class,
)
from rpg_character_styles import install_rpg_styles


install_rpg_styles(ui)


def _safe_notify_error(error, fallback):
    if isinstance(error, (ValueError, PermissionError)):
        message = str(error)
        notification_type = "warning"
    else:
        message = fallback
        notification_type = "negative"
    ui.notify(message, type=notification_type)


def _character_url(character_id, section=None):
    url = f"/?tab=jdr&character={character_id}"
    if section:
        url += f"&section={section}"
    return url


def _create_character_dialog(user_id, player_default):
    open_new_character_dialog(
        ui=ui,
        user_id=user_id,
        player_default=player_default,
        create_rpg_character=create_rpg_character,
        character_url=_character_url,
        notify_error=_safe_notify_error,
    )


def _delete_character_dialog(user_id, character):
    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-md p-5"):
            ui.label("Supprimer le personnage?").classes(
                "text-xl font-bold"
            )
            ui.label(character["character_name"]).classes("font-bold")
            ui.label(
                "Cette suppression est définitive. Les sauvegardes, "
                "compétences, dons et attaques seront supprimés."
            ).classes("text-sm text-negative")

            def confirm():
                try:
                    delete_rpg_character(
                        user_id,
                        character["id"],
                    )
                except Exception as error:
                    _safe_notify_error(
                        error,
                        "Le personnage n’a pas pu être supprimé.",
                    )
                    return

                dialog.close()
                ui.notify("Personnage supprimé.", type="positive")
                ui.navigate.to("/?tab=jdr")

            with ui.row().classes("w-full justify-end gap-2 mt-3"):
                ui.button(
                    "Annuler",
                    on_click=dialog.close,
                ).props("flat")
                ui.button(
                    "Supprimer",
                    icon="delete",
                    on_click=confirm,
                ).props("color=negative")
    dialog.open()


def rpg_character_panel(
    current_user,
    *,
    selected_character_id=None,
    initial_section="identite",
    show_heading=True,
):
    user_id = current_user["id"]
    characters = list_rpg_characters(user_id)

    if show_heading:
        with ui.row().classes(
            "w-full items-start justify-between gap-3 flex-wrap"
        ):
            with ui.column().classes("gap-0"):
                ui.label("Personnages JDR").classes(
                    "text-2xl font-bold"
                )
                ui.label(
                    "Feuille interactive Pathfinder dans l’univers Ravenloft."
                ).classes("text-sm jf-muted")
            ui.icon("casino").classes("text-4xl text-primary")

    with ui.element("div").classes("jf-rpg-private"):
        with ui.row().classes("items-start gap-2 flex-nowrap"):
            ui.icon("lock").classes("text-xl shrink-0")
            ui.label(
                "Chaque personnage est privé à son propriétaire. "
                "Le partage entre campagnes et joueurs sera ajouté "
                "dans une phase ultérieure avec invitation et consentement."
            ).classes("text-sm")

    if not characters:
        with ui.card().classes(
            "w-full p-7 items-center text-center"
        ):
            ui.icon("person_add").classes(
                "text-6xl text-gray-400"
            )
            ui.label("Créez votre premier personnage").classes(
                "text-xl font-bold"
            )
            ui.label(
                "La feuille comprend la création guidée, l’identité, "
                "la foi, les sorts, la progression, les dons, le combat, "
                "l’équipement, les sauvegardes, les compétences et les attaques."
            ).classes("text-sm jf-muted max-w-xl")
            ui.button(
                "Créer un personnage",
                icon="person_add",
                on_click=lambda: _create_character_dialog(
                    user_id,
                    current_user["display_name"],
                ),
            ).props("color=primary")
        return

    character_ids = {
        int(character["id"])
        for character in characters
    }
    try:
        requested_id = int(selected_character_id)
    except (TypeError, ValueError):
        requested_id = None

    current_id = (
        requested_id
        if requested_id in character_ids
        else int(characters[0]["id"])
    )

    character = get_rpg_character(user_id, current_id)

    combat_session = build_combat_session(
        ui=ui,
        user_id=user_id,
        character=character,
        list_rpg_attacks=list_rpg_attacks,
        list_rpg_saves=list_rpg_saves,
        list_rpg_feats=list_rpg_feats,
        collect_feat_combat_effects=collect_feat_combat_effects,
        get_spellcasting_profile=get_spellcasting_profile,
        list_prepared_spells=list_prepared_spells,
        cast_prepared_spell=cast_prepared_spell,
        spell_catalog_by_key=spell_catalog_by_key,
        update_rpg_character_combat=update_rpg_character_combat,
        armor_class_total=armor_class_total,
        touch_armor_class=touch_armor_class,
        flat_footed_armor_class=flat_footed_armor_class,
        initiative_total=initiative_total,
        cmb_total=cmb_total,
        cmd_total=cmd_total,
        attack_total=attack_total,
        save_total=save_total,
        format_modifier=format_modifier,
        character_url=_character_url,
        notify_error=_safe_notify_error,
    )

    def open_combat_session():
        try:
            fresh = get_rpg_character(user_id, current_id)
        except Exception as error:
            _safe_notify_error(
                error,
                "Le personnage n’a pas pu être rechargé.",
            )
            return
        character.clear()
        character.update(fresh)
        combat_session.open()

    with ui.card().classes("w-full p-4"):
        with ui.row().classes(
            "w-full items-end gap-3 flex-wrap"
        ):
            character_select = ui.select(
                {
                    int(item["id"]): item["character_name"]
                    for item in characters
                },
                value=current_id,
                label="Personnage actif",
            ).classes("grow min-w-[220px]")

            character_select.on_value_change(
                lambda event: ui.navigate.to(
                    _character_url(event.value)
                )
            )

            ui.button(
                "Nouveau",
                icon="person_add",
                on_click=lambda: _create_character_dialog(
                    user_id,
                    current_user["display_name"],
                ),
            ).props("outline color=primary")

            ui.button(
                "Combat rapide",
                icon="sports_martial_arts",
                on_click=open_combat_session,
            ).props("color=primary")

            ui.button(
                icon="delete",
                on_click=lambda: _delete_character_dialog(
                    user_id,
                    character,
                ),
            ).props(
                "flat round color=negative"
            ).tooltip("Supprimer le personnage actif")

    with ui.element("div").classes("jf-rpg-character-banner"):
        with ui.row().classes(
            "w-full items-start justify-between gap-4 flex-wrap"
        ):
            _portrait_block(user_id, character)

            with ui.column().classes("gap-0 grow min-w-0"):
                ui.label(character["character_name"]).classes(
                    "text-2xl font-bold"
                )
                ui.label(
                    " · ".join(
                        value
                        for value in (
                            character["race"],
                            (
                                (
                                    f"{character['class_name']}"
                                    + (
                                        f" — {character.get('subclass_name')}"
                                        if character.get("subclass_name")
                                        else ""
                                    )
                                    + f" niveau {character['character_level']}"
                                )
                                if character["class_name"]
                                else f"Niveau {character['character_level']}"
                            ),
                            character["campaign"],
                        )
                        if value
                    )
                ).classes("text-sm opacity-90")

            with ui.row().classes("gap-4 flex-wrap"):
                with ui.column().classes("gap-0"):
                    ui.label("PV").classes("text-xs opacity-80")
                    ui.label(
                        f"{character['current_hp']}/{character['max_hp']}"
                    ).classes("text-xl font-bold")
                with ui.column().classes("gap-0"):
                    ui.label("CA").classes("text-xs opacity-80")
                    ui.label(
                        str(armor_class_total(character))
                    ).classes("text-xl font-bold")
                with ui.column().classes("gap-0"):
                    ui.label("Initiative").classes(
                        "text-xs opacity-80"
                    )
                    ui.label(
                        format_modifier(
                            initiative_total(character)
                        )
                    ).classes("text-xl font-bold")

    with ui.tabs().props(
        "dense no-caps inline-label "
        "mobile-arrows outside-arrows align=left"
    ).classes("jf-rpg-main-tabs") as tabs:
        creation_tab = ui.tab(
            "Création guidée",
            icon="auto_fix_high",
        )
        identity_tab = ui.tab("Identité", icon="badge")
        faith_tab = ui.tab("Foi", icon="church")
        spells_tab = ui.tab("Sorts", icon="auto_stories")
        progression_tab = ui.tab(
            "Progression",
            icon="trending_up",
        )
        feats_tab = ui.tab("Dons", icon="military_tech")
        combat_tab = ui.tab("Combat", icon="shield")
        equipment_tab = ui.tab("Équipement", icon="backpack")
        saves_tab = ui.tab("Sauvegardes", icon="security")
        skills_tab = ui.tab("Compétences", icon="psychology")
        attacks_tab = ui.tab(
            "Attaques",
            icon="sports_martial_arts",
        )

    normalized_section = str(
        initial_section or "identite"
    ).strip().lower()

    initial_tab = {
        "creation": creation_tab,
        "identite": identity_tab,
        "identity": identity_tab,
        "foi": faith_tab,
        "faith": faith_tab,
        "domaines": faith_tab,
        "domains": faith_tab,
        "sorts": spells_tab,
        "spell": spells_tab,
        "spells": spells_tab,
        "magie": spells_tab,
        "progression": progression_tab,
        "niveau": progression_tab,
        "level": progression_tab,
        "dons": feats_tab,
        "don": feats_tab,
        "feats": feats_tab,
        "feat": feats_tab,
        "combat": combat_tab,
        "caracteristiques": combat_tab,
        "equipement": equipment_tab,
        "équipement": equipment_tab,
        "equipment": equipment_tab,
        "sauvegardes": saves_tab,
        "saves": saves_tab,
        "competences": skills_tab,
        "skills": skills_tab,
        "attaques": attacks_tab,
        "attacks": attacks_tab,
    }.get(normalized_section, identity_tab)

    with ui.tab_panels(
        tabs,
        value=initial_tab,
    ).classes("w-full bg-transparent"):
        with ui.tab_panel(creation_tab).classes("px-0"):
            build_character_creation_panel(
                ui=ui,
                user_id=user_id,
                character=character,
                get_rpg_character=get_rpg_character,
                update_rpg_character_identity=update_rpg_character_identity,
                update_rpg_character_combat=update_rpg_character_combat,
                list_rpg_saves=list_rpg_saves,
                update_rpg_saves=update_rpg_saves,
                list_rpg_skills=list_rpg_skills,
                update_rpg_skills=update_rpg_skills,
                list_rpg_equipment=list_rpg_equipment,
                list_rpg_attacks=list_rpg_attacks,
                character_sheet_audit=character_sheet_audit,
                apply_equipment_effects=apply_equipment_effects,
                armor_class_total=armor_class_total,
                touch_armor_class=touch_armor_class,
                flat_footed_armor_class=flat_footed_armor_class,
                initiative_total=initiative_total,
                cmb_total=cmb_total,
                cmd_total=cmd_total,
                ability_modifier=ability_modifier,
                format_modifier=format_modifier,
                get_race_profile=get_race_profile,
                race_labels=RACE_LABELS,
                size_labels=SIZE_LABELS,
                ability_labels=ABILITY_LABELS,
                ability_long_labels=ABILITY_LONG_LABELS,
                save_definitions=SAVE_DEFINITIONS,
                character_url=_character_url,
                notify_error=_safe_notify_error,
            )

        with ui.tab_panel(identity_tab).classes("px-0"):
            _identity_panel(user_id, character)

        with ui.tab_panel(faith_tab).classes("px-0"):
            _faith_panel(user_id, character)

        with ui.tab_panel(spells_tab).classes("px-0"):
            _spells_panel(user_id, character)

        with ui.tab_panel(progression_tab).classes("px-0"):
            _progression_panel(user_id, character)

        with ui.tab_panel(feats_tab).classes("px-0"):
            _feats_panel(user_id, character)

        with ui.tab_panel(combat_tab).classes("px-0"):
            _combat_panel(user_id, character)

        with ui.tab_panel(equipment_tab).classes("px-0"):
            _equipment_panel(user_id, character)

        with ui.tab_panel(saves_tab).classes("px-0"):
            _saves_panel(user_id, character)

        with ui.tab_panel(skills_tab).classes("px-0"):
            _skills_panel(user_id, character)

        with ui.tab_panel(attacks_tab).classes("px-0"):
            _attacks_panel(user_id, character)

    with ui.element("div").classes("jf-rpg-help"):
        ui.label("Foi, sorts et dons structurés").classes("font-bold")
        ui.label(
            "Les dons possèdent leur propre onglet et peuvent alimenter "
            "Combat rapide. La section Foi conserve maintenant la divinité, "
            "les deux domaines et leurs sous-domaines. L’onglet Sorts suit "
            "maintenant la préparation du Clerc et ses emplacements, sans "
            "modifier automatiquement les effets de combat."
        ).classes("text-sm")
