"""Panneau JDR — Identité et profil racial.

Ce module ne dépend directement ni de NiceGUI, ni de la base de données,
ni du module principal JDR. Toutes ses dépendances sont injectées.
"""
from __future__ import annotations


def build_identity_panel(
    *,
    ui,
    user_id,
    character,
    race_labels,
    size_labels,
    infer_race_key,
    get_race_profile,
    update_rpg_character_identity,
    notify_error,
    character_url,
):
    """Construit le panneau Identité sans modifier silencieusement les scores."""
    current_race_key = str(
        character.get("race_key")
        or infer_race_key(character.get("race"))
    )
    if current_race_key not in race_labels:
        current_race_key = "custom"

    with ui.card().classes("w-full p-5"):
        ui.label("Identité du personnage").classes("text-xl font-bold")
        ui.label(
            "La race alimente le profil de taille, de vitesse et "
            "d’encombrement, sans modifier silencieusement les scores."
        ).classes("text-sm jf-muted")

        with ui.element("div").classes("jf-rpg-grid mt-2"):
            name_input = ui.input(
                label="Nom du personnage",
                value=character["character_name"],
            ).props("maxlength=120").classes("w-full")
            player_input = ui.input(
                label="Joueur",
                value=character["player_name"] or "",
            ).props("maxlength=120").classes("w-full")
            campaign_input = ui.input(
                label="Campagne",
                value=character["campaign"] or "",
            ).props("maxlength=160").classes("w-full")
            class_input = ui.input(
                label="Classe",
                value=character["class_name"] or "",
            ).props("maxlength=120").classes("w-full")
            subclass_input = ui.input(
                label="Sous-classe facultative",
                value=character.get("subclass_name") or "",
            ).props("maxlength=160 clearable").classes("w-full")
            level_input = ui.number(
                label="Niveau",
                value=character["character_level"],
                min=1,
                max=100,
                step=1,
            ).props("inputmode=numeric").classes("w-full")
            alignment_input = ui.input(
                label="Alignement",
                value=character["alignment"] or "",
            ).props("maxlength=80").classes("w-full")
            deity_input = ui.input(
                label="Divinité",
                value=character["deity"] or "",
            ).props("maxlength=120").classes("w-full")
            age_input = ui.input(
                label="Âge",
                value=character["age_text"] or "",
            ).props("maxlength=60").classes("w-full")
            gender_input = ui.input(
                label="Genre",
                value=character["gender"] or "",
            ).props("maxlength=80").classes("w-full")
            height_input = ui.input(
                label="Taille physique",
                value=character["height_text"] or "",
            ).props("maxlength=60").classes("w-full")
            weight_input = ui.input(
                label="Poids du personnage",
                value=character["weight_text"] or "",
            ).props("maxlength=60").classes("w-full")
            eyes_input = ui.input(
                label="Yeux",
                value=character["eyes"] or "",
            ).props("maxlength=80").classes("w-full")
            hair_input = ui.input(
                label="Cheveux",
                value=character["hair"] or "",
            ).props("maxlength=80").classes("w-full")
            skin_input = ui.input(
                label="Peau",
                value=character["skin"] or "",
            ).props("maxlength=80").classes("w-full")
            xp_input = ui.number(
                label="Points d’expérience",
                value=character["experience_points"],
                min=0,
                step=1,
            ).props("inputmode=numeric").classes("w-full")

        with ui.element("section").classes("jf-rpg-race-profile mt-3"):
            ui.label("Profil racial").classes("text-lg font-bold")
            with ui.element("div").classes("jf-rpg-grid mt-2"):
                race_select = ui.select(
                    race_labels,
                    label="Race principale",
                    value=current_race_key,
                ).props(
                    "use-input fill-input hide-selected "
                    "input-debounce=0 options-dense"
                ).classes("w-full")
                custom_race_input = ui.input(
                    label="Nom de la race personnalisée",
                    value=(
                        character.get("race") or ""
                        if current_race_key == "custom"
                        else ""
                    ),
                ).props("maxlength=120").classes("w-full")
                heritage_input = ui.input(
                    label="Héritage / sous-race facultatif",
                    value=character.get("race_heritage") or "",
                ).props("maxlength=160").classes("w-full")
                size_input = ui.select(
                    size_labels,
                    label="Catégorie de taille",
                    value=character["size_key"],
                ).classes("w-full")
                base_speed_input = ui.number(
                    label="Vitesse de base (pi)",
                    value=character.get("base_speed") or 30,
                    min=0,
                    max=500,
                    step=5,
                ).props("inputmode=numeric").classes("w-full")
                creature_type_input = ui.input(
                    label="Type de créature",
                    value=character.get("creature_type") or "Humanoïde",
                ).props("maxlength=120").classes("w-full")
                subtypes_input = ui.input(
                    label="Sous-types raciaux",
                    value=character.get("racial_subtypes") or "",
                ).props("maxlength=240").classes("w-full")
                vision_input = ui.input(
                    label="Sens et vision",
                    value=character.get("vision") or "",
                ).props("maxlength=240").classes("w-full")
                languages_input = ui.input(
                    label="Langues",
                    value=character.get("languages") or "",
                ).props("maxlength=500").classes("w-full")
                ability_adjustments_input = ui.input(
                    label="Ajustements raciaux de caractéristiques",
                    value=character.get("racial_ability_adjustments") or "",
                ).props("maxlength=240").classes("w-full")
                carrying_multiplier_input = ui.number(
                    label="Multiplicateur de capacité de charge",
                    value=float(
                        character.get("carrying_capacity_multiplier") or 1
                    ),
                    min=.001,
                    max=100,
                    step=.25,
                ).props("inputmode=decimal").classes("w-full")

            with ui.row().classes("w-full gap-4 flex-wrap mt-2"):
                quadruped_input = ui.checkbox(
                    "Quadrupède",
                    value=bool(character.get("is_quadruped")),
                )
                ignore_armor_speed_input = ui.checkbox(
                    "L’armure ne réduit pas la vitesse",
                    value=bool(character.get("ignore_armor_speed")),
                )
                ignore_load_speed_input = ui.checkbox(
                    "L’encombrement ne réduit pas la vitesse",
                    value=bool(character.get("ignore_encumbrance_speed")),
                )

            alternate_traits_input = ui.textarea(
                label="Traits raciaux alternatifs / personnalisés",
                value=character.get("alternate_racial_traits") or "",
                placeholder=(
                    "Un trait par ligne. Indiquez aussi le trait standard "
                    "remplacé lorsqu’il y a lieu."
                ),
            ).props(
                "outlined autogrow maxlength=4000"
            ).classes("w-full mt-2")

            standard_traits_label = ui.label("").classes(
                "text-xs jf-muted mt-1"
            )
            ui.label(
                "Les ajustements raciaux sont documentés, mais les scores "
                "déjà saisis ne sont jamais modifiés automatiquement."
            ).classes("text-xs jf-muted")

        race_state = {
            "accepted_key": current_race_key,
            "suppress": False,
        }

        def refresh_race_visibility():
            is_custom = race_select.value == "custom"
            custom_race_input.set_visibility(is_custom)
            profile = get_race_profile(race_select.value)
            standard_traits_label.set_text(
                (
                    "Traits standards suggérés : "
                    + profile["standard_traits"]
                    if profile["standard_traits"]
                    else (
                        "Profil personnalisé : inscrivez les traits "
                        "utilisés dans votre campagne."
                    )
                )
            )

        def set_control(control, value):
            control.value = value
            control.update()

        def apply_profile(profile_key, *, keep_current=False):
            profile = get_race_profile(profile_key)
            race_state["accepted_key"] = profile_key
            set_control(race_select, profile_key)
            if profile_key != "custom":
                set_control(custom_race_input, "")
            if not keep_current:
                set_control(size_input, profile["size_key"])
                set_control(base_speed_input, profile["base_speed"])
                set_control(creature_type_input, profile["creature_type"])
                set_control(subtypes_input, profile["subtypes"])
                set_control(vision_input, profile["vision"])
                set_control(languages_input, profile["languages"])
                set_control(
                    ability_adjustments_input,
                    profile["ability_adjustments"],
                )
                set_control(
                    carrying_multiplier_input,
                    profile["carrying_capacity_multiplier"],
                )
                set_control(quadruped_input, profile["is_quadruped"])
                set_control(
                    ignore_armor_speed_input,
                    profile["ignore_armor_speed"],
                )
                set_control(
                    ignore_load_speed_input,
                    profile["ignore_encumbrance_speed"],
                )
            refresh_race_visibility()

        def race_preview_dialog(new_key):
            profile = get_race_profile(new_key)
            old_key = race_state["accepted_key"]
            old_label = race_labels.get(old_key, "Personnalisée")
            rows = (
                ("Race", old_label, profile["label"]),
                (
                    "Taille",
                    size_labels.get(size_input.value, size_input.value),
                    size_labels.get(profile["size_key"], profile["size_key"]),
                ),
                (
                    "Vitesse",
                    f"{base_speed_input.value} pi",
                    f"{profile['base_speed']} pi",
                ),
                ("Vision", vision_input.value or "—", profile["vision"] or "—"),
                (
                    "Langues",
                    languages_input.value or "—",
                    profile["languages"] or "—",
                ),
                (
                    "Charge",
                    str(carrying_multiplier_input.value or 1),
                    str(profile["carrying_capacity_multiplier"]),
                ),
                (
                    "Vitesse sous armure",
                    "Exception" if ignore_armor_speed_input.value else "Normale",
                    "Exception" if profile["ignore_armor_speed"] else "Normale",
                ),
                (
                    "Vitesse sous charge",
                    "Exception" if ignore_load_speed_input.value else "Normale",
                    "Exception"
                    if profile["ignore_encumbrance_speed"]
                    else "Normale",
                ),
            )

            with ui.dialog() as dialog:
                with ui.card().classes("w-full max-w-3xl p-4"):
                    ui.label(
                        "Prévisualiser le changement de race"
                    ).classes("text-xl font-bold")
                    ui.label(
                        "Le profil suggéré peut être appliqué ou ignoré. "
                        "Les six scores de caractéristiques ne seront pas changés."
                    ).classes("text-sm jf-muted")
                    with ui.element("div").classes(
                        "jf-rpg-race-preview-row mt-2 font-bold"
                    ):
                        ui.label("Valeur")
                        ui.label("Actuelle")
                        ui.label("Suggérée")
                    for label, current_value, suggested_value in rows:
                        with ui.element("div").classes(
                            "jf-rpg-race-preview-row"
                        ):
                            ui.label(label).classes("font-bold")
                            ui.label(str(current_value))
                            ui.label(str(suggested_value))

                    def cancel_change():
                        race_state["suppress"] = True
                        set_control(race_select, old_key)
                        race_state["suppress"] = False
                        refresh_race_visibility()
                        dialog.close()

                    def keep_values():
                        apply_profile(new_key, keep_current=True)
                        dialog.close()

                    def apply_values():
                        apply_profile(new_key, keep_current=False)
                        dialog.close()

                    with ui.row().classes(
                        "w-full justify-end gap-2 mt-3 flex-wrap"
                    ):
                        ui.button(
                            "Annuler",
                            on_click=cancel_change,
                        ).props("flat")
                        ui.button(
                            "Conserver mes valeurs",
                            on_click=keep_values,
                        ).props("outline color=primary")
                        ui.button(
                            "Appliquer le profil",
                            icon="check",
                            on_click=apply_values,
                        ).props("color=primary")
            dialog.open()

        def race_changed(event):
            if race_state["suppress"]:
                return
            new_key = str(event.value or "custom")
            if new_key == race_state["accepted_key"]:
                refresh_race_visibility()
                return
            if new_key == "custom":
                race_state["accepted_key"] = "custom"
                refresh_race_visibility()
                return
            race_preview_dialog(new_key)

        race_select.on_value_change(race_changed)
        refresh_race_visibility()

        def save_identity():
            race_key = str(race_select.value or "custom")
            race_name = (
                custom_race_input.value
                if race_key == "custom"
                else race_labels[race_key]
            )
            try:
                update_rpg_character_identity(
                    user_id,
                    character["id"],
                    {
                        "character_name": name_input.value,
                        "player_name": player_input.value,
                        "campaign": campaign_input.value,
                        "class_name": class_input.value,
                        "subclass_name": subclass_input.value,
                        "character_level": level_input.value,
                        "race_key": race_key,
                        "race": race_name,
                        "race_heritage": heritage_input.value,
                        "alternate_racial_traits": alternate_traits_input.value,
                        "creature_type": creature_type_input.value,
                        "racial_subtypes": subtypes_input.value,
                        "vision": vision_input.value,
                        "languages": languages_input.value,
                        "racial_ability_adjustments": ability_adjustments_input.value,
                        "carrying_capacity_multiplier": carrying_multiplier_input.value,
                        "is_quadruped": quadruped_input.value,
                        "ignore_armor_speed": ignore_armor_speed_input.value,
                        "ignore_encumbrance_speed": ignore_load_speed_input.value,
                        "base_speed": base_speed_input.value,
                        "alignment": alignment_input.value,
                        "deity": deity_input.value,
                        "size_key": size_input.value,
                        "age_text": age_input.value,
                        "gender": gender_input.value,
                        "height_text": height_input.value,
                        "weight_text": weight_input.value,
                        "eyes": eyes_input.value,
                        "hair": hair_input.value,
                        "skin": skin_input.value,
                        "experience_points": xp_input.value,
                    },
                )
            except Exception as error:
                notify_error(
                    error,
                    "L’identité n’a pas pu être enregistrée.",
                )
                return

            ui.notify(
                "Identité et profil racial enregistrés.",
                type="positive",
            )
            ui.navigate.to(
                character_url(character["id"], "identite")
            )

        with ui.row().classes("jf-rpg-section-actions"):
            ui.button(
                "Enregistrer l’identité",
                icon="save",
                on_click=save_identity,
            ).props("color=primary")
