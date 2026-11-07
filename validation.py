from decimal import Decimal, InvalidOperation


def parse_cost_cents(text):
    try:
        cost = Decimal(text)
    except InvalidOperation:
        raise ValueError("Enter a cost like 45.10.")

    if not cost.is_finite():
        raise ValueError("Cost must be a number.")

    if cost < 0:
        raise ValueError("Cost cannot be negative.")

    cents = cost * 100
    if cents != cents.to_integral_value():
        raise ValueError("Cost can't have more than two decimal places.")

    return int(cents)