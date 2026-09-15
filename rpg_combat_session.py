from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from rpg_character_spell_cast_dialog import open_spell_cast_dialog
from rpg_character_spell_casting import (
    available_prepared_spells,
    remaining_prepared_uses,
)


COMBAT_FIELDS = (
    "str_score",
    "dex_score",
    "con_score",
    "int_score",
    "wis_score",
    "cha_score",
    "str_temp_score",
    "dex_temp_score",
    "con_temp_score",
    "int_temp_score",
    "wis_temp_score",
    "cha_temp_score",
    "max_hp",
    "current_hp",
    "nonlethal_damage",
    "speed",
    "damage_reduction",
    "spell_resistance",
    "base_attack_bonus",
    "armor_bonus",
    "shield_bonus",
    "natural_armor_bonus",
    "deflection_bonus",
    "misc_ac_modifier",
    "armor_check_penalty",
    "initiative_misc_modifier",
    "grapple_misc_modifier",
    "cmb_misc_modifier",
    "cmd_misc_modifier",
)


def _as_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def adjusted_current_hp(
    current_hp: Any,
    *,
    damage: Any = 0,
    healing: Any = 0,
) -> int:
    """Applique rapidement dégâts et soins aux PV actuels."""
    return (
        _as_int(current_hp)
        - max(0, _as_int(damage))
        + max(0, _as_int(healing))
    )


def adjusted_nonlethal(
    current_nonlethal: Any,
    *,
    added: Any = 0,
    removed: Any = 0,
) -> int:
    """Met à jour les dégâts non létaux sans permettre une valeur négative."""
    return max(
        0,
        _as_int(current_nonlethal)
        + max(0, _as_int(added))
        - max(0, _as_int(removed)),
    )


def find_attack(
    attacks: Sequence[Mapping[str, Any]],
    attack_id: Any,
) -> Mapping[str, Any] | None:
    try:
        wanted = int(attack_id)
    except (TypeError, ValueError):
        return None
    for attack in attacks:
        try:
            if int(attack.get("id")) == wanted:
                return attack
        except (TypeError, ValueError):
            continue
    return None


def hp_update_payload(
    character: Mapping[str, Any],
    *,
    current_hp: Any,
    nonlethal_damage: Any,
) -> dict[str, Any]:
    """Préserve tout le contrat Combat et ne change que les pertes rapides."""
    payload = {
        field: character.get(field)
        for field in COMBAT_FIELDS
    }
    payload["current_hp"] = current_hp
    payload["nonlethal_damage"] = nonlethal_damage
    if payload.get("grapple_misc_modifier") in (None, ""):
        payload["grapple_misc_modifier"] = (
            payload.get("cmb_misc_modifier") or 0
        )
    return payload


