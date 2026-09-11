from __future__ import annotations

import unittest
from unittest.mock import MagicMock, Mock

from rpg_character_progression import build_progression_panel


class ProgressionPanelTests(unittest.TestCase):
    def test_renders_current_level_and_reads_history(self):
        ui = MagicMock()
        skills = Mock(return_value=[])
        history = Mock(return_value=[])

        build_progression_panel(
            ui=ui,
            user_id=7,
            character={
                "id": 42,
                "character_level": 4,
                "class_name": "Clerc",
                "subclass_name": "",
                "base_attack_bonus": 3,
            },
            list_rpg_skills=skills,
            list_rpg_level_history=history,
            format_modifier=lambda value: f"{int(value):+d}",
            format_number=lambda value: str(value),
            ability_labels={
                "str": "FOR",
                "dex": "DEX",
                "con": "CON",
                "int": "INT",
                "wis": "SAG",
                "cha": "CHA",
            },
            ability_long_labels={
                "str": "Force",
                "dex": "Dextérité",
                "con": "Constitution",
                "int": "Intelligence",
                "wis": "Sagesse",
                "cha": "Charisme",
            },
            skill_display_name=lambda fr, en: fr or en or "Sans nom",
            apply_rpg_level_up=Mock(),
            notify_error=Mock(),
            character_url=Mock(return_value="/jdr"),
        )

        skills.assert_called_once_with(7, 42)
        history.assert_called_once_with(7, 42)
        self.assertTrue(
            any(
                call.args and call.args[0] == "Monter au niveau 5"
                for call in ui.button.call_args_list
            )
        )
        self.assertTrue(
            any(
                call.args and call.args[0] == "Historique des niveaux"
                for call in ui.label.call_args_list
            )
        )

    def test_level_100_button_is_disabled(self):
        ui = MagicMock()
        button_widget = MagicMock()
        button_widget.props.return_value = button_widget
        ui.button.return_value = button_widget

        build_progression_panel(
            ui=ui,
            user_id=1,
            character={
                "id": 5,
                "character_level": 100,
                "class_name": "Clerc",
                "subclass_name": "",
                "base_attack_bonus": 75,
            },
            list_rpg_skills=Mock(return_value=[]),
            list_rpg_level_history=Mock(return_value=[]),
            format_modifier=lambda value: str(value),
            format_number=lambda value: str(value),
            ability_labels={"wis": "SAG"},
            ability_long_labels={"wis": "Sagesse"},
            skill_display_name=lambda fr, en: fr or en or "Sans nom",
            apply_rpg_level_up=Mock(),
            notify_error=Mock(),
            character_url=Mock(return_value="/jdr"),
        )

        button_widget.set_enabled.assert_called_once_with(False)


if __name__ == "__main__":
    unittest.main()
