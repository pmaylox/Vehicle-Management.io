"""Editable vehicle details with an explicit preview before applying VIN results."""
from queue import Empty, Queue
from threading import Thread
import tkinter as tk
from tkinter import messagebox, ttk

from vin_lookup import PROFILE_FIELDS, clean_profile, lookup_vin, normalize_vin


class VehicleProfileFields(ttk.LabelFrame):
    def __init__(self, form, row, name_var, year_var, existing=None):
        super().__init__(form, text="VIN and vehicle specifications", padding=10)
        self.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.original = clean_profile(existing)
        self.metadata = {key: self.original[key] for key in ("source", "decoded_at") if key in self.original}
        self.name_var, self.year_var = name_var, year_var
        self.vin = tk.StringVar(value=self.original.get("vin", ""))
        self.fields = {}
        self.queue = Queue()
        self.busy = False
        ttk.Label(self, text="VIN (17 characters):").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(self, textvariable=self.vin, width=30).grid(row=0, column=1, sticky="ew")
        self.lookup_button = ttk.Button(self, text="Look up VIN", command=self.lookup)
        self.lookup_button.grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(self, text="Lookup sends this VIN to NHTSA. Review results before applying.\n"
                  "Missing details, color and paint code can be entered manually.", wraplength=550).grid(
                      row=2, column=0, columnspan=2, sticky="w", pady=(0, 8))
        for row_number, (key, label) in enumerate(PROFILE_FIELDS.items(), 3):
            variable = tk.StringVar(value=self.original.get(key, ""))
            self.fields[key] = variable
            ttk.Label(self, text=label + ":").grid(row=row_number, column=0, sticky="w", pady=3)
            if key == "drive_type":
                entry = ttk.Combobox(self, textvariable=variable, width=34,
                    values=("FWD", "RWD", "AWD", "4WD", "2WD", "Unknown"))
            else:
                entry = ttk.Entry(self, textvariable=variable, width=36)
            entry.grid(row=row_number, column=1, sticky="ew", padx=(8, 0))
        self.columnconfigure(1, weight=1)
        self.status = tk.StringVar(value="Saved vehicle details are available offline.")
        ttk.Label(self, textvariable=self.status, wraplength=550).grid(
            row=3 + len(PROFILE_FIELDS), column=0, columnspan=2, sticky="w", pady=8)

    def get_value(self):
        vin = normalize_vin(self.vin.get())
        result = {key: variable.get().strip() for key, variable in self.fields.items() if variable.get().strip()}
        if vin:
            result["vin"] = vin
        # Provenance is only retained for the VIN that was actually decoded.
        if vin and vin == self.metadata.get("vin", self.original.get("vin")):
            result.update({key: self.metadata[key] for key in ("source", "decoded_at") if key in self.metadata})
        return result

    def lookup(self):
        if self.busy:
            return
        try:
            vin = normalize_vin(self.vin.get())
            if not vin:
                raise ValueError("Enter a VIN first.")
        except ValueError as error:
            messagebox.showerror("Invalid VIN", str(error), parent=self)
            return
        year = self.year_var.get().strip()
        self.busy = True
        self.lookup_button.configure(state="disabled")
        self.status.set("Looking up VIN… You can still enter details manually.")

        def worker():
            try:
                self.queue.put((vin, lookup_vin(vin, year), None))
            except Exception as error:
                self.queue.put((vin, None, str(error)))
        Thread(target=worker, daemon=True).start()
        self.after(100, self.poll)

    def poll(self):
        try:
            requested_vin, result, error = self.queue.get_nowait()
        except Empty:
            self.after(100, self.poll)
            return
        self.busy = False
        self.lookup_button.configure(state="normal")
        if self.vin.get().strip().upper() != requested_vin:
            self.status.set("VIN changed during lookup. Look up the current VIN again.")
            return
        if error:
            self.status.set("Lookup unsuccessful; manual entry is still available.")
            messagebox.showerror("VIN lookup", error, parent=self)
            return
        self.review(*result)

    def review(self, year, profile):
        dialog = tk.Toplevel(self)
        dialog.title("Review VIN results")
        dialog.transient(self.winfo_toplevel())
        body = ttk.Frame(dialog, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=f"{year} {profile.get('make', '')} {profile.get('model', '')}",
                  font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(body, text=f"VIN: {profile['vin']}\nSource: NHTSA vPIC · Availability varies by vehicle.").pack(anchor="w", pady=6)
        table = ttk.Treeview(body, columns=("field", "value"), show="headings", height=11)
        table.heading("field", text="Detail")
        table.heading("value", text="Decoded value")
        table.column("field", width=145)
        table.column("value", width=390)
        table.pack(fill="both", expand=True)
        for key, label in PROFILE_FIELDS.items():
            table.insert("", "end", values=(label, profile.get(key) or "Not provided — enter manually"))
        use_name = tk.BooleanVar(value=not self.name_var.get().strip())
        use_year = tk.BooleanVar(value=True)
        ttk.Checkbutton(body, text="Use decoded make/model as the vehicle name", variable=use_name).pack(anchor="w", pady=(8, 0))
        ttk.Checkbutton(body, text="Use decoded model year", variable=use_year).pack(anchor="w")
        ttk.Label(body, text="Only returned specifications will replace existing entries.\n"
                  "Color, paint code, odometer and maintenance history are kept unchanged.").pack(anchor="w", pady=6)
        controls = ttk.Frame(body)
        controls.pack(anchor="e")

        def close():
            dialog.destroy()
            self.winfo_toplevel().grab_set()

        def apply():
            if normalize_vin(self.vin.get()) != profile["vin"]:
                messagebox.showerror("VIN changed", "Look up the current VIN again before applying.", parent=dialog)
                return
            for key, variable in self.fields.items():
                if profile.get(key) and key not in ("color", "paint_code"):
                    variable.set(profile[key])
            self.metadata = {key: profile[key] for key in ("vin", "source", "decoded_at") if key in profile}
            if use_name.get():
                self.name_var.set(f"{profile['make']} {profile['model']}")
            if use_year.get():
                self.year_var.set(str(year))
            self.status.set("VIN results applied. Review fields, then Save Vehicle to keep them.")
            close()
        ttk.Button(controls, text="Cancel", command=close).pack(side="left", padx=4)
        ttk.Button(controls, text="Apply details", command=apply).pack(side="left")
        dialog.protocol("WM_DELETE_WINDOW", close)
        dialog.grab_set()
