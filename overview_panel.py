from pathlib import Path
from PIL import Image, ImageOps, ImageTk
import tkinter as tk
from tkinter import ttk


class OverviewPanel(ttk.Frame):
   
    def set_photo(self, filename):
        self.vehicle_photo.configure(image="", text="")
        self.photo_image = None

        if not filename:
            self.vehicle_photo.configure(
                text="Add a photo in Edit Vehicle"
            )
            return

        try:
            path = Path(filename)
            if not path.is_absolute():
                path = Path(__file__).resolve().parent / path

            with Image.open(path) as source:
                photo = ImageOps.exif_transpose(source).convert("RGBA")
                photo.thumbnail((360, 200), Image.Resampling.LANCZOS)

            self.photo_image = ImageTk.PhotoImage(
                photo, master=self.vehicle_photo
            )
            self.vehicle_photo.configure(image=self.photo_image)

        except (OSError, ValueError, Image.DecompressionBombError):
            self.vehicle_photo.configure(
                text="Photo unavailable — choose another in Edit Vehicle"
            )
    
    def __init__(self, parent, colors):
        super().__init__(parent)

        self.heading = tk.StringVar(value="Select a vehicle")
        self.mileage = tk.StringVar()
        self.specifications = tk.StringVar()
        self.oil = tk.StringVar(value="Oil change: —")
        self.tires = tk.StringVar(value="Tire rotation: —")
        self.details = tk.StringVar()
        self.battery = tk.StringVar()
        self.pressures = tk.StringVar()
        self.service = tk.StringVar()
        self.fuel = tk.StringVar()

        style = ttk.Style(self)
        style.configure(
            "Card.TFrame",
            background="#FFFFFF"
        )
        style.configure(
            "Card.TLabel",
            background="#FFFFFF",
            foreground=colors["text"],
            font=("Segoe UI", 12)
        )
        style.configure(
            "CardTitle.TLabel",
            background="#FFFFFF",
            foreground=colors["text"],
            font=("Segoe UI", 18, "bold")
        )
        style.configure(
            "CardAccent.TLabel",
            background="#FFFFFF",
            foreground=colors["accent"],
            font=("Segoe UI", 13)
        )

        scrollbar = ttk.Scrollbar(self, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.canvas = tk.Canvas(
            self,
            background=colors["background"],
            highlightthickness=0,
            yscrollcommand=scrollbar.set
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self.canvas.yview)

        content = ttk.Frame(self.canvas)
        content_window = self.canvas.create_window(
            0, 0, window=content, anchor="nw"
        )

        self.wrapping_labels = []

        vehicle_card = self.make_card(content)
        self.vehicle_photo = ttk.Label(
            vehicle_card,
            text="No vehicle photo selected",
            style="Card.TLabel",
            anchor="center"
        )
        self.vehicle_photo.pack(fill="x", pady=(0, 12))
        self.photo_image = None
        self.add_label(
            vehicle_card, self.heading, "CardTitle.TLabel"
        )
        self.add_label(
            vehicle_card, self.mileage, "CardAccent.TLabel"
        )

        profile_card = self.make_card(content)
        ttk.Label(profile_card, text="VEHICLE DETAILS", style="CardAccent.TLabel").pack(
            anchor="w", pady=(0, 8))
        self.add_label(profile_card, self.specifications)

        maintenance_card = self.make_card(content)
        ttk.Label(
            maintenance_card,
            text="MAINTENANCE",
            style="CardAccent.TLabel"
        ).pack(anchor="w", pady=(0, 8))

        self.add_label(maintenance_card, self.oil)
        self.add_label(maintenance_card, self.tires)

        battery_card = self.make_card(content)
        ttk.Label(
            battery_card,
            text="BATTERY",
            style="CardAccent.TLabel"
        ).pack(anchor="w", pady=(0, 8))
        self.add_label(battery_card, self.battery)

        pressure_card = self.make_card(content)
        ttk.Label(
            pressure_card,
            text="TIRE PRESSURE · calculated PSI",
            style="CardAccent.TLabel"
        ).pack(anchor="w", pady=(0, 8))
        self.add_label(pressure_card, self.pressures)

        service_card = self.make_card(content)
        ttk.Label(
            service_card, text="SERVICE", style="CardAccent.TLabel"
        ).pack(anchor="w", pady=(0, 8))
        self.add_label(service_card, self.service)

        fuel_card = self.make_card(content)
        ttk.Label(
            fuel_card, text="FUEL", style="CardAccent.TLabel"
        ).pack(anchor="w", pady=(0, 8))
        self.add_label(fuel_card, self.fuel)

        status_label = ttk.Label(
            content, textvariable=self.details, justify="left"
        )
        status_label.pack(anchor="w", fill="x")
        self.wrapping_labels.append(status_label)

        def fit_width(event):
            self.canvas.itemconfigure(
                content_window, width=event.width
            )
            for label in self.wrapping_labels:
                label.configure(
                    wraplength=max(120, event.width - 40)
                )

        self.canvas.bind("<Configure>", fit_width)
        content.bind(
            "<Configure>",
            lambda event: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        # Newly selected vehicles should open with their title fully visible.
        self.heading.trace_add("write", self.reset_scroll)
        self.canvas.bind("<Map>", self.reset_scroll)

    def reset_scroll(self, *args):
        self.after_idle(lambda: self.canvas.yview_moveto(0))

    def make_card(self, parent):
        card = ttk.Frame(
            parent, style="Card.TFrame", padding=16
        )
        card.pack(fill="x", pady=(0, 12))
        return card

    def add_label(self, parent, variable, style="Card.TLabel"):
        label = ttk.Label(
            parent,
            textvariable=variable,
            style=style,
            justify="left"
        )
        label.pack(anchor="w", fill="x", pady=(2, 4))
        self.wrapping_labels.append(label)
