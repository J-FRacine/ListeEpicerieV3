"""Panneau Compétences de Personnages JDR.

Ce module ne dépend ni de NiceGUI, ni de la base de données, ni de la façade
``rpg_character``. Toutes les dépendances sont injectées par ``rpg_character.py``.
"""
from __future__ import annotations

from decimal import Decimal


def build_skills_panel(
    *,
    ui,
    user_id,
    character,
    list_rpg_skills,
    character_sheet_audit,
    create_custom_rpg_skill,
    delete_custom_rpg_skill,
    update_rpg_skills,
    skill_total,
    skill_breakdown,
    format_number,
    ability_labels,
    skill_dialog,
    skill_display_name,
    skill_breakdown_text,
    notify_error,
    character_url,
    calculation_rules_dialog,
):
    """Construit le panneau Compétences en conservant le comportement V1.4.1."""

    with ui.row().classes(
        "w-full items-center justify-between gap-3 flex-wrap"
    ):
        with ui.column().classes("gap-0"):
            ui.label("Compétences Pathfinder").classes("text-xl font-bold")
            ui.label(
                "Les compétences possédées ont au moins 1 rang. "
                "Le bonus de +3 d’une compétence de classe est "
                "ajouté automatiquement."
            ).classes("text-sm jf-muted")

        ui.button(
            "Ajouter une compétence",
            icon="add",
            on_click=lambda: skill_dialog(
                user_id,
                character,
                lambda: ui.navigate.to(
                    character_url(character["id"], "competences")
                ),
            ),
        ).props("outline color=primary")

    skills = list_rpg_skills(user_id, character["id"])
    audit = character_sheet_audit(character, skills)

    audit_class = "jf-rpg-audit"
    if audit["warnings"]:
        audit_class += " jf-rpg-audit-warning"

    with ui.element("section").classes(audit_class):
        with ui.row().classes(
            "w-full items-center justify-between gap-2 flex-wrap"
        ):
            with ui.column().classes("gap-0 min-w-0"):
                ui.label("Vérification des calculs").classes(
                    "text-sm font-bold"
                )
                ui.label(
                    f"{audit['reference_checks_passed']} sur "
                    f"{audit['reference_checks_total']} tests "
                    "de référence réussis."
                ).classes("text-xs jf-muted")

            ui.label(
                "Aucun point à examiner"
                if not audit["warnings"]
                else f"{len(audit['warnings'])} point(s) à examiner"
            ).classes(
                "text-xs text-positive font-bold"
                if not audit["warnings"]
                else "text-xs text-warning font-bold"
            )

        if audit["warnings"]:
            # Phase 7 : cette section reste volontairement repliée à chaque
            # rendu, y compris après l'enregistrement des compétences.
            with ui.expansion(
                "Afficher les points à vérifier",
                icon="fact_check",
                value=False,
            ).props("dense expand-separator").classes("w-full mt-1"):
                for warning in audit["warnings"]:
                    icon = {
                        "error": "error",
                        "warning": "warning",
                        "info": "info",
                    }.get(warning["severity"], "info")
                    css = {
                        "error": "text-negative",
                        "warning": "text-warning",
                        "info": "text-primary",
                    }.get(warning["severity"], "text-primary")
                    with ui.element("div").classes("jf-rpg-audit-row"):
                        ui.icon(icon).classes(css)
                        with ui.column().classes("gap-0 min-w-0"):
                            ui.label(warning["title"]).classes(
                                "text-sm font-bold"
                            )
                            ui.label(warning["detail"]).classes(
                                "text-xs jf-muted"
                            )
        else:
            ui.label(
                "Les bonus de compétence de classe, les rangs "
                "et les pénalités d’armure ne présentent aucune "
                "incohérence détectable."
            ).classes("text-xs jf-muted mt-1")

    editors = []
    initial_owned_count = sum(
        1
        for skill_row in skills
        if Decimal(str(skill_row["ranks"] or 0)) > 0
    )
    default_filter = "owned" if initial_owned_count > 0 else "all"

    with ui.card().classes("w-full p-4"):
        with ui.row().classes("w-full items-end gap-3 flex-wrap"):
            filter_toggle = ui.toggle(
                {
                    "owned": "Mes compétences",
                    "class": "Compétences de classe",
                    "unranked": "Sans rang",
                    "all": "Toutes",
                },
                value=default_filter,
            ).props("spread no-caps").classes("grow min-w-[260px]")

            search_input = ui.input(
                label="Rechercher",
                placeholder="Ex. Perception ou Acrobatics",
            ).props("clearable").classes("grow min-w-[220px]")

        count_label = ui.label("").classes(
            "jf-rpg-skill-filter-summary text-sm mt-3"
        )
        ui.label(
            "Les rangs Pathfinder sont des nombres entiers. "
            "Les noms français et anglais sont réunis sur une "
            "seule ligne. La formule complète apparaît sous "
            "chaque compétence."
        ).classes("text-xs jf-muted mt-2")

    empty_message = ui.card().classes(
        "w-full p-6 items-center text-center"
    )
    with empty_message:
        ui.icon("filter_alt_off").classes("text-4xl text-gray-400")
        empty_title = ui.label("Aucune compétence dans ce filtre").classes(
            "text-lg font-bold"
        )
        empty_detail = ui.label(
            "Choisissez un autre filtre ou modifiez la recherche."
        ).classes("text-sm jf-muted")

    cards_container = ui.column().classes("w-full gap-2")
    with cards_container:
        for skill_row in skills:
            name_state = {
                "fr": str(skill_row["skill_name"] or "").strip(),
                "en": str(skill_row["english_name"] or "").strip(),
            }

            card = ui.element("div").classes("jf-rpg-skill-card")
            with card:
                with ui.element("div").classes("jf-rpg-skill-header"):
                    name_label = ui.label(
                        skill_display_name(name_state["fr"], name_state["en"])
                    ).classes("jf-rpg-skill-name grow")

                    edit_name_button = ui.button(icon="edit").props(
                        "flat dense round color=primary"
                    ).classes("jf-rpg-skill-edit-button").tooltip(
                        "Modifier les noms"
                    )

                    with ui.element("div").classes(
                        "jf-rpg-skill-badges-compact"
                    ):
                        owned_badge = ui.label("✓ Possédée").classes(
                            "jf-rpg-skill-badge jf-rpg-skill-badge-owned"
                        )
                        class_badge = ui.label("★ Classe").classes(
                            "jf-rpg-skill-badge jf-rpg-skill-badge-class"
                        )
                        trained_badge = ui.label("Formation").classes(
                            "jf-rpg-skill-badge"
                        )
                        armor_badge = ui.label("Armure").classes(
                            "jf-rpg-skill-badge"
                        )
                        legacy_badge = ui.label("Ancienne 3.5").classes(
                            "jf-rpg-skill-badge"
                        )

                    total_label = ui.label(
                        format_number(skill_total(character, skill_row))
                    ).classes("jf-rpg-skill-total")

                    if skill_row["is_custom"]:
                        def remove_skill(selected=skill_row):
                            try:
                                delete_custom_rpg_skill(
                                    user_id,
                                    character["id"],
                                    selected["id"],
                                )
                            except Exception as error:
                                notify_error(
                                    error,
                                    "La compétence n’a pas pu être supprimée.",
                                )
                                return
                            ui.notify("Compétence supprimée.", type="positive")
                            ui.navigate.to(
                                character_url(character["id"], "competences")
                            )

                        ui.button(
                            icon="delete",
                            on_click=remove_skill,
                        ).props("flat dense round color=negative").tooltip(
                            "Supprimer la compétence personnalisée"
                        )

                with ui.element("div").classes("jf-rpg-skill-controls"):
                    ability_input = ui.select(
                        ability_labels,
                        label="Carac.",
                        value=skill_row["ability_key"],
                    ).props("dense outlined options-dense").classes(
                        "jf-rpg-skill-control"
                    )
                    ranks_input = ui.number(
                        label="Rangs",
                        value=float(skill_row["ranks"]),
                        min=0,
                        max=999,
                        step=1,
                    ).props("dense outlined").classes("jf-rpg-skill-control")
                    misc_input = ui.number(
                        label="Divers",
                        value=skill_row["misc_modifier"],
                        step=1,
                    ).props("dense outlined").classes("jf-rpg-skill-control")
                    class_input = ui.checkbox(
                        "Classe",
                        value=skill_row["class_skill"],
                    ).classes("jf-rpg-skill-check").tooltip(
                        "Compétence de classe"
                    )
                    trained_input = ui.checkbox(
                        "Formation",
                        value=skill_row["trained_only"],
                    ).classes("jf-rpg-skill-check").tooltip(
                        "Formation requise"
                    )
                    armor_input = ui.checkbox(
                        "Armure",
                        value=skill_row["armor_check_applies"],
                    ).classes("jf-rpg-skill-check").tooltip(
                        "La pénalité d’armure s’applique"
                    )
                    double_input = ui.checkbox(
                        "×2",
                        value=skill_row["double_armor_penalty"],
                    ).classes("jf-rpg-skill-check").tooltip(
                        "Doubler la pénalité d’armure"
                    )

                calculation_label = ui.label("").classes(
                    "jf-rpg-skill-calculation"
                )
                warning_row = ui.element("div").classes(
                    "jf-rpg-skill-warning"
                )
                with warning_row:
                    ui.label(
                        "Le +3 de compétence de classe est déjà "
                        "automatique. Vérifiez si « Divers +3 » "
                        "le répète."
                    ).classes("grow")
                    clear_duplicate_button = ui.button(
                        "Mettre Divers à 0"
                    ).props("flat dense no-caps color=warning")

                editor = {
                    "row": skill_row,
                    "container": card,
                    "name_state": name_state,
                    "name_label": name_label,
                    "ability": ability_input,
                    "ranks": ranks_input,
                    "misc": misc_input,
                    "class_skill": class_input,
                    "trained": trained_input,
                    "armor": armor_input,
                    "double": double_input,
                    "total": total_label,
                    "calculation": calculation_label,
                    "warning": warning_row,
                    "owned_badge": owned_badge,
                    "class_badge": class_badge,
                    "trained_badge": trained_badge,
                    "armor_badge": armor_badge,
                    "legacy_badge": legacy_badge,
                }
                editors.append(editor)

                def update_total(event=None, *, selected=editor):
                    row = {
                        "ability_key": selected["ability"].value or "int",
                        "ranks": selected["ranks"].value or 0,
                        "misc_modifier": selected["misc"].value or 0,
                        "class_skill": bool(selected["class_skill"].value),
                        "armor_check_applies": bool(selected["armor"].value),
                        "double_armor_penalty": bool(selected["double"].value),
                    }
                    breakdown = skill_breakdown(character, row)
                    selected["total"].set_text(
                        format_number(breakdown["total"])
                    )
                    selected["calculation"].set_text(
                        skill_breakdown_text(breakdown)
                    )
                    selected["warning"].set_visibility(
                        breakdown["class_bonus"] == 3
                        and breakdown["misc_modifier"] == 3
                    )

                def update_indicators(event=None, *, selected=editor):
                    ranks = Decimal(str(selected["ranks"].value or 0))
                    selected["owned_badge"].set_visibility(ranks > 0)
                    selected["class_badge"].set_visibility(
                        bool(selected["class_skill"].value)
                    )
                    selected["trained_badge"].set_visibility(
                        bool(selected["trained"].value)
                    )
                    selected["armor_badge"].set_visibility(
                        bool(selected["armor"].value)
                    )
                    selected["legacy_badge"].set_visibility(
                        "ancienne 3.5" in selected["name_state"]["fr"].lower()
                    )

                def open_name_dialog(event=None, *, selected=editor):
                    with ui.dialog() as dialog:
                        with ui.card().classes("w-full max-w-lg p-5"):
                            ui.label(
                                "Modifier les noms de la compétence"
                            ).classes("text-xl font-bold")
                            french_input = ui.input(
                                label="Nom français",
                                value=selected["name_state"]["fr"],
                            ).props("autofocus maxlength=120").classes("w-full")
                            english_input = ui.input(
                                label="Nom anglais",
                                value=selected["name_state"]["en"],
                            ).props("maxlength=120").classes("w-full")

                            def apply_names():
                                french = str(french_input.value or "").strip()
                                english = str(english_input.value or "").strip()
                                if not french:
                                    ui.notify(
                                        "Le nom français est obligatoire.",
                                        type="warning",
                                    )
                                    return
                                selected["name_state"]["fr"] = french
                                selected["name_state"]["en"] = english
                                selected["name_label"].set_text(
                                    skill_display_name(french, english)
                                )
                                update_indicators(selected=selected)
                                apply_filters()
                                dialog.close()

                            with ui.row().classes(
                                "w-full justify-end gap-2 mt-3"
                            ):
                                ui.button(
                                    "Annuler",
                                    on_click=dialog.close,
                                ).props("flat")
                                ui.button(
                                    "Appliquer",
                                    icon="check",
                                    on_click=apply_names,
                                ).props("color=primary")
                    dialog.open()

                edit_name_button.on("click", open_name_dialog)

                def clear_duplicate(event=None, *, selected=editor):
                    selected["misc"].value = 0
                    update_total(selected=selected)

                clear_duplicate_button.on("click", clear_duplicate)

                for control in (
                    ability_input,
                    ranks_input,
                    misc_input,
                    class_input,
                    armor_input,
                    double_input,
                ):
                    control.on_value_change(update_total)

                for control in (
                    ranks_input,
                    class_input,
                    trained_input,
                    armor_input,
                ):
                    control.on_value_change(update_indicators)

                update_total()
                update_indicators()

    def skill_state(editor):
        ranks = Decimal(str(editor["ranks"].value or 0))
        return {
            "owned": ranks > 0,
            "class_skill": bool(editor["class_skill"].value),
            "unranked": ranks == 0,
            "name": editor["name_state"]["fr"].lower(),
            "english_name": editor["name_state"]["en"].lower(),
        }

    def refresh_counts():
        owned_count = 0
        class_count = 0
        unranked_count = 0
        for editor in editors:
            state = skill_state(editor)
            owned_count += int(state["owned"])
            class_count += int(state["class_skill"])
            unranked_count += int(state["unranked"])
        count_label.set_text(
            f"Mes compétences : {owned_count}  ·  "
            f"Compétences de classe : {class_count}  ·  "
            f"Sans rang : {unranked_count}  ·  Total : {len(editors)}"
        )

    def apply_filters(event=None):
        selected_filter = filter_toggle.value or "all"
        query = str(search_input.value or "").strip().lower()
        visible_count = 0

        for editor in editors:
            state = skill_state(editor)
            if selected_filter == "owned":
                category_match = state["owned"]
            elif selected_filter == "class":
                category_match = state["class_skill"]
            elif selected_filter == "unranked":
                category_match = state["unranked"]
            else:
                category_match = True

            search_match = (
                not query
                or query in state["name"]
                or query in state["english_name"]
            )
            visible = category_match and search_match
            editor["container"].set_visibility(visible)
            visible_count += int(visible)

        empty_message.set_visibility(visible_count == 0)
        if visible_count == 0:
            if selected_filter == "owned":
                empty_title.set_text("Aucune compétence possédée")
                empty_detail.set_text(
                    "Passez à « Sans rang » ou « Toutes », "
                    "puis investissez au moins 1 rang."
                )
            else:
                empty_title.set_text("Aucune compétence dans ce filtre")
                empty_detail.set_text(
                    "Choisissez un autre filtre ou modifiez la recherche."
                )
        refresh_counts()

    filter_toggle.on_value_change(apply_filters)
    search_input.on_value_change(apply_filters)
    for editor in editors:
        editor["ranks"].on_value_change(lambda event: refresh_counts())
        editor["class_skill"].on_value_change(lambda event: refresh_counts())

    apply_filters()

    def save_skills():
        rows = [
            {
                "id": editor["row"]["id"],
                "skill_name": editor["name_state"]["fr"],
                "english_name": editor["name_state"]["en"],
                "ability_key": editor["ability"].value,
                "ranks": editor["ranks"].value,
                "misc_modifier": editor["misc"].value,
                "class_skill": editor["class_skill"].value,
                "trained_only": editor["trained"].value,
                "armor_check_applies": editor["armor"].value,
                "double_armor_penalty": editor["double"].value,
            }
            for editor in editors
        ]
        try:
            update_rpg_skills(user_id, character["id"], rows)
        except Exception as error:
            notify_error(
                error,
                "Les compétences n’ont pas pu être enregistrées.",
            )
            return

        ui.notify("Compétences Pathfinder enregistrées.", type="positive")
        ui.navigate.to(character_url(character["id"], "competences"))

    with ui.row().classes("jf-rpg-section-actions gap-2 flex-wrap"):
        ui.button(
            "Règles de calcul",
            icon="menu_book",
            on_click=lambda: calculation_rules_dialog(user_id, character),
        ).props("outline color=primary")
        ui.button(
            "Enregistrer les compétences",
            icon="save",
            on_click=save_skills,
        ).props("color=primary")
