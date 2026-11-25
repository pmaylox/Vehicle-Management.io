from dashboard_panel import DashboardPanel
from car_history_ui import CarHistoryPanel
from expenses_panel import ExpensesPanel
from mobile_export import build_mobile_backup
from vehicle_profile_ui import VehicleProfileFields
from vin_lookup import profile_summary
from overview_panel import OverviewPanel
from receipt_ui import ReceiptPanel, scrollable_form
from fuel_fields import octane_field, parse_octane, fuel_type_field, parse_fuel_type, is_diesel
import json
from pathlib import Path


from service_fields import service_entry, battery_fields
from datetime import date
from decimal import Decimal, InvalidOperation
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from formatting import format_mileage, format_date, cents_to_dollars
from validation import parse_cost_cents
from Vehicle_Manager import Vehicle
from excel_export import export_vehicle_excel
from storage import save_vehicles, load_vehicles
from battery import battery_summary, battery_term_text
from dashboard_charts import DashboardChart, cost_per_mile_points


# Main function
def main():
    window = tk.Tk()
    window.title("MileSage - by Red Dirt Coding")
    window.geometry("1100x650")
    window.minsize(800, 500)
    # ===== APP COLORS =====
    colors = {
        "background": "#F5F1EB",
        "text": "#292724",
        "accent": "#B65C3A",
        "selected_tab": "#FFFFFF"
    }

    window.configure(background=colors["background"])

    style = ttk.Style(window)
    style.theme_use("clam")
    style.configure(
        "TButton",
        font=("Segoe UI", 10),
        padding=(10, 7),
        background="#F1DDD2",
        foreground="#292724",
        borderwidth=0
    )
    style.map(
        "TButton",
        background=[
            ("pressed", "#B65C3A"),
            ("active", "#DDD5CD")
        ],
        foreground=[
            ("pressed", "#FFFFFF")
        ]
    )

    style.configure(
        "TFrame",
        background=colors["background"]
    )
    style.configure(
        "TLabel",
        background=colors["background"],
        foreground=colors["text"]
    )
    style.configure(
        "TNotebook",
        background=colors["background"],
        borderwidth=0
    )
    style.configure(
        "TNotebook.Tab",
        padding=(14, 8)
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", colors["selected_tab"])],
        foreground=[("selected", colors["accent"])]
    )
    preferences_file = Path(__file__).with_name("preferences.json")
    preferences = {}

    try:
        preferences = json.loads(
            preferences_file.read_text(encoding="utf-8")
        )
        if not isinstance(preferences, dict):
            preferences = {}
    except (OSError, ValueError):
        pass

    saved_sort = preferences.get("sort", "Name")
    if saved_sort not in ("Name", "Year", "Mileage"):
        saved_sort = "Name"

    width = preferences.get("width", 1100)
    height = preferences.get("height", 650)

    if type(width) is int and type(height) is int:
        if width >= 800 and height >= 500:
            window.geometry(f"{width}x{height}")
    try:
        vehicles = load_vehicles()
    except (OSError, ValueError, KeyError, TypeError) as error:
        messagebox.showerror(
            "Could not load vehicles",
            f"{error}\n\nYour saved data has not been changed.",
            parent=window
        )
        window.destroy()
        return
    
        # ===== MAIN LAYOUT =====
    navigation = tk.Frame(
        window,
        background="#292724",
        width=190
    )
    navigation.pack(side="left", fill="y")
    navigation.pack_propagate(False)

    tk.Label(
        navigation,
        text="MileSage",
        font=("Segoe UI", 22, "bold"),
        background="#292724",
        foreground="#FFFFFF"
    ).pack(anchor="w", padx=18, pady=(24, 0))

    tk.Label(
        navigation,
        text="by Red Dirt Coding",
        font=("Segoe UI", 10),
        background="#292724",
        foreground="#F1DDD2"
    ).pack(anchor="w", padx=18, pady=(2, 24))

    container = ttk.Frame(window, padding=12)
    container.pack(side="left", fill="both", expand=True)

    management_visible = False

    # Reserve space for the vehicle controls even when charts request more width.
    sidebar_width = preferences.get("sidebar_width", 300)
    if type(sidebar_width) is not int:
        sidebar_width = 300
    sidebar_width = min(450, max(280, sidebar_width))
    panels = tk.PanedWindow(
        container, orient="horizontal", sashwidth=7,
        borderwidth=0, showhandle=False, opaqueresize=True
    )
    panels.pack(fill="both", expand=True)

    list_panel = ttk.Frame(panels, padding=10)
    details_panel = ttk.Frame(panels, padding=15)

    panels.add(list_panel, minsize=280, width=sidebar_width, stretch="never")
    panels.add(details_panel, minsize=400, stretch="always")

    sidebar_footer = ttk.Frame(list_panel)

    # ===== VEHICLE LIST =====
    ttk.Label(
        list_panel,
        text="Your vehicles",
        font=("Segoe UI", 14, "bold")
    ).pack(anchor="w", pady=(0, 10))

    search_var = tk.StringVar()
    ttk.Label(list_panel, text="Search by name or year:").pack(anchor="w")
    search_row = ttk.Frame(list_panel)
    search_row.pack(fill="x", pady=(4, 8))
    search_entry = ttk.Entry(search_row, textvariable=search_var)
    search_entry.pack(side="left", fill="x", expand=True)
    def focus_search(event=None):
        if not management_visible:
            toggle_management()
        search_entry.focus_set()
        search_entry.selection_range(0, tk.END)
        return "break"

    window.bind("<Control-f>", focus_search)
    search_entry.bind("<Escape>", lambda event: search_var.set(""))   
    ttk.Button(search_row, text="Clear", command=lambda: search_var.set("")).pack(
        side="left", padx=(6, 0))
    sort_var = tk.StringVar(value=saved_sort)
    ttk.Label(list_panel, text="Sort by:").pack(anchor="w")
    ttk.Combobox(
        list_panel,
        textvariable=sort_var,
        values=["Name", "Year", "Mileage"],
        state="readonly"
    ).pack(anchor="w", pady=(4, 8))

    reverse_var = tk.BooleanVar(
        value=preferences.get("reverse") is True
    )
    ttk.Checkbutton(
        list_panel,
        text="Reverse order",
        variable=reverse_var
    ).pack(anchor="w", pady=(0, 8))

    visible_vehicles = []

    vehicle_list = tk.Listbox(
        list_panel,
        font=("Segoe UI", 12),
        height=4,
        exportselection=False,
        background="#FFFFFF",
        foreground="#292724",
        selectbackground="#B65C3A",
        selectforeground="#FFFFFF",
        relief="flat",
        highlightthickness=1,
        highlightbackground="#DDD5CD",
        highlightcolor="#B65C3A",
        activestyle="none"
    )
    vehicle_list.pack(fill="x")
    sidebar_footer.pack(fill="x", pady=(6, 0))
    vehicle_count = tk.StringVar()
    ttk.Label(
        sidebar_footer, textvariable=vehicle_count
    ).pack(anchor="w", pady=(0, 8))
    vehicle_actions = ttk.Frame(sidebar_footer)
    vehicle_actions.pack(fill="x")
    vehicle_actions.columnconfigure(0, weight=1)
    vehicle_actions.columnconfigure(1, weight=1)

    def refresh_vehicle_list(preferred=None):
        selection = vehicle_list.curselection()
        if preferred is None and selection and selection[0] < len(visible_vehicles):
            preferred = visible_vehicles[selection[0]]
        query = search_var.get().strip().casefold()
        visible_vehicles[:] = [
            vehicle for vehicle in vehicles
            if query in f"{vehicle.year} {vehicle.name} {vehicle.mileage}".casefold()
        ]
        if sort_var.get() == "Year":
            visible_vehicles.sort(key=lambda v: (v.year, v.name.casefold()))
        elif sort_var.get() == "Mileage":
            visible_vehicles.sort(key=lambda v: (v.mileage, v.name.casefold()))
        else:
            visible_vehicles.sort(key=lambda v: v.name.casefold())
        if reverse_var.get():
            visible_vehicles.reverse()
        vehicle_count.set(f"Total vehicles: {len(visible_vehicles)}")
        vehicle_list.delete(0, tk.END)
        for vehicle in visible_vehicles:
            vehicle_list.insert(tk.END, f"{vehicle.year} {vehicle.name}")
        if visible_vehicles:
            index = next((i for i, vehicle in enumerate(visible_vehicles)
                          if vehicle is preferred), 0)
            vehicle_list.selection_set(index)
            vehicle_list.see(index)
        show_vehicle()

    # ===== TABS =====
    notebook = ttk.Notebook(details_panel, style="MileSage.TNotebook")
    style.configure("MileSage.TNotebook", background=colors["background"], borderwidth=0)
    style.layout("MileSage.TNotebook.Tab", [])
    notebook.pack(fill="both", expand=True)

    dashboard_tab = ttk.Frame(notebook,padding=15)
    notebook.add(dashboard_tab, text="Dashboard")
    overview_tab = ttk.Frame(notebook, padding=15)
    service_tab = ttk.Frame(notebook, padding=10)
    fuel_tab = ttk.Frame(notebook, padding=10)

    notebook.add(overview_tab, text="Overview")
    notebook.add(service_tab, text="Service History")
    notebook.add(fuel_tab, text="Fuel History")
    graphs_tab = ttk.Frame(notebook, padding=15)
    notebook.add(graphs_tab, text="Graphs")
    expenses_tab = ttk.Frame(notebook, padding=12)
    history_tab = ttk.Frame(notebook, padding=12)
    backup_tab = ttk.Frame(notebook, padding=12)
    notebook.add(expenses_tab, text="Expenses")
    notebook.add(history_tab, text="Car History")
    notebook.add(backup_tab, text="Data & backup")

    def toggle_management():
        nonlocal management_visible
        management_visible = not management_visible
        if management_visible:
            panels.paneconfigure(details_panel, minsize=200)
            panels.add(list_panel, before=details_panel, minsize=280, width=sidebar_width, stretch="never")
            search_entry.focus_set()
        else:
            panels.forget(list_panel)
            panels.paneconfigure(details_panel, minsize=400)

    panels.forget(list_panel)
        # ===== NAVIGATION BUTTONS =====
    navigation_buttons = {}

    def update_navigation(event=None):
        selected_tab = notebook.select()
        if selected_tab == str(overview_tab):
            selected_tab = str(dashboard_tab)

        for tab, button in navigation_buttons.items():
            active = str(tab) == selected_tab
            button.configure(
                background="#B65C3A" if active else "#292724"
            )

    for title, tab in (
        ("Dashboard", dashboard_tab),
        ("Maintenance", service_tab),
        ("Fuel Economy", fuel_tab),
        ("Expenses", expenses_tab),
        ("Car History", history_tab),
        ("Graphs", graphs_tab),
        ("Data & backup", backup_tab),
    ):
        button = tk.Button(
            navigation,
            text=title,
            command=lambda target=tab: notebook.select(target),
            font=("Segoe UI", 11, "bold"),
            anchor="w",
            background="#292724",
            foreground="#FFFFFF",
            activebackground="#B65C3A",
            activeforeground="#FFFFFF",
            relief="flat",
            borderwidth=0,
            padx=14,
            pady=12,
            cursor="hand2"
        )
        button.pack(fill="x", padx=10, pady=4)
        navigation_buttons[tab] = button

    notebook.bind(
        "<<NotebookTabChanged>>",
        update_navigation,
        add="+"
    )
    update_navigation()
    graphs_scroll = ttk.Scrollbar(graphs_tab, orient="vertical")
    graphs_scroll.pack(side="right", fill="y")

    graphs_canvas = tk.Canvas(
        graphs_tab,
        highlightthickness=0,
        yscrollcommand=graphs_scroll.set
    )
    graphs_canvas.pack(side="left", fill="both", expand=True)
    graphs_scroll.configure(command=graphs_canvas.yview)

    graphs_content = ttk.Frame(graphs_canvas)
    graphs_window = graphs_canvas.create_window(
        0, 0,
        window=graphs_content,
        anchor="nw"
    )

    def resize_graphs(event=None):
        graphs_canvas.configure(
            scrollregion=graphs_canvas.bbox("all")
        )

    def fit_graph_width(event):
        graphs_canvas.itemconfigure(
            graphs_window,
            width=event.width
        )

    graphs_content.bind("<Configure>", resize_graphs)
    graphs_canvas.bind("<Configure>", fit_graph_width)

    spending_kind = tk.StringVar(value="Fuel")

    ttk.Combobox(
        graphs_content,
        textvariable=spending_kind,
        values=("Fuel", "Service"),
        state="readonly"
    ).pack(anchor="w", pady=6)

    graph_status = tk.StringVar()
    ttk.Label(
        graphs_content,
        textvariable=graph_status,
        wraplength=600
    ).pack(anchor="w", pady=(0, 6))

    spending_chart = DashboardChart(
        graphs_content,
        "Monthly recorded spending ($)"
    )
    spending_chart.pack(fill="x", pady=(0, 12))

    mpg_chart = DashboardChart(
        graphs_content,
        "Fuel economy (MPG)",
        kind="line"
    )
    mpg_chart.pack(fill="x")

    distance_chart = DashboardChart(
        graphs_content,
        "Miles between recorded fill-ups",
        kind="line"
    )
    distance_chart.pack(fill="x", pady=(12, 0))

    price_chart = DashboardChart(
        graphs_content,
        "Fuel price per US gallon ($)",
        kind="line",
        decimals=3
    )
    price_chart.pack(fill="x", pady=(12, 0))

    cost_chart = DashboardChart(
        graphs_content,
        "Fuel cost per mile ($) â€” full-tank intervals",
        kind="line",
        decimals=3
    )
    cost_chart.pack(fill="x", pady=(12, 0))

    overview_actions = ttk.Frame(overview_tab)
    overview_actions.pack(side="bottom", fill="x", pady=(8, 0))
    overview_actions.columnconfigure((0, 1), weight=1)
    overview = OverviewPanel(overview_tab, colors)
    overview.pack(fill="both", expand=True)

    vehicle_heading = overview.heading
    mileage_heading = overview.mileage
    details_text = overview.details

    # ===== PICTURED VEHICLE DASHBOARD =====
    def select_dashboard_vehicle(vehicle):
        refresh_vehicle_list(preferred=vehicle)
        notebook.select(overview_tab)

    dashboard = DashboardPanel(
        dashboard_tab,
        on_select=select_dashboard_vehicle,
        on_manage=toggle_management,
        actions=[
            ("Update Mileage", lambda: update_mileage()),
            ("Log Service", lambda: record_service()),
            ("Record Fuel", lambda: record_fuel()),
            ("View details", lambda: notebook.select(overview_tab)),
        ]
    )
    dashboard.pack(fill="both", expand=True)

    def refresh_dashboard():
        selection = vehicle_list.curselection()
        selected = visible_vehicles[selection[0]] if selection else None
        dashboard.set_vehicles(visible_vehicles, selected)

    def save_history():
        save_vehicles(vehicles)
        show_vehicle()

    history_panel = CarHistoryPanel(history_tab, save_history)
    expenses_panel = ExpensesPanel(expenses_tab, save_history)

    # ===== SHARED TABLE BUILDER =====
    def make_table(parent, columns):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        table = ttk.Treeview(
            frame,
            columns=[column[0] for column in columns],
            show="headings"
        )

        for key, heading, width in columns:
            table.heading(key, text=heading)
            table.column(key, width=width, minwidth=80)

        vertical = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=table.yview
        )
        horizontal = ttk.Scrollbar(
            frame,
            orient="horizontal",
            command=table.xview
        )

        table.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set
        )

        table.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")

        return table

    # ===== SERVICE TABLE =====
    service_table = make_table(service_tab, [
        ("date", "Date", 110),
        ("mileage", "Mileage", 100),
        ("description", "Service Performed", 260),
        ("cost", "Cost ($)", 110)
    ])

    service_status = tk.StringVar(
        value="Select a vehicle to view service history."
    )

    ttk.Label(
        service_tab,
        textvariable=service_status
    ).pack(anchor="w", pady=(8, 0))

    # ===== FUEL TABLE =====
    fuel_table = make_table(fuel_tab, [
        ("date", "Date", 110),
        ("mileage", "Mileage", 100),
        ("distance", "Distance (miles)", 200),
        ("gallons", "US Gallons", 100),
        ("cost", "Total Cost ($)", 110),
        ("full", "Full Tank", 90),
        ("mpg", "MPG", 170),
        ("price_per_gallon", "Price/Gallon ($)", 130),
        ("octane", "Octane", 90),
        ("fuel_type", "Fuel type / blend", 200)
    ])

    fuel_status = tk.StringVar(
        value="Select a vehicle to view fuel history."
    )

    ttk.Label(
        fuel_tab,
        textvariable=fuel_status
     ).pack(anchor="w", pady=(8, 0))

        # ===== REFRESH SELECTED VEHICLE =====
    def show_vehicle(event=None):
        selection = vehicle_list.curselection()
        refresh_dashboard()

        if not selection:
            history_panel.show(None)
            expenses_panel.show(None)
            overview.set_photo("")
            vehicle_heading.set("No vehicle selected")
            mileage_heading.set("")
            overview.specifications.set("No vehicle selected")
            overview.oil.set("Oil change: â€”")
            overview.tires.set("Tire rotation: â€”")
            overview.battery.set("No vehicle selected")
            overview.pressures.set("No vehicle selected")
            overview.service.set("No vehicle selected")
            overview.fuel.set("No vehicle selected")
            details_text.set(
                "No matching vehicles. Try another search or click Clear."
                if search_var.get().strip() and vehicles
                else "No vehicle selected. Use Add Vehicle to create a vehicle."
            )

            for table in (service_table, fuel_table):
                for item in table.get_children():
                    table.delete(item)

            service_status.set("No vehicle selected")
            fuel_status.set("No vehicle selected")
            spending_chart.set_data([])
            mpg_chart.set_data([])
            distance_chart.set_data([])
            price_chart.set_data([])
            cost_chart.set_data([])
            graph_status.set("Select a vehicle to view its graphs.")
            return

        vehicle = visible_vehicles[selection[0]]
        history_panel.show(vehicle)
        expenses_panel.show(vehicle)
        overview.set_photo(vehicle.photo_path, vehicle.mobile_photo)
        vehicle_heading.set(f"{vehicle.year} {vehicle.name}")
        mileage_heading.set(
            f"Odometer Â· {format_mileage(vehicle.mileage)}"
        )
        overview.specifications.set(profile_summary(vehicle))
        # ===== SPENDING DATA =====
        monthly_cents = {}
        missing_costs = 0

        records = (
            vehicle.fuel_history
            if spending_kind.get() == "Fuel"
            else vehicle.service_history
        )

        for record in records:
            cents = record.get("cost_cents")

            if cents is None:
                missing_costs += 1
                continue

            month = record["date"][:7]
            monthly_cents[month] = monthly_cents.get(month, 0) + cents

        spending_points = [
            (
                date.fromisoformat(month + "-01").strftime("%b %Y"),
                cents / 100
            )
            for month, cents in sorted(monthly_cents.items())[-6:]
        ]

        spending_chart.set_data(spending_points)
        cost_chart.set_data(cost_per_mile_points(vehicle.fuel_history)[-6:])
        graph_status.set(
            f"{vehicle.year} {vehicle.name} â€¢ "
            f"{spending_kind.get()} spending â€¢ "
            f"Latest 6 recorded months â€¢ "
            f"{missing_costs} records with unknown cost excluded"
        )

        mpg_points = []

        # ===== MAINTENANCE STATUS =====
        def maintenance_status(remaining):
            if remaining < 0:
                return f"OVERDUE by {abs(remaining):,} miles"
            if remaining == 0:
                return "DUE NOW"
            return f"{remaining:,} miles remaining"

        oil_remaining = (
            vehicle.next_service() - vehicle.mileage
        )
        oil_status = maintenance_status(oil_remaining)

        if vehicle.last_tire_rotation_mileage is None:
            tire_status = "Last rotation unknown"
        else:
            tire_remaining = (
                vehicle.last_tire_rotation_mileage
                + vehicle.tire_rotation_interval
                - vehicle.mileage
            )
            tire_status = maintenance_status(tire_remaining)

        overview.oil.set(f"Oil change: {oil_status}")
        overview.tires.set(f"Tire rotation: {tire_status}")

        # ===== SERVICE SPENDING =====
        service_cents = 0
        unknown_costs = 0

        for record in vehicle.service_history:
            cents = record.get("cost_cents")

            if cents is None:
                unknown_costs += 1
            else:
                service_cents += cents

        service_total = Decimal(service_cents) / 100

        # ===== FUEL SPENDING =====
        fuel_cents = 0
        total_gallons = Decimal("0")

        for record in vehicle.fuel_history:
            fuel_cents += record["cost_cents"]
            total_gallons += Decimal(record["gallons"])

        fuel_total = Decimal(fuel_cents) / 100

        if total_gallons > 0:
            average_price = fuel_total / total_gallons
            average_text = f"${average_price:.3f}"
        else:
            average_text = "Not available"
        def pressure_text(position):
            pressure = vehicle.tire_pressures[position]

            if pressure is None:
                return "Not recorded"
            return f"{pressure:g} PSI"

              # ===== DASHBOARD CARDS =====
        overview.battery.set(battery_summary(vehicle))
        overview.pressures.set(
            f"Driver's front: {pressure_text('driver_front')}\n"
            f"Driver's rear: {pressure_text('driver_rear')}\n"
            f"Passenger front: {pressure_text('passenger_front')}\n"
            f"Passenger rear: {pressure_text('passenger_rear')}"
        )

        overview.service.set(
            f"Records: {len(vehicle.service_history)}\n"
            f"Recorded spending: ${service_total:,.2f}\n"
            f"Records without a cost: {unknown_costs}\n"
            "Missing costs are excluded from spending."
        )
        overview.fuel.set(
            f"Fill-ups: {len(vehicle.fuel_history)}\n"
            f"Total fuel: {total_gallons:,.3f} US gallons\n"
            f"Total spending: ${fuel_total:,.2f}\n"
            f"Average price per gallon: {average_text}"
        )
        details_text.set("")

        # ===== REFRESH HISTORY TABLES =====
        for table in (service_table, fuel_table):
            for item in table.get_children():
                table.delete(item)

        for record in vehicle.service_history:
            service_table.insert("", tk.END, values=(
                format_date(record["date"]),
                f"{record['mileage']:,}",
                record["description"],
                vehicle.format_service_cost(record)
            ))

        previous_full_mileage = None
        gallons_since_full = Decimal("0")
        previous_fill_mileage = None
        distance_points = []
        price_points = []

        for record in vehicle.fuel_history:
            current_mileage = record["mileage"]

            if current_mileage is None:
                distance_text = "Mileage not recorded"
            elif previous_fill_mileage is None:
                distance_text = "No previous mileage"
            elif current_mileage < previous_fill_mileage:
                distance_text = "Check odometer order"
            else:
                distance = current_mileage - previous_fill_mileage
                distance_text = f"{distance:,} miles"
                distance_points.append((
                    date.fromisoformat(record["date"]).strftime("%m/%d/%y"),
                    distance
                ))

            previous_fill_mileage = current_mileage
            gallons = Decimal(record["gallons"])
            full_tank = record["full_tank"]

            if current_mileage is None:
                previous_full_mileage = None
                gallons_since_full = Decimal("0")
                mpg_text = "Mileage not recorded"
            elif previous_full_mileage is None:
                if full_tank:
                    previous_full_mileage = current_mileage
                    gallons_since_full = Decimal("0")
                    mpg_text = "Starting full tank"
                else:
                    mpg_text = "Need starting full tank"
            else:
                gallons_since_full += gallons
                if full_tank:
                    miles = current_mileage - previous_full_mileage
                    if miles > 0 and gallons_since_full > 0:
                        mpg = Decimal(miles) / gallons_since_full
                        mpg_text = f"{mpg:.2f}"
                        mpg_points.append((
                            date.fromisoformat(record["date"]).strftime("%m/%d/%y"),
                            float(mpg)
                        ))
                    else:
                        mpg_text = "Insufficient distance"
                    previous_full_mileage = current_mileage
                    gallons_since_full = Decimal("0")
                else:
                    mpg_text = "Waiting for full tank"

            price_points.append((
                date.fromisoformat(record["date"]).strftime("%m/%d/%y"),
                float(Decimal(record["cost_cents"]) / 100 / gallons)
            ))

            fuel_table.insert("", tk.END, values=(
                format_date(record["date"]),
                format_mileage(record["mileage"]),
                distance_text,
                record["gallons"],
                vehicle.format_service_cost(record),
                "Yes" if full_tank else "No",
                mpg_text,
                f"{Decimal(record['cost_cents']) / 100 / gallons:.3f}",
                "N/A (diesel)" if is_diesel(record.get("fuel_type") or "") else record.get("octane") if record.get("octane") is not None else "Not recorded",
                record.get("fuel_type") or "Not recorded"
            ))

        mpg_chart.set_data(mpg_points[-6:])
        distance_chart.set_data(distance_points[-6:])
        price_chart.set_data(price_points[-6:])
        cost_chart.set_data(
            cost_per_mile_points(vehicle.fuel_history)[-6:]
        )

        service_status.set(
            f"{len(vehicle.service_history)} service records"
        )
        fuel_status.set(
            f"Fill-ups: {len(vehicle.fuel_history)}\n"
            f"Total fuel: {total_gallons:,.3f} US gallons\n"
            f"Total spending: ${fuel_total:,.2f}\n"
            f"Average price per gallon: {average_text}"
        )

    # ===== UPDATE MILEAGE =====
    def update_mileage():
        selection = vehicle_list.curselection()

        if not selection:
            messagebox.showinfo(
                "Select a vehicle",
                "Choose a vehicle first.",
                parent=window
            )
            return

        vehicle = visible_vehicles[selection[0]]

        miles = simpledialog.askinteger(
            "Update mileage",
            f"{vehicle.year} {vehicle.name}\n"
            f"Current odometer: {vehicle.mileage:,} miles\n\n"
            "Enter miles to add or subtract.\n"
            "Examples: +250 or -250",
            minvalue=-vehicle.mileage,
            parent=window
        )

        if miles is None or miles == 0:
            return

        old_mileage = vehicle.mileage
        new_mileage = old_mileage + miles

        confirmed = messagebox.askyesno(
            "Confirm mileage",
            f"Adjust {vehicle.name} by {miles:+,} miles?\n\n"
            f"Current odometer: {old_mileage:,}\n"
            f"New odometer: {new_mileage:,}",
            parent=window
        )

        if not confirmed:
            return

        vehicle.mileage = new_mileage

        try:
            save_vehicles(vehicles)
        except (OSError, TypeError, ValueError) as error:
            vehicle.mileage = old_mileage
            messagebox.showerror(
                "Could not save",
                f"Mileage update was canceled.\n\n{error}",
                parent=window
            )
            return

        refresh_vehicle_list(preferred=vehicle)
        messagebox.showinfo(
            "Mileage updated",
            f"{vehicle.name} now has {vehicle.mileage:,} miles.",
            parent=window
        )

    ttk.Button(
        overview_actions,
        text="Update Mileage",
        command=update_mileage
    ).grid(row=0, column=0, sticky="ew", padx=4, pady=4)


    def update_tire_pressure():
        selection = vehicle_list.curselection()
        if not selection:
            messagebox.showinfo("Select a vehicle", "Choose a vehicle first.", parent=window)
            return
        vehicle = visible_vehicles[selection[0]]
        dialog = tk.Toplevel(window)
        dialog.title("Tire Pressure â€” Starting PSI and Air Added")
        dialog.resizable(False, False)
        dialog.transient(window)
        form = ttk.Frame(dialog, padding=20)
        form.pack(fill="both", expand=True)
        positions = [
            ("driver_front", "Driver's front"),
            ("driver_rear", "Driver's rear"),
            ("passenger_front", "Passenger front"),
            ("passenger_rear", "Passenger rear")
        ]
        for column, title in enumerate(("Tire", "Starting PSI", "Add PSI", "Current PSI")):
            ttk.Label(form, text=title).grid(row=0, column=column, padx=8, pady=6, sticky="w")
        starting_vars, added_vars = {}, {}
        for row, (key, label) in enumerate(positions, start=1):
            baseline = vehicle.starting_tire_pressures[key]
            current = vehicle.tire_pressures[key]
            starting_vars[key] = tk.StringVar(value="" if baseline is None else f"{baseline:g}")
            added_vars[key] = tk.StringVar(value="0")
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=6)
            ttk.Entry(form, textvariable=starting_vars[key], width=12).grid(row=row, column=1, padx=8)
            ttk.Entry(form, textvariable=added_vars[key], width=12).grid(row=row, column=2, padx=8)
            ttk.Label(form, text="Not recorded" if current is None else f"{current:g}").grid(row=row, column=3, padx=8, sticky="w")
        ttk.Label(form, text="Add PSI is the increase, not the final gauge reading. 0 adds no air.\n"
                  "Changing Starting PSI resets that tire's calculated pressure.\n"
                  "Blank starting fields keep existing values. Verify with a tire gauge.").grid(
                      row=5, column=0, columnspan=4, sticky="w", pady=12)

        reset_starting = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="Use starting PSI as fresh measured readings", variable=reset_starting).grid(
            row=6, column=0, columnspan=4, sticky="w")

        def save_pressures():
            old_current = vehicle.tire_pressures.copy()
            old_starting = vehicle.starting_tire_pressures.copy()
            old_history = list(vehicle.tire_pressure_history)
            try:
                changed = vehicle.record_tire_pressure(
                    {key: var.get().strip() for key, var in starting_vars.items()},
                    {key: var.get().strip() for key, var in added_vars.items()},
                    reset_starting=reset_starting.get()
                )
            except ValueError as error:
                messagebox.showerror("Invalid pressure", str(error), parent=dialog)
                return
            if changed:
                try:
                    save_vehicles(vehicles)
                except (OSError, TypeError, ValueError) as error:
                    vehicle.tire_pressures = old_current
                    vehicle.starting_tire_pressures = old_starting
                    vehicle.tire_pressure_history = old_history
                    messagebox.showerror("Could not save", f"Update canceled.\n\n{error}", parent=dialog)
                    return
            show_vehicle()
            dialog.destroy()

        ttk.Label(form, text="Pressure history (newest first)").grid(row=7, column=0, columnspan=4, sticky="w", pady=(8, 4))
        history_frame = ttk.Frame(form)
        history_frame.grid(row=8, column=0, columnspan=4, sticky="ew")
        history = ttk.Treeview(history_frame, columns=("date", "tire", "before", "added", "after"), show="headings", height=5)
        for key, label, width in (("date", "Recorded", 155), ("tire", "Tire", 125), ("before", "Previous PSI", 90), ("added", "Added PSI", 75), ("after", "Current PSI", 90)):
            history.heading(key, text=label)
            history.column(key, width=width, stretch=False)
        history.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=history.yview)
        scrollbar.pack(side="right", fill="y")
        history.configure(yscrollcommand=scrollbar.set)
        def display(value):
            return "Unknown" if value is None else f"{value:g}"
        for event in reversed(vehicle.tire_pressure_history):
            for key, label in positions:
                before = event["before"][key]
                after = event["current"][key]
                added = event["added_psi"][key]
                if before != after or added:
                    history.insert("", "end", values=(event["recorded_at"][:19].replace("T", " "), label, display(before), display(added), display(after)))
        buttons = ttk.Frame(form)
        buttons.grid(row=9, column=0, columnspan=4, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Save Pressures", command=save_pressures).pack(side="left")

    ttk.Button(
        overview_actions,
        text="Update Tire Pressure",
        command=update_tire_pressure
    ).grid(row=0, column=1, sticky="ew", padx=4, pady=4)

    # ===== ADD VEHICLE =====
       
    def add_vehicle():
        dialog = tk.Toplevel(window)
        dialog.title("Add Vehicle")
        dialog.resizable(False, False)
        dialog.transient(window)

        form = scrollable_form(dialog)

        name_var = tk.StringVar()
        year_var = tk.StringVar()
        mileage_var = tk.StringVar()
        photo_var = tk.StringVar()

        def choose_vehicle_photo():
            filename = filedialog.askopenfilename(
                parent=dialog,
                title="Choose Vehicle Photo",
                filetypes=[("Vehicle photos", "*.jpg *.jpeg *.png"), ("All files", "*.*")]
            )
            if filename:
                photo_var.set(filename)

        fields = [
            ("Vehicle name:", name_var),
            ("Model year:", year_var),
            ("Starting odometer:", mileage_var)
        ]

        name_entry = None

        for row, (label, variable) in enumerate(fields):
            ttk.Label(
                form, text=label
            ).grid(row=row, column=0, sticky="w", pady=6)

            entry = ttk.Entry(
                form, textvariable=variable, width=30
            )
            entry.grid(
                row=row, column=1, padx=(12, 0), pady=6
            )

            if row == 0:
                name_entry = entry

        photo_row = ttk.Frame(form)
        photo_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(photo_row, text="Choose Vehicle Photo", command=choose_vehicle_photo).pack(anchor="w")
        ttk.Label(photo_row, textvariable=photo_var, wraplength=500).pack(anchor="w", pady=(4, 0))

        profile_fields = VehicleProfileFields(form, 4, name_var, year_var)

        def save_new_vehicle():
            name = name_var.get().strip()

            if not name:
                messagebox.showerror(
                    "Invalid name",
                    "Enter a vehicle name.",
                    parent=dialog
                )
                return

            try:
                year = int(year_var.get().strip())
                mileage = int(mileage_var.get().strip())

                if year <= 0 or mileage < 0:
                    raise ValueError

            except ValueError:
                messagebox.showerror(
                    "Invalid details",
                    "Year must be a positive whole number.\n"
                    "Mileage must be a non-negative whole number.",
                    parent=dialog
                )
                return

            try:
                profile = profile_fields.get_value()
            except ValueError as error:
                messagebox.showerror("Invalid vehicle details", str(error), parent=dialog)
                return
            if profile.get("vin") and any(
                other.profile.get("vin", "").upper() == profile["vin"] for other in vehicles
            ):
                messagebox.showerror("VIN already saved", "Another vehicle already uses that VIN. Edit that vehicle instead.", parent=dialog)
                return

            confirmed = messagebox.askyesno(
                "Confirm new vehicle",
                f"Add {year} {name}?\n\n"
                f"Starting odometer: {mileage:,} miles",
                parent=dialog
            )

            if not confirmed:
                return

            new_vehicle = Vehicle(name, year, mileage)
            new_vehicle.profile = profile
            new_vehicle.photo_path = photo_var.get()
            vehicles.append(new_vehicle)

            try:
                save_vehicles(vehicles)
            except (OSError, TypeError, ValueError) as error:
                vehicles.pop()

                messagebox.showerror(
                    "Could not save",
                    f"Vehicle was not added.\n\n{error}",
                    parent=dialog
                )
                return

            search_var.set("")
            refresh_vehicle_list(new_vehicle)

            dialog.destroy()

            messagebox.showinfo(
                "Vehicle added",
                f"{year} {name} was added and saved.",
                parent=window
            )

        buttons = ttk.Frame(form)
        buttons.grid(
            row=5, column=0, columnspan=2,
            sticky="e", pady=(15, 0)
        )

        ttk.Button(
            buttons,
            text="Cancel",
            command=dialog.destroy
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            buttons,
            text="Save Vehicle",
            command=save_new_vehicle
        ).pack(side="left")

        dialog.bind("<Escape>", lambda event: dialog.destroy())
        dialog.wait_visibility()
        dialog.grab_set()
        name_entry.focus_set()

    ttk.Button(
        vehicle_actions,
        text="Add Vehicle",
        command=add_vehicle
    ).grid(row=0, column=0, sticky="ew", padx=(0, 4))

        # ===== EDIT VEHICLE =====
    def edit_vehicle():
        selection = vehicle_list.curselection()

        if not selection:
            messagebox.showinfo(
                "Select a vehicle",
                "Choose a vehicle first.",
                parent=window
            )
            return

        vehicle = visible_vehicles[selection[0]]
        index = vehicles.index(vehicle)

        dialog = tk.Toplevel(window)
        dialog.title("Edit Vehicle")
        dialog.resizable(False, False)
        dialog.transient(window)

        form = scrollable_form(dialog)

        name_var = tk.StringVar(value=vehicle.name)
        year_var = tk.StringVar(value=str(vehicle.year))
        mileage_var = tk.StringVar(value=str(vehicle.mileage))
        photo_var = tk.StringVar(value=vehicle.photo_path)

        def choose_vehicle_photo():
            filename = filedialog.askopenfilename(
                parent=dialog,
                title="Choose vehicle photo",
                filetypes=[
                    ("Vehicle photos", "*.jpg *.jpeg *.png"),
                    ("All files", "*.*")
                ]
            )
            if filename:
                photo_var.set(filename)
        fields = [
            ("Vehicle name:", name_var),
            ("Model year:", year_var),
            ("Current odometer:", mileage_var)
        ]

        for row, (label, variable) in enumerate(fields):
            ttk.Label(
                form, text=label
            ).grid(row=row, column=0, sticky="w", pady=6)

            ttk.Entry(
                form, textvariable=variable, width=30
            ).grid(
                row=row, column=1, padx=(12, 0), pady=6
            )

        photo_row = ttk.Frame(form)
        photo_row.grid(
            row=3, column=0, columnspan=2,
            sticky="ew", pady=(10, 0)
        )

        ttk.Button(
            photo_row,
            text="Choose Vehicle Photo",
            command=choose_vehicle_photo
        ).pack(anchor="w")

        ttk.Label(
            photo_row,
            textvariable=photo_var,
            wraplength=500
        ).pack(anchor="w", pady=(4, 0))

        profile_fields = VehicleProfileFields(form, 4, name_var, year_var, vehicle.profile)

        def save_changes():
            name = name_var.get().strip()

            if not name:
                messagebox.showerror(
                    "Invalid name",
                    "Enter a vehicle name.",
                    parent=dialog
                )
                return

            try:
                year = int(year_var.get().strip())
                mileage = int(mileage_var.get().strip())

            except ValueError:
                messagebox.showerror(
                    "Invalid details",
                    "Year and mileage must be whole numbers.",
                    parent=dialog
                )
                return

            if year <= 0:
                messagebox.showerror(
                    "Invalid year",
                    "Year must be positive.",
                    parent=dialog
                )
                return

            if mileage < 0:
                messagebox.showerror(
                    "Invalid mileage",
                    "Odometer cannot be below zero.",
                    parent=dialog
                )
                return

            try:
                profile = profile_fields.get_value()
            except ValueError as error:
                messagebox.showerror("Invalid vehicle details", str(error), parent=dialog)
                return
            if profile.get("vin") and any(
                other is not vehicle and other.profile.get("vin", "").upper() == profile["vin"] for other in vehicles
            ):
                messagebox.showerror("VIN already saved", "Another vehicle already uses that VIN. Edit that vehicle instead.", parent=dialog)
                return

            old_values = (
                vehicle.name,
                vehicle.year,
                vehicle.mileage
            )

            old_profile = vehicle.profile.copy()
            old_photo = vehicle.photo_path
            if (
                (name, year, mileage) == old_values
                and profile == old_profile
                and photo_var.get() == old_photo
            ):
                messagebox.showinfo(
                    "No changes",
                    "The vehicle details are unchanged.",
                    parent=dialog
                )
                return

            confirmed = messagebox.askyesno(
                "Confirm changes",
                f"Save {year} {name}?\n\n"
                f"Odometer: {mileage:,} miles",
                parent=dialog
            )

            if not confirmed:
                return

            vehicle.profile = profile
            vehicle.photo_path = photo_var.get()
            vehicle.name = name
            vehicle.year = year
            vehicle.mileage = mileage

            try:
                save_vehicles(vehicles)

            except (OSError, TypeError, ValueError) as error:
                vehicle.profile = old_profile
                vehicle.photo_path = old_photo
                (
                    vehicle.name,
                    vehicle.year,
                    vehicle.mileage
                ) = old_values

                messagebox.showerror(
                    "Could not save",
                    f"Changes were canceled.\n\n{error}",
                    parent=dialog
                )
                return

            refresh_vehicle_list(vehicle)

            dialog.destroy()

            messagebox.showinfo(
                "Vehicle updated",
                "Changes were saved.",
                parent=window
            )

        buttons = ttk.Frame(form)
        buttons.grid(
            row=5, column=0, columnspan=2,
            sticky="e", pady=(15, 0)
        )

        ttk.Button(
            buttons,
            text="Cancel",
            command=dialog.destroy
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            buttons,
            text="Save Changes",
            command=save_changes
        ).pack(side="left")

        dialog.bind("<Escape>", lambda event: dialog.destroy())
        dialog.wait_visibility()
        dialog.grab_set()

    ttk.Button(
        vehicle_actions,
        text="Edit Vehicle",
        command=edit_vehicle
    ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # ===== REMOVE VEHICLE =====
    def remove_vehicle():
        selection = vehicle_list.curselection()

        if not selection:
            messagebox.showinfo(
                "Select a vehicle",
                "Choose a vehicle first.",
                parent=window
            )
            return

        vehicle = visible_vehicles[selection[0]]
        index = vehicles.index(vehicle)

        confirmed = messagebox.askyesno(
            "Remove vehicle",
            f"Remove {vehicle.year} {vehicle.name}?\n\n"
            f"This also removes its "
            f"{len(vehicle.service_history)} service records and "
            f"{len(vehicle.fuel_history)} fuel records.\n\n"
            "Continue?",
            parent=window,
            default=messagebox.NO
        )

        if not confirmed:
            return

        vehicles.pop(index)

        try:
            save_vehicles(vehicles)

        except (OSError, TypeError, ValueError) as error:
            vehicles.insert(index, vehicle)

            messagebox.showerror(
                "Could not save",
                f"The vehicle was not removed.\n\n{error}",
                parent=window
            )
            return

        refresh_vehicle_list()

        messagebox.showinfo(
            "Vehicle removed",
            f"{vehicle.year} {vehicle.name} was removed and saved.",
            parent=window
        )

    ttk.Button(
        vehicle_actions,
        text="Remove Vehicle",
        command=remove_vehicle
    ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        # ===== RECORD SERVICE =====
   
    def record_service():
        selection = vehicle_list.curselection()

        if not selection:
            messagebox.showinfo(
                "Select a vehicle",
                "Choose a vehicle first.",
                parent=window
            )
            return

        vehicle = visible_vehicles[selection[0]]

        dialog = tk.Toplevel(window)
        dialog.title("Record Service")
        dialog.resizable(False, False)
        dialog.transient(window)

        form = scrollable_form(dialog)

        date_var = tk.StringVar(value=date.today().isoformat())
        service_mileage_var = tk.StringVar(value=str(vehicle.mileage))
        description_var = tk.StringVar()
        cost_var = tk.StringVar()
        oil_var = tk.BooleanVar(value=False)
        tire_var = tk.BooleanVar(value=False)

        ttk.Label(
            form,
            text=f"{vehicle.year} {vehicle.name}",
            font=("Segoe UI", 13, "bold")
        ).grid(
            row=0, column=0, columnspan=2,
            sticky="w", pady=(0, 8)
        )

        ttk.Label(form, text="Service odometer mileage:").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=service_mileage_var, width=20).grid(
            row=1, column=1, sticky="w", padx=(12, 0), pady=6)

        ttk.Label(
            form, text="Service performed:"
        ).grid(row=2, column=0, sticky="w", pady=6)

        description_entry = service_entry(form, description_var, vehicle.service_history)
        description_entry.grid(
            row=2, column=1, padx=(12, 0), pady=6
        )

        ttk.Label(
            form, text="Total cost ($):"
        ).grid(row=3, column=0, sticky="w", pady=6)

        ttk.Entry(
            form, textvariable=cost_var, width=20
        ).grid(
            row=3, column=1, sticky="w",
            padx=(12, 0), pady=6
        )

        ttk.Label(
            form, text="Leave cost blank if unknown."
        ).grid(
            row=4, column=1, sticky="w", padx=(12, 0)
        )

        ttk.Checkbutton(
            form,
            text="Reset oil change countdown",
            variable=oil_var
        ).grid(
            row=5, column=0, columnspan=2,
            sticky="w", pady=(15, 4)
        )

        ttk.Checkbutton(
            form,
            text="Reset tire rotation countdown",
            variable=tire_var
        ).grid(
            row=6, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(
            form, text="Service date (YYYY-MM-DD):"
        ).grid(
            row=7, column=0, sticky="w", pady=(12, 6)
        )

        ttk.Entry(
            form, textvariable=date_var, width=20
        ).grid(
            row=7, column=1, sticky="w",
            padx=(12, 0), pady=(12, 6)
        )

        get_battery = battery_fields(form, 8, description_var, lambda: date_var.get().strip())

        receipt = ReceiptPanel(form, 9, "service", {"date": date_var, "mileage": service_mileage_var, "description": description_var, "cost": cost_var})

        def save_service():
            try:
                service_date = date.fromisoformat(
                    date_var.get().strip()
                )
            except ValueError:
                messagebox.showerror(
                    "Invalid date",
                    "Enter a valid service date as YYYY-MM-DD.",
                    parent=dialog
                )
                return

            if service_date > date.today():
                messagebox.showerror(
                    "Invalid date",
                    "Service date cannot be in the future.",
                    parent=dialog
                )
                return
            
            try:
                service_mileage = int(service_mileage_var.get().strip())
                if not vehicle.starting_mileage <= service_mileage <= vehicle.mileage:
                    raise ValueError(f"Service mileage must be between {vehicle.starting_mileage:,} and {vehicle.mileage:,}. Update the vehicle mileage first if needed.")
                if oil_var.get() and service_mileage < vehicle.last_service_mileage:
                    raise ValueError("An older service cannot reset a newer oil change countdown.")
                if tire_var.get() and service_mileage < (vehicle.last_tire_rotation_mileage or 0):
                    raise ValueError("An older service cannot reset a newer tire rotation countdown.")
            except ValueError as error:
                messagebox.showerror("Invalid service mileage", str(error), parent=dialog)
                return

            description = description_var.get().strip()
            cost_input = cost_var.get().strip()

            if not description:
                messagebox.showerror(
                    "Missing description",
                    "Enter the service performed.",
                    parent=dialog
                )
                return

            cost_cents = None
            
            if cost_input:
                try:
                    cost_cents = parse_cost_cents(cost_input)
                except (InvalidOperation, ValueError):
                    messagebox.showerror(
                        "Invalid cost",
                        "Enter a non-negative cost with no more "
                        "than two decimal places.\n"
                        "Do not include dollar signs or commas.",
                        parent=dialog
                    )
                    return
            
            record = {
                "date": service_date.isoformat(),
                "mileage": service_mileage,
                "description": description,
                "cost_cents": cost_cents,
                "oil_reset": oil_var.get(),
                "tire_reset": tire_var.get()
            }

            try:
                battery = get_battery()
            except ValueError as error:
                messagebox.showerror("Invalid battery details", str(error), parent=dialog)
                return
            if battery:
                record["battery"] = battery

            cost_text = vehicle.format_service_cost(record)

            confirmed = messagebox.askyesno(
                "Confirm service",
                f"{vehicle.year} {vehicle.name}\n"
                f"Service date: {service_date:%m/%d/%Y}\n"
                f"Mileage: {service_mileage:,}\n"
                f"Service: {description}\n"
                f"Cost ($): {cost_text}\n"
                + (f"Battery installed: {battery['installed']} â€” {battery_term_text(battery['months'])} ({battery['term']})\n" if battery else "")
                + f"\nReset oil: {'Yes' if oil_var.get() else 'No'}\n"
                f"Reset tires: {'Yes' if tire_var.get() else 'No'}\n\n"
                "Save this service?",
                parent=dialog
            )

            if not confirmed:
                return

            old_oil_mileage = vehicle.last_service_mileage
            old_tire_mileage = vehicle.last_tire_rotation_mileage

            vehicle.service_history.append(record)

            if record["oil_reset"]:
                vehicle.last_service_mileage = service_mileage

            if record["tire_reset"]:
                vehicle.last_tire_rotation_mileage = service_mileage

            try:
                receipt.commit(record)
                save_vehicles(vehicles)

            except (OSError, TypeError, ValueError) as error:
                receipt.rollback()
                vehicle.service_history.pop()
                vehicle.last_service_mileage = old_oil_mileage
                vehicle.last_tire_rotation_mileage = old_tire_mileage

                messagebox.showerror(
                    "Could not save",
                    f"Service was not recorded.\n\n{error}",
                    parent=dialog
                )
                return

            show_vehicle()
            notebook.select(service_tab)
            dialog.destroy()

            messagebox.showinfo(
                "Service recorded",
                "The service record was saved.",
                parent=window
            )

        buttons = ttk.Frame(form)
        buttons.grid(
            row=10, column=0, columnspan=2,
            sticky="e", pady=(20, 0)
        )

        ttk.Button(
            buttons,
            text="Cancel",
            command=dialog.destroy
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            buttons,
            text="Save Service",
            command=save_service
        ).pack(side="left")

        dialog.bind("<Escape>", lambda event: dialog.destroy())
        dialog.wait_visibility()
        dialog.grab_set()
        description_entry.focus_set()

    ttk.Button(
        service_tab,
        text="Record Service",
        command=record_service
    ).pack(anchor="w", pady=(10, 0))

        # ===== EDIT SERVICE =====
    def edit_service():
        vehicle_selection = vehicle_list.curselection()
        record_selection = service_table.selection()

        if not vehicle_selection or not record_selection:
            messagebox.showinfo(
                "Select a service record",
                "Choose a vehicle, then select a service record.",
                parent=window
            )
            return

        vehicle = visible_vehicles[vehicle_selection[0]]
        index = service_table.index(record_selection[0])
        record = vehicle.service_history[index]

        dialog = tk.Toplevel(window)
        dialog.title("Edit Service")
        dialog.resizable(False, False)
        dialog.transient(window)

        form = scrollable_form(dialog)

        description_var = tk.StringVar(
            value=record["description"]
        )

        current_cents = record.get("cost_cents")
        cost_var = tk.StringVar(
            value=(
                f"{Decimal(current_cents) / 100:.2f}"
                if current_cents is not None
                else ""
            )
        )

        ttk.Label(
            form,
            text=f"{vehicle.year} {vehicle.name}",
            font=("Segoe UI", 13, "bold")
        ).grid(
            row=0, column=0, columnspan=2,
            sticky="w", pady=(0, 8)
        )

        ttk.Label(
            form,
            text=(
                f"Service date: {date.fromisoformat(record['date']):%m/%d/%Y}\n"
                f"{record['mileage']:,} miles"
            )
        ).grid(
            row=1, column=0, columnspan=2,
            sticky="w", pady=(0, 12)
        )

        ttk.Label(
            form, text="Service performed:"
        ).grid(row=2, column=0, sticky="w", pady=6)

        description_entry = service_entry(form, description_var, vehicle.service_history)
        description_entry.grid(
            row=2, column=1, padx=(12, 0), pady=6
        )

        ttk.Label(
            form, text="Total cost ($):"
        ).grid(row=3, column=0, sticky="w", pady=6)

        ttk.Entry(
            form, textvariable=cost_var, width=20
        ).grid(
            row=3, column=1, sticky="w",
            padx=(12, 0), pady=6
        )

        ttk.Label(
            form,
            text="A blank cost means cost not recorded."
        ).grid(
            row=4, column=0, columnspan=2,
            sticky="w", pady=(4, 0)
        )

        get_battery = battery_fields(form, 5, description_var, lambda: record["date"], record.get("battery"))

        receipt = ReceiptPanel(form, 6, "service", {"description": description_var, "cost": cost_var}, record.get("receipt_photo"))

        def save_service_changes():
            description = description_var.get().strip()
            cost_input = cost_var.get().strip()

            if not description:
                messagebox.showerror(
                    "Missing description",
                    "Enter the service performed.",
                    parent=dialog
                )
                return

            cost_cents = None

            if cost_input:
                try:
                    cost_cents = parse_cost_cents(cost_input)
                except (InvalidOperation, ValueError):
                    messagebox.showerror(
                        "Invalid cost",
                        "Enter a non-negative cost with no more "
                        "than two decimal places.\n"
                        "Do not include dollar signs or commas.",
                        parent=dialog
                    )
                    return

            try:
                battery = get_battery()
            except ValueError as error:
                messagebox.showerror("Invalid battery details", str(error), parent=dialog)
                return

            if (
                not receipt.source
                and description == record["description"]
                and cost_cents == current_cents
                and battery == record.get("battery")
            ):
                messagebox.showinfo(
                    "No changes",
                    "The service record is unchanged.",
                    parent=dialog
                )
                return

            updated_record = record.copy()
            updated_record["description"] = description
            updated_record["cost_cents"] = cost_cents
            updated_record.pop("battery", None)
            if battery:
                updated_record["battery"] = battery

            cost_text = vehicle.format_service_cost(
                updated_record
            )

            confirmed = messagebox.askyesno(
                "Confirm service changes",
                f"Service: {description}\n"
                f"Cost ($): {cost_text}\n"
                + (f"Battery installed: {battery['installed']} â€” {battery_term_text(battery['months'])} ({battery['term']})\n" if battery else "")
                + "\nSave these changes?",
                parent=dialog
            )

            if not confirmed:
                return

            vehicle.service_history[index] = updated_record

            try:
                receipt.commit(updated_record)
                save_vehicles(vehicles)

            except (OSError, TypeError, ValueError) as error:
                receipt.rollback()
                vehicle.service_history[index] = record

                messagebox.showerror(
                    "Could not save",
                    f"Changes were canceled.\n\n{error}",
                    parent=dialog
                )
                return

            show_vehicle()

            # Restore selection after refreshing the table.
            items = service_table.get_children()
            service_table.selection_set(items[index])
            service_table.see(items[index])

            dialog.destroy()

            messagebox.showinfo(
                "Service updated",
                "Changes were saved.",
                parent=window
            )

        buttons = ttk.Frame(form)
        buttons.grid(
            row=7, column=0, columnspan=2,
            sticky="e", pady=(20, 0)
        )

        ttk.Button(
            buttons,
            text="Cancel",
            command=dialog.destroy
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            buttons,
            text="Save Changes",
            command=save_service_changes
        ).pack(side="left")

        dialog.bind("<Escape>", lambda event: dialog.destroy())
        dialog.wait_visibility()
        dialog.grab_set()
        description_entry.focus_set()

    ttk.Button(
        service_tab,
        text="Edit Service",
        command=edit_service
    ).pack(anchor="w", pady=(8, 0))

        # ===== DELETE SERVICE =====
    def delete_service():
        vehicle_selection = vehicle_list.curselection()
        record_selection = service_table.selection()

        if not vehicle_selection or not record_selection:
            messagebox.showinfo(
                "Select a service record",
                "Choose a vehicle, then select a service record.",
                parent=window
            )
            return

        vehicle = visible_vehicles[vehicle_selection[0]]
        index = service_table.index(record_selection[0])
        record = vehicle.service_history[index]

        confirmed = messagebox.askyesno(
            "Delete service record",
            f"{vehicle.year} {vehicle.name}\n\n"
            f"Delete service date: {date.fromisoformat(record['date']):%m/%d/%Y}\n"
            f"Mileage: {record['mileage']:,}\n"
            f"Service: {record['description']}\n"
            f"Cost ($): {vehicle.format_service_cost(record)}\n\n"
            "Maintenance countdowns will remain unchanged.\n\n"
            "Delete this record?",
            parent=window,
            default=messagebox.NO
        )

        if not confirmed:
            return

        vehicle.service_history.pop(index)

        try:
            save_vehicles(vehicles)

        except (OSError, TypeError, ValueError) as error:
            vehicle.service_history.insert(index, record)

            messagebox.showerror(
                "Could not save",
                f"The record was not deleted.\n\n{error}",
                parent=window
            )
            return

        show_vehicle()

        items = service_table.get_children()

        if items:
            next_index = min(index, len(items) - 1)
            service_table.selection_set(items[next_index])
            service_table.see(items[next_index])

        messagebox.showinfo(
            "Service deleted",
            "The service record was deleted and saved.",
            parent=window
        )

    ttk.Button(
        service_tab,
        text="Delete Service",
        command=delete_service
    ).pack(anchor="w", pady=(8, 0))

        # ===== RECORD FUEL =====
    def record_fuel():
        selection = vehicle_list.curselection()

        if not selection:
            messagebox.showinfo(
                "Select a vehicle",
                "Choose a vehicle first.",
                parent=window
            )
            return

        vehicle = visible_vehicles[selection[0]]

        dialog = tk.Toplevel(window)
        dialog.title("Record Fuel")
        dialog.resizable(False, False)
        dialog.transient(window)

        form = scrollable_form(dialog)

        date_var = tk.StringVar(value=date.today().isoformat())
        mileage_var = tk.StringVar(value=str(vehicle.mileage))
        gallons_var = tk.StringVar()
        cost_var = tk.StringVar()
        full_var = tk.BooleanVar(value=False)

        ttk.Label(
            form,
            text=f"{vehicle.year} {vehicle.name}",
            font=("Segoe UI", 13, "bold")
        ).grid(
            row=0, column=0, columnspan=2,
            sticky="w", pady=(0, 12)
        )

        fields = [
            ("Fill-up date (YYYY-MM-DD):", date_var),
            ("Odometer mileage:", mileage_var),
            ("US gallons added:", gallons_var),
            ("Total paid ($):", cost_var)
        ]

        for row, (label, variable) in enumerate(fields, start=1):
            ttk.Label(
                form, text=label
            ).grid(
                row=row, column=0, sticky="w", pady=6
            )

            ttk.Entry(
                form, textvariable=variable, width=25
            ).grid(
                row=row, column=1, padx=(12, 0), pady=6
            )

        ttk.Label(
            form,
            text="Enter the receipt total, not the price per gallon."
        ).grid(
            row=5, column=0, columnspan=2,
            sticky="w", pady=(4, 10)
        )

        ttk.Checkbutton(
            form,
            text="Tank was filled completely",
            variable=full_var
        ).grid(
            row=6, column=0, columnspan=2, sticky="w"
        )

        octane_var = octane_field(form, 7)
        fuel_type_var = fuel_type_field(form, 9, octane_var=octane_var)

        receipt = ReceiptPanel(form, 11, "fuel", {"date": date_var, "mileage": mileage_var, "gallons": gallons_var, "cost": cost_var, "octane": octane_var, "fuel_type": fuel_type_var})

        def save_fuel():
            try:
                fill_up_date = date.fromisoformat(
                    date_var.get().strip()
                )
                if fill_up_date > date.today():
                    messagebox.showerror(
                        "Invalid date",
                        "Fill-up date cannot be in the future.",
                        parent=dialog
                    )
                    return
                if vehicle.fuel_history:
                    latest_date = max(
                        date.fromisoformat(record["date"])
                        for record in vehicle.fuel_history
                    )

                    if fill_up_date < latest_date:
                        messagebox.showerror(
                            "Invalid date",
                            f"Fill-up date cannot be before "
                            f"{latest_date:%m/%d/%Y}, the latest "
                            "recorded fill-up.",
                            parent=dialog
                        )
                        return
                    
                mileage = int(mileage_var.get().strip())
                gallons = Decimal(gallons_var.get().strip())
                cost_cents = parse_cost_cents(cost_var.get().strip())
                cost = cents_to_dollars(cost_cents)

                if mileage < vehicle.mileage:
                    messagebox.showerror(
                        "Invalid mileage",
                        f"Odometer cannot be below "
                        f"{vehicle.mileage:,} miles.",
                        parent=dialog
                    )
                    return

                if not gallons.is_finite() or gallons <= 0:
                    raise ValueError

            except (ValueError, InvalidOperation):
                messagebox.showerror(
                    "Invalid entry",
                    "Enter a valid date as YYYY-MM-DD "
                    "(example: 2026-10-30).\n"
                    "Use whole numbers for mileage.\n"
                    "Gallons must be greater than zero.\n"
                    "Cost must be non-negative with no more "
                    "than two decimal places.\n\n"
                    "Do not include commas or dollar signs.",
                    parent=dialog
                )
                return

            try:
                fuel_type = parse_fuel_type(fuel_type_var.get())
                octane = None if is_diesel(fuel_type or "") else parse_octane(octane_var.get())
            except ValueError as error:
                messagebox.showerror("Invalid fuel details", str(error), parent=dialog)
                return

            price_per_gallon = cost / gallons
            full_tank = full_var.get()

            confirmed = messagebox.askyesno(
                "Confirm fill-up",
                f"{vehicle.year} {vehicle.name}\n\n"
                f"Fill-up date: {fill_up_date:%m/%d/%Y}\n"
                f"Odometer: {mileage:,} miles\n"
                f"US gallons: {gallons}\n"
                f"Octane: {'Not applicable (diesel)' if is_diesel(fuel_type or '') else octane if octane is not None else 'Not recorded'}\n"
                f"Fuel type: {fuel_type or 'Not recorded'}\n"
                f"Total paid: ${cost:.2f}\n"
                f"Price per gallon: ${price_per_gallon:.3f}\n"
                f"Full tank: {'Yes' if full_tank else 'No'}\n\n"
                "Save this fill-up and update the odometer?",
                parent=dialog
            )

            if not confirmed:
                return

            record = {
                "date": fill_up_date.isoformat(),
                "mileage": mileage,
                "gallons": str(gallons),
                "cost_cents": cost_cents,
                "full_tank": full_tank,
                "octane": octane,
                "fuel_type": fuel_type
            }

            old_mileage = vehicle.mileage
            vehicle.fuel_history.append(record)
            vehicle.mileage = mileage

            try:
                receipt.commit(record)
                save_vehicles(vehicles)

            except (OSError, TypeError, ValueError) as error:
                receipt.rollback()
                vehicle.fuel_history.pop()
                vehicle.mileage = old_mileage

                messagebox.showerror(
                    "Could not save",
                    f"The fill-up was not recorded.\n\n{error}",
                    parent=dialog
                )
                return

            show_vehicle()
            notebook.select(fuel_tab)

            items = fuel_table.get_children()

            if items:
                fuel_table.selection_set(items[-1])
                fuel_table.see(items[-1])

            dialog.destroy()

            messagebox.showinfo(
                "Fuel recorded",
                "The fill-up and odometer were saved.",
                parent=window
            )

        buttons = ttk.Frame(form)
        buttons.grid(
            row=12, column=0, columnspan=2,
            sticky="e", pady=(20, 0)
        )

        ttk.Button(
            buttons,
            text="Cancel",
            command=dialog.destroy
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            buttons,
            text="Save Fill-up",
            command=save_fuel
        ).pack(side="left")

        dialog.bind("<Escape>", lambda event: dialog.destroy())
        dialog.wait_visibility()
        dialog.grab_set()

    ttk.Button(
        fuel_tab,
        text="Record Fuel",
        command=record_fuel
    ).pack(anchor="w", pady=(10, 0))

        # ===== EDIT FUEL =====
    def edit_fuel():
        vehicle_selection = vehicle_list.curselection()
        record_selection = fuel_table.selection()

        if not vehicle_selection or not record_selection:
            messagebox.showinfo(
                "Select a fuel record",
                "Choose a vehicle, then select a fuel record.",
                parent=window
            )
            return

        vehicle = visible_vehicles[vehicle_selection[0]]
        index = fuel_table.index(record_selection[0])
        record = vehicle.fuel_history[index]

        dialog = tk.Toplevel(window)
        dialog.title("Edit Fuel")
        dialog.resizable(False, False)
        dialog.transient(window)

        form = scrollable_form(dialog)

        mileage_var = tk.StringVar(
            value=str(record["mileage"])
        )
        gallons_var = tk.StringVar(
            value=record["gallons"]
        )
        cost_var = tk.StringVar(
            value=f"{Decimal(record['cost_cents']) / 100:.2f}"
        )
        full_var = tk.BooleanVar(
            value=record["full_tank"]
        )

        ttk.Label(
            form,
            text=f"{vehicle.year} {vehicle.name}",
            font=("Segoe UI", 13, "bold")
        ).grid(
            row=0, column=0, columnspan=2,
            sticky="w", pady=(0, 8)
        )

        ttk.Label(
           form, text=f"Fill-up date: {date.fromisoformat(record['date']):%m/%d/%Y}"
        ).grid(
            row=1, column=0, columnspan=2,
            sticky="w", pady=(0, 12)
        )

        fields = [
            ("Odometer mileage:", mileage_var),
            ("US gallons added:", gallons_var),
            ("Total paid ($):", cost_var)
        ]

        for row, (label, variable) in enumerate(fields, start=2):
            ttk.Label(
                form, text=label
            ).grid(row=row, column=0, sticky="w", pady=6)

            ttk.Entry(
                form, textvariable=variable, width=25
            ).grid(
                row=row, column=1, padx=(12, 0), pady=6
            )

        ttk.Checkbutton(
            form,
            text="Tank was filled completely",
            variable=full_var
        ).grid(
            row=5, column=0, columnspan=2,
            sticky="w", pady=(10, 0)
        )

        octane_var = octane_field(form, 6, record.get("octane"))
        fuel_type_var = fuel_type_field(form, 8, record.get("fuel_type"), octane_var)

        receipt = ReceiptPanel(form, 10, "fuel", {"mileage": mileage_var, "gallons": gallons_var, "cost": cost_var, "octane": octane_var, "fuel_type": fuel_type_var}, record.get("receipt_photo"))

        def save_fuel_changes():
            try:
                mileage = int(mileage_var.get().strip())
                gallons = Decimal(gallons_var.get().strip())
                cost_cents = parse_cost_cents(cost_var.get().strip())
                cost = cents_to_dollars(cost_cents)

                if not gallons.is_finite() or gallons <= 0:     # keep
                    raise ValueError                            # keep

            except (ValueError, InvalidOperation):
                messagebox.showerror(
                    "Invalid entry",
                    "Use whole numbers for mileage.\n"
                    "Gallons must be greater than zero.\n"
                    "Cost must be non-negative with no more "
                    "than two decimal places.\n\n"
                    "Do not include commas or dollar signs.",
                    parent=dialog
                )
                return
            minimum_mileage = vehicle.starting_mileage

            if index > 0:
                minimum_mileage = max(
                    minimum_mileage,
                    vehicle.fuel_history[index - 1]["mileage"]
                )

            maximum_mileage = (
                vehicle.fuel_history[index + 1]["mileage"]
                if index + 1 < len(vehicle.fuel_history)
                else vehicle.mileage
            )

            if not minimum_mileage <= mileage <= maximum_mileage:
                messagebox.showerror(
                    "Invalid mileage",
                    f"Mileage must be between "
                    f"{minimum_mileage:,} and "
                    f"{maximum_mileage:,}.\n\n"
                    "This preserves fill-up order and stays "
                    "within the current odometer.",
                    parent=dialog
                )
                return

            try:
                fuel_type = parse_fuel_type(fuel_type_var.get())
                octane = None if is_diesel(fuel_type or "") else parse_octane(octane_var.get())
            except ValueError as error:
                messagebox.showerror("Invalid fuel details", str(error), parent=dialog)
                return

            full_tank = full_var.get()

            if (
                not receipt.source
                and mileage == record["mileage"]
                and gallons == Decimal(record["gallons"])
                and cost_cents == record["cost_cents"]
                and full_tank == record["full_tank"]
                and octane == record.get("octane")
                and fuel_type == record.get("fuel_type")
            ):
                messagebox.showinfo(
                    "No changes",
                    "The fuel record is unchanged.",
                    parent=dialog
                )
                return

            price_per_gallon = cost / gallons

            confirmed = messagebox.askyesno(
                "Confirm fuel changes",
                f"Odometer: {mileage:,} miles\n"
                f"US gallons: {gallons}\n"
                f"Octane: {'Not applicable (diesel)' if is_diesel(fuel_type or '') else octane if octane is not None else 'Not recorded'}\n"
                f"Fuel type: {fuel_type or 'Not recorded'}\n"
                f"Total paid: ${cost:.2f}\n"
                f"Price per gallon: ${price_per_gallon:.3f}\n"
                f"Full tank: {'Yes' if full_tank else 'No'}\n\n"
                "The current vehicle odometer will stay unchanged.\n"
                "Changes will affect MPG calculations.\n\n"
                "Save these changes?",
                parent=dialog
            )

            if not confirmed:
                return

            updated_record = record.copy()
            updated_record.update({
                "mileage": mileage,
                "gallons": str(gallons),
                "cost_cents": cost_cents,
                "full_tank": full_tank,
                "octane": octane,
                "fuel_type": fuel_type
            })

            vehicle.fuel_history[index] = updated_record

            try:
                receipt.commit(updated_record)
                save_vehicles(vehicles)

            except (OSError, TypeError, ValueError) as error:
                receipt.rollback()
                vehicle.fuel_history[index] = record

                messagebox.showerror(
                    "Could not save",
                    f"Changes were canceled.\n\n{error}",
                    parent=dialog
                )
                return

            show_vehicle()

            items = fuel_table.get_children()
            fuel_table.selection_set(items[index])
            fuel_table.see(items[index])

            dialog.destroy()

            messagebox.showinfo(
                "Fuel updated",
                "Changes were saved.",
                parent=window
            )

        buttons = ttk.Frame(form)
        buttons.grid(
            row=11, column=0, columnspan=2,
            sticky="e", pady=(20, 0)
        )

        ttk.Button(
            buttons,
            text="Cancel",
            command=dialog.destroy
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            buttons,
            text="Save Changes",
            command=save_fuel_changes
        ).pack(side="left")

        dialog.bind("<Escape>", lambda event: dialog.destroy())
        dialog.wait_visibility()
        dialog.grab_set()

    ttk.Button(
        fuel_tab,
        text="Edit Fuel",
        command=edit_fuel
    ).pack(anchor="w", pady=(8, 0))

        # ===== DELETE FUEL =====
    def delete_fuel():
        vehicle_selection = vehicle_list.curselection()
        record_selection = fuel_table.selection()

        if not vehicle_selection or not record_selection:
            messagebox.showinfo(
                "Select a fuel record",
                "Choose a vehicle, then select a fuel record.",
                parent=window
            )
            return

        vehicle = visible_vehicles[vehicle_selection[0]]
        index = fuel_table.index(record_selection[0])
        record = vehicle.fuel_history[index]
        cost = Decimal(record["cost_cents"]) / 100

        confirmed = messagebox.askyesno(
            "Delete fuel record",
            f"{vehicle.year} {vehicle.name}\n\n"
            f"Delete fuel date: {date.fromisoformat(record['date']):%m/%d/%Y}\n"
            f"Odometer: {record['mileage']:,} miles\n"
            f"US gallons: {record['gallons']}\n"
            f"Total paid: ${cost:.2f}\n"
            f"Full tank: {'Yes' if record['full_tank'] else 'No'}\n\n"
            "Removing a fill-up can make MPG inaccurate "
            "because its gallons will no longer be included.\n"
            "The current odometer will remain unchanged.\n\n"
            "Delete this record?",
            parent=window,
            default=messagebox.NO
        )

        if not confirmed:
            return

        vehicle.fuel_history.pop(index)

        try:
            save_vehicles(vehicles)

        except (OSError, TypeError, ValueError) as error:
            vehicle.fuel_history.insert(index, record)

            messagebox.showerror(
                "Could not save",
                f"The fuel record was not deleted.\n\n{error}",
                parent=window
            )
            return

        show_vehicle()

        items = fuel_table.get_children()

        if items:
            next_index = min(index, len(items) - 1)
            fuel_table.selection_set(items[next_index])
            fuel_table.see(items[next_index])

        messagebox.showinfo(
            "Fuel deleted",
            "The fuel record was deleted and saved.",
            parent=window
        )

    ttk.Button(
        fuel_tab,
        text="Delete Fuel",
        command=delete_fuel
    ).pack(anchor="w", pady=(8, 0))

        # ===== EXPORT SELECTED VEHICLE =====
    def export_selected_vehicle():
        selection = vehicle_list.curselection()

        if not selection:
            messagebox.showinfo(
                "Select a vehicle",
                "Choose a vehicle first.",
                parent=window
            )
            return

        vehicle = visible_vehicles[selection[0]]

        safe_name = "".join(
            character if character.isalnum() else "_"
            for character in vehicle.name
        ).strip("_") or "vehicle"

        filename = filedialog.asksaveasfilename(
            parent=window,
            title="Export vehicle to Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
            initialfile=f"{vehicle.year}_{safe_name}.xlsx"
        )

        if not filename:
            return

        try:
            saved_file = export_vehicle_excel(
                vehicle,
                output_file=filename
            )
        except (
            OSError, ValueError, TypeError,
            KeyError, InvalidOperation
        ) as error:
            messagebox.showerror(
                "Export failed",
                f"Could not export the workbook.\n\n{error}",
                parent=window
            )
            return

        if saved_file is None:
            messagebox.showerror(
                "Export failed",
                "Could not save the workbook.\n\n"
                "If it is open in Excel, close it and try again.\n"
                "Also check that you can save in that folder.",
                parent=window
            )
            return

        messagebox.showinfo(
            "Export complete",
            f"Workbook saved to:\n{saved_file}",
            parent=window
        )

    ttk.Label(backup_tab, text="Data & backup", font=("Segoe UI", 22, "bold")).pack(anchor="w", pady=12)
    ttk.Label(backup_tab, text="Export for Mobile includes your vehicle photos. Back up the phone before importing; imports do not merge newer phone entries. PDF attachments must be copied separately.", wraplength=480).pack(anchor="w", pady=10)
    ttk.Button(backup_tab, text="Manage vehicles", command=toggle_management).pack(anchor="w", pady=8)

    ttk.Button(
        backup_tab,
        text="Export to Excel",
        command=export_selected_vehicle
    ).pack(anchor="w", pady=(8, 0))

        # ===== EXPORT FOR MOBILE =====
    def export_for_mobile():
        if not vehicles:
            messagebox.showinfo(
                "No vehicles",
                "Add a vehicle before exporting.",
                parent=window
            )
            return

        filename = filedialog.asksaveasfilename(
            parent=window,
            title="Export vehicles and photos for mobile",
            defaultextension=".json",
            filetypes=[("Mobile backup", "*.json")],
            initialfile="MileSage_mobile_backup.json"
        )

        if not filename:
            return

        destination = Path(filename)

        if destination.resolve() in {
            Path(__file__).with_name("vehicles.json").resolve(),
            Path(__file__).with_name("vehicles_backup.json").resolve()
        }:
            messagebox.showerror(
                "Choose another filename",
                "Keep the mobile export separate from your desktop data.",
                parent=window
            )
            return

        try:
            backup = build_mobile_backup(vehicles)
            destination.write_text(
                json.dumps(backup, indent=2),
                encoding="utf-8"
            )

        except (OSError, ValueError, TypeError) as error:
            messagebox.showerror(
                "Export failed",
                str(error),
                parent=window
            )
            return

        messagebox.showinfo(
            "Mobile export saved",
            f"Saved to:\n{destination}\n\n"
            "Transfer this file to your phone.\n"
            "Back up your phone records before importing it "
            "through Data & backup.",
            parent=window
        )

    ttk.Button(
        backup_tab,
        text="Export for Mobile",
        command=export_for_mobile
    ).pack(anchor="w", pady=(8, 0))


    # ===== STARTUP SELECTION =====
    vehicle_list.bind("<<ListboxSelect>>", show_vehicle)

    search_var.trace_add("write", lambda *args: refresh_vehicle_list())
    sort_var.trace_add("write", lambda *args: refresh_vehicle_list())
    reverse_var.trace_add("write", lambda *args: refresh_vehicle_list())
    spending_kind.trace_add("write", lambda *args: show_vehicle())
    refresh_vehicle_list()

    ttk.Label(
        container,
        text="Vehicle Manager â€” mileage updates save automatically",
        foreground="#666666"
    ).pack(anchor="w", pady=(12, 0))

    def close_app():
        preferences = {
            "sort": sort_var.get(),
            "reverse": reverse_var.get(),
            "width": window.winfo_width(),
            "height": window.winfo_height(),
            "sidebar_width": list_panel.winfo_width() if management_visible else sidebar_width
        }
        try:
            preferences_file.write_text(
                json.dumps(preferences, indent=4),
                encoding="utf-8"
            )
        except OSError as error:
            messagebox.showerror(
                "Could not save preferences",
                str(error),
                parent=window
            )
            return

        window.destroy()

    window.protocol("WM_DELETE_WINDOW", close_app)

    window.mainloop()


if __name__ == "__main__":
    main()
