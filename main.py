import json
from pathlib import Path
from Vehicle_Manager import Vehicle
import csv
import shutil
import time
import os
from decimal import Decimal
from excel_export import export_vehicle_excel


DATA_FILE = Path(__file__).with_name("vehicles.json")

print("Python has opened main.py")

def select_vehicle(vehicles):
    if not vehicles:
        print("No vehicles available. Add a vehicle using option 6.")
        return None
    print("\nWhich vehicle?")

    for number, vehicle in enumerate(vehicles, start=1):
        print(f"{number}. {vehicle.name}")

    try:
        choice = int(input(f"Select vehicle (1-{len(vehicles)}): "))

        if 1 <= choice <= len(vehicles):
            return vehicles[choice - 1]

        print("Invalid vehicle selection.")
    except ValueError:
        print("Please enter a whole number.")

    return None

def save_vehicles(vehicles):
    vehicle_data = [vehicle.to_dict() for vehicle in vehicles]
    backup_file = DATA_FILE.with_name("vehicles_backup.json")
    temp_file = DATA_FILE.with_name("vehicles.tmp")

    for attempt in range(3):
        try:
            if DATA_FILE.exists():
                shutil.copy2(DATA_FILE, backup_file)

            with open(temp_file, "w", encoding="utf-8") as file:
                json.dump(vehicle_data, file, indent=4)

            os.replace(temp_file, DATA_FILE)
            return

        except PermissionError:
            if attempt < 2:
                time.sleep(0.5)
            else:
                print(
                    "Could not save: the data or backup file is locked. "
                    "Your changes are still in memory."
                )
                raise

def export_service_history(vehicle):
    if not vehicle.service_history:
        print("No service records to export.")
        return

    export_folder = Path(__file__).parent / "exports"
    export_folder.mkdir(exist_ok=True)

    # Keep only letters and numbers for the filename.
    safe_name = "".join(
        character if character.isalnum() else "_"
        for character in vehicle.name
    ).strip("_") or "vehicle"

    export_file = (
        export_folder
        / f"{vehicle.year}_{safe_name}_service_history.csv"
    )

    if export_file.exists():
        confirm = input(
            f"{export_file.name} already exists. Replace it? (yes/no): "
        ).strip().lower()

        if confirm != "yes":
            print("Export canceled.")
            return

    try:
        with open(
            export_file, "w", newline="", encoding="utf-8-sig"
        ) as file:
            writer = csv.writer(file)

            writer.writerow([
                "Vehicle",
                "Year",
                "Date",
                "Mileage",
                "Service performed",
                "cost",
                "Oil countdown reset",
                "Tire countdown reset"
                
            ])

            for record in vehicle.service_history:
                oil_reset = (
                    "Yes" if record["oil_reset"] else "No"
                ) if "oil_reset" in record else "Unknown"

                tire_reset = (
                    "Yes" if record["tire_reset"] else "No"
                ) if "tire_reset" in record else "Unknown"
                
                cost_cents = record.get("cost_cents")
                cost_text = (
                    f"{cost_cents // 100}.{cost_cents % 100:02d}"
                    if cost_cents is not None
                    else "Not recorded"
                )

                writer.writerow([
                    vehicle.name,
                    vehicle.year,
                    record["date"],
                    record["mileage"],
                    record["description"],
                    cost_text,
                    oil_reset,
                    tire_reset
                ])

        print(f"Service history exported to:\n{export_file}")

    except OSError as error:
        print(f"Could not export service history: {error}")
        print("If the CSV is open in Excel, close it and try again.")

