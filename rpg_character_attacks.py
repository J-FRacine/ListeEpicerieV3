"""Panneau JDR — Attaques.

Ce module ne dépend directement ni de NiceGUI, ni de la base de données,
ni du module principal JDR. Toutes ses dépendances sont injectées.
"""
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
    create_rpg_attack,
    update_rpg_attack,
    delete_rpg_attack,
    notify_error,
    character_url,
):
    """Construit le panneau Attaques et son dialogue d'ajout/modification."""

    def attack_dialog(attack=None):
        editing = attack is not None

        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-2xl p-5"):
                ui.label(
                    "Modifier l’attaque" if editing else "Ajouter une attaque"
                ).classes("text-xl font-bold")

                with ui.element("div").classes("jf-rpg-grid"):
                    name_input = ui.input(
                        label="Nom de l’attaque",
                        value=attack["attack_name"] if editing else "",
                    ).props("autofocus maxlength=120").classes("w-full")

                    ability_input = ui.select(
                        ability_labels,
                        label="Caractéristique",
                        value=attack["ability_key"] if editing else "str",
                    ).classes("w-full")

                    magic_input = ui.number(
                        label="Bonus magique",
                        value=attack["magic_bonus"] if editing else 0,
                        step=1,
                    ).classes("w-full")

                    misc_input = ui.number(
                        label="Bonus divers",
                        value=attack["misc_bonus"] if editing else 0,
                        step=1,
                    ).classes("w-full")

                    damage_input = ui.input(
                        label="Dégâts",
                        value=(attack["damage"] or "") if editing else "",
                        placeholder="Ex. 1d8+3",
                    ).props("maxlength=120").classes("w-full")

                    critical_input = ui.input(
                        label="Critique",
                        value=(attack["critical"] or "") if editing else "",
                        placeholder="Ex. 19-20/x2",
                    ).props("maxlength=80").classes("w-full")

                    range_input = ui.input(
                        label="Portée",
                        value=(attack["attack_range"] or "") if editing else "",
                    ).props("maxlength=80").classes("w-full")

                    type_input = ui.input(
                        label="Type",
                        value=(attack["attack_type"] or "") if editing else "",
                        placeholder="Ex. tranchant",
                    ).props("maxlength=80").classes("w-full")

                    ammo_current_input = ui.number(
                        label="Munitions actuelles",
                        value=attack["ammunition_current"] if editing else None,
                        min=0,
                        step=1,
                    ).props("clearable").classes("w-full")

                    ammo_max_input = ui.number(
                        label="Munitions maximums",
                        value=attack["ammunition_max"] if editing else None,
                        min=0,
                        step=1,
                    ).props("clearable").classes("w-full")

                notes_input = ui.textarea(
                    label="Notes",
                    value=(attack["notes"] or "") if editing else "",
                ).props("maxlength=1000 autogrow").classes("w-full")

                total_label = ui.label("").classes("jf-rpg-stat-value")

                def refresh_total(event=None):
                    draft = {
                        "ability_key": ability_input.value,
                        "magic_bonus": magic_input.value,
                        "misc_bonus": misc_input.value,
                    }
                    total_label.set_text(
                        "Bonus total : "
                        + format_modifier(attack_total(character, draft))
                    )

                for control in (ability_input, magic_input, misc_input):
                    control.on_value_change(refresh_total)

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
                        "ammunition_current": ammo_current_input.value,
                        "ammunition_max": ammo_max_input.value,
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
                        "Attaque modifiée." if editing else "Attaque ajoutée.",
                        type="positive",
                    )
                    ui.navigate.to(
                        character_url(character["id"], "attaques")
                    )

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
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
                "Le bonus total combine le bonus de base, "
                "la caractéristique, la taille, la magie "
                "et les modificateurs divers."
            ).classes("text-sm jf-muted")

        ui.button(
            "Ajouter une attaque",
            icon="add",
            on_click=lambda: attack_dialog(),
        ).props("color=primary")

    attacks = list_rpg_attacks(user_id, character["id"])

    if not attacks:
        with ui.card().classes("w-full p-6 items-center text-center"):
            ui.icon("sports_martial_arts").classes(
                "text-5xl text-gray-400"
            )
            ui.label("Aucune attaque enregistrée").classes(
                "text-lg font-bold"
            )
            ui.label(
                "Ajoutez une arme, une attaque naturelle "
                "ou une attaque à distance."
            ).classes("text-sm jf-muted")
        return

    with ui.element("div").classes("jf-rpg-grid"):
        for attack in attacks:
            with ui.element("div").classes("jf-rpg-attack-card"):
                with ui.row().classes(
                    "w-full items-start justify-between gap-2"
                ):
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(attack["attack_name"]).classes(
                            "font-bold text-lg"
                        )
                        ui.label(
                            "Bonus total "
                            f"{format_modifier(attack_total(character, attack))}"
                        ).classes("text-primary font-bold")

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
                                character_url(character["id"], "attaques")
                            )

                        ui.button(
                            icon="delete",
                            on_click=remove_attack,
                        ).props(
                            "flat round color=negative"
                        ).tooltip("Supprimer")

                with ui.element("div").classes("jf-rpg-grid mt-2"):
                    for label, value in (
                        ("Caractéristique", ability_labels[attack["ability_key"]]),
                        ("Dégâts", attack["damage"] or "—"),
                        ("Critique", attack["critical"] or "—"),
                        ("Portée", attack["attack_range"] or "—"),
                        ("Type", attack["attack_type"] or "—"),
                    ):
                        with ui.column().classes("gap-0"):
                            ui.label(label).classes("text-xs jf-muted")
                            ui.label(str(value)).classes(
                                "text-sm font-bold"
                            )

                if (
                    attack["ammunition_current"] is not None
                    or attack["ammunition_max"] is not None
                ):
                    ui.label(
                        "Munitions : "
                        f"{attack['ammunition_current'] or 0}"
                        " / "
                        f"{attack['ammunition_max'] or 0}"
                    ).classes("text-sm mt-2")

                if attack["notes"]:
                    ui.separator().classes("my-2")
                    ui.label(attack["notes"]).classes("text-sm jf-muted")
