from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence


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


def adjusted_current_hp(current_hp: Any, *, damage: Any = 0, healing: Any = 0) -> int:
    """Applique rapidement dégâts et soins aux PV actuels."""
    return _as_int(current_hp) - max(0, _as_int(damage)) + max(0, _as_int(healing))


def adjusted_nonlethal(current_nonlethal: Any, *, added: Any = 0, removed: Any = 0) -> int:
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
    payload = {field: character.get(field) for field in COMBAT_FIELDS}
    payload["current_hp"] = current_hp
    payload["nonlethal_damage"] = nonlethal_damage
    if payload.get("grapple_misc_modifier") in (None, ""):
        payload["grapple_misc_modifier"] = payload.get("cmb_misc_modifier") or 0
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
    attack_total: Callable[[Mapping[str, Any], Mapping[str, Any]], Any],
    save_total: Callable[[Mapping[str, Any], Mapping[str, Any]], Any],
) -> dict[str, Any]:
    """Construit les chiffres utiles d'une fenêtre de combat sans modifier la feuille."""
    selected = find_attack(attacks, selected_attack_id)
    selected_total = None
    if selected is not None:
        selected_total = _as_int(attack_total(character, selected)) + _as_int(
            temporary_attack_bonus
        )

    save_totals = {
        str(row.get("save_key") or ""): save_total(character, row)
        for row in saves
        if row.get("save_key")
    }

    return {
        "current_hp": _as_int(character.get("current_hp")),
        "max_hp": _as_int(character.get("max_hp")),
        "nonlethal_damage": _as_int(character.get("nonlethal_damage")),
        "armor_class": armor_class_total(character),
        "touch_armor_class": touch_armor_class(character),
        "flat_footed_armor_class": flat_footed_armor_class(character),
        "initiative": initiative_total(character),
        "cmb": cmb_total(character),
        "cmd": cmd_total(character),
        "selected_attack": selected,
        "selected_attack_total": selected_total,
        "save_totals": save_totals,
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
    list_rpg_attacks: Callable[..., Sequence[Mapping[str, Any]]],
    list_rpg_saves: Callable[..., Sequence[Mapping[str, Any]]],
    update_rpg_character_combat: Callable[..., Any],
    armor_class_total: Callable[[Mapping[str, Any]], Any],
    touch_armor_class: Callable[[Mapping[str, Any]], Any],
    flat_footed_armor_class: Callable[[Mapping[str, Any]], Any],
    initiative_total: Callable[[Mapping[str, Any]], Any],
    cmb_total: Callable[[Mapping[str, Any]], Any],
    cmd_total: Callable[[Mapping[str, Any]], Any],
    attack_total: Callable[[Mapping[str, Any], Mapping[str, Any]], Any],
    save_total: Callable[[Mapping[str, Any], Mapping[str, Any]], Any],
    format_modifier: Callable[[Any], str],
    character_url: Callable[..., str],
    notify_error: Callable[[Exception, str], None],
) -> CombatSessionHandle:
    """Prépare une fenêtre de combat rapide sans nouvelle table ni logique métier."""

    def open_dialog() -> None:
        attacks = list(list_rpg_attacks(user_id, character["id"]))
        saves = list(list_rpg_saves(user_id, character["id"]))

        attack_options = {
            int(row["id"]): str(row.get("attack_name") or f"Attaque {row['id']}")
            for row in attacks
        }
        first_attack = next(iter(attack_options), None)

        with ui.dialog() as dialog:
            with ui.card().classes("w-full max-w-5xl p-4 max-h-[92vh] overflow-auto"):
                with ui.row().classes(
                    "w-full items-start justify-between gap-3 flex-wrap"
                ):
                    with ui.column().classes("gap-0"):
                        ui.label("Combat rapide").classes("text-2xl font-bold")
                        ui.label(
                            "Consultez les principaux chiffres, choisissez une attaque "
                            "et notez rapidement les pertes de PV."
                        ).classes("text-sm jf-muted")
                    ui.button(icon="close", on_click=dialog.close).props("flat round")

                with ui.element("div").classes("jf-rpg-result-grid mt-3"):
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
                        with ui.element("div").classes("jf-rpg-result-item"):
                            ui.label(label).classes("text-xs jf-muted")
                            stat_labels[key] = ui.label("—").classes("jf-rpg-stat-value")

                with ui.card().classes("w-full p-4 mt-3"):
                    ui.label("Attaque utilisée").classes("text-lg font-bold")
                    attack_select = ui.select(
                        attack_options,
                        label="Arme / attaque",
                        value=first_attack,
                    ).props("options-dense").classes("w-full")
                    if not attack_options:
                        ui.label(
                            "Aucune attaque enregistrée. Ajoutez-en depuis l’onglet Attaques."
                        ).classes("text-sm jf-muted")

                    with ui.element("div").classes("jf-rpg-grid mt-2"):
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

                    ui.textarea(
                        label="Dons, tactique ou modificateurs utilisés pendant ce combat",
                        placeholder=(
                            "Ex. Attaque en puissance, bonus de flanc, bénédiction, "
                            "malus circonstanciel…"
                        ),
                    ).props("outlined autogrow maxlength=2000").classes("w-full mt-2")
                    ui.label(
                        "Cette note est temporaire dans cette première version et n’est "
                        "pas enregistrée dans la fiche."
                    ).classes("text-xs jf-muted")

                with ui.card().classes("w-full p-4 mt-3"):
                    ui.label("Pertes et soins rapides").classes("text-lg font-bold")
                    with ui.element("div").classes("jf-rpg-grid mt-2"):
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
                            value=character.get("nonlethal_damage") or 0,
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
                    ).props("outline color=primary").classes("mt-2")

                def refresh_stats(_event=None) -> None:
                    draft = dict(character)
                    draft["current_hp"] = current_hp.value
                    draft["nonlethal_damage"] = current_nonlethal.value
                    snapshot = combat_summary(
                        character=draft,
                        attacks=attacks,
                        saves=saves,
                        selected_attack_id=attack_select.value,
                        temporary_attack_bonus=temporary_bonus.value,
                        armor_class_total=armor_class_total,
                        touch_armor_class=touch_armor_class,
                        flat_footed_armor_class=flat_footed_armor_class,
                        initiative_total=initiative_total,
                        cmb_total=cmb_total,
                        cmd_total=cmd_total,
                        attack_total=attack_total,
                        save_total=save_total,
                    )
                    stat_labels["hp"].set_text(
                        f"{snapshot['current_hp']}/{snapshot['max_hp']}"
                    )
                    stat_labels["ac"].set_text(str(snapshot["armor_class"]))
                    stat_labels["touch"].set_text(str(snapshot["touch_armor_class"]))
                    stat_labels["flat"].set_text(
                        str(snapshot["flat_footed_armor_class"])
                    )
                    stat_labels["initiative"].set_text(
                        format_modifier(snapshot["initiative"])
                    )
                    stat_labels["cmb"].set_text(format_modifier(snapshot["cmb"]))
                    stat_labels["cmd"].set_text(str(snapshot["cmd"]))
                    stat_labels["fortitude"].set_text(
                        format_modifier(snapshot["save_totals"].get("fortitude", 0))
                    )
                    stat_labels["reflex"].set_text(
                        format_modifier(snapshot["save_totals"].get("reflex", 0))
                    )
                    stat_labels["will"].set_text(
                        format_modifier(snapshot["save_totals"].get("will", 0))
                    )
                    selected = snapshot["selected_attack"]
                    if selected is None:
                        attack_total_display.value = "—"
                        damage_display.value = "—"
                        critical_display.value = "—"
                    else:
                        attack_total_display.value = format_modifier(
                            snapshot["selected_attack_total"]
                        )
                        damage_display.value = selected.get("damage") or "—"
                        critical_display.value = selected.get("critical") or "—"
                    attack_total_display.update()
                    damage_display.update()
                    critical_display.update()

                attack_select.on_value_change(refresh_stats)
                temporary_bonus.on_value_change(refresh_stats)
                current_hp.on_value_change(refresh_stats)
                current_nonlethal.on_value_change(refresh_stats)
                refresh_stats()

                def save_losses() -> None:
                    try:
                        update_rpg_character_combat(
                            user_id,
                            character["id"],
                            hp_update_payload(
                                character,
                                current_hp=current_hp.value,
                                nonlethal_damage=current_nonlethal.value,
                            ),
                        )
                    except Exception as error:
                        notify_error(
                            error,
                            "Les pertes de combat n’ont pas pu être enregistrées.",
                        )
                        return
                    dialog.close()
                    ui.notify("État de combat enregistré.", type="positive")
                    ui.navigate.to(character_url(character["id"], "combat"))

                with ui.row().classes(
                    "w-full justify-between gap-2 mt-4 flex-wrap"
                ):
                    ui.button(
                        "Voir la fiche Combat",
                        icon="shield",
                        on_click=lambda: ui.navigate.to(
                            character_url(character["id"], "combat")
                        ),
                    ).props("flat")
                    with ui.row().classes("gap-2"):
                        ui.button("Fermer", on_click=dialog.close).props("flat")
                        ui.button(
                            "Enregistrer les pertes",
                            icon="save",
                            on_click=save_losses,
                        ).props("color=primary")

        dialog.open()

    return CombatSessionHandle(on_open=open_dialog)
