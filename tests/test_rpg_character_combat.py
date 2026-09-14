from __future__ import annotations

from unittest.mock import MagicMock, Mock
import unittest

from rpg_character_combat import build_combat_panel


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

    def set_text(self, *args, **kwargs):
        return None

    def set_visibility(self, *args, **kwargs):
        return None

    def update(self, *args, **kwargs):
        return None

    def on_value_change(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def character():
    row = {
        "id": 42,
        "max_hp": 30,
        "current_hp": 24,
        "nonlethal_damage": 0,
        "speed": "",
        "base_speed": 30,
        "final_speed": 20,
        "damage_reduction": "",
        "spell_resistance": None,
        "base_attack_bonus": 3,
        "armor_bonus": 0,
        "shield_bonus": 0,
        "natural_armor_bonus": 0,
        "deflection_bonus": 0,
        "misc_ac_modifier": 0,
        "armor_check_penalty": 0,
        "initiative_misc_modifier": 0,
        "cmb_misc_modifier": 0,
        "cmd_misc_modifier": 0,
        "grapple_misc_modifier": 0,
    }
    for key, score in {
        "str": 14,
        "dex": 14,
        "con": 12,
        "int": 10,
        "wis": 18,
        "cha": 14,
    }.items():
        row[f"{key}_score"] = score
        row[f"{key}_temp_score"] = None
    return row


def equipment_effects():
    return {
        "final_speed": 20,
        "carrying_capacity": {"light_max": 58},
        "equipped_armor": {"item_name": "Breastplate"},
        "equipped_shield": {"item_name": "Bouclier"},
        "effective_max_dex_bonus": 3,
        "carried_weight": 55,
        "load_label": "Légère",
        "base_speed": 30,
        "effective_armor_check_penalty": -4,
    }


class CombatPanelTests(unittest.TestCase):
    def make_ui(self):
        ui = MagicMock()

        def context_widget(*args, **kwargs):
            return Widget()

        for name in ("card", "row", "column", "element"):
            getattr(ui, name).side_effect = context_widget

        ui.label.side_effect = lambda *a, **k: Widget()
        ui.number.side_effect = lambda *a, **k: Widget(value=k.get("value"))
        ui.input.side_effect = lambda *a, **k: Widget(value=k.get("value"))
        ui.button.side_effect = lambda *a, **k: Widget()

        def refreshable(func):
            func.refresh = Mock()
            return func

        ui.refreshable.side_effect = refreshable
        return ui

    def dependencies(self, ui, *, update=None, rules=None):
        equipment = [{"id": 1, "item_name": "Breastplate"}]
        list_equipment = Mock(return_value=equipment)

        def apply_effects(draft, rows):
            self.assertIs(rows, equipment)
            enriched = dict(draft)
            enriched["equipment_effects"] = equipment_effects()
            return enriched

        return {
            "ui": ui,
            "user_id": 7,
            "character": character(),
            "list_rpg_equipment": list_equipment,
            "ability_labels": {
                "str": "FOR",
                "dex": "DEX",
                "con": "CON",
                "int": "INT",
                "wis": "SAG",
                "cha": "CHA",
            },
            "ability_long_labels": {
                "str": "Force",
                "dex": "Dextérité",
                "con": "Constitution",
                "int": "Intelligence",
                "wis": "Sagesse",
                "cha": "Charisme",
            },
            "ability_modifier": lambda score, temp=None: (
                int(((temp if temp is not None else score) - 10) // 2)
            ),
            "format_modifier": lambda value: f"{int(value):+d}",
            "apply_equipment_effects": apply_effects,
            "armor_class_total": Mock(return_value=21),
            "touch_armor_class": Mock(return_value=12),
            "flat_footed_armor_class": Mock(return_value=19),
            "initiative_total": Mock(return_value=2),
            "cmb_total": Mock(return_value=5),
            "cmd_total": Mock(return_value=17),
            "format_number": str,
            "update_rpg_character_combat": update or Mock(),
            "notify_error": Mock(),
            "character_url": Mock(return_value="/?tab=jdr&character=42&section=combat"),
            "calculation_rules_dialog": rules or Mock(),
        }

    def test_reads_equipment_and_renders_equipment_aware_preview(self):
        ui = self.make_ui()
        deps = self.dependencies(ui)

        build_combat_panel(**deps)

        deps["list_rpg_equipment"].assert_called_once_with(7, 42)
        labels = [
            call.args[0]
            for call in ui.label.call_args_list
            if call.args
        ]
        self.assertIn("Caractéristiques", labels)
        self.assertIn("Combat et défenses", labels)
        self.assertIn("Équipement et encombrement", labels)
        self.assertTrue(
            any(
                isinstance(value, str)
                and "Breastplate" in value
                and "Bouclier" in value
                for value in labels
            )
        )

    def test_save_uses_existing_combat_update_and_navigates(self):
        ui = self.make_ui()
        update = Mock()
        deps = self.dependencies(ui, update=update)

        build_combat_panel(**deps)

        save_call = next(
            call
            for call in ui.button.call_args_list
            if call.args
            and call.args[0] == "Enregistrer les caractéristiques"
        )
        save_call.kwargs["on_click"]()

        update.assert_called_once()
        user_id, character_id, values = update.call_args.args
        self.assertEqual((user_id, character_id), (7, 42))
        self.assertEqual(values["wis_score"], 18)
        self.assertEqual(values["base_attack_bonus"], 3)
        self.assertEqual(
            values["equipment_effects"]["equipped_armor"]["item_name"],
            "Breastplate",
        )
        deps["character_url"].assert_called_once_with(42, "combat")
        ui.navigate.to.assert_called_once_with(
            "/?tab=jdr&character=42&section=combat"
        )

    def test_rules_button_uses_current_equipment_aware_draft(self):
        ui = self.make_ui()
        rules = Mock()
        deps = self.dependencies(ui, rules=rules)

        build_combat_panel(**deps)

        rules_call = next(
            call
            for call in ui.button.call_args_list
            if call.args and call.args[0] == "Règles de calcul"
        )
        rules_call.kwargs["on_click"]()

        rules.assert_called_once()
        user_id, draft = rules.call_args.args
        self.assertEqual(user_id, 7)
        self.assertEqual(draft["equipment_effects"]["final_speed"], 20)


if __name__ == "__main__":
    unittest.main()
