"""VIN decoding, manual profile entry, preview, and persistence checks."""
from io import BytesIO
import json
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch
from urllib.error import URLError

from Vehicle_Manager import Vehicle
from vehicle_profile_ui import VehicleProfileFields
from vin_lookup import clean_profile, decode_result, lookup_vin, normalize_vin, profile_summary

VIN = "1HGCM82633A004352"  # Test fixture only; never sent to the live service.
PAYLOAD = {"Results": [{"ErrorCode": "0", "ModelYear": "2003", "Make": "HONDA", "Model": "Accord",
    "DriveType": "FWD", "DisplacementL": "3", "EngineCylinders": "6", "FuelTypePrimary": "Gasoline",
    "TransmissionStyle": "Automatic", "BodyClass": "Sedan", "Trim": "EX"}]}


class VinTests(unittest.TestCase):
    def test_validation(self):
        self.assertEqual(normalize_vin(" " + VIN.lower() + " "), VIN)
        self.assertEqual(normalize_vin(""), "")
        for value in ("short", "I" * 17, "O" * 17, "Q" * 17, "../" + VIN):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_vin(value)

    def test_decode_and_network_failures(self):
        year, profile = decode_result(PAYLOAD)
        self.assertEqual(year, 2003)
        self.assertEqual(profile["drive_type"], "FWD")
        self.assertIn("6 cylinders", profile["engine"])
        self.assertNotIn("color", profile)
        with patch("vin_lookup.urlopen", return_value=BytesIO(json.dumps(PAYLOAD).encode())) as request:
            year, profile = lookup_vin(VIN, 2003)
            self.assertIn("vpic.nhtsa.dot.gov", request.call_args.args[0].full_url)
            self.assertEqual(profile["source"], "NHTSA vPIC")
        with patch("vin_lookup.urlopen", side_effect=URLError("offline")):
            with self.assertRaises(RuntimeError):
                lookup_vin(VIN)
        for bad in ({"Results": []}, {"Results": [{"ErrorCode": "1", "ErrorText": "Check digit error"}]},
                    {"Results": [{"ErrorCode": "0", "Make": "HONDA"}]}):
            with self.assertRaises(ValueError):
                decode_result(bad)

    def test_legacy_and_json_roundtrip(self):
        vehicle = Vehicle("Practice", 2020, 100)
        old = vehicle.to_dict()
        old.pop("profile")
        self.assertEqual(Vehicle.from_dict(old).profile, {})
        vehicle.profile = {"vin": VIN, "drive_type": "FWD", "color": "Blue", "paint_code": "B123"}
        loaded = Vehicle.from_dict(json.loads(json.dumps(vehicle.to_dict())))
        self.assertEqual(loaded.profile, vehicle.profile)
        self.assertIn("Color: Blue", profile_summary(loaded))
        self.assertEqual(clean_profile({"color": None, "make": " Honda ", "unexpected": "x"}), {"make": "Honda"})

    def test_review_keeps_manual_color_and_custom_name(self):
        root = tk.Tk()
        root.withdraw()
        errors = []
        root.report_callback_exception = lambda *error: errors.append(error)
        try:
            form = ttk.Frame(root)
            name, year = tk.StringVar(value="My daily driver"), tk.StringVar(value="2020")
            panel = VehicleProfileFields(form, 0, name, year, {"color": "Blue", "paint_code": "B123"})
            panel.vin.set(VIN)
            _, profile = decode_result(PAYLOAD)
            profile.update(vin=VIN, source="NHTSA vPIC", decoded_at="2026-11-14T00:00:00+00:00")
            panel.review(2003, profile)
            self.assertEqual(year.get(), "2020")  # Nothing applies until the user chooses Apply.
            dialog = next(w for w in panel.winfo_children() if isinstance(w, tk.Toplevel))
            def descendants(widget):
                for child in widget.winfo_children():
                    yield child
                    yield from descendants(child)
            button = next(w for w in descendants(dialog) if isinstance(w, ttk.Button) and w.cget("text") == "Apply details")
            button.invoke()
            self.assertEqual(name.get(), "My daily driver")
            self.assertEqual(year.get(), "2003")
            saved = panel.get_value()
            self.assertEqual(saved["color"], "Blue")
            self.assertEqual(saved["paint_code"], "B123")
            self.assertEqual(saved["drive_type"], "FWD")
            self.assertEqual(saved["vin"], VIN)
            self.assertEqual(saved["source"], "NHTSA vPIC")
            panel.vin.set("1" * 17)
            self.assertNotIn("source", panel.get_value())
            self.assertFalse(errors, errors)
        finally:
            root.destroy()

    def test_profile_only_edit_and_save_failure_rollback(self):
        import app
        from test_vehicle_search import VehicleSearchTests

        def scenario(root, vehicles, save):
            def descendants(widget):
                for child in widget.winfo_children():
                    yield child
                    yield from descendants(child)
            def button(parent, label):
                return next(w for w in descendants(parent) if isinstance(w, ttk.Button) and w.cget("text") == label)
            listing = next(w for w in descendants(root) if isinstance(w, tk.Listbox))
            selected_name = listing.get(listing.curselection()[0])
            vehicle = next(v for v in vehicles if f"{v.year} {v.name}" == selected_name)
            before = json.dumps(vehicle.to_dict(), sort_keys=True)
            button(root, "Edit Vehicle").invoke()
            dialog = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
            panel = next(w for w in descendants(dialog) if isinstance(w, VehicleProfileFields))
            panel.vin.set(VIN)
            panel.fields["color"].set("Blue")
            panel.fields["drive_type"].set("FWD")
            with patch.object(app, "save_vehicles", side_effect=PermissionError("Practice failure")):
                button(dialog, "Save Changes").invoke()
            self.assertEqual(json.dumps(vehicle.to_dict(), sort_keys=True), before)
            button(dialog, "Save Changes").invoke()
            self.assertEqual(vehicle.profile["vin"], VIN)
            self.assertEqual(vehicle.profile["color"], "Blue")
            overview = next(w for w in descendants(root) if isinstance(w, app.OverviewPanel))
            self.assertIn("Color: Blue", overview.specifications.get())
            self.assertIn("Drive type: FWD", overview.specifications.get())
        VehicleSearchTests.run_app(self, scenario)


if __name__ == "__main__":
    unittest.main()
