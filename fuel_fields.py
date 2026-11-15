"""Optional fuel receipt details shared by the record and edit dialogs."""
import tkinter as tk
from tkinter import ttk


def octane_field(form, row, existing=None):
    variable = tk.StringVar(value="" if existing is None else str(existing))
    ttk.Label(form, text="Octane rating (pump number):").grid(
        row=row, column=0, sticky="w", pady=6)
    ttk.Combobox(form, textvariable=variable, width=23,
                 values=("", "85", "87", "89", "90", "91", "93", "94", "95", "98", "100")).grid(
                     row=row, column=1, padx=(12, 0), pady=6)
    ttk.Label(form, text="Optional. Enter the octane number, not ethanol %. Keep the same rating scale.").grid(
        row=row + 1, column=0, columnspan=2, sticky="w")
    return variable


def parse_octane(text):
    text = text.strip()
    if not text:
        return None
    if not text.isascii() or not text.isdecimal() or not 1 <= int(text) <= 150:
        raise ValueError("Octane must be a whole pump rating from 1 to 150, or blank if unknown. Do not enter a % sign.")
    return int(text)


def fuel_type_field(form, row, existing=None, octane_var=None):
    variable = tk.StringVar(value=existing or "")
    ttk.Label(form, text="Fuel type / blend:").grid(row=row, column=0, sticky="w", pady=6)
    ttk.Combobox(form, textvariable=variable, width=28, values=(
        "", "Gasoline — blend unknown", "E0 — Non-ethanol",
        "E10 — gasoline", "E15 — gasoline", "E85 — flex fuel",
        "Diesel", "Diesel — B5", "Diesel — B20", "Biodiesel — B100"
    )).grid(row=row, column=1, padx=(12, 0), pady=6)
    ttk.Label(form, text="Optional. Select the pump's label or type another fuel/blend.").grid(
        row=row + 1, column=0, columnspan=2, sticky="w")

    def update_octane(*args):
        if octane_var is None:
            return
        diesel = is_diesel(variable.get())
        if diesel:
            octane_var.set("")
        for widget in form.winfo_children():
            if isinstance(widget, ttk.Combobox) and str(widget.cget("textvariable")) == str(octane_var):
                widget.configure(state="disabled" if diesel else "normal")

    variable.trace_add("write", update_octane)
    update_octane()
    return variable


def is_diesel(text):
    return "diesel" in text.casefold()


def parse_fuel_type(text):
    text = text.strip()
    if len(text) > 80 or any(ord(char) < 32 for char in text):
        raise ValueError("Fuel type must be a single line of no more than 80 characters.")
    return text or None
