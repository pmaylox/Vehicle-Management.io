from pathlib import Path
import base64
from io import BytesIO
import re
import tkinter as tk

from PIL import Image, ImageOps, ImageTk


class VehicleCard(tk.Frame):
    def __init__(self, parent, vehicle, command, selected=False):
        super().__init__(
            parent,
            background="#FFFFFF",
            padx=14,
            pady=14,
            highlightthickness=2,
            highlightbackground="#B65C3A" if selected else "#DDD5CD",
            cursor="hand2",
            takefocus=True
        )

        self.photo_image = None
        self.wrapping_labels = []

        title = tk.Label(
            self,
            text=f"{vehicle.year} {vehicle.name}",
            font=("Segoe UI", 16, "bold"),
            background="#FFFFFF",
            foreground="#292724",
            wraplength=280
        )
        title.pack(anchor="w")
        self.wrapping_labels.append(title)

        photo_area = tk.Frame(self, background="#FFFFFF", height=160)
        photo_area.pack(fill="x", pady=12)
        photo_area.pack_propagate(False)
        photo_label = tk.Label(
            photo_area,
            text="No vehicle photo selected",
            background="#FFFFFF",
            foreground="#6B655E"
        )
        photo_label.pack(fill="both", expand=True)

        if vehicle.photo_path or vehicle.mobile_photo:
            try:
                path = Path(vehicle.photo_path)
                if not path.is_absolute():
                    path = Path(__file__).resolve().parent / path

                if vehicle.photo_path and path.is_file():
                    photo_source = path
                elif (len(vehicle.mobile_photo) <= 1_400_000 and
                      re.fullmatch(r"data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}", vehicle.mobile_photo)):
                    photo_source = BytesIO(base64.b64decode(vehicle.mobile_photo.split(",", 1)[1], validate=True))
                else:
                    raise ValueError("No usable vehicle photo")
                with Image.open(photo_source) as source:
                    photo = ImageOps.exif_transpose(source).convert("RGBA")
                    photo.thumbnail(
                        (280, 160),
                        Image.Resampling.LANCZOS
                    )

                self.photo_image = ImageTk.PhotoImage(photo, master=self)
                photo_label.configure(image=self.photo_image, text="")

            except (OSError, ValueError, Image.DecompressionBombError):
                photo_label.configure(text="Vehicle photo unavailable")

        status_label = tk.Label(
            self,
            text=f"{vehicle.mileage:,} miles",
            font=("Segoe UI", 20, "bold"),
            background="#FFFFFF",
            foreground="#292724"
        )
        status_label.pack(anchor="w")
        self.wrapping_labels.append(status_label)

        if vehicle.last_service_mileage > vehicle.mileage:
            status = "Check recorded service mileage"
        else:
            remaining = (
                vehicle.last_service_mileage
                + vehicle.service_interval
                - vehicle.mileage
            )
            status = (
                "Oil service due"
                if remaining <= 0
                else f"Oil service: {remaining:,} miles left"
            )

        badge = tk.Label(
            self,
            text=status,
            font=("Segoe UI", 11),
            background="#FFF0D2" if "due" in status or "Check" in status else "#E1F3E4",
            foreground="#292724",
            padx=10,
            pady=8,
            wraplength=260
        )
        badge.pack(fill="x", pady=(12, 0))
        self.wrapping_labels.append(badge)

        def select_vehicle(event=None):
            command(vehicle)
            return "break"

        self.bind("<Button-1>", select_vehicle)
        self.bind("<Return>", select_vehicle)
        self.bind("<space>", select_vehicle)

        for widget in self.winfo_children():
            widget.bind("<Button-1>", select_vehicle)
        photo_label.bind("<Button-1>", select_vehicle)

    def set_selected(self, selected):
        self.configure(highlightbackground="#B65C3A" if selected else "#DDD5CD")

    def fit_width(self, width):
        for label in self.wrapping_labels:
            label.configure(wraplength=width)
