"""Vehicle profile storage and public NHTSA vPIC VIN decoding."""
from datetime import datetime, timezone
import json
import re
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROFILE_FIELDS = {
    "make": "Make", "model": "Model", "trim": "Trim", "series": "Series",
    "drive_type": "Drive type", "engine": "Engine", "fuel_type": "Fuel type",
    "transmission": "Transmission", "body_style": "Body style", "doors": "Doors",
    "plant_country": "Assembly country", "color": "Color", "paint_code": "Paint code"
}


def normalize_vin(value):
    vin = value.strip().upper()
    if vin and not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", vin):
        raise ValueError("Enter a full 17-character VIN, without I, O, or Q. Leave blank if unknown.")
    return vin


def clean_profile(profile):
    if not isinstance(profile, dict):
        return {}
    return {key: value.strip() for key, value in profile.items()
            if key in {"vin", "decoded_at", "source", *PROFILE_FIELDS}
            and isinstance(value, str) and value.strip()}


def decode_result(data):
    results = data.get("Results", [])
    if not results or not isinstance(results[0], dict):
        raise ValueError("The VIN service returned no vehicle details.")
    raw = results[0]
    errors = {code.strip() for code in str(raw.get("ErrorCode", "")).split(",") if code.strip()}
    if errors - {"0"}:
        raise ValueError("VIN could not be verified: " + (raw.get("ErrorText") or "Check all 17 characters and the model year."))
    profile = {}
    mapping = {"make": "Make", "model": "Model", "trim": "Trim", "series": "Series",
               "drive_type": "DriveType", "fuel_type": "FuelTypePrimary", "body_style": "BodyClass",
               "doors": "Doors", "plant_country": "PlantCountry"}
    for key, source in mapping.items():
        value = raw.get(source)
        if isinstance(value, str) and value.strip():
            profile[key] = value.strip()
    engine = [f"{raw['DisplacementL']} L" if raw.get("DisplacementL") else "",
              f"{raw['EngineCylinders']} cylinders" if raw.get("EngineCylinders") else "",
              raw.get("EngineConfiguration") or "", raw.get("EngineModel") or ""]
    transmission = [raw.get("TransmissionStyle") or "",
                    f"{raw['TransmissionSpeeds']} speeds" if raw.get("TransmissionSpeeds") else ""]
    if any(engine):
        profile["engine"] = " · ".join(part for part in engine if part)
    if any(transmission):
        profile["transmission"] = " · ".join(part for part in transmission if part)
    year = str(raw.get("ModelYear") or "")
    if not year.isdigit() or not profile.get("make") or not profile.get("model"):
        raise ValueError("The VIN service did not return a usable year, make, and model. Enter details manually.")
    return int(year), profile


def lookup_vin(value, model_year=None):
    vin = normalize_vin(value)
    if not vin:
        raise ValueError("Enter a VIN before looking it up.")
    parameters = {"format": "json"}
    if str(model_year or "").isdigit():
        parameters["modelyear"] = str(model_year)
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?{urlencode(parameters)}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "VehicleManager/1.0"})
    try:
        with urlopen(request, timeout=25) as response:
            data = json.load(response)
    except (URLError, TimeoutError, OSError, ValueError) as error:
        raise RuntimeError("VIN lookup is unavailable. Check your internet connection or enter the details manually.") from error
    year, profile = decode_result(data)
    profile.update(vin=vin, source="NHTSA vPIC", decoded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    return year, profile


def profile_summary(vehicle):
    profile = clean_profile(getattr(vehicle, "profile", {}))
    if not profile:
        return "VIN and specifications not recorded. Add them in Edit Vehicle."
    lines = [f"VIN: {profile['vin']}"] if profile.get("vin") else []
    lines.extend(f"{label}: {profile[key]}" for key, label in PROFILE_FIELDS.items() if profile.get(key))
    return "\n".join(lines)
