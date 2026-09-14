"""Petits dialogues et formats partagés par les compétences JDR."""
from __future__ import annotations


def skill_display_name(french_name, english_name) -> str:
    french = str(french_name or "").strip()
    english = str(english_name or "").strip()

    if french and english:
        return f"{french} — {english}"
    return french or english or "Compétence sans nom"


def skill_breakdown_text(
    breakdown,
    *,
    ability_labels,
    format_modifier,
) -> str:
    ability_label = ability_labels.get(
        breakdown["ability_key"],
        str(breakdown["ability_key"]).upper(),
    )

    parts = [
        f"{ability_label} {format_modifier(breakdown['ability_modifier'])}",
        f"rangs {format_modifier(breakdown['ranks'])}",
        f"classe {format_modifier(breakdown['class_bonus'])}",
        f"divers {format_modifier(breakdown['misc_modifier'])}",
    ]
    if breakdown["armor_penalty"] != 0:
        parts.append(
            f"armure {format_modifier(breakdown['armor_penalty'])}"
        )

    return (
        " + ".join(parts)
        + " = total "
        + format_modifier(breakdown["total"])
    )


def open_skill_dialog(
    *,
    ui,
    user_id,
    character,
    on_saved,
    ability_labels,
    ability_long_labels,
    create_custom_rpg_skill,
    notify_error,
):
    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-lg p-5"):
            ui.label("Ajouter une compétence").classes(
                "text-xl font-bold"
            )

            name_input = ui.input(
                label="Nom français",
            ).props("autofocus maxlength=120").classes("w-full")
            english_name_input = ui.input(
                label="Nom anglais (facultatif)",
                placeholder="Ex. Knowledge (local)",
            ).props("maxlength=120").classes("w-full")
            ability_input = ui.select(
                {
                    key: f"{label} - {ability_long_labels[key]}"
                    for key, label in ability_labels.items()
                },
                value="int",
                label="Caractéristique",
            ).classes("w-full")
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
                        english_name=english_name_input.value,
                        ability_key=ability_input.value,
                        trained_only=trained_input.value,
                        armor_check_applies=armor_input.value,
                        double_armor_penalty=double_input.value,
                    )
                except Exception as error:
                    notify_error(
                        error,
                        "La compétence n’a pas pu être créée.",
                    )
                    return

                dialog.close()
                ui.notify("Compétence ajoutée.", type="positive")
                on_saved()

            with ui.row().classes("w-full justify-end gap-2 mt-3"):
                ui.button("Annuler", on_click=dialog.close).props("flat")
                ui.button(
                    "Ajouter",
                    icon="add",
                    on_click=save,
                ).props("color=primary")

    dialog.open()
