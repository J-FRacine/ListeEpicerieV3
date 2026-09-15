from __future__ import annotations

import unittest
from unittest.mock import Mock

from rpg_character_magic_dialog import open_magic_item_dialog


class _Widget:
    def __init__(self, value=None):
        self.value = value
        self.opened = False

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
    def to(self, *_args, **_kwargs):
        return None


class _StrictUI:
    """UI minimale qui refuse les valeurs de select absentes des options."""

    def __init__(self):
        self.navigate = _Navigate()
        self.select_calls = []
        self.dialog_widget = None

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

    def button(self, *_args, **_kwargs):
        return _Widget()

    def notify(self, *_args, **_kwargs):
        return None

    def select(self, options, *_args, value=None, **_kwargs):
        self.select_calls.append((dict(options), value))
        if value not in options:
            raise ValueError(
                f"Valeur de select invalide: {value!r}; options={options!r}"
            )
        return _Widget(value)


class MagicDialogTests(unittest.TestCase):
    def test_new_magic_item_dialog_opens_with_valid_empty_choices(self):
        ui = _StrictUI()
        open_magic_item_dialog(
            ui=ui,
            user_id=7,
            character={"id": 42},
            magic_kind_labels={
                "passive": "Passif",
                "charges": "À charges",
                "activatable": "Activable",
                "container": "Conteneur magique",
                "other": "Autre",
            },
            magic_item_templates={
                "cloak_resistance": {"label": "Cloak of Resistance"},
            },
            magic_template_values=Mock(return_value={}),
            container_options={},
            save_rpg_equipment=Mock(),
            notify_error=Mock(),
            character_url=Mock(return_value="/"),
        )

        self.assertTrue(ui.dialog_widget.opened)
        self.assertEqual(ui.select_calls[0][1], "")
        self.assertIn("", ui.select_calls[0][0])
        self.assertEqual(ui.select_calls[2][1], "")
        self.assertIn("", ui.select_calls[2][0])


if __name__ == "__main__":
    unittest.main()
