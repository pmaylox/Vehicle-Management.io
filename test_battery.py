"""Battery calendar, history, persistence, and form regression checks."""
from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

from battery import battery_details, battery_summary, service_suggestions
from Vehicle_Manager import Vehicle
from service_fields import battery_fields


class BatteryTests(unittest.TestCase):
    def test_calendar_and_countdown(self):
        details = battery_details("2024-02-29", 12, "Expected life", date(2025, 2, 28))
        self.assertEqual(details["target"], date(2025, 2, 28))
        self.assertIn("today", details["countdown"])
        self.assertEqual(battery_details("2025-01-31", 1, "Warranty", date(2025, 2, 27))["countdown"], "1 day remaining")
        self.assertIn("expired by 1 day", battery_details("2025-01-31", 1, "Warranty", date(2025, 3, 1))["countdown"])

    def test_invalid_inputs(self):
        for installed, months, term in [("bad", 12, "Warranty"), ("2027-01-01", 12, "Warranty"),
                                         ("2024-01-01", 0, "Warranty"), ("2024-01-01", -1, "Warranty"),
                                         ("2024-01-01", 1.5, "Warranty"), ("2024-01-01", 12, "Other"),
                                         ("2024-01-01", 999999, "Warranty")]:
            with self.subTest(installed=installed, months=months, term=term):
                with self.assertRaises(ValueError):
                    battery_details(installed, months, term, date(2026, 1, 1))

    def test_history_roundtrip_and_delete(self):
        vehicle = Vehicle("Practice", 2020, 100)
        self.assertIn("Not recorded", battery_summary(vehicle))
        def record(installed):
            return {"date": installed, "mileage": 100, "description": "Battery replaced",
                    "cost_cents": 0, "battery": {"installed": installed, "months": 36, "term": "Warranty"}}
        vehicle.service_history = [record("2025-02-01"), record("2024-01-01")]
        loaded = Vehicle.from_dict(json.loads(json.dumps(vehicle.to_dict())))
        self.assertIn("February 2025", battery_summary(loaded, date(2026, 1, 1)))
        loaded.service_history.pop(0)
        self.assertIn("January 2024", battery_summary(loaded, date(2026, 1, 1)))
        loaded.service_history[0]["battery"]["months"] = 48
        self.assertIn("01/01/2028", battery_summary(loaded, date(2026, 1, 1)))

    def test_suggestions(self):
        self.assertEqual(service_suggestions("bat"), ("Battery replaced",))
        self.assertIn("Custom work", service_suggestions("custom", [{"description": "Custom work"}]))

    def test_terminal_battery_service(self):
        vehicle = Vehicle("Practice", 2020, 100)
        with patch("builtins.input", side_effect=["bat", "4", "100", "2024-01-01", "48", "2"]), patch("builtins.print"):
            vehicle.service()
        self.assertEqual(vehicle.service_history[0]["battery"],
                         {"installed": "2024-01-01", "months": 48, "term": "Warranty"})
        with patch("builtins.input", side_effect=["Battery replaced", "4", "", "2024-01-01", "0", "1"]), patch("builtins.print"):
            vehicle.service()
        self.assertEqual(len(vehicle.service_history), 1)

    def test_form_validation_and_edit(self):
        root = tk.Tk()
        root.withdraw()
        try:
            form = ttk.Frame(root)
            description = tk.StringVar(root, "Battery replaced")
            get_value = battery_fields(form, 0, description, lambda: "2025-01-01",
                                       {"installed": "2024-01-01", "months": 36, "term": "Warranty"})
            self.assertEqual(get_value()["months"], 36)
            frame = form.winfo_children()[0]
            entries = [widget for widget in frame.winfo_children() if type(widget) is ttk.Entry]
            entries[1].delete(0, "end")
            entries[1].insert(0, "1.5")
            with self.assertRaises(ValueError):
                get_value()
        finally:
            root.destroy()

    def test_export_does_not_modify_data(self):
        from excel_export import export_vehicle_excel
        from openpyxl import load_workbook
        vehicle = Vehicle("Practice", 2020, 100)
        vehicle.service_history = [{"date": "2024-01-01", "mileage": 100,
            "description": "Battery replaced", "cost_cents": 0,
            "battery": {"installed": "2024-01-01", "months": 48, "term": "Expected life"}}]
        before = json.dumps(vehicle.to_dict(), sort_keys=True)
        with TemporaryDirectory(dir=Path(__file__).parent) as folder:
            path = export_vehicle_excel(vehicle, Path(folder) / "practice.xlsx")
            workbook = load_workbook(path)
            try:
                self.assertIn("Battery last replaced", workbook["Overview"]["A34"].value)
                self.assertEqual(workbook["Service History"]["D5"].value, 0)
                self.assertEqual(workbook["Overview"].page_setup.fitToHeight, 1)
            finally:
                workbook.close()
        self.assertEqual(before, json.dumps(vehicle.to_dict(), sort_keys=True))

    def test_record_dialog_save_failure_and_success(self):
        import app
        root = tk.Tk()
        root.withdraw()
        vehicle = Vehicle("Practice", 2020, 100)

        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)

        def button(parent, text):
            return next(w for w in descendants(parent)
                        if isinstance(w, ttk.Button) and w.cget("text") == text)

        def run_dialog():
            button(root, "Record Service").invoke()
            dialog = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
            description = next(w for w in descendants(dialog) if isinstance(w, ttk.Combobox))
            description.set("Battery replaced")
            battery_frame = next(w for w in descendants(dialog) if isinstance(w, ttk.LabelFrame))
            entries = [w for w in battery_frame.winfo_children() if type(w) is ttk.Entry]
            entries[1].insert(0, "48")
            with patch.object(app, "save_vehicles", side_effect=PermissionError("Practice locked file")):
                button(dialog, "Save Service").invoke()
            self.assertEqual(vehicle.service_history, [])
            with patch.object(app, "save_vehicles") as save:
                button(dialog, "Save Service").invoke()
                save.assert_called_once()
            self.assertEqual(vehicle.service_history[0]["battery"]["months"], 48)
            self.assertIn("days remaining", battery_summary(vehicle))

        try:
            with patch.object(app.tk, "Tk", return_value=root), \
                 patch.object(root, "mainloop", side_effect=run_dialog), \
                 patch.object(app, "load_vehicles", return_value=[vehicle]), \
                 patch.object(tk.Toplevel, "wait_visibility"), \
                 patch.object(tk.Toplevel, "grab_set"), \
                 patch.object(app.messagebox, "askyesno", return_value=True), \
                 patch.object(app.messagebox, "showerror") as error, \
                 patch.object(app.messagebox, "showinfo"):
                app.main()
                self.assertEqual(error.call_count, 1)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
