"""Receipt camera/import controls with local OCR and review before autofill."""
import os
from pathlib import Path
from queue import Queue, Empty
from threading import Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from receipts import extract_fields, recognize_photo, receipt_path, store_photo


def scrollable_form(dialog):
    """Keep receipt controls and Save/Cancel reachable on shorter displays."""
    shell = ttk.Frame(dialog)
    shell.pack(fill="both", expand=True)
    canvas = tk.Canvas(shell, highlightthickness=0, width=650,
                       height=min(690, max(350, dialog.winfo_screenheight() - 220)))
    scrollbar = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.configure(yscrollcommand=scrollbar.set)
    form = ttk.Frame(canvas, padding=20)
    item = canvas.create_window(0, 0, window=form, anchor="nw")
    form.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda event: canvas.itemconfigure(item, width=event.width))

    def wheel(event):
        canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"
    # A dialog-local bindtag, not a global mouse-wheel binding.
    dialog.bind("<MouseWheel>", wheel)
    return form


class ReceiptPanel(ttk.LabelFrame):
    def __init__(self, form, row, kind, fields, existing=None):
        super().__init__(form, text="Receipt photo", padding=8)
        self.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.kind, self.fields = kind, fields
        self.existing = existing
        self.source = None
        self.created = None
        self.busy = False
        self.queue = Queue()
        buttons = ttk.Frame(self)
        buttons.pack(anchor="w")
        ttk.Button(buttons, text="Take photo", command=self.camera).pack(side="left")
        ttk.Button(buttons, text="Choose photo", command=self.choose).pack(side="left", padx=4)
        self.read_button = ttk.Button(buttons, text="Read / autofill", command=self.scan)
        self.read_button.pack(side="left", padx=4)
        ttk.Button(buttons, text="View photo", command=self.view).pack(side="left")
        self.status = tk.StringVar(value="Receipt attached" if existing else "No receipt attached. Photos are read locally on this PC.")
        ttk.Label(self, textvariable=self.status, wraplength=570).pack(anchor="w", pady=(6, 0))

    def camera(self):
        try:
            os.startfile("microsoft.windows.camera:")
        except OSError as error:
            messagebox.showerror("Camera unavailable", f"{error}\nYou can use Choose photo for a phone photo instead.", parent=self)
            return
        self.status.set("Take and save the photo in Windows Camera, then click Choose photo here (usually Pictures / Camera Roll).")

    def choose(self):
        path = filedialog.askopenfilename(parent=self, title="Choose a receipt photo",
            initialdir=str(Path.home() / "Pictures"),
            filetypes=[("Receipt photos", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"), ("All files", "*.*")])
        if not path:
            return
        try:
            from PIL import Image
            with Image.open(path) as image:
                image.verify()
        except (OSError, ValueError) as error:
            messagebox.showerror("Cannot open photo", str(error), parent=self)
            return
        self.source = path
        self.status.set(f"Selected: {Path(path).name}. Review extracted values before saving.")
        self.scan()

    def current_path(self):
        return Path(self.source) if self.source else receipt_path(self.existing) if self.existing else None

    def view(self):
        try:
            path = self.current_path()
            if path is None:
                messagebox.showinfo("No receipt", "Choose a photo first.", parent=self)
                return
            if not path.is_file():
                raise OSError("Receipt photo is missing. Keep the receipts folder with your vehicle data.")
            os.startfile(str(path))
        except (OSError, ValueError) as error:
            messagebox.showerror("Cannot view receipt", str(error), parent=self)

    def scan(self):
        if self.busy:
            return
        try:
            path = self.current_path()
        except ValueError as error:
            messagebox.showerror("Cannot read receipt", str(error), parent=self)
            return
        if path is None:
            self.choose()
            return
        self.busy = True
        self.read_button.configure(state="disabled")
        self.status.set("Reading receipt locally… You can still enter details manually.")

        def worker():
            try:
                self.queue.put((recognize_photo(path), None))
            except Exception as error:
                self.queue.put((None, str(error)))
        Thread(target=worker, daemon=True).start()
        self.after(100, self.poll)

    def poll(self):
        try:
            lines, error = self.queue.get_nowait()
        except Empty:
            self.after(100, self.poll)
            return
        self.busy = False
        self.read_button.configure(state="normal")
        if error:
            self.status.set("Photo selected; automatic reading failed. Enter details manually or retry.")
            messagebox.showerror("Receipt could not be read", error, parent=self)
            return
        self.status.set("Review the detected values. Fields not found will stay unchanged.")
        self.review(lines)

    def review(self, lines):
        proposals = extract_fields(lines, self.kind)
        dialog = tk.Toplevel(self)
        dialog.title("Review receipt autofill")
        dialog.transient(self.winfo_toplevel())
        body = ttk.Frame(dialog, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Check the photo and values. Apply only the fields you want.\nThis does not save a record or reset maintenance.").pack(anchor="w")
        rows = {}
        names = {"date": "Date", "cost": "Total cost ($)", "mileage": "Odometer", "gallons": "US gallons",
                 "description": "Service performed", "octane": "Octane rating", "fuel_type": "Fuel type / blend"}
        for key, value in proposals.items():
            if key not in self.fields:
                continue
            row = ttk.Frame(body)
            row.pack(fill="x", pady=3)
            selected = tk.BooleanVar(value=True)
            variable = tk.StringVar(value=value)
            ttk.Checkbutton(row, text=names[key], variable=selected, width=22).pack(side="left")
            ttk.Entry(row, textvariable=variable, width=44).pack(side="left")
            rows[key] = selected, variable
        if not rows:
            ttk.Label(body, text="No editable fields were confidently identified. You can enter them manually.").pack(anchor="w", pady=8)
        raw = tk.Text(body, width=78, height=10, wrap="word")
        raw.pack(fill="both", expand=True, pady=8)
        raw.insert("1.0", "\n".join(lines) or "No text recognized.")
        raw.configure(state="disabled")
        controls = ttk.Frame(body)
        controls.pack(anchor="e")

        def close():
            dialog.destroy()
            if self.winfo_exists():
                self.winfo_toplevel().grab_set()

        def apply():
            for key, (selected, variable) in rows.items():
                if selected.get():
                    self.fields[key].set(variable.get())
            self.status.set("Receipt values applied. Check all fields, then use Save to record them.")
            close()
        ttk.Button(controls, text="Keep current fields", command=close).pack(side="left", padx=4)
        ttk.Button(controls, text="Apply selected fields", command=apply).pack(side="left")
        dialog.protocol("WM_DELETE_WINDOW", close)
        dialog.grab_set()

    def commit(self, record):
        if self.source:
            self.created = store_photo(self.source)
            record["receipt_photo"] = self.created
        elif self.existing:
            record["receipt_photo"] = self.existing

    def rollback(self):
        if self.created:
            try:
                receipt_path(self.created).unlink(missing_ok=True)
            except OSError:
                # Never hide the original record-save error if a file is locked.
                pass
            self.created = None
