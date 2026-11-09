"""Calendar-based battery tracking derived from saved service records."""
import calendar
from datetime import date


def battery_details(installed, months, term, today=None):
    today = today or date.today()
    installed = date.fromisoformat(installed)
    if installed > today:
        raise ValueError("Battery installation date cannot be in the future.")
    if isinstance(months, bool) or not isinstance(months, int) or months <= 0:
        raise ValueError("Battery term must be a positive whole number of months.")
    if term not in ("Expected life", "Warranty"):
        raise ValueError("Choose Expected life or Warranty.")
    month_index = installed.year * 12 + installed.month - 1 + months
    year, month = divmod(month_index, 12)
    month += 1
    if year > 9999:
        raise ValueError("Battery term produces a date beyond year 9999.")
    target = date(year, month, min(installed.day, calendar.monthrange(year, month)[1]))
    days = (target - today).days
    day_text = f"{abs(days):,} {'day' if abs(days) == 1 else 'days'}"
    label = "Warranty ends" if term == "Warranty" else "Estimated replacement"
    if days > 0:
        countdown = f"{day_text} remaining"
    elif days == 0:
        countdown = "Warranty ends today" if term == "Warranty" else "Estimated replacement date is today"
    else:
        countdown = f"{'Warranty expired' if term == 'Warranty' else 'Past estimated replacement date'} by {day_text}"
    return {"installed": installed, "target": target, "label": label,
            "countdown": countdown, "months": months, "term": term}


def battery_summary(vehicle, today=None):
    records = [r for r in vehicle.service_history if r.get("battery")]
    if not records:
        return "Battery last replaced: Not recorded"
    try:
        record = max(enumerate(records), key=lambda item: (item[1]["battery"]["installed"], item[0]))[1]
        details = battery_details(**record["battery"], today=today)
    except (ValueError, TypeError, KeyError):
        return "Battery details need correction in Edit Service."
    return (f"Battery last replaced: {details['installed']:%B %Y}\n"
            f"{details['term']}: {details['months']} months\n"
            f"{details['label']}: {details['target']:%m/%d/%Y}\n"
            f"{details['countdown']}")


def service_suggestions(text, history=()):
    choices = ["Battery replaced", "Oil change", "Tire rotation", "Wiper blades replaced",
               "Air filter replaced", "Brake service", "Coolant service"]
    choices += [r["description"] for r in history]
    return tuple(c for c in dict.fromkeys(choices) if text.casefold() in c.casefold())
