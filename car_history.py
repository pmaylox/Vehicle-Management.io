"""Independent, user-reviewed vehicle history (not a CARFAX data integration).

History findings never change MileSage's odometer, maintenance, or expense logs.
"""
from calendar import monthrange
from datetime import date

HISTORY_CATEGORIES = (
    "Accident / damage", "Title / registration", "Ownership",
    "Odometer", "Service", "Recall", "Other",
)
HISTORY_SOURCES = (
    "CARFAX Car Care", "CARFAX Vehicle History Report",
    "Shop / dealership", "Other",
)
CARFAX_CARE_URL = "https://www.carfax.com/Service"


def _date_string(value):
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def empty_car_history():
    return {
        "last_review_date": None,
        "review_source": "",
        "review_notes": "",
        "events": [],
    }


def clean_car_history(raw):
    """Normalize old or imported records without touching other vehicle fields."""
    out = empty_car_history()
    if not isinstance(raw, dict):
        return out
    out["last_review_date"] = _date_string(raw.get("last_review_date"))
    out["review_source"] = str(raw.get("review_source") or "")[:100]
    out["review_notes"] = str(raw.get("review_notes") or "")[:2000]
    events = raw.get("events")
    if isinstance(events, list):
        for event in events:
            if not isinstance(event, dict):
                continue
            happened = _date_string(event.get("date"))
            if not happened:
                continue
            try:
                mileage = event.get("mileage")
                if mileage in ("", None):
                    mileage = None
                elif isinstance(mileage, bool):
                    continue
                elif isinstance(mileage, int) and mileage >= 0:
                    pass
                else:
                    if not str(mileage).isdigit():
                        continue
                    mileage = int(mileage)
                if mileage is not None and mileage > 900_000_000:
                    continue
            except (TypeError, ValueError):
                continue
            out["events"].append({
                "date": happened,
                "category": str(event.get("category") or "Other")[:80],
                "description": str(event.get("description") or "")[:1000],
                "source": str(event.get("source") or "Other")[:100],
                "mileage": mileage,
                "recorded_by": "user",
            })
    return out


def next_history_review(last_review_date):
    """Review anniversary, including Feb 29 -> Feb 28 in non-leap years."""
    iso = _date_string(last_review_date)
    if iso is None:
        return None
    d = date.fromisoformat(iso)
    next_year = d.year + 1
    day = min(d.day, monthrange(next_year, d.month)[1])
    return date(next_year, d.month, day).isoformat()


def history_review_status(history, today=None):
    if today is None:
        today = date.today()
    if isinstance(today, str):
        today = date.fromisoformat(today)
    last = clean_car_history(history)["last_review_date"]
    due = next_history_review(last)
    return {
        "last_review_date": last,
        "next_review_date": due,
        "due": due is None or due <= today.isoformat(),
    }


def mark_history_review(history, reviewed_on, source, notes="", today=None):
    """Return new history after explicit user confirmation of a review."""
    if today is None:
        today = date.today()
    iso = _date_string(reviewed_on)
    if not iso or date.fromisoformat(iso) > today:
        raise ValueError("Enter a valid review date, not in the future.")
    if source not in HISTORY_SOURCES:
        raise ValueError("Choose a history source.")
    updated = clean_car_history(history)
    updated["last_review_date"] = iso
    updated["review_source"] = source
    updated["review_notes"] = str(notes).strip()[:2000]
    return updated


def add_history_event(history, happened_on, category, description, source,
                      mileage=None, today=None):
    """Add a reported finding, without changing the live vehicle odometer."""
    if today is None:
        today = date.today()
    iso = _date_string(happened_on)
    if not iso or date.fromisoformat(iso) > today:
        raise ValueError("Enter a valid event date, not in the future.")
    if category not in HISTORY_CATEGORIES:
        raise ValueError("Choose an event category.")
    if source not in HISTORY_SOURCES:
        raise ValueError("Choose an event source.")
    description = str(description).strip()
    if not description:
        raise ValueError("Describe the reported event.")
    if mileage not in (None, ""):
        if isinstance(mileage, bool) or not str(mileage).isdigit():
            raise ValueError("Reported mileage must be a whole number.")
        mileage = int(mileage)
        if mileage > 900_000_000:
            raise ValueError("Reported mileage is too large.")
    else:
        mileage = None
    updated = clean_car_history(history)
    updated["events"].append({
        "date": iso,
        "category": category,
        "description": description[:1000],
        "source": source,
        "mileage": mileage,
        "recorded_by": "user",
    })
    return updated
