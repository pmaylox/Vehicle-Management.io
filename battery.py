"""Calendar-based battery tracking derived from saved service records."""
import calendar
import re
from datetime import date
from decimal import Decimal, InvalidOperation


def battery_term_text(months):
    """Display stored months as years, retaining any extra months exactly."""
    years, extra = divmod(months, 12)
    parts = []
    if years:
        parts.append(f"{years} {'year' if years == 1 else 'years'}")
    if extra or not parts:
        parts.append(f"{extra} {'month' if extra == 1 else 'months'}")
    return ", ".join(parts)


def battery_years_to_months(text):
    """Accept years or an existing years/months label; store whole months."""
    text = str(text).strip().casefold()
    mixed = re.fullmatch(r"(\d+) years?,?\s+(\d+) months?", text)
    if mixed:
        months = int(mixed[1]) * 12 + int(mixed[2])
    elif re.fullmatch(r"\d+ months?", text):
        months = int(text.split()[0])
    else:
        try:
            years = Decimal(re.sub(r"\s*years?$", "", text))
            value = years * 12
            if not value.is_finite() or value <= 0 or value != value.to_integral_value():
                raise ValueError
            months = int(value)
        except (InvalidOperation, ValueError, OverflowError):
            raise ValueError("Choose a term in years, or enter a positive value such as 5 or 2.5 years (whole months only).") from None
    if months <= 0 or months > 119987:
        raise ValueError("Choose a positive battery term within the calendar's date range.")
    return months


def battery_details(installed, months, term, today=None, maker=""):
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
    age_days = ((today or date.today()) - details["installed"]).days
    return (f"Battery last replaced: {details['installed']:%B %Y}\n"
            f"Battery age (days): {age_days}\n"
            f"Battery maker: {record['battery'].get('maker') or 'Not recorded'}\n"
            f"{details['term']}: {battery_term_text(details['months'])}\n"
            f"{details['label']}: {details['target']:%m/%d/%Y}\n"
            f"{details['countdown']}")


def service_suggestions(text, history=()):
    choices = ["Battery replaced", "Oil change", "Tire rotation", "Wiper blades replaced",
               "Air filter replaced", "Brake service", "Coolant service"]
    choices += [r["description"] for r in history]
    return tuple(c for c in dict.fromkeys(choices) if text.casefold() in c.casefold())
