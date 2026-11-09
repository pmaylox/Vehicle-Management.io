"""Reusable service suggestions and battery fields for record/edit dialogs."""
import tkinter as tk
from datetime import date
from tkinter import ttk
from battery import battery_details, service_suggestions


def service_entry(form, variable, history):
    entry = ttk.Combobox(form, textvariable=variable, width=40,
                         values=service_suggestions("", history))
    entry.bind("<KeyRelease>", lambda event: entry.configure(
        values=service_suggestions(variable.get(), history)))
    return entry


def battery_fields(form, row, description, date_value, existing=None):
    existing = existing or {}
    enabled = tk.BooleanVar(value=bool(existing))
    installed = tk.StringVar(value=existing.get("installed", date_value()))
    months = tk.StringVar(value=str(existing.get("months", "")))
    term = tk.StringVar(value=existing.get("term", "Expected life"))
    frame = ttk.LabelFrame(form, text="Battery replacement", padding=8)
    frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    ttk.Checkbutton(frame, text="This service replaced the battery", variable=enabled).grid(
        row=0, column=0, columnspan=2, sticky="w")
    for index, (label, variable) in enumerate([
        ("Installed (YYYY-MM-DD):", installed), ("Listed term (months):", months)
    ], 1):
        ttk.Label(frame, text=label).grid(row=index, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=variable, width=20).grid(row=index, column=1, sticky="w")
    ttk.Label(frame, text="Term type:").grid(row=3, column=0, sticky="w")
    ttk.Combobox(frame, textvariable=term, values=("Expected life", "Warranty"),
                 state="readonly", width=20).grid(row=3, column=1, sticky="w")
    ttk.Label(frame, text="Use the label's term; an estimate is not a failure prediction.").grid(
        row=4, column=0, columnspan=2, sticky="w", pady=3)

    def suggest(*args):
        if description.get().strip().casefold() == "battery replaced":
            enabled.set(True)
    description.trace_add("write", suggest)
    suggest()

    def get_value():
        if not enabled.get():
            return None
        try:
            count = int(months.get().strip())
        except ValueError:
            raise ValueError("Enter a positive whole number of months for the battery term.") from None
        value = {"installed": installed.get().strip(), "months": count, "term": term.get()}
        details = battery_details(**value)
        value["installed"] = details["installed"].isoformat()
        if details["installed"] > date.fromisoformat(date_value()):
            raise ValueError("Battery installation cannot be after the service date.")
        return value
    return get_value
