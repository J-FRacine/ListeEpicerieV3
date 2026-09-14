"""Dialogue « Règles de calcul » de la fiche JDR."""
from __future__ import annotations

from decimal import Decimal


def open_calculation_rules_dialog(
    *,
    ui,
    user_id,
    character,
    list_rpg_saves,
    list_rpg_skills,
    list_rpg_attacks,
    armor_class_breakdown,
    initiative_breakdown,
    cmb_breakdown,
    cmd_breakdown,
    equipment_effects,
    format_number,
    format_modifier,
    ability_labels,
    ability_modifier_for_character,
    save_breakdown,
    save_definitions,
    pathfinder_reference_checks,
    skill_breakdown,
    attack_breakdown,
    skill_display_name,
):
    """Ouvre les formules et les exemples calculés du personnage."""

    try:
        saves = list_rpg_saves(user_id, character["id"])
    except Exception:
        saves = []

    try:
        skills = list_rpg_skills(user_id, character["id"])
    except Exception:
        skills = []

    try:
        attacks = list_rpg_attacks(user_id, character["id"])
    except Exception:
        attacks = []

    ac = armor_class_breakdown(character)
    initiative = initiative_breakdown(character)
    cmb = cmb_breakdown(character)
    cmd = cmd_breakdown(character)
    effects = character.get("equipment_effects") or equipment_effects(
        character,
        [],
    )

    def signed_rule_part(label, value):
        return f"{label} {format_modifier(value)}"

    def formula_block(title, formula, example, note=None):
        ui.label(title).classes("font-bold mt-2")
        ui.label(formula).classes("jf-rpg-rules-formula")
        ui.label(
            f"Avec ce personnage : {example}"
        ).classes("jf-rpg-rules-example")
        if note:
            ui.label(note).classes("text-xs jf-muted mt-1")

    with ui.dialog() as dialog:
        with ui.card().classes(
            "w-full max-w-5xl p-0 max-h-[90vh] overflow-auto"
        ):
            with ui.row().classes(
                "w-full items-center justify-between gap-3 p-4 pb-2"
            ):
                with ui.column().classes("gap-0"):
                    ui.label("Règles de calcul").classes(
                        "text-2xl font-bold"
                    )
                    ui.label(
                        "Formules Pathfinder et Ravenloft, avec des "
                        "exemples calculés à partir du personnage."
                    ).classes("text-sm jf-muted")
                ui.button(
                    icon="close",
                    on_click=dialog.close,
                ).props("flat round")

            with ui.column().classes("w-full gap-2 px-4 pb-4"):
                with ui.expansion(
                    "Caractéristiques",
                    icon="tune",
                    value=True,
                ).props("expand-separator").classes("w-full"):
                    ui.label(
                        "Modificateur = arrondi inférieur de "
                        "((score effectif − 10) ÷ 2). Le score temporaire "
                        "remplace le score normal lorsqu’il est rempli."
                    ).classes("jf-rpg-rules-formula")
                    ability_examples = []
                    for ability_key in ability_labels:
                        score = (
                            character.get(f"{ability_key}_temp_score")
                            or character.get(f"{ability_key}_score")
                        )
                        ability_examples.append(
                            f"{ability_labels[ability_key]} {score} → "
                            f"{format_modifier(ability_modifier_for_character(character, ability_key))}"
                        )
                    ui.label(
                        "Avec ce personnage : "
                        + "  ·  ".join(ability_examples)
                    ).classes("jf-rpg-rules-example")

                with ui.expansion(
                    "Classe d’armure et initiative",
                    icon="shield",
                    value=True,
                ).props("expand-separator").classes("w-full"):
                    formula_block(
                        "CA totale",
                        "CA = 10 + armure + bouclier + DEX + taille + "
                        "armure naturelle + déviation + divers",
                        " + ".join([
                            "10",
                            signed_rule_part("armure", ac["armor_bonus"]),
                            signed_rule_part("bouclier", ac["shield_bonus"]),
                            signed_rule_part("DEX", ac["dex_modifier"]),
                            signed_rule_part("taille", ac["size_modifier"]),
                            signed_rule_part(
                                "naturelle",
                                ac["natural_armor_bonus"],
                            ),
                            signed_rule_part(
                                "déviation",
                                ac["deflection_bonus"],
                            ),
                            signed_rule_part("divers", ac["misc_modifier"]),
                        ]) + f" = {ac['total']}",
                    )
                    formula_block(
                        "CA de contact",
                        "CA de contact = 10 + DEX + taille + déviation + divers",
                        " + ".join([
                            "10",
                            signed_rule_part("DEX", ac["dex_modifier"]),
                            signed_rule_part("taille", ac["size_modifier"]),
                            signed_rule_part(
                                "déviation",
                                ac["deflection_bonus"],
                            ),
                            signed_rule_part("divers", ac["misc_modifier"]),
                        ]) + f" = {ac['touch']}",
                        "L’armure, le bouclier et l’armure naturelle ne "
                        "protègent normalement pas contre une attaque de contact.",
                    )
                    formula_block(
                        "CA pris au dépourvu",
                        "CA pris au dépourvu = 10 + armure + bouclier + "
                        "DEX négative seulement + taille + armure naturelle + "
                        "déviation + divers",
                        " + ".join([
                            "10",
                            signed_rule_part("armure", ac["armor_bonus"]),
                            signed_rule_part("bouclier", ac["shield_bonus"]),
                            signed_rule_part(
                                "DEX retenue",
                                ac["flat_footed_dex_modifier"],
                            ),
                            signed_rule_part("taille", ac["size_modifier"]),
                            signed_rule_part(
                                "naturelle",
                                ac["natural_armor_bonus"],
                            ),
                            signed_rule_part(
                                "déviation",
                                ac["deflection_bonus"],
                            ),
                            signed_rule_part("divers", ac["misc_modifier"]),
                        ]) + f" = {ac['flat_footed']}",
                        "Un bonus positif de DEX est retiré; une pénalité "
                        "de DEX demeure.",
                    )
                    formula_block(
                        "Initiative",
                        "Initiative = modificateur de DEX + divers",
                        " + ".join([
                            signed_rule_part(
                                "DEX",
                                initiative["dex_modifier"],
                            ),
                            signed_rule_part(
                                "divers",
                                initiative["misc_modifier"],
                            ),
                        ]) + f" = {format_modifier(initiative['total'])}",
                    )

                with ui.expansion(
                    "BMO / CMB et DMD / CMD",
                    icon="sports_martial_arts",
                    value=True,
                ).props("expand-separator").classes("w-full"):
                    cmb_ability = ability_labels.get(
                        cmb["ability_key"],
                        cmb["ability_key"].upper(),
                    )
                    formula_block(
                        "BMO / CMB",
                        "BMO/CMB = BBA + modificateur de Force "
                        "(ou Dextérité pour une créature Très petite ou plus "
                        "petite) + modificateur spécial de taille + divers",
                        " + ".join([
                            signed_rule_part(
                                "BBA",
                                cmb["base_attack_bonus"],
                            ),
                            signed_rule_part(
                                cmb_ability,
                                cmb["ability_modifier"],
                            ),
                            signed_rule_part(
                                "taille spéciale",
                                cmb["size_modifier"],
                            ),
                            signed_rule_part(
                                "divers",
                                cmb["misc_modifier"],
                            ),
                        ]) + f" = {format_modifier(cmb['total'])}",
                    )
                    formula_block(
                        "DMD / CMD",
                        "DMD/CMD = 10 + BBA + FOR + DEX + modificateur "
                        "spécial de taille + déviation + autres bonus "
                        "applicables + divers",
                        " + ".join([
                            "10",
                            signed_rule_part(
                                "BBA",
                                cmd["base_attack_bonus"],
                            ),
                            signed_rule_part(
                                "FOR",
                                cmd["strength_modifier"],
                            ),
                            signed_rule_part(
                                "DEX",
                                cmd["dexterity_modifier"],
                            ),
                            signed_rule_part(
                                "taille spéciale",
                                cmd["size_modifier"],
                            ),
                            signed_rule_part(
                                "déviation",
                                cmd["deflection_bonus"],
                            ),
                            signed_rule_part(
                                "pénalités CA",
                                cmd["automatic_ac_penalty"],
                            ),
                            signed_rule_part(
                                "divers",
                                cmd["misc_modifier"],
                            ),
                        ]) + f" = {cmd['total']}",
                        "Les bonus d’esquive et les autres bonus applicables "
                        "doivent être inscrits dans Divers – DMD/CMD. Les "
                        "pénalités négatives du champ Divers CA sont "
                        "appliquées automatiquement.",
                    )

                with ui.expansion(
                    "Équipement, poids et vitesse",
                    icon="backpack",
                ).props("expand-separator").classes("w-full"):
                    capacity = effects["carrying_capacity"]
                    ui.label(
                        "Charge = somme des poids transportés; les seuils "
                        "dépendent de la Force, de la taille, du type bipède "
                        "ou quadrupède et du multiplicateur racial."
                    ).classes("jf-rpg-rules-formula")
                    formula_block(
                        "Capacité de charge",
                        "Comparer le poids transporté aux seuils de charge "
                        "légère, moyenne et lourde",
                        (
                            f"FOR {capacity['strength']} — légère "
                            f"{format_number(capacity['light_max'])} lb — "
                            f"moyenne {format_number(capacity['medium_max'])} lb — "
                            f"lourde {format_number(capacity['heavy_max'])} lb"
                        ),
                        (
                            f"Poids actuel "
                            f"{format_number(effects['carried_weight'])} lb : "
                            f"charge {effects['load_label'].lower()}."
                        ),
                    )
                    formula_block(
                        "Vitesse finale",
                        "Retenir la vitesse la plus défavorable entre la base, "
                        "l’armure et la charge, sauf exception raciale",
                        (
                            f"Base {effects['base_speed']} pi — armure "
                            f"{effects['armor_speed'] if effects['armor_speed'] is not None else 'sans réduction'} — "
                            f"charge {effects['load_speed'] if effects['load_speed'] is not None else 'sans réduction'} "
                            f"= {effects['final_speed']} pi"
                        ),
                        (
                            "Exception d’armure active. "
                            if effects["ignore_armor_speed"]
                            else ""
                        )
                        + (
                            "Exception d’encombrement active."
                            if effects["ignore_encumbrance_speed"]
                            else ""
                        ),
                    )
                    formula_block(
                        "DEX maximale et pénalité aux tests",
                        "Pour chaque catégorie, utiliser la restriction la "
                        "plus défavorable entre l’armure et la charge; ne pas "
                        "les additionner deux fois",
                        (
                            f"DEX brute "
                            f"{format_modifier(effects['raw_dex_modifier'])}; "
                            f"DEX max "
                            f"{effects['effective_max_dex_bonus'] if effects['effective_max_dex_bonus'] is not None else 'aucune'}; "
                            f"DEX retenue "
                            f"{format_modifier(effects['effective_ac_dex_modifier'])}; "
                            f"pénalité retenue "
                            f"{format_modifier(effects['effective_armor_check_penalty'])}"
                        ),
                    )

                with ui.expansion(
                    "Jets de sauvegarde",
                    icon="health_and_safety",
                ).props("expand-separator").classes("w-full"):
                    ui.label(
                        "Total = base + modificateur de caractéristique + "
                        "magie + divers + temporaire"
                    ).classes("jf-rpg-rules-formula")
                    if saves:
                        for save_row in saves:
                            breakdown = save_breakdown(
                                character,
                                save_row,
                            )
                            definition = save_definitions[
                                save_row["save_key"]
                            ]
                            ability_label = ability_labels[
                                breakdown["ability_key"]
                            ]
                            example = " + ".join([
                                signed_rule_part(
                                    "base",
                                    breakdown["base_save"],
                                ),
                                signed_rule_part(
                                    ability_label,
                                    breakdown["ability_modifier"],
                                ),
                                signed_rule_part(
                                    "magie",
                                    breakdown["magic_modifier"],
                                ),
                                signed_rule_part(
                                    "divers",
                                    breakdown["misc_modifier"],
                                ),
                                signed_rule_part(
                                    "temp.",
                                    breakdown["temporary_modifier"],
                                ),
                            ]) + f" = {format_modifier(breakdown['total'])}"
                            formula_block(
                                definition["label"],
                                f"{definition['label']} = base + "
                                f"{ability_label} + magie + divers + temporaire",
                                example,
                                "Peur, Horreur et Folie utilisent actuellement "
                                "la Sagesse dans cette feuille Ravenloft.",
                            )
                    else:
                        ui.label(
                            "Aucun jet de sauvegarde n’est disponible pour "
                            "construire un exemple."
                        ).classes("text-sm jf-muted")

                with ui.expansion(
                    "Compétences",
                    icon="psychology",
                ).props("expand-separator").classes("w-full"):
                    ui.label(
                        "Total = caractéristique + rangs + bonus de compétence "
                        "de classe (+3 si au moins 1 rang) + divers + pénalité "
                        "d’armure"
                    ).classes("jf-rpg-rules-formula")
                    formula_block(
                        "Exemple de référence — Dressage / Handle Animal",
                        "Charisme −2 + rangs 1 + compétence de classe 3 "
                        "+ divers 0 = total +2",
                        "CHA −2 + rangs +1 + classe +3 + divers +0 = +2",
                        "Le bonus automatique de compétence de classe ne doit "
                        "pas être recopié dans le champ Divers.",
                    )

                    reference_checks = pathfinder_reference_checks()
                    with ui.expansion(
                        "Tests de référence intégrés",
                        icon="verified",
                        value=False,
                    ).props(
                        "dense expand-separator"
                    ).classes("w-full"):
                        for check in reference_checks:
                            with ui.element("div").classes(
                                "jf-rpg-reference-row"
                            ):
                                ui.icon(
                                    "check_circle"
                                    if check["passed"]
                                    else "error"
                                ).classes(
                                    "text-positive"
                                    if check["passed"]
                                    else "text-negative"
                                )
                                with ui.column().classes(
                                    "gap-0 min-w-0"
                                ):
                                    ui.label(check["label"]).classes(
                                        "text-sm font-bold"
                                    )
                                    ui.label(check["formula"]).classes(
                                        "jf-rpg-reference-formula"
                                    )
                                ui.label(
                                    "OK"
                                    if check["passed"]
                                    else (
                                        f"Attendu {check['expected']}, "
                                        f"obtenu {check['actual']}"
                                    )
                                ).classes(
                                    "text-xs text-positive font-bold"
                                    if check["passed"]
                                    else "text-xs text-negative font-bold"
                                )

                    sample_skill = next(
                        (
                            row
                            for row in skills
                            if row.get("skill_key") == "handle_animal"
                            and Decimal(
                                str(row.get("ranks") or 0)
                            ) > 0
                        ),
                        None,
                    ) or next(
                        (
                            row
                            for row in skills
                            if Decimal(
                                str(row.get("ranks") or 0)
                            ) > 0
                        ),
                        None,
                    )

                    if sample_skill:
                        breakdown = skill_breakdown(
                            character,
                            sample_skill,
                        )
                        ability_label = ability_labels[
                            breakdown["ability_key"]
                        ]
                        example = " + ".join([
                            signed_rule_part(
                                ability_label,
                                breakdown["ability_modifier"],
                            ),
                            signed_rule_part(
                                "rangs",
                                breakdown["ranks"],
                            ),
                            signed_rule_part(
                                "classe",
                                breakdown["class_bonus"],
                            ),
                            signed_rule_part(
                                "divers",
                                breakdown["misc_modifier"],
                            ),
                            signed_rule_part(
                                "armure",
                                breakdown["armor_penalty"],
                            ),
                        ]) + f" = {format_modifier(breakdown['total'])}"
                        formula_block(
                            skill_display_name(
                                sample_skill.get("skill_name"),
                                sample_skill.get("english_name"),
                            ),
                            "Caractéristique + rangs + classe + divers + armure",
                            example,
                            "Le bonus de classe +3 est automatique et ne doit "
                            "pas être recopié dans Divers.",
                        )
                    else:
                        ui.label(
                            "Ajoutez au moins 1 rang dans une compétence "
                            "pour obtenir un exemple personnalisé."
                        ).classes("text-sm jf-muted")

                with ui.expansion(
                    "Attaques",
                    icon="gps_fixed",
                ).props("expand-separator").classes("w-full"):
                    ui.label(
                        "Bonus d’attaque = BBA + caractéristique + "
                        "modificateur de taille à la CA + magie + divers"
                    ).classes("jf-rpg-rules-formula")
                    if attacks:
                        attack = attacks[0]
                        breakdown = attack_breakdown(
                            character,
                            attack,
                        )
                        ability_label = ability_labels[
                            breakdown["ability_key"]
                        ]
                        example = " + ".join([
                            signed_rule_part(
                                "BBA",
                                breakdown["base_attack_bonus"],
                            ),
                            signed_rule_part(
                                ability_label,
                                breakdown["ability_modifier"],
                            ),
                            signed_rule_part(
                                "taille",
                                breakdown["size_modifier"],
                            ),
                            signed_rule_part(
                                "magie",
                                breakdown["magic_bonus"],
                            ),
                            signed_rule_part(
                                "divers",
                                breakdown["misc_bonus"],
                            ),
                        ]) + f" = {format_modifier(breakdown['total'])}"
                        formula_block(
                            attack.get("attack_name") or "Première attaque",
                            "BBA + caractéristique + taille + magie + divers",
                            example,
                        )
                    else:
                        ui.label(
                            "Ajoutez une attaque pour obtenir un exemple "
                            "personnalisé."
                        ).classes("text-sm jf-muted")

                with ui.row().classes(
                    "w-full justify-end mt-2"
                ):
                    ui.button(
                        "Fermer",
                        icon="close",
                        on_click=dialog.close,
                    ).props("outline")

    dialog.open()
