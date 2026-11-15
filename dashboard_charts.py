import tkinter as tk
from tkinter import ttk
from datetime import date
from decimal import Decimal

def cost_per_mile_points(records):
    points = []
    starting_mileage = None
    interval_cents = 0
    costs_known = True

    for record in records:
        mileage = record["mileage"]

        if mileage is None:
            starting_mileage = None
            interval_cents = 0
            costs_known = True
            continue

        if starting_mileage is None:
            if record["full_tank"]:
                starting_mileage = mileage
            continue

        cents = record.get("cost_cents")
        if cents is None:
            costs_known = False
        else:
            interval_cents += cents

        if record["full_tank"]:
            miles = mileage - starting_mileage

            if miles > 0 and costs_known:
                cost_per_mile = Decimal(interval_cents) / 100 / miles
                points.append((
                    date.fromisoformat(record["date"]).strftime("%m/%d/%y"),
                    float(cost_per_mile)
                ))

            starting_mileage = mileage
            interval_cents = 0
            costs_known = True

    return points

class DashboardChart(ttk.Frame):
    def __init__(self, parent, title, kind="bar", decimals=1):
        super().__init__(parent, padding=12)

        self.kind = kind
        self.points = []
        self.decimals = decimals

        ttk.Label(
            self,
            text=title,
            font=("segeo UI", 14, "bold")
        ).pack(anchor="w")

        self.canvas = tk.Canvas(
            self,
            background="#ffffff",
            height=240,
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.draw)

    def set_data(self, points):
        self.points = points
        self.draw()

 
    def draw(self, event=None):
        canvas = self.canvas
        canvas.delete("all")

        width = max(canvas.winfo_width(), 300)
        height = max(canvas.winfo_height(), 200)

        if not self.points:
            canvas.create_text(
                width / 2, height / 2,
                text="Not enough recorded data yet",
                fill="#666666",
                font=("Segoe UI", 11)
            )
            return

        left = 65
        right = width - 25
        top = 30
        bottom = height - 45

        highest = max(value for label, value in self.points)
        scale_max = highest * 1.2 if highest > 0 else 1

        for step in range(5):
            fraction = step / 4
            y = bottom - fraction * (bottom - top)

            canvas.create_line(
                left, y, right, y, fill="#E8E3DE"
            )
            canvas.create_text(
                left - 8, y,
                text=f"{fraction * scale_max:,.{self.decimals}f}",
                anchor="e",
                fill="#666666"
            )

        spacing = (right - left) / len(self.points)
        previous = None

        for index, (label, value) in enumerate(self.points):
            x = left + spacing * (index + 0.5)
            y = bottom - value / scale_max * (bottom - top)

            if self.kind == "bar":
                half_width = spacing * 0.28
                canvas.create_rectangle(
                    x - half_width, y,
                    x + half_width, bottom,
                    fill="#B65C3A",
                    outline=""
                )
            else:
                if previous is not None:
                    canvas.create_line(
                        *previous, x, y,
                        fill="#327D80",
                        width=3
                    )

                canvas.create_oval(
                    x - 4, y - 4,
                    x + 4, y + 4,
                    fill="#327D80",
                    outline=""
                )
                previous = (x, y)

            canvas.create_text(
                x, y - 12,
                text=f"{value:,.{self.decimals}f}",
                fill="#333333"
            )
            canvas.create_text(
                x, bottom + 18,
                text=label,
                fill="#666666"
            )

