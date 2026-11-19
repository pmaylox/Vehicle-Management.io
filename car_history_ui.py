"""Car History tab UI for the desktop MileSage application."""
from datetime import date
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from car_history import (
    CARFAX_CARE_URL, HISTORY_CATEGORIES, HISTORY_SOURCES,
    add_history_event, clean_car_history, history_review_status,
    mark_history_review,
)


class CarHistoryPanel(ttk.Frame):
    """Manual reporting and annual review: not a CARFAX live connection."""

    def __init__(self, parent, on_save):
        super().__init__(parent)
        self.on_save = on_save
        self.vehicle = None
        self.pack(fill="both", expand=True)

        self.title = tk.StringVar(value="Select a vehicle to view its history.")
        ttk.Label(self, textvariable=self.title,
                  font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 6))
        self.status = tk.StringVar(value="No vehicle selected")
        ttk.Label(self, textvariable=self.status,
                  wraplength=800).pack(anchor="w", pady=(0, 8))

        ttk.Button(self, text="Open CARFAX Car Care in browser",
                   command=lambda: webbrowser.open(CARFAX_CARE_URL)).pack(anchor="w")
        ttk.Label(
            self,
            text="CARFAX does not automatically send history to MileSage. "
                 "Review the report yourself and record findings below. "
                 "Reported mileage does not change your MileSage odometer.",
            wraplength=800,
        ).pack(anchor="w", pady=(4, 9))

        review = ttk.LabelFrame(self, text="Annual CARFAX / vehicle history review", padding=8)
        review.pack(fill="x", pady=(0, 8))
        review_row = ttk.Frame(review)
        review_row.pack(fill="x")
        ttk.Label(review_row, text="Reviewed on (YYYY-MM-DD)").pack(side="left")
        self.review_date = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(review_row, textvariable=self.review_date, width=13).pack(side="left", padx=(5, 12))
        ttk.Label(review_row, text="Source").pack(side="left")
        self.review_source = tk.StringVar(value=HISTORY_SOURCES[0])
        ttk.Combobox(review_row, textvariable=self.review_source,
                     values=HISTORY_SOURCES, state="readonly", width=27).pack(
                         side="left", padx=6)
        ttk.Button(review_row, text="Mark reviewed",
                   command=self._mark_reviewed).pack(side="left", padx=8)
        note_row = ttk.Frame(review)
        note_row.pack(fill="x", pady=(6, 0))
        ttk.Label(note_row, text="Review notes").pack(side="left")
        self.review_notes = tk.StringVar()
        ttk.Entry(note_row, textvariable=self.review_notes).pack(
            side="left", padx=8, fill="x", expand=True)

        event_area = ttk.LabelFrame(self, text="Add an independently reported history event", padding=8)
        event_area.pack(fill="x", pady=(0, 8))
        row1 = ttk.Frame(event_area)
        row1.pack(fill="x")
        ttk.Label(row1, text="Date").pack(side="left")
        self.event_date = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(row1, textvariable=self.event_date, width=13).pack(side="left", padx=5)
        ttk.Label(row1, text="Type").pack(side="left", padx=(10, 0))
        self.category = tk.StringVar(value=HISTORY_CATEGORIES[0])
        ttk.Combobox(row1, textvariable=self.category, values=HISTORY_CATEGORIES,
                     state="readonly", width=20).pack(side="left", padx=5)
        ttk.Label(row1, text="Source").pack(side="left")
        self.source = tk.StringVar(value=HISTORY_SOURCES[0])
        ttk.Combobox(row1, textvariable=self.source, values=HISTORY_SOURCES,
                     state="readonly", width=26).pack(side="left", padx=5)

        row2 = ttk.Frame(event_area)
        row2.pack(fill="x", pady=(6, 0))
        ttk.Label(row2, text="Reported mileage (optional)").pack(side="left")
        self.mileage = tk.StringVar()
        ttk.Entry(row2, textvariable=self.mileage, width=12).pack(side="left", padx=6)
        ttk.Label(row2, text="Details").pack(side="left", padx=(7, 0))
        self.description = tk.StringVar()
        ttk.Entry(row2, textvariable=self.description).pack(
            side="left", fill="x", expand=True, padx=6)
        ttk.Button(row2, text="Add event", command=self._add_event).pack(side="left")

        list_area = ttk.LabelFrame(self, text="Car history timeline (not service/fuel logs)", padding=8)
        list_area.pack(fill="both", expand=True)
        columns = ("date", "category", "mileage", "source", "description")
        self.table = ttk.Treeview(list_area, columns=columns, show="headings",
                                  height=7, selectmode="browse")
        widths = (94, 130, 90, 165, 260)
        for column, width in zip(columns, widths):
            self.table.heading(column, text=column.capitalize())
            self.table.column(column, width=width, minwidth=65,
                              stretch=column == "description")
        scroll = ttk.Scrollbar(list_area, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.table.pack(fill="both", expand=True)
        ttk.Button(self, text="Delete selected history event",
                   command=self._delete_event).pack(anchor="e", pady=(5, 0))
        self.show(None)

    def show(self, vehicle):
        self.vehicle = vehicle
        self.table.delete(*self.table.get_children())
        if vehicle is None:
            self.title.set("Select a vehicle to view its history.")
            self.status.set("No vehicle selected.")
            return
        self.title.set(f"{vehicle.year} {vehicle.name} · Car History")
        status = history_review_status(vehicle.car_history)
        if status["last_review_date"] is None:
            self.status.set("History not reviewed yet. Annual review due now.")
        else:
            due = status["next_review_date"]
            self.status.set(
                f"Last review: {status['last_review_date']} · "
                f"Next review: {due} · "
                f"{'Review due' if status['due'] else 'Up to date'}"
            )
        history = clean_car_history(vehicle.car_history)
        self.review_notes.set(history["review_notes"])
        if history["review_source"] in HISTORY_SOURCES:
            self.review_source.set(history["review_source"])
        self.review_date.set(date.today().isoformat())
        for index, event in sorted(enumerate(history["events"]),
                                   key=lambda item: item[1]["date"], reverse=True):
            mileage = event["mileage"]
            self.table.insert("", "end", iid=str(index), values=(
                event["date"], event["category"],
                "" if mileage is None else f"{mileage:,}",
                event["source"], event["description"],
            ))

    def _apply(self, updated):
        if self.vehicle is None:
            return
        original = self.vehicle.car_history
        self.vehicle.car_history = updated
        try:
            self.on_save()
        except (OSError, ValueError, TypeError) as exc:
            self.vehicle.car_history = original
            messagebox.showerror("Car history not saved",
                                 f"Your changes were not committed: {exc}")
            return
        self.show(self.vehicle)

    def _mark_reviewed(self):
        if self.vehicle is None:
            return
        try:
            updated = mark_history_review(
                self.vehicle.car_history, self.review_date.get(),
                self.review_source.get(), self.review_notes.get())
            self._apply(updated)
        except ValueError as exc:
            messagebox.showerror("Review date error", str(exc))

    def _add_event(self):
        if self.vehicle is None:
            return
        try:
            updated = add_history_event(
                self.vehicle.car_history, self.event_date.get(),
                self.category.get(), self.description.get(),
                self.source.get(), self.mileage.get())
            self._apply(updated)
            self.description.set("")
            self.mileage.set("")
        except ValueError as exc:
            messagebox.showerror("History entry error", str(exc))

    def _delete_event(self):
        if self.vehicle is None:
            return
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo("Car history", "Select a history event to delete.")
            return
        if not messagebox.askyesno("Delete history event",
                                  "Delete this user-entered history event?"):
            return
        updated = clean_car_history(self.vehicle.car_history)
        index = int(selected[0])
        if 0 <= index < len(updated["events"]):
            updated["events"].pop(index)
            self._apply(updated)
