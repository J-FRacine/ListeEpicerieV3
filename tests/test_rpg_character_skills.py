from __future__ import annotations

from decimal import Decimal
import ast
from pathlib import Path
import unittest
from unittest.mock import MagicMock, Mock

from rpg_character_skills import build_skills_panel

ROOT = Path(__file__).resolve().parents[1]
SKILLS_PATH = ROOT / "rpg_character_skills.py"


def widget(value=None):
    item = MagicMock()
    item.value = value
    item.classes.return_value = item
    item.props.return_value = item
    item.tooltip.return_value = item
    item.on_value_change.return_value = item
    item.on.return_value = item
    item.__enter__.return_value = item
    item.__exit__.return_value = False
    return item


def make_ui():
    ui = MagicMock()
    for name in ("row", "column", "card", "element", "expansion", "dialog"):
        getattr(ui, name).side_effect = lambda *a, **k: widget()
    for name in ("label", "icon", "button"):
        getattr(ui, name).side_effect = lambda *a, **k: widget()
    ui.toggle.side_effect = lambda *a, **k: widget(k.get("value"))
    ui.input.side_effect = lambda *a, **k: widget(k.get("value", ""))
    ui.number.side_effect = lambda *a, **k: widget(k.get("value"))
    ui.select.side_effect = lambda *a, **k: widget(k.get("value"))
    ui.checkbox.side_effect = lambda *a, **k: widget(k.get("value", False))
    return ui


def audit(warnings=None):
    return {
        "reference_checks_passed": 12,
        "reference_checks_total": 12,
        "warnings": list(warnings or []),
    }


def dependencies(ui, skills, warnings=None):
    return dict(
        ui=ui,
        user_id=7,
        character={"id": 42},
        list_rpg_skills=Mock(return_value=skills),
        character_sheet_audit=Mock(return_value=audit(warnings)),
        create_custom_rpg_skill=Mock(),
        delete_custom_rpg_skill=Mock(),
        update_rpg_skills=Mock(),
        skill_total=Mock(return_value=Decimal("5")),
        skill_breakdown=Mock(
            return_value={
                "ability_key": "wis",
                "ability_modifier": 2,
                "ranks": 1,
                "class_bonus": 3,
                "misc_modifier": 0,
                "armor_penalty": 0,
                "total": 6,
            }
        ),
        format_number=str,
        ability_labels={"wis": "SAG"},
        skill_dialog=Mock(),
        skill_display_name=lambda fr, en: f"{fr} — {en}" if en else fr,
        skill_breakdown_text=lambda row: "calcul",
        notify_error=Mock(),
        character_url=Mock(return_value="/jdr"),
        calculation_rules_dialog=Mock(),
    )


class SkillsPanelTests(unittest.TestCase):
    def test_audit_expansion_is_collapsed_by_default(self):
        ui = make_ui()
        kwargs = dependencies(
            ui,
            [],
            warnings=[
                {
                    "severity": "warning",
                    "title": "À vérifier",
                    "detail": "Détail",
                }
            ],
        )
        build_skills_panel(**kwargs)

        expansion = next(
            call
            for call in ui.expansion.call_args_list
            if call.args and call.args[0] == "Afficher les points à vérifier"
        )
        self.assertIs(expansion.kwargs["value"], False)
        kwargs["list_rpg_skills"].assert_called_once_with(7, 42)
        kwargs["character_sheet_audit"].assert_called_once_with(
            {"id": 42}, []
        )

    def test_save_reuses_existing_update_api_and_returns_to_skills(self):
        ui = make_ui()
        skill = {
            "id": 8,
            "skill_name": "Perception",
            "english_name": "Perception",
            "ability_key": "wis",
            "class_skill": True,
            "trained_only": False,
            "armor_check_applies": False,
            "double_armor_penalty": False,
            "ranks": Decimal("1"),
            "misc_modifier": 0,
            "is_custom": False,
        }
        kwargs = dependencies(ui, [skill])
        build_skills_panel(**kwargs)

        save_call = next(
            call
            for call in ui.button.call_args_list
            if call.args and call.args[0] == "Enregistrer les compétences"
        )
        save_call.kwargs["on_click"]()

        kwargs["update_rpg_skills"].assert_called_once()
        user_id, character_id, rows = kwargs["update_rpg_skills"].call_args.args
        self.assertEqual((user_id, character_id), (7, 42))
        self.assertEqual(rows[0]["id"], 8)
        self.assertEqual(rows[0]["skill_name"], "Perception")
        kwargs["character_url"].assert_called_with(42, "competences")
        ui.navigate.to.assert_called_with("/jdr")

    def test_extracted_module_has_no_framework_or_back_reference(self):
        parsed = ast.parse(SKILLS_PATH.read_text(encoding="utf-8"))
        imports = {
            node.module
            for node in ast.walk(parsed)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        imports |= {
            alias.name
            for node in ast.walk(parsed)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertTrue(
            {"nicegui", "db", "rpg_character", "rpg_character_ui"}.isdisjoint(
                imports
            )
        )
        functions = {
            node.name
            for node in parsed.body
            if isinstance(node, ast.FunctionDef)
        }
        self.assertEqual(functions, {"build_skills_panel"})


if __name__ == "__main__":
    unittest.main()
