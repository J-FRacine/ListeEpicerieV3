from __future__ import annotations

import unittest
from unittest.mock import MagicMock, Mock

from rpg_character_saves import build_saves_panel


def chained(value=None):
    widget = MagicMock()
    widget.value = value
    widget.classes.return_value = widget
    widget.props.return_value = widget
    return widget


class SavesPanelTests(unittest.TestCase):
    def test_save_uses_current_editor_values(self):
        ui = MagicMock()

        controls = [
            chained(2),   # base
            chained(1),   # magie
            chained(-1),  # divers
            chained(3),   # temporaire
        ]
        ui.number.side_effect = controls
        notes = chained("bonus conditionnel")
        ui.textarea.return_value = notes

        list_saves = Mock(return_value=[{
            "save_key": "fortitude",
            "base_save": 2,
            "magic_modifier": 0,
            "misc_modifier": 0,
            "temporary_modifier": 0,
            "conditional_notes": "",
        }])
        update = Mock()

        build_saves_panel(
            ui=ui,
            user_id=7,
            character={"id": 42},
            list_rpg_saves=list_saves,
            save_definitions={
                "fortitude": {
                    "label": "Vigueur",
                    "ability_key": "con",
                    "ravenloft": False,
                }
            },
            ability_labels={"con": "CON"},
            ability_modifier_for_character=Mock(return_value=2),
            save_total=Mock(return_value=4),
            format_modifier=lambda value: f"{value:+d}",
            as_number=lambda value: int(value or 0),
            update_rpg_saves=update,
            notify_error=Mock(),
            calculation_rules_dialog=Mock(),
        )

        save_button = next(
            call for call in ui.button.call_args_list
            if call.args and call.args[0] == "Enregistrer les sauvegardes"
        )
        save_button.kwargs["on_click"]()

        list_saves.assert_called_once_with(7, 42)
        update.assert_called_once_with(
            7,
            42,
            [{
                "save_key": "fortitude",
                "base_save": 2,
                "magic_modifier": 1,
                "misc_modifier": -1,
                "temporary_modifier": 3,
                "conditional_notes": "bonus conditionnel",
            }],
        )
        ui.notify.assert_called_once_with(
            "Jets de sauvegarde enregistrés.",
            type="positive",
        )

    def test_save_error_is_reported_without_success_message(self):
        ui = MagicMock()
        ui.number.side_effect = [chained(1) for _ in range(4)]
        ui.textarea.return_value = chained("")
        error = ValueError("refus")
        notify_error = Mock()
        update = Mock(side_effect=error)

        build_saves_panel(
            ui=ui,
            user_id=7,
            character={"id": 42},
            list_rpg_saves=Mock(return_value=[{
                "save_key": "will",
                "base_save": 1,
                "magic_modifier": 0,
                "misc_modifier": 0,
                "temporary_modifier": 0,
                "conditional_notes": "",
            }]),
            save_definitions={
                "will": {
                    "label": "Volonté",
                    "ability_key": "wis",
                    "ravenloft": False,
                }
            },
            ability_labels={"wis": "SAG"},
            ability_modifier_for_character=Mock(return_value=2),
            save_total=Mock(return_value=3),
            format_modifier=lambda value: f"{value:+d}",
            as_number=lambda value: int(value or 0),
            update_rpg_saves=update,
            notify_error=notify_error,
            calculation_rules_dialog=Mock(),
        )

        save_button = next(
            call for call in ui.button.call_args_list
            if call.args and call.args[0] == "Enregistrer les sauvegardes"
        )
        save_button.kwargs["on_click"]()

        notify_error.assert_called_once()
        self.assertIs(notify_error.call_args.args[0], error)
        ui.notify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
