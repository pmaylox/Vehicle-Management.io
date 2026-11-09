"""Reusable service suggestions and battery fields for record/edit dialogs."""
import tkinter as tk
from datetime import date
from tkinter import ttk
from battery import battery_details, service_suggestions, battery_term_text, battery_years_to_months


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
    years = tk.StringVar(value=battery_term_text(existing["months"]) if "months" in existing else "")
    term = tk.StringVar(value=existing.get("term", "Expected life"))
    maker = tk.StringVar(value=existing.get("maker", ""))
    frame = ttk.LabelFrame(form, text="Battery replacement", padding=8)
    frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    ttk.Checkbutton(frame, text="This service replaced the battery", variable=enabled).grid(
        row=0, column=0, columnspan=2, sticky="w")
    ttk.Label(frame, text="Installed (YYYY-MM-DD):").grid(row=1, column=0, sticky="w", pady=3)
    ttk.Entry(frame, textvariable=installed, width=20).grid(row=1, column=1, sticky="w")
    ttk.Label(frame, text="Listed term (years):").grid(row=2, column=0, sticky="w", pady=3)
    ttk.Combobox(frame, textvariable=years, width=20,
                 values=tuple(battery_term_text(n * 12) for n in range(1, 9))).grid(
                     row=2, column=1, sticky="w")
    ttk.Label(frame, text="Term type:").grid(row=3, column=0, sticky="w")
    ttk.Combobox(frame, textvariable=term, values=("Expected life", "Warranty"),
                 state="readonly", width=20).grid(row=3, column=1, sticky="w")
    ttk.Label(frame, text="Battery maker / brand:").grid(row=4, column=0, sticky="w", pady=3)
    ttk.Combobox(frame, textvariable=maker, width=20,
                 values=("ACDelco", "Bosch", "Champion", "Deka", "DieHard",
                         "Duralast", "Duralast Gold", "Duralast Platinum",
                         "EverStart", "Exide", "Interstate Batteries", "Motorcraft",
                         "NAPA", "Odyssey", "Optima")).grid(row=4, column=1, sticky="w")
    ttk.Label(frame, text="Choose years or type a custom term, e.g. 2.5 years.\nMaker is optional; type another brand if needed.").grid(
        row=5, column=0, columnspan=2, sticky="w", pady=3)

    def suggest(*args):
        if description.get().strip().casefold() == "battery replaced":
            enabled.set(True)
    description.trace_add("write", suggest)
    suggest()

    def get_value():
        if not enabled.get():
            return None
        count = battery_years_to_months(years.get())
        value = {"installed": installed.get().strip(), "months": count, "term": term.get()}
        details = battery_details(**value)
        value["installed"] = details["installed"].isoformat()
        if maker.get().strip():
            value["maker"] = maker.get().strip()
        if details["installed"] > date.fromisoformat(date_value()):
            raise ValueError("Battery installation cannot be after the service date.")
        return value
    return get_value
