"""Panneau Combat de la fiche Personnage JDR.

Le module ne dépend ni de NiceGUI, ni de la base de données, ni de la façade
JDR. Toutes les dépendances sont injectées par ``rpg_character.py``.
"""
from __future__ import annotations


def build_combat_panel(
    *,
    ui,
    user_id,
    character,
    list_rpg_equipment,
    ability_labels,
    ability_long_labels,
    ability_modifier,
    format_modifier,
    apply_equipment_effects,
    armor_class_total,
    touch_armor_class,
    flat_footed_armor_class,
    initiative_total,
    cmb_total,
    cmd_total,
    format_number,
    update_rpg_character_combat,
    notify_error,
    character_url,
    calculation_rules_dialog,
):
    """Construit l'onglet Combat sans modifier son comportement historique."""
    equipment = list_rpg_equipment(
        user_id,
        character["id"],
    )

    with ui.card().classes(
        "w-full p-4"
    ):
        ui.label(
            "Caractéristiques"
        ).classes(
            "text-xl font-bold"
        )
        ui.label(
            "Le score temporaire remplace le score normal pour les calculs. "
            "Les six caractéristiques tiennent sur une seule ligne sur grand écran."
        ).classes(
            "text-sm jf-muted"
        )

        ability_inputs = {}

        with ui.element("div").classes(
            "jf-rpg-ability-grid mt-2"
        ):
            for ability_key in ability_labels:
                with ui.element("div").classes(
                    "jf-rpg-ability-card"
                ):
                    with ui.element("div").classes(
                        "jf-rpg-ability-header"
                    ):
                        ui.label(
                            f"{ability_labels[ability_key]} — "
                            f"{ability_long_labels[ability_key]}"
                        ).classes(
                            "jf-rpg-ability-title"
                        )
                        modifier_label = ui.label(
                            ""
                        ).classes(
                            "jf-rpg-ability-modifier"
                        )

                    with ui.element("div").classes(
                        "jf-rpg-ability-fields"
                    ):
                        score_input = ui.number(
                            label="Score",
                            value=character[
                                f"{ability_key}_score"
                            ],
                            min=1,
                            max=100,
                            step=1,
                        ).props(
                            "dense outlined inputmode=numeric"
                        ).classes(
                            "jf-rpg-compact-field"
                        )

                        temp_input = ui.number(
                            label="Temp.",
                            value=character[
                                f"{ability_key}_temp_score"
                            ],
                            min=1,
                            max=100,
                            step=1,
                        ).props(
                            "dense outlined inputmode=numeric clearable"
                        ).classes(
                            "jf-rpg-compact-field"
                        ).tooltip(
                            "Score temporaire"
                        )

                    def update_modifier(
                        _=None,
                        *,
                        score_control=score_input,
                        temp_control=temp_input,
                        label_control=modifier_label,
                    ):
                        label_control.set_text(
                            format_modifier(
                                ability_modifier(
                                    score_control.value,
                                    temp_control.value,
                                )
                            )
                        )

                    score_input.on_value_change(
                        update_modifier
                    )
                    temp_input.on_value_change(
                        update_modifier
                    )
                    update_modifier()

                    ability_inputs[ability_key] = {
                        "score": score_input,
                        "temp": temp_input,
                    }

    with ui.card().classes(
        "w-full p-4"
    ):
        ui.label(
            "Combat et défenses"
        ).classes(
            "text-xl font-bold"
        )

        with ui.element("div").classes(
            "jf-rpg-combat-grid mt-2"
        ):
            max_hp_input = ui.number(
                label="PV maximums",
                value=character["max_hp"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value")
            current_hp_input = ui.number(
                label="PV actuels",
                value=character["current_hp"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value")
            nonlethal_input = ui.number(
                label="Dégâts non létaux",
                value=character["nonlethal_damage"],
                min=0,
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value")
            final_speed_display = ui.input(
                label="Vitesse finale",
                value=(
                    f"{character.get('final_speed', character.get('base_speed', 30))} pi"
                ),
            ).props(
                "dense outlined readonly"
            ).classes(
                "jf-rpg-compact-field jf-rpg-combat-value"
            ).tooltip(
                "Calculée à partir de la race, de l’armure et de la charge"
            )
            speed_input = ui.input(
                label="Autres vitesses / note",
                value=character["speed"] or "",
                placeholder="Ex. nage 20 pi",
            ).props(
                "dense outlined maxlength=80"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value")
            dr_input = ui.input(
                label="Réduction dégâts",
                value=character["damage_reduction"] or "",
                placeholder="Ex. 5/argent",
            ).props(
                "dense outlined maxlength=80"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value").tooltip(
                "Réduction des dégâts"
            )
            sr_input = ui.number(
                label="Résistance magie",
                value=character["spell_resistance"],
                min=0,
                step=1,
            ).props(
                "dense outlined clearable inputmode=numeric"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value").tooltip(
                "Résistance à la magie"
            )
            bab_input = ui.number(
                label="BBA",
                value=character["base_attack_bonus"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value").tooltip(
                "Bonus de base à l’attaque"
            )
            armor_input = ui.number(
                label="Armure (manuel)",
                value=character["armor_bonus"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value").tooltip(
                "Bonus d’armure"
            )
            shield_input = ui.number(
                label="Bouclier (manuel)",
                value=character["shield_bonus"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value").tooltip(
                "Bonus de bouclier"
            )
            natural_input = ui.number(
                label="Armure naturelle",
                value=character["natural_armor_bonus"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value")
            deflection_input = ui.number(
                label="Déviation",
                value=character["deflection_bonus"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value").tooltip(
                "Bonus de déviation"
            )
            misc_ac_input = ui.number(
                label="Divers CA",
                value=character["misc_ac_modifier"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value")
            armor_penalty_input = ui.number(
                label="Pénalité armure (manuel)",
                value=character["armor_check_penalty"],
                max=0,
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value")
            initiative_misc_input = ui.number(
                label="Divers initiative",
                value=character["initiative_misc_modifier"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value")
            cmb_misc_input = ui.number(
                label="Divers BMO/CMB",
                value=character["cmb_misc_modifier"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value")
            cmd_misc_input = ui.number(
                label="Divers DMD/CMD",
                value=character["cmd_misc_modifier"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field jf-rpg-combat-value")

        def current_draft():
            draft = dict(character)

            for ability_key, controls in ability_inputs.items():
                draft[f"{ability_key}_score"] = controls["score"].value
                draft[f"{ability_key}_temp_score"] = controls["temp"].value

            draft.update({
                "max_hp": max_hp_input.value,
                "current_hp": current_hp_input.value,
                "nonlethal_damage": nonlethal_input.value,
                "speed": speed_input.value,
                "damage_reduction": dr_input.value,
                "spell_resistance": sr_input.value,
                "base_attack_bonus": bab_input.value,
                "armor_bonus": armor_input.value,
                "shield_bonus": shield_input.value,
                "natural_armor_bonus": natural_input.value,
                "deflection_bonus": deflection_input.value,
                "misc_ac_modifier": misc_ac_input.value,
                "armor_check_penalty": armor_penalty_input.value,
                "initiative_misc_modifier": initiative_misc_input.value,
                "cmb_misc_modifier": cmb_misc_input.value,
                "cmd_misc_modifier": cmd_misc_input.value,
                "grapple_misc_modifier": cmb_misc_input.value,
            })
            return apply_equipment_effects(
                draft,
                equipment,
            )

        @ui.refreshable
        def render_preview():
            draft = current_draft()
            final_speed_display.value = (
                f"{draft['equipment_effects']['final_speed']} pi"
            )
            final_speed_display.update()

            with ui.element("div").classes(
                "jf-rpg-summary mt-3"
            ):
                with ui.element("div").classes(
                    "jf-rpg-result-grid"
                ):
                    for label, value in (
                        ("CA totale", armor_class_total(draft)),
                        ("CA contact", touch_armor_class(draft)),
                        (
                            "Pris au dépourvu",
                            flat_footed_armor_class(draft),
                        ),
                        (
                            "Initiative",
                            format_modifier(initiative_total(draft)),
                        ),
                        (
                            "BMO / CMB",
                            format_modifier(cmb_total(draft)),
                        ),
                        ("DMD / CMD", str(cmd_total(draft))),
                    ):
                        with ui.element("div").classes(
                            "jf-rpg-result-item"
                        ):
                            ui.label(label).classes(
                                "text-xs jf-muted"
                            )
                            ui.label(str(value)).classes(
                                "jf-rpg-stat-value"
                            )

                effects = draft["equipment_effects"]
                capacity = effects["carrying_capacity"]
                armor_name = (
                    effects["equipped_armor"]["item_name"]
                    if effects["equipped_armor"]
                    else "Aucune"
                )
                shield_name = (
                    effects["equipped_shield"]["item_name"]
                    if effects["equipped_shield"]
                    else "Aucun"
                )
                max_dex = effects["effective_max_dex_bonus"]
                with ui.element("div").classes(
                    "jf-rpg-equipment-breakdown mt-2"
                ):
                    ui.label(
                        "Équipement et encombrement"
                    ).classes("font-bold")
                    ui.label(
                        (
                            f"Armure : {armor_name} — "
                            f"bouclier : {shield_name} — "
                            f"poids {format_number(effects['carried_weight'])} lb — "
                            f"charge {effects['load_label'].lower()} — "
                            f"seuil léger {format_number(capacity['light_max'])} lb."
                        )
                    )
                    ui.label(
                        (
                            f"Vitesse de base {effects['base_speed']} pi → "
                            f"vitesse finale {effects['final_speed']} pi; "
                            f"DEX max "
                            f"{max_dex if max_dex is not None else '—'}; "
                            f"pénalité aux tests "
                            f"{format_modifier(effects['effective_armor_check_penalty'])}."
                        )
                    )

        preview_controls = [
            max_hp_input,
            current_hp_input,
            nonlethal_input,
            bab_input,
            armor_input,
            shield_input,
            natural_input,
            deflection_input,
            misc_ac_input,
            armor_penalty_input,
            initiative_misc_input,
            cmb_misc_input,
            cmd_misc_input,
        ]

        for control in preview_controls:
            control.on_value_change(
                lambda event: render_preview.refresh()
            )

        for controls in ability_inputs.values():
            controls["score"].on_value_change(
                lambda event: render_preview.refresh()
            )
            controls["temp"].on_value_change(
                lambda event: render_preview.refresh()
            )

        render_preview()

        def save_combat():
            values = current_draft()

            try:
                update_rpg_character_combat(
                    user_id,
                    character["id"],
                    values,
                )
            except Exception as error:
                notify_error(
                    error,
                    "Les caractéristiques n’ont pas pu être enregistrées.",
                )
                return

            ui.notify(
                "Caractéristiques enregistrées.",
                type="positive",
            )
            ui.navigate.to(
                character_url(
                    character["id"],
                    "combat",
                )
            )

        def open_rules():
            calculation_rules_dialog(
                user_id,
                current_draft(),
            )

        with ui.row().classes(
            "jf-rpg-section-actions gap-2 flex-wrap"
        ):
            ui.button(
                "Règles de calcul",
                icon="menu_book",
                on_click=open_rules,
            ).props(
                "outline color=primary"
            )
            ui.button(
                "Enregistrer les caractéristiques",
                icon="save",
                on_click=save_combat,
            ).props(
                "color=primary"
            )
