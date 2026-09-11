"""Panneau JDR — Progression du personnage.

Le module ne dépend directement ni de NiceGUI, ni de la base de données,
ni du module principal JDR. Les dépendances sont injectées par la façade.
"""
from __future__ import annotations


def build_progression_panel(
    *,
    ui,
    user_id,
    character,
    list_rpg_skills,
    list_rpg_level_history,
    format_modifier,
    format_number,
    ability_labels,
    ability_long_labels,
    skill_display_name,
    apply_rpg_level_up,
    notify_error,
    character_url,
):
    """Construit le panneau de progression et l'historique des niveaux."""
    next_level = int(character.get("character_level") or 1) + 1
    skills = list_rpg_skills(user_id, character["id"])
    history = list_rpg_level_history(user_id, character["id"])

    with ui.card().classes("w-full p-5"):
        with ui.row().classes("w-full items-start justify-between gap-3 flex-wrap"):
            with ui.column().classes("gap-0"):
                ui.label("Progression du personnage").classes("text-xl font-bold")
                ui.label(
                    "Montez d’un niveau à la fois. L’assistant applique seulement "
                    "les valeurs que vous confirmez et conserve un historique."
                ).classes("text-sm jf-muted")
            ui.button(
                f"Monter au niveau {next_level}",
                icon="trending_up",
                on_click=lambda: open_level_up_dialog(),
            ).props("color=primary").set_enabled(next_level <= 100)

        with ui.element("div").classes("jf-rpg-grid mt-3"):
            for label, value in (
                ("Niveau actuel", character.get("character_level") or 1),
                ("Classe", character.get("class_name") or "—"),
                ("Sous-classe", character.get("subclass_name") or "Aucune"),
                ("BBA", format_modifier(character.get("base_attack_bonus") or 0)),
            ):
                with ui.column().classes("gap-0"):
                    ui.label(label).classes("text-xs jf-muted")
                    ui.label(str(value)).classes("font-bold")

    def open_level_up_dialog():
        if next_level > 100:
            ui.notify("Le niveau maximal de cette feuille est 100.", type="warning")
            return

        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-4xl p-5"):
                ui.label(f"Passage au niveau {next_level}").classes("text-2xl font-bold")
                ui.label(
                    "La sous-classe est facultative. Si elle reste vide, "
                    "aucune étape propre aux sous-classes n’est requise."
                ).classes("text-sm jf-muted")

                with ui.expansion("1. Classe et sous-classe", icon="badge", value=True).props(
                    "expand-separator"
                ).classes("w-full"):
                    with ui.element("div").classes("jf-rpg-grid mt-2"):
                        class_input = ui.input(
                            label="Classe",
                            value=character.get("class_name") or "",
                        ).props("maxlength=120")
                        subclass_input = ui.input(
                            label="Sous-classe facultative",
                            value=character.get("subclass_name") or "",
                        ).props("maxlength=160 clearable")
                    subclass_notes = ui.textarea(
                        label="Choix / capacités propres à la sous-classe",
                        value="",
                    ).props("outlined autogrow maxlength=4000").classes("w-full")

                    def refresh_subclass_notes(_event=None):
                        subclass_notes.set_visibility(
                            bool(str(subclass_input.value or "").strip())
                        )

                    subclass_input.on_value_change(refresh_subclass_notes)
                    refresh_subclass_notes()

                with ui.expansion(
                    "2. Vitalité et progression de base",
                    icon="favorite",
                    value=True,
                ).props("expand-separator").classes("w-full"):
                    with ui.element("div").classes("jf-rpg-grid mt-2"):
                        hp_gain = ui.number(
                            label="PV gagnés",
                            value=0,
                            min=0,
                            max=1000,
                            step=1,
                        ).props("inputmode=numeric")
                        add_current_hp = ui.checkbox(
                            "Ajouter aussi aux PV actuels",
                            value=True,
                        )
                        bab_delta = ui.number(
                            label="BBA gagné",
                            value=0,
                            min=0,
                            max=20,
                            step=1,
                        ).props("inputmode=numeric")
                        fort_delta = ui.number(
                            label="Vigueur de base gagnée",
                            value=0,
                            min=0,
                            max=20,
                            step=1,
                        ).props("inputmode=numeric")
                        reflex_delta = ui.number(
                            label="Réflexes de base gagnés",
                            value=0,
                            min=0,
                            max=20,
                            step=1,
                        ).props("inputmode=numeric")
                        will_delta = ui.number(
                            label="Volonté de base gagnée",
                            value=0,
                            min=0,
                            max=20,
                            step=1,
                        ).props("inputmode=numeric")
                        ability_options = {"": "Aucune"}
                        ability_options.update(
                            {
                                key: ability_long_labels[key]
                                for key in ability_labels
                            }
                        )
                        ability_input = ui.select(
                            ability_options,
                            label="Caractéristique +1 facultative",
                            value="",
                        ).props("options-dense")
                    if next_level % 4 == 0:
                        ui.label(
                            "Rappel Pathfinder : ce niveau est un multiple de 4; "
                            "une augmentation de caractéristique est généralement à vérifier."
                        ).classes("text-sm text-primary font-bold mt-2")

                rank_inputs = {}
                with ui.expansion(
                    "3. Rangs de compétences",
                    icon="psychology",
                ).props("expand-separator").classes("w-full"):
                    ui.label(
                        "Inscrivez uniquement les nouveaux rangs gagnés à ce niveau. "
                        "Les rangs existants sont conservés."
                    ).classes("text-sm jf-muted")
                    for skill in skills:
                        with ui.row().classes(
                            "w-full items-center justify-between gap-3 py-1"
                        ):
                            ui.label(
                                f"{skill_display_name(skill.get('skill_name'), skill.get('english_name'))} "
                                f"— rangs actuels {format_number(skill.get('ranks') or 0)}"
                            ).classes("text-sm grow min-w-0")
                            rank_inputs[int(skill["id"])] = ui.number(
                                label="+ rangs",
                                value=0,
                                min=0,
                                max=100,
                                step=1,
                            ).props("dense inputmode=numeric").classes("w-28")

                with ui.expansion(
                    "4. Choix et notes du niveau",
                    icon="edit_note",
                ).props("expand-separator").classes("w-full"):
                    feat_notes = ui.textarea(
                        label="Dons / choix de don",
                        value="",
                    ).props("outlined autogrow maxlength=4000").classes("w-full")
                    special_notes = ui.textarea(
                        label="Capacités spéciales / pouvoirs de classe",
                        value="",
                    ).props("outlined autogrow maxlength=4000").classes("w-full")
                    general_notes = ui.textarea(
                        label="Autres notes de progression",
                        value="",
                    ).props("outlined autogrow maxlength=4000").classes("w-full")

                def collected_skill_deltas():
                    return {
                        skill_id: int(control.value or 0)
                        for skill_id, control in rank_inputs.items()
                        if int(control.value or 0) > 0
                    }

                def apply_level_now(confirm_dialog):
                    try:
                        result = apply_rpg_level_up(
                            user_id,
                            character["id"],
                            class_name=class_input.value,
                            subclass_name=subclass_input.value,
                            hp_gain=hp_gain.value,
                            increase_current_hp=add_current_hp.value,
                            bab_delta=bab_delta.value,
                            fortitude_delta=fort_delta.value,
                            reflex_delta=reflex_delta.value,
                            will_delta=will_delta.value,
                            ability_key=ability_input.value or None,
                            skill_rank_deltas=collected_skill_deltas(),
                            feat_notes=feat_notes.value,
                            special_ability_notes=special_notes.value,
                            subclass_notes=subclass_notes.value,
                            general_notes=general_notes.value,
                        )
                    except Exception as error:
                        notify_error(
                            error,
                            "La montée de niveau n’a pas pu être appliquée.",
                        )
                        return
                    confirm_dialog.close()
                    dialog.close()
                    ui.notify(
                        f"Niveau {result['to_level']} appliqué et ajouté à l’historique.",
                        type="positive",
                    )
                    ui.navigate.to(
                        character_url(
                            character["id"],
                            "progression",
                        )
                    )

                def preview_level():
                    skill_deltas = collected_skill_deltas()
                    skill_by_id = {
                        int(row["id"]): row
                        for row in skills
                    }
                    with ui.dialog() as confirm_dialog:
                        with ui.card().classes("w-full max-w-2xl p-5"):
                            ui.label(
                                "Prévisualisation de la montée de niveau"
                            ).classes("text-xl font-bold")
                            subclass_value = str(
                                subclass_input.value or ""
                            ).strip()
                            summary_lines = [
                                f"Niveau {character['character_level']} → {next_level}",
                                f"Classe : {str(class_input.value or '').strip() or 'à préciser'}",
                                f"Sous-classe : {subclass_value or 'aucune'}",
                                f"PV : +{int(hp_gain.value or 0)}",
                                f"BBA : +{int(bab_delta.value or 0)}",
                                (
                                    "Sauvegardes de base : "
                                    f"Vigueur +{int(fort_delta.value or 0)}, "
                                    f"Réflexes +{int(reflex_delta.value or 0)}, "
                                    f"Volonté +{int(will_delta.value or 0)}"
                                ),
                            ]
                            if ability_input.value:
                                summary_lines.append(
                                    "Caractéristique : "
                                    f"{ability_long_labels[ability_input.value]} +1"
                                )
                            for line in summary_lines:
                                ui.label(line).classes("text-sm")
                            if skill_deltas:
                                ui.separator().classes("my-2")
                                ui.label("Compétences").classes("font-bold")
                                for skill_id, delta in skill_deltas.items():
                                    row = skill_by_id[skill_id]
                                    ui.label(
                                        f"{skill_display_name(row.get('skill_name'), row.get('english_name'))} "
                                        f": +{delta} rang(s)"
                                    ).classes("text-sm")
                            if not subclass_value:
                                ui.label(
                                    "Aucune sous-classe : les choix de sous-classe seront ignorés."
                                ).classes("text-sm jf-muted mt-2")
                            with ui.row().classes(
                                "w-full justify-end gap-2 mt-3 flex-wrap"
                            ):
                                ui.button(
                                    "Retour",
                                    on_click=confirm_dialog.close,
                                ).props("flat")
                                ui.button(
                                    "Appliquer ce niveau",
                                    icon="check",
                                    on_click=lambda: apply_level_now(
                                        confirm_dialog
                                    ),
                                ).props("color=primary")
                    confirm_dialog.open()

                with ui.row().classes(
                    "w-full justify-end gap-2 mt-4 flex-wrap"
                ):
                    ui.button(
                        "Annuler",
                        on_click=dialog.close,
                    ).props("flat")
                    ui.button(
                        "Prévisualiser",
                        icon="preview",
                        on_click=preview_level,
                    ).props("color=primary")
        dialog.open()

    with ui.card().classes("w-full p-5"):
        ui.label("Historique des niveaux").classes("text-xl font-bold")
        if not history:
            ui.label(
                "Aucune montée de niveau guidée n’a encore été enregistrée."
            ).classes("text-sm jf-muted")
        for row in history:
            with ui.expansion(
                (
                    f"Niveau {row['from_level']} → {row['to_level']} — "
                    f"{row.get('class_name') or 'Classe non précisée'}"
                ),
                icon="history",
            ).props("expand-separator").classes("w-full"):
                if row.get("subclass_name"):
                    ui.label(
                        f"Sous-classe : {row['subclass_name']}"
                    ).classes("text-sm font-bold")
                ui.label(
                    f"PV +{row.get('hp_gain') or 0} · "
                    f"BBA +{row.get('bab_delta') or 0} · "
                    f"Vig +{row.get('fortitude_delta') or 0} · "
                    f"Réf +{row.get('reflex_delta') or 0} · "
                    f"Vol +{row.get('will_delta') or 0}"
                ).classes("text-sm")
                if row.get("ability_key"):
                    ui.label(
                        f"{ability_long_labels.get(row['ability_key'], row['ability_key'])} "
                        f"+{row.get('ability_delta') or 1}"
                    ).classes("text-sm")
                for change in row.get("skill_changes") or []:
                    ui.label(
                        f"{change.get('name')}: +{change.get('added')} rang(s) "
                        f"({change.get('before')} → {change.get('after')})"
                    ).classes("text-sm")
                for label, value in (
                    ("Dons", row.get("feat_notes")),
                    ("Capacités spéciales", row.get("special_ability_notes")),
                    ("Sous-classe", row.get("subclass_notes")),
                    ("Notes", row.get("general_notes")),
                ):
                    if value:
                        ui.label(
                            f"{label} : {value}"
                        ).classes("text-sm jf-muted")
