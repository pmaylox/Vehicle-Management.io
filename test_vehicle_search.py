"""Exercise filtered vehicle actions using isolated Tk forms and fake storage."""
from contextlib import ExitStack
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

import app
from Vehicle_Manager import Vehicle


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def button(parent, label):
    return next(w for w in descendants(parent)
                if isinstance(w, ttk.Button) and w.cget("text") == label)


class VehicleSearchTests(unittest.TestCase):
    def run_app(self, scenario):
        root = tk.Tk()
        root.withdraw()
        vehicles = [Vehicle("Toyota Tacoma", 2026, 100), Vehicle("Ford Explorer", 2025, 200)]
        errors = []
        root.report_callback_exception = lambda *error: errors.append(error)
        try:
            with ExitStack() as stack:
                stack.enter_context(patch.object(app.tk, "Tk", return_value=root))
                stack.enter_context(patch.object(app, "load_vehicles", return_value=vehicles))
                save = stack.enter_context(patch.object(app, "save_vehicles"))
                stack.enter_context(patch.object(tk.Toplevel, "wait_visibility"))
                stack.enter_context(patch.object(tk.Toplevel, "grab_set"))
                stack.enter_context(patch.object(app.messagebox, "askyesno", return_value=True))
                stack.enter_context(patch.object(app.messagebox, "showinfo"))
                stack.enter_context(patch.object(app.messagebox, "showerror"))
                stack.enter_context(patch.object(root, "mainloop", side_effect=lambda: scenario(root, vehicles, save)))
                app.main()
            self.assertEqual(errors, [])
        finally:
            root.destroy()

    def controls(self, root):
        search = next(w for w in descendants(root) if type(w) is ttk.Entry)
        listing = next(w for w in descendants(root) if isinstance(w, tk.Listbox))
        overview = next(w for w in descendants(root) if isinstance(w, tk.Text))
        return search, listing, overview

    def search(self, entry, query):
        entry.delete(0, "end")
        entry.insert(0, query)

    def test_filter_actions_and_no_matches(self):
        def scenario(root, vehicles, save):
            search, listing, overview = self.controls(root)
            self.search(search, " eXpLoReR ")
            self.assertEqual(listing.get(0, "end"), ("2025 Ford Explorer",))
            self.assertIn("Ford Explorer", overview.get("1.0", "end"))
            with patch.object(app.simpledialog, "askinteger", return_value=10):
                button(root, "Update Mileage").invoke()
            self.assertEqual([v.mileage for v in vehicles], [100, 210])
            with patch.object(app.filedialog, "asksaveasfilename", return_value="fake.xlsx"), \
                 patch.object(app, "export_vehicle_excel", return_value=Path("fake.xlsx")) as export:
                button(root, "Export to Excel").invoke()
                self.assertIs(export.call_args.args[0], vehicles[1])
            for label in ("Record Service", "Record Fuel", "Update Tire Pressure"):
                button(root, label).invoke()
                dialog = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
                self.assertTrue(any("Ford Explorer" in str(w.cget("text"))
                                    for w in descendants(dialog) if isinstance(w, ttk.Label))) if label != "Update Tire Pressure" else None
                button(dialog, "Cancel").invoke()
            self.search(search, "no such vehicle")
            self.assertEqual(listing.size(), 0)
            self.assertIn("No matching vehicles", overview.get("1.0", "end"))
            before = save.call_count
            button(root, "Remove Vehicle").invoke()
            self.assertEqual(save.call_count, before)
            button(root, "Clear").invoke()
            self.assertEqual(listing.size(), 2)
            self.search(search, "2026")
            self.assertEqual(listing.get(0), "2026 Toyota Tacoma")
        self.run_app(scenario)

    def test_filtered_edit_and_remove(self):
        def scenario(root, vehicles, save):
            search, listing, overview = self.controls(root)
            self.search(search, "Explorer")
            button(root, "Edit Vehicle").invoke()
            dialog = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
            name = next(w for w in descendants(dialog) if type(w) is ttk.Entry)
            name.delete(0, "end")
            name.insert(0, "Ford Expedition")
            button(dialog, "Save Changes").invoke()
            self.assertEqual(vehicles[1].name, "Ford Expedition")
            self.assertEqual(listing.size(), 0)
            self.search(search, "Expedition")
            button(root, "Remove Vehicle").invoke()
            self.assertEqual([v.name for v in vehicles], ["Toyota Tacoma"])
            self.assertEqual(listing.size(), 0)
            button(root, "Clear").invoke()
            self.assertEqual(listing.get(0), "2026 Toyota Tacoma")
        self.run_app(scenario)

    def test_add_clears_filter_and_selects_new_vehicle(self):
        def scenario(root, vehicles, save):
            search, listing, overview = self.controls(root)
            self.search(search, "nothing")
            button(root, "Add Vehicle").invoke()
            dialog = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
            fields = [w for w in descendants(dialog) if type(w) is ttk.Entry]
            for entry, value in zip(fields, ("Practice Car", "2020", "500")):
                entry.delete(0, "end")
                entry.insert(0, value)
            button(dialog, "Save Vehicle").invoke()
            self.assertEqual(search.get(), "")
            self.assertEqual(listing.get(listing.curselection()[0]), "2020 Practice Car")
            self.assertEqual(len(vehicles), 3)
        self.run_app(scenario)


if __name__ == "__main__":
    unittest.main()
