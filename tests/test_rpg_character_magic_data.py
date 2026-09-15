from __future__ import annotations

import sys
import types
from unittest import TestCase
from unittest.mock import patch

_db_stub = types.ModuleType("db")
_db_stub.get_connection = lambda: None
sys.modules.setdefault("db", _db_stub)

import rpg_character_magic_data as magic_data


class _Cursor:
    def __init__(self, *, capacity=120, selected_rows=None):
        self.capacity = capacity
        self.selected_rows = list(selected_rows or [])
        self._one = None
        self._all = []
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(str(sql).split())
        self.executed.append((normalized, params))

        if "FROM rpg_characters" in normalized:
            self._one = {"id": 42}
            self._all = []
        elif (
            "FROM rpg_character_equipment" in normalized
            and "LEFT JOIN" not in normalized
        ):
            self._one = {
                "id": 10,
                "item_name": "Handy Haversack",
                "item_type": "gear",
                "quantity": 1,
                "weight_each": 5,
            }
            self._all = []
        elif (
            "SELECT magic_kind, capacity_weight" in normalized
            and "rpg_character_magic_item_details" in normalized
        ):
            self._one = {
                "magic_kind": "container",
                "capacity_weight": self.capacity,
            }
            self._all = []
        elif "LEFT JOIN rpg_character_magic_item_details" in normalized:
            self._one = None
            self._all = list(self.selected_rows)
        else:
            self._one = None
            self._all = []

    def fetchone(self):
        return self._one

    def fetchall(self):
        return list(self._all)


class _Connection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1


class MagicContainerDataTests(TestCase):
    def _patch_connection(self, connection):
        return patch.multiple(
            magic_data,
            get_connection=lambda: connection,
            ensure_equipment_schema=lambda **_kwargs: None,
            ensure_magic_item_schema=lambda **_kwargs: None,
        )

    def test_replaces_container_contents_in_one_transaction(self):
        cursor = _Cursor(selected_rows=[
            {
                "id": 2,
                "item_name": "Corde",
                "quantity": 1,
                "weight_each": 10,
                "child_magic_kind": None,
            },
            {
                "id": 3,
                "item_name": "Wand",
                "quantity": 1,
                "weight_each": 0,
                "child_magic_kind": "charges",
            },
        ])
        connection = _Connection(cursor)

        with self._patch_connection(connection):
            count = magic_data.set_magic_container_contents(
                7,
                42,
                10,
                [2, 3],
            )

        self.assertEqual(count, 2)
        self.assertEqual(connection.commits, 1)
        delete_queries = [
            sql for sql, _params in cursor.executed
            if sql.startswith(
                "DELETE FROM rpg_character_equipment_containment"
            )
        ]
        insert_queries = [
            sql for sql, _params in cursor.executed
            if sql.startswith(
                "INSERT INTO rpg_character_equipment_containment"
            )
        ]
        self.assertEqual(len(delete_queries), 1)
        self.assertEqual(len(insert_queries), 2)

    def test_over_capacity_stops_before_any_containment_write(self):
        cursor = _Cursor(
            capacity=20,
            selected_rows=[{
                "id": 2,
                "item_name": "Objet lourd",
                "quantity": 1,
                "weight_each": 25,
                "child_magic_kind": None,
            }],
        )
        connection = _Connection(cursor)

        with self._patch_connection(connection):
            with self.assertRaisesRegex(ValueError, "capacité"):
                magic_data.set_magic_container_contents(
                    7,
                    42,
                    10,
                    [2],
                )

        self.assertEqual(connection.commits, 0)
        self.assertFalse(any(
            sql.startswith("DELETE FROM rpg_character_equipment_containment")
            or sql.startswith("INSERT INTO rpg_character_equipment_containment")
            for sql, _params in cursor.executed
        ))

    def test_nested_magic_container_is_rejected(self):
        cursor = _Cursor(selected_rows=[{
            "id": 2,
            "item_name": "Autre sac magique",
            "quantity": 1,
            "weight_each": 5,
            "child_magic_kind": "container",
        }])
        connection = _Connection(cursor)

        with self._patch_connection(connection):
            with self.assertRaisesRegex(ValueError, "conteneur magique"):
                magic_data.set_magic_container_contents(
                    7,
                    42,
                    10,
                    [2],
                )

        self.assertEqual(connection.commits, 0)


if __name__ == "__main__":
    import unittest
    unittest.main()
