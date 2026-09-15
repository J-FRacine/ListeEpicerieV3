from __future__ import annotations

import ast
from pathlib import Path
import unittest

import app_versions

ROOT = Path(__file__).resolve().parents[1]


class SpellArchitectureTests(unittest.TestCase):
    def test_phase15a_keeps_official_version_180_during_validation(self):
        self.assertEqual(app_versions.APP_VERSIONS["rpg"], "1.8.0")

    def test_schema_is_automatic_and_non_destructive(self):
        source = (ROOT / "rpg_character_spell_schema.py").read_text(encoding="utf-8")
        upper = source.upper()
        self.assertIn("CREATE TABLE IF NOT EXISTS RPG_CHARACTER_SPELLCASTING_PROFILES", upper)
        self.assertIn("CREATE TABLE IF NOT EXISTS RPG_CHARACTER_PREPARED_SPELLS", upper)
        self.assertIn("ON DELETE CASCADE", upper)
        self.assertNotIn("DROP TABLE", upper)
        self.assertNotIn("TRUNCATE", upper)

    def test_facade_wires_spells_panel(self):
        source = (ROOT / "rpg_character.py").read_text(encoding="utf-8")
        text = ast.unparse(ast.parse(source))
        self.assertIn("from rpg_character_spells import build_spells_panel", text)
        self.assertIn("_impl._spells_panel = _spells_panel", text)
        for name in (
            "get_spellcasting_profile",
            "save_spellcasting_profile",
            "list_prepared_spells",
            "save_prepared_spell",
            "set_prepared_spell_used_count",
            "reset_spell_usage",
        ):
            self.assertIn(name, source)

    def test_ui_contains_spells_tab_and_routes(self):
        source = (ROOT / "rpg_character_ui.py").read_text(encoding="utf-8")
        text = ast.unparse(ast.parse(source))
        self.assertIn("spells_tab = ui.tab('Sorts', icon='auto_stories')", text)
        self.assertIn("'sorts': spells_tab", text)
        self.assertIn("'spells': spells_tab", text)
        self.assertIn("_spells_panel(user_id, character)", text)

    def test_spells_ui_tracks_preparation_usage_domains_and_reset(self):
        source = (ROOT / "rpg_character_spells.py").read_text(encoding="utf-8")
        for expected in (
            "Préparer un sort",
            "Emplacements du jour",
            "Sorts de domaine disponibles",
            "Nouvelle prière / repos",
            "Marquer 1 emplacement utilisé",
            "Réutilisable",
            "Préparé {prepared_count}",
            "Utilisé {used_count}",
            "Restant {remaining}",
            "Normaux : {normal_remaining} restant(s)",
            "Domaine : {domain_remaining} restant",
        ):
            self.assertIn(expected, source)

    def test_catalog_and_rules_are_kept_out_of_main_ui_shell(self):
        ui_path = ROOT / "rpg_character_ui.py"
        self.assertLess(ui_path.stat().st_size, 32_000)
        self.assertTrue((ROOT / "rpg_character_spell_catalog.py").exists())
        self.assertTrue((ROOT / "rpg_character_spell_rules.py").exists())
        self.assertTrue((ROOT / "rpg_character_spell_data.py").exists())


if __name__ == "__main__":
    unittest.main()
