"""Panneau JDR — Attaques."""
from __future__ import annotations


def build_attacks_panel(
    *,
    ui,
    user_id,
    character,
    ability_labels,
    attack_total,
    format_modifier,
    list_rpg_attacks,
    list_rpg_equipment,
    weapon_handedness_labels,
    attack_grip_labels,
    create_rpg_attack,
    update_rpg_attack,
    delete_rpg_attack,
    notify_error,
    character_url,
):
    equipment = list(
        list_rpg_equipment(user_id, character["id"])
    )
    weapons = [
        row for row in equipment
        if row.get("item_type") == "weapon"
    ]
    weapon_by_id = {
        int(row["id"]): row for row in weapons
    }
    weapon_options = {
        None: "Aucune arme physique liée",
        **{
            int(row["id"]): str(
                row.get("item_name")
                or f"Arme {row['id']}"
            )
            for row in weapons
        },
    }

    def attack_dialog(attack=None):
        editing = attack is not None
        attack = dict(attack or {})

        with ui.dialog() as dialog:
            with ui.card().classes(
                "w-full max-w-3xl p-5 "
                "max-h-[92vh] overflow-auto"
            ):
                ui.label(
                    "Modifier l’attaque"
                    if editing
                    else "Ajouter une attaque"
                ).classes("text-xl font-bold")

                linked_weapon_input = ui.select(
                    weapon_options,
                    label="Arme physique liée (Équipement)",
                    value=attack.get("linked_equipment_id"),
                ).props(
                    "clearable options-dense"
                ).classes("w-full")

                grip_input = ui.select(
                    attack_grip_labels,
                    label="Prise pour cette attaque",
                    value=attack.get("grip_mode") or "default",
                ).props("options-dense").classes("w-full")

                link_info = ui.label("").classes(
                    "text-sm jf-muted"
                )

                with ui.element("div").classes(
                    "jf-rpg-grid mt-2"
                ):
                    name_input = ui.input(
                        label="Nom de l’attaque",
                        value=attack.get("attack_name") or "",
                    ).props(
                        "autofocus maxlength=120"
                    ).classes("w-full")

                    ability_input = ui.select(
                        ability_labels,
                        label="Caractéristique",
                        value=attack.get("ability_key") or "str",
                    ).classes("w-full")

                    magic_input = ui.number(
                        label="Bonus magique manuel",
                        value=attack.get(
                            "manual_magic_bonus",
                            attack.get("magic_bonus", 0),
                        ),
                        step=1,
                    ).classes("w-full")

                    misc_input = ui.number(
                        label="Bonus divers",
                        value=attack.get("misc_bonus") or 0,
                        step=1,
                    ).classes("w-full")

                    damage_input = ui.input(
                        label="Dégâts de cette attaque",
                        value=(
                            attack.get(
                                "stored_damage",
                                attack.get("damage"),
                            )
                            or ""
                        ),
                        placeholder=(
                            "Ex. 1d8+3; vide = reprendre l’arme liée"
                        ),
                    ).props("maxlength=120").classes("w-full")

                    critical_input = ui.input(
                        label="Critique",
                        value=(
                            attack.get(
                                "stored_critical",
                                attack.get("critical"),
                            )
                            or ""
                        ),
                        placeholder="Vide = reprendre l’arme liée",
                    ).props("maxlength=80").classes("w-full")

                    range_input = ui.input(
                        label="Portée",
                        value=(
                            attack.get(
                                "stored_attack_range",
                                attack.get("attack_range"),
                            )
                            or ""
                        ),
                        placeholder="Vide = reprendre l’arme liée",
                    ).props("maxlength=80").classes("w-full")

                    type_input = ui.input(
                        label="Type",
                        value=(
                            attack.get(
                                "stored_attack_type",
                                attack.get("attack_type"),
                            )
                            or ""
                        ),
                        placeholder="Vide = reprendre l’arme liée",
                    ).props("maxlength=80").classes("w-full")

                    ammo_current_input = ui.number(
                        label="Munitions actuelles (attaque non liée)",
                        value=attack.get(
                            "stored_ammunition_current",
                            attack.get("ammunition_current"),
                        ),
                        min=0,
                        step=1,
                    ).props("clearable").classes("w-full")

                    ammo_max_input = ui.number(
                        label="Munitions maximums (attaque non liée)",
                        value=attack.get(
                            "stored_ammunition_max",
                            attack.get("ammunition_max"),
                        ),
                        min=0,
                        step=1,
                    ).props("clearable").classes("w-full")

                notes_input = ui.textarea(
                    label="Notes",
                    value=attack.get("notes") or "",
                ).props(
                    "maxlength=1000 autogrow"
                ).classes("w-full")

                total_label = ui.label("").classes(
                    "jf-rpg-stat-value"
                )

                def selected_weapon():
                    try:
                        return weapon_by_id.get(
                            int(linked_weapon_input.value)
                        )
                    except (TypeError, ValueError):
                        return None

                def refresh_link_info(_event=None):
                    weapon = selected_weapon()
                    linked = weapon is not None
                    magic_input.set_visibility(not linked)
                    ammo_current_input.set_visibility(not linked)
                    ammo_max_input.set_visibility(not linked)
                    if not weapon:
                        link_info.set_text(
                            "Sans lien, les valeurs de l’attaque "
                            "restent entièrement indépendantes."
                        )
                        return
                    bonus = int(
                        weapon.get("weapon_attack_bonus") or 0
                    )
                    link_info.set_text(
                        " · ".join([
                            "Arme : "
                            + str(weapon.get("item_name") or "—"),
                            "bonus d’arme "
                            + format_modifier(bonus),
                            "dégâts de base "
                            + str(
                                weapon.get("weapon_damage") or "—"
                            ),
                            "critique "
                            + str(
                                weapon.get("weapon_critical") or "—"
                            ),
                            weapon_handedness_labels.get(
                                weapon.get("weapon_handedness"),
                                str(
                                    weapon.get("weapon_handedness")
                                    or "—"
                                ),
                            ),
                        ])
                    )

                def copy_weapon_values():
                    weapon = selected_weapon()
                    if not weapon:
                        ui.notify(
                            "Choisissez d’abord une arme liée.",
                            type="warning",
                        )
                        return
                    for control, value in (
                        (name_input, weapon.get("item_name") or ""),
                        (
                            damage_input,
                            weapon.get("weapon_damage") or "",
                        ),
                        (
                            critical_input,
                            weapon.get("weapon_critical") or "",
                        ),
                        (
                            range_input,
                            weapon.get("weapon_range") or "",
                        ),
                        (
                            type_input,
                            weapon.get("weapon_damage_type") or "",
                        ),
                    ):
                        control.value = value
                        control.update()
                    ui.notify(
                        "Valeurs de base reprises depuis l’Équipement. "
                        "Ajustez les dégâts selon la Force, les dons "
                        "et les autres effets du personnage.",
                        type="positive",
                    )
                    refresh_total()

                ui.button(
                    "Reprendre les valeurs de l’arme",
                    icon="sync",
                    on_click=copy_weapon_values,
                ).props("outline color=primary")

                def refresh_total(_event=None):
                    weapon = selected_weapon()
                    effective_magic = (
                        weapon.get("weapon_attack_bonus")
                        if weapon
                        else magic_input.value
                    )
                    draft = {
                        "ability_key": ability_input.value,
                        "magic_bonus": effective_magic,
                        "misc_bonus": misc_input.value,
                    }
                    total_label.set_text(
                        "Bonus total : "
                        + format_modifier(
                            attack_total(character, draft)
                        )
                    )

                for control in (
                    ability_input,
                    magic_input,
                    misc_input,
                    linked_weapon_input,
                ):
                    control.on_value_change(refresh_total)

                linked_weapon_input.on_value_change(
                    refresh_link_info
                )
                refresh_link_info()
                refresh_total()

                def save():
                    values = {
                        "attack_name": name_input.value,
                        "ability_key": ability_input.value,
                        "magic_bonus": magic_input.value,
                        "misc_bonus": misc_input.value,
                        "damage": damage_input.value,
                        "critical": critical_input.value,
                        "attack_range": range_input.value,
                        "attack_type": type_input.value,
                        "notes": notes_input.value,
                        "ammunition_current":
                            ammo_current_input.value,
                        "ammunition_max": ammo_max_input.value,
                        "linked_equipment_id":
                            linked_weapon_input.value,
                        "grip_mode": grip_input.value,
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
                        notify_error(
                            error,
                            "L’attaque n’a pas pu être enregistrée.",
                        )
                        return

                    dialog.close()
                    ui.notify(
                        "Attaque modifiée."
                        if editing
                        else "Attaque ajoutée.",
                        type="positive",
                    )
                    ui.navigate.to(
                        character_url(
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
                    ).props("flat")
                    ui.button(
                        "Enregistrer",
                        icon="save",
                        on_click=save,
                    ).props("color=primary")
        dialog.open()

    with ui.row().classes(
        "w-full items-center justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Attaques").classes("text-xl font-bold")
            ui.label(
                "Une attaque peut être indépendante ou liée à une "
                "arme physique de l’Équipement. Le lien reprend "
                "automatiquement le bonus propre à l’arme."
            ).classes("text-sm jf-muted")

        ui.button(
            "Ajouter une attaque",
            icon="add",
            on_click=lambda: attack_dialog(),
        ).props("color=primary")

    attacks = list_rpg_attacks(user_id, character["id"])

    if not attacks:
        with ui.card().classes(
            "w-full p-6 items-center text-center"
        ):
            ui.icon("sports_martial_arts").classes(
                "text-5xl text-gray-400"
            )
            ui.label("Aucune attaque enregistrée").classes(
                "text-lg font-bold"
            )
            ui.label(
                "Ajoutez une attaque ici ou créez-la directement "
                "depuis une arme de l’onglet Équipement."
            ).classes("text-sm jf-muted")
        return

    with ui.element("div").classes("jf-rpg-grid"):
        for attack in attacks:
            with ui.element("div").classes(
                "jf-rpg-attack-card"
            ):
                with ui.row().classes(
                    "w-full items-start justify-between gap-2"
                ):
                    with ui.column().classes(
                        "gap-0 grow min-w-0"
                    ):
                        ui.label(
                            attack["attack_name"]
                        ).classes("font-bold text-lg")
                        ui.label(
                            "Bonus total "
                            + format_modifier(
                                attack_total(character, attack)
                            )
                        ).classes("text-primary font-bold")

                        if attack.get("linked_equipment_name"):
                            ui.label(
                                "Équipement lié : "
                                + str(
                                    attack["linked_equipment_name"]
                                )
                            ).classes(
                                "text-xs text-primary font-bold"
                            )

                    with ui.row().classes("gap-0"):
                        ui.button(
                            icon="edit",
                            on_click=(
                                lambda selected=attack:
                                attack_dialog(selected)
                            ),
                        ).props(
                            "flat round color=primary"
                        ).tooltip("Modifier")

                        def remove_attack(selected=attack):
                            try:
                                delete_rpg_attack(
                                    user_id,
                                    character["id"],
                                    selected["id"],
                                )
                            except Exception as error:
                                notify_error(
                                    error,
                                    "L’attaque n’a pas pu être supprimée.",
                                )
                                return
                            ui.notify(
                                "Attaque supprimée.",
                                type="positive",
                            )
                            ui.navigate.to(
                                character_url(
                                    character["id"],
                                    "attaques",
                                )
                            )

                        ui.button(
                            icon="delete",
                            on_click=remove_attack,
                        ).props(
                            "flat round color=negative"
                        ).tooltip("Supprimer")

                with ui.element("div").classes(
                    "jf-rpg-grid mt-2"
                ):
                    values = (
                        (
                            "Caractéristique",
                            ability_labels[
                                attack["ability_key"]
                            ],
                        ),
                        ("Dégâts", attack.get("damage") or "—"),
                        (
                            "Critique",
                            attack.get("critical") or "—",
                        ),
                        (
                            "Portée",
                            attack.get("attack_range") or "—",
                        ),
                        (
                            "Type",
                            attack.get("attack_type") or "—",
                        ),
                        (
                            "Prise",
                            attack_grip_labels.get(
                                attack.get("grip_mode")
                                or "default",
                                "—",
                            ),
                        ),
                    )
                    for label, value in values:
                        with ui.column().classes("gap-0"):
                            ui.label(label).classes(
                                "text-xs jf-muted"
                            )
                            ui.label(str(value)).classes(
                                "text-sm font-bold"
                            )

                if (
                    attack.get("ammunition_current") is not None
                    or attack.get("ammunition_max") is not None
                ):
                    ui.label(
                        "Munitions : "
                        f"{attack.get('ammunition_current') or 0}"
                        " / "
                        f"{attack.get('ammunition_max') or 0}"
                    ).classes("text-sm mt-2")

                if attack.get("weapon_damage_bonus"):
                    ui.label(
                        "Bonus magique aux dégâts de l’arme : "
                        + format_modifier(
                            attack["weapon_damage_bonus"]
                        )
                        + " — à intégrer dans la formule de dégâts "
                        "si elle n’y est pas déjà."
                    ).classes("text-xs jf-muted mt-1")

                if attack.get("notes"):
                    ui.separator().classes("my-2")
                    ui.label(attack["notes"]).classes(
                        "text-sm jf-muted"
                    )
