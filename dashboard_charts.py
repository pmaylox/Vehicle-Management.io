import tkinter as tk
from tkinter import ttk

class DashboardChart(ttk.Frame):
    def __init__(self, parent, title, kind="bar"):
        super().__init__(parent, padding=12)

        self.kind = kind
        self.points = []

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

    def set_date(self, points):
        self.points = points
        self.draw()

    def draw(self, event=None):
        canvas = self.canvas
        canvas.delete("all")

        width = max(canvas.winfo_width(), 300)
        height = max(canvas.winfo_height(), 200)

        if not  self.points:
            canvas.create_text(
                width /2,
                height / 2,
                text="Notenough recorded data yet",
                fill="#666666",
                font=("Segoe UI", 11)
            )
            return

        left =55
        right = width - 20
        top = 25
        bottom = height - 40

        highest = max(value for label, value in self.points)
        scale_max = highest * 1.15 if highest >0 else 1


        # Horizontal grid lines and value labels.
        for step in range(5):
            fraction = step /4
            y = bottom - fraction * (bottom - top)

            canvas.create_line(
                left, y, right, y,
                fill="#E8E3DE"
            )
            canvas.create_text(
                left - 8, y,
                text=f"{fraction * scale_max:,.1f}",
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
                text=f"{value:,.1f}",
                fill="#333333"
            )
            canvas.create_text(
                x, bottom + 18,
                text=label,
                fill="#666666"
            )

