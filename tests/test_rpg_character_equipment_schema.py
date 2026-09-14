from __future__ import annotations

import unittest
from unittest.mock import Mock

import rpg_character_equipment_schema as schema


class Cursor:
    def __init__(self):
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, statement):
        self.statements.append(statement)


class Connection:
    def __init__(self):
        self.cursor_value = Cursor()
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commits += 1


class EquipmentSchemaTests(unittest.TestCase):
    def setUp(self):
        schema._schema_ready = False

    def test_migration_adds_detailed_equipment_columns_without_deleting_data(self):
        connection = Connection()
        get_connection = Mock(return_value=connection)

        schema.ensure_equipment_schema(get_connection=get_connection)

        sql = "\n".join(connection.cursor_value.statements)
        for column in (
            "armor_category",
            "armor_bonus",
            "shield_bonus",
            "enhancement_bonus",
            "max_dex_bonus",
            "armor_check_penalty",
            "arcane_spell_failure",
            "speed_reduction_applies",
            "reduced_speed_override",
            "proficiency_required",
        ):
            self.assertIn(f"ADD COLUMN IF NOT EXISTS {column}", sql)

        self.assertNotIn("DROP TABLE", sql.upper())
        self.assertNotIn("TRUNCATE", sql.upper())
        self.assertNotIn("DELETE FROM", sql.upper())
        self.assertEqual(connection.commits, 1)

    def test_migration_runs_once_per_process_after_success(self):
        connection = Connection()
        get_connection = Mock(return_value=connection)

        schema.ensure_equipment_schema(get_connection=get_connection)
        schema.ensure_equipment_schema(get_connection=get_connection)

        get_connection.assert_called_once_with()
        self.assertEqual(connection.commits, 1)


if __name__ == "__main__":
    unittest.main()
