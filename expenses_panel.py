"""Desktop expenses: shared mobile records, local document access, safe saves."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from validation import parse_cost_cents


class ExpensesPanel(ttk.Frame):
    def __init__(self, parent, on_save):
        super().__init__(parent)
        self.pack(fill="both", expand=True)
        self.on_save = on_save
        self.vehicle = None
        self.heading = tk.StringVar(value="Expenses")
        self.summary = tk.StringVar()
        ttk.Label(self, textvariable=self.heading, font=("Segoe UI", 20, "bold")).pack(anchor="w")
        self.summary_label = ttk.Label(self, textvariable=self.summary, font=("Segoe UI", 11), justify="left")
        self.summary_label.pack(anchor="w", pady=12)
        ttk.Label(self, text="Other expense history · fuel and service costs remain in their own histories").pack(anchor="w", pady=6)
        area = ttk.Frame(self)
        area.pack(fill="both", expand=True)
        area.rowconfigure(0, weight=1)
        area.columnconfigure(0, weight=1)
        self.table = ttk.Treeview(area, columns=("date", "description", "amount", "document"), show="headings", selectmode="browse")
        for key, label, width in [("date", "Date", 100), ("description", "Description", 230), ("amount", "Cost ($)", 90), ("document", "Document", 110)]:
            self.table.heading(key, text=label)
            self.table.column(key, width=width, minwidth=70, stretch=key == "description")
        self.table.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(area, orient="vertical", command=self.table.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(area, orient="horizontal", command=self.table.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=10)
        for index, (text, command) in enumerate([
            ("Add expense", self.add), ("Open document", self.open_document),
            ("Attach local PDF", self.attach), ("Delete expense", self.delete),
        ]):
            ttk.Button(actions, text=text, command=command).grid(row=index // 2, column=index % 2, sticky="ew", padx=3, pady=3)
        actions.columnconfigure((0, 1), weight=1)
        self.bind("<Configure>", lambda e: self.summary_label.configure(wraplength=max(180, e.width - 20)))

    def show(self, vehicle):
        self.vehicle = vehicle
        self.table.delete(*self.table.get_children())
        if vehicle is None:
            self.heading.set("Expenses")
            self.summary.set("Select a vehicle on the Dashboard.")
            return
        self.heading.set(f"{vehicle.year} {vehicle.name}")
        service = sum(r.get("cost_cents") or 0 for r in vehicle.service_history)
        fuel = sum(r.get("cost_cents") or 0 for r in vehicle.fuel_history)
        other = sum(r.get("cost_cents") or 0 for r in vehicle.mobile_expenses)
        self.summary.set(f"Recorded spending  ${(service + fuel + other) / 100:,.2f}\nService  ${service / 100:,.2f}     Fuel  ${fuel / 100:,.2f}     Other  ${other / 100:,.2f}")
        for index, record in sorted(enumerate(vehicle.mobile_expenses), key=lambda item: str(item[1].get("date", "")), reverse=True):
            document = record.get("desktop_document_path") or record.get("expense_document") or record.get("receipt_photo")
            self.table.insert("", "end", iid=str(index), values=(record.get("date", ""), record.get("description", ""), f"{(record.get('cost_cents') or 0) / 100:,.2f}", "Attached" if document else "—"))

    def _selected(self):
        rows = self.table.selection()
        if self.vehicle is None or not rows:
            messagebox.showinfo("Expenses", "Select an expense first.", parent=self.winfo_toplevel())
            return None
        return int(rows[0])

    def _commit(self, changed):
        original = self.vehicle.mobile_expenses
        self.vehicle.mobile_expenses = changed
        try:
            self.on_save()
        except (OSError, ValueError, TypeError) as error:
            self.vehicle.mobile_expenses = original
            messagebox.showerror("Expense not saved", str(error), parent=self.winfo_toplevel())
            return False
        return True

    def add(self):
        if self.vehicle is None:
            return
        vehicle = self.vehicle
        dialog = tk.Toplevel(self)
        dialog.title("Add other expense")
        dialog.transient(self.winfo_toplevel())
        form = ttk.Frame(dialog, padding=18)
        form.pack(fill="both", expand=True)
        fields = {}
        for row, (name, value) in enumerate([("Description", ""), ("Date (YYYY-MM-DD)", date.today().isoformat()), ("Cost ($)", "")]):
            ttk.Label(form, text=name).grid(row=row, column=0, sticky="w", pady=7)
            fields[name] = tk.StringVar(value=value)
            ttk.Entry(form, textvariable=fields[name], width=34).grid(row=row, column=1, padx=8)

        def save():
            try:
                description = fields["Description"].get().strip()
                if not description:
                    raise ValueError("Enter an expense description.")
                day = date.fromisoformat(fields["Date (YYYY-MM-DD)"].get().strip())
                if day > date.today():
                    raise ValueError("Expense date cannot be in the future.")
                cents = parse_cost_cents(fields["Cost ($)"].get().strip())
                if self.vehicle is not vehicle:
                    raise ValueError("Vehicle selection changed. Close and reopen the form.")
                record = {"date": day.isoformat(), "description": description, "cost_cents": cents, "mileage": vehicle.mileage}
                if self._commit([*deepcopy(vehicle.mobile_expenses), record]):
                    dialog.destroy()
            except (ValueError, TypeError) as error:
                messagebox.showerror("Check expense", str(error), parent=dialog)

        ttk.Button(form, text="Save expense", command=save).grid(row=3, column=1, sticky="e", pady=12)
        ttk.Button(form, text="Cancel", command=dialog.destroy).grid(row=3, column=0, sticky="w", pady=12)
        dialog.grab_set()

    def attach(self):
        index = self._selected()
        if index is None:
            return
        filename = filedialog.askopenfilename(parent=self.winfo_toplevel(), title="Attach PDF on this PC", filetypes=[("PDF document", "*.pdf")])
        if not filename:
            return
        path = Path(filename)
        try:
            if path.suffix.lower() != ".pdf" or path.stat().st_size > 30_000_000:
                raise ValueError("Choose a PDF under 30 MB.")
            with path.open("rb") as source:
                if not source.read(5).startswith(b"%PDF-"):
                    raise ValueError("This file is not a PDF.")
            changed = deepcopy(self.vehicle.mobile_expenses)
            changed[index]["desktop_document_path"] = str(path)
            self._commit(changed)
        except (OSError, ValueError) as error:
            messagebox.showerror("Cannot attach PDF", str(error), parent=self.winfo_toplevel())

    def open_document(self):
        index = self._selected()
        if index is None:
            return
        filename = self.vehicle.mobile_expenses[index].get("desktop_document_path")
        if filename and Path(filename).is_file() and Path(filename).suffix.lower() == ".pdf":
            os.startfile(filename)
        else:
            messagebox.showinfo("Document on another device", "A phone PDF reference does not contain the actual file. Export the PDF from the phone, copy it to this PC, then use Attach local PDF. Existing phone references are preserved.", parent=self.winfo_toplevel())

    def delete(self):
        index = self._selected()
        if index is not None and messagebox.askyesno("Delete expense", "Delete this expense entry? Attached files will not be deleted.", parent=self.winfo_toplevel()):
            changed = deepcopy(self.vehicle.mobile_expenses)
            changed.pop(index)
            self._commit(changed)
