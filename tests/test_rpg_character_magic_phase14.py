from __future__ import annotations

from decimal import Decimal
import unittest

from rpg_character_magic_catalog import (
    MAGIC_ITEM_TEMPLATES,
    cure_light_wounds_effect,
    magic_template_values,
)
from rpg_character_magic_rules import (
    add_magic_save_bonuses,
    container_capacity_state,
    container_loads,
    magic_resistance_bonus,
    merge_equipment_with_magic_details,
    prepare_equipment_for_encumbrance,
    validate_container_preview,
)


class MagicCatalogTests(unittest.TestCase):
    def test_three_reference_templates_are_available(self):
        self.assertEqual(
            set(MAGIC_ITEM_TEMPLATES),
            {
                "cloak_resistance",
                "wand_cure_light_wounds",
                "handy_haversack",
            },
        )

    def test_reference_values(self):
        cloak = magic_template_values("cloak_resistance")
        self.assertEqual(cloak["weight_each"], 1)
        self.assertEqual(cloak["magic_resistance_bonus"], 1)
        self.assertTrue(cloak["magic_requires_equipped"])

        wand = magic_template_values("wand_cure_light_wounds")
        self.assertEqual(wand["magic_charges_current"], 50)
        self.assertEqual(wand["magic_charges_max"], 50)
        self.assertEqual(wand["magic_caster_level"], 1)
        self.assertEqual(
            wand["magic_contained_spell_name"],
            "Cure Light Wounds",
        )

        haversack = magic_template_values("handy_haversack")
        self.assertEqual(haversack["weight_each"], 5)
        self.assertEqual(haversack["magic_capacity_weight"], 120)
        self.assertEqual(haversack["magic_kind"], "container")

    def test_cure_light_wounds_effect_is_capped_at_plus_five(self):
        self.assertEqual(cure_light_wounds_effect(1), "1d8+1 PV")
        self.assertEqual(cure_light_wounds_effect(5), "1d8+5 PV")
        self.assertEqual(cure_light_wounds_effect(12), "1d8+5 PV")


class MagicRulesTests(unittest.TestCase):
    def test_resistance_uses_best_active_bonus_only(self):
        equipment = [
            {
                "is_magic_item": True,
                "carried": True,
                "equipped": True,
                "magic_requires_equipped": True,
                "magic_resistance_bonus": 2,
            },
            {
                "is_magic_item": True,
                "carried": True,
                "equipped": True,
                "magic_requires_equipped": True,
                "magic_resistance_bonus": 4,
            },
            {
                "is_magic_item": True,
                "carried": True,
                "equipped": False,
                "magic_requires_equipped": True,
                "magic_resistance_bonus": 5,
            },
        ]
        self.assertEqual(magic_resistance_bonus(equipment), 4)

    def test_resistance_applies_only_to_three_standard_saves(self):
        saves = [
            {"save_key": "fortitude"},
            {"save_key": "reflex"},
            {"save_key": "will"},
            {"save_key": "fear"},
        ]
        equipment = [{
            "is_magic_item": True,
            "carried": True,
            "equipped": True,
            "magic_requires_equipped": True,
            "magic_resistance_bonus": 3,
        }]
        result = add_magic_save_bonuses(saves, equipment)
        self.assertEqual(
            [row["magic_item_bonus"] for row in result],
            [3, 3, 3, 0],
        )

    def test_haversack_contents_do_not_add_to_encumbrance(self):
        rows = [
            {
                "id": 1,
                "item_name": "Handy Haversack",
                "weight_each": 5,
                "quantity": 1,
                "carried": True,
                "magic_kind": "container",
            },
            {
                "id": 2,
                "item_name": "Rope",
                "weight_each": 10,
                "quantity": 2,
                "carried": True,
                "container_equipment_id": 1,
            },
        ]
        prepared = prepare_equipment_for_encumbrance(rows)
        by_id = {row["id"]: row for row in prepared}
        self.assertEqual(by_id[1]["weight_each"], 5)
        self.assertEqual(by_id[2]["weight_each"], 0)
        self.assertEqual(by_id[2]["_actual_weight_each"], 10)

    def test_container_load_and_remaining_capacity(self):
        rows = [
            {
                "id": 1,
                "magic_kind": "container",
                "magic_capacity_weight": 120,
            },
            {
                "id": 2,
                "weight_each": 10,
                "quantity": 2,
                "container_equipment_id": 1,
            },
            {
                "id": 3,
                "weight_each": 3,
                "quantity": 4,
                "container_equipment_id": 1,
            },
        ]
        self.assertEqual(container_loads(rows)[1], Decimal("32"))
        state = container_capacity_state(rows, 1)
        self.assertEqual(state["load"], Decimal("32"))
        self.assertEqual(state["remaining"], Decimal("88"))
        self.assertFalse(state["over_capacity"])

    def test_preview_blocks_over_capacity_and_nested_magic_container(self):
        rows = [{
            "id": 1,
            "magic_kind": "container",
            "magic_capacity_weight": 20,
        }]
        with self.assertRaises(ValueError):
            validate_container_preview(
                rows,
                {
                    "quantity": 1,
                    "weight_each": 21,
                    "magic_enabled": False,
                },
                container_equipment_id=1,
            )
        with self.assertRaises(ValueError):
            validate_container_preview(
                rows,
                {
                    "quantity": 1,
                    "weight_each": 5,
                    "magic_enabled": True,
                    "magic_kind": "container",
                },
                equipment_id=2,
                container_equipment_id=1,
            )

    def test_preview_blocks_self_containment(self):
        rows = [{
            "id": 7,
            "magic_kind": "container",
            "magic_capacity_weight": 120,
        }]
        with self.assertRaises(ValueError):
            validate_container_preview(
                rows,
                {
                    "quantity": 1,
                    "weight_each": 5,
                    "magic_enabled": False,
                },
                equipment_id=7,
                container_equipment_id=7,
            )

    def test_merge_adds_magic_and_container_metadata(self):
        merged = merge_equipment_with_magic_details(
            [{"id": 2, "item_name": "Wand"}],
            {
                2: {
                    "magic_kind": "charges",
                    "charges_current": 12,
                    "charges_max": 50,
                }
            },
            {
                2: {
                    "container_equipment_id": 1,
                    "container_equipment_name": "Handy Haversack",
                }
            },
        )
        self.assertTrue(merged[0]["is_magic_item"])
        self.assertEqual(merged[0]["magic_charges_current"], 12)
        self.assertEqual(merged[0]["container_equipment_id"], 1)


if __name__ == "__main__":
    unittest.main()
