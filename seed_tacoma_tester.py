"""Populate only Tacoma TESTER with clearly marked local demonstration data."""
import copy
import json
import os
import shutil
from datetime import date, timedelta, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from Vehicle_Manager import Vehicle

BASE = Path(__file__).resolve().parent
TAG = "tacoma-tester-nov2026"


def document(filename, lines):
    folder = BASE / "receipts" / TAG
    folder.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1100, 1450), "#eeeae2")
    draw = ImageDraw.Draw(image)
    draw.rectangle((45, 35, 1055, 1415), fill="#fffef9", outline="#aaa69e", width=2)
    font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 28)
    heading = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 37)
    draw.text((90, 80), "SAMPLE - NOT VALID", fill="#9f4529", font=heading)
    for index, line in enumerate(lines):
        draw.text((90, 165 + index * 46), line, fill="#292724", font=font)
    draw.text((90, 1320), "Fictional document for MileSage testing only", fill="#9f4529", font=font)
    target = folder / filename
    image.save(target)
    return target.relative_to(BASE).as_posix()


def main():
    source = BASE / "vehicles.json"
    original = json.loads(source.read_text(encoding="utf-8"))
    data = copy.deepcopy(original)
    matches = [v for v in data if "tacoma" in v["name"].lower() and "tester" in v["name"].lower()]
    if len(matches) != 1:
        raise ValueError("Expected exactly one Tacoma TESTER; nothing changed.")
    target = matches[0]
    if any(r.get("sample_batch") == TAG for r in target["fuel_history"] + target["service_history"]):
        raise ValueError("This sample batch already exists; nothing changed.")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = BASE / "data-snapshots" / ("before-tacoma-tester-" + stamp)
    backup.mkdir(parents=True)
    shutil.copy2(source, backup / "vehicles.json")
    start = date(2026, 6, 1)
    prices = ["3.099", "3.159", "3.249", "3.199", "3.359", "3.289"]
    new_fuel = []
    for i in range(18):
        day = start + timedelta(days=169 * i // 17)
        mileage = 500 + 250 * i + (i % 3) * 20
        partial = i in (4, 10, 15)
        gallons = Decimal("6.800") if partial else Decimal(["11.800", "12.450", "13.100", "12.000"][i % 4])
        price = Decimal(prices[i % len(prices)])
        cents = int((gallons * price * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        record = dict(date=day.isoformat(), mileage=mileage, gallons=str(gallons),
                      cost_cents=cents, full_tank=not partial, octane=[87, 89, 93][i % 3],
                      fuel_type=["E10 — gasoline", "E0 — Non-ethanol", "E15 — gasoline"][i % 3],
                      sample_data=True, sample_batch=TAG)
        if i in (0, 8, 17):
            lines = ["MILESAGE TEST FUEL STOP", "Fictional fuel receipt", "", f"Date: {day.isoformat()}",
                     "Vehicle: Toyota Tacoma TESTER", f"Odometer: {mileage}",
                     f"Gallons: {gallons}", f"Price/Gallon: ${price}",
                     f"Octane: {record['octane']}", f"Fuel: {record['fuel_type']}",
                     f"Total: ${Decimal(cents)/100:.2f}", "", "No payment or purchase occurred."]
            record["receipt_photo"] = document(f"fuel-{day}.png", lines)
        new_fuel.append(record)
    target["fuel_history"].extend(new_fuel)
    target["fuel_history"].sort(key=lambda r: (r["date"], r["mileage"]))
    services = [
        ("2026-06-15", 850, "Oil change", 7495, True),
        ("2026-07-18", 1700, "Wiper blades replaced", 3299, False),
        ("2026-08-20", 2500, "Cabin air filter replaced", 2499, False),
        ("2026-09-18", 3250, "Brake inspection", 0, False),
        ("2026-10-15", 3900, "Battery test", None, False),
        ("2026-11-17", 4750, "Oil change and inspection", 8995, True),
    ]
    for i, (day, mileage, description, cents, oil) in enumerate(services):
        record = dict(date=day, mileage=mileage, description=description, cost_cents=cents,
                      oil_reset=oil, tire_reset=False, sample_data=True, sample_batch=TAG)
        if i in (0, 3, 5):
            record["receipt_photo"] = document(f"service-{day}.png", [
                "MILESAGE TEST SERVICE CENTER", "Fictional service work order", "", f"Date: {day}",
                "Vehicle: Toyota Tacoma TESTER", f"Odometer: {mileage}",
                f"Service: {description}", f"Total: ${Decimal(cents)/100:.2f}",
                "", "Sample technician: TEST ONLY", "No work or payment occurred."])
        target["service_history"].append(record)
    target["service_history"].sort(key=lambda r: (r["date"], r["mileage"]))
    target["mileage"] = max(target["mileage"], *(r["mileage"] for r in new_fuel))
    target["last_service_mileage"] = 4750
    # Preserve the existing rotation record, VIN/profile, photo, and other vehicles.
    for before, after in zip(original, data):
        if after is not target:
            assert before == after
    for item in data:
        Vehicle.from_dict(item)
    for record in target["fuel_history"] + target["service_history"]:
        if record.get("sample_batch") == TAG and record.get("receipt_photo"):
            with Image.open(BASE / record["receipt_photo"]) as image:
                image.verify()
    # Avoid overwriting changes made by a running app while documents were built.
    if json.loads(source.read_text(encoding="utf-8")) != original:
        raise RuntimeError("Vehicle data changed during preparation. Backup retained; no data overwritten.")
    temporary = source.with_name("vehicles.tester-seed.tmp")
    temporary.write_text(json.dumps(data, indent=4), encoding="utf-8")
    os.replace(temporary, source)
    print(f"Updated {target['name']}: {len(new_fuel)} sample fills, {len(services)} sample services, 6 mock documents.")
    print(f"Odometer: {target['mileage']:,}; existing history retained; other vehicles unchanged.")
    print(f"Backup: {backup}")


if __name__ == "__main__":
    main()
