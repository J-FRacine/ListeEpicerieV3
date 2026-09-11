from __future__ import annotations

import unittest
from unittest.mock import MagicMock, Mock

from rpg_character_identity import build_identity_panel


def widget(value=None):
    item = MagicMock()
    item.value = value
    item.classes.return_value = item
    item.props.return_value = item
    item.tooltip.return_value = item
    item.__enter__.return_value = item
    item.__exit__.return_value = False
    return item


def profile(key="human"):
    if key == "custom":
        return {
            "label": "Autre / personnalisée",
            "standard_traits": "",
            "size_key": "medium",
            "base_speed": 30,
            "creature_type": "Humanoïde",
            "subtypes": "",
            "vision": "",
            "languages": "",
            "ability_adjustments": "",
            "carrying_capacity_multiplier": 1,
            "is_quadruped": False,
            "ignore_armor_speed": False,
            "ignore_encumbrance_speed": False,
        }
    return {
        "label": "Humain",
        "standard_traits": "Don supplémentaire; compétence polyvalente",
        "size_key": "medium",
        "base_speed": 30,
        "creature_type": "Humanoïde",
        "subtypes": "humain",
        "vision": "normale",
        "languages": "commun",
        "ability_adjustments": "+2 à une caractéristique",
        "carrying_capacity_multiplier": 1,
        "is_quadruped": False,
        "ignore_armor_speed": False,
        "ignore_encumbrance_speed": False,
    }


def character():
    return {
        "id": 42,
        "character_name": "Aldren",
        "player_name": "JF",
        "campaign": "Ravenloft",
        "class_name": "Clerc",
        "subclass_name": "",
        "character_level": 4,
        "alignment": "NB",
        "deity": "Ezra",
        "age_text": "32",
        "gender": "Homme",
        "height_text": "1,78 m",
        "weight_text": "78 kg",
        "eyes": "Verts",
        "hair": "Noirs",
        "skin": "Claire",
        "experience_points": 9000,
        "race_key": "human",
        "race": "Humain",
        "race_heritage": "",
        "size_key": "medium",
        "base_speed": 30,
        "creature_type": "Humanoïde",
        "racial_subtypes": "humain",
        "vision": "normale",
        "languages": "commun",
        "racial_ability_adjustments": "+2 à une caractéristique",
        "carrying_capacity_multiplier": 1,
        "is_quadruped": False,
        "ignore_armor_speed": False,
        "ignore_encumbrance_speed": False,
        "alternate_racial_traits": "",
        "str_score": 14,
        "dex_score": 12,
        "con_score": 14,
        "int_score": 10,
        "wis_score": 18,
        "cha_score": 14,
    }


