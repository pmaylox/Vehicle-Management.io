from cmath import cos
from datetime import date
from decimal import Decimal, InvalidOperation
class Vehicle:
    def __init__(self, name, year, mileage, service_interval=5000):
        self.name = name
        self.year = year
        self.mileage = mileage
        self.starting_mileage = mileage
        self.last_service_mileage = mileage
        self.service_interval = service_interval
        self.service_history = []  # Initialize an empty service history list
        self.fuel_history = []  # Initialize an empty fuel history list
        self.tire_rotation_interval = 5000  # Default tire rotation interval
        self.last_tire_rotation_mileage = None

    def drive(self, miles):
        self.mileage += miles

    def display_info(self):
        print(f"Your {self.year} {self.name} has {self.mileage:,} miles on it")

    def service(self):
        description = input("Service performed: ").strip()

        if not description:
            print("Service description cannot be empty.")
            return

        print("\nWhich maintenance countdown should reset?")
        print("1. Oil change")
        print("2. Tire rotation")
        print("3. Both")
        print("4. Neither")

        reset_choice = input("Choose (1-4): ").strip()

        if reset_choice not in ("1", "2", "3", "4"):
            print("Invalid choice. Service was not recorded.")
            return
        while True:
            cost_input = input(
                "Service cost (example: 89.95, Enter if unknown):").strip()

            if not cost_input:
                cost_cents= None
                break

            try:
                cost = Decimal(cost_input)

                if not cost.is_finite() or cost < 0:
                    print("Enter a valid, non-negative cost.")
                    continue

                cents = cost * 100
                if cents != cents.to_integral_value():
                    print("Use no more than two decimal places.")
                    continue

                cost_cents = int(cents)
                break
            except (InvalidOperation, ValueError):
                print("Enter a number without dollar signs or commas.")

        record = {
            "date": date.today().isoformat(),
            "mileage": self.mileage,
            "description": description,
            "cost_cents": cost_cents,
            "oil_reset": reset_choice in ("1", "3"),
            "tire_reset": reset_choice in ("2", "3")
        }

        self.service_history.append(record)

        if reset_choice in ("1", "3"):
            self.last_service_mileage = self.mileage

        if reset_choice in ("2", "3"):
            self.last_tire_rotation_mileage = self.mileage

        print(f"Service recorded for your {self.year} {self.name}.")

    def display_maintenance_info(self):
        print(f"\nMaintenance Information: {self.year} {self.name}")
        print(f"Current mileage: {self.mileage:,} miles")
        print(f"Total miles driven: {self.miles_driven():,} miles")

        print("\nOil change")
        print(f"Interval: {self.service_interval:,} miles")
        print(f"Last tracked service: {self.last_service_mileage:,} miles")
        print(f"Next scheduled at: {self.next_service():,} miles")

        if self.check_maintenance():
            print("Oil change is due!")
        else:
            print(f"Miles remaining: {self.miles_until_service():,}")

        print("\nTire rotation")
        print(f"Interval: {self.tire_rotation_interval:,} miles")

        if self.last_tire_rotation_mileage is None:
            print("Last tire rotation mileage is unknown.")
            print("Record a tire rotation to start its countdown.")
        else:
            next_rotation = (
                self.last_tire_rotation_mileage
                + self.tire_rotation_interval
            )

            print(
                f"Last rotation: "
                f"{self.last_tire_rotation_mileage:,} miles"
            )
            print(f"Next scheduled at: {next_rotation:,} miles")

            if self.mileage >= next_rotation:
                print("Tire rotation is due!")
            else:
                remaining = next_rotation - self.mileage
                print(f"Miles remaining: {remaining:,}")

    def get_mileage(self):
        return self.mileage

    def current_mileage(self):
        return self.mileage

    def miles_driven(self):
        return self.mileage - self.starting_mileage

    def miles_since_service(self):
        return self.mileage - self.last_service_mileage

    def check_maintenance(self):
        return self.miles_since_service() >= self.service_interval

    def miles_until_service(self):
        return max(0, self.next_service() - self.mileage)

    def next_service(self):
        next_service = self.service_interval + self.last_service_mileage
        return next_service
    def display_service_history(self):
        print(f"\nService history: {self.year} {self.name}")

        if not self.service_history:
            print("No service records yet.")
            return

        for number, record in enumerate(self.service_history, start=1):
            print(
                f"\n{number}. {record['date']} | "
                f"{record['mileage']:,} miles"
            )
            print(f"   Service: {record['description']}")

            cost_cents = record.get("cost_cents")

            if cost_cents is None:
                print("   Cost: not recorded")
            else:
                print(f"   Cost: ${cost_cents / 100:.2f}")

            if "oil_reset" not in record or "tire_reset" not in record:
                print("   Countdown resets: not tracked in this older record")
                continue

            resets = []

            if record["oil_reset"]:
                resets.append("Oil change")

            if record["tire_reset"]:
                resets.append("Tire rotation")

            if resets:
                print(f"Countdown resets: {', '.join(resets)}")
            else:
                print("Countdown resets: Neither")

    def edit_service_record(self):
        if not self.service_history:
            print("No service records to edit.")
            return False

        self.display_service_history()

        try:
            choice = int(input("\nRecord number to edit: "))

            if not 1 <= choice <= len(self.service_history):
                print("Invalid record number.")
                return False

        except ValueError:
            print("Please enter a whole number.")
            return False

        record = self.service_history[choice - 1]

        description_input = input(
            f"Description [{record['description']}]: "
        ).strip()

        description = description_input or record["description"]
        current_cost = record.get("cost_cents")

        print(f"Current cost: {self.format_service_cost(record)}")
        print("Press Enter to keep it, or type unknown to clear it.")

        while True:
            cost_input = input("New cost: ").strip()

            if not cost_input:
                cost_cents = current_cost
                break

            if cost_input.lower() == "unknown":
                cost_cents = None
                break

            try:
                cost = Decimal(cost_input)

                if not cost.is_finite() or cost < 0:
                    print("Enter a valid, non-negative cost.")
                    continue

                cents = cost * 100

                if cents != cents.to_integral_value():
                    print("Use no more than two decimal places.")
                    continue

                cost_cents = int(cents)
                break

            except InvalidOperation:
                print("Enter a number without dollar signs or commas.")

        if (
            description == record["description"]
            and cost_cents == current_cost
        ):
            print("No changes made.")
            return False

        proposed_record = {
            "description": description,
            "cost_cents": cost_cents
        }

        print(f"\nDescription: {description}")
        print(f"Cost: {self.format_service_cost(proposed_record)}")

        confirm = input(
            "Save these changes? (yes/no): "
        ).strip().lower()

        if confirm != "yes":
            print("Edit canceled.")
            return False

        record["description"] = description
        record["cost_cents"] = cost_cents

        print("Service record updated.")
        return True

    def delete_service_record(self):
        if not self.service_history:
            print("No service records to delete.")
            return False

        self.display_service_history()

        try:
            choice = int(input("\nRecord number to delete: "))

            if not 1 <= choice <= len(self.service_history):
                print("Invalid record number.")
                return False

        except ValueError:
            print("Please enter a whole number.")
            return False

        record = self.service_history[choice - 1]

        print(
            f"\nSelected: {record['date']} | "
            f"{record['mileage']:,} miles | "
            f"{record['description']}"
        )
        print(
            "Deleting this history entry will keep the current "
            "oil and tire maintenance countdowns unchanged."
        )

        confirm = input(
            "Delete this record? (yes/no): "
        ).strip().lower()

        if confirm != "yes":
            print("Deletion canceled.")
            return False

        self.service_history.pop(choice - 1)
        print("Service record deleted.")
        return True

    def display_spending_summary(self):
        pass

    def display_fuel_history(self):
        print(f"\nFuel history: {self.year} {self.name}")

        if not self.fuel_history:
            print("No fuel fill-ups recorded.")
            return

        previous_full_mileage = None
        gallons_since_full = Decimal("0")

        for number, record in enumerate(self.fuel_history, start=1):
            gallons = Decimal(record["gallons"])
            cost = Decimal(record["cost_cents"]) / 100
            full_tank = record["full_tank"]

            print(
                f"\n{number}. {record['date']} | "
                f"{record['mileage']:,} miles"
            )
            print(f"   Fuel added: {gallons} US gallons")
            print(f"   Total cost: ${cost:,.2f}")
            price_per_gallon = cost / gallons
            print(
                f"   Price per US gallon: "
                f"${price_per_gallon:.3f}"
            )
            print(f"   Full tank: {'Yes' if full_tank else 'No'}")

            if previous_full_mileage is None:
                if full_tank:
                    previous_full_mileage = record["mileage"]
                    print("   MPG: starting full-tank reading")
                else:
                    print("   MPG: waiting for a starting full tank")

                continue

            gallons_since_full += gallons

            if not full_tank:
                print("   MPG: waiting for the next full tank")
                continue

            miles = record["mileage"] - previous_full_mileage

            if miles > 0 and gallons_since_full > 0:
                mpg = Decimal(miles) / gallons_since_full
                print(f"   Fuel economy: {mpg:.2f} MPG")
            else:
                print("   MPG: insufficient distance to calculate")

            previous_full_mileage = record["mileage"]
            gallons_since_full = Decimal("0")

    def record_fuel(self):
        print(f"\nRecord fuel: {self.year} {self.name}")
        print("Enter numbers without commas or dollar signs.")

        try:
            mileage = int(input("Odometer mileage: "))

            if mileage < self.mileage:
                print(
                    f"Mileage cannot be below the current "
                    f"{self.mileage:,} miles."
                )
                return False

            gallons = Decimal(
                input("US gallons added: ").strip()
            )
            cost = Decimal(
                input(
                    "Total paid for this fill-up (not price per gallon): "
                ).strip()
            )

            if not gallons.is_finite() or gallons <= 0:
                print("Gallons must be greater than zero.")
                return False

            if not cost.is_finite() or cost < 0:
                print("Cost must be zero or greater.")
                return False

            cents = cost * 100

            if cents != cents.to_integral_value():
                print(
                    "Cost must have no more than two decimal places."
                )
                return False

        except (ValueError, InvalidOperation):
            print("Invalid entry. Fill-up was not recorded.")
            return False

        full_input = input(
            "Did you fill the tank completely? (yes/no): "
        ).strip().lower()

        if full_input not in ("yes", "no"):
            print("Enter yes or no. Fill-up was not recorded.")
            return False

        cost_cents = int(cents)
        full_tank = full_input == "yes"
        price_per_gallon = cost / gallons


        print(f"\nOdometer: {mileage:,} miles")
        print(f"Fuel added: {gallons} US gallons")
        print(f"Total cost: ${cost:.2f}")
        print(f"Price per US gallon: ${price_per_gallon:.3f}")
        print(f"Full tank: {full_input}")

        confirm = input(
            "Save this fill-up? (yes/no): "
        ).strip().lower()

        if confirm != "yes":
            print("Fill-up canceled.")
            return False

        self.fuel_history.append({
            "date": date.today().isoformat(),
            "mileage": mileage,
            "gallons": str(gallons),
            "cost_cents": cost_cents,
            "full_tank": full_tank
        })

        self.mileage = mileage

        print("Fuel fill-up recorded and vehicle mileage updated.")
        return True

    def edit_fuel_record(self):
    
        if not self.fuel_history:
            print("No fuel records to edit.")
            return False

        self.display_fuel_history()

        try:
            choice = int(input("\nRecord number to edit:"))

            if not 1 <= choice <= len(self.fuel_history):
                print("Invalid record number.")
                return False

        except ValueError:
            print("Please enter a whole number")
            return False

        index = choice - 1
        record = self.fuel_history[index]
        current_cost = Decimal(record["cost_cents"]) / 100

        print("Press Enter to keep the current value.")

        mileage_input = input(
            f"Odometer [{record['mileage']}]:").strip()
        gallons_input = input(
            f"US gallons [{record['gallons']}]").strip()
        cost_input = input(
            f"Total fuel cost [{current_cost:,.2f}]").strip()
        full_input = input(
            f"Full tank [{'yes' if record['full_tank'] else 'no'}]:").strip().lower()

        try:
            mileage = (
                int(mileage_input)
                if mileage_input
                else record["mileage"]
            )
            gallons = Decimal(gallons_input or record["gallons"])
            cost = (
                Decimal(cost_input)
                if cost_input
                else current_cost
            )

            if not gallons.is_finite() or gallons <= 0:
                print("Gallons must be greater than zero.")
                return False
            
            if not cost.is_finite() or cost < 0:
                print("cost must be zero or greater.")
                return False

            cents = cost * 100

            if cents != cents.to_integral_value():
                print("Cost must have no more than two decimal places.")
                return False

        except (ValueError, InvalidOperation):
            print("Invalid number. No changes saved.")
            return False

        if full_input not in ("", "yes", "no"):
            print("Full tank must be yes or no.")
            return False

        minimum_mileage = self.starting_mileage

        if index > 0:
            minimum_mileage = max(
                minimum_mileage,
                self.fuel_history[index - 1]["mileage"]
            )

        maximum_mileage = (
            self.fuel_history[index + 1]["mileage"]
            if index + 1 < len(self.fuel_history)
            else self.mileage
        )

        if not minimum_mileage <= mileage <= maximum_mileage:
            print(
                f"Mileage must be between {minimum_mileage:,} "
                f"and {maximum_mileage:,} to preserve record order"
                "and stay within the current odometer."
            )
            return False

        full_tank = (
            record["full_tank"]if not full_input
            else full_input == "yes"
        )

        updated = record.copy()
        updated.update({
            "mileage": mileage,
            "gallons": str(gallons),
            "cost_cents": int(cents),
            "full_tank": full_tank
        })

        if updated == record:
            print("No changes made.")
            return False

        print(f"\nOdometer: {mileage:,} miles")
        print(f"Fuel added: {gallons} US gallons")
        print(f"Total cost: ${cost:.2f}")
        print(f"Full tank: {'yes' if full_tank else 'no'}")
        print("The vehicle's current odometer will remain unchanged.")

        confirm = input(
            "Save these changes?(yes/no): "
        ).strip().lower()

        if confirm != "yes":
            print("Edit canceled.")
            return False

        
        self.fuel_history[index] = updated
        print("Fuel record updated successfully.")
        return True


    def delete_fuel_record(self):
        if not self.fuel_history:
            print("No fuel records to delete.")
            return False

        self.display_fuel_history()

        try:
            choice = int(input("\nRecord number to delete: "))

            if not 1 <= choice <= len(self.fuel_history):
                print("Invalid record number.")
                return False

        except ValueError:
            print("Please enter a whole number.")
            return False

        record = self.fuel_history[choice - 1]
        cost = Decimal(record["cost_cents"]) / 100

        print(f"\nDate: {record['date']}")
        print(f"Odometer: {record['mileage']:,} miles")
        print(f"Fuel added: {record['gallons']} US gallons")
        print(f"Total cost: ${cost:.2f}")
        print(
            f"Full tank: {'Yes' if record['full_tank'] else 'No'}"
        )

        print(
            "\nDeleting a fill-up can make MPG inaccurate because "
            "its gallons will no longer be included."
        )
        print("The vehicle's current odometer will remain unchanged.")

        confirm = input(
            "Delete this fill-up? (yes/no): "
        ).strip().lower()

        if confirm != "yes":
            print("Deletion canceled.")
            return False

        self.fuel_history.pop(choice - 1)
        print("Fuel record deleted.")
        return True

    def display_fuel_summary(self):
        print(f"\nFuel spending: {self.year} {self.name}")

        if not self.fuel_history:
            print("No fuel fill-ups recorded.")
            return

        total_gallons = Decimal("0")
        total_cents = 0

        for record in self.fuel_history:
            total_gallons += Decimal(record["gallons"])
            total_cents += record["cost_cents"]

        total_cost = Decimal(total_cents) / 100

        print(f"Fill-ups recorded: {len(self.fuel_history)}")
        print(f"Total fuel added: {total_gallons:,.3f} US gallons")
        print(f"Total fuel cost: ${total_cost:,.2f}")

        if total_gallons > 0:
            average_price = total_cost / total_gallons
            print(
                f"Average price per US gallon: "
                f"${average_price:.3f}"
            )

            
    def to_dict(self):
        return {
            "name": self.name,
            "year": self.year,
            "mileage": self.mileage,
            "starting_mileage": self.starting_mileage,
            "last_service_mileage": self.last_service_mileage,
            "service_interval": self.service_interval,
            "service_history": self.service_history,
            "tire_rotation_interval": self.tire_rotation_interval,
            "last_tire_rotation_mileage": self.last_tire_rotation_mileage,
            "fuel_history": self.fuel_history
        }
    @classmethod
    def from_dict(cls, data):
        vehicle = cls(
            data["name"],
            data["year"],
            data["starting_mileage"],
            data["service_interval"]
        )

        vehicle.mileage = data["mileage"]
        vehicle.last_service_mileage = data["last_service_mileage"]
        vehicle.service_history = data.get("service_history", [])
        vehicle.fuel_history = data.get("fuel_history", [])

        vehicle.tire_rotation_interval = data.get(
            "tire_rotation_interval", 5000
        )
        vehicle.last_tire_rotation_mileage = data.get(
            "last_tire_rotation_mileage"
        )

        return vehicle

    @staticmethod
    def format_service_cost(record):
        cost_cents = record.get("cost_cents")

        if cost_cents is None:
            return "Not recorded"

        return f"{Decimal(cost_cents) / 100:.2f}"