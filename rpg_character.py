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
    armor_class_breakdown,
    armor_class_total,
    attack_breakdown,
    attack_total,
    cmb_breakdown,
    cmb_total,
    cmd_breakdown,
    cmd_total,
    flat_footed_armor_class,
    format_modifier,
    format_number,
    initiative_breakdown,
    initiative_total,
    save_breakdown,
    save_total,
    skill_breakdown,
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

.jf-rpg-skill-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    width: 100%;
}

.jf-rpg-skill-badge {
    display: inline-flex;
    align-items: center;
    width: fit-content;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--jf-navy);
    background: var(--jf-blue-soft);
}

.jf-rpg-skill-badge-owned {
    color: #156c47;
    background: rgba(33, 145, 92, 0.13);
}

.jf-rpg-skill-badge-class {
    color: #65420e;
    background: rgba(189, 149, 85, 0.17);
}

.jf-rpg-skill-filter-summary {
    width: 100%;
    padding: 0.7rem 0.85rem;
    border-radius: 12px;
    background: rgba(34, 70, 122, 0.07);
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
    min-width: 3rem;
    padding: 0.2rem 0.58rem;
    border-radius: 999px;
    text-align: center;
    color: white;
    background: var(--jf-navy);
    font-size: 0.95rem;
    font-weight: 800;
}

.jf-rpg-skill-card {
    padding: 0.58rem 0.7rem;
    border-radius: 13px;
}

.jf-rpg-skill-header {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    width: 100%;
    min-width: 0;
}

.jf-rpg-skill-name {
    min-width: 0;
    overflow-wrap: anywhere;
    color: var(--jf-navy);
    font-size: 0.98rem;
    font-weight: 800;
}

.body--dark .jf-rpg-skill-name {
    color: #dceaf6;
}

.jf-rpg-skill-edit-button {
    flex: 0 0 auto;
}

.jf-rpg-skill-badges-compact {
    display: flex;
    flex: 1 1 auto;
    flex-wrap: wrap;
    gap: 0.25rem;
    min-width: 0;
}

.jf-rpg-skill-badges-compact .jf-rpg-skill-badge {
    padding: 0.12rem 0.42rem;
    font-size: 0.66rem;
}

.jf-rpg-skill-controls {
    display: grid;
    grid-template-columns:
        minmax(6.5rem, 8.5rem)
        minmax(4.6rem, 5.7rem)
        minmax(4.6rem, 5.7rem)
        max-content
        max-content
        max-content
        max-content;
    align-items: center;
    gap: 0.25rem 0.55rem;
    width: 100%;
    margin-top: 0.35rem;
}

.jf-rpg-skill-control .q-field__control {
    min-height: 36px;
    height: 36px;
}

.jf-rpg-skill-control .q-field__native,
.jf-rpg-skill-control .q-field__input,
.jf-rpg-skill-control .q-field__label {
    font-size: 0.78rem;
}

.jf-rpg-skill-check {
    margin: 0;
    white-space: nowrap;
}

.jf-rpg-skill-check .q-checkbox__label {
    font-size: 0.74rem;
}

.jf-rpg-skill-check .q-checkbox__inner {
    font-size: 32px;
}

.jf-rpg-skill-calculation {
    width: 100%;
    margin-top: 0.3rem;
    padding: 0.28rem 0.5rem;
    border-radius: 9px;
    color: var(--jf-muted);
    background: rgba(34, 70, 122, 0.055);
    font-size: 0.72rem;
}

.jf-rpg-skill-warning {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.45rem;
    width: 100%;
    margin-top: 0.28rem;
    padding: 0.28rem 0.5rem;
    border-radius: 9px;
    color: #75500f;
    background: rgba(189, 149, 85, 0.16);
    font-size: 0.72rem;
}

@media (max-width: 980px) {
    .jf-rpg-skill-controls {
        grid-template-columns:
            minmax(6.5rem, 1.2fr)
            minmax(4.6rem, 0.7fr)
            minmax(4.6rem, 0.7fr)
            repeat(2, max-content);
    }
}

@media (max-width: 680px) {
    .jf-rpg-skill-header {
        align-items: flex-start;
        flex-wrap: wrap;
    }

    .jf-rpg-skill-badges-compact {
        flex-basis: 100%;
    }

    .jf-rpg-skill-controls {
        grid-template-columns:
            minmax(6rem, 1fr)
            minmax(4.4rem, 0.65fr)
            minmax(4.4rem, 0.65fr)
            repeat(2, max-content);
    }

    .jf-rpg-skill-check .q-checkbox__label {
        font-size: 0.7rem;
    }
}

@media (max-width: 470px) {
    .jf-rpg-skill-controls {
        grid-template-columns:
            minmax(5.8rem, 1fr)
            minmax(4.2rem, 0.75fr)
            minmax(4.2rem, 0.75fr);
    }
}

.jf-rpg-ability-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 0.5rem;
}

.jf-rpg-ability-card {
    padding: 0.58rem 0.65rem;
    border-radius: 13px;
}

.jf-rpg-ability-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.35rem;
    width: 100%;
}

.jf-rpg-ability-title {
    min-width: 0;
    font-size: 0.82rem;
    font-weight: 800;
}

.jf-rpg-ability-modifier {
    flex: 0 0 auto;
    min-width: 2.45rem;
    padding: 0.12rem 0.42rem;
    border-radius: 999px;
    text-align: center;
    color: white;
    background: var(--jf-navy);
    font-size: 0.92rem;
    font-weight: 800;
}

