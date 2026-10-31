import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from datetime import date
from decimal import Decimal, InvalidOperation
from storage import load_vehicles, save_vehicles
from formatting import format_mileage, format_date, cents_to_dollars
from validation import parse_cost_cents
from Vehicle_Manager import Vehicle
from excel_export import export_vehicle_excel

# Main function
def main():
    window = tk.Tk()
    window.title("Vehicle Manager")
    window.geometry("1100x650")
    window.minsize(800, 500)

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
    container = ttk.Frame(window, padding=20)
    container.pack(fill="both", expand=True)

    ttk.Label(
        container,
        text="Vehicle Manager",
        font=("Segoe UI", 24, "bold")
    ).pack(anchor="w", pady=(0, 15))

    panels = ttk.Panedwindow(container, orient="horizontal")
    panels.pack(fill="both", expand=True)

    list_panel = ttk.Frame(panels, padding=10)
    details_panel = ttk.Frame(panels, padding=15)

    panels.add(list_panel, weight=1)
    panels.add(details_panel, weight=2)

    # ===== VEHICLE LIST =====
    ttk.Label(
        list_panel,
        text="Your vehicles",
        font=("Segoe UI", 14, "bold")
    ).pack(anchor="w", pady=(0, 10))

    vehicle_list = tk.Listbox(
        list_panel,
        font=("Segoe UI", 12),
        exportselection=False
    )
    vehicle_list.pack(fill="both", expand=True)

    for vehicle in vehicles:
        vehicle_list.insert(
            tk.END,
            f"{vehicle.year} {vehicle.name}"
        )

    # ===== TABS =====
    notebook = ttk.Notebook(details_panel)
    notebook.pack(fill="both", expand=True)

    overview_tab = ttk.Frame(notebook, padding=15)
    service_tab = ttk.Frame(notebook, padding=10)
    fuel_tab = ttk.Frame(notebook, padding=10)

    notebook.add(overview_tab, text="Overview")
    notebook.add(service_tab, text="Service History")
    notebook.add(fuel_tab, text="Fuel History")

    details_text = tk.StringVar(
        value="Select a vehicle to view its details."
    )

    ttk.Label(
        overview_tab,
        textvariable=details_text,
        font=("Segoe UI", 12),
        justify="left",
        anchor="nw"
    ).pack(fill="both", expand=True)

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
        ("gallons", "US Gallons", 100),
        ("cost", "Total Cost ($)", 110),
        ("full", "Full Tank", 90),
        ("mpg", "MPG", 170),
        ("price_per_gallon", "Price/Gallon ($)", 130)
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

        if not selection:
            details_text.set(
                "No vehicle selected.\n"
                "Use Add Vehicle to create a vehicle."
            )

            for table in (service_table, fuel_table):
                for item in table.get_children():
                    table.delete(item)

            service_status.set("No vehicle selected")
            fuel_status.set("No vehicle selected")
            return

        vehicle = vehicles[selection[0]]

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

        # ===== DASHBOARD TEXT =====
        details_text.set(
            f"{vehicle.year} {vehicle.name}\n"
            f"Current odometer: {format_mileage(vehicle.mileage)}\n\n"
            f"MAINTENANCE\n"
            f"Oil change: {oil_status}\n"
            f"Tire rotation: {tire_status}\n\n"
            f"SERVICE\n"
            f"Records: {len(vehicle.service_history)}\n"
            f"Recorded spending: ${service_total:,.2f}\n"
            f"Records without a cost: {unknown_costs}\n"
            f"Missing costs are excluded from spending.\n\n"
            f"FUEL\n"
            f"Fill-ups: {len(vehicle.fuel_history)}\n"
            f"Total fuel: {total_gallons:,.3f} US gallons\n"
            f"Total spending: ${fuel_total:,.2f}\n"
            f"Average price per gallon: {average_text}"
        )

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

        for record in vehicle.fuel_history:
            gallons = Decimal(record["gallons"])
            full_tank = record["full_tank"]

            if record["mileage"] is None:
                previous_full_mileage = None
                gallons_since_full = Decimal("0")
                mpg_text = "Mileage not recorded"

            elif previous_full_mileage is None:
                if full_tank:
                    previous_full_mileage = record["mileage"]
                    gallons_since_full = Decimal("0")
                    mpg_text = "Starting full tank"
                else:
                    mpg_text = "Need starting full tank"

            else:
                gallons_since_full += gallons

                if full_tank:
                    miles = (
                        record["mileage"] - previous_full_mileage
                    )

                    if miles > 0 and gallons_since_full > 0:
                        mpg = Decimal(miles) / gallons_since_full
                        mpg_text = f"{mpg:.2f}"
                    else:
                        mpg_text = "Insufficient distance"

                    previous_full_mileage = record["mileage"]
                    gallons_since_full = Decimal("0")
                else:
                    mpg_text = "Waiting for full tank"

            fuel_table.insert("", tk.END, values=(
                format_date(record["date"]),
                format_mileage(record["mileage"]),
                record["gallons"],
                vehicle.format_service_cost(record),
                "Yes" if full_tank else "No",
                mpg_text,
                f"{Decimal(record['cost_cents']) / 100 / gallons:.3f}"
            ))

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

        vehicle = vehicles[selection[0]]

        miles = simpledialog.askinteger(
            "Update mileage",
            f"{vehicle.year} {vehicle.name}\n"
            f"Current odometer: {vehicle.mileage:,} miles\n\n"
            "How many miles did you drive?",
            minvalue=0,
            parent=window
        )

        if miles is None or miles == 0:
            return

        old_mileage = vehicle.mileage
        new_mileage = old_mileage + miles

        confirmed = messagebox.askyesno(
            "Confirm mileage",
            f"Add {miles:,} miles to {vehicle.name}?\n\n"
            f"Current odometer: {old_mileage:,}\n"
            f"New odometer: {new_mileage:,}",
            parent=window
        )

        if not confirmed:
            return

        vehicle.drive(miles)

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

        show_vehicle()
        messagebox.showinfo(
            "Mileage updated",
            f"{vehicle.name} now has {vehicle.mileage:,} miles.",
            parent=window
        )

    ttk.Button(
        overview_tab,
        text="Update Mileage",
        command=update_mileage
    ).pack(anchor="w", pady=(12, 0))

        # ===== ADD VEHICLE =====
    def add_vehicle():
        dialog = tk.Toplevel(window)
        dialog.title("Add Vehicle")
        dialog.resizable(False, False)
        dialog.transient(window)

        form = ttk.Frame(dialog, padding=20)
        form.pack(fill="both", expand=True)

        name_var = tk.StringVar()
        year_var = tk.StringVar()
        mileage_var = tk.StringVar()

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

            confirmed = messagebox.askyesno(
                "Confirm new vehicle",
                f"Add {year} {name}?\n\n"
                f"Starting odometer: {mileage:,} miles",
                parent=dialog
            )

            if not confirmed:
                return

            new_vehicle = Vehicle(name, year, mileage)
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

            vehicle_list.insert(
                tk.END, f"{year} {name}"
            )
            vehicle_list.selection_clear(0, tk.END)
            vehicle_list.selection_set(len(vehicles) - 1)
            vehicle_list.see(tk.END)
            show_vehicle()

            dialog.destroy()

            messagebox.showinfo(
                "Vehicle added",
                f"{year} {name} was added and saved.",
                parent=window
            )

        buttons = ttk.Frame(form)
        buttons.grid(
            row=3, column=0, columnspan=2,
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
        list_panel,
        text="Add Vehicle",
        command=add_vehicle
    ).pack(anchor="w", pady=(10, 0))

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

        index = selection[0]
        vehicle = vehicles[index]

        dialog = tk.Toplevel(window)
        dialog.title("Edit Vehicle")
        dialog.resizable(False, False)
        dialog.transient(window)

        form = ttk.Frame(dialog, padding=20)
        form.pack(fill="both", expand=True)

        name_var = tk.StringVar(value=vehicle.name)
        year_var = tk.StringVar(value=str(vehicle.year))
        mileage_var = tk.StringVar(value=str(vehicle.mileage))

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

            minimum_mileage = max(
                vehicle.starting_mileage,
                vehicle.last_service_mileage,
                vehicle.last_tire_rotation_mileage or 0,
                max(
                    (
                        record["mileage"]
                        for record in vehicle.service_history
                    ),
                    default=0
                ),
                max(
                    (
                        record["mileage"]
                        for record in vehicle.fuel_history
                    ),
                    default=0
                )
            )

            if year <= 0:
                messagebox.showerror(
                    "Invalid year",
                    "Year must be positive.",
                    parent=dialog
                )
                return

            if mileage < minimum_mileage:
                messagebox.showerror(
                    "Invalid mileage",
                    f"Mileage cannot be below "
                    f"{minimum_mileage:,}, based on tracked history.",
                    parent=dialog
                )
                return

            old_values = (
                vehicle.name,
                vehicle.year,
                vehicle.mileage
            )

            if (name, year, mileage) == old_values:
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

            vehicle.name = name
            vehicle.year = year
            vehicle.mileage = mileage

            try:
                save_vehicles(vehicles)

            except (OSError, TypeError, ValueError) as error:
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

            vehicle_list.delete(index)
            vehicle_list.insert(index, f"{year} {name}")
            vehicle_list.selection_set(index)
            vehicle_list.see(index)
            show_vehicle()

            dialog.destroy()

            messagebox.showinfo(
                "Vehicle updated",
                "Changes were saved.",
                parent=window
            )

        buttons = ttk.Frame(form)
        buttons.grid(
            row=3, column=0, columnspan=2,
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
        list_panel,
        text="Edit Vehicle",
        command=edit_vehicle
    ).pack(anchor="w", pady=(8, 0))

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

        index = selection[0]
        vehicle = vehicles[index]

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

        vehicle_list.delete(index)
        vehicle_list.selection_clear(0, tk.END)

        if vehicles:
            next_index = min(index, len(vehicles) - 1)
            vehicle_list.selection_set(next_index)
            vehicle_list.see(next_index)

        show_vehicle()

        messagebox.showinfo(
            "Vehicle removed",
            f"{vehicle.year} {vehicle.name} was removed and saved.",
            parent=window
        )

    ttk.Button(
        list_panel,
        text="Remove Vehicle",
        command=remove_vehicle
    ).pack(anchor="w", pady=(8, 0))

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

        vehicle = vehicles[selection[0]]

        dialog = tk.Toplevel(window)
        dialog.title("Record Service")
        dialog.resizable(False, False)
        dialog.transient(window)

        form = ttk.Frame(dialog, padding=20)
        form.pack(fill="both", expand=True)

        date_var = tk.StringVar(value=date.today().isoformat())
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

        ttk.Label(
            form,
            text=f"Service mileage: {vehicle.mileage:,}"
        ).grid(
            row=1, column=0, columnspan=2,
            sticky="w", pady=(0, 12)
        )

        ttk.Label(
            form, text="Service performed:"
        ).grid(row=2, column=0, sticky="w", pady=6)

        description_entry = ttk.Entry(
            form, textvariable=description_var, width=40
        )
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
                    cost = Decimal(cost_input)

                    if not cost.is_finite() or cost < 0:
                        raise ValueError

                    cents = cost * 100

                    if cents != cents.to_integral_value():
                        raise ValueError

                    cost_cents = int(cents)

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
                "mileage": vehicle.mileage,
                "description": description,
                "cost_cents": cost_cents,
                "oil_reset": oil_var.get(),
                "tire_reset": tire_var.get()
            }

            cost_text = vehicle.format_service_cost(record)

            confirmed = messagebox.askyesno(
                "Confirm service",
                f"{vehicle.year} {vehicle.name}\n"
                f"Service date: {service_date:%m/%d/%Y}\n"
                f"Mileage: {vehicle.mileage:,}\n"
                f"Service: {description}\n"
                f"Cost ($): {cost_text}\n\n"
                f"Reset oil: {'Yes' if oil_var.get() else 'No'}\n"
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
                vehicle.last_service_mileage = vehicle.mileage

            if record["tire_reset"]:
                vehicle.last_tire_rotation_mileage = vehicle.mileage

            try:
                save_vehicles(vehicles)

            except (OSError, TypeError, ValueError) as error:
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
            row=8, column=0, columnspan=2,
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

        vehicle = vehicles[vehicle_selection[0]]
        index = service_table.index(record_selection[0])
        record = vehicle.service_history[index]

        dialog = tk.Toplevel(window)
        dialog.title("Edit Service")
        dialog.resizable(False, False)
        dialog.transient(window)

        form = ttk.Frame(dialog, padding=20)
        form.pack(fill="both", expand=True)

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

        description_entry = ttk.Entry(
            form, textvariable=description_var, width=40
        )
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
                    cost = Decimal(cost_input)

                    if not cost.is_finite() or cost < 0:
                        raise ValueError

                    cents = cost * 100

                    if cents != cents.to_integral_value():
                        raise ValueError

                    cost_cents = int(cents)

                except (InvalidOperation, ValueError):
                    messagebox.showerror(
                        "Invalid cost",
                        "Enter a non-negative cost with no more "
                        "than two decimal places.\n"
                        "Do not include dollar signs or commas.",
                        parent=dialog
                    )
                    return

            if (
                description == record["description"]
                and cost_cents == current_cents
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

            cost_text = vehicle.format_service_cost(
                updated_record
            )

            confirmed = messagebox.askyesno(
                "Confirm service changes",
                f"Service: {description}\n"
                f"Cost ($): {cost_text}\n\n"
                "Save these changes?",
                parent=dialog
            )

            if not confirmed:
                return

            vehicle.service_history[index] = updated_record

            try:
                save_vehicles(vehicles)

            except (OSError, TypeError, ValueError) as error:
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
            row=5, column=0, columnspan=2,
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

        vehicle = vehicles[vehicle_selection[0]]
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

        vehicle = vehicles[selection[0]]

        dialog = tk.Toplevel(window)
        dialog.title("Record Fuel")
        dialog.resizable(False, False)
        dialog.transient(window)

        form = ttk.Frame(dialog, padding=20)
        form.pack(fill="both", expand=True)

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
                cost = Decimal(cost_var.get().strip())

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

                if not cost.is_finite() or cost < 0:
                    raise ValueError

                cents = cost * 100

                if cents != cents.to_integral_value():
                    raise ValueError

                cost_cents = int(cents)

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

            price_per_gallon = cost / gallons
            full_tank = full_var.get()

            confirmed = messagebox.askyesno(
                "Confirm fill-up",
                f"{vehicle.year} {vehicle.name}\n\n"
                f"Fill-up date: {fill_up_date:%m/%d/%Y}\n"
                f"Odometer: {mileage:,} miles\n"
                f"US gallons: {gallons}\n"
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
                "full_tank": full_tank
            }

            old_mileage = vehicle.mileage
            vehicle.fuel_history.append(record)
            vehicle.mileage = mileage

            try:
                save_vehicles(vehicles)

            except (OSError, TypeError, ValueError) as error:
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

        vehicle = vehicles[vehicle_selection[0]]
        index = fuel_table.index(record_selection[0])
        record = vehicle.fuel_history[index]

        dialog = tk.Toplevel(window)
        dialog.title("Edit Fuel")
        dialog.resizable(False, False)
        dialog.transient(window)

        form = ttk.Frame(dialog, padding=20)
        form.pack(fill="both", expand=True)

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

        def save_fuel_changes():
            try:
                mileage = int(mileage_var.get().strip())
                gallons = Decimal(gallons_var.get().strip())
                cost = Decimal(cost_var.get().strip())

                if not gallons.is_finite() or gallons <= 0:
                    raise ValueError

                if not cost.is_finite() or cost < 0:
                    raise ValueError

                cents = cost * 100

                if cents != cents.to_integral_value():
                    raise ValueError

                cost_cents = int(cents)

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

            full_tank = full_var.get()

            if (
                mileage == record["mileage"]
                and gallons == Decimal(record["gallons"])
                and cost_cents == record["cost_cents"]
                and full_tank == record["full_tank"]
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
                "full_tank": full_tank
            })

            vehicle.fuel_history[index] = updated_record

            try:
                save_vehicles(vehicles)

            except (OSError, TypeError, ValueError) as error:
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
            row=6, column=0, columnspan=2,
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

        vehicle = vehicles[vehicle_selection[0]]
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

        vehicle = vehicles[selection[0]]

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

    ttk.Button(
        overview_tab,
        text="Export to Excel",
        command=export_selected_vehicle
    ).pack(anchor="w", pady=(8, 0))

    # ===== STARTUP SELECTION =====
    vehicle_list.bind("<<ListboxSelect>>", show_vehicle)

    if vehicles:
        vehicle_list.selection_set(0)
        show_vehicle()
    else:
        details_text.set(
            "No vehicles saved yet.\n"
            "Add a vehicle through the terminal app."
        )

    ttk.Label(
        container,
        text="Vehicle Manager — mileage updates save automatically",
        foreground="#666666"
    ).pack(anchor="w", pady=(12, 0))

    window.mainloop()


if __name__ == "__main__":
    main()