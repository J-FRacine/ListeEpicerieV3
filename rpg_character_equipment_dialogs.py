"""Dialogues d'ajout, modification et suppression d'équipement JDR."""
from __future__ import annotations


def open_equipment_dialog(
    *,
    ui,
    user_id,
    character,
    row=None,
    equipment_type_labels,
    armor_category_labels,
    save_rpg_equipment,
    notify_error,
    character_url,
):
    editing = row is not None
    row = dict(row or {})

    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-4xl p-4"):
            ui.label(
                "Modifier l’équipement" if editing else "Ajouter un équipement"
            ).classes("text-xl font-bold")

            with ui.element("div").classes("jf-rpg-grid mt-2"):
                name_input = ui.input(
                    label="Nom",
                    value=row.get("item_name") or "",
                ).props("maxlength=160").classes("w-full")
                type_input = ui.select(
                    equipment_type_labels,
                    label="Type",
                    value=row.get("item_type") or "gear",
                ).props("options-dense").classes("w-full")
                quantity_input = ui.number(
                    label="Quantité",
                    value=row.get("quantity") or 1,
                    min=0,
                    max=100000,
                    step=1,
                ).props("inputmode=numeric").classes("w-full")
                weight_input = ui.number(
                    label="Poids unitaire (lb)",
                    value=float(row.get("weight_each") or 0),
                    min=0,
                    step=.1,
                ).props("inputmode=decimal").classes("w-full")
                value_input = ui.input(
                    label="Valeur",
                    value=row.get("value_text") or "",
                    placeholder="Ex. 1 500 po",
                ).props("maxlength=120").classes("w-full")
                proficiency_input = ui.input(
                    label="Maîtrise requise",
                    value=row.get("proficiency_required") or "",
                    placeholder="Ex. Armures lourdes",
                ).props("maxlength=160").classes("w-full")

            with ui.row().classes("w-full gap-4 flex-wrap mt-2"):
                carried_input = ui.checkbox(
                    "Transporté",
                    value=bool(row.get("carried", True)),
                )
                equipped_input = ui.checkbox(
                    "Équipé",
                    value=bool(row.get("equipped")),
                )

            protection_container = ui.element("section").classes(
                "jf-rpg-race-profile mt-3"
            )
            with protection_container:
                ui.label("Propriétés de protection").classes(
                    "text-lg font-bold"
                )
                ui.label(
                    "Ces valeurs alimentent automatiquement la CA, "
                    "la DEX maximale, les compétences et la vitesse."
                ).classes("text-sm jf-muted")

                with ui.element("div").classes("jf-rpg-grid mt-2"):
                    armor_category_input = ui.select(
                        armor_category_labels,
                        label="Catégorie d’armure",
                        value=row.get("armor_category") or "none",
                    ).classes("w-full")
                    armor_bonus_input = ui.number(
                        label="Bonus d’armure",
                        value=row.get("armor_bonus") or 0,
                        min=0,
                        max=100,
                        step=1,
                    ).classes("w-full")
                    shield_bonus_input = ui.number(
                        label="Bonus de bouclier",
                        value=row.get("shield_bonus") or 0,
                        min=0,
                        max=100,
                        step=1,
                    ).classes("w-full")
                    enhancement_input = ui.number(
                        label="Bonus d’altération",
                        value=row.get("enhancement_bonus") or 0,
                        min=0,
                        max=20,
                        step=1,
                    ).classes("w-full")
                    max_dex_input = ui.number(
                        label="Bonus DEX maximal",
                        value=row.get("max_dex_bonus"),
                        min=-100,
                        max=100,
                        step=1,
                    ).props("clearable").classes("w-full")
                    armor_penalty_input = ui.number(
                        label="Pénalité aux tests",
                        value=row.get("armor_check_penalty") or 0,
                        min=-100,
                        max=0,
                        step=1,
                    ).classes("w-full")
                    spell_failure_input = ui.number(
                        label="Échec sorts profanes (%)",
                        value=row.get("arcane_spell_failure") or 0,
                        min=0,
                        max=100,
                        step=1,
                    ).classes("w-full")
                    reduced_speed_input = ui.number(
                        label="Vitesse réduite personnalisée",
                        value=row.get("reduced_speed_override"),
                        min=0,
                        max=500,
                        step=5,
                    ).props("clearable").classes("w-full")

                speed_reduction_input = ui.checkbox(
                    "Cet équipement réduit la vitesse",
                    value=bool(row.get("speed_reduction_applies")),
                )

            notes_input = ui.textarea(
                label="Note facultative",
                value=row.get("notes") or "",
            ).props("outlined autogrow maxlength=2000").classes("w-full mt-3")

            def refresh_type_visibility():
                item_type = type_input.value or "gear"
                is_protection = item_type in {"armor", "shield"}
                protection_container.set_visibility(is_protection)
                armor_category_input.set_visibility(item_type == "armor")
                armor_bonus_input.set_visibility(item_type == "armor")
                shield_bonus_input.set_visibility(item_type == "shield")
                reduced_speed_input.set_visibility(item_type == "armor")
                speed_reduction_input.set_visibility(item_type == "armor")
                proficiency_input.set_visibility(
                    item_type in {"armor", "shield", "weapon"}
                )

            type_input.on_value_change(
                lambda event: refresh_type_visibility()
            )
            refresh_type_visibility()

            def save_now():
                try:
                    save_rpg_equipment(
                        user_id,
                        character["id"],
                        {
                            "item_name": name_input.value,
                            "item_type": type_input.value,
                            "quantity": quantity_input.value,
                            "weight_each": weight_input.value,
                            "value_text": value_input.value,
                            "notes": notes_input.value,
                            "carried": carried_input.value,
                            "equipped": equipped_input.value,
                            "armor_category": armor_category_input.value,
                            "armor_bonus": armor_bonus_input.value,
                            "shield_bonus": shield_bonus_input.value,
                            "enhancement_bonus": enhancement_input.value,
                            "max_dex_bonus": max_dex_input.value,
                            "armor_check_penalty": armor_penalty_input.value,
                            "arcane_spell_failure": spell_failure_input.value,
                            "speed_reduction_applies": speed_reduction_input.value,
                            "reduced_speed_override": reduced_speed_input.value,
                            "proficiency_required": proficiency_input.value,
                            "sort_order": row.get("sort_order") or 0,
                        },
                        equipment_id=row.get("id"),
                    )
                except Exception as error:
                    notify_error(
                        error,
                        "L’équipement n’a pas pu être enregistré.",
                    )
                    return

                dialog.close()
                ui.notify("Équipement enregistré.", type="positive")
                ui.navigate.to(
                    character_url(character["id"], "equipement")
                )

            with ui.row().classes("w-full justify-end gap-2 mt-3"):
                ui.button("Annuler", on_click=dialog.close).props("flat")
                ui.button(
                    "Enregistrer",
                    icon="save",
                    on_click=save_now,
                ).props("color=primary")

    dialog.open()


def open_delete_equipment_dialog(
    *,
    ui,
    user_id,
    character,
    row,
    delete_rpg_equipment,
    notify_error,
    character_url,
):
    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-lg p-4"):
            ui.label("Supprimer l’équipement").classes(
                "text-xl font-bold"
            )
            ui.label(f"Supprimer « {row['item_name']} »?")

            def confirm():
                try:
                    delete_rpg_equipment(
                        user_id,
                        character["id"],
                        row["id"],
                    )
                except Exception as error:
                    notify_error(
                        error,
                        "L’équipement n’a pas pu être supprimé.",
                    )
                    return
                dialog.close()
                ui.notify("Équipement supprimé.", type="positive")
                ui.navigate.to(
                    character_url(character["id"], "equipement")
                )

            with ui.row().classes("w-full justify-end gap-2 mt-3"):
                ui.button("Annuler", on_click=dialog.close).props("flat")
                ui.button(
                    "Supprimer",
                    icon="delete",
                    on_click=confirm,
                ).props("color=negative")
    dialog.open()
