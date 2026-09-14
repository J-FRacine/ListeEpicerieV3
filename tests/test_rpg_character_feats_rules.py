from __future__ import annotations

import unittest

from rpg_character_feats_rules import (
    collect_feat_combat_effects,
)


class FeatCombatRulesTests(unittest.TestCase):
    def test_passive_and_selected_active_feats_are_applied(self):
        feats = [
            {
                "id": 1,
                "feat_name": "Science de l’initiative",
                "feat_kind": "passive",
                "initiative_modifier": 4,
                "attack_modifier": 0,
                "cmb_modifier": 0,
                "cmd_modifier": 0,
                "save_modifier": 0,
            },
            {
                "id": 2,
                "feat_name": "Attaque en puissance",
                "feat_kind": "active",
                "attack_modifier": -2,
                "damage_note": "+4 dégâts",
                "initiative_modifier": 0,
                "cmb_modifier": -2,
                "cmd_modifier": 0,
                "save_modifier": 0,
            },
        ]

        effects = collect_feat_combat_effects(
            feats,
            active_feat_ids={2},
            selected_attack_id=8,
        )

        self.assertEqual(effects["initiative_modifier"], 4)
        self.assertEqual(effects["attack_modifier"], -2)
        self.assertEqual(effects["cmb_modifier"], -2)
        self.assertEqual(effects["damage_notes"], ["+4 dégâts"])
        self.assertEqual(
            [row["id"] for row in effects["applied_feats"]],
            [1, 2],
        )

    def test_unselected_active_and_info_feats_do_not_modify(self):
        feats = [
            {
                "id": 2,
                "feat_name": "Actif",
                "feat_kind": "active",
                "attack_modifier": 8,
            },
            {
                "id": 3,
                "feat_name": "Info",
                "feat_kind": "info",
                "initiative_modifier": 9,
            },
        ]

        effects = collect_feat_combat_effects(
            feats,
            active_feat_ids=set(),
            selected_attack_id=1,
        )
        self.assertEqual(effects["attack_modifier"], 0)
        self.assertEqual(effects["initiative_modifier"], 0)
        self.assertEqual(effects["applied_feats"], [])

    def test_linked_attack_modifier_only_applies_to_matching_attack(self):
        feat = {
            "id": 5,
            "feat_name": "Arme de prédilection",
            "feat_kind": "passive",
            "linked_attack_id": 17,
            "attack_modifier": 1,
            "damage_note": "",
        }

        wrong = collect_feat_combat_effects(
            [feat],
            selected_attack_id=18,
        )
        right = collect_feat_combat_effects(
            [feat],
            selected_attack_id=17,
        )

        self.assertEqual(wrong["attack_modifier"], 0)
        self.assertEqual(right["attack_modifier"], 1)

    def test_save_targets_can_be_specific_or_global(self):
        feats = [
            {
                "id": 1,
                "feat_name": "Vigueur",
                "feat_kind": "passive",
                "save_key": "fortitude",
                "save_modifier": 2,
            },
            {
                "id": 2,
                "feat_name": "Tous",
                "feat_kind": "passive",
                "save_key": "all",
                "save_modifier": 1,
            },
        ]

        effects = collect_feat_combat_effects(feats)
        self.assertEqual(
            effects["save_modifiers"],
            {"fortitude": 2, "all": 1},
        )


if __name__ == "__main__":
    unittest.main()
