"""Dialogue spécialisé pour les objets magiques JDR — Phase 14."""
from __future__ import annotations


def open_magic_item_dialog(
    *,
    ui,
    user_id,
    character,
    row=None,
    magic_kind_labels,
    magic_item_templates,
    magic_template_values,
    container_options,
    save_rpg_equipment,
    notify_error,
    character_url,
):
    editing = row is not None
    original = dict(row or {})

    with ui.dialog() as dialog:
        with ui.card().classes(
            "w-full max-w-3xl p-4 max-h-[92vh] overflow-auto"
        ):
            ui.label(
                "Configurer l’objet magique"
                if editing
                else "Ajouter un objet magique"
            ).classes("text-xl font-bold")

            template_input = ui.select(
                {
                    key: value["label"]
                    for key, value in magic_item_templates.items()
                },
                label="Modèle facultatif",
                value=original.get("magic_template_key") or "",
            ).props("options-dense").classes("w-full")

            with ui.element("div").classes("jf-rpg-grid mt-2"):
                name_input = ui.input(
                    label="Nom",
                    value=original.get("item_name") or "",
                ).props("maxlength=160").classes("w-full")
                quantity_input = ui.number(
                    label="Quantité",
                    value=original.get("quantity") or 1,
                    min=0,
                    max=100000,
                    step=1,
                ).classes("w-full")
                weight_input = ui.number(
                    label="Poids unitaire (lb)",
                    value=float(original.get("weight_each") or 0),
                    min=0,
                    step=.1,
                ).classes("w-full")
                value_input = ui.input(
                    label="Valeur",
                    value=original.get("value_text") or "",
                    placeholder="Ex. 2 000 po",
                ).props("maxlength=120").classes("w-full")

            with ui.row().classes("w-full gap-4 flex-wrap mt-2"):
                carried_input = ui.checkbox(
                    "Transporté",
                    value=bool(original.get("carried", True)),
                )
                equipped_input = ui.checkbox(
                    "Équipé / porté",
                    value=bool(original.get("equipped")),
                )
                magic_enabled_input = ui.checkbox(
                    "Objet magique",
                    value=(
                        bool(original.get("is_magic_item"))
                        if editing
                        else True
                    ),
                )

            with ui.element("div").classes("jf-rpg-grid mt-2"):
                kind_input = ui.select(
                    magic_kind_labels,
                    label="Fonction magique",
                    value=original.get("magic_kind") or "other",
                ).props("options-dense").classes("w-full")
                resistance_input = ui.number(
                    label="Bonus de résistance aux sauvegardes",
                    value=original.get("magic_resistance_bonus") or 0,
                    min=0,
                    max=20,
                    step=1,
                ).classes("w-full")
                charges_current_input = ui.number(
                    label="Charges actuelles",
                    value=original.get("magic_charges_current"),
                    min=0,
                    max=100000,
                    step=1,
                ).props("clearable").classes("w-full")
                charges_max_input = ui.number(
                    label="Charges maximums",
                    value=original.get("magic_charges_max"),
                    min=0,
                    max=100000,
                    step=1,
                ).props("clearable").classes("w-full")
                spell_input = ui.input(
                    label="Sort contenu",
                    value=original.get("magic_contained_spell_name") or "",
                    placeholder="Ex. Cure Light Wounds",
                ).props("maxlength=200").classes("w-full")
                caster_level_input = ui.number(
                    label="Niveau de lanceur de sorts",
                    value=original.get("magic_caster_level"),
                    min=0,
                    max=100,
                    step=1,
                ).props("clearable").classes("w-full")
                capacity_input = ui.number(
                    label="Capacité magique (lb)",
                    value=original.get("magic_capacity_weight"),
                    min=0,
                    max=100000,
                    step=1,
                ).props("clearable").classes("w-full")
                container_input = ui.select(
                    container_options,
                    label="Rangé dans",
                    value=original.get("container_equipment_id"),
                ).props("options-dense clearable").classes("w-full")

            requires_equipped_input = ui.checkbox(
                "L’effet exige que l’objet soit équipé / porté",
                value=bool(original.get("magic_requires_equipped")),
            )

            activation_input = ui.textarea(
                label="Effet / activation",
                value=original.get("magic_activation_text") or "",
            ).props(
                "outlined autogrow maxlength=2000"
            ).classes("w-full mt-2")

            ui.label(
                "Le bonus de résistance est ajouté sans modifier les valeurs "
                "permanentes des Sauvegardes. Les bonus de résistance ne "
                "s’additionnent pas : le meilleur bonus actif est retenu."
            ).classes("text-xs jf-muted")

            def apply_template(_event=None):
                values = magic_template_values(template_input.value)
                if not values:
                    return
                controls = (
                    (name_input, values.get("item_name") or ""),
                    (quantity_input, values.get("quantity") or 1),
                    (weight_input, values.get("weight_each") or 0),
                    (value_input, values.get("value_text") or ""),
                    (carried_input, bool(values.get("carried", True))),
                    (equipped_input, bool(values.get("equipped"))),
                    (magic_enabled_input, True),
                    (kind_input, values.get("magic_kind") or "other"),
                    (
                        requires_equipped_input,
                        bool(values.get("magic_requires_equipped")),
                    ),
                    (
                        resistance_input,
                        values.get("magic_resistance_bonus") or 0,
                    ),
                    (
                        charges_current_input,
                        values.get("magic_charges_current"),
                    ),
                    (charges_max_input, values.get("magic_charges_max")),
                    (
                        spell_input,
                        values.get("magic_contained_spell_name") or "",
                    ),
                    (
                        caster_level_input,
                        values.get("magic_caster_level"),
                    ),
                    (
                        capacity_input,
                        values.get("magic_capacity_weight"),
                    ),
                    (
                        activation_input,
                        values.get("magic_activation_text") or "",
                    ),
                )
                for control, value in controls:
                    control.value = value
                    control.update()

            template_input.on_value_change(apply_template)

            def save_now():
                values = dict(original)
                values.update({
                    "item_name": name_input.value,
                    "item_type": original.get("item_type") or "gear",
                    "quantity": quantity_input.value,
                    "weight_each": weight_input.value,
                    "value_text": value_input.value,
                    "carried": carried_input.value,
                    "equipped": equipped_input.value,
                    "magic_enabled": magic_enabled_input.value,
                    "magic_template_key": template_input.value,
                    "magic_kind": kind_input.value,
                    "magic_requires_equipped":
                        requires_equipped_input.value,
                    "magic_resistance_bonus": resistance_input.value,
                    "magic_charges_current":
                        charges_current_input.value,
                    "magic_charges_max": charges_max_input.value,
                    "magic_contained_spell_name": spell_input.value,
                    "magic_caster_level": caster_level_input.value,
                    "magic_capacity_weight": capacity_input.value,
                    "magic_activation_text": activation_input.value,
                    "container_equipment_id": container_input.value,
                })
                try:
                    save_rpg_equipment(
                        user_id,
                        character["id"],
                        values,
                        equipment_id=original.get("id"),
                    )
                except Exception as error:
                    notify_error(
                        error,
                        "L’objet magique n’a pas pu être enregistré.",
                    )
                    return

                dialog.close()
                ui.notify("Objet magique enregistré.", type="positive")
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
