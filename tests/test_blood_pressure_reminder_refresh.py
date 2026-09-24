from __future__ import annotations

from datetime import date, time
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import app_versions


ROOT = Path(__file__).resolve().parents[1]
BLOOD_PRESSURE_PATH = ROOT / "blood_pressure.py"
BLOOD_PRESSURE_DATA_PATH = ROOT / "blood_pressure_data.py"


def _load_blood_pressure_data_without_psycopg():
    """Charge le module de données avec un faux ``db`` limité à ce test.

    Le poste de validation peut ne pas avoir le pilote PostgreSQL ``psycopg``.
    Ces tests utilisent déjà une connexion simulée et ne doivent donc pas
    dépendre du pilote réel ni tenter une connexion de production.
    """

    fake_db = types.ModuleType("db")

    def unavailable_connection():
        raise AssertionError(
            "Une connexion PostgreSQL réelle ne doit pas être ouverte par ce test."
        )

    fake_db.get_connection = unavailable_connection
    previous_db = sys.modules.get("db")
    sys.modules["db"] = fake_db
    try:
        spec = importlib.util.spec_from_file_location(
            "_blood_pressure_data_test_target",
            BLOOD_PRESSURE_DATA_PATH,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("Impossible de charger blood_pressure_data.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_db is None:
            sys.modules.pop("db", None)
        else:
            sys.modules["db"] = previous_db


blood_pressure_data = _load_blood_pressure_data_without_psycopg()


SLOTS = [
    {
        "id": 1,
        "label": "Matin",
        "start_time": time(6, 0),
        "end_time": time(11, 0),
        "notify_enabled": True,
        "notify_time": time(10, 0),
        "sort_order": 0,
    },
    {
        "id": 2,
        "label": "Soir",
        "start_time": time(17, 0),
        "end_time": time(22, 0),
        "notify_enabled": True,
        "notify_time": time(21, 0),
        "sort_order": 1,
    },
]


class FakeCursor:
    def __init__(self, settings, readings_by_date):
        self.settings = settings
        self.readings_by_date = readings_by_date
        self.last_sql = ""
        self.last_params = None
        self.executions = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.last_sql = sql
        self.last_params = params
        self.executions.append((sql, params))

    def fetchone(self):
        if "FROM blood_pressure_reminder_settings" in self.last_sql:
            return dict(self.settings)
        raise AssertionError(f"fetchone inattendu pour: {self.last_sql}")

    def fetchall(self):
        if "FROM blood_pressure_readings" not in self.last_sql:
            raise AssertionError(f"fetchall inattendu pour: {self.last_sql}")
        wanted_date = self.last_params[1]
        return [dict(row) for row in self.readings_by_date.get(wanted_date, [])]


class FakeConnection:
    def __init__(self, settings, readings_by_date):
        self.cursor_object = FakeCursor(settings, readings_by_date)
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_object

    def commit(self):
        self.commits += 1


class BloodPressureReminderRefreshTests(unittest.TestCase):
    def setUp(self):
        self.settings = {
            "enabled": True,
            "target_per_day": 2,
            "start_date": date(2026, 9, 1),
            "end_date": date(2026, 9, 30),
        }
        self.last_connection = None

    def status(self, readings_by_date, on_date, current_time):
        connection = FakeConnection(self.settings, readings_by_date)
        self.last_connection = connection
        with patch.object(
            blood_pressure_data,
            "get_connection",
            return_value=connection,
        ), patch.object(
            blood_pressure_data,
            "_ensure_reminder_slots",
            return_value=[dict(row) for row in SLOTS],
        ):
            return blood_pressure_data.get_blood_pressure_reminder_status(
                42,
                on_date,
                current_time,
            )

    def test_zero_reading_means_two_remaining(self):
        status = self.status({}, "2026-09-18", "07:00")
        self.assertTrue(status["active"])
        self.assertEqual(status["completed_count"], 0)
        self.assertEqual(status["remaining_count"], 2)
        self.assertEqual(status["state"], "due")
        self.assertEqual(status["next_slot"]["label"], "Matin")

    def test_one_reading_means_one_remaining(self):
        status = self.status(
            {
                date(2026, 9, 18): [
                    {"id": 10, "measured_time": time(8, 15)},
                ]
            },
            "2026-09-18",
            "12:00",
        )
        self.assertEqual(status["completed_count"], 1)
        self.assertEqual(status["remaining_count"], 1)
        self.assertEqual(status["state"], "upcoming")
        self.assertEqual(status["next_slot"]["label"], "Soir")

    def test_two_readings_complete_the_day(self):
        status = self.status(
            {
                date(2026, 9, 18): [
                    {"id": 10, "measured_time": time(8, 15)},
                    {"id": 11, "measured_time": time(19, 40)},
                ]
            },
            "2026-09-18",
            "20:00",
        )
        self.assertEqual(status["completed_count"], 2)
        self.assertEqual(status["remaining_count"], 0)
        self.assertEqual(status["state"], "complete")
        self.assertIsNone(status["next_slot"])

    def test_extra_reading_does_not_exceed_daily_target(self):
        status = self.status(
            {
                date(2026, 9, 18): [
                    {"id": 10, "measured_time": time(7, 0)},
                    {"id": 11, "measured_time": time(18, 0)},
                    {"id": 12, "measured_time": time(21, 0)},
                ]
            },
            "2026-09-18",
            "21:30",
        )
        self.assertEqual(status["total_readings_count"], 3)
        self.assertEqual(status["completed_count"], 2)
        self.assertEqual(status["remaining_count"], 0)

    def test_readings_outside_suggested_ranges_still_count(self):
        status = self.status(
            {
                date(2026, 9, 18): [
                    {"id": 10, "measured_time": time(5, 30)},
                    {"id": 11, "measured_time": time(23, 10)},
                ]
            },
            "2026-09-18",
            "23:20",
        )
        self.assertEqual(status["completed_count"], 2)
        self.assertEqual(status["state"], "complete")

    def test_day_rollover_uses_the_requested_local_date(self):
        readings = {
            date(2026, 9, 17): [
                {"id": 10, "measured_time": time(8, 0)},
                {"id": 11, "measured_time": time(20, 0)},
            ],
            date(2026, 9, 18): [],
        }
        previous_day = self.status(readings, "2026-09-17", "23:59")
        self.assertEqual(previous_day["completed_count"], 2)
        new_day = self.status(readings, "2026-09-18", "00:01")
        self.assertEqual(new_day["completed_count"], 0)
        self.assertEqual(new_day["remaining_count"], 2)

    def test_database_query_receives_normalized_local_date(self):
        self.status({}, "2026-09-18", "09:30")
        reading_queries = [
            params
            for sql, params in self.last_connection.cursor_object.executions
            if "FROM blood_pressure_readings" in sql
        ]
        self.assertEqual(reading_queries, [(42, date(2026, 9, 18))])

    def test_client_time_initializers_use_nicegui_timers(self):
        source = BLOOD_PRESSURE_PATH.read_text(encoding="utf-8")
        self.assertIn("ui.timer(\n        0.15,\n        load_status_after_mount,\n        once=True,", source)
        self.assertIn("ui.timer(\n                    0.15,\n                    use_device_after_mount,\n                    once=True,", source)
        self.assertIn("ui.timer(\n                    0.15,\n                    refresh_reminder_after_mount,\n                    once=True,", source)
        self.assertNotIn("_start_background_task(\n        load_status_after_mount()", source)
        self.assertNotIn("_start_background_task(\n                    use_device_after_mount()", source)
        self.assertNotIn("_start_background_task(\n                    refresh_reminder_after_mount()", source)

    def test_official_version_is_123(self):
        self.assertEqual(
            app_versions.APP_VERSIONS["blood_pressure"],
            "1.2.3",
        )


if __name__ == "__main__":
    unittest.main()
