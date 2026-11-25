import unittest
from datetime import date

from car_history import (
    empty_car_history, clean_car_history, next_history_review,
    history_review_status, mark_history_review, add_history_event,
)
from Vehicle_Manager import Vehicle


class CarHistoryTests(unittest.TestCase):
    def test_annual_review_and_leap_day(self):
        self.assertEqual(next_history_review("2024-02-29"), "2025-02-28")
        self.assertEqual(next_history_review("2025-11-19"), "2026-11-19")
        self.assertTrue(history_review_status(empty_car_history(),
                                              date(2026, 11, 19))["due"])
        done = mark_history_review(empty_car_history(), "2026-11-19",
                                   "CARFAX Car Care", "Reviewed",
                                   today=date(2026, 11, 19))
        self.assertFalse(history_review_status(done, "2027-11-18")["due"])
        self.assertTrue(history_review_status(done, "2027-11-19")["due"])

    def test_invalid_dates_and_events(self):
        with self.assertRaises(ValueError):
            mark_history_review({}, "2026-02-30", "CARFAX Car Care")
        with self.assertRaises(ValueError):
            add_history_event({}, "2099-01-01", "Service",
                              "Oil changed", "CARFAX Car Care")
        with self.assertRaises(ValueError):
            add_history_event({}, "2026-01-01", "Odometer",
                              "Reported", "Other", -1)

    def test_import_sanitizes_malformed_history(self):
        h = clean_car_history({"last_review_date": "not a date",
                               "events": [{"date": "bad"},
                                          {"date": "2025-07-11", "mileage": 500,
                                           "description": "Recall event"}]})
        self.assertIsNone(h["last_review_date"])
        self.assertEqual(len(h["events"]), 1)
        self.assertEqual(h["events"][0]["mileage"], 500)

    def test_vehicle_isolation_backup_and_no_odometer_side_effect(self):
        tacoma = Vehicle("Toyota Tacoma", 2026, 5000)
        explorer = Vehicle("Ford Explorer", 2025, 12000)
        tacoma.car_history = mark_history_review(
            tacoma.car_history, "2026-11-19", "CARFAX Car Care",
            today=date(2026, 11, 19))
        tacoma.car_history = add_history_event(
            tacoma.car_history, "2026-10-01", "Odometer",
            "Reported mileage", "CARFAX Car Care", mileage=8000,
            today=date(2026, 11, 19))
        self.assertEqual(tacoma.mileage, 5000)
        self.assertEqual(tacoma.service_history, [])
        self.assertEqual(explorer.car_history, empty_car_history())
        restored = Vehicle.from_dict(tacoma.to_dict())
        self.assertEqual(restored.car_history, tacoma.car_history)
        self.assertEqual(restored.mileage, 5000)
        legacy = tacoma.to_dict()
        del legacy["car_history"]
        self.assertEqual(Vehicle.from_dict(legacy).car_history,
                         empty_car_history())


if __name__ == "__main__":
    unittest.main()
