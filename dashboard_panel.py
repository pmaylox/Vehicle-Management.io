"""Responsive pictured garage with persistent, selected-vehicle quick actions."""
import tkinter as tk
from tkinter import ttk

from vehicle_card import VehicleCard


class DashboardPanel(ttk.Frame):
    def __init__(self, parent, on_select, on_manage, actions):
        super().__init__(parent)
        self.on_select = on_select
        self.cards = []
        self.signature = None
        self.vehicles = []
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="Dashboard", font=("Segoe UI", 23, "bold")).pack(side="left")
        ttk.Button(header, text="Manage vehicles", command=on_manage).pack(side="right")
        ttk.Label(self, text="Your garage · select a vehicle to see its details").pack(anchor="w", pady=(0, 12))

        area = ttk.Frame(self)
        area.pack(fill="both", expand=True)
        scroll = ttk.Scrollbar(area, orient="vertical")
        scroll.pack(side="right", fill="y")
        self.canvas = tk.Canvas(area, background="#F5F1EB", highlightthickness=0,
                                yscrollcommand=scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scroll.configure(command=self.canvas.yview)
        self.content = ttk.Frame(self.canvas)
        self.window = self.canvas.create_window(0, 0, window=self.content, anchor="nw")
        self.canvas.bind("<Configure>", self.arrange)
        self.content.bind("<Configure>", lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        footer = ttk.Frame(self, padding=(0, 12, 0, 0))
        footer.pack(fill="x")
        self.selection = tk.StringVar(value="Select a vehicle")
        self.selection_label = ttk.Label(footer, textvariable=self.selection,
                                        font=("Segoe UI", 11, "bold"))
        self.selection_label.pack(anchor="w", pady=(0, 8))
        action_row = ttk.Frame(footer)
        action_row.pack(fill="x")
        self.action_buttons = []
        for index, (label, callback) in enumerate(actions):
            button = ttk.Button(action_row, text=label, command=callback)
            button.grid(row=index // 2, column=index % 2, sticky="ew", padx=(0, 6), pady=3)
            self.action_buttons.append(button)
        action_row.columnconfigure((0, 1), weight=1)

    def _scroll(self, event):
        if self.canvas.yview() != (0.0, 1.0):
            self.canvas.yview_scroll(-int(event.delta / 120), "units")
        return "break"

    def set_vehicles(self, vehicles, selected):
        self.vehicles = list(vehicles)
        signature = tuple((id(v), v.name, v.year, v.mileage, v.photo_path, v.mobile_photo,
                           v.last_service_mileage, v.service_interval,
                           v.last_tire_rotation_mileage, v.tire_rotation_interval) for v in vehicles)
        if signature != self.signature:
            for child in self.content.winfo_children():
                child.destroy()
            self.cards.clear()
            for vehicle in vehicles:
                card = VehicleCard(self.content, vehicle, self.on_select, selected=vehicle is selected)
                self.cards.append(card)
                for widget in (card, *card.winfo_children()):
                    widget.bind("<MouseWheel>", self._scroll)
                    for child in widget.winfo_children():
                        child.bind("<MouseWheel>", self._scroll)
            if not vehicles:
                ttk.Label(self.content, text="No matching vehicles. Use Manage vehicles to add one or clear the search.",
                          wraplength=300).grid(row=0, column=0, padx=12, pady=24)
            self.signature = signature
        for vehicle, card in zip(vehicles, self.cards):
            card.set_selected(vehicle is selected)
        self.selection.set(f"{selected.year} {selected.name} · {selected.mileage:,} miles" if selected else "Select a vehicle")
        for button in self.action_buttons:
            button.configure(state="normal" if selected else "disabled")
        self.arrange()

    def arrange(self, event=None):
        width = max(1, self.canvas.winfo_width())
        self.canvas.itemconfigure(self.window, width=width)
        self.selection_label.configure(wraplength=max(180, width - 15))
        columns = 2 if width >= 680 else 1
        for column in range(2):
            self.content.columnconfigure(column, weight=1 if column < columns else 0, uniform="cards")
        for index, card in enumerate(self.cards):
            card.grid(row=index // columns, column=index % columns, sticky="nsew", padx=5, pady=6)
            card.fit_width(max(180, width // columns - 50))
