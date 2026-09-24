from __future__ import annotations

from datetime import date, time
from pathlib import Path
import tempfile
import unittest

from blood_pressure_pdf import (
    build_blood_pressure_pdf,
    calculate_blood_pressure_averages,
)


ROOT = Path(__file__).resolve().parents[1]


READINGS = [
    {
        "id": 1,
        "measured_date": date(2026, 9, 20),
        "measured_time": time(8, 0),
        "systolic": 120,
        "diastolic": 80,
        "pulse": 60,
        "note": "Matin",
    },
    {
        "id": 2,
        "measured_date": date(2026, 9, 20),
        "measured_time": time(19, 0),
        "systolic": 130,
        "diastolic": 84,
        "pulse": 70,
        "note": "Soir",
    },
    {
        "id": 3,
        "measured_date": date(2026, 9, 21),
        "measured_time": time(7, 45),
        "systolic": 125,
        "diastolic": 82,
        "pulse": 65,
        "note": "",
    },
    {
        "id": 4,
        "measured_date": date(2026, 10, 1),
        "measured_time": time(8, 0),
        "systolic": 200,
        "diastolic": 100,
        "pulse": 100,
        "note": "Hors intervalle",
    },
]


class BloodPressurePdfAveragesTests(unittest.TestCase):
    def test_averages_use_only_readings_inside_interval(self):
        result = calculate_blood_pressure_averages(
            READINGS,
            "2026-09-20",
            "2026-09-30",
        )
        self.assertEqual(result["measurement_count"], 3)
        self.assertAlmostEqual(result["systolic_average"], 125.0)
        self.assertAlmostEqual(result["diastolic_average"], 82.0)
        self.assertAlmostEqual(result["pulse_average"], 65.0)

    def test_empty_interval_returns_no_average(self):
        result = calculate_blood_pressure_averages(
            READINGS,
            "2026-08-01",
            "2026-08-02",
        )
        self.assertEqual(result["measurement_count"], 0)
        self.assertIsNone(result["systolic_average"])
        self.assertIsNone(result["diastolic_average"])
        self.assertIsNone(result["pulse_average"])

    def test_invalid_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_blood_pressure_averages(
                READINGS,
                "2026-09-30",
                "2026-09-20",
            )

    def test_pdf_builds_with_and_without_averages(self):
        with tempfile.TemporaryDirectory() as directory:
            plain = Path(directory) / "plain.pdf"
            with_averages = Path(directory) / "averages.pdf"

            build_blood_pressure_pdf(
                full_name="Test",
                start_date="2026-09-20",
                end_date="2026-09-22",
                readings=READINGS,
                output_path=plain,
                include_averages=False,
            )
            build_blood_pressure_pdf(
                full_name="Test",
                start_date="2026-09-20",
                end_date="2026-09-22",
                readings=READINGS,
                output_path=with_averages,
                include_averages=True,
            )

            self.assertTrue(plain.exists())
            self.assertTrue(with_averages.exists())
            self.assertGreater(plain.stat().st_size, 1000)
            self.assertGreater(with_averages.stat().st_size, 1000)

    def test_ui_has_optional_checkbox_and_passes_value_to_pdf(self):
        source = (ROOT / "blood_pressure.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '"Inclure les moyennes de l’intervalle dans le PDF"',
            source,
        )
        self.assertIn("include_averages=bool(", source)
        self.assertIn("report_averages_input.value", source)

    def test_existing_pdf_rules_are_preserved(self):
        source = (ROOT / "blood_pressure_pdf.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("Aucune donnée pour ce jour", source)
        self.assertIn('date_label += " (suite)"', source)
        self.assertIn("_note_text(", source)
        self.assertIn(
            'if normalized_time_display_mode == "period"',
            source,
        )

    def test_version_is_1_2_3(self):
        source = (ROOT / "app_versions.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"blood_pressure": "1.2.3"', source)


if __name__ == "__main__":
    unittest.main()
