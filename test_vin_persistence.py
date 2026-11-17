"""VIN persistence across mobile JSON, desktop load and saved file."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Vehicle_Manager import Vehicle
import storage


class VINPersistenceTests(unittest.TestCase):
    def test_optional_vin_survives_json_round_trip(self):
        car = Vehicle("Toyota Tacoma", 2026, 4605)
        car.vin = "1HGCM82633A004352"
        car.service_history.append({
            "date": "2026-11-14", "mileage": 4605,
            "description": "Test entry", "cost_cents": 0,
        })
        saved = json.loads(json.dumps(car.to_dict()))
        loaded = Vehicle.from_dict(saved)
        self.assertEqual(loaded.vin, car.vin)
        self.assertEqual(loaded.service_history, car.service_history)
        self.assertEqual(loaded.mileage, 4605)

    def test_legacy_without_vin_remains_supported(self):
        car = Vehicle("Toyota Tacoma — Tester", 2026, 1100)
        old = car.to_dict()
        old.pop("vin")
        recovered = Vehicle.from_dict(old)
        self.assertIsNone(recovered.vin)
        self.assertEqual(recovered.name, "Toyota Tacoma — Tester")

    def test_two_toyotas_remain_distinct_after_file_save(self):
        actual = Vehicle("Toyota Tacoma", 2026, 4605)
        actual.vin = "1HGCM82633A004352"
        tester = Vehicle("Toyota Tacoma — Tester", 2026, 7000)
        tester.service_history.append({"description":"Test entry","mileage":7000})
        with tempfile.TemporaryDirectory() as dirname:
            path = Path(dirname) / "vehicles.json"
            with patch.object(storage, "DATA_FILE", path):
                storage.save_vehicles([actual, tester])
                reread = storage.load_vehicles()
        self.assertEqual(len(reread), 2)
        self.assertEqual(reread[0].vin, actual.vin)
        self.assertIsNone(reread[1].vin)
        self.assertEqual(len(reread[1].service_history), 1)


if __name__ == "__main__":
    unittest.main()
