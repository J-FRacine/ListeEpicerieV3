from __future__ import annotations

from decimal import Decimal

from nicegui import ui

from rpg_character_data import (
    create_custom_rpg_skill,
    create_rpg_attack,
    create_rpg_character,
    delete_custom_rpg_skill,
    delete_rpg_attack,
    delete_rpg_character,
    get_rpg_character,
    list_rpg_attacks,
    list_rpg_characters,
    list_rpg_saves,
    list_rpg_skills,
    update_rpg_attack,
    update_rpg_character_combat,
    update_rpg_character_identity,
    update_rpg_saves,
    update_rpg_skills,
)
from rpg_character_rules import (
    ABILITY_LABELS,
    ABILITY_LONG_LABELS,
    SAVE_DEFINITIONS,
    SIZE_LABELS,
    ability_modifier,
    ability_modifier_for_character,
    armor_class_total,
    attack_total,
    flat_footed_armor_class,
    format_modifier,
    format_number,
    grapple_total,
    initiative_total,
    save_total,
    skill_total,
    touch_armor_class,
)


RPG_CSS = r"""
.jf-rpg-private {
    width: 100%;
    padding: 0.85rem 1rem;
    border-left: 5px solid #65508f;
    border-radius: 14px;
    background: rgba(101, 80, 143, 0.10);
}

.jf-rpg-grid {
    display: grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(
                min(100%, 13rem),
                1fr
            )
        );
    gap: 0.8rem;
    width: 100%;
}

.jf-rpg-ability-grid {
    display: grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(
                min(100%, 12rem),
                1fr
            )
        );
    gap: 0.75rem;
    width: 100%;
}

.jf-rpg-ability-card,
.jf-rpg-save-card,
.jf-rpg-skill-card,
.jf-rpg-attack-card {
    width: 100%;
    padding: 0.95rem;
    border: 1px solid var(--jf-border);
    border-radius: 16px;
    background: var(--jf-surface);
}

.jf-rpg-stat-value {
    color: var(--jf-navy);
    font-size: 1.55rem;
    font-weight: 800;
}

.body--dark .jf-rpg-stat-value {
    color: #dceaf6;
}

.jf-rpg-summary {
    width: 100%;
    padding: 0.85rem 1rem;
    border-left: 5px solid var(--jf-blue);
    border-radius: 14px;
    background: var(--jf-blue-soft);
}

.jf-rpg-ravenloft {
    border-left: 5px solid #65508f;
}

.jf-rpg-help {
    width: 100%;
    padding: 0.8rem 0.95rem;
    border-left: 4px solid var(--jf-gold);
    border-radius: 12px;
    background: rgba(189, 149, 85, 0.10);
}

.jf-rpg-character-banner {
    width: 100%;
    padding: 1rem;
    border-radius: 16px;
    color: white;
    background:
        linear-gradient(
            135deg,
            #1b2836 0%,
            #35485d 62%,
            #65508f 100%
        );
}

.jf-rpg-skill-total {
    min-width: 3.4rem;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    text-align: center;
    color: white;
    background: var(--jf-navy);
    font-weight: 800;
}

.jf-rpg-section-actions {
    position: sticky;
    bottom: 0.75rem;
    z-index: 3;
    width: fit-content;
    margin-left: auto;
    padding: 0.4rem;
    border: 1px solid var(--jf-border);
    border-radius: 14px;
    background: var(--jf-surface);
    box-shadow: var(--jf-shadow);
}

@media (max-width: 680px) {
    .jf-rpg-section-actions {
        width: 100%;
    }

    .jf-rpg-section-actions .q-btn {
        width: 100%;
    }
}
"""

ui.add_css(
    RPG_CSS,
    shared=True,
)


def _as_number(value, default=0):
    if value in (None, ""):
        return default

    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


def _optional_number(value):
    if value in (None, ""):
        return None

    return _as_number(value)


def _safe_notify_error(
    error,
    fallback,
):
    if isinstance(
        error,
        (
            ValueError,
            PermissionError,
        ),
    ):
        message = str(error)
    else:
        message = fallback

    ui.notify(
        message,
        type="warning"
        if isinstance(
            error,
            (
                ValueError,
                PermissionError,
            ),
        )
        else "negative",
    )


def _character_url(
    character_id,
    section=None,
):
    url = (
        f"/?tab=jdr"
        f"&character={character_id}"
    )

    if section:
        url += (
            f"&section={section}"
        )

    return url


def _create_character_dialog(
    user_id,
    player_default,
):
    with ui.dialog() as dialog:
        with ui.card().classes(
            "w-full max-w-lg p-5"
        ):
            ui.label(
                "Créer un personnage"
            ).classes(
                "text-xl font-bold"
            )

            name_input = ui.input(
                label="Nom du personnage",
            ).props(
                "autofocus maxlength=120"
            ).classes(
                "w-full"
            )

            player_input = ui.input(
                label="Nom du joueur",
                value=player_default,
            ).props(
                "maxlength=120"
            ).classes(
                "w-full"
            )

            def create():
                try:
                    character_id = (
                        create_rpg_character(
                            user_id,
                            name_input.value,
                            player_input.value,
                        )
                    )
                except Exception as error:
                    _safe_notify_error(
                        error,
                        (
                            "Le personnage n’a pas "
                            "pu être créé."
                        ),
                    )
                    return

                dialog.close()
                ui.notify(
                    "Personnage créé.",
                    type="positive",
                )
                ui.navigate.to(
                    _character_url(
                        character_id
                    )
                )

            with ui.row().classes(
                "w-full justify-end gap-2 mt-3"
            ):
                ui.button(
                    "Annuler",
                    on_click=dialog.close,
                ).props(
                    "flat"
                )
                ui.button(
                    "Créer",
                    icon="person_add",
                    on_click=create,
                ).props(
                    "color=primary"
                )

    dialog.open()


def _delete_character_dialog(
    user_id,
    character,
):
    with ui.dialog() as dialog:
        with ui.card().classes(
            "w-full max-w-md p-5"
        ):
            ui.label(
                "Supprimer le personnage?"
            ).classes(
                "text-xl font-bold"
            )
            ui.label(
                character[
                    "character_name"
                ]
            ).classes(
                "font-bold"
            )
            ui.label(
                "Cette suppression est définitive. "
                "Les sauvegardes, compétences et "
                "attaques du personnage seront supprimées."
            ).classes(
                "text-sm text-negative"
            )

            def confirm():
                try:
                    delete_rpg_character(
                        user_id,
                        character["id"],
                    )
                except Exception as error:
                    _safe_notify_error(
                        error,
                        (
                            "Le personnage n’a pas "
                            "pu être supprimé."
                        ),
                    )
                    return

                dialog.close()
                ui.notify(
                    "Personnage supprimé.",
                    type="positive",
                )
                ui.navigate.to(
                    "/?tab=jdr"
                )

            with ui.row().classes(
                "w-full justify-end gap-2 mt-3"
            ):
                ui.button(
                    "Annuler",
                    on_click=dialog.close,
                ).props(
                    "flat"
                )
                ui.button(
                    "Supprimer",
                    icon="delete",
                    on_click=confirm,
                ).props(
                    "color=negative"
                )

    dialog.open()


