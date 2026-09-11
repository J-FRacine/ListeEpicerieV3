"""Panneau JDR — Jets de sauvegarde.

Ce module ne dépend ni de NiceGUI, ni de la base de données, ni du module
principal JDR. Toutes ses dépendances sont injectées par la façade publique.
"""
from __future__ import annotations


def build_saves_panel(
    *,
    ui,
    user_id,
    character,
    list_rpg_saves,
    save_definitions,
    ability_labels,
    ability_modifier_for_character,
    save_total,
    format_modifier,
    as_number,
    update_rpg_saves,
    notify_error,
    calculation_rules_dialog,
):
    """Construit le panneau des jets de sauvegarde du personnage."""
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
                    save_definitions[
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
                            f"{ability_labels[ability_key]} "
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
                            as_number(
                                base_control.value
                            )
                            + as_number(
                                magic_control.value
                            )
                            + as_number(
                                misc_control.value
                            )
                            + as_number(
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
                notify_error(
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
                on_click=lambda: calculation_rules_dialog(
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
