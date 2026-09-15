from __future__ import annotations

import unittest
from unittest.mock import Mock

from rpg_character_magic_dialog import open_magic_item_dialog


class _Widget:
    def __init__(self, value=None, on_click=None):
        self.value = value
        self.opened = False
        self.on_click = on_click

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def classes(self, *_args, **_kwargs):
        return self

    def props(self, *_args, **_kwargs):
        return self

    def on_value_change(self, handler):
        self.handler = handler
        return self

    def update(self):
        return self

    def open(self):
        self.opened = True

    def close(self):
        self.opened = False


class _Navigate:
    def __init__(self):
        self.calls = []

    def to(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return None


class _StrictUI:
    """UI minimale qui refuse les valeurs de select absentes des options."""

    def __init__(self):
        self.navigate = _Navigate()
        self.select_calls = []
        self.select_widgets = []
        self.buttons = {}
        self.dialog_widget = None
        self.notifications = []

    def dialog(self):
        self.dialog_widget = _Widget()
        return self.dialog_widget

    def card(self):
        return _Widget()

    def row(self):
        return _Widget()

    def element(self, *_args, **_kwargs):
        return _Widget()

    def label(self, *_args, **_kwargs):
        return _Widget()

    def input(self, *_args, value=None, **_kwargs):
        return _Widget(value)

    def number(self, *_args, value=None, **_kwargs):
        return _Widget(value)

    def checkbox(self, *_args, value=False, **_kwargs):
        return _Widget(value)

    def textarea(self, *_args, value=None, **_kwargs):
        return _Widget(value)

    def button(self, *args, on_click=None, **_kwargs):
        widget = _Widget(on_click=on_click)
        if args and isinstance(args[0], str):
            self.buttons[args[0]] = widget
        return widget

    def notify(self, *args, **kwargs):
        self.notifications.append((args, kwargs))
        return None

    def select(self, options, *_args, value=None, multiple=False, **_kwargs):
        options = dict(options)
        self.select_calls.append((options, value, multiple))
        if multiple:
            for selected in value or []:
                if selected not in options:
                    raise ValueError(
                        f"Valeur multiple invalide: {selected!r}; "
                        f"options={options!r}"
                    )
        elif value not in options:
            raise ValueError(
                f"Valeur de select invalide: {value!r}; options={options!r}"
            )
        widget = _Widget(value)
        self.select_widgets.append(widget)
        return widget


class MagicDialogTests(unittest.TestCase):
    def _base_kwargs(self, ui):
        return {
            "ui": ui,
            "user_id": 7,
            "character": {"id": 42},
            "magic_kind_labels": {
                "passive": "Passif",
                "charges": "À charges",
                "activatable": "Activable",
                "container": "Conteneur magique",
                "other": "Autre",
            },
            "magic_item_templates": {
                "cloak_resistance": {"label": "Cloak of Resistance"},
            },
            "magic_template_values": Mock(return_value={}),
            "container_options": {},
            "save_rpg_equipment": Mock(return_value=99),
            "notify_error": Mock(),
            "character_url": Mock(return_value="/"),
        }

    def test_new_magic_item_dialog_opens_with_valid_empty_choices(self):
        ui = _StrictUI()
        open_magic_item_dialog(**self._base_kwargs(ui))

        self.assertTrue(ui.dialog_widget.opened)
        self.assertEqual(ui.select_calls[0][1], "")
        self.assertIn("", ui.select_calls[0][0])
        self.assertEqual(ui.select_calls[2][1], "")
        self.assertIn("", ui.select_calls[2][0])

    def test_existing_container_shows_current_contents(self):
        ui = _StrictUI()
        kwargs = self._base_kwargs(ui)
        kwargs.update({
            "row": {
                "id": 10,
                "item_name": "Handy Haversack",
                "magic_kind": "container",
                "is_magic_item": True,
                "magic_capacity_weight": 120,
            },
            "equipment_options": {
                2: "Corde — 10 lb",
                3: "Wand of Cure Light Wounds",
            },
            "container_content_ids": [2],
            "set_magic_container_contents": Mock(),
        })

        open_magic_item_dialog(**kwargs)

        multiple_calls = [
            call for call in ui.select_calls if call[2]
        ]
        self.assertEqual(len(multiple_calls), 1)
        self.assertEqual(multiple_calls[0][1], [2])
        self.assertEqual(set(multiple_calls[0][0]), {2, 3})

    def test_save_container_replaces_its_contents(self):
        ui = _StrictUI()
        save_equipment = Mock(return_value=10)
        set_contents = Mock()
        kwargs = self._base_kwargs(ui)
        kwargs.update({
            "row": {
                "id": 10,
                "item_name": "Handy Haversack",
                "magic_kind": "container",
                "is_magic_item": True,
                "magic_capacity_weight": 120,
            },
            "equipment_options": {
                2: "Corde — 10 lb",
                3: "Wand of Cure Light Wounds",
            },
            "container_content_ids": [2],
            "save_rpg_equipment": save_equipment,
            "set_magic_container_contents": set_contents,
        })

        open_magic_item_dialog(**kwargs)
        contents_widget = next(
            widget
            for widget, call in zip(ui.select_widgets, ui.select_calls)
            if call[2]
        )
        contents_widget.value = [2, 3]

        ui.buttons["Enregistrer"].on_click()

        self.assertTrue(save_equipment.called)
        set_contents.assert_called_once_with(7, 42, 10, [2, 3])
        self.assertFalse(ui.dialog_widget.opened)
        self.assertEqual(ui.notifications[-1][0][0], "Objet magique enregistré.")


if __name__ == "__main__":
    unittest.main()