def _identity_panel(
    user_id,
    character,
):
    with ui.card().classes(
        "w-full p-5"
    ):
        ui.label(
            "Identité du personnage"
        ).classes(
            "text-xl font-bold"
        )
        ui.label(
            "Les champs suivent l’organisation générale "
            "de la feuille Ravenloft fournie."
        ).classes(
            "text-sm jf-muted"
        )

        with ui.element("div").classes(
            "jf-rpg-grid mt-2"
        ):
            name_input = ui.input(
                label="Nom du personnage",
                value=character[
                    "character_name"
                ],
            ).props(
                "maxlength=120"
            ).classes(
                "w-full"
            )
            player_input = ui.input(
                label="Joueur",
                value=character[
                    "player_name"
                ] or "",
            ).props(
                "maxlength=120"
            ).classes(
                "w-full"
            )
            campaign_input = ui.input(
                label="Campagne",
                value=character[
                    "campaign"
                ] or "",
            ).props(
                "maxlength=160"
            ).classes(
                "w-full"
            )
            class_input = ui.input(
                label="Classe",
                value=character[
                    "class_name"
                ] or "",
            ).props(
                "maxlength=120"
            ).classes(
                "w-full"
            )
            level_input = ui.number(
                label="Niveau",
                value=character[
                    "character_level"
                ],
                min=1,
                max=100,
                step=1,
            ).props(
                "inputmode=numeric"
            ).classes(
                "w-full"
            )
            race_input = ui.input(
                label="Race",
                value=character[
                    "race"
                ] or "",
            ).props(
                "maxlength=120"
            ).classes(
                "w-full"
            )
            alignment_input = ui.input(
                label="Alignement",
                value=character[
                    "alignment"
                ] or "",
            ).props(
                "maxlength=80"
            ).classes(
                "w-full"
            )
            deity_input = ui.input(
                label="Divinité",
                value=character[
                    "deity"
                ] or "",
            ).props(
                "maxlength=120"
            ).classes(
                "w-full"
            )
            size_input = ui.select(
                SIZE_LABELS,
                label="Catégorie de taille",
                value=character[
                    "size_key"
                ],
            ).classes(
                "w-full"
            )
            age_input = ui.input(
                label="Âge",
                value=character[
                    "age_text"
                ] or "",
            ).props(
                "maxlength=60"
            ).classes(
                "w-full"
            )
            gender_input = ui.input(
                label="Genre",
                value=character[
                    "gender"
                ] or "",
            ).props(
                "maxlength=80"
            ).classes(
                "w-full"
            )
            height_input = ui.input(
                label="Taille physique",
                value=character[
                    "height_text"
                ] or "",
            ).props(
                "maxlength=60"
            ).classes(
                "w-full"
            )
            weight_input = ui.input(
                label="Poids",
                value=character[
                    "weight_text"
                ] or "",
            ).props(
                "maxlength=60"
            ).classes(
                "w-full"
            )
            eyes_input = ui.input(
                label="Yeux",
                value=character[
                    "eyes"
                ] or "",
            ).props(
                "maxlength=80"
            ).classes(
                "w-full"
            )
            hair_input = ui.input(
                label="Cheveux",
                value=character[
                    "hair"
                ] or "",
            ).props(
                "maxlength=80"
            ).classes(
                "w-full"
            )
            skin_input = ui.input(
                label="Peau",
                value=character[
                    "skin"
                ] or "",
            ).props(
                "maxlength=80"
            ).classes(
                "w-full"
            )
            xp_input = ui.number(
                label="Points d’expérience",
                value=character[
                    "experience_points"
                ],
                min=0,
                step=1,
            ).props(
                "inputmode=numeric"
            ).classes(
                "w-full"
            )

        def save_identity():
            try:
                update_rpg_character_identity(
                    user_id,
                    character["id"],
                    {
                        "character_name": (
                            name_input.value
                        ),
                        "player_name": (
                            player_input.value
                        ),
                        "campaign": (
                            campaign_input.value
                        ),
                        "class_name": (
                            class_input.value
                        ),
                        "character_level": (
                            level_input.value
                        ),
                        "race": race_input.value,
                        "alignment": (
                            alignment_input.value
                        ),
                        "deity": deity_input.value,
                        "size_key": (
                            size_input.value
                        ),
                        "age_text": age_input.value,
                        "gender": gender_input.value,
                        "height_text": (
                            height_input.value
                        ),
                        "weight_text": (
                            weight_input.value
                        ),
                        "eyes": eyes_input.value,
                        "hair": hair_input.value,
                        "skin": skin_input.value,
                        "experience_points": (
                            xp_input.value
                        ),
                    },
                )
            except Exception as error:
                _safe_notify_error(
                    error,
                    (
                        "L’identité n’a pas "
                        "pu être enregistrée."
                    ),
                )
                return

            ui.notify(
                "Identité enregistrée.",
                type="positive",
            )
            ui.navigate.to(
                _character_url(
                    character["id"],
                    "identite",
                )
            )

        with ui.row().classes(
            "jf-rpg-section-actions"
        ):
            ui.button(
                "Enregistrer l’identité",
                icon="save",
                on_click=save_identity,
            ).props(
                "color=primary"
            )


