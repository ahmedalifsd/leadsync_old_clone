from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def clean_price(value):
    """
    Remove trailing zeros after decimal point.
    1000.00 → 1000
    1000.50 → 1000.50
    1000.10 → 1000.10
    """
    try:
        d = Decimal(str(value))
        # Normalize removes trailing zeros: 1000.00 → 1000, 1000.50 → 1000.5
        normalized = d.normalize()
        # If it's a whole number, return as integer string
        if normalized == normalized.to_integral_value():
            return str(int(normalized))
        # Otherwise return with decimals
        return str(normalized)
    except Exception:
        return value
