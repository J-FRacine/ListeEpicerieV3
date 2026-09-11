from __future__ import annotations

from decimal import Decimal
import unittest
from unittest.mock import MagicMock, Mock

from rpg_character_equipment import build_equipment_panel


def widget(value=None):
    item = MagicMock()
    item.value = value
    item.classes.return_value = item
    item.props.return_value = item
    item.tooltip.return_value = item
    item.__enter__.return_value = item
    item.__exit__.return_value = False
    return item


def effects():
    return {
        "equipment_effects": {
            "carrying_capacity": {
                "light_max": Decimal("50"),
                "medium_max": Decimal("100"),
                "heavy_max": Decimal("150"),
                "lift_off_ground_max": Decimal("300"),
                "push_drag_max": Decimal("750"),
            },
            "load_key": "light",
            "load_label": "Légère",
            "remaining_before_next_threshold": Decimal("35"),
            "carried_weight": Decimal("15"),
            "final_speed": 30,
            "run_multiplier": 4,
            "equipped_armor": None,
            "equipped_shield": None,
            "equipment_armor_bonus": 0,
            "equipment_shield_bonus": 0,
            "raw_dex_modifier": 2,
            "effective_max_dex_bonus": None,
            "effective_ac_dex_modifier": 2,
            "equipment_armor_check_penalty": 0,
            "effective_armor_check_penalty": 0,
            "base_speed": 30,
            "armor_speed": None,
            "load_speed": None,
            "ignore_armor_speed": False,
            "ignore_encumbrance_speed": False,
        }
    }


class EquipmentPanelTests(unittest.TestCase):
    def make_ui(self):
        ui = MagicMock()
        for name in ("card", "row", "column", "element"):
            getattr(ui, name).side_effect = lambda *a, **k: widget()
        ui.label.side_effect = lambda *a, **k: widget()
        ui.icon.side_effect = lambda *a, **k: widget()
        ui.button.side_effect = lambda *a, **k: widget()
        ui.badge.side_effect = lambda *a, **k: widget()
        ui.switch.side_effect = lambda *a, **k: widget(k.get("value"))
        return ui

    def test_empty_equipment_shows_empty_state(self):
        ui = self.make_ui()
        list_equipment = Mock(return_value=[])
        apply_effects = Mock(return_value=effects())

        build_equipment_panel(
            ui=ui,
            user_id=7,
            character={"id": 42},
            list_rpg_equipment=list_equipment,
            apply_equipment_effects=apply_effects,
            equipment_type_labels={"armor": "Armures"},
            armor_category_labels={},
            format_number=str,
            format_modifier=lambda value: f"{int(value):+d}",
            update_rpg_equipment_state=Mock(),
            notify_error=Mock(),
            character_url=Mock(return_value="/jdr"),
            equipment_dialog=Mock(),
            delete_equipment_dialog=Mock(),
        )

        list_equipment.assert_called_once_with(7, 42)
        apply_effects.assert_called_once_with({"id": 42}, [])
        self.assertTrue(
            any(
                call.args and call.args[0] == "Aucun équipement"
                for call in ui.label.call_args_list
            )
        )

    def test_state_change_uses_existing_equipment_state_api(self):
        ui = self.make_ui()
        row = {
            "id": 9,
            "item_type": "gear",
            "item_name": "Sac",
            "quantity": 1,
            "weight_each": Decimal("2"),
            "carried": True,
            "equipped": False,
            "notes": "",
        }
        update = Mock()
        url = Mock(
            return_value="/?tab=jdr&character=42&section=equipement"
        )

        build_equipment_panel(
            ui=ui,
            user_id=7,
            character={"id": 42},
            list_rpg_equipment=Mock(return_value=[row]),
            apply_equipment_effects=Mock(return_value=effects()),
            equipment_type_labels={"gear": "Possessions"},
            armor_category_labels={},
            format_number=str,
            format_modifier=lambda value: f"{int(value):+d}",
            update_rpg_equipment_state=update,
            notify_error=Mock(),
            character_url=url,
            equipment_dialog=Mock(),
            delete_equipment_dialog=Mock(),
        )

        self.assertEqual(ui.switch.call_count, 2)
        for call in ui.switch.call_args_list:
            self.assertIn(call.args[0], {"Transporté", "Équipé"})

    def test_edit_and_delete_delegate_to_existing_dialogs(self):
        ui = self.make_ui()
        row = {
            "id": 9,
            "item_type": "gear",
            "item_name": "Sac",
            "quantity": 1,
            "weight_each": Decimal("2"),
            "carried": True,
            "equipped": False,
            "notes": "",
        }
        edit_dialog = Mock()
        delete_dialog = Mock()

        build_equipment_panel(
            ui=ui,
            user_id=7,
            character={"id": 42},
            list_rpg_equipment=Mock(return_value=[row]),
            apply_equipment_effects=Mock(return_value=effects()),
            equipment_type_labels={"gear": "Possessions"},
            armor_category_labels={},
            format_number=str,
            format_modifier=lambda value: f"{int(value):+d}",
            update_rpg_equipment_state=Mock(),
            notify_error=Mock(),
            character_url=Mock(return_value="/jdr"),
            equipment_dialog=edit_dialog,
            delete_equipment_dialog=delete_dialog,
        )

        edit_call = next(
            call for call in ui.button.call_args_list
            if call.kwargs.get("icon") == "edit"
        )
        delete_call = next(
            call for call in ui.button.call_args_list
            if call.kwargs.get("icon") == "delete"
        )

        edit_call.kwargs["on_click"]()
        delete_call.kwargs["on_click"]()

        edit_dialog.assert_called_once_with(7, {"id": 42}, row)
        delete_dialog.assert_called_once_with(7, {"id": 42}, row)


if __name__ == "__main__":
    unittest.main()
