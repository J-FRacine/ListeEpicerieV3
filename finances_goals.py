"""Panneau Objectifs construit avec ses services injectés."""
from dataclasses import dataclass
from datetime import date
from typing import Callable


@dataclass
class GoalsPanelHandle:
    on_refresh: Callable[[], None]

    def refresh(self) -> None:
        self.on_refresh()


def build_goals_panel(
    *,
    ui,
    user_id,
    goals_tab,
    CARRY_POLICIES,
    _category_options,
    _tag_options,
    _money,
    save_goal,
    list_goals,
    toggle_goal,
    refresh_all,
) -> GoalsPanelHandle:
    # OBJECTIFS
    with ui.tab_panel(goals_tab).classes("px-0"):
        goals_box = ui.column().classes("w-full gap-2")

        def goal_dialog(row=None):
            categories = _category_options(user_id)
            tags = _tag_options(user_id)
            with ui.dialog() as dialog:
                with ui.card().classes("w-full max-w-2xl p-4"):
                    ui.label(
                        "Modifier l’objectif" if row else "Nouvel objectif"
                    ).classes("text-xl font-bold")
                    kind = ui.toggle(
                        {"category": "Catégorie", "tag": "Étiquette"},
                        value=row["goal_type"] if row else "category",
                    ).props("dense spread no-caps").classes("w-full")
                    target = ui.select(
                        categories if not row or row["goal_type"] == "category" else tags,
                        value=(
                            row["category_id"]
                            if row and row["goal_type"] == "category"
                            else (row["tag_id"] if row else None)
                        ),
                        label="Cible",
                    ).props("dense outlined options-dense").classes("w-full")

                    def refresh_targets():
                        target.options = (
                            categories if kind.value == "category" else tags
                        )
                        target.value = None
                        target.update()

                    kind.on_value_change(lambda event: refresh_targets())

                    with ui.element("div").classes("jf-finance-form-grid"):
                        amount = ui.number(
                            label="Objectif mensuel",
                            value=row["monthly_amount"] if row else None,
                            min=.01,
                            step=.01,
                        ).props("dense outlined").classes("jf-finance-field")
                        start_month = ui.input(
                            label="Début",
                            value=(
                                row["start_month"].strftime("%Y-%m")
                                if row else date.today().strftime("%Y-%m")
                            ),
                        ).props("type=month dense outlined").classes(
                            "jf-finance-field"
                        )
                        end_month = ui.input(
                            label="Fin facultative",
                            value=(
                                row["end_month"].strftime("%Y-%m")
                                if row and row["end_month"] else ""
                            ),
                        ).props("type=month dense outlined").classes(
                            "jf-finance-field jf-finance-description"
                        )
                    carry = ui.select(
                        CARRY_POLICIES,
                        value=row["carry_policy"] if row else "none",
                        label="Report au mois suivant",
                    ).props("dense outlined options-dense").classes("w-full")
                    maximum = ui.number(
                        label="Plafond de report facultatif",
                        value=row["max_carry"] if row else None,
                        min=0,
                        step=.01,
                    ).props("dense outlined clearable").classes("w-full")
                    ui.label(
                        "Les mois déjà créés conservent leur historique."
                    ).classes("text-xs jf-muted")

                    def save_goal_now():
                        try:
                            save_goal(
                                user_id=user_id,
                                goal_id=row["id"] if row else None,
                                goal_type=kind.value,
                                target_id=target.value,
                                monthly_amount=amount.value,
                                carry_policy=carry.value,
                                start_month=start_month.value,
                                end_month=end_month.value or None,
                                max_carry=maximum.value,
                            )
                        except Exception as error:
                            ui.notify(str(error), type="warning")
                            return
                        dialog.close()
                        ui.notify("Objectif enregistré.", type="positive")
                        refresh_all()

                    with ui.row().classes("w-full justify-end gap-2"):
                        ui.button(
                            "Annuler", on_click=dialog.close
                        ).props("flat")
                        ui.button(
                            "Enregistrer", icon="save", on_click=save_goal_now
                        ).props("color=primary")
            dialog.open()

        @ui.refreshable
        def render_goals():
            goals_box.clear()
            rows = list_goals(user_id)
            with goals_box:
                with ui.row().classes(
                    "w-full items-center justify-between"
                ):
                    ui.label("Objectifs mensuels").classes(
                        "text-xl font-bold"
                    )
                    ui.button(
                        "Ajouter",
                        icon="add",
                        on_click=lambda: goal_dialog(),
                    ).props("color=primary dense")
                if not rows:
                    ui.label("Aucun objectif.").classes(
                        "text-sm jf-muted"
                    )
                for row in rows:
                    with ui.element("div").classes("jf-finance-card"):
                        with ui.row().classes(
                            "w-full items-center justify-between gap-2"
                        ):
                            with ui.column().classes("gap-0 min-w-0"):
                                ui.label(row["target_name"]).classes(
                                    "text-sm font-bold"
                                )
                                ui.label(
                                    f"{_money(row['monthly_amount'])} / mois "
                                    f"— {CARRY_POLICIES[row['carry_policy']]}"
                                ).classes("text-xs jf-muted")
                            with ui.row().classes("gap-1"):
                                ui.switch(
                                    value=row["is_active"],
                                    on_change=(
                                        lambda event,
                                        selected=row["id"]:
                                        change_goal_state(
                                            selected, event.value
                                        )
                                    ),
                                ).props("dense")
                                ui.button(
                                    icon="edit",
                                    on_click=(
                                        lambda _event=None,
                                        selected=row:
                                        goal_dialog(selected)
                                    ),
                                ).props(
                                    "flat dense round size=sm color=primary"
                                )

        def change_goal_state(goal_id, value):
            toggle_goal(user_id, goal_id, value)
            refresh_all()

        render_goals()

    return GoalsPanelHandle(on_refresh=lambda: render_goals.refresh())
