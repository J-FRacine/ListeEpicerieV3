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

    def update(self, *args, **kwargs):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class IomedaePresetUiTests(unittest.TestCase):
    def test_preset_fills_iomedae_war_and_sun(self):
        ui = MagicMock()
        for name in ("card", "row", "column", "element", "expansion"):
            getattr(ui, name).side_effect = lambda *a, **k: Widget()

        inputs = []

        def input_factory(*args, **kwargs):
            widget = Widget(value=kwargs.get("value"))
            inputs.append((kwargs.get("label"), widget))
            return widget

        ui.input.side_effect = input_factory
        ui.textarea.side_effect = lambda *a, **k: Widget(value=k.get("value"))
        ui.label.side_effect = lambda *a, **k: Widget()
        ui.button.side_effect = lambda *a, **k: Widget()

        profile = {
            "deity_name": "Iomedae",
            "alignment": "LG",
            "domains": {
                "Glory": (),
                "Good": (),
                "Law": (),
                "Sun": (),
                "War": (),
            },
            "personal_domain_preset": ("War", "Sun"),
        }

        build_faith_panel(
            ui=ui,
            user_id=7,
            character={"id": 42, "class_name": "Clerc"},
            get_rpg_faith=Mock(
                return_value={
                    "id": 42,
                    "deity": "",
                    "domain_1": "",
                    "subdomain_1": "",
                    "domain_2": "",
                    "subdomain_2": "",
                    "faith_notes": "",
                }
            ),
            update_rpg_faith=Mock(),
            deity_profiles={"iomedae": profile},
            notify_error=Mock(),
            character_url=Mock(),
        )

        preset_call = next(
            call
            for call in ui.button.call_args_list
            if call.args
            and call.args[0] == "Préconfigurer Iomedae + Guerre / Soleil"
        )
        preset_call.kwargs["on_click"]()

        by_label = dict(inputs)
        self.assertEqual(by_label["Divinité"].value, "Iomedae")
        self.assertEqual(by_label["Domaine 1"].value, "War")
        self.assertEqual(by_label["Domaine 2"].value, "Sun")


if __name__ == "__main__":
    unittest.main()
