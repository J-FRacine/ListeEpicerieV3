"""Composants NiceGUI pour les rounds et effets temporaires de Combat rapide."""
from __future__ import annotations

from typing import Any, Callable, Mapping

from rpg_combat_effects import EFFECT_TARGET_LABELS


def build_combat_effects_panel(
    *,
    ui: Any,
    state_getter: Callable[[], Mapping[str, Any]],
    add_effect: Callable[..., Any],
    remove_effect: Callable[[Any], Any],
    advance_round: Callable[[], Any],
    on_change: Callable[[], None],
):
    """Affiche et rafraîchit la section Round et effets actifs."""

    @ui.refreshable
    def render():
        state = dict(state_getter() or {})
        with ui.card().classes("w-full p-4 mt-3"):
            with ui.row().classes("w-full items-start justify-between gap-3 flex-wrap"):
                with ui.column().classes("gap-0"):
                    ui.label("Round et effets actifs").classes("text-lg font-bold")
                    ui.label(
                        "Les effets sont temporaires à cette session et ne réécrivent pas "
                        "les bonus permanents de la fiche."
                    ).classes("text-sm jf-muted")
                with ui.row().classes("items-center gap-2"):
                    ui.badge(f"Round {int(state.get('round') or 1)}").props(
                        "color=primary"
                    ).classes("text-sm font-bold px-3 py-1")

                    def next_round():
                        advance_round()
                        render.refresh()
                        on_change()

                    ui.button(
                        "Round suivant",
                        icon="skip_next",
                        on_click=next_round,
                    ).props("outline color=primary")

            with ui.element("div").classes("jf-rpg-effect-entry-grid mt-3"):
                name_input = ui.input(
                    label="Effet / état",
                    placeholder="Ex. Bless, Stunned, flanc…",
                ).classes("w-full")
                target_input = ui.select(
                    EFFECT_TARGET_LABELS,
                    label="Modifie",
                    value="note",
                ).props("options-dense").classes("w-full")
                modifier_input = ui.number(
                    label="Bonus / malus",
                    value=0,
                    step=1,
                ).props("inputmode=numeric").classes("w-full")
                rounds_input = ui.number(
                    label="Durée (rounds)",
                    value=0,
                    min=0,
                    step=1,
                ).props("inputmode=numeric").classes("w-full")

            ui.label(
                "Durée 0 = reste actif jusqu’à suppression manuelle."
            ).classes("text-xs jf-muted mt-1")

            def submit_effect():
                add_effect(
                    name=name_input.value,
                    target=target_input.value,
                    modifier=modifier_input.value,
                    rounds=rounds_input.value,
                )
                render.refresh()
                on_change()

            ui.button(
                "Ajouter l’effet",
                icon="add",
                on_click=submit_effect,
            ).props("outline color=primary").classes("mt-2")

            effects = list(state.get("effects") or [])
            if not effects:
                ui.label("Aucun effet temporaire actif.").classes("text-sm jf-muted mt-3")
            else:
                with ui.column().classes("w-full gap-1 mt-3"):
                    for row in effects:
                        with ui.row().classes(
                            "w-full items-center justify-between gap-2 jf-rpg-effect-row"
                        ):
                            parts = [str(row.get("name") or "Effet")]
                            target = str(row.get("target") or "note")
                            modifier = int(row.get("modifier") or 0)
                            if target != "note":
                                parts.append(
                                    f"{EFFECT_TARGET_LABELS.get(target, target)} {modifier:+d}"
                                )
                            remaining = row.get("remaining_rounds")
                            if remaining not in (None, "", 0):
                                parts.append(f"{remaining} round(s)")
                            ui.label(" • ".join(parts)).classes("text-sm font-medium grow")

                            def remove(_event=None, effect_id=row.get("id")):
                                remove_effect(effect_id)
                                render.refresh()
                                on_change()

                            ui.button(icon="close", on_click=remove).props(
                                "flat round dense color=negative"
                            ).tooltip("Retirer l’effet")

            journal = list(state.get("journal") or [])
            with ui.expansion("Journal de session", icon="menu_book").props(
                "dense expand-separator"
            ).classes("w-full mt-3"):
                if not journal:
                    ui.label("Rounds, effets, dégâts et soins apparaîtront ici.").classes(
                        "text-sm jf-muted"
                    )
                else:
                    for entry in reversed(journal[-30:]):
                        ui.label(
                            f"R{entry.get('round', '?')} · {entry.get('at', '')} — "
                            f"{entry.get('message', '')}"
                        ).classes("text-xs py-1")

    render()
    return render
