"""Panneau Foi / Domaines de la fiche Personnage JDR.

Le module ne dépend directement ni de NiceGUI, ni de la base de données.
Toutes les dépendances sont injectées par la façade.
"""
from __future__ import annotations


def build_faith_panel(
    *,
    ui,
    user_id,
    character,
    get_rpg_faith,
    update_rpg_faith,
    deity_profiles,
    notify_error,
    character_url,
):
    try:
        faith = dict(
            get_rpg_faith(
                user_id,
                character["id"],
            )
        )
    except Exception as error:
        notify_error(
            error,
            "La section Foi n’a pas pu être chargée.",
        )
        with ui.card().classes("w-full p-4"):
            ui.label("Foi / Domaines").classes("text-xl font-bold")
            ui.label(
                "Les renseignements de foi sont temporairement indisponibles."
            ).classes("text-sm jf-muted")
        return

    class_name = str(
        character.get("class_name") or ""
    ).strip().lower()
    is_cleric = (
        "clerc" in class_name
        or "cleric" in class_name
    )

    with ui.card().classes("w-full p-4"):
        ui.label("Foi / Domaines").classes("text-xl font-bold")
        ui.label(
            "La divinité utilise le même champ que dans Identité. "
            "Les domaines restent libres afin de respecter la divinité, "
            "Ravenloft et les règles particulières de la campagne."
        ).classes("text-sm jf-muted")

        if is_cleric:
            with ui.element("div").classes("jf-rpg-help mt-3"):
                ui.label("Repère Clerc").classes("font-bold")
                ui.label(
                    "Un Clerc Pathfinder choisit normalement deux domaines, "
                    "sous réserve de sa divinité et des règles de campagne. "
                    "L’application n’impose aucun choix automatiquement."
                ).classes("text-sm")

        deity_input = ui.input(
            label="Divinité",
            value=faith.get("deity") or "",
            placeholder="Ex. Iomedae",
        ).props("maxlength=160").classes("w-full mt-3")

        ui.label("Domaines").classes("text-lg font-bold mt-3")
        ui.label(
            "Les sous-domaines sont facultatifs. Ils sont conservés "
            "séparément du domaine principal."
        ).classes("text-sm jf-muted")

        with ui.element("div").classes("jf-rpg-grid mt-2"):
            domain_1_input = ui.input(
                label="Domaine 1",
                value=faith.get("domain_1") or "",
                placeholder="Ex. Glory",
            ).props("maxlength=160").classes("w-full")
            subdomain_1_input = ui.input(
                label="Sous-domaine 1 (facultatif)",
                value=faith.get("subdomain_1") or "",
            ).props("maxlength=160").classes("w-full")
            domain_2_input = ui.input(
                label="Domaine 2",
                value=faith.get("domain_2") or "",
                placeholder="Ex. War",
            ).props("maxlength=160").classes("w-full")
            subdomain_2_input = ui.input(
                label="Sous-domaine 2 (facultatif)",
                value=faith.get("subdomain_2") or "",
            ).props("maxlength=160").classes("w-full")

        iomedae = deity_profiles.get("iomedae") or {}
        if iomedae:
            with ui.expansion(
                "Préconfiguration Iomedae",
                icon="auto_awesome",
                value=(
                    str(faith.get("deity") or "").strip().lower()
                    == "iomedae"
                ),
            ).props(
                "expand-separator"
            ).classes("w-full mt-3"):
                ui.label(
                    "Profil de référence Pathfinder 1e. "
                    "Pour ce personnage, le bouton préremplit aussi "
                    "les domaines choisis : Guerre (War) et Soleil (Sun). "
                    "Les champs restent modifiables."
                ).classes("text-sm jf-muted")

                with ui.element("div").classes("jf-rpg-grid mt-2"):
                    for label, value in (
                        ("Alignement", iomedae.get("alignment")),
                        (
                            "Domaines",
                            ", ".join(
                                (iomedae.get("domains") or {}).keys()
                            ),
                        ),
                        (
                            "Arme favorite",
                            iomedae.get("favored_weapon"),
                        ),
                        ("Symbole", iomedae.get("symbol")),
                        (
                            "Couleurs sacrées",
                            iomedae.get("sacred_colors"),
                        ),
                        (
                            "Animal sacré",
                            iomedae.get("sacred_animal"),
                        ),
                    ):
                        with ui.card().classes("w-full p-3"):
                            ui.label(label).classes(
                                "text-xs jf-muted"
                            )
                            ui.label(value or "—").classes(
                                "font-bold"
                            )

                ui.label("Domaines et sous-domaines").classes(
                    "font-bold mt-3"
                )
                for domain_name, subdomains in (
                    iomedae.get("domains") or {}
                ).items():
                    ui.label(
                        f"{domain_name} : "
                        + ", ".join(subdomains)
                    ).classes("text-sm")
                if iomedae.get("domain_note"):
                    ui.label(
                        iomedae["domain_note"]
                    ).classes("text-xs jf-muted")

                ui.label("Domaines à choisir").classes(
                    "font-bold mt-3"
                )
                ui.label(
                    "Iomedae offre Glory, Good, Law, Sun et War. "
                    "Le préréglage personnel de ce personnage utilise "
                    "War et Sun, conformément à votre choix actuel."
                ).classes("text-sm")

                if iomedae.get("unique_cleric_spells"):
                    ui.label(
                        "Sorts particuliers Clerc / Warpriest"
                    ).classes("font-bold mt-3")
                    ui.label(
                        " · ".join(
                            iomedae["unique_cleric_spells"]
                        )
                    ).classes("text-sm")

                if iomedae.get("future_equipment_reference"):
                    ui.label("Équipement").classes(
                        "font-bold mt-3"
                    )
                    ui.label(
                        iomedae["future_equipment_reference"]
                    ).classes("text-sm")

                if iomedae.get("source_text"):
                    ui.label(
                        f"Source : {iomedae['source_text']}"
                    ).classes("text-xs jf-muted mt-2")

                def preset_iomedae():
                    deity_input.value = iomedae["deity_name"]
                    preset_domains = tuple(
                        iomedae.get("personal_domain_preset") or ()
                    )
                    if len(preset_domains) >= 1:
                        domain_1_input.value = preset_domains[0]
                    if len(preset_domains) >= 2:
                        domain_2_input.value = preset_domains[1]

                    for control in (
                        deity_input,
                        domain_1_input,
                        domain_2_input,
                    ):
                        control.update()

                    ui.notify(
                        "Iomedae préconfigurée avec Guerre / War "
                        "et Soleil / Sun.",
                        type="positive",
                    )

                ui.button(
                    "Préconfigurer Iomedae + Guerre / Soleil",
                    icon="auto_awesome",
                    on_click=preset_iomedae,
                ).props("outline color=primary").classes("mt-3")

        notes_input = ui.textarea(
            label="Notes de foi / campagne",
            value=faith.get("faith_notes") or "",
            placeholder=(
                "Ex. symbole sacré, restrictions de campagne, "
                "interprétation de la foi, choix à confirmer…"
            ),
        ).props(
            "outlined autogrow maxlength=5000"
        ).classes("w-full mt-3")

        with ui.expansion(
            "Ce que cette phase automatise",
            icon="info",
            value=False,
        ).props("dense expand-separator").classes("w-full mt-3"):
            ui.label(
                "La divinité, les deux domaines et leurs sous-domaines sont "
                "structurés ici. La Phase 15A relie maintenant les domaines "
                "à la préparation des sorts et aux créneaux de domaine. Les "
                "pouvoirs de domaine et la canalisation restent à automatiser "
                "dans des modules spécialisés ultérieurs."
            ).classes("text-sm")

        def save_faith():
            try:
                update_rpg_faith(
                    user_id,
                    character["id"],
                    {
                        "deity": deity_input.value,
                        "domain_1": domain_1_input.value,
                        "subdomain_1": subdomain_1_input.value,
                        "domain_2": domain_2_input.value,
                        "subdomain_2": subdomain_2_input.value,
                        "faith_notes": notes_input.value,
                    },
                )
            except Exception as error:
                notify_error(
                    error,
                    "La foi et les domaines n’ont pas pu être enregistrés.",
                )
                return

            ui.notify(
                "Foi et domaines enregistrés.",
                type="positive",
            )
            ui.navigate.to(
                character_url(
                    character["id"],
                    "foi",
                )
            )

        with ui.row().classes(
            "jf-rpg-section-actions gap-2 flex-wrap"
        ):
            ui.button(
                "Enregistrer la foi",
                icon="save",
                on_click=save_faith,
            ).props("color=primary")
