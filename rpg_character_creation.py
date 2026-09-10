from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable, Mapping, Sequence

from rpg_character_guides import (
    FIGHTER_CLASS_SKILL_LABELS,
    FIGHTER_PROFICIENCIES,
    fighter_cumulative_milestones,
    fighter_feat_counts,
    fighter_reference,
    fighter_skill_rank_budget,
    gear_preset_options,
    gear_reference_lines,
    is_fighter,
    is_fighter_class_skill,
    race_comparison,
)


CREATION_STEPS = (
    ("identity", "Identité", "badge"),
    ("race", "Race", "diversity_3"),
    ("abilities", "Caractéristiques", "tune"),
    ("combat", "Combat", "shield"),
    ("skills", "Compétences", "psychology"),
    ("gear", "Équipement", "backpack"),
    ("summary", "Résumé", "fact_check"),
)

IDENTITY_FIELDS = (
    "character_name",
    "player_name",
    "campaign",
    "class_name",
    "subclass_name",
    "character_level",
    "race",
    "race_key",
    "race_heritage",
    "alternate_racial_traits",
    "creature_type",
    "racial_subtypes",
    "vision",
    "languages",
    "racial_ability_adjustments",
    "carrying_capacity_multiplier",
    "is_quadruped",
    "ignore_armor_speed",
    "ignore_encumbrance_speed",
    "base_speed",
    "alignment",
    "deity",
    "size_key",
    "age_text",
    "gender",
    "height_text",
    "weight_text",
    "eyes",
    "hair",
    "skin",
    "experience_points",
)

COMBAT_FIELDS = (
    "str_score",
    "dex_score",
    "con_score",
    "int_score",
    "wis_score",
    "cha_score",
    "str_temp_score",
    "dex_temp_score",
    "con_temp_score",
    "int_temp_score",
    "wis_temp_score",
    "cha_temp_score",
    "max_hp",
    "current_hp",
    "nonlethal_damage",
    "speed",
    "damage_reduction",
    "spell_resistance",
    "base_attack_bonus",
    "armor_bonus",
    "shield_bonus",
    "natural_armor_bonus",
    "deflection_bonus",
    "misc_ac_modifier",
    "armor_check_penalty",
    "initiative_misc_modifier",
    "grapple_misc_modifier",
    "cmb_misc_modifier",
    "cmd_misc_modifier",
)


def _as_decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _as_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def identity_payload(character: Mapping[str, Any], **updates: Any) -> dict[str, Any]:
    """Construit le contrat complet attendu par update_rpg_character_identity."""
    payload = {field: character.get(field) for field in IDENTITY_FIELDS}
    payload.update(updates)
    return payload


def combat_payload(character: Mapping[str, Any], **updates: Any) -> dict[str, Any]:
    """Construit le contrat complet attendu par update_rpg_character_combat."""
    payload = {field: character.get(field) for field in COMBAT_FIELDS}
    payload.update(updates)
    # Le champ historique est encore accepté par la couche de données actuelle.
    if payload.get("grapple_misc_modifier") in (None, ""):
        payload["grapple_misc_modifier"] = payload.get("cmb_misc_modifier") or 0
    return payload


def skill_update_rows(
    skills: Sequence[Mapping[str, Any]],
    *,
    ranks: Mapping[int, Any] | None = None,
    class_skills: Mapping[int, Any] | None = None,
) -> list[dict[str, Any]]:
    """Préserve toutes les propriétés d'une compétence lors de l'édition guidée."""
    ranks = ranks or {}
    class_skills = class_skills or {}
    rows: list[dict[str, Any]] = []
    for skill in skills:
        skill_id = int(skill["id"])
        rows.append(
            {
                "id": skill_id,
                "skill_name": skill.get("skill_name"),
                "english_name": skill.get("english_name"),
                "ability_key": skill.get("ability_key"),
                "ranks": ranks.get(skill_id, skill.get("ranks") or 0),
                "misc_modifier": skill.get("misc_modifier") or 0,
                "class_skill": bool(
                    class_skills.get(skill_id, skill.get("class_skill"))
                ),
                "trained_only": bool(skill.get("trained_only")),
                "armor_check_applies": bool(skill.get("armor_check_applies")),
                "double_armor_penalty": bool(skill.get("double_armor_penalty")),
            }
        )
    return rows


def used_skill_ranks(values: Mapping[int, Any] | Sequence[Mapping[str, Any]]) -> Decimal:
    if isinstance(values, Mapping):
        return sum((_as_decimal(value) for value in values.values()), Decimal("0"))
    return sum((_as_decimal(row.get("ranks")) for row in values), Decimal("0"))


def creation_warnings(
    character: Mapping[str, Any],
    *,
    saves: Sequence[Mapping[str, Any]] = (),
    skills: Sequence[Mapping[str, Any]] = (),
    equipment: Sequence[Mapping[str, Any]] = (),
    attacks: Sequence[Mapping[str, Any]] = (),
) -> list[str]:
    """Avertissements non bloquants pour le résumé de création."""
    warnings: list[str] = []
    if not str(character.get("class_name") or "").strip():
        warnings.append("Classe à préciser.")
    if not str(character.get("race") or "").strip():
        warnings.append("Race à préciser.")
    if int(character.get("max_hp") or 0) <= 0:
        warnings.append("PV maximums à vérifier.")
    if not any(_as_decimal(row.get("ranks")) > 0 for row in skills):
        warnings.append("Aucun rang de compétence n’est encore attribué.")
    if not attacks:
        warnings.append("Aucune attaque n’est encore enregistrée.")
    if not equipment:
        warnings.append("Aucun équipement n’est encore enregistré.")
    core_saves = {str(row.get("save_key") or "") for row in saves}
    for key, label in (
        ("fortitude", "Vigueur"),
        ("reflex", "Réflexes"),
        ("will", "Volonté"),
    ):
        if key not in core_saves:
            warnings.append(f"Sauvegarde {label} à vérifier.")
    return warnings