.jf-rpg-ability-fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.35rem;
    width: 100%;
    margin-top: 0.35rem;
}

.jf-rpg-compact-field .q-field__control {
    min-height: 38px;
    height: 38px;
}

.jf-rpg-compact-field .q-field__native,
.jf-rpg-compact-field .q-field__input,
.jf-rpg-compact-field .q-field__label {
    font-size: 0.78rem;
}

.jf-rpg-combat-grid {
    display: grid;
    grid-template-columns: repeat(8, minmax(7.25rem, 1fr));
    gap: 0.45rem 0.55rem;
    width: 100%;
}

.jf-rpg-result-grid {
    display: grid;
    grid-template-columns: repeat(6, minmax(6.5rem, 1fr));
    gap: 0.55rem;
    width: 100%;
}

.jf-rpg-result-item {
    padding: 0.45rem 0.55rem;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.52);
}

.body--dark .jf-rpg-result-item {
    background: rgba(0, 0, 0, 0.12);
}

.jf-rpg-rules-formula {
    width: 100%;
    margin-top: 0.3rem;
    padding: 0.55rem 0.65rem;
    border-radius: 10px;
    background: var(--jf-blue-soft);
    font-size: 0.82rem;
    font-weight: 700;
}

.jf-rpg-rules-example {
    width: 100%;
    margin-top: 0.35rem;
    padding: 0.55rem 0.65rem;
    border-left: 4px solid var(--jf-gold);
    border-radius: 9px;
    background: rgba(189, 149, 85, 0.09);
    font-size: 0.8rem;
}

@media (max-width: 1180px) {
    .jf-rpg-ability-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .jf-rpg-combat-grid {
        grid-template-columns: repeat(5, minmax(7rem, 1fr));
    }

    .jf-rpg-result-grid {
        grid-template-columns: repeat(3, minmax(6.5rem, 1fr));
    }
}

@media (max-width: 760px) {
    .jf-rpg-ability-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .jf-rpg-combat-grid {
        grid-template-columns: repeat(3, minmax(6.5rem, 1fr));
    }
}

