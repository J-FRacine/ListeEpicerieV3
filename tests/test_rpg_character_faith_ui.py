from __future__ import annotations

import unittest
from unittest.mock import MagicMock, Mock

from rpg_character_faith import build_faith_panel


class Widget(MagicMock):
    def __init__(self, *args, value=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.value = value

    def classes(self, *args, **kwargs):
        return self

    def props(self, *args, **kwargs):
        return self

    def tooltip(self, *args, **kwargs):
        return self

    def set_visibility(self, *args, **kwargs):
        return None

    def update(self, *args, **kwargs):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FaithPanelTests(unittest.TestCase):
    def make_ui(self):
        ui = MagicMock()
        for name in (
            "card",
            "row",
            "column",
            "element",
            "expansion",
        ):
            getattr(ui, name).side_effect = (
                lambda *a, **k: Widget()
            )

        ui.label.side_effect = lambda *a, **k: Widget()
        ui.input.side_effect = (
            lambda *a, **k: Widget(value=k.get("value"))
        )
        ui.textarea.side_effect = (
            lambda *a, **k: Widget(value=k.get("value"))
        )
        ui.button.side_effect = lambda *a, **k: Widget()
        return ui

    def test_save_uses_same_deity_and_structured_domains(self):
        ui = self.make_ui()
        update = Mock()
        get_faith = Mock(
            return_value={
                "id": 42,
                "deity": "Ezra",
                "domain_1": "Protection",
                "subdomain_1": "",
                "domain_2": "Healing",
                "subdomain_2": "",
                "faith_notes": "Campagne Ravenloft",
            }
        )
        character_url = Mock(return_value="/faith")

        build_faith_panel(
            ui=ui,
            user_id=7,
            character={
                "id": 42,
                "class_name": "Clerc",
            },
            get_rpg_faith=get_faith,
            update_rpg_faith=update,
            notify_error=Mock(),
            character_url=character_url,
        )

        save_call = next(
            call
            for call in ui.button.call_args_list
            if call.args
            and call.args[0] == "Enregistrer la foi"
        )
        save_call.kwargs["on_click"]()

        update.assert_called_once()
        user_id, character_id, values = update.call_args.args
        self.assertEqual((user_id, character_id), (7, 42))
        self.assertEqual(values["deity"], "Ezra")
        self.assertEqual(values["domain_1"], "Protection")
        self.assertEqual(values["domain_2"], "Healing")
        character_url.assert_called_once_with(42, "foi")
        ui.navigate.to.assert_called_once_with("/faith")

    def test_cleric_gets_non_blocking_reference_message(self):
        ui = self.make_ui()

        build_faith_panel(
            ui=ui,
            user_id=7,
            character={
                "id": 42,
                "class_name": "Cleric",
            },
            get_rpg_faith=Mock(
                return_value={
                    "id": 42,
                    "deity": None,
                    "domain_1": None,
                    "subdomain_1": None,
                    "domain_2": None,
                    "subdomain_2": None,
                    "faith_notes": None,
                }
            ),
            update_rpg_faith=Mock(),
            notify_error=Mock(),
            character_url=Mock(),
        )

        labels = [
            call.args[0]
            for call in ui.label.call_args_list
            if call.args
        ]
        self.assertIn("Repère Clerc", labels)
        self.assertTrue(
            any(
                isinstance(value, str)
                and "deux domaines" in value
                for value in labels
            )
        )


if __name__ == "__main__":
    unittest.main()