def race_selection_pending(character: Mapping[str, Any]) -> bool:
    """Indique si un nouveau personnage attend encore le choix réel de sa race."""
    race_key = str(character.get("race_key") or "custom").strip()
    race_name = str(character.get("race") or "").strip()
    return race_key == "custom" and not race_name


def open_new_character_dialog(
    *,
    ui: Any,
    user_id: int,
    player_default: str | None,
    create_rpg_character: Callable[..., Any],
    character_url: Callable[..., str],
    notify_error: Callable[[Exception, str], None],
) -> None:
    """Ouvre le choix Création guidée / Création rapide."""
    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-lg p-5"):
            ui.label("Créer un personnage").classes("text-xl font-bold")
            ui.label(
                "Choisissez le parcours guidé pour compléter la feuille étape par étape, "
                "ou la création rapide pour conserver le fonctionnement simple actuel."
            ).classes("text-sm jf-muted")

            mode = ui.toggle(
                {
                    "guided": "Création guidée",
                    "quick": "Création rapide",
                },
                value="guided",
            ).props("spread no-caps").classes("w-full")
            name_input = ui.input(label="Nom du personnage").props(
                "autofocus maxlength=120"
            ).classes("w-full")
            player_input = ui.input(
                label="Nom du joueur", value=player_default
            ).props("maxlength=120").classes("w-full")

            def create_now() -> None:
                try:
                    character_id = create_rpg_character(
                        user_id,
                        name_input.value,
                        player_input.value,
                    )
                except Exception as error:
                    notify_error(error, "Le personnage n’a pas pu être créé.")
                    return
                dialog.close()
                ui.notify("Personnage créé.", type="positive")
                section = "creation" if mode.value == "guided" else None
                ui.navigate.to(character_url(character_id, section))

            with ui.row().classes("w-full justify-end gap-2 mt-3"):
                ui.button("Annuler", on_click=dialog.close).props("flat")
                ui.button(
                    "Créer",
                    icon="person_add",
                    on_click=create_now,
                ).props("color=primary")
    dialog.open()