def _combat_panel(
    user_id,
    character,
):
    with ui.card().classes(
        "w-full p-5"
    ):
        ui.label(
            "Caractéristiques"
        ).classes(
            "text-xl font-bold"
        )
        ui.label(
            "Le modificateur est calculé automatiquement. "
            "Un score temporaire, lorsqu’il est inscrit, "
            "remplace le score normal pour les calculs."
        ).classes(
            "text-sm jf-muted"
        )

        ability_inputs = {}

        with ui.element("div").classes(
            "jf-rpg-ability-grid mt-3"
        ):
            for ability_key in ABILITY_LABELS:
                with ui.element("div").classes(
                    "jf-rpg-ability-card"
                ):
                    ui.label(
                        (
                            f"{ABILITY_LABELS[ability_key]} - "
                            f"{ABILITY_LONG_LABELS[ability_key]}"
                        )
                    ).classes(
                        "font-bold"
                    )

                    score_input = ui.number(
                        label="Score",
                        value=character[
                            f"{ability_key}_score"
                        ],
                        min=1,
                        max=100,
                        step=1,
                    ).props(
                        "inputmode=numeric"
                    ).classes(
                        "w-full"
                    )

                    temp_input = ui.number(
                        label="Score temporaire",
                        value=character[
                            f"{ability_key}_temp_score"
                        ],
                        min=1,
                        max=100,
                        step=1,
                    ).props(
                        "inputmode=numeric clearable"
                    ).classes(
                        "w-full"
                    )

                    modifier_label = ui.label(
                        ""
                    ).classes(
                        "jf-rpg-stat-value"
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

                    ability_inputs[
                        ability_key
                    ] = {
                        "score": score_input,
                        "temp": temp_input,
                    }

    with ui.card().classes(
        "w-full p-5"
    ):
        ui.label(
            "Combat et défenses"
        ).classes(
            "text-xl font-bold"
        )

        with ui.element("div").classes(
            "jf-rpg-grid mt-2"
        ):
            max_hp_input = ui.number(
                label="Points de vie maximums",
                value=character[
                    "max_hp"
                ],
                step=1,
            ).classes(
                "w-full"
            )
            current_hp_input = ui.number(
                label="Points de vie actuels",
                value=character[
                    "current_hp"
                ],
                step=1,
            ).classes(
                "w-full"
            )
            nonlethal_input = ui.number(
                label="Dégâts non létaux",
                value=character[
                    "nonlethal_damage"
                ],
                min=0,
                step=1,
            ).classes(
                "w-full"
            )
            speed_input = ui.input(
                label="Vitesse",
                value=character[
                    "speed"
                ] or "",
                placeholder="Ex. 30 ft",
            ).props(
                "maxlength=80"
            ).classes(
                "w-full"
            )
            dr_input = ui.input(
                label="Réduction des dégâts",
                value=character[
                    "damage_reduction"
                ] or "",
                placeholder="Ex. 5/argent",
            ).props(
                "maxlength=80"
            ).classes(
                "w-full"
            )
            sr_input = ui.number(
                label="Résistance à la magie",
                value=character[
                    "spell_resistance"
                ],
                min=0,
                step=1,
            ).props(
                "clearable"
            ).classes(
                "w-full"
            )
            bab_input = ui.number(
                label="Bonus de base à l’attaque",
                value=character[
                    "base_attack_bonus"
                ],
                step=1,
            ).classes(
                "w-full"
            )
            armor_input = ui.number(
                label="Bonus d’armure",
                value=character[
                    "armor_bonus"
                ],
                step=1,
            ).classes(
                "w-full"
            )
            shield_input = ui.number(
                label="Bonus de bouclier",
                value=character[
                    "shield_bonus"
                ],
                step=1,
            ).classes(
                "w-full"
            )
            natural_input = ui.number(
                label="Armure naturelle",
                value=character[
                    "natural_armor_bonus"
                ],
                step=1,
            ).classes(
                "w-full"
            )
            deflection_input = ui.number(
                label="Bonus de déviation",
                value=character[
                    "deflection_bonus"
                ],
                step=1,
            ).classes(
                "w-full"
            )
            misc_ac_input = ui.number(
                label="Modificateur divers de CA",
                value=character[
                    "misc_ac_modifier"
                ],
                step=1,
            ).classes(
                "w-full"
            )
            armor_penalty_input = ui.number(
                label="Pénalité d’armure",
                value=character[
                    "armor_check_penalty"
                ],
                max=0,
                step=1,
            ).classes(
                "w-full"
            )
            initiative_misc_input = ui.number(
                label="Divers - Initiative",
                value=character[
                    "initiative_misc_modifier"
                ],
                step=1,
            ).classes(
                "w-full"
            )
            grapple_misc_input = ui.number(
                label="Divers - Lutte",
                value=character[
                    "grapple_misc_modifier"
                ],
                step=1,
            ).classes(
                "w-full"
            )

        @ui.refreshable
        def render_preview():
            draft = dict(
                character
            )

            for ability_key, controls in (
                ability_inputs.items()
            ):
                draft[
                    f"{ability_key}_score"
                ] = controls[
                    "score"
                ].value
                draft[
                    f"{ability_key}_temp_score"
                ] = controls[
                    "temp"
                ].value

            draft.update(
                {
                    "max_hp": max_hp_input.value,
                    "current_hp": (
                        current_hp_input.value
                    ),
                    "nonlethal_damage": (
                        nonlethal_input.value
                    ),
                    "base_attack_bonus": (
                        bab_input.value
                    ),
                    "armor_bonus": (
                        armor_input.value
                    ),
                    "shield_bonus": (
                        shield_input.value
                    ),
                    "natural_armor_bonus": (
                        natural_input.value
                    ),
                    "deflection_bonus": (
                        deflection_input.value
                    ),
                    "misc_ac_modifier": (
                        misc_ac_input.value
                    ),
                    "armor_check_penalty": (
                        armor_penalty_input.value
                    ),
                    "initiative_misc_modifier": (
                        initiative_misc_input.value
                    ),
                    "grapple_misc_modifier": (
                        grapple_misc_input.value
                    ),
                }
            )

            with ui.element("div").classes(
                "jf-rpg-summary mt-3"
            ):
                with ui.element("div").classes(
                    "jf-rpg-grid"
                ):
                    for label, value in (
                        (
                            "CA totale",
                            armor_class_total(
                                draft
                            ),
                        ),
                        (
                            "CA de contact",
                            touch_armor_class(
                                draft
                            ),
                        ),
                        (
                            "Pris au dépourvu",
                            flat_footed_armor_class(
                                draft
                            ),
                        ),
                        (
                            "Initiative",
                            format_modifier(
                                initiative_total(
                                    draft
                                )
                            ),
                        ),
                        (
                            "Lutte",
                            format_modifier(
                                grapple_total(
                                    draft
                                )
                            ),
                        ),
                    ):
                        with ui.column().classes(
                            "gap-0"
                        ):
                            ui.label(
                                label
                            ).classes(
                                "text-xs jf-muted"
                            )
                            ui.label(
                                str(value)
                            ).classes(
                                "jf-rpg-stat-value"
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
            grapple_misc_input,
        ]

        for control in preview_controls:
            control.on_value_change(
                lambda event: (
                    render_preview.refresh()
                )
            )

        for controls in ability_inputs.values():
            controls["score"].on_value_change(
                lambda event: (
                    render_preview.refresh()
                )
            )
            controls["temp"].on_value_change(
                lambda event: (
                    render_preview.refresh()
                )
            )

        render_preview()

        def save_combat():
            values = {
                "max_hp": max_hp_input.value,
                "current_hp": (
                    current_hp_input.value
                ),
                "nonlethal_damage": (
                    nonlethal_input.value
                ),
                "speed": speed_input.value,
                "damage_reduction": (
                    dr_input.value
                ),
                "spell_resistance": (
                    sr_input.value
                ),
                "base_attack_bonus": (
                    bab_input.value
                ),
                "armor_bonus": (
                    armor_input.value
                ),
                "shield_bonus": (
                    shield_input.value
                ),
                "natural_armor_bonus": (
                    natural_input.value
                ),
                "deflection_bonus": (
                    deflection_input.value
                ),
                "misc_ac_modifier": (
                    misc_ac_input.value
                ),
                "armor_check_penalty": (
                    armor_penalty_input.value
                ),
                "initiative_misc_modifier": (
                    initiative_misc_input.value
                ),
                "grapple_misc_modifier": (
                    grapple_misc_input.value
                ),
            }

            for ability_key, controls in (
                ability_inputs.items()
            ):
                values[
                    f"{ability_key}_score"
                ] = controls[
                    "score"
                ].value
                values[
                    f"{ability_key}_temp_score"
                ] = controls[
                    "temp"
                ].value

            try:
                update_rpg_character_combat(
                    user_id,
                    character["id"],
                    values,
                )
            except Exception as error:
                _safe_notify_error(
                    error,
                    (
                        "Les caractéristiques "
                        "n’ont pas pu être enregistrées."
                    ),
                )
                return

            ui.notify(
                "Caractéristiques enregistrées.",
                type="positive",
            )
            ui.navigate.to(
                _character_url(
                    character["id"],
                    "combat",
                )
            )

        with ui.row().classes(
            "jf-rpg-section-actions"
        ):
            ui.button(
                "Enregistrer les caractéristiques",
                icon="save",
                on_click=save_combat,
            ).props(
                "color=primary"
            )


def _saves_panel(
    user_id,
    character,
):
    saves = list_rpg_saves(
        user_id,
        character["id"],
    )
    editors = []

    with ui.card().classes(
        "w-full p-5"
    ):
        ui.label(
            "Jets de sauvegarde"
        ).classes(
            "text-xl font-bold"
        )
        ui.label(
            "Vigueur, Réflexes et Volonté sont accompagnés "
            "des jets de Peur, Horreur et Folie de Ravenloft."
        ).classes(
            "text-sm jf-muted"
        )

        with ui.element("div").classes(
            "jf-rpg-grid mt-3"
        ):
            for save_row in saves:
                definition = (
                    SAVE_DEFINITIONS[
                        save_row[
                            "save_key"
                        ]
                    ]
                )

                card_classes = (
                    "jf-rpg-save-card "
                    "jf-rpg-ravenloft"
                    if definition[
                        "ravenloft"
                    ]
                    else "jf-rpg-save-card"
                )

                with ui.element("div").classes(
                    card_classes
                ):
                    with ui.row().classes(
                        "w-full items-start "
                        "justify-between gap-2"
                    ):
                        with ui.column().classes(
                            "gap-0"
                        ):
                            ui.label(
                                definition[
                                    "label"
                                ]
                            ).classes(
                                "font-bold"
                            )
                            ui.label(
                                (
                                    "Ravenloft"
                                    if definition[
                                        "ravenloft"
                                    ]
                                    else "Sauvegarde générale"
                                )
                            ).classes(
                                "text-xs jf-muted"
                            )

                        total_label = ui.label(
                            format_modifier(
                                save_total(
                                    character,
                                    save_row,
                                )
                            )
                        ).classes(
                            "jf-rpg-skill-total"
                        )

                    with ui.element("div").classes(
                        "jf-rpg-grid mt-2"
                    ):
                        base_input = ui.number(
                            label="Base",
                            value=save_row[
                                "base_save"
                            ],
                            step=1,
                        ).classes(
                            "w-full"
                        )
                        magic_input = ui.number(
                            label="Magie",
                            value=save_row[
                                "magic_modifier"
                            ],
                            step=1,
                        ).classes(
                            "w-full"
                        )
                        misc_input = ui.number(
                            label="Divers",
                            value=save_row[
                                "misc_modifier"
                            ],
                            step=1,
                        ).classes(
                            "w-full"
                        )
                        temp_input = ui.number(
                            label="Temporaire",
                            value=save_row[
                                "temporary_modifier"
                            ],
                            step=1,
                        ).classes(
                            "w-full"
                        )

                    notes_input = ui.textarea(
                        label=(
                            "Modificateurs conditionnels"
                        ),
                        value=save_row[
                            "conditional_notes"
                        ] or "",
                    ).props(
                        "maxlength=500 autogrow"
                    ).classes(
                        "w-full"
                    )

                    ability_key = definition[
                        "ability_key"
                    ]

                    ui.label(
                        (
                            "Caractéristique : "
                            f"{ABILITY_LABELS[ability_key]} "
                            f"{format_modifier(ability_modifier_for_character(character, ability_key))}"
                        )
                    ).classes(
                        "text-xs jf-muted"
                    )

                    def update_total(
                        event=None,
                        *,
                        base_control=base_input,
                        magic_control=magic_input,
                        misc_control=misc_input,
                        temp_control=temp_input,
                        ability=ability_key,
                        label_control=total_label,
                    ):
                        total = (
                            _as_number(
                                base_control.value
                            )
                            + _as_number(
                                magic_control.value
                            )
                            + _as_number(
                                misc_control.value
                            )
                            + _as_number(
                                temp_control.value
                            )
                            + ability_modifier_for_character(
                                character,
                                ability,
                            )
                        )
                        label_control.set_text(
                            format_modifier(total)
                        )

                    for control in (
                        base_input,
                        magic_input,
                        misc_input,
                        temp_input,
                    ):
                        control.on_value_change(
                            update_total
                        )

                    editors.append(
                        {
                            "save_key": (
                                save_row[
                                    "save_key"
                                ]
                            ),
                            "base": base_input,
                            "magic": magic_input,
                            "misc": misc_input,
                            "temp": temp_input,
                            "notes": notes_input,
                        }
                    )

        def save_saves():
            rows = [
                {
                    "save_key": editor[
                        "save_key"
                    ],
                    "base_save": editor[
                        "base"
                    ].value,
                    "magic_modifier": editor[
                        "magic"
                    ].value,
                    "misc_modifier": editor[
                        "misc"
                    ].value,
                    "temporary_modifier": editor[
                        "temp"
                    ].value,
                    "conditional_notes": editor[
                        "notes"
                    ].value,
                }
                for editor in editors
            ]

            try:
                update_rpg_saves(
                    user_id,
                    character["id"],
                    rows,
                )
            except Exception as error:
                _safe_notify_error(
                    error,
                    (
                        "Les sauvegardes n’ont "
                        "pas pu être enregistrées."
                    ),
                )
                return

            ui.notify(
                "Jets de sauvegarde enregistrés.",
                type="positive",
            )

        with ui.row().classes(
            "jf-rpg-section-actions"
        ):
            ui.button(
                "Enregistrer les sauvegardes",
                icon="save",
                on_click=save_saves,
            ).props(
                "color=primary"
            )


def _skill_dialog(
    user_id,
    character,
    on_saved,
):
    with ui.dialog() as dialog:
        with ui.card().classes(
            "w-full max-w-lg p-5"
        ):
            ui.label(
                "Ajouter une compétence"
            ).classes(
                "text-xl font-bold"
            )

            name_input = ui.input(
                label="Nom",
            ).props(
                "autofocus maxlength=120"
            ).classes(
                "w-full"
            )
            ability_input = ui.select(
                {
                    key: (
                        f"{label} - "
                        f"{ABILITY_LONG_LABELS[key]}"
                    )
                    for key, label
                    in ABILITY_LABELS.items()
                },
                value="int",
                label="Caractéristique",
            ).classes(
                "w-full"
            )
            trained_input = ui.checkbox(
                "Utilisable seulement avec formation"
            )
            armor_input = ui.checkbox(
                "La pénalité d’armure s’applique"
            )
            double_input = ui.checkbox(
                "Doubler la pénalité d’armure"
            )

            def save():
                try:
                    create_custom_rpg_skill(
                        user_id,
                        character["id"],
                        skill_name=name_input.value,
                        ability_key=(
                            ability_input.value
                        ),
                        trained_only=(
                            trained_input.value
                        ),
                        armor_check_applies=(
                            armor_input.value
                        ),
                        double_armor_penalty=(
                            double_input.value
                        ),
                    )
                except Exception as error:
                    _safe_notify_error(
                        error,
                        (
                            "La compétence n’a pas "
                            "pu être créée."
                        ),
                    )
                    return

                dialog.close()
                ui.notify(
                    "Compétence ajoutée.",
                    type="positive",
                )
                on_saved()

            with ui.row().classes(
                "w-full justify-end gap-2 mt-3"
            ):
                ui.button(
                    "Annuler",
                    on_click=dialog.close,
                ).props(
                    "flat"
                )
                ui.button(
                    "Ajouter",
                    icon="add",
                    on_click=save,
                ).props(
                    "color=primary"
                )

    dialog.open()


def _skills_panel(
    user_id,
    character,
):
    with ui.row().classes(
        "w-full items-center justify-between "
        "gap-3 flex-wrap"
    ):
        with ui.column().classes(
            "gap-0"
        ):
            ui.label(
                "Compétences"
            ).classes(
                "text-xl font-bold"
            )
            ui.label(
                "Les rangs peuvent contenir des demi-points. "
                "La pénalité d’armure est appliquée automatiquement."
            ).classes(
                "text-sm jf-muted"
            )

        ui.button(
            "Ajouter une compétence",
            icon="add",
            on_click=lambda: (
                _skill_dialog(
                    user_id,
                    character,
                    lambda: (
                        ui.navigate.to(
                            _character_url(
                                character["id"],
                                "competences",
                            )
                        )
                    ),
                )
            ),
        ).props(
            "outline color=primary"
        )

    skills = list_rpg_skills(
        user_id,
        character["id"],
    )
    editors = []

    with ui.column().classes(
        "w-full gap-3"
    ):
        for skill_row in skills:
            with ui.element("div").classes(
                "jf-rpg-skill-card"
            ):
                with ui.row().classes(
                    "w-full items-start "
                    "justify-between gap-2 flex-wrap"
                ):
                    with ui.column().classes(
                        "gap-0 grow min-w-[180px]"
                    ):
                        name_input = ui.input(
                            label="Compétence",
                            value=skill_row[
                                "skill_name"
                            ],
                        ).props(
                            "maxlength=120"
                        ).classes(
                            "w-full"
                        )

                        indicators = []

                        if skill_row[
                            "trained_only"
                        ]:
                            indicators.append(
                                "Formation requise"
                            )

                        if skill_row[
                            "armor_check_applies"
                        ]:
                            indicators.append(
                                "Pénalité d’armure"
                            )

                        if skill_row[
                            "double_armor_penalty"
                        ]:
                            indicators.append(
                                "Pénalité doublée"
                            )

                        ui.label(
                            (
                                " · ".join(
                                    indicators
                                )
                                if indicators
                                else (
                                    "Utilisation générale"
                                )
                            )
                        ).classes(
                            "text-xs jf-muted"
                        )

                    total_label = ui.label(
                        format_number(
                            skill_total(
                                character,
                                skill_row,
                            )
                        )
                    ).classes(
                        "jf-rpg-skill-total"
                    )

                    if skill_row[
                        "is_custom"
                    ]:
                        def remove_skill(
                            selected=skill_row,
                        ):
                            try:
                                delete_custom_rpg_skill(
                                    user_id,
                                    character["id"],
                                    selected["id"],
                                )
                            except Exception as error:
                                _safe_notify_error(
                                    error,
                                    (
                                        "La compétence n’a pas "
                                        "pu être supprimée."
                                    ),
                                )
                                return

                            ui.notify(
                                "Compétence supprimée.",
                                type="positive",
                            )
                            ui.navigate.to(
                                _character_url(
                                    character["id"],
                                    "competences",
                                )
                            )

                        ui.button(
                            icon="delete",
                            on_click=remove_skill,
                        ).props(
                            "flat round color=negative"
                        ).tooltip(
                            "Supprimer la compétence personnalisée"
                        )

                with ui.element("div").classes(
                    "jf-rpg-grid mt-2"
                ):
                    ability_input = ui.select(
                        ABILITY_LABELS,
                        label="Caractéristique",
                        value=skill_row[
                            "ability_key"
                        ],
                    ).classes(
                        "w-full"
                    )
                    ranks_input = ui.number(
                        label="Rangs",
                        value=float(
                            skill_row[
                                "ranks"
                            ]
                        ),
                        min=0,
                        max=999,
                        step=0.5,
                    ).classes(
                        "w-full"
                    )
                    misc_input = ui.number(
                        label="Divers",
                        value=skill_row[
                            "misc_modifier"
                        ],
                        step=1,
                    ).classes(
                        "w-full"
                    )
                    class_input = ui.checkbox(
                        "Compétence de classe",
                        value=skill_row[
                            "class_skill"
                        ],
                    )
                    trained_input = ui.checkbox(
                        "Formation requise",
                        value=skill_row[
                            "trained_only"
                        ],
                    )
                    armor_input = ui.checkbox(
                        "Pénalité d’armure",
                        value=skill_row[
                            "armor_check_applies"
                        ],
                    )
                    double_input = ui.checkbox(
                        "Pénalité doublée",
                        value=skill_row[
                            "double_armor_penalty"
                        ],
                    )

                def update_total(
                    event=None,
                    *,
                    ability_control=ability_input,
                    ranks_control=ranks_input,
                    misc_control=misc_input,
                    armor_control=armor_input,
                    double_control=double_input,
                    label_control=total_label,
                ):
                    ability_key = (
                        ability_control.value
                        or "int"
                    )
                    total = Decimal(
                        str(
                            ranks_control.value
                            or 0
                        )
                    )
                    total += Decimal(
                        ability_modifier_for_character(
                            character,
                            ability_key,
                        )
                    )
                    total += Decimal(
                        _as_number(
                            misc_control.value
                        )
                    )

                    if armor_control.value:
                        penalty = _as_number(
                            character[
                                "armor_check_penalty"
                            ]
                        )

                        if double_control.value:
                            penalty *= 2

                        total += Decimal(
                            penalty
                        )

                    label_control.set_text(
                        format_number(total)
                    )

                for control in (
                    ability_input,
                    ranks_input,
                    misc_input,
                    armor_input,
                    double_input,
                ):
                    control.on_value_change(
                        update_total
                    )

                editors.append(
                    {
                        "row": skill_row,
                        "name": name_input,
                        "ability": ability_input,
                        "ranks": ranks_input,
                        "misc": misc_input,
                        "class_skill": class_input,
                        "trained": trained_input,
                        "armor": armor_input,
                        "double": double_input,
                    }
                )

    def save_skills():
        rows = [
            {
                "id": editor[
                    "row"
                ]["id"],
                "skill_name": editor[
                    "name"
                ].value,
                "ability_key": editor[
                    "ability"
                ].value,
                "ranks": editor[
                    "ranks"
                ].value,
                "misc_modifier": editor[
                    "misc"
                ].value,
                "class_skill": editor[
                    "class_skill"
                ].value,
                "trained_only": editor[
                    "trained"
                ].value,
                "armor_check_applies": editor[
                    "armor"
                ].value,
                "double_armor_penalty": editor[
                    "double"
                ].value,
            }
            for editor in editors
        ]

        try:
            update_rpg_skills(
                user_id,
                character["id"],
                rows,
            )
        except Exception as error:
            _safe_notify_error(
                error,
                (
                    "Les compétences n’ont pas "
                    "pu être enregistrées."
                ),
            )
            return

        ui.notify(
            "Compétences enregistrées.",
            type="positive",
        )

    with ui.row().classes(
        "jf-rpg-section-actions"
    ):
        ui.button(
            "Enregistrer les compétences",
            icon="save",
            on_click=save_skills,
        ).props(
            "color=primary"
        )


def _attack_dialog(
    user_id,
    character,
    attack=None,
):
    editing = (
        attack is not None
    )

    with ui.dialog() as dialog:
        with ui.card().classes(
            "w-full max-w-2xl p-5"
        ):
            ui.label(
                (
                    "Modifier l’attaque"
                    if editing
                    else "Ajouter une attaque"
                )
            ).classes(
                "text-xl font-bold"
            )

            with ui.element("div").classes(
                "jf-rpg-grid"
            ):
                name_input = ui.input(
                    label="Nom de l’attaque",
                    value=(
                        attack[
                            "attack_name"
                        ]
                        if editing
                        else ""
                    ),
                ).props(
                    "autofocus maxlength=120"
                ).classes(
                    "w-full"
                )
                ability_input = ui.select(
                    ABILITY_LABELS,
                    label="Caractéristique",
                    value=(
                        attack[
                            "ability_key"
                        ]
                        if editing
                        else "str"
                    ),
                ).classes(
                    "w-full"
                )
                magic_input = ui.number(
                    label="Bonus magique",
                    value=(
                        attack[
                            "magic_bonus"
                        ]
                        if editing
                        else 0
                    ),
                    step=1,
                ).classes(
                    "w-full"
                )
                misc_input = ui.number(
                    label="Bonus divers",
                    value=(
                        attack[
                            "misc_bonus"
                        ]
                        if editing
                        else 0
                    ),
                    step=1,
                ).classes(
                    "w-full"
                )
                damage_input = ui.input(
                    label="Dégâts",
                    value=(
                        attack[
                            "damage"
                        ] or ""
                        if editing
                        else ""
                    ),
                    placeholder="Ex. 1d8+3",
                ).props(
                    "maxlength=120"
                ).classes(
                    "w-full"
                )
                critical_input = ui.input(
                    label="Critique",
                    value=(
                        attack[
                            "critical"
                        ] or ""
                        if editing
                        else ""
                    ),
                    placeholder="Ex. 19-20/x2",
                ).props(
                    "maxlength=80"
                ).classes(
                    "w-full"
                )
                range_input = ui.input(
                    label="Portée",
                    value=(
                        attack[
                            "attack_range"
                        ] or ""
                        if editing
                        else ""
                    ),
                ).props(
                    "maxlength=80"
                ).classes(
                    "w-full"
                )
                type_input = ui.input(
                    label="Type",
                    value=(
                        attack[
                            "attack_type"
                        ] or ""
                        if editing
                        else ""
                    ),
                    placeholder="Ex. tranchant",
                ).props(
                    "maxlength=80"
                ).classes(
                    "w-full"
                )
                ammo_current_input = ui.number(
                    label="Munitions actuelles",
                    value=(
                        attack[
                            "ammunition_current"
                        ]
                        if editing
                        else None
                    ),
                    min=0,
                    step=1,
                ).props(
                    "clearable"
                ).classes(
                    "w-full"
                )
                ammo_max_input = ui.number(
                    label="Munitions maximums",
                    value=(
                        attack[
                            "ammunition_max"
                        ]
                        if editing
                        else None
                    ),
                    min=0,
                    step=1,
                ).props(
                    "clearable"
                ).classes(
                    "w-full"
                )

            notes_input = ui.textarea(
                label="Notes",
                value=(
                    attack[
                        "notes"
                    ] or ""
                    if editing
                    else ""
                ),
            ).props(
                "maxlength=1000 autogrow"
            ).classes(
                "w-full"
            )

            total_label = ui.label(
                ""
            ).classes(
                "jf-rpg-stat-value"
            )

            def refresh_total(event=None):
                draft = {
                    "ability_key": (
                        ability_input.value
                    ),
                    "magic_bonus": (
                        magic_input.value
                    ),
                    "misc_bonus": (
                        misc_input.value
                    ),
                }
                total_label.set_text(
                    (
                        "Bonus total : "
                        + format_modifier(
                            attack_total(
                                character,
                                draft,
                            )
                        )
                    )
                )

            for control in (
                ability_input,
                magic_input,
                misc_input,
            ):
                control.on_value_change(
                    refresh_total
                )

            refresh_total()

            def save():
                values = {
                    "attack_name": (
                        name_input.value
                    ),
                    "ability_key": (
                        ability_input.value
                    ),
                    "magic_bonus": (
                        magic_input.value
                    ),
                    "misc_bonus": (
                        misc_input.value
                    ),
                    "damage": (
                        damage_input.value
                    ),
                    "critical": (
                        critical_input.value
                    ),
                    "attack_range": (
                        range_input.value
                    ),
                    "attack_type": (
                        type_input.value
                    ),
                    "notes": notes_input.value,
                    "ammunition_current": (
                        ammo_current_input.value
                    ),
                    "ammunition_max": (
                        ammo_max_input.value
                    ),
                }

                try:
                    if editing:
                        update_rpg_attack(
                            user_id,
                            character["id"],
                            attack["id"],
                            values,
                        )
                    else:
                        create_rpg_attack(
                            user_id,
                            character["id"],
                            values,
                        )
                except Exception as error:
                    _safe_notify_error(
                        error,
                        (
                            "L’attaque n’a pas "
                            "pu être enregistrée."
                        ),
                    )
                    return

                dialog.close()
                ui.notify(
                    (
                        "Attaque modifiée."
                        if editing
                        else "Attaque ajoutée."
                    ),
                    type="positive",
                )
                ui.navigate.to(
                    _character_url(
                        character["id"],
                        "attaques",
                    )
                )

            with ui.row().classes(
                "w-full justify-end gap-2 mt-3"
            ):
                ui.button(
                    "Annuler",
                    on_click=dialog.close,
                ).props(
                    "flat"
                )
                ui.button(
                    "Enregistrer",
                    icon="save",
                    on_click=save,
                ).props(
                    "color=primary"
                )

    dialog.open()


def _attacks_panel(
    user_id,
    character,
):
    with ui.row().classes(
        "w-full items-center justify-between "
        "gap-3 flex-wrap"
    ):
        with ui.column().classes(
            "gap-0"
        ):
            ui.label(
                "Attaques"
            ).classes(
                "text-xl font-bold"
            )
            ui.label(
                "Le bonus total combine le bonus de base, "
                "la caractéristique, la taille, la magie "
                "et les modificateurs divers."
            ).classes(
                "text-sm jf-muted"
            )

        ui.button(
            "Ajouter une attaque",
            icon="add",
            on_click=lambda: (
                _attack_dialog(
                    user_id,
                    character,
                )
            ),
        ).props(
            "color=primary"
        )

    attacks = list_rpg_attacks(
        user_id,
        character["id"],
    )

    if not attacks:
        with ui.card().classes(
            "w-full p-6 items-center text-center"
        ):
            ui.icon(
                "sports_martial_arts"
            ).classes(
                "text-5xl text-gray-400"
            )
            ui.label(
                "Aucune attaque enregistrée"
            ).classes(
                "text-lg font-bold"
            )
            ui.label(
                "Ajoutez une arme, une attaque naturelle "
                "ou une attaque à distance."
            ).classes(
                "text-sm jf-muted"
            )
        return

    with ui.element("div").classes(
        "jf-rpg-grid"
    ):
        for attack in attacks:
            with ui.element("div").classes(
                "jf-rpg-attack-card"
            ):
                with ui.row().classes(
                    "w-full items-start "
                    "justify-between gap-2"
                ):
                    with ui.column().classes(
                        "gap-0 grow min-w-0"
                    ):
                        ui.label(
                            attack[
                                "attack_name"
                            ]
                        ).classes(
                            "font-bold text-lg"
                        )
                        ui.label(
                            (
                                f"Bonus total "
                                f"{format_modifier(attack_total(character, attack))}"
                            )
                        ).classes(
                            "text-primary font-bold"
                        )

                    with ui.row().classes(
                        "gap-0"
                    ):
                        ui.button(
                            icon="edit",
                            on_click=(
                                lambda selected=attack:
                                _attack_dialog(
                                    user_id,
                                    character,
                                    selected,
                                )
                            ),
                        ).props(
                            "flat round color=primary"
                        ).tooltip(
                            "Modifier"
                        )

                        def remove_attack(
                            selected=attack,
                        ):
                            try:
                                delete_rpg_attack(
                                    user_id,
                                    character["id"],
                                    selected["id"],
                                )
                            except Exception as error:
                                _safe_notify_error(
                                    error,
                                    (
                                        "L’attaque n’a pas "
                                        "pu être supprimée."
                                    ),
                                )
                                return

                            ui.notify(
                                "Attaque supprimée.",
                                type="positive",
                            )
                            ui.navigate.to(
                                _character_url(
                                    character["id"],
                                    "attaques",
                                )
                            )

                        ui.button(
                            icon="delete",
                            on_click=remove_attack,
                        ).props(
                            "flat round color=negative"
                        ).tooltip(
                            "Supprimer"
                        )

                with ui.element("div").classes(
                    "jf-rpg-grid mt-2"
                ):
                    for label, value in (
                        (
                            "Caractéristique",
                            ABILITY_LABELS[
                                attack[
                                    "ability_key"
                                ]
                            ],
                        ),
                        (
                            "Dégâts",
                            attack[
                                "damage"
                            ] or "—",
                        ),
                        (
                            "Critique",
                            attack[
                                "critical"
                            ] or "—",
                        ),
                        (
                            "Portée",
                            attack[
                                "attack_range"
                            ] or "—",
                        ),
                        (
                            "Type",
                            attack[
                                "attack_type"
                            ] or "—",
                        ),
                    ):
                        with ui.column().classes(
                            "gap-0"
                        ):
                            ui.label(
                                label
                            ).classes(
                                "text-xs jf-muted"
                            )
                            ui.label(
                                str(value)
                            ).classes(
                                "text-sm font-bold"
                            )

                if (
                    attack[
                        "ammunition_current"
                    ] is not None
                    or attack[
                        "ammunition_max"
                    ] is not None
                ):
                    ui.label(
                        (
                            "Munitions : "
                            f"{attack['ammunition_current'] or 0}"
                            " / "
                            f"{attack['ammunition_max'] or 0}"
                        )
                    ).classes(
                        "text-sm mt-2"
                    )

                if attack["notes"]:
                    ui.separator().classes(
                        "my-2"
                    )
                    ui.label(
                        attack["notes"]
                    ).classes(
                        "text-sm jf-muted"
                    )


def rpg_character_panel(
    current_user,
    *,
    selected_character_id=None,
    initial_section="identite",
):
    user_id = current_user["id"]
    characters = list_rpg_characters(
        user_id
    )

    with ui.row().classes(
        "w-full items-start justify-between "
        "gap-3 flex-wrap"
    ):
        with ui.column().classes(
            "gap-0"
        ):
            ui.label(
                "Personnages JDR"
            ).classes(
                "text-2xl font-bold"
            )
            ui.label(
                "Feuille interactive inspirée de "
                "D&D 3.5 et de Ravenloft."
            ).classes(
                "text-sm jf-muted"
            )

        ui.icon(
            "casino"
        ).classes(
            "text-4xl text-primary"
        )

    with ui.element("div").classes(
        "jf-rpg-private"
    ):
        with ui.row().classes(
            "items-start gap-2 flex-nowrap"
        ):
            ui.icon(
                "lock"
            ).classes(
                "text-xl shrink-0"
            )
            ui.label(
                "Chaque personnage est privé à son propriétaire. "
                "Le partage entre campagnes et joueurs sera ajouté "
                "dans une phase ultérieure avec invitation et consentement."
            ).classes(
                "text-sm"
            )

    if not characters:
        with ui.card().classes(
            "w-full p-7 items-center text-center"
        ):
            ui.icon(
                "person_add"
            ).classes(
                "text-6xl text-gray-400"
            )
            ui.label(
                "Créez votre premier personnage"
            ).classes(
                "text-xl font-bold"
            )
            ui.label(
                "La phase 1 comprend l’identité, les caractéristiques, "
                "le combat, les sauvegardes, les compétences et les attaques."
            ).classes(
                "text-sm jf-muted max-w-xl"
            )
            ui.button(
                "Créer un personnage",
                icon="person_add",
                on_click=lambda: (
                    _create_character_dialog(
                        user_id,
                        current_user[
                            "display_name"
                        ],
                    )
                ),
            ).props(
                "color=primary"
            )
        return

    character_ids = {
        int(
            character["id"]
        )
        for character in characters
    }

    try:
        requested_id = int(
            selected_character_id
        )
    except (
        TypeError,
        ValueError,
    ):
        requested_id = None

    current_id = (
        requested_id
        if requested_id
        in character_ids
        else int(
            characters[0]["id"]
        )
    )

    character = get_rpg_character(
        user_id,
        current_id,
    )

    with ui.card().classes(
        "w-full p-4"
    ):
        with ui.row().classes(
            "w-full items-end gap-3 flex-wrap"
        ):
            character_select = ui.select(
                {
                    int(item["id"]): (
                        item[
                            "character_name"
                        ]
                    )
                    for item in characters
                },
                value=current_id,
                label="Personnage actif",
            ).classes(
                "grow min-w-[220px]"
            )

            character_select.on_value_change(
                lambda event: ui.navigate.to(
                    _character_url(
                        event.value
                    )
                )
            )

            ui.button(
                "Nouveau",
                icon="person_add",
                on_click=lambda: (
                    _create_character_dialog(
                        user_id,
                        current_user[
                            "display_name"
                        ],
                    )
                ),
            ).props(
                "outline color=primary"
            )

            ui.button(
                icon="delete",
                on_click=lambda: (
                    _delete_character_dialog(
                        user_id,
                        character,
                    )
                ),
            ).props(
                "flat round color=negative"
            ).tooltip(
                "Supprimer le personnage actif"
            )

    with ui.element("div").classes(
        "jf-rpg-character-banner"
    ):
        with ui.row().classes(
            "w-full items-start "
            "justify-between gap-4 flex-wrap"
        ):
            with ui.column().classes(
                "gap-0 grow min-w-0"
            ):
                ui.label(
                    character[
                        "character_name"
                    ]
                ).classes(
                    "text-2xl font-bold"
                )
                ui.label(
                    " · ".join(
                        value
                        for value in (
                            character[
                                "race"
                            ],
                            (
                                (
                                    f"{character['class_name']} "
                                    f"niveau {character['character_level']}"
                                )
                                if character[
                                    "class_name"
                                ]
                                else (
                                    f"Niveau "
                                    f"{character['character_level']}"
                                )
                            ),
                            character[
                                "campaign"
                            ],
                        )
                        if value
                    )
                ).classes(
                    "text-sm opacity-90"
                )

            with ui.row().classes(
                "gap-4 flex-wrap"
            ):
                with ui.column().classes(
                    "gap-0"
                ):
                    ui.label(
                        "PV"
                    ).classes(
                        "text-xs opacity-80"
                    )
                    ui.label(
                        (
                            f"{character['current_hp']}"
                            f"/{character['max_hp']}"
                        )
                    ).classes(
                        "text-xl font-bold"
                    )
                with ui.column().classes(
                    "gap-0"
                ):
                    ui.label(
                        "CA"
                    ).classes(
                        "text-xs opacity-80"
                    )
                    ui.label(
                        str(
                            armor_class_total(
                                character
                            )
                        )
                    ).classes(
                        "text-xl font-bold"
                    )
                with ui.column().classes(
                    "gap-0"
                ):
                    ui.label(
                        "Initiative"
                    ).classes(
                        "text-xs opacity-80"
                    )
                    ui.label(
                        format_modifier(
                            initiative_total(
                                character
                            )
                        )
                    ).classes(
                        "text-xl font-bold"
                    )

    with ui.tabs().classes(
        "w-full"
    ) as tabs:
        identity_tab = ui.tab(
            "Identité",
            icon="badge",
        )
        combat_tab = ui.tab(
            "Combat",
            icon="shield",
        )
        saves_tab = ui.tab(
            "Sauvegardes",
            icon="security",
        )
        skills_tab = ui.tab(
            "Compétences",
            icon="psychology",
        )
        attacks_tab = ui.tab(
            "Attaques",
            icon="sports_martial_arts",
        )

    normalized_section = str(
        initial_section
        or "identite"
    ).strip().lower()

    initial_tab = {
        "identite": identity_tab,
        "identity": identity_tab,
        "combat": combat_tab,
        "caracteristiques": combat_tab,
        "sauvegardes": saves_tab,
        "saves": saves_tab,
        "competences": skills_tab,
        "skills": skills_tab,
        "attaques": attacks_tab,
        "attacks": attacks_tab,
    }.get(
        normalized_section,
        identity_tab,
    )

    with ui.tab_panels(
        tabs,
        value=initial_tab,
    ).classes(
        "w-full bg-transparent"
    ):
        with ui.tab_panel(
            identity_tab
        ).classes(
            "px-0"
        ):
            _identity_panel(
                user_id,
                character,
            )

        with ui.tab_panel(
            combat_tab
        ).classes(
            "px-0"
        ):
            _combat_panel(
                user_id,
                character,
            )

        with ui.tab_panel(
            saves_tab
        ).classes(
            "px-0"
        ):
            _saves_panel(
                user_id,
                character,
            )

        with ui.tab_panel(
            skills_tab
        ).classes(
            "px-0"
        ):
            _skills_panel(
                user_id,
                character,
            )

        with ui.tab_panel(
            attacks_tab
        ).classes(
            "px-0"
        ):
            _attacks_panel(
                user_id,
                character,
            )

    with ui.element("div").classes(
        "jf-rpg-help"
    ):
        ui.label(
            "Phase 1"
        ).classes(
            "font-bold"
        )
        ui.label(
            "L’équipement, les dons, les capacités spéciales, "
            "les langues, les sorts, le PDF et les campagnes "
            "seront ajoutés dans les phases suivantes."
        ).classes(
            "text-sm"
        )
