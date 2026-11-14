"""Regression tests for fluid checks, filter records and Excel exports.

Run with: python -m unittest test_fluid_filters.py
"""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from Vehicle_Manager import Vehicle
from excel_export import export_vehicle_excel
from openpyxl import load_workbook


class FluidFilterTests(unittest.TestCase):
    def setUp(self):
        self.vehicle = Vehicle("Toyota Tacoma", 2026, 20000)
        self.vehicle.mileage = 22000

    def test_independent_5000_mile_fluid_resets(self):
        self.assertTrue(self.vehicle.fluid_check_status("washer")["due"])
        self.assertTrue(self.vehicle.fluid_check_status("coolant")["due"])

        self.vehicle.reset_fluid_to_full("washer")
        self.assertEqual(self.vehicle.fluid_check_status("washer")["miles_remaining"], 5000)
        self.assertTrue(self.vehicle.fluid_check_status("coolant")["due"])
        self.vehicle.mileage += 4999
        self.assertFalse(self.vehicle.fluid_check_status("washer")["due"])
        self.vehicle.reset_fluid_to_full("coolant")
        self.assertEqual(self.vehicle.fluid_check_status("coolant")["miles_remaining"], 5000)
        self.vehicle.mileage += 1
        self.assertTrue(self.vehicle.fluid_check_status("washer")["due"])
        self.assertFalse(self.vehicle.fluid_check_status("coolant")["due"])

    def test_reset_is_allowed_early(self):
        self.vehicle.reset_fluid_to_full("washer")
        self.vehicle.mileage += 100
        self.vehicle.reset_fluid_to_full("washer")
        self.assertEqual(self.vehicle.fluid_check_status("washer")["next_due_mileage"],
                         self.vehicle.mileage + 5000)
        self.assertEqual(len(self.vehicle.fluid_check_history), 2)

    def test_filter_records_persist_and_have_dates(self):
        self.vehicle.record_air_filter_change("interior", date.today().isoformat(), 21000)
        self.vehicle.record_air_filter_change("exterior", date.today().isoformat(), 22000)
        recovered = Vehicle.from_dict(self.vehicle.to_dict())
        self.assertEqual(len(recovered.air_filter_changes), 2)
        self.assertEqual(recovered.air_filter_changes[0]["filter_type"], "interior")
        self.assertEqual(recovered.air_filter_changes[1]["filter_type"], "exterior")
        self.assertEqual(recovered.air_filter_changes[0]["mileage"], 21000)

    def test_invalid_replacement_date_or_mileage(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        with self.assertRaises(ValueError):
            self.vehicle.record_air_filter_change("interior", tomorrow)
        with self.assertRaises(ValueError):
            self.vehicle.record_air_filter_change("exterior", date.today(), 23000)

    def test_legacy_vehicle_files_load_without_new_fields(self):
        legacy = {
            "name": "Toyota Tacoma", "year": 2026,
            "starting_mileage": 20000, "mileage": 22000,
            "last_service_mileage": 20000, "service_interval": 10000,
        }
        restored = Vehicle.from_dict(legacy)
        self.assertEqual(restored.fluid_check_history, [])
        self.assertEqual(restored.air_filter_changes, [])
        self.assertTrue(restored.fluid_check_status("washer")["due"])

    def test_excel_contains_event_history_and_separate_sheets(self):
        self.vehicle.reset_fluid_to_full("washer")
        self.vehicle.reset_fluid_to_full("coolant")
        self.vehicle.record_air_filter_change("interior", date.today(), 21000)
        self.vehicle.record_air_filter_change("exterior", date.today(), 22000)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "vehicle.xlsx"
            self.assertEqual(export_vehicle_excel(self.vehicle, target), target)
            workbook = load_workbook(target, read_only=True, data_only=True)
            self.assertIn("Service History", workbook.sheetnames)
            self.assertIn("Fluid Checks", workbook.sheetnames)
            self.assertIn("Air Filters", workbook.sheetnames)
            fluids = list(workbook["Fluid Checks"].values)
            filters = list(workbook["Air Filters"].values)
            service = list(workbook["Service History"].values)
            self.assertTrue(any("Windshield washer fluid" in row for row in fluids))
            self.assertTrue(any("Interior / cabin air filter" in row for row in filters))
            self.assertTrue(any("Fluid Checks & Air Filter Replacements" in row for row in service))
            workbook.close()


if __name__ == "__main__":
    unittest.main()
