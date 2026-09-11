from __future__ import annotations

import unittest
from unittest.mock import MagicMock, Mock

from rpg_character_attacks import build_attacks_panel


def widget(value=None):
    item = MagicMock()
    item.value = value
    item.classes.return_value = item
    item.props.return_value = item
    item.tooltip.return_value = item
    return item


def common_kwargs(ui, *, attacks, create=None, update=None, delete=None):
    return dict(
        ui=ui,
        user_id=7,
        character={"id": 42},
        ability_labels={"str": "FOR", "dex": "DEX"},
        attack_total=Mock(return_value=6),
        format_modifier=lambda value: f"{int(value):+d}",
        list_rpg_attacks=Mock(return_value=attacks),
        create_rpg_attack=create or Mock(),
        update_rpg_attack=update or Mock(),
        delete_rpg_attack=delete or Mock(),
        notify_error=Mock(),
        character_url=Mock(return_value="/?tab=jdr&character=42&section=attaques"),
    )


class AttacksPanelTests(unittest.TestCase):
    def test_empty_panel_lists_attacks_and_shows_empty_message(self):
        ui = MagicMock()
        kwargs = common_kwargs(ui, attacks=[])

        build_attacks_panel(**kwargs)

        kwargs["list_rpg_attacks"].assert_called_once_with(7, 42)
        self.assertTrue(
            any(
                call.args and call.args[0] == "Aucune attaque enregistrée"
                for call in ui.label.call_args_list
            )
        )

    def test_add_attack_saves_complete_values_and_navigates(self):
        ui = MagicMock()
        create = Mock()

        ui.input.side_effect = [
            widget("Épée longue"),
            widget("1d8+3"),
            widget("19-20/x2"),
            widget("corps à corps"),
            widget("tranchant"),
        ]
        ui.select.return_value = widget("str")
        ui.number.side_effect = [
            widget(1),
            widget(2),
            widget(None),
            widget(None),
        ]
        ui.textarea.return_value = widget("arme principale")

        kwargs = common_kwargs(ui, attacks=[], create=create)
        build_attacks_panel(**kwargs)

        add_button = next(
            call for call in ui.button.call_args_list
            if call.args and call.args[0] == "Ajouter une attaque"
        )
        add_button.kwargs["on_click"]()

        save_button = next(
            call for call in ui.button.call_args_list
            if call.args and call.args[0] == "Enregistrer"
        )
        save_button.kwargs["on_click"]()

        create.assert_called_once_with(
            7,
            42,
            {
                "attack_name": "Épée longue",
                "ability_key": "str",
                "magic_bonus": 1,
                "misc_bonus": 2,
                "damage": "1d8+3",
                "critical": "19-20/x2",
                "attack_range": "corps à corps",
                "attack_type": "tranchant",
                "notes": "arme principale",
                "ammunition_current": None,
                "ammunition_max": None,
            },
        )
        ui.notify.assert_called_with("Attaque ajoutée.", type="positive")
        ui.navigate.to.assert_called_once_with(
            "/?tab=jdr&character=42&section=attaques"
        )

    def test_delete_attack_uses_selected_attack(self):
        ui = MagicMock()
        delete = Mock()
        attack = {
            "id": 9,
            "attack_name": "Arc",
            "ability_key": "dex",
            "magic_bonus": 0,
            "misc_bonus": 0,
            "damage": "1d8",
            "critical": "x3",
            "attack_range": "100 pi",
            "attack_type": "perforant",
            "ammunition_current": 12,
            "ammunition_max": 20,
            "notes": "",
        }

        kwargs = common_kwargs(ui, attacks=[attack], delete=delete)
        build_attacks_panel(**kwargs)

        delete_button = next(
            call for call in ui.button.call_args_list
            if call.kwargs.get("icon") == "delete"
        )
        delete_button.kwargs["on_click"]()

        delete.assert_called_once_with(7, 42, 9)
        ui.notify.assert_called_with("Attaque supprimée.", type="positive")


if __name__ == "__main__":
    unittest.main()
