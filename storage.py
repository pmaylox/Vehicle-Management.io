from pathlib import Path
import json
import shutil
import os
import time
from Vehicle_Manager import Vehicle

DATA_FILE = Path(__file__).with_name("vehicles.json")

def load_vehicles():
    if not DATA_FILE.exists():
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        saved_data = json.load(file)

    if not isinstance(saved_data, list):
        raise ValueError("Saved vehicle data must be a list.")

    return [Vehicle.from_dict(data) for data in saved_data]

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
            if attempt == 2:
                raise

            time.sleep(0.5)