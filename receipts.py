"""Local receipt OCR, conservative field extraction, and photo attachments."""
from datetime import date
from pathlib import Path
import json
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from uuid import uuid4

BASE = Path(__file__).resolve().parent
RECEIPTS = BASE / "receipts"


def recognize_photo(path):
    from PIL import Image, ImageOps
    # Normalize phone orientation and size for the Windows OCR engine.
    with TemporaryDirectory(prefix="receipt-ocr-") as folder:
        prepared = Path(folder) / "receipt.png"
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((2400, 2400))
            image.save(prepared)
        result = subprocess.run([
            "powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-File", str(BASE / "receipt_ocr.ps1"), "-ImagePath", str(prepared.resolve())
        ], capture_output=True, encoding="utf-8-sig", errors="replace", timeout=90,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode:
            raise RuntimeError("Windows could not read this photo. Try a clearer image, or enter the details manually.\n" + result.stderr[-700:])
        lines = json.loads(result.stdout or "[]")
        return lines if isinstance(lines, list) else [lines] if lines else []


def extract_fields(lines, kind):
    """Only propose explicitly labeled fields. No inference of full tank/resets."""
    text = "\n".join(lines)
    result = {}
    # OCR sometimes inserts whitespace between date digits.
    for token in re.findall(r"\b\d[\d ]{0,3}[-/]\d{1,2}[-/]\d{1,4}\b", text):
        token = token.replace(" ", "")
        parts = re.split(r"[-/]", token)
        try:
            if len(parts[0]) == 4:
                y, m, d = map(int, parts)
            else:
                m, d, y = map(int, parts)
                y = y + 2000 if y < 100 else y
            result["date"] = date(y, m, d).isoformat()
            break
        except ValueError:
            continue

    def labeled_number(pattern, decimal_places=None):
        # A value may appear on the following line, but never beyond it.
        for index, line in enumerate(lines):
            if pattern.startswith(r"\b(?:grand") and re.search(r"\bsub[ -]*total\b|\btotal\s+(?:savings|tax|gallons|miles|quantity)\b", line, re.I):
                continue
            match = re.search(pattern, line, re.I)
            if not match:
                continue
            tail = line[match.end():].strip(" :#$=\t")
            if not tail and index + 1 < len(lines):
                tail = lines[index + 1].strip(" :#$=\t")
            found = re.match(r"\$?\s*(\d[\d,]*(?:\.\d+)?)\b", tail)
            if found:
                number = found[1].replace(",", "")
                if decimal_places is None or len(number.partition(".")[2]) <= decimal_places:
                    return number
        return None

    total = labeled_number(r"\b(?:grand\s+total|total\s+(?:paid|due|amount)|amount\s+(?:paid|due)|total)\b", 2)
    if total is not None:
        result["cost"] = total
    mileage = labeled_number(r"\b(?:odometer|odo|mileage(?:\s+in)?)\b", 0)
    if mileage is not None:
        result["mileage"] = mileage
    if kind == "fuel":
        gallons = labeled_number(r"\b(?:gallons?(?:\s+(?:pumped|added))?|gal|volume)\b")
        if gallons is not None:
            result["gallons"] = gallons
        # Also recognize receipts using "12.345 GAL".
        if "gallons" not in result:
            match = re.search(r"\b(\d+\.\d+)\s*(?:GAL|GALLONS)\b", text, re.I)
            if match:
                result["gallons"] = match[1]
        octane = labeled_number(r"\b(?:octane|AKI)\b", 0)
        if octane is not None and 1 <= int(octane) <= 150:
            result["octane"] = octane
        # Explicit blends only; never infer ethanol percentage from Regular/Premium.
        if re.search(r"\b(?:DIESEL|BIODIESEL)\b", text, re.I):
            blend = re.search(r"\bB(5|20|100)\b", text, re.I)
            result["fuel_type"] = "Diesel" + (f" — B{blend[1]}" if blend else "")
            result.pop("octane", None)
        else:
            blend = re.search(r"\bE(0|10|15|85)\b", text, re.I)
            if blend:
                result["fuel_type"] = {"0": "E0 — Non-ethanol", "10": "E10 — gasoline", "15": "E15 — gasoline", "85": "E85 — flex fuel"}[blend[1]]
            elif re.search(r"\b(?:NON[- ]ETHANOL|ETHANOL[- ]FREE)\b", text, re.I):
                result["fuel_type"] = "E0 — Non-ethanol"
    else:
        services = []
        for pattern, label in [(r"\boil\s+(?:change|service)\b", "Oil change"),
                               (r"\btire\s+rotation\b", "Tire rotation"),
                               (r"\bbattery\s+(?:replace(?:d|ment)?|install(?:ed|ation)?)\b", "Battery replaced"),
                               (r"\b(?:engine\s+)?air\s+filter\b", "Air filter replaced"),
                               (r"\bbrake\s+(?:service|pads?)\b", "Brake service")]:
            if re.search(pattern, text, re.I):
                services.append(label)
        if services:
            result["description"] = "; ".join(services)
    return result


def receipt_path(relative):
    path = (BASE / relative).resolve()
    if not path.is_relative_to(RECEIPTS.resolve()):
        raise ValueError("Invalid receipt attachment location.")
    return path


def store_photo(source):
    from PIL import Image
    with Image.open(source) as image:
        image.verify()
    RECEIPTS.mkdir(exist_ok=True)
    destination = RECEIPTS / (uuid4().hex + Path(source).suffix.lower())
    try:
        shutil.copy2(source, destination)
    except OSError:
        destination.unlink(missing_ok=True)
        raise
    return destination.relative_to(BASE).as_posix()
