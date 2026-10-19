"""Panneau temporaire rounds / effets de Combat rapide."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from rpg_combat_effects import (
    EFFECT_TARGETS,
    advance_effect_round,
    effect_duration_text,
    normalize_effect,
    summarize_effect_modifiers,
)


@dataclass
class CombatEffectsHandle:
    active_effects: list[dict[str, Any]]
    combat_log: list[str]
    round_state: dict[str, int]
    on_log: Callable[[str], None]
    on_refresh: Callable[[], None]

    def modifiers(self) -> dict[str, int]:
        return summarize_effect_modifiers(self.active_effects)

    def log(self, message: str) -> None:
        self.on_log(message)

    def refresh(self) -> None:
        self.on_refresh()


def build_combat_effects_panel(
    *,
    ui,
    format_modifier,
    on_changed,
) -> CombatEffectsHandle:
    active_effects: list[dict[str, Any]] = []
    combat_log: list[str] = []
    round_state = {"value": 1}
    next_effect_id = {"value": 1}

    def add_log(message: str) -> None:
        clean = str(message or "").strip()
        if not clean:
            return
        combat_log.insert(
            0,
            f"R{round_state['value']} — {clean}",
        )
        del combat_log[12:]

    with ui.card().classes(
        "jf-rpg-combat-section w-full p-4 mt-3"
    ):
        with ui.row().classes(
            "w-full items-center justify-between gap-3 flex-wrap"
        ):
            with ui.column().classes("gap-0"):
                ui.label("Round et effets actifs").classes(
                    "text-lg font-bold"
                )
                ui.label(
                    "Les effets sont temporaires à cette session et ne "
                    "réécrivent pas les bonus permanents de la fiche."
                ).classes("text-xs jf-muted")
            round_label = ui.label("Round 1").classes(
                "jf-rpg-round-badge"
            )

        with ui.element("div").classes(
            "jf-rpg-combat-effect-form mt-3"
        ):
            effect_name = ui.input(
                label="Effet / état",
                placeholder="Ex. Bénédiction, À terre, Frayé…",
            ).props("dense outlined maxlength=120")
            effect_target = ui.select(
                EFFECT_TARGETS,
                value="state",
                label="Modifie",
            ).props("dense outlined options-dense")
            effect_modifier = ui.number(
                label="Bonus / malus",
                value=0,
                step=1,
            ).props("dense outlined inputmode=numeric")
            effect_rounds = ui.number(
                label="Durée (rounds)",
                value=0,
                min=0,
                step=1,
            ).props("dense outlined inputmode=numeric").tooltip(
                "0 = jusqu’à la fin du combat"
            )
            effect_note = ui.input(
                label="Note",
                placeholder="Optionnel",
            ).props("dense outlined maxlength=500")

        @ui.refreshable
        def render_effects():
            if not active_effects:
                ui.label(
                    "Aucun effet temporaire actif."
                ).classes("text-sm jf-muted mt-3")
                return

            with ui.column().classes("w-full gap-2 mt-3"):
                for effect in active_effects:
                    with ui.element("div").classes(
                        "jf-rpg-combat-effect-row"
                    ):
                        with ui.column().classes(
                            "gap-0 grow min-w-0"
                        ):
                            ui.label(effect["name"]).classes("font-bold")
                            details = [
                                EFFECT_TARGETS.get(
                                    effect["target"],
                                    "État",
                                ),
                                effect_duration_text(effect),
                            ]
                            if effect["target"] != "state":
                                details.insert(
                                    1,
                                    format_modifier(
                                        effect["modifier"]
                                    ),
                                )
                            ui.label(
                                " · ".join(details)
                            ).classes("text-xs jf-muted")
                            if effect.get("note"):
                                ui.label(
                                    effect["note"]
                                ).classes(
                                    "text-xs jf-muted "
                                    "whitespace-pre-wrap"
                                )

                        def remove_effect(
                            _event=None,
                            *,
                            effect_id=effect["id"],
                            effect_name_value=effect["name"],
                        ):
                            active_effects[:] = [
                                row
                                for row in active_effects
                                if row["id"] != effect_id
                            ]
                            add_log(
                                f"Effet retiré : {effect_name_value}"
                            )
                            render_effects.refresh()
                            render_log.refresh()
                            on_changed()

                        ui.button(
                            icon="close",
                            on_click=remove_effect,
                        ).props(
                            "flat dense round color=negative"
                        ).tooltip("Retirer l’effet")

        @ui.refreshable
        def render_log():
            with ui.element("div").classes(
                "jf-rpg-combat-log mt-3"
            ):
                ui.label("Journal de session").classes("font-bold")
                if not combat_log:
                    ui.label(
                        "Rounds, effets, dégâts et soins apparaîtront ici."
                    ).classes("text-xs jf-muted")
                else:
                    for entry in combat_log:
                        ui.label(entry).classes("text-xs")

        def add_effect():
            try:
                effect = normalize_effect(
                    effect_id=next_effect_id["value"],
                    name=effect_name.value,
                    target=effect_target.value,
                    modifier=effect_modifier.value,
                    rounds=effect_rounds.value,
                    note=effect_note.value,
                )
            except ValueError as error:
                ui.notify(str(error), type="warning")
                return

            next_effect_id["value"] += 1
            active_effects.append(effect)
            add_log(f"Effet ajouté : {effect['name']}")

            effect_name.value = ""
            effect_modifier.value = 0
            effect_rounds.value = 0
            effect_note.value = ""
            for control in (
                effect_name,
                effect_modifier,
                effect_rounds,
                effect_note,
            ):
                control.update()

            render_effects.refresh()
            render_log.refresh()
            on_changed()

        def next_round():
            active, expired = advance_effect_round(
                active_effects
            )
            active_effects[:] = active
            round_state["value"] += 1
            round_label.set_text(
                f"Round {round_state['value']}"
            )

            if expired:
                for effect in expired:
                    add_log(
                        f"Effet expiré : {effect['name']}"
                    )
            else:
                add_log("Round suivant")

            render_effects.refresh()
            render_log.refresh()
            on_changed()

        def reset_session():
            active_effects.clear()
            combat_log.clear()
            round_state["value"] = 1
            round_label.set_text("Round 1")
            render_effects.refresh()
            render_log.refresh()
            on_changed()
            ui.notify(
                "Round et effets temporaires réinitialisés.",
                type="positive",
            )

        with ui.row().classes(
            "w-full items-center justify-between gap-2 mt-3 flex-wrap"
        ):
            ui.button(
                "Ajouter l’effet",
                icon="add",
                on_click=add_effect,
            ).props("outline color=primary")
            with ui.row().classes("gap-2 flex-wrap"):
                ui.button(
                    "Réinitialiser",
                    icon="restart_alt",
                    on_click=reset_session,
                ).props("flat color=secondary")
                ui.button(
                    "Round suivant",
                    icon="skip_next",
                    on_click=next_round,
                ).props("color=primary")

        render_effects()
        render_log()

    return CombatEffectsHandle(
        active_effects=active_effects,
        combat_log=combat_log,
        round_state=round_state,
        on_log=lambda message: (
            add_log(message),
            render_log.refresh(),
        ),
        on_refresh=lambda: (
            render_effects.refresh(),
            render_log.refresh(),
        ),
    )
