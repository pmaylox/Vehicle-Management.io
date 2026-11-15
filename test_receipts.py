"""Receipt extraction, review, and attachment lifecycle regression tests."""
from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

from PIL import Image
import receipts
from receipt_ui import ReceiptPanel


class ReceiptTests(unittest.TestCase):
    def test_fuel_fields_are_explicit(self):
        fields = receipts.extract_fields([
            "11/14/2026", "GALLONS 12.500", "SUB TOTAL 35.00", "TOTAL TAX 5.00",
            "TOTAL $40.00", "ODOMETER 7,000", "OCTANE 87", "E10"
        ], "fuel")
        self.assertEqual(fields, {"date": "2026-11-14", "gallons": "12.500", "cost": "40.00",
                                  "mileage": "7000", "octane": "87", "fuel_type": "E10 — gasoline"})
        self.assertNotIn("full_tank", fields)

    def test_missing_ambiguous_and_diesel(self):
        self.assertEqual(receipts.extract_fields(["REGULAR", "$3.19", "THANK YOU"], "fuel"), {})
        self.assertNotIn("cost", receipts.extract_fields(["SUB TOTAL 12.00"], "fuel"))
        self.assertNotIn("date", receipts.extract_fields(["02/30/2026"], "fuel"))
        fields = receipts.extract_fields(["DIESEL", "B20", "OCTANE 87"], "fuel")
        self.assertEqual(fields, {"fuel_type": "Diesel — B20"})
        self.assertEqual(receipts.extract_fields(["1 1/14/2026"], "fuel")["date"], "2026-11-14")

    def test_service_fields(self):
        fields = receipts.extract_fields(["2026-11-14", "Oil Change", "Tire Rotation",
                                           "TOTAL 85.45", "MILEAGE 7000"], "service")
        self.assertEqual(fields["description"], "Oil change; Tire rotation")
        self.assertEqual(fields["cost"], "85.45")
        self.assertNotIn("oil_reset", fields)

    def test_review_and_attachment_rollback(self):
        root = tk.Tk()
        root.withdraw()
        try:
            with TemporaryDirectory(dir=Path(__file__).parent) as directory:
                base = Path(directory)
                source = base / "practice.png"
                Image.new("RGB", (20, 20), "white").save(source)
                with patch.object(receipts, "BASE", base), patch.object(receipts, "RECEIPTS", base / "receipts"):
                    form = ttk.Frame(root)
                    variables = {"cost": tk.StringVar(value="99"), "gallons": tk.StringVar(value="")}
                    panel = ReceiptPanel(form, 0, "fuel", variables)
                    panel.source = str(source)
                    self.assertFalse((base / "receipts").exists())
                    panel.review(["TOTAL 40.00", "GALLONS 12.500"])
                    self.assertEqual(variables["cost"].get(), "99")
                    dialog = next(w for w in panel.winfo_children() if isinstance(w, tk.Toplevel))
                    def descendants(widget):
                        for child in widget.winfo_children():
                            yield child
                            yield from descendants(child)
                    apply = next(w for w in descendants(dialog) if isinstance(w, ttk.Button)
                                 and w.cget("text") == "Apply selected fields")
                    apply.invoke()
                    self.assertEqual(variables["cost"].get(), "40.00")
                    self.assertEqual(variables["gallons"].get(), "12.500")
                    record = {}
                    panel.commit(record)
                    stored = receipts.receipt_path(record["receipt_photo"])
                    self.assertTrue(stored.is_file())
                    self.assertNotEqual(stored, source)
                    panel.rollback()
                    self.assertFalse(stored.exists())
                    self.assertTrue(source.exists())
                    with self.assertRaises(ValueError):
                        receipts.receipt_path("../outside.png")
        finally:
            root.destroy()

    def test_record_and_edit_save_paths(self):
        import app
        from test_vehicle_search import VehicleSearchTests

        def scenario(root, vehicles, save):
            def descendants(widget):
                for child in widget.winfo_children():
                    yield child
                    yield from descendants(child)
            def button(parent, text):
                return next(w for w in descendants(parent) if isinstance(w, ttk.Button) and w.cget("text") == text)
            def dialog():
                return next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
            with TemporaryDirectory(dir=Path(__file__).parent) as directory:
                base = Path(directory)
                source = base / "practice.png"
                Image.new("RGB", (20, 20), "white").save(source)
                with patch.object(receipts, "BASE", base), patch.object(receipts, "RECEIPTS", base / "receipts"):
                    button(root, "Record Fuel").invoke()
                    d = dialog()
                    entries = [w for w in descendants(d) if type(w) is ttk.Entry]
                    # Date and current odometer are already valid defaults.
                    entries[2].insert(0, "10")
                    entries[3].insert(0, "30")
                    panel = next(w for w in descendants(d) if isinstance(w, ReceiptPanel))
                    panel.source = str(source)
                    button(d, "Save Fill-up").invoke()
                    selected = next(v for v in vehicles if v.fuel_history)
                    self.assertTrue(receipts.receipt_path(selected.fuel_history[0]["receipt_photo"]).exists())
                    table = next(w for w in descendants(root) if isinstance(w, ttk.Treeview) and "gallons" in w.cget("columns"))
                    table.selection_set(table.get_children()[0])
                    button(root, "Edit Fuel").invoke()
                    d = dialog()
                    panel = next(w for w in descendants(d) if isinstance(w, ReceiptPanel))
                    old = selected.fuel_history[0]["receipt_photo"]
                    panel.source = str(source)
                    with patch.object(app, "save_vehicles", side_effect=PermissionError("Practice failure")):
                        button(d, "Save Changes").invoke()
                    self.assertEqual(selected.fuel_history[0]["receipt_photo"], old)
                    self.assertEqual(len(list((base / "receipts").iterdir())), 1)
                    button(d, "Cancel").invoke()
                    button(root, "Record Service").invoke()
                    d = dialog()
                    description = next(w for w in descendants(d) if isinstance(w, ttk.Combobox))
                    description.set("Receipt practice service")
                    panel = next(w for w in descendants(d) if isinstance(w, ReceiptPanel))
                    panel.source = str(source)
                    button(d, "Save Service").invoke()
                    self.assertTrue(receipts.receipt_path(selected.service_history[0]["receipt_photo"]).exists())
                    table = next(w for w in descendants(root) if isinstance(w, ttk.Treeview) and "description" in w.cget("columns"))
                    table.selection_set(table.get_children()[0])
                    button(root, "Edit Service").invoke()
                    d = dialog()
                    panel = next(w for w in descendants(d) if isinstance(w, ReceiptPanel))
                    self.assertEqual(panel.existing, selected.service_history[0]["receipt_photo"])
                    panel.source = str(source)
                    button(d, "Save Changes").invoke()
                    self.assertTrue(receipts.receipt_path(selected.service_history[0]["receipt_photo"]).exists())
        VehicleSearchTests.run_app(self, scenario)


if __name__ == "__main__":
    unittest.main()