def combat_summary(
    *,
    character: Mapping[str, Any],
    attacks: Sequence[Mapping[str, Any]],
    saves: Sequence[Mapping[str, Any]],
    selected_attack_id: Any,
    temporary_attack_bonus: Any,
    armor_class_total: Callable[[Mapping[str, Any]], Any],
    touch_armor_class: Callable[[Mapping[str, Any]], Any],
    flat_footed_armor_class: Callable[[Mapping[str, Any]], Any],
    initiative_total: Callable[[Mapping[str, Any]], Any],
    cmb_total: Callable[[Mapping[str, Any]], Any],
    cmd_total: Callable[[Mapping[str, Any]], Any],
    attack_total: Callable[
        [Mapping[str, Any], Mapping[str, Any]],
        Any,
    ],
    save_total: Callable[
        [Mapping[str, Any], Mapping[str, Any]],
        Any,
    ],
    feat_effects: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Construit les chiffres utiles de Combat rapide."""
    effects = dict(feat_effects or {})
    selected = find_attack(attacks, selected_attack_id)
    selected_total = None
    if selected is not None:
        selected_total = (
            _as_int(attack_total(character, selected))
            + _as_int(temporary_attack_bonus)
            + _as_int(effects.get("attack_modifier"))
        )

    save_modifiers = effects.get("save_modifiers") or {}
    all_save_mod = _as_int(save_modifiers.get("all"))
    save_totals = {
        str(row.get("save_key") or ""): (
            _as_int(save_total(character, row))
            + all_save_mod
            + _as_int(
                save_modifiers.get(
                    str(row.get("save_key") or "")
                )
            )
        )
        for row in saves
        if row.get("save_key")
    }

    return {
        "current_hp": _as_int(character.get("current_hp")),
        "max_hp": _as_int(character.get("max_hp")),
        "nonlethal_damage": _as_int(
            character.get("nonlethal_damage")
        ),
        "armor_class": armor_class_total(character),
        "touch_armor_class": touch_armor_class(character),
        "flat_footed_armor_class": flat_footed_armor_class(character),
        "initiative": (
            _as_int(initiative_total(character))
            + _as_int(effects.get("initiative_modifier"))
        ),
        "cmb": (
            _as_int(cmb_total(character))
            + _as_int(effects.get("cmb_modifier"))
        ),
        "cmd": (
            _as_int(cmd_total(character))
            + _as_int(effects.get("cmd_modifier"))
        ),
        "selected_attack": selected,
        "selected_attack_total": selected_total,
        "save_totals": save_totals,
        "feat_effects": effects,
    }


@dataclass
class CombatSessionHandle:
    on_open: Callable[[], None]

    def open(self) -> None:
        self.on_open()


def build_combat_session(
    *,
    ui: Any,
    user_id: int,
    character: Mapping[str, Any],
    list_rpg_attacks: Callable[
        ..., Sequence[Mapping[str, Any]]
    ],
    list_rpg_saves: Callable[
        ..., Sequence[Mapping[str, Any]]
    ],
    list_rpg_feats: Callable[
        ..., Sequence[Mapping[str, Any]]
    ],
    collect_feat_combat_effects: Callable[..., Mapping[str, Any]],
    get_spellcasting_profile: Callable[..., Mapping[str, Any]],
    list_prepared_spells: Callable[..., Sequence[Mapping[str, Any]]],
    cast_prepared_spell: Callable[..., Mapping[str, Any]],
    spell_catalog_by_key: Callable[..., Mapping[str, Mapping[str, Any]]],
    update_rpg_character_combat: Callable[..., Any],
    armor_class_total: Callable[[Mapping[str, Any]], Any],
    touch_armor_class: Callable[[Mapping[str, Any]], Any],
    flat_footed_armor_class: Callable[[Mapping[str, Any]], Any],
    initiative_total: Callable[[Mapping[str, Any]], Any],
    cmb_total: Callable[[Mapping[str, Any]], Any],
    cmd_total: Callable[[Mapping[str, Any]], Any],
    attack_total: Callable[
        [Mapping[str, Any], Mapping[str, Any]],
        Any,
    ],
    save_total: Callable[
        [Mapping[str, Any], Mapping[str, Any]],
        Any,
    ],
    format_modifier: Callable[[Any], str],
    character_url: Callable[..., str],
    notify_error: Callable[[Exception, str], None],
) -> CombatSessionHandle:
    """Prépare une fenêtre Combat rapide avec les dons structurés."""

    def open_dialog() -> None:
        attacks = list(
            list_rpg_attacks(user_id, character["id"])
        )
        saves = list(
            list_rpg_saves(user_id, character["id"])
        )
        feats = list(
            list_rpg_feats(user_id, character["id"])
        )

        attack_options = {
            int(row["id"]): str(
                row.get("attack_name") or f"Attaque {row['id']}"
            )
            for row in attacks
        }
        first_attack = next(iter(attack_options), None)

        with ui.dialog() as dialog:
            with ui.card().classes(
                "w-full max-w-5xl p-4 "
                "max-h-[92vh] overflow-auto"
            ):
                with ui.row().classes(
                    "w-full items-start justify-between "
                    "gap-3 flex-wrap"
                ):
                    with ui.column().classes("gap-0"):
                        ui.label("Combat rapide").classes(
                            "text-2xl font-bold"
                        )
                        ui.label(
                            "Consultez les principaux chiffres, choisissez une attaque, "
                            "activez vos dons, lancez vos sorts préparés et notez rapidement "
                            "les pertes de PV."
                        ).classes("text-sm jf-muted")
                    ui.button(
                        icon="close",
                        on_click=dialog.close,
                    ).props("flat round")

                with ui.element("div").classes(
                    "jf-rpg-result-grid mt-3"
                ):
                    stat_labels = {}
                    for key, label in (
                        ("hp", "PV"),
                        ("ac", "CA"),
                        ("touch", "Contact"),
                        ("flat", "Pris au dépourvu"),
                        ("initiative", "Initiative"),
                        ("cmb", "BMO / CMB"),
                        ("cmd", "DMD / CMD"),
                        ("fortitude", "Vigueur"),
                        ("reflex", "Réflexes"),
                        ("will", "Volonté"),
                    ):
                        with ui.element("div").classes(
                            "jf-rpg-result-item"
                        ):
                            ui.label(label).classes(
                                "text-xs jf-muted"
                            )
                            stat_labels[key] = ui.label("—").classes(
                                "jf-rpg-stat-value"
                            )

                with ui.card().classes("w-full p-4 mt-3"):
                    ui.label("Attaque utilisée").classes(
                        "text-lg font-bold"
                    )
                    attack_select = ui.select(
                        attack_options,
                        label="Arme / attaque",
                        value=first_attack,
                    ).props("options-dense").classes("w-full")
                    if not attack_options:
                        ui.label(
                            "Aucune attaque enregistrée. Ajoutez-en "
                            "depuis l’onglet Attaques."
                        ).classes("text-sm jf-muted")

                    with ui.element("div").classes(
                        "jf-rpg-grid mt-2"
                    ):
                        temporary_bonus = ui.number(
                            label="Bonus/malus temporaire",
                            value=0,
                            step=1,
                        ).props("inputmode=numeric")
                        attack_total_display = ui.input(
                            label="Bonus total",
                            value="—",
                        ).props("readonly")
                        damage_display = ui.input(
                            label="Dégâts",
                            value="—",
                        ).props("readonly")
                        critical_display = ui.input(
                            label="Critique",
                            value="—",
                        ).props("readonly")

                    feat_damage_label = ui.label("").classes(
                        "text-sm text-primary font-bold mt-2"
                    )
                    feat_damage_label.set_visibility(False)

                    tactics_input = ui.textarea(
                        label=(
                            "Tactique ou autres modificateurs "
                            "utilisés pendant ce combat"
                        ),
                        placeholder=(
                            "Ex. flanc, bénédiction, malus circonstanciel…"
                        ),
                    ).props(
                        "outlined autogrow maxlength=2000"
                    ).classes("w-full mt-2")
                    ui.label(
                        "Cette note reste temporaire et n’est pas "
                        "enregistrée dans la fiche."
                    ).classes("text-xs jf-muted")

                active_controls = {}
                if feats:
                    with ui.card().classes("w-full p-4 mt-3"):
                        ui.label("Dons").classes(
                            "text-lg font-bold"
                        )
                        ui.label(
                            "Les dons passifs sont toujours pris en compte. "
                            "Cochez seulement les dons activables utilisés "
                            "pour cette action ou ce round."
                        ).classes("text-sm jf-muted")

                        for feat in feats:
                            kind = str(
                                feat.get("feat_kind") or "info"
                            )
                            title = str(
                                feat.get("feat_name") or "Don"
                            )
                            english = str(
                                feat.get("english_name") or ""
                            ).strip()
                            if english:
                                title += f" — {english}"

                            with ui.element("div").classes(
                                "w-full py-2 border-b "
                                "border-gray-200"
                            ):
                                with ui.row().classes(
                                    "w-full items-start "
                                    "justify-between gap-2 flex-wrap"
                                ):
                                    with ui.column().classes(
                                        "gap-0 grow min-w-0"
                                    ):
                                        ui.label(title).classes(
                                            "font-bold"
                                        )
                                        if feat.get("summary"):
                                            ui.label(
                                                feat["summary"]
                                            ).classes(
                                                "text-xs jf-muted"
                                            )
                                        if feat.get(
                                            "linked_attack_name"
                                        ):
                                            ui.label(
                                                "Lié à : "
                                                + str(
                                                    feat[
                                                        "linked_attack_name"
                                                    ]
                                                )
                                            ).classes(
                                                "text-xs jf-muted"
                                            )

                                    if kind == "active":
                                        control = ui.checkbox(
                                            "Utiliser",
                                            value=False,
                                        )
                                        active_controls[
                                            int(feat["id"])
                                        ] = control
                                    elif kind == "passive":
                                        ui.badge(
                                            "Passif",
                                            color="positive",
                                        )
                                    else:
                                        ui.badge(
                                            "Info",
                                            color="grey",
                                        )

                        feat_summary_label = ui.label("").classes(
                            "text-xs jf-muted mt-2"
                        )
                else:
                    feat_summary_label = None

                @ui.refreshable
                def render_combat_spells():
                    with ui.card().classes("w-full p-4 mt-3"):
                        ui.label("Sorts préparés").classes("text-lg font-bold")
                        ui.label(
                            "Lancez un sort sans quitter Combat rapide. La même utilisation "
                            "est immédiatement consommée dans l’onglet Sorts."
                        ).classes("text-sm jf-muted")

                        try:
                            spell_profile = dict(
                                get_spellcasting_profile(user_id, character["id"])
                            )
                            prepared_spells = list(
                                list_prepared_spells(user_id, character["id"])
                            )
                        except Exception as error:
                            notify_error(
                                error,
                                "Les sorts préparés n’ont pas pu être chargés.",
                            )
                            return

                        available = available_prepared_spells(prepared_spells)
                        if not prepared_spells:
                            ui.label(
                                "Aucun sort préparé. Utilisez l’onglet Sorts pour préparer la journée."
                            ).classes("text-sm jf-muted mt-2")
                            return

                        remaining_slots = sum(
                            remaining_prepared_uses(row)
                            for row in prepared_spells
                            if int(row.get("spell_level") or 0) > 0
                        )
                        used_slots = sum(
                            int(row.get("used_count") or 0)
                            for row in prepared_spells
                            if int(row.get("spell_level") or 0) > 0
                        )
                        with ui.row().classes("gap-2 items-center flex-wrap mt-2"):
                            ui.badge(
                                f"{remaining_slots} emplacement(s) préparé(s) restant(s)"
                            ).props(
                                "color=positive" if remaining_slots > 0 else "color=negative"
                            ).classes("text-sm font-bold px-2 py-1")
                            ui.badge(
                                f"{used_slots} utilisé(s)",
                                color="grey-7",
                            ).classes("text-sm font-bold px-2 py-1")

                        if not available:
                            ui.label(
                                "Tous les sorts préparés de niveau 1+ sont utilisés. "
                                "Les oraisons préparées resteraient disponibles ici."
                            ).classes("text-sm text-warning mt-2")
                            return

                        options = {}
                        rows_by_id = {}
                        for spell in available:
                            spell_id = int(spell["id"])
                            rows_by_id[spell_id] = spell
                            level = int(spell.get("spell_level") or 0)
                            if level == 0:
                                suffix = "réutilisable"
                            else:
                                suffix = f"{remaining_prepared_uses(spell)} restant(s)"
                            domain_label = " • domaine" if spell.get("slot_kind") == "domain" else ""
                            options[spell_id] = (
                                f"Niv. {level} — {spell.get('spell_name') or 'Sort'}"
                                f"{domain_label} — {suffix}"
                            )

                        first_spell = next(iter(options), None)
                        spell_select = ui.select(
                            options,
                            label="Sort à lancer",
                            value=first_spell,
                        ).props("options-dense use-input").classes("w-full mt-2")

                        def launch_selected_spell():
                            try:
                                selected_id = int(spell_select.value)
                            except (TypeError, ValueError):
                                ui.notify("Choisissez un sort à lancer.", type="warning")
                                return
                            selected = rows_by_id.get(selected_id)
                            if not selected:
                                ui.notify("Ce sort n’est plus disponible.", type="warning")
                                render_combat_spells.refresh()
                                return
                            open_spell_cast_dialog(
                                ui=ui,
                                user_id=user_id,
                                character=character,
                                profile=spell_profile,
                                prepared_spell=selected,
                                cast_prepared_spell=cast_prepared_spell,
                                catalog_by_key=spell_catalog_by_key,
                                notify_error=notify_error,
                                on_cast=render_combat_spells.refresh,
                            )

                        with ui.row().classes("w-full justify-end mt-2"):
                            ui.button(
                                "Lancer le sort",
                                icon="auto_fix_high",
                                on_click=launch_selected_spell,
                            ).props("color=primary")

                        ui.label(
                            "Les dégâts, soins et états restent à appliquer manuellement dans "
                            "cette phase; le résumé du sort est affiché avant confirmation."
                        ).classes("text-xs jf-muted mt-2")

                render_combat_spells()

                with ui.card().classes("w-full p-4 mt-3"):
                    ui.label("Pertes et soins rapides").classes(
                        "text-lg font-bold"
                    )
                    with ui.element("div").classes(
                        "jf-rpg-grid mt-2"
                    ):
                        current_hp = ui.number(
                            label="PV actuels",
                            value=character.get("current_hp") or 0,
                            step=1,
                        ).props("inputmode=numeric")
                        damage_taken = ui.number(
                            label="Dégâts reçus",
                            value=0,
                            min=0,
                            step=1,
                        ).props("inputmode=numeric")
                        healing_received = ui.number(
                            label="Soins reçus",
                            value=0,
                            min=0,
                            step=1,
                        ).props("inputmode=numeric")
                        current_nonlethal = ui.number(
                            label="Dégâts non létaux",
                            value=(
                                character.get("nonlethal_damage")
                                or 0
                            ),
                            min=0,
                            step=1,
                        ).props("inputmode=numeric")
                        nonlethal_added = ui.number(
                            label="Non létaux reçus",
                            value=0,
                            min=0,
                            step=1,
                        ).props("inputmode=numeric")
                        nonlethal_removed = ui.number(
                            label="Non létaux retirés",
                            value=0,
                            min=0,
                            step=1,
                        ).props("inputmode=numeric")

                    def apply_quick_changes() -> None:
                        current_hp.value = adjusted_current_hp(
                            current_hp.value,
                            damage=damage_taken.value,
                            healing=healing_received.value,
                        )
                        current_nonlethal.value = adjusted_nonlethal(
                            current_nonlethal.value,
                            added=nonlethal_added.value,
                            removed=nonlethal_removed.value,
                        )
                        current_hp.update()
                        current_nonlethal.update()

                        damage_taken.value = 0
                        healing_received.value = 0
                        nonlethal_added.value = 0
                        nonlethal_removed.value = 0
                        for control in (
                            damage_taken,
                            healing_received,
                            nonlethal_added,
                            nonlethal_removed,
                        ):
                            control.update()
                        refresh_stats()

                    ui.button(
                        "Appliquer les pertes / soins",
                        icon="calculate",
                        on_click=apply_quick_changes,
                    ).props(
                        "outline color=primary"
                    ).classes("mt-2")

                def selected_active_ids():
                    return {
                        feat_id
                        for feat_id, control
                        in active_controls.items()
                        if bool(control.value)
                    }

                def refresh_stats(_event=None) -> None:
                    draft = dict(character)
                    draft["current_hp"] = current_hp.value
                    draft["nonlethal_damage"] = (
                        current_nonlethal.value
                    )

                    effects = collect_feat_combat_effects(
                        feats,
                        active_feat_ids=selected_active_ids(),
                        selected_attack_id=attack_select.value,
                    )

                    snapshot = combat_summary(
                        character=draft,
                        attacks=attacks,
                        saves=saves,
                        selected_attack_id=attack_select.value,
                        temporary_attack_bonus=temporary_bonus.value,
                        armor_class_total=armor_class_total,
                        touch_armor_class=touch_armor_class,
                        flat_footed_armor_class=(
                            flat_footed_armor_class
                        ),
                        initiative_total=initiative_total,
                        cmb_total=cmb_total,
                        cmd_total=cmd_total,
                        attack_total=attack_total,
                        save_total=save_total,
                        feat_effects=effects,
                    )

                    stat_labels["hp"].set_text(
                        f"{snapshot['current_hp']}/"
                        f"{snapshot['max_hp']}"
                    )
                    stat_labels["ac"].set_text(
                        str(snapshot["armor_class"])
                    )
                    stat_labels["touch"].set_text(
                        str(snapshot["touch_armor_class"])
                    )
                    stat_labels["flat"].set_text(
                        str(snapshot["flat_footed_armor_class"])
                    )
                    stat_labels["initiative"].set_text(
                        format_modifier(snapshot["initiative"])
                    )
                    stat_labels["cmb"].set_text(
                        format_modifier(snapshot["cmb"])
                    )
                    stat_labels["cmd"].set_text(
                        str(snapshot["cmd"])
                    )
                    stat_labels["fortitude"].set_text(
                        format_modifier(
                            snapshot["save_totals"].get(
                                "fortitude",
                                0,
                            )
                        )
                    )
                    stat_labels["reflex"].set_text(
                        format_modifier(
                            snapshot["save_totals"].get(
                                "reflex",
                                0,
                            )
                        )
                    )
                    stat_labels["will"].set_text(
                        format_modifier(
                            snapshot["save_totals"].get(
                                "will",
                                0,
                            )
                        )
                    )

                    selected = snapshot["selected_attack"]
                    if selected is None:
                        attack_total_display.value = "—"
                        damage_display.value = "—"
                        critical_display.value = "—"
                    else:
                        attack_total_display.value = (
                            format_modifier(
                                snapshot["selected_attack_total"]
                            )
                        )
                        damage_display.value = (
                            selected.get("damage") or "—"
                        )
                        critical_display.value = (
                            selected.get("critical") or "—"
                        )

                    damage_notes = (
                        snapshot["feat_effects"].get(
                            "damage_notes"
                        )
                        or []
                    )
                    if damage_notes:
                        feat_damage_label.set_text(
                            "Dons — dégâts : "
                            + " · ".join(damage_notes)
                        )
                        feat_damage_label.set_visibility(True)
                    else:
                        feat_damage_label.set_text("")
                        feat_damage_label.set_visibility(False)

                    if feat_summary_label is not None:
                        applied = (
                            snapshot["feat_effects"].get(
                                "applied_feats"
                            )
                            or []
                        )
                        if applied:
                            feat_summary_label.set_text(
                                "Appliqués : "
                                + ", ".join(
                                    str(row["name"])
                                    for row in applied
                                )
                            )
                        else:
                            feat_summary_label.set_text(
                                "Aucun don modifiant les chiffres "
                                "n’est actif."
                            )

                    attack_total_display.update()
                    damage_display.update()
                    critical_display.update()

                attack_select.on_value_change(refresh_stats)
                temporary_bonus.on_value_change(refresh_stats)
                current_hp.on_value_change(refresh_stats)
                current_nonlethal.on_value_change(refresh_stats)
                for control in active_controls.values():
                    control.on_value_change(refresh_stats)

                refresh_stats()

                def save_losses() -> None:
                    try:
                        update_rpg_character_combat(
                            user_id,
                            character["id"],
                            hp_update_payload(
                                character,
                                current_hp=current_hp.value,
                                nonlethal_damage=(
                                    current_nonlethal.value
                                ),
                            ),
                        )
                    except Exception as error:
                        notify_error(
                            error,
                            "Les pertes de combat n’ont pas "
                            "pu être enregistrées.",
                        )
                        return

                    dialog.close()
                    ui.notify(
                        "État de combat enregistré.",
                        type="positive",
                    )
                    ui.navigate.to(
                        character_url(
                            character["id"],
                            "combat",
                        )
                    )

                with ui.row().classes(
                    "w-full justify-between gap-2 mt-4 flex-wrap"
                ):
                    ui.button(
                        "Voir la fiche Combat",
                        icon="shield",
                        on_click=lambda: ui.navigate.to(
                            character_url(
                                character["id"],
                                "combat",
                            )
                        ),
                    ).props("flat")
                    with ui.row().classes("gap-2"):
                        ui.button(
                            "Fermer",
                            on_click=dialog.close,
                        ).props("flat")
                        ui.button(
                            "Enregistrer les pertes",
                            icon="save",
                            on_click=save_losses,
                        ).props("color=primary")

        dialog.open()

    return CombatSessionHandle(on_open=open_dialog)