class IdentityPanelTests(unittest.TestCase):
    def make_ui(self):
        ui = MagicMock()
        generic = lambda *args, **kwargs: widget()
        ui.card.side_effect = generic
        ui.element.side_effect = generic
        ui.row.side_effect = generic
        ui.label.side_effect = generic
        ui.dialog.side_effect = generic
        ui.button.side_effect = generic
        return ui

    def test_save_identity_keeps_race_profile_separate_from_ability_scores(self):
        ui = self.make_ui()
        c = character()
        update = Mock()
        url = Mock(return_value="/?tab=jdr&character=42&section=identite")

        # 21 champs texte, dans l'ordre exact du panneau.
        text_values = [
            "Aldren", "JF", "Ravenloft", "Clerc", "",
            "NB", "Ezra", "32", "Homme", "1,78 m", "78 kg",
            "Verts", "Noirs", "Claire",
            "", "", "Humanoïde", "humain", "normale", "commun",
            "+2 à une caractéristique",
        ]
        ui.input.side_effect = [widget(v) for v in text_values]
        ui.number.side_effect = [
            widget(4),       # niveau
            widget(9000),    # XP
            widget(30),      # vitesse
            widget(1.0),     # charge
        ]
        ui.select.side_effect = [
            widget("human"),
            widget("medium"),
        ]
        ui.checkbox.side_effect = [
            widget(False),
            widget(False),
            widget(False),
        ]
        ui.textarea.return_value = widget("")

        build_identity_panel(
            ui=ui,
            user_id=7,
            character=c,
            race_labels={
                "human": "Humain",
                "custom": "Autre / personnalisée",
            },
            size_labels={"medium": "Moyenne"},
            infer_race_key=Mock(return_value="human"),
            get_race_profile=Mock(side_effect=profile),
            update_rpg_character_identity=update,
            notify_error=Mock(),
            character_url=url,
        )

        save_button = next(
            call for call in ui.button.call_args_list
            if call.args and call.args[0] == "Enregistrer l’identité"
        )
        save_button.kwargs["on_click"]()

        update.assert_called_once()
        user_id, character_id, values = update.call_args.args
        self.assertEqual((user_id, character_id), (7, 42))
        self.assertEqual(values["race_key"], "human")
        self.assertEqual(values["race"], "Humain")
        self.assertEqual(values["class_name"], "Clerc")
        self.assertEqual(values["character_level"], 4)
        self.assertEqual(values["base_speed"], 30)

        # Décision métier importante : changer/enregistrer la race ne touche
        # jamais directement aux six scores de caractéristiques.
        for ability in ("str", "dex", "con", "int", "wis", "cha"):
            self.assertNotIn(f"{ability}_score", values)
            self.assertNotIn(f"{ability}_temp_score", values)

        url.assert_called_once_with(42, "identite")
        ui.navigate.to.assert_called_once_with(
            "/?tab=jdr&character=42&section=identite"
        )

    def test_unknown_existing_race_falls_back_to_custom(self):
        ui = self.make_ui()
        c = character()
        c["race_key"] = "race_inconnue"

        ui.input.side_effect = [widget("") for _ in range(21)]
        ui.number.side_effect = [widget(4), widget(0), widget(30), widget(1.0)]
        race_select = widget("custom")
        ui.select.side_effect = [race_select, widget("medium")]
        ui.checkbox.side_effect = [widget(False), widget(False), widget(False)]
        ui.textarea.return_value = widget("")

        build_identity_panel(
            ui=ui,
            user_id=7,
            character=c,
            race_labels={
                "human": "Humain",
                "custom": "Autre / personnalisée",
            },
            size_labels={"medium": "Moyenne"},
            infer_race_key=Mock(return_value="custom"),
            get_race_profile=Mock(side_effect=profile),
            update_rpg_character_identity=Mock(),
            notify_error=Mock(),
            character_url=Mock(return_value="/jdr"),
        )

        self.assertEqual(race_select.value, "custom")

    def test_save_error_is_reported_without_success_navigation(self):
        ui = self.make_ui()
        c = character()
        error = ValueError("nom invalide")
        notify_error = Mock()

        ui.input.side_effect = [widget("") for _ in range(21)]
        ui.number.side_effect = [widget(4), widget(0), widget(30), widget(1.0)]
        ui.select.side_effect = [widget("human"), widget("medium")]
        ui.checkbox.side_effect = [widget(False), widget(False), widget(False)]
        ui.textarea.return_value = widget("")

        build_identity_panel(
            ui=ui,
            user_id=7,
            character=c,
            race_labels={
                "human": "Humain",
                "custom": "Autre / personnalisée",
            },
            size_labels={"medium": "Moyenne"},
            infer_race_key=Mock(return_value="human"),
            get_race_profile=Mock(side_effect=profile),
            update_rpg_character_identity=Mock(side_effect=error),
            notify_error=notify_error,
            character_url=Mock(return_value="/jdr"),
        )

        save_button = next(
            call for call in ui.button.call_args_list
            if call.args and call.args[0] == "Enregistrer l’identité"
        )
        save_button.kwargs["on_click"]()

        notify_error.assert_called_once_with(
            error,
            "L’identité n’a pas pu être enregistrée.",
        )
        ui.navigate.to.assert_not_called()


if __name__ == "__main__":
    unittest.main()