def export_fuel_history(vehicle):
    if not vehicle.fuel_history:
        print("No fuel records to export.")
        return

    safe_name = "".join(
        character if character.isalnum() else "_"
        for character in vehicle.name
    ).strip("_") or "vehicle"

    export_folder = Path(__file__).parent / "exports"
    export_file = (
        export_folder
        / f"{vehicle.year}_{safe_name}_fuel_history.csv"
    )

    if export_file.exists():
        confirm = input(
            f"{export_file.name} already exists. Replace it? (yes/no): "
        ).strip().lower()

        if confirm != "yes":
            print("Export canceled.")
            return

    try:
        export_folder.mkdir(exist_ok=True)

        with open(
            export_file, "w", newline="", encoding="utf-8-sig"
        ) as file:
            writer = csv.writer(file)

            writer.writerow([
                "Vehicle",
                "Model Year",
                "Fill-up Date",
                "Odometer Miles",
                "US Gallons",
                "Total Fuel Cost",
                "Full Tank"
            ])

            for record in vehicle.fuel_history:
                writer.writerow([
                    vehicle.name,
                    vehicle.year,
                    record["date"],
                    record["mileage"],
                    record["gallons"],
                    vehicle.format_service_cost(record),
                    "Yes" if record["full_tank"] else "No"
                ])

        print(f"Fuel history exported to:\n{export_file}")

    except OSError as error:
        print(f"Could not export fuel history: {error}")
        print("If the CSV is open in Excel, close it and try again.")
        