def build_character_creation_panel(
    *,
    ui: Any,
    user_id: int,
    character: Mapping[str, Any],
    get_rpg_character: Callable[..., Mapping[str, Any]],
    update_rpg_character_identity: Callable[..., Any],
    update_rpg_character_combat: Callable[..., Any],
    list_rpg_saves: Callable[..., Sequence[Mapping[str, Any]]],
    update_rpg_saves: Callable[..., Any],
    list_rpg_skills: Callable[..., Sequence[Mapping[str, Any]]],
    update_rpg_skills: Callable[..., Any],
    list_rpg_equipment: Callable[..., Sequence[Mapping[str, Any]]],
    list_rpg_attacks: Callable[..., Sequence[Mapping[str, Any]]],
    character_sheet_audit: Callable[..., Mapping[str, Any]],
    apply_equipment_effects: Callable[..., Mapping[str, Any]],
    armor_class_total: Callable[..., Any],
    touch_armor_class: Callable[..., Any],
    flat_footed_armor_class: Callable[..., Any],
    initiative_total: Callable[..., Any],
    cmb_total: Callable[..., Any],
    cmd_total: Callable[..., Any],
    ability_modifier: Callable[..., Any],
    format_modifier: Callable[[Any], str],
    get_race_profile: Callable[[str], Mapping[str, Any]],
    race_labels: Mapping[str, str],
    size_labels: Mapping[str, str],
    ability_labels: Mapping[str, str],
    ability_long_labels: Mapping[str, str],
    save_definitions: Mapping[str, Mapping[str, Any]],
    character_url: Callable[..., str],
    notify_error: Callable[[Exception, str], None],
) -> None:
    """Construit l'assistant de création sur un personnage déjà persistant."""
    working = dict(character)
    character_id = int(working["id"])

    def reload_character() -> dict[str, Any]:
        fresh = dict(get_rpg_character(user_id, character_id))
        working.clear()
        working.update(fresh)
        return fresh

    with ui.card().classes("w-full p-5"):
        ui.label("Création guidée").classes("text-2xl font-bold")
        ui.label(
            "Chaque étape est enregistrée avant de passer à la suivante. Pour un nouveau "
            "personnage dont la race n’est pas encore choisie, l’Identité est enregistrée "
            "avec la Race à l’étape suivante."
        ).classes("text-sm jf-muted")
        ui.label(
            "Nouveau : des repères Fighter niveaux 1 à 4, un comparatif Humain/Elfe "
            "et un catalogue d’armes/armures facilitent la saisie sans imposer vos choix."
        ).classes("text-xs jf-muted mt-1")

    with ui.tabs().props(
        "dense no-caps mobile-arrows outside-arrows align=left"
    ).classes("jf-rpg-main-tabs") as step_tabs:
        tab_by_key: dict[str, Any] = {}
        for key, label, icon in CREATION_STEPS:
            tab_by_key[key] = ui.tab(label, icon=icon)

    def go(key: str) -> None:
        step_tabs.set_value(tab_by_key[key])

    def nav_buttons(
        previous: str | None,
        next_step: str | None,
        save: Callable[[], bool] | None = None,
    ) -> None:
        with ui.row().classes("w-full justify-between gap-2 mt-4 flex-wrap"):
            if previous:
                ui.button(
                    "Précédent",
                    icon="chevron_left",
                    on_click=lambda: go(previous),
                ).props("flat")
            else:
                ui.element("div")

            def next_clicked() -> None:
                if save is not None and not save():
                    return
                if next_step:
                    go(next_step)

            if next_step:
                ui.button(
                    "Enregistrer et suivant",
                    icon="chevron_right",
                    on_click=next_clicked,
                ).props("color=primary")

    with ui.tab_panels(
        step_tabs,
        value=tab_by_key["identity"],
    ).classes("w-full bg-transparent"):
        with ui.tab_panel(tab_by_key["identity"]).classes("px-0"):
            with ui.card().classes("w-full p-5"):
                ui.label("1. Identité").classes("text-xl font-bold")
                with ui.element("div").classes("jf-rpg-grid mt-2"):
                    identity_controls = {
                        "character_name": ui.input(
                            label="Nom du personnage",
                            value=working.get("character_name") or "",
                        ).props("maxlength=120"),
                        "player_name": ui.input(
                            label="Joueur",
                            value=working.get("player_name") or "",
                        ).props("maxlength=120"),
                        "campaign": ui.input(
                            label="Campagne",
                            value=working.get("campaign") or "",
                        ).props("maxlength=160"),
                        "class_name": ui.input(
                            label="Classe",
                            value=working.get("class_name") or "",
                            placeholder="Ex. Fighter ou Guerrier",
                        ).props("maxlength=120"),
                        "subclass_name": ui.input(
                            label="Sous-classe / archétype (facultatif)",
                            value=working.get("subclass_name") or "",
                            placeholder="Laisser vide pour un Fighter standard",
                        ).props("maxlength=160 clearable"),
                        "character_level": ui.number(
                            label="Niveau",
                            value=working.get("character_level") or 1,
                            min=1,
                            max=100,
                            step=1,
                        ),
                        "alignment": ui.input(
                            label="Alignement",
                            value=working.get("alignment") or "",
                        ).props("maxlength=80"),
                        "deity": ui.input(
                            label="Divinité",
                            value=working.get("deity") or "",
                        ).props("maxlength=120"),
                    }

                @ui.refreshable
                def fighter_identity_help() -> None:
                    class_name = identity_controls["class_name"].value
                    if not is_fighter(class_name):
                        return
                    level = _as_int(identity_controls["character_level"].value, 1)
                    with ui.element("div").classes("jf-rpg-summary mt-3"):
                        ui.label("Repères Fighter / Guerrier").classes("font-bold")
                        reference = fighter_reference(level)
                        if reference is None:
                            ui.label(
                                "Cette aide détaillée couvre actuellement les niveaux 1 à 4. "
                                "La feuille reste entièrement modifiable au-delà."
                            ).classes("text-sm jf-muted")
                        else:
                            ui.label(
                                f"Niveau {level} : d10 de vie · BBA +{reference['bab']} · "
                                f"Vigueur +{reference['fortitude']} · Réflexes +{reference['reflex']} · "
                                f"Volonté +{reference['will']}."
                            ).classes("text-sm")
                            ui.label(
                                "Capacités de ce niveau : " + ", ".join(reference["specials"])
                            ).classes("text-sm")
                            feats_no_race = fighter_feat_counts(level)
                            ui.label(
                                f"Dons cumulés sans bonus racial : {feats_no_race['total']} "
                                f"({feats_no_race['general']} généraux + {feats_no_race['fighter_bonus']} bonus Fighter). "
                                "Au niveau 4, un Humain standard en a normalement un de plus."
                            ).classes("text-sm")
                        ui.label("Maîtrises : " + FIGHTER_PROFICIENCIES).classes("text-xs jf-muted")
                        ui.label(
                            "Compétences de classe : " + ", ".join(FIGHTER_CLASS_SKILL_LABELS)
                        ).classes("text-xs jf-muted")

                identity_controls["class_name"].on_value_change(
                    lambda _event: fighter_identity_help.refresh()
                )
                identity_controls["character_level"].on_value_change(
                    lambda _event: fighter_identity_help.refresh()
                )
                fighter_identity_help()

                def save_identity() -> bool:
                    updates = {
                        key: control.value
                        for key, control in identity_controls.items()
                    }

                    # Un personnage créé par l'assistant commence volontairement avec
                    # race_key='custom' et aucun nom de race. La couche de données
                    # refuse d'enregistrer ce profil incomplet. On conserve donc
                    # l'Identité dans l'état de l'assistant et on l'enregistre avec
                    # la Race à l'étape suivante, sans inventer de race temporaire.
                    if race_selection_pending(working):
                        working.update(updates)
                        ui.notify(
                            "Identité prête. Choisissez maintenant la race; "
                            "les deux étapes seront enregistrées ensemble.",
                            type="info",
                        )
                        return True

                    try:
                        update_rpg_character_identity(
                            user_id,
                            character_id,
                            identity_payload(working, **updates),
                        )
                    except Exception as error:
                        notify_error(error, "L’identité n’a pas pu être enregistrée.")
                        return False
                    working.update(updates)
                    ui.notify("Identité enregistrée.", type="positive")
                    return True

                nav_buttons(None, "race", save_identity)

        with ui.tab_panel(tab_by_key["race"]).classes("px-0"):
            with ui.card().classes("w-full p-5"):
                ui.label("2. Race").classes("text-xl font-bold")
                ui.label(
                    "Le profil racial suggère des valeurs de feuille, mais ne change jamais "
                    "automatiquement FOR, DEX, CON, INT, SAG ou CHA."
                ).classes("text-sm jf-muted")

                with ui.expansion(
                    "Humain ou Elfe pour un Fighter avec une orientation magique?",
                    icon="compare_arrows",
                    value=True,
                ).props("expand-separator").classes("w-full mt-2"):
                    for race_key in ("human", "elf"):
                        info = race_comparison(race_key) or {}
                        with ui.element("div").classes("jf-rpg-summary mt-2"):
                            ui.label(str(info.get("label") or race_key)).classes("font-bold")
                            ui.label(
                                "Caractéristiques : " + str(info.get("ability_adjustments") or "—")
                            ).classes("text-sm")
                            ui.label(str(info.get("combat") or "")).classes("text-sm")
                            ui.label(str(info.get("skills") or "")).classes("text-sm")
                            ui.label("Magie : " + str(info.get("magic") or "")).classes("text-sm")
                            ui.label(str(info.get("fighter_note") or "")).classes("text-xs jf-muted")
                    ui.label(
                        "Important : être Elfe ne donne pas de sorts à un Fighter. Une future classe ou capacité "
                        "de lanceur de sorts reste nécessaire."
                    ).classes("text-xs jf-muted mt-2")

                current_race_key = str(working.get("race_key") or "custom")
                if current_race_key not in race_labels:
                    current_race_key = "custom"
                with ui.element("div").classes("jf-rpg-grid mt-2"):
                    race_select = ui.select(
                        race_labels,
                        label="Race principale",
                        value=current_race_key,
                    ).classes("w-full")
                    custom_race = ui.input(
                        label="Nom de la race personnalisée",
                        value=(working.get("race") or "") if current_race_key == "custom" else "",
                    ).props("maxlength=120").classes("w-full")
                    heritage = ui.input(
                        label="Héritage / sous-race",
                        value=working.get("race_heritage") or "",
                    ).props("maxlength=160")
                    size = ui.select(
                        size_labels,
                        label="Catégorie de taille",
                        value=working.get("size_key") or "medium",
                    )
                    base_speed = ui.number(
                        label="Vitesse de base (pi)",
                        value=working.get("base_speed") or 30,
                        min=0,
                        max=500,
                        step=5,
                    )
                    creature_type = ui.input(
                        label="Type de créature",
                        value=working.get("creature_type") or "Humanoïde",
                    ).props("maxlength=120")
                    subtypes = ui.input(
                        label="Sous-types",
                        value=working.get("racial_subtypes") or "",
                    ).props("maxlength=240")
                    vision = ui.input(
                        label="Vision / sens",
                        value=working.get("vision") or "",
                    ).props("maxlength=240")
                    languages = ui.input(
                        label="Langues",
                        value=working.get("languages") or "",
                    ).props("maxlength=500")
                    ability_adjustments = ui.input(
                        label="Ajustements raciaux",
                        value=working.get("racial_ability_adjustments") or "",
                    ).props("maxlength=240")
                    carrying_multiplier = ui.number(
                        label="Multiplicateur de charge",
                        value=float(working.get("carrying_capacity_multiplier") or 1),
                        min=.001,
                        max=100,
                        step=.25,
                    )
                with ui.row().classes("w-full gap-4 flex-wrap mt-2"):
                    quadruped = ui.checkbox(
                        "Quadrupède",
                        value=bool(working.get("is_quadruped")),
                    )
                    ignore_armor_speed = ui.checkbox(
                        "L’armure ne réduit pas la vitesse",
                        value=bool(working.get("ignore_armor_speed")),
                    )
                    ignore_load_speed = ui.checkbox(
                        "L’encombrement ne réduit pas la vitesse",
                        value=bool(working.get("ignore_encumbrance_speed")),
                    )
                alternate_traits = ui.textarea(
                    label="Traits raciaux alternatifs / personnalisés",
                    value=working.get("alternate_racial_traits") or "",
                ).props("outlined autogrow maxlength=4000").classes("w-full")
                profile_label = ui.label("").classes("text-sm jf-muted")
                magic_orientation_label = ui.label("").classes("text-xs jf-muted")

                def selected_profile() -> Mapping[str, Any]:
                    return get_race_profile(str(race_select.value or "custom"))

                def refresh_profile(_event: Any = None) -> None:
                    profile = selected_profile()
                    traits = str(profile.get("standard_traits") or "").strip()
                    profile_label.set_text(
                        "Profil suggéré — "
                        + "; ".join(
                            part
                            for part in (
                                f"taille {size_labels.get(profile.get('size_key'), profile.get('size_key'))}",
                                f"vitesse {profile.get('base_speed')} pi",
                                str(profile.get("vision") or ""),
                                str(profile.get("languages") or ""),
                                str(profile.get("ability_adjustments") or ""),
                                ("traits : " + traits) if traits else "",
                            )
                            if part
                        )
                    )
                    custom_race.set_visibility(race_select.value == "custom")
                    comparison = race_comparison(race_select.value)
                    if comparison:
                        magic_orientation_label.set_text(
                            "Orientation magique — " + str(comparison.get("magic") or "")
                        )
                    else:
                        magic_orientation_label.set_text("")

                def apply_profile() -> None:
                    profile = selected_profile()
                    for control, value in (
                        (size, profile.get("size_key")),
                        (base_speed, profile.get("base_speed")),
                        (creature_type, profile.get("creature_type")),
                        (subtypes, profile.get("subtypes")),
                        (vision, profile.get("vision")),
                        (languages, profile.get("languages")),
                        (ability_adjustments, profile.get("ability_adjustments")),
                        (carrying_multiplier, profile.get("carrying_capacity_multiplier")),
                        (quadruped, profile.get("is_quadruped")),
                        (ignore_armor_speed, profile.get("ignore_armor_speed")),
                        (ignore_load_speed, profile.get("ignore_encumbrance_speed")),
                    ):
                        control.value = value
                        control.update()
                    ui.notify(
                        "Profil racial suggéré appliqué aux champs de race. Les caractéristiques restent inchangées.",
                        type="positive",
                    )

                race_select.on_value_change(refresh_profile)
                refresh_profile()
                ui.button(
                    "Appliquer le profil racial",
                    icon="auto_fix_high",
                    on_click=apply_profile,
                ).props("outline color=primary")

                def save_race() -> bool:
                    key = str(race_select.value or "custom")
                    race_name = (
                        custom_race.value
                        if key == "custom"
                        else race_labels.get(key)
                    )
                    updates = {
                        "race_key": key,
                        "race": race_name,
                        "race_heritage": heritage.value,
                        "alternate_racial_traits": alternate_traits.value,
                        "creature_type": creature_type.value,
                        "racial_subtypes": subtypes.value,
                        "vision": vision.value,
                        "languages": languages.value,
                        "racial_ability_adjustments": ability_adjustments.value,
                        "carrying_capacity_multiplier": carrying_multiplier.value,
                        "is_quadruped": quadruped.value,
                        "ignore_armor_speed": ignore_armor_speed.value,
                        "ignore_encumbrance_speed": ignore_load_speed.value,
                        "base_speed": base_speed.value,
                        "size_key": size.value,
                    }
                    try:
                        update_rpg_character_identity(
                            user_id,
                            character_id,
                            identity_payload(working, **updates),
                        )
                    except Exception as error:
                        notify_error(error, "Le profil racial n’a pas pu être enregistré.")
                        return False
                    working.update(updates)
                    ui.notify("Race enregistrée.", type="positive")
                    return True

                nav_buttons("identity", "abilities", save_race)

        with ui.tab_panel(tab_by_key["abilities"]).classes("px-0"):
            with ui.card().classes("w-full p-5"):
                ui.label("3. Caractéristiques").classes("text-xl font-bold")
                ui.label(
                    "Saisissez les scores finaux utilisés par la feuille. Les ajustements raciaux "
                    "restent affichés comme aide et ne sont jamais appliqués silencieusement."
                ).classes("text-sm jf-muted")
                if working.get("racial_ability_adjustments"):
                    ui.label(
                        "Rappel racial : " + str(working.get("racial_ability_adjustments"))
                    ).classes("jf-rpg-help")
                with ui.expansion(
                    "Repère Fighter avec possible magie plus tard",
                    icon="tips_and_updates",
                    value=False,
                ).classes("w-full mt-2"):
                    ui.label(
                        "Un Fighter de mêlée privilégie souvent FOR et CON; un profil agile peut valoriser DEX. "
                        "Si une future magie basée sur l’INT est envisagée, l’INT devient aussi importante."
                    ).classes("text-sm")
                    ui.label(
                        "Humain : +2 flexible. Elfe : +2 DEX, +2 INT, −2 CON. L’assistant ne choisit ni ne modifie ces scores à votre place."
                    ).classes("text-xs jf-muted")

                ability_controls: dict[str, Any] = {}
                with ui.element("div").classes("jf-rpg-ability-grid mt-3"):
                    for key, short_label in ability_labels.items():
                        with ui.element("div").classes("jf-rpg-ability-card"):
                            ui.label(
                                f"{short_label} — {ability_long_labels.get(key, key)}"
                            ).classes("font-bold")
                            score = ui.number(
                                label="Score",
                                value=working.get(f"{key}_score") or 10,
                                min=1,
                                max=100,
                                step=1,
                            )
                            modifier = ui.label("").classes("jf-rpg-ability-modifier")

                            def update_mod(
                                _event: Any = None,
                                *,
                                control=score,
                                label=modifier,
                            ) -> None:
                                label.set_text(
                                    format_modifier(ability_modifier(control.value))
                                )

                            score.on_value_change(update_mod)
                            update_mod()
                            ability_controls[key] = score

                def save_abilities() -> bool:
                    updates = {
                        f"{key}_score": control.value
                        for key, control in ability_controls.items()
                    }
                    try:
                        update_rpg_character_combat(
                            user_id,
                            character_id,
                            combat_payload(working, **updates),
                        )
                    except Exception as error:
                        notify_error(
                            error,
                            "Les caractéristiques n’ont pas pu être enregistrées.",
                        )
                        return False
                    working.update(updates)
                    ui.notify("Caractéristiques enregistrées.", type="positive")
                    return True

                nav_buttons("race", "combat", save_abilities)

        with ui.tab_panel(tab_by_key["combat"]).classes("px-0"):
            saves = [dict(row) for row in list_rpg_saves(user_id, character_id)]
            with ui.card().classes("w-full p-5"):
                ui.label("4. Combat et sauvegardes").classes("text-xl font-bold")
                ui.label(
                    "Pour un Fighter standard niveaux 1 à 4, l’assistant peut préremplir uniquement "
                    "le BBA et les sauvegardes de base. Les PV et autres choix restent manuels."
                ).classes("text-xs jf-muted")
                with ui.element("div").classes("jf-rpg-grid mt-2"):
                    max_hp = ui.number(
                        label="PV maximums",
                        value=working.get("max_hp") or 0,
                        step=1,
                    )
                    current_hp = ui.number(
                        label="PV actuels",
                        value=working.get("current_hp") or 0,
                        step=1,
                    )
                    bab = ui.number(
                        label="BBA",
                        value=working.get("base_attack_bonus") or 0,
                        step=1,
                    )
                save_editors: list[tuple[dict[str, Any], Any]] = []
                with ui.element("div").classes("jf-rpg-grid mt-3"):
                    for row in saves:
                        definition = save_definitions.get(
                            str(row.get("save_key")),
                            {},
                        )
                        base = ui.number(
                            label=f"{definition.get('label', row.get('save_key'))} — base",
                            value=row.get("base_save") or 0,
                            step=1,
                        )
                        save_editors.append((row, base))

                fighter_combat_note = ui.label("").classes("text-sm jf-muted mt-2")

                def apply_fighter_combat_reference() -> None:
                    if not is_fighter(working.get("class_name")):
                        ui.notify(
                            "La classe enregistrée n’est pas Fighter / Guerrier.",
                            type="warning",
                        )
                        return
                    level = _as_int(working.get("character_level"), 1)
                    reference = fighter_reference(level)
                    if reference is None:
                        ui.notify(
                            "Le préremplissage Fighter couvre actuellement les niveaux 1 à 4.",
                            type="warning",
                        )
                        return
                    bab.value = reference["bab"]
                    bab.update()
                    targets = {
                        "fortitude": reference["fortitude"],
                        "reflex": reference["reflex"],
                        "will": reference["will"],
                    }
                    for row, base in save_editors:
                        key = str(row.get("save_key") or "")
                        if key in targets:
                            base.value = targets[key]
                            base.update()
                    note_parts = list(reference["specials"])
                    if level >= 2:
                        note_parts.append(
                            "Bravoure +1 : bonus de Volonté contre la peur; à noter comme bonus conditionnel."
                        )
                    if level >= 3:
                        note_parts.append(
                            "Entraînement aux armures 1 : ACP 1 moins sévère, DEX max +1 et vitesse normale en armure intermédiaire."
                        )
                    fighter_combat_note.set_text(" · ".join(note_parts))
                    ui.notify(
                        f"Repères Fighter niveau {level} appliqués au BBA et aux sauvegardes de base.",
                        type="positive",
                    )

                ui.button(
                    "Appliquer les repères Fighter du niveau",
                    icon="auto_fix_high",
                    on_click=apply_fighter_combat_reference,
                ).props("outline color=primary").classes("mt-2")

                @ui.refreshable
                def combat_preview() -> None:
                    draft = combat_payload(
                        working,
                        max_hp=max_hp.value,
                        current_hp=current_hp.value,
                        base_attack_bonus=bab.value,
                    )
                    equipped = list_rpg_equipment(user_id, character_id)
                    effective = apply_equipment_effects(draft, equipped)
                    with ui.element("div").classes("jf-rpg-summary mt-3"):
                        for label, value in (
                            ("CA", armor_class_total(effective)),
                            ("CA contact", touch_armor_class(effective)),
                            ("Pris au dépourvu", flat_footed_armor_class(effective)),
                            ("Initiative", format_modifier(initiative_total(effective))),
                            ("BMO / CMB", format_modifier(cmb_total(effective))),
                            ("DMD / CMD", str(cmd_total(effective))),
                        ):
                            ui.label(f"{label} : {value}")

                for control in (max_hp, current_hp, bab):
                    control.on_value_change(
                        lambda _event: combat_preview.refresh()
                    )
                combat_preview()

                def save_combat_and_saves() -> bool:
                    try:
                        update_rpg_character_combat(
                            user_id,
                            character_id,
                            combat_payload(
                                working,
                                max_hp=max_hp.value,
                                current_hp=current_hp.value,
                                base_attack_bonus=bab.value,
                            ),
                        )
                        save_rows = []
                        for row, base in save_editors:
                            save_rows.append(
                                {
                                    "save_key": row.get("save_key"),
                                    "base_save": base.value,
                                    "magic_modifier": row.get("magic_modifier") or 0,
                                    "misc_modifier": row.get("misc_modifier") or 0,
                                    "temporary_modifier": row.get("temporary_modifier") or 0,
                                    "conditional_notes": row.get("conditional_notes"),
                                }
                            )
                        update_rpg_saves(user_id, character_id, save_rows)
                    except Exception as error:
                        notify_error(
                            error,
                            "Le combat et les sauvegardes n’ont pas pu être enregistrés.",
                        )
                        return False
                    working.update(
                        max_hp=max_hp.value,
                        current_hp=current_hp.value,
                        base_attack_bonus=bab.value,
                    )
                    ui.notify(
                        "Combat et sauvegardes enregistrés.",
                        type="positive",
                    )
                    return True

                nav_buttons("abilities", "skills", save_combat_and_saves)

        with ui.tab_panel(tab_by_key["skills"]).classes("px-0"):
            skills = [dict(row) for row in list_rpg_skills(user_id, character_id)]
            with ui.card().classes("w-full p-5"):
                ui.label("5. Compétences").classes("text-xl font-bold")
                ui.label(
                    "Le nombre de rangs disponibles est une aide facultative. L’assistant ne "
                    "devine pas les règles d’une autre classe ou d’un multiclassage."
                ).classes("text-sm jf-muted")
                available = ui.number(
                    label="Rangs disponibles (facultatif)",
                    min=0,
                    step=1,
                ).props("clearable")
                rank_controls: dict[int, Any] = {}
                class_controls: dict[int, Any] = {}
                summary = ui.label("").classes("jf-rpg-help")
                for row in skills:
                    skill_id = int(row["id"])
                    with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                        name = str(row.get("skill_name") or "Compétence")
                        if is_fighter_class_skill(row):
                            name += " · Fighter"
                        ui.label(name).classes("grow min-w-[180px]")
                        rank_controls[skill_id] = ui.number(
                            label="Rangs",
                            value=float(row.get("ranks") or 0),
                            min=0,
                            step=1,
                        ).classes("w-28")
                        class_controls[skill_id] = ui.checkbox(
                            "Classe",
                            value=bool(row.get("class_skill")),
                        )

                fighter_skill_note = ui.label("").classes("text-xs jf-muted mt-2")

                def apply_fighter_skill_reference() -> None:
                    if not is_fighter(working.get("class_name")):
                        ui.notify(
                            "La classe enregistrée n’est pas Fighter / Guerrier.",
                            type="warning",
                        )
                        return
                    marked = 0
                    for row in skills:
                        if not is_fighter_class_skill(row):
                            continue
                        control = class_controls.get(int(row["id"]))
                        if control is None:
                            continue
                        if not bool(control.value):
                            control.value = True
                            control.update()
                        marked += 1

                    budget = fighter_skill_rank_budget(
                        working.get("character_level") or 1,
                        working.get("int_score") or 10,
                        working.get("race_key"),
                    )
                    available.value = budget["total_without_favored_class"]
                    available.update()
                    refresh_rank_summary()
                    note = (
                        f"Fighter pur : {budget['per_level']} rang(s)/niveau avec l’INT actuelle; "
                        f"{budget['fighter_total']} sur {working.get('character_level') or 1} niveau(x)."
                    )
                    if budget["human_standard_bonus"]:
                        note += (
                            f" Humain standard : +{budget['human_standard_bonus']} rang(s) via Skilled."
                        )
                    note += (
                        " Le bonus éventuel de classe favorite n’est pas inclus. "
                        "Si un trait racial remplace Skilled ou si le personnage est multiclassé, ajustez le total."
                    )
                    fighter_skill_note.set_text(note)
                    ui.notify(
                        f"{marked} compétence(s) Fighter marquée(s) comme compétences de classe.",
                        type="positive",
                    )

                ui.button(
                    "Appliquer les repères de compétences Fighter",
                    icon="school",
                    on_click=apply_fighter_skill_reference,
                ).props("outline color=primary").classes("mt-2")

                def refresh_rank_summary(_event: Any = None) -> None:
                    used = used_skill_ranks(
                        {
                            key: control.value
                            for key, control in rank_controls.items()
                        }
                    )
                    if available.value in (None, ""):
                        summary.set_text(f"Rangs utilisés : {used}")
                        return
                    total = _as_decimal(available.value)
                    remaining = total - used
                    text = (
                        f"Rangs utilisés : {used} / {total} — reste : {remaining}"
                    )
                    if remaining < 0:
                        text += " — dépassement à vérifier"
                    summary.set_text(text)

                for control in list(rank_controls.values()) + [available]:
                    control.on_value_change(refresh_rank_summary)
                refresh_rank_summary()

                def save_skills() -> bool:
                    rows = skill_update_rows(
                        skills,
                        ranks={
                            key: control.value
                            for key, control in rank_controls.items()
                        },
                        class_skills={
                            key: control.value
                            for key, control in class_controls.items()
                        },
                    )
                    try:
                        update_rpg_skills(user_id, character_id, rows)
                    except Exception as error:
                        notify_error(
                            error,
                            "Les compétences n’ont pas pu être enregistrées.",
                        )
                        return False
                    ui.notify("Compétences enregistrées.", type="positive")
                    return True

                nav_buttons("combat", "gear", save_skills)

        with ui.tab_panel(tab_by_key["gear"]).classes("px-0"):
            equipment = list_rpg_equipment(user_id, character_id)
            attacks = list_rpg_attacks(user_id, character_id)
            with ui.card().classes("w-full p-5"):
                ui.label("6. Équipement et attaques").classes("text-xl font-bold")
                ui.label(
                    "Les formulaires complets existent déjà dans la feuille. Les armures et boucliers "
                    "équipés influencent automatiquement CA, DEX max, pénalité d’armure, poids et vitesse; "
                    "les attaques enregistrées alimentent Attaques et Combat rapide."
                ).classes("text-sm jf-muted")
                ui.label(f"Équipements enregistrés : {len(equipment)}").classes("font-bold")
                ui.label(f"Attaques enregistrées : {len(attacks)}").classes("font-bold")

                with ui.expansion(
                    "Catalogue de référence — armes et armures courantes",
                    icon="inventory_2",
                    value=True,
                ).props("expand-separator").classes("w-full mt-3"):
                    ui.label(
                        "Choisissez un objet pour voir les valeurs Pathfinder à saisir. "
                        "Aucune donnée n’est enregistrée automatiquement."
                    ).classes("text-xs jf-muted")
                    preset_select = ui.select(
                        gear_preset_options(),
                        label="Objet de référence",
                        value="breastplate",
                    ).props("options-dense").classes("w-full")

                    @ui.refreshable
                    def gear_reference() -> None:
                        lines = gear_reference_lines(preset_select.value)
                        with ui.element("div").classes("jf-rpg-summary mt-2"):
                            for index, line in enumerate(lines):
                                ui.label(line).classes(
                                    "font-bold" if index == 0 else "text-sm"
                                )
                            ui.label(
                                "Pour une arme possédée : ajoutez-la dans Équipement pour son poids, puis dans Attaques "
                                "pour le bonus d’attaque, les dégâts, le critique et la portée."
                            ).classes("text-xs jf-muted mt-1")
                            ui.label(
                                "Fighter niveau 3–6 standard : Entraînement aux armures 1 réduit l’ACP de 1, "
                                "augmente la DEX max de 1 et permet la vitesse normale en armure intermédiaire. "
                                "Cette capacité de classe reste un repère manuel tant que l’app ne suit pas les niveaux par classe/archétype."
                            ).classes("text-xs jf-muted mt-1")
                            ui.label(
                                "Si vous prévoyez de la magie profane plus tard, surveillez le champ Échec sorts profanes : "
                                "l’armure et le bouclier peuvent gêner les sorts avec composantes somatiques. "
                                "Elven Magic n’annule pas ce risque."
                            ).classes("text-xs jf-muted mt-1")

                    preset_select.on_value_change(
                        lambda _event: gear_reference.refresh()
                    )
                    gear_reference()

                with ui.row().classes("gap-2 flex-wrap mt-3"):
                    ui.button(
                        "Ouvrir Équipement",
                        icon="backpack",
                        on_click=lambda: ui.navigate.to(
                            character_url(character_id, "equipement")
                        ),
                    ).props("outline color=primary")
                    ui.button(
                        "Ouvrir Attaques",
                        icon="sports_martial_arts",
                        on_click=lambda: ui.navigate.to(
                            character_url(character_id, "attaques")
                        ),
                    ).props("outline color=primary")
                ui.label(
                    "Après avoir ajouté vos éléments, revenez dans l’onglet Création pour poursuivre."
                ).classes("text-xs jf-muted")
                nav_buttons("skills", "summary", None)

        with ui.tab_panel(tab_by_key["summary"]).classes("px-0"):
            with ui.card().classes("w-full p-5"):
                ui.label("7. Résumé").classes("text-xl font-bold")

                @ui.refreshable
                def summary_panel() -> None:
                    fresh = reload_character()
                    saves_now = [
                        dict(row)
                        for row in list_rpg_saves(user_id, character_id)
                    ]
                    skills_now = [
                        dict(row)
                        for row in list_rpg_skills(user_id, character_id)
                    ]
                    equipment_now = [
                        dict(row)
                        for row in list_rpg_equipment(user_id, character_id)
                    ]
                    attacks_now = [
                        dict(row)
                        for row in list_rpg_attacks(user_id, character_id)
                    ]
                    effective = apply_equipment_effects(fresh, equipment_now)
                    with ui.element("div").classes("jf-rpg-grid"):
                        for label, value in (
                            ("Personnage", fresh.get("character_name") or "—"),
                            ("Race", fresh.get("race") or "—"),
                            ("Classe", fresh.get("class_name") or "—"),
                            ("Niveau", fresh.get("character_level") or 1),
                            (
                                "PV",
                                f"{fresh.get('current_hp') or 0}/{fresh.get('max_hp') or 0}",
                            ),
                            ("CA", armor_class_total(effective)),
                            (
                                "Initiative",
                                format_modifier(initiative_total(effective)),
                            ),
                            (
                                "BMO / CMB",
                                format_modifier(cmb_total(effective)),
                            ),
                            ("DMD / CMD", str(cmd_total(effective))),
                        ):
                            with ui.column().classes("gap-0"):
                                ui.label(label).classes("text-xs jf-muted")
                                ui.label(str(value)).classes("font-bold")
                    ability_line = " · ".join(
                        f"{ability_labels[key]} {fresh.get(f'{key}_score') or 10} "
                        f"({format_modifier(ability_modifier(fresh.get(f'{key}_score') or 10))})"
                        for key in ability_labels
                    )
                    ui.label(ability_line).classes("text-sm")
                    ui.label(
                        f"Compétences avec rangs : "
                        f"{sum(1 for row in skills_now if _as_decimal(row.get('ranks')) > 0)} · "
                        f"Équipement : {len(equipment_now)} · Attaques : {len(attacks_now)}"
                    ).classes("text-sm")

                    effects = effective.get("equipment_effects") or {}
                    armor = effects.get("equipped_armor")
                    shield = effects.get("equipped_shield")
                    if armor or shield:
                        ui.label(
                            "Protection équipée : "
                            + " · ".join(
                                part
                                for part in (
                                    str(armor.get("item_name")) if armor else "",
                                    str(shield.get("item_name")) if shield else "",
                                )
                                if part
                            )
                            + f" · vitesse {effects.get('final_speed', '—')} pi"
                        ).classes("text-sm")

                    if is_fighter(fresh.get("class_name")):
                        level = _as_int(fresh.get("character_level"), 1)
                        reference = fighter_reference(level)
                        with ui.expansion(
                            "Résumé Fighter",
                            icon="shield",
                            value=True,
                        ).classes("w-full mt-3"):
                            if reference:
                                ui.label(
                                    f"BBA attendu +{reference['bab']} · sauvegardes de base : "
                                    f"Vig +{reference['fortitude']}, Réf +{reference['reflex']}, Vol +{reference['will']}."
                                ).classes("text-sm")
                                for line in fighter_cumulative_milestones(level):
                                    ui.label("• " + line).classes("text-sm")
                                feats = fighter_feat_counts(level, fresh.get("race_key"))
                                ui.label(
                                    f"Dons de référence : {feats['general']} généraux + "
                                    f"{feats['fighter_bonus']} bonus Fighter + "
                                    f"{feats['human_bonus']} racial humain = {feats['total']}."
                                ).classes("text-sm")
                            else:
                                ui.label(
                                    "Les repères détaillés Fighter couvrent actuellement les niveaux 1 à 4."
                                ).classes("text-sm jf-muted")
                            comparison = race_comparison(fresh.get("race_key"))
                            if comparison:
                                ui.label(
                                    "Race et magie : " + str(comparison.get("magic") or "")
                                ).classes("text-xs jf-muted")

                    warnings = creation_warnings(
                        fresh,
                        saves=saves_now,
                        skills=skills_now,
                        equipment=equipment_now,
                        attacks=attacks_now,
                    )
                    audit = character_sheet_audit(effective, skills_now)
                    for warning in audit.get("warnings") or ():
                        detail = str(
                            warning.get("detail")
                            or warning.get("title")
                            or ""
                        ).strip()
                        if detail:
                            warnings.append(detail)
                    if warnings:
                        with ui.expansion(
                            "Éléments à vérifier",
                            icon="warning",
                            value=True,
                        ).props("expand-separator").classes("w-full mt-3"):
                            for warning in warnings:
                                ui.label("• " + warning).classes("text-sm")
                    else:
                        ui.label(
                            "Aucun élément évident à compléter."
                        ).classes("text-positive font-bold mt-3")

                summary_panel()
                with ui.row().classes(
                    "w-full justify-between gap-2 mt-4 flex-wrap"
                ):
                    ui.button(
                        "Précédent",
                        icon="chevron_left",
                        on_click=lambda: go("gear"),
                    ).props("flat")
                    ui.button(
                        "Actualiser le résumé",
                        icon="refresh",
                        on_click=summary_panel.refresh,
                    ).props("outline color=primary")
                    ui.button(
                        "Terminer la création",
                        icon="check_circle",
                        on_click=lambda: ui.navigate.to(
                            character_url(character_id, "identite")
                        ),
                    ).props("color=primary")
