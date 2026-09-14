"""Panneau JDR — Équipement et encombrement."""
from __future__ import annotations

from decimal import Decimal


def build_equipment_panel(
    *,
    ui,
    user_id,
    character,
    list_rpg_equipment,
    apply_equipment_effects,
    equipment_type_labels,
    armor_category_labels,
    weapon_handedness_labels,
    format_number,
    format_modifier,
    update_rpg_equipment_state,
    create_attack_from_weapon,
    notify_error,
    character_url,
    equipment_dialog,
    delete_equipment_dialog,
):
    equipment = list_rpg_equipment(user_id, character["id"])
    effective = apply_equipment_effects(character, equipment)
    effects = effective["equipment_effects"]
    capacity = effects["carrying_capacity"]

    has_iomedae_longsword = any(
        row.get("weapon_template_key") == "iomedae_longsword"
        for row in equipment
    )

    with ui.card().classes("w-full p-5"):
        with ui.row().classes(
            "w-full items-start justify-between gap-3 flex-wrap"
        ):
            with ui.column().classes("gap-0"):
                ui.label("Équipement et encombrement").classes(
                    "text-xl font-bold"
                )
                ui.label(
                    "Les protections alimentent les statistiques. "
                    "Les armes physiques peuvent maintenant être liées aux Attaques."
                ).classes("text-sm jf-muted")

            with ui.row().classes("gap-2 flex-wrap"):
                if (
                    str(character.get("deity") or "").strip().lower()
                    == "iomedae"
                    and not has_iomedae_longsword
                ):
                    ui.button(
                        "Épée longue d’Iomedae",
                        icon="auto_awesome",
                        on_click=lambda: equipment_dialog(
                            user_id,
                            character,
                            preset_key="iomedae_longsword",
                        ),
                    ).props("outline color=primary")

                ui.button(
                    "Ajouter",
                    icon="add",
                    on_click=lambda: equipment_dialog(
                        user_id,
                        character,
                    ),
                ).props("color=primary")

        with ui.element("div").classes(
            "jf-rpg-equipment-summary-grid mt-3"
        ):
            threshold_label = {
                "light": "Avant ralentissement",
                "medium": "Avant charge lourde",
                "heavy": "Avant surcharge",
                "overloaded": "Avant immobilisation",
                "immovable": "Surcharge excédentaire",
            }.get(
                effects["load_key"],
                "Avant le prochain seuil",
            )
            threshold_value = (
                effects["remaining_before_next_threshold"]
                if effects["load_key"] != "immovable"
                else max(
                    Decimal("0"),
                    effects["carried_weight"]
                    - capacity["lift_off_ground_max"],
                )
            )
            summary_values = (
                ("Poids transporté",
                 f"{format_number(effects['carried_weight'])} lb"),
                ("Charge actuelle", effects["load_label"]),
                (threshold_label,
                 f"{format_number(threshold_value)} lb"),
                ("Charge légère max.",
                 f"{format_number(capacity['light_max'])} lb"),
                ("Charge moyenne max.",
                 f"{format_number(capacity['medium_max'])} lb"),
                ("Charge lourde max.",
                 f"{format_number(capacity['heavy_max'])} lb"),
                ("Soulever du sol max.",
                 f"{format_number(capacity['lift_off_ground_max'])} lb"),
                ("Pousser / tirer max.",
                 f"{format_number(capacity['push_drag_max'])} lb"),
                ("Vitesse finale", f"{effects['final_speed']} pi"),
                (
                    "Course",
                    f"×{effects['run_multiplier']}"
                    if effects["run_multiplier"]
                    else "Impossible",
                ),
            )
            for label, value in summary_values:
                with ui.element("div").classes(
                    "jf-rpg-equipment-stat"
                ):
                    ui.label(label).classes("text-xs jf-muted")
                    ui.label(value).classes(
                        "jf-rpg-equipment-stat-value"
                    )

        armor = effects["equipped_armor"]
        shield = effects["equipped_shield"]
        with ui.element("div").classes(
            "jf-rpg-equipment-breakdown mt-3"
        ):
            ui.label("Décomposition retenue").classes("font-bold")
            ui.label(
                f"Armure : {armor['item_name'] if armor else 'aucune'} "
                f"({format_modifier(effects['equipment_armor_bonus'])}); "
                f"bouclier : {shield['item_name'] if shield else 'aucun'} "
                f"({format_modifier(effects['equipment_shield_bonus'])})."
            )
            ui.label(
                f"DEX brute {format_modifier(effects['raw_dex_modifier'])}; "
                f"DEX maximale "
                f"{effects['effective_max_dex_bonus'] if effects['effective_max_dex_bonus'] is not None else 'aucune'}; "
                f"DEX retenue "
                f"{format_modifier(effects['effective_ac_dex_modifier'])}."
            )
            ui.label(
                f"Pénalité équipement "
                f"{format_modifier(effects['equipment_armor_check_penalty'])}; "
                f"pénalité finale "
                f"{format_modifier(effects['effective_armor_check_penalty'])}."
            )

            speed_parts = [f"base {effects['base_speed']} pi"]
            if effects["armor_speed"] is not None:
                speed_parts.append(
                    "armure ignorée par exception"
                    if effects["ignore_armor_speed"]
                    else f"armure {effects['armor_speed']} pi"
                )
            if effects["load_speed"] is not None:
                speed_parts.append(
                    "charge ignorée par exception"
                    if effects["ignore_encumbrance_speed"]
                    else f"charge {effects['load_speed']} pi"
                )
            speed_parts.append(f"retenue {effects['final_speed']} pi")
            ui.label("Vitesse : " + " → ".join(speed_parts) + ".")

        ui.label(
            "Une seule armure et un seul bouclier contribuent à la fois. "
            "Une arme physique peut alimenter plusieurs Attaques sans être dupliquée."
        ).classes("text-xs jf-muted mt-2")

    if not equipment:
        with ui.card().classes(
            "w-full p-7 items-center text-center mt-3"
        ):
            ui.icon("backpack").classes("text-6xl text-gray-400")
            ui.label("Aucun équipement").classes("text-xl font-bold")
            ui.label(
                "Ajoutez d’abord une armure, un bouclier, une arme ou une possession."
            ).classes("text-sm jf-muted")
            ui.button(
                "Ajouter un équipement",
                icon="add",
                on_click=lambda: equipment_dialog(user_id, character),
            ).props("color=primary")
        return

    for item_type, type_label in equipment_type_labels.items():
        rows = [
            row for row in equipment
            if row["item_type"] == item_type
        ]
        if not rows:
            continue

        ui.label(type_label).classes("text-lg font-bold mt-3")

        with ui.column().classes("w-full gap-2"):
            for row in rows:
                total_weight = (
                    Decimal(str(row["weight_each"] or 0))
                    * Decimal(str(row["quantity"] or 0))
                )

                with ui.element("article").classes(
                    "jf-rpg-equipment-card"
                ):
                    with ui.element("div").classes(
                        "jf-rpg-equipment-row"
                    ):
                        with ui.column().classes("gap-0 min-w-0"):
                            with ui.row().classes(
                                "items-center gap-2 flex-wrap"
                            ):
                                ui.label(row["item_name"]).classes(
                                    "jf-rpg-equipment-name"
                                )
                                if row["equipped"]:
                                    ui.badge("Équipé", color="positive")
                                if not row["carried"]:
                                    ui.badge(
                                        "Non transporté", color="grey"
                                    )
                                if (
                                    item_type == "weapon"
                                    and row.get("weapon_masterwork")
                                ):
                                    ui.badge("Maître", color="primary")
                                if (
                                    item_type == "weapon"
                                    and int(
                                        row.get("weapon_enhancement_bonus")
                                        or 0
                                    ) > 0
                                ):
                                    ui.badge(
                                        f"+{row['weapon_enhancement_bonus']} magique",
                                        color="purple",
                                    )

                            ui.label(
                                f"Quantité {row['quantity']} — "
                                f"{format_number(row['weight_each'])} lb chacun — "
                                f"total {format_number(total_weight)} lb"
                            ).classes("jf-rpg-equipment-meta")

                            if item_type in {"armor", "shield"}:
                                protection_bits = []
                                if item_type == "armor":
                                    protection_bits.append(
                                        "armure "
                                        + format_modifier(
                                            row["armor_bonus"]
                                            + row["enhancement_bonus"]
                                        )
                                    )
                                    protection_bits.append(
                                        armor_category_labels.get(
                                            row["armor_category"],
                                            row["armor_category"],
                                        )
                                    )
                                else:
                                    protection_bits.append(
                                        "bouclier "
                                        + format_modifier(
                                            row["shield_bonus"]
                                            + row["enhancement_bonus"]
                                        )
                                    )
                                if row["max_dex_bonus"] is not None:
                                    protection_bits.append(
                                        f"DEX max {row['max_dex_bonus']}"
                                    )
                                protection_bits.append(
                                    "tests "
                                    + format_modifier(
                                        row["armor_check_penalty"]
                                    )
                                )
                                protection_bits.append(
                                    f"échec profane "
                                    f"{row['arcane_spell_failure']} %"
                                )
                                ui.label(
                                    " — ".join(protection_bits)
                                ).classes("jf-rpg-equipment-meta")

                            if item_type == "weapon":
                                weapon_bits = [
                                    "dégâts "
                                    + (row.get("weapon_damage") or "—"),
                                    "critique "
                                    + (row.get("weapon_critical") or "—"),
                                    row.get("weapon_damage_type")
                                    or "type —",
                                    weapon_handedness_labels.get(
                                        row.get("weapon_handedness"),
                                        row.get("weapon_handedness") or "—",
                                    ),
                                ]
                                if row.get("weapon_range"):
                                    weapon_bits.append(
                                        "portée "
                                        + str(row["weapon_range"])
                                    )
                                ui.label(
                                    " — ".join(weapon_bits)
                                ).classes("jf-rpg-equipment-meta")

                                if row.get("proficiency_required"):
                                    ui.label(
                                        "Maîtrise : "
                                        + str(row["proficiency_required"])
                                    ).classes("text-xs jf-muted")

                                if (
                                    row.get("weapon_ammunition_type")
                                    or row.get("weapon_ammunition_current")
                                    is not None
                                    or row.get("weapon_ammunition_max")
                                    is not None
                                ):
                                    ammo_prefix = (
                                        str(row["weapon_ammunition_type"])
                                        + " — "
                                        if row.get(
                                            "weapon_ammunition_type"
                                        )
                                        else ""
                                    )
                                    ui.label(
                                        "Munitions : "
                                        + ammo_prefix
                                        + str(
                                            row.get(
                                                "weapon_ammunition_current"
                                            )
                                            or 0
                                        )
                                        + " / "
                                        + str(
                                            row.get(
                                                "weapon_ammunition_max"
                                            )
                                            or 0
                                        )
                                    ).classes("text-xs jf-muted")

                                linked = list(
                                    row.get("linked_attacks") or ()
                                )
                                if linked:
                                    ui.label(
                                        "Attaque"
                                        + ("s" if len(linked) > 1 else "")
                                        + " liée"
                                        + ("s" if len(linked) > 1 else "")
                                        + " : "
                                        + ", ".join(
                                            str(a["attack_name"])
                                            for a in linked
                                        )
                                    ).classes(
                                        "text-xs text-primary font-bold"
                                    )

                            if row.get("notes"):
                                ui.label(row["notes"]).classes(
                                    "text-xs jf-muted"
                                )

                        with ui.row().classes(
                            "items-center gap-1 flex-wrap justify-end"
                        ):
                            carried_switch = ui.switch(
                                "Transporté",
                                value=bool(row["carried"]),
                            ).props("dense")
                            equipped_switch = ui.switch(
                                "Équipé",
                                value=bool(row["equipped"]),
                            ).props("dense")

                            def state_changed(
                                _=None,
                                *,
                                current_row=row,
                                carried_control=carried_switch,
                                equipped_control=equipped_switch,
                            ):
                                try:
                                    update_rpg_equipment_state(
                                        user_id,
                                        character["id"],
                                        current_row["id"],
                                        carried=carried_control.value,
                                        equipped=equipped_control.value,
                                    )
                                except Exception as error:
                                    notify_error(
                                        error,
                                        "L’état de l’équipement n’a pas pu être modifié.",
                                    )
                                    return
                                ui.navigate.to(
                                    character_url(
                                        character["id"],
                                        "equipement",
                                    )
                                )

                            carried_switch.on_value_change(state_changed)
                            equipped_switch.on_value_change(state_changed)

                            if (
                                item_type == "weapon"
                                and not row.get("linked_attacks")
                            ):
                                def create_linked_attack(current=row):
                                    try:
                                        _, created = (
                                            create_attack_from_weapon(
                                                user_id,
                                                character,
                                                current,
                                            )
                                        )
                                    except Exception as error:
                                        notify_error(
                                            error,
                                            "L’attaque liée n’a pas pu être créée.",
                                        )
                                        return
                                    ui.notify(
                                        "Attaque liée créée."
                                        if created
                                        else (
                                            "Cette arme possède déjà "
                                            "une attaque liée."
                                        ),
                                        type="positive",
                                    )
                                    ui.navigate.to(
                                        character_url(
                                            character["id"],
                                            "attaques",
                                        )
                                    )

                                ui.button(
                                    icon="link",
                                    on_click=create_linked_attack,
                                ).props(
                                    "flat round color=primary"
                                ).tooltip("Créer une attaque liée")

                            elif (
                                item_type == "weapon"
                                and row.get("linked_attacks")
                            ):
                                ui.button(
                                    icon="sports_martial_arts",
                                    on_click=lambda: ui.navigate.to(
                                        character_url(
                                            character["id"],
                                            "attaques",
                                        )
                                    ),
                                ).props(
                                    "flat round color=primary"
                                ).tooltip("Voir les attaques liées")

                            ui.button(
                                icon="edit",
                                on_click=lambda current=row:
                                    equipment_dialog(
                                        user_id,
                                        character,
                                        current,
                                    ),
                            ).props("flat round")

                            ui.button(
                                icon="delete",
                                on_click=lambda current=row:
                                    delete_equipment_dialog(
                                        user_id,
                                        character,
                                        current,
                                    ),
                            ).props("flat round color=negative")