@media (max-width: 480px) {
    .jf-rpg-ability-grid {
        grid-template-columns: 1fr;
    }

    .jf-rpg-combat-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .jf-rpg-result-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
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



def _signed_rule_part(
    label,
    value,
) -> str:
    return f"{label} {format_modifier(value)}"


def _calculation_rules_dialog(
    user_id,
    character,
):
    """Ouvre une aide complète avec formules et exemples actuels."""

    try:
        saves = list_rpg_saves(
            user_id,
            character["id"],
        )
    except Exception:
        saves = []

    try:
        skills = list_rpg_skills(
            user_id,
            character["id"],
        )
    except Exception:
        skills = []

    try:
        attacks = list_rpg_attacks(
            user_id,
            character["id"],
        )
    except Exception:
        attacks = []

    ac = armor_class_breakdown(character)
    initiative = initiative_breakdown(character)
    cmb = cmb_breakdown(character)
    cmd = cmd_breakdown(character)

    def formula_block(
        title,
        formula,
        example,
        note=None,
    ):
        ui.label(title).classes(
            "font-bold mt-2"
        )
        ui.label(formula).classes(
            "jf-rpg-rules-formula"
        )
        ui.label(
            f"Avec ce personnage : {example}"
        ).classes(
            "jf-rpg-rules-example"
        )
        if note:
            ui.label(note).classes(
                "text-xs jf-muted mt-1"
            )

    with ui.dialog() as dialog:
        with ui.card().classes(
            "w-full max-w-5xl p-0 max-h-[90vh] overflow-auto"
        ):
            with ui.row().classes(
                "w-full items-center justify-between gap-3 p-4 pb-2"
            ):
                with ui.column().classes("gap-0"):
                    ui.label(
                        "Règles de calcul"
                    ).classes(
                        "text-2xl font-bold"
                    )
                    ui.label(
                        "Formules Pathfinder et Ravenloft, avec des exemples calculés à partir du personnage."
                    ).classes(
                        "text-sm jf-muted"
                    )
                ui.button(
                    icon="close",
                    on_click=dialog.close,
                ).props(
                    "flat round"
                )

            with ui.column().classes(
                "w-full gap-2 px-4 pb-4"
            ):
                with ui.expansion(
                    "Caractéristiques",
                    icon="tune",
                    value=True,
                ).props(
                    "expand-separator"
                ).classes("w-full"):
                    ui.label(
                        "Modificateur = arrondi inférieur de ((score effectif − 10) ÷ 2). Le score temporaire remplace le score normal lorsqu’il est rempli."
                    ).classes(
                        "jf-rpg-rules-formula"
                    )
                    ability_examples = []
                    for ability_key in ABILITY_LABELS:
                        score = character.get(
                            f"{ability_key}_temp_score"
                        ) or character.get(
                            f"{ability_key}_score"
                        )
                        ability_examples.append(
                            f"{ABILITY_LABELS[ability_key]} {score} → {format_modifier(ability_modifier_for_character(character, ability_key))}"
                        )
                    ui.label(
                        "Avec ce personnage : " + "  ·  ".join(ability_examples)
                    ).classes(
                        "jf-rpg-rules-example"
                    )

                with ui.expansion(
                    "Classe d’armure et initiative",
                    icon="shield",
                    value=True,
                ).props(
                    "expand-separator"
                ).classes("w-full"):
                    formula_block(
                        "CA totale",
                        "CA = 10 + armure + bouclier + DEX + taille + armure naturelle + déviation + divers",
                        " + ".join([
                            "10",
                            _signed_rule_part("armure", ac["armor_bonus"]),
                            _signed_rule_part("bouclier", ac["shield_bonus"]),
                            _signed_rule_part("DEX", ac["dex_modifier"]),
                            _signed_rule_part("taille", ac["size_modifier"]),
                            _signed_rule_part("naturelle", ac["natural_armor_bonus"]),
                            _signed_rule_part("déviation", ac["deflection_bonus"]),
                            _signed_rule_part("divers", ac["misc_modifier"]),
                        ]) + f" = {ac['total']}",
                    )
                    formula_block(
                        "CA de contact",
                        "CA de contact = 10 + DEX + taille + déviation + divers",
                        " + ".join([
                            "10",
                            _signed_rule_part("DEX", ac["dex_modifier"]),
                            _signed_rule_part("taille", ac["size_modifier"]),
                            _signed_rule_part("déviation", ac["deflection_bonus"]),
                            _signed_rule_part("divers", ac["misc_modifier"]),
                        ]) + f" = {ac['touch']}",
                        "L’armure, le bouclier et l’armure naturelle ne protègent normalement pas contre une attaque de contact.",
                    )
                    formula_block(
                        "CA pris au dépourvu",
                        "CA pris au dépourvu = 10 + armure + bouclier + DEX négative seulement + taille + armure naturelle + déviation + divers",
                        " + ".join([
                            "10",
                            _signed_rule_part("armure", ac["armor_bonus"]),
                            _signed_rule_part("bouclier", ac["shield_bonus"]),
                            _signed_rule_part("DEX retenue", ac["flat_footed_dex_modifier"]),
                            _signed_rule_part("taille", ac["size_modifier"]),
                            _signed_rule_part("naturelle", ac["natural_armor_bonus"]),
                            _signed_rule_part("déviation", ac["deflection_bonus"]),
                            _signed_rule_part("divers", ac["misc_modifier"]),
                        ]) + f" = {ac['flat_footed']}",
                        "Un bonus positif de DEX est retiré; une pénalité de DEX demeure.",
                    )
                    formula_block(
                        "Initiative",
                        "Initiative = modificateur de DEX + divers",
                        " + ".join([
                            _signed_rule_part("DEX", initiative["dex_modifier"]),
                            _signed_rule_part("divers", initiative["misc_modifier"]),
                        ]) + f" = {format_modifier(initiative['total'])}",
                    )

                with ui.expansion(
                    "BMO / CMB et DMD / CMD",
                    icon="sports_martial_arts",
                    value=True,
                ).props(
                    "expand-separator"
                ).classes("w-full"):
                    cmb_ability = ABILITY_LABELS.get(
                        cmb["ability_key"],
                        cmb["ability_key"].upper(),
                    )
                    formula_block(
                        "BMO / CMB",
                        "BMO/CMB = BBA + modificateur de Force (ou Dextérité pour une créature Très petite ou plus petite) + modificateur spécial de taille + divers",
                        " + ".join([
                            _signed_rule_part("BBA", cmb["base_attack_bonus"]),
                            _signed_rule_part(cmb_ability, cmb["ability_modifier"]),
                            _signed_rule_part("taille spéciale", cmb["size_modifier"]),
                            _signed_rule_part("divers", cmb["misc_modifier"]),
                        ]) + f" = {format_modifier(cmb['total'])}",
                    )
                    formula_block(
                        "DMD / CMD",
                        "DMD/CMD = 10 + BBA + FOR + DEX + modificateur spécial de taille + déviation + autres bonus applicables + divers",
                        " + ".join([
                            "10",
                            _signed_rule_part("BBA", cmd["base_attack_bonus"]),
                            _signed_rule_part("FOR", cmd["strength_modifier"]),
                            _signed_rule_part("DEX", cmd["dexterity_modifier"]),
                            _signed_rule_part("taille spéciale", cmd["size_modifier"]),
                            _signed_rule_part("déviation", cmd["deflection_bonus"]),
                            _signed_rule_part("pénalités CA", cmd["automatic_ac_penalty"]),
                            _signed_rule_part("divers", cmd["misc_modifier"]),
                        ]) + f" = {cmd['total']}",
                        "Les bonus d’esquive et les autres bonus applicables doivent être inscrits dans Divers – DMD/CMD. Les pénalités négatives du champ Divers CA sont appliquées automatiquement.",
                    )

                with ui.expansion(
                    "Jets de sauvegarde",
                    icon="health_and_safety",
                ).props(
                    "expand-separator"
                ).classes("w-full"):
                    ui.label(
                        "Total = base + modificateur de caractéristique + magie + divers + temporaire"
                    ).classes(
                        "jf-rpg-rules-formula"
                    )
                    if saves:
                        for save_row in saves:
                            breakdown = save_breakdown(
                                character,
                                save_row,
                            )
                            definition = SAVE_DEFINITIONS[
                                save_row["save_key"]
                            ]
                            ability_label = ABILITY_LABELS[
                                breakdown["ability_key"]
                            ]
                            example = " + ".join([
                                _signed_rule_part("base", breakdown["base_save"]),
                                _signed_rule_part(ability_label, breakdown["ability_modifier"]),
                                _signed_rule_part("magie", breakdown["magic_modifier"]),
                                _signed_rule_part("divers", breakdown["misc_modifier"]),
                                _signed_rule_part("temp.", breakdown["temporary_modifier"]),
                            ]) + f" = {format_modifier(breakdown['total'])}"
                            formula_block(
                                definition["label"],
                                f"{definition['label']} = base + {ability_label} + magie + divers + temporaire",
                                example,
                                "Peur, Horreur et Folie utilisent actuellement la Sagesse dans cette feuille Ravenloft.",
                            )
                    else:
                        ui.label(
                            "Aucun jet de sauvegarde n’est disponible pour construire un exemple."
                        ).classes("text-sm jf-muted")

                with ui.expansion(
                    "Compétences",
                    icon="psychology",
                ).props(
                    "expand-separator"
                ).classes("w-full"):
                    ui.label(
                        "Total = caractéristique + rangs + bonus de compétence de classe (+3 si au moins 1 rang) + divers + pénalité d’armure"
                    ).classes(
                        "jf-rpg-rules-formula"
                    )
                    sample_skill = next(
                        (
                            row for row in skills
                            if row.get("skill_key") == "handle_animal"
                            and Decimal(str(row.get("ranks") or 0)) > 0
                        ),
                        None,
                    ) or next(
                        (
                            row for row in skills
                            if Decimal(str(row.get("ranks") or 0)) > 0
                        ),
                        None,
                    )
                    if sample_skill:
                        breakdown = skill_breakdown(
                            character,
                            sample_skill,
                        )
                        ability_label = ABILITY_LABELS[
                            breakdown["ability_key"]
                        ]
                        example = " + ".join([
                            _signed_rule_part(ability_label, breakdown["ability_modifier"]),
                            _signed_rule_part("rangs", breakdown["ranks"]),
                            _signed_rule_part("classe", breakdown["class_bonus"]),
                            _signed_rule_part("divers", breakdown["misc_modifier"]),
                            _signed_rule_part("armure", breakdown["armor_penalty"]),
                        ]) + f" = {format_modifier(breakdown['total'])}"
                        formula_block(
                            _skill_display_name(
                                sample_skill.get("skill_name"),
                                sample_skill.get("english_name"),
                            ),
                            "Caractéristique + rangs + classe + divers + armure",
                            example,
                            "Le bonus de classe +3 est automatique et ne doit pas être recopié dans Divers.",
                        )
                    else:
                        ui.label(
                            "Ajoutez au moins 1 rang dans une compétence pour obtenir un exemple personnalisé."
                        ).classes("text-sm jf-muted")

                with ui.expansion(
                    "Attaques",
                    icon="gps_fixed",
                ).props(
                    "expand-separator"
                ).classes("w-full"):
                    ui.label(
                        "Bonus d’attaque = BBA + caractéristique + modificateur de taille à la CA + magie + divers"
                    ).classes(
                        "jf-rpg-rules-formula"
                    )
                    if attacks:
                        attack = attacks[0]
                        breakdown = attack_breakdown(
                            character,
                            attack,
                        )
                        ability_label = ABILITY_LABELS[
                            breakdown["ability_key"]
                        ]
                        example = " + ".join([
                            _signed_rule_part("BBA", breakdown["base_attack_bonus"]),
                            _signed_rule_part(ability_label, breakdown["ability_modifier"]),
                            _signed_rule_part("taille", breakdown["size_modifier"]),
                            _signed_rule_part("magie", breakdown["magic_bonus"]),
                            _signed_rule_part("divers", breakdown["misc_bonus"]),
                        ]) + f" = {format_modifier(breakdown['total'])}"
                        formula_block(
                            attack.get("attack_name") or "Première attaque",
                            "BBA + caractéristique + taille + magie + divers",
                            example,
                        )
                    else:
                        ui.label(
                            "Ajoutez une attaque pour obtenir un exemple personnalisé."
                        ).classes("text-sm jf-muted")

                with ui.row().classes(
                    "w-full justify-end mt-2"
                ):
                    ui.button(
                        "Fermer",
                        icon="close",
                        on_click=dialog.close,
                    ).props("outline")

    dialog.open()


def _combat_panel(
    user_id,
    character,
):
    with ui.card().classes(
        "w-full p-4"
    ):
        ui.label(
            "Caractéristiques"
        ).classes(
            "text-xl font-bold"
        )
        ui.label(
            "Le score temporaire remplace le score normal pour les calculs. Les six caractéristiques tiennent sur une seule ligne sur grand écran."
        ).classes(
            "text-sm jf-muted"
        )

        ability_inputs = {}

        with ui.element("div").classes(
            "jf-rpg-ability-grid mt-2"
        ):
            for ability_key in ABILITY_LABELS:
                with ui.element("div").classes(
                    "jf-rpg-ability-card"
                ):
                    with ui.element("div").classes(
                        "jf-rpg-ability-header"
                    ):
                        ui.label(
                            f"{ABILITY_LABELS[ability_key]} — {ABILITY_LONG_LABELS[ability_key]}"
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
            ).classes("jf-rpg-compact-field")
            current_hp_input = ui.number(
                label="PV actuels",
                value=character["current_hp"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field")
            nonlethal_input = ui.number(
                label="Dégâts non létaux",
                value=character["nonlethal_damage"],
                min=0,
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field")
            speed_input = ui.input(
                label="Vitesse",
                value=character["speed"] or "",
                placeholder="Ex. 30 ft",
            ).props(
                "dense outlined maxlength=80"
            ).classes("jf-rpg-compact-field")
            dr_input = ui.input(
                label="Réduction dégâts",
                value=character["damage_reduction"] or "",
                placeholder="Ex. 5/argent",
            ).props(
                "dense outlined maxlength=80"
            ).classes("jf-rpg-compact-field").tooltip(
                "Réduction des dégâts"
            )
            sr_input = ui.number(
                label="Résistance magie",
                value=character["spell_resistance"],
                min=0,
                step=1,
            ).props(
                "dense outlined clearable inputmode=numeric"
            ).classes("jf-rpg-compact-field").tooltip(
                "Résistance à la magie"
            )
            bab_input = ui.number(
                label="BBA",
                value=character["base_attack_bonus"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field").tooltip(
                "Bonus de base à l’attaque"
            )
            armor_input = ui.number(
                label="Armure",
                value=character["armor_bonus"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field").tooltip(
                "Bonus d’armure"
            )
            shield_input = ui.number(
                label="Bouclier",
                value=character["shield_bonus"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field").tooltip(
                "Bonus de bouclier"
            )
            natural_input = ui.number(
                label="Armure naturelle",
                value=character["natural_armor_bonus"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field")
            deflection_input = ui.number(
                label="Déviation",
                value=character["deflection_bonus"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field").tooltip(
                "Bonus de déviation"
            )
            misc_ac_input = ui.number(
                label="Divers CA",
                value=character["misc_ac_modifier"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field")
            armor_penalty_input = ui.number(
                label="Pénalité armure",
                value=character["armor_check_penalty"],
                max=0,
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field")
            initiative_misc_input = ui.number(
                label="Divers initiative",
                value=character["initiative_misc_modifier"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field")
            cmb_misc_input = ui.number(
                label="Divers BMO/CMB",
                value=character["cmb_misc_modifier"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field")
            cmd_misc_input = ui.number(
                label="Divers DMD/CMD",
                value=character["cmd_misc_modifier"],
                step=1,
            ).props(
                "dense outlined inputmode=numeric"
            ).classes("jf-rpg-compact-field")

        with ui.element("div").classes(
            "jf-rpg-help mt-3"
        ):
            ui.markdown(
                """
**BMO / CMB** = BBA + modificateur de Force *(ou Dextérité pour une créature Très petite ou plus petite)* + modificateur spécial de taille + divers.

**DMD / CMD** = 10 + BBA + modificateur de Force + modificateur de Dextérité + modificateur spécial de taille + bonus de déviation + autres bonus applicables + divers.

Les bonus d’esquive et les autres bonus applicables doivent être inscrits dans **Divers – DMD/CMD**. Les pénalités négatives inscrites dans **Divers CA** sont appliquées automatiquement au DMD/CMD.
                """
            ).classes("text-sm")

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
            return draft

        @ui.refreshable
        def render_preview():
            draft = current_draft()

            with ui.element("div").classes(
                "jf-rpg-summary mt-3"
            ):
                with ui.element("div").classes(
                    "jf-rpg-result-grid"
                ):
                    for label, value in (
                        ("CA totale", armor_class_total(draft)),
                        ("CA contact", touch_armor_class(draft)),
                        ("Pris au dépourvu", flat_footed_armor_class(draft)),
                        ("Initiative", format_modifier(initiative_total(draft))),
                        ("BMO / CMB", format_modifier(cmb_total(draft))),
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
                _safe_notify_error(
                    error,
                    "Les caractéristiques n’ont pas pu être enregistrées.",
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

        def open_rules():
            _calculation_rules_dialog(
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
            "jf-rpg-section-actions gap-2 flex-wrap"
        ):
            ui.button(
                "Règles de calcul",
                icon="menu_book",
                on_click=lambda: _calculation_rules_dialog(
                    user_id,
                    character,
                ),
            ).props(
                "outline color=primary"
            )
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
                label="Nom français",
            ).props(
                "autofocus maxlength=120"
            ).classes(
                "w-full"
            )
            english_name_input = ui.input(
                label="Nom anglais (facultatif)",
                placeholder=(
                    "Ex. Knowledge (local)"
                ),
            ).props(
                "maxlength=120"
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
                        english_name=(
                            english_name_input.value
                        ),
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



def _skill_display_name(
    french_name,
    english_name,
) -> str:
    french = str(
        french_name
        or ""
    ).strip()
    english = str(
        english_name
        or ""
    ).strip()

    if french and english:
        return (
            f"{french} — {english}"
        )

    return french or english or "Compétence sans nom"


def _skill_breakdown_text(
    breakdown,
) -> str:
    ability_label = ABILITY_LABELS.get(
        breakdown[
            "ability_key"
        ],
        str(
            breakdown[
                "ability_key"
            ]
        ).upper(),
    )

    parts = [
        (
            f"{ability_label} "
            f"{format_modifier(breakdown['ability_modifier'])}"
        ),
        (
            "rangs "
            f"{format_modifier(breakdown['ranks'])}"
        ),
        (
            "classe "
            f"{format_modifier(breakdown['class_bonus'])}"
        ),
        (
            "divers "
            f"{format_modifier(breakdown['misc_modifier'])}"
        ),
    ]

    if (
        breakdown[
            "armor_penalty"
        ]
        != 0
    ):
        parts.append(
            (
                "armure "
                f"{format_modifier(breakdown['armor_penalty'])}"
            )
        )

    return (
        " + ".join(
            parts
        )
        + " = total "
        + format_modifier(
            breakdown[
                "total"
            ]
        )
    )


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
                "Compétences Pathfinder"
            ).classes(
                "text-xl font-bold"
            )
            ui.label(
                "Les compétences possédées ont au moins 1 rang. "
                "Le bonus de +3 d’une compétence de classe est "
                "ajouté automatiquement."
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

    initial_owned_count = sum(
        1
        for skill_row in skills
        if Decimal(
            str(
                skill_row[
                    "ranks"
                ]
                or 0
            )
        ) > 0
    )

    default_filter = (
        "owned"
        if initial_owned_count > 0
        else "all"
    )

    with ui.card().classes(
        "w-full p-4"
    ):
        with ui.row().classes(
            "w-full items-end gap-3 flex-wrap"
        ):
            filter_toggle = ui.toggle(
                {
                    "owned": "Mes compétences",
                    "class": "Compétences de classe",
                    "unranked": "Sans rang",
                    "all": "Toutes",
                },
                value=default_filter,
            ).props(
                "spread no-caps"
            ).classes(
                "grow min-w-[260px]"
            )

            search_input = ui.input(
                label="Rechercher",
                placeholder=(
                    "Ex. Perception ou Acrobatics"
                ),
            ).props(
                "clearable"
            ).classes(
                "grow min-w-[220px]"
            )

        count_label = ui.label(
            ""
        ).classes(
            "jf-rpg-skill-filter-summary text-sm mt-3"
        )

        ui.label(
            "Les rangs Pathfinder sont des nombres entiers. "
            "Les noms français et anglais sont réunis sur une "
            "seule ligne. La formule complète apparaît sous "
            "chaque compétence."
        ).classes(
            "text-xs jf-muted mt-2"
        )

    empty_message = ui.card().classes(
        "w-full p-6 items-center text-center"
    )

    with empty_message:
        ui.icon(
            "filter_alt_off"
        ).classes(
            "text-4xl text-gray-400"
        )
        empty_title = ui.label(
            "Aucune compétence dans ce filtre"
        ).classes(
            "text-lg font-bold"
        )
        empty_detail = ui.label(
            "Choisissez un autre filtre ou modifiez la recherche."
        ).classes(
            "text-sm jf-muted"
        )

    cards_container = ui.column().classes(
        "w-full gap-2"
    )

    with cards_container:
        for skill_row in skills:
            name_state = {
                "fr": str(
                    skill_row[
                        "skill_name"
                    ]
                    or ""
                ).strip(),
                "en": str(
                    skill_row[
                        "english_name"
                    ]
                    or ""
                ).strip(),
            }

            card = ui.element("div").classes(
                "jf-rpg-skill-card"
            )

            with card:
                with ui.element("div").classes(
                    "jf-rpg-skill-header"
                ):
                    name_label = ui.label(
                        _skill_display_name(
                            name_state[
                                "fr"
                            ],
                            name_state[
                                "en"
                            ],
                        )
                    ).classes(
                        "jf-rpg-skill-name grow"
                    )

                    edit_name_button = ui.button(
                        icon="edit",
                    ).props(
                        "flat dense round color=primary"
                    ).classes(
                        "jf-rpg-skill-edit-button"
                    ).tooltip(
                        "Modifier les noms"
                    )

                    with ui.element("div").classes(
                        "jf-rpg-skill-badges-compact"
                    ):
                        owned_badge = ui.label(
                            "✓ Possédée"
                        ).classes(
                            "jf-rpg-skill-badge "
                            "jf-rpg-skill-badge-owned"
                        )
                        class_badge = ui.label(
                            "★ Classe"
                        ).classes(
                            "jf-rpg-skill-badge "
                            "jf-rpg-skill-badge-class"
                        )
                        trained_badge = ui.label(
                            "Formation"
                        ).classes(
                            "jf-rpg-skill-badge"
                        )
                        armor_badge = ui.label(
                            "Armure"
                        ).classes(
                            "jf-rpg-skill-badge"
                        )
                        legacy_badge = ui.label(
                            "Ancienne 3.5"
                        ).classes(
                            "jf-rpg-skill-badge"
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
                            "flat dense round color=negative"
                        ).tooltip(
                            "Supprimer la compétence personnalisée"
                        )

                with ui.element("div").classes(
                    "jf-rpg-skill-controls"
                ):
                    ability_input = ui.select(
                        ABILITY_LABELS,
                        label="Carac.",
                        value=skill_row[
                            "ability_key"
                        ],
                    ).props(
                        "dense outlined options-dense"
                    ).classes(
                        "jf-rpg-skill-control"
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
                        step=1,
                    ).props(
                        "dense outlined"
                    ).classes(
                        "jf-rpg-skill-control"
                    )

                    misc_input = ui.number(
                        label="Divers",
                        value=skill_row[
                            "misc_modifier"
                        ],
                        step=1,
                    ).props(
                        "dense outlined"
                    ).classes(
                        "jf-rpg-skill-control"
                    )

                    class_input = ui.checkbox(
                        "Classe",
                        value=skill_row[
                            "class_skill"
                        ],
                    ).classes(
                        "jf-rpg-skill-check"
                    ).tooltip(
                        "Compétence de classe"
                    )

                    trained_input = ui.checkbox(
                        "Formation",
                        value=skill_row[
                            "trained_only"
                        ],
                    ).classes(
                        "jf-rpg-skill-check"
                    ).tooltip(
                        "Formation requise"
                    )

                    armor_input = ui.checkbox(
                        "Armure",
                        value=skill_row[
                            "armor_check_applies"
                        ],
                    ).classes(
                        "jf-rpg-skill-check"
                    ).tooltip(
                        "La pénalité d’armure s’applique"
                    )

                    double_input = ui.checkbox(
                        "×2",
                        value=skill_row[
                            "double_armor_penalty"
                        ],
                    ).classes(
                        "jf-rpg-skill-check"
                    ).tooltip(
                        "Doubler la pénalité d’armure"
                    )

                calculation_label = ui.label(
                    ""
                ).classes(
                    "jf-rpg-skill-calculation"
                )

                warning_row = ui.element("div").classes(
                    "jf-rpg-skill-warning"
                )

                with warning_row:
                    ui.label(
                        "Le +3 de compétence de classe est déjà "
                        "automatique. Vérifiez si « Divers +3 » "
                        "le répète."
                    ).classes(
                        "grow"
                    )

                    clear_duplicate_button = ui.button(
                        "Mettre Divers à 0",
                    ).props(
                        "flat dense no-caps color=warning"
                    )

                editor = {
                    "row": skill_row,
                    "container": card,
                    "name_state": name_state,
                    "name_label": name_label,
                    "ability": ability_input,
                    "ranks": ranks_input,
                    "misc": misc_input,
                    "class_skill": class_input,
                    "trained": trained_input,
                    "armor": armor_input,
                    "double": double_input,
                    "total": total_label,
                    "calculation": calculation_label,
                    "warning": warning_row,
                    "owned_badge": owned_badge,
                    "class_badge": class_badge,
                    "trained_badge": trained_badge,
                    "armor_badge": armor_badge,
                    "legacy_badge": legacy_badge,
                }
                editors.append(
                    editor
                )

                def update_total(
                    event=None,
                    *,
                    selected=editor,
                ):
                    row = {
                        "ability_key": (
                            selected[
                                "ability"
                            ].value
                            or "int"
                        ),
                        "ranks": (
                            selected[
                                "ranks"
                            ].value
                            or 0
                        ),
                        "misc_modifier": (
                            selected[
                                "misc"
                            ].value
                            or 0
                        ),
                        "class_skill": bool(
                            selected[
                                "class_skill"
                            ].value
                        ),
                        "armor_check_applies": bool(
                            selected[
                                "armor"
                            ].value
                        ),
                        "double_armor_penalty": bool(
                            selected[
                                "double"
                            ].value
                        ),
                    }

                    breakdown = (
                        skill_breakdown(
                            character,
                            row,
                        )
                    )

                    selected[
                        "total"
                    ].set_text(
                        format_number(
                            breakdown[
                                "total"
                            ]
                        )
                    )

                    selected[
                        "calculation"
                    ].set_text(
                        _skill_breakdown_text(
                            breakdown
                        )
                    )

                    duplicate_class_bonus = (
                        breakdown[
                            "class_bonus"
                        ]
                        == 3
                        and breakdown[
                            "misc_modifier"
                        ]
                        == 3
                    )

                    selected[
                        "warning"
                    ].set_visibility(
                        duplicate_class_bonus
                    )

                def update_indicators(
                    event=None,
                    *,
                    selected=editor,
                ):
                    ranks = Decimal(
                        str(
                            selected[
                                "ranks"
                            ].value
                            or 0
                        )
                    )

                    selected[
                        "owned_badge"
                    ].set_visibility(
                        ranks > 0
                    )
                    selected[
                        "class_badge"
                    ].set_visibility(
                        bool(
                            selected[
                                "class_skill"
                            ].value
                        )
                    )
                    selected[
                        "trained_badge"
                    ].set_visibility(
                        bool(
                            selected[
                                "trained"
                            ].value
                        )
                    )
                    selected[
                        "armor_badge"
                    ].set_visibility(
                        bool(
                            selected[
                                "armor"
                            ].value
                        )
                    )
                    selected[
                        "legacy_badge"
                    ].set_visibility(
                        (
                            "ancienne 3.5"
                            in selected[
                                "name_state"
                            ][
                                "fr"
                            ].lower()
                        )
                    )

                def open_name_dialog(
                    event=None,
                    *,
                    selected=editor,
                ):
                    with ui.dialog() as dialog:
                        with ui.card().classes(
                            "w-full max-w-lg p-5"
                        ):
                            ui.label(
                                "Modifier les noms de la compétence"
                            ).classes(
                                "text-xl font-bold"
                            )

                            french_input = ui.input(
                                label="Nom français",
                                value=selected[
                                    "name_state"
                                ][
                                    "fr"
                                ],
                            ).props(
                                "autofocus maxlength=120"
                            ).classes(
                                "w-full"
                            )

                            english_input = ui.input(
                                label="Nom anglais",
                                value=selected[
                                    "name_state"
                                ][
                                    "en"
                                ],
                            ).props(
                                "maxlength=120"
                            ).classes(
                                "w-full"
                            )

                            def apply_names():
                                french = str(
                                    french_input.value
                                    or ""
                                ).strip()
                                english = str(
                                    english_input.value
                                    or ""
                                ).strip()

                                if not french:
                                    ui.notify(
                                        "Le nom français est obligatoire.",
                                        type="warning",
                                    )
                                    return

                                selected[
                                    "name_state"
                                ][
                                    "fr"
                                ] = french
                                selected[
                                    "name_state"
                                ][
                                    "en"
                                ] = english

                                selected[
                                    "name_label"
                                ].set_text(
                                    _skill_display_name(
                                        french,
                                        english,
                                    )
                                )

                                update_indicators(
                                    selected=selected
                                )
                                apply_filters()
                                dialog.close()

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
                                    "Appliquer",
                                    icon="check",
                                    on_click=apply_names,
                                ).props(
                                    "color=primary"
                                )

                    dialog.open()

                edit_name_button.on(
                    "click",
                    open_name_dialog,
                )

                def clear_duplicate(
                    event=None,
                    *,
                    selected=editor,
                ):
                    selected[
                        "misc"
                    ].value = 0
                    update_total(
                        selected=selected
                    )

                clear_duplicate_button.on(
                    "click",
                    clear_duplicate,
                )

                for control in (
                    ability_input,
                    ranks_input,
                    misc_input,
                    class_input,
                    armor_input,
                    double_input,
                ):
                    control.on_value_change(
                        update_total
                    )

                for control in (
                    ranks_input,
                    class_input,
                    trained_input,
                    armor_input,
                ):
                    control.on_value_change(
                        update_indicators
                    )

                update_total()
                update_indicators()

    def skill_state(
        editor,
    ):
        ranks = Decimal(
            str(
                editor[
                    "ranks"
                ].value
                or 0
            )
        )

        return {
            "owned": ranks > 0,
            "class_skill": bool(
                editor[
                    "class_skill"
                ].value
            ),
            "unranked": ranks == 0,
            "name": editor[
                "name_state"
            ][
                "fr"
            ].lower(),
            "english_name": editor[
                "name_state"
            ][
                "en"
            ].lower(),
        }

    def refresh_counts():
        owned_count = 0
        class_count = 0
        unranked_count = 0

        for editor in editors:
            state = skill_state(
                editor
            )
            owned_count += int(
                state[
                    "owned"
                ]
            )
            class_count += int(
                state[
                    "class_skill"
                ]
            )
            unranked_count += int(
                state[
                    "unranked"
                ]
            )

        count_label.set_text(
            (
                f"Mes compétences : {owned_count}  ·  "
                f"Compétences de classe : {class_count}  ·  "
                f"Sans rang : {unranked_count}  ·  "
                f"Total : {len(editors)}"
            )
        )

    def apply_filters(
        event=None,
    ):
        selected_filter = (
            filter_toggle.value
            or "all"
        )
        query = str(
            search_input.value
            or ""
        ).strip().lower()

        visible_count = 0

        for editor in editors:
            state = skill_state(
                editor
            )

            if selected_filter == "owned":
                category_match = state[
                    "owned"
                ]
            elif selected_filter == "class":
                category_match = state[
                    "class_skill"
                ]
            elif selected_filter == "unranked":
                category_match = state[
                    "unranked"
                ]
            else:
                category_match = True

            search_match = (
                not query
                or query
                in state[
                    "name"
                ]
                or query
                in state[
                    "english_name"
                ]
            )
            visible = (
                category_match
                and search_match
            )

            editor[
                "container"
            ].set_visibility(
                visible
            )
            visible_count += int(
                visible
            )

        empty_message.set_visibility(
            visible_count == 0
        )

        if visible_count == 0:
            if selected_filter == "owned":
                empty_title.set_text(
                    "Aucune compétence possédée"
                )
                empty_detail.set_text(
                    "Passez à « Sans rang » ou « Toutes », "
                    "puis investissez au moins 1 rang."
                )
            else:
                empty_title.set_text(
                    "Aucune compétence dans ce filtre"
                )
                empty_detail.set_text(
                    "Choisissez un autre filtre "
                    "ou modifiez la recherche."
                )

        refresh_counts()

    filter_toggle.on_value_change(
        apply_filters
    )
    search_input.on_value_change(
        apply_filters
    )

    for editor in editors:
        editor[
            "ranks"
        ].on_value_change(
            lambda event: (
                refresh_counts()
            )
        )
        editor[
            "class_skill"
        ].on_value_change(
            lambda event: (
                refresh_counts()
            )
        )

    apply_filters()

    def save_skills():
        rows = [
            {
                "id": editor[
                    "row"
                ][
                    "id"
                ],
                "skill_name": editor[
                    "name_state"
                ][
                    "fr"
                ],
                "english_name": editor[
                    "name_state"
                ][
                    "en"
                ],
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
                character[
                    "id"
                ],
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
            "Compétences Pathfinder enregistrées.",
            type="positive",
        )
        ui.navigate.to(
            _character_url(
                character[
                    "id"
                ],
                "competences",
            )
        )

    with ui.row().classes(
        "jf-rpg-section-actions gap-2 flex-wrap"
    ):
        ui.button(
            "Règles de calcul",
            icon="menu_book",
            on_click=lambda: _calculation_rules_dialog(
                user_id,
                character,
            ),
        ).props(
            "outline color=primary"
        )
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
    show_heading=True,
):
    user_id = current_user["id"]
    characters = list_rpg_characters(
        user_id
    )

    if show_heading:
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
                    "Feuille interactive Pathfinder "
                    "dans l’univers Ravenloft."
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
