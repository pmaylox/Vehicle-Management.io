from datetime import date
from decimal import Decimal

def format_mileage(mileage):
    if mileage is None:
        return "Not recorded"
    return f"{mileage:,} miles"

def format_date(iso_text):
    if iso_text is None:
        return "Not recorded"
    return date.fromisoformat(iso_text).strftime("%m/%d/%Y")

def cents_to_dollars(cents):
    return Decimal(cents) / 100
