import tkinter as tk
from tkinter import ttk


class OverviewPanel(ttk.Frame):
    def __init__(self, parent, colors):
        super().__init__(parent)

        self.heading = tk.StringVar(value="Select a vehicle")
        self.mileage = tk.StringVar()
        self.oil = tk.StringVar(value="Oil change: —")
        self.tires = tk.StringVar(value="Tire rotation: —")
        self.details = tk.StringVar()

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
        self.add_label(
            vehicle_card, self.heading, "CardTitle.TLabel"
        )
        self.add_label(
            vehicle_card, self.mileage, "CardAccent.TLabel"
        )

        maintenance_card = self.make_card(content)
        ttk.Label(
            maintenance_card,
            text="MAINTENANCE",
            style="CardAccent.TLabel"
        ).pack(anchor="w", pady=(0, 8))

        self.add_label(maintenance_card, self.oil)
        self.add_label(maintenance_card, self.tires)

        details_card = self.make_card(content)
        self.add_label(details_card, self.details)

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