def main():
    print("Vehicle Manager is starting")

    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r") as file:
                loaded_vehicles = json.load(file)

            if not isinstance(loaded_vehicles, list):
                raise ValueError(
                    "Saved vehicle data must be a list."
                )

            vehicles = [
                Vehicle.from_dict(data)
                for data in loaded_vehicles
            ]

        except (OSError, ValueError, KeyError, TypeError) as error:
            print("\nCould not load saved vehicles.")
            print(f"File: {DATA_FILE}")
            print(f"Reason: {error}")
            print("Your saved file has not been changed.")
            print("Restore a working backup before trying again.")
            return

        print("Saved vehicles loaded successfully!")

    else:
        vehicles = [
            Vehicle("Toyota Tacoma", 2026, 5000),
            Vehicle("Ford Explorer", 2025, 12000)
        ]
    # Display vehicle information
    # tacoma.display_info()
    # explorer.display_info()

    #Vehicle Manager Menu
    while True:
        print ("\n===== VEHICLE MANAGER =====")

        print("\nVEHICLES")
        print("1. View vehicles")
        print("2. Update mileage")
        print("6. Add a vehicle")
        print("7. Remove vehicle")
        print("8. Edit a vehicle")

        print("\nMAINTENANCE AND SERVICE")
        print("3. Check maintenance")
        print("4. Record service")
        print("9. Service history")
        print("10. Set maintenance intervals")
        print("11. Maintenance summary")        
        print("13. edit service record")
        print("14. Delete service record")
        print("15. Service spending summary")

        print("\nFUEL")
        print("16. Record fuel fill-up")
        print("17. View fuel history")
        print("18. Edit fuel fill-up")
        print("19. Delete fuel fill-up")        
        print("21. Fuel Spending Summary")


        print("\nEXPORTS")
        print("12. Export service history")
        print("20. Export Excel workbook (service and fuel)")

        print("\nSAVE AND EXIT")
        print("5. Save and exit")
        
        choice = input("\nEnter your choice (1-21): ").strip()
        if choice == "1":
           for vehicle in vehicles:
               vehicle.display_info()
        elif choice == "2":
            selected_vehicle = select_vehicle(vehicles)

            if selected_vehicle is None:
                continue

            try:
                miles = int(input("How many miles did you drive?"))

                if miles < 0:
                   print("Miles cannot be negative.")
                else:
                        selected_vehicle.drive(miles)
                        selected_vehicle.display_info()
                        save_vehicles(vehicles)

            except ValueError:
                print("please enter a whole number")

        elif choice == "3":
            selected_vehicle = select_vehicle(vehicles)
            if selected_vehicle is not None:
                selected_vehicle.display_maintenance_info()
       
        elif choice == "4":
            selected_vehicle = select_vehicle(vehicles)

            if selected_vehicle is not None:
                selected_vehicle.service()
                save_vehicles(vehicles)

        elif choice == "5":
            save_vehicles(vehicles)
            print("Saving vehicles and exiting...")
            break
       
        elif choice == "6":
            name = input("Vehicle name: ").strip()

            if not name:
                print("Vehicle name cannot be empty.")
                continue
            try:
                year= int(input("Vehicle year: "))
                mileage = int(input("Current mileage:"))

                if year<= 0 or mileage < 0:
                    print("Year must be positive and mileage cannot be negative.")
                    continue

                vehicles.append(Vehicle(name, year, mileage))
                save_vehicles(vehicles)
                print(f"{name} added successfully!")

            except ValueError:
                print("Year and mileage must be a whole number.")
                continue

        elif choice == "7":
            selected_vehicle = select_vehicle(vehicles)

            if selected_vehicle is None:
                continue

            confirm = input(
                f"Remove {selected_vehicle.name}? (yes/no): "
            ).strip().lower()

            if confirm == "yes":
                vehicles.remove(selected_vehicle)
                save_vehicles(vehicles)
                print("Vehicle removed successfully.")
            else:
                print("Removal canceled.")

        elif choice == "8":
            selected_vehicle = select_vehicle(vehicles)

            if selected_vehicle is None:
                continue

            print("Press Enter to keep the current value.")

            name_input = input(
                f"Name [{selected_vehicle.name}]: "
            ).strip()
            year_input = input(
                f"Year [{selected_vehicle.year}]: "
            ).strip()
            mileage_input = input(
                f"Mileage [{selected_vehicle.mileage}]: "
            ).strip()

            try:
                name = name_input or selected_vehicle.name
                year = (
                    int(year_input)
                    if year_input
                    else selected_vehicle.year
                )
                mileage = (
                    int(mileage_input)
                    if mileage_input
                    else selected_vehicle.mileage
                )

                minimum_mileage = max(
                    selected_vehicle.starting_mileage,
                    selected_vehicle.last_service_mileage,
                    selected_vehicle.last_tire_rotation_mileage or 0,
                    max(
                        (
                            record["mileage"]
                            for record in selected_vehicle.service_history
                        ),
                        default=0
                    )
                )

                if year <= 0:
                    print("Year must be positive.")
                    continue

                if mileage < minimum_mileage:
                    print(
                        f"Mileage cannot be below {minimum_mileage:,}, "
                        "based on the vehicle's tracked history."
                    )
                    continue

            except ValueError:
                print("Year and mileage must be whole numbers.")
                continue

            print(
                f"\nProposed vehicle: {year} {name}, "
                f"{mileage:,} miles"
            )

            confirm = input(
                "Save these changes? (yes/no): "
            ).strip().lower()

            if confirm == "yes":
                selected_vehicle.name = name
                selected_vehicle.year = year
                selected_vehicle.mileage = mileage
                save_vehicles(vehicles)
                print("Vehicle updated and saved.")
            else:
                print("Update canceled.")

            
        elif choice == "9":
            selected_vehicle = select_vehicle(vehicles)
            if selected_vehicle is not None:
                selected_vehicle.display_service_history()

        elif choice == "10":
            selected_vehicle = select_vehicle(vehicles)

            if selected_vehicle is None:
                continue

            print("Enter intervals in miles.")
            print("Press Enter to keep the current value.")

            oil_input = input(
                f"Oil change interval "
                f"[{selected_vehicle.service_interval:,}]: "
            ).strip()

            tire_input = input(
                f"Tire rotation interval "
                f"[{selected_vehicle.tire_rotation_interval:,}]: "
            ).strip()

            try:
                oil_interval = (
                    int(oil_input)
                    if oil_input
                    else selected_vehicle.service_interval
                )

                tire_interval = (
                    int(tire_input)
                    if tire_input
                    else selected_vehicle.tire_rotation_interval
                )

                if oil_interval <= 0 or tire_interval <= 0:
                    print("Intervals must be greater than zero.")
                    continue

            except ValueError:
                print("Enter whole numbers without commas.")
                continue

            print(f"\nOil change: every {oil_interval:,} miles")
            print(f"Tire rotation: every {tire_interval:,} miles")

            confirm = input(
                "Save these intervals? (yes/no): "
            ).strip().lower()

            if confirm == "yes":
                selected_vehicle.service_interval = oil_interval
                selected_vehicle.tire_rotation_interval = tire_interval
                save_vehicles(vehicles)
                print("Maintenance intervals saved.")
            else:
                print("Changes canceled.")
    
        elif choice == "11":
            print("\n=====MAINTENANCE SUMMARY=====")

            if not vehicles:
                print("No vehicles added yet.")
                continue
            for vehicle in vehicles:
                print(f"\n{vehicle.year} {vehicle.name}")
                print(f"Current mileage: {vehicle.mileage:,}")

                oil_remaining = (
                    vehicle.next_service() - vehicle.mileage
                )
                if oil_remaining < 0:
                    print(
                        f"Oil change: OVERDUE by "
                        f"{abs(oil_remaining):,} miles"
                    )
                elif oil_remaining == 0:
                    print(" Oil change: DUE NOW!")

                else:
                    print(
                        f"Oil change: "
                        f"{oil_remaining:,} miles remaining"
                    )
                if vehicle.last_tire_rotation_mileage is None:
                   print("Tire rotation: last service unknown")
                else:
                    tire_remaining = (
                        vehicle.last_tire_rotation_mileage 
                          + vehicle.tire_rotation_interval
                          - vehicle.mileage
                        )
                    if tire_remaining < 0:
                        print(
                            f"Tire rotation: OVERDUE by "
                            f"{abs(tire_remaining):,} miles"
                        )
                    elif tire_remaining == 0:
                        print("Tire rotation: DUE NOW!")
                    else:
                        print(
                            f"Tire rotation: "
                            f"{tire_remaining:,} miles remaining"
                        )
        
            # ===== OPTION 12: EXPORT SERVICE HISTORY =====
        elif choice == "12":
            selected_vehicle = select_vehicle(vehicles)

            if selected_vehicle is None:
                continue

            export_service_history(selected_vehicle)

            # ===== OPTION 13: EDIT SERVICE RECORD =====
        elif choice == "13":
            selected_vehicle = select_vehicle(vehicles)

            if selected_vehicle is None:
                continue

            if selected_vehicle.edit_service_record():
                save_vehicles(vehicles)

        # ===== OPTION 14: DELETE SERVICE RECORD =====
        elif choice == "14":
            selected_vehicle = select_vehicle(vehicles)

            if selected_vehicle is None:
                continue

            if selected_vehicle.delete_service_record():
                save_vehicles(vehicles)

        # ===== OPTION 15: SERVICE SPENDING SUMMARY =====
        elif choice == "15":
            selected_vehicle = select_vehicle(vehicles)

            if selected_vehicle is None:
                continue

            selected_vehicle.display_spending_summary()

        # ===== OPTION 16: RECORD FUEL FILL-UP =====
               # ===== OPTION 16: RECORD FUEL FILL-UP =====
        elif choice == "16":
            selected_vehicle = select_vehicle(vehicles)

            if selected_vehicle is None:
                continue

            if selected_vehicle.record_fuel():
                save_vehicles(vehicles)
        # ===== OPTION 17: VIEW FUEL HISTORY =====
        elif choice == "17":

            selected_vehicle = select_vehicle(vehicles)

            if selected_vehicle is None:
                continue

            selected_vehicle.display_fuel_history()

        # ===== OPTION 18: EDIT FUEL FILL-UP =====
        elif choice == "18":
            selected_vehicle = select_vehicle(vehicles)

            if selected_vehicle is None:
                continue

            if selected_vehicle.edit_fuel_record():
                save_vehicles(vehicles)

                # ===== OPTION 19: DELETE FUEL FILL-UP =====
       
        elif choice == "19":
            selected_vehicle = select_vehicle(vehicles)

            if selected_vehicle is None:
                continue

            if selected_vehicle.delete_fuel_record():
                save_vehicles(vehicles)

        # ===== OPTION 20: EXPORT FUEL HISTORY =====
               # ===== OPTION 20: EXPORT EXCEL WORKBOOK =====
        elif choice == "20":
            selected_vehicle = select_vehicle(vehicles)

            if selected_vehicle is None:
                continue

            export_vehicle_excel(selected_vehicle)
       
        elif choice == "21":
            selected_vehicle = select_vehicle(vehicles)

            if selected_vehicle is None:
                continue

            selected_vehicle.display_fuel_summary()


        else:
            print("Invalid choice. Please enter a number between 1 and 21" ".")

    

if __name__ == "__main__":
        main()
