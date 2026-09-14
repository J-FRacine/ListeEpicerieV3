"""Panneau Dons de la fiche Personnage JDR.

Le module ne dépend directement ni de NiceGUI, ni de la base de données.
Toutes les dépendances sont injectées par la façade.
"""
from __future__ import annotations


def build_feats_panel(
    *,
    ui,
    user_id,
    character,
    list_rpg_feats,
    list_rpg_attacks,
    create_rpg_feat,
    update_rpg_feat,
    delete_rpg_feat,
    feat_kind_labels,
    save_target_labels,
    feat_templates,
    format_modifier,
    notify_error,
    character_url,
):
    feats = list(list_rpg_feats(user_id, character["id"]))
    attacks = list(list_rpg_attacks(user_id, character["id"]))
    attack_options = {
        int(row["id"]): str(row.get("attack_name") or f"Attaque {row['id']}")
        for row in attacks
    }
    linked_options = {None: "Toutes / aucune attaque précise"}
    linked_options.update(attack_options)

    def feat_title(row):
        french = str(row.get("feat_name") or "").strip()
        english = str(row.get("english_name") or "").strip()
        if french and english:
            return f"{french} — {english}"
        return french or english or "Don sans nom"

    def modifier_lines(row):
        lines = []
        if int(row.get("attack_modifier") or 0):
            lines.append(
                "Attaque "
                + format_modifier(row.get("attack_modifier") or 0)
            )
        if int(row.get("initiative_modifier") or 0):
            lines.append(
                "Initiative "
                + format_modifier(row.get("initiative_modifier") or 0)
            )
        if int(row.get("cmb_modifier") or 0):
            lines.append(
                "BMO/CMB "
                + format_modifier(row.get("cmb_modifier") or 0)
            )
        if int(row.get("cmd_modifier") or 0):
            lines.append(
                "DMD/CMD "
                + format_modifier(row.get("cmd_modifier") or 0)
            )
        if int(row.get("save_modifier") or 0):
            save_label = save_target_labels.get(
                row.get("save_key") or "",
                row.get("save_key") or "Sauvegarde",
            )
            lines.append(
                f"{save_label} "
                + format_modifier(row.get("save_modifier") or 0)
            )
        if row.get("damage_note"):
            lines.append(f"Dégâts : {row['damage_note']}")
        return lines

    def open_details(row):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-3xl p-5"):
                with ui.row().classes(
                    "w-full items-start justify-between gap-3"
                ):
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(feat_title(row)).classes(
                            "text-2xl font-bold"
                        )
                        ui.label(
                            feat_kind_labels.get(
                                row.get("feat_kind"),
                                row.get("feat_kind") or "Don",
                            )
                        ).classes("text-sm text-primary font-bold")
                    ui.button(
                        icon="close",
                        on_click=dialog.close,
                    ).props("flat round")

                if row.get("source_text"):
                    ui.label(
                        f"Source : {row['source_text']}"
                    ).classes("text-xs jf-muted")
                if row.get("prerequisites"):
                    ui.label("Prérequis").classes("font-bold mt-2")
                    ui.label(row["prerequisites"]).classes(
                        "text-sm whitespace-pre-wrap"
                    )
                if row.get("summary"):
                    ui.label("Résumé").classes("font-bold mt-2")
                    ui.label(row["summary"]).classes(
                        "text-sm whitespace-pre-wrap"
                    )
                if row.get("effects"):
                    ui.label("Effets").classes("font-bold mt-2")
                    ui.label(row["effects"]).classes(
                        "text-sm whitespace-pre-wrap"
                    )

                mods = modifier_lines(row)
                if mods:
                    ui.label("Combat rapide").classes("font-bold mt-2")
                    for line in mods:
                        ui.label(line).classes("text-sm")
                    if row.get("linked_attack_name"):
                        ui.label(
                            "Attaque liée : "
                            + str(row["linked_attack_name"])
                        ).classes("text-xs jf-muted")

                if row.get("notes"):
                    ui.label("Notes").classes("font-bold mt-2")
                    ui.label(row["notes"]).classes(
                        "text-sm whitespace-pre-wrap"
                    )

                with ui.row().classes("w-full justify-end mt-3"):
                    ui.button(
                        "Fermer",
                        on_click=dialog.close,
                    ).props("outline")
        dialog.open()

    def open_editor(row=None):
        editing = row is not None
        row = dict(row or {})

        with ui.dialog() as dialog:
            with ui.card().classes(
                "w-full max-w-4xl p-5 max-h-[92vh] overflow-auto"
            ):
                ui.label(
                    "Modifier le don" if editing else "Ajouter un don"
                ).classes("text-2xl font-bold")

                template_select = ui.select(
                    {
                        key: value["label"]
                        for key, value in feat_templates.items()
                    },
                    label="Modèle facultatif",
                    value="",
                ).props("options-dense").classes("w-full")

                with ui.element("div").classes("jf-rpg-grid mt-2"):
                    name_input = ui.input(
                        label="Nom français",
                        value=row.get("feat_name") or "",
                    ).props("maxlength=160").classes("w-full")
                    english_input = ui.input(
                        label="Nom anglais",
                        value=row.get("english_name") or "",
                    ).props("maxlength=160").classes("w-full")
                    kind_input = ui.select(
                        feat_kind_labels,
                        label="Type",
                        value=row.get("feat_kind") or "info",
                    ).props("options-dense").classes("w-full")
                    source_input = ui.input(
                        label="Source / référence",
                        value=row.get("source_text") or "",
                    ).props("maxlength=300").classes("w-full")
                    attack_link_input = ui.select(
                        linked_options,
                        label="Attaque liée",
                        value=row.get("linked_attack_id"),
                    ).props(
                        "clearable options-dense"
                    ).classes("w-full")

                prereq_input = ui.textarea(
                    label="Prérequis",
                    value=row.get("prerequisites") or "",
                ).props(
                    "outlined autogrow maxlength=2000"
                ).classes("w-full")
                summary_input = ui.textarea(
                    label="Résumé",
                    value=row.get("summary") or "",
                ).props(
                    "outlined autogrow maxlength=4000"
                ).classes("w-full")
                effects_input = ui.textarea(
                    label="Effets détaillés",
                    value=row.get("effects") or "",
                ).props(
                    "outlined autogrow maxlength=6000"
                ).classes("w-full")

                with ui.expansion(
                    "Modificateurs pour Combat rapide",
                    icon="sports_martial_arts",
                    value=True,
                ).props("expand-separator").classes("w-full"):
                    ui.label(
                        "Les dons passifs sont appliqués automatiquement dans "
                        "Combat rapide. Les dons activables ne le sont que si "
                        "vous cochez « Utiliser » pendant le combat. Ces valeurs "
                        "ne réécrivent pas la fiche permanente."
                    ).classes("text-sm jf-muted")

                    with ui.element("div").classes("jf-rpg-grid mt-2"):
                        attack_mod_input = ui.number(
                            label="Attaque",
                            value=row.get("attack_modifier") or 0,
                            min=-100,
                            max=100,
                            step=1,
                        )
                        initiative_mod_input = ui.number(
                            label="Initiative",
                            value=row.get("initiative_modifier") or 0,
                            min=-100,
                            max=100,
                            step=1,
                        )
                        cmb_mod_input = ui.number(
                            label="BMO / CMB",
                            value=row.get("cmb_modifier") or 0,
                            min=-100,
                            max=100,
                            step=1,
                        )
                        cmd_mod_input = ui.number(
                            label="DMD / CMD",
                            value=row.get("cmd_modifier") or 0,
                            min=-100,
                            max=100,
                            step=1,
                        )
                        save_key_input = ui.select(
                            save_target_labels,
                            label="Jet ciblé",
                            value=row.get("save_key") or "",
                        ).props("options-dense")
                        save_mod_input = ui.number(
                            label="Bonus/malus sauvegarde",
                            value=row.get("save_modifier") or 0,
                            min=-100,
                            max=100,
                            step=1,
                        )

                    damage_note_input = ui.input(
                        label="Effet sur les dégâts (texte)",
                        value=row.get("damage_note") or "",
                        placeholder=(
                            "Ex. +4 dégâts à deux mains; ou effet à vérifier"
                        ),
                    ).props("maxlength=1000").classes("w-full")

                notes_input = ui.textarea(
                    label="Notes personnelles",
                    value=row.get("notes") or "",
                ).props(
                    "outlined autogrow maxlength=4000"
                ).classes("w-full")

                def apply_template(_event=None):
                    key = str(template_select.value or "")
                    template = feat_templates.get(key) or {}
                    if not key:
                        return

                    controls = (
                        (name_input, template.get("feat_name") or ""),
                        (english_input, template.get("english_name") or ""),
                        (kind_input, template.get("feat_kind") or "info"),
                        (source_input, template.get("source_text") or ""),
                        (prereq_input, template.get("prerequisites") or ""),
                        (summary_input, template.get("summary") or ""),
                        (effects_input, template.get("effects") or ""),
                        (
                            attack_mod_input,
                            template.get("attack_modifier") or 0,
                        ),
                        (
                            initiative_mod_input,
                            template.get("initiative_modifier") or 0,
                        ),
                        (cmb_mod_input, template.get("cmb_modifier") or 0),
                        (cmd_mod_input, template.get("cmd_modifier") or 0),
                        (save_key_input, template.get("save_key") or ""),
                        (
                            save_mod_input,
                            template.get("save_modifier") or 0,
                        ),
                        (
                            damage_note_input,
                            template.get("damage_note") or "",
                        ),
                    )
                    for control, value in controls:
                        control.value = value
                        control.update()

                template_select.on_value_change(apply_template)

                def save():
                    values = {
                        "feat_name": name_input.value,
                        "english_name": english_input.value,
                        "feat_kind": kind_input.value,
                        "catalog_key": (
                            template_select.value
                            if template_select.value
                            else row.get("catalog_key")
                        ),
                        "source_text": source_input.value,
                        "prerequisites": prereq_input.value,
                        "summary": summary_input.value,
                        "effects": effects_input.value,
                        "notes": notes_input.value,
                        "linked_attack_id": attack_link_input.value,
                        "attack_modifier": attack_mod_input.value,
                        "damage_note": damage_note_input.value,
                        "initiative_modifier": initiative_mod_input.value,
                        "cmb_modifier": cmb_mod_input.value,
                        "cmd_modifier": cmd_mod_input.value,
                        "save_key": save_key_input.value,
                        "save_modifier": save_mod_input.value,
                        "sort_order": row.get("sort_order") or 0,
                    }
                    try:
                        if editing:
                            update_rpg_feat(
                                user_id,
                                character["id"],
                                row["id"],
                                values,
                            )
                        else:
                            create_rpg_feat(
                                user_id,
                                character["id"],
                                values,
                            )
                    except Exception as error:
                        notify_error(
                            error,
                            "Le don n’a pas pu être enregistré.",
                        )
                        return

                    dialog.close()
                    ui.notify(
                        "Don modifié." if editing else "Don ajouté.",
                        type="positive",
                    )
                    ui.navigate.to(
                        character_url(character["id"], "dons")
                    )

                with ui.row().classes(
                    "w-full justify-end gap-2 mt-3 flex-wrap"
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
        "w-full items-start justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Dons").classes("text-xl font-bold")
            ui.label(
                "Conservez les prérequis, effets et modificateurs de chaque "
                "don. Les dons activables peuvent ensuite être cochés dans "
                "Combat rapide."
            ).classes("text-sm jf-muted")
        ui.button(
            "Ajouter un don",
            icon="add",
            on_click=lambda: open_editor(),
        ).props("color=primary")

    if not feats:
        with ui.card().classes(
            "w-full p-7 items-center text-center mt-3"
        ):
            ui.icon("military_tech").classes(
                "text-6xl text-gray-400"
            )
            ui.label("Aucun don structuré").classes(
                "text-xl font-bold"
            )
            ui.label(
                "Ajoutez vos dons actuels. Les anciennes notes de Progression "
                "restent conservées et ne sont pas supprimées."
            ).classes("text-sm jf-muted max-w-xl")
            ui.button(
                "Ajouter mon premier don",
                icon="add",
                on_click=lambda: open_editor(),
            ).props("outline color=primary")
        return

    grouped = [
        ("active", "Activables"),
        ("passive", "Passifs"),
        ("info", "Informatifs"),
    ]

    for kind, heading in grouped:
        rows = [
            row
            for row in feats
            if (row.get("feat_kind") or "info") == kind
        ]
        if not rows:
            continue

        ui.label(heading).classes("text-lg font-bold mt-3")
        with ui.element("div").classes("jf-rpg-grid"):
            for row in rows:
                with ui.card().classes("w-full p-4"):
                    with ui.row().classes(
                        "w-full items-start justify-between gap-2"
                    ):
                        with ui.column().classes("gap-0 grow min-w-0"):
                            ui.label(feat_title(row)).classes(
                                "font-bold text-lg"
                            )
                            ui.label(
                                feat_kind_labels.get(kind, kind)
                            ).classes("text-xs text-primary font-bold")
                        with ui.row().classes("gap-0"):
                            ui.button(
                                icon="visibility",
                                on_click=lambda selected=row: open_details(
                                    selected
                                ),
                            ).props(
                                "flat round color=primary"
                            ).tooltip("Voir les détails")
                            ui.button(
                                icon="edit",
                                on_click=lambda selected=row: open_editor(
                                    selected
                                ),
                            ).props(
                                "flat round color=primary"
                            ).tooltip("Modifier")

                            def remove(selected=row):
                                try:
                                    delete_rpg_feat(
                                        user_id,
                                        character["id"],
                                        selected["id"],
                                    )
                                except Exception as error:
                                    notify_error(
                                        error,
                                        "Le don n’a pas pu être supprimé.",
                                    )
                                    return
                                ui.notify(
                                    "Don supprimé.",
                                    type="positive",
                                )
                                ui.navigate.to(
                                    character_url(
                                        character["id"],
                                        "dons",
                                    )
                                )

                            ui.button(
                                icon="delete",
                                on_click=remove,
                            ).props(
                                "flat round color=negative"
                            ).tooltip("Supprimer")

                    if row.get("summary"):
                        ui.label(row["summary"]).classes(
                            "text-sm mt-2"
                        )

                    mods = modifier_lines(row)
                    if mods:
                        ui.label(
                            " · ".join(mods)
                        ).classes("text-xs jf-muted mt-2")

                    if row.get("linked_attack_name"):
                        ui.label(
                            "Lié à : "
                            + str(row["linked_attack_name"])
                        ).classes("text-xs jf-muted")
