"""Isolated checks for pictured garage layout and phone-record preservation."""
import base64
from copy import deepcopy
from io import BytesIO
import tkinter as tk
import unittest
from unittest.mock import patch

from PIL import Image
from Vehicle_Manager import Vehicle
from dashboard_panel import DashboardPanel
from expenses_panel import ExpensesPanel
from test_vehicle_search import VehicleSearchTests, descendants, button


class InterfaceRefreshTests(unittest.TestCase):
    def test_phone_fields_survive_desktop_round_trip(self):
        original = Vehicle("Tester", 2026, 5000).to_dict()
        original.update(mobile_expenses=[{"date": "2026-11-01", "cost_cents": 435810,
                                         "expense_document": {"id": "phone-pdf"}}],
                        resale_history=[{"date": "2026-11-01", "value_cents": 4000000}],
                        mobile_mileage_log=[{"before": 4990, "after": 5000}],
                        future_phone_field={"keep": [1, 2]})
        loaded = Vehicle.from_dict(original)
        loaded.mileage = 5010
        result = loaded.to_dict()
        for key in ("mobile_expenses", "resale_history", "mobile_mileage_log", "future_phone_field"):
            self.assertEqual(result[key], original[key])
        loaded.mobile_expenses[0]["cost_cents"] = 1
        self.assertEqual(original["mobile_expenses"][0]["cost_cents"], 435810)

    def test_dashboard_selection_layout_and_mobile_photo(self):
        def scenario(root, vehicles, save):
            buffer = BytesIO()
            Image.new("RGBA", (120, 60), "silver").save(buffer, "PNG")
            vehicles[0].mobile_photo = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
            dashboard = next(w for w in descendants(root) if isinstance(w, DashboardPanel))
            root.deiconify()
            root.geometry("1200x750")
            root.update()
            dashboard.set_vehicles(vehicles, vehicles[0])
            root.update()
            self.assertIsNotNone(dashboard.cards[0].photo_image)
            self.assertEqual([int(c.grid_info()["column"]) for c in dashboard.cards], [0, 1])
            dashboard.cards[1].event_generate("<Button-1>")
            root.update()
            overview = next(w for w in descendants(root) if w.__class__.__name__ == "OverviewPanel")
            self.assertIn(vehicles[1].name, overview.heading.get())
            # Return to Dashboard and shrink; cards stack and quick actions remain visible.
            next(w for w in descendants(root) if isinstance(w, tk.Button) and w.cget("text") == "Dashboard").invoke()
            root.geometry("800x650")
            root.update()
            self.assertEqual([int(c.grid_info()["column"]) for c in dashboard.cards], [0, 0])
            for action in dashboard.action_buttons:
                self.assertLessEqual(action.winfo_rooty() + action.winfo_height(), root.winfo_rooty() + root.winfo_height())
            save.assert_not_called()
        VehicleSearchTests.run_app(self, scenario)

    def test_expense_save_failure_preserves_phone_document(self):
        root = tk.Tk()
        root.withdraw()
        try:
            panel = ExpensesPanel(root, lambda: (_ for _ in ()).throw(OSError("disk full")))
            vehicle = Vehicle("Tester", 2026, 5000)
            vehicle.mobile_expenses = [{"cost_cents": 100, "expense_document": {"id": "keep"}}]
            original = deepcopy(vehicle.mobile_expenses)
            panel.show(vehicle)
            with patch("expenses_panel.messagebox.showerror"):
                self.assertFalse(panel._commit([]))
            self.assertEqual(vehicle.mobile_expenses, original)
            self.assertEqual(vehicle.mileage, 5000)
        finally:
            root.destroy()

    def test_manage_actions_fit_small_desktop(self):
        def scenario(root, vehicles, save):
            root.deiconify()
            root.geometry("800x500")
            root.update()
            button(root, "Manage vehicles").invoke()
            root.update()
            for label in ("Add Vehicle", "Edit Vehicle", "Remove Vehicle"):
                action = button(root, label)
                self.assertTrue(action.winfo_ismapped(), label)
                self.assertGreaterEqual(action.winfo_rooty(), root.winfo_rooty(), label)
                self.assertLessEqual(action.winfo_rooty() + action.winfo_height(), root.winfo_rooty() + root.winfo_height(), label)
            save.assert_not_called()
        VehicleSearchTests.run_app(self, scenario)
