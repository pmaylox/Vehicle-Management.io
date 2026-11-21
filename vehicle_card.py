from pathlib import Path
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

        title = tk.Label(
            self,
            text=f"{vehicle.year} {vehicle.name}",
            font=("Segoe UI", 16, "bold"),
            background="#FFFFFF",
            foreground="#292724",
            wraplength=280
        )
        title.pack(anchor="w")

        photo_label = tk.Label(
            self,
            text="No vehicle photo selected",
            background="#FFFFFF",
            foreground="#6B655E"
        )
        photo_label.pack(fill="x", pady=12)

        if vehicle.photo_path:
            try:
                path = Path(vehicle.photo_path)
                if not path.is_absolute():
                    path = Path(__file__).resolve().parent / path

                with Image.open(path) as source:
                    photo = ImageOps.exif_transpose(source).convert("RGBA")
                    photo.thumbnail(
                        (280, 160),
                        Image.Resampling.LANCZOS
                    )

                self.photo_image = ImageTk.PhotoImage(photo, master=self)
                photo_label.configure(image=self.photo_image, text="")

            except (OSError, ValueError, Image.DecompressionBombError):
                photo_label.configure(text="Vehicle photo unavailable")

        tk.Label(
            self,
            text=f"{vehicle.mileage:,} miles",
            font=("Segoe UI", 20, "bold"),
            background="#FFFFFF",
            foreground="#292724"
        ).pack(anchor="w")

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

        tk.Label(
            self,
            text=status,
            font=("Segoe UI", 11),
            background="#F1DDD2",
            foreground="#292724",
            padx=10,
            pady=8,
            wraplength=260
        ).pack(fill="x", pady=(12, 0))

        def select_vehicle(event=None):
            command(vehicle)
            return "break"

        self.bind("<Button-1>", select_vehicle)
        self.bind("<Return>", select_vehicle)
        self.bind("<space>", select_vehicle)

        for widget in self.winfo_children():
            widget.bind("<Button-1>", select_vehicle)