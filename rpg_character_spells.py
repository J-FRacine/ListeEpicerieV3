"""Panneau Sorts — préparation du Clerc, Phase 15A."""
from __future__ import annotations


def build_spells_panel(
    *,
    ui,
    user_id,
    character,
    get_rpg_faith,
    get_spellcasting_profile,
    save_spellcasting_profile,
    list_prepared_spells,
    save_prepared_spell,
    delete_prepared_spell,
    set_prepared_spell_used_count,
    reset_spell_usage,
    catalog_by_key,
    domain_spell_rows,
    cleric_slot_table,
    effective_ability_score,
    ability_modifier_from_score,
    prepared_usage_summary,
    ability_labels,
    ability_long_labels,
    format_modifier,
    notify_error,
):
    """Construit le panneau de préparation et de suivi des sorts."""

    def domains_from_faith():
        try:
            faith = dict(get_rpg_faith(user_id, character["id"]))
        except Exception:
            return []
        return [
            value
            for value in (faith.get("domain_1"), faith.get("domain_2"))
            if str(value or "").strip()
        ]

    def level_label(level):
        return "Oraisons (niveau 0)" if int(level) == 0 else f"Sorts de niveau {level}"

    def open_profile_dialog(profile):
        profile = dict(profile or {})
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-3xl p-5"):
                ui.label("Configuration des sorts").classes("text-2xl font-bold")
                ui.label(
                    "Le niveau de Clerc détermine les emplacements. Le niveau de "
                    "lanceur sert de référence pour les effets; ils peuvent différer "
                    "si la campagne ou une classe de prestige le demande."
                ).classes("text-sm jf-muted")

                with ui.element("div").classes("jf-rpg-grid mt-3"):
                    class_level = ui.number(
                        label="Niveau de Clerc — emplacements",
                        value=profile.get("class_level") or character.get("character_level") or 1,
                        min=1,
                        max=20,
                        step=1,
                    ).props("inputmode=numeric")
                    caster_level = ui.number(
                        label="Niveau de lanceur — effets",
                        value=profile.get("caster_level") or profile.get("class_level") or character.get("character_level") or 1,
                        min=1,
                        max=100,
                        step=1,
                    ).props("inputmode=numeric")
                    ability_key = ui.select(
                        ability_labels,
                        label="Caractéristique de lancement",
                        value=profile.get("ability_key") or "wis",
                    ).props("options-dense")
                    spontaneous_mode = ui.select(
                        {
                            "cure": "Conversion spontanée — soins (Cure)",
                            "inflict": "Conversion spontanée — blessures (Inflict)",
                            "none": "Aucune conversion suivie",
                        },
                        label="Conversion spontanée",
                        value=profile.get("spontaneous_mode") or "cure",
                    ).props("options-dense")

                notes = ui.textarea(
                    label="Notes de préparation / heure de prière",
                    value=profile.get("preparation_notes") or "",
                    placeholder="Ex. prière à l’aube; restrictions ou décisions du MJ…",
                ).props("outlined autogrow maxlength=5000").classes("w-full")

                def save_profile():
                    try:
                        save_spellcasting_profile(
                            user_id,
                            character["id"],
                            {
                                "class_key": "cleric",
                                "class_level": class_level.value,
                                "caster_level": caster_level.value,
                                "ability_key": ability_key.value,
                                "spontaneous_mode": spontaneous_mode.value,
                                "preparation_notes": notes.value,
                            },
                        )
                    except Exception as error:
                        notify_error(error, "La configuration des sorts n’a pas pu être enregistrée.")
                        return
                    dialog.close()
                    render_spells.refresh()
                    ui.notify("Configuration des sorts enregistrée.", type="positive")

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button("Enregistrer", icon="save", on_click=save_profile).props("color=primary")
        dialog.open()

    def open_preparation_dialog(profile, row=None):
        editing = row is not None
        row = dict(row or {})
        score = effective_ability_score(character, profile.get("ability_key") or "wis")
        slots = cleric_slot_table(profile.get("class_level") or 1, score)
        maximum = max(int(item["spell_level"]) for item in slots)
        domains = domains_from_faith()
        catalog = catalog_by_key(max_spell_level=maximum, domains=domains)

        catalog_options = {"": "Sort personnalisé"}
        for key, spell in catalog.items():
            suffix = " — domaine " + str(spell.get("domain_source")) if spell.get("slot_kind") == "domain" else ""
            catalog_options[key] = f"Niv. {spell['spell_level']} — {spell['name']}{suffix}"

        domain_options = {"": "Aucun / à préciser"}
        for domain in domains:
            domain_options[str(domain)] = str(domain)

        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-4xl p-5 max-h-[92vh] overflow-auto"):
                ui.label("Modifier le sort préparé" if editing else "Préparer un sort").classes("text-2xl font-bold")
                ui.label(
                    "Choisissez un sort du catalogue ou saisissez un sort personnalisé. "
                    "Les limites d’emplacements sont vérifiées à l’enregistrement."
                ).classes("text-sm jf-muted")

                catalog_input = ui.select(
                    catalog_options,
                    label="Catalogue",
                    value=(row.get("catalog_key") if row.get("catalog_key") in catalog_options else ""),
                ).props("options-dense use-input").classes("w-full")

                with ui.element("div").classes("jf-rpg-grid mt-2"):
                    name_input = ui.input(
                        label="Nom du sort",
                        value=row.get("spell_name") or "",
                    ).props("maxlength=200").classes("w-full")
                    level_input = ui.number(
                        label="Niveau du sort",
                        value=row.get("spell_level") if row.get("spell_level") is not None else 0,
                        min=0,
                        max=maximum,
                        step=1,
                    ).props("inputmode=numeric")
                    slot_kind_input = ui.select(
                        {"normal": "Emplacement normal", "domain": "Emplacement de domaine"},
                        label="Type d’emplacement",
                        value=row.get("slot_kind") or "normal",
                    ).props("options-dense")
                    domain_input = ui.select(
                        domain_options,
                        label="Domaine",
                        value=(row.get("domain_source") or "") if (row.get("domain_source") or "") in domain_options else "",
                    ).props("options-dense clearable")
                    prepared_count = ui.number(
                        label="Nombre préparé",
                        value=row.get("prepared_count") or 1,
                        min=1,
                        max=100,
                        step=1,
                    ).props("inputmode=numeric")
                    school_input = ui.input(
                        label="École",
                        value=row.get("school") or "",
                    ).props("maxlength=160")
                    range_input = ui.input(
                        label="Portée / cible — référence",
                        value=row.get("range_text") or "",
                    ).props("maxlength=300")
                    source_input = ui.input(
                        label="Source",
                        value=row.get("source_text") or "",
                    ).props("maxlength=500")

                summary_input = ui.textarea(
                    label="Résumé de l’effet",
                    value=row.get("summary") or "",
                ).props("outlined autogrow maxlength=4000").classes("w-full")
                notes_input = ui.textarea(
                    label="Notes personnelles",
                    value=row.get("notes") or "",
                ).props("outlined autogrow maxlength=4000").classes("w-full")

                def apply_catalog(_event=None):
                    selected = catalog.get(str(catalog_input.value or ""))
                    if not selected:
                        return
                    values = (
                        (name_input, selected.get("name") or ""),
                        (level_input, selected.get("spell_level") or 0),
                        (slot_kind_input, selected.get("slot_kind") or "normal"),
                        (domain_input, selected.get("domain_source") or ""),
                        (school_input, selected.get("school") or ""),
                        (range_input, selected.get("range_text") or ""),
                        (source_input, selected.get("source_text") or ""),
                        (summary_input, selected.get("summary") or ""),
                    )
                    for control, value in values:
                        control.value = value
                        control.update()

                catalog_input.on_value_change(apply_catalog)

                def save():
                    selected = catalog.get(str(catalog_input.value or "")) or {}
                    try:
                        save_prepared_spell(
                            user_id,
                            character["id"],
                            {
                                "catalog_key": catalog_input.value or row.get("catalog_key"),
                                "spell_name": name_input.value,
                                "spell_level": level_input.value,
                                "slot_kind": slot_kind_input.value,
                                "domain_source": domain_input.value,
                                "prepared_count": prepared_count.value,
                                "used_count": row.get("used_count") or 0,
                                "school": school_input.value,
                                "range_text": range_input.value,
                                "summary": summary_input.value,
                                "source_text": source_input.value,
                                "notes": notes_input.value,
                                "sort_order": row.get("sort_order") or 0,
                            },
                            preparation_id=row.get("id") if editing else None,
                        )
                    except Exception as error:
                        notify_error(error, "Le sort préparé n’a pas pu être enregistré.")
                        return
                    dialog.close()
                    render_spells.refresh()
                    ui.notify("Préparation enregistrée.", type="positive")

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button("Enregistrer", icon="save", on_click=save).props("color=primary")
        dialog.open()

    def confirm_delete(row):
        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-md p-5"):
                ui.label("Retirer ce sort préparé?").classes("text-xl font-bold")
                ui.label(str(row.get("spell_name") or "Sort")).classes("font-bold")

                def confirm():
                    try:
                        delete_prepared_spell(user_id, character["id"], row["id"])
                    except Exception as error:
                        notify_error(error, "Le sort préparé n’a pas pu être retiré.")
                        return
                    dialog.close()
                    render_spells.refresh()

                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("Annuler", on_click=dialog.close).props("flat")
                    ui.button("Retirer", icon="delete", on_click=confirm).props("color=negative")
        dialog.open()

    @ui.refreshable
    def render_spells():
        try:
            profile = dict(get_spellcasting_profile(user_id, character["id"]))
            prepared = list(list_prepared_spells(user_id, character["id"]))
        except Exception as error:
            notify_error(error, "Les sorts n’ont pas pu être chargés.")
            with ui.card().classes("w-full p-4"):
                ui.label("Sorts").classes("text-xl font-bold")
                ui.label("La préparation des sorts est temporairement indisponible.").classes("text-sm jf-muted")
            return

        ability_key = profile.get("ability_key") or "wis"
        score = effective_ability_score(character, ability_key)
        modifier = ability_modifier_from_score(score)
        slots = cleric_slot_table(profile.get("class_level") or 1, score)
        usage = prepared_usage_summary(slots, prepared)
        max_level = max(int(row["spell_level"]) for row in slots)
        domains = domains_from_faith()
        domain_rows = domain_spell_rows(domains, max_level)

        with ui.card().classes("w-full p-5"):
            with ui.row().classes("w-full items-start justify-between gap-3 flex-wrap"):
                with ui.column().classes("gap-0"):
                    ui.label("Sorts préparés").classes("text-xl font-bold")
                    ui.label(
                        "Phase 15A — préparation du Clerc, emplacements quotidiens, "
                        "créneau de domaine et suivi des utilisations."
                    ).classes("text-sm jf-muted")
                with ui.row().classes("gap-2"):
                    ui.button(
                        "Configurer",
                        icon="settings",
                        on_click=lambda: open_profile_dialog(profile),
                    ).props("outline color=primary")
                    ui.button(
                        "Préparer un sort",
                        icon="auto_stories",
                        on_click=lambda: open_preparation_dialog(profile),
                    ).props("color=primary")

            with ui.element("div").classes("jf-rpg-grid mt-3"):
                for label, value in (
                    ("Niveau de Clerc", profile.get("class_level") or 1),
                    ("Niveau de lanceur", profile.get("caster_level") or 1),
                    (
                        "Caractéristique",
                        f"{ability_long_labels.get(ability_key, ability_key)} {score} ({format_modifier(modifier)})",
                    ),
                    ("Niveau de sort maximal", max_level),
                ):
                    with ui.column().classes("gap-0"):
                        ui.label(label).classes("text-xs jf-muted")
                        ui.label(str(value)).classes("font-bold")

            if profile.get("is_default"):
                ui.label(
                    "Configuration proposée à partir du niveau actuel du personnage. "
                    "Utilisez Configurer si son niveau de Clerc est différent."
                ).classes("text-xs text-primary mt-2")

            if profile.get("preparation_notes"):
                ui.label(str(profile["preparation_notes"])).classes("text-sm jf-muted mt-2 whitespace-pre-wrap")

            mode = profile.get("spontaneous_mode") or "cure"
            mode_text = {
                "cure": "Les emplacements normaux de niveau 1+ peuvent servir à la conversion spontanée en sorts de soins; l’automatisation du lancement viendra en Phase 15B.",
                "inflict": "Les emplacements normaux de niveau 1+ peuvent servir à la conversion spontanée en sorts de blessures; l’automatisation du lancement viendra en Phase 15B.",
                "none": "Aucune conversion spontanée n’est suivie pour ce profil.",
            }[mode]
            ui.label(mode_text).classes("text-xs jf-muted mt-2")

        with ui.card().classes("w-full p-5"):
            with ui.row().classes("w-full items-center justify-between gap-2 flex-wrap"):
                with ui.column().classes("gap-0"):
                    ui.label("Emplacements du jour").classes("text-xl font-bold")
                    ui.label(
                        "Les sorts de niveau 0 sont des oraisons : ils restent disponibles après utilisation."
                    ).classes("text-sm jf-muted")

                def reset_day():
                    try:
                        reset_spell_usage(user_id, character["id"])
                    except Exception as error:
                        notify_error(error, "Les utilisations n’ont pas pu être réinitialisées.")
                        return
                    render_spells.refresh()
                    ui.notify("Utilisations réinitialisées après la prière / le repos.", type="positive")

                ui.button(
                    "Nouvelle prière / repos",
                    icon="restart_alt",
                    on_click=reset_day,
                ).props("outline color=primary")

            with ui.element("div").classes("jf-rpg-grid mt-3"):
                for slot in usage:
                    level = int(slot["spell_level"])
                    with ui.card().classes("w-full p-3"):
                        ui.label("Niveau 0 — oraisons" if level == 0 else f"Niveau {level}").classes("font-bold")
                        if not slot.get("can_cast"):
                            ui.label(
                                f"Caractéristique insuffisante : {slot['required_ability_score']} requis."
                            ).classes("text-xs text-negative")
                        ui.label(f"DD de référence : {slot['save_dc']}").classes("text-xs jf-muted")
                        if level == 0:
                            ui.label(
                                f"Préparées : {slot['normal_prepared']} / {slot['normal_slots']} — réutilisables"
                            ).classes("text-sm")
                        else:
                            ui.label(
                                f"Normaux : {slot['normal_prepared']} préparé(s) / {slot['normal_slots']} — "
                                f"{slot['normal_available']} encore disponible(s)"
                            ).classes("text-sm")
                            ui.label(
                                f"Domaine : {slot['domain_prepared']} préparé / {slot['domain_slots']} — "
                                f"{slot['domain_available']} encore disponible"
                            ).classes("text-sm")

        if domains:
            with ui.card().classes("w-full p-5"):
                ui.label("Sorts de domaine disponibles").classes("text-xl font-bold")
                ui.label(
                    "Un seul créneau de domaine est disponible par niveau de sort accessible. "
                    "Vous pouvez y préparer le sort de l’un ou l’autre de vos domaines."
                ).classes("text-sm jf-muted")
                if domain_rows:
                    with ui.element("div").classes("jf-rpg-grid mt-3"):
                        for item in domain_rows:
                            with ui.card().classes("w-full p-3"):
                                ui.label(f"Niv. {item['spell_level']} — {item['name']}").classes("font-bold")
                                ui.label(f"Domaine : {item['domain_source']}").classes("text-xs text-primary")
                else:
                    ui.label(
                        "Aucun des domaines actuels n’a encore de table intégrée. "
                        "Les sorts de domaine peuvent néanmoins être saisis manuellement."
                    ).classes("text-sm jf-muted")

        usage_by_level = {int(item["spell_level"]): item for item in usage}

        with ui.card().classes("w-full p-5"):
            ui.label("Préparation actuelle").classes("text-xl font-bold")
            ui.label(
                "Le nombre restant est mis en évidence pour être lisible rapidement en jeu."
            ).classes("text-sm jf-muted")
            if not prepared:
                ui.label(
                    "Aucun sort préparé. Utilisez « Préparer un sort » pour remplir les emplacements du jour."
                ).classes("text-sm jf-muted mt-2")
                return

            for level in sorted({int(row.get("spell_level") or 0) for row in prepared}):
                level_usage = usage_by_level.get(level, {})
                with ui.row().classes(
                    "w-full items-center justify-between gap-2 flex-wrap mt-3"
                ):
                    ui.label(level_label(level)).classes("text-lg font-bold")
                    with ui.row().classes("gap-2 items-center flex-wrap"):
                        if level == 0:
                            ui.badge(
                                f"{int(level_usage.get('normal_prepared') or 0)} préparée(s) — réutilisables"
                            ).props("color=primary").classes("text-sm font-bold px-2 py-1")
                        else:
                            normal_used = int(level_usage.get("normal_used") or 0)
                            normal_remaining = int(level_usage.get("normal_available") or 0)
                            ui.badge(
                                f"Normaux : {normal_remaining} restant(s) • {normal_used} utilisé(s)"
                            ).props(
                                "color=positive" if normal_remaining > 0 else "color=negative"
                            ).classes("text-sm font-bold px-2 py-1")
                            if int(level_usage.get("domain_slots") or 0):
                                domain_used = int(level_usage.get("domain_used") or 0)
                                domain_remaining = int(level_usage.get("domain_available") or 0)
                                ui.badge(
                                    f"Domaine : {domain_remaining} restant • {domain_used} utilisé"
                                ).props(
                                    "color=positive" if domain_remaining > 0 else "color=negative"
                                ).classes("text-sm font-bold px-2 py-1")

                for row in [item for item in prepared if int(item.get("spell_level") or 0) == level]:
                    prepared_count = int(row.get("prepared_count") or 1)
                    used_count = 0 if level == 0 else int(row.get("used_count") or 0)
                    remaining = prepared_count if level == 0 else max(0, prepared_count - used_count)
                    with ui.card().classes("w-full p-3"):
                        with ui.row().classes("w-full items-start justify-between gap-3 flex-wrap"):
                            with ui.column().classes("gap-1 grow min-w-0"):
                                title = str(row.get("spell_name") or "Sort")
                                if row.get("slot_kind") == "domain":
                                    title += " — Domaine"
                                with ui.row().classes(
                                    "w-full items-center justify-between gap-2 flex-wrap"
                                ):
                                    ui.label(title).classes("text-lg font-bold")
                                    with ui.row().classes("gap-1 items-center flex-wrap"):
                                        ui.badge(
                                            f"Préparé {prepared_count}"
                                        ).props("color=grey-7").classes(
                                            "text-sm font-bold px-2 py-1"
                                        )
                                        if level == 0:
                                            ui.badge(
                                                "Réutilisable"
                                            ).props("color=primary").classes(
                                                "text-sm font-bold px-2 py-1"
                                            )
                                        else:
                                            ui.badge(
                                                f"Utilisé {used_count}"
                                            ).props(
                                                "color=orange-8" if used_count > 0 else "color=grey-6"
                                            ).classes("text-sm font-bold px-2 py-1")
                                            ui.badge(
                                                f"Restant {remaining}"
                                            ).props(
                                                "color=positive" if remaining > 0 else "color=negative"
                                            ).classes(
                                                "text-base font-bold px-3 py-1"
                                            )
                                meta = []
                                if row.get("school"):
                                    meta.append(str(row["school"]))
                                if row.get("domain_source"):
                                    meta.append("Domaine " + str(row["domain_source"]))
                                if row.get("range_text"):
                                    meta.append(str(row["range_text"]))
                                if meta:
                                    ui.label(" • ".join(meta)).classes("text-xs jf-muted")
                                if row.get("summary"):
                                    ui.label(str(row["summary"])).classes("text-sm mt-1")
                            with ui.row().classes("gap-1"):
                                if level > 0:
                                    def mark_used(_event=None, selected=dict(row)):
                                        current = int(selected.get("used_count") or 0)
                                        maximum = int(selected.get("prepared_count") or 1)
                                        if current >= maximum:
                                            ui.notify("Tous les exemplaires préparés sont déjà utilisés.", type="warning")
                                            return
                                        try:
                                            set_prepared_spell_used_count(
                                                user_id,
                                                character["id"],
                                                selected["id"],
                                                current + 1,
                                            )
                                        except Exception as error:
                                            notify_error(error, "L’utilisation n’a pas pu être enregistrée.")
                                            return
                                        render_spells.refresh()

                                    def restore_one(_event=None, selected=dict(row)):
                                        current = int(selected.get("used_count") or 0)
                                        if current <= 0:
                                            return
                                        try:
                                            set_prepared_spell_used_count(
                                                user_id,
                                                character["id"],
                                                selected["id"],
                                                current - 1,
                                            )
                                        except Exception as error:
                                            notify_error(error, "L’utilisation n’a pas pu être annulée.")
                                            return
                                        render_spells.refresh()

                                    ui.button(icon="remove_circle_outline", on_click=mark_used).props("flat round dense color=primary").tooltip("Marquer 1 emplacement utilisé")
                                    ui.button(icon="add_circle_outline", on_click=restore_one).props("flat round dense color=primary").tooltip("Rendre 1 utilisation")
                                ui.button(
                                    icon="edit",
                                    on_click=lambda _event=None, selected=dict(row): open_preparation_dialog(profile, selected),
                                ).props("flat round dense color=primary").tooltip("Modifier la préparation")
                                ui.button(
                                    icon="delete",
                                    on_click=lambda _event=None, selected=dict(row): confirm_delete(selected),
                                ).props("flat round dense color=negative").tooltip("Retirer de la préparation")

    render_spells()
